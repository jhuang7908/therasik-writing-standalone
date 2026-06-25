@echo off
title Stop Local API :8000 / :8001
cd /d D:\InSynBio-AI-Research\Antibody_Engineer_Suite

echo.
echo  [*] Stopping processes listening on ports 8000 and 8001...
for /f "tokens=5" %%a in ('netstat -ano ^| findstr ":8000" ^| findstr "LISTENING"') do (
    echo  [+] Killing PID %%a ^(8000^)
    taskkill /F /PID %%a >nul 2>&1
)
for /f "tokens=5" %%a in ('netstat -ano ^| findstr ":8001" ^| findstr "LISTENING"') do (
    echo  [+] Killing PID %%a ^(8001^)
    taskkill /F /PID %%a >nul 2>&1
)

echo.
echo  [OK] Ports 8000 and 8001 cleared.
echo  Note: ngrok is not stopped. Use STOP_CONSOLE.bat if you need to kill ngrok too.
echo.
pause
