import os
from backend.utils import log

def get_video_file(file_path: str, job_id=None) -> str:
    if not file_path:
        log("Error: You must provide a file path", job_id=job_id)
        raise ValueError("File path cannot be empty.")
        
    video_path = os.path.abspath(file_path)
    if not os.path.isfile(video_path):
        log(f"Error: Local file not found: {file_path}", job_id=job_id)
        raise FileNotFoundError(f"Local file not found: {file_path}")
    
    return video_path
