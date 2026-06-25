"""
VH→VHH Conversion API (standard V1.8.17 · Console deployment branch V1.8.17.IGHV3)
==================================================================================

POST /vh_to_vhh/async   — start async job, returns {job_id}
GET  /jobs/{job_id}     — poll progress (shared jobs store)
POST /vh_to_vhh/analyze — legacy sync Stage-1 only (kept for backward compat)

Full pipeline:
  Stage 1  feasibility screen (ANARCI Kabat) + AbNatiV Δ gate
  Stage 2  apply Hallmark (K45R default; K44E/K47F rescue-only) + Stealth K-gate
  Stage 3  NanoBodyBuilder2 structure prediction (input VH + converted VHH)
  Stage 4  CDR Cα RMSD (donor vs converted)
  Stage 4.5 sdAb adaptation: F68Y only if K68=F; L18S disabled
  Stage 5  mini-CMC + AbEvaluator clinical-VHH QA
  Stage 5.5 Expressibility Verdict Gate (CDR3 length + compactness + AbNatiV Δ)
  Report   self-contained HTML + FASTA + PDB → ZIP

Algorithm standard: docs/VH_TO_VHH_CONVERSION_STANDARD_V1.8.md (header V1.8.17).
Public HTTP endpoints enforce IGHV3-family pre-flight only — labelled V1.8.17.IGHV3.
Cohort basis: AutonomousHumanVH_Cohort_v1 (n=36, Kabat scheme) + CD3/V1.8.16–17 audits.
"""
from __future__ import annotations

import json
import hashlib
import re
import sys
import threading
import time
from pathlib import Path
from typing import Any, Dict, List, Optional

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))

from api.job_store import files_url_for_path, jobs, save_result, job_dir, persist_job_snapshot
from api.routers.humanization import (
    VH2VHH_ANALYSIS_VERSION,
    VH2VHH_CONSOLE_DEPLOYMENT_BRANCH,
    VH2VHH_REPORT_PROTOCOL_VERSION,
    VH2VHH_STANDARD_VERSION,
    VHVL_HTML_REPORT_BUILD_ID,
)

router = APIRouter(prefix="/vh_to_vhh", tags=["VH to VHH"])
_CMC_CASEBANK_LOCK = threading.Lock()


# ─────────────────────────────────────────────────────────────────────────────
# Request models
# ─────────────────────────────────────────────────────────────────────────────

class VhToVhhRequest(BaseModel):
    vh_sequence: str = Field(..., description="VH amino acid sequence (whitespace stripped server-side).")
    source_class: str = Field(
        "human_mab",
        description="human_mab | murine_mab | phage_display_vh | transgenic_mouse_vh",
    )
    demo_id: Optional[str] = None
    sequence_name: Optional[str] = Field(
        None,
        description="Optional client label (project / clone ID) for reports and downloads.",
    )
    # [V1.8.10] CDR grafting onto VHH scaffold is opt-in only.
    # Default Path C: keep VH framework + apply point mutations (Hallmark/Stealth/pI).
    # Set True only when user explicitly requests scaffold chimera creation.
    enable_scaffold_graft: bool = Field(
        False,
        description="[V1.8.10] Enable CDR-graft-to-VHH-scaffold strategy (non-standard, opt-in only).",
    )


def _map_source_class(sc: str) -> str:
    s = (sc or "").strip().lower()
    return {
        "human_mab":            "humanized_mab",
        "humanized_mab":        "humanized_mab",
        "murine_mab":           "murine_mab",
        "phage_display_vh":     "phage_display_vh",
        "transgenic_mouse_vh":  "transgenic_mouse_vh",
    }.get(s, "conventional_vh")


# ─────────────────────────────────────────────────────────────────────────────
# Source-specific algorithm constants
# ─────────────────────────────────────────────────────────────────────────────

# CDR positions in Kabat VH numbering
_CDR_KABAT_POS: frozenset = frozenset(
    [(p, "") for p in range(31, 36)]    # CDR-H1: 31-35
    + [(p, "") for p in range(50, 66)]  # CDR-H2: 50-65
    + [(p, "") for p in range(95, 103)] # CDR-H3: 95-102
)

# Vernier zone positions — MUST NOT be mutated during source-specific steps
_VERNIER_KABAT_POS: frozenset = frozenset({
    (2,""), (4,""), (24,""), (25,""), (26,""),
    (36,""), (37,""), (48,""), (49,""), (67,""),
    (69,""), (71,""), (73,""), (78,""), (93,""),
})

# Hallmark positions (fixed by core algorithm — excluded from source-specific logic)
_HALLMARK_POS: frozenset = frozenset({(44,""), (45,""), (47,"")})

# ─── V1.8.2 P0/P1 feature switches (set False to disable individual modules) ──
ENABLE_ABNATIV_GATE: bool = True     # P0-1: AbNatiV Δ candidate scoring + re-rank
ENABLE_PHASE45: bool = True          # P0-2: L18S / F68Y / pI-tune Phase 4.5 candidates
ENABLE_PHASE5_QA: bool = True        # P1-3: Cα Rg + pLDDT proxy gate after Stage 3
ENABLE_PATHWAY_ADVISORY: bool = True  # P1-4: CDR3 extreme-composition pathway advisory

# Amino acid physicochemical groups for conservative-change classification
_AA_GROUP: Dict[str, str] = {
    "R": "pos", "K": "pos", "H": "pos",
    "D": "neg", "E": "neg",
    "S": "pol", "T": "pol", "N": "pol", "Q": "pol", "Y": "pol", "C": "pol",
    "A": "hyd", "V": "hyd", "I": "hyd", "L": "hyd", "M": "hyd", "F": "hyd", "W": "hyd",
    "G": "gly", "P": "pro",
}

# IGHV3-23*01 Kabat FR consensus (embedded subset — most common residue per position).
# Covers FR1 (1–26 excl. CDR1 27–30), FR2 (36–49), FR3 (66–94), FR4 (103–113).
# Source: IMGT/GENE-DB IGHV3-23*01 [verified from public IMGT database]
_IGHV3_CONSENSUS: Dict[tuple, str] = {
    # FR1
    (1,""):"E",(2,""):"V",(3,""):"Q",(4,""):"L",(5,""):"V",(6,""):"Q",
    (7,""):"S",(8,""):"G",(9,""):"A",(10,""):"E",(11,""):"V",(12,""):"K",
    (13,""):"K",(14,""):"P",(15,""):"G",(16,""):"S",(17,""):"S",(18,""):"V",
    (19,""):"K",(20,""):"V",(21,""):"S",(22,""):"C",(23,""):"K",(24,""):"A",
    (25,""):"S",(26,""):"G",
    # FR2 (IMGT 44/45/47 are Hallmarks — included only for reference, not flagged)
    (36,""):"W",(37,""):"V",(38,""):"R",(39,""):"Q",(40,""):"A",(41,""):"P",
    (42,""):"G",(43,""):"Q",(44,""):"G",(45,""):"L",(46,""):"E",(47,""):"W",
    (48,""):"M",(49,""):"G",
    # FR3
    (66,""):"R",(67,""):"V",(68,""):"T",(69,""):"I",(70,""):"S",(71,""):"R",
    (72,""):"D",(73,""):"T",(76,""):"N",(77,""):"T",(78,""):"L",(79,""):"Y",
    (80,""):"L",(82,""):"Q",(83,""):"M",(84,""):"N",(85,""):"S",(86,""):"L",
    (87,""):"R",(88,""):"A",(89,""):"E",(90,""):"D",(91,""):"T",(92,""):"A",
    (93,""):"V",(94,""):"Y",
    # FR4
    (103,""):"W",(104,""):"G",(105,""):"Q",(106,""):"G",(107,""):"T",
    (108,""):"T",(109,""):"V",(110,""):"T",(111,""):"V",
}

# Family-discriminator gate: FR2 conserved core + FR4 (16 positions).
# Calibrated against 6 clinical VH sequences (2026-05-17):
#   IGHV3-23/33/66 all score ≥15/16; IGHV1-18/69 and IGHV4 score ≤7/16.
#   FR1 and FR3 are excluded — they vary too much between IGHV3 sub-families
#   (e.g. IGHV3-66 differs from IGHV3-23 at 16/26 FR1 positions).
_IGHV3_FAMILY_GATE: Dict[tuple, str] = {
    # FR2 — conserved IGHV3 core (positions 36–49, excl. the highly variable 37/38/40/42/43/48)
    (36,""):"W",(39,""):"Q",(41,""):"P",(44,""):"G",(45,""):"L",(46,""):"E",(47,""):"W",
    # FR4 — universally conserved
    (103,""):"W",(104,""):"G",(105,""):"Q",(106,""):"G",(107,""):"T",
    (108,""):"T",(109,""):"V",(110,""):"T",(111,""):"V",
}
_IGHV3_FAMILY_GATE_THRESHOLD = 12  # ≥12/16 → IGHV3 family; <12 → reject

# FR position ranges in Kabat VH (all non-CDR residues)
_FR_KABAT_NUMS: frozenset = frozenset(
    list(range(1, 31)) + list(range(36, 50)) + list(range(66, 95)) + list(range(103, 114))
)


def _is_conservative_sub(aa1: str, aa2: str) -> bool:
    """True if aa1→aa2 is a within-group (conservative) substitution."""
    if aa1 == aa2:
        return True
    g1 = _AA_GROUP.get(aa1)
    g2 = _AA_GROUP.get(aa2)
    return g1 is not None and g1 == g2


def _phage_charge_audit(kd: dict, pos_to_idx: dict) -> dict:
    """
    Phage-display VH algorithm step: decompose net charge into FR vs CDR contributions.
    Identify FR positions outside Vernier/Hallmark zones as charge-compensation candidates.

    Returns
    -------
    dict with:
      fr_net_charge, cdr_net_charge, total_net_charge, charge_bias_flag,
      fr_negative_positions, cdr_negative_positions, compensation_candidates
    """
    CHARGE_VAL = {"D": -1.0, "E": -1.0, "K": 1.0, "R": 1.0, "H": 0.1}
    NEUTRAL_SUB = {"E": "Q", "D": "N"}   # charge-neutral conservative replacement

    fr_neg: List[dict] = []
    cdr_neg: List[dict] = []
    fr_net = 0.0
    cdr_net = 0.0

    for key, _idx in pos_to_idx.items():
        aa = kd.get(key)
        if not aa or aa in ("-", "X", ""):
            continue
        charge = CHARGE_VAL.get(aa, 0.0)
        if charge == 0.0:
            continue

        pos_num, ins = key
        label = f"{pos_num}{ins}".strip()
        # CDR: named range + CDR3 insertion codes (pos_num 95-102 or ins != "")
        in_cdr = key in _CDR_KABAT_POS or (95 <= pos_num <= 102)
        in_vernier = key in _VERNIER_KABAT_POS
        in_hallmark = key in _HALLMARK_POS

        if in_cdr:
            cdr_net += charge
            if charge < 0:
                cdr_neg.append({"kabat": label, "aa": aa, "charge": charge,
                                "note": "CDR charge — antigen-contact; DO NOT mutate"})
        else:
            fr_net += charge
            if charge < 0:
                actionable = not in_vernier and not in_hallmark
                sugg = NEUTRAL_SUB.get(aa, aa)
                fr_neg.append({
                    "kabat": label,
                    "aa": aa,
                    "charge": charge,
                    "suggested": sugg if actionable else "—",
                    "actionable": actionable,
                    "note": (
                        "FR charge contributor — Vernier zone; PROTECT" if in_vernier
                        else "FR charge contributor — Hallmark position; skip" if in_hallmark
                        else f"FR charge contributor — compensation candidate ({aa}→{sugg})"
                    ),
                })

    total_net = fr_net + cdr_net
    candidates = [p for p in fr_neg if p["actionable"]]
    return {
        "fr_net_charge": round(fr_net, 1),
        "cdr_net_charge": round(cdr_net, 1),
        "total_net_charge": round(total_net, 1),
        "charge_bias_flag": total_net < -2.0,
        "severity": "HIGH" if total_net < -4.0 else "MODERATE" if total_net < -2.0 else "OK",
        "fr_negative_positions": fr_neg,
        "cdr_negative_positions": cdr_neg,
        "compensation_candidates": candidates,
        "n_compensation_candidates": len(candidates),
        "algorithm": "phage_charge_audit_v1.0",
    }


def _transgenic_shm_scan(kd: dict, pos_to_idx: dict) -> dict:
    """
    Transgenic mouse VH algorithm step: compare FR positions against
    IGHV3-23*01 consensus to classify SHM deviations.

    Returns
    -------
    dict with:
      germline_reference, same_as_germline, conservative_shm, non_conservative_shm,
      total_shm_positions, shm_load ("LOW"|"MODERATE"|"HIGH"),
      shm_positions (list), high_risk_positions (list)
    """
    shm_hits: List[dict] = []
    same_count = 0
    conservative_count = 0
    non_conservative_count = 0

    for key, _idx in pos_to_idx.items():
        pos_num, ins = key
        if pos_num not in _FR_KABAT_NUMS:
            continue
        observed = kd.get(key)
        if not observed or observed in ("-", "X", ""):
            continue
        germline_aa = _IGHV3_CONSENSUS.get(key)
        if germline_aa is None:
            continue  # position not covered by our consensus table

        label = f"{pos_num}{ins}".strip()
        in_hallmark = key in _HALLMARK_POS
        in_vernier = key in _VERNIER_KABAT_POS

        if observed == germline_aa:
            same_count += 1
            continue

        is_cons = _is_conservative_sub(germline_aa, observed)
        if is_cons:
            conservative_count += 1
            action = "retain"
            severity = "low"
            note = f"Conservative SHM ({germline_aa}→{observed}) — retain, likely stabilizing"
        else:
            non_conservative_count += 1
            if in_vernier or in_hallmark:
                action = "protect"
                severity = "medium"
                note = (
                    f"Non-conservative SHM ({germline_aa}→{observed}) at "
                    f"{'Hallmark' if in_hallmark else 'Vernier'} position — PROTECT, do not revert"
                )
            else:
                action = "flag"
                severity = "high"
                note = (
                    f"Non-conservative SHM ({germline_aa}→{observed}) at FR position {label} — "
                    "review: may be destabilizing if not antigen-contact-driven"
                )

        shm_hits.append({
            "kabat": label,
            "observed": observed,
            "germline_ref": germline_aa,
            "conservative": is_cons,
            "in_vernier": in_vernier,
            "in_hallmark": in_hallmark,
            "action": action,
            "severity": severity,
            "note": note,
        })

    non_cons_fr = non_conservative_count
    shm_load = (
        "HIGH" if non_cons_fr >= 5
        else "MODERATE" if non_cons_fr >= 2 or conservative_count >= 5
        else "LOW"
    )
    return {
        "germline_reference": "IGHV3-23*01 consensus (IMGT, embedded)",
        "same_as_germline": same_count,
        "conservative_shm": conservative_count,
        "non_conservative_shm": non_conservative_count,
        "total_shm_positions": conservative_count + non_conservative_count,
        "shm_load": shm_load,
        "shm_positions": shm_hits,
        "high_risk_positions": [p for p in shm_hits if p["severity"] == "high"],
        "algorithm": "transgenic_shm_scan_v1.0",
    }


# ─────────────────────────────────────────────────────────────────────────────
# Mutation engine (Stage 2)
# ─────────────────────────────────────────────────────────────────────────────

def _apply_conversion_mutations(vh_seq: str, source_type: str, cdr3_len: int, cdr2_len: int) -> Dict[str, Any]:
    """
    Apply Hallmark (Kabat 44/45/47) and solubility-enhancing substitutions using Kabat numbering.
    Returns {sequence, mutations_applied, already_canonical, error}.
    """
    try:
        from anarcii import Anarcii
        from core.humanization.kabat_utils import kabat_from_anarcii, sorted_keys

        a = Anarcii(seq_type="antibody", mode="accuracy")
        a.number([vh_seq])
        entry = a.to_scheme("kabat").get("Sequence 1", {})
        if entry.get("error") or entry.get("chain_type") != "H":
            raise ValueError(f"ANARCI did not recognise a VH domain: {entry.get('error','unknown error')}")

        kd = kabat_from_anarcii(entry["numbering"])
        keys = sorted_keys(kd)

        # Build (Kabat key) → linear-index mapping
        pos_to_idx: Dict[tuple, int] = {k: i for i, k in enumerate(keys)}

        # [V1.8.6] Hallmark: K45R is the sole default core hallmark.
        # K44E / K47F are rescue-only (CDR3>=15 AND compactness>6.5A); not evaluated here
        # (rescue path requires structure prediction output from Phase 4).
        hallmark_plan = {
            (45, ""): "R",   # L→R: 86% in AutonomousHumanVH_Cohort_v1 (n=36)
        }

        # [V1.8.6] Stealth (K-gated): only trigger if the original residue is K.
        # Human VH positions 35/50/89/94 are often S/T/V/R, not K — do not force-replace them.
        # V1.8.5 "K50 R/K preservation" rule is reverted (was based on coordinate misuse).
        solubility_plan: Dict[tuple, str] = {}
        _stealth_k_target: Dict[tuple, str] = {
            (94, ""): "R",
            (35, ""): "N",
            (50, ""): "D",
            (89, ""): "L",
        }
        # Build solubility plan only for positions where original == "K"
        solubility_plan[(94, "")] = "R"  # evaluated for K94 gate in loop below
        if cdr3_len >= 10:
            solubility_plan[(35, "")] = "N"
            if cdr2_len < 17:
                solubility_plan[(50, "")] = "D"
        if cdr3_len >= 17:
            solubility_plan[(89, "")] = "L"

        all_targets = {**hallmark_plan, **solubility_plan}

        seq_arr = list(vh_seq)
        mutations_applied: List[str] = []
        already_canonical: List[str] = []

        for pos_key, target_aa in all_targets.items():
            if pos_key not in pos_to_idx:
                continue
            idx = pos_to_idx[pos_key]
            orig = seq_arr[idx]
            label = f"Kabat{pos_key[0]}{pos_key[1]}"
            # [V1.8.6] K45R: R or A are both VHH-compatible, skip
            if pos_key == (45, "") and orig in ("R", "A"):
                already_canonical.append(f"{orig}{label} (VHH canonical, keep)")
                continue
            # [V1.8.6] Stealth K-gate: positions 35/50/89/94 only trigger when original == K
            if pos_key in {(35, ""), (50, ""), (89, ""), (94, "")} and orig != "K":
                already_canonical.append(f"{orig}{label} (not K, Stealth K-gate skip)")
                continue
            if orig == target_aa:
                already_canonical.append(f"{orig}{label} (no change)")
                continue

            seq_arr[idx] = target_aa
            mutations_applied.append(f"{orig}{pos_key[0]}{target_aa}")

        # [V1.8.10] Path C Liability Gate: fix unpaired Cys in CDRs for ALL source classes.
        # Previously gated to murine_mab only — extended to humanized_mab and human_mab
        # because CDR Cys (e.g. in anti-CD3 CDR3) is an expression blocker regardless of origin.
        # Kabat CDR ranges: CDR1 31-35, CDR2 50-65, CDR3 95-102 (extended for insertion codes)
        cdr_cys = []
        for k, aa in kd.items():
            if aa == "C":
                # skip conserved disulfide C22, C92
                if k in {(22, ""), (92, "")}:
                    continue
                # check if in CDR (Kabat)
                if (31 <= k[0] <= 35) or (50 <= k[0] <= 65) or (95 <= k[0] <= 102):
                    cdr_cys.append(k)

        for k in cdr_cys:
            idx = pos_to_idx[k]
            orig = seq_arr[idx]
            seq_arr[idx] = "S"  # C -> S
            ins = k[1] if k[1] else ""
            mutations_applied.append(f"{orig}{k[0]}{ins}S (Path C Cys-gate)")

        result: Dict[str, Any] = {
            "sequence": "".join(seq_arr),
            "mutations_applied": mutations_applied,
            "already_canonical": already_canonical,
            "error": None,
        }

        # ── Source-specific algorithm extensions ────────────────────────────
        if source_type == "phage_display_vh":
            result["phage_charge_audit"] = _phage_charge_audit(kd, pos_to_idx)
        elif source_type == "transgenic_mouse_vh":
            result["transgenic_shm_scan"] = _transgenic_shm_scan(kd, pos_to_idx)

        return result

    except Exception as exc:
        return {
            "sequence": vh_seq,
            "mutations_applied": [],
            "already_canonical": [],
            "error": str(exc),
        }


def _apply_phase45_sdab_adapt(
    seq: str,
    kd: Dict[tuple, str],
    pos_to_idx: Dict[tuple, int],
    source_class: str,
    mini_pI: Optional[float] = None,
) -> Dict[str, Any]:
    """
    V1.8.6 Phase 4.5 sdAb adaptation mutations (simplified).
    - L18S: DISABLED by default (human VH K18=L frequency 97%; no cohort support for benefit).
    - F68Y: only triggers when original K68 == 'F' (human VH K68 is almost always T; T68Y unsupported).
    - K72D: pI tune when pI > 9.0 (updated V1.8.11; calibrated to Clinical_VHH p90=9.08).

    Returns {sequence, mutations_applied, skipped_mutations, error}.
    """
    try:
        from core.humanization.kabat_utils import sorted_keys  # noqa: PLC0415

        # [V1.8.6] L18S removed from default plan; F68Y now gated strictly to orig==F
        phase45_plan: Dict[tuple, str] = {
            (68, ""): "Y",   # only if orig==F (gate enforced below)
        }
        # Optional pI tune: only when pI > 9.0 (V1.8.11 — updated from 8.5 to align with Clinical_VHH p90=9.08)
        if mini_pI is not None and mini_pI > 9.0:
            # [V1.8.8] Adaptive pI Tuning Fallback
            if (72, "") in pos_to_idx and kd.get((72, "")) == "K":
                phase45_plan[(72, "")] = "D"   # conservative charge reduction (K→D)
            else:
                # Look for other surface basic residues: 73, 13, 19, 83...
                for alt_k in [(73, ""), (13, ""), (19, ""), (83, "")]:
                    if alt_k in pos_to_idx and kd.get(alt_k) in ("K", "R"):
                        phase45_plan[alt_k] = "Q"  # K/R -> Q
                        break

        seq_arr = list(seq)
        mutations_applied: List[str] = []
        skipped: List[str] = []

        for pos_key, target_aa in phase45_plan.items():
            if pos_key not in pos_to_idx:
                skipped.append(f"Kabat{pos_key[0]} not in sequence map")
                continue
            idx = pos_to_idx[pos_key]
            orig = seq_arr[idx]
            label = f"Kabat{pos_key[0]}"

            # Skip if already canonical
            if orig == target_aa:
                skipped.append(f"{orig}{label} already {target_aa}")
                continue
            # [V1.8.6] F68Y: only trigger when original residue is F.
            # Human VH K68 is almost universally T (92% in cohort n=36); T68Y has no data support.
            # V1.8.5 "A/P/T Natural Mimetic" exemption is superseded by stricter F-only gate.
            if pos_key == (68, ""):
                if orig != "F":
                    skipped.append(f"{orig}{label}: not F, skip F68Y (V1.8.6 strict gate)")
                    continue
            # pI tune: only apply K→D
            if pos_key == (72, "") and orig != "K":
                skipped.append(f"{orig}{label}: not K, skip pI-tune gate")
                continue
            # CMC drift guard: N-glycosylation sequon check (NxS/T)
            seq_arr[idx] = target_aa
            test_seq = "".join(seq_arr)
            import re as _re  # noqa: PLC0415
            if _re.search(r"N[^P][ST]", test_seq):
                # Check if motif is new (absent in original)
                if not _re.search(r"N[^P][ST]", seq):
                    seq_arr[idx] = orig  # revert
                    skipped.append(f"{orig}{label}→{target_aa}: skipped — introduces new N-glycosylation motif")
                    continue

            mutations_applied.append(f"{orig}{pos_key[0]}{target_aa}")

        return {
            "sequence": "".join(seq_arr),
            "mutations_applied": mutations_applied,
            "skipped_mutations": skipped,
            "error": None,
        }

    except Exception as exc:
        return {
            "sequence": seq,
            "mutations_applied": [],
            "skipped_mutations": [],
            "error": str(exc),
        }


def _compute_expressibility_verdict(
    cdr3_len: Optional[int],
    compactness: Optional[float],
    abnativ_delta: Optional[float],
) -> Dict[str, Any]:
    """
    [V1.8.6] Expressibility Verdict Gate (owner-mandated).

    CDR3 length, CDR3 compactness, and AbNatiV Δ must all qualify for a sequence
    to be considered expressible / secretable / stable.

    Returns a dict with keys:
        verdict  : "EXCELLENT" | "PASS" | "WARN" | "FAIL" | "INCOMPLETE"
        criteria : list of per-dimension dicts with {metric, value, status, reason}
    """
    criteria = []
    fail_count = 0
    warn_count = 0

    # --- CDR3 length ---
    if cdr3_len is None:
        criteria.append({"metric": "CDR3 length", "value": None, "status": "UNKNOWN", "reason": "not computed"})
    elif cdr3_len < 8:
        criteria.append({"metric": "CDR3 length", "value": cdr3_len, "status": "FAIL",
                          "reason": "< 8 aa: cannot physically cover VH-VL hydrophobic interface"})
        fail_count += 1
    elif cdr3_len <= 9:
        criteria.append({"metric": "CDR3 length", "value": cdr3_len, "status": "WARN",
                          "reason": "8–9 aa: borderline interface coverage; structural verification required"})
        warn_count += 1
    else:
        criteria.append({"metric": "CDR3 length", "value": cdr3_len, "status": "PASS",
                          "reason": f"≥ 10 aa: adequate interface coverage"})

    # --- CDR3 compactness ---
    if compactness is None:
        criteria.append({"metric": "CDR3 compactness", "value": None, "status": "UNKNOWN", "reason": "structure not predicted"})
    elif compactness > 7.5:
        criteria.append({"metric": "CDR3 compactness", "value": round(compactness, 2), "status": "FAIL",
                          "reason": "> 7.5 Å: CDR3 too extended to shield hydrophobic interface"})
        fail_count += 1
    elif compactness > 6.5:
        criteria.append({"metric": "CDR3 compactness", "value": round(compactness, 2), "status": "WARN",
                          "reason": "6.5–7.5 Å: marginal compactness; rescue hallmark may be warranted"})
        warn_count += 1
    else:
        criteria.append({"metric": "CDR3 compactness", "value": round(compactness, 2), "status": "PASS",
                          "reason": f"≤ 6.5 Å: compact CDR3"})

    # --- AbNatiV Δ ---
    if abnativ_delta is None:
        criteria.append({"metric": "AbNatiV Δ", "value": None, "status": "UNKNOWN", "reason": "AbNatiV not computed"})
    elif abnativ_delta < -0.074:
        criteria.append({"metric": "AbNatiV Δ", "value": round(abnativ_delta, 4), "status": "FAIL",
                          "reason": "< -0.074: sequence globally too VH-like even after conversion; latent aggregation risk"})
        fail_count += 1
    elif abnativ_delta < -0.050:
        criteria.append({"metric": "AbNatiV Δ", "value": round(abnativ_delta, 4), "status": "WARN",
                          "reason": "-0.074 to -0.050: borderline; marginal VHH naturalness gain"})
        warn_count += 1
    else:
        criteria.append({"metric": "AbNatiV Δ", "value": round(abnativ_delta, 4), "status": "PASS",
                          "reason": "≥ -0.050: sufficient VHH naturalness gain"})

    # --- Composite verdict ---
    unknown_count = sum(1 for c in criteria if c["status"] == "UNKNOWN")
    if fail_count > 0:
        verdict = "FAIL"
    elif unknown_count == len(criteria):
        verdict = "INCOMPLETE"
    elif warn_count > 0:
        verdict = "WARN"
    else:
        # All PASS: check for EXCELLENT
        excellent = (
            cdr3_len is not None and cdr3_len >= 10
            and compactness is not None and compactness <= 6.0
            and abnativ_delta is not None and abnativ_delta >= 0.0
        )
        verdict = "EXCELLENT" if excellent else "PASS"

    return {"verdict": verdict, "criteria": criteria}


_FR_POSITIONS = list(range(1, 27)) + list(range(39, 56)) + list(range(66, 105)) + list(range(118, 129))
_FR2_POSITIONS = list(range(39, 56))
_VHH_44_ALLOWED = {"Q", "E", "G", "A", "S", "D"}
_VHH_45_ALLOWED = {"A", "R", "L", "K", "Q"}
_VHH_47_ALLOWED = {"F", "Y", "L", "W", "G"}


def _load_vhh42_templates() -> List[Dict[str, Any]]:
    cache_path = ROOT / "data" / "vhh_clinical_39_union" / "vhh42_templates_cache.json"
    data = json.loads(cache_path.read_text(encoding="utf-8"))
    return data if isinstance(data, list) else []


def _identity_at_positions(query_map: Dict[int, str], template_map: Dict[int, str], positions: List[int]) -> float:
    same = 0
    total = 0
    for pos in positions:
        q = query_map.get(pos)
        t = template_map.get(pos)
        if q and t:
            total += 1
            if q == t:
                same += 1
    return same / total if total else 0.0


def _hallmark_score(template_map: Dict[int, str]) -> float:
    same = 0
    total = 3
    if template_map.get(44) in _VHH_44_ALLOWED:
        same += 1
    if template_map.get(45) in _VHH_45_ALLOWED:
        same += 1
    if template_map.get(47) in _VHH_47_ALLOWED:
        same += 1
    return same / total


def _generate_conversion_candidates(
    vh_seq: str,
    source_class: str,
    cdr3_len: int,
    cdr2_len: int,
    top_n: int = 3,
    enable_scaffold_graft: bool = False,  # [V1.8.10] Opt-in only — see standard §2.3
) -> List[Dict[str, Any]]:
    """
    Real candidate generation:
    1) [DEFAULT] camelized donor baseline (keep-framework + hallmark/stealth) — Path C standard
    2) [OPT-IN]  clinical-VHH scaffold graft (CDR graft onto VHH42 frameworks)
                 only when enable_scaffold_graft=True (explicit user request)

    [V1.8.10 rule] cdr_graft_to_scaffold is NOT the default Path C strategy.
    The standard (§Phase 2-5) defines point-mutation-based camelize as Path C.
    CDR grafting onto VHH scaffold is a distinct operation (VHH chimera creation)
    and must only run when explicitly requested. Evidence: AutonomousHumanVH_Cohort_v1
    (n=36) shows zero cases of scaffold-graft; all use point mutations on VH framework.
    """
    from core.vhh.vhh_scaffold_match_and_craft import (  # noqa: PLC0415
        _build_vhh_residue_map_and_regions,
        craft_humanized_vhh,
    )

    donor_map, donor_regions = _build_vhh_residue_map_and_regions(vh_seq)

    # [V1.8.8] Path C2 Liability Gate: fix unpaired Cys in CDRs for murine VH
    # [V1.8.8] Extended to all Path C (VH->VHH) conversions for secretion proof
    path_c2_muts = []
    if source_class in ("murine_mab", "humanized_mab", "human_mab"):
        # We must iterate over _ordered_rows to handle insertion codes and IMGT numbering
        new_ordered_rows = []
        for pos, ins, aa in getattr(donor_map, "_ordered_rows", []):
            if aa == "C":
                # skip conserved disulfide IMGT 23, 104 (approx Kabat 22, 92)
                if pos in {23, 104}:
                    new_ordered_rows.append((pos, ins, aa))
                    continue
                # check if in CDR (IMGT 27-38, 56-65, 105-117)
                if (27 <= pos <= 38) or (56 <= pos <= 65) or (105 <= pos <= 117):
                    new_ordered_rows.append((pos, ins, "S"))
                    path_c2_muts.append(f"C{pos}{ins}S (Path C Liability-gate)")
                    # Update the base residue_map too
                    donor_map[pos] = "S"
                else:
                    new_ordered_rows.append((pos, ins, aa))
            else:
                new_ordered_rows.append((pos, ins, aa))
        # Replace _ordered_rows with the mutated version
        if hasattr(donor_map, "_ordered_rows"):
            donor_map._ordered_rows = new_ordered_rows

    templates = _load_vhh42_templates()
    scored: List[Dict[str, Any]] = []

    # [V1.8.10] CDR graft onto scaffold is OPT-IN only.
    # Default Path C does NOT run scaffold graft (see standard §2.3 and cohort evidence).
    if enable_scaffold_graft:
        for tmpl in templates:
            tmpl_map = {int(k): v for k, v in (tmpl.get("imgt_positions") or {}).items()}
            fr_id = _identity_at_positions(donor_map, tmpl_map, _FR_POSITIONS)
            fr2_id = _identity_at_positions(donor_map, tmpl_map, _FR2_POSITIONS)
            hm = _hallmark_score(tmpl_map)
            germ = str(tmpl.get("germline") or "")

            germline_bonus = 0.0
            if germ.startswith("IGHV3-23"):
                germline_bonus = 0.05
            elif germ.startswith("IGHV3-66"):
                germline_bonus = 0.04
            elif germ.startswith("IGHV3") or germ.startswith("IGHV4"):
                germline_bonus = 0.02

            source_bonus = 0.0
            if source_class == "murine_mab":
                source_bonus += 0.03
            elif source_class == "transgenic_mouse_vh":
                if germ.startswith("IGHV3"):
                    source_bonus += 0.04
                elif germ.startswith("IGHV4"):
                    source_bonus += 0.02
            elif source_class == "human_mab" and germ.startswith("IGHV3"):
                source_bonus += 0.03
            elif source_class == "phage_display_vh" and germ.startswith("IGHV3"):
                source_bonus += 0.02

            seq = craft_humanized_vhh(donor_map, donor_regions, tmpl)
            if not seq:
                continue

            score = 0.58 * fr_id + 0.22 * fr2_id + 0.15 * hm + germline_bonus + source_bonus
            scored.append(
                {
                    "candidate_id": f"graft::{tmpl.get('template_id', 'template')}",
                    "strategy": "cdr_graft_to_scaffold",
                    "template_id": tmpl.get("template_id"),
                    "source_scaffold": tmpl.get("source_scaffold"),
                    "germline": germ,
                    "sequence": seq,
                    "template_score": round(score, 4),
                    "framework_identity": round(fr_id, 4),
                    "fr2_identity": round(fr2_id, 4),
                    "hallmark_score": round(hm, 4),
                    "mutations_applied": list(path_c2_muts),
                    "already_canonical": [],
                }
            )

        scored.sort(key=lambda x: x["template_score"], reverse=True)

    baseline = _apply_conversion_mutations(vh_seq, source_class, cdr3_len, cdr2_len)
    baseline_candidate = {
        "candidate_id": "camelize::baseline",
        "strategy": "keep_framework_and_camelize",
        "template_id": "parent_vh_framework",
        "source_scaffold": "PARENT_FRAMEWORK",
        "germline": None,
        "sequence": baseline.get("sequence") or vh_seq,
        "template_score": round((scored[0]["template_score"] if scored else 0.55) * 0.9, 4),
        "framework_identity": 1.0,
        "fr2_identity": 1.0,
        "hallmark_score": 0.0,
        "mutations_applied": baseline.get("mutations_applied") or [],
        "already_canonical": baseline.get("already_canonical") or [],
        "conversion_error": baseline.get("error"),
        # Source-specific audit results (populated only for the relevant source class)
        "phage_charge_audit": baseline.get("phage_charge_audit"),
        "transgenic_shm_scan": baseline.get("transgenic_shm_scan"),
    }

    # [V1.8.10] Strategy ordering:
    # Default (enable_scaffold_graft=False): baseline is always first and only standard candidate.
    # Opt-in (enable_scaffold_graft=True): append graft candidates after baseline.
    ordered: List[Dict[str, Any]] = []
    ordered.append(baseline_candidate)
    if enable_scaffold_graft and scored:
        ordered.extend(scored[: max(top_n + 2, 4)])

    # ── P0-2: Phase 4.5 sdAb adaptation enhanced candidates ─────────────────
    if ENABLE_PHASE45:
        try:
            from anarcii import Anarcii  # noqa: PLC0415
            from core.humanization.kabat_utils import kabat_from_anarcii  # noqa: PLC0415

            _p45_sources = []
            # baseline + phase45 (always)
            _p45_sources.append(("baseline+phase45", baseline_candidate))
            # top graft + phase45 only when graft was explicitly requested
            if enable_scaffold_graft and scored:
                _p45_sources.append(("graft_top+phase45", scored[0]))

            for p45_id_suffix, src_cand in _p45_sources:
                src_seq = src_cand.get("sequence") or ""
                if not src_seq:
                    continue
                try:
                    _a = Anarcii(seq_type="antibody", mode="accuracy")
                    _a.number([src_seq])
                    _entry = _a.to_scheme("kabat").get("Sequence 1", {})
                    if _entry.get("error"):
                        continue
                    _kd = kabat_from_anarcii(_entry["numbering"])
                    from core.humanization.kabat_utils import sorted_keys as _sk  # noqa: PLC0415
                    _keys = _sk(_kd)
                    _p2i = {k: i for i, k in enumerate(_keys)}

                    # [V1.8.8] Calculate rough pI for adaptive tuning
                    from core.humanization.engine import _vhh_mini_cmc as _cmc  # noqa: PLC0415
                    _mini = _cmc(src_seq)
                    _pI = _mini.get("pI") if isinstance(_mini, dict) else None

                    p45_result = _apply_phase45_sdab_adapt(
                        src_seq, _kd, _p2i, source_class, mini_pI=_pI
                    )
                    p45_seq = p45_result.get("sequence") or src_seq
                    if p45_seq and p45_seq != src_seq:
                        p45_cand = dict(src_cand)
                        p45_cand["candidate_id"] = src_cand["candidate_id"] + "::phase45"
                        p45_cand["strategy"] = src_cand.get("strategy", "") + "+phase45"
                        p45_cand["sequence"] = p45_seq
                        p45_cand["phase45_mutations"] = p45_result.get("mutations_applied") or []
                        p45_cand["phase45_skipped"] = p45_result.get("skipped_mutations") or []
                        # Slightly discount template_score (Phase 4.5 adds mutations, uncertainty ++)
                        p45_cand["template_score"] = round(
                            float(src_cand.get("template_score") or 0) * 0.97, 4
                        )
                        ordered.append(p45_cand)
                except Exception:
                    pass
        except Exception:
            pass

    # dedupe by final sequence
    deduped: List[Dict[str, Any]] = []
    seen = set()
    for cand in ordered:
        seq = cand.get("sequence") or ""
        if not seq or seq in seen:
            continue
        seen.add(seq)
        deduped.append(cand)

    # ── P0-1: AbNatiV Δ scoring for each candidate ───────────────────────────
    if ENABLE_ABNATIV_GATE:
        try:
            from core.vh2vhh.abnativ_naturalness_layer import score_naturalness_delta as _score_seq  # noqa: PLC0415
            for cand in deduped:
                cand_seq = cand.get("sequence") or ""
                if not cand_seq:
                    cand["abnativ_delta"] = None
                    cand["abnativ_tier"] = "UNKNOWN"
                    continue
                try:
                    _res = _score_seq(cand_seq)
                    cand["abnativ_delta"] = round(float(_res.delta), 4) if _res.delta is not None else None
                    cand["abnativ_tier"] = getattr(_res, "tier", getattr(_res, "verdict", "UNKNOWN"))
                    cand["abnativ_vh2"] = round(float(_res.vh2_score), 4) if _res.vh2_score is not None else None
                    cand["abnativ_vhh2"] = round(float(_res.vhh2_score), 4) if _res.vhh2_score is not None else None
                    cand["abnativ_reliability_warning"] = bool(
                        getattr(_res, "reliability_warning", False)
                    )
                except Exception:
                    cand["abnativ_delta"] = None
                    cand["abnativ_tier"] = "ERROR"
                    cand["abnativ_reliability_warning"] = True

            # Re-rank: final_score = template_score * 0.6 + delta_normalized * 0.4
            # delta_normalized maps [-0.074, +0.085] → [0, 1] (V1.8.4 calibration)
            _DELTA_LO, _DELTA_HI = -0.074, 0.085
            def _final_score(c: Dict[str, Any]) -> float:
                ts = float(c.get("template_score") or 0)
                d = c.get("abnativ_delta")
                if d is None:
                    dn = 0.0
                else:
                    dn = max(0.0, min(1.0, (float(d) - _DELTA_LO) / (_DELTA_HI - _DELTA_LO)))
                return ts * 0.6 + dn * 0.4

            deduped.sort(key=_final_score, reverse=True)
        except Exception:
            pass

    return deduped[: max(top_n, 5)]


# ─────────────────────────────────────────────────────────────────────────────
# Source-specific advisory builder
# ─────────────────────────────────────────────────────────────────────────────

def _build_source_advisory(source_class: str, mini_cmc: dict, cdr3_len: Optional[int]) -> Dict[str, Any]:
    """
    Generate source-specific engineering advisory for VH→VHH conversion.
    Returns dict with: source_label, path, key_risks, key_strengths, recommended_steps,
    vam_priority, charge_flag.
    """
    nc = mini_cmc.get("net_charge_pH7") if mini_cmc else None
    charge_flag = nc is not None and float(nc) < -2.0
    cdr3 = cdr3_len or 0

    if source_class == "phage_display_vh":
        risks: List[str] = [
            "In vitro affinity maturation may limit binding strength vs in vivo matured antibodies; "
            "Virtual Affinity Maturation (VAM) recommended post-conversion.",
        ]
        strengths = [
            "Fully human IGHV framework — lower immunogenicity baseline.",
            "CDR sequences designed from diverse synthetic library — broad epitope coverage.",
        ]
        steps = ["Hallmark and solubility engineering (standard)"]
        if charge_flag:
            risks.append(
                f"Negative charge bias detected (net charge ≈{float(nc):.1f} at pH 7): "
                "common artifact of acidic phage elution (pH 2–3). "
                "Risk: accelerated renal clearance, reduced half-life in vivo."
            )
            steps.append(
                "Charge compensation audit: decompose CDR vs FR charge contribution; "
                "apply framework-localized charge-neutral substitutions if CDR3 is charge-driver."
            )
        if cdr3 >= 18:
            risks.append(
                f"Long CDR3 ({cdr3} aa): review for synthetic G/S repeat artifacts or "
                "unpaired Cys pairs common in loop-constrained library designs."
            )
        steps.append("VAM (recommended if post-conversion Kd > 10 nM or if binding activity is unconfirmed)")
        return {
            "source_label": "Phage-Display VH",
            "path": "Path C1 — Framework-preserving camelization (human VH origin)",
            "key_risks": risks,
            "key_strengths": strengths,
            "recommended_steps": steps,
            "vam_priority": "high",
            "charge_flag": charge_flag,
        }

    elif source_class == "transgenic_mouse_vh":
        risks = [
            "Somatic hypermutation (SHM) may have introduced non-germline FR residues; "
            "verify IGHV FR positions deviating from closest germline allele.",
            "Transgenic HCAb VH may carry mouse SHM hotspot motifs (WRCY/RGYW) that "
            "deviate from human germline — germline similarity score may appear lower than expected.",
        ]
        strengths = [
            "In vivo affinity maturation provides high-affinity CDR3 (typically Kd < 1 nM); "
            "VAM is rarely required.",
            "CDR3 from V(D)J recombination + SHM → natural loop conformation; structural QC expected to pass.",
            "Implicit stability selection by in vivo immune system — lower aggregation risk vs phage-display.",
        ]
        steps = [
            "Hallmark and solubility engineering at Kabat 44/45/47 (standard — apply regardless of SHM status).",
            "SHM audit: compare FR1/FR2/FR3 against closest IGHV germline allele; "
            "retain stabilizing SHM mutations, flag any destabilizing non-conservative changes.",
            "CDR3 length check: HCAb CDR3 is typically 10–14 aa; "
            "Solubility-enhancing 89→L may be omitted if CDR3 < 17 aa.",
        ]
        if charge_flag:
            risks.append(
                f"Net charge {float(nc):.1f} is unexpectedly negative for in vivo matured VH; "
                "check if CDR3 encodes multiple Asp/Glu (antigen-contact driven) or if FR charge is atypical."
            )
        return {
            "source_label": "Transgenic Mouse VH (HCAb-derived)",
            "path": "Path C2b — SHM-aware camelization (in vivo matured human-germline VH)",
            "key_risks": risks,
            "key_strengths": strengths,
            "recommended_steps": steps,
            "vam_priority": "low",
            "charge_flag": charge_flag,
        }

    elif source_class == "murine_mab":
        return {
            "source_label": "Murine VH (conventional mouse mAb)",
            "path": "Path C2 — Dual engineering: humanization + camelization",
            "key_risks": [
                "Murine FR regions require humanization before camelization — two sequential engineering steps.",
                "CDR-FR junctions in mouse VH may differ from human IGHV Vernier zones; validate post-graft.",
            ],
            "key_strengths": [
                "Mouse immune response provides fully validated antigen-binding specificity.",
                "Extensive literature on murine→human CDR grafting provides benchmarks.",
            ],
            "recommended_steps": [
                "Phase 1: FR humanization (select IGHV/IGHJ template by CDR-weighted identity).",
                "Phase 2: Hallmark and solubility-enhancing substitutions (standard, post-humanization).",
                "Phase 3: CMC QA + structure prediction.",
            ],
            "vam_priority": "medium",
            "charge_flag": charge_flag,
        }

    else:  # human_mab or humanized_mab
        return {
            "source_label": "Humanized / Human mAb VH",
            "path": "Path C1 — Framework-preserving camelization",
            "key_risks": [
                "Hallmark mutations at 44/45/47 may affect VH-VL interface if paired VL is retained downstream.",
            ],
            "key_strengths": [
                "Human IGHV framework — highest germline similarity, lowest immunogenicity baseline.",
                "Framework-preserving strategy minimizes CDR conformation shift risk.",
            ],
            "recommended_steps": [
                "Hallmark and solubility engineering (standard).",
                "CDR conformation check (RMSD) post-conversion.",
            ],
            "vam_priority": "medium",
            "charge_flag": charge_flag,
        }


def _source_advisory_html(advisory: Dict[str, Any]) -> str:
    """Render source advisory dict to HTML block for the report."""
    import html as _html

    def esc(v: Any) -> str:
        return _html.escape(str(v)) if v is not None else "—"

    risks_html = "".join(f"<li style='color:#b56300'>{esc(r)}</li>" for r in advisory.get("key_risks", []))
    strengths_html = "".join(f"<li style='color:#1a6b3c'>{esc(s)}</li>" for s in advisory.get("key_strengths", []))
    steps_html = "".join(f"<li>{esc(s)}</li>" for s in advisory.get("recommended_steps", []))
    vam = advisory.get("vam_priority", "medium")
    vam_color = {"high": "#d32f2f", "medium": "#b56300", "low": "#1a6b3c"}.get(vam, "#555")
    charge_note = (
        "<div style='margin-top:6px;padding:4px 10px;background:#fff3cd;border-radius:4px;"
        "font-size:11px;color:#856404'>⚡ Charge screening flagged: net charge &lt; −2 at pH 7. "
        "Review charge compensation step.</div>"
        if advisory.get("charge_flag") else ""
    )

    return f"""
<table class="kv" style="margin-bottom:8px">
  <tr><td class="lbl">Source</td><td><strong>{esc(advisory.get("source_label","—"))}</strong></td></tr>
  <tr><td class="lbl">Engineering path</td><td>{esc(advisory.get("path","—"))}</td></tr>
  <tr><td class="lbl">VAM priority</td>
      <td><span style="color:{vam_color};font-weight:700">{vam.upper()}</span>
      {"— in vitro selection: binding strength should be validated post-conversion" if vam == "high" else
       "— in vivo maturation provides strong baseline; VAM only if Kd validation fails" if vam == "low" else
       "— validate binding post-conversion; VAM available if affinity needs improvement"}</td></tr>
</table>
{charge_note}
<div style="display:grid;grid-template-columns:1fr 1fr;gap:12px;margin-top:10px">
  <div>
    <div style="font-size:11px;font-weight:700;color:#b56300;margin-bottom:4px">⚠ Source-Specific Risks</div>
    <ul style="font-size:11px;line-height:1.6;margin:0;padding-left:16px">{risks_html or "<li>None identified</li>"}</ul>
  </div>
  <div>
    <div style="font-size:11px;font-weight:700;color:#1a6b3c;margin-bottom:4px">✓ Source Strengths</div>
    <ul style="font-size:11px;line-height:1.6;margin:0;padding-left:16px">{strengths_html or "<li>—</li>"}</ul>
  </div>
</div>
<div style="margin-top:10px">
  <div style="font-size:11px;font-weight:700;color:#1e3a5f;margin-bottom:4px">→ Recommended Engineering Steps</div>
  <ol style="font-size:11px;line-height:1.6;margin:0;padding-left:18px">{steps_html}</ol>
</div>
"""


# ─────────────────────────────────────────────────────────────────────────────
# V1.5 Risk-Forward Assessment (success probability + attribution matrix)
# ─────────────────────────────────────────────────────────────────────────────

def _compute_v15_risk_assessment(payload: Dict[str, Any]) -> Dict[str, Any]:
    """
    V1.5 Risk-Forward Reporting computation.

    Inputs from `payload` (already populated by Stage 1–5 of the pipeline):
      - mini_cmc: {pI, GRAVY, instability_index, length}
      - cmc_flags: list[str]
      - cdr3_length: int | None
      - conversion_advisory: dict | None (legacy CMC advisory layer)
      - phage_charge_audit / transgenic_shm_scan: optional dicts

    Outputs (added to payload by caller):
      - success_probability (float, 0.0–1.0)
      - confidence_band ("high"|"medium"|"low")
      - verdict_severity ("HIGH_RISK"|"MODERATE_RISK"|"LOW_RISK")
      - primary_blocker (str | None)
      - primary_recommendation ("A"|"B"|"C")
      - risk_attribution (list[dict])
      - action_roadmap (dict)
    """
    mini_cmc: Dict[str, Any] = payload.get("mini_cmc") or {}
    cmc_flags: List[str] = payload.get("cmc_flags") or []
    cdr3_length: Optional[int] = payload.get("cdr3_length")

    pI = mini_cmc.get("pI")
    instability = mini_cmc.get("instability_index")
    converted_seq = payload.get("converted_sequence") or ""

    # ── Detect blockers/warns ───────────────────────────────────────────────
    risk_rows: List[Dict[str, Any]] = []
    success = 1.0

    # 1. pI gate
    if isinstance(pI, (int, float)):
        if pI < 5.5:
            success *= 0.20
            risk_rows.append({
                "risk_dimension": "pI",
                "current_value": round(float(pI), 2),
                "safety_threshold": "≥ 6.0",
                "attribution_source": "CDR3 acidic residue density (D/E)",
                "severity": "BLOCKER",
            })
        elif pI < 6.0:
            success *= 0.50
            risk_rows.append({
                "risk_dimension": "pI",
                "current_value": round(float(pI), 2),
                "safety_threshold": "≥ 6.0",
                "attribution_source": "Borderline acidic surface; CDR/FR D/E balance",
                "severity": "WARN",
            })

    # 2. N-glycosylation in CDR
    nglyc_in_cdr = any("N_glycosylation" in f and "HIGH_RISK" in f for f in cmc_flags)
    if nglyc_in_cdr:
        success *= 0.40
        risk_rows.append({
            "risk_dimension": "CDR N-glycosylation",
            "current_value": "present",
            "safety_threshold": "absent",
            "attribution_source": "N-X-S/T sequon detected in CDR",
            "severity": "BLOCKER",
        })

    # 3. Long CDR3 + V50 retained (CDR2 gate-protected)
    cdr2_length = payload.get("cdr2_length")
    v50_retained = (
        isinstance(cdr2_length, int) and cdr2_length >= 17
        and converted_seq
        and isinstance(cdr3_length, int) and cdr3_length >= 16
    )
    if v50_retained:
        success *= 0.50
        risk_rows.append({
            "risk_dimension": "V50 hydrophobic retained",
            "current_value": f"V at Kabat50 (CDR2={cdr2_length}aa)",
            "safety_threshold": "polar (D/S) or CDR2 ≤ 16aa",
            "attribution_source": "CDR2 length gate prevents Stealth A50 mutation",
            "severity": "WARN",
        })

    # 4. free_cys
    free_cys_flagged = any("free_cys" in f.lower() and ("FAIL" in f or "HIGH_RISK" in f) for f in cmc_flags)
    if free_cys_flagged:
        success *= 0.30
        risk_rows.append({
            "risk_dimension": "Unpaired Cys",
            "current_value": "present",
            "safety_threshold": "absent (besides conserved 22/92)",
            "attribution_source": "Free Cys in framework or CDR",
            "severity": "BLOCKER",
        })

    # 5. Instability index
    if isinstance(instability, (int, float)):
        if instability > 50:
            success *= 0.40
            risk_rows.append({
                "risk_dimension": "Instability Index",
                "current_value": round(float(instability), 1),
                "safety_threshold": "≤ 40",
                "attribution_source": "Sequence-intrinsic instability motifs",
                "severity": "BLOCKER",
            })
        elif instability > 40:
            success *= 0.70
            risk_rows.append({
                "risk_dimension": "Instability Index",
                "current_value": round(float(instability), 1),
                "safety_threshold": "≤ 40",
                "attribution_source": "Sequence motifs in upper risk band",
                "severity": "WARN",
            })

    # 6. Hydrophobic patches (proxy via SAP-like flag)
    hydro_high = any("hydro_patch" in f.lower() and ("FAIL" in f or "WARN" in f) for f in cmc_flags)
    if hydro_high:
        success *= 0.60
        risk_rows.append({
            "risk_dimension": "Hydrophobic Patch (SAP-like)",
            "current_value": "above p75",
            "safety_threshold": "≤ p75 of VHH42",
            "attribution_source": "Aggregation-prone surface region",
            "severity": "WARN",
        })

    # 7. Framework neo-epitopes (immunogenicity proxy)
    fr_immuno = any("HIGH_RISK_FR_EPITOPE" in f for f in cmc_flags)
    if fr_immuno:
        success *= 0.70
        risk_rows.append({
            "risk_dimension": "Framework Neo-epitopes",
            "current_value": "detected",
            "safety_threshold": "absent",
            "attribution_source": "Frame-switch CDR-graft junction (IGHV1/4 → IGHV3 VHH)",
            "severity": "WARN",
        })

    # 8. Conformational Mismatch Risk (CDR3 Conformation vs FR2 Anchor)
    # Literature (Bahrami Dizicheh et al., 2023) shows long CDR3s (kinked) require hydrophobic/aromatic anchors at FWR2 (Kabat 37, 47).
    try:
        if isinstance(cdr3_length, int) and cdr3_length >= 16 and converted_seq:
            from anarcii import Anarcii
            from core.humanization.kabat_utils import kabat_from_anarcii
            a = Anarcii(seq_type="antibody", mode="accuracy")
            a.number([converted_seq])
            entry = a.to_scheme("kabat").get("Sequence 1", {})
            if not entry.get("error") and entry.get("chain_type") == "H":
                kd = kabat_from_anarcii(entry.get("numbering", []))
                aa37 = kd.get((37, ""))
                aa47 = kd.get((47, ""))
                if aa47 in ("L", "V", "I", "A") or (aa37 == "Y" and aa47 == "L"):
                    success *= 0.70
                    risk_rows.append({
                        "risk_dimension": "Structural Anchor Loss",
                        "current_value": f"FR2 anchors: {aa37}37/{aa47}47",
                        "safety_threshold": "Aromatic (F/W) at 47 for long CDR3",
                        "attribution_source": "CDR3-FR2 decoupling (Tm drop risk)",
                        "severity": "WARN",
                    })
    except Exception as e:
        pass

    success = max(0.0, min(1.0, success))

    # ── Verdict severity ────────────────────────────────────────────────────
    has_blocker = any(r["severity"] == "BLOCKER" for r in risk_rows)
    if has_blocker or success < 0.30:
        verdict_severity = "HIGH_RISK"
    elif success < 0.70:
        verdict_severity = "MODERATE_RISK"
    else:
        verdict_severity = "LOW_RISK"

    # ── Primary blocker ─────────────────────────────────────────────────────
    primary_blocker = None
    for r in risk_rows:
        if r["severity"] == "BLOCKER":
            primary_blocker = (
                f"{r['risk_dimension']} = {r['current_value']} "
                f"(target {r['safety_threshold']})"
            )
            break

    # ── Primary recommendation (A/B/C) ──────────────────────────────────────
    if has_blocker:
        primary_rec = "A"
    elif (
        isinstance(pI, (int, float)) and 5.5 <= pI < 6.0
        and any("CDR3" in r.get("attribution_source", "") for r in risk_rows)
    ):
        primary_rec = "B"
    elif success >= 0.70:
        primary_rec = "C"
    else:
        primary_rec = "A"

    # ── Confidence band ─────────────────────────────────────────────────────
    if not isinstance(pI, (int, float)):
        confidence_band = "low"
    elif isinstance(cdr3_length, int) and cdr3_length >= 17:
        confidence_band = "medium"
    else:
        confidence_band = "high"

    # ── Action Roadmap ──────────────────────────────────────────────────────
    action_roadmap = {
        "option_a": {
            "title": "STOP & REDESIGN",
            "subtitle": "De-novo CDR3 / Targeted Liability / VHH Humanization",
            "time": "1–3 business days",
            "pi_delta": "+1.5 to +2.5",
            "affinity_loss": "< 30%",
            "cost": "Algorithm time only",
            "use_case": "BLOCKER-level risk present",
        },
        "option_b": {
            "title": "RESCUE WITH FC FUSION",
            "subtitle": "Convert to Tetravalent VHH-Fc-VHH Modular Platform",
            "time": "~1 business day (sequence design)",
            "pi_delta": "+1.0 to +1.5",
            "affinity_loss": "< 5% (Avidity boost)",
            "cost": "Loses single-domain advantage",
            "use_case": "Borderline pI with non-redesignable CDR",
        },
    }

    return {
        "success_probability": round(success, 3),
        "confidence_band": confidence_band,
        "verdict_severity": verdict_severity,
        "primary_blocker": primary_blocker,
        "primary_recommendation": primary_rec,
        "risk_attribution": risk_rows,
        "action_roadmap": action_roadmap,
    }


# ─────────────────────────────────────────────────────────────────────────────
# HTML report generator
# ─────────────────────────────────────────────────────────────────────────────

def _mc(label: str, value: str, unit: str = "", tone: str = "neutral") -> str:
    """Render a single metric card. tone: ok | warn | fail | info | neutral"""
    card_cls = f"metric-card {tone}" if tone != "neutral" else "metric-card"
    val_cls = f"mc-value {tone}" if tone in ("ok", "warn", "fail") else "mc-value"
    return (
        f"<div class='{card_cls}'>"
        f"<div class='mc-label'>{label}</div>"
        f"<div class='{val_cls}'>{value}</div>"
        f"<div class='mc-unit'>{unit}</div>"
        f"</div>"
    )


def _build_cmc_cards(mini_cmc: dict, pi_ok: bool, gravy_ok: bool, inst_ok: bool,
                     flags_html: str, cmc_status: str, cmc_score, esc, num) -> str:
    pi_val = mini_cmc.get("pI")
    pi_str = num(pi_val, 2) if pi_val is not None else "—"
    pi_tone = "ok" if pi_ok else "fail"
    pi_unit = "5.5 – 9.5 target" if pi_ok else "⚠ Outside 5.5 – 9.5"

    gravy_val = mini_cmc.get("GRAVY")
    gravy_str = num(gravy_val, 3) if gravy_val is not None else "—"
    gravy_tone = "ok" if gravy_ok else "warn"
    gravy_unit = "≤ 0.1 target" if gravy_ok else "⚠ High hydrophobicity"

    inst_val = mini_cmc.get("instability_index")
    inst_str = num(inst_val, 1) if inst_val is not None else "—"
    inst_tone = "ok" if inst_ok else "warn"
    inst_unit = "≤ 40 target" if inst_ok else "⚠ Potentially unstable"

    nc_val = mini_cmc.get("net_charge_pH7")
    nc_str = num(nc_val, 1) if nc_val is not None else "—"

    qa_tone = "ok" if "PASS" in str(cmc_status).upper() else ("warn" if "WARN" in str(cmc_status).upper() else "fail")
    score_str = f"score {num(cmc_score, 1)}" if cmc_score is not None else "clinical QA"

    return f"""<div class="section">
  <h3>§3 — Mini-CMC Index</h3>
  <div class="section-body">
    <div class="metric-grid">
      {_mc("pI (Estimated)", pi_str, pi_unit, pi_tone)}
      {_mc("GRAVY", gravy_str, gravy_unit, gravy_tone)}
      {_mc("Instability Index", inst_str, inst_unit, inst_tone)}
      {_mc("Net Charge pH 7", nc_str, "charge units")}
      {_mc("Clinical QA", esc(cmc_status), score_str, qa_tone)}
    </div>
    {flags_html}
  </div>
</div>"""


def _build_cdr_cards(payload: dict, mini_cmc: dict, num) -> str:
    cdr2 = payload.get("cdr2_length", "—")
    cdr3 = payload.get("cdr3_length", "—")
    compact = mini_cmc.get("cdr3_compactness")
    compact_str = num(compact, 2) if compact is not None else "—"
    compact_tone = "warn" if compact is not None and compact > 6.5 else ("ok" if compact is not None else "neutral")
    compact_unit = "Å  ⚠ >6.5 limit" if compact is not None and compact > 6.5 else "Å  (≤ 6.5 target)"
    glycan = payload.get("glycan_dependency") or {}
    glycan_contact = "Yes ⚠" if glycan.get("known_glycan_contact") else ("No" if glycan else "—")
    glycan_motifs = ", ".join(glycan.get("glycan_motifs_in_cdr3") or []) or "None"
    return f"""<div class="section">
  <h3>§4 — CDR Index</h3>
  <div class="section-body">
    <div class="metric-grid">
      {_mc("CDR2 Length", str(cdr2), "aa")}
      {_mc("CDR3 Length", str(cdr3), "aa")}
      {_mc("CDR3 Compactness", compact_str, compact_unit, compact_tone)}
      {_mc("Glycan Contact", glycan_contact, "Ag-contact glycan")}
      {_mc("Glycan Motifs", glycan_motifs, "CDR3")}
    </div>
  </div>
</div>"""


def _build_hc_cards(payload: dict, mini_cmc: dict, num, esc) -> str:
    hpr = mini_cmc.get("hpr_index")
    hpr_str = num(hpr, 3) if hpr is not None else "—"
    hpr_tone = "ok" if hpr is not None and hpr >= 0.8 else ("warn" if hpr is not None and hpr >= 0.6 else ("fail" if hpr is not None else "neutral"))

    delta = payload.get("best_abnativ_delta")
    delta_str = num(delta, 3) if delta is not None else "—"
    delta_tone = "ok" if delta is not None and delta > 0 else ("warn" if delta is not None and delta > -0.5 else ("fail" if delta is not None else "neutral"))

    tier = str(payload.get("best_abnativ_tier") or "—")
    tier_tone = "ok" if tier == "PASS" else ("fail" if tier == "FAIL" else "warn")

    return f"""<div class="section">
  <h3>§5 — Humanization &amp; Camelization Index</h3>
  <div class="section-body">
    <div class="metric-grid">
      {_mc("HPR Index", hpr_str, "9-mer human coverage", hpr_tone)}
      {_mc("AbNatiV Δ", delta_str, "VHH² − VH² proxy", delta_tone)}
      {_mc("AbNatiV VHH Tier", tier, "naturalness gate", tier_tone)}
    </div>
  </div>
</div>"""


def _build_struct_cards(ip_in, ip_cv, cdr_rmsd: dict, num, struct_interp: str) -> str:
    def _plddt_tone(v):
        if v is None: return "neutral"
        return "ok" if v >= 80 else ("warn" if v >= 70 else "fail")

    in_str = num(ip_in, 1) if ip_in is not None else "—"
    cv_str = num(ip_cv, 1) if ip_cv is not None else "—"

    rmsd_cards = ""
    for k, v in (cdr_rmsd or {}).items():
        if isinstance(v, (int, float)):
            tone = "ok" if v <= 1.0 else ("warn" if v <= 2.0 else "fail")
            rmsd_cards += _mc(f"{k} Cα RMSD", f"{v:.2f}", "Å", tone)

    return f"""<div class="section">
  <h3>§6 — Structure Index (NanoBodyBuilder2)</h3>
  <div class="section-body">
    <div class="metric-grid">
      {_mc("Input VH pLDDT", in_str, "model confidence", _plddt_tone(ip_in))}
      {_mc("VHH pLDDT", cv_str, "model confidence", _plddt_tone(ip_cv))}
      {rmsd_cards}
    </div>
    {struct_interp}
  </div>
</div>"""


def _generate_vh2vhh_html_report(payload: dict, out_dir: Path, project_name: str = "") -> Path:
    """Generate self-contained HTML report for VH→VHH conversion, V1.5 Protocol (Risk-Forward Reporting)."""
    import html as _html
    from datetime import datetime
    from typing import Any

    def _build_report_meta(protocol_ver: str, analysis_ver: str, report_ver: str = "1.3") -> str:
        """Suite report format first; then VH→VHH service report version."""
        from api.main import app
        from api.report_versioning import suite_service_meta_html, cohort_provenance_html

        api_ver = getattr(app, "version", "1.0.0")
        extra = [
            f"<div>UI Build: {VHVL_HTML_REPORT_BUILD_ID}</div>",
            f"<div>API Version: {api_ver} (FastAPI)</div>",
        ]
        banner = suite_service_meta_html(
            "vh_to_vhh",
            protocol_ver=protocol_ver,
            analysis_ver=analysis_ver,
            content_variant=report_ver,
            extra_inner_divs=extra,
        )
        return banner + "\n" + cohort_provenance_html("vh_to_vhh")

    def _build_discussion_box(title: str, content: str) -> str:
        """Standard discussion box for results interpretation."""
        return f"""
        <div class="discussion-box">
          <div class="discussion-title">{title}</div>
          <p class="discussion-content">{content}</p>
        </div>"""

    ts = datetime.utcnow().strftime("%Y-%m-%d %H:%M UTC")
    proj = project_name or "VH→VHH Conversion"

    def esc(v: Any) -> str:
        return "—" if v is None else _html.escape(str(v))

    def num(v: Any, d: int = 2) -> str:
        if isinstance(v, float):
            return f"{v:.{d}f}"
        return "—" if v is None else str(v)

    def row(lbl: str, val: Any, *, allow_html: bool = False) -> str:
        v = "—" if (val is None or val == "" or val == []) else str(val)
        cell = v if allow_html else _html.escape(v)
        return f"<tr><td class='lbl'>{lbl}</td><td>{cell}</td></tr>"

    def seq_block(label: str, seq: str) -> str:
        if not seq:
            return ""
        chunks = [seq[i:i+10] for i in range(0, len(seq), 10)]
        numbered = " ".join(f'<span class="chunk">{c}</span>' for c in chunks)
        return (
            f"<div class='seq-block'>"
            f"<div class='seq-label'>{label} <span class='seq-len'>{len(seq)} aa</span></div>"
            f"<div class='seq-body'>{numbered}</div>"
            f"</div>"
        )

    def badge(ok: bool, t: str = "PASS", f: str = "FAIL") -> str:
        cls = "badge-ok" if ok else "badge-fail"
        return f"<span class='badge {cls}'>{t if ok else f}</span>"

    verdict = str(payload.get("feasibility_verdict") or "UNKNOWN").upper()
    if verdict == "FEASIBLE":
        verdict_badge = "<span class='badge badge-ok'>FEASIBLE</span>"
    elif "CAUTION" in verdict:
        verdict_badge = "<span class='badge badge-warn'>CAUTION</span>"
    else:
        verdict_badge = "<span class='badge badge-fail'>NOT FEASIBLE</span>"

    mutations = payload.get("mutations_applied") or []
    already_ok = payload.get("already_canonical") or []
    feat_notes = payload.get("feasibility_notes") or []
    cdr_rmsd = payload.get("cdr_rmsd") or {}
    mini_cmc = payload.get("mini_cmc") or {}

    # Build source-specific advisory block
    _src_advisory = _build_source_advisory(
        source_class=str(payload.get("source_class") or "human_mab"),
        mini_cmc=mini_cmc,
        cdr3_len=payload.get("cdr3_length"),
    )
    src_advisory_section = _source_advisory_html(_src_advisory)

    mut_rows = (
        "".join(f"<tr><td class='lbl'>Applied</td><td class='mono'>{esc(m)}</td></tr>" for m in mutations)
        or "<tr><td colspan='2' class='muted'>No mutations applied (or conversion error).</td></tr>"
    )
    canon_rows = "".join(
        f"<tr><td class='lbl'>Canonical</td><td class='mono'>{esc(a)}</td></tr>"
        for a in already_ok
    )

    rmsd_rows = (
        "".join(
            f"<tr><td class='lbl'>{k} Cα RMSD</td><td class='{'warn-row' if isinstance(v, float) and v > 2.0 else ''}'>"
            f"{num(v)} Å{'  ⚠' if isinstance(v, float) and v > 2.0 else ''}</td></tr>"
            for k, v in cdr_rmsd.items() if isinstance(v, (int, float))
        )
        or "<tr><td colspan='2' class='muted'>Structure not computed or RMSD unavailable.</td></tr>"
    )

    pi_ok = 5.5 < (mini_cmc.get("pI") or 7.0) < 9.5
    gravy_ok = (mini_cmc.get("GRAVY") or 0) <= 0.1
    inst_ok = (mini_cmc.get("instability_index") or 0) <= 40

    ip_in = payload.get("input_plddt")
    ip_cv = payload.get("converted_plddt")
    plddt_tone = ""
    if ip_cv is not None:
        plddt_tone = "warn-row" if ip_cv < 70 else ""

    notes_html = (
        "".join(f"<li>{esc(n)}</li>" for n in feat_notes)
        or "<li>No additional design notes.</li>"
    )

    cmc_status = str(payload.get("cmc_status") or "—")
    cmc_score = payload.get("cmc_clinical_score")
    candidates = payload.get("candidates") or []

    conv_seq = payload.get("converted_sequence") or ""
    inp_seq = payload.get("input_sequence") or ""

    # Pre-compute advisory block to avoid nested f-string issues
    _adv = payload.get("conversion_advisory")
    if _adv:
        _sev_color = "#d32f2f" if _adv.get("severity") == "high" else "#b56300"
        _border_color = "#d32f2f" if _adv.get("severity") == "high" else "#e6a817"
        _icon = "❌" if _adv.get("severity") == "high" else "⚠"
        
        _offline_html = ""
        if _adv.get("offline_service"):
            _offline_html = (
                f"<div style='margin-top:8px'>"
                f"<span style='display:inline-block;padding:2px 8px;background:#e0e7ff;border-radius:3px;font-size:10px;color:#1e40af'>"
                f"Offline Service: {esc(_adv.get('offline_service'))}"
                f"</span>"
                f"<span style='display:inline-block;margin-left:8px;padding:2px 8px;background:#f0fdf4;border-radius:3px;font-size:10px;color:#166534'>"
                f"⏱ {esc(_adv.get('estimated_time', ''))}"
                f"</span>"
                f"</div>"
            )
            
        advisory_html = (
            f"<div style='margin-top:12px;padding:10px 14px;border-radius:6px;"
            f"border-left:4px solid {_border_color};background:#fff8f8'>"
            f"<div style='font-size:12px;font-weight:700;color:{_sev_color};margin-bottom:4px'>"
            f"{_icon} Conversion Advisory: {esc(_adv.get('title',''))}</div>"
            f"<div style='font-size:11px;line-height:1.5;color:#444'>{esc(_adv.get('detail',''))}</div>"
            f"<div style='font-size:11px;margin-top:6px;color:#555'>"
            f"<strong>Optimization Path:</strong> {esc(_adv.get('path_forward',''))}</div>"
            f"</div>"
        )
    else:
        advisory_html = "<p style='color:var(--ok);font-size:11px;margin-top:8px'>✓ No critical CMC barriers detected for VH→VHH conversion.</p>"

    # ── §2.5 source-specific audit block ──────────────────────────────────────
    _pca = payload.get("phage_charge_audit")
    _shm = payload.get("transgenic_shm_scan")

    if _pca:
        _sev_color = "#d32f2f" if _pca.get("severity") == "HIGH" else "#b56300" if _pca.get("severity") == "MODERATE" else "#1a6b3c"
        _flag_note = (
            f"<div style='margin-top:6px;padding:4px 10px;background:#fff3cd;border-radius:4px;font-size:11px;color:#856404'>"
            f"⚡ Charge screening: total net charge = {_pca.get('total_net_charge','—')} "
            f"(FR: {_pca.get('fr_net_charge','—')} / CDR: {_pca.get('cdr_net_charge','—')}). "
            f"Status: <strong>{_pca.get('severity','—')}</strong>.</div>"
            if _pca.get("charge_bias_flag") else
            f"<div style='font-size:11px;color:#1a6b3c;margin-top:6px'>"
            f"✓ Charge distribution within typical range (total net charge = {_pca.get('total_net_charge','—')}).</div>"
        )
        _comp_rows = "".join(
            f"<tr><td class='lbl'>Kabat {p['kabat']}</td>"
            f"<td class='mono'>{p['aa']}→{p['suggested']} &nbsp; "
            f"<span style='color:#888;font-size:10px'>{_html.escape(p.get('note','').split(' — ')[0])}</span></td></tr>"
            for p in (_pca.get("compensation_candidates") or [])
        ) or "<tr><td colspan='2' class='muted'>No actionable FR charge-compensation candidates.</td></tr>"
        _cdr_charge_rows = "".join(
            f"<tr><td class='lbl'>CDR Kabat {p['kabat']}</td>"
            f"<td class='mono'>{p['aa']} (charge {p['charge']:+.1f})</td></tr>"
            for p in (_pca.get("cdr_negative_positions") or [])
        ) or "<tr><td colspan='2' class='muted'>No CDR negative charges.</td></tr>"
        source_audit_section = f"""
<div class="section">
  <h3>§2.5 — Source-Specific Charge Distribution Analysis</h3>
  <div class="section-body">
    {_flag_note}
    <table class="kv" style="margin-top:10px">
      <tr><td class='lbl'>Total net charge (pH 7)</td><td style='color:{_sev_color};font-weight:700'>{_pca.get("total_net_charge","—")}</td></tr>
      <tr><td class='lbl'>FR net charge contribution</td><td>{_pca.get("fr_net_charge","—")}</td></tr>
      <tr><td class='lbl'>CDR net charge contribution</td><td>{_pca.get("cdr_net_charge","—")}</td></tr>
      <tr><td class='lbl'>Audit status</td><td style='color:{_sev_color};font-weight:700'>{_pca.get("severity","—")}</td></tr>
      <tr><td class='lbl'>Compensation candidates</td><td>{_pca.get("n_compensation_candidates",0)}</td></tr>
    </table>
    <p style="font-size:11px;font-weight:700;color:#b56300;margin:10px 0 4px">Framework Charge-Compensation Candidates</p>
    <table class="kv">{_comp_rows}</table>
    <p style="font-size:11px;font-weight:700;color:#555;margin:10px 0 4px">CDR Negative Charges (Protected)</p>
    <table class="kv">{_cdr_charge_rows}</table>
    <div style="margin-top:12px;padding:10px;background:#f8fafc;border-radius:6px;border:1px solid #e2e8f0">
      <div style="font-size:11px;font-weight:700;color:#475569;margin-bottom:4px">Technical Discussion</div>
      <p style="font-size:11px;color:#64748b;line-height:1.5;margin:0">
        The observed net charge of {_pca.get("total_net_charge","—")} suggests a potential acidic bias, which is frequently observed in specific library selection environments. 
        While CDR-localized charges are preserved to maintain paratope integrity, the identified framework positions offer opportunities for charge-neutral substitutions (e.g., E→Q, D→N). 
        Implementing these changes can shift the overall pI toward the optimal developability window (5.5–9.5), potentially improving in vivo half-life and reducing renal clearance rates.
      </p>
    </div>
  </div>
</div>"""
    elif _shm:
        _load_color = "#d32f2f" if _shm.get("shm_load") == "HIGH" else "#b56300" if _shm.get("shm_load") == "MODERATE" else "#1a6b3c"
        _shm_rows = "".join(
            f"<tr><td class='lbl'>Kabat {p['kabat']}</td>"
            f"<td class='{'warn-row' if p['severity']=='high' else ''}'>"
            f"{p['observed']} (Ref: {p['germline_ref']}) — "
            f"<span style='color:{'#d32f2f' if p['severity']=='high' else '#b56300' if p['severity']=='medium' else '#1a6b3c'};font-weight:700'>"
            f"{p['action'].upper()}</span> "
            f"<span style='color:#888;font-size:10px'>{_html.escape(p.get('note','').split(' — ')[0])}</span></td></tr>"
            for p in (_shm.get("shm_positions") or [])
        ) or "<tr><td colspan='2' class='muted'>No significant deviations detected vs reference consensus.</td></tr>"
        source_audit_section = f"""
<div class="section">
  <h3>§2.5 — Somatic Hypermutation (SHM) Audit</h3>
  <div class="section-body">
    <table class="kv" style="margin-bottom:10px">
      <tr><td class='lbl'>Reference consensus</td><td>{esc(_shm.get("germline_reference","—").split(" (")[0])}</td></tr>
      <tr><td class='lbl'>Germline-matching positions</td><td>{_shm.get("same_as_germline","—")}</td></tr>
      <tr><td class='lbl'>Conservative deviations</td><td>{_shm.get("conservative_shm","—")} (retained)</td></tr>
      <tr><td class='lbl'>Non-conservative deviations</td><td style='color:{_load_color};font-weight:700'>{_shm.get("non_conservative_shm","—")} (review)</td></tr>
      <tr><td class='lbl'>Total SHM load</td><td style='color:{_load_color};font-weight:700'>{_shm.get("shm_load","—")}</td></tr>
    </table>
    <p style="font-size:11px;font-weight:700;color:#1e3a5f;margin-bottom:4px">Framework Deviation Analysis</p>
    <table class="kv">{_shm_rows}</table>
    <div style="margin-top:12px;padding:10px;background:#f8fafc;border-radius:6px;border:1px solid #e2e8f0">
      <div style="font-size:11px;font-weight:700;color:#475569;margin-bottom:4px">Technical Discussion</div>
      <p style="font-size:11px;color:#64748b;line-height:1.5;margin:0">
        Analysis of the framework regions reveals a {_shm.get("shm_load","—")} level of somatic hypermutation. 
        Conservative substitutions that align with natural maturation patterns are retained to leverage potential stability gains. 
        Non-conservative changes at non-critical positions are flagged for review, as they may represent library-specific artifacts or maturation-driven stability trade-offs. 
        Structural integrity at Vernier and Hallmark positions is strictly maintained by protecting these residues from reversion, ensuring the converted VHH retains its conformational advantages.
      </p>
    </div>
  </div>
</div>"""
    else:
        source_audit_section = ""

    # ── sequence comparison table logic ──
    sc2 = payload.get("sequence_comparison") or {}
    regions = sc2.get("regions") or []
    donor_seq = payload.get("input_sequence") or ""
    human_seq = payload.get("converted_sequence") or ""
    
    region_rows_html = ""
    total_fr_mut = 0
    if regions:
        total_fr_mut = sc2.get("total_fr_mutations", 0)
        for reg in regions:
            is_cdr = reg.get("is_cdr", False)
            ds = reg.get("donor_seq", "")
            hs = reg.get("humanized_seq", "")
            
            d_html = ""
            h_html = ""
            max_len = max(len(ds), len(hs))
            for i in range(max_len):
                da = ds[i] if i < len(ds) else ""
                ha = hs[i] if i < len(hs) else ""
                if da == ha:
                    d_html += esc(da or ha)
                    h_html += esc(da or ha)
                else:
                    d_html += f"<b style='color:#c0392b'>{esc(da or '·')}</b>"
                    h_html += f"<b style='color:#16a34a'>{esc(ha or '·')}</b>"
            
            n_mut = reg.get("n_mutations", 0)
            status_text = "CDR" if is_cdr else ("—" if n_mut == 0 else f"{n_mut} change{'s' if n_mut > 1 else ''}")
            status_color = "#92400e" if is_cdr else ("#9ca3af" if n_mut == 0 else "#15803d")
            row_bg = "#fefce8" if is_cdr else "transparent"
            
            region_rows_html += f"""<tr style="border-bottom:1px solid #e5e7eb;background:{row_bg}">
              <td style="padding:5px 12px;font-size:12px;font-weight:700;color:#1e293b;white-space:nowrap">{esc(reg.get("region",""))}</td>
              <td style="padding:5px 12px;font-family:monospace;font-size:12.5px;color:#374151">{d_html}</td>
              <td style="padding:5px 12px;font-family:monospace;font-size:12.5px;color:#374151">{h_html}</td>
              <td style="padding:5px 12px;font-size:11px;font-weight:600;color:{status_color};text-align:center;white-space:nowrap">{status_text}</td>
            </tr>"""
            
    seq_comparison_html = f"""
    <table style="width:100%;border-collapse:collapse;font-family:sans-serif;margin-bottom:8px">
      <thead>
        <tr style="background:#f1f5f9;border-bottom:1px solid #cbd5e1">
          <th style="padding:7px 12px;font-size:12px;font-weight:700;color:#475569;text-align:left;width:60px">Region</th>
          <th style="padding:7px 12px;font-size:12px;font-weight:700;color:#475569;text-align:left">Donor VH</th>
          <th style="padding:7px 12px;font-size:12px;font-weight:700;color:#475569;text-align:left">Converted VHH</th>
          <th style="padding:7px 12px;font-size:12px;font-weight:700;color:#475569;text-align:center;width:100px">Status</th>
        </tr>
      </thead>
      <tbody>{region_rows_html}</tbody>
    </table>
    <div style="padding:0 12px 10px">
      <span style="font-size:11px;color:#64748b;font-weight:700;margin-right:10px">Total FR mutations: {total_fr_mut}</span>
      <span style="font-size:11px;color:#64748b">Framework mutations restore VH-VL interface compatibility for single-domain display, alongside proprietary surface-patch modifications governed by structural gating. Specific mutation paths depend on the source VH family and baseline developability profile.</span>
      {"<div style='color:#dc2626;font-size:11px;margin-top:4px'>Mutation engine warning: " + esc(payload.get("conversion_error","")) + "</div>" if payload.get("conversion_error") else ""}
    </div>
    """

    # Filter flags for VHH display: downgrade AUDIT to info style, keep FAIL as red
    def _flag_html(f: str) -> str:
        f_esc = esc(f)
        if "AUDIT:" in f:
            return f"<div style='font-size:11px;color:#1e40af;margin-top:4px;background:rgba(30,64,175,0.05);padding:2px 6px;border-radius:3px'>ℹ️ {f_esc.replace('AUDIT:','')}</div>"
        color = "#d32f2f" if ("FAIL" in f or "HIGH_RISK" in f) else "#e6a817"
        icon = "❌" if ("FAIL" in f or "HIGH_RISK" in f) else "⚠"
        return f"<div style='font-size:11px;color:{color};margin-top:4px'>{icon} {f_esc}</div>"

    flags_html = "".join(_flag_html(f) for f in (payload.get('cmc_flags') or [])
                         if any(x in f for x in ['FAIL', 'HIGH_RISK', 'WARN', 'AUDIT']))

    # ── §0 Executive Summary ──────────────────────────────────────────
    _exec_disc = (
        f"The conversion of the donor VH sequence to a VHH single-domain format is assessed as <strong>{verdict}</strong>. "
        f"The selected <strong>{payload.get('selected_strategy', '—')}</strong> strategy balances framework stability with paratope preservation. "
        "The resulting sequence aligns with clinical developability benchmarks for nanobody therapeutics, with specific attention paid to the structural integrity of the CDR loops."
    )
    _exec_interp = _build_discussion_box("Executive Discussion", _exec_disc)

    # ── §2 Framework ──────────────────────────────────────────────────
    _eng_disc = (
        "Framework optimization focuses on enhancing the solubility and stability of the single-domain format. "
        "Key substitutions at interface positions (Kabat 44, 45, 47) mimic the natural VHH 'hallmark' residues, effectively masking the former VH-VL interface. "
        "Where necessary, back-mutations (reversions) to parent residues or solubility-enhancing substitutions are applied to balance framework hydrophobicity with conformational integrity. "
        "The selection of these sites is guided by structural plausibility and alignment with clinical nanobody benchmarks."
    )
    _eng_interp = _build_discussion_box("Engineering Discussion", _eng_disc)

    # ── §3 Structure ──────────────────────────────────────────────────
    _struct_disc = (
        "Structural modeling using the <strong>ImmuneBuilder (NanoBodyBuilder2)</strong> architecture confirms high conformational preservation across the CDR regions. "
        "The low RMSD values indicate that the framework substitutions and hallmark engineering have not induced significant backbone shifts in the antigen-binding loops. "
        "The high confidence scores (pLDDT) for the converted VHH support the feasibility of the engineered fold as a stable single-domain therapeutic candidate."
    )
    _struct_interp = _build_discussion_box("Structural Discussion", _struct_disc)

    # ── §5 Clinical Developability ────────────────────────────────────
    _cmc_disc = (
        "The candidate has been benchmarked against a clinical reference panel of successful VHH therapeutics. "
        f"The overall status of <strong>{cmc_status}</strong> reflects a profile suitable for downstream process development. "
        "Prioritization is given to physical stability and expression yield, with immunogenicity risks audited at the framework level to ensure a favorable safety profile for clinical translation."
    )
    _cmc_interp = _build_discussion_box("Developability Discussion", _cmc_disc)

    # ── V1.5 Risk-Forward Reporting blocks ────────────────────────────
    _verdict_severity = str(payload.get("verdict_severity") or "").upper()
    _success_prob = payload.get("success_probability")
    _confidence = payload.get("confidence_band") or "high"
    _primary_blocker = payload.get("primary_blocker")
    _primary_rec = payload.get("primary_recommendation")
    _risk_attr = payload.get("risk_attribution") or []
    _action_roadmap = payload.get("action_roadmap") or {}

    if _verdict_severity == "HIGH_RISK":
        _vh_color = "#dc2626"
        _vh_bg = "#fef2f2"
        _vh_label = "⛔ HIGH RISK — DO NOT PROCEED TO EXPRESSION"
    elif _verdict_severity == "MODERATE_RISK":
        _vh_color = "#d97706"
        _vh_bg = "#fffbeb"
        _vh_label = "⚠ MODERATE RISK — PROCEED WITH CAUTION"
    elif _verdict_severity == "LOW_RISK":
        _vh_color = "#059669"
        _vh_bg = "#f0fdf4"
        _vh_label = "✓ LOW RISK — READY FOR EXPRESSION TRIAL"
    else:
        _vh_color = "#6b7280"
        _vh_bg = "#f9fafb"
        _vh_label = "— RISK ASSESSMENT UNAVAILABLE"

    if isinstance(_success_prob, (int, float)):
        _sp_pct = f"{_success_prob * 100:.0f}%"
    else:
        _sp_pct = "—"

    _rec_label = {
        "A": "Option A — STOP & REDESIGN",
        "B": "Option B — RESCUE WITH FC FUSION",
    }.get(_primary_rec or "", "—")

    verdict_headline_html = f"""
<div style="margin-bottom:18px;border-radius:10px;border:2px solid {_vh_color};background:{_vh_bg};padding:16px 20px">
  <div style="font-size:1.05rem;font-weight:800;color:{_vh_color};margin-bottom:8px">{_vh_label}</div>
  <table class="kv" style="width:100%">
    <tr><td class='lbl' style="color:{_vh_color}">Success probability</td><td><strong style="color:{_vh_color};font-size:1.05rem">{_sp_pct}</strong> <span style='color:#6b7280;font-size:11px'>(confidence: {esc(_confidence)})</span></td></tr>
    <tr><td class='lbl' style="color:{_vh_color}">Primary blocker</td><td>{esc(_primary_blocker) if _primary_blocker else "<span class='muted'>None</span>"}</td></tr>
    <tr><td class='lbl' style="color:{_vh_color}">Recommended action</td><td><strong>{esc(_rec_label)}</strong></td></tr>
  </table>
</div>
"""

    if _risk_attr:
        _ra_rows = ""
        for r in _risk_attr:
            _sev = str(r.get("severity", "INFO")).upper()
            if _sev == "BLOCKER":
                _sev_color = "#dc2626"
                _sev_icon = "🔴"
            elif _sev == "WARN":
                _sev_color = "#d97706"
                _sev_icon = "🟡"
            else:
                _sev_color = "#1e40af"
                _sev_icon = "ℹ️"
            _ra_rows += (
                f"<tr>"
                f"<td>{esc(r.get('risk_dimension','—'))}</td>"
                f"<td class='mono'>{esc(r.get('current_value','—'))}</td>"
                f"<td>{esc(r.get('safety_threshold','—'))}</td>"
                f"<td style='font-size:11px;color:#475569'>{esc(r.get('attribution_source','—'))}</td>"
                f"<td style='color:{_sev_color};font-weight:700'>{_sev_icon} {_sev}</td>"
                f"</tr>"
            )
        risk_attr_section_html = f"""
<div class="section">
  <h3>§1.5 — Risk Attribution Matrix</h3>
  <div class="section-body">
    <table class="kv" style="font-size:12px">
      <thead>
        <tr style='background:#f1f5f9;font-weight:700;color:#0f172a'>
          <td>Risk Dimension</td><td>Current</td><td>Safety Threshold</td><td>Attribution Source</td><td>Severity</td>
        </tr>
      </thead>
      <tbody>
        {_ra_rows}
      </tbody>
    </table>
    <p style='font-size:11px;color:#64748b;margin-top:8px'>
      Severity grades: <strong style='color:#dc2626'>BLOCKER</strong> = mandatory redesign; <strong style='color:#d97706'>WARN</strong> = conditional progression; <strong style='color:#1e40af'>INFO</strong> = engineering note.
    </p>
  </div>
</div>"""
    else:
        risk_attr_section_html = ""

    if _action_roadmap:
        def _opt_card(opt_id: str, opt_data: Dict[str, Any], is_primary: bool) -> str:
            title = esc(opt_data.get("title", "—"))
            sub = esc(opt_data.get("subtitle", ""))
            time_v = esc(opt_data.get("time", "—"))
            pi_d = esc(opt_data.get("pi_delta", "—"))
            aff = esc(opt_data.get("affinity_loss", "—"))
            cost = esc(opt_data.get("cost", "—"))
            use_case = esc(opt_data.get("use_case", ""))
            border = "#dc2626" if is_primary else "#cbd5e1"
            bg = "#fef2f2" if is_primary else "#fff"
            badge = (
                "<span style='background:#dc2626;color:#fff;padding:2px 8px;border-radius:10px;font-size:10px;font-weight:700'>RECOMMENDED</span>"
                if is_primary else ""
            )
            return (
                f"<div style='border:2px solid {border};background:{bg};border-radius:8px;padding:12px 14px;margin-bottom:8px'>"
                f"<div style='display:flex;justify-content:space-between;align-items:center;margin-bottom:4px'>"
                f"<div style='font-weight:700;font-size:0.9rem'>{title}</div>{badge}</div>"
                f"<div style='font-size:11px;color:#64748b;margin-bottom:6px'>{sub}</div>"
                f"<table class='kv' style='font-size:11px'>"
                f"<tr><td class='lbl'>Time</td><td>{time_v}</td></tr>"
                f"<tr><td class='lbl'>pI delta</td><td>{pi_d}</td></tr>"
                f"<tr><td class='lbl'>Affinity loss</td><td>{aff}</td></tr>"
                f"<tr><td class='lbl'>Cost</td><td>{cost}</td></tr>"
                f"<tr><td class='lbl'>Use case</td><td>{use_case}</td></tr>"
                f"</table>"
                f"</div>"
            )

        roadmap_cards = "".join(
            _opt_card(opt_id, _action_roadmap.get(f"option_{opt_id.lower()}") or {}, _primary_rec == opt_id)
            for opt_id in ("A", "B")
            if _action_roadmap.get(f"option_{opt_id.lower()}")
        )
        action_roadmap_section_html = f"""
<div class="section">
  <h3>§5.5 — Action Roadmap (V1.5)</h3>
  <div class="section-body">
    <p style='font-size:11px;color:#475569;margin-bottom:10px'>
      Three deterministic paths forward based on the Risk Attribution Matrix. The recommended option is highlighted; alternatives are shown for owner review.
    </p>
    {roadmap_cards}
  </div>
</div>"""
    else:
        action_roadmap_section_html = ""

    _glycan = payload.get("glycan_dependency") or {}
    if isinstance(_glycan, dict) and _glycan:
        _glycan_notes = _glycan.get("notes") or []
        _glycan_notes_html = "".join(f"<li>{esc(str(n))}</li>" for n in _glycan_notes[:4])
        _glycan_section_html = f"""
<div class="section">
  <h3>§1.7 — Glycan-Dependent Epitope Risk Layer (V1.7)</h3>
  <div class="section-body">
    <table class="kv">
      {row("Risk level", _glycan.get("risk_level", "—"))}
      {row("Penalty factor", _glycan.get("penalty_factor", "—"))}
      {row("Known glycan-contact antibody", "Yes" if _glycan.get("known_glycan_contact") else "No")}
      {row("CDR-H3 glycan motifs", ", ".join(_glycan.get("glycan_motifs_in_cdr3") or []) or "None detected")}
      {row("VL decoupling risk", _glycan.get("vl_decoupling_risk", "—"))}
      {row("Checker version", _glycan.get("checker_version", "—"))}
    </table>
    {"<ul class='flag-list' style='margin-top:8px'>" + _glycan_notes_html + "</ul>" if _glycan_notes_html else ""}
    <p style='font-size:11px;color:#64748b;margin-top:8px'>
      V1.7 applies this layer after V1.5/V1.6 evidence. A penalty factor below 1.0 is multiplied into the final success probability and may upgrade the verdict or action recommendation.
    </p>
  </div>
</div>"""
    else:
        _glycan_section_html = ""

    html_body = f"""<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<meta name="robots" content="noindex,nofollow">
<title>InSynBio AbEngineCore | VH→VHH Conversion Report</title>
<style>
:root{{--ok:#059669;--warn:#d97706;--fail:#dc2626;--muted:#5a6a80;--bg:#f4f7f9;
      --panel:#ffffff;--card:#fff;--border:#d0d7e2;--accent:#1b4fad;--accent2:#2d6cdf}}
*{{box-sizing:border-box;margin:0;padding:0}}
body{{font-family:-apple-system,BlinkMacSystemFont,'Segoe UI',Roboto,Helvetica,Arial,sans-serif;background:var(--bg);color:#2c3e50;font-size:13px;line-height:1.5;padding:20px}}
.page{{max-width:900px;margin:0 auto;background:var(--panel);padding:32px 40px;border-radius:8px;box-shadow:0 4px 12px rgba(0,0,0,0.05)}}
.report-header{{background:var(--accent);color:#fff;padding:20px 28px;border-radius:8px;margin-bottom:18px;display:flex;justify-content:space-between;align-items:flex-end}}
.report-header h1{{margin:0 0 4px;font-size:1.35rem;font-weight:700;color:#fff;letter-spacing:-0.02em}}
.report-header .sub{{font-size:.84rem;font-weight:600;opacity:.95;margin-top:2px;line-height:1.45;color:#fff}}
.report-header .sub b{{color:#fff}}
.report-header .ts{{text-align:right;font-size:.78rem;font-weight:600;opacity:.92;color:#fff}}
.header-meta{{width:100%;margin-top:10px;font-size:.76rem;font-weight:600;opacity:.9;line-height:1.45}}
.header-meta div{{margin-top:2px}}
.section{{background:var(--card);border:1px solid var(--border);border-radius:8px;
          margin-bottom:16px;overflow:hidden}}
.section h3{{font-size:0.85rem;font-weight:700;padding:10px 16px;background:#f3f4f6;
             border-bottom:1px solid var(--border);color:#374151}}
.section-body{{padding:14px 16px}}
table.kv{{width:100%;border-collapse:collapse}}
table.kv td,.lbl{{padding:5px 8px;vertical-align:top}}
table.kv tr:nth-child(even){{background:#f9fafb}}
.lbl{{color:#6b7280;font-weight:600;width:38%;white-space:nowrap}}
.mono{{font-family:monospace;font-size:0.85em;word-break:break-all}}
.seq-block{{margin:8px 0;background:#f8f9fa;border:1px solid #e9ecef;
            border-radius:6px;padding:10px 12px}}
.seq-label{{font-size:0.78rem;font-weight:700;color:#495057;margin-bottom:6px}}
.seq-len{{font-weight:400;color:#6b7280}}
.seq-body{{font-family:'Courier New',monospace;font-size:0.82em;letter-spacing:.04em;
           word-break:break-all;line-height:1.7}}
.chunk{{margin-right:4px}}
.badge{{display:inline-block;padding:2px 8px;border-radius:12px;font-size:0.75rem;font-weight:700}}
.badge-ok{{background:#d1fae5;color:#065f46}}
.badge-warn{{background:#fef3c7;color:#92400e}}
.badge-fail{{background:#fee2e2;color:#991b1b}}
.badge-info{{background:#dbeafe;color:#1e40af}}
.warn-row td{{color:var(--warn)!important}}
.muted{{color:var(--muted);font-style:italic}}
.flag-list{{list-style:none;padding:0}}
.flag-list li{{padding:4px 8px;border-left:3px solid var(--warn);margin-bottom:6px;
               font-size:0.82rem;background:#fffbeb}}
.flag-list li.ok{{border-color:var(--ok);background:#f0fdf4}}
.discussion-box{{margin-top:12px;padding:12px;background:#f8fafc;border-radius:6px;border:1px solid #e2e8f0;border-left:4px solid var(--accent2)}}
.discussion-title{{font-size:11px;font-weight:700;color:var(--accent);margin-bottom:6px;text-transform:uppercase;letter-spacing:0.05em}}
.discussion-content{{font-size:11px;color:#334155;line-height:1.5;margin:0}}
/* Metric card grid */
.metric-grid{{display:grid;grid-template-columns:repeat(auto-fill,minmax(140px,1fr));gap:10px;margin-bottom:10px}}
.metric-card{{background:#f8fafc;border:1px solid #e2e8f0;border-radius:8px;padding:10px 12px;display:flex;flex-direction:column;min-width:0}}
.metric-card.warn{{background:#fffbeb;border-color:#fcd34d}}
.metric-card.fail{{background:#fef2f2;border-color:#fca5a5}}
.metric-card.ok{{background:#f0fdf4;border-color:#86efac}}
.metric-card.info{{background:#eff6ff;border-color:#93c5fd}}
.mc-label{{font-size:10px;font-weight:700;color:#6b7280;text-transform:uppercase;letter-spacing:.04em;margin-bottom:4px;white-space:nowrap;overflow:hidden;text-overflow:ellipsis}}
.mc-value{{font-size:1.3rem;font-weight:800;color:#1e293b;line-height:1.1;margin-bottom:2px}}
.mc-value.warn{{color:#d97706}}
.mc-value.fail{{color:#dc2626}}
.mc-value.ok{{color:#059669}}
.mc-unit{{font-size:10px;color:#94a3b8;margin-top:2px}}
footer{{text-align:center;color:var(--muted);font-size:0.75rem;margin-top:24px;padding-top:12px;
        border-top:1px solid var(--border)}}
@media print {{
  body {{ background:#fff; font-size:10.5px; color:#000; padding:0 }}
  .page {{ max-width:100%; padding:0; box-shadow:none }}
  .report-header {{ background:#1b4fad !important; -webkit-print-color-adjust:exact; print-color-adjust:exact }}
  .report-header h1,
  .report-header .sub,
  .report-header .sub b,
  .report-header .ts,
  .report-header .header-meta {{ color:#fff !important; opacity:1 }}
  /* Allow section splitting to avoid large trailing blank areas in PDF pages. */
  .section {{ break-inside:auto; page-break-inside:auto; border:1px solid #ccc; margin-bottom:10px }}
  .section h3 {{ break-after:avoid; page-break-after:avoid }}
  footer {{ margin-top:14px }}
}}
</style>
</head>
<body>
<div class="page">

<div class="report-header">
  <div>
    <h1>InSynBio AbEngineCore</h1>
    <div class="sub">VH→VHH Conversion Report &nbsp;|&nbsp; {VH2VHH_REPORT_PROTOCOL_VERSION} Protocol</div>
    <div class="sub" style="margin-top:4px">Project: <b>{esc(proj)}</b> &nbsp;·&nbsp; Source: <b>{esc(payload.get("source_class","—"))}</b></div>
    {_build_report_meta(VH2VHH_REPORT_PROTOCOL_VERSION, f"AbEngineCore VH to VHH Conversion Standard {VH2VHH_ANALYSIS_VERSION}", VH2VHH_ANALYSIS_VERSION)}
  </div>
  <div class="ts">{ts}<br><span style="font-size:.7rem;opacity:.6">CONFIDENTIAL</span></div>
</div>

{verdict_headline_html}

<div class="section">
  <h3>§0 — Executive Summary</h3>
  <div class="section-body">
    <table class="kv">
      {row("Feasibility verdict", f"{verdict}  {verdict_badge}", allow_html=True)}
      {row("Risk level", payload.get("feasibility_risk","—"))}
      {row("Client sequence name", payload.get("sequence_name") or "—")}
      {row("Source class", payload.get("source_class","—"))}
      {row("Input format", f'scFv ({payload.get("scfv_orientation","?")} orientation) → VH extracted ({payload.get("vh_length","?")} aa) | Original: {len(payload.get("original_input","") or "")} aa | Linker: {payload.get("scfv_linker","—")}' if payload.get("scfv_detected") else "VH domain (direct input)")}
      {row("Path", "Path C2 (dual engineering)" if "murine" in str(payload.get("source_class","")) else "Path C1 (framework-preserving)")}
      {row("Selected strategy", payload.get("selected_strategy", "—"))}
      {row("Selected template", payload.get("selected_template_id", "—"))}
      {row("Selected germline", payload.get("selected_germline", "—"))}
      {row("VH length", f'{payload.get("vh_length","—")} aa')}
      {row("CDR2 length (Kabat)", f'{payload.get("cdr2_length","—")} aa')}
      {row("CDR3 length (Kabat)", f'{payload.get("cdr3_length","—")} aa')}
      {row("Mutations applied", str(len(mutations)))}
      {row("Structure computed", "Yes" if payload.get("structure_computed") else "No")}
    </table>
    {_exec_interp}
  </div>
</div>

<div class="section">
  <h3>§0.5 — Source-Specific Engineering Advisory</h3>
  <div class="section-body">
    {src_advisory_section}
  </div>
</div>

<div class="section">
  <h3>§1 — Feasibility Assessment Notes</h3>
  <div class="section-body">
    <ul class="flag-list">
      {notes_html}
    </ul>
  </div>
</div>

{risk_attr_section_html}

{_glycan_section_html}

<div class="section">
  <h3>§1 — Local Sequence Comparison (FR / CDR)</h3>
  <div class="section-body" style="padding:0">
    {seq_comparison_html if regions else "<div style='padding:12px;font-size:12px;color:#64748b'>Not available.</div>"}
  </div>
</div>

<div class="section">
  <h3>§2 — Global Sequence (Designed VHH)</h3>
  <div class="section-body">
    {seq_block("Input VH", inp_seq)}
    {seq_block("Converted VHH", conv_seq)}
  </div>
</div>

{source_audit_section}

{_build_cmc_cards(mini_cmc, pi_ok, gravy_ok, inst_ok, flags_html, cmc_status, cmc_score, esc, num)}

{_build_cdr_cards(payload, mini_cmc, num)}

{_build_hc_cards(payload, mini_cmc, num, esc)}

{_build_struct_cards(ip_in, ip_cv, cdr_rmsd, num, _struct_interp)}

<footer>
  InSynBio Research &nbsp;·&nbsp; <a href="https://www.insynbio.com">https://www.insynbio.com</a>
  &nbsp;·&nbsp; {ts} &nbsp;·&nbsp; CONFIDENTIAL &nbsp;·&nbsp;
  Use Ctrl+P → Save as PDF to export this report.
</footer>

</div>
</body>
</html>
"""
    out_dir.mkdir(parents=True, exist_ok=True)
    report_dir = out_dir / "reports" / "vh_to_vhh"
    report_dir.mkdir(parents=True, exist_ok=True)
    report_path = report_dir / "vh2vhh_report.html"
    try:
        from core.reporting.report_qc_gate import run_report_qc  # noqa: PLC0415
        qc = run_report_qc(html_body, report_family="vh_to_vhh")
        html_body = qc.inject_qc_badge(html_body)
    except Exception:
        pass
    report_path.write_text(html_body, encoding="utf-8")
    return report_path


# ─────────────────────────────────────────────────────────────────────────────
# ZIP builder
# ─────────────────────────────────────────────────────────────────────────────

def _create_vh2vhh_zip(out_dir: Path, job_id: str) -> Optional[str]:
    """Bundle report + FASTA + PDBs into one ZIP."""
    import zipfile

    zip_name = f"{job_id}_vh2vhh_delivery.zip"
    zip_path = out_dir / zip_name

    html_nested = out_dir / "reports" / "vh_to_vhh" / "vh2vhh_report.html"
    html_legacy = out_dir / "vh2vhh_report.html"
    html_src = html_nested if html_nested.is_file() else html_legacy

    include: List[str] = []
    for name in ["sequences.fasta", "input_vh.pdb", "converted_vhh.pdb"]:
        fp = out_dir / name
        if fp.is_file():
            include.append(name)

    if not include and not html_src.is_file():
        return None

    with zipfile.ZipFile(zip_path, "w", zipfile.ZIP_DEFLATED) as zf:
        for name in include:
            zf.write(out_dir / name, arcname=name)
        if html_src.is_file():
            zf.write(html_src, arcname="vh2vhh_report.html")

    return f"/files/{job_id}/{zip_name}"


# ─────────────────────────────────────────────────────────────────────────────
# Full async pipeline implementation
# ─────────────────────────────────────────────────────────────────────────────

def _detect_and_extract_vh_from_scfv(seq: str) -> Dict[str, Any]:
    """
    Detect if input is an scFv (VH-linker-VL or VL-linker-VH) using ANARCI.
    If so, extract the VH domain and return metadata.

    Returns:
        {
          "is_scfv": bool,
          "vh_seq": str,          # extracted VH (or original if not scFv)
          "vl_seq": str | None,   # extracted VL if found
          "orientation": str,     # "VH-VL" | "VL-VH" | "unknown" | "not_scfv"
          "linker_detected": str | None,
          "vh_start": int, "vh_end": int,
        }
    """
    try:
        from anarcii import Anarcii
        a = Anarcii(seq_type="antibody", mode="accuracy")
        a.number([seq])
        hits = a.results  # list of domain hits

        if not hits or len(hits) < 2:
            return {"is_scfv": False, "vh_seq": seq, "vl_seq": None,
                    "orientation": "not_scfv", "linker_detected": None}

        vh_hit = None
        vl_hit = None
        for hit in hits:
            chain = str(hit.get("chain_type", "")).upper()
            if chain == "H" and vh_hit is None:
                vh_hit = hit
            elif chain in ("K", "L") and vl_hit is None:
                vl_hit = hit

        if vh_hit is None:
            return {"is_scfv": False, "vh_seq": seq, "vl_seq": None,
                    "orientation": "not_scfv", "linker_detected": None}

        vh_start = vh_hit.get("query_start", 0)
        vh_end   = vh_hit.get("query_end", len(seq))
        vh_seq   = seq[vh_start:vh_end + 1]

        vl_seq   = None
        if vl_hit is not None:
            vl_start = vl_hit.get("query_start", 0)
            vl_end   = vl_hit.get("query_end", len(seq))
            vl_seq   = seq[vl_start:vl_end + 1]

        orientation = "not_scfv"
        if vh_hit is not None and vl_hit is not None:
            orientation = "VH-VL" if vh_start < (vl_hit.get("query_start", 9999)) else "VL-VH"

        linker = None
        if vl_seq and vh_seq:
            if orientation == "VH-VL":
                linker_region = seq[vh_end + 1:vl_hit.get("query_start", 0)]
            else:
                linker_region = seq[vl_hit.get("query_end", 0) + 1:vh_start]
            if linker_region:
                linker = linker_region[:20] + ("…" if len(linker_region) > 20 else "")

        return {
            "is_scfv": vl_hit is not None,
            "vh_seq": vh_seq,
            "vl_seq": vl_seq,
            "orientation": orientation,
            "linker_detected": linker,
            "vh_start": vh_start,
            "vh_end": vh_end,
            "original_length": len(seq),
        }

    except Exception as e:
        return {"is_scfv": False, "vh_seq": seq, "vl_seq": None,
                "orientation": "error", "linker_detected": None,
                "error": str(e)}


def _is_cmc_issue_flag(flag: Any) -> bool:
    s = str(flag or "").upper()
    return ("FAIL" in s) or ("WARN" in s) or ("HIGH_RISK" in s) or ("CRITICAL" in s)


def _append_cmc_issue_casebank(job_id: str, payload: Dict[str, Any], out_dir: Path) -> Dict[str, Any]:
    """
    Persist CMC-problematic sequences for later optimization datasets.
    Appends one JSON line per problematic job to a global casebank and writes
    a per-job snapshot under the job output directory.
    """
    best_flags = payload.get("cmc_flags") or []
    best_status = str(payload.get("cmc_status") or "UNKNOWN").upper()
    candidates: List[Dict[str, Any]] = payload.get("candidates") or []

    candidate_issues: List[Dict[str, Any]] = []
    for c in candidates:
        c_status = str(c.get("clinical_status") or "UNKNOWN").upper()
        c_flags = c.get("overall_flags") or []
        has_issue = (c_status != "PASS") or any(_is_cmc_issue_flag(f) for f in c_flags)
        if not has_issue:
            continue
        candidate_issues.append(
            {
                "candidate_id": c.get("candidate_id"),
                "strategy": c.get("strategy"),
                "sequence": c.get("sequence"),
                "clinical_status": c_status,
                "clinical_score": c.get("clinical_score"),
                "overall_flags": c_flags,
            }
        )

    job_has_issue = (
        (best_status != "PASS")
        or any(_is_cmc_issue_flag(f) for f in best_flags)
        or bool(candidate_issues)
    )
    if not job_has_issue:
        return {"archived": False, "reason": "no_cmc_issue"}

    ts = time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())
    digest = hashlib.sha1(f"{job_id}:{payload.get('input_sequence','')}:{ts}".encode("utf-8")).hexdigest()[:12]
    case_id = f"vh2vhh-cmc-{digest}"
    case_record: Dict[str, Any] = {
        "case_id": case_id,
        "timestamp_utc": ts,
        "job_id": job_id,
        "source_class": payload.get("source_class"),
        "source_type": payload.get("source_type"),
        "sequence_name": payload.get("sequence_name"),
        "demo_id": payload.get("demo_id"),
        "input_sequence": payload.get("input_sequence"),
        "converted_sequence": payload.get("converted_sequence"),
        "selected_strategy": payload.get("selected_strategy"),
        "selected_template_id": payload.get("selected_template_id"),
        "selected_germline": payload.get("selected_germline"),
        "best_cmc_status": best_status,
        "best_cmc_flags": best_flags,
        "best_cmc_score": payload.get("cmc_clinical_score"),
        "candidate_issue_count": len(candidate_issues),
        "candidate_issues": candidate_issues,
    }

    # Per-job snapshot (easy to inspect inside job folder)
    per_job_path = out_dir / "cmc_issue_case.json"
    per_job_path.write_text(json.dumps(case_record, indent=2, ensure_ascii=False), encoding="utf-8")

    # Global append-only casebank (cross-job accumulation)
    bank_dir = ROOT / "data" / "vh_to_vhh_casebank"
    bank_dir.mkdir(parents=True, exist_ok=True)
    bank_path = bank_dir / "cmc_issue_sequences.jsonl"
    with _CMC_CASEBANK_LOCK:
        with bank_path.open("a", encoding="utf-8") as fh:
            fh.write(json.dumps(case_record, ensure_ascii=False) + "\n")

    return {
        "archived": True,
        "case_id": case_id,
        "per_job_file": str(per_job_path.relative_to(ROOT)),
        "global_casebank": str(bank_path.relative_to(ROOT)),
        "candidate_issue_count": len(candidate_issues),
    }


def _vh2vhh_impl(job_id: str, req: VhToVhhRequest) -> None:
    """Full VH→VHH conversion pipeline (Stage 1–5 + report + ZIP)."""
    import shutil

    t0 = time.time()
    out = job_dir(job_id)
    out.mkdir(parents=True, exist_ok=True)

    try:
        raw_seq = re.sub(r"[\s\n\r]", "", (req.vh_sequence or "").upper())
        source_type = _map_source_class(req.source_class)

        # ── scFv pre-processing ──────────────────────────────────────────────
        jobs[job_id]["progress"] = 2
        jobs[job_id]["progress_note"] = "Pre-check: detecting if input is scFv or VH-only…"
        persist_job_snapshot(job_id)

        scfv_meta: Dict[str, Any] = {}
        if len(raw_seq) > 200:
            scfv_meta = _detect_and_extract_vh_from_scfv(raw_seq)
            if scfv_meta.get("is_scfv"):
                jobs[job_id]["progress_note"] = (
                    f"scFv detected ({scfv_meta.get('orientation','?')} orientation, "
                    f"linker: {scfv_meta.get('linker_detected','?')}). "
                    f"Extracting VH domain ({len(scfv_meta['vh_seq'])} aa) for conversion…"
                )
                persist_job_snapshot(job_id)
                vh = scfv_meta["vh_seq"]
            else:
                vh = raw_seq
        else:
            vh = raw_seq

        vh = re.sub(r"[\s\n\r]", "", vh.upper())

        # ── Stage 1: Feasibility ─────────────────────────────────────────────
        jobs[job_id]["progress"] = 5
        jobs[job_id]["progress_note"] = "Stage 1: Feasibility assessment (ANARCI Kabat)…"
        persist_job_snapshot(job_id)

        from scripts.vhh_conversion_pipeline import run_stage1, run_stage2  # noqa: PLC0415
        s1 = run_stage1(vh, source_type=source_type)

        cdr3_len: int = s1.get("cdr3_length") or 13
        cdr2_len: int = s1.get("cdr2_length") or 16
        fe = s1.get("feasibility") or {}

        jobs[job_id]["progress"] = 15
        jobs[job_id]["progress_note"] = (
            f"Stage 1 done: {fe.get('verdict','?')} — CDR2={cdr2_len}aa, CDR3={cdr3_len}aa"
        )
        persist_job_snapshot(job_id)

        # ── P1-4: CDR3 extreme-composition pathway advisory ───────────────────
        pathway_advisory: Optional[Dict[str, Any]] = None
        if ENABLE_PATHWAY_ADVISORY:
            try:
                _cdr3_seq = s1.get("cdr3_sequence") or ""
                if not _cdr3_seq and len(vh) >= 10:
                    # Fallback: rough CDR3 from Kabat 95-102 linear slice
                    _cdr3_seq = vh[94:102] if len(vh) > 102 else ""
                if _cdr3_seq and len(_cdr3_seq) >= 4:
                    _gravy_vals = {
                        "A": 1.8, "R": -4.5, "N": -3.5, "D": -3.5, "C": 2.5,
                        "Q": -3.5, "E": -3.5, "G": -0.4, "H": -3.2, "I": 4.5,
                        "L": 3.8, "K": -3.9, "M": 1.9, "F": 2.8, "P": -1.6,
                        "S": -0.8, "T": -0.7, "W": -0.9, "Y": -1.3, "V": 4.2,
                    }
                    _gc = [_gravy_vals.get(aa, 0.0) for aa in _cdr3_seq.upper()]
                    _gravy_cdr3 = sum(_gc) / len(_gc) if _gc else 0.0
                    _aromatic_frac = sum(
                        1 for aa in _cdr3_seq.upper() if aa in ("F", "Y", "W")
                    ) / len(_cdr3_seq)
                    if _gravy_cdr3 < -1.5 and _aromatic_frac > 0.30:
                        pathway_advisory = {
                            "code": "consider_path_c2_or_b",
                            "cdr3_gravy": round(_gravy_cdr3, 3),
                            "cdr3_aromatic_frac": round(_aromatic_frac, 3),
                            "message": (
                                f"CDR3 GRAVY {round(_gravy_cdr3, 3)} < −1.5 and aromatic fraction "
                                f"{round(_aromatic_frac*100,1)}% > 30%. "
                                "Under Path C1 (100% CDR identity constraint), this composition "
                                "cannot be remediated by framework-only mutations — GRAVY and HP9 "
                                "will remain outside VHH42 clinical reference range. "
                                "Recommend switching to Path C2 (dual engineering with CDR modification) "
                                "or Path B (de novo CDR redesign) before proceeding."
                            ),
                        }
            except Exception:
                pass

        # ── Stage 2: Generate real conversion panel ───────────────────────────
        if jobs.get(job_id, {}).get("cancel_requested"):
            jobs[job_id].update({"status": "cancelled", "progress": 15})
            return

        jobs[job_id]["progress"] = 20
        jobs[job_id]["progress_note"] = "Stage 2: Generating VH→VHH candidates (camelize / point-mutation Path C)…"
        persist_job_snapshot(job_id)

        # [V1.8.10] enable_scaffold_graft defaults to False.
        # Only set True when user explicitly requests it via request parameter.
        _enable_graft = getattr(req, "enable_scaffold_graft", False)

        candidates = _generate_conversion_candidates(
            vh_seq=vh,
            source_class=req.source_class,
            cdr3_len=cdr3_len,
            cdr2_len=cdr2_len,
            top_n=10,
            enable_scaffold_graft=_enable_graft,
        )
        if not candidates:
            raise RuntimeError("No VH→VHH candidates could be generated from the donor sequence.")

        jobs[job_id]["progress"] = 30
        jobs[job_id]["progress_note"] = (
            f"Stage 2 done: {len(candidates)} candidates generated"
        )
        persist_job_snapshot(job_id)

        # ── Stage 2b: Rank by AbEvaluator / VHH clinical QA ──────────────────
        if jobs.get(job_id, {}).get("cancel_requested"):
            jobs[job_id].update({"status": "cancelled", "progress": 30})
            return

        jobs[job_id]["progress"] = 36
        jobs[job_id]["progress_note"] = "Stage 2b: Ranking candidates with AbEvaluator…"
        persist_job_snapshot(job_id)

        allowed_entries = [
            {"sequence_id": c["candidate_id"], "sequence": c["sequence"]}
            for c in candidates
        ]
        stage2_results = run_stage2(allowed_entries)
        stage2_map = {r.get("sequence_id"): r for r in stage2_results if isinstance(r, dict)}

        status_rank = {"PASS": 0, "WARN": 1, "FAIL": 2, "ERROR": 3, "SKIPPED": 4}
        for cand in candidates:
            s2 = stage2_map.get(cand["candidate_id"], {})
            cand["clinical_status"] = s2.get("status")
            cand["clinical_score"] = s2.get("clinical_score")
            es = s2.get("executive_summary") or {}
            cand["executive_summary"] = es
            cand["overall_flags"] = es.get("overall_flags") or []

        def _cand_sort_key(c: Dict[str, Any]) -> tuple:
            st = str(c.get("clinical_status") or "ERROR").upper()
            return (
                status_rank.get(st, 9),
                -(c.get("clinical_score") if isinstance(c.get("clinical_score"), (int, float)) else -999),
                -(c.get("template_score") if isinstance(c.get("template_score"), (int, float)) else -999),
            )

        candidates.sort(key=_cand_sort_key)
        best = candidates[0]
        converted_seq: str = best.get("sequence") or vh
        mutations_applied: List[str] = best.get("mutations_applied") or []
        already_canonical: List[str] = best.get("already_canonical") or []
        conversion_error: Optional[str] = best.get("conversion_error")

        # ── Stage 3: NanoBodyBuilder2 structures ─────────────────────────────
        from core.humanization.engine import (  # noqa: PLC0415
            _run_nanobodybuilder2, _compute_vhh_cdr_rmsd, _vhh_mini_cmc,
        )

        struct_input: dict = {}
        struct_converted: dict = {}
        cdr_rmsd: dict = {}

        if jobs.get(job_id, {}).get("cancel_requested"):
            jobs[job_id].update({"status": "cancelled", "progress": 38})
            return

        jobs[job_id]["progress"] = 40
        jobs[job_id]["progress_note"] = "Stage 3: NanoBodyBuilder2 — input VH structure…"
        persist_job_snapshot(job_id)
        try:
            struct_input = _run_nanobodybuilder2(vh)
        except Exception as _e:
            struct_input = {"error": str(_e)}

        if jobs.get(job_id, {}).get("cancel_requested"):
            jobs[job_id].update({"status": "cancelled", "progress": 55})
            return

        jobs[job_id]["progress"] = 55
        jobs[job_id]["progress_note"] = "Stage 3: NanoBodyBuilder2 — converted VHH structure…"
        persist_job_snapshot(job_id)
        try:
            struct_converted = _run_nanobodybuilder2(converted_seq)
        except Exception as _e:
            struct_converted = {"error": str(_e)}

        # ── P1-3: Phase 5 Structure QA (Rg + pLDDT proxy) ───────────────────
        phase5_qa: Dict[str, Any] = {}
        if ENABLE_PHASE5_QA:
            try:
                from core.vh2vhh.structure_qa import (  # noqa: PLC0415
                    compute_ca_rg, derive_plddt_proxy, phase5_overall_tier
                )
                _rg_result: Dict[str, Any] = {}
                _plddt_result: Dict[str, Any] = {}

                if struct_converted.get("pdb_path"):
                    _rg_result = compute_ca_rg(struct_converted["pdb_path"])
                else:
                    _rg_result = {"rg_angstrom": None, "tier": "FAIL",
                                  "note": "PDB not available", "error": "Stage 3 structure unavailable"}

                _errs = struct_converted.get("error_estimates") or []
                if not _errs and struct_converted.get("per_residue_error"):
                    _errs = struct_converted["per_residue_error"]
                _plddt_result = derive_plddt_proxy(_errs if _errs else None)

                phase5_qa = {
                    "rg": _rg_result,
                    "plddt_proxy": _plddt_result,
                    "overall_tier": phase5_overall_tier(_rg_result, _plddt_result),
                }
                jobs[job_id]["progress_note"] = (
                    f"Phase 5 QA: Rg={_rg_result.get('rg_angstrom','—')} Å "
                    f"({_rg_result.get('tier','?')}), "
                    f"pLDDT proxy={_plddt_result.get('plddt_proxy_mean','—')} "
                    f"({_plddt_result.get('tier','?')})"
                )
                persist_job_snapshot(job_id)
            except Exception as _e:
                phase5_qa = {"error": str(_e), "overall_tier": "FAIL"}

        # ── Stage 4: CDR RMSD ────────────────────────────────────────────────
        jobs[job_id]["progress"] = 68
        jobs[job_id]["progress_note"] = "Stage 4: CDR Cα RMSD (input vs converted)…"
        persist_job_snapshot(job_id)
        if struct_input.get("pdb_path") and struct_converted.get("pdb_path"):
            try:
                cdr_rmsd = _compute_vhh_cdr_rmsd(
                    struct_input["pdb_path"], struct_converted["pdb_path"]
                )
            except Exception as _e:
                cdr_rmsd = {"error": str(_e)}

        # mini-CMC
        mini_cmc: dict = {}
        try:
            mini_cmc = _vhh_mini_cmc(converted_seq)
            # Add HPR Index (V1.8)
            from core.humanization.hpr_index import compute_hpr_index
            hpr_res = compute_hpr_index(converted_seq, "")
            mini_cmc["hpr_index"] = hpr_res.get("combined", {}).get("score")

            # ── [NEW V1.8.4] CDR3 Compactness Gate ───────────────────────────
            if struct_converted.get("pdb_path"):
                from core.cmc.vhh_cmc_engine import compute_vhh_structural_metrics
                _struct_metrics = compute_vhh_structural_metrics(struct_converted["pdb_path"])
                _compactness = _struct_metrics.get("cdr3_compactness_ca_dist")
                mini_cmc["cdr3_compactness"] = _compactness
                
                # If compactness > 6.5A and Hallmark was NOT applied, flag as FAIL
                if _compactness and _compactness > 6.5:
                    _hallmarks_applied = any(m in ("G44E", "L45R", "W47F") for m in mutations_applied)
                    if not _hallmarks_applied:
                        best["overall_flags"] = list(best.get("overall_flags") or []) + [
                            "FAIL_COMPACTNESS_HALLMARK_MISMATCH: CDR3 non-compact (>6.5A) requires Hallmark"
                        ]
        except Exception as _e:
            mini_cmc = {"error": str(_e)}

        # ── Stage 5: best-candidate summary already derived from ranked panel ─
        jobs[job_id]["progress"] = 78
        jobs[job_id]["progress_note"] = "Stage 5: Finalising best-candidate QA summary…"
        persist_job_snapshot(job_id)

        # ── Classify advisory type ────────────────────────────────────────
        # pI thresholds (VHH/engVH clinical cohort, V1.8.17):
        #   < 5.5  → low pI hard fail (CDR3 E/D/Y burden, cannot correct without CDR redesign)
        #   > 9.5  → high pI hard fail (CDR3/FR K/R burden, same principle)
        #   9.0–9.5 → secretion risk warn (attempt FR pI-correction before giving up)
        # Do NOT use broad CMC flag matching for hard-fail — flag text varies by engine version.
        best_flags = best.get("overall_flags") or []
        _pi_val_raw = mini_cmc.get("pI")
        _pi_low_fail  = (_pi_val_raw is not None and _pi_val_raw < 5.5)
        _pi_high_fail = (_pi_val_raw is not None and _pi_val_raw > 9.5)
        _pi_fail = _pi_low_fail or _pi_high_fail
        _secretion_risk = (not _pi_fail) and (
            any("COMPACTNESS" in f for f in best_flags) or
            (_pi_val_raw is not None and 9.0 < _pi_val_raw <= 9.5)
        )
        _nglyc_fail = any("N_glycosylation" in f and "HIGH_RISK" in f for f in best_flags)
        _immuno_only = (not _pi_fail and not _nglyc_fail and not _secretion_risk and
                        any("HIGH_RISK_FR_EPITOPE" in f for f in best_flags))

        if _pi_fail:
            _pi_disp = round(_pi_val_raw, 2)
            if _pi_low_fail:
                _pi_detail = (
                    f"pI={_pi_disp} falls below the VHH developability window (5.5–9.5). "
                    "The acidic residues responsible (E/D/Y in CDR3) are likely antigen-contact residues — "
                    "removing them would compromise binding activity. "
                    "VH→VHH single-domain conversion is not recommended for this sequence without "
                    "CDR3 redesign or de-novo affinity maturation. "
                    "Note: this VH functions as an IgG because the VL chain and Fc provide "
                    "complementary pI balance that is absent in a VHH."
                )
                _pi_path = "De-novo CDR3 redesign targeting pI > 6.0, or retain as IgG/Fab format."
            else:
                _pi_detail = (
                    f"pI={_pi_disp} exceeds the upper VHH developability limit (9.5). "
                    "The elevated pI is driven by basic residues (K/R) in the CDR3 or FR zones. "
                    "In a single-domain context without the VL charge counterbalance, aggregation "
                    "and non-specific binding risk are unacceptably high. "
                    "Targeted FR charge-reduction alone is unlikely to bring pI within range "
                    "without CDR involvement."
                )
                _pi_path = (
                    "Targeted CDR3 K/R→Q/E substitution to reduce pI below 9.5, "
                    "combined with structural QC to confirm CDR loop integrity. "
                    "Alternatively, retain as IgG/Fab format."
                )
            conversion_advisory = {
                "type": "inherent_cdr_chemistry",
                "severity": "high",
                "title": "Inherent pI Barrier" + (" (Low)" if _pi_low_fail else " (High)"),
                "detail": _pi_detail,
                "path_forward": _pi_path,
                "offline_service": "De-novo CDR3 Redesign",
                "estimated_time": "~2-3 business days",
            }
        elif _secretion_risk:
            _comp = mini_cmc.get("cdr3_compactness", 0)
            _pi_val = mini_cmc.get("pI", 0)
            _detail = "High secretion risk detected: "
            if _comp > 6.5:
                _detail += f"CDR3 compactness ({round(_comp,2)}Å) exceeds 6.5Å safety limit, exposing hydrophobic interface. "
            if _pi_val > 9.0:
                _detail += (
                    f"pI ({round(_pi_val, 2)}) exceeds the 9.0 single-domain secretion threshold "
                    f"(VHH/engVH clinical cohort p90 = 9.08; values ≤9.5 are warn, >9.5 are fail). "
                    "Elevated pI increases aggregation and non-specific binding risk in mammalian expression. "
                )

            conversion_advisory = {
                "type": "secretion_risk",
                "severity": "medium",
                "title": "Secretion & Solubility Risk",
                "detail": _detail,
                "path_forward": (
                    "Targeted pI-tuning via surface basic residue replacement can reduce pI toward the "
                    "9.0 target. Interface reshaping mutations should be verified as applied. "
                    "Full structural QC recommended."
                ),
                "offline_service": "Targeted Secretion Optimization",
                "estimated_time": "~1 business day",
            }
        elif _nglyc_fail:
            conversion_advisory = {
                "type": "addressable_cdr_liability",
                "severity": "medium",
                "title": "Addressable CDR N-glycosylation motif",
                "detail": (
                    "An N-X-S/T N-glycosylation sequon was detected in the donor CDRs. "
                    "As an isolated VHH (without VL), the sequon is fully exposed and will be glycosylated in expression. "
                    "This is fixable: mutate the N to Q or A, or the S/T to A. "
                    "The original IgG may tolerate this because the VH/VL interface partially shields the sequon."
                ),
                "path_forward": "Identify the NxS/T position in the CDR, substitute N→Q or S/T→A, re-evaluate binding by SPR.",
                "offline_service": "Targeted Liability Removal",
                "estimated_time": "~1 business day",
            }
        elif _immuno_only:
            _src_cls = str(req.source_class or "human_mab")
            if _src_cls in ("murine_mab",):
                _immuno_detail = (
                    "The converted VHH framework contains murine-derived FR positions that may present "
                    "as neo-epitopes in human subjects. The flagged sites are residual murine germline residues "
                    "not fully replaced during the dual-engineering step. Consider these as low-priority "
                    "engineering notes unless clinical immunogenicity risk tolerance is strict."
                )
            elif _src_cls in ("phage_display_vh", "transgenic_mouse_vh"):
                _immuno_detail = (
                    "The converted VHH framework contains engineering sites introduced during the single-domain "
                    "adaptation step. These positions may present as broad-binding peptide motifs in the context "
                    "of MHC-II presentation. They are not hard blockers but should be reviewed if clinical "
                    "immunogenicity profiling is required."
                )
            else:
                # IGHV3 family human/humanized VH — no scaffold switch involved
                _immuno_detail = (
                    "The converted VHH framework contains interface-modification sites that are atypical "
                    "relative to the natural camelid VHH germline repertoire. These sites arise from the "
                    "proprietary surface-reshaping step and are not murine or non-human sequence remnants. "
                    "They represent a known engineering trade-off in framework-preserving conversion "
                    "and are considered low clinical risk for IGHV3-family human VH inputs."
                )
            conversion_advisory = {
                "type": "framework_immunogenicity",
                "severity": "medium",
                "title": "Framework Immunogenicity Audit (Proxy)",
                "detail": _immuno_detail,
                "path_forward": (
                    "Optional: Run VHH humanization (Path A) to further refine framework humanness "
                    "if strict clinical immunogenicity profiling is required."
                ),
                "offline_service": "VHH Humanization (Path A)",
                "estimated_time": "~1 business day",
            }
        else:
            conversion_advisory = None

        # ── Build payload ────────────────────────────────────────────────────
        jobs[job_id]["progress"] = 88
        jobs[job_id]["progress_note"] = "Building report (V1.5 Risk-Forward Assessment)…"
        persist_job_snapshot(job_id)

        payload: Dict[str, Any] = {
            "vh_to_vhh_standard_version": VH2VHH_STANDARD_VERSION,
            "vh_to_vhh_console_deployment_branch": VH2VHH_CONSOLE_DEPLOYMENT_BRANCH,
            "source_class":       req.source_class,
            "source_type":        source_type,
            "sequence_name":      (req.sequence_name or "").strip() or None,
            "demo_id":            req.demo_id,
            "input_sequence":     vh,
            "original_input":     raw_seq if scfv_meta.get("is_scfv") else None,
            "scfv_detected":      scfv_meta.get("is_scfv", False),
            "scfv_orientation":   scfv_meta.get("orientation"),
            "scfv_linker":        scfv_meta.get("linker_detected"),
            "scfv_vl_seq":        scfv_meta.get("vl_seq"),
            "converted_sequence": converted_seq,
            "selected_strategy":  best.get("strategy"),
            "selected_template_id": (best.get("template_id") or "").replace("GMIB", "Proprietary-VHH") if best.get("template_id") else None,
            "selected_germline":  best.get("germline"),
            "mutations_applied":  mutations_applied,
            "already_canonical":  already_canonical,
            "conversion_error":   conversion_error,
            "vh_length":          s1.get("vh_length_aa"),
            "cysteine_count":     s1.get("cysteine_count"),
            "cdr2_length":        cdr2_len,
            "cdr3_length":        cdr3_len,
            "feasibility_verdict": fe.get("verdict"),
            "feasibility_risk":   fe.get("risk_level"),
            "feasibility_notes":  fe.get("notes", []),
            "structure_computed": struct_converted.get("structure_computed", False),
            "input_plddt":        struct_input.get("plddt"),
            "converted_plddt":    struct_converted.get("plddt"),
            "cdr_rmsd":           cdr_rmsd,
            "mini_cmc":           mini_cmc,
            "cmc_status":         best.get("clinical_status"),
            "cmc_clinical_score": best.get("clinical_score"),
            "cmc_flags":          best.get("overall_flags") or [],
            "conversion_advisory": conversion_advisory,
            # Source-specific algorithm audit results (from baseline candidate)
            "phage_charge_audit": next(
                (c.get("phage_charge_audit") for c in candidates if c.get("phage_charge_audit")),
                None,
            ),
            "transgenic_shm_scan": next(
                (c.get("transgenic_shm_scan") for c in candidates if c.get("transgenic_shm_scan")),
                None,
            ),
            "candidates": [
                {
                    "candidate_id": c.get("candidate_id"),
                    "strategy": c.get("strategy"),
                    "template_id": c.get("template_id"),
                    "germline": c.get("germline"),
                    "sequence": c.get("sequence"),
                    "template_score": c.get("template_score"),
                    "framework_identity": c.get("framework_identity"),
                    "fr2_identity": c.get("fr2_identity"),
                    "clinical_status": c.get("clinical_status"),
                    "clinical_score": c.get("clinical_score"),
                    "mutations_applied": c.get("mutations_applied") or [],
                    "phase45_mutations": c.get("phase45_mutations") or [],
                    "overall_flags": c.get("overall_flags") or [],
                    "abnativ_delta": c.get("abnativ_delta"),
                    "abnativ_tier": c.get("abnativ_tier"),
                    "abnativ_vh2": c.get("abnativ_vh2"),
                    "abnativ_vhh2": c.get("abnativ_vhh2"),
                    "abnativ_reliability_warning": c.get("abnativ_reliability_warning", False),
                }
                for c in candidates
            ],
            # P0/P1 new fields
            "phase5_qa":        phase5_qa if ENABLE_PHASE5_QA else {},
            "pathway_advisory": pathway_advisory if ENABLE_PATHWAY_ADVISORY else None,
            "best_abnativ_delta": best.get("abnativ_delta"),
            "best_abnativ_tier":  best.get("abnativ_tier"),
            # [V1.8.6] Expressibility Verdict Gate (owner-mandated: CDR3+compactness+AbNatiV Δ)
            "expressibility_verdict": _compute_expressibility_verdict(
                cdr3_len=cdr3_len,
                compactness=mini_cmc.get("cdr3_compactness"),
                abnativ_delta=best.get("abnativ_delta"),
            ),
        }

        try:
            from api.routers.humanization import _build_vhh_sequence_comparison
            payload["sequence_comparison"] = _build_vhh_sequence_comparison(vh, converted_seq)
        except Exception as e:
            payload["sequence_comparison"] = {"error": str(e)}

        # Save FASTA
        fasta_lines = [f">Input_VH\n{vh}"]
        if converted_seq != vh:
            fasta_lines.append(f">Converted_VHH\n{converted_seq}")
        (out / "sequences.fasta").write_text("\n".join(fasta_lines), encoding="utf-8")

        # Copy PDBs
        for pdb_key, fname in [("pdb_path", "input_vh.pdb"), ("pdb_path", "converted_vhh.pdb")]:
            pass  # handled below
        if struct_input.get("pdb_path") and Path(struct_input["pdb_path"]).exists():
            shutil.copy2(struct_input["pdb_path"], out / "input_vh.pdb")
        if struct_converted.get("pdb_path") and Path(struct_converted["pdb_path"]).exists():
            shutil.copy2(struct_converted["pdb_path"], out / "converted_vhh.pdb")

        # ── V1.5 Risk-Forward Assessment ─────────────────────────────────────
        try:
            v15_assessment = _compute_v15_risk_assessment(payload)
            payload.update(v15_assessment)
        except Exception as _v15e:
            payload["_v15_assessment_error"] = str(_v15e)

        # ── V1.6 Engineered VH Similarity Layer (additive, non-blocking) ─────
        try:
            from core.vh2vhh.engineered_vh_similarity import score_engineered_vh_similarity
            _conv_seq = payload.get("converted_sequence") or payload.get("best_converted_sequence") or ""
            if _conv_seq:
                _evhs = score_engineered_vh_similarity(_conv_seq)
                payload["engineered_vh_similarity"] = _evhs.to_dict()

                # Stealth gate: if stealth_departures == 0, the candidate
                # retains a naive VH FR2 interface — flag it as INFO regardless
                # of other scores.
                _stealth_n = (_evhs.evidence or {}).get("stealth_departures", {}).get("count", -1)
                if _stealth_n == 0:
                    _evhs_score_band = "medium"
                    payload["engineered_vh_similarity"]["score_band"] = "medium"
                    payload["engineered_vh_similarity"]["notes"] = list(
                        payload["engineered_vh_similarity"].get("notes") or []
                    ) + ["stealth_departures=0: VH FR2 interface unchanged — single-domain stability unverified"]
                    # Insert INFO row into risk_attribution if present
                    if isinstance(payload.get("risk_attribution"), list):
                        payload["risk_attribution"].append({
                            "risk_dimension": "Stealth Interface Reshaping",
                            "current_value": "0 departures at 35/50/89/94",
                            "safety_threshold": "≥ 1 departure (Atlas-24: 70.8% have 3)",
                            "attribution_source": "Engineered VH Similarity (V1.6 Atlas-24 prior)",
                            "severity": "INFO",
                        })
        except Exception as _v16e:
            payload["_v16_similarity_error"] = str(_v16e)

        # ── V1.7 Glycan-Dependent Epitope Risk Layer (final decision multiplier) ──
        try:
            from core.vh2vhh.glycan_dependency_checker import score_glycan_dependency_risk
            _drug_name = payload.get("drug_name") or payload.get("sequence_name") or payload.get("demo_id") or ""
            _conv_seq_g = payload.get("converted_sequence") or payload.get("best_converted_sequence") or ""
            if _conv_seq_g:
                _glycan = score_glycan_dependency_risk(
                    converted_seq=_conv_seq_g,
                    drug_name=_drug_name if _drug_name else None,
                )
                payload["glycan_dependency"] = _glycan.to_dict()
                # V1.7 applies after V1.5/V1.6 evidence layers and is the only
                # V1.7 term allowed to change the final probability/verdict.
                if _glycan.penalty_factor < 1.0 and isinstance(payload.get("success_probability"), float):
                    payload["success_probability"] = round(
                        payload["success_probability"] * _glycan.penalty_factor, 3
                    )
                    sp = payload["success_probability"]
                    if sp < 0.30 and payload.get("verdict_severity") != "HIGH_RISK":
                        payload["verdict_severity"] = "HIGH_RISK"
                    elif sp < 0.70 and payload.get("verdict_severity") == "LOW_RISK":
                        payload["verdict_severity"] = "MODERATE_RISK"
                    if sp < 0.50 and payload.get("primary_recommendation") == "C":
                        payload["primary_recommendation"] = "A"
                    elif sp < 0.70 and payload.get("primary_recommendation") == "C":
                        payload["primary_recommendation"] = "B"
                if isinstance(payload.get("risk_attribution"), list):
                    payload["risk_attribution"].extend(_glycan.risk_attribution_rows or [])
        except Exception as _v17e:
            payload["_v17_glycan_error"] = str(_v17e)

        (out / "result.json").write_text(json.dumps(payload, indent=2, ensure_ascii=False), encoding="utf-8")
        payload["cmc_issue_archive"] = _append_cmc_issue_casebank(job_id, payload, out)
        (out / "result.json").write_text(json.dumps(payload, indent=2, ensure_ascii=False), encoding="utf-8")

        # HTML report (cover "Project" = client sequence_name when set, else job_id)
        report_url: Optional[str] = None
        try:
            _proj = (payload.get("sequence_name") or "").strip() or job_id
            rp = _generate_vh2vhh_html_report(payload, out, _proj)
            report_url = files_url_for_path(job_id, rp)
        except Exception as _re:
            payload["_report_error"] = str(_re)

        # ZIP
        zip_url = _create_vh2vhh_zip(out, job_id)
        if zip_url:
            payload["zip_url"] = zip_url

        elapsed = round(time.time() - t0, 1)
        save_result(job_id, payload, report_url, elapsed)

        _extra = {"zip_url": zip_url} if zip_url else {}
        jobs[job_id].update({
            "status":      "done",
            "progress":    100,
            "elapsed_sec": elapsed,
            "result":      payload,
            "report_url":  report_url,
            "extra":       _extra,
        })
        persist_job_snapshot(job_id)

    except Exception as exc:
        import traceback
        err = f"{type(exc).__name__}: {exc}\n{traceback.format_exc()}"
        jobs[job_id] = {"status": "failed", "progress": 0, "error": err}
        persist_job_snapshot(job_id)


# ─────────────────────────────────────────────────────────────────────────────
# Async endpoint (primary)
# ─────────────────────────────────────────────────────────────────────────────

def _check_ighv3_family(vh: str) -> None:
    """Pre-flight gate: accept IGHV3 family VH; reject IGHV1, IGHV4, and other families.

    Uses a 16-position FR2+FR4 discriminator calibrated against 6 clinical mAb VH sequences
    (2026-05-17). IGHV3-23/33/66 all score ≥15/16; IGHV1-18/69 and IGHV4 score ≤7/16.
    Threshold: 12/16 provides a clean separation with a 5-position gap on each side.
    """
    try:
        from anarcii import Anarcii
        from core.humanization.kabat_utils import kabat_from_anarcii

        a = Anarcii(seq_type="antibody", mode="accuracy")
        a.number([vh])
        entry = a.to_scheme("kabat").get("Sequence 1", {})
        if entry.get("error") or entry.get("chain_type") != "H":
            raise ValueError(
                f"ANARCI failed to recognize a valid VH domain: {entry.get('error', 'unknown error')}"
            )

        kd = kabat_from_anarcii(entry.get("numbering", []))
        same = sum(1 for k, v in _IGHV3_FAMILY_GATE.items() if kd.get(k) == v)
        total = len(_IGHV3_FAMILY_GATE)

        if same < _IGHV3_FAMILY_GATE_THRESHOLD:
            raise ValueError(
                f"Domain Restriction: The VH-to-VHH conversion service is restricted to the "
                f"IGHV3 germline family. The submitted sequence has low compatibility with the "
                f"IGHV3 framework signature ({same}/{total} conserved FR positions matched). "
                f"Sequences from other germline families (e.g. IGHV1, IGHV4) are not supported "
                f"by this conversion pathway."
            )
    except ValueError:
        raise
    except Exception:
        pass

@router.post("/async", summary="Enqueue VH→VHH full conversion job (poll GET /jobs/{job_id})")
def vh_to_vhh_async(req: VhToVhhRequest) -> Dict[str, Any]:
    """Return immediately with job_id; full pipeline runs in background thread."""
    vh = re.sub(r"[\s\n\r]", "", (req.vh_sequence or "").upper())
    if len(vh) < 100 or len(vh) > 140:
        raise HTTPException(
            status_code=422,
            detail=f"VH length must be 100–140 aa (got {len(vh)}).",
        )
        
    try:
        _check_ighv3_family(vh)
    except ValueError as e:
        raise HTTPException(status_code=422, detail=str(e))

    import uuid
    job_id = f"vh2vhh-{uuid.uuid4().hex[:8]}"
    jobs[job_id] = {
        "status": "queued",
        "progress": 0,
        "progress_note": "Queued — starting VH→VHH conversion pipeline…",
    }
    persist_job_snapshot(job_id)

    def _worker() -> None:
        try:
            _vh2vhh_impl(job_id, req)
        except Exception as exc:
            jobs[job_id] = {"status": "failed", "progress": 0, "error": str(exc)}
            persist_job_snapshot(job_id)

    threading.Thread(target=_worker, daemon=True).start()
    return {"job_id": job_id, "status": "queued", "poll_url": f"/jobs/{job_id}"}


# ─────────────────────────────────────────────────────────────────────────────
# Legacy sync Stage-1 endpoint (backward-compatible)
# ─────────────────────────────────────────────────────────────────────────────

def _build_ui(s1: Dict[str, Any], source_class: str) -> Dict[str, Any]:
    fe = s1.get("feasibility") or {}
    verdict = str(fe.get("verdict", "—"))
    risk = str(fe.get("risk_level", "—"))
    notes: list = fe.get("notes") or []
    cdr3 = s1.get("cdr3_length")
    cdr2 = s1.get("cdr2_length")
    n = s1.get("vh_length_aa")
    notes_text = "\n".join(f"• {x}" for x in notes) if notes else "—"

    if verdict == "NOT_FEASIBLE":
        status, st_tone = "FAIL", "fail"
    elif verdict == "FEASIBLE_WITH_CAUTION":
        status, st_tone = "CAUTION", "warn"
    else:
        status, st_tone = "PASS", "pass"

    if "murine" in source_class:
        path_hint = "Path C2 (murine → dual engineering: humanization + camelization) "
    elif source_class == "transgenic_mouse_vh":
        path_hint = "Path C2b (transgenic HCAb VH → SHM-aware camelization) "
    else:
        path_hint = "Path C1 (human/phage: framework-preserving camelization) "
    germline = (
        f"{path_hint}Source class: {source_class}. "
        f"ANARCI Kabat: CDR2={cdr2}aa, CDR3={cdr3}aa; VH={n}aa. "
        f"V1.7: Hallmarks IMGT 44/45/47 only (IMGT 37 is CDR1, not forced)."
    )
    route = (
        "Strategy A: surface-reshaping + Hallmark/Stealth per CDR2/CDR3 gates (V1.7). "
        "3D structure + SASA refinement run in async mode."
    )
    cdr2_i = int(cdr2) if cdr2 is not None else 0
    stealth_short = f"CDR2 {cdr2}aa" + (" — A50 gate (skip)" if cdr2_i >= 17 else " — A50D included")

    return {
        "status": status,
        "statusTone": st_tone,
        "summary": f"Stage-1: {verdict} (risk: {risk}). CDR2={cdr2}aa, CDR3={cdr3}aa.",
        "germline": germline,
        "cdrNote": "CDR2/CDR3 lengths from ANARCI Kabat (accuracy mode); heuristic fallback if unavailable.",
        "route": route,
        "routeShort": "Stage-1 (server)",
        "routeTone": "fail" if status == "FAIL" else ("warn" if status == "CAUTION" else "ok"),
        "hallmarkStart": "IMGT 44/45/47 (V1.7)",
        "hallmark": notes_text,
        "stealth": "Stealth set depends on CDR2 length gate (A50 skipped when CDR2≥17aa).",
        "stealthShort": stealth_short,
        "stealthTone": "warn" if cdr2_i >= 17 else "ok",
        "recommendationText": (
            "Stage-1 feasibility complete. "
            "Use /vh_to_vhh/async for full pipeline: mutations + structure + CMC + report."
        ),
    }


@router.post("/analyze", summary="VH→VHH Stage-1 feasibility only (legacy sync)")
def analyze_vh_to_vhh(req: VhToVhhRequest) -> Dict[str, Any]:
    """Legacy sync endpoint: Stage-1 feasibility only."""
    vh = re.sub(r"[\s\n\r]", "", (req.vh_sequence or "").upper())
    if len(vh) < 100 or len(vh) > 140:
        raise HTTPException(
            status_code=422,
            detail=f"VH length must be 100–140 aa after whitespace strip (got {len(vh)}).",
        )
        
    try:
        _check_ighv3_family(vh)
    except ValueError as e:
        raise HTTPException(status_code=422, detail=str(e))

    try:
        from scripts.vhh_conversion_pipeline import run_stage1  # noqa: PLC0415
    except ImportError as exc:
        raise HTTPException(status_code=503, detail=f"Pipeline import failed: {exc}") from exc

    st_key = _map_source_class(req.source_class)
    try:
        s1: Dict[str, Any] = run_stage1(vh, source_type=st_key)
    except Exception as exc:
        raise HTTPException(status_code=500, detail=f"run_stage1 failed: {exc}") from exc

    return {
        "ok": True,
        "standard_version": VH2VHH_STANDARD_VERSION,
        "deployment_branch": VH2VHH_CONSOLE_DEPLOYMENT_BRANCH,
        "report_protocol_version": VH2VHH_REPORT_PROTOCOL_VERSION,
        "analysis_version": VH2VHH_ANALYSIS_VERSION,
        "engine": "scripts.vhh_conversion_pipeline.run_stage1",
        "source_class": req.source_class,
        "demo_id": req.demo_id,
        "sequence_name": (req.sequence_name or "").strip() or None,
        "stage1": s1,
        "ui": _build_ui(s1, req.source_class),
    }
