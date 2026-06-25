@echo off
REM VHH论文PDF生成脚本 (Windows批处理)
REM 最简单的方法：使用Pandoc + XeLaTeX

chcp 65001 >nul
echo ========================================
echo VHH人源化论文PDF生成工具
echo ========================================
echo.

cd /d "%~dp0"

set INPUT_FILE=VHH人源化分析与7D12设计论文_InSynBio.md
set OUTPUT_FILE=VHH人源化分析与7D12设计论文_InSynBio.pdf

REM 检查文件是否存在
if not exist "%INPUT_FILE%" (
    echo [错误] 找不到文件: %INPUT_FILE%
    pause
    exit /b 1
)

echo [信息] 输入文件: %INPUT_FILE%
echo [信息] 输出文件: %OUTPUT_FILE%
echo.

REM 检查pandoc
where pandoc >nul 2>&1
if errorlevel 1 (
    echo [错误] 未找到pandoc，请先安装:
    echo        下载地址: https://pandoc.org/installing.html
    echo.
    echo 或者使用Typora:
    echo        1. 安装Typora: https://typora.io/
    echo        2. 打开 %INPUT_FILE%
    echo        3. 文件 -^> 导出 -^> PDF
    pause
    exit /b 1
)

REM 检查xelatex
where xelatex >nul 2>&1
if errorlevel 1 (
    echo [警告] 未找到xelatex，将尝试使用pdflatex
    echo        建议安装MiKTeX或TeX Live以获得更好的中文支持
    echo.
    set LATEX_ENGINE=pdflatex
) else (
    set LATEX_ENGINE=xelatex
)

echo [信息] 使用引擎: %LATEX_ENGINE%
echo [信息] 开始生成PDF...
echo.

REM 生成PDF
pandoc "%INPUT_FILE%" ^
    -o "%OUTPUT_FILE%" ^
    --pdf-engine=%LATEX_ENGINE% ^
    --from=markdown+raw_html+tex_math_dollars ^
    --toc ^
    --number-sections ^
    -V geometry:margin=2.5cm ^
    -V fontsize=11pt ^
    -V linestretch=1.5

if errorlevel 1 (
    echo.
    echo [错误] PDF生成失败！
    echo.
    echo 可能的解决方案:
    echo 1. 安装MiKTeX: https://miktex.org/download
    echo 2. 使用Typora: https://typora.io/
    echo 3. 查看详细指南: PDF_GENERATION_GUIDE.md
    pause
    exit /b 1
)

echo.
echo [成功] PDF已生成: %OUTPUT_FILE%
if exist "%OUTPUT_FILE%" (
    for %%A in ("%OUTPUT_FILE%") do echo [信息] 文件大小: %%~zA 字节
)

echo.
echo 按任意键打开PDF...
pause >nul
start "" "%OUTPUT_FILE%"
