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
import threading
import time as _time
from fastapi import FastAPI, Request
from fastapi.responses import HTMLResponse, StreamingResponse, JSONResponse, FileResponse
from fastapi.staticfiles import StaticFiles

app = FastAPI()

# Global to keep track of running process for cancellation
current_process = None

FRONTEND_DIR = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "frontend")
DIST_DIR = os.path.join(FRONTEND_DIR, "dist")
SERVE_DIR = DIST_DIR if os.path.exists(DIST_DIR) else FRONTEND_DIR


def _stop_process(process):
    """Stop worker and every child renderer process."""
    if not process or process.poll() is not None:
        return
    try:
        if os.name == 'nt':
            subprocess.run(['taskkill', '/F', '/T', '/PID', str(process.pid)], capture_output=True)
        else:
            os.killpg(os.getpgid(process.pid), signal.SIGKILL)
    except Exception:
        process.kill()


def _worker_is_active():
    return current_process is not None and current_process.poll() is None

@app.get("/api/video-stream")
async def video_stream(path: str = ""):
    """Stream video file for HTML5 Video Preview."""
    if not path:
        return JSONResponse(status_code=400, content={"error": "Path parameter is empty"})

    path = os.path.normpath(path)
    if not os.path.exists(path) or not os.path.isfile(path):
        return JSONResponse(status_code=404, content={"error": f"Video file not found: {path}"})

    media_type, _ = mimetypes.guess_type(path)
    return FileResponse(path, media_type=media_type or "application/octet-stream")

@app.get("/", response_class=HTMLResponse)
async def index():
    index_path = os.path.join(SERVE_DIR, "index.html")
    if not os.path.exists(index_path):
        index_path = os.path.join(FRONTEND_DIR, "index.html")
    with open(index_path, "r", encoding="utf-8") as f:
        return f.read()

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
    if not os.path.exists(path):
        path = os.path.expanduser("~")
        path = os.path.normpath(path)

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
    if os.path.exists(path):
        try:
            if os.name == 'nt':
                os.startfile(path)
            elif sys.platform == 'darwin':
                subprocess.Popen(['open', path])
            else:
                subprocess.Popen(['xdg-open', path])
            return {"status": "opened"}
        except Exception as e:
            return JSONResponse(status_code=500, content={"error": str(e)})
    return JSONResponse(status_code=404, content={"error": f"Folder tidak ditemukan: {path}"})


@app.get("/api/pick-file")
async def pick_file():
    """Trigger native OS file chooser dialog (Windows / macOS / Linux) and return chosen file path."""
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
    except Exception as e:
        return JSONResponse(status_code=500, content={"error": str(e)})

    return {"path": selected_path}

@app.post("/cancel")
async def cancel():
    global current_process
    if current_process and current_process.poll() is None:
        _stop_process(current_process)
        current_process = None
        return {"status": "cancelled"}
    return {"status": "no_process"}

@app.post("/shutdown")
async def shutdown():
    global current_process
    if current_process and current_process.poll() is None:
        _stop_process(current_process)
    pid_file = os.path.join(os.path.expanduser("~"), ".visionclipper.pid")
    try:
        os.remove(pid_file)
    except OSError:
        pass
    os._exit(0)
    return {"status": "shutting_down"}


# ── Helper: SSE generator from subprocess ──
def _sse_from_process(cmd):
    """Shared SSE generator: spawn subprocess, stream stdout line-by-line."""
    global current_process
    process = None
    try:
        kwargs = {}
        if os.name == 'nt':
            kwargs['creationflags'] = 0x08000000
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
        current_process = process

        q = queue.Queue()

        def read_output():
            buffer = ""
            while True:
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
            if buffer:
                q.put(buffer)
            q.put(None)

        t = threading.Thread(target=read_output)
        t.daemon = True
        t.start()
        while True:
            try:
                line = q.get(timeout=10)
                if line is None:
                    break
                if line:
                    yield f"data: {line}\n\n".encode("utf-8")
            except queue.Empty:
                yield b"data: [HEARTBEAT]\n\n"

        return_code = process.wait()

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
        if current_process is process:
            current_process = None


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
async def analyze(mode: str = "", source: str = "", num_clips: str = "5", whisper_model: str = "groq"):
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

    analysis_id = f"analysis_{int(_time.time() * 1000)}"

    cmd = [
        sys.executable, "-u", "-m", "backend.worker",
        "--file", source,
        "--num-clips", str(clip_count),
        "--mode", mode or "hook",
        "--model", whisper_model,
        "--analyze-only"
    ]

    def generate():
        save_failed = False
        for chunk in _sse_from_process(cmd):
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

    cmd = [
        sys.executable, "-u", "-m", "backend.worker",
        "--file", video_path,
        "--clips-json", analysis_path,
        "--render-indices", indices_str,
        "--sub-style", sub_style,
        "--framing-mode", framing_mode
    ]

    return StreamingResponse(_sse_from_process(cmd), media_type="text/event-stream")


@app.get("/stream")
async def stream(mode: str = "", source_type: str = "", source: str = "", num_clips: str = "5", sub_style: str = "tiktok_viral", whisper_model: str = "groq", framing_mode: str = "smart_crop"):

    cmd = [
        sys.executable, "-u", "-m", "backend.worker",
        "--file", source,
        "--num-clips", str(num_clips),
        "--mode", mode,
        "--sub-style", sub_style,
        "--model", whisper_model,
        "--framing-mode", framing_mode
    ]

    return StreamingResponse(_sse_from_process(cmd), media_type="text/event-stream")

# Serve static files from frontend directory (production dist or root)
app.mount("/", StaticFiles(directory=SERVE_DIR), name="static")

if __name__ == '__main__':
    import uvicorn
    uvicorn.run("backend.main:app", host="127.0.0.1", port=5050, reload=False)
