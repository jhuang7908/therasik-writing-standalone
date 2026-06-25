@echo off
title InSynBio Console Launcher
cd /d D:\InSynBio-AI-Research\Antibody_Engineer_Suite

echo.
echo  [*] Cleaning up port 8001...
for /f "tokens=5" %%a in ('netstat -ano ^| findstr ":8001" ^| findstr "LISTENING"') do (
    taskkill /F /PID %%a >nul 2>&1
)

echo  [1] Starting local API...
start "InSynBio API" /D "D:\InSynBio-AI-Research\Antibody_Engineer_Suite" cmd /c "call d:\Users\NextVivo\miniconda3\Scripts\activate.bat anarcii && set KMP_DUPLICATE_LIB_OK=TRUE && python -m uvicorn api.main:app --host 127.0.0.1 --port 8001 --reload"

echo  [*] Waiting for API...
timeout /t 5 /nobreak >nul

echo  [2] Starting Tunnel...
start "InSynBio Tunnel" cmd /c "ngrok http 8001"

echo.
echo  DONE. Please check the ngrok window for the new URL.
echo.
pause
