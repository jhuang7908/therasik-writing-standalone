"""
DeepFR-CTX-Pet — shared protection rules and 9-mer optimization for dog/cat petization.

Pipeline phases (v2.8.0):
  P1 graft baseline
  P2 structure gate (optional PDB locks)
  P3 pet 9-mer contextual voting (dog_9mer_v1 / cat_9mer_v1)
  P4 Pet-native Guard (9-mer self-consistency + hard structural veto)
  P5 CMC micro-tune (FR-only, structure-respecting)
  P6 conserved-Cys validation

Guards against modifying:
  - CDR regions
  - Canonical intra-domain disulfide Cys (VH 22/92, VL 23/88)
  - Any existing Cys in framework (never introduce/remove Cys)
  - Vernier / activity anchor positions
"""
from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Dict, List, Optional, Set, Tuple

from anarci import anarci

from core.humanization.kabat_utils import get_kabat_numbering, sorted_keys

ALGORITHM_ID = "deepfr-ctx-pet"
PROTOCOL_VERSION = "2.8.0"
DISPLAY_NAME = "DeepFR-CTX-Pet"
PIPELINE_PHASES = [
    "P1_graft",
    "P2_structure_gate",
    "P3_pet_9mer_ctx",
    "P4_pet_native_guard",
    "P5_cmc_tune",
    "P6_validation",
]

SUITE_ROOT = Path(__file__).resolve().parents[2]
PET_9MER_DB: Dict[str, Path] = {
    "dog": SUITE_ROOT / "data/reference/pet_9mer_db/dog_9mer_v1.json",
    "cat": SUITE_ROOT / "data/reference/pet_9mer_db/cat_9mer_v1.json",
}
DOG_9MER_DB_PATH = PET_9MER_DB["dog"]

AMINO_ACIDS = list("ACDEFGHIKLMNPQRSTVWY")

# Kabat canonical intra-domain disulfide partners
CANONICAL_CYS_KABAT: Dict[str, Set[int]] = {
    "VH": {22, 92},
    "VL": {23, 88},
}

VERNIER_VH: Set[int] = {2, 27, 28, 29, 30, 47, 48, 49, 67, 69, 71, 73, 78, 93, 94}
VERNIER_VL: Set[int] = {2, 4, 36, 46, 49, 69, 71, 98}

CDR_RANGES: Dict[str, List[Tuple[int, int]]] = {
    "VH": [(26, 35), (50, 65), (95, 102)],
    "VL": [(24, 34), (50, 56), (89, 97)],
}

# Dog J-segment FR4 tails (appended after variable region design)
DOG_FR4: Dict[str, str] = {
    "VH": "WGQGTLVTVSS",
    "VL_KAPPA": "FGQGTKVELK",
    "VL_LAMBDA": "FGGGTHLTVL",
}


def get_kabat_dict(seq: str) -> Optional[Dict[Tuple[int, str], str]]:
    results = anarci([("seq", seq)], scheme="kabat")
    if not results[0] or not results[0][0]:
        return None
    numbering = results[0][0][0][0]
    return {(pos, ins.strip()): aa for (pos, ins), aa in numbering}


def is_in_cdr(pos: int, chain: str) -> bool:
    for lo, hi in CDR_RANGES[chain]:
        if lo <= pos <= hi:
            return True
    return False


def protected_kabat_positions(chain: str, extra_anchors: Optional[Dict[int, str]] = None) -> Set[int]:
    """Return Kabat positions that must never be modified by 9-mer voting."""
    vernier = VERNIER_VH if chain == "VH" else VERNIER_VL
    protected = set(vernier) | CANONICAL_CYS_KABAT[chain]
    if extra_anchors:
        protected |= set(extra_anchors.keys())
    return protected


def is_position_locked(
    pos: int,
    chain: str,
    current_aa: str,
    extra_anchors: Optional[Dict[int, str]] = None,
    struct_lock_kabat: Optional[Set[int]] = None,
) -> bool:
    if is_in_cdr(pos, chain):
        return True
    if pos in protected_kabat_positions(chain, extra_anchors):
        return True
    if struct_lock_kabat and pos in struct_lock_kabat:
        return True
    # Any framework Cys — hard lock (canonical or not)
    if current_aa == "C":
        return True
    return False


def is_ctx_eligible(
    pos: int,
    chain: str,
    struct_eligible_kabat: Optional[Set[int]] = None,
) -> bool:
    """When structure guidance is active, only these FR positions may be voted."""
    if struct_eligible_kabat is None:
        return True
    return pos in struct_eligible_kabat


def enforce_canonical_cys(kd: Dict[Tuple[int, str], str], chain: str) -> None:
    """Force C at canonical disulfide positions (in-place)."""
    for pos in CANONICAL_CYS_KABAT[chain]:
        key = (pos, "")
        if key in kd or any(k[0] == pos for k in kd):
            kd[key] = "C"


def validate_conserved_cys(seq: str, chain: str) -> List[str]:
    """Return list of errors; empty if both canonical Cys present."""
    kd = get_kabat_dict(seq)
    if not kd:
        return [f"{chain}: Kabat numbering failed"]
    errors: List[str] = []
    for pos in CANONICAL_CYS_KABAT[chain]:
        aa = kd.get((pos, ""))
        if aa != "C":
            errors.append(f"{chain} Kabat {pos}: expected C, found {aa!r}")
    n_cys = sum(1 for aa in kd.values() if aa == "C")
    if n_cys != 2:
        errors.append(f"{chain}: expected 2 Cys total, found {n_cys}")
    return errors


def load_pet_9mer_db(species: str = "dog", path: Optional[Path] = None) -> Dict[str, int]:
    sp = (species or "dog").strip().lower()
    db_path = path or PET_9MER_DB.get(sp)
    if db_path is None or not db_path.is_file():
        raise FileNotFoundError(f"Pet 9-mer DB not found for species={species!r}")
    with open(db_path, encoding="utf-8") as f:
        data = json.load(f)
    return data["nine_mer_counts"]


def load_dog_9mer_db(path: Path = DOG_9MER_DB_PATH) -> Dict[str, int]:
    return load_pet_9mer_db("dog", path)


def _would_create_n_glyc(seq: str, idx: int) -> bool:
    """Check N-X-S/T motif spanning position idx (X != P)."""
    for start in range(max(0, idx - 2), min(len(seq) - 2, idx + 1)):
        tri = seq[start : start + 3]
        if len(tri) == 3 and tri[0] == "N" and tri[1] != "P" and tri[2] in "ST":
            return True
    return False


def design_deepfr_ctx_chain(
    donor_seq: str,
    scaffold_seq: str,
    chain: str,
    anchors: Optional[Dict[int, str]] = None,
    db: Optional[Dict[str, int]] = None,
    vote_threshold: int = 10,
    struct_lock_kabat: Optional[Set[int]] = None,
    struct_eligible_kabat: Optional[Set[int]] = None,
) -> Tuple[str, List[dict], Dict[str, Any]]:
    """
    Graft donor CDRs onto dog scaffold FR, then apply 9-mer contextual optimization.

    When struct_eligible_kabat is provided, 9-mer voting is restricted to those
    Kabat positions (structure-guided surface reshaping mode).

    Returns (variable_region_seq_without_FR4, changes, meta).
    """
    anchors = anchors or {}
    db = db or load_dog_9mer_db()
    meta: Dict[str, Any] = {
        "structure_guided": struct_eligible_kabat is not None,
        "n_struct_locked": len(struct_lock_kabat or set()),
        "n_struct_eligible": len(struct_eligible_kabat or set()),
    }

    donor_kd = get_kabat_dict(donor_seq)
    scaffold_kd = get_kabat_dict(scaffold_seq)
    if not donor_kd or not scaffold_kd:
        raise RuntimeError(f"Kabat numbering failed for {chain}")

    grafted_kd: Dict[Tuple[int, str], str] = {}
    all_pos = sorted(set(donor_kd.keys()) | set(scaffold_kd.keys()))

    for k in all_pos:
        pos, _ins = k
        if is_in_cdr(pos, chain):
            grafted_kd[k] = donor_kd.get(k, "-")
        elif pos in anchors:
            grafted_kd[k] = anchors[pos]
        elif pos in CANONICAL_CYS_KABAT[chain]:
            # Prefer donor Cys, else scaffold, else force C
            grafted_kd[k] = donor_kd.get(k) or scaffold_kd.get(k) or "C"
        else:
            grafted_kd[k] = scaffold_kd.get(k, "-")

    enforce_canonical_cys(grafted_kd, chain)

    sorted_k = sorted_keys(grafted_kd)
    graft_baseline_body = "".join(grafted_kd[k] for k in sorted_k if grafted_kd[k] != "-")
    current_seq = graft_baseline_body
    final_seq_list = list(current_seq)
    changes: List[dict] = []

    for i, k in enumerate(sorted_k):
        pos, ins = k
        original_aa = grafted_kd[k]
        if original_aa == "-":
            continue
        # Map Kabat key to linear index in gap-stripped sequence
        linear_i = sum(
            1 for j in range(i) if grafted_kd[sorted_k[j]] != "-"
        )
        if is_position_locked(pos, chain, original_aa, anchors, struct_lock_kabat):
            continue
        if not is_ctx_eligible(pos, chain, struct_eligible_kabat):
            continue

        scores: Dict[str, int] = {}
        for aa in AMINO_ACIDS:
            if aa == "C":
                continue  # never introduce Cys via voting
            temp_seq = current_seq[:linear_i] + aa + current_seq[linear_i + 1 :]
            start_idx = max(0, linear_i - 8)
            end_idx = min(len(temp_seq) - 9, linear_i)
            votes = sum(db.get(temp_seq[j : j + 9], 0) for j in range(start_idx, end_idx + 1))
            scores[aa] = votes

        ranked = sorted(scores.items(), key=lambda x: x[1], reverse=True)
        top_aa, top_votes = ranked[0]
        original_votes = scores.get(original_aa, 0)

        if top_aa == original_aa or top_votes <= original_votes or top_votes < vote_threshold:
            continue

        candidate = "".join(final_seq_list[:linear_i]) + top_aa + "".join(final_seq_list[linear_i + 1 :])
        if _would_create_n_glyc(candidate, linear_i):
            continue

        final_seq_list[linear_i] = top_aa
        changes.append({
            "pos": f"{pos}{ins}",
            "old": original_aa,
            "new": top_aa,
            "votes_old": original_votes,
            "votes_new": top_votes,
        })

    result = "".join(final_seq_list)
    errors = validate_conserved_cys(result, chain)
    if errors:
        raise RuntimeError(f"DeepFR-CTX-Pet validation failed for {chain}: {'; '.join(errors)}")
    meta["n_substitutions"] = len(changes)
    meta["graft_baseline_body"] = graft_baseline_body
    return result, changes, meta


def _kabat_pos_for_index(seq: str, index_1: int) -> Optional[int]:
    kd = get_kabat_numbering(seq)
    if not kd:
        return None
    keys = sorted_keys(kd)
    i0 = int(index_1) - 1
    if 0 <= i0 < len(keys):
        return keys[i0][0]
    return None


def _nine_mer_votes(seq: str, linear_i: int, db: Dict[str, int]) -> int:
    start_idx = max(0, linear_i - 8)
    end_idx = min(len(seq) - 9, linear_i)
    if end_idx < start_idx:
        return 0
    return sum(db.get(seq[j : j + 9], 0) for j in range(start_idx, end_idx + 1))


def _hard_veto_mutation(seq: str, linear_i: int, old_aa: str, new_aa: str) -> Optional[str]:
    if old_aa == new_aa:
        return None
    if new_aa == "C" or (old_aa == "C" and new_aa != "C"):
        return "cys_change"
    if old_aa in {"P", "G"} or new_aa in {"P", "G"}:
        return "pro_gly"
    candidate = seq[:linear_i] + new_aa + seq[linear_i + 1 :]
    if _would_create_n_glyc(candidate, linear_i):
        return "n_glyc_motif"
    return None


def apply_pet_native_guard(
    optimized_body: str,
    graft_baseline_body: str,
    chain: str,
    *,
    species: str = "dog",
    db: Optional[Dict[str, int]] = None,
    vote_threshold: int = 10,
    extra_anchors: Optional[Dict[int, str]] = None,
    struct_lock_kabat: Optional[Set[int]] = None,
) -> Tuple[str, List[Dict[str, Any]], Dict[str, Any]]:
    """
    Pet-native Guard: re-check P3 FR substitutions against the pet 9-mer library.

    Roll back to graft baseline when:
      - hard structural/CMC veto (Cys, Pro/Gly, N-glyc motif), or
      - pet 9-mer votes for the substitution do not beat graft AA (or fall below threshold).

    Does NOT use human clinical_842 or human OAS — insufficient canine/feline repertoire data.
    """
    if len(optimized_body) != len(graft_baseline_body):
        raise ValueError(
            f"{chain}: length mismatch optimized ({len(optimized_body)}) "
            f"vs graft ({len(graft_baseline_body)})"
        )
    db = db or load_pet_9mer_db(species)
    kd = get_kabat_numbering(optimized_body)
    if not kd:
        raise RuntimeError(f"Pet-native guard: Kabat numbering failed for {chain}")

    keys = sorted_keys(kd)
    seq_list = list(optimized_body)
    rollbacks: List[Dict[str, Any]] = []

    for linear_i, key in enumerate(keys):
        pos, ins = key
        graft_aa = graft_baseline_body[linear_i]
        opt_aa = optimized_body[linear_i]
        if graft_aa == opt_aa:
            continue
        if is_in_cdr(pos, chain):
            continue

        veto = _hard_veto_mutation(graft_baseline_body, linear_i, graft_aa, opt_aa)
        if veto:
            seq_list[linear_i] = graft_aa
            rollbacks.append({
                "pos": f"{pos}{ins}",
                "graft_aa": graft_aa,
                "optimized_aa": opt_aa,
                "reason": veto,
                "decision": "ROLLBACK",
            })
            continue

        graft_votes = _nine_mer_votes(graft_baseline_body, linear_i, db)
        opt_seq = graft_baseline_body[:linear_i] + opt_aa + graft_baseline_body[linear_i + 1 :]
        opt_votes = _nine_mer_votes(opt_seq, linear_i, db)

        if opt_votes <= graft_votes or opt_votes < vote_threshold:
            seq_list[linear_i] = graft_aa
            rollbacks.append({
                "pos": f"{pos}{ins}",
                "graft_aa": graft_aa,
                "optimized_aa": opt_aa,
                "votes_graft": graft_votes,
                "votes_optimized": opt_votes,
                "vote_threshold": vote_threshold,
                "reason": "insufficient_pet_9mer_support",
                "decision": "ROLLBACK",
            })

    guarded_body = "".join(seq_list)
    meta: Dict[str, Any] = {
        "guard_type": "pet_native",
        "species": species,
        "nine_mer_db": PET_9MER_DB.get(species.lower(), DOG_9MER_DB_PATH).name,
        "n_rollbacks": len(rollbacks),
        "vote_threshold": vote_threshold,
    }
    return guarded_body, rollbacks, meta


def _cmc_site_allowed(
    site: Dict[str, Any],
    seq: str,
    chain: str,
    extra_anchors: Optional[Dict[int, str]],
    struct_lock_kabat: Optional[Set[int]],
    struct_eligible_kabat: Optional[Set[int]],
) -> bool:
    idx1 = site.get("index_1")
    if idx1 is None:
        return False
    i0 = int(idx1) - 1
    if not (0 <= i0 < len(seq)):
        return False
    kabat = _kabat_pos_for_index(seq, int(idx1))
    if kabat is None:
        return False
    aa = seq[i0]
    if is_position_locked(kabat, chain, aa, extra_anchors, struct_lock_kabat):
        return False
    if struct_eligible_kabat is not None and kabat not in struct_eligible_kabat:
        return False
    to_aa = str(site.get("to_aa_hint") or "").strip().upper()
    if not to_aa or len(to_aa) != 1:
        return False
    if aa in {"C", "P", "G"} or to_aa in {"C", "P", "G"}:
        return False
    candidate = seq[:i0] + to_aa + seq[i0 + 1 :]
    if _would_create_n_glyc(candidate, i0):
        return False
    return True


def _collect_cmc_sites(payload: Dict[str, Any]) -> List[Dict[str, Any]]:
    sites: List[Dict[str, Any]] = []
    for key in (
        "fr_positive_charge_sites",
        "fr_negative_charge_sites",
        "fr_instability_sites",
    ):
        sites.extend(payload.get(key) or [])
    for run in payload.get("fr_hydrophobic_runs") or []:
        sites.extend(run.get("per_residue") or [])
    return sites


def apply_cmc_micro_tune(
    vh: str,
    vl: str,
    *,
    pdb_path: Optional[Path] = None,
    vh_anchors: Optional[Dict[int, str]] = None,
    vh_lock: Optional[Set[int]] = None,
    vl_lock: Optional[Set[int]] = None,
    vh_eligible: Optional[Set[int]] = None,
    vl_eligible: Optional[Set[int]] = None,
    max_mutations: int = 3,
) -> Tuple[str, str, List[Dict[str, Any]], Dict[str, Any]]:
    """Apply up to ``max_mutations`` FR-only CMC suggestions respecting structure locks."""
    from core.cmc.fr_mutation_sites import apply_mutations_to_sequence
    from core.evaluation.cmc_advisor_module import run_cmc_advisor

    vh_cur = (vh or "").strip().upper()
    vl_cur = (vl or "").strip().upper()
    pdb_str = str(pdb_path) if pdb_path and pdb_path.is_file() else None

    cmc_before = run_cmc_advisor(vh_cur, vl_cur, structure_path=pdb_str)
    meta: Dict[str, Any] = {
        "cmc_before": cmc_before.get("status"),
        "mutations_applied": [],
        "skipped": False,
    }
    if cmc_before.get("status") == "PASS":
        meta["skipped"] = True
        meta["reason"] = "no_tune_needed"
        return vh_cur, vl_cur, [], meta
    if cmc_before.get("status") in ("SKIPPED", "ERROR"):
        meta["skipped"] = True
        meta["reason"] = cmc_before.get("reason") or cmc_before.get("status")
        return vh_cur, vl_cur, [], meta

    from core.cmc.fr_mutation_sites import build_candidate_payload_for_metric

    # Build actionable list from annotated metrics (re-query with PDB when available)
    failing: List[Tuple[str, str, str]] = []
    for metric, info in (cmc_before.get("metrics") or {}).items():
        if not isinstance(info, dict):
            continue
        gate = info.get("gate")
        if gate not in ("FAIL", "WARN"):
            continue
        val = info.get("value")
        ref_p95 = info.get("ref_p95")
        ref_p5 = info.get("ref_p5")
        if ref_p95 is not None and val is not None and float(val) > float(ref_p95):
            failing.append((metric, "too_high", gate))
        elif ref_p5 is not None and val is not None and float(val) < float(ref_p5):
            failing.append((metric, "too_low", gate))
        else:
            failing.append((metric, "too_high" if gate == "FAIL" else "too_low", gate))

    failing.sort(key=lambda x: (0 if x[2] == "FAIL" else 1, x[0]))

    applied: List[Dict[str, Any]] = []
    for metric, direction, gate in failing:
        if len(applied) >= max_mutations:
            break
        payload = build_candidate_payload_for_metric(
            metric, direction, vh_cur, vl_cur, pdb_str
        )
        if payload.get("patch_is_cdr_driven"):
            continue
        for site in _collect_cmc_sites(payload):
            if len(applied) >= max_mutations:
                break
            chain = site.get("chain", "")
            if chain == "VH":
                seq = vh_cur
                elig, lock, anchors = vh_eligible, vh_lock, vh_anchors
                chain_id = "VH"
            elif chain == "VL":
                seq = vl_cur
                elig, lock, anchors = vl_eligible, vl_lock, {}
                chain_id = "VL"
            else:
                continue
            if not _cmc_site_allowed(site, seq, chain_id, anchors, lock, elig):
                continue
            idx1 = int(site["index_1"])
            i0 = idx1 - 1
            old_aa = seq[i0]
            new_aa = str(site["to_aa_hint"]).upper()
            if chain == "VH":
                vh_cur = vh_cur[:i0] + new_aa + vh_cur[i0 + 1 :]
            else:
                vl_cur = vl_cur[:i0] + new_aa + vl_cur[i0 + 1 :]
            kabat = _kabat_pos_for_index(seq, idx1)
            applied.append({
                "chain": chain,
                "index_1": idx1,
                "kabat": kabat,
                "old": old_aa,
                "new": new_aa,
                "metric": metric,
                "gate": gate,
            })

    for chain_id, seq in [("VH", vh_cur), ("VL", vl_cur)]:
        errs = validate_conserved_cys(seq, chain_id)
        if errs:
            raise RuntimeError(f"CMC tune broke Cys on {chain_id}: {'; '.join(errs)}")

    cmc_after = run_cmc_advisor(vh_cur, vl_cur, structure_path=pdb_str)
    meta["cmc_after"] = cmc_after.get("status")
    meta["mutations_applied"] = applied
    meta["n_applied"] = len(applied)
    return vh_cur, vl_cur, applied, meta


def run_deepfr_ctx_pet_chain(
    donor_seq: str,
    scaffold_seq: str,
    chain: str,
    fr4: str,
    *,
    species: str = "dog",
    germline: str = "",
    anchors: Optional[Dict[int, str]] = None,
    db: Optional[Dict[str, int]] = None,
    vote_threshold: int = 10,
    struct_lock_kabat: Optional[Set[int]] = None,
    struct_eligible_kabat: Optional[Set[int]] = None,
    apply_pet_guard: bool = True,
) -> Tuple[str, Dict[str, Any]]:
    """Full per-chain DeepFR-CTX-Pet pipeline through P4 (Pet-native Guard)."""
    db = db or load_pet_9mer_db(species)
    body, ctx_changes, design_meta = design_deepfr_ctx_chain(
        donor_seq,
        scaffold_seq,
        chain,
        anchors=anchors,
        db=db,
        vote_threshold=vote_threshold,
        struct_lock_kabat=struct_lock_kabat,
        struct_eligible_kabat=struct_eligible_kabat,
    )
    graft_body = design_meta["graft_baseline_body"]

    pipeline_meta: Dict[str, Any] = {
        "protocol_version": PROTOCOL_VERSION,
        "algorithm_id": ALGORITHM_ID,
        "species": species,
        "phases": list(PIPELINE_PHASES),
        "ctx_voting": {
            "changes": ctx_changes,
            **design_meta,
        },
    }

    if apply_pet_guard:
        guarded_body, rollbacks, guard_meta = apply_pet_native_guard(
            body,
            graft_body,
            chain,
            species=species,
            db=db,
            vote_threshold=vote_threshold,
            extra_anchors=anchors,
            struct_lock_kabat=struct_lock_kabat,
        )
        pipeline_meta["pet_native_guard"] = {
            "rollbacks": rollbacks,
            **guard_meta,
        }
        final_body = guarded_body
    else:
        final_body = body
        pipeline_meta["pet_native_guard"] = {"skipped": True}

    final_full = final_body + fr4
    errs = validate_conserved_cys(final_full, chain)
    if errs:
        raise RuntimeError(f"{chain} post-guard validation: {'; '.join(errs)}")

    pipeline_meta["final_body"] = final_body
    if germline:
        pipeline_meta["germline"] = germline
    return final_full, pipeline_meta
