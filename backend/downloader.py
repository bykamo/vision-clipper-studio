import json
import os
import subprocess

import yt_dlp

from backend.utils import log
from backend.yt_cookies import resolve_cookie_file


# Resolusi lebih tinggi = crop 9:16 lebih tajam (crop dari 1080p hanya 608px lebar lalu di-upscale,
# crop dari 4K = 1215px lalu di-downscale). Batas atas bisa diatur via env VC_MAX_DOWNLOAD_HEIGHT
# (default 1080p agar unduhan cepat dan hemat bandwidth, atau 1440/2160 jika butuh resolusi ekstra).
PREFERRED_MIN_HEIGHT = 1080
MIN_ACCEPTABLE_HEIGHT = 720


def _max_download_height():
    try:
        value = int(os.environ.get("VC_MAX_DOWNLOAD_HEIGHT", "1080"))
    except ValueError:
        value = 1080
    return max(PREFERRED_MIN_HEIGHT, value)


def _build_format_selector(max_height):
    """Prioritas: H.264 (avc1) >=1080p -> format lain >=1080p -> H.264 >=720p -> format lain >=720p. Menghindari AV1 yang sering di-throttle."""
    return (
        f"bestvideo[height>={PREFERRED_MIN_HEIGHT}][height<={max_height}][vcodec^=avc1]+bestaudio[acodec^=mp4a]"
        f"/bestvideo[height>={PREFERRED_MIN_HEIGHT}][height<={max_height}][vcodec^=avc1]+bestaudio"
        f"/bestvideo[height>={PREFERRED_MIN_HEIGHT}][height<={max_height}]+bestaudio"
        f"/bestvideo[height>={MIN_ACCEPTABLE_HEIGHT}][height<={max_height}][vcodec^=avc1]+bestaudio"
        f"/bestvideo[height>={MIN_ACCEPTABLE_HEIGHT}][height<={max_height}]+bestaudio"
        f"/best[height>={MIN_ACCEPTABLE_HEIGHT}][height<={max_height}]"
    )


def _selected_video_format(info):
    """Return the video stream selected by yt-dlp, excluding audio-only streams."""
    requested_formats = info.get("requested_formats") or []
    for selected_format in requested_formats:
        if selected_format.get("vcodec") not in (None, "none"):
            return selected_format
    return info if info.get("vcodec") not in (None, "none") else None


def _selected_video_height(info):
    selected_format = _selected_video_format(info)
    if not selected_format:
        return None
    height = selected_format.get("height")
    try:
        return int(height) if height is not None else None
    except (TypeError, ValueError):
        return None


def _probe_video_resolution(file_path):
    """Probe resolusi via ffprobe (OpenCV sering gagal membaca AV1/VP9 yang dipakai YouTube untuk 1440p/4K)."""
    try:
        from backend.utils import get_ffprobe_binary
        cmd = [
            get_ffprobe_binary(), "-v", "error", "-select_streams", "v:0",
            "-show_entries", "stream=width,height", "-of", "json", file_path,
        ]
        res = subprocess.run(cmd, capture_output=True, text=True)
        if res.returncode != 0:
            return None, None
        streams = json.loads(res.stdout or "{}").get("streams", [])
        if not streams:
            return None, None
        width = int(streams[0].get("width") or 0)
        height = int(streams[0].get("height") or 0)
        if width <= 0 or height <= 0:
            return None, None
        return width, height
    except Exception:
        return None, None


def _final_download_path(ydl, info):
    requested_downloads = info.get("requested_downloads") or []
    for download in requested_downloads:
        file_path = download.get("filepath") or download.get("filename")
        if file_path and os.path.isfile(file_path):
            return os.path.abspath(file_path)

    prepared_path = ydl.prepare_filename(info)
    candidates = [prepared_path]
    if info.get("__files_to_move"):
        candidates.extend(info["__files_to_move"].values())
    if not prepared_path.lower().endswith(".mp4"):
        candidates.append(os.path.splitext(prepared_path)[0] + ".mp4")

    for file_path in candidates:
        if file_path and os.path.isfile(file_path):
            return os.path.abspath(file_path)
    return os.path.abspath(candidates[-1])

def _ensure_browser_compatible_audio(video_path: str, job_id=None):
    """Ensure MP4 audio stream is encoded in AAC with faststart for browser playback."""
    try:
        import subprocess
        from backend.utils import get_ffmpeg_binary, get_ffprobe_binary
        ffprobe_bin = get_ffprobe_binary()
        ffmpeg_bin = get_ffmpeg_binary()
        probe_cmd = [ffprobe_bin, "-v", "error", "-select_streams", "a:0", "-show_entries", "stream=codec_name", "-of", "csv=p=0", video_path]
        res = subprocess.run(probe_cmd, capture_output=True, text=True)
        codec = res.stdout.strip().lower()
        if codec and codec != "aac":
            log(f"Mengonversi audio ({codec} -> AAC) agar suara jernih di browser preview...", job_id=job_id)
            tmp_path = video_path + ".aac_fix.mp4"
            remux_cmd = [ffmpeg_bin, "-y", "-i", video_path, "-c:v", "copy", "-c:a", "aac", "-b:a", "192k", "-movflags", "+faststart", tmp_path]
            r2 = subprocess.run(remux_cmd, capture_output=True)
            if r2.returncode == 0 and os.path.exists(tmp_path) and os.path.getsize(tmp_path) > 0:
                os.replace(tmp_path, video_path)
                log("Audio remux AAC selesai dengan sukses.", job_id=job_id)
    except Exception as e:
        log(f"Info verifikasi audio: {e}", job_id=job_id)

def find_existing_downloaded_video(url: str, download_dir: str):
    """Cek apakah video YouTube ini sudah pernah diunduh dan tersimpan di folder downloads."""
    import re
    match = re.search(r'(?:v=|\/|live\/)([0-9A-Za-z_-]{11})', url)
    if not match:
        return None
    video_id = match.group(1)
    if not os.path.exists(download_dir):
        return None

    marker = f"[{video_id}]"
    for fname in os.listdir(download_dir):
        if fname.endswith(".mp4") and marker in fname and not fname.endswith(".part"):
            full_path = os.path.abspath(os.path.join(download_dir, fname))
            if os.path.isfile(full_path) and os.path.getsize(full_path) > 1024 * 1024:
                w, h = _probe_video_resolution(full_path)
                if h and h >= MIN_ACCEPTABLE_HEIGHT:
                    return full_path
    return None

def download_video_profesional(url: str, job_id=None) -> str:
    log(f"Memulai Download URL (Mode Profesional): {url}", job_id=job_id)
    
    download_dir = os.path.join(os.path.dirname(os.path.dirname(__file__)), "downloads")
    os.makedirs(download_dir, exist_ok=True)

    # Cek apakah file video sudah pernah diunduh secara komplit
    existing_file = find_existing_downloaded_video(url, download_dir)
    if existing_file:
        w, h = _probe_video_resolution(existing_file)
        log(f"[CACHE] Video sudah terunduh sebelumnya di folder downloads ({w}x{h}): {os.path.basename(existing_file)}. Menggunakan file lokal...", job_id=job_id)
        _ensure_browser_compatible_audio(existing_file, job_id=job_id)
        return existing_file
    
    import time
    last_update_time = [0.0]
    
    def ytdlp_progress_hook(d):
        if d['status'] == 'downloading':
            now = time.time()
            if now - last_update_time[0] >= 1.0:
                last_update_time[0] = now
                total = d.get('total_bytes') or d.get('total_bytes_estimate')
                downloaded = d.get('downloaded_bytes', 0)
                speed = d.get('speed')
                eta = d.get('eta')
                frag_idx = d.get('fragment_index')
                frag_cnt = d.get('fragment_count')
                
                percent = None
                if total and total > 0:
                    percent = (downloaded / total) * 100
                elif frag_cnt and frag_idx is not None and frag_cnt > 0:
                    percent = (frag_idx / frag_cnt) * 100
                elif d.get('_percent_str'):
                    try:
                        percent = float(d['_percent_str'].replace('%', '').strip())
                    except Exception:
                        percent = None

                speed_mb = (speed / 1024 / 1024) if speed else 0
                if not speed_mb and d.get('_speed_str'):
                    try:
                        raw_spd = d['_speed_str'].replace('iB/s', '').replace('B/s', '').strip()
                        if 'M' in d['_speed_str']:
                            speed_mb = float(raw_spd.replace('M', ''))
                        elif 'K' in d['_speed_str']:
                            speed_mb = float(raw_spd.replace('K', '')) / 1024
                    except Exception:
                        pass

                eta_str = d.get('_eta_str') or "--:--"
                if eta_str == "--:--" and eta is not None:
                    try:
                        eta_int = int(eta)
                        m, s = divmod(eta_int, 60)
                        h, m = divmod(m, 60)
                        eta_str = f"{h:02d}:{m:02d}:{s:02d}" if h > 0 else f"{m:02d}:{s:02d}"
                    except (ValueError, TypeError):
                        eta_str = "--:--"

                frag_info = f" [Frag {frag_idx}/{frag_cnt}]" if frag_cnt else ""
                pct_str = f"{percent:.1f}%" if percent is not None else "..."
                log(f"Progress Download: {pct_str}{frag_info} | Kecepatan: {speed_mb:.2f} MB/s | Sisa Waktu (ETA): {eta_str}", job_id=job_id)
        elif d['status'] == 'finished':
            log("Progress Download: 100.0% | Selesai mengunduh file video.", job_id=job_id)

    class MyLogger:
        def debug(self, msg):
            pass
        def info(self, msg):
            if not any(x in msg.lower() for x in ["downloading", "destination", "percent", "eta", "speed", "frag"]):
                log(f"[YT-DLP] {msg}", job_id=job_id)
        def warning(self, msg):
            pass
        def error(self, msg):
            log(f"[YT-DLP ERROR] {msg}", job_id=job_id)

    # Cari file cookies.txt (disimpan lewat Pengaturan Studio -> tab Cookies).
    cookie_file = resolve_cookie_file(download_dir)
    if cookie_file:
        log(f"[AUTH] Menggunakan file cookies: {cookie_file}", job_id=job_id)
    else:
        log(
            "[AUTH] cookies.txt tidak ditemukan. Buka Pengaturan Studio > Cookies "
            "untuk menempelkan cookies YouTube.",
            job_id=job_id,
        )

    # Ambil resolusi tertinggi yang tersedia (sampai VC_MAX_DOWNLOAD_HEIGHT, default 1080p).
    # Never silently accept a progressive 360p fallback.
    max_height = _max_download_height()
    format_selector = _build_format_selector(max_height)
    download_strategies = [
        {
            "name": "High-Res Stream (Web Embedded)",
            "format": format_selector,
            "extractor_args": {"youtube": {"player_client": ["web_embedded", "web"]}},
            "use_cookie": True
        },
        {
            "name": "High-Res Stream (Android VR)",
            "format": format_selector,
            "extractor_args": {"youtube": {"player_client": ["android_vr"]}},
            "use_cookie": True
        },
        {
            "name": "High-Res Stream (iOS / Web Client)",
            "format": format_selector,
            "extractor_args": {"youtube": {"player_client": ["ios", "web"]}},
            "use_cookie": True
        },
        {
            "name": "High-Res Stream (Default Client)",
            "format": format_selector,
            "extractor_args": {},
            "use_cookie": True
        },
        {
            "name": "High-Res Stream (Anonymous Fallback / Tanpa Cookie)",
            "format": format_selector,
            "extractor_args": {"youtube": {"player_client": ["web_embedded", "web"]}},
            "use_cookie": False
        }
    ]

    last_error = None
    # Round 1: semua metode wajib >=1080p. Round 2 (cadangan): terima >=720p dengan peringatan.
    for min_required_height in (PREFERRED_MIN_HEIGHT, MIN_ACCEPTABLE_HEIGHT):
        if min_required_height < PREFERRED_MIN_HEIGHT:
            log(
                f"Tidak ada metode yang menyediakan >= {PREFERRED_MIN_HEIGHT}p. "
                f"Mencoba ulang dengan batas minimum {min_required_height}p...",
                job_id=job_id
            )
        for strategy in download_strategies:
            try:
                log(f"Mencoba metode unduh: {strategy['name']} (min {min_required_height}p, maks {max_height}p)...", job_id=job_id)
                from backend.utils import get_ffmpeg_binary
                ffmpeg_bin = get_ffmpeg_binary()
                ydl_opts = {
                    'format': strategy['format'],
                    'merge_output_format': 'mp4',
                    'outtmpl': os.path.join(download_dir, '%(title)s [%(id)s].%(ext)s'),
                    'restrictfilenames': True,
                    'noplaylist': True,
                    'writethumbnail': False,
                    'continuedl': True,
                    'skip_unavailable_fragments': True,
                    'concurrent_fragment_downloads': 1,
                    'socket_timeout': 20,
                    'retries': 10,
                    'fragment_retries': 10,
                    'file_access_retries': 5,
                    'ffmpeg_location': ffmpeg_bin,
                    'extractor_args': strategy['extractor_args'],
                    'user_agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/132.0.0.0 Safari/537.36',
                    'http_headers': {
                        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/132.0.0.0 Safari/537.36',
                        'Accept-Language': 'en-US,en;q=0.9,id;q=0.8',
                        'Referer': 'https://www.youtube.com/',
                    },
                    'progress_hooks': [ytdlp_progress_hook],
                    'logger': MyLogger(),
                }
                if strategy.get("use_cookie") and cookie_file:
                    ydl_opts['cookiefile'] = cookie_file

                with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                    info = ydl.extract_info(url, download=True)
                    if not info:
                        raise RuntimeError("yt-dlp tidak mengembalikan informasi video.")

                    final_filename = _final_download_path(ydl, info)
                    width, height = _probe_video_resolution(final_filename)
                    if height is None or height < min_required_height:
                        try:
                            os.remove(final_filename)
                        except OSError:
                            pass
                        raise RuntimeError(
                            f"Validasi file gagal: hasil download {width or '?'}x{height or '?'}, "
                            f"di bawah minimum {min_required_height}p."
                        )

                    if height < PREFERRED_MIN_HEIGHT:
                        log(
                            f"⚠️ Sumber hanya {width}x{height}. Klip akan di-upscale dan bisa terlihat kurang tajam.",
                            job_id=job_id
                        )
                    log(
                        f"Download SUKSES! Resolusi terverifikasi {width}x{height}. "
                        f"File tersimpan sebagai: {final_filename}",
                        job_id=job_id
                    )
                    try:
                        uploader_name = info.get("uploader") or info.get("channel") or info.get("creator") or ""
                        with open(f"{final_filename}.meta.json", "w", encoding="utf-8") as mf:
                            json.dump({
                                "title": info.get("title", ""),
                                "uploader": uploader_name,
                                "channel": info.get("channel") or uploader_name,
                                "source_url": url,
                            }, mf, ensure_ascii=False)
                    except Exception:
                        pass
                    _ensure_browser_compatible_audio(final_filename, job_id=job_id)
                    return final_filename
            except Exception as e:
                last_error = e
                log(f"Metode '{strategy['name']}' gagal ({str(e)[:180]}). Beralih ke metode cadangan...", job_id=job_id)

    message = (
        f"Gagal mendapatkan stream video minimal {MIN_ACCEPTABLE_HEIGHT}p. Aplikasi tidak akan memakai fallback 360p. "
        "Perbarui cookies YouTube di Pengaturan Studio > Cookies, perbarui yt-dlp, "
        "atau pastikan video sumber memang menyediakan resolusi HD. "
        f"Error terakhir: {last_error}"
    )
    log(message, job_id=job_id)
    raise RuntimeError(message) from last_error

def get_video_file(file_path: str, job_id=None) -> str:
    if not file_path:
        log("Error: You must provide a file path or URL", job_id=job_id)
        raise ValueError("File path cannot be empty.")
        
    if file_path.startswith("http://") or file_path.startswith("https://"):
        return download_video_profesional(file_path, job_id=job_id)
        
    video_path = os.path.abspath(file_path)
    if not os.path.isfile(video_path):
        log(f"Error: Local file not found: {file_path}", job_id=job_id)
        raise FileNotFoundError(f"Local file not found: {file_path}")
    
    return video_path


def get_video_source_name(file_path_or_url: str) -> str:
    """Mengambil nama uploader/channel dari metadata video yang terdownload atau file sumber."""
    if not file_path_or_url:
        return ""
    meta_path = f"{file_path_or_url}.meta.json"
    if os.path.exists(meta_path):
        try:
            with open(meta_path, "r", encoding="utf-8") as mf:
                data = json.load(mf)
                name = data.get("uploader") or data.get("channel") or ""
                if name:
                    return str(name).strip()
        except Exception:
            pass
    return ""

