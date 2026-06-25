"""
core/cmc/vhh_fr_mutation_sites.py
==================================
FR mutation suggestion engine for VHH nanobodies and engineered autonomous VH (EngVH).

Two origin modes:
  - camelid_vhh / humanized_vhh / clinical_vhh
      Suggests FR mutations to reduce SAP/hydrophobicity, patch charge, pI, and
      instability. Protects CDR positions and VHH Hallmark positions (44/45/47/37).
  - engineered_vh / atlas24
      Adds sdAb adaptation sites (L18S, F68Y) as highest-priority suggestions.
      Skips Hallmark protection (VH-type FR2 is expected). Applies Atlas-24
      guided stealth/charge recommendations.

Output schema (list of dicts):
  {
    "category":       str  — "hydrophobic" | "charge" | "pI" | "stability" |
                              "sdab_adaptation" | "engvh_stealth",
    "kabat_pos":      int,
    "linear_pos":     int,   # 0-based position in full sequence (approximate)
    "found_aa":       str,
    "suggested_aa":   str,
    "priority":       str  — "HIGH" | "MEDIUM" | "LOW",
    "label":          str,   # display label e.g. "W103S (FR3)"
    "rationale":      str,   # one-line reason
    "note":           str,   # optional caveat
  }
"""
from __future__ import annotations

from typing import Any, Dict, List, Optional, Tuple

from Bio.SeqUtils.ProtParam import ProteinAnalysis

# ── Hydrophobicity scales ────────────────────────────────────────────────────
_HYDRO_RUN = set("AILMFWVY")
_POS_CHARGE = set("KRH")
_NEG_CHARGE = set("DE")

# Conservative hydrophobicity-reducing substitutions
_HYDRO_REDUCE: Dict[str, Tuple[str, str]] = {
    "A": ("S", "Ala→Ser: +OH, minimal steric change"),
    "I": ("T", "Ile→Thr: +OH, β-branched"),
    "L": ("S", "Leu→Ser"),
    "M": ("T", "Met→Thr: removes thioether"),
    "F": ("Y", "Phe→Tyr: adds -OH, retains aromatic packing"),
    "W": ("S", "Trp→Ser: reduces aromatic bulk — verify structure first"),
    "V": ("T", "Val→Thr: isosteric +OH"),
    "Y": ("S", "Tyr→Ser: reduces hydrophobic contribution"),
}

# pI / charge substitutions
_LOWER_PI: Dict[str, str] = {"K": "Q", "R": "Q", "H": "Q"}  # lower pI
_RAISE_PI:  Dict[str, str] = {"D": "N", "E": "Q"}            # raise pI

# Instability dipeptide → target substitution (charge-conservative)
# Rule: neutral original AA → neutral hint only.  Charged original (D/E) → charge-family hint only.
_INSTAB_DIPEPTIDE: Dict[str, Tuple[str, str]] = {
    # (dipeptide) → (position to mutate: 0=first, 1=second, suggested_aa)
    # NG: mutate G (pos 1) → A (neutral, steric blockade of succinimide). NOT D (adds charge).
    "NG": (1, "A"),  # NG → NA: Ala disrupts the succinimide intermediate; charge-neutral
    "NS": (1, "T"),  # NS → NT: Thr at +1 restricts backbone conformation (neutral)
    "DG": (1, "A"),  # DG → DA: removes isomerization (D is already charged; A at pos 1 ok)
    "DS": (1, "A"),  # DS → DA: removes isomerization (charge-neutral at pos 1)
}

# ── VHH framework region definitions (Kabat approximate boundaries) ──────────
# Hallmark positions: protected in camelid VHH (should NOT be mutated to non-VHH type)
_VHH_HALLMARK_KABAT = {37, 44, 45, 47}

# Kabat FR regions for VHH (approximate — see IMGT_REGIONS for canonical)
# FR1: 1-30, FR2: 36-49, FR3: 66-94, FR4: 103-113
_VHH_FR_KABAT_RANGES = [(1, 30), (36, 49), (66, 94), (103, 113)]
_VHH_CDR_KABAT_RANGES = [(31, 35), (50, 65), (95, 102)]  # CDR1/2/3

# EngVH sdAb adaptation sites (from VH→VHH Conversion Standard V1.8 §2 Phase 4.5)
_ENGVH_ADAPTATION: Dict[int, Dict[str, str]] = {
    18: {
        "vh_typical": "L",
        "sdab_aa":    "S",
        "label":      "L18S (Kabat 18)",
        "rationale":  "sdAb adaptation: reduces VH-type FR1 aggregation tendency in autonomous single-domain context",
        "priority":   "HIGH",
    },
    68: {
        "vh_typical": "F",
        "sdab_aa":    "Y",
        "label":      "F68Y (Kabat 68)",
        "rationale":  "sdAb adaptation: Phe→Tyr introduces H-bond network at FR3 junction, improves thermal stability",
        "priority":   "MEDIUM",
    },
}

# EngVH stealth positions (from Atlas-24 V1.6 analysis: 35/50/89/94 prefer IGHV3-23 identity)
_ENGVH_STEALTH_IGHV323: Dict[int, str] = {35: "S", 50: "A", 89: "V", 94: "K"}


def _kabat_pos_from_linear(seq: str) -> Dict[int, str]:
    """
    Best-effort Kabat numbering via ANARCI.
    Returns {kabat_pos: aa} for base positions (ins='' only).
    Falls back to empty dict on failure.
    """
    try:
        from anarcii import Anarcii  # type: ignore
        from core.humanization.kabat_utils import kabat_from_anarcii

        a = Anarcii()
        res = a.number([("vhh", seq)])
        try:
            res = a.to_scheme("kabat")
        except Exception:
            pass
        entry = res.get("vhh", {}) if isinstance(res, dict) else {}
        numbering = entry.get("numbering", []) if entry else []
        kd = kabat_from_anarcii(numbering)
        result = {pos: aa for (pos, ins), aa in kd.items() if ins == ""}
        if result:
            return result
    except Exception:
        pass

    # Fallback: linear → approximate Kabat for canonical ~120–130 aa VHH
    # Kabat positions: FR1 1-30, CDR1 31-35, FR2 36-49, CDR2 50-65, FR3 66-94, CDR3 95-102, FR4 103-113
    # Approximate by assigning linear positions directly (offset = 0 for standard VHH length)
    L = len(seq)
    result = {}
    for lin, aa in enumerate(seq):
        kp = lin + 1  # 1-indexed approximate Kabat
        if kp <= 113:
            result[kp] = aa
    return result


def _is_fr_kabat(pos: int, is_engvh: bool) -> bool:
    """Return True if kabat pos is in framework (not CDR)."""
    for lo, hi in _VHH_CDR_KABAT_RANGES:
        if lo <= pos <= hi:
            return False
    return True


def _fr_label(kabat_pos: int) -> str:
    if 1 <= kabat_pos <= 30:
        return "FR1"
    if 36 <= kabat_pos <= 49:
        return "FR2"
    if 66 <= kabat_pos <= 94:
        return "FR3"
    if 103 <= kabat_pos <= 113:
        return "FR4"
    return "FR?"


_INSTAB_GATE = 40.0  # Guruprasad instability gate (clinical standard)


def _instab_side_effect_ok(seq: str, lin0: int, new_aa: str, base_ii: float) -> bool:
    """
    Guard for NON-stability-targeted mutations (e.g. hydrophobic, charge).

    A hydrophobic-reducing mutation (e.g. A→S, V→T) should not push the
    instability index above the clinical gate (40.0) when the base is below it,
    and should not worsen it by more than 1.0 when the base is already above.

    Returns True (OK to proceed) / False (reject candidate).
    """
    if not (0 <= lin0 < len(seq)):
        return True  # cannot verify — allow through
    try:
        clean = seq.replace("X", "A")
        after_s = clean[:lin0] + new_aa.upper() + clean[lin0 + 1:]
        ii_after = ProteinAnalysis(after_s).instability_index()
        if base_ii < _INSTAB_GATE:
            return ii_after < _INSTAB_GATE          # must stay below gate
        else:
            return ii_after <= base_ii + 1.0        # already above gate: cap worsening
    except Exception:
        return True  # Bio failure — conservative pass-through


def get_vhh_fr_suggestions(
    seq: str,
    flags: Dict[str, Any],
    metrics: Dict[str, Any],
    *,
    origin: str = "camelid_vhh",
    engvh_adaptation: Optional[Dict[str, Any]] = None,
) -> List[Dict[str, Any]]:
    """
    Generate FR mutation suggestions for a VHH or EngVH sequence.

    Parameters
    ----------
    seq              : full VHH/EngVH AA sequence
    flags            : risk_flags dict from evaluate_single_vhh
    metrics          : metrics dict from evaluate_single_vhh
    origin           : sdab_origin string — determines rule set and hallmark protection
    engvh_adaptation : result from compute_engvh_adaptation_check (for EngVH path)

    Returns
    -------
    List of suggestion dicts, sorted by priority (HIGH first).
    """
    seq = seq.strip().upper()
    _onorm = origin.lower().replace("-", "_")
    is_engvh = _onorm in {"engineered_vh", "atlas24", "engineered"}
    # SCAb/transgenic_sdab is also VH-like by design (VH-canonical FR2, no camelid hallmark).
    # It must NOT receive VHH hallmark "rescue" suggestions or hallmark-position protection.
    is_vh_like_sdab = is_engvh or _onorm in {"transgenic_sdab", "transgenic", "porustobart"}
    suggestions: List[Dict[str, Any]] = []
    seen: set = set()  # (kabat_pos, suggested_aa) dedup

    # Base instability for side-effect guards (used by hydrophobic / charge paths)
    _base_instab: float = float(metrics.get("instability_index") or 0.0)

    # ── Get Kabat numbering ─────────────────────────────────────────────────
    kabat = _kabat_pos_from_linear(seq)
    # Fallback heuristic map (approx Kabat pos → linear 0-indexed)
    # for a canonical 120-130aa VHH/VH domain
    L = len(seq)
    def _approx_linear(kb: int) -> int:
        """Very rough Kabat→linear for display only."""
        return min(kb - 1, L - 1)

    def _add(category: str, kabat_pos: int, found: str, sugg: str,
             priority: str, label: str, rationale: str, note: str = "") -> None:
        key = (kabat_pos, sugg)
        if key in seen:
            return
        seen.add(key)
        lin = _approx_linear(kabat_pos)
        suggestions.append({
            "category":   category,
            "kabat_pos":  kabat_pos,
            "linear_pos": lin,
            "found_aa":   found,
            "suggested_aa": sugg,
            "priority":   priority,
            "label":      f"{found}{kabat_pos}{sugg} ({_fr_label(kabat_pos)})",
            "rationale":  rationale,
            "note":       note,
        })

    # ── Path A: EngVH sdAb adaptation sites ────────────────────────────────
    if is_engvh and engvh_adaptation:
        for site in (engvh_adaptation.get("sites") or []):
            if site.get("status") == "VH_CANONICAL":
                kp = site["kabat_pos"]
                found_aa = site["found_aa"]
                sugg_aa  = site["sdab_aa"]
                info     = _ENGVH_ADAPTATION.get(kp, {})
                _add(
                    category  = "sdab_adaptation",
                    kabat_pos = kp,
                    found     = found_aa,
                    sugg      = sugg_aa,
                    priority  = info.get("priority", "HIGH"),
                    label     = info.get("label", f"{found_aa}{kp}{sugg_aa}"),
                    rationale = info.get("rationale", "sdAb adaptation site"),
                )

    # ── Path B: SAP / hydrophobic patch reduction ───────────────────────────
    if flags.get("SAP_score") in ("WARN", "FAIL") or flags.get("hydro_patch_max9") in ("WARN", "FAIL") or flags.get("GRAVY") in ("WARN", "FAIL") or flags.get("psh") in ("WARN", "FAIL"):
        # F3: CDR-driven hydrophobic patch detection for VHH
        # If the peak hydrophobic window is CDR-internal, FR mutations won't fix it.
        cdr_driven_patch = False
        if flags.get("hydro_patch_max9") in ("WARN", "FAIL") or flags.get("psh") in ("WARN", "FAIL"):
            try:
                # Find max 9-mer window
                best_i = -1
                best_count = -1
                for i in range(len(seq) - 8):
                    c = sum(1 for aa in seq[i:i+9] if aa in _HYDRO_RUN)
                    if c > best_count:
                        best_count = c
                        best_i = i
                
                if best_i >= 0:
                    # Check if window [best_i, best_i+9) is CDR-driven
                    # VHH CDRs (Kabat): 31-35, 50-65, 95-102
                    cdr_count = 0
                    for offset in range(9):
                        # Find kabat pos for linear index best_i + offset
                        kp = next((k for k, v in kabat.items() if _approx_linear(k) == (best_i + offset)), None)
                        if kp:
                            if any(start <= kp <= end for start, end in _VHH_CDR_KABAT_RANGES):
                                cdr_count += 1
                    
                    if cdr_count >= 5: # >= 55% CDR residues
                        cdr_driven_patch = True
                        suggestions.append({
                            "category": "hydrophobic",
                            "priority": "INFO",
                            "label": "CDR-driven patch detected",
                            "rationale": "Hydrophobic patch peak is CDR-internal. FR-only mutations cannot move local hydro_patch_max9. Addressing this requires CDR redesign.",
                        })
            except Exception:
                pass

        if not cdr_driven_patch:
            # Only suggest mutations if the overall hydrophobicity is high
            for kp, aa in kabat.items():
                if aa not in _HYDRO_RUN:
                    continue
                if not _is_fr_kabat(kp, is_engvh):
                    continue
                # Protect VHH Hallmark positions ONLY for camelid VHH (not VH-like sdAb such as
                # engineered_vh or transgenic_sdab, where VH residues at 37/44/45/47 are expected).
                if not is_vh_like_sdab and kp in _VHH_HALLMARK_KABAT:
                    continue
                sugg, subst_note = _HYDRO_REDUCE.get(aa, (None, ""))
                if sugg is None:
                    continue
                # Side-effect guard: hydrophobic mutation must not push instability above gate
                lin0 = _approx_linear(kp)
                if not _instab_side_effect_ok(seq, lin0, sugg, _base_instab):
                    continue
                prio = "HIGH" if flags.get("SAP_score") == "FAIL" else "MEDIUM"
                _add(
                    category  = "hydrophobic",
                    kabat_pos = kp,
                    found     = aa,
                    sugg      = sugg,
                    priority  = prio,
                    label     = f"{aa}{kp}{sugg}",
                    rationale = f"SAP/hydrophobic patch elevated — {aa}{kp}{sugg} reduces surface hydrophobicity",
                    note      = subst_note if aa in ("W", "F") else "",
                )

    # ── Path B2: FR2 specific hydrophobicity reduction ──────────────────────
    if flags.get("exposed_fr2_hydrophobicity") in ("WARN", "FAIL"):
        prio = "HIGH" if flags.get("exposed_fr2_hydrophobicity") == "FAIL" else "MEDIUM"
        
        # 1. First, check if the high hydrophobicity is caused by VH-canonical hallmarks.
        # Restoring VHH hallmarks is the most biologically correct way to fix FR2 hydrophobicity.
        _VHH_HALLMARK_RESCUE = {
            37: {"W": "F", "V": "F", "I": "F", "L": "F"}, # Y is acceptable for VHH, don't rescue
            44: {"G": "E"},
            45: {"L": "R"},
            47: {"W": "G", "L": "G", "F": "G"}
        }
        
        # Hallmark rescue ONLY applies to camelid VHH that has lost its hallmarks.
        # VH-like sdAb (engineered_vh, transgenic_sdab/SCAb) legitimately uses VH-canonical
        # residues at 37/44/45/47 — pushing them toward VHH would un-engineer the molecule.
        if not is_vh_like_sdab:
            for kp, rescue_map in _VHH_HALLMARK_RESCUE.items():
                found_aa = kabat.get(kp)
                if found_aa is None:
                    continue
                sugg = rescue_map.get(found_aa)
                if sugg is None:
                    continue
                _add(
                    category  = "hydrophobic",
                    kabat_pos = kp,
                    found     = found_aa,
                    sugg      = sugg,
                    priority  = prio,
                    label     = f"{found_aa}{kp}{sugg} (FR2 Hallmark)",
                    rationale = f"FR2 hydrophobicity elevated — restoring VHH hallmark {found_aa}{kp}{sugg} reduces aggregation risk",
                )

        # 2. Then, check other FR2 positions (Kabat 36-49) for general hydrophobicity reduction.
        # We strictly protect structurally critical positions (36, 49) and the hallmarks (37, 44, 45, 47).
        _FR2_PROTECTED = {36, 37, 44, 45, 47, 49}
        for kp, aa in kabat.items():
            if not (36 <= kp <= 49):
                continue
            if kp in _FR2_PROTECTED:
                continue
            if aa not in _HYDRO_RUN:
                continue
            if not _is_fr_kabat(kp, is_engvh):
                continue
            
            sugg, subst_note = _HYDRO_REDUCE.get(aa, (None, ""))
            if sugg is None:
                continue
            # Side-effect guard: must not push instability above gate
            lin0 = _approx_linear(kp)
            if not _instab_side_effect_ok(seq, lin0, sugg, _base_instab):
                continue
            _add(
                category  = "hydrophobic",
                kabat_pos = kp,
                found     = aa,
                sugg      = sugg,
                priority  = prio,
                label     = f"{aa}{kp}{sugg} (FR2)",
                rationale = f"FR2 hydrophobicity elevated — {aa}{kp}{sugg} reduces FR2 surface hydrophobicity",
                note      = subst_note if aa in ("W", "F") else "",
            )

    # ── Path C: pI tuning ─────────────────────────────────────────────────
    pi_val = metrics.get("pI")
    if pi_val is not None:
        if flags.get("pI") in ("WARN", "FAIL"):
            if pi_val > 8.5:
                # pI too high → introduce negative charge
                for kp, aa in kabat.items():
                    if aa not in _LOWER_PI:
                        continue
                    if not _is_fr_kabat(kp, is_engvh):
                        continue
                    if not is_vh_like_sdab and kp in _VHH_HALLMARK_KABAT:
                        continue
                    sugg = _LOWER_PI[aa]
                    _add(
                        category  = "pI",
                        kabat_pos = kp,
                        found     = aa,
                        sugg      = sugg,
                        priority  = "MEDIUM",
                        label     = f"{aa}{kp}{sugg}",
                        rationale = f"pI {pi_val:.2f} above target — {aa}{kp}{sugg} lowers pI",
                    )
            elif pi_val < 6.0:
                # pI too low → reduce negative charge
                for kp, aa in kabat.items():
                    if aa not in _RAISE_PI:
                        continue
                    if not _is_fr_kabat(kp, is_engvh):
                        continue
                    if not is_vh_like_sdab and kp in _VHH_HALLMARK_KABAT:
                        continue
                    sugg = _RAISE_PI[aa]
                    _add(
                        category  = "pI",
                        kabat_pos = kp,
                        found     = aa,
                        sugg      = sugg,
                        priority  = "MEDIUM",
                        label     = f"{aa}{kp}{sugg}",
                        rationale = f"pI {pi_val:.2f} below target — {aa}{kp}{sugg} raises pI",
                    )

    # ── Path D: Charge patch reduction ─────────────────────────────────────
    # Target local clusters (PPC/PNC) independently of global net_charge.
    if flags.get("ppc") in ("WARN", "FAIL") or flags.get("charge_patch_max7") in ("WARN", "FAIL"):
        # Positive patch: target K/R/H
        for kp, aa in kabat.items():
            if aa not in _POS_CHARGE:
                continue
            if not _is_fr_kabat(kp, is_engvh):
                continue
            if not is_vh_like_sdab and kp in _VHH_HALLMARK_KABAT:
                continue
            sugg = _LOWER_PI.get(aa)
            if sugg:
                _add(
                    category  = "charge",
                    kabat_pos = kp,
                    found     = aa,
                    sugg      = sugg,
                    priority  = "MEDIUM",
                    label     = f"{aa}{kp}{sugg}",
                    rationale = f"Positive charge patch elevated — {aa}{kp}{sugg} reduces cluster",
                )
    
    if flags.get("pnc") in ("WARN", "FAIL"):
        # Negative patch: target D/E
        for kp, aa in kabat.items():
            if aa not in _NEG_CHARGE:
                continue
            if not _is_fr_kabat(kp, is_engvh):
                continue
            if not is_vh_like_sdab and kp in _VHH_HALLMARK_KABAT:
                continue
            sugg = _RAISE_PI.get(aa)
            if sugg:
                _add(
                    category  = "charge",
                    kabat_pos = kp,
                    found     = aa,
                    sugg      = sugg,
                    priority  = "MEDIUM",
                    label     = f"{aa}{kp}{sugg}",
                    rationale = f"Negative charge patch elevated — {aa}{kp}{sugg} reduces cluster",
                )

    # ── Path E: Instability dipeptide (FR-only) ─────────────────────────────
    if flags.get("instability_index") in ("WARN", "FAIL") and kabat:
        # Scan kabat dict for adjacent dipeptide motifs
        sorted_kp = sorted(kabat.keys())
        for i, kp in enumerate(sorted_kp[:-1]):
            kp_next = sorted_kp[i + 1]
            if kp_next != kp + 1:
                continue  # not adjacent
            dipep = kabat[kp] + kabat[kp_next]
            if dipep not in _INSTAB_DIPEPTIDE:
                continue
            pos_idx, sugg_aa = _INSTAB_DIPEPTIDE[dipep]
            target_kp = kp if pos_idx == 0 else kp_next
            found_aa  = kabat[target_kp]
            if not _is_fr_kabat(target_kp, is_engvh):
                continue
            if not is_vh_like_sdab and target_kp in _VHH_HALLMARK_KABAT:
                continue
            _add(
                category  = "stability",
                kabat_pos = target_kp,
                found     = found_aa,
                sugg      = sugg_aa,
                priority  = "LOW",
                label     = f"{found_aa}{target_kp}{sugg_aa}",
                rationale = f"Instability dipeptide {dipep} at Kabat {kp}–{kp_next} — mutating {found_aa}{target_kp}{sugg_aa} removes motif",
            )

    # ── Path F: EngVH stealth positions (Atlas-24 IGHV3-23 alignment) ──────
    if is_engvh and flags.get("SAP_score") in ("WARN", "FAIL"):
        for kp, ref_aa in _ENGVH_STEALTH_IGHV323.items():
            found_aa = kabat.get(kp)
            if found_aa is None or found_aa == ref_aa:
                continue
            if not _is_fr_kabat(kp, is_engvh):
                continue
            _add(
                category  = "engvh_stealth",
                kabat_pos = kp,
                found     = found_aa,
                sugg      = ref_aa,
                priority  = "LOW",
                label     = f"{found_aa}{kp}{ref_aa}",
                rationale = f"Atlas-24 stealth position {kp}: IGHV3-23 reference is {ref_aa} — restoring improves EngVH similarity score",
                note      = "Only apply if CDR3 analysis confirms the substitution is not critical.",
            )

    # ── Sort: HIGH first, then by kabat_pos within each tier ───────────────
    prio_order = {"HIGH": 0, "MEDIUM": 1, "LOW": 2}
    suggestions.sort(key=lambda s: (prio_order.get(s["priority"], 3), s["kabat_pos"]))

    return suggestions
