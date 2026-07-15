import os
import subprocess
from flask import Flask, render_template, request, Response, jsonify

app = Flask(__name__)

# To hold the currently running process
current_process = None

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/browse', methods=['GET'])
def browse():
    import tkinter as tk
    from tkinter import filedialog
    
    # Create a root window and hide it
    root = tk.Tk()
    root.withdraw()
    # Force the window to the top
    root.attributes('-topmost', True)
    
    file_path = filedialog.askopenfilename(
        title="Pilih File Video",
        filetypes=[("Video Files", "*.mp4 *.mov *.mkv *.avi"), ("All Files", "*.*")]
    )
    
    root.destroy()
    return jsonify({"path": file_path})

@app.route('/shutdown', methods=['POST'])
def shutdown():
    global current_process
    if current_process and current_process.poll() is None:
        try:
            subprocess.run(['taskkill', '/F', '/T', '/PID', str(current_process.pid)], capture_output=True)
        except:
            pass
    # Clean up PID file so CLI knows the server is gone
    pid_file = os.path.join(os.path.expanduser("~"), ".visionclipper.pid")
    try:
        os.remove(pid_file)
    except OSError:
        pass
    os._exit(0)
    return jsonify({"status": "shutting_down"})

@app.route('/cancel', methods=['POST'])
def cancel():
    global current_process
    if current_process and current_process.poll() is None:
        try:
            # On Windows, use taskkill to kill the entire process tree (including ffmpeg/yt-dlp child processes)
            subprocess.run(['taskkill', '/F', '/T', '/PID', str(current_process.pid)], capture_output=True)
        except Exception as e:
            # Fallback
            current_process.kill()
            
        current_process = None
        return jsonify({"status": "cancelled"})
    return jsonify({"status": "no_process"})

@app.route('/stream')
def stream():
    mode = request.args.get('mode')
    source_type = request.args.get('source_type')
    source = request.args.get('source')
    num_clips = request.args.get('num_clips', '5')
    
    import sys
    script_name = "affiliate_clipper.py" if mode == "affiliate" else "hook_cutter.py"
    script_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), script_name)
    
    # Run with -u for unbuffered stdout
    cmd = [sys.executable, "-u", script_path, f"--{source_type}", source, "--num-clips", str(num_clips)]
    
    def generate():
        global current_process
        try:
            kwargs = {}
            if os.name == 'nt':
                kwargs['creationflags'] = 0x08000000 # CREATE_NO_WINDOW

            current_process = subprocess.Popen(
                cmd,
                stdout=subprocess.PIPE,
                stderr=subprocess.STDOUT,
                bufsize=0, # Unbuffered for real-time reading
                **kwargs
            )
            
            buffer = ""
            while True:
                byte = current_process.stdout.read(1)
                if not byte:
                    break
                    
                char = byte.decode('utf-8', errors='replace')
                if char == '\r' or char == '\n':
                    if buffer:
                        yield f"data: {buffer}\n\n"
                        buffer = ""
                else:
                    buffer += char
                    
            if buffer:
                yield f"data: {buffer}\n\n"
                
            return_code = current_process.wait()
            
            if return_code == 0:
                yield f"data: [PROCESS_COMPLETE]\n\n"
            else:
                yield f"data: [PROCESS_FAILED]\n\n"
                
        except Exception as e:
            yield f"data: Error: {str(e)}\n\n"
            
    return Response(generate(), mimetype='text/event-stream')

if __name__ == '__main__':
    # Buka port localhost:5000
    app.run(host='127.0.0.1', port=5000, debug=True)
