"""
VL-Interface Hydrophobic Patch Map
====================================
Defines canonical VH residues that contact VL in conventional Fv, scans engineered
VHH sequences to identify hydrophobic exposure risk (positions where bulky hydrophobic
side chains lose VL packing and face solvent).

Position derivation: pattern-matched relative to FR2 anchor (W-V-R/G-Q) and FR3 Cys2 anchor.
Reference: Honegger & Plückthun 2001 + Lefranc IMGT VH-VL interface map + AutonomousHumanVH cohort (n=36).
"""
from __future__ import annotations
import re
import json
from pathlib import Path
from typing import Dict, List, Optional

ROOT = Path(__file__).resolve().parent.parent
V1813_DIR = ROOT / "projects" / "CD3_VH2VHH_Batch_20260515" / "v1813_reports"

# Hydrophobic amino acids (Kyte-Doolittle GRAVY > 1.0): V/L/I/F/W/Y/M/C/A
HYDROPHOBIC = set("VLIFWYMA")
STRONG_HYDROPHOBIC = set("VLIFWY")  # excludes M, A, C

# Canonical VL-interface positions (Kabat) and their VHH-natural targets
VL_INTERFACE_POSITIONS = {
    "k35":  {"role": "CDR1-FR2 edge",     "vh_typical": "H/N/A", "vhh_target_class": "polar",     "anchor": "fr2_pre"},
    "k37":  {"role": "FR2 deep pocket",   "vh_typical": "V/I",    "vhh_target_class": "F or Y",    "anchor": "fr2_pre"},
    "k39":  {"role": "FR2 surface",       "vh_typical": "Q/K/R",  "vhh_target_class": "polar",     "anchor": "fr2_pre"},
    "k44":  {"role": "FR2 VL contact",    "vh_typical": "Q/G",    "vhh_target_class": "E",         "anchor": "fr2_hallmark"},
    "k45":  {"role": "FR2 core hallmark", "vh_typical": "L",      "vhh_target_class": "R",         "anchor": "fr2_hallmark"},
    "k47":  {"role": "FR2 deep VL pocket","vh_typical": "W",      "vhh_target_class": "F/G/L",     "anchor": "fr2_hallmark"},
    "k50":  {"role": "CDR2 anchor",       "vh_typical": "S/R/Y",  "vhh_target_class": "D",         "anchor": "cdr2_start"},
    "k89":  {"role": "FR3 VL contact",    "vh_typical": "V",      "vhh_target_class": "V/L",       "anchor": "fr3_cys2"},
    "k91":  {"role": "FR3 VL edge",       "vh_typical": "Y",      "vhh_target_class": "Y",         "anchor": "fr3_cys2"},
    "k103": {"role": "CDR3 anchor (Trp)", "vh_typical": "W",      "vhh_target_class": "W (locked)","anchor": "fr4_wgxg"},
}


def find_canonical_cys2(seq: str) -> Optional[int]:
    m = re.search(r'[A-Z]C[AS][KR]', seq[85:115])
    if m: return 85 + m.start() + 1
    m = re.search(r'[YFW][YFC]C', seq[80:112])
    if m: return 80 + m.start() + 2
    return None


def find_fr2_hallmark_anchor(seq: str) -> Optional[int]:
    """Find G-L/A/R-E/Q-W motif anchor (positions 44-45-46-47 reside relative to this)."""
    m = re.search(r'[GA][LRA][EQ][WLY]', seq[35:55])
    if m: return 35 + m.start()
    return None


def find_fr2_pre_anchor(seq: str) -> Optional[int]:
    """Find W34 (start of FR2) via multiple motif variants. Returns idx of W."""
    # Standard human VH: WVRQ / WIRQ / WVGQ
    m = re.search(r'W[VI][RG]Q', seq[30:55])
    if m: return 30 + m.start()
    # Mouse VH / IGHV1 variants: WVKQ (Kabat 38 = K in some mouse), WIKQ
    m = re.search(r'W[VI][KR][KQR]', seq[30:55])
    if m: return 30 + m.start()
    # General fallback: W at expected position followed by hydrophobic + polar
    m = re.search(r'W[VILM][A-Z][QKR]', seq[30:55])
    if m: return 30 + m.start()
    return None


def find_cdr2_start(seq: str) -> Optional[int]:
    """CDR2 starts ~ Kabat 50 (after FR2 ends with KGLEW or similar; commonly ~8 res after W34)."""
    fr2_anchor = find_fr2_pre_anchor(seq)
    if fr2_anchor is not None:
        return fr2_anchor + 15  # rough: W34 + 16 = 50 (Kabat)
    return None


def find_fr4_wgxg(seq: str) -> Optional[int]:
    """W of WGXG motif at start of FR4 (Kabat 103 = W)."""
    m = re.search(r'WG.G', seq[95:])
    if m: return 95 + m.start()
    return None


def _derive_positions(seq: str) -> Dict[str, Optional[int]]:
    """Derive canonical Kabat positions from anchors. Returns label → seq_idx."""
    fr2_hallmark = find_fr2_hallmark_anchor(seq)  # points to G at Kabat 44
    fr2_pre = find_fr2_pre_anchor(seq)            # points to W at Kabat 36
    cys2 = find_canonical_cys2(seq)                # position of FR3-terminal Cys (Kabat 92)
    cdr2_start = find_cdr2_start(seq)
    fr4_wgxg = find_fr4_wgxg(seq)

    positions: Dict[str, Optional[int]] = {}
    if fr2_pre is not None:
        # W is Kabat 36 in conventional VH numbering
        positions["k35"] = fr2_pre - 1     # H35 or other (just before W36)
        positions["k36_W"] = fr2_pre       # W36 (always W; conserved)
        positions["k37"] = fr2_pre + 1     # V37 (deep VL pocket)
        positions["k38"] = fr2_pre + 2     # V/K38
        positions["k39"] = fr2_pre + 3     # Q39
    if fr2_hallmark is not None:
        positions["k44"] = fr2_hallmark     # G44 (in GLEW) — Hallmark rescue position
        positions["k45"] = fr2_hallmark + 1 # L45 (Hallmark core)
        positions["k46"] = fr2_hallmark + 2 # E46
        positions["k47"] = fr2_hallmark + 3 # W47 (Hallmark deep)
    if cdr2_start is not None:
        positions["k50"] = cdr2_start       # CDR2 anchor
    if cys2 is not None:
        # cys2 ≈ Kabat 92 (Cys). Then Kabat 91 = cys-1 (Y), 89 = cys-3 (V/T), 94 = cys+2
        positions["k89"] = cys2 - 3
        positions["k91"] = cys2 - 1
        positions["k94"] = cys2 + 2
    if fr4_wgxg is not None:
        positions["k103"] = fr4_wgxg        # W of WGXG (always W; conserved)
    return positions


def map_vl_interface_residues(orig_seq: str, eng_seq: str) -> List[Dict]:
    """
    Use ORIGINAL sequence to derive anchor positions (eliminates anchor drift
    after Hallmark mutations), then compare residue at each position between
    original and engineered. V1.8.x mutations are point substitutions only, so
    indices are preserved.
    """
    positions = _derive_positions(orig_seq)
    result = []
    for k_label, idx in positions.items():
        if idx is None or idx < 0 or idx >= len(orig_seq):
            continue
        orig_aa = orig_seq[idx]
        eng_aa = eng_seq[idx] if idx < len(eng_seq) else "-"
        meta = VL_INTERFACE_POSITIONS.get(k_label, {"role": "—", "vh_typical": "—", "vhh_target_class": "—"})

        def _risk(aa):
            if k_label in ("k36_W", "k103"):
                return "conserved" if aa == "W" else f"BROKEN ({aa}, should be W)"
            is_strong = aa in STRONG_HYDROPHOBIC
            is_hp = aa in HYDROPHOBIC
            vhh_t = meta["vhh_target_class"]
            if is_strong:
                if aa in vhh_t:
                    return "LOW (matches VHH-natural)"
                if vhh_t in ("R", "E", "D", "polar"):
                    return "HIGH (hydrophobic but should be polar/charged)"
                return "MEDIUM (hydrophobic, partially compatible)"
            if is_hp:
                return "LOW (mildly hydrophobic)"
            return "OK (not hydrophobic)"

        result.append({
            "kabat": k_label,
            "seq_idx": idx,
            "seq_pos": idx + 1,
            "orig_residue": orig_aa,
            "eng_residue": eng_aa,
            "changed": orig_aa != eng_aa,
            "role": meta["role"],
            "vh_typical": meta["vh_typical"],
            "vhh_target": meta["vhh_target_class"],
            "orig_risk": _risk(orig_aa),
            "eng_risk": _risk(eng_aa),
        })
    return result


def main():
    samples = ["SP34", "Teplizumab", "OKT3", "Visilizumab", "Otelixizumab", "Foralumab"]
    report = {}
    for name in samples:
        json_path = V1813_DIR / f"{name}_v1813.json"
        if not json_path.exists():
            continue
        d = json.loads(json_path.read_text(encoding="utf-8"))
        orig_seq = d["input_seq"]
        eng_seq = d.get("final_seq", orig_seq)
        ighv = d["ighv_family"]

        vl_map = map_vl_interface_residues(orig_seq, eng_seq)
        report[name] = {"ighv": ighv, "vl_interface_map": vl_map}

        print(f"\n=== {name}  (IGHV: {ighv}) ===")
        print(f"  {'Kabat':<7} {'role':<28} {'orig':<5} {'eng':<5} {'change':<8} {'eng_risk':<55}")
        for r in vl_map:
            change = f"{r['orig_residue']}→{r['eng_residue']}" if r['changed'] else "—"
            print(f"  {r['kabat']:<7} {r['role'][:27]:<28} {r['orig_residue']:<5} {r['eng_residue']:<5} {change:<8} {r['eng_risk']:<55}")

    out = ROOT / "data" / "_v1814_design" / "vl_interface_hydrophobic_map.json"
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(report, indent=2, ensure_ascii=False), encoding="utf-8")
    print(f"\nSaved → {out}")


if __name__ == "__main__":
    main()
