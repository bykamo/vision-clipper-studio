@echo off
setlocal
cd /d "%~dp0\.."

echo =========================================
echo   VISION CLIPPER STUDIO INSTALLER (Windows)
echo =========================================
echo.

:: 1. Cek Python
where python >nul 2>&1
if %errorlevel% neq 0 (
    echo [ERROR] Python tidak ditemukan. Silakan install Python 3.10+ terlebih dahulu.
    pause
    exit /b 1
)

:: 2. Setup .venv
if not exist ".venv" (
    echo [*] Membuat virtual environment (.venv)...
    python -m venv .venv
)

echo [*] Menginstall dependencies ke .venv...
call .venv\Scripts\activate.bat
python -m pip install --upgrade pip setuptools wheel
pip install -e .

:: 3. Build Frontend jika belum tersedia
if not exist "frontend\dist\index.html" (
    echo [*] Memeriksa npm dan membangun frontend...
    where npm >nul 2>&1
    if %errorlevel% equ 0 (
        cd frontend
        if exist "package-lock.json" (
            call npm ci
        ) else (
            call npm install
        )
        call npm run build
        cd ..
    ) else (
        echo [!] Peringatan: Node.js / npm belum terpasang di sistem.
        echo     Frontend belum dibuild ke frontend\dist.
        echo     Silakan install Node.js (v18+) dan jalankan: cd frontend ^&^& npm install ^&^& npm run build
    )
) else (
    echo [✓] Frontend build (frontend\dist) sudah tersedia.
)

:: 4. Setup AI Config jika belum ada atau belum lengkap
set "NEEDS_CFG=0"
if not exist ".env" set "NEEDS_CFG=1"
if exist ".env" (
    findstr /r /c:"^ROUTER_API_KEY=$" ".env" >nul && set "NEEDS_CFG=1"
    findstr /r /c:"^ROUTER_API_KEY=sk-xxxx" ".env" >nul && set "NEEDS_CFG=1"
    findstr /r /c:"^GROQ_API_KEY=$" ".env" >nul && set "NEEDS_CFG=1"
    findstr /r /c:"^GROQ_API_KEY=gsk_xxxx" ".env" >nul && set "NEEDS_CFG=1"
)

if "%NEEDS_CFG%"=="1" (
    call scripts\configure_ai.bat
)

:: 5. Mendaftarkan Perintah Global Windows ke User PATH
echo [*] Mendaftarkan perintah 'vision-clipper' ke System PATH...
set "TARGET_DIR=%~dp0"
set "TARGET_DIR=%TARGET_DIR:~0,-1%"

powershell -Command "$userPath = [Environment]::GetEnvironmentVariable('Path', 'User'); if ($userPath -notmatch [regex]::Escape('%TARGET_DIR%')) { [Environment]::SetEnvironmentVariable('Path', $userPath + ';%TARGET_DIR%', 'User'); Write-Host '[OK] Added to User PATH!' } else { Write-Host '[OK] Already in User PATH.' }"

echo.
echo =========================================
echo   INSTALLASI SELESAI!
echo =========================================
echo Sekarang Anda bisa membuka CMD/PowerShell baru dan menggunakan:
echo   vision-clipper            -> Jalankan web di background
echo   vision-clipper config     -> Ganti API Key / Model AI
echo   vision-clipper stop       -> Matikan server
echo   vision-clipper status     -> Cek status server
echo   vision-clipper uninstall  -> Hapus instalasi .venv
echo =========================================
pause
