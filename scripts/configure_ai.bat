@echo off
setlocal enabledelayedexpansion

cd /d "%~dp0\.."

if not exist ".env" (
    if exist ".env.example" copy .env.example .env >nul
)

echo =========================================
echo    🤖 KONFIGURASI AI LLM VISION CLIPPER
echo =========================================
echo Pilih Provider AI yang ingin digunakan:
echo   1) OpenRouter (Rekomendasi - Model Beragam, Opsi Free/Murah)
echo   2) OpenAI Resmi (GPT-4o, GPT-4o-mini)
echo   3) Custom Endpoint (9Router, Groq, Ollama, DeepSeek, dll)
echo.
set /p PROVIDER_CHOICE="Pilihan provider [1-3] (Default: 1): "
if "%PROVIDER_CHOICE%"=="" set PROVIDER_CHOICE=1

if "%PROVIDER_CHOICE%"=="2" (
    set "SELECTED_ENDPOINT=https://api.openai.com/v1/chat/completions"
    set "DEFAULT_MODEL=gpt-4o-mini"
) else if "%PROVIDER_CHOICE%"=="3" (
    set /p "SELECTED_ENDPOINT=Masukkan URL Endpoint: "
    set /p "DEFAULT_MODEL=Masukkan Model Name: "
) else (
    set "SELECTED_ENDPOINT=https://openrouter.ai/api/v1/chat/completions"
    set "DEFAULT_MODEL=google/gemini-2.0-flash-exp:free"
)

echo.
set /p "USER_MODEL=Model AI (Tekan Enter untuk '%DEFAULT_MODEL%'): "
if "%USER_MODEL%"=="" set "USER_MODEL=%DEFAULT_MODEL%"

echo.
set /p "USER_KEY=Masukkan API Key Anda: "

(
echo # VisionClipper Studio Environment Config
echo ROUTER_API_ENDPOINT=%SELECTED_ENDPOINT%
echo ROUTER_API_KEY=%USER_KEY%
echo ROUTER_LLM_MODEL=%USER_MODEL%
) > .env

echo.
echo =========================================
echo   [OK] KONFIGURASI AI BERHASIL DISIMPAN!
echo =========================================
echo Endpoint : %SELECTED_ENDPOINT%
echo Model    : %USER_MODEL%
echo API Key  : Terkonfigurasi aman di .env
echo =========================================
