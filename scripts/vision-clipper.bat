@echo off
setlocal enabledelayedexpansion
set "PROJECT_DIR=%~dp0\.."
cd /d "%PROJECT_DIR%"

if "%1"=="install" (
    call "%PROJECT_DIR%\scripts\install.bat"
    exit /b 0
)

if "%1"=="config" (
    call "%PROJECT_DIR%\scripts\configure_ai.bat"
    exit /b 0
)

if "%1"=="uninstall" (
    call "%PROJECT_DIR%\scripts\uninstall_windows.bat"
    exit /b 0
)

if "%1"=="help" (
    echo VisionClipper Studio — AI Viral Video Clipper
    echo.
    echo Usage:
    echo   vision-clipper            Jalankan server di background ^& buka dashboard
    echo   vision-clipper install    Install dependensi ^& setup environment .venv
    echo   vision-clipper config     Atur / ganti API Key, Endpoint, dan Model AI
    echo   vision-clipper stop       Hentikan server yang sedang berjalan
    echo   vision-clipper status     Cek status server
    echo   vision-clipper uninstall  Hapus instalasi tools ^& bersihkan cache
    echo   vision-clipper help       Tampilkan bantuan ini
    exit /b 0
)

:: Auto create .venv jika belum ada
if not exist ".venv" (
    echo [!] Virtual environment belum terpasang.
    call "%PROJECT_DIR%\scripts\install.bat"
)

:: Auto prompt config jika .env belum ada
if not exist ".env" (
    call "%PROJECT_DIR%\scripts\configure_ai.bat"
)

:: Jalankan backend CLI lewat .venv python
if exist ".venv\Scripts\python.exe" (
    call ".venv\Scripts\activate.bat"
    python -m backend.cli %*
) else (
    python -m backend.cli %*
)

