import json
import os
import subprocess

import yt_dlp

from backend.utils import log


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
    """Prioritas: >=1080p (sampai max_height) -> >=720p -> progressive >=720p. Tidak pernah 360p."""
    return (
        f"bestvideo[height>={PREFERRED_MIN_HEIGHT}][height<={max_height}]+bestaudio"
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

def download_video_profesional(url: str, job_id=None) -> str:
    log(f"Memulai Download URL (Mode Profesional): {url}", job_id=job_id)
    
    download_dir = os.path.join(os.path.dirname(os.path.dirname(__file__)), "downloads")
    os.makedirs(download_dir, exist_ok=True)
    
    import time
    last_update_time = [0.0]
    
    def ytdlp_progress_hook(d):
        if d['status'] == 'downloading':
            now = time.time()
            if now - last_update_time[0] >= 1.0:
                last_update_time[0] = now
                total = d.get('total_bytes') or d.get('total_bytes_estimate')
                downloaded = d.get('downloaded_bytes', 0)
                eta = d.get('eta')
                speed = d.get('speed')
                if total:
                    percent = (downloaded / total) * 100
                    speed_mb = (speed / 1024 / 1024) if speed else 0
                    if eta is not None:
                        try:
                            eta_int = int(eta)
                            m, s = divmod(eta_int, 60)
                            h, m = divmod(m, 60)
                            eta_str = f"{h:02d}:{m:02d}:{s:02d}" if h > 0 else f"{m:02d}:{s:02d}"
                        except (ValueError, TypeError):
                            eta_str = "--:--"
                    else:
                        eta_str = "--:--"
                    log(f"Progress Download: {percent:.1f}% | Kecepatan: {speed_mb:.2f} MB/s | Sisa Waktu (ETA): {eta_str}", job_id=job_id)
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

    # Cek apakah ada file cookies.txt di root project atau folder downloads
    project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    cookies_candidates = [
        os.path.join(project_root, "cookies.txt"),
        os.path.join(download_dir, "cookies.txt"),
        os.path.join(os.getcwd(), "cookies.txt")
    ]
    cookie_file = None
    for c_path in cookies_candidates:
        if os.path.exists(c_path) and os.path.getsize(c_path) > 0:
            cookie_file = c_path
            log(f"[AUTH] Menggunakan file cookies: {c_path}", job_id=job_id)
            break

    # Ambil resolusi tertinggi yang tersedia (sampai VC_MAX_DOWNLOAD_HEIGHT, default 1080p).
    # Never silently accept a progressive 360p fallback.
    max_height = _max_download_height()
    format_selector = _build_format_selector(max_height)
    download_strategies = [
        {
            "name": "High-Res Stream (Web Embedded)",
            "format": format_selector,
            "extractor_args": {"youtube": {"player_client": ["web_embedded"]}},
            "use_cookie": True
        },
        {
            "name": "High-Res Stream (Android VR)",
            "format": format_selector,
            "extractor_args": {"youtube": {"player_client": ["android_vr"]}},
            "use_cookie": True
        },
        {
            "name": "High-Res Stream (Default Client)",
            "format": format_selector,
            "extractor_args": {},
            "use_cookie": True
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
                ydl_opts = {
                    'format': strategy['format'],
                    'merge_output_format': 'mp4',
                    'outtmpl': os.path.join(download_dir, '%(title)s [%(id)s].%(ext)s'),
                    'restrictfilenames': True,
                    'noplaylist': True,
                    'writethumbnail': False,
                    'concurrent_fragment_downloads': 8,
                    'buffersize': 1024 * 1024 * 16,
                    'http_chunk_size': 10485760,
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
                    info = ydl.extract_info(url, download=False)
                    selected_height = _selected_video_height(info)
                    if selected_height is None or selected_height < min_required_height:
                        raise RuntimeError(
                            f"Metode hanya menyediakan {selected_height or 'resolusi tidak diketahui'}p, "
                            f"di bawah minimum {min_required_height}p."
                        )

                    selected_format = _selected_video_format(info) or {}
                    log(
                        f"Stream terpilih: format {selected_format.get('format_id', '?')} "
                        f"({selected_format.get('vcodec', '?')}) | "
                        f"{selected_format.get('width', '?')}x{selected_height}. Memulai download...",
                        job_id=job_id
                    )
                    info = ydl.extract_info(url, download=True)
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
        "Perbarui cookies.txt/yt-dlp atau pastikan video sumber memang menyediakan resolusi HD. "
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

