#!/bin/bash
set -e

# Linux / VPS installer. Mirrors install_mac.sh but uses apt instead of Homebrew,
# installs the CPU-only torch wheel (saves ~2 GB and avoids CUDA dependency),
# and never tries to open a browser.
#
# Usage:
#   bash scripts/install_linux.sh            # full install
#   bash scripts/install_linux.sh --no-apt   # skip apt (deps already present)

PROJECT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$PROJECT_DIR"

SKIP_APT=false
for arg in "$@"; do
    case "$arg" in
        --no-apt) SKIP_APT=true ;;
    esac
done

echo "========================================="
echo "  VISION CLIPPER STUDIO INSTALLER (Linux)"
echo "========================================="
echo ""

# ── 1. System packages ────────────────────────────────────────────────────────
# libgl1 + libglib2.0-0 are required at import time by opencv-python-headless
# (see .github/workflows/ci.yml). fontconfig is needed so libass can find the
# subtitle fonts listed below.
if [ "$SKIP_APT" = false ]; then
    if ! command -v apt-get >/dev/null 2>&1; then
        echo "[!] apt-get tidak ditemukan. Lewati instalasi paket sistem."
        echo "    Pastikan ffmpeg, python3-venv, libgl1 dan libglib2.0-0 sudah terpasang manual."
    else
        echo "[*] Menginstall paket sistem (ffmpeg, libGL, fontconfig)..."
        SUDO=""
        if [ "$(id -u)" -ne 0 ]; then
            SUDO="sudo"
        fi
        $SUDO apt-get update
        $SUDO apt-get install -y --no-install-recommends \
            ffmpeg \
            python3 python3-venv python3-pip \
            libgl1 libglib2.0-0 \
            fontconfig \
            curl ca-certificates
    fi
else
    echo "[*] Melewati apt (--no-apt)."
fi

# ── 2. Verify prerequisites ───────────────────────────────────────────────────
if ! command -v ffmpeg >/dev/null 2>&1; then
    echo "[ERROR] FFmpeg tidak ditemukan. Install dulu: sudo apt install ffmpeg"
    exit 1
fi
echo "[✓] FFmpeg tersedia."

if ! command -v python3 >/dev/null 2>&1; then
    echo "[ERROR] Python 3 belum terpasang. Install: sudo apt install python3 python3-venv"
    exit 1
fi
echo "[✓] Python 3 tersedia."

# ── 3. Virtual environment ────────────────────────────────────────────────────
if [ ! -d ".venv" ]; then
    echo "[*] Membuat virtual environment (.venv)..."
    python3 -m venv .venv
fi

# shellcheck disable=SC1091
source .venv/bin/activate
echo "[*] Menginstall dependencies Python..."
pip install --upgrade pip setuptools wheel

# CPU-only torch FIRST, so `pip install -e .` (which pulls ultralytics -> torch)
# does not download the multi-GB CUDA build on a GPU-less VPS.
if ! python -c "import torch" >/dev/null 2>&1; then
    echo "[*] Menginstall PyTorch CPU-only (hemat ~2 GB dibanding wheel CUDA)..."
    pip install torch torchvision --index-url https://download.pytorch.org/whl/cpu
else
    echo "[✓] PyTorch sudah terpasang."
fi

pip install -e .

# ── 4. Frontend build ─────────────────────────────────────────────────────────
# backend/main.py serves frontend/dist, so this step is mandatory.
if [ ! -d "frontend/dist" ] || [ ! -f "frontend/dist/index.html" ]; then
    echo "[*] Memeriksa instalasi Node.js & membangun frontend..."
    if command -v npm >/dev/null 2>&1; then
        echo "[*] Menjalankan build frontend (npm ci && npm run build)..."
        (cd frontend && if [ -f "package-lock.json" ]; then npm ci; else npm install; fi && npm run build)
    else
        echo "[!] Peringatan: npm / Node.js tidak ditemukan."
        echo "    Dashboard TIDAK akan tampil tanpa frontend/dist."
        echo "    Pasang Node.js 18+ lalu jalankan: cd frontend && npm install && npm run build"
    fi
else
    echo "[✓] Frontend build (frontend/dist) sudah tersedia."
fi

# ── 5. Subtitle fonts (optional, recommended) ─────────────────────────────────
# ASS styles request "Plus Jakarta Sans", "Montserrat" and "Impact". Without
# them libass silently falls back to DejaVu and the rendered subtitles look
# different from the local preview.
FONT_DIR="$HOME/.local/share/fonts"
mkdir -p "$FONT_DIR"
if [ -d "backend/fonts" ] && [ -n "$(ls -A backend/fonts 2>/dev/null)" ]; then
    cp -n backend/fonts/*.ttf "$FONT_DIR/" 2>/dev/null || true
fi
if command -v fc-cache >/dev/null 2>&1; then
    fc-cache -f >/dev/null 2>&1 || true
fi
if command -v fc-match >/dev/null 2>&1; then
    for family in "Plus Jakarta Sans" "Montserrat" "Impact"; do
        if fc-match "$family" 2>/dev/null | grep -qi "$family"; then
            echo "[✓] Font subtitle tersedia: $family"
        else
            echo "[!] Font '$family' tidak ditemukan — subtitle akan memakai fallback DejaVu."
            echo "    Copy file .ttf ke $FONT_DIR lalu jalankan: fc-cache -f"
        fi
    done
fi

# ── 6. AI config ──────────────────────────────────────────────────────────────
needs_config=false
if [ ! -f ".env" ]; then
    needs_config=true
elif ! grep -q "^ROUTER_API_KEY=" .env 2>/dev/null || grep -q "^ROUTER_API_KEY=sk-xxxx" .env 2>/dev/null || grep -q "^ROUTER_API_KEY=$" .env 2>/dev/null; then
    needs_config=true
elif ! grep -q "^GROQ_API_KEY=" .env 2>/dev/null || grep -q "^GROQ_API_KEY=gsk_xxxx" .env 2>/dev/null || grep -q "^GROQ_API_KEY=$" .env 2>/dev/null; then
    needs_config=true
fi

if [ "$needs_config" = true ]; then
    if [ -f "scripts/configure_ai.sh" ]; then
        chmod +x scripts/configure_ai.sh
        echo ""
        echo "[*] Mengatur konfigurasi AI & Groq API..."
        bash scripts/configure_ai.sh || true
    else
        echo "[!] scripts/configure_ai.sh tidak ditemukan."
        echo "    Buat .env manual dari .env.example lalu isi ROUTER_API_KEY dan GROQ_API_KEY."
    fi
fi

# ── 7. YouTube cookies hint ───────────────────────────────────────────────────
if [ ! -f "cookies.txt" ]; then
    echo ""
    echo "[!] cookies.txt belum ada. Unduhan YouTube dari IP datacenter sering"
    echo "    diblokir dengan 'Sign in to confirm you're not a bot'."
    echo "    Export cookies (format Netscape) ke $PROJECT_DIR/cookies.txt"
fi

# ── 8. systemd unit hint ──────────────────────────────────────────────────────
echo ""
echo "========================================="
echo "[SUCCESS] Instalasi selesai."
echo ""
echo "Jalankan manual:"
echo "  .venv/bin/python -m backend.main"
echo ""
echo "Atau sebagai service (auto-start):"
echo "  sudo cp deploy/visionclipper.service /etc/systemd/system/"
echo "  sudo systemctl daemon-reload"
echo "  sudo systemctl enable --now visionclipper"
echo ""
echo "Akses dari komputer lokal (paling aman, tanpa buka port):"
echo "  ssh -L 5050:127.0.0.1:5050 $(whoami)@\$(hostname -I | awk '{print \$1}')"
echo "  lalu buka http://localhost:5050"
echo "========================================="
