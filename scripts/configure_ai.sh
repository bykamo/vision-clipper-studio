#!/bin/bash

# Pindah ke root folder project
PROJECT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$PROJECT_DIR"

if [ ! -f ".env" ] && [ -f ".env.example" ]; then
    cp .env.example .env
fi

CURRENT_ENDPOINT=$(grep "^ROUTER_API_ENDPOINT=" .env 2>/dev/null | cut -d '=' -f2-)
CURRENT_KEY=$(grep "^ROUTER_API_KEY=" .env 2>/dev/null | cut -d '=' -f2-)
CURRENT_MODEL=$(grep "^ROUTER_LLM_MODEL=" .env 2>/dev/null | cut -d '=' -f2-)
CURRENT_GROQ_KEY=$(grep "^GROQ_API_KEY=" .env 2>/dev/null | cut -d '=' -f2-)

echo "========================================="
echo "   🤖 KONFIGURASI AI LLM VISION CLIPPER"
echo "========================================="
echo "Pilih Provider AI yang ingin digunakan:"
echo "  1) OpenRouter (Rekomendasi - Model Beragam, Banyak Opsi Free/Murah)"
echo "  2) OpenAI Resmi (GPT-4o, GPT-4o-mini)"
echo "  3) Custom Endpoint (9Router, Groq, Ollama, DeepSeek, dll)"
echo ""
read -p "Pilihan provider [1-3] (Default: 1): " PROVIDER_CHOICE
PROVIDER_CHOICE=${PROVIDER_CHOICE:-1}

case "$PROVIDER_CHOICE" in
    2)
        SELECTED_ENDPOINT="https://api.openai.com/v1/chat/completions"
        DEFAULT_MODEL="gpt-4o-mini"
        ;;
    3)
        read -p "Masukkan URL Endpoint (cth: https://api.groq.com/openai/v1/chat/completions): " USER_ENDPOINT
        SELECTED_ENDPOINT=${USER_ENDPOINT:-$CURRENT_ENDPOINT}
        DEFAULT_MODEL=${CURRENT_MODEL:-"llama-3.3-70b-versatile"}
        ;;
    *)
        SELECTED_ENDPOINT="https://openrouter.ai/api/v1/chat/completions"
        DEFAULT_MODEL="google/gemini-2.0-flash-exp:free"
        ;;
esac

echo ""
echo "Model AI default untuk provider ini: $DEFAULT_MODEL"
read -p "Gunakan model ini atau ketik model lain (Enter untuk '$DEFAULT_MODEL'): " USER_MODEL
USER_MODEL=${USER_MODEL:-$DEFAULT_MODEL}

echo ""
if [ -n "$CURRENT_KEY" ] && [[ "$CURRENT_KEY" != "sk-xxxx"* ]]; then
    MASKED_KEY="${CURRENT_KEY:0:6}...${CURRENT_KEY: -4}"
    echo "LLM API Key saat ini: $MASKED_KEY"
    read -p "Masukkan LLM API Key baru (atau Enter untuk tetap gunakan yang lama): " USER_KEY
    USER_KEY=${USER_KEY:-$CURRENT_KEY}
else
    read -p "Masukkan LLM API Key Anda: " USER_KEY
fi

echo ""
echo "-----------------------------------------"
echo "  🎙️ GROQ CLOUD WHISPER (Transkripsi Super Cepat ~3 detik)"
echo "  Gratis tanpa kartu kredit di: https://console.groq.com"
echo "-----------------------------------------"
if [ -n "$CURRENT_GROQ_KEY" ] && [[ "$CURRENT_GROQ_KEY" != "gsk_xxxx"* ]]; then
    MASKED_GROQ="${CURRENT_GROQ_KEY:0:6}...${CURRENT_GROQ_KEY: -4}"
    echo "Groq API Key saat ini: $MASKED_GROQ"
    read -p "Masukkan Groq API Key baru (Enter untuk tetap gunakan yang lama): " USER_GROQ_KEY
    USER_GROQ_KEY=${USER_GROQ_KEY:-$CURRENT_GROQ_KEY}
else
    read -p "Masukkan Groq API Key (opsional/bisa diisi nanti): " USER_GROQ_KEY
fi

# Tulis konfigurasi ke file .env
cat << ENV_EOF > .env
# VisionClipper Studio Environment Config
ROUTER_API_ENDPOINT=$SELECTED_ENDPOINT
ROUTER_API_KEY=$USER_KEY
ROUTER_LLM_MODEL=$USER_MODEL
GROQ_API_KEY=$USER_GROQ_KEY
ENV_EOF

echo ""
echo "========================================="
echo "  ✓ KONFIGURASI AI BERHASIL DISIMPAN!"
echo "========================================="
echo "Endpoint : $SELECTED_ENDPOINT"
echo "Model    : $USER_MODEL"
echo "API Key  : Terkonfigurasi aman di .env"
echo "========================================="
