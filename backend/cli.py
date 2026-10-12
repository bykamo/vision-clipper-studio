import sys
import os
import subprocess
import time
import signal
import argparse

PID_FILE = os.path.join(os.path.expanduser("~"), ".visionclipper.pid")
SERVER_URL = "http://localhost:5050"

def _is_vision_clipper_process(pid: int) -> bool:
    """Verify if a given PID actually belongs to VisionClipper."""
    try:
        if os.name == 'nt':
            res = subprocess.run(
                ["wmic", "process", "where", f"ProcessId={pid}", "get", "CommandLine"],
                capture_output=True, text=True, creationflags=0x08000000
            )
            return "vision" in res.stdout.lower() or "backend" in res.stdout.lower()
        else:
            res = subprocess.run(["ps", "-p", str(pid), "-o", "command="], capture_output=True, text=True)
            cmd = res.stdout.lower()
            return "vision" in cmd or "backend.bg_server" in cmd or "backend.main" in cmd or "uvicorn" in cmd
    except Exception:
        return False

def get_running_pid():
    """Read PID from file and check if the process is still alive and belongs to VisionClipper."""
    if not os.path.exists(PID_FILE):
        return None
    try:
        with open(PID_FILE, "r") as f:
            pid = int(f.read().strip())
        
        if os.name == 'nt':
            result = subprocess.run(
                ["tasklist", "/FI", f"PID eq {pid}", "/NH"],
                capture_output=True, text=True, creationflags=0x08000000
            )
            if str(pid) in result.stdout:
                return pid
        else:
            os.kill(pid, 0)
            if _is_vision_clipper_process(pid):
                return pid
    except (ValueError, FileNotFoundError, OSError):
        cleanup_pid_file()
        return None
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

def check_and_prompt_ai_config():
    """Prompt AI configuration if LLM API Key, endpoint, or Groq Key is missing."""
    project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    env_path = os.path.join(project_root, ".env")
    
    needs_config = False
    if not os.path.exists(env_path):
        needs_config = True
    else:
        with open(env_path, "r", encoding="utf-8") as f:
            content = f.read()
        if "ROUTER_API_KEY=" not in content or "ROUTER_API_KEY=sk-xxxx" in content or "ROUTER_API_KEY=\n" in content:
            needs_config = True
        elif "GROQ_API_KEY=" not in content or "GROQ_API_KEY=gsk_xxxx" in content or "GROQ_API_KEY=\n" in content:
            needs_config = True
            
    if needs_config:
        print("[INFO] Konfigurasi AI LLM atau Groq API Key belum lengkap.")
        print("       Anda dapat menghubungkan dan mengatur AI langsung melalui Web Dashboard Studio (ikon ⚙️ Pengaturan AI).")

def stop_server():
    """Stop the running background server."""
    pid = get_running_pid()
    if pid:
        print(f"[STOP] Menghentikan VisionClipper Studio (PID: {pid})...")
        try:
            if os.name == 'nt':
                subprocess.run(
                    ["taskkill", "/F", "/T", "/PID", str(pid)],
                    capture_output=True, creationflags=0x08000000
                )
            else:
                os.kill(pid, signal.SIGTERM)
                time.sleep(0.5)
                try:
                    os.kill(pid, signal.SIGKILL)
                except OSError:
                    pass
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
    check_and_prompt_ai_config()

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
        print(f"[INFO] Port 5050 sudah dipakai (mungkin instance sebelumnya).")
        print(f"[INFO] Buka di browser: {SERVER_URL}")
        import webbrowser
        webbrowser.open(SERVER_URL)
        return

    print("=======================================================")
    print("         VISION CLIPPER STUDIO — BACKGROUND SERVER")
    print("=======================================================")
    print()

    # Find python executable for windowless/detached execution
    python_dir = os.path.dirname(sys.executable)
    pythonw = os.path.join(python_dir, "pythonw.exe")

    if not os.path.exists(pythonw):
        pythonw = sys.executable

    # The background server script
    server_script = os.path.join(os.path.dirname(os.path.abspath(__file__)), "bg_server.py")

    print(f"[START] Meluncurkan server di background...")
    print(f"[INFO]  PID file: {PID_FILE}")

    # Launch as a fully detached process (survives terminal close)
    popen_kwargs = {
        "close_fds": True,
        "stdout": subprocess.DEVNULL,
        "stderr": subprocess.DEVNULL,
    }
    if os.name == 'nt':
        # DETACHED_PROCESS (0x00000008) + CREATE_NO_WINDOW (0x08000000)
        popen_kwargs["creationflags"] = 0x00000008 | 0x08000000
    else:
        popen_kwargs["start_new_session"] = True

    process = subprocess.Popen(
        [pythonw, server_script],
        **popen_kwargs
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
        print("[ERROR] Server gagal start. Cek apakah port 5050 sudah dipakai.")
        cleanup_pid_file()

def run_install():
    """Run installation and frontend build."""
    project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    if os.name == 'nt':
        script_path = os.path.join(project_root, "scripts", "install.bat")
        if os.path.exists(script_path):
            subprocess.run([script_path], shell=True)
    else:
        script_path = os.path.join(project_root, "scripts", "install_mac.sh")
        if os.path.exists(script_path):
            subprocess.run(["bash", script_path, "install"])

def run_uninstall():
    """Run uninstall cleanup."""
    project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    if os.name == 'nt':
        script_path = os.path.join(project_root, "scripts", "uninstall_windows.bat")
        if os.path.exists(script_path):
            subprocess.run([script_path], shell=True)
    else:
        script_path = os.path.join(project_root, "scripts", "uninstall_mac.sh")
        if os.path.exists(script_path):
            subprocess.run(["bash", script_path])

def run_config():
    """Run interactive configuration wizard."""
    try:
        from backend.config_wizard import run_interactive_config
        project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        run_interactive_config(project_root)
    except Exception as e:
        print(f"[ERROR] Gagal menjalankan wizard konfigurasi: {e}")

def get_status():
    """Display running server status."""
    pid = get_running_pid()
    if pid:
        print(f"[RUNNING] VisionClipper Studio aktif (PID: {pid})")
        print(f"          Dashboard: {SERVER_URL}")
    elif is_server_alive():
        print(f"[RUNNING] Server aktif di {SERVER_URL} (PID file tidak ditemukan)")
    else:
        print("[OFFLINE] Tidak ada server yang sedang berjalan.")

def main():
    parser = argparse.ArgumentParser(
        prog="vision-clipper",
        description="VisionClipper Studio — AI Viral Video Clipper",
        formatter_class=argparse.RawTextHelpFormatter
    )
    subparsers = parser.add_subparsers(dest="command", help="Subcommand yang tersedia")

    subparsers.add_parser("start", help="Jalankan server di background & buka dashboard")
    subparsers.add_parser("stop", help="Hentikan server yang sedang berjalan")
    subparsers.add_parser("status", help="Cek status server")
    subparsers.add_parser("config", help="Atur / ganti API Key, Endpoint, dan Model AI")
    subparsers.add_parser("install", help="Install dependensi & setup environment .venv")
    subparsers.add_parser("uninstall", help="Hapus instalasi tools & bersihkan cache")

    # Compatibility flags
    parser.add_argument("--stop", "-s", action="store_true", help="Hentikan server")
    parser.add_argument("--status", action="store_true", help="Cek status server")
    parser.add_argument("--config", "-c", action="store_true", help="Konfigurasi AI")
    parser.add_argument("--install", action="store_true", help="Instalasi dependensi")
    parser.add_argument("--uninstall", action="store_true", help="Hapus instalasi")

    # Handle bare call or flags
    args = parser.parse_args()

    if args.command == "stop" or args.stop:
        stop_server()
    elif args.command == "status" or args.status:
        get_status()
    elif args.command == "config" or args.config:
        run_config()
    elif args.command == "install" or args.install:
        run_install()
    elif args.command == "uninstall" or args.uninstall:
        run_uninstall()
    elif args.command == "start" or args.command is None:
        start_server()
    else:
        parser.print_help()

if __name__ == "__main__":
    main()
