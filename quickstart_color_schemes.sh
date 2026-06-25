#!/bin/bash
# Quick start: Color scheme system demo

echo "🎨 Color Scheme System - Quick Start"
echo "===================================="
echo ""

# Check if Python is available
if ! command -v python3 &> /dev/null; then
    echo "❌ Python3 not found. Please install Python 3.7+"
    exit 1
fi

cd "$(dirname "$0")" || exit 1

echo "✅ Step 1: Generate HTML preview of all color schemes"
python3 scripts/preview_color_schemes.py
echo ""

echo "✅ Step 2: List all available schemes"
python3 scripts/color_scheme_manager.py list
echo ""

echo "✅ Step 3: Show details of 'publication' scheme"
python3 scripts/color_scheme_manager.py show publication
echo ""

echo "✅ Step 4: Create a custom scheme template"
python3 scripts/color_scheme_manager.py template custom_scheme.json
echo ""

echo "🎉 Quick start complete!"
echo ""
echo "Next steps:"
echo "1. Open 'color_schemes_preview.html' in your browser"
echo "2. Try: python3 scripts/colorize_interface_pdb.py --pdb your_complex.pdb --scheme publication --ab_chains A --ag_chain B --output result.pdb"
echo ""
echo "📖 Documentation: docs/COLOR_SCHEME_QUICK_START.md"
