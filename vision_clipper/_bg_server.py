"""
Background server launcher for VisionClipper Studio.
This script is spawned by cli.py as a detached process (via pythonw.exe).
It runs the Flask app and cleans up the PID file when shutting down.
"""
import os
import sys
import atexit

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

# Import and run the Flask app
from vision_clipper.app import app
app.run(host='127.0.0.1', port=5000, debug=False, use_reloader=False)
