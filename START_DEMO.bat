@echo off
title InSynBio AbEngineCore Demo Server
set KMP_DUPLICATE_LIB_OK=TRUE
cd /d D:\InSynBio-AI-Research\Antibody_Engineer_Suite
call d:\Users\NextVivo\miniconda3\Scripts\activate.bat anarcii
echo.
echo  ===================================================
echo   InSynBio AbEngineCore Demo
echo   Open browser: http://localhost:8000
echo   Structure computation takes ~60s (ABodyBuilder2)
echo  ===================================================
echo.
python -m uvicorn api.main:app --host 0.0.0.0 --port 8000 --reload
