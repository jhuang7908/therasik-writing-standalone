"""Pytest bootstrap: ensure project root is importable as a package.

This file is intentionally minimal — it only inserts the Antibody_Engineer_Suite
project root into ``sys.path`` so that ``from core.vhh_humanization import ...``
resolves regardless of where pytest is invoked.
"""

from __future__ import annotations

import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))
