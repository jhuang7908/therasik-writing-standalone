"""Step A — huNSG-QUAD plan + 5-section draft (PNAS) + QC score."""
from __future__ import annotations

import json
import sys
from datetime import datetime, timezone
from pathlib import Path

# Import shared smoke utilities
sys.path.insert(0, str(Path(__file__).parent))
from run_ordered_smoke_v1545 import (  # noqa: E402
    HU_ABSTRACT,
    SMOKE_INSERT_CITATIONS,
    merge_reference_lists,
    post,
    prose_from_draft,
    step3_qc,
)

TARGET = "pnas"


def main() -> int:
    print(f"\n=== STEP A: huNSG-QUAD → {TARGET} ===")

    print("  plan_paper …")
    import time
    t0 = time.time()
    code, plan = post("/plan_paper", {
        "user_intent": HU_ABSTRACT,
        "article_type": "research",
        "data_summary": (
            "6-week engraftment of human monocytes, DCs, granulocytes; "
            "IP and intranasal LPS; MCC950 blocks IL-1b/IL-18 without monocyte death."
        ),
        "experimental_design": (
            "NSG-QUAD + human HSPC; flow cytometry; Luminex; LPS challenge; MCC950."
        ),
    }, timeout=300)
    print(f"    plan HTTP {code} {round(time.time()-t0,1)}s")
    if code != 200:
        print(plan)
        return 1

    sections = []
    per_section_refs: list[list[str]] = []
    print(f"  auto_insert_citations={SMOKE_INSERT_CITATIONS}")
    for sec in ("abstract", "introduction", "results", "discussion", "methods"):
        print(f"  draft_section → {sec} …")
        t0 = time.time()
        code, dr = post("/draft_section", {
            "plan": plan,
            "section_key": sec,
            "target_journal": TARGET,
            "article_type": "research",
            "auto_insert_citations": SMOKE_INSERT_CITATIONS,
            "force_author_year": True,
        }, timeout=300)
        prose, refs, cite_meta = prose_from_draft(dr)
        per_section_refs.append(refs)
        fills = dr.get("fill_markers_used") or []
        sections.append({
            "key": sec,
            "title": sec.title(),
            "text": prose,
            "http": code,
            "elapsed_s": round(time.time() - t0, 1),
            "words": dr.get("approximate_words"),
            "fill_count": len(fills),
            "reference_count": len(refs),
            "citation_meta": cite_meta,
        })
        print(
            f"    HTTP {code} fills={len(fills)} words={dr.get('approximate_words')} "
            f"refs={len(refs)} cite_left={cite_meta.get('cite_placeholders_left')}"
        )

    merged_refs = merge_reference_lists(per_section_refs)
    qc = step3_qc(sections, plan, TARGET, "pnas_draft_cited", reference_list=merged_refs)

    report = {
        "target_journal": TARGET,
        "auto_insert_citations": SMOKE_INSERT_CITATIONS,
        "merged_reference_count": len(merged_refs),
        "merged_reference_list": merged_refs[:20],
        "plan_title": plan.get("suggested_title"),
        "sections_summary": [
            {"key": s["key"], "words": s["words"], "fill_count": s["fill_count"]}
            for s in sections
        ],
        "qc": qc,
        "sections": sections,
    }
    ts = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    out = Path(__file__).parent / f"huNSG_QUAD_pnas_{ts}.json"
    out.write_text(json.dumps(report, indent=2, ensure_ascii=False), encoding="utf-8")
    print(f"\nQC overall={qc.get('overall_score')} {qc.get('overall_verdict')}")
    print(f"Wrote {out}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
