"""
Step 2: Full huNSG-QUAD draft → frontiers_immunology + research (BMRC abstract + figure manifests).

Usage:
  WM_BASE=https://write.insynbio.com WM_AUTH=Admin:Rocky123 python smoke/run_full_draft_frontiers_v1547.py
"""

from __future__ import annotations

import json
import re
import sys
import time
from datetime import datetime, timezone
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
from run_full_draft_v1546 import (  # noqa: E402
    DATA_SUMMARY,
    EXPERIMENTAL_DESIGN,
    HU_ABSTRACT,
    SECTION_TARGETS,
)
from run_ordered_smoke_v1545 import (  # noqa: E402
    BASE,
    SMOKE_INSERT_CITATIONS,
    merge_reference_lists,
    post,
    prose_from_draft,
    step3_qc,
)
from run_results_with_figs import FIG_MANIFESTS  # noqa: E402
from run_abstract_bmrc_smoke import check_bmrc_structure  # noqa: E402

TARGET = "frontiers_immunology"
ARTICLE_TYPE = "research"
OUT_DIR = Path(__file__).resolve().parent


def wc(text: str) -> int:
    return len(re.findall(r"[A-Za-z0-9'-]+", text or ""))


def main() -> int:
    print(f"\n=== FULL DRAFT v1547: huNSG-QUAD → {TARGET} ===")
    print(f"  base={BASE}")
    print(f"  auto_insert_citations={SMOKE_INSERT_CITATIONS}")
    print(f"  section_word_targets={SECTION_TARGETS}")

    print("\n  plan_paper …")
    t0 = time.time()
    plan_code, plan = post(
        "/plan_paper",
        {
            "user_intent": HU_ABSTRACT,
            "article_type": ARTICLE_TYPE,
            "target_journal": TARGET,
            "data_summary": DATA_SUMMARY,
            "experimental_design": EXPERIMENTAL_DESIGN,
        },
        timeout=360,
    )
    print(f"    HTTP {plan_code} {round(time.time()-t0,1)}s")
    if plan_code != 200:
        print("PLAN FAILED:", plan)
        return 1

    sections: list[dict] = []
    per_section_refs: list[list] = []

    for sec in ("abstract", "introduction", "methods", "results", "discussion"):
        target_words = SECTION_TARGETS.get(sec)
        print(f"\n  draft_section → {sec} (target ~{target_words}) …")
        t0 = time.time()
        body: dict = {
            "plan": plan,
            "section_key": sec,
            "target_journal": TARGET,
            "article_type": ARTICLE_TYPE,
            "auto_insert_citations": SMOKE_INSERT_CITATIONS,
            "force_author_year": True,
            "section_word_target": target_words,
        }
        if sec == "results":
            body["figure_quantitative_manifests"] = FIG_MANIFESTS

        draft_code, dr = post("/draft_section", body, timeout=480)
        prose, refs, cite_meta = prose_from_draft(dr)
        per_section_refs.append(refs)
        bmrc = check_bmrc_structure(prose) if sec == "abstract" else None

        sections.append({
            "key": sec,
            "title": sec.title(),
            "text": prose,
            "http": draft_code,
            "elapsed_s": round(time.time() - t0, 1),
            "words": dr.get("approximate_words") or wc(prose),
            "target_words": target_words,
            "fill_count": len(dr.get("fill_markers_used") or []),
            "reference_count": len(refs),
            "citation_meta": cite_meta,
            "bmrc_enforcement": dr.get("_bmrc_enforcement"),
            "bmrc_check": bmrc,
        })
        extra = f"  bmrc={bmrc['bmrc_complete']}" if bmrc else ""
        print(
            f"    HTTP {draft_code} {sections[-1]['elapsed_s']}s  "
            f"words={sections[-1]['words']}/{target_words}  "
            f"fills={sections[-1]['fill_count']}  refs={len(refs)}{extra}"
        )

    merged_refs = merge_reference_lists(per_section_refs)
    qc = step3_qc(sections, plan, TARGET, "full_draft_frontiers_v1547", reference_list=merged_refs)

    wc_by = {s["key"]: wc(s["text"]) for s in sections}
    wc_total = sum(wc_by.values())
    bench = {
        "abstract": 251,
        "introduction": 565,
        "methods": 1375,
        "results": 3233,
        "discussion": 1927,
        "total": 7351,
        "refs": 44,
    }

    print(f"\n  word_count_by_section = {wc_by}")
    print(f"  word_count_total = {wc_total}  refs={len(merged_refs)}")
    print("\n  === vs expert Front. Immunol. 2024;15:1419117 ===")
    for k in ("abstract", "introduction", "methods", "results", "discussion"):
        print(f"  {k:<14} {wc_by[k]:>5} / {bench[k]:>5} ({round(wc_by[k]/bench[k]*100)}%)")
    print(f"  {'TOTAL':<14} {wc_total:>5} / {bench['total']:>5} ({round(wc_total/bench['total']*100)}%)")

    ts = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    report = {
        "protocol_version": "v1547_full_draft_frontiers_immunology",
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "target_journal": TARGET,
        "article_type": ARTICLE_TYPE,
        "auto_insert_citations": SMOKE_INSERT_CITATIONS,
        "section_word_targets": SECTION_TARGETS,
        "merged_reference_count": len(merged_refs),
        "merged_reference_list": merged_refs,
        "word_count_by_section": wc_by,
        "word_count_total": wc_total,
        "expert_benchmark": {
            "source": "Front. Immunol. 2024;15:1419117",
            "doi": "10.3389/fimmu.2024.1419117",
            "ref_count": bench["refs"],
            "word_total": bench["total"],
            "words_by_section": {k: bench[k] for k in wc_by},
        },
        "qc": qc,
        "plan": plan,
        "sections": sections,
    }

    out_json = OUT_DIR / f"huNSG_QUAD_frontiers_{ts}.json"
    out_json.write_text(json.dumps(report, indent=2, ensure_ascii=False), encoding="utf-8")

    manuscript_lines = [
        f"# huNSG-QUAD — {TARGET} draft ({ts})",
        f"Words: {wc_total} | Refs: {len(merged_refs)} | QC: {qc.get('overall_verdict')}",
        "",
    ]
    for s in sections:
        manuscript_lines.append(f"## {s['title']}\n")
        manuscript_lines.append(s["text"])
        manuscript_lines.append("")
    out_txt = OUT_DIR / f"huNSG_QUAD_frontiers_{ts}.txt"
    out_txt.write_text("\n".join(manuscript_lines), encoding="utf-8")

    abs_bmrc = next(
        (s["bmrc_check"] for s in sections if s["key"] == "abstract"),
        {},
    )
    print(f"\nQC overall={qc.get('overall_score')} {qc.get('overall_verdict')}")
    print(f"Abstract BMRC: {abs_bmrc.get('bmrc_complete')}")
    print(f"Wrote {out_json.name}")
    print(f"Wrote {out_txt.name}")

    return 0 if abs_bmrc.get("bmrc_complete") else 2


if __name__ == "__main__":
    raise SystemExit(main())
