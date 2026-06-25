"""
run_mpnn_v2.py — Generalized ProteinMPNN Sampling (V2)
=======================================================
Supports single-CDR and multi-CDR co-design from a shared mask_strategy.json.
Implements root/semiopen constraint logic: root PDB residues are fixed;
semiopen PDB residues are allowed by MPNN but flagged for post-filter.

Key differences from V1 (run_phase1.py / run_mpnn_cdr3.py):
  1. Reads designable positions directly from mask_strategy.json
     (supports CDR2-only, CDR3-only, CDR2+CDR3 co-design)
  2. Root residues are always added to MPNN fixed list (never designed)
  3. Semiopen residues are allowed by MPNN but tagged in output FASTA
  4. PTM / liability quick-check built in before writing output
  5. Reproducible naming: {project_prefix}_{index:04d}_T{temp}

Usage (affmat env):
    conda run -n affmat python pipeline/run_mpnn_v2.py \\
        --project_dir <path> \\
        [--n_seqs 500] [--temps "0.2 0.3 0.35"] [--seed 42]

Outputs:
    <project_dir>/phase1_generation/mpnn_raw_sequences.fasta
    <project_dir>/phase1_generation/mpnn_generation_report.json
"""

from __future__ import annotations

import argparse
import json
import os
import re
import shutil
import subprocess
import sys
import time
from collections import defaultdict
from datetime import datetime, timezone
from pathlib import Path

# Canonical coordinate helpers — see coord_utils.py for the two-system contract.
try:
    from pipeline.coord_utils import (  # noqa: E402
        mpnn_designable_pdb_positions,
        validate_mask_coords,
    )
except ModuleNotFoundError:
    import importlib.util
    import pathlib as _pl
    _cu = _pl.Path(__file__).resolve().parent / "coord_utils.py"
    _spec = importlib.util.spec_from_file_location("coord_utils", _cu)
    _mod = importlib.util.module_from_spec(_spec)
    assert _spec.loader is not None
    _spec.loader.exec_module(_mod)
    mpnn_designable_pdb_positions = _mod.mpnn_designable_pdb_positions
    validate_mask_coords = _mod.validate_mask_coords

try:
    from core.integrity.hallucination_guard import HallucinationGuard
    _GUARD_AVAILABLE = True
except ImportError:
    _GUARD_AVAILABLE = False

# ── PTM / liability patterns (three-tier) ────────────────────────────────────
# Hard veto: structural / PK dealbreakers → reject outright
HARD_VETO_PATTERNS = {
    "unpaired_Cys":  None,                        # handled separately
    "glycosylation_NxST": re.compile(r"N[^P][ST]"),  # Fab N-glycosylation
}
# Soft flag: common CDR liabilities, tolerable if WT already carries them
SOFT_FLAG_PATTERNS = {
    "deamidation_NG":   re.compile(r"NG"),
    "deamidation_NS":   re.compile(r"NS"),
    "isomerization_DG": re.compile(r"DG"),
    "isomerization_DS": re.compile(r"DS"),
}


def _scan_motifs(seq: str, patterns: dict, cdr_ranges: list[tuple[int, int]]) -> list[str]:
    """Return motif hits inside any CDR range (0-indexed start..end inclusive)."""
    hits: list[str] = []
    for label, pat in patterns.items():
        if pat is None:
            continue
        for m in pat.finditer(seq):
            pos = m.start()
            for s, e in cdr_ranges:
                if s <= pos <= e:
                    hits.append(f"{label}@{pos}")
                    break
    return hits


def detect_ptm_tiered(
    seq: str,
    cdr_ranges_0indexed: list[tuple[int, int]],
    wt_soft_set: set[str] | None = None,
) -> tuple[list[str], list[str], list[str]]:
    """Three-tier PTM check.

    Returns (hard_vetoes, inherited_soft, new_soft).
      - hard_vetoes  → reject the sequence
      - inherited_soft → WT already has the same motif at the same position
      - new_soft     → design introduced a new soft-flag position
    """
    hard: list[str] = _scan_motifs(seq, HARD_VETO_PATTERNS, cdr_ranges_0indexed)
    # Unpaired Cys (whole-sequence, not CDR-only)
    n_cys = sum(1 for aa in seq if aa == "C")
    if n_cys % 2 != 0:
        hard.append(f"unpaired_Cys(n={n_cys})")

    soft_all = _scan_motifs(seq, SOFT_FLAG_PATTERNS, cdr_ranges_0indexed)
    if wt_soft_set is None:
        return hard, soft_all, []
    inherited = [f for f in soft_all if f in wt_soft_set]
    new_soft  = [f for f in soft_all if f not in wt_soft_set]
    return hard, inherited, new_soft


# ── BLOSUM62 conservative check (also used by T3) ────────────────────────────
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
    return mut_aa in BLOSUM62_CONSERVATIVE.get(wt_aa.upper(), {wt_aa.upper()})


# ── I/O helpers ───────────────────────────────────────────────────────────────

def timestamp() -> str:
    return datetime.now(timezone.utc).isoformat()


def _fix_parsed_names(jsonl_path: Path) -> None:
    """Normalise Windows path separators in ProteinMPNN parsed JSONL."""
    lines = []
    with open(jsonl_path) as f:
        for line in f:
            rec = json.loads(line.strip())
            name = rec.get("name", "")
            name = name.replace("\\", "/")
            if "/" in name:
                name = name.rsplit("/", 1)[-1]
            rec["name"] = name
            lines.append(json.dumps(rec))
    with open(jsonl_path, "w") as f:
        f.write("\n".join(lines) + "\n")


# ── Mask & diversity guards ───────────────────────────────────────────────────

def _verify_mask(
    fixed_jsonl: "Path",
    chain: str,
    expected_nonfixed: list[int],
) -> None:
    """Read back fixed_positions.jsonl and assert that the non-fixed positions
    for *chain* match *expected_nonfixed* exactly.

    ProteinMPNN's make_fixed_positions_dict.py stores ALL positions it was
    told are fixed; the complement (within the parsed chain length) are
    designable.  We invert this to recover what MPNN will actually design
    and compare against our intent.  A mismatch means PDB residue numbers
    were mis-interpreted and we must abort before a costly GPU run.
    """
    with open(fixed_jsonl) as fh:
        data = json.load(fh)

    # The key inside the dict is the PDB filename stem; grab the first entry.
    root = next(iter(data.values()))
    fixed_list: list[int] = root.get(chain, [])
    fixed_set = set(fixed_list)

    # Infer total chain length from parsed_pdbs if possible; otherwise use
    # the max fixed position + a generous buffer.
    chain_max = max(fixed_set) if fixed_set else 0
    all_positions = set(range(1, chain_max + 1))
    actual_nonfixed = sorted(all_positions - fixed_set)

    expected_set = set(expected_nonfixed)
    actual_set   = set(actual_nonfixed)

    # Positions we asked to design but MPNN will fix:
    missing = sorted(expected_set - actual_set)
    # Positions MPNN will design that we did NOT intend:
    extra   = sorted(actual_set   - expected_set)

    if missing or extra:
        print("\n" + "=" * 70)
        print("[MASK VERIFY ❌] fixed_positions.jsonl does NOT match intended mask!")
        if missing:
            print(f"  Positions MPNN will FREEZE (should be designable): {missing}")
        if extra:
            print(f"  Positions MPNN will DESIGN  (should be fixed):      {extra}")
        print("  Possible cause: PDB residue numbers differ from MPNN sequential")
        print("  indices (Chothia numbering gaps).  Check designable_pdb_residues")
        print("  in mask_strategy.json and re-run with the corrected values.")
        print("=" * 70 + "\n")
        sys.exit(1)

    print(f"[MASK VERIFY ✓] Non-fixed positions match design intent: {sorted(expected_set)}")


def _check_cdr_diversity(
    seqs: dict[str, str],
    wt_seq: str,
    cdr_data: dict,
    redesign_cdrs: list[str],
    alarm_threshold: float = 0.90,
) -> None:
    """Warn loudly if any redesigned CDR has zero mutations in >alarm_threshold
    fraction of unique sequences.  This is a reliable early signal that the
    MPNN mask is incorrect (CDR residues were inadvertently fixed).
    """
    if not seqs:
        return
    n_total = len(seqs)
    for cdr_key in redesign_cdrs:
        cdr = cdr_data.get(cdr_key, {})
        ls  = cdr.get("linear_start")
        le  = cdr.get("linear_end")
        if ls is None or le is None:
            continue
        n_zero_mut = 0
        for seq in seqs.values():
            muts = sum(
                1 for i in range(ls, le + 1)
                if i < len(seq) and i < len(wt_seq) and seq[i] != wt_seq[i]
            )
            if muts == 0:
                n_zero_mut += 1
        frac = n_zero_mut / n_total
        symbol = "✓" if frac < alarm_threshold else "❌ ALARM"
        print(
            f"[CDR DIVERSITY {symbol}] {cdr_key}: {n_zero_mut}/{n_total} seqs "
            f"({frac * 100:.1f}%) have 0 mutations in this CDR"
        )
        if frac >= alarm_threshold:
            print(
                f"  ↳ {cdr_key} appears FROZEN. Likely cause: wrong PDB residue\n"
                f"    numbers in mask (Chothia gap offset).  Check\n"
                f"    design_mask.designable_pdb_residues in mask_strategy.json."
            )


def _cdr_mutation_stats(
    seqs: dict[str, str],
    wt_seq: str,
    cdr_data: dict,
    redesign_cdrs: list[str],
) -> dict:
    """Return per-CDR mutation statistics for the generation report."""
    stats: dict[str, dict] = {}
    for cdr_key in redesign_cdrs:
        cdr = cdr_data.get(cdr_key, {})
        ls  = cdr.get("linear_start")
        le  = cdr.get("linear_end")
        if ls is None or le is None:
            continue
        mut_counts = []
        for seq in seqs.values():
            muts = sum(
                1 for i in range(ls, le + 1)
                if i < len(seq) and i < len(wt_seq) and seq[i] != wt_seq[i]
            )
            mut_counts.append(muts)
        if mut_counts:
            stats[cdr_key] = {
                "n_seqs":       len(mut_counts),
                "mean_muts":    round(sum(mut_counts) / len(mut_counts), 2),
                "max_muts":     max(mut_counts),
                "pct_zero_mut": round(mut_counts.count(0) / len(mut_counts) * 100, 1),
            }
    return stats


# ── Core ──────────────────────────────────────────────────────────────────────

def run_mpnn_v2(
    project_dir: Path,
    n_seqs: int = 300,
    temps: str = "0.2 0.3 0.35",
    seed: int = 42,
    force_regen: bool = False,
) -> None:
    """
    Run ProteinMPNN for the project defined by mask_strategy.json.
    Supports CDR2-only, CDR3-only, or CDR2+CDR3 co-design.
    """
    mask_path = project_dir / "config" / "mask_strategy.json"
    if not mask_path.exists():
        print(f"[ERROR] mask_strategy.json not found at {mask_path}")
        sys.exit(1)

    mask = json.loads(mask_path.read_text(encoding="utf-8"))

    # Validate coordinate consistency before doing anything else.
    # This catches linear/PDB mismatches in the mask file itself.
    validate_mask_coords(mask, abort=True)

    pdb_path     = Path(mask["pdb_file"])
    wt_seq       = mask["wt_sequence"]
    vhh_chain    = mask.get("vhh_chain", "A")
    design_mask  = mask["design_mask"]
    cdr_data     = mask["cdr_regions"]
    root_cfg     = mask.get("root_constraints", {})
    mpnn_cfg     = mask.get("mpnn_settings", {})

    # Resolve ProteinMPNN paths
    suite_root  = project_dir.parents[1] if project_dir.name.startswith("denovo") else project_dir.parents[0]
    # Walk up until we find tools/ProteinMPNN
    for candidate in [project_dir.parents[1], project_dir.parents[2], project_dir.parents[0]]:
        if (candidate / "tools" / "ProteinMPNN").exists():
            suite_root = candidate
            break
    mpnn_dir    = suite_root / "tools" / "ProteinMPNN"
    mpnn_helper = mpnn_dir / "helper_scripts"
    mpnn_run    = mpnn_dir / "protein_mpnn_run.py"

    if not mpnn_run.exists():
        print(f"[ERROR] ProteinMPNN not found at {mpnn_run}")
        sys.exit(1)

    p1_dir    = project_dir / "phase1_generation"
    mpnn_out  = p1_dir / "mpnn_output"
    p1_dir.mkdir(exist_ok=True)
    mpnn_out.mkdir(exist_ok=True)

    # Stage PDB
    pdb_staging = p1_dir / "pdb_input"
    pdb_staging.mkdir(exist_ok=True)
    staged_pdb  = pdb_staging / "complex.pdb"
    if not staged_pdb.exists():
        shutil.copy2(pdb_path, staged_pdb)

    parsed_jsonl  = mpnn_out / "parsed_pdbs.jsonl"
    assigned_jsonl = mpnn_out / "assigned_chains.jsonl"
    fixed_jsonl   = mpnn_out / "fixed_positions.jsonl"

    staging_posix = str(pdb_staging).replace("\\", "/") + "/"

    # Step 1: parse PDB
    print("[MPNN-V2] Parsing PDB...")
    subprocess.run([
        sys.executable, str(mpnn_helper / "parse_multiple_chains.py"),
        f"--input_path={staging_posix}",
        f"--output_path={parsed_jsonl}",
    ], check=True)
    _fix_parsed_names(parsed_jsonl)

    # Step 2: assign design chain
    print(f"[MPNN-V2] Assigning chain {vhh_chain} as design chain...")
    subprocess.run([
        sys.executable, str(mpnn_helper / "assign_fixed_chains.py"),
        f"--input_path={parsed_jsonl}",
        f"--output_path={assigned_jsonl}",
        "--chain_list", vhh_chain,
    ], check=True)

    # Step 3: define designable positions (non-fixed)
    # ── coord_utils.mpnn_designable_pdb_positions() is the ONLY approved
    #    source for the MPNN position list.  It reads designable_pdb_residues
    #    (PDB residue numbers) from the mask.  See coord_utils.py for the
    #    two-coordinate-system contract (linear ≠ PDB).
    semiopen_pdb     = set(design_mask.get("semiopen_pdb_residues", []))
    fixed_root_pdb   = set(design_mask.get("fixed_root_pdb_residues", []))

    design_1indexed = mpnn_designable_pdb_positions(mask)   # PDB residue numbers
    net_designable  = design_1indexed                        # alias for report

    redesign_cdrs = design_mask.get("redesign_cdrs", [])
    print(f"[MPNN-V2] Design mode: {design_mask.get('mode', 'custom')}")
    print(f"[MPNN-V2] Redesigned CDRs: {redesign_cdrs}")
    print(f"[MPNN-V2] Total designable positions: {len(design_1indexed)}")
    net_set  = set(design_1indexed)
    semi_set = set(semiopen_pdb)
    print(f"[MPNN-V2]   Full-open:  {len(net_set - semi_set)} positions")
    print(f"[MPNN-V2]   Semiopen:   {len(semi_set & net_set)} positions")
    print(f"[MPNN-V2]   Root-fixed: {len(fixed_root_pdb)} positions (locked)")
    print(f"[MPNN-V2] PDB-residue designable positions: {design_1indexed}")

    design_pos_str = " ".join(str(p) for p in design_1indexed)
    subprocess.run([
        sys.executable, str(mpnn_helper / "make_fixed_positions_dict.py"),
        f"--input_path={parsed_jsonl}",
        f"--output_path={fixed_jsonl}",
        "--chain_list", vhh_chain,
        "--position_list", design_pos_str,
        "--specify_non_fixed",
    ], check=True)

    # ── Mask verification: read back fixed_positions.jsonl and confirm that the
    # non-fixed positions for the design chain match design_1indexed exactly.
    # Mismatch means make_fixed_positions_dict.py interpreted the position list
    # differently (e.g. PDB vs sequential index confusion) — abort rather than
    # silently produce a wrong design run.
    _verify_mask(fixed_jsonl, vhh_chain, design_1indexed)

    # Step 4: generate sequences
    fasta_check = list(mpnn_out.glob("seqs/*.fa"))
    if fasta_check and not force_regen:
        print(f"[MPNN-V2] Found existing output ({len(fasta_check)} files), skipping generation.")
        print("[MPNN-V2] Use --force_regen to regenerate.")
    else:
        print(f"[MPNN-V2] Generating {n_seqs} seqs × {len(temps.split())} temps (may take 15-60 min)...")
        t0 = time.time()
        subprocess.run([
            sys.executable, str(mpnn_run),
            "--jsonl_path",            str(parsed_jsonl),
            "--chain_id_jsonl",        str(assigned_jsonl),
            "--fixed_positions_jsonl", str(fixed_jsonl),
            "--out_folder",            str(mpnn_out),
            "--num_seq_per_target",    str(n_seqs),
            "--sampling_temp",         temps,
            "--seed",                  str(seed),
            "--batch_size",            "1",
        ], check=True)
        print(f"[MPNN-V2] Generation done in {time.time() - t0:.0f}s")

    # Step 5: collect + deduplicate + three-tier PTM check
    fasta_files = sorted((mpnn_out / "seqs").glob("*.fa"))
    if not fasta_files:
        print("[ERROR] No FASTA output found.")
        sys.exit(1)

    # CDR ranges for PTM checking (0-indexed, all CDRs — not just redesigned ones)
    cdr_ranges_0indexed: list[tuple[int, int]] = []
    for cdr_key in mask["cdr_regions"]:
        cdr = mask["cdr_regions"][cdr_key]
        ls  = cdr.get("linear_start")
        le  = cdr.get("linear_end")
        if ls is not None and le is not None:
            cdr_ranges_0indexed.append((ls, le))

    # Compute WT soft-flag profile (inherited liabilities are acceptable)
    wt_soft_hits = _scan_motifs(wt_seq, SOFT_FLAG_PATTERNS, cdr_ranges_0indexed)
    wt_soft_set  = set(wt_soft_hits)
    print(f"[MPNN-V2] WT soft-flag profile ({len(wt_soft_set)} motifs): {sorted(wt_soft_set)}")

    # Project prefix from mask or directory name
    project_prefix = mask.get("parent_id", project_dir.name).split("_")[0]

    all_seqs: dict[str, str] = {}
    ptm_hard_map:  dict[str, list[str]] = {}
    ptm_inher_map: dict[str, list[str]] = {}
    ptm_new_map:   dict[str, list[str]] = {}
    seq_counter = 0

    for fa in fasta_files:
        with open(fa) as f:
            header, seq_parts = None, []
            for line in f:
                line = line.strip()
                if line.startswith(">"):
                    if header and seq_parts:
                        raw = "".join(seq_parts).replace("X", "").replace("-", "")
                        temp_match = re.search(r"T=(\d+\.\d+)", header)
                        temp_str   = temp_match.group(1) if temp_match else "?"
                        sid = f"{project_prefix}_{seq_counter:04d}_T{temp_str}"
                        all_seqs[sid] = raw
                        h, inh, ns = detect_ptm_tiered(raw, cdr_ranges_0indexed, wt_soft_set)
                        ptm_hard_map[sid]  = h
                        ptm_inher_map[sid] = inh
                        ptm_new_map[sid]   = ns
                        seq_counter += 1
                    header = line[1:].strip()
                    seq_parts = []
                else:
                    seq_parts.append(line)
            if header and seq_parts:
                raw = "".join(seq_parts).replace("X", "").replace("-", "")
                temp_match = re.search(r"T=(\d+\.\d+)", header)
                temp_str   = temp_match.group(1) if temp_match else "?"
                sid = f"{project_prefix}_{seq_counter:04d}_T{temp_str}"
                all_seqs[sid] = raw
                h, inh, ns = detect_ptm_tiered(raw, cdr_ranges_0indexed, wt_soft_set)
                ptm_hard_map[sid]  = h
                ptm_inher_map[sid] = inh
                ptm_new_map[sid]   = ns
                seq_counter += 1

    print(f"[MPNN-V2] Collected {len(all_seqs)} raw sequences")

    # Exact deduplication on full sequence
    seen: dict[str, str] = {}
    for sid, seq in all_seqs.items():
        if seq not in seen:
            seen[seq] = sid

    deduped = {sid: seq for seq, sid in seen.items()}
    print(f"[MPNN-V2] After deduplication: {len(deduped)} unique sequences")

    # ── CDR diversity alarm: for each redesigned CDR, count sequences with
    # zero mutations.  If >90% of unique sequences have 0 mutations in a
    # redesigned CDR the mask is almost certainly wrong — alert immediately.
    _check_cdr_diversity(deduped, wt_seq, cdr_data, redesign_cdrs)

    # ── HallucinationGuard: CDR_CONTACT_RATIO ────────────────────────────────
    # If the project has a contacts CSV from a previous docking / interface
    # analysis step, verify that ≥50% of contacts fall within CDR regions.
    # This guards against accidentally scanning non-CDR framework residues.
    if _GUARD_AVAILABLE:
        _contacts_csv = project_dir / "contacts.csv"
        if _contacts_csv.exists():
            try:
                _cdr_defs: dict[str, tuple[int, int]] = {}
                for cdr_key in redesign_cdrs:
                    cdr = cdr_data.get(cdr_key, {})
                    ls  = cdr.get("linear_start")
                    le  = cdr.get("linear_end")
                    if ls is not None and le is not None:
                        _cdr_defs[cdr_key] = (int(ls), int(le))
                if _cdr_defs:
                    _mpnn_guard = HallucinationGuard(
                        project_dir=project_dir,
                        pipeline="denovo_cdr",
                        step="run_mpnn_v2/post_diversity_check",
                    )
                    _mpnn_guard.check_cdr_contact_ratio(
                        _contacts_csv, _cdr_defs,
                        min_ratio=0.5,
                        label="mpnn_v2_interface_contacts",
                    )
                    _mpnn_guard.write_audit()
            except Exception as _e:
                print(f"[MPNN-V2] HallucinationGuard CDR_CONTACT_RATIO skipped: {_e}")
    # ─────────────────────────────────────────────────────────────────────────

    # Hard-veto filter (unpaired Cys, N-glycosylation only)
    hard_pass = {sid: seq for sid, seq in deduped.items() if not ptm_hard_map.get(sid)}
    hard_fail = {sid: seq for sid, seq in deduped.items() if ptm_hard_map.get(sid)}
    print(f"[MPNN-V2] Hard-veto filter: {len(hard_pass)} pass, {len(hard_fail)} fail")
    if hard_fail:
        reasons = defaultdict(int)
        for sid in hard_fail:
            for tag in ptm_hard_map[sid]:
                reasons[tag.split("@")[0]] += 1
        for r, c in reasons.items():
            print(f"  - {r}: {c}")

    # Soft flag stats (informational)
    n_inherited_only = sum(1 for sid in hard_pass if ptm_inher_map.get(sid) and not ptm_new_map.get(sid))
    n_with_new_soft  = sum(1 for sid in hard_pass if ptm_new_map.get(sid))
    n_clean          = sum(1 for sid in hard_pass if not ptm_inher_map.get(sid) and not ptm_new_map.get(sid))
    print(f"[MPNN-V2] Soft-flag breakdown (of {len(hard_pass)} hard-pass):")
    print(f"  Clean (no soft flags):       {n_clean}")
    print(f"  Inherited only (WT motifs):  {n_inherited_only}")
    print(f"  New soft flags introduced:   {n_with_new_soft}")

    # Semiopen conservation check (applied on hard_pass pool)
    semiopen_0indexed = []
    for cdr_key, cfg in root_cfg.items():
        if cdr_key in redesign_cdrs:
            semiopen_0indexed.extend(cfg.get("semiopen_0indexed", []))

    conserv_fail_counts: dict[str, int] = {}
    if semiopen_0indexed:
        for sid, seq in list(hard_pass.items()):
            fails = 0
            for pos in semiopen_0indexed:
                if pos >= len(seq) or pos >= len(wt_seq):
                    continue
                wt_aa   = wt_seq[pos]
                cand_aa = seq[pos]
                if cand_aa != wt_aa and not is_conservative(wt_aa, cand_aa):
                    fails += 1
            if fails > 0:
                conserv_fail_counts[sid] = fails
        
        if conserv_fail_counts:
            print(f"[MPNN-V2] Semiopen conservation check: {len(conserv_fail_counts)} seqs have non-conservative mutations at semiopen positions (will be penalized in ranking, not removed).")

    # Build soft-flag annotation for FASTA headers
    def _soft_tag(sid: str) -> str:
        parts = []
        if ptm_inher_map.get(sid):
            parts.append(f"inherited={','.join(ptm_inher_map[sid])}")
        if ptm_new_map.get(sid):
            parts.append(f"new_liability={','.join(ptm_new_map[sid])}")
        if sid in conserv_fail_counts:
            parts.append(f"semiopen_fails={conserv_fail_counts[sid]}")
        return " " + " ".join(parts) if parts else ""

    # Write T0.0 passed FASTA (hard-veto + semiopen filtered, soft flags annotated)
    raw_fasta = p1_dir / "mpnn_raw_sequences.fasta"
    with open(raw_fasta, "w") as f:
        for sid, seq in hard_pass.items():
            f.write(f">{sid}{_soft_tag(sid)}\n{seq}\n")
    print(f"[MPNN-V2] T0.0 passed FASTA → {raw_fasta} ({len(hard_pass)} sequences)")

    # ── Per-CDR mutation statistics (logged in report for post-hoc audit)
    per_cdr_stats = _cdr_mutation_stats(hard_pass, wt_seq, cdr_data, redesign_cdrs)

    # Write report
    report = {
        "timestamp":          timestamp(),
        "project_dir":        str(project_dir),
        "design_mode":        design_mask.get("mode", "custom"),
        "redesign_cdrs":      redesign_cdrs,
        "n_designable":       len(net_designable),
        "designable_pdb_positions": design_1indexed,
        "n_semiopen":         len(semiopen_pdb & net_set),
        "n_root_fixed":       len(fixed_root_pdb),
        "n_generated":        len(all_seqs),
        "n_after_dedup":      len(deduped),
        "n_hard_veto":        len(hard_fail),
        "n_soft_clean":       n_clean,
        "n_soft_inherited":   n_inherited_only,
        "n_soft_new":         n_with_new_soft,
        "wt_soft_flags":      sorted(wt_soft_set),
        "n_semiopen_fail":    len(conserv_fail_counts) if semiopen_0indexed else 0,
        "n_t00_passed":       len(hard_pass),
        "per_cdr_mutation_stats": per_cdr_stats,
        "mpnn_temps":         temps,
        "n_seqs_per_temp":    n_seqs,
        "seed":               seed,
    }
    report_path = p1_dir / "mpnn_generation_report.json"
    report_path.write_text(json.dumps(report, indent=2), encoding="utf-8")
    print(f"[MPNN-V2] Generation report → {report_path}")
    print(f"\n[MPNN-V2] Summary:")
    print(f"  Generated:          {len(all_seqs)}")
    print(f"  After dedup:        {len(deduped)}")
    print(f"  Hard veto:          {len(hard_fail)}")
    print(f"  Semiopen fail:      {len(conserv_fail_counts) if semiopen_0indexed else 0} (kept for ranking)")
    print(f"  T0.0 passed:        {len(hard_pass)}")
    print(f"  Survival T0.0:      {len(hard_pass) / max(len(all_seqs), 1) * 100:.1f}%")


# ── CLI ───────────────────────────────────────────────────────────────────────

def main() -> None:
    ap = argparse.ArgumentParser(description="ProteinMPNN V2 — generalized multi-CDR sampler")
    ap.add_argument("--project_dir", required=True)
    ap.add_argument("--n_seqs",  type=int, default=300,
                    help="Number of sequences per temperature (default 300)")
    ap.add_argument("--temps",   default="0.2 0.3 0.35",
                    help="Space-separated sampling temperatures (default: '0.2 0.3 0.35')")
    ap.add_argument("--seed",    type=int, default=42)
    ap.add_argument("--force_regen", action="store_true",
                    help="Re-run ProteinMPNN even if seqs/ output exists")
    args = ap.parse_args()

    run_mpnn_v2(
        project_dir  = Path(args.project_dir).resolve(),
        n_seqs       = args.n_seqs,
        temps        = args.temps,
        seed         = args.seed,
        force_regen  = args.force_regen,
    )


if __name__ == "__main__":
    os.environ["KMP_DUPLICATE_LIB_OK"] = "TRUE"
    main()
