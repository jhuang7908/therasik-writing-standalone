"""
CDR Fingerprint Cross-Database Analysis
========================================
Analyzes CDR physicochemical properties across all 4 VHH databases to identify
expression and affinity risks in VH-derived VHH sequences.

Databases:
  A  — Database A: 138 autonomous human VH single-domain antibodies (sabdab_vhh_atlas)
  B  — Database B: 29 humanized camelid VHH (sabdab_vhh_atlas)
  C  — Clinical VHH: 39 validated clinical/approved VHH (vhh_clinical_39_union)
  E  — Engineered VH: subset of Database A marked as engineered for VHH use

CDR Fingerprint Metrics (per sequence, Kabat numbering via ANARCI):
  - CDR-H1/H2/H3 lengths
  - CDR-H3 net charge (sum of D/E = -1, K/R = +1)
  - CDR-H3 GRAVY (hydrophobicity index, Kyte-Doolittle)
  - CDR-H3 D/E density (acidic residue fraction)
  - CDR-H3 aromatic density (F/W/Y fraction)
  - CDR-H1+H2+H3 combined GRAVY
  - Presence of N-glycosylation sequon (N-X-S/T) in any CDR
  - Presence of deamidation (NG/NS) motif in any CDR
  - CDR-H3 first residue (loop anchor: Pro/Asp = risk; Ala/Ser = safe)
  - pI of CDR-H3 sequence

Output:
  .tmp_cdr_fingerprint_4db.json   — full per-entry results
  .tmp_cdr_fingerprint_4db.md     — cross-database comparison report
"""
from __future__ import annotations
import json, math
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

ROOT = Path(__file__).resolve().parents[1]
BASE = ROOT

# ─────────────────────────────────────────────────────────────────────────────
# Amino acid tables
# ─────────────────────────────────────────────────────────────────────────────
KD_SCALE = {  # Kyte-Doolittle
    "A": 1.8, "R": -4.5, "N": -3.5, "D": -3.5, "C": 2.5,
    "Q": -3.5, "E": -3.5, "G": -0.4, "H": -3.2, "I": 4.5,
    "L": 3.8, "K": -3.9, "M": 1.9, "F": 2.8, "P": -1.6,
    "S": -0.8, "T": -0.7, "W": -0.9, "Y": -1.3, "V": 4.2,
}
PKA_GROUPS = {  # simplified pKa for pI estimation
    "D": 3.9, "E": 4.1, "H": 6.0, "C": 8.3, "Y": 10.1, "K": 10.5, "R": 12.5,
}
NEG_AA = frozenset("DE")
POS_AA = frozenset("KRH")
AROM_AA = frozenset("FWY")
HYDRO_AA = frozenset("AILMFWV")

AA3TO1 = {
    "ALA":"A","ARG":"R","ASN":"N","ASP":"D","CYS":"C","GLN":"Q","GLU":"E",
    "GLY":"G","HIS":"H","ILE":"I","LEU":"L","LYS":"K","MET":"M","PHE":"F",
    "PRO":"P","SER":"S","THR":"T","TRP":"W","TYR":"Y","VAL":"V",
}


# ─────────────────────────────────────────────────────────────────────────────
# CDR metrics
# ─────────────────────────────────────────────────────────────────────────────

def gravy(seq: str) -> float:
    if not seq: return 0.0
    return round(sum(KD_SCALE.get(aa, 0.0) for aa in seq.upper()) / len(seq), 3)


def net_charge(seq: str) -> float:
    s = seq.upper()
    return float(sum(1 for aa in s if aa in POS_AA) - sum(1 for aa in s if aa in NEG_AA))


def acid_density(seq: str) -> float:
    if not seq: return 0.0
    return round(sum(1 for aa in seq.upper() if aa in NEG_AA) / len(seq), 3)


def arom_density(seq: str) -> float:
    if not seq: return 0.0
    return round(sum(1 for aa in seq.upper() if aa in AROM_AA) / len(seq), 3)


def has_nglyc(seq: str) -> bool:
    s = seq.upper()
    for i in range(len(s) - 2):
        if s[i] == "N" and s[i+1] != "P" and s[i+2] in "ST":
            return True
    return False


def has_deamid(seq: str) -> bool:
    s = seq.upper()
    return "NG" in s or "NS" in s


def cdr3_anchor(seq: str) -> str:
    """First residue of CDR-H3 (risk: P/D; safe: A/S/G/T)."""
    if not seq: return "?"
    return seq[0].upper()


# ─────────────────────────────────────────────────────────────────────────────
# ANARCI-based CDR extraction (Kabat H)
# ─────────────────────────────────────────────────────────────────────────────

def extract_cdrs_kabat(seq: str) -> Dict[str, Any]:
    """
    Run ANARCI, extract CDR-H1 (31-35), CDR-H2 (50-65), CDR-H3 (95-102+ins).
    Returns dict with cdr1/cdr2/cdr3 sequences and lengths, or error.
    """
    try:
        from anarcii import Anarcii
    except ImportError:
        return {"error": "anarcii not available"}

    a = Anarcii(seq_type="antibody", mode="accuracy", verbose=False)
    a.number([seq])
    entry = a.to_scheme("kabat").get("Sequence 1", {})
    if entry.get("error") or entry.get("chain_type") != "H":
        return {"error": f"ANARCI: {entry.get('error') or 'not VH'}"}

    numbering = entry.get("numbering", [])
    cdr_ranges = {
        "cdr1": (31, 35),
        "cdr2": (50, 65),
        "cdr3": (95, 102),
    }
    cdrs: Dict[str, str] = {}
    for cdr_name, (lo, hi) in cdr_ranges.items():
        res = [aa for (pos, _), aa in numbering if lo <= pos <= hi and aa != "-"]
        cdrs[cdr_name] = "".join(res)

    return {
        "cdr1": cdrs["cdr1"],
        "cdr2": cdrs["cdr2"],
        "cdr3": cdrs["cdr3"],
        "cdr1_len": len(cdrs["cdr1"]),
        "cdr2_len": len(cdrs["cdr2"]),
        "cdr3_len": len(cdrs["cdr3"]),
    }


def fingerprint(seq: str) -> Dict[str, Any]:
    """Full CDR fingerprint for one VHH/VH sequence."""
    seq = seq.upper().strip()
    cdrs = extract_cdrs_kabat(seq)
    if cdrs.get("error"):
        return {"error": cdrs["error"]}

    c1, c2, c3 = cdrs["cdr1"], cdrs["cdr2"], cdrs["cdr3"]
    all_cdr = c1 + c2 + c3

    return {
        "cdr1": c1, "cdr2": c2, "cdr3": c3,
        "cdr1_len": len(c1), "cdr2_len": len(c2), "cdr3_len": len(c3),
        "cdr3_net_charge": net_charge(c3),
        "cdr3_gravy": gravy(c3),
        "cdr3_acid_density": acid_density(c3),
        "cdr3_arom_density": arom_density(c3),
        "all_cdr_gravy": gravy(all_cdr),
        "cdr3_has_nglyc": has_nglyc(c3),
        "any_cdr_has_nglyc": has_nglyc(all_cdr),
        "any_cdr_deamid": has_deamid(all_cdr),
        "cdr3_anchor": cdr3_anchor(c3),
        "cdr3_anchor_risk": cdr3_anchor(c3) in "PD",
        "seq_len": len(seq),
    }


# ─────────────────────────────────────────────────────────────────────────────
# Load all 4 databases
# ─────────────────────────────────────────────────────────────────────────────

def load_database_a() -> List[Dict[str, Any]]:
    """
    138 autonomous human VH single-domain antibodies (Database A).
    Sub-labeled as 'Eng-VH' if single_domain_strategy contains camelization
    (i.e., genuine E44/R45-type VHH-like conversion, ~9 entries).
    All 138 also contribute to the 'DB-A' group for full-database stats.
    """
    p = BASE / "data/sabdab_vhh_atlas/autonomous_human_vh_db.json"
    raw = json.loads(p.read_text())
    entries = []
    for e in raw:
        seq = (e.get("sequence") or "").strip().upper()
        if not seq: continue
        strategy = str(e.get("single_domain_strategy") or "")
        # Genuine camelization sub-group: VHH-like E44/R45 conversion
        is_camel_eng = "camelization" in strategy.lower()
        entries.append({
            "db": "Eng-VH" if is_camel_eng else "DB-A",
            "id": f"{e.get('pdb','?')}_{e.get('chain','?')}",
            "pdb": e.get("pdb"),
            "target": e.get("target") or e.get("antigen_name"),
            "sequence": seq,
            "hallmark": e.get("hallmark_motif_pos37_44_45_47"),
            "germline": e.get("germline_best_match"),
            "n_interface_mut": e.get("n_interface_mutations", 0),
            "strategy": strategy,
        })
    return entries


def load_database_b() -> List[Dict[str, Any]]:
    """29 humanized camelid VHH."""
    p = BASE / "data/sabdab_vhh_atlas/humanized_camelid_vhh_db.json"
    raw = json.loads(p.read_text())
    entries = []
    for e in raw:
        seq = (e.get("sequence") or "").strip().upper()
        if not seq: continue
        entries.append({
            "db": "DB-B",
            "id": f"{e.get('pdb','?')}_{e.get('chain','?')}",
            "pdb": e.get("pdb"),
            "target": e.get("target") or e.get("antigen_name"),
            "sequence": seq,
        })
    return entries


def load_clinical_vhh() -> List[Dict[str, Any]]:
    """39 clinical/approved VHH."""
    p = BASE / "data/vhh_clinical_39_union/vhh_39_sequences_clinical_validated.json"
    raw = json.loads(p.read_text())
    entries = []
    for e in raw.get("vhh", []):
        seq = (e.get("Sequence") or "").strip().upper()
        if not seq: continue
        entries.append({
            "db": "Clinical",
            "id": e.get("Name", "?"),
            "pdb": None,
            "target": e.get("Target"),
            "sequence": seq,
        })
    return entries


def load_engineered_vh_24() -> List[Dict[str, Any]]:
    """
    24 Engineered Human VH single-domain antibodies from Atlas v3.
    """
    p = BASE / "data/vhh_design_atlas_v3.json"
    if not p.exists():
        return []
    raw = json.loads(p.read_text())
    entries = []
    for e in raw:
        cat = str(e.get("category") or e.get("Category") or "")
        if cat == "Engineered_Human_VH":
            seq = (e.get("sequence") or "").strip().upper()
            if not seq: continue
            entries.append({
                "db": "Eng-VH-24",
                "id": e.get("name") or e.get("pdb_id") or "?",
                "pdb": e.get("pdb_id"),
                "target": e.get("target"),
                "sequence": seq,
            })
    return entries


def load_all() -> List[Dict[str, Any]]:
    entries = []
    entries.extend(load_clinical_vhh())
    entries.extend(load_database_b())
    entries.extend(load_database_a())
    entries.extend(load_engineered_vh_24())
    return entries


# ─────────────────────────────────────────────────────────────────────────────
# Statistics helpers
# ─────────────────────────────────────────────────────────────────────────────

def stats(values: List[float]) -> Dict[str, float]:
    if not values:
        return {"n": 0, "mean": None, "std": None, "min": None, "p25": None, "median": None, "p75": None, "max": None}
    n = len(values)
    v = sorted(values)
    mean = sum(v) / n
    variance = sum((x - mean) ** 2 for x in v) / n
    std = math.sqrt(variance)
    def pct(p):
        idx = (n - 1) * p
        lo, hi = int(idx), min(int(idx) + 1, n - 1)
        return round(v[lo] + (idx - lo) * (v[hi] - v[lo]), 3)
    return {
        "n": n, "mean": round(mean, 3), "std": round(std, 3),
        "min": round(v[0], 3), "p25": pct(0.25),
        "median": pct(0.50), "p75": pct(0.75), "max": round(v[-1], 3),
    }


def db_stats(fps: List[Dict[str, Any]], metric: str) -> Dict[str, float]:
    vals = [fp[metric] for fp in fps if fp.get(metric) is not None and not fp.get("error")]
    return stats(vals)


def flag_rate(fps: List[Dict[str, Any]], flag: str) -> str:
    valid = [fp for fp in fps if not fp.get("error")]
    if not valid: return "—"
    n = sum(1 for fp in valid if fp.get(flag))
    return f"{n}/{len(valid)} ({n*100//len(valid)}%)"


# ─────────────────────────────────────────────────────────────────────────────
# Report generation
# ─────────────────────────────────────────────────────────────────────────────

DB_LABELS = {
    "Clinical": "Clinical VHH (39)",
    "DB-B":     "DB-B Humanized Camelid VHH (29)",
    "DB-A":     "DB-A Autonomous Human VH (129)",
    "Eng-VH":   "DB-A Camelization sub-group (9)",
    "Eng-VH-24": "Engineered Human VH (Atlas-24)",
}
DB_ORDER = ["Clinical", "DB-B", "DB-A", "Eng-VH", "Eng-VH-24"]


def md_stat_row(label: str, metric: str, by_db: Dict[str, List]) -> str:
    cells = [label]
    for db in DB_ORDER:
        fps = by_db.get(db, [])
        s = db_stats(fps, metric)
        if s["n"] == 0:
            cells.append("—")
        else:
            cells.append(f"{s['mean']} ± {s['std']} [{s['min']}…{s['max']}]")
    return "| " + " | ".join(cells) + " |"


def md_flag_row(label: str, flag: str, by_db: Dict[str, List]) -> str:
    cells = [label]
    for db in DB_ORDER:
        cells.append(flag_rate(by_db.get(db, []), flag))
    return "| " + " | ".join(cells) + " |"


def generate_report(all_results: List[Dict[str, Any]]) -> str:
    # Group by db
    by_db: Dict[str, List] = {db: [] for db in DB_ORDER}
    for r in all_results:
        db = r.get("db", "?")
        fp = r.get("fingerprint") or {}
        fp["db"] = db
        fp["id"] = r.get("id")
        fp["target"] = r.get("target")
        by_db.setdefault(db, []).append(fp)

    lines = []
    lines.append("# CDR Fingerprint Cross-Database Analysis")
    lines.append("> Generated by `scripts/analyze_cdr_fingerprint_4db.py`")
    lines.append("> **Purpose:** Identify systematic CDR-level differences between VH-derived VHH")
    lines.append("> and native/clinical VHH — assess expression and affinity risks.")
    lines.append("")

    # Database sizes
    lines.append("## 0. Database Sizes Processed")
    lines.append("")
    lines.append("| Database | Label | Entries loaded | ANARCI success |")
    lines.append("|----------|-------|---------------|----------------|")
    for db in DB_ORDER:
        fps = by_db.get(db, [])
        ok = sum(1 for fp in fps if not fp.get("error"))
        lines.append(f"| `{db}` | {DB_LABELS.get(db, db)} | {len(fps)} | {ok} |")
    lines.append("")

    # CDR length stats
    lines.append("## 1. CDR Length Distribution")
    lines.append("")
    lines.append(f"| Metric | {' | '.join(DB_LABELS.get(db, db).split(' (')[0] for db in DB_ORDER)} |")
    lines.append("|--------|" + "|".join("---" for _ in DB_ORDER) + "|")
    for metric, label in [("cdr1_len", "CDR-H1 length"), ("cdr2_len", "CDR-H2 length"), ("cdr3_len", "CDR-H3 length")]:
        lines.append(md_stat_row(label, metric, by_db))
    lines.append("")

    # CDR-H3 physicochemistry
    lines.append("## 2. CDR-H3 Physicochemistry")
    lines.append("")
    lines.append(f"| Metric | {' | '.join(DB_LABELS.get(db, db).split(' (')[0] for db in DB_ORDER)} |")
    lines.append("|--------|" + "|".join("---" for _ in DB_ORDER) + "|")
    for metric, label in [
        ("cdr3_net_charge",    "CDR-H3 Net Charge"),
        ("cdr3_gravy",         "CDR-H3 GRAVY"),
        ("cdr3_acid_density",  "CDR-H3 Acid density (D/E fraction)"),
        ("cdr3_arom_density",  "CDR-H3 Aromatic density (F/W/Y)"),
        ("all_cdr_gravy",      "All-CDR GRAVY"),
    ]:
        lines.append(md_stat_row(label, metric, by_db))
    lines.append("")

    # Risk flags
    lines.append("## 3. Expression & Affinity Risk Flags")
    lines.append("")
    lines.append(f"| Flag | {' | '.join(DB_LABELS.get(db, db).split(' (')[0] for db in DB_ORDER)} |")
    lines.append("|------|" + "|".join("---" for _ in DB_ORDER) + "|")
    for flag, label in [
        ("any_cdr_has_nglyc",   "N-glycosylation motif in any CDR"),
        ("any_cdr_deamid",      "Deamidation (NG/NS) in any CDR"),
        ("cdr3_anchor_risk",    "CDR-H3 anchor = Pro/Asp (expression risk)"),
    ]:
        lines.append(md_flag_row(label, flag, by_db))
    lines.append("")

    # CDR-H3 net charge distribution (critical for pI analysis)
    lines.append("## 4. CDR-H3 Net Charge Breakdown (Key for pI Risk)")
    lines.append("")
    lines.append("*(Negative CDR-H3 net charge drives low pI → expression & formulation risk in VHH)*")
    lines.append("")
    for db in DB_ORDER:
        fps = [fp for fp in by_db.get(db, []) if not fp.get("error") and fp.get("cdr3_net_charge") is not None]
        if not fps: continue
        neg = sum(1 for fp in fps if fp["cdr3_net_charge"] < -1)
        neutral = sum(1 for fp in fps if -1 <= fp["cdr3_net_charge"] <= 1)
        pos = sum(1 for fp in fps if fp["cdr3_net_charge"] > 1)
        mean_nc = round(sum(fp["cdr3_net_charge"] for fp in fps) / len(fps), 2)
        lines.append(f"**{DB_LABELS.get(db, db)}** (n={len(fps)}, mean={mean_nc})")
        lines.append(f"- Negative (< −1): {neg} ({neg*100//len(fps)}%)")
        lines.append(f"- Neutral [−1, +1]: {neutral} ({neutral*100//len(fps)}%)")
        lines.append(f"- Positive (> +1): {pos} ({pos*100//len(fps)}%)")
        lines.append("")

    # CDR-H3 length × charge cross-table for DB-A vs Clinical
    lines.append("## 5. CDR-H3 Length × Net Charge Cross-Analysis (DB-A + Eng-VH vs Clinical VHH)")
    lines.append("")
    lines.append("| CDR-H3 Length | Clinical VHH mean charge | DB-A+Eng mean charge | Delta |")
    lines.append("|---------------|--------------------------|---------------------|-------|")
    clin_fps = [fp for fp in by_db.get("Clinical", []) if not fp.get("error")]
    dba_fps  = [fp for fp in by_db.get("DB-A", []) + by_db.get("Eng-VH", []) if not fp.get("error")]
    for lo, hi in [(3, 9), (10, 13), (14, 17), (18, 30)]:
        c_vals = [fp["cdr3_net_charge"] for fp in clin_fps if lo <= (fp.get("cdr3_len") or 0) <= hi]
        a_vals = [fp["cdr3_net_charge"] for fp in dba_fps  if lo <= (fp.get("cdr3_len") or 0) <= hi]
        c_mean = round(sum(c_vals)/len(c_vals), 2) if c_vals else None
        a_mean = round(sum(a_vals)/len(a_vals), 2) if a_vals else None
        delta = round(a_mean - c_mean, 2) if (c_mean is not None and a_mean is not None) else "—"
        lines.append(f"| {lo}–{hi} aa | {c_mean or '—'} (n={len(c_vals)}) | {a_mean or '—'} (n={len(a_vals)}) | {delta} |")
    lines.append("")

    # N-glycosylation hotspots in DB-A
    lines.append("## 6. N-Glycosylation Hotspots in DB-A CDRs")
    lines.append("")
    lines.append("*(Exposed sequons in VHH without VL shielding → expression heterogeneity)*")
    lines.append("")
    nglyc_cases = [(fp["id"], fp.get("cdr3","?"), fp["db"])
                   for fp in by_db.get("DB-A",[]) + by_db.get("Eng-VH",[])
                   if fp.get("any_cdr_has_nglyc") and not fp.get("error")]
    if nglyc_cases:
        lines.append(f"DB-A entries with N-X-S/T in any CDR ({len(nglyc_cases)}):")
        for id_, c3, db_ in nglyc_cases[:15]:
            lines.append(f"  - `{id_}` [{db_}] | CDR-H3: `{c3}`")
    else:
        lines.append("No N-glycosylation motifs in DB-A CDRs.")
    lines.append("")

    # Algorithm implications
    lines.append("## 7. Algorithm Validation Implications")
    lines.append("")
    lines.append("| Finding | Implication for VH→VHH Algorithm |")
    lines.append("|---------|-----------------------------------|")

    # Compute key numbers using combined DB-A + Eng-VH
    all_dba = [fp for fp in by_db.get("DB-A",[]) + by_db.get("Eng-VH",[]) + by_db.get("Eng-VH-24", []) if not fp.get("error")]
    clin_fps_clean = [fp for fp in by_db.get("Clinical", []) if not fp.get("error")]
    eng_24_fps = [fp for fp in by_db.get("Eng-VH-24", []) if not fp.get("error")]

    clin_mean_nc = round(sum(fp.get("cdr3_net_charge",0) for fp in clin_fps_clean)/max(len(clin_fps_clean),1), 2) if clin_fps_clean else "?"
    dba_mean_nc  = round(sum(fp.get("cdr3_net_charge",0) for fp in all_dba)/max(len(all_dba),1), 2) if all_dba else "?"
    eng24_mean_nc = round(sum(fp.get("cdr3_net_charge",0) for fp in eng_24_fps)/max(len(eng_24_fps),1), 2) if eng_24_fps else "?"
    
    clin_neg_pct = round(sum(1 for fp in clin_fps_clean if fp.get("cdr3_net_charge",0) < -1)*100/max(len(clin_fps_clean),1)) if clin_fps_clean else 0
    dba_neg_pct  = round(sum(1 for fp in all_dba if fp.get("cdr3_net_charge",0) < -1)*100/max(len(all_dba),1)) if all_dba else 0
    eng24_neg_pct = round(sum(1 for fp in eng_24_fps if fp.get("cdr3_net_charge",0) < -1)*100/max(len(eng_24_fps),1)) if eng_24_fps else 0

    lines.append(f"| DB-A CDR-H3 mean charge={dba_mean_nc} vs Clinical mean={clin_mean_nc} | DB-A is systematically {'more acidic — higher pI risk for VH→VHH' if (dba_mean_nc not in ('?',) and clin_mean_nc not in ('?',) and float(str(dba_mean_nc)) < float(str(clin_mean_nc))) else 'similar to or more basic than clinical VHH'} |")
    lines.append(f"| Engineered-24 mean charge={eng24_mean_nc} vs Clinical mean={clin_mean_nc} | Eng-24 is {'more acidic' if (eng24_mean_nc not in ('?',) and clin_mean_nc not in ('?',) and float(str(eng24_mean_nc)) < float(str(clin_mean_nc))) else 'similar/more basic'} |")
    lines.append(f"| DB-A negative CDR-H3 charge rate={dba_neg_pct}% vs Clinical={clin_neg_pct}% | {'DB-A has lower negative-CDR3 prevalence' if dba_neg_pct < clin_neg_pct else 'Consistent with or worse than clinical VHH'} |")
    lines.append(f"| Eng-24 negative CDR-H3 charge rate={eng24_neg_pct}% vs Clinical={clin_neg_pct}% | {'Eng-24 has lower negative-CDR3 prevalence' if eng24_neg_pct < clin_neg_pct else 'Consistent with or worse than clinical VHH'} |")

    clin_ng = round(sum(1 for fp in clin_fps_clean if fp.get("any_cdr_has_nglyc"))*100/max(len(clin_fps_clean),1)) if clin_fps_clean else 0
    dba_ng  = round(sum(1 for fp in all_dba if fp.get("any_cdr_has_nglyc"))*100/max(len(all_dba),1)) if all_dba else 0
    lines.append(f"| N-glycosylation: DB-A={dba_ng}% vs Clinical={clin_ng}% | {'VH→VHH conversion must flag sequons exposed by removal of VL' if dba_ng > clin_ng else 'N-glyc risk comparable or lower in DB-A'} |")

    clin_g = round(sum(fp.get("all_cdr_gravy",0) for fp in clin_fps_clean)/max(len(clin_fps_clean),1), 3) if clin_fps_clean else "?"
    dba_g  = round(sum(fp.get("all_cdr_gravy",0) for fp in all_dba)/max(len(all_dba),1), 3) if all_dba else "?"
    lines.append(f"| All-CDR GRAVY: DB-A={dba_g} vs Clinical={clin_g} | {'DB-A CDRs are more hydrophobic → aggregation risk in VHH format without VL shielding' if (dba_g not in ('?',) and clin_g not in ('?',) and float(str(dba_g)) > float(str(clin_g))) else 'CDR hydrophobicity similar or lower in DB-A'} |")

    # CDR-H3 length comparison
    clin_c3_mean = round(sum(fp.get("cdr3_len",0) for fp in clin_fps_clean)/max(len(clin_fps_clean),1), 1) if clin_fps_clean else "?"
    dba_c3_mean  = round(sum(fp.get("cdr3_len",0) for fp in all_dba)/max(len(all_dba),1), 1) if all_dba else "?"
    dba_long_c3  = round(sum(1 for fp in all_dba if (fp.get("cdr3_len") or 0) >= 16)*100/max(len(all_dba),1)) if all_dba else 0
    clin_long_c3 = round(sum(1 for fp in clin_fps_clean if (fp.get("cdr3_len") or 0) >= 16)*100/max(len(clin_fps_clean),1)) if clin_fps_clean else 0
    lines.append(f"| DB-A mean CDR-H3 length={dba_c3_mean} vs Clinical={clin_c3_mean}; long (≥16): DB-A={dba_long_c3}% vs Clinical={clin_long_c3}% | {'DB-A has higher proportion of long CDR3 → elevated Conformational Mismatch Risk (CDR3-FR2 decoupling) in VH→VHH conversion' if dba_long_c3 > clin_long_c3 else 'CDR3 length distribution comparable'} |")

    lines.append("")
    return "\n".join(lines)


# ─────────────────────────────────────────────────────────────────────────────
# Main
# ─────────────────────────────────────────────────────────────────────────────

def main() -> int:
    print("Loading all 4 databases...")
    entries = load_all()
    print(f"  Total entries: {len(entries)}")

    # Count by DB
    from collections import Counter
    db_counts = Counter(e["db"] for e in entries)
    for db, n in db_counts.items():
        print(f"  [{db}]: {n}")
    print()

    print("Computing CDR fingerprints (ANARCI)...")
    all_results = []
    for i, entry in enumerate(entries):
        if (i+1) % 20 == 0 or (i+1) == len(entries):
            print(f"  {i+1}/{len(entries)}...", end="\r", flush=True)
        fp = fingerprint(entry["sequence"])
        all_results.append({**entry, "fingerprint": fp})
    print()

    # Summary
    errors = sum(1 for r in all_results if r.get("fingerprint", {}).get("error"))
    print(f"ANARCI errors: {errors}/{len(all_results)}")

    # Save JSON
    out_json = BASE / ".tmp_cdr_fingerprint_4db.json"
    out_json.write_text(json.dumps(all_results, indent=2, ensure_ascii=False, default=str), encoding="utf-8")
    print(f"JSON saved: {out_json}")

    # Generate report
    md = generate_report(all_results)
    out_md = BASE / ".tmp_cdr_fingerprint_4db.md"
    out_md.write_text(md, encoding="utf-8")
    print(f"Report saved: {out_md}")

    # Print summary table to console
    print()
    print(md)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
