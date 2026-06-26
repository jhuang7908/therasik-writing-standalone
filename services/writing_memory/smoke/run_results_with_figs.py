"""
Re-draft Results (and full paper) using figure quantitative manifests extracted from Fig 1-4.

Usage (VPS):
  cd /srv/services/writing_memory
  .venv/bin/python smoke/run_results_with_figs.py
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
    SMOKE_INSERT_CITATIONS,
    merge_reference_lists,
    post,
    prose_from_draft,
    step3_qc,
)

TARGET = "elife"

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

DATA_SUMMARY = """
Experimental details for section drafting:

Figure 1 — Engraftment (6 weeks post-HSPC):
- Peripheral blood Week 5: ~42% human CD45+; B cells ~65%, T cells ~0.2%, monocytes ~18%
- Peripheral blood Week 6: ~35% hCD45+; monocytes ~18%, DCs ~12%, granulocytes ~9%, neutrophils ~1%
- Spleen Week 6: ~65% hCD45+; monocytes ~20%, granulocytes ~21%, DCs ~4%
- Liver Week 6: ~55% hCD45+; granulocytes ~8%, monocytes ~3%, DCs ~3%
- Monocyte subsets (blood): classical ~47%, intermediate ~20%, non-classical ~10%
- n=6-9 mice per group; HSPC threshold >10% hCD45+ for inclusion

Figure 2 — NF-κB and type I IFN responses to IP/intranasal LPS:
- Serum IP LPS: hTNF ~50 ng/ml (***; ~25-50x vs PBS ~1-2 ng/ml), hIL-6 ~8 ng/ml (***; ~40x), hIL-8 ~10 ng/ml (***)
- Liver IP LPS: hTNF ~20 pg/mg (***; ~40x), hIL-6 ~2.5 pg/mg (***; ~80x), hIL-8 ~12 pg/mg (***)
- Lung intranasal LPS: hTNF ~100 pg/mg (***; ~10x), hIL-6 ~6 pg/mg (***; ~60x), hIL-8 ~25 pg/mg (***)
- Type I IFN: serum hIFNα2 no change (ns); hCXCL10 ~90 pg/ml (***; ~9x in serum)
- Liver hCXCL10 ~300 pg/mg (***; ~3.75x); lung hCXCL10 ns

Figure 3 — NLRP3 inflammasome activation (IP and intranasal LPS, serum/BAL/spleen/liver):
- Serum hIL-1β ~12-fold increase (PBS ~1 vs LPS ~12 pg/ml; ***); hIL-18 ns
- BAL hIL-1β ~125-fold increase (PBS ~0.02 vs LPS ~2.5 pg/ml; ***); hIL-18 ns in BAL
- Liver hIL-1β ~14-fold increase (***); hIL-18 ns
- NF-κB cytokines induced in all compartments (hTNF, hIL-6, hIL-8 all ***)
- hCXCL10 strongly induced in serum (~3.3x ***) and liver (~100x ***)
- Spleen/liver: granulocyte counts increased ~6x with LPS (***)

Figure 4 — MCC950 pharmacological validation:
- Pre-treatment: comparable hCD45+ (~40%), monocyte (~13-14%) proportions across groups (all ns)
- hIL-1β: LPS ~180 pg/ml; +MCC950 ~50 pg/ml (***reduction); PBS ~1 pg/ml
- hIL-18: LPS ~35 pg/ml; +MCC950 ~10 pg/ml (*); PBS ~2 pg/ml
- hTNF: LPS ~150 ng/ml; +MCC950 ~60 ng/ml (ns vs LPS); PBS ~0.05 ng/ml
- hIL-6: LPS ~18 ng/ml; +MCC950 ~12 ng/ml (ns vs LPS)
- Monocyte viability: monocyte % decreased PBS→LPS (~13%→~5%; ***), not rescued by MCC950
- Dead monocyte absolute counts: ns across groups (~0.3-0.4x10^4 cells/ml)
- Conclusion: MCC950 specifically blocks inflammasome cytokines without cytotoxicity
"""

EXPERIMENTAL_DESIGN = """
NSG-QUAD (JAX #028657): human IL-3, GM-CSF, SCF, CSF1 transgenes.
Human CD34+ HSPCs from cord blood; 50,000-100,000 cells i.v. at Week 0 post 100-150 cGy irradiation.
>10% hCD45+ threshold for successful humanization.
LPS: E. coli O111:B4 (Sigma L2630); IP 15 μg/mouse; intranasal 6 mg/kg; sacrifice 6 h post-challenge.
MCC950 (MCE HY-12815A) 50 mg/kg i.p. 1 h before LPS; vehicle control.
BAL: 4x 1 mL PBS lavage via tracheal cannula.
Cytokines: Luminex multiplex (TNF, IL-6, IL-8, IL-1β, IL-18, IFNα2, CXCL10).
Monocyte viability: flow cytometry (live/dead staining, BD LSRFortessa, FlowJo v10).
Statistics: 2-way ANOVA, log-transformed data, Sidak's multiple comparison; p<0.05.
Ethics: EC2022-003 (VIB-UGent); cord blood BC-06143.
"""

# Figure quantitative manifests (extracted from images)
FIG_MANIFESTS = [
    {
        "figure_number": 1,
        "panels": 8,
        "writing_manifest": [
            "Figure 1A: Experimental timeline showing HSPC isolation from umbilical cord blood, irradiation and injection at Week 0, assessment of human immune cell engraftment at Week 5, and inflammatory challenge at Week 6.",
            "Figure 1B: At Week 5 in peripheral blood, human immune cells comprised ~42% of total CD45+ cells (n=8). B cells represented ~65% of human immune cells (n=7), while T cells were minimal (~0.2%, n=7). Monocytes constituted ~18% of human immune cells (n=7).",
            "Figure 1C: At Week 6 in peripheral blood, human immune cells comprised ~35% of total CD45+ cells (n=8). Monocytes represented ~18% of human immune cells (n=7), dendritic cells ~12% (n=7), granulocytes ~9% (n=6), and neutrophils ~1.0% (n=7).",
            "Figure 1D: At Week 6 in spleen, human immune cells comprised ~65% of total CD45+ cells (n=9). Monocytes represented ~20% of human immune cells (n=7), granulocytes ~21% (n=8), dendritic cells ~4% (n=8).",
            "Figure 1E: At Week 6 in liver, human immune cells comprised ~55% of total CD45+ cells (n=8). Granulocytes represented ~8% of human immune cells (n=8), monocytes ~3% (n=8), dendritic cells ~3% (n=6).",
            "Figure 1F: In peripheral blood monocyte subset analysis: classical monocytes (CD14++CD16-) ~47% (n=9), intermediate (CD14++CD16+) ~20% (n=9), non-classical (CD14+CD16++) ~10% (n=7).",
        ],
    },
    {
        "figure_number": 2,
        "panels": 6,
        "writing_manifest": [
            "Figure 2A: IP LPS induced robust NF-κB responses in serum: hTNF ~50 ng/ml (***p<0.001 vs PBS ~1-2 ng/ml; ~25-50x increase), hIL-6 ~8 ng/ml (***; ~40x), hIL-8 ~10 ng/ml (***; ~10x); n~6-7/group.",
            "Figure 2B: Liver hTNF ~20 pg/mg (***; ~40x), hIL-6 ~2.5 pg/mg (***; ~80x), hIL-8 ~12 pg/mg (***; ~12x) after IP LPS; hIL-18 ns; n~6-7/group.",
            "Figure 2C: Intranasal LPS in lung: hTNF ~100 pg/mg (***; ~10x), hIL-6 ~6 pg/mg (***; ~60x), hIL-8 ~25 pg/mg (***; ~5x), hIL-1β ~3 pg/mg (***; ~30x); hIL-18 ns; n~6-7/group.",
            "Figure 2D: IP LPS did not alter serum hIFNα2 (ns), but induced hCXCL10 to ~90 pg/ml (***; ~9x vs PBS ~10 pg/ml); n~6/group.",
            "Figure 2E: Liver hCXCL10 ~300 pg/mg after IP LPS (***; ~3.75x vs PBS ~80 pg/mg); hIFNα2 ns; n~6/group.",
            "Figure 2F: Intranasal LPS in lung: hIFNα2 ns; hCXCL10 ns (PBS ~400 vs LPS ~600 pg/mg); n~6/group.",
        ],
    },
    {
        "figure_number": 3,
        "panels": 4,
        "writing_manifest": [
            "Figure 3A serum: hTNF ~10x increase (PBS ~0.2 vs LPS ~2.0 ng/ml; ***), hIL-6 ~250x (PBS ~0.01 vs LPS ~2.5 ng/ml; ***), hIL-8 ~16x (***). hIL-1β ~12-fold increase (PBS ~1.0 vs LPS ~12 pg/ml; ***); hIL-18 ns. hCXCL10 ~3.3x (PBS ~30 vs LPS ~100 ng/ml; ***); hIFNα2 ns.",
            "Figure 3B BAL: hTNF ~10x (PBS ~10 vs LPS ~100 pg/ml; ***), hIL-6 ~10x (***), hIL-8 ~5x (***). hIL-1β ~125x increase (PBS ~0.02 vs LPS ~2.5 pg/ml; ***); hIL-18 ns. hCXCL10 ~10x (PBS ~0.15 vs LPS ~1.5 ng/ml; ***); hIFNα2 ns.",
            "Figure 3C spleen: Granulocyte counts increased ~6.3x with LPS (PBS ~30 vs LPS ~190 cells/ml; ***). Monocyte subsets and DC counts showed no significant differences (all ns).",
            "Figure 3D liver: hTNF ~225x (PBS ~0.02 vs LPS ~4.5 pg/ml; ***), hIL-6 ~1100x (PBS ~0.5 vs LPS ~550 pg/ml; ***), hIL-8 ~260x (***). hIL-1β ~14x (PBS ~1.0 vs LPS ~14 pg/ml; ***); hIL-18 ns. hCXCL10 ~100x (PBS ~0.02 vs LPS ~2.0 ng/ml; ***); hIFNα2 ns.",
        ],
    },
    {
        "figure_number": 4,
        "panels": 12,
        "writing_manifest": [
            "Figure 4A-D: Pre-treatment baseline: comparable hCD45+ (~40%), monocyte (~13-14%) proportions across PBS, LPS, and LPS+MCC950 groups (all ns).",
            "Figure 4E: hIL-1β: PBS ~1 pg/ml; LPS ~180 pg/ml (***vs PBS); LPS+MCC950 ~50 pg/ml (***reduction vs LPS alone).",
            "Figure 4F: hIL-18: PBS ~2 pg/ml; LPS ~35 pg/ml (***); LPS+MCC950 ~10 pg/ml (*p<0.05 reduction vs LPS).",
            "Figure 4G: hTNF: PBS ~0.05 ng/ml; LPS ~150 ng/ml (***); LPS+MCC950 ~60 ng/ml (ns vs LPS — not significantly reduced).",
            "Figure 4H: hIL-6: PBS ~0.015 ng/ml; LPS ~18 ng/ml (***); LPS+MCC950 ~12 ng/ml (ns vs LPS).",
            "Figure 4I-J: Monocyte frequency decreased PBS~13%→LPS~5% (***); absolute counts PBS~6×10^4→LPS~2×10^4 cells/ml (**); neither restored by MCC950 (ns vs LPS).",
            "Figure 4K-L: Dead monocyte percentage: PBS ~2%; LPS ~14% (***); LPS+MCC950 ~15% (*slightly higher vs LPS). Absolute dead monocyte counts ns across all groups (~0.3-0.4×10^4 cells/ml).",
        ],
    },
]

SECTION_TARGETS = {
    "abstract":     250,
    "introduction": 580,
    "methods":     1400,
    "results":     3200,
    "discussion":  1950,
}


def main() -> int:
    print(f"\n=== FULL DRAFT v1546b: huNSG-QUAD + FIGURE MANIFESTS ===")
    print(f"  auto_insert_citations={SMOKE_INSERT_CITATIONS}")

    # ── Plan ──────────────────────────────────────────────────────────────────
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

    # ── Sections ──────────────────────────────────────────────────────────────
    sections: list[dict] = []
    per_section_refs: list[list] = []

    for sec in ("abstract", "introduction", "methods", "results", "discussion"):
        target_words = SECTION_TARGETS.get(sec)
        # pass figure manifests only for results; description for other sections
        manifests = FIG_MANIFESTS if sec == "results" else None
        print(f"\n  draft_section → {sec} (target ~{target_words}) …")
        t0 = time.time()
        body: dict = {
            "plan": plan,
            "section_key": sec,
            "target_journal": TARGET,
            "article_type": "research",
            "auto_insert_citations": SMOKE_INSERT_CITATIONS,
            "force_author_year": True,
            "section_word_target": target_words,
        }
        if manifests:
            body["figure_quantitative_manifests"] = manifests

        code, dr = post("/draft_section", body, timeout=480)
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

    merged_refs = merge_reference_lists(per_section_refs)
    print(f"\n  merged_reference_count = {len(merged_refs)}")

    qc = step3_qc(sections, plan, TARGET, "full_draft_fig_v1546b", reference_list=merged_refs)

    def wc(t: str) -> int:
        return len(re.findall(r"[A-Za-z0-9'-]+", t or ""))

    wc_by = {s["key"]: wc(s["text"]) for s in sections}
    wc_total = sum(wc_by.values())
    print(f"\n  word_count = {wc_by}  total={wc_total}")

    bench = {"abstract": 251, "introduction": 565, "methods": 1375, "results": 3233, "discussion": 1927, "total": 7351, "refs": 44}
    print("\n  === Comparison vs expert (Front. Immunol. 2024;15:1419117) ===")
    for k in ("abstract","introduction","methods","results","discussion"):
        pct = round(wc_by[k] / bench[k] * 100)
        print(f"  {k:<14} {wc_by[k]:>5} / {bench[k]:>5} ({pct}%)")
    print(f"  {'TOTAL':<14} {wc_total:>5} / {bench['total']:>5} ({round(wc_total/bench['total']*100)}%)")
    print(f"  {'References':<14} {len(merged_refs):>5} / {bench['refs']:>5} ({round(len(merged_refs)/bench['refs']*100)}%)")

    report = {
        "protocol_version": "v1546b_full_draft_with_figures",
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "target_journal": TARGET,
        "auto_insert_citations": SMOKE_INSERT_CITATIONS,
        "section_word_targets": SECTION_TARGETS,
        "merged_reference_count": len(merged_refs),
        "merged_reference_list": merged_refs,
        "word_count_by_section": wc_by,
        "word_count_total": wc_total,
        "expert_benchmark": {
            "source": "Front. Immunol. 2024;15:1419117", "doi": "10.3389/fimmu.2024.1419117",
            "ref_count": 44, "word_total": 7351,
            "words_by_section": {k: bench[k] for k in ("abstract","introduction","methods","results","discussion")},
        },
        "qc": qc,
        "plan": plan,
        "sections": sections,
    }

    ts = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    out = Path(__file__).parent / f"huNSG_QUAD_figdraft_{ts}.json"
    out.write_text(json.dumps(report, indent=2, ensure_ascii=False), encoding="utf-8")
    print(f"\nQC overall={qc.get('overall_score')} {qc.get('overall_verdict')}")
    print(f"Wrote {out}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
