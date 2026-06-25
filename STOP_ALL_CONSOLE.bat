 @echo off
title InSynBio Console Stopper
echo.
echo  [*] Stopping all InSynBio Console processes...
echo.

:: 杀掉占用 8000 和 8001 端口的进程
for /f "tokens=5" %%a in ('netstat -ano ^| findstr ":8000 :8001" ^| findstr "LISTENING"') do (
    echo  [+] Killing process on PID %%a...
    taskkill /F /PID %%a >nul 2>&1
)

:: 杀掉 ngrok 进程
taskkill /F /IM ngrok.exe >nul 2>&1

:: 杀掉 python 进程 (慎用，如果还有其他 python 程序在跑)
:: taskkill /F /IM python.exe >nul 2>&1

echo.
echo  [OK] All console services stopped.
echo.
timeout /t 3
