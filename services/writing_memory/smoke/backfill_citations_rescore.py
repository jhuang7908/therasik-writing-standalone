"""
Backfill PubMed citations on an existing smoke JSON (no re-draft).

  cd /srv/services/writing_memory
  .venv/bin/python smoke/backfill_citations_rescore.py smoke/huNSG_QUAD_pnas_20260527T001202Z.json

Reads sections[].text, calls /insert_citations per section, merges reference_list, rescores QC.
"""

from __future__ import annotations

import json
import re
import sys
import time
from datetime import datetime, timezone
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
from run_ordered_smoke_v1545 import (  # noqa: E402
    HU_ABSTRACT,
    citation_signals,
    merge_reference_lists,
    post,
    step3_qc,
)

CITE_RE = re.compile(r"\[CITE:\s*[^\]]+\]", re.I)


def backfill_section(text: str, journal: str) -> tuple[str, list[str], dict]:
    if not CITE_RE.search(text):
        return text, [], {"skipped": True}
    code, res = post(
        "/insert_citations",
        {
            "paragraph": text,
            "target_journal": journal,
            "force_author_year": True,
        },
        timeout=240,
    )
    if code != 200:
        return text, [], {"http": code, "error": res}
    prose = res.get("rewritten_paragraph") or text
    refs = list(res.get("reference_list") or [])
    meta = res.get("_meta") or {}
    return prose, refs, {
        "http": code,
        "n_citations": meta.get("n_citations"),
        "n_verified": meta.get("n_verified"),
        "signals_after": citation_signals(prose),
    }


def main() -> int:
    if len(sys.argv) < 2:
        print("Usage: backfill_citations_rescore.py <report.json>")
        return 2
    src = Path(sys.argv[1])
    data = json.loads(src.read_text(encoding="utf-8"))
    journal = data.get("target_journal") or "pnas"
    plan = data.get("plan")
    sections_in = data.get("sections") or []
    if not sections_in:
        print("No sections in report")
        return 1

    print(f"Backfill citations → {journal} ({len(sections_in)} sections)")
    updated: list[dict] = []
    all_refs: list[list[str]] = []
    for s in sections_in:
        key = s.get("key", "?")
        text = s.get("text") or ""
        print(f"  {key} …", end=" ", flush=True)
        t0 = time.time()
        prose, refs, meta = backfill_section(text, journal)
        all_refs.append(refs)
        ns = dict(s)
        ns["text"] = prose
        ns["reference_count"] = len(refs)
        ns["citation_backfill"] = meta
        updated.append(ns)
        print(
            f"{round(time.time()-t0,1)}s refs={len(refs)} "
            f"signals={meta.get('signals_after', {})}"
        )

    merged = merge_reference_lists(all_refs)
    print(f"Merged references: {len(merged)}")
    qc = step3_qc(updated, plan, journal, "after_citation_backfill", reference_list=merged)

    out = {
        "source_report": str(src),
        "backfilled_at": datetime.now(timezone.utc).isoformat(),
        "target_journal": journal,
        "merged_reference_count": len(merged),
        "merged_reference_list": merged,
        "sections": updated,
        "qc": qc,
    }
    ts = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    out_path = src.parent / f"{src.stem}_cited_{ts}.json"
    out_path.write_text(json.dumps(out, indent=2, ensure_ascii=False), encoding="utf-8")
    print(f"QC overall={qc.get('overall_score')} {qc.get('overall_verdict')}")
    print(f"Wrote {out_path}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
