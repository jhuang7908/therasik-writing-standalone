@echo off
title InSynBio Console Stop
cd /d D:\InSynBio-AI-Research\Antibody_Engineer_Suite

echo.
echo  [*] Stopping InSynBio console services (ports 8000 / 8001)...
for /f "tokens=5" %%a in ('netstat -ano ^| findstr ":8000 :8001" ^| findstr "LISTENING"') do (
    echo  [+] Killing PID %%a
    taskkill /F /PID %%a >nul 2>&1
)

echo  [*] Stopping ngrok tunnel (if running)...
taskkill /F /IM ngrok.exe >nul 2>&1

echo.
echo  [OK] Console services stopped.
echo.
