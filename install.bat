@echo off
echo =========================================
echo   VISION CLIPPER STUDIO INSTALLER
echo =========================================
echo.
echo Installing dependencies and CLI tool...
pip install -e .

echo.
echo Configuring System PATH...
for /f "delims=" %%i in ('python -c "import sysconfig, os; print(sysconfig.get_path('scripts', f'{os.name}_user'))"') do set SCRIPTS_DIR=%%i

echo Python Scripts directory: %SCRIPTS_DIR%

powershell -Command "$userPath = [Environment]::GetEnvironmentVariable('Path', 'User'); $target = '%SCRIPTS_DIR%'; if ($userPath -notmatch [regex]::Escape($target)) { [Environment]::SetEnvironmentVariable('Path', $userPath + ';' + $target, 'User'); Write-Host 'Added to User PATH successfully!' } else { Write-Host 'Already in User PATH.' }"

echo.
echo =========================================
echo INSTALLATION COMPLETE!
echo. 
echo PENTING:
echo Tutup terminal ini, lalu buka terminal/CMD BARU.
echo Setelah itu lo bisa bebas ketik: visionclipper
echo =========================================
pause
