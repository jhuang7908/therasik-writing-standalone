@echo off
REM VHH  (Windows)
REM 

setlocal enabledelayedexpansion

REM 
set "RESULT_JSON=%~1"
set "OUTPUT_DIR=%~2"
set "PROJECT_ID=%~3"

if "%RESULT_JSON%"=="" set "RESULT_JSON=result.json"
if "%OUTPUT_DIR%"=="" set "OUTPUT_DIR=reports\output"
if "%PROJECT_ID%"=="" set "PROJECT_ID="

echo ==========================================
echo VHH 
echo ==========================================
echo : %RESULT_JSON%
echo : %OUTPUT_DIR%
echo ID: %PROJECT_ID%
echo ==========================================
echo.

REM 
if not exist "%RESULT_JSON%" (
    echo ❌ :  %RESULT_JSON%
    exit /b 1
)

REM ID，JSON
if "%PROJECT_ID%"=="" (
    for /f "delims=" %%i in ('python -c "import json; print(json.load(open('"%RESULT_JSON%"')).get('project_id', 'unknown_project'))" 2^>nul') do set "PROJECT_ID=%%i"
    if "%PROJECT_ID%"=="" set "PROJECT_ID=unknown_project"
)

echo 📊  1: ...
python scripts\plot_vhh_report_figures_v1.py --input "%RESULT_JSON%" --output_dir "%OUTPUT_DIR%" --project-id "%PROJECT_ID%"

if %errorlevel% equ 0 (
    echo ✅ 
) else (
    echo ⚠️  ，...
)

echo.
echo 📄  2:  Markdown + DOCX ...
python scripts\generate_vhh_report_v1.py --input "%RESULT_JSON%" --output_dir "%OUTPUT_DIR%" --project-id "%PROJECT_ID%"

if %errorlevel% neq 0 (
    echo ❌ 
    exit /b 1
)

echo ✅ 
echo.
echo ==========================================
echo ✅ ！
echo ==========================================
echo.
echo ：
echo   📄 Markdown: %OUTPUT_DIR%\%PROJECT_ID%\report_v1.md
echo   📄 DOCX:     %OUTPUT_DIR%\%PROJECT_ID%\report_v1.docx
echo   📊 :     %OUTPUT_DIR%\%PROJECT_ID%\figures\*.png
echo.
echo  / PI /  / ""。
echo ==========================================

endlocal

















