"""
CMC design — V3 pI optimization for VH/VL humanization.

Designs v3 by lowering pI via FR-only charge reduction mutations (K/R → Q/E).
Invariants: never mutate CDR; avoid Vernier positions; CDR preservation hard-gated.

Used by: verify --fix (when pI > 8.5), rebuild_fxy_2c2_ssot.py --design-v3.
"""

from __future__ import annotations

from typing import Any, Dict, List, Optional, Tuple

from core.humanization.kabat_utils import (
    CDR_RANGES_VH,
    CDR_RANGES_VL,
    VERNIER_KABAT_TO_IMGT_VH,
    VERNIER_KABAT_TO_IMGT_VL,
    get_kabat_numbering,
    sorted_keys,
    verify_cdr_preservation,
)


def _compute_pi(vh: str, vl: str) -> Optional[float]:
    try:
        from Bio.SeqUtils.ProtParam import ProteinAnalysis  # type: ignore

        seq = (vh or "") + (vl or "")
        if not seq:
            return None
        return float(ProteinAnalysis(seq).isoelectric_point())
    except Exception:
        return None


def _in_cdr_kabat(pos: int, chain: str) -> bool:
    ranges = CDR_RANGES_VH if chain == "VH" else CDR_RANGES_VL
    return any(lo <= pos <= hi for lo, hi in ranges)


def _kabatdict_to_seq(kd: Dict[Tuple[int, str], str]) -> str:
    return "".join(kd[k] for k in sorted_keys(kd))


def design_v3_pi(
    v2_vh: str,
    v2_vl: str,
    mouse_vh_kd: Dict[Tuple[int, str], str],
    mouse_vl_kd: Dict[Tuple[int, str], str],
    target_pi_max: float = 8.5,
    max_mutations: int = 4,
) -> Tuple[str, str, List[Dict[str, Any]]]:
    """
    Design v3 by lowering pI via FR-only charge reduction mutations.

    Invariants:
      - Never mutate Kabat CDR positions
      - Avoid Vernier positions (conservative)
      - Verify all 6 CDRs exactly match mouse after each change

    Returns:
        (v3_vh, v3_vl, mutations_v2_to_v3)

    Raises:
        RuntimeError: If Kabat numbering fails, pI computation fails,
            or design cannot reach target_pi_max (no safe mutations left).
    """
    vh_vernier = set(int(x) for x in VERNIER_KABAT_TO_IMGT_VH.keys())
    vl_vernier = set(int(x) for x in VERNIER_KABAT_TO_IMGT_VL.keys())

    vh_kd = get_kabat_numbering(v2_vh)
    vl_kd = get_kabat_numbering(v2_vl)
    if not vh_kd or not vl_kd:
        raise RuntimeError("Kabat numbering failed for v2; cannot design v3.")

    base_pi = _compute_pi(v2_vh, v2_vl)
    if base_pi is None:
        raise RuntimeError("Unable to compute pI (BioPython missing or bad sequence).")

    muts: List[Dict[str, Any]] = []

    def _candidate_positions(
        kd: Dict[Tuple[int, str], str], chain: str
    ) -> List[int]:
        out: List[int] = []
        vernier = vh_vernier if chain == "VH" else vl_vernier
        for (pos, ins), aa in kd.items():
            if ins != "":
                continue
            if aa not in ("K", "R"):
                continue
            if _in_cdr_kabat(pos, chain):
                continue
            if pos in vernier:
                continue
            out.append(pos)
        return sorted(set(out))

    vh_cands = _candidate_positions(vh_kd, "VH")
    vl_cands = _candidate_positions(vl_kd, "VL")

    current_vh_kd = dict(vh_kd)
    current_vl_kd = dict(vl_kd)
    current_pi = base_pi

    def _try_mut(
        chain: str, pos: int, new_aa: str
    ) -> Optional[Tuple[float, str, str, str]]:
        kd = current_vh_kd if chain == "VH" else current_vl_kd
        key = (pos, "")
        old = kd.get(key)
        if old is None or old == new_aa:
            return None
        if old not in ("K", "R"):
            return None

        kd2 = dict(kd)
        kd2[key] = new_aa

        if chain == "VH":
            vh_seq = _kabatdict_to_seq(kd2)
            vl_seq = _kabatdict_to_seq(current_vl_kd)
        else:
            vh_seq = _kabatdict_to_seq(current_vh_kd)
            vl_seq = _kabatdict_to_seq(kd2)

        vh_errs = verify_cdr_preservation(
            get_kabat_numbering(vh_seq), mouse_vh_kd, "VH"
        )
        vl_errs = verify_cdr_preservation(
            get_kabat_numbering(vl_seq), mouse_vl_kd, "VL"
        )
        if vh_errs or vl_errs:
            return None

        pi_val = _compute_pi(vh_seq, vl_seq)
        if pi_val is None:
            return None
        return (pi_val, vh_seq, vl_seq, old)

    palette = [("Q", 0), ("E", 1)]
    used: set[Tuple[str, int]] = set()

    for _round in range(max_mutations):
        if current_pi <= target_pi_max:
            break

        best = None  # (new_pi, chain, pos, new_aa, old_aa, new_vh, new_vl)

        for chain, cands in [("VH", vh_cands), ("VL", vl_cands)]:
            for pos in cands:
                if (chain, pos) in used:
                    continue
                old_aa = (
                    current_vh_kd if chain == "VH" else current_vl_kd
                ).get((pos, ""))
                if old_aa not in ("K", "R"):
                    continue
                for new_aa, _ in palette:
                    trial = _try_mut(chain, pos, new_aa)
                    if not trial:
                        continue
                    new_pi, new_vh, new_vl, old_aa_val = trial
                    if best is None or new_pi < best[0]:
                        best = (new_pi, chain, pos, new_aa, old_aa_val, new_vh, new_vl)

        if best is None:
            raise RuntimeError(
                f"No safe FR mutation found to lower pI. Current pI={current_pi:.2f}, "
                f"target≤{target_pi_max}."
            )

        new_pi, chain, pos, new_aa, old_aa, new_vh, new_vl = best
        if chain == "VH":
            current_vh_kd = get_kabat_numbering(new_vh)
        else:
            current_vl_kd = get_kabat_numbering(new_vl)
        current_pi = new_pi
        used.add((chain, pos))

        muts.append({
            "chain": chain,
            "kabat_pos": pos,
            "from": old_aa,
            "to": new_aa,
            "region": "FR（CMC）",
            "rationale": "pI ：/（ CDR）",
        })

    v3_vh = _kabatdict_to_seq(current_vh_kd)
    v3_vl = _kabatdict_to_seq(current_vl_kd)
    final_pi = _compute_pi(v3_vh, v3_vl)
    if final_pi is None:
        raise RuntimeError("Unable to compute final pI.")
    if final_pi > target_pi_max:
        raise RuntimeError(
            f"v3 design failed to reach target pI≤{target_pi_max}. Got pI={final_pi:.2f}."
        )
    return (v3_vh, v3_vl, muts)


def design_v3_liabilities(
    v2_vh: str,
    v2_vl: str,
    mouse_vh_kd: Dict[Tuple[int, str], str],
    mouse_vl_kd: Dict[Tuple[int, str], str],
    liabilities: List[Dict[str, Any]],
    fr_only: bool = True,
) -> Tuple[str, str, List[Dict[str, Any]]]:
    """
    Design v3 by mitigating CMC liabilities (N-gly, deamidation, isomerization).

    Strategy:
      - Map linear pos (VH+VL) to Kabat.
      - If fr_only=True, skip CDR positions.
      - Apply conservative mutations:
        - N-glycosylation (N[^P][ST]): N->Q (if N in FR) or S/T->A (if S/T in FR)
        - Deamidation (NG/NS): N->Q
        - Isomerization (DG/DS): D->E
      - Verify CDR preservation after each mutation.

    Returns:
        (v3_vh, v3_vl, mutations_list)
    """
    vh_vernier = set(int(x) for x in VERNIER_KABAT_TO_IMGT_VH.keys())
    vl_vernier = set(int(x) for x in VERNIER_KABAT_TO_IMGT_VL.keys())

    vh_kd = get_kabat_numbering(v2_vh)
    vl_kd = get_kabat_numbering(v2_vl)
    if not vh_kd or not vl_kd:
        # If numbering fails, return original
        return (v2_vh, v2_vl, [])

    vh_len = len(v2_vh)
    muts: List[Dict[str, Any]] = []

    # Working copies
    current_vh_kd = dict(vh_kd)
    current_vl_kd = dict(vl_kd)

    # Sort liabilities by pos to handle sequentially (though independent mutations usually ok)
    # We need to be careful if mutations shift indices, but here we work on Kabat which is stable
    # unless we insert/delete. Our mutations are substitutions.
    # However, input liabilities 'pos' are based on v2 input sequence.
    # Since we only do substitutions, length shouldn't change, so 'pos' remains valid.

    sorted_liabs = sorted(liabilities, key=lambda x: x.get("pos", -1))
    processed_sites = set()

    for item in sorted_liabs:
        typ = item.get("type")
        pos = item.get("pos")  # 0-based in VH+VL
        if pos is None:
            continue

        # Map to chain & Kabat
        if pos < vh_len:
            chain = "VH"
            seq_idx = pos
            target_kd = current_vh_kd
            ref_mouse_kd = mouse_vh_kd
            vernier = vh_vernier
        else:
            chain = "VL"
            seq_idx = pos - vh_len
            target_kd = current_vl_kd
            ref_mouse_kd = mouse_vl_kd
            vernier = vl_vernier

        # Find Kabat key for this seq_idx
        # We need to iterate sorted keys to find the n-th residue
        sorted_k = sorted_keys(target_kd)
        if seq_idx >= len(sorted_k):
            continue
        kabat_key = sorted_k[seq_idx]  # (pos_int, ins_str)
        kabat_pos_int = kabat_key[0]

        if (chain, kabat_key) in processed_sites:
            continue

        # Check FR/CDR
        is_cdr = _in_cdr_kabat(kabat_pos_int, chain)
        if fr_only and is_cdr:
            continue

        # Check Vernier (conservative: don't touch Vernier for auto-fix)
        if kabat_pos_int in vernier:
            continue

        # Determine mutation
        old_aa = target_kd[kabat_key]
        new_aa = None
        rationale = ""

        if typ == "N-glycosylation":
            # Pattern N[^P][ST]. The liability marks 'N'.
            # Common fix: N->Q (conservative) or N->D (risk of deamidation/isomerization)
            # We prefer N->Q.
            if old_aa == "N":
                new_aa = "Q"
                rationale = " N- (N→Q)"
        elif typ == "deamidation":
            # Pattern NG, NS. Liability marks 'N'.
            # Fix: N->Q
            if old_aa == "N":
                new_aa = "Q"
                rationale = " (N→Q)"
        elif typ == "isomerization":
            # Pattern DG, DS. Liability marks 'D'.
            # Fix: D->E (keep charge)
            if old_aa == "D":
                new_aa = "E"
                rationale = " (D→E)"

        if not new_aa or new_aa == old_aa:
            continue

        # Apply trial mutation
        backup_aa = target_kd[kabat_key]
        target_kd[kabat_key] = new_aa

        # Verify CDR preservation
        if chain == "VH":
            test_seq = _kabatdict_to_seq(target_kd)
            errs = verify_cdr_preservation(get_kabat_numbering(test_seq), ref_mouse_kd, "VH")
        else:
            test_seq = _kabatdict_to_seq(target_kd)
            errs = verify_cdr_preservation(get_kabat_numbering(test_seq), ref_mouse_kd, "VL")

        if errs:
            # Revert if validation fails
            target_kd[kabat_key] = backup_aa
            continue

        # Commit
        processed_sites.add((chain, kabat_key))
        muts.append({
            "chain": chain,
            "kabat_pos": kabat_pos_int,
            "from": old_aa,
            "to": new_aa,
            "region": "CDR" if is_cdr else "FR（CMC）",
            "rationale": rationale,
        })

    v3_vh = _kabatdict_to_seq(current_vh_kd)
    v3_vl = _kabatdict_to_seq(current_vl_kd)
    return (v3_vh, v3_vl, muts)
