import os

import cv2
import yt_dlp

from backend.utils import log


TARGET_HEIGHT = 1080


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
    cap = cv2.VideoCapture(file_path)
    try:
        if not cap.isOpened():
            return None, None
        width = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH) or 0)
        height = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT) or 0)
        if width <= 0 or height <= 0:
            return None, None
        return width, height
    finally:
        cap.release()


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

    # Require an actual 1080p stream; never silently accept a progressive 360p fallback.
    download_strategies = [
        {
            "name": "Full HD 1080p Stream (Web Embedded)",
            "format": "bestvideo[height=1080]+bestaudio/best[height=1080]",
            "extractor_args": {"youtube": {"player_client": ["web_embedded"]}},
            "use_cookie": True
        },
        {
            "name": "Full HD 1080p Stream (Android VR)",
            "format": "bestvideo[height=1080]+bestaudio/best[height=1080]",
            "extractor_args": {"youtube": {"player_client": ["android_vr"]}},
            "use_cookie": True
        },
        {
            "name": "Full HD 1080p Stream (Default Client)",
            "format": "bestvideo[height=1080]+bestaudio/best[height=1080]",
            "extractor_args": {},
            "use_cookie": True
        }
    ]

    last_error = None
    for strategy in download_strategies:
        try:
            log(f"Mencoba metode unduh: {strategy['name']}...", job_id=job_id)
            ydl_opts = {
                'format': strategy['format'],
                'merge_output_format': 'mp4',
                'outtmpl': os.path.join(download_dir, '%(title)s.%(ext)s'),
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
                if selected_height != TARGET_HEIGHT:
                    raise RuntimeError(
                        f"Metode hanya menyediakan {selected_height or 'resolusi tidak diketahui'}p, bukan 1080p."
                    )

                selected_format = _selected_video_format(info) or {}
                log(
                    f"Stream terpilih: format {selected_format.get('format_id', '?')} | "
                    f"{selected_format.get('width', '?')}x{selected_height}. Memulai download...",
                    job_id=job_id
                )
                info = ydl.extract_info(url, download=True)
                final_filename = _final_download_path(ydl, info)

                width, height = _probe_video_resolution(final_filename)
                if height != TARGET_HEIGHT:
                    try:
                        os.remove(final_filename)
                    except OSError:
                        pass
                    raise RuntimeError(
                        f"Validasi file gagal: hasil download {width or '?'}x{height or '?'}, bukan 1920x1080."
                    )

                log(
                    f"Download SUKSES! Resolusi terverifikasi {width}x{height}. "
                    f"File tersimpan sebagai: {final_filename}",
                    job_id=job_id
                )
                return final_filename
        except Exception as e:
            last_error = e
            log(f"Metode '{strategy['name']}' gagal ({str(e)[:180]}). Beralih ke metode cadangan...", job_id=job_id)

    message = (
        "Gagal mendapatkan stream Full HD 1920x1080. Aplikasi tidak akan memakai fallback 360p. "
        "Perbarui cookies.txt/yt-dlp atau pastikan video sumber memang menyediakan 1080p. "
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
