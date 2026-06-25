#!/usr/bin/env python
"""
affinity_energy_cli.py
======================
Command-line interface for the Affinity Energy Toolkit.

Runs one or more binding-energy / ΔΔG tools on a set of mutation candidates
and writes a unified CSV report.

Environment
-----------
  conda activate affmat
  python scripts/affinity_energy_cli.py --help

Quick examples
--------------
  # PRODIGY on WT (sanity check, < 2 s):
  python scripts/affinity_energy_cli.py \\
      --pdb projects/PAG-1 project/7m_humanPAG1/7m_humanPAG1_df5fc/7m_humanPAG1_df5fc_relaxed_rank_001_alphafold2_multimer_v3_model_5_seed_000.pdb \\
      --ab-chains A B --ag-chains C \\
      --tools prodigy \\
      --mutations "WT"

  # Full pipeline on 3 mutation candidates:
  python scripts/affinity_energy_cli.py \\
      --pdb complex.pdb \\
      --ab-chains A B --ag-chains C \\
      --tools prodigy mmgbsa esm_if1 thermompnn antifold \\
      --mutations "WT" "A:67:Y:F" "A:102:K:R" "A:67:Y:F+A:102:K:R" \\
      --output results/affinity_scan.csv \\
      --mmgbsa-steps 300

  # VAM V1.5 — inject Stage 2.5 Structural Integrity Veto:
  python scripts/affinity_energy_cli.py \\
      --pdb complex.pdb \\
      --ab-chains H L --ag-chains A \\
      --tools evoef2 antifold mmgbsa \\
      --mutations "H:107:W:I" "H:107:W:L" "L:116:N:E" \\
      --stage2-5 \\
      --output results/affinity_scan.csv

  # From YAML mutation file:
  python scripts/affinity_energy_cli.py \\
      --pdb complex.pdb \\
      --ab-chains A B --ag-chains C \\
      --tools prodigy mmgbsa \\
      --mutation-yaml scripts/affinity_maturation/config.yaml \\
      --output results/affinity_scan.csv

Mutation string format
----------------------
  "WT"                         → wildtype (empty mutation list)
  "A:67:Y:F"                   → chain A, residue 67, Tyr→Phe
  "A:67:Y:F+A:102:K:R"         → two simultaneous mutations

Tool choices
------------
  evoef2        EvoEF2 ComputeBinding ΔΔG (< 5 s, MIT) — Layer 1 fast scan
  prodigy       Fast IC-based ΔG/Kd (< 2 s, MIT)
  mmgbsa        OpenMM MM/GBSA physics energy (1-3 min/mutant, MIT)
  esm_if1       ESM-IF1 inverse folding ΔΔG proxy (< 2 s, MIT)
  thermompnn    GNN ΔΔG + ΔTm (< 10 s, MIT)
  antifold      Antibody CDR log-likelihood proxy (< 1 s, MIT)

Stage 2.5 (VAM V1.5)
---------------------
  Add --stage2-5 to run the Structural Integrity Veto between Stage 2
  (EvoEF2) and Stage 3 (AntiFold/MM-GBSA).  Two checks are applied:
    VETO_PACKING  — blocks large-aromatic→small-aliphatic at VH-VL interface
    VETO_CHARGE   — blocks same-sign charge pairs in CDR loops (Cβ < 4 Å)
  Vetoed mutations are excluded from downstream tools unless rescued.
  Rescue suggestions are printed and saved to the JSON output.
"""

import argparse
import dataclasses
import json
import sys
import tempfile
from pathlib import Path

# Ensure repo root is on path
ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from core.structure.affinity_energy_toolkit import AffinityEnergyToolkit, _evoef2_build

EVOEF2_DEFAULT      = str(ROOT / "tools" / "EvoEF2_src" / "EvoEF2.exe")
THERMOMPNN_DEFAULT  = str(ROOT / "tools" / "ThermoMPNN")


# ── mutation parsing ─────────────────────────────────────────────────────────

def parse_mutation_string(s: str) -> list[dict]:
    """
    Parse CLI mutation string into list of mutation dicts.

    "WT"                  → []
    "A:67:Y:F"            → [{"chain":"A","resi":67,"wt":"Y","mut":"F"}]
    "A:67:Y:F+B:102:K:R"  → two mutations
    """
    s = s.strip()
    if s.upper() == "WT" or s == "":
        return []
    result = []
    for part in s.split("+"):
        part = part.strip()
        tokens = part.split(":")
        if len(tokens) == 4:
            chain, resi, wt, mut = tokens
            result.append({"chain": chain, "resi": int(resi), "wt": wt, "mut": mut})
        elif len(tokens) == 3:
            # No chain: default to first ab_chain
            resi, wt, mut = tokens
            result.append({"chain": "_DEFAULT_", "resi": int(resi), "wt": wt, "mut": mut})
        else:
            raise ValueError(
                f"Cannot parse mutation '{part}'. "
                "Expected format: CHAIN:RESI:WT:MUT (e.g. A:67:Y:F)"
            )
    return result


def load_mutations_from_yaml(yaml_path: str, default_chain: str) -> list[list[dict]]:
    """
    Load mutation candidates from existing config.yaml 'mutations' block.
    Returns list of single-mutation candidate lists.
    """
    import yaml
    cfg = yaml.safe_load(Path(yaml_path).read_text(encoding="utf-8"))
    muts_cfg = cfg.get("mutations", [])
    result = [[]]  # always include WT
    for m in muts_cfg:
        for candidate in m.get("candidates", []):
            result.append([{
                "chain": default_chain,
                "resi":  m["site"],
                "wt":    m["wt"],
                "mut":   candidate,
            }])
    return result


AA3_TO_1 = {
    "ALA": "A", "ARG": "R", "ASN": "N", "ASP": "D", "CYS": "C",
    "GLN": "Q", "GLU": "E", "GLY": "G", "HIS": "H", "ILE": "I",
    "LEU": "L", "LYS": "K", "MET": "M", "PHE": "F", "PRO": "P",
    "SER": "S", "THR": "T", "TRP": "W", "TYR": "Y", "VAL": "V",
}

CDR_RANGES = {
    "vh_vl": {
        "heavy": [("vh_cdr1", 27, 38), ("vh_cdr2", 56, 65), ("vh_cdr3", 105, 117)],
        "light": [("vl_cdr1", 27, 38), ("vl_cdr2", 56, 65), ("vl_cdr3", 105, 117)],
    },
    "vhh": {
        "heavy": [("vhh_cdr1", 25, 31), ("vhh_cdr2", 48, 56), ("vhh_cdr3", 94, 106)],
        "light": [],
    },
}


def _candidate_key(mutations: list[dict]) -> frozenset:
    return frozenset((m["chain"], m["resi"], m["wt"], m["mut"]) for m in mutations)


def _parse_pdb_sequences(pdb_path: str) -> dict[str, list[dict]]:
    """Return ordered per-chain residue records from ATOM lines."""
    chains: dict[str, list[dict]] = {}
    seen: set[tuple[str, int, str]] = set()
    with open(pdb_path, encoding="utf-8", errors="replace") as fh:
        for line in fh:
            if line[:6].strip() != "ATOM":
                continue
            chain = line[21].strip()
            if not chain:
                continue
            try:
                resi = int(line[22:26].strip())
            except ValueError:
                continue
            icode = line[26].strip()
            key = (chain, resi, icode)
            if key in seen:
                continue
            seen.add(key)
            aa = AA3_TO_1.get(line[17:20].strip().upper(), "X")
            chains.setdefault(chain, []).append({"resi": resi, "icode": icode, "aa": aa})
    return chains


def _resolve_antibody_format(value: str, ab_chains: list[str]) -> str:
    if value != "auto":
        return value
    return "vhh" if len(ab_chains) == 1 else "vh_vl"


def _infer_locus(
    mutation: dict,
    antibody_format: str,
    ab_chains: list[str],
    chain_records: dict[str, list[dict]],
) -> dict | None:
    """Infer CDR locus and 0-indexed CDR offset from chain + residue number."""
    chain = mutation["chain"]
    records = chain_records.get(chain)
    if not records:
        return None

    chain_role = "heavy" if antibody_format == "vhh" or chain == ab_chains[0] else "light"
    for locus, start_resi, end_resi in CDR_RANGES[antibody_format][chain_role]:
        if start_resi <= int(mutation["resi"]) <= end_resi:
            cdr_idxs = [
                idx for idx, rec in enumerate(records)
                if start_resi <= rec["resi"] <= end_resi
            ]
            if not cdr_idxs:
                return None
            seq_index_by_resi = {
                rec["resi"]: idx for idx, rec in enumerate(records)
                if start_resi <= rec["resi"] <= end_resi
            }
            if int(mutation["resi"]) not in seq_index_by_resi:
                return None
            cdr_start = min(cdr_idxs)
            cdr_end = max(cdr_idxs) + 1
            return {
                "locus": locus,
                "position_index": seq_index_by_resi[int(mutation["resi"])] - cdr_start,
                "chain_sequence": "".join(rec["aa"] for rec in records),
                "cdr_start": cdr_start,
                "cdr_end": cdr_end,
            }
    return None


def _run_check6_design_prior(
    mutations_list: list[list[dict]],
    antibody_format: str,
    ab_chains: list[str],
    chain_records: dict[str, list[dict]],
    min_freq: float,
) -> tuple[list[list[dict]], dict]:
    from core.structure.cdr_fingerprint_prior import design_prior_audit, load_fingerprint

    fp = load_fingerprint(antibody_format)
    audit: list[dict] = []
    passed: list[list[dict]] = []
    vetoed_keys: set[frozenset] = set()

    for candidate in mutations_list:
        if not candidate:
            passed.append(candidate)
            continue
        candidate_veto = False
        for mut in candidate:
            ctx = _infer_locus(mut, antibody_format, ab_chains, chain_records)
            if ctx is None:
                audit.append({
                    "verdict": "NOT_RUN",
                    "rule": "mutation_not_in_inferred_cdr_or_unmapped",
                    "mutation": mut,
                    "source": fp.prior_source,
                })
                continue
            entry = design_prior_audit(
                fp,
                locus=ctx["locus"],
                position_index=ctx["position_index"],
                proposed_aa=mut["mut"],
                min_freq=min_freq,
            )
            entry["mutation"] = mut
            audit.append(entry)
            if entry["verdict"] == "VETO":
                candidate_veto = True
        if candidate_veto:
            vetoed_keys.add(_candidate_key(candidate))
        else:
            passed.append(candidate)

    summary = {
        "active": True,
        "antibody_format": antibody_format,
        "threshold_source": fp.threshold_source,
        "prior_source": fp.prior_source,
        "min_freq": min_freq,
        "n_input": len(mutations_list),
        "n_passed": len(passed),
        "n_vetoed": len(vetoed_keys),
        "n_warned": sum(1 for item in audit if item.get("verdict") == "WARN"),
        "n_not_run": sum(1 for item in audit if item.get("verdict") == "NOT_RUN"),
    }
    return passed, {"summary": summary, "audit": audit}


def _run_check7_liability(
    mutations_list: list[list[dict]],
    antibody_format: str,
    ab_chains: list[str],
    chain_records: dict[str, list[dict]],
) -> tuple[list[list[dict]], dict]:
    from core.cmc.sequence_liability_filter import filter_candidates

    audit: list[dict] = []
    passed: list[list[dict]] = []
    vetoed = 0
    warned = 0
    not_run = 0

    for candidate in mutations_list:
        if not candidate:
            passed.append(candidate)
            continue
        candidate_veto = False
        for mut in candidate:
            ctx = _infer_locus(mut, antibody_format, ab_chains, chain_records)
            if ctx is None:
                not_run += 1
                audit.append({
                    "overall": "NOT_RUN",
                    "mutation": mut,
                    "reason": "mutation_not_in_inferred_cdr_or_unmapped",
                })
                continue
            seq_cand = dict(mut)
            seq_cand["index_in_cdr"] = ctx["position_index"]
            res = filter_candidates(
                wt_full_seq=ctx["chain_sequence"],
                candidates=[seq_cand],
                locus=ctx["locus"],
                cdr_start=ctx["cdr_start"],
                cdr_end=ctx["cdr_end"],
                antibody_format=antibody_format,
                keep_warnings=True,
            )
            if res.vetoed:
                candidate_veto = True
                vetoed += 1
                audit.extend(dataclasses.asdict(item) for item in res.vetoed)
            if res.warned:
                warned += len(res.warned)
                audit.extend(dataclasses.asdict(item) for item in res.warned)
            if not res.warned and not res.vetoed:
                audit.append({"overall": "PASS", "mutation": mut, "findings": []})
        if candidate_veto:
            continue
        passed.append(candidate)

    summary = {
        "active": True,
        "antibody_format": antibody_format,
        "n_input": len(mutations_list),
        "n_passed": len(passed),
        "n_warned": warned,
        "n_vetoed": vetoed,
        "n_not_run": not_run,
    }
    return passed, {"summary": summary, "audit": audit}


def _run_check8_relax_clash(
    mutations_list: list[list[dict]],
    args: argparse.Namespace,
) -> tuple[list[list[dict]], dict]:
    from core.structure.relax_and_clash_gate import relax_and_clash_check

    audit: list[dict] = []
    passed: list[list[dict]] = []
    out_dir = args.check8_out_dir or str(Path(args.output or "vam_results.csv").with_suffix(".check8"))

    for candidate in mutations_list:
        if not candidate:
            passed.append(candidate)
            continue
        with tempfile.TemporaryDirectory(prefix="vam_check8_") as tmp:
            mutant_pdb = _evoef2_build(args.evoef2, args.pdb, candidate, args.ab_chains[0], tmp)
            if mutant_pdb is None:
                audit.append({
                    "candidate": candidate,
                    "verdict": "VETO",
                    "notes": "EvoEF2 BuildMutant failed before CHECK 8",
                })
                continue
            result = relax_and_clash_check(
                pdb_path=mutant_pdb,
                ab_chains=args.ab_chains,
                antigen_chains=args.ag_chains,
                minimize=not args.check8_no_minimize,
                max_iterations=args.check8_iterations,
                out_dir=out_dir,
            )
        record = dataclasses.asdict(result)
        record["candidate"] = candidate
        audit.append(record)
        if result.verdict == "VETO":
            continue
        passed.append(candidate)

    summary = {
        "active": True,
        "n_input": len(mutations_list),
        "n_passed": len(passed),
        "n_pass": sum(1 for item in audit if item.get("verdict") == "PASS"),
        "n_warn": sum(1 for item in audit if item.get("verdict") == "WARN"),
        "n_veto": sum(1 for item in audit if item.get("verdict") == "VETO"),
        "n_not_run": sum(1 for item in audit if item.get("verdict") == "NOT_RUN"),
        "minimization": "disabled" if args.check8_no_minimize else f"openmm {args.check8_iterations} steps SD ff14SB+GBN2",
    }
    return passed, {"summary": summary, "audit": audit}


# ── print summary table ───────────────────────────────────────────────────────

def print_summary(rows: list[dict], tools: list[str]) -> None:
    print("\n" + "="*75)
    print("RESULTS SUMMARY")
    print("="*75)

    ddg_cols = {
        "evoef2":     "evoef2_ddg",
        "prodigy":    "prodigy_ddg",
        "mmgbsa":     "mmgbsa_ddg",
        "esm_if1":    "esm_ddg",
        "thermompnn": "thermo_ddg",
        "antifold":   "af_ddg",
    }
    active_cols = {t: ddg_cols[t] for t in tools if t in ddg_cols}

    header = f"{'Variant':<25}" + "".join(f"{t.upper():>13}" for t in active_cols)
    print(header)
    print("-" * len(header))

    for row in rows:
        line = f"{row['variant']:<25}"
        for t, col in active_cols.items():
            v = row.get(col)
            line += f"{v:+13.3f}" if isinstance(v, float) else f"{'N/A':>13}"
        print(line)

    print("="*75)
    print("ΔΔG in kcal/mol — negative = better binding / more stable")
    print()


# ── main ─────────────────────────────────────────────────────────────────────

def build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(
        description=__doc__,
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    p.add_argument("--pdb",    required=True,
                   help="Path to WT antibody-antigen complex PDB.")
    p.add_argument("--ab-chains", nargs="+", required=True, metavar="CHAIN",
                   help="Antibody chain IDs (e.g. --ab-chains A  or  --ab-chains A B).")
    p.add_argument("--ag-chains", nargs="+", required=True, metavar="CHAIN",
                   help="Antigen chain IDs (e.g. --ag-chains C).")
    p.add_argument(
        "--tools", nargs="+",
        choices=["evoef2","prodigy","mmgbsa","esm_if1","thermompnn","antifold","all"],
        default=["evoef2","prodigy"],
        help="Tools to run (default: evoef2 prodigy). Use 'all' for all six.",
    )
    mut_grp = p.add_mutually_exclusive_group(required=True)
    mut_grp.add_argument(
        "--mutations", nargs="+", metavar="MUT",
        help=(
            "Mutation strings: 'WT' or 'CHAIN:RESI:WT:MUT'. "
            "Combine with '+' for multi-mutants."
        ),
    )
    mut_grp.add_argument(
        "--mutation-yaml", metavar="YAML",
        help="Path to config.yaml with 'mutations:' block.",
    )
    p.add_argument("--output", default=None,
                   help="Output CSV path (default: auto-named in current dir).")
    p.add_argument("--evoef2",      default=EVOEF2_DEFAULT,
                   help=f"EvoEF2 executable (default: {EVOEF2_DEFAULT}).")
    p.add_argument("--thermompnn-dir", default=THERMOMPNN_DEFAULT,
                   help="ThermoMPNN repo directory.")
    p.add_argument("--mmgbsa-steps", type=int, default=300,
                   help="MM/GBSA minimization steps (default: 300).")
    p.add_argument("--temperature",  type=float, default=25.0,
                   help="Temperature °C for Kd conversion (default: 25).")
    p.add_argument("--ag-residue-range", default=None,
                   help=(
                       "Antigen truncation for MM/GBSA: 'CHAIN:START:END' "
                       "(e.g. C:520:620 to save time on large antigens)."
                   ))
    p.add_argument("--json-output", action="store_true",
                   help="Also write results as JSON alongside CSV.")
    # Stage 2.5 — Structural Integrity Veto (VAM V1.5)
    p.add_argument(
        "--stage2-5",
        action="store_true",
        default=False,
        help=(
            "[VAM V1.5] Run Stage 2.5 Structural Integrity Veto before expensive tools. "
            "Requires --pdb to be the WT complex (same PDB used for EvoEF2). "
            "Vetoed mutations are excluded from downstream MM/GBSA / AntiFold."
        ),
    )
    p.add_argument(
        "--stage2-5-rescue",
        action="store_true",
        default=True,
        help=(
            "[VAM V1.5] When --stage2-5 is active, attempt rescue design for "
            "high-affinity vetoed candidates (EvoEF2 ΔΔG < −1.5 kcal/mol). "
            "Default: enabled."
        ),
    )
    p.add_argument(
        "--skip-v16-gates",
        action="store_true",
        default=False,
        help="[VAM V1.6] Disable CHECK 6/7/8 and run legacy V1.5.2 behavior.",
    )
    p.add_argument(
        "--skip-fingerprint-prior",
        action="store_true",
        default=False,
        help="[VAM V1.6 CHECK 6] Skip CDR fingerprint design-prior filtering.",
    )
    p.add_argument(
        "--skip-seq-liability",
        action="store_true",
        default=False,
        help="[VAM V1.6 CHECK 7] Skip sequence-level CMC liability pre-filter.",
    )
    p.add_argument(
        "--skip-clash-gate",
        action="store_true",
        default=False,
        help="[VAM V1.6 CHECK 8] Skip relax + vdW clash gate.",
    )
    p.add_argument(
        "--antibody-format",
        choices=["auto", "vh_vl", "vhh"],
        default="auto",
        help="[VAM V1.6] Fingerprint cohort routing. auto => VHH when one antibody chain, else VH/VL.",
    )
    p.add_argument(
        "--fingerprint-min-freq",
        type=float,
        default=0.005,
        help="[VAM V1.6 CHECK 6] Minimum observed CDR AA frequency. Production default: 0.005.",
    )
    p.add_argument(
        "--check8-no-minimize",
        action="store_true",
        default=False,
        help="[VAM V1.6 CHECK 8] Scan raw EvoEF2 mutant PDBs without OpenMM minimization.",
    )
    p.add_argument(
        "--check8-iterations",
        type=int,
        default=500,
        help="[VAM V1.6 CHECK 8] OpenMM minimization iterations before clash scan.",
    )
    p.add_argument(
        "--check8-out-dir",
        default=None,
        help="[VAM V1.6 CHECK 8] Directory for minimized mutant PDBs.",
    )
    return p


def main(argv=None):
    args = build_parser().parse_args(argv)

    # Evidence Gate — pre-flight knowledge check
    try:
        from core.resources.evidence_gate import EvidenceGate, print_evidence_banner
        pdb_stem = Path(args.pdb).stem
        _gate = EvidenceGate(enable_network=False)
        _evidence_ctx = _gate.check(antibody_name=pdb_stem)
        print_evidence_banner(_evidence_ctx)
    except Exception as e:
        print(f"[VAM] Evidence gate skipped: {e}", flush=True)
        _evidence_ctx = None

    # Expand 'all'
    tools = args.tools
    if "all" in tools:
        tools = ["evoef2", "prodigy", "mmgbsa", "esm_if1", "thermompnn", "antifold"]

    # Build mutation list
    if args.mutations:
        mutations_list = [parse_mutation_string(m) for m in args.mutations]
        for ml in mutations_list:
            for m in ml:
                if m.get("chain") == "_DEFAULT_":
                    m["chain"] = args.ab_chains[0]
    else:
        mutations_list = load_mutations_from_yaml(args.mutation_yaml, args.ab_chains[0])

    # VAM V1.6 CHECK 6/7/8 — default-on production gates.
    v16_audit: dict = {
        "antibody_format": _resolve_antibody_format(args.antibody_format, args.ab_chains),
        "check_6_design_prior": {"summary": {"active": False, "reason": "not_run"}},
        "check_7_seq_liability": {"summary": {"active": False, "reason": "not_run"}},
        "check_8_relax_clash": {"summary": {"active": False, "reason": "not_run"}},
    }
    if args.skip_v16_gates:
        args.skip_fingerprint_prior = True
        args.skip_seq_liability = True
        args.skip_clash_gate = True
        v16_audit["disabled_by"] = "--skip-v16-gates"

    antibody_format = v16_audit["antibody_format"]
    chain_records = _parse_pdb_sequences(args.pdb)

    if not args.skip_fingerprint_prior:
        print("\n[VAM V1.6 CHECK 6] Running CDR fingerprint design-prior gate...", flush=True)
        mutations_list, v16_audit["check_6_design_prior"] = _run_check6_design_prior(
            mutations_list=mutations_list,
            antibody_format=antibody_format,
            ab_chains=args.ab_chains,
            chain_records=chain_records,
            min_freq=args.fingerprint_min_freq,
        )
        s = v16_audit["check_6_design_prior"]["summary"]
        print(
            f"[CHECK 6] Passed: {s['n_passed']} | Vetoed: {s['n_vetoed']} | "
            f"Warned: {s['n_warned']} | Not run: {s['n_not_run']}",
            flush=True,
        )

    if not args.skip_seq_liability:
        print("\n[VAM V1.6 CHECK 7] Running sequence-level CMC liability filter...", flush=True)
        mutations_list, v16_audit["check_7_seq_liability"] = _run_check7_liability(
            mutations_list=mutations_list,
            antibody_format=antibody_format,
            ab_chains=args.ab_chains,
            chain_records=chain_records,
        )
        s = v16_audit["check_7_seq_liability"]["summary"]
        print(
            f"[CHECK 7] Passed: {s['n_passed']} | Vetoed: {s['n_vetoed']} | "
            f"Warned: {s['n_warned']} | Not run: {s['n_not_run']}",
            flush=True,
        )

    # Antigen residue range
    ag_range = None
    if args.ag_residue_range:
        ch, s, e = args.ag_residue_range.split(":")
        ag_range = {"chain": ch, "start": int(s), "end": int(e)}

    # Output path
    output_csv = args.output
    if output_csv is None:
        pdb_stem   = Path(args.pdb).stem
        tools_str  = "_".join(t[:3] for t in tools)
        output_csv = f"{pdb_stem}_{tools_str}_affinity.csv"

    # Build toolkit
    tk = AffinityEnergyToolkit(
        complex_pdb    = args.pdb,
        ab_chains      = args.ab_chains,
        ag_chains      = args.ag_chains,
        evoef2_exe     = args.evoef2,
        thermompnn_dir = args.thermompnn_dir,
        temperature    = args.temperature,
    )

    # Stage 2.5 — Structural Integrity Veto (VAM V1.5)
    stage25_report = None
    rescued_extras: list[list[dict]] = []
    if args.stage2_5:
        try:
            from core.structure.structural_integrity_veto import run_stage2_5

            print("\n[Stage 2.5] Running Structural Integrity Veto (VAM V1.5)...", flush=True)

            # Collect only non-WT candidates for veto; WT always passes
            non_wt = [ml for ml in mutations_list if ml]  # empty list = WT
            stage25_report = run_stage2_5(
                pdb_path=args.pdb,
                ab_chains=args.ab_chains,
                candidates=non_wt,
                affinity_ddg=None,          # EvoEF2 not yet run; veto on geometry only
                rescue=args.stage2_5_rescue,
                antigen_chains=args.ag_chains,
            )

            vetoed_keys = {
                tuple((m["chain"], m["resi"], m["wt"], m["mut"])
                      for m in (vr.mutation if isinstance(vr.mutation, list) else [vr.mutation]))
                for vr in stage25_report.vetoed
            }

            def _mut_key(ml):
                if not ml:
                    return frozenset()
                return frozenset((m["chain"], m["resi"], m["wt"], m["mut"]) for m in ml)

            # Filter mutations_list: keep WT + passed candidates
            passed_keys = {_mut_key(c) for c in stage25_report.passed}
            filtered_list = [ml for ml in mutations_list
                             if (not ml) or (_mut_key(ml) in passed_keys)]

            n_removed = len(mutations_list) - len(filtered_list)

            # Summarise
            s = stage25_report.summary
            print(
                f"[Stage 2.5] Total: {s['total_input']} | "
                f"Passed: {s['passed']} | "
                f"Vetoed: {s['vetoed']} | "
                f"Rescued: {s['rescued']} | "
                f"Warned: {s['warned']} | "
                f"Pass rate: {s['pass_rate']}"
            )
            for vr in stage25_report.vetoed:
                m = vr.mutation if isinstance(vr.mutation, dict) else vr.mutation[0]
                print(f"  ✗ VETOED [{vr.veto_type}] {m['chain']}:{m['resi']} "
                      f"{m['wt']}→{m['mut']}: {vr.reason[:120]}")
            for wr in stage25_report.warned:
                m = wr.mutation
                print(f"  ⚠ WARN   [{wr.veto_type}] {m['chain']}:{m['resi']} "
                      f"{m['wt']}→{m['mut']}: {wr.reason}")
            for rc in stage25_report.rescued:
                muts = rc.get("original_mutations", [])
                tag = "+".join(f"{m['chain']}:{m['resi']}{m['wt']}→{m['mut']}" for m in muts)
                print(f"  ↻ RESCUE [{rc['rescue_type']}] {tag} — "
                      f"ΔΔG={rc.get('affinity_ddg','?')}")

            mutations_list = filtered_list
            print(f"[Stage 2.5] {n_removed} candidates removed; "
                  f"{len(mutations_list)} forwarded to downstream tools.\n", flush=True)

        except Exception as exc:
            print(f"[Stage 2.5] WARNING: Veto check failed ({exc}); "
                  "continuing without Stage 2.5 filter.", flush=True)

    if not args.skip_clash_gate:
        print("\n[VAM V1.6 CHECK 8] Running relax + vdW clash gate...", flush=True)
        try:
            mutations_list, v16_audit["check_8_relax_clash"] = _run_check8_relax_clash(
                mutations_list=mutations_list,
                args=args,
            )
            s = v16_audit["check_8_relax_clash"]["summary"]
            print(
                f"[CHECK 8] Passed: {s['n_passed']} | Vetoed: {s['n_veto']} | "
                f"Warned: {s['n_warn']} | Not run: {s['n_not_run']}",
                flush=True,
            )
        except Exception as exc:
            v16_audit["check_8_relax_clash"] = {
                "summary": {"active": True, "n_input": len(mutations_list), "n_not_run": len(mutations_list)},
                "error": str(exc),
            }
            print(f"[CHECK 8] WARNING: gate failed ({exc}); continuing with audit NOT_RUN.", flush=True)

    # Run
    results = tk.run_all(
        mutations_list     = mutations_list,
        tools              = tools,
        minimization_steps = args.mmgbsa_steps,
        output_csv         = output_csv,
    )

    print_summary(results, tools)

    if args.json_output:
        json_path = output_csv.replace(".csv", ".json")
        out_payload: dict = {"results": results, "v16_audit": v16_audit}
        if stage25_report is not None:
            out_payload["stage2_5_veto"] = {
                "summary": stage25_report.summary,
                "vetoed": [dataclasses.asdict(v) for v in stage25_report.vetoed],
                "rescued": stage25_report.rescued,
                "warned": [dataclasses.asdict(w) for w in stage25_report.warned],
            }
        Path(json_path).write_text(
            json.dumps(out_payload, indent=2, default=str), encoding="utf-8"
        )
        print(f"JSON written to: {json_path}")
    elif not args.skip_v16_gates:
        audit_path = output_csv.replace(".csv", ".v16_audit.json")
        Path(audit_path).write_text(
            json.dumps({"v16_audit": v16_audit}, indent=2, default=str), encoding="utf-8"
        )
        print(f"V1.6 audit written to: {audit_path}")

    print(f"CSV written to:  {output_csv}")

    # Self-Evolution: emit RunEvent
    try:
        from core.evolution.event_collector import EventCollector
        _collector = EventCollector()
        _run_event = _collector.from_vam_result(
            project_id=Path(args.pdb).stem,
            entrypoint="affinity_energy_cli.py",
            tools_used=tools,
            n_mutations=len(mutations_list),
            evidence_ctx=_evidence_ctx,
            exit_code=0,
        )
        _collector.emit(_run_event)
    except Exception:
        pass

    return 0


if __name__ == "__main__":
    sys.exit(main())
