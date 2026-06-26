"""
Full-length huNSG-QUAD draft targeting expert-article word count / citation density.

Target metrics (based on Front. Immunol. 2024;15:1419117 [verified]):
  Abstract       ~250 words
  Introduction   ~550 words   ≥5  [CITE:]
  Methods       ~1350 words   ≥8  [CITE:]
  Results       ~3200 words   ≥10 [CITE:]  (quantitative data → [FILL:])
  Discussion    ~1950 words   ≥9  [CITE:]
  Total body    ~7300 words   ≥44 references

Usage (VPS):
  cd /srv/services/writing_memory
  .venv/bin/python smoke/run_full_draft_v1546.py

Or fast (no citation lookup):
  WM_SMOKE_CITATIONS=0 .venv/bin/python smoke/run_full_draft_v1546.py
"""

from __future__ import annotations

import json
import sys
import time
from datetime import datetime, timezone
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
from run_ordered_smoke_v1545 import (  # noqa: E402
    SMOKE_INSERT_CITATIONS,
    merge_reference_lists,
    post,
    prose_from_draft,
    step3_qc,
)

TARGET = "elife"  # eLife style profile: 8000-word budget; PNAS-level hedging acceptable
# Note: targeting eLife profile to unlock longer per-section generation.
# The paper is formatted for Frontiers in Immunology (similar open-access scope).

HU_ABSTRACT = (
    "Background: Dysregulated innate immune responses underlie multiple inflammatory diseases, "
    "but clinical translation of preclinical innate immunity research in mice is hampered by the "
    "difficulty of studying human inflammatory reactions in an in vivo context. We therefore sought "
    "to establish in vivo human inflammatory responses in NSG-QUAD mice that express four human "
    "myelopoiesis transgenes to improve engraftment of a human innate immune system.\n\n"
    "Methods: We reconstituted NSG-QUAD mice with human hematopoietic stem and progenitor cells "
    "(HSPCs), after which we evaluated human myeloid cell development and subsequent human responses "
    "to systemic and local lipopolysaccharide (LPS) challenges.\n\n"
    "Results: NSG-QUAD mice already displayed engraftment of human monocytes, dendritic cells and "
    "granulocytes in peripheral blood, spleen and liver at 6 weeks after HSPC injection. "
    "HuNSG-QUAD mice responded to intraperitoneal and intranasal LPS with NF-κB-dependent cytokines, "
    "type I interferon, and NLRP3 inflammasome-mediated IL-1β and IL-18. MCC950 specifically "
    "abrogated IL-1β and IL-18 without affecting monocyte death.\n\n"
    "Conclusions: HuNSG-QUAD mice are competent for studying NF-κB, type I interferon and "
    "inflammasome effectors of human innate immunity in vivo."
)

# Rich experimental detail extracted from expert article (published data, used as grounding input)
DATA_SUMMARY = """
Experimental details (grounding — fill exact numbers from your data):

Engraftment (Figure 1):
- NSG-QUAD mice sublethally irradiated (100–150 cGy), i.v. injection of 50,000–100,000 human CD34+ HSPCs
- Peripheral blood, spleen and liver assessed by multicolor flow cytometry at 6 weeks post-injection
- Human CD45+ threshold for successful humanization: >10%
- Human myeloid subsets identified: classical (CD14++CD16-), intermediate (CD14++CD16+), and
  non-classical (CD14+CD16++) monocytes; conventional DCs (cDC); plasmacytoid DCs (pDC); neutrophils (CD66b+)
- [FILL: % human CD45+ cells in peripheral blood, spleen, liver; absolute subset numbers per organ]

NF-κB and type I IFN response to LPS (Figure 2):
- IP injection: 15 μg LPS from E. coli O111:B4 (Sigma L2630) in sterile PBS; sacrifice at 6 h
- Intranasal instillation: 6 mg/kg LPS; BAL fluid and serum collected
- NF-κB-dependent cytokines measured by Luminex multiplex: TNF-α, IL-6, IL-12p70, IL-8
- Type I IFN response: IFN-α quantified in serum; induction also confirmed with R848 (TLR7/8 agonist)
- [FILL: cytokine concentrations (pg/mL) and fold-changes; IFN-α levels; comparison IP vs IN routes]

NLRP3 inflammasome (Figure 3):
- IL-1β and IL-18 measured by ELISA in serum, BAL, spleen and liver supernatants
- Two-signal model confirmed: LPS provides both priming (signal 1) and activating (signal 2) stimuli
- [FILL: IL-1β and IL-18 concentrations; kinetics; comparison to NF-κB cytokines]

MCC950 pharmacological validation (Figure 4):
- MCC950 (NLRP3 inhibitor, 50 mg/kg i.p., MCE HY-12815A) administered 1 h before LPS
- IL-1β and IL-18 production specifically abrogated; TNF-α and IL-6 unaffected
- Human monocyte viability unchanged (flow cytometry, live/dead dye)
- LPS-induced human NLRP3 inflammasome cytokine release occurs independently of cell death (pyroptosis)
- [FILL: % inhibition of IL-1β/IL-18; statistical comparisons; viability percentages]
"""

EXPERIMENTAL_DESIGN = """
NSG-QUAD (NOD.Cg-Prkdcscid Il2rgtm1Wjl Tg(CMV-IL3,CSF2,KITLG)1Eav Tg(CSF1)3Sz/J; JAX #028657)
expressing human IL-3, GM-CSF, SCF (hemizygous) and CSF1 (hemizygous). Crossed from NSG-SGM3 × NSG-CSF1.
Human CD34+ HSPCs from umbilical cord blood (Cord Blood Bank; Lymphoprep density gradient + CD34 MACS).
Flow cytometry: BD LSRFortessa; FlowJo v10.
Cytokine multiplex: Luminex-based panel; BAL collected by 4× 1 mL PBS lavage.
Statistics: two-way ANOVA on log-transformed data; Sidak multiple comparison; p<0.05 threshold.
Ethics: VIB-UGent IACUC EC2022-003; human cord blood BC-06143 (Medical Ethical Committee Ghent UZ).
"""

# Per-section word targets matching expert article
SECTION_TARGETS = {
    "abstract":     250,
    "introduction": 580,
    "methods":     1400,
    "results":     3200,
    "discussion":  1950,
}


def main() -> int:
    print(f"\n=== FULL DRAFT v1546: huNSG-QUAD → {TARGET} ===")
    print(f"  auto_insert_citations={SMOKE_INSERT_CITATIONS}")
    print(f"  section_word_targets={SECTION_TARGETS}")

    # ── Plan ─────────────────────────────────────────────────────────────────
    print("\n  plan_paper …")
    t0 = time.time()
    code, plan = post("/plan_paper", {
        "user_intent": HU_ABSTRACT,
        "article_type": "research",
        "target_journal": TARGET,
        "data_summary": DATA_SUMMARY,
        "experimental_design": EXPERIMENTAL_DESIGN,
    }, timeout=360)
    print(f"    plan HTTP {code} {round(time.time()-t0,1)}s")
    if code != 200:
        print("PLAN FAILED:", plan)
        return 1

    # ── Sections ─────────────────────────────────────────────────────────────
    sections: list[dict] = []
    per_section_refs: list[list[str]] = []

    for sec in ("abstract", "introduction", "methods", "results", "discussion"):
        target_words = SECTION_TARGETS.get(sec)
        print(f"\n  draft_section → {sec} (target ~{target_words} words) …")
        t0 = time.time()
        body: dict = {
            "plan": plan,
            "section_key": sec,
            "target_journal": TARGET,
            "article_type": "research",
            "auto_insert_citations": SMOKE_INSERT_CITATIONS,
            "force_author_year": True,
        }
        if target_words:
            body["section_word_target"] = target_words

        code, dr = post("/draft_section", body, timeout=420)
        prose, refs, cite_meta = prose_from_draft(dr)
        per_section_refs.append(refs)
        fills = dr.get("fill_markers_used") or []
        approx = dr.get("approximate_words") or 0

        sections.append({
            "key": sec,
            "title": sec.title(),
            "text": prose,
            "http": code,
            "elapsed_s": round(time.time() - t0, 1),
            "words": approx,
            "target_words": target_words,
            "fill_count": len(fills),
            "reference_count": len(refs),
            "citation_meta": cite_meta,
        })
        print(
            f"    HTTP {code} {sections[-1]['elapsed_s']}s  "
            f"words={approx}/{target_words}  fills={len(fills)}  "
            f"refs={len(refs)}  cite_left={cite_meta.get('cite_placeholders_left')}"
        )

    # ── Merge references ─────────────────────────────────────────────────────
    merged_refs = merge_reference_lists(per_section_refs)
    print(f"\n  merged_reference_count = {len(merged_refs)}")

    # ── QC ───────────────────────────────────────────────────────────────────
    qc = step3_qc(sections, plan, TARGET, "full_draft_v1546", reference_list=merged_refs)

    # ── Word count summary ────────────────────────────────────────────────────
    import re
    def wc(t: str) -> int:
        return len(re.findall(r"[A-Za-z0-9'-]+", t or ""))

    wc_summary = {s["key"]: wc(s["text"]) for s in sections}
    wc_total = sum(wc_summary.values())
    print(f"\n  word_count_by_section = {wc_summary}")
    print(f"  word_count_total = {wc_total}")

    # ── Save ─────────────────────────────────────────────────────────────────
    report = {
        "protocol_version":      "v1546_full_draft",
        "generated_at":          datetime.now(timezone.utc).isoformat(),
        "target_journal":        TARGET,
        "auto_insert_citations": SMOKE_INSERT_CITATIONS,
        "section_word_targets":  SECTION_TARGETS,
        "merged_reference_count": len(merged_refs),
        "merged_reference_list": merged_refs,
        "word_count_by_section": wc_summary,
        "word_count_total":      wc_total,
        "expert_benchmark": {
            "source":     "Front. Immunol. 2024;15:1419117",
            "doi":        "10.3389/fimmu.2024.1419117",
            "ref_count":  44,
            "word_total": 7351,
            "words_by_section": {
                "abstract": 251, "introduction": 565,
                "methods": 1375, "results": 3233, "discussion": 1927,
            },
        },
        "qc":      qc,
        "plan":    plan,
        "sections": sections,
    }

    ts = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    out = Path(__file__).parent / f"huNSG_QUAD_full_{ts}.json"
    out.write_text(json.dumps(report, indent=2, ensure_ascii=False), encoding="utf-8")

    print(f"\nQC overall={qc.get('overall_score')} {qc.get('overall_verdict')}")
    print(f"  failed={qc.get('dimensions_failed')}")
    print(f"Words: {wc_total} / expert 7351 ({round(wc_total/7351*100)}%)")
    print(f"Refs:  {len(merged_refs)} / expert 44 ({round(len(merged_refs)/44*100)}%)")
    print(f"Wrote {out}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
