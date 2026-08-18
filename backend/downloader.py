import os
import yt_dlp
from backend.utils import log

def download_video_profesional(url: str, job_id=None) -> str:
    log(f"Memulai Download URL (Mode Profesional): {url}", job_id=job_id)
    
    format_string = (
        'bestvideo[height<=1080]+bestaudio/best[height<=1080]/best'
    )
    
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
                        m, s = divmod(eta, 60)
                        h, m = divmod(m, 60)
                        eta_str = f"{h:02d}:{m:02d}:{s:02d}" if h > 0 else f"{m:02d}:{s:02d}"
                    else:
                        eta_str = "--:--"
                    log(f"Progress Download: {percent:.1f}% | Kecepatan: {speed_mb:.2f} MB/s | Sisa Waktu (ETA): {eta_str}", job_id=job_id)
        elif d['status'] == 'finished':
            log("Progress Download: 100.0% | Selesai mengunduh file video.", job_id=job_id)

    ydl_opts = {
        'format': format_string,
        'merge_output_format': 'mp4',
        'outtmpl': os.path.join(download_dir, '%(title)s.%(ext)s'),
        'restrictfilenames': True,
        'noplaylist': True,
        'writethumbnail': False,
        'postprocessors': [{
            'key': 'FFmpegVideoConvertor',
            'preferedformat': 'mp4',
        }],
        'extractor_args': {
            'youtube': {
                'player_client': ['android_vr', 'web']
            }
        },
        'user_agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/132.0.0.0 Safari/537.36',
        'http_headers': {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/132.0.0.0 Safari/537.36',
            'Accept-Language': 'en-US,en;q=0.9,id;q=0.8',
            'Referer': 'https://www.youtube.com/',
        },
        'progress_hooks': [ytdlp_progress_hook],
    }
    
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
            
    ydl_opts['logger'] = MyLogger()
    
    try:
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            log("Mengekstrak informasi video...", job_id=job_id)
            info = ydl.extract_info(url, download=True)
            final_filename = ydl.prepare_filename(info)
            if not final_filename.endswith('.mp4'):
                base, _ = os.path.splitext(final_filename)
                final_filename = base + '.mp4'
            
        log(f"Download SUKSES! File tersimpan sebagai: {final_filename}", job_id=job_id)
        return final_filename
    except Exception as e:
        log(f"Gagal mendownload video: {str(e)}", job_id=job_id)
        raise e

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
