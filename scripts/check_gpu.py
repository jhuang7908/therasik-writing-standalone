import sys
import torch
sys.stderr.write(f"CUDA available: {torch.cuda.is_available()}\n")
if torch.cuda.is_available():
    sys.stderr.write(f"Device: {torch.cuda.get_device_name(0)}\n")
    sys.stderr.write(f"Memory: {torch.cuda.get_device_properties(0).total_mem / 1e9:.1f} GB\n")
else:
    sys.stderr.write("CPU only mode\n")
