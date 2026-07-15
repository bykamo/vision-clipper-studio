import sys
import os
import subprocess
import time
import signal

PID_FILE = os.path.join(os.path.expanduser("~"), ".visionclipper.pid")
SERVER_URL = "http://localhost:5000"

def get_running_pid():
    """Read PID from file and check if the process is still alive."""
    if not os.path.exists(PID_FILE):
        return None
    try:
        with open(PID_FILE, "r") as f:
            pid = int(f.read().strip())
        # Check if process is still running (Windows)
        result = subprocess.run(
            ["tasklist", "/FI", f"PID eq {pid}", "/NH"],
            capture_output=True, text=True, creationflags=0x08000000
        )
        if str(pid) in result.stdout:
            return pid
        else:
            # PID file is stale, clean it up
            cleanup_pid_file()
            return None
    except (ValueError, FileNotFoundError, OSError):
        cleanup_pid_file()
        return None

def cleanup_pid_file():
    """Remove stale PID file."""
    try:
        os.remove(PID_FILE)
    except OSError:
        pass

def is_server_alive():
    """Check if the server is responding on the expected port."""
    try:
        import urllib.request
        req = urllib.request.urlopen(SERVER_URL, timeout=2)
        req.close()
        return True
    except Exception:
        return False

def stop_server():
    """Stop the running background server."""
    pid = get_running_pid()
    if pid:
        print(f"[STOP] Menghentikan VisionClipper Studio (PID: {pid})...")
        try:
            subprocess.run(
                ["taskkill", "/F", "/T", "/PID", str(pid)],
                capture_output=True, creationflags=0x08000000
            )
            cleanup_pid_file()
            print("[DONE] Server berhasil dihentikan.")
        except Exception as e:
            print(f"[ERROR] Gagal menghentikan server: {e}")
    elif is_server_alive():
        print("[INFO] Server masih jalan tapi PID file tidak ditemukan.")
        print("[INFO] Coba matikan lewat Web Dashboard (tombol Shut Down).")
    else:
        print("[INFO] Tidak ada server yang sedang berjalan.")

def start_server():
    """Start the Flask server as a detached background process."""
    # Check if already running
    pid = get_running_pid()
    if pid:
        print(f"[INFO] VisionClipper Studio sudah berjalan (PID: {pid})!")
        print(f"[INFO] Buka di browser: {SERVER_URL}")
        print(f"[INFO] Untuk menghentikan: vision-clipper --stop")
        import webbrowser
        webbrowser.open(SERVER_URL)
        return

    if is_server_alive():
        print(f"[INFO] Port 5000 sudah dipakai (mungkin instance sebelumnya).")
        print(f"[INFO] Buka di browser: {SERVER_URL}")
        import webbrowser
        webbrowser.open(SERVER_URL)
        return

    print("=======================================================")
    print("         VISION CLIPPER STUDIO — BACKGROUND SERVER")
    print("=======================================================")
    print()

    # Find pythonw.exe for windowless execution
    python_dir = os.path.dirname(sys.executable)
    pythonw = os.path.join(python_dir, "pythonw.exe")

    if not os.path.exists(pythonw):
        # Fallback: use python.exe with CREATE_NO_WINDOW flag
        pythonw = sys.executable

    # The background server script
    server_script = os.path.join(os.path.dirname(os.path.abspath(__file__)), "_bg_server.py")

    print(f"[START] Meluncurkan server di background...")
    print(f"[INFO]  PID file: {PID_FILE}")

    # Launch as a fully detached process (survives terminal close)
    # DETACHED_PROCESS (0x00000008) + CREATE_NO_WINDOW (0x08000000)
    CREATE_FLAGS = 0x00000008 | 0x08000000

    process = subprocess.Popen(
        [pythonw, server_script],
        creationflags=CREATE_FLAGS,
        close_fds=True,
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
    )

    # Save PID
    with open(PID_FILE, "w") as f:
        f.write(str(process.pid))

    # Wait for server to come alive
    print("[WAIT] Menunggu server siap...", end="", flush=True)
    for i in range(15):
        time.sleep(1)
        print(".", end="", flush=True)
        if is_server_alive():
            break
    print()

    if is_server_alive():
        print()
        print("=======================================================")
        print("[SUCCESS] Server berjalan di background!")
        print(f"          Dashboard: {SERVER_URL}")
        print()
        print("  Lo bisa TUTUP terminal ini — server TETAP JALAN.")
        print()
        print("  Untuk menghentikan server:")
        print("    • Dari Web  : Klik tombol 'Shut Down' di dashboard")
        print("    • Dari CMD  : vision-clipper --stop")
        print("=======================================================")

        import webbrowser
        webbrowser.open(SERVER_URL)
    else:
        print()
        print("[ERROR] Server gagal start. Cek apakah port 5000 sudah dipakai.")
        cleanup_pid_file()

def main():
    if len(sys.argv) > 1 and sys.argv[1] in ("--stop", "-s", "stop"):
        stop_server()
    elif len(sys.argv) > 1 and sys.argv[1] in ("--status", "status"):
        pid = get_running_pid()
        if pid:
            print(f"[RUNNING] VisionClipper Studio aktif (PID: {pid})")
            print(f"          Dashboard: {SERVER_URL}")
        elif is_server_alive():
            print(f"[RUNNING] Server aktif di {SERVER_URL} (PID file tidak ditemukan)")
        else:
            print("[OFFLINE] Tidak ada server yang sedang berjalan.")
    elif len(sys.argv) > 1 and sys.argv[1] in ("--help", "-h", "help"):
        print("VisionClipper Studio — AI Viral Video Clipper")
        print()
        print("Usage:")
        print("  vision-clipper            Jalankan server di background")
        print("  vision-clipper --stop     Hentikan server yang sedang berjalan")
        print("  vision-clipper --status   Cek status server")
        print("  vision-clipper --help     Tampilkan bantuan ini")
    else:
        start_server()

if __name__ == "__main__":
    main()
