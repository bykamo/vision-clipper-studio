#!/bin/bash
set -e

# Pindah ke root folder project
PROJECT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$PROJECT_DIR"

if [ -f ".venv/bin/python" ]; then
    .venv/bin/python -m backend.config_wizard
elif command -v python3 &>/dev/null; then
    python3 -m backend.config_wizard
else
    echo "[ERROR] Python tidak ditemukan."
    exit 1
fi
echo "Model    : $USER_MODEL"
echo "API Key  : Terkonfigurasi aman di .env"
echo "========================================="
