"""
Runtime PATH and toolchain probes for the AbEngineCore API.

AbNatiV / ANARCI invoke ``hmmscan`` via subprocess and only search ``PATH``.
When uvicorn is started from systemd or nohup without ``conda activate``,
``sys.executable`` may be the anarcii interpreter while ``PATH`` omits
``.../envs/anarcii/bin`` — causing intermittent ``No such file or directory:
'hmmscan'`` failures.
"""
from __future__ import annotations

import os
import shutil
import sys
from pathlib import Path
from typing import Any, Dict


def ensure_toolchain_path() -> None:
    """Prepend the active interpreter's env ``bin`` (and optional extras) to PATH."""
    env_bin = str(Path(sys.executable).resolve().parent)
    extra_raw = os.environ.get("INSYNBIO_EXTRA_PATH", "").strip()
    prepend: list[str] = [env_bin]
    if extra_raw:
        prepend.extend(p for p in extra_raw.split(os.pathsep) if p.strip())

    current = os.environ.get("PATH", "")
    current_parts = [p for p in current.split(os.pathsep) if p]
    to_add = [p for p in prepend if p and p not in current_parts]
    if to_add:
        os.environ["PATH"] = os.pathsep.join(to_add + current_parts)


def probe_toolchain() -> Dict[str, Any]:
    """Return machine-checkable toolchain status for ``GET /api/health``."""
    ensure_toolchain_path()
    hmmscan = shutil.which("hmmscan")
    out: Dict[str, Any] = {
        "python_executable": sys.executable,
        "env_bin": str(Path(sys.executable).resolve().parent),
        "path_head": os.environ.get("PATH", "")[:240],
        "hmmscan": hmmscan,
        "hmmscan_ok": bool(hmmscan),
    }
    try:
        import ImmuneBuilder  # noqa: F401

        out["immunebuilder_ok"] = True
    except ImportError as exc:
        out["immunebuilder_ok"] = False
        out["immunebuilder_error"] = f"{type(exc).__name__}: {exc}"
    try:
        import abnativ  # noqa: F401

        out["abnativ_import_ok"] = True
    except ImportError as exc:
        out["abnativ_import_ok"] = False
        out["abnativ_import_error"] = f"{type(exc).__name__}: {exc}"
    out["toolchain_ok"] = bool(
        out["hmmscan_ok"]
        and out.get("immunebuilder_ok")
        and out.get("abnativ_import_ok")
    )
    return out
