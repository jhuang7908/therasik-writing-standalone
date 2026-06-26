"""
run_deep_freq_petization.py
───────────────────────────────────────────────────────────────────────────────
Deep Frequency-Guided (Structurally Protected) Dog Petization for VHH.

This method replaces the previous "Llamanade-style" name to better reflect its algorithm.
It is a frequency-driven approach (Track B) but incorporates strict structural
protections to make it VHH-safe.

Algorithm:
  1. Read donor sequence and PDB.
  2. Kabat numbering + SASA calculation + CDR distance calculation.
  3. Strict Protections:
     - CDR regions (Kabat definition).
     - VHH Hallmarks: 37, 44, 45, 47.
     - Canonical / All Cys residues.
     - Deep buried residues: SASA < 5.0 Å².
     - CDR-proximal residues: Minimum heavy-atom distance to any CDR < 5.0 Å.
  4. For the remaining FR positions, compare against dog IGHV Kabat profile:
     - If donor freq >= freq_threshold (0.10) → Keep.
     - Else → Substitute with the highest-frequency dog germline residue.

Usage:
  python scripts/run_deep_freq_petization.py \
    --fasta  projects/anti_HSA_VHH_dog_petization/input/A6_A16_donor.fasta \
    --pdb-dir projects/anti_HSA_VHH_dog_petization/structures \
    --out    projects/anti_HSA_VHH_dog_petization/deep_freq/deep_freq_result.json
"""
from __future__ import annotations

import argparse
import json
import os
import sys
from pathlib import Path

os.environ.setdefault("KMP_DUPLICATE_LIB_OK", "TRUE")

REPO = Path(__file__).resolve().parents[1]
DOG_PROFILE = REPO / "data/reference/pet_replacement_profiles/v2/dog_ighv_aa_freq_kabat_v2.json"

# ─── Kabat CDR boundaries (VHH, standard) ─────────────────────────────────
_KABAT_CDR = (26, 32, 52, 56, 95, 102)

# VHH-specific hallmark positions (Kabat)
_VHH_HALLMARKS_KABAT = {37, 44, 45, 47}

# Canonical disulfide Cys in VHH
_CANONICAL_CYS_KABAT = {22, 92}

# Protection Thresholds
_DEEP_BURIED_SASA_THRESHOLD = 5.0    # Å²
_CDR_PROXIMAL_DIST_THRESHOLD = 5.0   # Å (heavy atom distance)


def _load_dog_profile(path: Path) -> dict[str, dict[str, float]]:
    data = json.loads(path.read_text(encoding="utf-8"))
    positions: dict[str, dict[str, float]] = {}
    for pos_key, aa_map in data["positions"].items():
        positions[pos_key] = dict(
            sorted(aa_map.items(), key=lambda kv: kv[1], reverse=True)
        )
    return positions


def _compute_sasa_and_distance(pdb_path: str, cdr_resnums: set[int]) -> tuple[dict[int, float], dict[int, float]]:
    """Return {seq_resnum: sasa_A2} and {seq_resnum: min_dist_to_cdr}."""
    from Bio.PDB import PDBParser
    from Bio.PDB.SASA import ShrakeRupley

    parser = PDBParser(QUIET=True)
    structure = parser.get_structure("nb", pdb_path)
    model = structure[0]
    chain = list(model.get_chains())[0]

    sr = ShrakeRupley()
    sr.compute(structure, level="R")

    sasa_map: dict[int, float] = {}
    residues = list(chain.get_residues())
    
    for res in residues:
        resnum = res.get_id()[1]
        sasa_map[resnum] = res.sasa

    # Calculate min distance to CDRs
    cdr_residues = [r for r in residues if r.get_id()[1] in cdr_resnums]
    non_cdr_residues = [r for r in residues if r.get_id()[1] not in cdr_resnums]
    
    dist_map: dict[int, float] = {}
    
    if not cdr_residues:
        for r in non_cdr_residues:
            dist_map[r.get_id()[1]] = 999.0
        return sasa_map, dist_map

    for r in non_cdr_residues:
        min_d = 999.0
        # Compute min heavy atom distance
        for atom in r.get_atoms():
            if atom.element == 'H': continue
            for cdr_r in cdr_residues:
                for cdr_atom in cdr_r.get_atoms():
                    if cdr_atom.element == 'H': continue
                    d = atom - cdr_atom
                    if d < min_d:
                        min_d = d
        dist_map[r.get_id()[1]] = min_d
        
    for r in cdr_residues:
        dist_map[r.get_id()[1]] = 0.0

    return sasa_map, dist_map


def _number_seq(seq: str) -> list[dict] | None:
    import contextlib, io
    try:
        from anarcii import Anarcii
    except ImportError:
        raise RuntimeError("anarcii not found")

    seq = "".join(seq.upper().split())
    runner = Anarcii()
    with contextlib.redirect_stdout(io.StringIO()):
        runner.number(seq)
        result = runner.to_scheme("kabat")

    seq_data = list(result.values())[0] if result else {}
    numbered = seq_data.get("numbering", [])
    rows: list[dict] = []
    for (pos_int, ins_code), aa in numbered:
        if aa == "-" or aa is None:
            continue
        rows.append({"pos": int(pos_int), "ins": str(ins_code).strip().upper(), "aa": aa})
    return rows if rows else None


def _kabat_key(row: dict) -> str:
    return str(row["pos"]) + row["ins"]


def deep_freq_reshape(
    seq: str,
    pdb_path: str,
    freq_threshold: float = 0.10,
) -> dict:
    """Apply Deep Frequency-Guided petization with VHH-safe structural protection."""
    
    rows = _number_seq(seq)
    if rows is None:
        return {"error": f"Numbering failed for: {seq[:30]}"}

    c1s, c1e, c2s, c2e, c3s, c3e = _KABAT_CDR
    cdr_keys: set[str] = set()
    cdr_seq_indices: set[int] = set()
    
    seq_idx = 1
    for r in rows:
        p = r["pos"]
        if c1s <= p <= c1e or c2s <= p <= c2e or c3s <= p <= c3e:
            cdr_keys.add(_kabat_key(r))
            cdr_seq_indices.add(seq_idx)
        seq_idx += 1

    sasa_map, dist_map = _compute_sasa_and_distance(pdb_path, cdr_seq_indices)

    seq_idx = 1
    for r in rows:
        r["seq_idx"] = seq_idx
        r["sasa"] = float(sasa_map.get(seq_idx, 0.0))
        r["cdr_dist"] = float(dist_map.get(seq_idx, 999.0))
        seq_idx += 1

    dog_profile = _load_dog_profile(DOG_PROFILE)

    per_pos: list[dict] = []
    reshaped_aa_list: list[str] = []
    mutations: list[str] = []

    for r in rows:
        kk = _kabat_key(r)
        orig = r["aa"]
        sasa = r["sasa"]
        dist = r["cdr_dist"]

        # 1. CDR lock
        if kk in cdr_keys:
            per_pos.append({"kabat_key": kk, "original_aa": orig, "reshaped_aa": orig,
                            "action": "CDR_LOCK", "sasa": sasa, "cdr_dist": dist, "reason": "CDR region"})
            reshaped_aa_list.append(orig)
            continue

        # 2. Canonical Cys
        if r["pos"] in _CANONICAL_CYS_KABAT or orig == "C":
            per_pos.append({"kabat_key": kk, "original_aa": orig, "reshaped_aa": orig,
                            "action": "STRUCT_PROTECT", "sasa": sasa, "cdr_dist": dist, "reason": "Cys conserved"})
            reshaped_aa_list.append(orig)
            continue

        # 3. VHH hallmark (37, 44, 45, 47)
        if r["pos"] in _VHH_HALLMARKS_KABAT:
            per_pos.append({"kabat_key": kk, "original_aa": orig, "reshaped_aa": orig,
                            "action": "STRUCT_PROTECT", "sasa": sasa, "cdr_dist": dist,
                            "reason": f"VHH hallmark Kabat {r['pos']}"})
            reshaped_aa_list.append(orig)
            continue

        # 4. Deep Buried (SASA < 5.0)
        if sasa < _DEEP_BURIED_SASA_THRESHOLD:
            per_pos.append({"kabat_key": kk, "original_aa": orig, "reshaped_aa": orig,
                            "action": "STRUCT_PROTECT", "sasa": sasa, "cdr_dist": dist,
                            "reason": f"Deep buried: SASA={sasa:.1f} < {_DEEP_BURIED_SASA_THRESHOLD}"})
            reshaped_aa_list.append(orig)
            continue

        # 5. CDR-Proximal (Distance < 5.0)
        if dist < _CDR_PROXIMAL_DIST_THRESHOLD:
            per_pos.append({"kabat_key": kk, "original_aa": orig, "reshaped_aa": orig,
                            "action": "STRUCT_PROTECT", "sasa": sasa, "cdr_dist": dist,
                            "reason": f"CDR proximal: dist={dist:.1f} < {_CDR_PROXIMAL_DIST_THRESHOLD}"})
            reshaped_aa_list.append(orig)
            continue

        # Frequency Check
        pos_profile = dog_profile.get(kk, {})
        if not pos_profile:
            per_pos.append({"kabat_key": kk, "original_aa": orig, "reshaped_aa": orig,
                            "action": "KEEP_NO_DATA", "sasa": sasa, "cdr_dist": dist,
                            "reason": f"No dog data for pos {kk}"})
            reshaped_aa_list.append(orig)
            continue

        dog_freq = pos_profile.get(orig, 0.0)

        if dog_freq >= freq_threshold:
            per_pos.append({"kabat_key": kk, "original_aa": orig, "reshaped_aa": orig,
                            "action": "FREQ_OK", "sasa": sasa, "cdr_dist": dist,
                            "reason": f"dog_freq={dog_freq:.3f} >= {freq_threshold}"})
            reshaped_aa_list.append(orig)
        else:
            top_dog_aa = next(iter(pos_profile))
            top_freq = list(pos_profile.values())[0]
            per_pos.append({"kabat_key": kk, "original_aa": orig, "reshaped_aa": top_dog_aa,
                            "action": "SUBSTITUTE", "sasa": sasa, "cdr_dist": dist,
                            "reason": f"dog_freq={dog_freq:.3f}<{freq_threshold}; top_dog={top_dog_aa}(freq={top_freq:.3f})"})
            reshaped_aa_list.append(top_dog_aa)
            mutations.append(f"{orig}{kk}{top_dog_aa}")

    reshaped_seq = "".join(reshaped_aa_list)

    return {
        "method": "deep_freq_guided_petization",
        "freq_threshold": freq_threshold,
        "pdb_source": pdb_path,
        "original_seq": seq,
        "reshaped_seq": reshaped_seq,
        "seq_identity_pct": round(
            sum(a == b for a, b in zip(seq, reshaped_seq)) / max(len(seq), 1) * 100, 1
        ),
        "n_positions_total": len(rows),
        "n_substituted": len(mutations),
        "n_struct_protected": sum(1 for p in per_pos if p["action"] == "STRUCT_PROTECT"),
        "mutations": mutations,
        "per_position": per_pos,
        "dog_profile_source": str(DOG_PROFILE.relative_to(REPO)),
        "algorithm_note": (
            "Deep Frequency-Guided Petization: A frequency-driven approach with "
            "strict structural protections. Substitutes FR residues with top dog "
            "germline frequency if donor frequency < threshold. Protects CDRs, Cys, "
            "VHH hallmarks (37,44,45,47), deep buried sites (SASA < 5.0 Å²), and "
            "CDR-proximal sites (distance < 5.0 Å)."
        ),
    }


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--fasta",       "-f", required=True)
    ap.add_argument("--pdb-dir",     "-p", required=True)
    ap.add_argument("--freq-threshold",  type=float, default=0.10)
    ap.add_argument("--out",         "-o", default=None)
    args = ap.parse_args()

    fasta_path = Path(args.fasta)
    lines = [l.strip() for l in fasta_path.read_text(encoding="utf-8").splitlines() if l.strip()]

    records: list[tuple[str, str]] = []
    current_id, current_seq = "", []
    for line in lines:
        if line.startswith(">"):
            if current_id:
                records.append((current_id, "".join(current_seq)))
            current_id = line[1:].split("|")[0].strip()
            current_seq = []
        else:
            current_seq.append(line.upper())
    if current_id:
        records.append((current_id, "".join(current_seq)))

    results: dict[str, dict] = {}
    for seq_id, seq in records:
        pdb_file = Path(args.pdb_dir) / f"{seq_id}_donor.pdb"
        if not pdb_file.is_file():
            print(f"[{seq_id}] PDB not found: {pdb_file}", file=sys.stderr)
            results[seq_id] = {"error": f"PDB not found: {pdb_file}"}
            continue

        print(f"\n[{seq_id}] Deep Frequency-Guided petization from {pdb_file.name} ({len(seq)} aa)...",
              flush=True)
        res = deep_freq_reshape(
            seq=seq,
            pdb_path=str(pdb_file),
            freq_threshold=args.freq_threshold,
        )
        results[seq_id] = res

        if "error" not in res:
            print(f"  Original : {res['original_seq']}")
            print(f"  Reshaped : {res['reshaped_seq']}")
            print(f"  Identity : {res['seq_identity_pct']}%")
            print(f"  Struct Protected: {res['n_struct_protected']}")
            print(f"  Substituted: {res['n_substituted']}  Mutations: {', '.join(res['mutations'])}")
        else:
            print("  ERROR:", res["error"])

    if args.out:
        out_path = Path(args.out)
        out_path.parent.mkdir(parents=True, exist_ok=True)
        out_path.write_text(json.dumps(results, indent=2, ensure_ascii=False), encoding="utf-8")
        print(f"\nResults written to {out_path}")


if __name__ == "__main__":
    main()
