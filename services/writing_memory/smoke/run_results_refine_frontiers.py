"""
Step 2: Re-draft Results for frontiers_immunology using per-figure subsections.

Each of the 4 figures is drafted as a separate Results sub-section (~800 words each),
then assembled into one Results block (~3200 words total).

Usage:
  WM_BASE=https://write.insynbio.com WM_AUTH=Admin:Rocky123 \\
      python smoke/run_results_refine_frontiers.py
"""

from __future__ import annotations

import json
import re
import sys
import time
from datetime import datetime, timezone
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
from run_results_with_figs import EXPERIMENTAL_DESIGN, FIG_MANIFESTS  # noqa: E402
from run_full_draft_v1546 import DATA_SUMMARY, HU_ABSTRACT  # noqa: E402
from run_ordered_smoke_v1545 import (  # noqa: E402
    BASE,
    SMOKE_INSERT_CITATIONS,
    merge_reference_lists,
    post,
    prose_from_draft,
)

TARGET = "frontiers_immunology"
ARTICLE_TYPE = "research"
OUT_DIR = Path(__file__).resolve().parent

FIG_SECTION_KEYS = [
    ("results_fig1", "Results — Figure 1: Engraftment of human myeloid cells in NSG-QUAD mice", FIG_MANIFESTS[0:1]),
    ("results_fig2", "Results — Figure 2: NF-κB and type I interferon responses to LPS", FIG_MANIFESTS[1:2]),
    ("results_fig3", "Results — Figure 3: NLRP3 inflammasome activation by LPS", FIG_MANIFESTS[2:3]),
    ("results_fig4", "Results — Figure 4: MCC950 pharmacological validation", FIG_MANIFESTS[3:4]),
]


def wc(text: str) -> int:
    return len(re.findall(r"[A-Za-z0-9'-]+", text or ""))


def load_plan(plan_path: Path | None) -> dict | None:
    if plan_path and plan_path.exists():
        d = json.loads(plan_path.read_text(encoding="utf-8"))
        return d.get("plan")
    return None


def main() -> int:
    print(f"\n=== RESULTS REFINE (per-figure) → {TARGET} ===")
    print(f"  base={BASE}  citations={SMOKE_INSERT_CITATIONS}")

    # Try reusing plan from latest frontiers full draft
    frontiers_drafts = sorted(OUT_DIR.glob("huNSG_QUAD_frontiers_*.json"), reverse=True)
    plan: dict | None = load_plan(frontiers_drafts[0] if frontiers_drafts else None)

    if plan is None:
        print("  No cached plan found — calling plan_paper …")
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
    else:
        print(f"  Reusing plan from {frontiers_drafts[0].name}")

    # Draft each figure sub-section at ~800 words
    sub_sections: list[dict] = []
    per_sub_refs: list[list] = []

    for sec_key, heading, manifests in FIG_SECTION_KEYS:
        fig_num = manifests[0]["figure_number"]
        print(f"\n  draft_section → {sec_key} (Fig {fig_num}, target ~800 words) …")
        t0 = time.time()
        draft_code, dr = post(
            "/draft_section",
            {
                "plan": plan,
                "section_key": "results",
                "section_heading_hint": heading,
                "target_journal": TARGET,
                "article_type": ARTICLE_TYPE,
                "section_word_target": 800,
                "auto_insert_citations": SMOKE_INSERT_CITATIONS,
                "force_author_year": True,
                "figure_quantitative_manifests": manifests,
            },
            timeout=420,
        )
        prose, refs, cite_meta = prose_from_draft(dr)
        per_sub_refs.append(refs)
        words = dr.get("approximate_words") or wc(prose)
        print(f"    HTTP {draft_code} {round(time.time()-t0,1)}s  words≈{words}  refs={len(refs)}")
        sub_sections.append({
            "fig_num": fig_num,
            "key": sec_key,
            "heading": heading,
            "text": prose,
            "http": draft_code,
            "words": words,
            "fill_count": len(dr.get("fill_markers_used") or []),
        })

    # Assemble into single Results block with H3-style headings
    assembled_parts: list[str] = []
    for sub in sub_sections:
        heading_line = sub["heading"].replace("Results — ", "### ")
        assembled_parts.append(f"{heading_line}\n\n{sub['text'].strip()}")
    results_text = "\n\n".join(assembled_parts)
    total_words = sum(s["words"] for s in sub_sections)

    merged_refs = merge_reference_lists(per_sub_refs)
    print(f"\n  Results assembled: {total_words} words across 4 sub-sections")
    print(f"  Merged refs: {len(merged_refs)}")

    ts = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    out_json = OUT_DIR / f"huNSG_QUAD_results_refined_{ts}.json"
    out_txt = OUT_DIR / f"huNSG_QUAD_results_refined_{ts}.txt"

    payload = {
        "protocol_version": "results_refine_per_fig_v1",
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "target_journal": TARGET,
        "total_words": total_words,
        "sub_sections": sub_sections,
        "assembled_results_text": results_text,
        "merged_reference_list": merged_refs,
    }
    out_json.write_text(json.dumps(payload, indent=2, ensure_ascii=False), encoding="utf-8")
    out_txt.write_text(results_text, encoding="utf-8")

    expert_results_words = 3233
    pct = round(total_words / expert_results_words * 100)
    print(f"\n  Results: {total_words} / {expert_results_words} expert words ({pct}%)")
    for sub in sub_sections:
        print(f"    Fig {sub['fig_num']}: {sub['words']} words  fills={sub['fill_count']}")
    print(f"\n  Saved: {out_json.name}")
    print(f"  Saved: {out_txt.name}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
