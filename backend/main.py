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
from fastapi.responses import HTMLResponse, StreamingResponse, JSONResponse, FileResponse, RedirectResponse, Response
from fastapi.staticfiles import StaticFiles
from backend import youtube_uploader
from backend.config_wizard import (
    get_ai_config,
    save_ai_config,
    test_ai_connection,
    test_groq_connection,
    fetch_available_models,
)
from backend.utils import env_bool

app = FastAPI()

# Local CSRF / Host validation & Local Session Token
SESSION_TOKEN_FILE = os.path.join(os.path.expanduser("~"), ".visionclipper_session_token")

def _get_or_create_session_token() -> str:
    if os.path.exists(SESSION_TOKEN_FILE):
        try:
            with open(SESSION_TOKEN_FILE, "r", encoding="utf-8") as f:
                token = f.read().strip()
                if len(token) == 64 and all(c in "0123456789abcdefABCDEF" for c in token):
                    return token
        except Exception:
            pass
    token = secrets.token_hex(32)
    try:
        flags = os.O_WRONLY | os.O_CREAT | os.O_TRUNC
        fd = os.open(SESSION_TOKEN_FILE, flags, 0o600)
        with open(fd, "w", encoding="utf-8") as f:
            f.write(token)
    except Exception:
        pass
    return token

SESSION_TOKEN = _get_or_create_session_token()

ALLOWED_HOSTS = {
    "localhost", "127.0.0.1", "[::1]", "0.0.0.0",
    "localhost:3000", "127.0.0.1:3000", "[::1]:3000", "0.0.0.0:3000",
    "localhost:5050", "127.0.0.1:5050", "[::1]:5050", "0.0.0.0:5050",
    "testserver"
}

def _extra_allowed_hosts():
    """Extra Host/Origin allowlist from VC_ALLOWED_HOSTS (comma separated).

    Empty by default, so local desktop installs keep the original loopback-only
    behaviour. Only needed when the dashboard is served through a domain or a
    non-private IP (e.g. a VPS behind nginx).
    """
    raw = os.environ.get("VC_ALLOWED_HOSTS", "")
    return {item.strip().lower() for item in raw.split(",") if item.strip()}

def _is_allowed_host(host: str) -> bool:
    if not host:
        return True
    host_clean = host.strip().lower()
    if host_clean in ALLOWED_HOSTS:
        return True
    hostname = host_clean.split(":")[0]
    if hostname in {"localhost", "127.0.0.1", "0.0.0.0", "::1", "testserver"}:
        return True
    extra_hosts = _extra_allowed_hosts()
    if extra_hosts and (host_clean in extra_hosts or hostname in extra_hosts):
        return True
    if hostname.startswith("192.168.") or hostname.startswith("10.") or hostname.startswith("127."):
        return True
    if re.match(r"^172\.(1[6-9]|2[0-9]|3[0-1])\.", hostname):
        return True
    return False

SESSION_EXEMPT_PATHS = {"/api/session", "/api/social/youtube/callback"}
SESSION_PROTECTED_PATHS = {"/stream", "/cancel", "/shutdown"}

@app.middleware("http")
async def security_middleware(request: Request, call_next):
    # 1. Validate Host header to protect against DNS rebinding
    host_header = request.headers.get("host", "").strip().lower()
    if host_header and not _is_allowed_host(host_header):
        from backend.utils import log
        log(f"[SECURITY 403] Host '{host_header}' is not allowed for path {request.url.path}")
        return JSONResponse(status_code=403, content={"error": f"Forbidden: Invalid Host header ({host_header})"})

    # 2. Require the browser session cookie for every local API/control endpoint.
    path = request.url.path
    session_required = path.startswith("/api/") or path in SESSION_PROTECTED_PATHS
    if session_required and path not in SESSION_EXEMPT_PATHS:
        session_token = request.cookies.get("vc_session_token", "")
        if not session_token or not secrets.compare_digest(session_token, SESSION_TOKEN):
            from backend.utils import log
            log(f"[SECURITY 403] Invalid session token for path '{path}'")
            return JSONResponse(status_code=403, content={"error": "Forbidden: Invalid local session"})

    # 3. Validate Origin/Referer when supplied on mutating actions.
    if request.method in ("POST", "PUT", "DELETE", "PATCH"):
        origin = request.headers.get("origin")
        referer = request.headers.get("referer")
        
        # Check Origin if present
        if origin:
            try:
                parsed = urlparse(origin)
                netloc = parsed.netloc.lower()
                if not _is_allowed_host(netloc):
                    from backend.utils import log
                    log(f"[SECURITY 403] Origin '{origin}' is not allowed for path {path}")
                    return JSONResponse(status_code=403, content={"error": "Forbidden: Invalid Origin header"})
            except Exception:
                return JSONResponse(status_code=403, content={"error": "Forbidden: Malformed Origin header"})
        elif referer:
            try:
                parsed = urlparse(referer)
                netloc = parsed.netloc.lower()
                if not _is_allowed_host(netloc):
                    from backend.utils import log
                    log(f"[SECURITY 403] Referer '{referer}' is not allowed for path {path}")
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
CLIPS_DIR = os.path.realpath(os.path.join(PROJECT_ROOT, "clips"))


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
            # Check for stale reservation (timeout after 15 seconds)
            if _time.time() - _ACTIVE_JOB.get("reserved_at", 0) > 15:
                _ACTIVE_JOB = None
                return False
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
            if process is None:
                if _time.time() - _ACTIVE_JOB.get("reserved_at", 0) > 15:
                    _ACTIVE_JOB = None
                else:
                    raise RuntimeError("A worker is already processing a request")
            elif process.poll() is None:
                raise RuntimeError("A worker is already processing a request")
        job_id = str(uuid.uuid4())
        _ACTIVE_JOB = {"job_id": job_id, "process": None, "reserved_at": _time.time()}
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


class RenderedClipsFolderError(ValueError):
    def __init__(self, status_code: int, message: str):
        super().__init__(message)
        self.status_code = status_code


def _path_is_within(root_path: str, target_path: str) -> bool:
    try:
        real_root = os.path.realpath(os.path.abspath(root_path))
        real_target = os.path.realpath(os.path.abspath(target_path))
        return os.path.commonpath([real_root, real_target]) == real_root
    except (OSError, TypeError, ValueError):
        return False


def _resolve_rendered_clips_folder(target_path: str) -> str:
    """Resolve one render project folder while keeping it contained in clips/."""
    if not isinstance(target_path, str) or not target_path.strip():
        raise RenderedClipsFolderError(400, "Path parameter is empty")

    raw_path = target_path.strip()
    if not os.path.isabs(raw_path):
        candidate = os.path.join(PROJECT_ROOT, raw_path)
        if os.path.exists(candidate):
            requested_path = candidate
        else:
            requested_path = os.path.abspath(os.path.expanduser(raw_path))
    else:
        requested_path = os.path.abspath(os.path.expanduser(raw_path))

    if not os.path.exists(requested_path):
        raise RenderedClipsFolderError(404, f"Folder tidak ditemukan: {target_path}")

    # If the user selected a video file inside a project folder, resolve to its parent folder
    if os.path.isfile(requested_path):
        requested_path = os.path.dirname(requested_path)

    if not os.path.isdir(requested_path):
        raise RenderedClipsFolderError(400, "Path must point to a rendered clips folder")
    if os.path.islink(requested_path):
        raise RenderedClipsFolderError(403, "Symlink folders cannot be loaded as rendered clips")

    real_clips_dir = os.path.realpath(CLIPS_DIR)
    real_target = os.path.realpath(requested_path)
    if real_target == real_clips_dir:
        raise RenderedClipsFolderError(400, "Select one project folder inside clips, not the clips root")
    if not _path_is_within(real_clips_dir, real_target):
        raise RenderedClipsFolderError(403, "Rendered clips folder must be inside the clips directory")
    return real_target


def _rendered_clip_sort_key(path: str):
    filename = os.path.basename(path)
    prefix = re.match(r"^(\d+)(?:[\s_-]|$)", filename)
    return (0, int(prefix.group(1)), filename.lower()) if prefix else (1, 0, filename.lower())


def _rendered_video_paths(target_path: str):
    real_folder = _resolve_rendered_clips_folder(target_path)
    video_paths = []
    with os.scandir(real_folder) as entries:
        for entry in entries:
            try:
                if entry.name.startswith('.') or not entry.is_file(follow_symlinks=False):
                    continue
                if os.path.splitext(entry.name)[1].lower() not in ALLOWED_VIDEO_EXTENSIONS:
                    continue
                real_file = os.path.realpath(entry.path)
                if _path_is_within(real_folder, real_file):
                    video_paths.append(real_file)
            except OSError:
                continue
    return real_folder, sorted(video_paths, key=_rendered_clip_sort_key)


def _fallback_rendered_title(video_path: str) -> str:
    stem = os.path.splitext(os.path.basename(video_path))[0]
    stem = re.sub(r"^\d+[\s_-]*", "", stem)
    title = re.sub(r"[_\s]+", " ", stem).strip()
    return title or "Rendered Clip"


def _parse_rendered_clip_metadata(metadata_path: str):
    """Parse renderer sidecar text without requiring metadata to load a clip."""
    sections = {
        "title options": [],
        "caption": [],
        "hashtags": [],
        "hook": [],
        "first comment": [],
        "series": [],
    }
    current_section = None
    try:
        with open(metadata_path, "r", encoding="utf-8") as metadata_file:
            for raw_line in metadata_file.read().splitlines():
                heading = raw_line.strip().rstrip(":").lower()
                if heading in sections:
                    current_section = heading
                    continue
                if current_section is not None:
                    sections[current_section].append(raw_line)
    except (OSError, UnicodeError):
        return {
            "title": "",
            "caption": "",
            "hashtags": [],
            "hook_line": "",
            "first_comment": "",
            "series": "",
        }

    def _joined(key):
        return "\n".join(sections[key]).strip()

    titles = [
        re.sub(r"^\s*[-*]\s*", "", line).strip()
        for line in sections["title options"]
        if line.strip()
    ]
    caption = _joined("caption")
    hashtags_text = " ".join(sections["hashtags"]).strip()
    hashtags = re.findall(r"#[^\s#]+", hashtags_text)
    if not hashtags and hashtags_text:
        hashtags = [token.lstrip("#") for token in re.split(r"[\s,]+", hashtags_text) if token.strip("#")]

    return {
        "title": titles[0] if titles else "",
        "caption": caption,
        "hashtags": hashtags,
        "hook_line": _joined("hook").replace("\n", " "),
        "first_comment": _joined("first comment").replace("\n", " "),
        "series": _joined("series").replace("\n", " "),
    }


def _load_rendered_clips(target_path: str):
    real_folder, video_paths = _rendered_video_paths(target_path)
    if not video_paths:
        raise RenderedClipsFolderError(404, "Folder ini tidak berisi video hasil render")

    clips = []
    for index, video_path in enumerate(video_paths, 1):
        metadata_path = os.path.splitext(video_path)[0] + ".txt"
        metadata = {
            "title": "",
            "caption": "",
            "hashtags": [],
            "hook_line": "",
            "first_comment": "",
            "series": "",
        }
        if (
            os.path.isfile(metadata_path)
            and not os.path.islink(metadata_path)
            and _path_is_within(real_folder, metadata_path)
        ):
            metadata = _parse_rendered_clip_metadata(metadata_path)

        fallback_title = _fallback_rendered_title(video_path)
        clips.append({
            "id": str(index),
            "title": metadata["title"] or fallback_title,
            "filename": os.path.basename(video_path),
            "out_file": video_path,
            "caption": metadata["caption"] or fallback_title,
            "hashtags": metadata["hashtags"],
            "hook_line": metadata.get("hook_line", ""),
            "first_comment": metadata.get("first_comment", ""),
            "series": metadata.get("series", ""),
        })

    return {"output_dir": real_folder, "clips": clips}

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


def _is_allowed_clip_upload(target_path: str) -> bool:
    try:
        real_target = os.path.realpath(os.path.abspath(target_path))
        return (
            os.path.isfile(real_target)
            and os.path.splitext(real_target)[1].lower() in ALLOWED_VIDEO_EXTENSIONS
            and os.path.commonpath([CLIPS_DIR, real_target]) == CLIPS_DIR
        )
    except (OSError, ValueError, TypeError):
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

def _set_session_cookie(response: Response):
    response.set_cookie(
        key="vc_session_token",
        value=SESSION_TOKEN,
        httponly=True,
        samesite="strict",
        # Default False: a Secure cookie is rejected over plain HTTP, which would
        # break every /api/* call on local desktop installs (http://localhost).
        # Enable it only when the dashboard is served over HTTPS (VPS + TLS).
        secure=env_bool("VC_COOKIE_SECURE", False),
    )
    return response


@app.get("/api/session", status_code=204)
async def bootstrap_session():
    response = Response(status_code=204, headers={"Cache-Control": "no-store"})
    return _set_session_cookie(response)


@app.get("/", response_class=HTMLResponse)
async def index():
    index_path = os.path.join(SERVE_DIR, "index.html")
    if not os.path.exists(index_path):
        # Do not serve raw unbundled TSX/HTML
        return _set_session_cookie(HTMLResponse(content=FALLBACK_HTML, status_code=200))
    with open(index_path, "r", encoding="utf-8") as f:
        html_content = f.read()
    return _set_session_cookie(HTMLResponse(content=html_content))

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

    path = real_path
    try:
        folders = []
        files = []
        with os.scandir(path) as entries:
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
                        if ext in ALLOWED_VIDEO_EXTENSIONS:
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

        render_clip_count = 0
        try:
            _, rendered_paths = _rendered_video_paths(path)
            render_clip_count = len(rendered_paths)
        except RenderedClipsFolderError:
            pass

        return {
            "current_path": path,
            "parent_path": parent_path,
            "drives": drives,
            "home_path": os.path.realpath(os.path.expanduser("~")),
            "clips_path": os.path.realpath(CLIPS_DIR),
            "can_load_rendered": render_clip_count > 0,
            "render_clip_count": render_clip_count,
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
            "home_path": os.path.realpath(os.path.expanduser("~")),
            "clips_path": os.path.realpath(CLIPS_DIR),
            "can_load_rendered": False,
            "render_clip_count": 0,
            "folders": [],
            "files": []
        }


@app.post("/api/rendered-clips/load")
async def load_rendered_clips(request: Request):
    """Restore an existing render project so it can be previewed and posted."""
    try:
        data = await request.json()
    except Exception:
        return JSONResponse(status_code=400, content={"error": "Invalid JSON body"})

    path = data.get("path") if isinstance(data, dict) else None
    try:
        return _load_rendered_clips(path)
    except RenderedClipsFolderError as error:
        return JSONResponse(status_code=error.status_code, content={"error": str(error)})

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

    if not os.path.isdir(real_path):
        return JSONResponse(status_code=400, content={"error": "Path harus berupa direktori"})

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


def _has_desktop_session() -> bool:
    """True when a GUI session exists so a native dialog can actually be shown.

    Headless Linux (VPS, docker, systemd without a seat) has no DISPLAY and no
    WAYLAND_DISPLAY, and usually no zenity either. Spawning it there only wastes
    time and returns nothing, so the pickers short-circuit and the frontend falls
    back to the manual path/URL input.
    """
    return bool(os.environ.get("DISPLAY") or os.environ.get("WAYLAND_DISPLAY"))

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
            # Linux zenity fallback (only when a desktop session exists)
            if _has_desktop_session():
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


def _run_native_folder_picker(initial_dir: str = "") -> str:
    """Synchronous folder picker logic called inside asyncio.to_thread."""
    selected_path = ""
    target_dir = initial_dir if initial_dir and os.path.exists(initial_dir) else CLIPS_DIR
    try:
        if sys.platform == 'darwin':
            # AppleScript native folder picker
            if target_dir and os.path.exists(target_dir):
                escaped_dir = os.path.realpath(target_dir).replace('"', '\\"')
                script = (
                    f'set defaultLoc to POSIX file "{escaped_dir}"\n'
                    'return POSIX path of (choose folder with prompt "Pilih Folder Hasil Render (Clips)" default location defaultLoc)'
                )
            else:
                script = 'return POSIX path of (choose folder with prompt "Pilih Folder Hasil Render (Clips)")'
            res = subprocess.run(['osascript', '-e', script], capture_output=True, text=True)
            if res.returncode == 0:
                selected_path = res.stdout.strip()
        elif os.name == 'nt':
            escaped_dir = os.path.realpath(target_dir).replace('"', '`"') if target_dir and os.path.exists(target_dir) else ""
            initial_ps = f'$f.SelectedPath = "{escaped_dir}";' if escaped_dir else ""
            ps_script = (
                'Add-Type -AssemblyName System.Windows.Forms;'
                '$f = New-Object System.Windows.Forms.FolderBrowserDialog;'
                '$f.Description = "Pilih Folder Hasil Render (Clips)";'
                + initial_ps +
                'if ($f.ShowDialog() -eq [System.Windows.Forms.DialogResult]::OK) { Write-Output $f.SelectedPath }'
            )
            res = subprocess.run(['powershell', '-NoProfile', '-Command', ps_script], capture_output=True, text=True)
            if res.returncode == 0:
                selected_path = res.stdout.strip()
        else:
            # Linux zenity fallback (only when a desktop session exists)
            if _has_desktop_session():
                cmd = ['zenity', '--file-selection', '--directory', '--title=Pilih Folder Hasil Render (Clips)']
                if target_dir and os.path.exists(target_dir):
                    cmd.append(f'--filename={os.path.realpath(target_dir)}/')
                res = subprocess.run(cmd, capture_output=True, text=True)
                if res.returncode == 0:
                    selected_path = res.stdout.strip()
    except Exception:
        pass
    return selected_path


@app.post("/api/pick-folder")
async def pick_folder():
    """Trigger native OS folder chooser dialog in threadpool and return chosen folder path."""
    try:
        selected_path = await asyncio.to_thread(_run_native_folder_picker, CLIPS_DIR)
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
            # Explicit stdio: never inherit the server's (possibly stale) fds.
            # Inheriting a dead terminal fd as stdin makes the child abort at
            # interpreter init: "Fatal Python error: init_sys_streams ... Bad file descriptor".
            stdin=subprocess.DEVNULL,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            bufsize=0,
            close_fds=True,
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

# Cleanup stale files on startup
from backend.utils import cleanup_temp_files
cleanup_temp_files()

for _f in os.listdir(TEMP_ANALYSIS_DIR):
    if _f.startswith("analysis_") and _f.endswith(".json"):
        _fpath = os.path.join(TEMP_ANALYSIS_DIR, _f)
        try:
            if _time.time() - os.path.getmtime(_fpath) > 86400:
                os.remove(_fpath)
        except Exception:
            pass


@app.get("/api/analyze")
async def analyze(request: Request, mode: str = "", source: str = "", num_clips: str = "5", whisper_model: str = "groq", source_lang: str = "id"):
    """Phase 1: Transcribe + LLM analysis only. Returns SSE stream with [ANALYSIS_RESULT] JSON."""
    if _worker_is_active():
        return JSONResponse(status_code=409, content={"error": "A worker is already processing a request"})
    if not source.strip():
        return JSONResponse(status_code=400, content={"error": "Source parameter is empty"})
    if mode and mode not in {"hook", "affiliate"}:
        return JSONResponse(status_code=400, content={"error": "Invalid mode"})
    if whisper_model not in {"groq"}:
        return JSONResponse(status_code=400, content={"error": "Invalid transcription model. Hanya 'groq' yang didukung."})
    if source_lang not in {"id", "en", "auto"}:
        return JSONResponse(status_code=400, content={"error": "Invalid source language"})
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
        "--source-lang", source_lang,
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


@app.get("/api/analysis-clip-words")
async def analysis_clip_words(analysis_id: str = "", index: str = "1"):
    """Return the transcript words inside one analysed clip.

    The SSE payload deliberately drops ``segments`` to keep it small, so the
    pre-render preview asks for the words of the clip it is currently showing.
    That lets the subtitle preview display the real spoken text instead of a
    hard-coded sample, in sync with the video position.
    """
    if not _valid_analysis_id(analysis_id):
        return JSONResponse(status_code=400, content={"error": "Invalid analysis_id"})
    try:
        clip_index = int(index)
    except (TypeError, ValueError):
        return JSONResponse(status_code=400, content={"error": "index must be an integer"})

    analysis_path = os.path.join(TEMP_ANALYSIS_DIR, f"{analysis_id}.json")
    if not os.path.exists(analysis_path):
        return JSONResponse(status_code=404, content={"error": "Analysis file not found"})

    try:
        with open(analysis_path, "r", encoding="utf-8") as f:
            analysis = json.load(f)
    except Exception as e:
        return JSONResponse(status_code=500, content={"error": f"Failed to read analysis: {e}"})

    clips = analysis.get("clips") or []
    segments = analysis.get("segments") or []
    if not isinstance(clips, list) or not 1 <= clip_index <= len(clips):
        return JSONResponse(status_code=400, content={"error": "clip index out of range"})

    clip = clips[clip_index - 1]
    clip_start = float(clip.get("start", 0.0))
    clip_end = float(clip.get("end", 0.0))

    words = []
    for seg in segments:
        seg_start = float(seg.get("start", 0.0))
        seg_end = float(seg.get("end", 0.0))
        if seg_end <= clip_start or seg_start >= clip_end:
            continue
        seg_words = seg.get("words") or []
        if seg_words:
            for w in seg_words:
                w_start = float(w.get("start", 0.0))
                w_end = float(w.get("end", 0.0))
                if w_end > clip_start and w_start < clip_end:
                    words.append({
                        "word": str(w.get("word", "")).strip(),
                        "start": round(w_start, 3),
                        "end": round(w_end, 3),
                    })
        else:
            words.append({
                "word": str(seg.get("text", "")).strip(),
                "start": round(seg_start, 3),
                "end": round(seg_end, 3),
            })

    words = [w for w in words if w["word"]]
    return JSONResponse(content={
        "index": clip_index,
        "start": clip_start,
        "end": clip_end,
        "words": words,
    })

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
    sub_position = data.get("sub_position", 68)
    try:
        sub_position = max(30, min(85, int(sub_position)))
    except (TypeError, ValueError):
        sub_position = 68
    # Frontend always sends this key; default to enabled to match the analyze
    # endpoint and the UI toggle's initial state.
    watermark_enabled = bool(data.get("watermark_enabled", True))

    if not _valid_analysis_id(analysis_id) or not isinstance(clip_indices, list) or not clip_indices:
        return JSONResponse(status_code=400, content={"error": "Missing analysis_id or clip_indices"})
    if sub_style not in {"tiktok_viral", "classic_karaoke", "minimalist", "word_pop", "no_subtitle", "none"}:
        return JSONResponse(status_code=400, content={"error": "Invalid subtitle style"})
    if framing_mode not in {"smart_crop", "fit_blur", "split_screen"}:
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
        "--framing-mode", framing_mode,
        "--sub-position", str(sub_position),
    ]
    source_watermark = str(data.get("source_watermark", "")).strip()
    account_watermark = str(data.get("account_watermark", "")).strip()
    if watermark_enabled:
        cmd.append("--watermark-enabled")
    else:
        cmd.append("--no-watermark")
    if source_watermark:
        cmd.extend(["--source-watermark", source_watermark])
    if account_watermark:
        cmd.extend(["--account-watermark", account_watermark])

    return StreamingResponse(_sse_from_process(cmd, job_id=job_id, request=request), media_type="text/event-stream")


@app.get("/stream")
async def stream(request: Request, mode: str = "", source_type: str = "", source: str = "", num_clips: str = "5", sub_style: str = "tiktok_viral", whisper_model: str = "groq", framing_mode: str = "smart_crop", sub_position: str = "68", watermark_enabled: str = "true", source_watermark: str = "", account_watermark: str = "", source_lang: str = "id"):
    """Legacy streaming endpoint protected with synchronized worker slot."""
    if _worker_is_active():
        return JSONResponse(status_code=409, content={"error": "A worker is already processing a request"})
    if not source.strip():
        return JSONResponse(status_code=400, content={"error": "Source parameter is empty"})
    if framing_mode not in {"smart_crop", "fit_blur", "split_screen"}:
        return JSONResponse(status_code=400, content={"error": "Invalid framing mode"})

    try:
        sub_pos_int = max(30, min(85, int(sub_position)))
    except (TypeError, ValueError):
        sub_pos_int = 68
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
        "--framing-mode", framing_mode,
        "--sub-position", str(sub_pos_int),
        "--source-lang", source_lang if source_lang in {"id", "en", "auto"} else "id",
    ]
    wm_bool = watermark_enabled.lower() in {"1", "true", "yes"}
    if wm_bool:
        cmd.append("--watermark-enabled")
    else:
        cmd.append("--no-watermark")
    if source_watermark.strip():
        cmd.extend(["--source-watermark", source_watermark.strip()])
    if account_watermark.strip():
        cmd.extend(["--account-watermark", account_watermark.strip()])

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
    if not _is_allowed_clip_upload(video_path):
        return JSONResponse(status_code=403, content={"error": "Only rendered videos inside the clips folder may be uploaded"})
    video_path = os.path.realpath(video_path)

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


# ── AI Model & Provider Configuration Endpoints ──
@app.get("/api/ai-config")
async def api_get_ai_config(request: Request):
    """Retrieve current AI configuration with masked secrets."""
    try:
        config = get_ai_config()
        return JSONResponse(config)
    except Exception as e:
        return JSONResponse(status_code=500, content={"error": str(e)})


@app.post("/api/ai-config")
async def api_save_ai_config(request: Request):
    """Save AI configuration atomically and refresh active engine settings."""
    try:
        data = await request.json()
    except Exception:
        return JSONResponse(status_code=400, content={"error": "Invalid JSON body"})

    try:
        result = save_ai_config(
            provider=data.get("provider"),
            endpoint=data.get("endpoint"),
            model=data.get("model"),
            api_key=data.get("api_key"),
            groq_key=data.get("groq_key"),
        )
        return JSONResponse(result)
    except Exception as e:
        return JSONResponse(status_code=500, content={"error": str(e)})


@app.post("/api/ai-config/test")
async def api_test_ai_connection(request: Request):
    """Test connection to LLM endpoint with given or saved credentials."""
    try:
        data = await request.json()
    except Exception:
        data = {}

    try:
        result = await asyncio.to_thread(
            test_ai_connection,
            endpoint=data.get("endpoint"),
            api_key=data.get("api_key"),
            model=data.get("model"),
        )
        return JSONResponse(result)
    except Exception as e:
        return JSONResponse(status_code=500, content={"ok": False, "error": str(e)})


@app.post("/api/ai-config/models")
async def api_fetch_available_models(request: Request):
    """Auto-detect available models from the provider endpoint (GET {base}/models)."""
    try:
        data = await request.json()
    except Exception:
        data = {}

    try:
        result = await asyncio.to_thread(
            fetch_available_models,
            endpoint=data.get("endpoint"),
            api_key=data.get("api_key"),
        )
        return JSONResponse(result)
    except Exception as e:
        return JSONResponse(status_code=500, content={"ok": False, "error": str(e)})

@app.post("/api/ai-config/test-groq")
async def api_test_groq_connection(request: Request):
    """Test Groq API key with Groq Cloud."""
    try:
        data = await request.json()
    except Exception:
        data = {}

    try:
        result = await asyncio.to_thread(
            test_groq_connection,
            groq_key=data.get("groq_key"),
        )
        return JSONResponse(result)
    except Exception as e:
        return JSONResponse(status_code=500, content={"ok": False, "error": str(e)})


# Serve static files from frontend directory (production dist or root)
app.mount("/", StaticFiles(directory=SERVE_DIR, html=True), name="static")

if __name__ == '__main__':
    import uvicorn
    # VC_HOST lets a VPS bind to 0.0.0.0 (or a specific interface). The port stays
    # fixed at 5050 because it is referenced by the CLI, the installers and the
    # YouTube OAuth redirect URI.
    uvicorn.run(
        "backend.main:app",
        host=os.environ.get("VC_HOST", "127.0.0.1"),
        port=5050,
        reload=False,
    )
