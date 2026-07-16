import os
import yt_dlp
from backend.utils import log

def download_video_profesional(url: str, job_id=None) -> str:
    log(f"Memulai Download URL (Mode Profesional): {url}", job_id=job_id)
    
    format_string = (
        'bestvideo[height<=1080][ext=mp4][vcodec^=avc]+bestaudio[ext=m4a]/'
        'bestvideo[height<=1080][ext=webm][vcodec^=vp9]+bestaudio/'
        'bestvideo[height<=1080][vcodec!^=av01]+bestaudio/'
        'best'
    )
    
    download_dir = os.path.join(os.path.dirname(os.path.dirname(__file__)), "downloads")
    os.makedirs(download_dir, exist_ok=True)
    
    ydl_opts = {
        'format': format_string,
        'merge_output_format': 'mp4',
        'outtmpl': os.path.join(download_dir, '%(title)s.%(ext)s'),
        'restrictfilenames': True,
        'noplaylist': True,
        'writethumbnail': False,
        'postprocessors': [],
        'user_agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/132.0.0.0 Safari/537.36',
        'http_headers': {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/132.0.0.0 Safari/537.36',
            'Accept-Language': 'en-US,en;q=0.9,id;q=0.8',
            'Referer': 'https://www.youtube.com/',
        },
    }
    
    class MyLogger:
        def debug(self, msg):
            if "Downloading" in msg or "Destination" in msg:
                log(f"[YT-DLP] {msg}", job_id=job_id)
        def info(self, msg):
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
