import os
import subprocess
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

PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
TEMP_DIR = os.path.join(PROJECT_ROOT, "temp")
os.makedirs(TEMP_DIR, exist_ok=True)
DEFAULT_OUT_DIR = os.path.join(PROJECT_ROOT, "clips")

for _pattern in ["tmp*.wav", "temp_crop_*.mov", "temp_*.ass"]:
    for _f in glob.glob(os.path.join(TEMP_DIR, _pattern)):
        try:
            os.remove(_f)
        except Exception:
            pass

VERTICAL_WIDTH = 1080
VERTICAL_HEIGHT = 1920

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

def run_command(cmd_list, description="", job_id=None):
    if description:
        log(description, job_id=job_id)
    log("Running: " + " ".join(str(c) for c in cmd_list), job_id=job_id)
    
    kwargs = {}
    if os.name == 'nt':
        kwargs['creationflags'] = 0x08000000
        
    result = subprocess.run(
        cmd_list,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        text=True,
        **kwargs
    )
    if result.returncode != 0:
        log("Command failed with output:\n" + result.stdout, job_id=job_id)
        raise RuntimeError(f"Command failed: {' '.join(str(c) for c in cmd_list)}")
    return result.stdout

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
