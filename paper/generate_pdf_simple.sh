#!/bin/bash
# VHH论文PDF生成脚本 (Linux/Mac)
# 最简单的方法：使用Pandoc + XeLaTeX

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$SCRIPT_DIR"

INPUT_FILE="VHH人源化分析与7D12设计论文_InSynBio.md"
OUTPUT_FILE="VHH人源化分析与7D12设计论文_InSynBio.pdf"

echo "========================================"
echo "VHH人源化论文PDF生成工具"
echo "========================================"
echo

# 检查文件是否存在
if [ ! -f "$INPUT_FILE" ]; then
    echo "[错误] 找不到文件: $INPUT_FILE"
    exit 1
fi

echo "[信息] 输入文件: $INPUT_FILE"
echo "[信息] 输出文件: $OUTPUT_FILE"
echo

# 检查pandoc
if ! command -v pandoc &> /dev/null; then
    echo "[错误] 未找到pandoc，请先安装:"
    echo "       macOS: brew install pandoc"
    echo "       Ubuntu: sudo apt-get install pandoc"
    echo "       或访问: https://pandoc.org/installing.html"
    echo
    echo "或者使用Typora:"
    echo "      1. 安装Typora: https://typora.io/"
    echo "      2. 打开 $INPUT_FILE"
    echo "      3. 文件 -> 导出 -> PDF"
    exit 1
fi

# 检查LaTeX引擎
if command -v xelatex &> /dev/null; then
    LATEX_ENGINE="xelatex"
elif command -v lualatex &> /dev/null; then
    LATEX_ENGINE="lualatex"
elif command -v pdflatex &> /dev/null; then
    LATEX_ENGINE="pdflatex"
    echo "[警告] 使用pdflatex，中文支持可能不完整"
    echo "       建议安装XeLaTeX或LuaLaTeX"
else
    echo "[错误] 未找到LaTeX引擎"
    echo "       请安装TeX Live或MiKTeX"
    exit 1
fi

echo "[信息] 使用引擎: $LATEX_ENGINE"
echo "[信息] 开始生成PDF..."
echo

# 生成PDF
pandoc "$INPUT_FILE" \
    -o "$OUTPUT_FILE" \
    --pdf-engine="$LATEX_ENGINE" \
    --from=markdown+raw_html+tex_math_dollars \
    --toc \
    --number-sections \
    -V geometry:margin=2.5cm \
    -V fontsize=11pt \
    -V linestretch=1.5 \
    -V CJKmainfont="Noto Sans CJK SC" \
    -V mainfont="Times New Roman" \
    --highlight-style=tango

if [ $? -eq 0 ] && [ -f "$OUTPUT_FILE" ]; then
    echo
    echo "[成功] PDF已生成: $OUTPUT_FILE"
    FILE_SIZE=$(stat -f%z "$OUTPUT_FILE" 2>/dev/null || stat -c%s "$OUTPUT_FILE" 2>/dev/null)
    echo "[信息] 文件大小: $FILE_SIZE 字节"
    echo
    echo "使用以下命令打开PDF:"
    echo "  open $OUTPUT_FILE  # macOS"
    echo "  xdg-open $OUTPUT_FILE  # Linux"
else
    echo
    echo "[错误] PDF生成失败！"
    echo
    echo "可能的解决方案:"
    echo "1. 安装TeX Live: https://www.tug.org/texlive/"
    echo "2. 使用Typora: https://typora.io/"
    echo "3. 查看详细指南: PDF_GENERATION_GUIDE.md"
    exit 1
fi
