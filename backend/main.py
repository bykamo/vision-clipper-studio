import os
import subprocess
import sys
import json
import mimetypes
import re
import signal
import string
import ctypes
import queue
import secrets
import threading
import time as _time
import uuid
import asyncio
from urllib.parse import urlparse
from fastapi import FastAPI, Request
from fastapi.responses import HTMLResponse, StreamingResponse, JSONResponse, FileResponse, RedirectResponse
from fastapi.staticfiles import StaticFiles
from backend import youtube_uploader

app = FastAPI()

# Local CSRF / Host validation & Local Session Token
SESSION_TOKEN = secrets.token_hex(32)
ALLOWED_HOSTS = {
    "localhost", "127.0.0.1", "[::1]",
    "localhost:5050", "127.0.0.1:5050", "[::1]:5050",
    "testserver"
}

@app.middleware("http")
async def security_middleware(request: Request, call_next):
    # 1. Validate Host header to protect against DNS rebinding
    host_header = request.headers.get("host", "").strip().lower()
    if host_header and host_header not in ALLOWED_HOSTS:
        return JSONResponse(status_code=403, content={"error": "Forbidden: Invalid Host header"})

    # 2. Validate Origin/Referer on mutating actions to mitigate localhost CSRF
    if request.method in ("POST", "PUT", "DELETE", "PATCH"):
        origin = request.headers.get("origin")
        referer = request.headers.get("referer")
        
        # Check Origin if present
        if origin:
            try:
                parsed = urlparse(origin)
                netloc = parsed.netloc.lower()
                if netloc not in ALLOWED_HOSTS:
                    return JSONResponse(status_code=403, content={"error": "Forbidden: Invalid Origin header"})
            except Exception:
                return JSONResponse(status_code=403, content={"error": "Forbidden: Malformed Origin header"})
        elif referer:
            try:
                parsed = urlparse(referer)
                netloc = parsed.netloc.lower()
                if netloc not in ALLOWED_HOSTS:
                    return JSONResponse(status_code=403, content={"error": "Forbidden: Invalid Referer header"})
            except Exception:
                return JSONResponse(status_code=403, content={"error": "Forbidden: Malformed Referer header"})

    response = await call_next(request)
    return response

# Global synchronization and registry for worker processes
_WORKER_LOCK = threading.Lock()
# Structure: {"job_id": str, "process": Optional[subprocess.Popen]}
_ACTIVE_JOB = None

PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
FRONTEND_DIR = os.path.join(PROJECT_ROOT, "frontend")
DIST_DIR = os.path.join(FRONTEND_DIR, "dist")
SERVE_DIR = DIST_DIR if os.path.exists(DIST_DIR) else FRONTEND_DIR


def _stop_process(process):
    """Stop worker and every child renderer process in its process group."""
    if not process or process.poll() is not None:
        return
    try:
        if os.name == 'nt':
            subprocess.run(['taskkill', '/F', '/T', '/PID', str(process.pid)], capture_output=True)
        else:
            try:
                pgid = os.getpgid(process.pid)
                os.killpg(pgid, signal.SIGTERM)
                _time.sleep(0.2)
                if process.poll() is None:
                    os.killpg(pgid, signal.SIGKILL)
            except Exception:
                process.kill()
    except Exception:
        try:
            process.kill()
        except Exception:
            pass
    try:
        process.wait(timeout=1.0)
    except Exception:
        pass


def _worker_is_active():
    with _WORKER_LOCK:
        global _ACTIVE_JOB
        if _ACTIVE_JOB is None:
            return False
        process = _ACTIVE_JOB.get("process")
        if process is None:
            return True  # Slot reserved, process launching
        if process.poll() is None:
            return True
        _ACTIVE_JOB = None
        return False


def _reserve_worker_slot() -> str:
    """Synchronously reserve worker slot before creating HTTP response."""
    with _WORKER_LOCK:
        global _ACTIVE_JOB
        if _ACTIVE_JOB is not None:
            process = _ACTIVE_JOB.get("process")
            if process is None or process.poll() is None:
                raise RuntimeError("A worker is already processing a request")
        job_id = str(uuid.uuid4())
        _ACTIVE_JOB = {"job_id": job_id, "process": None}
        return job_id


def _release_worker_slot(job_id: str, process=None):
    with _WORKER_LOCK:
        global _ACTIVE_JOB
        if _ACTIVE_JOB and _ACTIVE_JOB.get("job_id") == job_id:
            proc = process or _ACTIVE_JOB.get("process")
            if proc:
                _stop_process(proc)
            _ACTIVE_JOB = None

ALLOWED_VIDEO_EXTENSIONS = {".mp4", ".mov", ".mkv", ".avi", ".webm", ".m4v"}

def _is_path_safe_and_allowed(target_path: str, must_exist: bool = True) -> bool:
    """Validate that target_path does not access sensitive system folders."""
    try:
        real_target = os.path.realpath(os.path.abspath(target_path))
        if must_exist and not os.path.exists(real_target):
            return False

        # Disallow sensitive directories across OS
        forbidden_prefixes = [
            "/etc", "/proc", "/sys", "/dev", "/var/run", "/var/log",
            "C:\\Windows", "C:\\Program Files", "C:\\Program Files (x86)"
        ]
        # Sensitive home folders (.ssh, .gnupg, .config, credentials)
        user_home = os.path.realpath(os.path.expanduser("~"))
        sensitive_home_dirs = [
            os.path.join(user_home, ".ssh"),
            os.path.join(user_home, ".gnupg"),
            os.path.join(user_home, ".aws"),
            os.path.join(user_home, ".config", "gcloud"),
        ]

        for p in forbidden_prefixes:
            if real_target.lower().startswith(os.path.realpath(p).lower()):
                return False

        for s in sensitive_home_dirs:
            if real_target.lower().startswith(s.lower()):
                return False

        return True
    except Exception:
        return False

@app.api_route("/api/video-stream", methods=["GET", "HEAD"])
async def video_stream(path: str = ""):
    """Stream video file for HTML5 Video Preview."""
    if not path:
        return JSONResponse(status_code=400, content={"error": "Path parameter is empty"})

    if not os.path.isabs(path):
        candidate = os.path.join(PROJECT_ROOT, path)
        if os.path.exists(candidate):
            path = candidate
        else:
            path = os.path.abspath(path)
    else:
        path = os.path.normpath(path)

    real_path = os.path.realpath(path)
    if not os.path.exists(real_path) or not os.path.isfile(real_path):
        return JSONResponse(status_code=404, content={"error": f"Video file not found: {path}"})

    ext = os.path.splitext(real_path)[1].lower()
    if ext not in ALLOWED_VIDEO_EXTENSIONS:
        return JSONResponse(status_code=403, content={"error": "File type not allowed for video streaming"})

    if not _is_path_safe_and_allowed(real_path, must_exist=True):
        return JSONResponse(status_code=403, content={"error": "Access to path is forbidden"})

    media_type, _ = mimetypes.guess_type(real_path)
    return FileResponse(real_path, media_type=media_type or "application/octet-stream")

FALLBACK_HTML = """<!DOCTYPE html>
<html lang="id">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>VisionClipper Studio — Frontend Build Diperlukan</title>
    <style>
        body { font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif; background: #0f172a; color: #f8fafc; display: flex; justify-content: center; align-items: center; min-height: 100vh; margin: 0; padding: 20px; }
        .card { max-width: 600px; background: #1e293b; border: 1px solid #334155; border-radius: 12px; padding: 32px; box-shadow: 0 10px 25px rgba(0,0,0,0.5); }
        h1 { color: #f59e0b; margin-top: 0; font-size: 24px; }
        p { line-height: 1.6; color: #cbd5e1; }
        code { background: #0f172a; padding: 3px 8px; border-radius: 6px; font-family: monospace; color: #38bdf8; border: 1px solid #1e293b; }
        pre { background: #0f172a; padding: 14px; border-radius: 8px; overflow-x: auto; color: #38bdf8; border: 1px solid #334155; }
    </style>
</head>
<body>
    <div class="card">
        <h1>⚠️ Frontend Belum Dibuild</h1>
        <p>Aplikasi VisionClipper Studio berjalan, namun berkas produksi dashboard (<code>frontend/dist</code>) belum tersedia.</p>
        <p>Silakan build frontend dengan menjalankan perintah berikut di terminal:</p>
        <pre>cd frontend
npm ci && npm run build</pre>
        <p>Setelah build selesai, muat ulang (refresh) halaman ini untuk membuka Dashboard VisionClipper Studio.</p>
    </div>
</body>
</html>
"""

@app.get("/", response_class=HTMLResponse)
async def index():
    index_path = os.path.join(SERVE_DIR, "index.html")
    if not os.path.exists(index_path):
        # Do not serve raw unbundled TSX/HTML
        return HTMLResponse(content=FALLBACK_HTML, status_code=200)
    with open(index_path, "r", encoding="utf-8") as f:
        html_content = f.read()
    response = HTMLResponse(content=html_content)
    response.set_cookie(key="vc_session_token", value=SESSION_TOKEN, httponly=False, samesite="strict")
    return response

@app.get("/api/list-dir")
async def list_dir_api(path: str = ""):
    drives = []
    if os.name == 'nt':
        try:
            bitmask = ctypes.windll.kernel32.GetLogicalDrives()
            for letter in string.ascii_uppercase:
                if bitmask & 1:
                    drives.append(f"{letter}:\\")
                bitmask >>= 1
        except Exception:
            drives = ["C:\\"]
    else:
        drives = ['/']

    if not path:
        path = os.path.expanduser("~")
    else:
        path = os.path.abspath(path)

    path = os.path.normpath(path)
    real_path = os.path.realpath(path)

    if not os.path.exists(real_path) or not _is_path_safe_and_allowed(real_path, must_exist=True):
        real_path = os.path.realpath(os.path.expanduser("~"))
        path = real_path

    try:
        entries = os.scandir(path)
        folders = []
        files = []
        for entry in entries:
            try:
                if entry.name.startswith('.'):
                    continue
                if entry.is_dir(follow_symlinks=False):
                    folders.append({
                        "name": entry.name,
                        "path": os.path.normpath(entry.path)
                    })
                elif entry.is_file(follow_symlinks=False):
                    ext = os.path.splitext(entry.name)[1].lower()
                    if ext in ['.mp4', '.mov', '.mkv', '.avi', '.webm', '.m4v']:
                        try:
                            size_bytes = entry.stat().st_size
                            if size_bytes < 1024:
                                size_str = f"{size_bytes} B"
                            elif size_bytes < 1024 * 1024:
                                size_str = f"{size_bytes / 1024:.1f} KB"
                            elif size_bytes < 1024 * 1024 * 1024:
                                size_str = f"{size_bytes / (1024 * 1024):.1f} MB"
                            else:
                                size_str = f"{size_bytes / (1024 * 1024 * 1024):.1f} GB"
                        except Exception:
                            size_str = "Unknown size"

                        files.append({
                            "name": entry.name,
                            "path": os.path.normpath(entry.path),
                            "size": size_str
                        })
            except Exception:
                pass

        folders.sort(key=lambda x: x['name'].lower())
        files.sort(key=lambda x: x['name'].lower())

        parent_path = os.path.dirname(path)
        if parent_path == path:
            parent_path = ""
        else:
            parent_path = os.path.normpath(parent_path)

        return {
            "current_path": path,
            "parent_path": parent_path,
            "drives": drives,
            "folders": folders,
            "files": files
        }
    except Exception as e:
        parent_path = os.path.dirname(path)
        if parent_path == path:
            parent_path = ""
        else:
            parent_path = os.path.normpath(parent_path)
        return {
            "error": str(e),
            "current_path": path,
            "parent_path": parent_path,
            "drives": drives,
            "folders": [],
            "files": []
        }

@app.post("/api/open-folder")
async def open_folder(request: Request):
    try:
        data = await request.json()
    except Exception:
        return JSONResponse(status_code=400, content={"error": "Invalid JSON body"})

    path = data.get("path")
    if not path:
        return JSONResponse(status_code=400, content={"error": "Path parameter is empty"})

    path = os.path.normpath(path)
    real_path = os.path.realpath(path)

    if not _is_path_safe_and_allowed(real_path, must_exist=True):
        return JSONResponse(status_code=403, content={"error": "Access to path is forbidden"})

    if os.path.exists(real_path):
        try:
            if os.name == 'nt':
                os.startfile(real_path)
            elif sys.platform == 'darwin':
                subprocess.Popen(['open', real_path])
            else:
                subprocess.Popen(['xdg-open', real_path])
            return {"status": "opened"}
        except Exception as e:
            return JSONResponse(status_code=500, content={"error": str(e)})
    return JSONResponse(status_code=404, content={"error": f"Folder tidak ditemukan: {path}"})


def _run_native_picker() -> str:
    """Synchronous file picker logic called inside asyncio.to_thread."""
    selected_path = ""
    try:
        if sys.platform == 'darwin':
            # AppleScript native file picker
            script = 'POSIX path of (choose file with prompt "Pilih File Video" of type {"public.movie", "mp4", "mkv", "mov", "webm", "avi", "m4v"})'
            res = subprocess.run(['osascript', '-e', script], capture_output=True, text=True)
            if res.returncode == 0:
                selected_path = res.stdout.strip()
        elif os.name == 'nt':
            # PowerShell OpenFileDialog
            ps_script = (
                'Add-Type -AssemblyName System.Windows.Forms;'
                '$f = New-Object System.Windows.Forms.OpenFileDialog;'
                '$f.Filter = "Video Files (*.mp4;*.mkv;*.mov;*.webm;*.avi)|*.mp4;*.mkv;*.mov;*.webm;*.avi|All Files (*.*)|*.*";'
                '$f.Title = "Pilih File Video";'
                'if ($f.ShowDialog() -eq [System.Windows.Forms.DialogResult]::OK) { Write-Output $f.FileName }'
            )
            res = subprocess.run(['powershell', '-NoProfile', '-Command', ps_script], capture_output=True, text=True)
            if res.returncode == 0:
                selected_path = res.stdout.strip()
        else:
            # Linux zenity fallback
            res = subprocess.run(['zenity', '--file-selection', '--title=Pilih File Video', '--file-filter=Video Files | *.mp4 *.mkv *.mov *.webm *.avi'], capture_output=True, text=True)
            if res.returncode == 0:
                selected_path = res.stdout.strip()
    except Exception:
        pass
    return selected_path


@app.post("/api/pick-file")
async def pick_file():
    """Trigger native OS file chooser dialog in threadpool and return chosen file path."""
    try:
        selected_path = await asyncio.to_thread(_run_native_picker)
    except Exception as e:
        return JSONResponse(status_code=500, content={"error": str(e)})

    return {"path": selected_path}

@app.post("/cancel")
async def cancel():
    with _WORKER_LOCK:
        global _ACTIVE_JOB
        if _ACTIVE_JOB and _ACTIVE_JOB.get("process"):
            proc = _ACTIVE_JOB.get("process")
            if proc.poll() is None:
                _stop_process(proc)
            _ACTIVE_JOB = None
            return {"status": "cancelled"}
        elif _ACTIVE_JOB:
            _ACTIVE_JOB = None
            return {"status": "cancelled"}
    return {"status": "no_process"}

@app.post("/shutdown")
async def shutdown():
    with _WORKER_LOCK:
        global _ACTIVE_JOB
        if _ACTIVE_JOB and _ACTIVE_JOB.get("process"):
            _stop_process(_ACTIVE_JOB.get("process"))
            _ACTIVE_JOB = None
    pid_file = os.path.join(os.path.expanduser("~"), ".visionclipper.pid")
    try:
        os.remove(pid_file)
    except OSError:
        pass
    os._exit(0)
    return {"status": "shutting_down"}


# ── Helper: Async SSE generator from subprocess with disconnect detection ──
async def _sse_from_process(cmd, job_id: str, request: Request = None):
    """Shared async SSE generator: spawn subprocess, stream stdout line-by-line, detect client disconnect."""
    process = None
    try:
        kwargs = {}
        if os.name == 'nt':
            kwargs['creationflags'] = 0x08000200  # CREATE_NO_WINDOW | CREATE_NEW_PROCESS_GROUP
        else:
            kwargs['start_new_session'] = True

        process = subprocess.Popen(
            cmd,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            bufsize=0,
            cwd=os.path.dirname(FRONTEND_DIR),
            **kwargs
        )
        with _WORKER_LOCK:
            global _ACTIVE_JOB
            if _ACTIVE_JOB and _ACTIVE_JOB.get("job_id") == job_id:
                _ACTIVE_JOB["process"] = process

        q = queue.Queue()

        def read_output():
            buffer = ""
            while True:
                try:
                    byte = process.stdout.read(1)
                    if not byte:
                        break
                    char = byte.decode('utf-8', errors='replace')
                    if char == '\r' or char == '\n':
                        if buffer:
                            q.put(buffer)
                            buffer = ""
                    else:
                        buffer += char
                except Exception:
                    break
            if buffer:
                q.put(buffer)
            q.put(None)

        t = threading.Thread(target=read_output, daemon=True)
        t.start()

        while True:
            # Check client disconnect periodically
            if request and await request.is_disconnected():
                _stop_process(process)
                break

            try:
                line = q.get_nowait()
                if line is None:
                    break
                if line:
                    yield f"data: {line}\n\n".encode("utf-8")
            except queue.Empty:
                await asyncio.sleep(0.1)

        return_code = process.wait() if process else 1
        if return_code == 0:
            yield b"data: [PROCESS_COMPLETE]\n\n"
        else:
            yield b"data: [PROCESS_FAILED]\n\n"

    except Exception as e:
        yield f"data: Error: {str(e)}\n\n".encode("utf-8")
    finally:
        if process and process.stdout:
            try:
                process.stdout.close()
            except Exception:
                pass
        _release_worker_slot(job_id, process)


def _valid_analysis_id(value):
    return isinstance(value, str) and re.fullmatch(r"analysis_\d+", value) is not None


# ── Temp analysis dir (reuse project temp/) ──
TEMP_ANALYSIS_DIR = os.path.join(os.path.dirname(FRONTEND_DIR), "temp")
os.makedirs(TEMP_ANALYSIS_DIR, exist_ok=True)

# Cleanup old analysis files (>24h) on startup
for _f in os.listdir(TEMP_ANALYSIS_DIR):
    if _f.startswith("analysis_") and _f.endswith(".json"):
        _fpath = os.path.join(TEMP_ANALYSIS_DIR, _f)
        try:
            if _time.time() - os.path.getmtime(_fpath) > 86400:
                os.remove(_fpath)
        except Exception:
            pass


@app.get("/api/analyze")
async def analyze(request: Request, mode: str = "", source: str = "", num_clips: str = "5", whisper_model: str = "groq"):
    """Phase 1: Transcribe + LLM analysis only. Returns SSE stream with [ANALYSIS_RESULT] JSON."""
    if _worker_is_active():
        return JSONResponse(status_code=409, content={"error": "A worker is already processing a request"})
    if not source.strip():
        return JSONResponse(status_code=400, content={"error": "Source parameter is empty"})
    if mode and mode not in {"hook", "affiliate"}:
        return JSONResponse(status_code=400, content={"error": "Invalid mode"})
    if whisper_model not in {"groq", "youtube"}:
        return JSONResponse(status_code=400, content={"error": "Invalid transcription model"})
    try:
        clip_count = int(num_clips)
    except ValueError:
        return JSONResponse(status_code=400, content={"error": "num_clips must be an integer"})
    if not 1 <= clip_count <= 10:
        return JSONResponse(status_code=400, content={"error": "num_clips must be between 1 and 10"})

    try:
        job_id = _reserve_worker_slot()
    except RuntimeError:
        return JSONResponse(status_code=409, content={"error": "A worker is already processing a request"})

    analysis_id = f"analysis_{int(_time.time() * 1000)}"

    cmd = [
        sys.executable, "-u", "-m", "backend.worker",
        "--file", source,
        "--num-clips", str(clip_count),
        "--mode", mode or "hook",
        "--model", whisper_model,
        "--analyze-only"
    ]

    async def generate():
        save_failed = False
        async for chunk in _sse_from_process(cmd, job_id=job_id, request=request):
            decoded = chunk.decode("utf-8", errors="replace")
            # Intercept analysis result: save to temp file
            if "data: [ANALYSIS_RESULT]" in decoded:
                try:
                    json_str = decoded.split("[ANALYSIS_RESULT]", 1)[1].strip()
                    # Remove SSE trailing newlines
                    json_str = json_str.rstrip("\n")
                    analysis_data = json.loads(json_str)
                    analysis_data["analysis_id"] = analysis_id
                    save_path = os.path.join(TEMP_ANALYSIS_DIR, f"{analysis_id}.json")
                    with open(save_path, "w", encoding="utf-8") as f:
                        json.dump(analysis_data, f, ensure_ascii=False)
                    # Browser only needs candidate data. Keep transcript words server-side.
                    public_data = {key: value for key, value in analysis_data.items() if key != "segments"}
                    yield f"data: [ANALYSIS_RESULT]{json.dumps(public_data, ensure_ascii=False)}\n\n".encode("utf-8")
                except Exception as e:
                    save_failed = True
                    yield f"data: Error saving analysis: {str(e)}\n\n".encode("utf-8")
            elif save_failed and b"[PROCESS_COMPLETE]" in chunk:
                yield b"data: [PROCESS_FAILED]\n\n"
            else:
                yield chunk

    return StreamingResponse(generate(), media_type="text/event-stream")


@app.post("/api/render-selected")
async def render_selected(request: Request):
    """Phase 2: Render only user-approved clips. Returns SSE stream."""
    if _worker_is_active():
        return JSONResponse(status_code=409, content={"error": "A worker is already processing a request"})
    try:
        data = await request.json()
    except Exception:
        return JSONResponse(status_code=400, content={"error": "Invalid JSON body"})

    analysis_id = data.get("analysis_id", "")
    clip_indices = data.get("clip_indices", [])
    sub_style = data.get("sub_style", "tiktok_viral")
    framing_mode = data.get("framing_mode", "smart_crop")

    if not _valid_analysis_id(analysis_id) or not isinstance(clip_indices, list) or not clip_indices:
        return JSONResponse(status_code=400, content={"error": "Missing analysis_id or clip_indices"})
    if sub_style not in {"tiktok_viral", "classic_karaoke", "minimalist", "word_pop", "no_subtitle", "none"}:
        return JSONResponse(status_code=400, content={"error": "Invalid subtitle style"})
    if framing_mode not in {"smart_crop", "fit_blur"}:
        return JSONResponse(status_code=400, content={"error": "Invalid framing mode"})

    analysis_path = os.path.join(TEMP_ANALYSIS_DIR, f"{analysis_id}.json")
    if not os.path.exists(analysis_path):
        return JSONResponse(status_code=404, content={"error": f"Analysis file not found: {analysis_id}"})

    # Read analysis to get video_path for --file arg
    with open(analysis_path, "r", encoding="utf-8") as f:
        analysis_data = json.load(f)

    video_path = analysis_data.get("video_path", "")
    clips = analysis_data.get("clips", [])
    try:
        indices = [int(index) for index in clip_indices]
    except (TypeError, ValueError):
        return JSONResponse(status_code=400, content={"error": "clip_indices must contain integers"})
    if not video_path or not isinstance(clips, list):
        return JSONResponse(status_code=500, content={"error": "Analysis data is invalid"})
    if len(set(indices)) != len(indices) or any(index < 1 or index > len(clips) for index in indices):
        return JSONResponse(status_code=400, content={"error": "clip_indices are out of range"})
    indices_str = ",".join(str(index) for index in indices)

    try:
        job_id = _reserve_worker_slot()
    except RuntimeError:
        return JSONResponse(status_code=409, content={"error": "A worker is already processing a request"})

    cmd = [
        sys.executable, "-u", "-m", "backend.worker",
        "--file", video_path,
        "--clips-json", analysis_path,
        "--render-indices", indices_str,
        "--sub-style", sub_style,
        "--framing-mode", framing_mode
    ]

    return StreamingResponse(_sse_from_process(cmd, job_id=job_id, request=request), media_type="text/event-stream")


@app.get("/stream")
async def stream(request: Request, mode: str = "", source_type: str = "", source: str = "", num_clips: str = "5", sub_style: str = "tiktok_viral", whisper_model: str = "groq", framing_mode: str = "smart_crop"):
    """Legacy streaming endpoint protected with synchronized worker slot."""
    if _worker_is_active():
        return JSONResponse(status_code=409, content={"error": "A worker is already processing a request"})
    if not source.strip():
        return JSONResponse(status_code=400, content={"error": "Source parameter is empty"})

    try:
        job_id = _reserve_worker_slot()
    except RuntimeError:
        return JSONResponse(status_code=409, content={"error": "A worker is already processing a request"})

    cmd = [
        sys.executable, "-u", "-m", "backend.worker",
        "--file", source,
        "--num-clips", str(num_clips),
        "--mode", mode,
        "--sub-style", sub_style,
        "--model", whisper_model,
        "--framing-mode", framing_mode
    ]

    return StreamingResponse(_sse_from_process(cmd, job_id=job_id, request=request), media_type="text/event-stream")


# ── YouTube Social Media Endpoints ──
@app.get("/api/social/youtube/auth-url")
async def youtube_auth_url():
    """Generate Google OAuth URL for YouTube uploading permissions."""
    try:
        url, _ = youtube_uploader.get_auth_url()
        return {"url": url}
    except Exception as e:
        return JSONResponse(status_code=500, content={"error": str(e)})


@app.get("/api/social/youtube/callback")
async def youtube_callback(code: str = "", state: str = "", error: str = ""):
    """Handle OAuth redirect callback from Google with state validation."""
    if error:
        return RedirectResponse(url=f"/?youtube_auth=error&msg={error}")
    if not code:
        return RedirectResponse(url="/?youtube_auth=error&msg=missing_code")
    if not state:
        return RedirectResponse(url="/?youtube_auth=failed&msg=Missing+OAuth+state")
    try:
        youtube_uploader.save_credentials_from_code(code, state=state)
        return RedirectResponse(url="/?youtube_auth=success")
    except Exception as e:
        return RedirectResponse(url=f"/?youtube_auth=failed&msg={str(e)}")


@app.get("/api/social/youtube/status")
async def youtube_status():
    """Get connected channel info if logged in."""
    info = youtube_uploader.get_channel_info()
    return {
        "connected": info is not None,
        "channel": info
    }


@app.post("/api/social/youtube/disconnect")
async def youtube_disconnect():
    """Disconnect and clear saved YouTube credentials."""
    success = youtube_uploader.disconnect_youtube()
    return {"status": "disconnected" if success else "failed"}


@app.post("/api/social/youtube/upload")
async def youtube_upload(request: Request):
    """Upload rendered video clip to YouTube channel in threadpool."""
    try:
        data = await request.json()
    except Exception:
        return JSONResponse(status_code=400, content={"error": "Invalid JSON body"})

    video_path = data.get("video_path", "")
    title = data.get("title", "VisionClipper Clip")
    description = data.get("description", "")
    tags = data.get("tags", [])
    privacy = data.get("privacy", "private")

    if not video_path:
        return JSONResponse(status_code=400, content={"error": "Parameter video_path is required"})

    try:
        result = await asyncio.to_thread(
            youtube_uploader.upload_video_to_youtube,
            video_path=video_path,
            title=title,
            description=description,
            tags=tags,
            privacy_status=privacy
        )
        return {"status": "success", **result}
    except Exception as e:
        return JSONResponse(status_code=500, content={"error": str(e)})


# Serve static files from frontend directory (production dist or root)
app.mount("/", StaticFiles(directory=SERVE_DIR), name="static")

if __name__ == '__main__':
    import uvicorn
    uvicorn.run("backend.main:app", host="127.0.0.1", port=5050, reload=False)
