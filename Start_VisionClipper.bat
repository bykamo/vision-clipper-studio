@echo off
title VisionClipper Studio Server
color 0B

echo =======================================================
echo          VISION CLIPPER STUDIO SERVER STARTER
echo =======================================================
echo.
echo Starting the AI Engine in the background...

:: Jalankan Flask di latar belakang tanpa memblokir terminal
start "" pythonw app.py

echo Server is now running silently!
echo Opening Web Dashboard in your default browser...

:: Beri waktu 2 detik agar server Flask sempat booting
timeout /t 2 /nobreak > NUL

:: Buka browser otomatis
start http://localhost:5000

echo.
echo =======================================================
echo [SUCCESS] You can now safely close this black window. 
echo The AI Server will continue running in the background.
echo To completely turn it off, click the red "Shut Down"
echo button at the bottom of the Web Dashboard.
echo =======================================================
timeout /t 5 > NUL
exit
