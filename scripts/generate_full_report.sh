#!/bin/bash
# VHH 
# 

set -e  # 

# 
RESULT_JSON="${1:-result.json}"
OUTPUT_DIR="${2:-reports/output}"
PROJECT_ID="${3:-}"

echo "=========================================="
echo "VHH "
echo "=========================================="
echo ": $RESULT_JSON"
echo ": $OUTPUT_DIR"
echo "ID: $PROJECT_ID"
echo "=========================================="
echo ""

# 
if [ ! -f "$RESULT_JSON" ]; then
    echo "❌ :  $RESULT_JSON"
    exit 1
fi

# ID，JSON
if [ -z "$PROJECT_ID" ]; then
    if command -v python &> /dev/null; then
        PROJECT_ID=$(python -c "import json; print(json.load(open('$RESULT_JSON')).get('project_id', 'unknown_project'))" 2>/dev/null || echo "unknown_project")
    else
        PROJECT_ID="unknown_project"
    fi
fi

echo "📊  1: ..."
python scripts/plot_vhh_report_figures_v1.py \
    --input "$RESULT_JSON" \
    --output_dir "$OUTPUT_DIR" \
    --project-id "$PROJECT_ID"

if [ $? -eq 0 ]; then
    echo "✅ "
else
    echo "⚠️  ，..."
fi

echo ""
echo "📄  2:  Markdown + DOCX ..."
python scripts/generate_vhh_report_v1.py \
    --input "$RESULT_JSON" \
    --output_dir "$OUTPUT_DIR" \
    --project-id "$PROJECT_ID"

if [ $? -eq 0 ]; then
    echo "✅ "
else
    echo "❌ "
    exit 1
fi

echo ""
echo "=========================================="
echo "✅ ！"
echo "=========================================="
echo ""
echo "："
echo "  📄 Markdown: $OUTPUT_DIR/$PROJECT_ID/report_v1.md"
echo "  📄 DOCX:     $OUTPUT_DIR/$PROJECT_ID/report_v1.docx"
echo "  📊 :     $OUTPUT_DIR/$PROJECT_ID/figures/*.png"
echo ""
echo " / PI /  / ""。"
echo "=========================================="

















