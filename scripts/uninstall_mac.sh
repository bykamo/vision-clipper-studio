#!/bin/bash

# Pindah ke root folder project
PROJECT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$PROJECT_DIR"

echo "========================================="
echo "  VISION CLIPPER STUDIO UNINSTALLER (macOS)"
echo "========================================="
echo ""
echo "Script ini akan menghapus:"
echo "  [x] Virtual Environment (.venv)"
echo "  [x] Shortcut perintah 'vision-clipper' di ~/.local/bin"
echo "  [x] File build & cache Python (.egg-info, __pycache__)"
echo "  [x] File logs dan temporary cache (temp/, server.log)"
echo ""
echo "Catatan: Python & FFmpeg sistem TIDAK AKAN disentuh."
echo "========================================="
read -p "Apakah Anda yakin ingin menghapus instalasi tools ini? (y/N): " CONFIRM

if [[ "$CONFIRM" != "y" && "$CONFIRM" != "Y" ]]; then
    echo "[!] Uninstal dibatalkan."
    exit 0
fi

echo ""
# 1. Hentikan server jika masih berjalan
echo "[1/5] Memastikan server VisionClipper dimatikan..."
PID_FILE="$HOME/.visionclipper.pid"
if [ -f "$PID_FILE" ]; then
    PID=$(cat "$PID_FILE")
    if kill -0 "$PID" 2>/dev/null; then
        kill -9 "$PID" 2>/dev/null || true
    fi
    rm -f "$PID_FILE"
fi

# Pastikan port 5050 bersih
PIDS=$(lsof -ti :5050 2>/dev/null || true)
if [ -n "$PIDS" ]; then
    kill -9 $PIDS 2>/dev/null || true
fi

# 2. Hapus Shortcut CLI di ~/.local/bin
echo "[2/5] Menghapus perintah 'vision-clipper' dari ~/.local/bin..."
LAUNCHER="$HOME/.local/bin/vision-clipper"
if [ -f "$LAUNCHER" ]; then
    rm -f "$LAUNCHER"
    echo "      ✓ Perintah 'vision-clipper' berhasil dihapus."
fi

# 3. Hapus Virtual Environment (.venv)
echo "[3/5] Menghapus virtual environment (.venv)..."
if [ -d ".venv" ]; then
    rm -rf .venv
    echo "      ✓ Folder .venv berhasil dihapus (space terbebaskan)."
fi

# 4. Hapus Build Artifacts & Cache Python
echo "[4/5] Membersihkan cache Python dan package build..."
rm -rf *.egg-info build dist .pytest_cache
find . -type d -name "__pycache__" -exec rm -rf {} + 2>/dev/null || true
find . -type f -name "*.pyc" -delete 2>/dev/null || true
echo "      ✓ Cache & metadata build dibersihkan."

# 5. Hapus file log & folder temp
echo "[5/5] Membersihkan log & file sementara..."
rm -f server.log server_error.log
rm -rf temp/* 2>/dev/null || true

echo ""
echo "========================================="
echo "      UNINSTALL SELESAI BERSIH! 🎉"
echo "========================================="
echo "• Semua library dan instalasi tools telah dihapus."
echo "• File source code, konfigurasi .env, dan folder output video (clips/) tetap dipertahankan."
echo "========================================="
