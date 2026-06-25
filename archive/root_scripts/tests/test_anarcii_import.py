#!/usr/bin/env python3
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent
sys.path.insert(0, str(PROJECT_ROOT))

print("Testing ANARCII import...")

try:
    from anarcii import Anarcii
    print("✅ anarcii.Anarcii imported successfully")
except ImportError as e:
    print(f"❌ Failed to import anarcii.Anarcii: {e}")

try:
    from core.numbering.imgt_anarcii import imgt_number_anarcii, IMGTNumberingError
    print("✅ core.numbering.imgt_anarcii imported successfully")
except ImportError as e:
    print(f"❌ Failed to import core.numbering.imgt_anarcii: {e}")
