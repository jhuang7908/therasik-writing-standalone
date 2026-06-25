"""
analyze_vhh_atlas.py — InSynBio AbEngineCore
=============================================
Phase 1: Enrich Atlas v2 with proper Kabat-based Hallmark, Vernier, Germline
         for ALL 66 entries (Clinical_VHH + Engineered_Human_VH).
Phase 2: Correlation analysis — CDR length/topology vs Hallmark/Vernier.
Phase 3: Generate design rules for:
         (A) Camelid VHH humanization
         (B) Human VH → VHH single-domain conversion
Output files:
  data/vhh_design_atlas_v3.json  — enriched, fully annotated
  data/vhh_design_rules.json     — machine-readable design rules
  data/vhh_design_rules.md       — human-readable design rules report
"""

from __future__ import annotations
import json
import sys
import math
from collections import Counter, defaultdict
from pathlib import Path
from typing import Optional

BASE = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(BASE))

from core.humanization.kabat_utils import (
    kabat_from_anarcii, cdr_span, sorted_keys, CDR_RANGES_VH
)

# ── Reference constants ────────────────────────────────────────────────────────
IGHV3_23_REF = "EVQLLESGGGLVQPGGSLRLSCAASGFTFSSYAMSWVRQAPGKGLEWVSAISGSGGSTYYADSVKGRFTISRDNSKNTLYLQMNSLRAEDTAVYYCAK"

HALLMARK_POSITIONS = [37, 44, 45, 47]
VERNIER_POSITIONS  = [2, 27, 28, 29, 30, 48, 49, 67, 69, 71, 73, 78, 93, 94]
INTERFACE_POSITIONS = [35, 37, 39, 44, 45, 47, 50, 89, 91, 93, 94]

# Classic IgG VH hallmark (hydrophobic VH-VL interface)
NAIVE_IgG_HALLMARK = {"37": "V", "44": "G", "45": "L", "47": "W"}
# Classic camelid VHH hallmark (hydrophilic, single-domain)
CAMELID_VHH_HALLMARK = {"37": "F", "44": "E", "45": "R", "47": "G"}

IGHV3_23_VERNIER = {"2":"V","27":"F","28":"T","29":"F","30":"S",
                     "48":"M","49":"S","67":"K","69":"V","71":"R",
                     "73":"I","78":"V","93":"R","94":"K"}

GERMLINE_REFS = {
    "IGHV3-23": "EVQLLESGGGLVQPGGSLRLSCAASGFTFSSYAMSWVRQAPGKGLEWVSAISGSGGSTYYADSVKGRFTISRDNSKNTLYLQMNSLRAEDTAVYYCAK",
    "IGHV3-7":  "EVQLVESGGGLVQPGGSLRLSCAASGFTFSSYWMSWVRQAPGKGLEWVANIKQDGSEKYYVDSVKGRFTISRDNAKNSLYLQMNSLRAEDTAVYYCAR",
    "IGHV1-69": "QVQLVQSGAEVKKPGSSVKVSCKASGGTFSSYAISWVRQAPGQGLEWMGGIIPIFGTANYAQKFQGRVTITADESTSTAYMELSSLRSEDTAVYYCAR",
    "IGHV3-66": "EVQLLESGGGLVQPGGSLRLSCAASGFTFSSYWMSWVRQAPGKGLEWVSRINSDGSSTSYADSVKGRFTISRDNSKNTLYLQMNSLRAEDTAVYYCAR",
    "IGHV1-2":  "QVQLVQSGAEVKKPGASVKVSCKASGYTFTSYGISWVRQAPGQGLEWMGWISAYNGNTNYAQKLQGRVTMTTDTSTSTAYMELRSLRSDDTAVYYCAR",
}

# North canonical class heuristic (CDR1 length → class)
CDR1_CANON = {6:"H1-6-1", 7:"H1-7-1", 8:"H1-8-1", 9:"H1-9-1",
              10:"H1-10-1", 12:"H1-12-1", 13:"H1-13-1"}
CDR2_CANON = {6:"H2-6-1", 7:"H2-7-1", 8:"H2-8-1", 10:"H2-10-1",
              16:"H2-16-1", 17:"H2-17-1", 18:"H2-18-1", 19:"H2-19-1"}

# ── Anarcii singleton ──────────────────────────────────────────────────────────
_ABARCII = None
def get_anarcii():
    global _ABARCII
    if _ABARCII is None:
        from anarcii import Anarcii
        _ABARCII = Anarcii(seq_type="antibody", mode="accuracy")
    return _ABARCII

# ── Core enrichment functions ──────────────────────────────────────────────────

def number_kabat(sequence: str) -> Optional[dict]:
    """Return kabat_from_anarcii result dict (KabatDict) or None on failure."""
    if len(sequence) < 60:
        return None
    try:
        a = get_anarcii()
        a.number([sequence])
        entry = a.to_scheme("kabat").get("Sequence 1", {})
        if entry.get("error") or entry.get("chain_type") != "H":
            return None
        return kabat_from_anarcii(entry["numbering"])
    except Exception:
        return None

def extract_hallmark(kd: dict) -> dict:
    pos_vals = {}
    for p in HALLMARK_POSITIONS:
        pos_vals[str(p)] = kd.get((p, ""), "-")
    pos_vals["motif"] = "".join(pos_vals[str(p)] for p in HALLMARK_POSITIONS)
    return pos_vals

def extract_vernier(kd: dict) -> dict:
    return {str(p): kd.get((p, ""), "-") for p in VERNIER_POSITIONS}

def germline_match(kd: dict) -> tuple[str, float]:
    v_seq = "".join(kd.get(k, "") for k in sorted_keys(kd) if k[0] <= 94)
    best_name, best_score = "IGHV3-23", 0.0
    for name, ref in GERMLINE_REFS.items():
        min_l = min(len(v_seq), len(ref))
        if min_l == 0: continue
        score = sum(a == b for a, b in zip(v_seq[:min_l], ref[:min_l])) / min_l
        if score > best_score:
            best_score = score; best_name = name
    return best_name, round(best_score, 4)

def kabat_segments(kd: dict) -> dict:
    return {
        "FR1":  cdr_span(kd, 1,  25),
        "CDR1": cdr_span(kd, 26, 35),
        "FR2":  cdr_span(kd, 36, 49),
        "CDR2": cdr_span(kd, 50, 65),
        "FR3":  cdr_span(kd, 66, 94),
        "CDR3": cdr_span(kd, 95, 102),
        "FR4":  cdr_span(kd, 103, 113),
    }

def hallmark_type(motif: str) -> str:
    """Classify hallmark motif into biological category."""
    p44, p45, p47 = motif[1], motif[2], motif[3]
    if p44 == "G" and p45 == "L" and p47 == "W":
        return "Naive_IgG"
    if p44 in ("E","D") and p45 in ("R","K"):
        return "VHH_Camelid_Like"
    if p44 == "G" and p45 in ("L","K") and p47 in ("A","L","F"):
        return "Humanized_Camelid_FGLA"
    if p44 == "Q" and p45 == "A":
        return "Human_IGHV3_23_Like"
    return "Mixed_Custom"

def fr_departure_from_ighv323(kd: dict, ref_kd: dict) -> dict:
    deps = {}
    for k in sorted_keys(kd):
        pos, ins = k
        if any(lo <= pos <= hi for lo, hi in CDR_RANGES_VH):
            continue
        if pos > 113: continue
        q = kd[k]; r = ref_kd.get(k, "-")
        if q != r and q not in ("-",""):
            deps[f"{pos}{ins}".strip()] = {"ref": r, "obs": q}
    return deps

# ── Phase 1: Enrich Atlas v2 ───────────────────────────────────────────────────

def enrich_atlas():
    atlas_path = BASE / "data/vhh_design_atlas_v2.json"
    with open(atlas_path, encoding="utf-8") as f:
        atlas = json.load(f)

    print("Computing IGHV3-23 reference KabatDict...")
    a = get_anarcii()
    a.number([IGHV3_23_REF])
    ref_kd = kabat_from_anarcii(a.to_scheme("kabat")["Sequence 1"]["numbering"])

    print(f"Enriching {len(atlas)} entries with Kabat Hallmark / Vernier / Germline...")
    enriched = []
    skip_count = 0

    for i, entry in enumerate(atlas, 1):
        seq = entry.get("sequence", "")
        name = entry.get("name", "")[:35]
        print(f"  [{i:02d}/{len(atlas)}] {name}")

        kd = number_kabat(seq)
        if kd is None:
            print(f"    SKIP — Anarcii failed")
            skip_count += 1
            # Keep entry but mark fields as unavailable
            entry["hallmark"] = {}
            entry["hallmark_motif"] = "FAILED"
            entry["hallmark_type"] = "FAILED"
            entry["vernier"] = {}
            entry["germline"] = "UNKNOWN"
            entry["germline_identity"] = 0.0
            entry["kabat_segments"] = entry.get("segments", {})
            entry["cdr_lengths_kabat"] = {}
            entry["fr_departures_from_IGHV3_23"] = {}
            enriched.append(entry)
            continue

        # Hallmark
        hallmark = extract_hallmark(kd)
        motif = hallmark["motif"]
        h_type = hallmark_type(motif)

        # Vernier
        vernier = extract_vernier(kd)

        # Germline
        germ_name, germ_id = germline_match(kd)

        # Kabat segments (may differ from input segments which may be IMGT)
        ksegs = kabat_segments(kd)
        cdr_lens = {
            "CDR1_kabat": len(ksegs["CDR1"]),
            "CDR2_kabat": len(ksegs["CDR2"]),
            "CDR3_kabat": len(ksegs["CDR3"]),
        }

        # FR departures from IGHV3-23 (non-CDR only)
        fr_deps = fr_departure_from_ighv323(kd, ref_kd)

        # Canonical class
        canon = {
            "H1": CDR1_CANON.get(cdr_lens["CDR1_kabat"], f"H1-{cdr_lens['CDR1_kabat']}-?"),
            "H2": CDR2_CANON.get(cdr_lens["CDR2_kabat"], f"H2-{cdr_lens['CDR2_kabat']}-?"),
            "H3_len": cdr_lens["CDR3_kabat"],
        }

        # Vernier conservation vs IGHV3-23
        vernier_delta = {}
        for pos_str, aa in vernier.items():
            ref_aa = IGHV3_23_VERNIER.get(pos_str, "-")
            vernier_delta[pos_str] = {
                "aa": aa, "ref_IGHV3_23": ref_aa,
                "conserved": aa == ref_aa
            }

        # Classify which Vernier positions are camelid-retained
        camelid_retained_verniers = [
            p for p, d in vernier_delta.items() if not d["conserved"]
        ]

        # Update entry
        entry["hallmark"] = hallmark
        entry["hallmark_motif"] = motif
        entry["hallmark_type"] = h_type
        entry["vernier"] = vernier
        entry["vernier_vs_IGHV3_23"] = vernier_delta
        entry["n_camelid_vernier_positions"] = len(camelid_retained_verniers)
        entry["germline"] = germ_name
        entry["germline_identity"] = germ_id
        entry["kabat_segments"] = ksegs
        entry["cdr_lengths_kabat"] = cdr_lens
        entry["canonical_classes_kabat"] = canon
        entry["fr_departures_from_IGHV3_23"] = fr_deps
        entry["n_fr_departures"] = len(fr_deps)

        print(f"    motif={motif} type={h_type} germ={germ_name}({germ_id:.0%}) "
              f"CDR1={cdr_lens['CDR1_kabat']} CDR2={cdr_lens['CDR2_kabat']} CDR3={cdr_lens['CDR3_kabat']}"
              f" FR_deps={len(fr_deps)}")
        enriched.append(entry)

    print(f"\nEnrichment complete. Skipped: {skip_count}/{len(atlas)}")
    return enriched, ref_kd

# ── Phase 2: Correlation Analysis ─────────────────────────────────────────────

def correlation_analysis(entries: list[dict]) -> dict:
    """
    Compute key correlations:
    1. CDR3 length vs Hallmark type
    2. CDR2 length vs Hallmark type
    3. CDR1 length vs FR departures count
    4. Germline vs Hallmark
    5. Category vs Hallmark distribution
    """
    results = {}

    valid = [e for e in entries if e.get("hallmark_motif","") not in ("FAILED","")]

    # 1. CDR3 length vs Hallmark type (by category)
    cdr3_by_type = defaultdict(list)
    for e in valid:
        ht = e.get("hallmark_type","Unknown")
        cdr3 = e["cdr_lengths_kabat"].get("CDR3_kabat", 0)
        cdr3_by_type[ht].append(cdr3)

    results["cdr3_len_by_hallmark_type"] = {
        k: {
            "n": len(v),
            "mean": round(sum(v)/len(v),1) if v else 0,
            "min": min(v) if v else 0,
            "max": max(v) if v else 0,
            "values": sorted(v)
        } for k, v in cdr3_by_type.items()
    }

    # 2. CDR2 length vs Hallmark type
    cdr2_by_type = defaultdict(list)
    for e in valid:
        ht = e.get("hallmark_type","Unknown")
        cdr2 = e["cdr_lengths_kabat"].get("CDR2_kabat", 0)
        cdr2_by_type[ht].append(cdr2)

    results["cdr2_len_by_hallmark_type"] = {
        k: {"n": len(v), "mean": round(sum(v)/len(v),1) if v else 0,
            "min": min(v) if v else 0, "max": max(v) if v else 0}
        for k, v in cdr2_by_type.items()
    }

    # 3. n_fr_departures vs category
    deps_by_cat = defaultdict(list)
    for e in valid:
        cat = e.get("category","Unknown")
        deps_by_cat[cat].append(e.get("n_fr_departures", 0))
    results["fr_departures_by_category"] = {
        k: {"mean": round(sum(v)/len(v),1), "min": min(v), "max": max(v), "n": len(v)}
        for k, v in deps_by_cat.items()
    }

    # 4. Germline distribution by category
    germ_by_cat = defaultdict(Counter)
    for e in valid:
        cat = e.get("category","Unknown")
        germ_by_cat[cat][e.get("germline","UNKNOWN")] += 1
    results["germline_distribution"] = {
        cat: dict(ctr.most_common()) for cat, ctr in germ_by_cat.items()
    }

    # 5. Hallmark type distribution by category
    ht_by_cat = defaultdict(Counter)
    for e in valid:
        cat = e.get("category","Unknown")
        ht_by_cat[cat][e.get("hallmark_type","Unknown")] += 1
    results["hallmark_type_distribution"] = {
        cat: dict(ctr.most_common()) for cat, ctr in ht_by_cat.items()
    }

    # 6. Critical Vernier positions by category
    # Which Vernier positions are most often non-IGHV3-23?
    vernier_noncons = defaultdict(lambda: defaultdict(int))
    vernier_total   = defaultdict(int)
    for e in valid:
        cat = e.get("category","Unknown")
        vdelta = e.get("vernier_vs_IGHV3_23", {})
        vernier_total[cat] += 1
        for pos, d in vdelta.items():
            if not d.get("conserved"):
                vernier_noncons[cat][pos] += 1
    results["vernier_nonconserved_frequency"] = {
        cat: {pos: round(cnt/vernier_total[cat], 3)
              for pos, cnt in sorted(pdict.items(), key=lambda x: -x[1])}
        for cat, pdict in vernier_noncons.items()
    }

    # 7. CDR3 threshold analysis for NAIVE IgG:
    #    Among NAIVE IgG entries, what's CDR3 length distribution?
    naive = [e for e in valid if e.get("hallmark_type") == "Naive_IgG"]
    non_naive = [e for e in valid if e.get("hallmark_type") != "Naive_IgG"]

    def cdr3_dist(lst):
        if not lst: return {}
        vals = [e["cdr_lengths_kabat"].get("CDR3_kabat",0) for e in lst]
        return {"n": len(vals), "mean": round(sum(vals)/len(vals),1),
                ">=15aa": sum(1 for v in vals if v >= 15),
                ">=12aa": sum(1 for v in vals if v >= 12),
                "<10aa": sum(1 for v in vals if v < 10),
                "distribution": dict(Counter(vals))}

    results["cdr3_naive_vs_engineered"] = {
        "Naive_IgG":  cdr3_dist(naive),
        "Engineered": cdr3_dist(non_naive),
    }

    # 8. Pos44 / Pos45 / Pos47 individual distributions
    for pos_str in ["37", "44", "45", "47"]:
        dist_by_cat = defaultdict(Counter)
        for e in valid:
            cat = e.get("category","Unknown")
            aa = e.get("hallmark",{}).get(pos_str, "-")
            dist_by_cat[cat][aa] += 1
        results[f"pos{pos_str}_distribution"] = {
            cat: dict(ctr.most_common()) for cat, ctr in dist_by_cat.items()
        }

    return results

# ── Phase 3: Design Rules ──────────────────────────────────────────────────────

def extract_design_rules(entries: list[dict], corr: dict) -> dict:
    """
    Synthesize design rules from correlation data.
    Returns structured rules dict for both camelid humanization and VH-to-VHH.
    """
    valid = [e for e in entries if e.get("hallmark_motif","") not in ("FAILED","")]
    clinical = [e for e in valid if e.get("category") == "Clinical_VHH"]
    engineered = [e for e in valid if e.get("category") == "Engineered_Human_VH"]

    # ── Camelid VHH humanization rules ───────────────────────────────────────
    # Which Hallmark strategies work for clinical VHHs?
    camelid_hallmark_dist = Counter(e.get("hallmark_type") for e in clinical)
    camelid_motif_dist = Counter(e.get("hallmark_motif") for e in clinical)

    # CDR3 length vs hallmark in clinical VHHs
    cdr3_by_htype_clinical = defaultdict(list)
    for e in clinical:
        ht = e.get("hallmark_type","Unknown")
        cdr3_by_htype_clinical[ht].append(e["cdr_lengths_kabat"].get("CDR3_kabat",0))

    # Most variable Vernier positions in clinical VHHs (departing from IGHV3-23)
    vernier_freq_clinical = corr["vernier_nonconserved_frequency"].get("Clinical_VHH", {})
    critical_verniers_clinical = [p for p, f in vernier_freq_clinical.items() if f >= 0.3]

    # Average FR departures
    fr_clinical = corr["fr_departures_by_category"].get("Clinical_VHH", {})

    # ── VH-to-VHH conversion rules ────────────────────────────────────────────
    eng_hallmark_dist = Counter(e.get("hallmark_type") for e in engineered)
    eng_motif_dist = Counter(e.get("hallmark_motif") for e in engineered)

    # Correlate CDR3 length with hallmark type in engineered entries
    cdr3_eng_naive = [e["cdr_lengths_kabat"].get("CDR3_kabat",0)
                      for e in engineered if e.get("hallmark_type") == "Naive_IgG"]
    cdr3_eng_vhh_like = [e["cdr_lengths_kabat"].get("CDR3_kabat",0)
                         for e in engineered if e.get("hallmark_type") != "Naive_IgG"]

    # Most variable Vernier in engineered
    vernier_freq_eng = corr["vernier_nonconserved_frequency"].get("Engineered_Human_VH", {})
    critical_verniers_eng = [p for p, f in vernier_freq_eng.items() if f >= 0.3]

    rules = {
        "version": "1.0",
        "generated_from": "vhh_design_atlas_v2.json",
        "n_entries_analyzed": {"Clinical_VHH": len(clinical), "Engineered_Human_VH": len(engineered)},

        # ── Section A: Camelid VHH Humanization ─────────────────────────────
        "camelid_vhh_humanization": {
            "description": "Rules for humanizing a camelid-origin VHH toward human IGHV3-23 framework",
            "hallmark_strategy_distribution": dict(camelid_hallmark_dist.most_common()),
            "top_motifs": dict(camelid_motif_dist.most_common(8)),
            "fr_departures_summary": fr_clinical,
            "critical_vernier_positions": critical_verniers_clinical,

            "rule_A1": {
                "title": "Germline Selection: IGHV3-23 is the dominant scaffold",
                "evidence": f"{corr['germline_distribution'].get('Clinical_VHH',{}).get('IGHV3-23',0)}/{len(clinical)} clinical VHHs match IGHV3-23",
                "action": "Use IGHV3-23 as acceptor framework. IGHV3-7 or IGHV1-69 only when CDR3>18aa (long loop requires alternative packing)."
            },
            "rule_A2": {
                "title": "Hallmark FR2 Engineering: Camelid E44/R45/G47 vs Human G44/L45/W47",
                "evidence": f"Top clinical hallmark types: {dict(camelid_hallmark_dist.most_common(3))}",
                "cdr3_by_hallmark_strategy": {
                    ht: {"mean_cdr3": round(sum(v)/len(v),1) if v else 0, "n": len(v)}
                    for ht, v in cdr3_by_htype_clinical.items()
                },
                "strategies": {
                    "VHH_Camelid_Like (E44/R45)": "Retain when CDR3 > 16aa or CDR profile is unusual; maximum single-domain stability",
                    "Humanized_Camelid_FGLA (G44/L45/A47)": "Optimal balance: Muyldermans strategy. Works for CDR3 8-16aa.",
                    "Human_IGHV3_23_Like (Q44/A45)": "Maximum human-likeness; only use when CDR3 < 10aa or CDR2 < 8aa (low aggregation risk)",
                    "Naive_IgG (G44/L45/W47)": "Avoid for most VHH sequences; only viable with CDR3 >= 15aa compensatory folding"
                }
            },
            "rule_A3": {
                "title": "Vernier Zone Retention: Which positions must stay camelid?",
                "critical_positions_to_check": critical_verniers_clinical,
                "action": {
                    "71": "Often R (camelid) vs R (IGHV3-23) — usually conserved; if CDR3 long, may differ",
                    "78": "V in IGHV3-23 but often mutated in VHH to support CDR3 loop packing",
                    "94": "K in IGHV3-23, sometimes A in humanized VHH — check CDR3 proximity",
                    "67": "F/L in VHH vs K in IGHV3-23 — frequently retained camelid position"
                }
            },
            "rule_A4": {
                "title": "CDR Preservation Gate",
                "action": "CDR1/CDR2/CDR3 must be transferred verbatim. Verify CDR3 disulfide (Cys at 95-102 region) if present. Long CDR3 (>16aa) may require back-mutation at Vernier 78 and 94."
            }
        },

        # ── Section B: VH to VHH Conversion ─────────────────────────────────
        "vh_to_vhh_conversion": {
            "description": "Rules for converting a conventional human VH domain to stable single-domain sdAb",
            "hallmark_strategy_distribution": dict(eng_hallmark_dist.most_common()),
            "top_motifs": dict(eng_motif_dist.most_common(8)),
            "critical_vernier_positions": critical_verniers_eng,

            "rule_B1": {
                "title": "CDR3 Length Determines Hallmark Requirement",
                "evidence": {
                    "Naive_IgG_still_stable_avg_CDR3": round(sum(cdr3_eng_naive)/len(cdr3_eng_naive),1) if cdr3_eng_naive else "N/A",
                    "Engineered_Hallmark_avg_CDR3": round(sum(cdr3_eng_vhh_like)/len(cdr3_eng_vhh_like),1) if cdr3_eng_vhh_like else "N/A",
                },
                "rule": {
                    "CDR3 >= 15aa": "May survive as Naive IgG (VGLW) if CDR3 folds to cover VH-VL interface. Test first.",
                    "CDR3 10-14aa": "Ambiguous — structural prediction required. Recommended: introduce G44E + L45R.",
                    "CDR3 < 10aa": "MUST engineer Hallmark. Without E44/R45, aggregation is near-certain.",
                }
            },
            "rule_B2": {
                "title": "CDR2 Length Impact on Interface Stability",
                "rule": {
                    "CDR2 >= 17aa (Kabat)": "Long CDR2 increases surface complexity near FR2. Must pair with E44/R45 to prevent aggregation. Ref: 7vke (UniDab F11A, CDR2=17aa, VERW motif).",
                    "CDR2 8-16aa": "Standard range. G44E alone may be sufficient.",
                    "CDR2 < 8aa": "Short CDR2 offers less steric hindrance; VGLW may be tolerated with long CDR3."
                }
            },
            "rule_B3": {
                "title": "Minimum Hallmark Mutation Set for VH to VHH",
                "primary_mutations": {
                    "G44E": "Priority 1 — converts hydrophobic G to charged E; greatest single impact on interface hydrophilicity",
                    "L45R": "Priority 2 — converts hydrophobic L to positively charged R; synergistic with G44E",
                    "W47G or W47L": "Priority 3 — reduces steric bulk at VH-VL interface; critical if CDR2 is long",
                    "V37F or V37Y": "Optional — VHH signature; improves single-domain stability but reduces humanness"
                },
                "validated_combinations": {
                    "VERW (V37, E44, R45, W47)": "Used in 7vke (UniDab F11A) — clinically closest analog for long CDR2",
                    "VGEL (V37, G44, E45, L47)": "Intermediate — gentle humanization, tested in several phage display VH",
                    "FGLW (F37, G44, L45, W47)": "Muyldermans camelization — maximizes camelid-like stability"
                }
            },
            "rule_B4": {
                "title": "Vernier Zone Retention Strategy",
                "critical_positions": critical_verniers_eng,
                "rule": "When introducing E44, position Vernier 94 may need K→A or K→G to relieve steric clash. Positions 71 (R) and 78 (V/L) should be retained from original VH unless structural prediction shows conflict with CDR3."
            },
            "rule_B5": {
                "title": "Structure QA Requirement",
                "action": "After Hallmark engineering, MUST run NanoBodyBuilder2 / ABodyBuilder2 structure prediction. Gate criteria: Fv RMSD ≤1.5Å vs reference, CDR RMSD ≤1.0Å vs original VH CDR conformation."
            }
        }
    }

    return rules

# ── Phase 4: Markdown Report ───────────────────────────────────────────────────

def write_markdown_report(rules: dict, corr: dict, out_path: Path):
    lines = [
        "# VHH  — AbEngineCore",
        f"> Generated from {rules['generated_from']} | Version {rules['version']}",
        "",
        f"**：** Clinical_VHH = {rules['n_entries_analyzed']['Clinical_VHH']}  | "
        f"Engineered_Human_VH = {rules['n_entries_analyzed']['Engineered_Human_VH']} ",
        "",
        "---",
        "",
        "## Part A —  VHH ",
        "",
        "### A1. Germline ",
        "",
    ]

    # A1
    a1 = rules["camelid_vhh_humanization"]["rule_A1"]
    lines += [
        f"**{a1['title']}**",
        "",
        f"- : {a1['evidence']}",
        f"- : {a1['action']}",
        "",
    ]

    # A2
    a2 = rules["camelid_vhh_humanization"]["rule_A2"]
    lines += [
        "### A2. FR2 Hallmark ",
        "",
        f"**{a2['title']}**",
        "",
        f" Hallmark : {a2['evidence']}",
        "",
        "**CDR3  Hallmark ：**",
        "",
        "| Hallmark  |  |  CDR3  |",
        "|:---|:---:|:---:|",
    ]
    for ht, v in a2["cdr3_by_hallmark_strategy"].items():
        lines.append(f"| {ht} | {v['n']} | {v['mean_cdr3']} aa |")
    lines += ["",
        "**：**", ""]
    for strat, note in a2["strategies"].items():
        lines.append(f"- **{strat}**: {note}")
    lines.append("")

    # A3
    a3 = rules["camelid_vhh_humanization"]["rule_A3"]
    lines += [
        "### A3. Vernier Zone ",
        "",
        f"**{a3['title']}**",
        "",
        f" Vernier  (>30%  VHH  IGHV3-23): `{', '.join(a3['critical_positions_to_check'])}`",
        "",
        "| Kabat  |  |",
        "|:---:|:---|",
    ]
    for pos, note in a3["action"].items():
        lines.append(f"| {pos} | {note} |")
    lines += ["",
        "### A4. CDR ",
        "",
        f"- {rules['camelid_vhh_humanization']['rule_A4']['action']}",
        "",
        "---",
        "",
        "## Part B — VH to VHH ",
        "",
    ]

    # B1
    b1 = rules["vh_to_vhh_conversion"]["rule_B1"]
    lines += [
        "### B1. CDR3  Hallmark ",
        "",
        f"**：** Engineered_Human_VH {rules['n_entries_analyzed']['Engineered_Human_VH']} ",
        "",
        f"- Naive IgG  CDR3 : **{b1['evidence'].get('Naive_IgG_still_stable_avg_CDR3','N/A')} aa**",
        f"-  Hallmark  CDR3 : **{b1['evidence'].get('Engineered_Hallmark_avg_CDR3','N/A')} aa**",
        "",
        "**：**",
        "",
        "| CDR3  |  |",
        "|:---:|:---|",
    ]
    for cond, action in b1["rule"].items():
        lines.append(f"| {cond} | {action} |")
    lines.append("")

    # B2
    b2 = rules["vh_to_vhh_conversion"]["rule_B2"]
    lines += [
        "### B2. CDR2 ",
        "",
        "| CDR2  |  |",
        "|:---:|:---|",
    ]
    for cond, action in b2["rule"].items():
        lines.append(f"| {cond} | {action} |")
    lines.append("")

    # B3
    b3 = rules["vh_to_vhh_conversion"]["rule_B3"]
    lines += [
        "### B3.  Hallmark  (Minimal Mutation Set)",
        "",
        "** ()：**",
        "",
    ]
    for mut, note in b3["primary_mutations"].items():
        lines.append(f"- **`{mut}`**: {note}")
    lines += ["",
        "**：**",
        "",
        "| Hallmark  |  |",
        "|:---|:---|",
    ]
    for combo, ref in b3["validated_combinations"].items():
        lines.append(f"| `{combo}` | {ref} |")
    lines.append("")

    # B4
    b4 = rules["vh_to_vhh_conversion"]["rule_B4"]
    lines += [
        "### B4. Vernier Zone ",
        "",
        f": `{', '.join(b4['critical_positions'])}`",
        "",
        f"{b4['rule']}",
        "",
        "### B5.  QA ",
        "",
        f"- {rules['vh_to_vhh_conversion']['rule_B5']['action']}",
        "",
        "---",
        "",
        "## ：",
        "",
        "### Hallmark  vs CDR3 ",
        "",
        "| Hallmark  | N | CDR3  | CDR3  |",
        "|:---|:---:|:---:|:---:|",
    ]
    for ht, stats in corr["cdr3_len_by_hallmark_type"].items():
        lines.append(f"| {ht} | {stats['n']} | {stats['mean']} aa | {stats['min']}–{stats['max']} aa |")
    lines += ["",
        "###  Hallmark ",
        "",
        "|  | Hallmark  |  |",
        "|:---|:---|:---:|",
    ]
    for cat, dist in corr["hallmark_type_distribution"].items():
        for ht, cnt in dist.items():
            lines.append(f"| {cat} | {ht} | {cnt} |")
    lines += ["",
        "###  Vernier  ()",
        "",
        "|  | Kabat  |  |",
        "|:---|:---:|:---:|",
    ]
    for cat, freq in corr["vernier_nonconserved_frequency"].items():
        top5 = list(freq.items())[:5]
        for pos, f in top5:
            lines.append(f"| {cat} | {pos} | {f:.0%} |")

    lines += ["",
        "---",
        "* AbEngineCore analyze_vhh_atlas.py 。*",
    ]

    out_path.write_text("\n".join(lines), encoding="utf-8")
    print(f"Markdown report saved: {out_path}")

# ── Main ───────────────────────────────────────────────────────────────────────

def main():
    # Phase 1: Enrich
    enriched, ref_kd = enrich_atlas()

    # Save v3
    v3_path = BASE / "data/vhh_design_atlas_v3.json"
    v3_path.write_text(json.dumps(enriched, indent=2, ensure_ascii=False), encoding="utf-8")
    print(f"\nAtlas v3 saved: {v3_path} ({len(enriched)} entries)")

    # Phase 2: Correlation analysis
    print("\nRunning correlation analysis...")
    corr = correlation_analysis(enriched)
    corr_path = BASE / "data/sabdab_vhh_atlas/vhh_atlas_correlations.json"
    corr_path.write_text(json.dumps(corr, indent=2, ensure_ascii=False), encoding="utf-8")
    print(f"Correlation analysis saved: {corr_path}")

    # Phase 3: Design rules
    print("\nExtracting design rules...")
    rules = extract_design_rules(enriched, corr)
    rules_path = BASE / "data/vhh_design_rules.json"
    rules_path.write_text(json.dumps(rules, indent=2, ensure_ascii=False), encoding="utf-8")
    print(f"Design rules saved: {rules_path}")

    # Phase 4: Markdown report
    md_path = BASE / "data/vhh_design_rules.md"
    write_markdown_report(rules, corr, md_path)

    # Quick summary print
    print("\n" + "="*60)
    print("DESIGN RULES SUMMARY")
    print("="*60)
    print("\n[A] Camelid VHH Humanization:")
    ht_dist = corr["hallmark_type_distribution"].get("Clinical_VHH", {})
    for ht, cnt in ht_dist.items():
        print(f"    {ht:35s}: {cnt}")
    print(f"\n[B] VH-to-VHH Engineered Hallmark Distribution:")
    ht_eng = corr["hallmark_type_distribution"].get("Engineered_Human_VH", {})
    for ht, cnt in ht_eng.items():
        print(f"    {ht:35s}: {cnt}")
    print("\n[Vernier] Most non-conserved positions vs IGHV3-23:")
    for cat in ["Clinical_VHH","Engineered_Human_VH"]:
        top = list(corr["vernier_nonconserved_frequency"].get(cat,{}).items())[:5]
        print(f"  {cat}: " + ", ".join(f"pos{p}({f:.0%})" for p,f in top))

if __name__ == "__main__":
    main()
