"""Build and load frozen article-type cohort releases."""

from __future__ import annotations

import json
import statistics
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

_COHORT_ROOT = Path(__file__).resolve().parent.parent / "data" / "article_type_cohorts"

COHORT_TARGETS: dict[str, int] = {
    "original_research": 8,
    "review_narrative": 6,
    "systematic_review": 5,
    "methods_protocols": 6,
    "case_report": 5,
    "brief_communication": 5,
    "perspective": 5,
    "clinical_trial": 5,
    "hypothesis": 5,
    "negative_results": 5,
    "resource_paper": 5,
    "translational_drug_discovery": 5,
}


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


def load_release(path: Path | None = None) -> dict[str, Any]:
    p = path or (_COHORT_ROOT / "RELEASE_v1.json")
    if not p.exists():
        return {}
    return json.loads(p.read_text(encoding="utf-8"))


def _aggregate_stats(papers: list[dict[str, Any]]) -> dict[str, Any]:
    if not papers:
        return {}
    abs_w = [p["metrics"]["word_count"]["abstract"] for p in papers if p.get("metrics")]
    disc_w = [p["metrics"]["word_count"]["discussion"] for p in papers if p.get("metrics")]
    ref_d = [p["metrics"]["citations_per_1000_words"] for p in papers if p.get("metrics")]

    def band(vals: list[float | int]) -> dict[str, float]:
        if not vals:
            return {}
        return {
            "n": len(vals),
            "median": round(statistics.median(vals), 2),
            "p10": round(sorted(vals)[max(0, len(vals) // 10)], 2),
            "p90": round(sorted(vals)[min(len(vals) - 1, max(0, (len(vals) * 9) // 10))], 2),
        }

    return {
        "abstract_words": band(abs_w),
        "discussion_words": band(disc_w),
        "citations_per_1000_words": band(ref_d),
    }


def build_release(
    selected: dict[str, list[dict[str, Any]]],
    *,
    version: str = "1.0.0",
    notes: str = "",
) -> dict[str, Any]:
    """Freeze cohort release JSON."""
    cohorts: dict[str, Any] = {}
    for ctype, papers in selected.items():
        cohorts[ctype] = {
            "target_n": COHORT_TARGETS.get(ctype, 5),
            "selected_n": len(papers),
            "stats": _aggregate_stats(papers),
            "papers": papers,
        }

    return {
        "release_id": "RELEASE_v1",
        "version": version,
        "generated_at": _now(),
        "policy": {
            "language": "English",
            "region_preference": "US/UK journals",
            "corresponding_author": "native_speaker_heuristic_last_author",
            "fame": "seed_landmark_plus_local_ranked",
            "partial_text": "PMC abstract+discussion+conclusion only in MVP",
        },
        "notes": notes,
        "cohorts": cohorts,
    }


def write_release(doc: dict[str, Any], path: Path | None = None) -> Path:
    out = path or (_COHORT_ROOT / "RELEASE_v1.json")
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(doc, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    return out
