#!/bin/bash
# ==============================================================================
# InSynBio WSL2 Content Generation Environment Setup
# ==============================================================================

set -e

echo "Updating system packages..."
apt update && apt install -y libgl1-mesa-glx libglib2.0-0 python3-venv python3-pip

# Define the working directory (WSL path)
WSL_DIR="/mnt/d/InSynBio-AI-Research/Antibody_Engineer_Suite/content_generation_tools"
cd "$WSL_DIR"

echo "Creating Linux virtual environment..."
if [ ! -d "venv_linux" ]; then
    python3 -m venv venv_linux
fi

echo "Activating environment and installing dependencies..."
source venv_linux/bin/activate

# Use a fast mirror for pip in China if needed, otherwise standard
pip install --upgrade pip
pip install paddlepaddle paddleocr python-pptx Pillow python-dotenv requests easyocr pytesseract onnxruntime

echo "=============================================================================="
echo "WSL2 Setup Complete!"
echo "To use the tools in WSL2, run:"
echo "cd $WSL_DIR"
echo "source venv_linux/bin/activate"
echo "=============================================================================="
