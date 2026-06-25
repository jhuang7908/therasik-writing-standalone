@echo off
title InSynBio Local API :8000
cd /d D:\InSynBio-AI-Research\Antibody_Engineer_Suite

echo.
echo  [*] Freeing port 8000 if busy...
for /f "tokens=5" %%a in ('netstat -ano ^| findstr ":8000" ^| findstr "LISTENING"') do (
    taskkill /F /PID %%a >nul 2>&1
)

echo  [1] Starting local API on http://127.0.0.1:8000/  (no tunnel, no 8001)
start "InSynBio API :8000" /D "D:\InSynBio-AI-Research\Antibody_Engineer_Suite" cmd /k "call d:\Users\NextVivo\miniconda3\Scripts\activate.bat anarcii && set KMP_DUPLICATE_LIB_OK=TRUE && python -m uvicorn api.main:app --host 127.0.0.1 --port 8000 --reload"

echo.
echo  [OK] API window opened. Open console: http://localhost:8000/
echo  To stop: run STOP_LOCAL_API_PORTS.bat
echo.
pause
