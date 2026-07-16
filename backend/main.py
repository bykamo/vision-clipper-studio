import os
import subprocess
import sys
import string
import ctypes
import queue
import threading
from fastapi import FastAPI, Request
from fastapi.responses import HTMLResponse, StreamingResponse, JSONResponse
from fastapi.staticfiles import StaticFiles

app = FastAPI()

# Global to keep track of running process for cancellation
current_process = None

FRONTEND_DIR = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "frontend")

@app.get("/", response_class=HTMLResponse)
async def index():
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

@app.post("/cancel")
async def cancel():
    global current_process
    if current_process and current_process.poll() is None:
        try:
            subprocess.run(['taskkill', '/F', '/T', '/PID', str(current_process.pid)], capture_output=True)
        except Exception:
            current_process.kill()
        current_process = None
        return {"status": "cancelled"}
    return {"status": "no_process"}

@app.post("/shutdown")
async def shutdown():
    global current_process
    if current_process and current_process.poll() is None:
        try:
            subprocess.run(['taskkill', '/F', '/T', '/PID', str(current_process.pid)], capture_output=True)
        except:
            pass
    pid_file = os.path.join(os.path.expanduser("~"), ".visionclipper.pid")
    try:
        os.remove(pid_file)
    except OSError:
        pass
    os._exit(0)
    return {"status": "shutting_down"}

@app.get("/stream")
async def stream(mode: str = "", source_type: str = "", source: str = "", num_clips: str = "5"):
    
    cmd = [
        sys.executable, "-u", "-m", "backend.worker",
        "--file", source,
        "--num-clips", str(num_clips),
        "--mode", mode
    ]
    
    def generate():
        global current_process
        try:
            kwargs = {}
            if os.name == 'nt':
                kwargs['creationflags'] = 0x08000000 

            current_process = subprocess.Popen(
                cmd,
                stdout=subprocess.PIPE,
                stderr=subprocess.STDOUT,
                bufsize=0, 
                cwd=os.path.dirname(FRONTEND_DIR),
                **kwargs
            )
            
            q = queue.Queue()
            
            def read_output():
                buffer = ""
                while True:
                    byte = current_process.stdout.read(1)
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
                    
            return_code = current_process.wait()
            
            if return_code == 0:
                yield b"data: [PROCESS_COMPLETE]\n\n"
            else:
                yield b"data: [PROCESS_FAILED]\n\n"
                
        except Exception as e:
            yield f"data: Error: {str(e)}\n\n".encode("utf-8")
        finally:
            if 'current_process' in globals() and current_process and current_process.stdout:
                try:
                    current_process.stdout.close()
                except Exception:
                    pass
            
    return StreamingResponse(generate(), media_type="text/event-stream")

# Serve static files from frontend directory
app.mount("/", StaticFiles(directory=FRONTEND_DIR), name="static")

if __name__ == '__main__':
    import uvicorn
    uvicorn.run("backend.main:app", host="127.0.0.1", port=5000, reload=False)
