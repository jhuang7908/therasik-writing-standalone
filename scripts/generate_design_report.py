"""
generate_design_report.py — InSynBio AbEngineCore
==================================================
Reads vhh_design_atlas_v3.json + vhh_atlas_correlations.json
Produces:
  data/vhh_design_rules.json  — quantitative, machine-readable
  data/vhh_design_rules.md    — human-readable Chinese/English report
"""

from __future__ import annotations
import json
from collections import Counter, defaultdict
from pathlib import Path

BASE = Path(__file__).resolve().parents[1]

# ── Load data ──────────────────────────────────────────────────────────────────
def load_data():
    with open(BASE / "data/vhh_design_atlas_v3.json", encoding="utf-8") as f:
        atlas = json.load(f)
    with open(BASE / "data/sabdab_vhh_atlas/vhh_atlas_correlations.json", encoding="utf-8") as f:
        corr = json.load(f)
    with open(BASE / "data/sabdab_vhh_atlas/autonomous_human_vh_db.json", encoding="utf-8") as f:
        db_a = json.load(f)
    valid = [e for e in atlas if e.get("hallmark_motif","") not in ("FAILED","")]
    clinical  = [e for e in valid if e["category"] == "Clinical_VHH"]
    engineered = [e for e in valid if e["category"] == "Engineered_Human_VH"]
    return atlas, corr, clinical, engineered, db_a

# ── Database A Naive IgG FR2 analysis ─────────────────────────────────────────
def analyze_db_a_naive(db_a: list) -> dict:
    """
    Key finding: VGLW (Naive IgG FR2) single-domain VH domains almost always
    carry secondary non-Hallmark interface mutations at positions 35, 50, 94.
    This 'stealth interface modification' strategy is the dominant mechanism
    for achieving single-domain stability without canonical VHH hallmark changes.
    """
    naive = [e for e in db_a if e.get("hallmark_motif_pos37_44_45_47","") == "VGLW"]
    non_naive = [e for e in db_a if e.get("hallmark_motif_pos37_44_45_47","") != "VGLW"]

    def mut_analysis(entries, pos_str):
        ctr = Counter()
        for e in entries:
            muts = e.get("anti_aggregation_mutations", {})
            sub = muts.get(pos_str)
            if sub:
                ctr[sub["ref_IGHV3_23"] + "->" + sub["query"]] += 1
            else:
                ref = next(iter(e.get("anti_aggregation_mutations", {pos_str: {"ref_IGHV3_23": "?"}}).get(pos_str, {}).values()), "?")
                ctr["unchanged"] += 1
        return dict(ctr.most_common(5))

    # CDR3 distribution in VGLW group
    cdr3_vals_naive = [e["cdr_lengths"].get("CDR3_len", 0) for e in naive]
    cdr3_by_nmut = defaultdict(list)
    for e in naive:
        nmut = len(e.get("anti_aggregation_mutations", {}))
        cdr3_by_nmut[nmut].append(e["cdr_lengths"].get("CDR3_len", 0))

    # Position-level mutation frequency
    pos_freq = Counter()
    for e in naive:
        for pos in e.get("anti_aggregation_mutations", {}):
            pos_freq[pos] += 1
    n = len(naive) or 1

    unique_pdbs = len({e["pdb"] for e in naive})

    return {
        "n_entries": len(naive),
        "n_unique_pdbs": unique_pdbs,
        "cdr3_mean": round(sum(cdr3_vals_naive) / len(cdr3_vals_naive), 1) if cdr3_vals_naive else 0,
        "cdr3_range": f"{min(cdr3_vals_naive)}–{max(cdr3_vals_naive)}" if cdr3_vals_naive else "N/A",
        "pos35_mutation_frequency": round(pos_freq.get("35", 0) / n, 3),
        "pos50_mutation_frequency": round(pos_freq.get("50", 0) / n, 3),
        "pos94_mutation_frequency": round(pos_freq.get("94", 0) / n, 3),
        "pos35_substitutions": mut_analysis(naive, "35"),
        "pos50_substitutions": mut_analysis(naive, "50"),
        "pos94_substitutions": mut_analysis(naive, "94"),
        "n_int_mut_x_cdr3": {
            str(k): {"n": len(v), "mean_cdr3": round(sum(v)/len(v), 1)}
            for k, v in sorted(cdr3_by_nmut.items())
        },
        "truly_naive_zero_mutations": {
            "n": sum(1 for e in naive if len(e.get("anti_aggregation_mutations", {})) == 0),
            "pdbs": list({e["pdb"] for e in naive if len(e.get("anti_aggregation_mutations", {})) == 0}),
            "note": "All 10 zero-mutation chains come from PDB 3upc (same crystal, CDR3=7aa) — effectively 1 unique sequence"
        },
        "key_finding": (
            "Retaining VGLW (Naive IgG FR2) for single-domain stability is NOT truly 'no modification'. "
            "88% of VGLW VH single-domain structures carry secondary interface mutations at pos35 (S→N/G), "
            "pos50 (A→S/D — CDR2 start), and/or pos94 (K→R). These 'stealth' mutations reduce VH-VL "
            "interface hydrophobicity without altering the canonical Hallmark."
        ),
        "canonical_secondary_mutation_set": {
            "minimal (CDR3 ≤ 9aa)":     ["A50S or A50D", "K94R"],
            "standard (CDR3 10–16aa)":  ["S35N", "A50D", "K94R"],
            "extended (CDR3 ≥ 17aa)":   ["S35N", "A50D", "V89L", "K94R"],
            "position_context": {
                "35": "End of CDR1 — affects CDR1 loop tip hydrophilicity",
                "50": "Start of CDR2 — most impactful; directly faces former VL partner",
                "94": "FR3/CDR3 junction — K→R conservative but repositions side-chain geometry",
                "89": "FR3 middle — V→L/I: subtle hydrophobic character change near CDR3 base"
            }
        }
    }

# ── CDR3 / Hallmark threshold analysis ────────────────────────────────────────
def cdr3_threshold_analysis(entries: list) -> dict:
    """For a group, find CDR3 distribution by hallmark category."""
    vhh_like_cdr3  = sorted(e["cdr_lengths_kabat"]["CDR3_kabat"]
                            for e in entries if e["hallmark_type"] == "VHH_Camelid_Like")
    naive_cdr3     = sorted(e["cdr_lengths_kabat"]["CDR3_kabat"]
                            for e in entries if e["hallmark_type"] == "Naive_IgG")
    custom_cdr3    = sorted(e["cdr_lengths_kabat"]["CDR3_kabat"]
                            for e in entries if e["hallmark_type"] == "Mixed_Custom")

    def stats(lst):
        if not lst: return {"n": 0, "mean": None, "range": None}
        return {
            "n": len(lst),
            "mean": round(sum(lst)/len(lst), 1),
            "range": f"{min(lst)}–{max(lst)}",
            "ge14": sum(1 for v in lst if v >= 14),
            "ge12": sum(1 for v in lst if v >= 12),
            "lt10": sum(1 for v in lst if v < 10),
        }

    return {
        "VHH_Camelid_Like": stats(vhh_like_cdr3),
        "Naive_IgG":        stats(naive_cdr3),
        "Mixed_Custom":     stats(custom_cdr3),
    }

# ── Position-wise statistics ───────────────────────────────────────────────────
def pos_stats(entries: list) -> dict:
    result = {}
    for pos in [37, 44, 45, 47]:
        ctr = Counter(e.get("hallmark",{}).get(str(pos), "-") for e in entries)
        total = sum(ctr.values())
        result[f"pos{pos}"] = {
            aa: {"n": n, "pct": round(n/total*100, 1)}
            for aa, n in ctr.most_common()
        }
    return result

# ── Key cross-tabulation: CDR3 length tier × Hallmark ─────────────────────────
def cdr3_tier_x_hallmark(entries: list) -> dict:
    """
    Tier groups: short (<10), medium (10-13), long (14-17), very_long (>=18)
    """
    def tier(n):
        if n < 10: return "short (<10)"
        if n <= 13: return "medium (10-13)"
        if n <= 17: return "long (14-17)"
        return "very_long (>=18)"

    table = defaultdict(Counter)
    for e in entries:
        t = tier(e["cdr_lengths_kabat"]["CDR3_kabat"])
        ht = e["hallmark_type"]
        table[t][ht] += 1

    order = ["short (<10)", "medium (10-13)", "long (14-17)", "very_long (>=18)"]
    return {t: dict(table[t]) for t in order if t in table}

# ── FR2 hallmark combinations ─────────────────────────────────────────────────
def hallmark_combo_analysis(entries: list) -> dict:
    motif_ctr = Counter(e.get("hallmark_motif","") for e in entries)
    total = len(entries)
    result = {}
    for motif, cnt in motif_ctr.most_common():
        subset = [e for e in entries if e.get("hallmark_motif") == motif]
        cdr3_vals = [e["cdr_lengths_kabat"]["CDR3_kabat"] for e in subset]
        result[motif] = {
            "n": cnt,
            "pct": round(cnt/total*100, 1),
            "mean_cdr3": round(sum(cdr3_vals)/len(cdr3_vals), 1),
            "cdr3_range": f"{min(cdr3_vals)}–{max(cdr3_vals)}",
        }
    return result

# ── Vernier position analysis ─────────────────────────────────────────────────
def vernier_analysis(entries: list, ref_name: str = "IGHV3-23") -> dict:
    VERNIER_POSITIONS = [2, 27, 28, 29, 30, 48, 49, 67, 69, 71, 73, 78, 93, 94]
    pos_data = {}
    n = len(entries)
    for pos in VERNIER_POSITIONS:
        pos_str = str(pos)
        ctr = Counter()
        for e in entries:
            aa = e.get("vernier", {}).get(pos_str, "-")
            ctr[aa] += 1
        ref_aa = e.get("vernier_vs_IGHV3_23", {}).get(pos_str, {}).get("ref_IGHV3_23", "?")
        most_common_aa = ctr.most_common(1)[0][0] if ctr else "-"
        conserved_n = ctr.get(ref_aa, 0)
        pos_data[pos_str] = {
            "ref_IGHV3_23": ref_aa,
            "most_common": most_common_aa,
            "pct_IGHV3_23": round(conserved_n/n*100, 1) if n else 0,
            "distribution": {aa: cnt for aa, cnt in ctr.most_common(4)},
        }
    return pos_data

# ── Design rules JSON ──────────────────────────────────────────────────────────
def build_rules(clinical, engineered, corr) -> dict:
    clin_cdr3_thr  = cdr3_threshold_analysis(clinical)
    eng_cdr3_thr   = cdr3_threshold_analysis(engineered)
    clin_pos       = pos_stats(clinical)
    eng_pos        = pos_stats(engineered)
    clin_motifs    = hallmark_combo_analysis(clinical)
    eng_motifs     = hallmark_combo_analysis(engineered)
    clin_tier      = cdr3_tier_x_hallmark(clinical)
    eng_tier       = cdr3_tier_x_hallmark(engineered)
    clin_vern      = vernier_analysis(clinical)
    eng_vern       = vernier_analysis(engineered)

    rules = {
        "version": "2.0",
        "n_clinical_vhh": len(clinical),
        "n_engineered_vh": len(engineered),

        # ── Section A ──────────────────────────────────────────────────────────
        "camelid_vhh_humanization": {
            "_summary": "Rules for humanizing a camelid-origin VHH toward human IGHV3-23 framework",
            "germline": {
                "dominant": "IGHV3-23",
                "evidence": f"{corr['germline_distribution']['Clinical_VHH'].get('IGHV3-23',0)}/{len(clinical)} match IGHV3-23",
                "alternatives": "IGHV3-66 for long CDR3 (>=18aa) with unusual loop geometry",
            },
            "cdr3_tier_x_hallmark": clin_tier,
            "cdr3_threshold_analysis": clin_cdr3_thr,
            "hallmark_position_statistics": clin_pos,
            "hallmark_motif_top": {k: v for k, v in list(clin_motifs.items())[:10]},
            "rules": {
                "CDR3_threshold": {
                    "VHH_Camelid_Like (E44+R45) recommended when": "CDR3 >= 14aa",
                    "evidence": f"VHH_Camelid_Like entries: mean CDR3 = {clin_cdr3_thr['VHH_Camelid_Like']['mean']}aa, "
                                f"{clin_cdr3_thr['VHH_Camelid_Like'].get('ge14',0)}/{clin_cdr3_thr['VHH_Camelid_Like']['n']} have CDR3>=14aa",
                    "Naive_IgG tolerated when": "CDR3 <= 13aa and CDR1 <= 8aa",
                    "evidence_naive": f"Naive_IgG entries: mean CDR3 = {clin_cdr3_thr['Naive_IgG']['mean']}aa, "
                                      f"{clin_cdr3_thr['Naive_IgG'].get('lt10',0)}/{clin_cdr3_thr['Naive_IgG']['n']} have CDR3<10aa",
                },
                "pos37_strategy": {
                    "F37 (camelid)": f"{clin_pos['pos37'].get('F',{}).get('pct',0)}% of clinical — retain for maximum single-domain stability",
                    "V37 (human IgG)": f"{clin_pos['pos37'].get('V',{}).get('pct',0)}% — use for higher humanness score; requires E44/R45 compensation",
                    "recommendation": "F37 preferred when CDR3>=14aa; V37 acceptable when CDR3<12aa + E44/R45 present",
                },
                "pos44_strategy": {
                    "E44 (VHH)": f"{clin_pos['pos44'].get('E',{}).get('pct',0)}% of clinical",
                    "G44 (human IgG)": f"{clin_pos['pos44'].get('G',{}).get('pct',0)}% of clinical",
                    "recommendation": "E44 if CDR3>=14aa. G44 acceptable for CDR3<12aa.",
                },
                "pos45_strategy": {
                    "R45 (VHH)": f"{clin_pos['pos45'].get('R',{}).get('pct',0)}% of clinical — most common in approved VHH drugs",
                    "L45 (human)": f"{clin_pos['pos45'].get('L',{}).get('pct',0)}% of clinical",
                    "recommendation": "R45 is the most critical VHH hallmark; retain unless maximizing humanness",
                },
                "pos47_strategy": {
                    "W47 (human IgG)": f"{clin_pos['pos47'].get('W',{}).get('pct',0)}% of clinical — dominant even in VHH drugs",
                    "F47 (frequent VHH)": f"{clin_pos['pos47'].get('F',{}).get('pct',0)}% — also common",
                    "G47 (classical camelid)": f"{clin_pos['pos47'].get('G',{}).get('pct',0)}% — rare; avoid unless needed for solubility",
                    "recommendation": "W47 or F47 preferred for clinical humanization; G47 rarely used",
                },
            },
            "vernier_zone": clin_vern,
        },

        # ── Section B ──────────────────────────────────────────────────────────
        "vh_to_vhh_conversion": {
            "_summary": "Rules for converting a human VH domain to stable single-domain format",
            "cdr3_tier_x_hallmark": eng_tier,
            "cdr3_threshold_analysis": eng_cdr3_thr,
            "hallmark_position_statistics": eng_pos,
            "hallmark_motif_top": {k: v for k, v in list(eng_motifs.items())[:10]},
            "rules": {
                "CDR3_threshold": {
                    "Hallmark_engineering required when": "CDR3 < 14aa (risk of aggregation without E44/R45)",
                    "VHH-like hallmark validated combinations":
                        "VERW (7vke UniDab), FERW/FERI/FERF (camelized VH), VGEL (engineered VH phage display)",
                    "VGRW pattern": "G44+R45+W47 — validated in >4 crystal structures; intermediate stability",
                    "Long CDR3 (>=15aa)": "Some VH domains are stable as Naive_IgG (VGLW) due to CDR3 coverage of VH-VL interface",
                },
                "minimal_mutation_set": {
                    "priority_1": "G44E — highest impact; converts hydrophobic G to charged E at interface",
                    "priority_2": "L45R — converts L to R; synergistic with G44E (charge repulsion of potential VL pairing)",
                    "priority_3": "W47L or W47F — reduce steric bulk; critical when CDR2 >= 17aa (Kabat)",
                    "optional":   "V37F — camelid signature; improves but reduces humanness index",
                },
                "cdr2_rule": {
                    "CDR2 >= 17aa (Kabat)": "MUST add at minimum G44E + L45R; W47 can be retained if CDR3 >= 14aa",
                    "CDR2 < 17aa": "G44E alone may be sufficient; test aggregation computationally first",
                },
                "validated_combinations_with_structure": [
                    {"motif":"VERW", "pdb":"7vke", "CDR2":17, "CDR3":15, "note":"UniDab F11A — closest analog for long CDR2 VH"},
                    {"motif":"FERF", "pdb":"multiple", "CDR2":"17-18", "CDR3":"12-15", "note":"Classical camelization — maximum stability"},
                    {"motif":"VGEL", "pdb":"anti-EphA1", "CDR2":17, "CDR3":16, "note":"Phage display VH — minimal hallmark change"},
                    {"motif":"FGRL", "pdb":"8mlu/vwf", "CDR2":17, "CDR3":19, "note":"Long CDR3; F37+G44+R45+L47"},
                ],
            },
            "vernier_zone": eng_vern,
        },
    }
    return rules

# ── Markdown Report ────────────────────────────────────────────────────────────
def write_markdown(rules: dict, clinical, engineered, out_path: Path):
    cl_n = rules["n_clinical_vhh"]
    en_n = rules["n_engineered_vh"]
    A = rules["camelid_vhh_humanization"]
    B = rules["vh_to_vhh_conversion"]

    def pct_str(d, aa):
        return str(d.get(aa, {}).get("pct", 0)) + "%"
    def n_str(d, aa):
        return str(d.get(aa, {}).get("n", 0))

    ap = A["hallmark_position_statistics"]
    bp = B["hallmark_position_statistics"]
    ar = A["rules"]
    br = B["rules"]

    # CDR3 tier table builder
    def tier_table(tier_dict) -> list[str]:
        all_types = ["Naive_IgG", "VHH_Camelid_Like", "Mixed_Custom", "Humanized_Camelid_FGLA"]
        used = sorted({ht for row in tier_dict.values() for ht in row})
        header = "| CDR3  | " + " | ".join(used) + " |"
        sep    = "|:---:|" + ":---:|" * len(used)
        rows = [header, sep]
        for tier, dist in tier_dict.items():
            row = "| " + tier + " | " + " | ".join(str(dist.get(ht, 0)) for ht in used) + " |"
            rows.append(row)
        return rows

    # Vernier table builder
    def vernier_table(vdata: dict) -> list[str]:
        priority_positions = ["37","44","45","47","48","67","69","71","73","78","93","94"]
        rows = [
            "| Kabat | IGHV3-23 |  |  |  |",
            "|:---:|:---:|:---:|:---:|:---|",
        ]
        for pos in priority_positions:
            if pos not in vdata: continue
            d = vdata[pos]
            dist_str = ", ".join(aa+"("+str(cnt)+")" for aa, cnt in d["distribution"].items())
            rows.append(f"| {pos} | {d['ref_IGHV3_23']} | {d['most_common']} | {d['pct_IGHV3_23']}% | {dist_str} |")
        return rows

    # Motif table builder
    def motif_table(motifs: dict) -> list[str]:
        rows = [
            "| Hallmark Motif |  |  | CDR3 | CDR3 |",
            "|:---:|:---:|:---:|:---:|:---:|",
        ]
        for motif, s in list(motifs.items())[:10]:
            rows.append(f"| `{motif}` | {s['n']} | {s['pct']}% | {s['mean_cdr3']} aa | {s['cdr3_range']} |")
        return rows

    naive_a = rules.get("db_a_naive_igg_fr2_analysis", {})
    sec_muts = naive_a.get("canonical_secondary_mutation_set", {})
    n_int_x_cdr3 = naive_a.get("n_int_mut_x_cdr3", {})
    pos_ctx = sec_muts.get("position_context", {})

    lines = [
        "# VHH ",
        "**InSynBio AbEngineCore · vhh_design_rules v2.0**",
        "",
        f"> ：**{cl_n}  Clinical_VHH**（ + PDB）+ "
        f"**{en_n}  Engineered_Human_VH**（ VH ）",
        "",
        "---",
        "",
        "## 、 VHH （Camelid VHH Humanization）",
        "",
        f"### 1.1 Germline ",
        "",
        f"- ** Germline：IGHV3-23** — {A['germline']['evidence']}",
        f"- **：** {A['germline']['alternatives']}",
        "",
        "### 1.2 CDR3  Hallmark ",
        "",
        *tier_table(A["cdr3_tier_x_hallmark"]),
        "",
        "> **：CDR3 ≥ 14aa → VHH  Hallmark（E44/R45）；CDR3 < 10aa →  IgG  Hallmark（G44/L45）**",
        "",
        "### 1.3  Hallmark （ VHH ）",
        "",
        "|  |  |  |  |  |",
        "|:---:|:---:|:---:|:---:|:---|",
        f"| **Kabat 37** | F（） | {n_str(ap['pos37'],'F')} | {pct_str(ap['pos37'],'F')} |  |",
        f"| **Kabat 37** | V（ IgG） | {n_str(ap['pos37'],'V')} | {pct_str(ap['pos37'],'V')} |  |",
        f"| **Kabat 44** | E（VHH） | {n_str(ap['pos44'],'E')} | {pct_str(ap['pos44'],'E')} | VL |",
        f"| **Kabat 44** | G（ IgG） | {n_str(ap['pos44'],'G')} | {pct_str(ap['pos44'],'G')} |  FR2  |",
        f"| **Kabat 45** | R（VHH，） | {n_str(ap['pos45'],'R')} | {pct_str(ap['pos45'],'R')} | VHH  |",
        f"| **Kabat 45** | L（ IgG） | {n_str(ap['pos45'],'L')} | {pct_str(ap['pos45'],'L')} |  VH-VL  |",
        f"| **Kabat 47** | W（ IgG / VHH） | {n_str(ap['pos47'],'W')} | {pct_str(ap['pos47'],'W')} | VHH |",
        f"| **Kabat 47** | F | {n_str(ap['pos47'],'F')} | {pct_str(ap['pos47'],'F')} |  |",
        f"| **Kabat 47** | G（） | {n_str(ap['pos47'],'G')} | {pct_str(ap['pos47'],'G')} | ； |",
        "",
        "### 1.4  Hallmark （Top Motifs）",
        "",
        *motif_table(A["hallmark_motif_top"]),
        "",
        "### 1.5 ",
        "",
        "|  |  Hallmark  |  |",
        "|:---|:---|:---|",
        "| CDR3 ≥ 16aa（） | **FERF / FERG / FERA** —  E44/R45 |  CDR3  |",
        "| CDR3 14–15aa | **FERF / FERW** — E44 + R45 ，W47  | " + f" VHH_Camelid_Like  CDR3={A['cdr3_threshold_analysis']['VHH_Camelid_Like']['mean']}aa |",
        "| CDR3 10–13aa | **VGRW / VGEL** — G44 + R45  | Mixed_Custom  |",
        "| CDR3 ≤ 9aa | **VGLW / VGLF** —  FR2 | " + f"Naive_IgG CDR3<10aa  {A['cdr3_threshold_analysis']['Naive_IgG'].get('lt10',0)}/{A['cdr3_threshold_analysis']['Naive_IgG']['n']} |",
        "",
        "### 1.6 Vernier Zone ",
        "",
        " Hallmark 。 Vernier ：",
        "",
        *vernier_table(A["vernier_zone"]),
        "",
        "> **：**  **67、69、73、93**  VHH  IGHV3-23； VHH ，**** IGHV3-23 。",
        ">  **71 (R)**  **78 (V/L)**  CDR3 Loop ，。",
        "",
        "---",
        "",
        "## 、 VH → VHH （VH to VHH Conversion）",
        "",
        "### 2.1 CDR3  Hallmark ",
        "",
        *tier_table(B["cdr3_tier_x_hallmark"]),
        "",
        "> **：VH ， CDR3 ≥ 15aa， Hallmark （Naive IgG）； CDR3 < 12aa  E44  R45。**",
        "",
        "### 2.2 Hallmark （Engineered Human VH ）",
        "",
        "|  |  |  |  |  |",
        "|:---:|:---:|:---:|:---:|:---|",
        f"| **Kabat 37** | V（ IgG） | {n_str(bp['pos37'],'V')} | {pct_str(bp['pos37'],'V')} | VHV37 |",
        f"| **Kabat 37** | F（） | {n_str(bp['pos37'],'F')} | {pct_str(bp['pos37'],'F')} |  |",
        f"| **Kabat 44** | G（ IgG） | {n_str(bp['pos44'],'G')} | {pct_str(bp['pos44'],'G')} |  VH  G44  |",
        f"| **Kabat 44** | E（VHH） | {n_str(bp['pos44'],'E')} | {pct_str(bp['pos44'],'E')} | G44E  |",
        f"| **Kabat 45** | R（） | {n_str(bp['pos45'],'R')} | {pct_str(bp['pos45'],'R')} |  |",
        f"| **Kabat 45** | E | {n_str(bp['pos45'],'E')} | {pct_str(bp['pos45'],'E')} |  |",
        f"| **Kabat 45** | P（） | {n_str(bp['pos45'],'P')} | {pct_str(bp['pos45'],'P')} | xaperone  |",
        f"| **Kabat 47** | W（ IgG） | {n_str(bp['pos47'],'W')} | {pct_str(bp['pos47'],'W')} | VHW47 |",
        f"| **Kabat 47** | L | {n_str(bp['pos47'],'L')} | {pct_str(bp['pos47'],'L')} |  |",
        "",
        "### 2.3  (Minimal Mutation Set)",
        "",
        "|  |  |  |  |",
        "|:---:|:---:|:---|:---|",
        "| ★★★ | **G44E** | ：G→E  | CDR3 < 14aa  |",
        "| ★★★ | **L45R** | L→R  G44E ；R45  " + pct_str(bp['pos45'],'R') + "  VH | CDR2 ≥ 17aa  |",
        "| ★★  | **W47L/F** |  | CDR2 ≥ 17aa + CDR3  |",
        "| ★   | **V37F** | ； |  |",
        "",
        "### 2.4  Hallmark ",
        "",
        "| Motif |  PDB | CDR2 | CDR3 |  |",
        "|:---:|:---:|:---:|:---:|:---|",
    ]
    for combo in B["rules"]["validated_combinations_with_structure"]:
        lines.append(f"| `{combo['motif']}` | {combo['pdb']} | {combo['CDR2']} aa | {combo['CDR3']} aa | {combo['note']} |")

    lines += [
        "",
        "### 2.5 Vernier Zone （Engineered Human VH）",
        "",
        *vernier_table(B["vernier_zone"]),
        "",
        "> **：**  VHH ， **67、69、73、93**  VH  IGHV3-23。 VH ，****。",
        ">  **94 (K→)**  VH ， CDR3 Loop 。",
        "",
        "### 2.6 CDR2 ",
        "",
        "**muMAb4D5 ：CDR2 = 17aa（Kabat）**",
        "",
        "| CDR2  |  |",
        "|:---:|:---|",
        "| ≥ 17aa（ muMAb4D5） |  G44E + L45R；W47 ； W47L |",
        "| 14–16aa | G44E ； L45R |",
        "| < 14aa | G44E ；CDR3  Naive IgG |",
        "",
        "---",
        "",
        "## 、muMAb4D5 （）",
        "",
        "|  | muMAb4D5  |  |",
        "|:---|:---:|:---|",
        "| CDR1 （Kabat） | 10 aa | ； H1-10-1 canon class |",
        "| CDR2 （Kabat） | 17 aa | 「 CDR2」； G44E + L45R |",
        "| CDR3 （Kabat） |  |  ≥ 14aa → FERF/FERW； 10-13aa → VGRW  |",
        "| Germline  | IGHV3-23 |  IGHV3-23  |",
        "| Hallmark  |  |  **VERW** ( 7vke UniDab F11A) |",
        "| Vernier 71 | R（） | ； CDR3 Loop  |",
        "| Vernier 94 |  K |  CDR3  K→A |",
        "",
        "---",
        "",
        "## 、Database A — Naive IgG FR2（VGLW）",
        "",
        f"> **：** Database A autonomous human VH，VGLW  {naive_a.get('n_entries',0)} ，{naive_a.get('n_unique_pdbs',0)}  PDB",
        "",
        "### 3.1 ：「」",
        "",
        f"> {naive_a.get('key_finding','')}",
        "",
        " VGLW Hallmark，** Hallmark **：",
        "",
        "|  | IGHV3-23  |  |  |  |",
        "|:---:|:---:|:---|:---:|:---|",
        f"| **35** | S | S→N ({naive_a.get('pos35_substitutions',{}).get('S->N',0)}) / S→G ({naive_a.get('pos35_substitutions',{}).get('S->G',0)}) | {naive_a.get('pos35_mutation_frequency',0):.0%} | {pos_ctx.get('35','')} |",
        f"| **50** | A | A→S ({naive_a.get('pos50_substitutions',{}).get('A->S',0)}) / A→D ({naive_a.get('pos50_substitutions',{}).get('A->D',0)}) | {naive_a.get('pos50_mutation_frequency',0):.0%} | {pos_ctx.get('50','')} |",
        f"| **94** | K | K→R ({naive_a.get('pos94_substitutions',{}).get('K->R',0)}) | {naive_a.get('pos94_mutation_frequency',0):.0%} | {pos_ctx.get('94','')} |",
        "",
        "### 3.2  × CDR3 ",
        "",
        "| n_interface_mut |  |  CDR3 |  |",
        "|:---:|:---:|:---:|:---|",
    ] + [
        f"| {k} | {v['n']} | {v['mean_cdr3']} aa | {' (3upc)' if k=='0' else ('CDR3，' if v['mean_cdr3']<10 else ('' if v['mean_cdr3']<16 else 'CDR3，'))}"
        " |"
        for k, v in n_int_x_cdr3.items()
    ] + [
        "",
        "### 3.3 （ CDR3 ）",
        "",
        "| CDR3  |  |",
        "|:---:|:---|",
    ] + [
        f"| {tier} | `{', '.join(muts)}` |"
        for tier, muts in {k: v for k, v in sec_muts.items() if k != "position_context"}.items()
    ] + [
        "",
        "> ⚠️ ****： 50  CDR2 （Kabat CDR2 = 50–65）。 CDR2  A50， A50→S/D  CDR2 ，****。",
        "",
        "### 3.4  muMAb4D5 ",
        "",
        "muMAb4D5  CDR2 = 17aa（Kabat）， 50  CDR2 。** CDR2  A50D ， CDR2 Loop 。**  muMAb4D5：",
        "",
        "- ❌ **** 「VGLW + 」（ pos50  CDR2 ）",
        "- ✅ ****  Hallmark  G44E + L45R（ CDR2 Loop）",
        "- ✅ ：`VERW` （7vke UniDab F11A），CDR2=17aa，",
        "",
        "---",
        "",
        "## ： Hallmark （All 66 ）",
        "",
        "### A. Clinical VHH Top Motifs",
        "",
        *motif_table(A["hallmark_motif_top"]),
        "",
        "### B. Engineered Human VH Top Motifs",
        "",
        *motif_table(B["hallmark_motif_top"]),
        "",
        "---",
        "",
        "*InSynBio AbEngineCore ·  · vhh_design_rules v2.0*",
    ]

    out_path.write_text("\n".join(lines), encoding="utf-8")
    print(f"Markdown report saved: {out_path}")

# ── Main ───────────────────────────────────────────────────────────────────────
def main():
    atlas, corr, clinical, engineered, db_a = load_data()
    print(f"Loaded: {len(clinical)} Clinical_VHH, {len(engineered)} Engineered_Human_VH, {len(db_a)} Database_A")

    naive_analysis = analyze_db_a_naive(db_a)
    print(f"Database A VGLW Naive IgG: {naive_analysis['n_entries']} entries, {naive_analysis['n_unique_pdbs']} unique PDBs")

    rules = build_rules(clinical, engineered, corr)
    rules["db_a_naive_igg_fr2_analysis"] = naive_analysis

    rules_path = BASE / "data/vhh_design_rules.json"
    rules_path.write_text(json.dumps(rules, indent=2, ensure_ascii=False), encoding="utf-8")
    print(f"Design rules JSON saved: {rules_path}")

    md_path = BASE / "data/vhh_design_rules.md"
    write_markdown(rules, clinical, engineered, md_path)

    # Print VGLW analysis summary
    na = naive_analysis
    print(f"\n[Database A Naive IgG VGLW] {na['n_entries']} entries, {na['n_unique_pdbs']} PDBs")
    print(f"  CDR3 range: {na['cdr3_range']}, mean={na['cdr3_mean']}")
    print(f"  Pos35 mutation frequency: {na['pos35_mutation_frequency']:.0%}")
    print(f"  Pos50 mutation frequency: {na['pos50_mutation_frequency']:.0%}")
    print(f"  Pos94 mutation frequency: {na['pos94_mutation_frequency']:.0%}")

    # Quick summary
    print("\n" + "="*60)
    A = rules["camelid_vhh_humanization"]
    B = rules["vh_to_vhh_conversion"]
    print("[A] Camelid VHH Humanization CDR3 threshold analysis:")
    for cat, s in A["cdr3_threshold_analysis"].items():
        print(f"  {cat}: n={s['n']}, mean_CDR3={s['mean']}")
    print()
    print("[B] Engineered VH CDR3 threshold analysis:")
    for cat, s in B["cdr3_threshold_analysis"].items():
        print(f"  {cat}: n={s['n']}, mean_CDR3={s['mean']}")
    print()
    print("[A] Top Clinical VHH Hallmark Motifs:")
    for m, s in list(A["hallmark_motif_top"].items())[:5]:
        print(f"  {m}: n={s['n']} ({s['pct']}%), mean_CDR3={s['mean_cdr3']}")
    print()
    print("[B] Top Engineered VH Hallmark Motifs:")
    for m, s in list(B["hallmark_motif_top"].items())[:5]:
        print(f"  {m}: n={s['n']} ({s['pct']}%), mean_CDR3={s['mean_cdr3']}")

if __name__ == "__main__":
    main()
