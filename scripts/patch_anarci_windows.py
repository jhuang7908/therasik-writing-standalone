"""
Patch anarci/anarci.py in the active conda env to handle Windows file-locking
when hmmscan writes temp files. Replaces the bare os.remove() in run_hmmer's
finally block with a try/except version.
One-time patch; idempotent (checks if already patched before modifying).
"""
import sys
import importlib
from pathlib import Path

try:
    import anarci.anarci as _mod
    anarci_path = Path(_mod.__file__)
except ImportError:
    print("anarci not found in this environment.")
    sys.exit(1)

src = anarci_path.read_text(encoding="utf-8")

PATCHED_MARKER = "# PATCHED_WINDOWS_FILE_LOCK"

if PATCHED_MARKER in src:
    print(f"anarci.py already patched: {anarci_path}")
    sys.exit(0)

OLD = "        os.remove(fasta_filename)\n        os.remove(output_filename)"
NEW = (
    "        # PATCHED_WINDOWS_FILE_LOCK\n"
    "        for _fname in (fasta_filename, output_filename):\n"
    "            try:\n"
    "                os.close(_anarci_fd_map.get(_fname, -1))\n"
    "            except Exception:\n"
    "                pass\n"
    "            try:\n"
    "                os.remove(_fname)\n"
    "            except (PermissionError, OSError):\n"
    "                pass"
)

# Simpler version: just wrap both removes
OLD_SIMPLE = "        os.remove(fasta_filename)\n        os.remove(output_filename)"
NEW_SIMPLE = (
    "        # PATCHED_WINDOWS_FILE_LOCK\n"
    "        for _f in [fasta_filename, output_filename]:\n"
    "            try:\n"
    "                os.remove(_f)\n"
    "            except Exception:\n"
    "                pass"
)

if OLD_SIMPLE not in src:
    print(f"Could not find target block in {anarci_path}")
    print("Lines around 'os.remove':")
    for i, line in enumerate(src.splitlines()):
        if "os.remove" in line:
            start = max(0, i - 2)
            end = min(len(src.splitlines()), i + 3)
            for j in range(start, end):
                print(f"  {j+1:4d}: {src.splitlines()[j]}")
    sys.exit(1)

patched = src.replace(OLD_SIMPLE, NEW_SIMPLE, 1)
anarci_path.write_text(patched, encoding="utf-8")
print(f"Patched: {anarci_path}")
print("Windows file-locking fix applied to anarci.anarci.run_hmmer")
