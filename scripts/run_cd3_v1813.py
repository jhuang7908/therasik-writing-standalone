"""
V1.8.13 VH→VHH Conversion
==========================
Key changes from V1.8.12:
  1. Pre-Tier pI prediction: before applying any mutation, predict the pI after all
     planned Stealth + Hallmark mutations to determine pI-correction need.
  2. Dual K→D for pI FAIL (>9.5): two K→D substitutions forced when initial pI > 9.5.
  3. pI correction integrated into Tier 1 (not a separate Phase 4.5 at the end).
  4. Single K→D for pI WARN (9.0–9.5): one K→D added to Tier 1 pool.
  
Architecture: same 3-Tier (Stealth / Hallmark / FAIC) but Tier 1 is now
"Stealth + pI-correction co-design". Stealth threshold remains pI > 9.0 (pre-prediction).
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


# ─── Sequence-pattern helpers (unchanged from V1.8.12) ───────────────────────

def find_canonical_cys2(seq: str) -> Optional[int]:
    """Find the canonical FR3-terminal Cys (before CDR3). Pattern: [any]C[AS][KR]."""
    # Broad pattern: any residue + C + (A|S) + (K|R) in expected range
    m = re.search(r'[A-Z]C[AS][KR]', seq[85:115])
    if m:
        return 85 + m.start() + 1  # index of the C
    # Fallback: any YYC or YFC or YHC before W*G (FR4 start)
    m = re.search(r'[YFW][YFC]C', seq[80:112])
    if m:
        return 80 + m.start() + 2
    return None


def find_cdr3(seq: str) -> Tuple[Optional[int], Optional[int], str]:
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
    out = {"K44": None, "K45": None, "K47": None}
    m = re.search(r'[GA][LRA][EQ][WLY]', seq[35:55])
    if m:
        base = 35 + m.start()
        out["K44"] = base
        out["K45"] = base + 1
        out["K47"] = base + 3
    return out


def find_stealth_positions(seq: str) -> Dict[str, Optional[int]]:
    out = {
        "K13": 12 if len(seq) > 12 else None,
        "K19": 18 if len(seq) > 18 else None,
    }
    cys = find_canonical_cys2(seq)
    if cys:
        out["K94"] = cys + 1 if cys + 1 < len(seq) else None
        out["K83"] = cys - 11 if cys >= 11 else None
        out["K74"] = cys - 20 if cys >= 20 else None
        out["K72"] = cys - 22 if cys >= 22 else None
    return out


def find_faic_positions(seq: str) -> Dict[str, Optional[int]]:
    out = {"K18": 17 if len(seq) > 17 else None}
    cys = find_canonical_cys2(seq)
    if cys:
        out["K89"] = cys - 5
        out["K77"] = cys - 17
        out["K68"] = cys - 26
    return out


def detect_ighv_family(seq: str) -> Tuple[str, str]:
    head = seq[:25]
    if re.match(r'.VQLVQSGAEVKKPG', head) or re.match(r'.IKLQSGAELARPG', head):
        return "IGHV1", "KKPGAS / ARPGAS motif"
    if re.search(r'.SGGG[LV]VQ', head) or re.search(r'.ESGGG[LV]', head):
        return "IGHV3", "SGGG[L/V]VQ canonical IGHV3 motif"
    return "IGHV_unknown", "no canonical N-terminal motif"


def compute_metrics(seq: str) -> Dict:
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
        "net_basic": seq.count("K") + seq.count("R") - seq.count("D") - seq.count("E"),
    }


def score_abnativ(seq: str) -> Dict:
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


def label_pi(pI: float) -> str:
    return "PASS" if pI <= 9.0 else ("WARN" if pI <= 9.5 else "FAIL")


def label_abnativ(d: Optional[float]) -> str:
    if d is None:    return "UNKNOWN"
    if d >= 0:       return "EXCELLENT"
    if d >= -0.12:   return "PASS"
    if d >= -0.20:   return "WARN"
    return "FAIL"


def metrics_pass(pI: float, d: Optional[float]) -> Tuple[bool, str]:
    pi_l = label_pi(pI)
    an_l = label_abnativ(d)
    return (pi_l == "PASS" and an_l in ("PASS", "EXCELLENT")), f"pI={pi_l}, AbNatiV={an_l}"


def apply_mutation_list(seq: str, mutations: List[Dict]) -> str:
    arr = list(seq)
    for m in mutations:
        i = m["idx"]
        if 0 <= i < len(arr):
            arr[i] = m["target_aa"]
    return "".join(arr)


# ─── V1.8.13 pI pre-prediction ────────────────────────────────────────────────

def predict_post_engineering_pi(seq: str, hallmark_pos: Dict, stealth_pos: Dict,
                                  stealth_scan: List[str]) -> float:
    """
    Predict pI after applying all planned Stealth mutations + full Hallmark package.
    Used to determine upfront how many K→D pI-corrections are needed.
    """
    arr = list(seq)
    # Apply all planned Stealth K→target (K-gated)
    stealth_targets = {"K94": "R", "K74": "T", "K83": "Q", "K13": "Q", "K19": "Q", "K72": "D"}
    for label in stealth_scan:
        idx = stealth_pos.get(label)
        if idx is not None and idx < len(arr) and arr[idx] == "K":
            arr[idx] = stealth_targets.get(label, "Q")

    # Apply full Hallmark package (K45R + G44E + W47G)
    for label, target in [("K45", "R"), ("K44", "E"), ("K47", "G")]:
        idx = hallmark_pos.get(label)
        if idx is not None and idx < len(arr):
            orig = arr[idx]
            if label == "K45" and orig in ("R", "A"):
                continue
            if orig != target:
                arr[idx] = target

    predicted_seq = "".join(arr)
    return round(ProteinAnalysis(predicted_seq).isoelectric_point(), 2)


def build_pi_corrections(seq: str, stealth_pos: Dict, n_corrections: int,
                          cdr3_start: Optional[int], cdr3_end: Optional[int],
                          hallmark_pos: Optional[Dict] = None) -> List[Dict]:
    """
    V1.8.13: Build pI-correction K→D mutations.
    Priority list: canonical Stealth positions first; then full-FR scan as fallback.
    n_corrections: 1 for WARN, 2 for FAIL.
    """
    grade = 'FAIL→PASS' if n_corrections == 2 else 'WARN→PASS'
    # Primary priority list (canonical Stealth positions)
    pi_correction_priority = [
        ("K72", "D", "K72D: dual-action (Stealth + pI): removes +K, adds −D; net −2 charge; "
                     "IGHV3-23 germline tolerance confirmed; primary pI correction target."),
        ("K74", "D", "K74D: secondary pI correction; −2 net charge vs −1 for K74T."),
        ("K83", "D", "K83D: FR3-late surface pI correction."),
        ("K94", "D", "K94D: CDR3-base; D tolerated when pI correction required."),
        ("K13", "D", "K13D: FR1 surface pI correction fallback."),
        ("K19", "D", "K19D: FR1 pI correction fallback."),
    ]
    used_indices: set = set()
    out: List[Dict] = []

    for label, target, rationale in pi_correction_priority:
        if len(out) >= n_corrections:
            break
        idx = stealth_pos.get(label)
        if idx is None or idx >= len(seq) or idx in used_indices:
            continue
        orig = seq[idx]
        if orig != "K":
            continue
        out.append({
            "tier": "Tier 1 pI-Correction",
            "label_kabat": label,
            "idx": idx, "orig_aa": orig, "target_aa": target,
            "rationale": f"[V1.8.13 pI-Correction, {grade}] {orig}{label}{target}: {rationale}",
        })
        used_indices.add(idx)

    # Fallback: scan ALL K in FR1/FR2/FR3 (exclude CDR3 + Hallmark zone) if shortage
    if len(out) < n_corrections:
        hallmark_indices = set(v for v in (hallmark_pos or {}).values() if v is not None)
        cdr3_range = set(range(cdr3_start, cdr3_end)) if (cdr3_start and cdr3_end) else set()
        for i, aa in enumerate(seq):
            if len(out) >= n_corrections:
                break
            if aa != "K" or i in used_indices or i in hallmark_indices or i in cdr3_range:
                continue
            if i > 110:  # avoid FR4
                continue
            label_fb = f"K_FR_{i+1}"
            out.append({
                "tier": "Tier 1 pI-Correction (fallback scan)",
                "label_kabat": label_fb,
                "idx": i, "orig_aa": aa, "target_aa": "D",
                "rationale": (f"[V1.8.13 pI-Correction fallback, {grade}] K→D at pos{i+1}: "
                              f"FR surface K; no canonical Stealth position available at this slot; "
                              f"D preferred for maximum pI reduction (−2 net charge)."),
            })
            used_indices.add(i)

    return out


# ─── V1.8.13 Main Design Function ─────────────────────────────────────────────

def v1813_design(seq: str, sample_name: str) -> Dict:
    family, fam_evidence = detect_ighv_family(seq)
    cdr3_start, cdr3_end, cdr3_aa = find_cdr3(seq)
    cdr3_len = len(cdr3_aa) if cdr3_aa else 0
    hallmark_pos = find_hallmark_positions(seq)
    stealth_pos = find_stealth_positions(seq)
    faic_pos = find_faic_positions(seq)

    init_metrics = compute_metrics(seq)
    init_abnativ = score_abnativ(seq)

    # Detect unpaired Cys in CDR3
    cdr3_cys_idx = []
    if cdr3_aa:
        n_cys = cdr3_aa.count("C")
        if n_cys == 1 or (n_cys == 2 and cdr3_len < 16):
            for i, aa in enumerate(cdr3_aa):
                if aa == "C":
                    cdr3_cys_idx.append(cdr3_start + i)

    # Tier 1 Stealth depth (CDR3-length scaled)
    if cdr3_len < 10:
        depth = "LIGHT (CDR3<10 aa)"
        stealth_scan = ["K13", "K19"]
    elif cdr3_len < 15:
        depth = "STANDARD (CDR3 10-14 aa)"
        stealth_scan = ["K13", "K19", "K74", "K83", "K94"]
    elif cdr3_len < 18:
        depth = "DEEP (CDR3 15-17 aa)"
        stealth_scan = ["K13", "K19", "K72", "K74", "K83", "K94"]
    else:
        depth = "STRICT-DEEP (CDR3 ≥18 aa)"
        stealth_scan = ["K13", "K19", "K72", "K74", "K83", "K94"]

    # ─────────────────────────────────────────────────────────────
    # [V1.8.13 NEW] Pre-Tier pI prediction
    # ─────────────────────────────────────────────────────────────
    predicted_pi = predict_post_engineering_pi(seq, hallmark_pos, stealth_pos, stealth_scan)
    pi_correction_muts: List[Dict] = []
    pi_correction_note = ""

    if predicted_pi > 9.5:
        pi_correction_muts = build_pi_corrections(
            seq, stealth_pos, n_corrections=2, cdr3_start=cdr3_start, cdr3_end=cdr3_end,
            hallmark_pos=hallmark_pos)
        pi_correction_note = (f"pI FAIL path: predicted pI after full engineering = {predicted_pi} > 9.5. "
                              f"Forcing 2× K→D to ensure final pI ≤ 9.0.")
    elif predicted_pi > 9.0:
        pi_correction_muts = build_pi_corrections(
            seq, stealth_pos, n_corrections=1, cdr3_start=cdr3_start, cdr3_end=cdr3_end,
            hallmark_pos=hallmark_pos)
        pi_correction_note = (f"pI WARN path: predicted pI after full engineering = {predicted_pi} ∈ (9.0, 9.5]. "
                              f"Adding 1× K→D preemptively to buffer against Hallmark K45R (+0.1–0.2 pI).")
    else:
        pi_correction_note = f"pI PASS path: predicted pI after full engineering = {predicted_pi} ≤ 9.0. No pI correction needed."

    log = {
        "sample": sample_name,
        "algorithm_version": "V1.8.13",
        "input_seq": seq,
        "ighv_family": family,
        "ighv_evidence": fam_evidence,
        "cdr3_aa": cdr3_aa,
        "cdr3_len": cdr3_len,
        "cdr3_start_idx": cdr3_start,
        "cdr3_end_idx": cdr3_end,
        "unpaired_cys_cdr3": cdr3_cys_idx,
        "initial_metrics": init_metrics,
        "initial_abnativ": init_abnativ,
        "v1813_pi_prediction": {
            "predicted_pi_post_engineering": predicted_pi,
            "pi_correction_path": "FAIL (2×K→D)" if predicted_pi > 9.5 else ("WARN (1×K→D)" if predicted_pi > 9.0 else "PASS (no correction)"),
            "note": pi_correction_note,
            "n_corrections_planned": len(pi_correction_muts),
        },
        "tier_log": [],
        "all_mutations": [],
    }

    all_muts: List[Dict] = []

    # ─── Pre-Tier: Cys-gate ───────────────────────────────────────
    for idx in cdr3_cys_idx:
        rel = idx - cdr3_start + 1
        all_muts.append({
            "tier": "Cys-gate",
            "label_kabat": f"Cys-CDR3-{rel}",
            "idx": idx, "orig_aa": seq[idx], "target_aa": "S",
            "rationale": (f"MANDATORY Cys-gate: unpaired CDR3 Cys at position {idx+1} "
                          f"(CDR3 residue {rel}/{cdr3_len}) causes misfolding/ER retention "
                          f"in single-domain context. C→S preserves H-bonding, eliminates "
                          f"disulfide misformation risk."),
        })
    if cdr3_cys_idx:
        log["tier_log"].append({
            "stage": "Pre-Tier: Cys-gate (MANDATORY)",
            "applied": [f"C→S@pos{m['idx']+1}" for m in all_muts],
        })

    # ─── Tier 1: Stealth + pI-Correction (co-design) ─────────────
    # [V1.8.13] pI corrections are inserted into Tier 1 pool FIRST,
    # before classic Stealth, so they are always applied regardless
    # of whether the position also appears in Stealth scan.
    
    # Stealth target map
    stealth_targets = {
        "K94": ("R",  "K94R: 53% of autonomous IGHV3 cohort (n=36); primary CDR3-base Stealth target."),
        "K74": ("T",  "K74T: 84% IGHV3-23 germline canonical; removes surface K."),
        "K83": ("Q",  "K83Q: FR3-late surface K reduction; Q neutral."),
        "K13": ("Q",  "K13Q: FR1 surface K reduction; consensus in autonomous VH cohort."),
        "K19": ("Q",  "K19Q: FR1 mid surface K reduction."),
        "K72": ("D",  "K72D: dual Stealth+pI (K→D: −2 net charge); primary pI-tune position."),
    }

    tier1_muts: List[Dict] = []

    # First: add pI-correction mutations (may overlap with Stealth positions)
    pi_corr_positions = {m["idx"] for m in pi_correction_muts}
    tier1_muts.extend(pi_correction_muts)

    # Then: Stealth scan (skip positions already covered by pI correction)
    for label in stealth_scan:
        idx = stealth_pos.get(label)
        if idx is None or idx >= len(seq):
            continue
        if idx in pi_corr_positions:
            continue  # already handled by pI correction (may use K→D instead of K→T etc.)
        orig = seq[idx]
        if orig != "K":
            continue
        target, rationale = stealth_targets.get(label, ("Q", "K→Q surface reduction"))
        tier1_muts.append({
            "tier": "Tier 1 Stealth",
            "label_kabat": label,
            "idx": idx, "orig_aa": orig, "target_aa": target,
            "rationale": f"[Tier 1 Stealth, {depth.split()[0]}] {orig}{label}{target}: {rationale}",
        })

    all_muts.extend(tier1_muts)
    seq_t1 = apply_mutation_list(seq, all_muts)
    m_t1 = compute_metrics(seq_t1)
    a_t1 = score_abnativ(seq_t1)
    passed_t1, lbl_t1 = metrics_pass(m_t1["pI"], a_t1["delta"])

    log["tier_log"].append({
        "stage": "Tier 1: Stealth + pI-Correction (co-design)",
        "depth": depth,
        "pi_correction_included": len(pi_correction_muts),
        "stealth_included": len(tier1_muts) - len(pi_correction_muts),
        "applied": [f"{m['orig_aa']}→{m['target_aa']}@{m['label_kabat']}(seq{m['idx']+1})"
                    for m in tier1_muts],
        "post_metrics": {"pI": m_t1["pI"], "GRAVY": m_t1["GRAVY"], "abnativ_delta": a_t1["delta"]},
        "verdict": lbl_t1,
        "escalate": not passed_t1,
    })

    if passed_t1:
        log["all_mutations"] = all_muts
        log["final_seq"] = seq_t1
        log["final_metrics"] = m_t1
        log["final_abnativ"] = a_t1
        log["final_verdict"] = lbl_t1
        log["stopped_at"] = "Tier 1"
        return log

    # ─── Tier 2: Hallmark Package (CDR3-length gated) ─────────────
    skip_hallmark = (cdr3_len >= 18)
    if skip_hallmark:
        log["tier_log"].append({
            "stage": "Tier 2: Hallmark",
            "skipped": True,
            "reason": f"CDR3 = {cdr3_len} aa ≥ 18: natural CDR3 drape covers VL interface (100% of long-CDR3 autonomous VH cohort retain GLW without Hallmark).",
        })
    else:
        tier2_muts: List[Dict] = []
        hallmark_rationales = {
            "K45": (lambda o: f"L45R Hallmark CORE: replaces hydrophobic {o} (VL contact) with R; "
                              f"CDR3 = {cdr3_len} aa lacks VL-drape coverage."),
            "K44": (lambda o: f"G44E Hallmark RESCUE: negative charge at VL interface masks hydrophobic exposure; "
                              f"11% of autonomous VH cohort show G44E naturally."),
            "K47": (lambda o: f"W47G Hallmark RESCUE: removes bulky W (deep VL pocket); "
                              f"17% of autonomous IGHV3 cohort have non-W at k47."),
        }
        for label, target, _ in [("K45","R","L"), ("K44","E","G"), ("K47","G","W")]:
            idx = hallmark_pos.get(label)
            if idx is None or idx >= len(seq):
                continue
            orig = seq[idx]
            if orig == target:
                continue
            if label == "K45" and orig in ("R", "A"):
                continue
            tier2_muts.append({
                "tier": "Tier 2 Hallmark",
                "label_kabat": label,
                "idx": idx, "orig_aa": orig, "target_aa": target,
                "rationale": f"[Tier 2 Hallmark] {orig}{label}{target}: {hallmark_rationales[label](orig)}",
            })

        all_muts.extend(tier2_muts)
        seq_t2 = apply_mutation_list(seq, all_muts)
        m_t2 = compute_metrics(seq_t2)
        a_t2 = score_abnativ(seq_t2)
        passed_t2, lbl_t2 = metrics_pass(m_t2["pI"], a_t2["delta"])

        log["tier_log"].append({
            "stage": "Tier 2: Hallmark Package",
            "applied": [f"{m['orig_aa']}→{m['target_aa']}@{m['label_kabat']}(seq{m['idx']+1})"
                        for m in tier2_muts],
            "post_metrics": {"pI": m_t2["pI"], "GRAVY": m_t2["GRAVY"], "abnativ_delta": a_t2["delta"]},
            "verdict": lbl_t2,
            "escalate": not passed_t2,
        })

        if passed_t2:
            log["all_mutations"] = all_muts
            log["final_seq"] = seq_t2
            log["final_metrics"] = m_t2
            log["final_abnativ"] = a_t2
            log["final_verdict"] = lbl_t2
            log["stopped_at"] = "Tier 2"
            return log

    # ─── Tier 3: FAIC (only for non-IGHV3) ────────────────────────
    if family == "IGHV3":
        log["tier_log"].append({
            "stage": "Tier 3: FAIC",
            "skipped": True,
            "reason": f"Input is {family} — already IGHV3 native framework. FAIC not required.",
        })
    else:
        faic_targets = {
            "K68": ("T", 1.00, "Internal stability core (100% IGHV3 autonomous cohort)"),
            "K89": ("V", 0.81, "FR3 VL-interface lower edge (81% V in IGHV3 cohort)"),
            "K18": ("L", 0.97, "FR1 internal hydrophobic core (97% L in IGHV3 cohort)"),
            "K77": ("T", 0.85, "FR3 surface stabilisation (IGHV3-23 germline)"),
        }
        tier3_muts: List[Dict] = []
        for label, (target, freq, role) in faic_targets.items():
            idx = faic_pos.get(label)
            if idx is None or idx >= len(seq):
                continue
            orig = seq[idx]
            if orig == target:
                continue
            tier3_muts.append({
                "tier": "Tier 3 FAIC",
                "label_kabat": label,
                "idx": idx, "orig_aa": orig, "target_aa": target,
                "rationale": (f"[Tier 3 FAIC] {orig}{label}{target}: IGHV3 framework adaptation "
                              f"({int(freq*100)}% IGHV3 cohort). Role: {role}. "
                              f"Input {family} lacks this stability element; CDR unchanged."),
            })

        all_muts.extend(tier3_muts)
        seq_t3 = apply_mutation_list(seq, all_muts)
        m_t3 = compute_metrics(seq_t3)
        a_t3 = score_abnativ(seq_t3)
        passed_t3, lbl_t3 = metrics_pass(m_t3["pI"], a_t3["delta"])

        log["tier_log"].append({
            "stage": "Tier 3: FAIC",
            "applied": [f"{m['orig_aa']}→{m['target_aa']}@{m['label_kabat']}(seq{m['idx']+1})"
                        for m in tier3_muts],
            "post_metrics": {"pI": m_t3["pI"], "GRAVY": m_t3["GRAVY"], "abnativ_delta": a_t3["delta"]},
            "verdict": lbl_t3,
        })

        if passed_t3:
            log["all_mutations"] = all_muts
            log["final_seq"] = seq_t3
            log["final_metrics"] = m_t3
            log["final_abnativ"] = a_t3
            log["final_verdict"] = lbl_t3
            log["stopped_at"] = "Tier 3"
            return log

    # ─── Finalize ─────────────────────────────────────────────────
    final_seq = apply_mutation_list(seq, all_muts)
    fin_m = compute_metrics(final_seq)
    fin_a = score_abnativ(final_seq)
    _, lbl_f = metrics_pass(fin_m["pI"], fin_a["delta"])

    log["all_mutations"] = all_muts
    log["final_seq"] = final_seq
    log["final_metrics"] = fin_m
    log["final_abnativ"] = fin_a
    log["final_verdict"] = lbl_f
    log["stopped_at"] = f"All tiers exhausted; verdict = {lbl_f}"
    return log


# ─── Batch Samples ────────────────────────────────────────────────────────────

SAMPLES = [
    ("SP34",         "DIKLQSGAELARPGASVKMSCKTSGYTFTRYTMHWVKQRPGQGLEWIGYINPSRGYTNYNQKFKDKATLTTDKSSSTAYMQLSSLTSEDSAVYYCARYYDDHYCLDYWGQGTTLTVSS"),
    ("Teplizumab",   "QVQLVQSGGGVVQPGRSLRLSCKASGYTFTRYTMHWVRQAPGKGLEWIGYINPSRGYTNYNQKVKDRFTISRDNSKNTAFLQMDSLRPEDTGVYFCARYYDDHYCLDYWGQGTPVTVSS"),
    ("OKT3",         "QVQLVQSGAEVKKPGASVKVSCKASGYTFTRYTMHWVRQAPGQGLEWIGYINPSRGYTNYNQKFKDRVTMTRDTSTSTVYMELSSLRSEDTAVYYCARYYDDHYCLDYWGQGTLVTVSS"),
    ("Visilizumab",  "QVQLVQSGAEVKKPGASVKVSCKASGYTFISYTMHWVRQAPGQGLEWMGYINPRSGYTHYNQKLKDKATLTADKSASTAYMELSSLRSEDTAVYYCARSAYYDYDGFAYWGQGTLVTVSS"),
    ("Otelixizumab", "EVQLLESGGGLVQPGGSLRLSCAASGFTFSSFPMAWVRQAPGKGLEWVSTISTSGGRTYYRDSVKGRFTISRDNSKNTLYLQMNSLRAEDTAVYYCAKFRQYSGGFDYWGQGTLVTVSS"),
    ("Foralumab",    "QVQLVESGGGVVQPGRSLRLSCAASGFKFSGYGMHWVRQAPGKGLEWVAVIWYDGSKKYYVDSVKGRFTISRDNSKNTLYLQMNSLRAEDTAVYYCARQMGYWHFDLWGRGTLVTVSS"),
]


def main():
    out_dir = ROOT / "projects" / "CD3_VH2VHH_Batch_20260515" / "v1813_reports"
    out_dir.mkdir(parents=True, exist_ok=True)

    summary = []
    for name, seq in SAMPLES:
        print(f"[{name}] Running V1.8.13...")
        result = v1813_design(seq, name)
        with (out_dir / f"{name}_v1813.json").open("w", encoding="utf-8") as f:
            json.dump(result, f, indent=2, ensure_ascii=False)

        pi_pred = result["v1813_pi_prediction"]
        print(f"  IGHV: {result['ighv_family']}  CDR3: {result['cdr3_len']} aa  "
              f"predicted_pI: {pi_pred['predicted_pi_post_engineering']} ({pi_pred['pi_correction_path']})")
        print(f"  mutations: {len(result['all_mutations'])}  stopped: {result['stopped_at'][:55]}")
        print(f"  pI: {result['initial_metrics']['pI']} → {result['final_metrics']['pI']}  "
              f"AbNatiV Δ: {result['initial_abnativ']['delta']} → {result['final_abnativ']['delta']}  "
              f"verdict: {result['final_verdict']}")

        summary.append({
            "name": name,
            "family": result["ighv_family"],
            "cdr3": result["cdr3_aa"],
            "cdr3_len": result["cdr3_len"],
            "predicted_pi": pi_pred["predicted_pi_post_engineering"],
            "pi_correction_path": pi_pred["pi_correction_path"],
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

    print(f"\n{'='*110}")
    print(f"{'Sample':<14} {'Family':<7} {'CDR3 len':<9} {'pI predict':<12} {'N_mut':<6} "
          f"{'pI init→final':<16} {'AbNatiV Δ init→final':<24} Verdict")
    print("=" * 110)
    for s in summary:
        print(f"{s['name']:<14} {s['family']:<7} {s['cdr3_len']:<9} "
              f"{s['predicted_pi']:<12} {s['n_mut']:<6} "
              f"{s['init_pI']}→{s['final_pI']:<11} "
              f"{s['init_delta']}→{s['final_delta']:<17} {s['verdict']}")


if __name__ == "__main__":
    main()
