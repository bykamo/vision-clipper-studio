@echo off
setlocal
cd /d "%~dp0\.."

echo =========================================
echo   VISION CLIPPER UNINSTALLER (Windows)
echo =========================================
echo.
echo Script ini akan menghapus:
echo   [x] Virtual Environment (.venv)
echo   [x] Cache build Python (__pycache__, *.egg-info)
echo   [x] File logs dan temporary cache
echo.
echo Catatan: File hasil video di folder clips/ TIDAK AKAN dihapus.
echo =========================================
set /p CONFIRM="Apakah Anda yakin ingin menghapus instalasi? (y/N): "
if /i not "%CONFIRM%"=="y" (
    echo [!] Uninstal dibatalkan.
    exit /b 0
)

echo.
echo [1/4] Mematikan server jika masih jalan...
set "PID_FILE=%USERPROFILE%\.visionclipper.pid"
if exist "%PID_FILE%" (
    set /p VC_PID=<"%PID_FILE%"
    if defined VC_PID (
        taskkill /F /PID %VC_PID% >nul 2>&1
    )
    del /f /q "%PID_FILE%" >nul 2>&1
)

echo [2/4] Menghapus virtual environment (.venv)...
if exist ".venv" rmdir /s /q ".venv"

echo [3/4] Membersihkan cache Python...
for /d /r . %%d in (__pycache__) do @if exist "%%d" rd /s /q "%%d" >nul 2>&1
for /d /r . %%d in (*.egg-info) do @if exist "%%d" rd /s /q "%%d" >nul 2>&1

echo [4/4] Membersihkan log & temp...
if exist "server.log" del /f /q server.log
if exist "server_error.log" del /f /q server_error.log
if exist "temp" (
    del /f /q temp\* >nul 2>&1
)

echo.
echo =========================================
echo       UNINSTALL SELESAI BERSIH!
echo =========================================
