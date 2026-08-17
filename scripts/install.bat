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

:: 3. Setup AI Config jika belum ada
if not exist ".env" (
    call scripts\configure_ai.bat
)

:: 4. Mendaftarkan Perintah Global Windows ke User PATH
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
