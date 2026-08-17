#!/bin/bash
set -e

# Pindah ke root folder project
PROJECT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$PROJECT_DIR"

echo "========================================="
echo "   VISION CLIPPER STUDIO INSTALLER (macOS)"
echo "========================================="
echo ""

# 1. Cek FFmpeg
if ! command -v ffmpeg &> /dev/null; then
    echo "[!] FFmpeg tidak ditemukan. Menginstall via Homebrew..."
    if ! command -v brew &> /dev/null; then
        echo "[ERROR] Homebrew belum terpasang. Pasang dulu dari: https://brew.sh"
        exit 1
    fi
    brew install ffmpeg
else
    echo "[✓] FFmpeg sudah terpasang."
fi

# 2. Cek Python3
if ! command -v python3 &> /dev/null; then
    echo "[ERROR] Python 3 belum terpasang. Install via: brew install python@3.11"
    exit 1
fi

# 3. Setup Virtual Environment
if [ ! -d ".venv" ]; then
    echo "[*] Membuat virtual environment (.venv)..."
    python3 -m venv .venv
fi

echo "[*] Mengaktifkan .venv dan menginstall dependencies..."
source .venv/bin/activate
pip install --upgrade pip setuptools wheel
pip install -e .

# 4. Buat file .env jika belum ada
if [ ! -f ".env" ]; then
    if [ -f ".env.example" ]; then
        cp .env.example .env
        echo "[*] Dibuat file .env dari .env.example. Jangan lupa isi API Key Anda!"
    fi
fi

# 5. Buat Global Launcher di ~/.local/bin
echo "[*] Mendaftarkan perintah 'vision-clipper'..."
BIN_DIR="$HOME/.local/bin"
mkdir -p "$BIN_DIR"

LAUNCHER="$BIN_DIR/vision-clipper"
cat << 'EOF' > "$LAUNCHER"
#!/bin/bash
PROJECT_DIR="TARGET_PROJECT_DIR"
PID_FILE="$HOME/.visionclipper.pid"
PORT=5000

is_running() {
    lsof -i :$PORT >/dev/null 2>&1
}

case "$1" in
    install|--install)
        echo "[*] Menjalankan instalasi/setup VisionClipper Studio..."
        if [ -f "$PROJECT_DIR/scripts/install_mac.sh" ]; then
            bash "$PROJECT_DIR/scripts/install_mac.sh"
        else
            echo "[ERROR] File install_mac.sh tidak ditemukan di $PROJECT_DIR/scripts/"
        fi
        ;;
    stop|--stop|-s)
        echo "[STOP] Menghentikan VisionClipper Studio..."
        if [ -f "$PID_FILE" ]; then
            PID=$(cat "$PID_FILE")
            if kill -0 "$PID" 2>/dev/null; then
                kill "$PID" 2>/dev/null || true
            fi
            rm -f "$PID_FILE"
        fi
        # Kill process listening on port 5000 jika masih ada
        PIDS=$(lsof -ti :$PORT 2>/dev/null || true)
        if [ -n "$PIDS" ]; then
            kill -9 $PIDS 2>/dev/null || true
        fi
        echo "[DONE] VisionClipper berhasil dihentikan."
        ;;
    status|--status)
        if is_running; then
            echo "[RUNNING] VisionClipper Studio aktif di http://localhost:$PORT"
        else
            echo "[OFFLINE] Tidak ada VisionClipper Studio yang berjalan."
        fi
        ;;
    uninstall|--uninstall)
        if [ -f "$PROJECT_DIR/scripts/uninstall_mac.sh" ]; then
            bash "$PROJECT_DIR/scripts/uninstall_mac.sh"
        else
            echo "[ERROR] File uninstall_mac.sh tidak ditemukan di $PROJECT_DIR/scripts/"
        fi
        ;;
    help|--help|-h)
        echo "VisionClipper Studio — AI Viral Video Clipper"
        echo ""
        echo "Usage:"
        echo "  vision-clipper            Jalankan server di background & buka dashboard"
        echo "  vision-clipper install    Install dependensi & setup environment .venv"
        echo "  vision-clipper stop       Hentikan server yang sedang berjalan"
        echo "  vision-clipper status     Cek status server"
        echo "  vision-clipper uninstall  Hapus instalasi tools & bersihkan cache"
        echo "  vision-clipper help       Tampilkan bantuan ini"
        ;;
    *)
        # Cek jika .venv belum ada, buat otomatis
        if [ ! -d "$PROJECT_DIR/.venv" ]; then
            echo "[!] Virtual environment (.venv) belum terpasang."
            echo "[*] Menjalankan instalasi otomatis..."
            bash "$PROJECT_DIR/scripts/install_mac.sh"
        fi

        if is_running; then
            echo "[INFO] VisionClipper Studio sudah berjalan di http://localhost:$PORT"
            open "http://localhost:$PORT"
            exit 0
        fi

        echo "[START] Menjalankan VisionClipper Studio di background..."
        cd "$PROJECT_DIR"
        source .venv/bin/activate
        
        # Jalankan background server
        nohup python -m backend.bg_server > server.log 2>&1 &
        SERVER_PID=$!
        echo $SERVER_PID > "$PID_FILE"

        echo -n "[WAIT] Menunggu server siap..."
        for i in {1..15}; do
            if is_running; then
                break
            fi
            sleep 1
            echo -n "."
        done
        echo ""

        if is_running; then
            echo "======================================================="
            echo "[SUCCESS] VisionClipper Studio berjalan!"
            echo "          Dashboard: http://localhost:$PORT"
            echo "          Untuk Stop: vision-clipper stop"
            echo "======================================================="
            open "http://localhost:$PORT"
        else
            echo "[ERROR] Gagal menjalankan server. Cek log di $PROJECT_DIR/server.log atau server_error.log"
            rm -f "$PID_FILE"
        fi
        ;;
esac
EOF

# Ganti placeholder direktori
sed -i '' "s|TARGET_PROJECT_DIR|$PROJECT_DIR|g" "$LAUNCHER"
chmod +x "$LAUNCHER"

# Pastikan ~/.local/bin ada di PATH shell profile
SHELL_CONFIG="$HOME/.zshrc"
if [ "$SHELL" = "*/bash" ]; then
    SHELL_CONFIG="$HOME/.bash_profile"
fi

if [[ ":$PATH:" != *":$BIN_DIR:"* ]]; then
    if ! grep -q 'export PATH="$HOME/.local/bin:$PATH"' "$SHELL_CONFIG" 2>/dev/null; then
        echo 'export PATH="$HOME/.local/bin:$PATH"' >> "$SHELL_CONFIG"
        echo "[*] PATH ~/.local/bin ditambahkan ke $SHELL_CONFIG"
    fi
fi

echo ""
echo "========================================="
echo "   INSTALLASI SELESAI!"
echo "========================================="
echo "Silakan jalankan perintah:"
echo "  source $SHELL_CONFIG"
echo ""
echo "Setelah itu Anda bisa menggunakan:"
echo "  vision-clipper        -> Menjalankan tools & buka web"
echo "  vision-clipper stop   -> Mematikan tools & proses"
echo "  vision-clipper status -> Cek status server"
echo "========================================="
