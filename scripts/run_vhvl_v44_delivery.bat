@echo off
REM VH/VL V4.4  + PDF + （Windows）
REM :
REM   scripts\run_vhvl_v44_delivery.bat 9c1 projects\9c1_Redesign
REM   scripts\run_vhvl_v44_delivery.bat 9c1 projects\9c1_Redesign --zip

setlocal

set "AB_ID=%~1"
set "PROJ_DIR=%~2"
set "ZIP_FLAG=%~3"

if "%AB_ID%"=="" (
  echo ❌ : antibody_id
  echo : scripts\run_vhvl_v44_delivery.bat ^<id^> ^<project_dir^> [--zip]
  exit /b 1
)

if "%PROJ_DIR%"=="" (
  echo ❌ : project_dir
  echo : scripts\run_vhvl_v44_delivery.bat ^<id^> ^<project_dir^> [--zip]
  exit /b 1
)

echo ==========================================================
echo VH/VL V4.4 
echo  - （MD）
echo  -  PDF（）
echo  -  delivery_^%AB_ID^% （ ZIP）
echo  - : ANARCII->ANARCI, ColabFold->AlphaFold2
echo ==========================================================
echo.

echo [1/3] （MD）...
python scripts\render_vhvl_v44_reports.py "%AB_ID%" "%PROJ_DIR%" --write
if %errorlevel% neq 0 (
  echo ❌ 
  exit /b 1
)

echo.
echo [2/3]  PDF...
python scripts\md_to_pdf.py "%PROJ_DIR%\reports\%AB_ID%_Client_zh.md" "%PROJ_DIR%\reports\%AB_ID%_Client_zh.pdf"
if %errorlevel% neq 0 (
  echo ❌  PDF 
  exit /b 1
)

REM  PDF（）
if exist "%PROJ_DIR%\reports\%AB_ID%_V44_Audit.md" (
  python scripts\md_to_pdf.py "%PROJ_DIR%\reports\%AB_ID%_V44_Audit.md" "%PROJ_DIR%\reports\%AB_ID%_V44_Audit.pdf"
)

echo.
echo [3/4] ...
if "%ZIP_FLAG%"=="--zip" (
  python scripts\package_delivery.py "%AB_ID%" "%PROJ_DIR%" --zip
) else (
  python scripts\package_delivery.py "%AB_ID%" "%PROJ_DIR%"
)

echo.
echo [4/4] （ + /）...
python scripts\verify_vhvl_v44_project.py "%AB_ID%" "%PROJ_DIR%"
if %errorlevel% neq 0 (
  echo ❌ ：（ --fix ）
  exit /b 1
)

echo.
echo ✅ 
endlocal

