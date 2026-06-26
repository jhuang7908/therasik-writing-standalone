"""
Step 1 smoke: huNSG-QUAD abstract only → frontiers_immunology + research (BMRC).

Verifies journal_surface injects Background/Methods/Results/Conclusion subheadings.

Usage:
  WM_BASE=https://write.insynbio.com WM_AUTH=Admin:Rocky123 python smoke/run_abstract_bmrc_smoke.py
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
)
from run_ordered_smoke_v1545 import (  # noqa: E402
    BASE,
    SMOKE_INSERT_CITATIONS,
    get,
    post,
    prose_from_draft,
)

TARGET = "frontiers_immunology"
ARTICLE_TYPE = "research"
ABSTRACT_TARGET_WORDS = 280
BMRC_LABELS = ("Background:", "Methods:", "Results:", "Conclusion:", "Conclusions:")
OUT_DIR = Path(__file__).resolve().parent


def check_bmrc_structure(text: str) -> dict:
    found = [lab for lab in BMRC_LABELS if lab in text]
    has_bg = any(x in text for x in ("Background:",))
    has_m = "Methods:" in text
    has_r = "Results:" in text
    has_c = "Conclusion:" in text or "Conclusions:" in text
    return {
        "labels_found": found,
        "has_background": has_bg,
        "has_methods": has_m,
        "has_results": has_r,
        "has_conclusion": has_c,
        "bmrc_complete": has_bg and has_m and has_r and has_c,
    }


def main() -> int:
    ts = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    out_path = OUT_DIR / f"huNSG_QUAD_abstract_bmrc_{ts}.json"

    print(f"\n=== ABSTRACT BMRC SMOKE → {TARGET} ({ARTICLE_TYPE}) ===")
    print(f"  base={BASE}")
    print(f"  auto_insert_citations={SMOKE_INSERT_CITATIONS}")

    # Journal context preview
    prev_code, preview = get(
        f"/journal_context_preview?journal_key={TARGET}"
        f"&section_key=abstract&article_type={ARTICLE_TYPE}",
        timeout=60,
    )
    print(f"\n  journal_context_preview HTTP {prev_code}")
    if prev_code == 200:
        ctx = preview.get("block") or preview.get("context_block") or ""
        print(f"    context_chars={len(ctx)}  bmrc_in_context={'BMRC' in ctx or 'Background' in ctx}")

    # Plan
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
    plan_elapsed = round(time.time() - t0, 1)
    print(f"    HTTP {plan_code} {plan_elapsed}s")
    if plan_code != 200:
        print("PLAN FAILED:", json.dumps(plan)[:600])
        return 1

    # Draft abstract only
    print(f"\n  draft_section → abstract (target ~{ABSTRACT_TARGET_WORDS} words) …")
    t0 = time.time()
    draft_code, dr = post(
        "/draft_section",
        {
            "plan": plan,
            "section_key": "abstract",
            "target_journal": TARGET,
            "article_type": ARTICLE_TYPE,
            "section_word_target": ABSTRACT_TARGET_WORDS,
            "auto_insert_citations": SMOKE_INSERT_CITATIONS,
            "force_author_year": True,
        },
        timeout=420,
    )
    draft_elapsed = round(time.time() - t0, 1)
    prose, refs, cite_meta = prose_from_draft(dr)
    bmrc = check_bmrc_structure(prose)
    words = dr.get("approximate_words") or len(prose.split())

    print(f"    HTTP {draft_code} {draft_elapsed}s  words≈{words}")
    print(f"    BMRC check: {bmrc}")
    print(f"    cite_meta: {cite_meta}")

    # lint_prose
    lint_result: dict = {}
    if prose.strip():
        print("\n  lint_prose …")
        t0 = time.time()
        lcode, lint_result = post(
            "/lint_prose",
            {"text": prose, "target_journal": TARGET, "section_key": "abstract"},
            timeout=120,
        )
        print(
            f"    HTTP {lcode} {round(time.time()-t0,1)}s  "
            f"vale_available={lint_result.get('vale_available')}  "
            f"alerts={len(lint_result.get('alerts') or [])}"
        )

    payload = {
        "protocol_version": "abstract_bmrc_smoke_v1",
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "target_journal": TARGET,
        "article_type": ARTICLE_TYPE,
        "section_word_target": ABSTRACT_TARGET_WORDS,
        "auto_insert_citations": SMOKE_INSERT_CITATIONS,
        "journal_context_preview": {"http": prev_code, "preview": preview},
        "plan_paper": {
            "http": plan_code,
            "elapsed_s": plan_elapsed,
            "suggested_title": plan.get("suggested_title"),
        },
        "abstract": {
            "http": draft_code,
            "elapsed_s": draft_elapsed,
            "text": prose,
            "approximate_words": words,
            "bmrc_check": bmrc,
            "reference_count": len(refs),
            "reference_list": refs[:20],
            "citation_meta": cite_meta,
            "fill_markers_used": dr.get("fill_markers_used") or [],
        },
        "lint_prose": lint_result,
    }

    out_path.write_text(json.dumps(payload, indent=2, ensure_ascii=False), encoding="utf-8")
    txt_path = out_path.with_suffix(".txt")
    txt_path.write_text(prose, encoding="utf-8")

    print(f"\n  saved: {out_path.name}")
    print(f"  saved: {txt_path.name}")
    print("\n--- ABSTRACT PREVIEW ---\n")
    print(prose[:1200])
    if len(prose) > 1200:
        print("…")

    ok = draft_code == 200 and bmrc["bmrc_complete"]
    print(f"\n  OVERALL: {'PASS' if ok else 'FAIL'} (BMRC structure required)")
    return 0 if ok else 2


if __name__ == "__main__":
    raise SystemExit(main())
