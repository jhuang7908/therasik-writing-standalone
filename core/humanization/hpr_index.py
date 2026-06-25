"""HPR Index utilities for VH/VL humanization.

HPR = Human Peptide Repertoire Compatibility Index.

This customer-facing name intentionally avoids external product or method names.
The metric computes local 9-mer human-antibody-repertoire coverage using the
local promb human-oas database when available.
"""

from __future__ import annotations

import os
import queue
import threading
from dataclasses import asdict, dataclass
from functools import lru_cache
from typing import Any, Dict


@dataclass
class ChainHPR:
    score: float | None
    found_9mers: int | None
    total_9mers: int | None
    status: str = "not_computed"
    error: str | None = None


@lru_cache(maxsize=1)
def _hpr_db() -> Any:
    import promb  # type: ignore

    return promb.init_db("human-oas", verbose=False)


def _score_chain(seq: str, db: Any) -> ChainHPR:
    seq = (seq or "").strip().upper()
    if len(seq) < 9:
        return ChainHPR(None, None, None, "not_computed", "sequence shorter than 9 aa")
    peptides = db.chop_seq_peptides(seq)
    total = len(peptides)
    if total <= 0:
        return ChainHPR(None, 0, 0, "not_computed", "no 9-mers generated")
    found = sum(1 for peptide in peptides if db.contains(peptide))
    return ChainHPR(round(found / total, 4), found, total, "computed", None)


def compute_hpr_index(vh: str, vl: str) -> Dict[str, Any]:
    """Compute VH/VL HPR scores with a stable result shape."""
    try:
        db = _hpr_db()
        vh_result = _score_chain(vh, db)
        vl_result = _score_chain(vl, db)
        combined_found = (vh_result.found_9mers or 0) + (vl_result.found_9mers or 0)
        combined_total = (vh_result.total_9mers or 0) + (vl_result.total_9mers or 0)
        combined_score = round(combined_found / combined_total, 4) if combined_total else None
        return {
            "metric_name": "HPR Index",
            "full_name": "Human Peptide Repertoire Compatibility Index",
            "method_summary": "Variable-region 9-mer compatibility against a local human antibody repertoire reference.",
            "vh": asdict(vh_result),
            "vl": asdict(vl_result),
            "combined": {
                "score": combined_score,
                "found_9mers": combined_found if combined_total else None,
                "total_9mers": combined_total if combined_total else None,
                "status": "computed" if combined_total else "not_computed",
            },
        }
    except Exception as exc:
        err = str(exc)
        empty = asdict(ChainHPR(None, None, None, "not_computed", err))
        return {
            "metric_name": "HPR Index",
            "full_name": "Human Peptide Repertoire Compatibility Index",
            "method_summary": "Variable-region 9-mer compatibility against a local human antibody repertoire reference.",
            "vh": empty,
            "vl": empty,
            "combined": {"score": None, "found_9mers": None, "total_9mers": None, "status": "not_computed"},
            "error": err,
        }


def _empty_hpr(error: str) -> Dict[str, Any]:
    empty = asdict(ChainHPR(None, None, None, "not_computed", error))
    return {
        "metric_name": "HPR Index",
        "full_name": "Human Peptide Repertoire Compatibility Index",
        "method_summary": "Variable-region 9-mer compatibility against a local human antibody repertoire reference.",
        "vh": empty,
        "vl": empty,
        "combined": {"score": None, "found_9mers": None, "total_9mers": None, "status": "not_computed"},
        "error": error,
    }


def _compare_hpr_worker(q: queue.Queue, donor_vh: str, donor_vl: str, humanized_vh: str, humanized_vl: str) -> None:
    try:
        q.put(_compare_hpr_inline(donor_vh, donor_vl, humanized_vh, humanized_vl))
    except Exception as exc:
        q.put({"error": str(exc)})


def _compare_hpr_inline(donor_vh: str, donor_vl: str, humanized_vh: str, humanized_vl: str) -> Dict[str, Any]:
    donor = compute_hpr_index(donor_vh, donor_vl)
    humanized = compute_hpr_index(humanized_vh, humanized_vl)

    def _delta(chain: str) -> float | None:
        d = (donor.get(chain) or {}).get("score")
        h = (humanized.get(chain) or {}).get("score")
        if d is None or h is None:
            return None
        return round(float(h) - float(d), 4)

    return {
        "metric_name": "HPR Index",
        "full_name": "Human Peptide Repertoire Compatibility Index",
        "donor": donor,
        "humanized": humanized,
        "delta": {
            "vh": _delta("vh"),
            "vl": _delta("vl"),
            "combined": _delta("combined"),
        },
        "display_note": (
            "HPR Index evaluates compatibility of variable-region 9-mer peptides with a "
            "human antibody repertoire reference. A higher score supports improved local "
            "humanness continuity after humanization."
        ),
    }


def _compare_hpr_inline_vhh(donor_vhh: str, humanized_vhh: str) -> Dict[str, Any]:
    donor = compute_hpr_index(donor_vhh, "")
    humanized = compute_hpr_index(humanized_vhh, "")

    def _delta(chain: str) -> float | None:
        d = (donor.get(chain) or {}).get("score")
        h = (humanized.get(chain) or {}).get("score")
        if d is None or h is None:
            return None
        return round(float(h) - float(d), 4)

    return {
        "metric_name": "HPR Index",
        "full_name": "Human Peptide Repertoire Compatibility Index",
        "donor": donor,
        "humanized": humanized,
        "delta": {
            "vhh": _delta("vh"),
            "combined": _delta("vh"),
        },
        "display_note": (
            "HPR Index evaluates compatibility of variable-region 9-mer peptides with a "
            "human antibody repertoire reference. A higher score supports improved local "
            "humanness continuity after humanization."
        ),
    }


def _compare_hpr_worker_vhh(q: queue.Queue, donor_vhh: str, humanized_vhh: str) -> None:
    try:
        q.put(_compare_hpr_inline_vhh(donor_vhh, humanized_vhh))
    except Exception as exc:
        q.put({"error": str(exc)})


def compare_hpr_vhh(donor_vhh: str, humanized_vhh: str) -> Dict[str, Any]:
    """Return donor-vs-humanized HPR for VHH with a hard timeout guard (thread-based)."""
    timeout_sec = float(os.environ.get("ABENGINE_HPR_TIMEOUT_SEC", "60"))
    if timeout_sec <= 0:
        return _compare_hpr_inline_vhh(donor_vhh, humanized_vhh)

    q: queue.Queue = queue.Queue()
    t = threading.Thread(
        target=_compare_hpr_worker_vhh,
        args=(q, donor_vhh, humanized_vhh),
        daemon=True,
    )
    t.start()
    t.join(timeout_sec)
    if not q.empty():
        result = q.get()
        if isinstance(result, dict) and result.get("error") and not result.get("donor"):
            result["status"] = "not_computed"
        return result
    err = f"HPR local repertoire scoring exceeded {timeout_sec:g}s timeout"
    return {
        "metric_name": "HPR Index",
        "full_name": "Human Peptide Repertoire Compatibility Index",
        "donor": _empty_hpr(err),
        "humanized": _empty_hpr(err),
        "delta": {"vhh": None, "combined": None},
        "display_note": (
            "HPR Index evaluates compatibility of variable-region 9-mer peptides with a "
            "human antibody repertoire reference. A higher score supports improved local "
            "humanness continuity after humanization."
        ),
        "status": "not_computed",
        "error": err,
    }


def compare_hpr(donor_vh: str, donor_vl: str, humanized_vh: str, humanized_vl: str) -> Dict[str, Any]:
    """Return donor-vs-humanized HPR with a hard timeout guard (thread-based)."""
    timeout_sec = float(os.environ.get("ABENGINE_HPR_TIMEOUT_SEC", "60"))
    if timeout_sec <= 0:
        return _compare_hpr_inline(donor_vh, donor_vl, humanized_vh, humanized_vl)

    q: queue.Queue = queue.Queue()
    t = threading.Thread(
        target=_compare_hpr_worker,
        args=(q, donor_vh, donor_vl, humanized_vh, humanized_vl),
        daemon=True,
    )
    t.start()
    t.join(timeout_sec)
    if not q.empty():
        result = q.get()
        if isinstance(result, dict) and result.get("error") and not result.get("donor"):
            result["status"] = "not_computed"
        return result
    err = f"HPR local repertoire scoring exceeded {timeout_sec:g}s timeout"
    return {
        "metric_name": "HPR Index",
        "full_name": "Human Peptide Repertoire Compatibility Index",
        "donor": _empty_hpr(err),
        "humanized": _empty_hpr(err),
        "delta": {"vh": None, "vl": None, "combined": None},
        "display_note": (
            "HPR Index evaluates compatibility of variable-region 9-mer peptides with a "
            "human antibody repertoire reference. A higher score supports improved local "
            "humanness continuity after humanization."
        ),
        "status": "not_computed",
        "error": err,
    }
