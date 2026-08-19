import os
import subprocess

# Trik untuk mencegah window cmd / terminal popup muncul berulang kali di Windows
# yang biasa dipanggil oleh package pihak ketiga (seperti stable-whisper/VAD/ffmpeg).
if os.name == 'nt':
    _original_popen = subprocess.Popen
    class NoWindowPopen(_original_popen):
        def __init__(self, *args, **kwargs):
            if 'creationflags' not in kwargs:
                kwargs['creationflags'] = 0x08000000 # CREATE_NO_WINDOW
            super().__init__(*args, **kwargs)
    subprocess.Popen = NoWindowPopen
from datetime import datetime
import glob
import sys
import tempfile

def load_env():
    script_dir = os.path.dirname(os.path.abspath(__file__))
    project_root = os.path.dirname(script_dir)
    
    candidates = [
        os.path.join(project_root, ".env"),
        os.path.join(os.getcwd(), ".env"),
    ]
    
    for env_path in candidates:
        if os.path.exists(env_path):
            with open(env_path, "r", encoding="utf-8") as f:
                for line in f:
                    line = line.strip()
                    if line and not line.startswith("#"):
                        parts = line.split("=", 1)
                        if len(parts) == 2:
                            os.environ[parts[0].strip()] = parts[1].strip()
            break

load_env()

DEFAULT_ENDPOINT = os.environ.get("ROUTER_API_ENDPOINT", "")
DEFAULT_API_KEY = os.environ.get("ROUTER_API_KEY", "")
DEFAULT_LLM_MODEL = os.environ.get("ROUTER_LLM_MODEL", "ag/gemini-3.5-flash-low")
GROQ_API_KEY = os.environ.get("GROQ_API_KEY", "")

PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
TEMP_DIR = os.path.join(PROJECT_ROOT, "temp")
os.makedirs(TEMP_DIR, exist_ok=True)
DEFAULT_OUT_DIR = os.path.join(PROJECT_ROOT, "clips")

for _pattern in ["tmp*.wav", "temp_crop_*.mp4", "temp_*.ass", "temp_sub*.vtt"]:
    for _f in glob.glob(os.path.join(TEMP_DIR, _pattern)):
        try:
            os.remove(_f)
        except Exception:
            pass

VERTICAL_WIDTH = 1080
VERTICAL_HEIGHT = 1920

def get_ffmpeg_binary():
    """Mengambil path binary FFmpeg terbaik yang mendukung filter subtitle & audio."""
    try:
        import imageio_ffmpeg
        exe = imageio_ffmpeg.get_ffmpeg_exe()
        if os.path.exists(exe):
            return exe
    except Exception:
        pass
    return "ffmpeg"

def log(message, job_id=None):
    timestamp = datetime.now().strftime("%H:%M:%S")
    msg = f"[{timestamp}] {message}"
    try:
        print(msg, flush=True)
    except UnicodeEncodeError:
        msg = msg.encode('ascii', 'replace').decode('ascii')
        print(msg, flush=True)
    
    # If job_id is provided, append to database logs
    if job_id is not None:
        from .database import append_job_log
        append_job_log(job_id, msg)

def run_command(cmd_list, description="", job_id=None, duration=None):
    if description:
        log(description, job_id=job_id)
    log("Running: " + " ".join(str(c) for c in cmd_list), job_id=job_id)
    
    kwargs = {}
    if os.name == 'nt':
        kwargs['creationflags'] = 0x08000000
        
    import subprocess
    process = subprocess.Popen(
        cmd_list,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        text=True,
        bufsize=1,
        **kwargs
    )
    
    output = []
    import time
    import re
    start_time = time.time()
    last_log_time = 0
    
    for line in process.stdout:
        line = line.strip()
        if not line: continue
        output.append(line)
        
        # Parse FFmpeg progress
        if line.startswith("frame=") or "time=" in line:
            time_match = re.search(r"time=(\d{2}):(\d{2}):(\d{2}\.\d{2})", line)
            if time_match:
                current_time = time.time()
                if current_time - last_log_time >= 1.0: # Log every 1s
                    h, m, s = float(time_match.group(1)), float(time_match.group(2)), float(time_match.group(3))
                    curr_sec = h * 3600 + m * 60 + s
                    if duration and duration > 0:
                        percent = min(100, (curr_sec / duration) * 100)
                        elapsed = current_time - start_time
                        if percent > 0:
                            eta = elapsed / (percent / 100) - elapsed
                            eta_str = format_timestamp(eta).split('.')[0]
                            log(f"Progress Rendering: {percent:.1f}% | Sisa Waktu (ETA): {eta_str}", job_id=job_id)
                    else:
                        log(f"Progress FFmpeg: {time_match.group(0)}", job_id=job_id)
                    last_log_time = current_time

    process.wait()
    if process.returncode != 0:
        full_out = "\n".join(output)
        log("Command failed with output:\n" + full_out, job_id=job_id)
        raise RuntimeError(f"Command failed: {' '.join(str(c) for c in cmd_list)}")
    else:
        if duration and duration > 0:
            log("Progress Rendering: 100.0% | Sisa Waktu (ETA): 00:00:00 | Rendering Selesai.", job_id=job_id)
    return "\n".join(output)

def format_timestamp(seconds):
    hrs = int(seconds // 3600)
    mins = int((seconds % 3600) // 60)
    secs = seconds % 60
    return f"{hrs:02d}:{mins:02d}:{secs:06.3f}"

def format_ass_timestamp(seconds):
    hrs = int(seconds // 3600)
    mins = int((seconds % 3600) // 60)
    secs = seconds % 60
    return f"{hrs}:{mins:02d}:{secs:05.2f}"

# Auto-add NVIDIA CUDA DLLs if installed via pip (for Windows)
if os.name == 'nt':
    os.environ["KMP_DUPLICATE_LIB_OK"] = "TRUE"
    import site
    for site_package in site.getsitepackages() + [site.getusersitepackages()]:
        torch_lib = os.path.join(site_package, "torch", "lib")
        if os.path.exists(torch_lib):
            os.environ["PATH"] = torch_lib + os.pathsep + os.environ.get("PATH", "")
            try:
                os.add_dll_directory(torch_lib)
            except AttributeError:
                pass

        for lib in ["cublas", "cudnn"]:
            lib_path = os.path.join(site_package, "nvidia", lib, "bin")
            if os.path.exists(lib_path):
                os.environ["PATH"] = lib_path + os.pathsep + os.environ.get("PATH", "")
                try:
                    os.add_dll_directory(lib_path)
                except AttributeError:
                    pass
