"""Legacy alias: V4b = ex-V5. Delegates to recalculate_v4b.py."""
import subprocess
import sys
from pathlib import Path

if __name__ == "__main__":
    script = Path(__file__).resolve().parent / "recalculate_v4b.py"
    raise SystemExit(subprocess.call([sys.executable, str(script)]))
