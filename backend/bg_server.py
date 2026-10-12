"""
Background server launcher for VisionClipper Studio.
This script is spawned by cli.py as a detached process (via pythonw.exe).
It runs the FastAPI/Uvicorn app and cleans up the PID file when shutting down.
"""
import os
import sys
import atexit

# Fix sys.path so 'vision_clipper' module can be found
script_dir = os.path.dirname(os.path.abspath(__file__))
project_root = os.path.dirname(script_dir)
if project_root not in sys.path:
    sys.path.insert(0, project_root)


PID_FILE = os.path.join(os.path.expanduser("~"), ".visionclipper.pid")

def cleanup_pid():
    """Remove PID file on exit."""
    try:
        os.remove(PID_FILE)
    except OSError:
        pass

# Register cleanup
atexit.register(cleanup_pid)

# Write our PID (update in case the parent recorded a different one)
with open(PID_FILE, "w") as f:
    f.write(str(os.getpid()))

# Redirect stdout/stderr to a log file to capture the crash reason
log_file = open(os.path.join(project_root, "server_error.log"), 'w', buffering=1)
sys.stdout = log_file
sys.stderr = log_file

import uvicorn
try:
    uvicorn.run("backend.main:app", host='127.0.0.1', port=5050, reload=False)
except Exception as e:
    import traceback
    traceback.print_exc()
