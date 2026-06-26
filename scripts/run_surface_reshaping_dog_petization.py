"""
run_surface_reshaping_dog_petization.py
───────────────────────────────────────────────────────────────────────────────
AbEngineCore  (Surface Reshaping) 

:
  1.  NanoBodyBuilder2  donor PDB
  2. BioPython Shrake-Rupley SASA 
  3.  FR  (SASA > sasa_threshold Å²)
  4.  FR ：
       - CDR  (Kabat CDR )
       - Hallmark  (VHH FR2: E44/R45/G47 )
       -  Cys 
  5.  FR :  donor aa  dog top-freq aa
       -  dog  aa (freq >= threshold) → 
       -  →  dog  aa（，）
  6. : JSON  + 

 vs. Llamanade :
  - :  SASA ""，
  - Llamanade:  SASA， FR （）

Usage:
  python scripts/run_surface_reshaping_dog_petization.py \\
    --fasta  projects/anti_HSA_VHH_dog_petization/input/A6_A16_donor.fasta \\
    --pdb-dir projects/anti_HSA_VHH_dog_petization/structures \\
    --out    projects/anti_HSA_VHH_dog_petization/surface_reshaping/surface_reshaping_result.json
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
# CDR1: 26-32  CDR2: 52-56  CDR3: 95-102
_KABAT_CDR = (26, 32, 52, 56, 95, 102)

# VHH-specific hallmark positions (Kabat): canonical hydrophilic substitutions
# that stabilise the VHH scaffold and must NOT be surface-reshaped
_VHH_HALLMARKS_KABAT = {44, 45, 47}   # E44, R45, G47 in VHH

# Canonical disulfide Cys in VHH (Kabat 22 and 92)
_CANONICAL_CYS_KABAT = {22, 92}

# SASA threshold (Å²) — residue considered "surface exposed" if SASA > this
_SASA_THRESHOLD_A2 = 20.0   # conservative; typical buried < 5, exposed > 30


def _load_dog_profile(path: Path) -> dict[str, dict[str, float]]:
    data = json.loads(path.read_text(encoding="utf-8"))
    positions: dict[str, dict[str, float]] = {}
    for pos_key, aa_map in data["positions"].items():
        positions[pos_key] = dict(
            sorted(aa_map.items(), key=lambda kv: kv[1], reverse=True)
        )
    return positions


def _compute_sasa(pdb_path: str) -> dict[int, float]:
    """Return {seq_resnum: sasa_A2} using Shrake-Rupley on first chain."""
    from Bio.PDB import PDBParser
    from Bio.PDB.SASA import ShrakeRupley

    parser = PDBParser(QUIET=True)
    structure = parser.get_structure("nb", pdb_path)
    model = structure[0]
    chain = list(model.get_chains())[0]

    sr = ShrakeRupley()
    sr.compute(structure, level="R")

    sasa_map: dict[int, float] = {}
    for res in chain.get_residues():
        resnum = res.get_id()[1]
        sasa_map[resnum] = res.sasa
    return sasa_map


def _number_seq(seq: str) -> list[dict] | None:
    """Run anarcii in Kabat scheme. Returns list of {pos, ins, aa}."""
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


def surface_reshape(
    seq: str,
    pdb_path: str,
    freq_threshold: float = 0.10,
    sasa_threshold: float = _SASA_THRESHOLD_A2,
) -> dict:
    """Apply structure-guided surface reshaping for dog petization."""

    # 1. Kabat numbering
    rows = _number_seq(seq)
    if rows is None:
        return {"error": f"Numbering failed for: {seq[:30]}"}

    # 2. SASA from structure
    sasa_map = _compute_sasa(pdb_path)

    # Map: Kabat sequential position → SASA (approx: PDB residue number ≈ sequential)
    # NanoBodyBuilder2 PDB residue numbers match the input sequence 1-indexed positions
    seq_len = len(seq)
    # Build mapping: numbered_index (1-based order) → SASA
    sasa_by_seq_idx: dict[int, float] = {}
    for i in range(1, seq_len + 1):
        sasa_by_seq_idx[i] = sasa_map.get(i, 0.0)

    # Also track the sequential index in numbered rows
    seq_idx = 1  # 1-based counter into original sequence
    for r in rows:
        r["seq_idx"] = seq_idx
        r["sasa"] = sasa_by_seq_idx.get(seq_idx, 0.0)
        seq_idx += 1

    # 3. Load dog profile
    dog_profile = _load_dog_profile(DOG_PROFILE)

    # 4. CDR positions (Kabat)
    c1s, c1e, c2s, c2e, c3s, c3e = _KABAT_CDR
    cdr_keys: set[str] = set()
    for r in rows:
        p = r["pos"]
        if c1s <= p <= c1e or c2s <= p <= c2e or c3s <= p <= c3e:
            cdr_keys.add(_kabat_key(r))

    per_pos: list[dict] = []
    reshaped_aa_list: list[str] = []
    mutations: list[str] = []

    for r in rows:
        kk = _kabat_key(r)
        orig = r["aa"]
        sasa = r["sasa"]

        # CDR lock
        if kk in cdr_keys:
            per_pos.append({"kabat_key": kk, "original_aa": orig, "reshaped_aa": orig,
                            "action": "CDR_LOCK", "sasa": sasa, "reason": "CDR region"})
            reshaped_aa_list.append(orig)
            continue

        # Canonical Cys
        if r["pos"] in _CANONICAL_CYS_KABAT or orig == "C":
            per_pos.append({"kabat_key": kk, "original_aa": orig, "reshaped_aa": orig,
                            "action": "CYS_PROTECT", "sasa": sasa, "reason": f"Cys conserved"})
            reshaped_aa_list.append(orig)
            continue

        # VHH hallmark
        if r["pos"] in _VHH_HALLMARKS_KABAT:
            per_pos.append({"kabat_key": kk, "original_aa": orig, "reshaped_aa": orig,
                            "action": "HALLMARK_PROTECT", "sasa": sasa,
                            "reason": f"VHH hallmark Kabat {r['pos']}"})
            reshaped_aa_list.append(orig)
            continue

        # Buried — keep
        if sasa < sasa_threshold:
            per_pos.append({"kabat_key": kk, "original_aa": orig, "reshaped_aa": orig,
                            "action": "BURIED_KEEP",
                            "sasa": sasa,
                            "reason": f"Buried: SASA={sasa:.1f} < {sasa_threshold}"})
            reshaped_aa_list.append(orig)
            continue

        # Surface-exposed FR position: evaluate against dog profile
        pos_profile = dog_profile.get(kk, {})
        if not pos_profile:
            per_pos.append({"kabat_key": kk, "original_aa": orig, "reshaped_aa": orig,
                            "action": "KEEP_NO_DATA",
                            "sasa": sasa,
                            "reason": f"No dog data for pos {kk}"})
            reshaped_aa_list.append(orig)
            continue

        dog_freq = pos_profile.get(orig, 0.0)

        if dog_freq >= freq_threshold:
            per_pos.append({"kabat_key": kk, "original_aa": orig, "reshaped_aa": orig,
                            "action": "SURFACE_FREQ_OK",
                            "sasa": sasa,
                            "reason": f"Surface exposed, dog_freq={dog_freq:.3f} >= {freq_threshold}"})
            reshaped_aa_list.append(orig)
        else:
            top_dog_aa = next(iter(pos_profile))
            top_freq = list(pos_profile.values())[0]
            per_pos.append({"kabat_key": kk, "original_aa": orig, "reshaped_aa": top_dog_aa,
                            "action": "SURFACE_SUBSTITUTE",
                            "sasa": sasa,
                            "reason": f"Surface SASA={sasa:.1f}; dog_freq={dog_freq:.3f}<{freq_threshold}; "
                                      f"top_dog={top_dog_aa}(freq={top_freq:.3f})"})
            reshaped_aa_list.append(top_dog_aa)
            mutations.append(f"{orig}{kk}{top_dog_aa}")

    reshaped_seq = "".join(reshaped_aa_list)

    n_surface = sum(1 for p in per_pos if p["action"] in ("SURFACE_FREQ_OK", "SURFACE_SUBSTITUTE", "KEEP_NO_DATA"))
    n_buried = sum(1 for p in per_pos if p["action"] == "BURIED_KEEP")

    return {
        "method": "surface_reshaping_dog_petization",
        "sasa_threshold_A2": sasa_threshold,
        "freq_threshold": freq_threshold,
        "pdb_source": pdb_path,
        "original_seq": seq,
        "reshaped_seq": reshaped_seq,
        "seq_identity_pct": round(
            sum(a == b for a, b in zip(seq, reshaped_seq)) / max(len(seq), 1) * 100, 1
        ),
        "n_positions_total": len(rows),
        "n_surface_exposed": n_surface,
        "n_buried": n_buried,
        "n_substituted": len(mutations),
        "mutations": mutations,
        "per_position": per_pos,
        "dog_profile_source": str(DOG_PROFILE.relative_to(REPO)),
        "algorithm_note": (
            "Structure-guided surface reshaping: BioPython Shrake-Rupley SASA on "
            f"NanoBodyBuilder2 PDB. Only surface-exposed FR residues (SASA > {sasa_threshold} Å²) "
            "are candidates for dog germline substitution. CDRs, Cys, VHH hallmarks "
            "(E44/R45/G47) are protected regardless of SASA. Buried FR residues are "
            "never substituted even if low dog-frequency."
        ),
    }


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--fasta",       "-f", required=True)
    ap.add_argument("--pdb-dir",     "-p", required=True,
                    help="Directory containing <ID>_donor.pdb files")
    ap.add_argument("--freq-threshold",  type=float, default=0.10)
    ap.add_argument("--sasa-threshold",  type=float, default=_SASA_THRESHOLD_A2)
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

        print(f"\n[{seq_id}] Surface reshaping from {pdb_file.name} ({len(seq)} aa)...",
              flush=True)
        res = surface_reshape(
            seq=seq,
            pdb_path=str(pdb_file),
            freq_threshold=args.freq_threshold,
            sasa_threshold=args.sasa_threshold,
        )
        results[seq_id] = res

        if "error" not in res:
            print(f"  Original : {res['original_seq']}")
            print(f"  Reshaped : {res['reshaped_seq']}")
            print(f"  Identity : {res['seq_identity_pct']}%")
            print(f"  Surface residues: {res['n_surface_exposed']}  |  Buried: {res['n_buried']}")
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
