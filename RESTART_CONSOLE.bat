@echo off
title InSynBio Console Restart
cd /d D:\InSynBio-AI-Research\Antibody_Engineer_Suite

echo.
echo  [1/2] Stopping existing console services...
call STOP_CONSOLE.bat
timeout /t 2 /nobreak >nul

echo  [2/2] Starting console services...
call START_CONSOLE.bat
