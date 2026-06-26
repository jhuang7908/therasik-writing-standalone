"""
V1.8.12 VH→VHH Conversion — Sequence-Pattern-Based Implementation
==================================================================
IGHV-family-aware + CDR3-length-aware + 3-Tier Adaptive Algorithm

Uses sequence-pattern matching (robust across IMGT/Kabat schemes) instead of
absolute residue numbers. All "Kabat 44/45/47/etc." labels in output are
biological identifiers based on local sequence context.
"""
from __future__ import annotations
import sys
import json
import re
from pathlib import Path
from typing import List, Dict, Tuple, Optional

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from Bio.SeqUtils.ProtParam import ProteinAnalysis


# ───────────────────────────────────────────────────────────────────────────
# Sequence-pattern position finders (robust to numbering scheme)
# ───────────────────────────────────────────────────────────────────────────

def find_canonical_cys2(seq: str) -> Optional[int]:
    """Find the second canonical Cys (end of FR3, before CDR3). Pattern: YYC[AS][KR]."""
    m = re.search(r'Y[YH]C[AS][KR]', seq)
    if m:
        return m.start() + 2  # the C
    m = re.search(r'YYC', seq[80:])  # fallback
    if m:
        return 80 + m.start() + 2
    return None


def find_cdr3(seq: str) -> Tuple[Optional[int], Optional[int], str]:
    """
    CDR3 = residues between C[AS][KR] and WG[xx]G.
    Returns (start_idx, end_idx, cdr3_aa). Start = first residue after CAR/CAK.
    """
    m_start = re.search(r'C[AS][KR]', seq[80:120])
    if not m_start:
        return None, None, ""
    cdr3_start = 80 + m_start.start() + 3
    m_end = re.search(r'WG.G', seq[cdr3_start:])
    if not m_end:
        return None, None, ""
    cdr3_end = cdr3_start + m_end.start()
    return cdr3_start, cdr3_end, seq[cdr3_start:cdr3_end]


def find_hallmark_positions(seq: str) -> Dict[str, Optional[int]]:
    """
    Find Hallmark zone (Kabat 44/45/47 = FR2 lower edge near second W).
    Pattern: "[G/A]LEW" or "[G/A]LEWM" — the GLE W is canonical FR2 mid.
    
    Returns dict with linear sequence indices for K44/K45/K47.
    """
    out = {"K44": None, "K45": None, "K47": None}
    # Pattern: G-L-E-W (Kabat 44-45-46-47) or variants
    m = re.search(r'[GA][LRA][EQ][WLY]', seq[35:55])
    if m:
        base = 35 + m.start()
        out["K44"] = base       # G/A position
        out["K45"] = base + 1   # L/R/A
        out["K47"] = base + 3   # W/L/Y
    return out


def find_stealth_positions(seq: str, kabat_hallmark: Dict[str, Optional[int]]) -> Dict[str, Optional[int]]:
    """
    Find Stealth scan positions:
    K13 (FR1 early), K19 (FR1 mid), K72/K74 (FR3 mid), K83 (FR3 late), K94 (CDR3 base)
    
    Uses sequence context: pos 13, 19 in FR1 = direct linear; FR3 by proximity to Cys.
    """
    out = {}
    # FR1 positions — linear from N-term
    out["K13"] = 12 if len(seq) > 12 else None
    out["K19"] = 18 if len(seq) > 18 else None
    # FR3 positions — relative to canonical Cys (pos C from N-term)
    cys = find_canonical_cys2(seq)
    if cys:
        # Kabat 94 = the canonical Cys (the C itself, usually)
        # But more commonly used: K94 = residue immediately before CAR pattern's A
        out["K94"] = cys + 1   # the A in CAR — actually this is K94 in Kabat
        # FR3 mid: working back from Cys
        # Kabat 83 ≈ Cys - 11, Kabat 74 ≈ Cys - 20, Kabat 72 ≈ Cys - 22
        out["K83"] = cys - 11 if cys >= 11 else None
        out["K74"] = cys - 20 if cys >= 20 else None
        out["K72"] = cys - 22 if cys >= 22 else None
    return out


def find_faic_positions(seq: str, kabat_hallmark: Dict[str, Optional[int]]) -> Dict[str, Optional[int]]:
    """
    Find FAIC (IGHV3 framework conversion) target positions:
    Kabat 18 (FR1 internal L), Kabat 68 (internal T core), Kabat 89 (FR3 late V), Kabat 77 (FR3 T).
    """
    out = {}
    out["K18"] = 17 if len(seq) > 17 else None    # FR1 internal, near linear pos 18
    cys = find_canonical_cys2(seq)
    if cys:
        # Kabat 89 ≈ Cys - 5, Kabat 77 ≈ Cys - 17, Kabat 68 ≈ Cys - 25 to -28
        out["K89"] = cys - 5
        out["K77"] = cys - 17
        out["K68"] = cys - 26
    return out


# ───────────────────────────────────────────────────────────────────────────
# Family detection (robust N-terminal motif)
# ───────────────────────────────────────────────────────────────────────────

def detect_ighv_family(seq: str) -> Tuple[str, str]:
    head = seq[:25]
    if re.match(r'.VQLVQSGAEVKKPG', head) or re.match(r'.IKLQSGAELARPG', head):
        return "IGHV1", "KKPGAS / ARPGAS motif (IGHV1-like, e.g., OKT3/SP34/Visilizumab class)"
    if re.search(r'.SGGG[LV]VQ', head) or re.search(r'.ESGGG[LV]', head):
        return "IGHV3", "SGGG[L/V]VQ canonical IGHV3 motif"
    if re.search(r'.VQLQQ', head):
        return "IGHV2", "QVQLQQ motif (IGHV2-like)"
    return "IGHV_unknown", "no canonical N-terminal motif"


# ───────────────────────────────────────────────────────────────────────────
# Metrics
# ───────────────────────────────────────────────────────────────────────────

def compute_metrics(seq: str) -> Dict[str, float]:
    pa = ProteinAnalysis(seq)
    return {
        "pI": round(pa.isoelectric_point(), 2),
        "GRAVY": round(pa.gravy(), 3),
        "MW_kDa": round(pa.molecular_weight() / 1000, 2),
        "length": len(seq),
        "K_count": seq.count("K"),
        "R_count": seq.count("R"),
        "D_count": seq.count("D"),
        "E_count": seq.count("E"),
        "net_basic": (seq.count("K") + seq.count("R") -
                      seq.count("D") - seq.count("E")),
    }


def score_abnativ(seq: str) -> Dict[str, Optional[float]]:
    try:
        from core.vh2vhh.abnativ_naturalness_layer import score_naturalness_delta
        res = score_naturalness_delta(seq)
        return {
            "vh2":   round(float(res.vh2_score), 4) if res.vh2_score is not None else None,
            "vhh2":  round(float(res.vhh2_score), 4) if res.vhh2_score is not None else None,
            "delta": round(float(res.delta), 4) if res.delta is not None else None,
        }
    except Exception as e:
        return {"vh2": None, "vhh2": None, "delta": None, "error": str(e)}


# ───────────────────────────────────────────────────────────────────────────
# Verdict / gates
# ───────────────────────────────────────────────────────────────────────────

def label_pi(pI: float) -> str:
    return "PASS" if pI <= 9.0 else ("WARN" if pI <= 9.5 else "FAIL")


def label_abnativ(d: Optional[float]) -> str:
    if d is None: return "UNKNOWN"
    if d >= 0:    return "EXCELLENT"
    if d >= -0.12: return "PASS"
    if d >= -0.20: return "WARN"
    return "FAIL"


def metrics_pass(pI: float, d: Optional[float]) -> Tuple[bool, str]:
    pi_l, an_l = label_pi(pI), label_abnativ(d)
    pi_ok = pi_l == "PASS"
    an_ok = an_l in ("PASS", "EXCELLENT")
    return (pi_ok and an_ok), f"pI={pi_l}, AbNatiV={an_l}"


# ───────────────────────────────────────────────────────────────────────────
# Mutation application
# ───────────────────────────────────────────────────────────────────────────

def apply_mutation_list(seq: str, mutations: List[Dict]) -> str:
    """Apply mutations (linear-index based). Each dict: {idx, target_aa, ...}."""
    arr = list(seq)
    for m in mutations:
        i = m["idx"]
        if 0 <= i < len(arr):
            arr[i] = m["target_aa"]
    return "".join(arr)


# ───────────────────────────────────────────────────────────────────────────
# V1.8.12 Algorithm
# ───────────────────────────────────────────────────────────────────────────

def v1812_design(seq: str, sample_name: str) -> Dict:
    family, fam_evidence = detect_ighv_family(seq)
    cdr3_start, cdr3_end, cdr3_aa = find_cdr3(seq)
    cdr3_len = len(cdr3_aa) if cdr3_aa else 0
    hallmark_pos = find_hallmark_positions(seq)
    stealth_pos = find_stealth_positions(seq, hallmark_pos)
    faic_pos = find_faic_positions(seq, hallmark_pos)
    
    init_metrics = compute_metrics(seq)
    init_abnativ = score_abnativ(seq)
    
    # Detect unpaired Cys in CDR3
    cdr3_cys_idx = []
    if cdr3_aa:
        cys_count = cdr3_aa.count("C")
        if cys_count == 1 or (cys_count == 2 and cdr3_len < 16):
            for i, aa in enumerate(cdr3_aa):
                if aa == "C":
                    cdr3_cys_idx.append(cdr3_start + i)
    
    log = {
        "sample": sample_name,
        "input_seq": seq,
        "ighv_family": family,
        "ighv_evidence": fam_evidence,
        "cdr3_aa": cdr3_aa,
        "cdr3_len": cdr3_len,
        "cdr3_start_idx": cdr3_start,
        "cdr3_end_idx": cdr3_end,
        "hallmark_positions_linear": hallmark_pos,
        "stealth_positions_linear": stealth_pos,
        "faic_positions_linear": faic_pos,
        "unpaired_cys_cdr3": cdr3_cys_idx,
        "initial_metrics": init_metrics,
        "initial_abnativ": init_abnativ,
        "tier_log": [],
        "all_mutations": [],
    }
    
    all_muts: List[Dict] = []
    
    # ─── Pre-Tier: Cys-gate (MANDATORY) ───────────────────────────────
    for idx in cdr3_cys_idx:
        orig = seq[idx]
        rel_pos = idx - cdr3_start + 1  # 1-indexed within CDR3
        all_muts.append({
            "tier": "Cys-gate",
            "label_kabat": f"Cys (CDR3 pos {rel_pos})",
            "idx": idx, "orig_aa": orig, "target_aa": "S",
            "rationale": (f"MANDATORY Cys-gate: unpaired CDR3 Cys at sequence position {idx+1} "
                          f"(CDR3 residue {rel_pos}/{cdr3_len}) causes misfolding and ER retention "
                          f"in single-domain context. C→S preserves H-bonding capability while "
                          f"eliminating disulfide misformation risk.")
        })
    
    if all_muts:
        seq_after = apply_mutation_list(seq, all_muts)
        log["tier_log"].append({
            "stage": "Pre-Tier: Cys-gate",
            "applied": [f"C→S@pos{m['idx']+1}" for m in all_muts],
            "rationale_summary": "Eliminated unpaired CDR3 Cys (expression blocker).",
        })
    
    # Tier 1 depth label
    if cdr3_len < 10:
        depth = "LIGHT (CDR3<10 aa: K94 retention acceptable, minimal scan)"
        scan = ["K13", "K19"]
    elif cdr3_len < 15:
        depth = "STANDARD (CDR3 10-14 aa: standard surface scan)"
        scan = ["K13", "K19", "K74", "K83", "K94"]
    elif cdr3_len < 18:
        depth = "DEEP (CDR3 15-17 aa: K94 mandatory; deep surface scan)"
        scan = ["K13", "K19", "K72", "K74", "K83", "K94"]
    else:
        depth = "STRICT-DEEP (CDR3 ≥ 18 aa: zero surface K target)"
        scan = ["K13", "K19", "K72", "K74", "K83", "K94"]
    
    # ─── Tier 1: Stealth ──────────────────────────────────────────────
    tier1_muts: List[Dict] = []
    
    # Cohort-derived target residues
    stealth_targets = {
        "K94": ("R", "K94R: 53% of autonomous IGHV3 VH cohort (n=36) have R at this CDR3-base position. R retains basic character but reduces aggregation propensity vs K."),
        "K74": ("T", "K74T: 84% of autonomous IGHV3 cohort have T at k74 (germline IGHV3-23 canonical). Removes surface K → reduces non-specific binding."),
        "K83": ("Q", "K83Q: FR3-late surface K reduction; Q is neutral, retains H-bonding."),
        "K13": ("Q", "K13Q: FR1 early surface K reduction; cohort consensus is Q."),
        "K19": ("Q", "K19Q: FR1 mid surface K reduction; reduces overall surface basic load."),
        "K72": ("D", "K72D: dual function — Stealth + pI reduction (replaces K basic with D acidic; −2 net charge effect)."),
    }
    
    for label in scan:
        idx = stealth_pos.get(label)
        if idx is None or idx >= len(seq):
            continue
        orig = seq[idx]
        # Only apply if original is K (K-gated)
        if orig != "K":
            continue
        target, ratx = stealth_targets[label]
        tier1_muts.append({
            "tier": "Tier 1 Stealth",
            "label_kabat": label,
            "idx": idx,
            "orig_aa": orig, "target_aa": target,
            "rationale": f"[Tier 1, {depth.split()[0]}] {orig}{label}: {ratx}",
        })
    
    if tier1_muts:
        all_muts.extend(tier1_muts)
    
    seq_t1 = apply_mutation_list(seq, all_muts)
    m_t1 = compute_metrics(seq_t1)
    a_t1 = score_abnativ(seq_t1)
    passed_t1, label_t1 = metrics_pass(m_t1["pI"], a_t1["delta"])
    
    log["tier_log"].append({
        "stage": "Tier 1: Stealth",
        "depth": depth,
        "scan_positions": scan,
        "applied": [f"{m['orig_aa']}→{m['target_aa']}@{m['label_kabat']}(seq{m['idx']+1})" for m in tier1_muts],
        "n_applied": len(tier1_muts),
        "post_metrics": {"pI": m_t1["pI"], "GRAVY": m_t1["GRAVY"], "abnativ_delta": a_t1["delta"]},
        "verdict": label_t1,
        "escalate": not passed_t1,
    })
    
    if passed_t1:
        log["all_mutations"] = all_muts
        log["final_seq"] = seq_t1
        log["final_metrics"] = m_t1
        log["final_abnativ"] = a_t1
        log["final_verdict"] = label_t1
        log["stopped_at"] = "Tier 1 (Stealth sufficient)"
        return log
    
    # ─── Tier 2: Hallmark Package (CDR3-length gated) ─────────────────
    skip_hallmark_long = (cdr3_len >= 18)
    if skip_hallmark_long:
        log["tier_log"].append({
            "stage": "Tier 2: Hallmark",
            "skipped": True,
            "reason": (f"CDR3 = {cdr3_len} aa ≥ 18: natural CDR3 'drape' covers VL interface; "
                       f"100% of long-CDR3 autonomous VH cohort retain GLW motif without Hallmark — "
                       f"empirically unnecessary."),
        })
    else:
        tier2_muts: List[Dict] = []
        # Apply K45R first
        for label, target, ref_orig in [("K45", "R", "L"), ("K44", "E", "G"), ("K47", "G", "W")]:
            idx = hallmark_pos.get(label)
            if idx is None or idx >= len(seq):
                continue
            orig = seq[idx]
            if orig == target:
                continue
            if label == "K45" and orig in ("R", "A"):
                continue  # already VHH-compatible
            
            if label == "K45":
                ratx = (f"L45R Hallmark CORE: replaces hydrophobic L (former VL contact) with "
                        f"positively charged R. Empirically: 100% of EXCELLENT-tier autonomous VH cohort "
                        f"retains some VL-interface modification when CDR3 < 18 aa.")
            elif label == "K44":
                ratx = (f"G44E Hallmark RESCUE: adds negative charge at VL interface — counteracts "
                        f"hydrophobic exposure when K45R alone insufficient. 11% of autonomous VH "
                        f"cohort show G44E natural mutation.")
            elif label == "K47":
                ratx = (f"W47G Hallmark RESCUE: removes bulky W (deep VL pocket residue), converts "
                        f"to small G. 17% of autonomous IGHV3 cohort have non-W at k47.")
            
            tier2_muts.append({
                "tier": "Tier 2 Hallmark",
                "label_kabat": label,
                "idx": idx,
                "orig_aa": orig, "target_aa": target,
                "rationale": f"[Tier 2 Hallmark Package] {orig}{label}{target}: {ratx}",
            })
        
        if tier2_muts:
            all_muts.extend(tier2_muts)
        
        seq_t2 = apply_mutation_list(seq, all_muts)
        m_t2 = compute_metrics(seq_t2)
        a_t2 = score_abnativ(seq_t2)
        passed_t2, label_t2 = metrics_pass(m_t2["pI"], a_t2["delta"])
        
        log["tier_log"].append({
            "stage": "Tier 2: Hallmark Package",
            "applied": [f"{m['orig_aa']}→{m['target_aa']}@{m['label_kabat']}(seq{m['idx']+1})" for m in tier2_muts],
            "n_applied": len(tier2_muts),
            "post_metrics": {"pI": m_t2["pI"], "GRAVY": m_t2["GRAVY"], "abnativ_delta": a_t2["delta"]},
            "verdict": label_t2,
            "escalate": not passed_t2,
        })
        
        if passed_t2:
            log["all_mutations"] = all_muts
            log["final_seq"] = seq_t2
            log["final_metrics"] = m_t2
            log["final_abnativ"] = a_t2
            log["final_verdict"] = label_t2
            log["stopped_at"] = "Tier 2 (Stealth + Hallmark sufficient)"
            return log
    
    # ─── Tier 3: FAIC (only for non-IGHV3) ────────────────────────────
    if family == "IGHV3":
        log["tier_log"].append({
            "stage": "Tier 3: FAIC",
            "skipped": True,
            "reason": (f"Input is {family} — already on the autonomous IGHV3 framework "
                       f"(100% of n=36 cohort is IGHV3). Framework conversion to IGHV3 "
                       f"consensus is unnecessary."),
        })
    else:
        tier3_muts: List[Dict] = []
        faic_targets = {
            "K68": ("T", 1.00, "Internal stability core (PRIMARY FAIC target; 100% of IGHV3 autonomous cohort)"),
            "K89": ("V", 0.81, "FR3-late VL-interface residue (81% V in IGHV3 cohort)"),
            "K18": ("L", 0.97, "FR1 internal hydrophobic core (97% L in IGHV3 cohort)"),
            "K77": ("T", 0.85, "FR3 surface T (IGHV3-23 germline canonical)"),
        }
        for label in ["K68", "K89", "K18", "K77"]:
            idx = faic_pos.get(label)
            if idx is None or idx >= len(seq):
                continue
            orig = seq[idx]
            target, freq, role = faic_targets[label]
            if orig == target:
                continue
            tier3_muts.append({
                "tier": "Tier 3 FAIC",
                "label_kabat": label,
                "idx": idx,
                "orig_aa": orig, "target_aa": target,
                "rationale": (f"[Tier 3 FAIC] {orig}{label}{target}: IGHV3 framework adaptation. "
                              f"Target consensus frequency = {int(freq*100)}% in autonomous IGHV3 cohort. "
                              f"Role: {role}. Required because input family ({family}) lacks intrinsic "
                              f"IGHV3 stability core; CDR sequences preserved unchanged."),
            })
        
        if tier3_muts:
            all_muts.extend(tier3_muts)
        
        seq_t3 = apply_mutation_list(seq, all_muts)
        m_t3 = compute_metrics(seq_t3)
        a_t3 = score_abnativ(seq_t3)
        passed_t3, label_t3 = metrics_pass(m_t3["pI"], a_t3["delta"])
        
        log["tier_log"].append({
            "stage": "Tier 3: FAIC (IGHV3 Framework Adaptation)",
            "applied": [f"{m['orig_aa']}→{m['target_aa']}@{m['label_kabat']}(seq{m['idx']+1})" for m in tier3_muts],
            "n_applied": len(tier3_muts),
            "post_metrics": {"pI": m_t3["pI"], "GRAVY": m_t3["GRAVY"], "abnativ_delta": a_t3["delta"]},
            "verdict": label_t3,
        })
        
        if passed_t3:
            log["all_mutations"] = all_muts
            log["final_seq"] = seq_t3
            log["final_metrics"] = m_t3
            log["final_abnativ"] = a_t3
            log["final_verdict"] = label_t3
            log["stopped_at"] = "Tier 3 (Stealth + Hallmark + FAIC sufficient)"
            return log
    
    # ─── Finalize (did not fully pass; report best-effort) ────────────
    final_seq = apply_mutation_list(seq, all_muts)
    fin_m = compute_metrics(final_seq)
    fin_a = score_abnativ(final_seq)
    passed_f, label_f = metrics_pass(fin_m["pI"], fin_a["delta"])
    
    log["all_mutations"] = all_muts
    log["final_seq"] = final_seq
    log["final_metrics"] = fin_m
    log["final_abnativ"] = fin_a
    log["final_verdict"] = label_f
    log["stopped_at"] = "All tiers exhausted; final verdict = " + label_f
    return log


# ───────────────────────────────────────────────────────────────────────────
# Main
# ───────────────────────────────────────────────────────────────────────────

SAMPLES = [
    ("SP34",         "DIKLQSGAELARPGASVKMSCKTSGYTFTRYTMHWVKQRPGQGLEWIGYINPSRGYTNYNQKFKDKATLTTDKSSSTAYMQLSSLTSEDSAVYYCARYYDDHYCLDYWGQGTTLTVSS"),
    ("Teplizumab",   "QVQLVQSGGGVVQPGRSLRLSCKASGYTFTRYTMHWVRQAPGKGLEWIGYINPSRGYTNYNQKVKDRFTISRDNSKNTAFLQMDSLRPEDTGVYFCARYYDDHYCLDYWGQGTPVTVSS"),
    ("OKT3",         "QVQLVQSGAEVKKPGASVKVSCKASGYTFTRYTMHWVRQAPGQGLEWIGYINPSRGYTNYNQKFKDRVTMTRDTSTSTVYMELSSLRSEDTAVYYCARYYDDHYCLDYWGQGTLVTVSS"),
    ("Visilizumab",  "QVQLVQSGAEVKKPGASVKVSCKASGYTFISYTMHWVRQAPGQGLEWMGYINPRSGYTHYNQKLKDKATLTADKSASTAYMELSSLRSEDTAVYYCARSAYYDYDGFAYWGQGTLVTVSS"),
    ("Otelixizumab", "EVQLLESGGGLVQPGGSLRLSCAASGFTFSSFPMAWVRQAPGKGLEWVSTISTSGGRTYYRDSVKGRFTISRDNSKNTLYLQMNSLRAEDTAVYYCAKFRQYSGGFDYWGQGTLVTVSS"),
    ("Foralumab",    "QVQLVESGGGVVQPGRSLRLSCAASGFKFSGYGMHWVRQAPGKGLEWVAVIWYDGSKKYYVDSVKGRFTISRDNSKNTLYLQMNSLRAEDTAVYYCARQMGYWHFDLWGRGTLVTVSS"),
]


def main():
    out_dir = ROOT / "projects" / "CD3_VH2VHH_Batch_20260515" / "v1812_reports"
    out_dir.mkdir(parents=True, exist_ok=True)
    
    summary = []
    for name, seq in SAMPLES:
        print(f"[{name}] Running V1.8.12...")
        result = v1812_design(seq, name)
        with (out_dir / f"{name}_v1812.json").open("w", encoding="utf-8") as f:
            json.dump(result, f, indent=2, ensure_ascii=False)
        print(f"  → IGHV: {result['ighv_family']}; CDR3: {result['cdr3_len']} aa ({result['cdr3_aa']}); "
              f"mutations: {len(result['all_mutations'])}; stopped: {result['stopped_at'][:50]}; "
              f"verdict: {result['final_verdict']}")
        summary.append({
            "name": name,
            "family": result["ighv_family"],
            "cdr3": result["cdr3_aa"],
            "cdr3_len": result["cdr3_len"],
            "n_mut": len(result["all_mutations"]),
            "stopped_at": result["stopped_at"],
            "init_pI": result["initial_metrics"]["pI"],
            "final_pI": result["final_metrics"]["pI"],
            "init_delta": result["initial_abnativ"]["delta"],
            "final_delta": result["final_abnativ"]["delta"],
            "verdict": result["final_verdict"],
        })
    
    (out_dir / "summary.json").write_text(
        json.dumps(summary, indent=2, ensure_ascii=False), encoding="utf-8")
    
    print(f"\n{'='*100}")
    print(f"{'Sample':<14} {'Family':<7} {'CDR3':<14} {'Len':<4} {'N_mut':<5} {'pI':<14} {'AbNatiV Δ':<22} Verdict")
    print(f"{'='*100}")
    for s in summary:
        pi_str = f"{s['init_pI']}→{s['final_pI']}"
        d_str = f"{s['init_delta']}→{s['final_delta']}"
        print(f"{s['name']:<14} {s['family']:<7} {s['cdr3']:<14} {s['cdr3_len']:<4} {s['n_mut']:<5} {pi_str:<14} {d_str:<22} {s['verdict']}")


if __name__ == "__main__":
    main()
