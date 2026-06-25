"""
run_t3_v2.py — Generalized T3 Complex Quality Gate (V2)
========================================================
Version 2 upgrades the hard MAX_CLASHES=5 cutoff to a three-tier funnel:

  GREEN  (clash  0 –  5): immediate pass — no repair needed
  GRAY   (clash  6 – 15): attempted sidechain repair via EvoEF2 RepairStructure,
                           then re-check; pass if repaired clash ≤ 5
  RED    (clash > 15):     immediate reject — structural incompatibility too large

Scientific rationale:
- The original hard cutoff of >5 penalises large sidechains (Trp, Tyr, Arg)
  that often form the tightest interfaces in VHH-antigen complexes.
- Gray-zone molecules only need one sidechain rotamer adjustment to fit.
- Molecules with >15 clashes require backbone movements — out of scope for
  current fixed-backbone pipeline; reject and recover via co-design next round.

Usage:
    conda run -n affmat python pipeline/run_t3_v2.py --project_dir <path>

The script reads config from <project_dir>/config/mask_strategy.json
and writes results to <project_dir>/phase3_complex/.
"""

from __future__ import annotations

import argparse
import json
import os
import shutil
import subprocess
import sys
import tempfile
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import Bio.PDB as bpdb

# ── Clash tiers ───────────────────────────────────────────────────────────────
CLASH_GREEN_MAX  =  5    # 0-5:  direct pass
CLASH_GRAY_MAX   = 15    # 6-15: repair + recheck
# >15: immediate reject

VDW_RADII = {
    "C": 1.70, "N": 1.55, "O": 1.52, "S": 1.80, "P": 1.80,
    "F": 1.47, "CL": 1.75, "BR": 1.85, "I": 1.98, "H": 1.20,
}
CLASH_SCALE   = 0.80   # fraction of sum of radii that triggers a clash
OVERLAP_MIN   = 0.60   # minimum CDR-antigen contact fraction
CONTACT_DIST  = 8.0    # Å for contact/overlap check

# ── BLOSUM62 conservative substitution set ────────────────────────────────────
# Key = WT amino acid; value = set of acceptable substitutions (BLOSUM62 ≥ 1)
BLOSUM62_CONSERVATIVE: dict[str, set[str]] = {
    "A": {"A", "G", "S", "T", "V"},
    "C": {"C", "S"},
    "D": {"D", "E", "N"},
    "E": {"E", "D", "K", "Q"},
    "F": {"F", "Y", "W", "L"},
    "G": {"G", "A", "S"},
    "H": {"H", "N", "Q", "Y"},
    "I": {"I", "L", "M", "V"},
    "K": {"K", "E", "Q", "R"},
    "L": {"L", "I", "F", "M", "V"},
    "M": {"M", "I", "L", "V"},
    "N": {"N", "D", "H", "S"},
    "P": {"P"},
    "Q": {"Q", "E", "K", "R"},
    "R": {"R", "K", "Q"},
    "S": {"S", "A", "G", "N", "T"},
    "T": {"T", "A", "S", "V"},
    "V": {"V", "A", "I", "L", "M", "T"},
    "W": {"W", "F", "Y"},
    "Y": {"Y", "F", "H", "W"},
}


def is_conservative(wt_aa: str, mut_aa: str) -> bool:
    """Return True if mut_aa is a conservative substitution for wt_aa."""
    return mut_aa in BLOSUM62_CONSERVATIVE.get(wt_aa.upper(), {wt_aa.upper()})


# ── I/O helpers ───────────────────────────────────────────────────────────────

def timestamp() -> str:
    return datetime.now(timezone.utc).isoformat()


def load_fasta(path: Path) -> dict[str, str]:
    seqs: dict[str, str] = {}
    sid, buf = None, []
    for line in path.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if line.startswith(">"):
            if sid and buf:
                seqs[sid] = "".join(buf)
            sid = line[1:].split()[0]
            buf = []
        elif line and sid:
            buf.append(line.upper())
    if sid and buf:
        seqs[sid] = "".join(buf)
    return seqs


def write_fasta(seqs: dict[str, str], path: Path) -> None:
    path.write_text(
        "\n".join(f">{sid}\n{seq}" for sid, seq in seqs.items()) + "\n",
        encoding="utf-8",
    )


def append_jsonl(path: Path, record: dict) -> None:
    with path.open("a", encoding="utf-8") as f:
        f.write(json.dumps(record, ensure_ascii=False) + "\n")


def load_jsonl(path: Path) -> list[dict]:
    if not path.exists():
        return []
    return [
        json.loads(ln)
        for ln in path.read_text(encoding="utf-8").strip().split("\n")
        if ln.strip()
    ]


def latest_jsonl_by_seq_id(path: Path) -> dict[str, dict]:
    """Last record wins per seq_id (handles retries / duplicate lines)."""
    out: dict[str, dict] = {}
    for r in load_jsonl(path):
        sid = r.get("seq_id")
        if sid:
            out[sid] = r
    return out


def resolve_phase2_monomer_pdb(p2_dir: Path, sid: str) -> Path | None:
    """Phase 2 may write to monomer_pdbs/ (denovo) or structures/ (legacy)."""
    for sub in ("monomer_pdbs", "structures"):
        p = p2_dir / sub / f"{sid}.pdb"
        if p.is_file():
            return p
    return None


# ── VDW / clash helpers ───────────────────────────────────────────────────────

def vdw_radius(atom_name: str) -> float:
    elem = "".join(c for c in atom_name if c.isalpha()).upper()
    return VDW_RADII.get(elem[:1] if elem else "C", 1.70)


def count_clashes(cdr_atoms: list, ag_atoms: list, scale: float = CLASH_SCALE) -> int:
    n = 0
    for a1 in cdr_atoms:
        v1 = a1.get_vector()
        r1 = vdw_radius(a1.get_name())
        for a2 in ag_atoms:
            r2 = vdw_radius(a2.get_name())
            if (v1 - a2.get_vector()).norm() < scale * (r1 + r2):
                n += 1
    return n


def compute_overlap(cdr_res: list, ag_atoms: list, dist: float = CONTACT_DIST) -> float:
    if not cdr_res or not ag_atoms:
        return 0.0
    contacts = 0
    for res in cdr_res:
        for a1 in res.get_atoms():
            v1 = a1.get_vector()
            for a2 in ag_atoms:
                if (v1 - a2.get_vector()).norm() <= dist:
                    contacts += 1
                    break
            else:
                continue
            break
    return contacts / len(cdr_res)


# ── EvoEF2 gray-zone sidechain repair ────────────────────────────────────────

def repair_sidechains_evoef2(
    pdb_in: Path,
    evoef2_exe: str | None,
) -> Path | None:
    """
    Run EvoEF2 RepairStructure on pdb_in, returning path to repaired PDB.
    Returns None if EvoEF2 is not available or repair fails.
    """
    if not evoef2_exe or not Path(evoef2_exe).exists():
        return None

    with tempfile.TemporaryDirectory() as tmp:
        tmp_dir = Path(tmp)
        shutil.copy2(pdb_in, tmp_dir / pdb_in.name)
        try:
            result = subprocess.run(
                [evoef2_exe, "--command=RepairStructure",
                 f"--pdb={pdb_in.name}"],
                cwd=str(tmp_dir),
                capture_output=True, text=True, timeout=120,
            )
            if result.returncode != 0:
                return None
            repaired = tmp_dir / f"{pdb_in.stem}_Repair.pdb"
            if not repaired.exists():
                return None
            dest = pdb_in.parent / f"{pdb_in.stem}_repaired.pdb"
            shutil.copy2(repaired, dest)
            return dest
        except Exception:
            return None


# ── Root conservation check ───────────────────────────────────────────────────

def check_root_conservation(
    cand_seq: str,
    wt_seq: str,
    root_positions_0indexed: list[int],
    semiopen_positions_0indexed: list[int],
) -> tuple[bool, str]:
    """
    Verify:
      1. root_positions: must be identical to WT
      2. semiopen_positions: must be conservative substitution

    Returns (pass: bool, reason: str).
    """
    for pos in root_positions_0indexed:
        if pos >= len(cand_seq) or pos >= len(wt_seq):
            continue
        if cand_seq[pos] != wt_seq[pos]:
            return False, f"root_changed@{pos}({wt_seq[pos]}->{cand_seq[pos]})"

    for pos in semiopen_positions_0indexed:
        if pos >= len(cand_seq) or pos >= len(wt_seq):
            continue
        wt_aa = wt_seq[pos]
        cand_aa = cand_seq[pos]
        if cand_aa == wt_aa:
            continue
        if not is_conservative(wt_aa, cand_aa):
            return False, (
                f"non_conservative@{pos}({wt_aa}->{cand_aa})"
            )

    return True, "ok"


# ── Main T3 check ─────────────────────────────────────────────────────────────

def run_t3(
    project_dir: Path,
    evoef2_exe: str | None = None,
    design_cdr_key: str = "CDR3",
    use_root_check: bool = True,
) -> None:
    """
    Full T3 complex quality gate.

    Parameters
    ----------
    project_dir : Path to the project directory (contains config/ phase2/ phase3/).
    evoef2_exe  : Path to EvoEF2 executable for gray-zone repair.
    design_cdr_key : Which CDR was redesigned (used to define CDR atoms for clash).
    use_root_check : Whether to enforce root/semiopen conservation rules.
    """
    mask = json.loads((project_dir / "config" / "mask_strategy.json").read_text())
    ref_pdb_path = Path(mask["pdb_file"])
    wt_seq       = mask["wt_sequence"]
    vhh_chain    = mask.get("vhh_chain", "A")
    ag_chain     = mask.get("antigen_chain", "B")

    # CDR PDB residue numbers from mask (multi-CDR co-design → union)
    redesign_cdrs = mask.get("design_mask", {}).get("redesign_cdrs")
    if redesign_cdrs and len(redesign_cdrs) > 1:
        cdr_resnums: set[int] = set()
        root_pos_0: list[int] = []
        semi_pos_0: list[int] = []
        for ck in redesign_cdrs:
            cdr_resnums.update(mask["cdr_regions"][ck]["pdb_resnums"])
            rc = mask.get("root_constraints", {}).get(ck, {})
            root_pos_0.extend(rc.get("fixed_0indexed", []))
            semi_pos_0.extend(rc.get("semiopen_0indexed", []))
        root_pos_0 = sorted(set(root_pos_0))
        semi_pos_0 = sorted(set(semi_pos_0))
        print(f"[T3-V2] Multi-CDR mode: {redesign_cdrs} ({len(cdr_resnums)} PDB sites)")
    else:
        design_cdr   = mask["cdr_regions"][design_cdr_key]
        cdr_resnums  = set(design_cdr["pdb_resnums"])
        root_cfg     = mask.get("root_constraints", {}).get(design_cdr_key, {})
        root_pos_0   = root_cfg.get("fixed_0indexed", [])
        semi_pos_0   = root_cfg.get("semiopen_0indexed", [])

    # Framework residues: all non-CDR VHH residues (approximate)
    all_cdr_resnums: set[int] = set()
    for cdr in mask["cdr_regions"].values():
        all_cdr_resnums.update(cdr["pdb_resnums"])
    # Derive framework from structure itself
    parser = bpdb.PDBParser(QUIET=True)
    ref_struct = parser.get_structure("ref", str(ref_pdb_path))
    ref_model  = ref_struct[0]
    ref_vhh    = ref_model[vhh_chain]
    all_resids = {res.get_id()[1] for res in ref_vhh.get_residues() if "CA" in res}
    fw_resnums = all_resids - all_cdr_resnums
    ref_fw_cas = [
        res["CA"] for res in ref_vhh.get_residues()
        if res.get_id()[1] in fw_resnums and "CA" in res
    ]

    ag_atoms  = list(ref_model[ag_chain].get_atoms())
    ref_cdr_res = [r for r in ref_vhh.get_residues() if r.get_id()[1] in cdr_resnums]
    ref_overlap = compute_overlap(ref_cdr_res, ag_atoms)

    print(f"[T3-V2] Reference CDR overlap: {ref_overlap:.3f}")
    print(f"[T3-V2] Framework Cα: {len(ref_fw_cas)}, Antigen atoms: {len(ag_atoms)}")

    # Paths
    p2_dir   = project_dir / "phase2_structure"
    p3_dir   = project_dir / "phase3_complex"
    p3_dir.mkdir(parents=True, exist_ok=True)
    t2_jsonl = p2_dir / "t2_monomer_qc.jsonl"
    t3_jsonl = p3_dir / "t3_complex_qc.jsonl"

    t2_latest = latest_jsonl_by_seq_id(t2_jsonl)
    t2_passed = {sid for sid, r in t2_latest.items() if r.get("pass")}
    t3_latest = latest_jsonl_by_seq_id(t3_jsonl)

    # Load sequences (merge all available FASTAs for id lookup)
    seq_map: dict[str, str] = {}
    for fa_path in [
        project_dir / "phase1_generation" / "p2_input_topk.fasta",
        project_dir / "phase1_generation" / "t05_clustered.fasta",
        project_dir / "phase1_generation" / "clustered_diverse.fasta",
        project_dir / "phase1_generation" / "mpnn_raw_sequences.fasta",
    ]:
        if fa_path.exists():
            seq_map.update(load_fasta(fa_path))

    passed: dict[str, str] = {}
    gray_repaired: list[str] = []

    for sid in sorted(t2_passed):
        tr = t3_latest.get(sid)
        if tr and tr.get("pass") and sid in seq_map:
            passed[sid] = seq_map[sid]
            continue

        pdb_path = resolve_phase2_monomer_pdb(p2_dir, sid)
        if pdb_path is None:
            print(f"  [WARN] PDB not found for {sid} under monomer_pdbs/ or structures/")
            continue

        print(f"  {sid} ...", end=" ", flush=True)

        try:
            cand_struct = parser.get_structure(sid, str(pdb_path))
            cand_model  = cand_struct[0]
            try:
                cand_chain = cand_model[vhh_chain]
            except KeyError:
                cand_chain = list(cand_model.get_chains())[0]

            # Superimpose on framework Cα
            cand_cas = [
                res["CA"] for res in cand_chain.get_residues()
                if res.get_id()[1] in fw_resnums and "CA" in res
            ]
            n_fw = min(len(ref_fw_cas), len(cand_cas))
            if n_fw < 20:
                record = {
                    "seq_id": sid, "phase": "t3_complex_v2",
                    "pass": False, "reason": f"fw_ca_count={n_fw}",
                    "timestamp": timestamp(),
                }
                append_jsonl(t3_jsonl, record)
                print(f"FAIL (fw_ca={n_fw})")
                continue

            sup = bpdb.Superimposer()
            sup.set_atoms(ref_fw_cas[:n_fw], cand_cas[:n_fw])
            sup.apply(cand_model.get_atoms())
            fw_rmsd = float(sup.rms)

            # Collect CDR residues + atoms
            cdr_res   = [r for r in cand_chain.get_residues() if r.get_id()[1] in cdr_resnums]
            cdr_atoms = [a for r in cdr_res for a in r.get_atoms()]

            # ── TIER CHECK ────────────────────────────────────────────────────
            n_clash  = count_clashes(cdr_atoms, ag_atoms)
            tier     = "green" if n_clash <= CLASH_GREEN_MAX else (
                       "gray"  if n_clash <= CLASH_GRAY_MAX  else "red")
            overlap  = compute_overlap(cdr_res, ag_atoms)
            repaired = False

            if tier == "gray" and evoef2_exe:
                # Attempt sidechain repair
                repaired_pdb = repair_sidechains_evoef2(pdb_path, evoef2_exe)
                if repaired_pdb:
                    rep_struct = parser.get_structure(sid + "_rep", str(repaired_pdb))
                    rep_model  = rep_struct[0]
                    try:
                        rep_chain = rep_model[vhh_chain]
                    except KeyError:
                        rep_chain = list(rep_model.get_chains())[0]
                    # Re-superimpose repaired structure
                    rep_cas = [
                        res["CA"] for res in rep_chain.get_residues()
                        if res.get_id()[1] in fw_resnums and "CA" in res
                    ]
                    n_fw2 = min(len(ref_fw_cas), len(rep_cas))
                    if n_fw2 >= 20:
                        sup2 = bpdb.Superimposer()
                        sup2.set_atoms(ref_fw_cas[:n_fw2], rep_cas[:n_fw2])
                        sup2.apply(rep_model.get_atoms())
                        rep_cdr_res   = [r for r in rep_chain.get_residues()
                                         if r.get_id()[1] in cdr_resnums]
                        rep_cdr_atoms = [a for r in rep_cdr_res for a in r.get_atoms()]
                        n_clash_after = count_clashes(rep_cdr_atoms, ag_atoms)
                        if n_clash_after <= CLASH_GREEN_MAX:
                            n_clash  = n_clash_after
                            tier     = "green"
                            repaired = True
                            overlap  = compute_overlap(rep_cdr_res, ag_atoms)
                            gray_repaired.append(sid)
                            print(f"(repair: {n_clash_after}) ", end="", flush=True)

            if tier == "red":
                ok     = False
                reason = f"clash_red ({n_clash}>{CLASH_GRAY_MAX})"
            elif tier == "gray" and not repaired:
                ok     = False
                reason = f"clash_gray_unresolved ({n_clash}>{CLASH_GREEN_MAX})"
            elif overlap < OVERLAP_MIN:
                ok     = False
                reason = f"low_overlap ({overlap:.3f}<{OVERLAP_MIN:.3f})"
            else:
                ok = True
                reason = "ok"

            # ── Root conservation check ────────────────────────────────────
            root_ok, root_reason = True, "ok"
            if ok and use_root_check and sid in seq_map and (root_pos_0 or semi_pos_0):
                root_ok, root_reason = check_root_conservation(
                    seq_map[sid], wt_seq, root_pos_0, semi_pos_0
                )
                if not root_ok:
                    ok = False
                    reason = f"root_violation: {root_reason}"

            status = "PASS" if ok else "FAIL"
            print(
                f"fw_rmsd={fw_rmsd:.2f} clash={n_clash}"
                f"({tier}) overlap={overlap:.3f} → {status} {reason}"
            )

            record = {
                "seq_id":            sid,
                "phase":             "t3_complex_v2",
                "fw_rmsd":           round(fw_rmsd, 3),
                "n_clashes_cdr_ag":  n_clash,
                "clash_tier":        tier,
                "repaired":          repaired,
                "cdr_overlap":       round(overlap, 3),
                "ref_overlap":       round(ref_overlap, 3),
                "pass":              bool(ok),
                "reason":            reason,
                "timestamp":         timestamp(),
            }

        except Exception as exc:
            print(f"ERROR: {exc}")
            record = {
                "seq_id": sid, "phase": "t3_complex_v2",
                "pass": False, "reason": f"error: {exc}",
                "timestamp": timestamp(),
            }

        append_jsonl(t3_jsonl, record)
        if record.get("pass") and sid in seq_map:
            passed[sid] = seq_map[sid]

    # ── Write outputs ─────────────────────────────────────────────────────────
    write_fasta(passed, p3_dir / "t3_passed.fasta")

    t3_final = latest_jsonl_by_seq_id(t3_jsonl)
    ranked = sorted(
        [r for r in t3_final.values() if r.get("pass")],
        key=lambda r: (
            r.get("n_clashes_cdr_ag", 99),
            -r.get("cdr_overlap", 0.0),
            r.get("fw_rmsd", 99),
        ),
    )
    (p3_dir / "ranked_candidates.json").write_text(
        json.dumps(ranked, indent=2), encoding="utf-8"
    )

    total = len(t2_passed)
    n_pass = len(passed)
    n_gray_saved = len(gray_repaired)
    print(f"\n[T3-V2] {n_pass}/{total} pass"
          f" (including {n_gray_saved} gray-zone rescued via EvoEF2 repair)")
    if gray_repaired:
        print(f"  Gray-zone rescued: {gray_repaired}")
    print(f"  T3 FASTA: {p3_dir / 't3_passed.fasta'}")
    print(f"  Ranking:  {p3_dir / 'ranked_candidates.json'}")


# ── CLI ───────────────────────────────────────────────────────────────────────

def main() -> None:
    ap = argparse.ArgumentParser(description="T3 Complex Gate V2 — three-tier clash filter")
    ap.add_argument("--project_dir", required=True,
                    help="Project directory containing config/mask_strategy.json")
    ap.add_argument("--evoef2",  default=None,
                    help="Path to EvoEF2 executable (for gray-zone sidechain repair)")
    ap.add_argument("--design_cdr", default="CDR3",
                    help="CDR key that was redesigned (CDR2 / CDR3 / CDR2CDR3)")
    ap.add_argument("--skip_root_check", action="store_true",
                    help="Disable root / semiopen conservation check")
    args = ap.parse_args()

    run_t3(
        project_dir    = Path(args.project_dir),
        evoef2_exe     = args.evoef2,
        design_cdr_key = args.design_cdr,
        use_root_check = not args.skip_root_check,
    )


if __name__ == "__main__":
    os.environ["KMP_DUPLICATE_LIB_OK"] = "TRUE"
    main()
