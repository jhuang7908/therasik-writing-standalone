"""
Optional BioPhi `biophi oasis` CLI wrapper for T20 / OASis-style humanness scores.

Requires locally:
  - `biophi` on PATH (conda: `conda install biophi -c bioconda -c conda-forge`)
  - `OASIS_DB_PATH` or `BIOPHI_OASIS_DB` pointing at `OASis_9mers_v1.db`

When unavailable, returns ``t20_score=None`` and an explanatory ``t20_error``.
"""

from __future__ import annotations

import os
import shutil
import subprocess
import tempfile
from pathlib import Path
from typing import Any, Dict, Optional


def compute_t20_biophi(vh: str, vl: str) -> Dict[str, Any]:
    """
    Run BioPhi OASis CLI on VH/VL FASTA; extract a primary numeric humanness score (T20-style).

    Returns keys: ``t20_score`` (float or None), ``t20_error`` (str or None), optional ``source``.
    """
    vh = (vh or "").strip().upper()
    vl = (vl or "").strip().upper()
    out: Dict[str, Any] = {"t20_score": None, "t20_error": None, "source": None}
    if not vh or not vl:
        out["t20_error"] = "missing_vh_or_vl"
        return out

    db = os.environ.get("OASIS_DB_PATH") or os.environ.get("BIOPHI_OASIS_DB")
    exe = shutil.which("biophi")
    if not exe:
        out["t20_error"] = (
            "biophi_cli_missing — install BioPhi (e.g. conda install biophi -c bioconda) "
            "and ensure `biophi` is on PATH for the API process."
        )
        return out
    if not db or not Path(db).is_file():
        out["t20_error"] = (
            "oasis_db_missing — set environment variable OASIS_DB_PATH (or BIOPHI_OASIS_DB) "
            "to OASis_9mers_v1.db (see BioPhi README / Zenodo)."
        )
        return out

    tmp = Path(tempfile.mkdtemp(prefix="biophi_oasis_"))
    fa = tmp / "fv.fa"
    xlsx = tmp / "oasis_out.xlsx"
    rid = "ABENGINEQUERY"
    fa.write_text(f">{rid}_VH\n{vh}\n>{rid}_VL\n{vl}\n", encoding="utf-8")

    try:
        subprocess.run(
            [exe, "oasis", str(fa), "--oasis-db", db, "--output", str(xlsx)],
            check=True,
            capture_output=True,
            text=True,
            timeout=600,
        )
    except subprocess.CalledProcessError as e:
        err_txt = (e.stderr or e.stdout or str(e))[:800]
        out["t20_error"] = f"biophi_oasis_failed: {err_txt}"
        return out
    except Exception as exc:  # noqa: BLE001
        out["t20_error"] = f"{type(exc).__name__}: {exc}"
        return out

    if not xlsx.is_file():
        out["t20_error"] = "biophi_oasis_no_xlsx"
        return out

    score = _extract_oasis_score_xlsx(xlsx)
    if score is None:
        out["t20_error"] = "biophi_oasis_parse_failed — check oasis output columns (pandas/openpyxl optional)"
        return out

    out["t20_score"] = round(float(score), 3)
    out["source"] = "biophi_oasis_cli"
    return out


def _extract_oasis_score_xlsx(path: Path) -> Optional[float]:
    """Pick T20 / mean humanness column from BioPhi oasis Excel export."""
    try:
        import pandas as pd  # type: ignore
    except ImportError:
        return None

    try:
        df = pd.read_excel(path)
    except Exception:
        return None

    if df is None or df.empty:
        return None

    cols = [str(c) for c in df.columns]
    lower_map = {c.lower(): c for c in cols}

    for key in ("t20", "t20_score", "humanness", "oasis_score", "score"):
        if key in lower_map:
            col = lower_map[key]
            try:
                v = float(df[col].iloc[0])
                if not (v != v):  # not NaN
                    return v
            except Exception:
                continue

    # Fallback: first numeric column in first row
    for col in df.columns:
        try:
            v = float(df[col].iloc[0])
            if v == v:
                return v
        except Exception:
            continue
    return None
