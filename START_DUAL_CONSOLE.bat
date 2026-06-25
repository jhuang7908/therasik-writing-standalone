@echo off
title InSynBio Dual-Environment Launcher
cd /d D:\InSynBio-AI-Research\Antibody_Engineer_Suite

echo.
echo  ===================================================
echo   InSynBio Dual-Environment Management
echo   [DEV]  Port 8000 - Internal (Current Folder)
echo   [LIVE] Port 8001 - External (PROD Folder)
echo  ===================================================
echo.

:: Ensure PROD folder exists (if first run)
if not exist "D:\InSynBio-AI-Research\Antibody_Engineer_Suite_PROD" (
    echo  [!] PROD folder not found. Running initial sync...
    powershell -ExecutionPolicy Bypass -File .\UPGRADE_LIVE_SYSTEM.ps1
)

echo  [*] Cleaning up ports 8000 and 8001...
for /f "tokens=5" %%a in ('netstat -ano ^| findstr ":8000 :8001" ^| findstr "LISTENING"') do (
    taskkill /F /PID %%a >nul 2>&1
)
timeout /t 2 /nobreak >nul

echo  [1] Starting INTERNAL DEV API (Port 8000)...
start "DEV API (8000)" /D "D:\InSynBio-AI-Research\Antibody_Engineer_Suite" cmd /k "call d:\Users\NextVivo\miniconda3\Scripts\activate.bat anarcii && set KMP_DUPLICATE_LIB_OK=TRUE && python -m uvicorn api.main:app --host 127.0.0.1 --port 8000 --reload"

echo  [2] Starting EXTERNAL LIVE API (Port 8001)...
:: 注意：这里运行的是 PROD 文件夹里的代码
start "LIVE API (8001)" /D "D:\InSynBio-AI-Research\Antibody_Engineer_Suite_PROD" cmd /k "call d:\Users\NextVivo\miniconda3\Scripts\activate.bat anarcii && set KMP_DUPLICATE_LIB_OK=TRUE && python -m uvicorn api.main:app --host 0.0.0.0 --port 8001 --workers 1"

echo  [*] Waiting 8s for services to warm up...
timeout /t 8 /nobreak >nul

echo  [3] Starting External Tunnel (Pointing to 8001)...
start "LIVE TUNNEL (8001)" cmd /k "ngrok http --domain=noncensurably-proconsolidation-clorinda.ngrok-free.dev 8001"

echo.
echo  ===================================================
echo   ALL SYSTEMS GO
echo.
echo   INTERNAL DEV: http://localhost:8000
echo   EXTERNAL LIVE: https://noncensurably-proconsolidation-clorinda.ngrok-free.dev
echo.
echo   To promote DEV changes to LIVE, run:
echo   powershell -File .\UPGRADE_LIVE_SYSTEM.ps1
echo  ===================================================
echo.
pause
