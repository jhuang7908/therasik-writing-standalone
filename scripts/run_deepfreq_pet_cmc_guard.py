"""
run_deepfreq_pet_cmc_guard.py
──────────────────────────────────────────────────────────────────────────────
DeepFreq-PET-CMC  —  / 


--------
 run_petization_pipeline.py ， CMC 
Germline Frequency Score（GFS），。


-----------
1. GFS（Germline Frequency Score） —  Regular VH/VL  HPR
2. pI （ VH 6.0–9.5； VH 5.5–9.0）
3. Aggregation Motifs （vs donor baseline）


--------
--donor-vh   : donor VH FASTA  FASTA 
--donor-vl   : donor VL FASTA  FASTA （，）
--candidates : petization pipeline  FASTA （）
--species    : dog | cat
--out-dir    : （JSON + MD + FASTA）

: anarcii conda 
Usage:
    python scripts/run_deepfreq_pet_cmc_guard.py \\
        --donor-vh EVQLVESGG... \\
        --donor-vl DIQMTQ... \\
        --candidates projects/anti_CD3_dog/petized_candidates.fasta \\
        --species dog \\
        --out-dir projects/anti_CD3_dog/cmc_guard
"""
from __future__ import annotations

import argparse
import json
import os
import sys
import warnings
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

warnings.filterwarnings("ignore")
os.environ.setdefault("KMP_DUPLICATE_LIB_OK", "TRUE")

REPO = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO))

# Pet Germline Coefficient (CGC/FGC) — added 2026-05-08
try:
    from core.cmc.pet_germline_coefficient import compute_pet_germline_coefficient  # type: ignore
except Exception:
    compute_pet_germline_coefficient = None  # type: ignore

# CGC/FGC non-regression tolerance & floor
PGC_DROP_TOLERANCE = 0.005
PGC_FLOOR = 0.70

# ─── Species CMC reference bounds ────────────────────────────────────────────
# pI target ranges; will be superseded by loaded JSON stats when available
_SPECIES_PI_BOUNDS: Dict[str, Dict[str, Tuple[float, float]]] = {
    "dog": {"VH": (6.0, 9.5), "VL_kappa": (4.5, 8.5), "VL_lambda": (4.5, 8.5)},
    "cat": {"VH": (5.5, 9.0), "VL_kappa": (4.0, 8.5), "VL_lambda": (4.0, 8.5)},
}

# Reference stats JSON paths (built from Tier-1 scaffolds)
_SPECIES_CMC_STATS: Dict[str, str] = {
    "dog": str(REPO / "data/reference/Dog_IgG_scaffold_cmc_stats_v1.json"),
    "cat": str(REPO / "data/reference/Cat_IgG_scaffold_cmc_stats_v1.json"),
}

# Three-tier clinical combined profiles (v3) — preferred over v2 germline-only
# Built by build_pet_clinical_combined_profile.py
# Priority: Clinical (×3) > CMC Scaffold (×2) > Germline (×1)
_SPECIES_COMBINED_VH: Dict[str, str] = {
    "dog": str(REPO / "data/reference/pet_replacement_profiles/v3/dog_ighv_clinical_combined_v1.json"),
    "cat": str(REPO / "data/reference/pet_replacement_profiles/v3/cat_ighv_clinical_combined_v1.json"),
}

# Germline frequency archives (v2, fallback when v3 not available)
_SPECIES_FREQ_IGHV: Dict[str, str] = {
    "dog": str(REPO / "data/reference/pet_replacement_profiles/v2/dog_ighv_aa_freq_kabat_v2.json"),
    "cat": str(REPO / "data/reference/pet_replacement_profiles/v2/cat_ighv_aa_freq_kabat_v2.json"),
}
_SPECIES_FREQ_IGKV: Dict[str, str] = {
    "dog": str(REPO / "data/reference/pet_replacement_profiles/v2/dog_igkv_aa_freq_kabat_v2.json"),
    "cat": str(REPO / "data/reference/pet_replacement_profiles/v2/cat_igkv_aa_freq_kabat_v2.json"),
}


# ══════════════════════════════════════════════════════════════════════════════
# Utility: FASTA / sequence parsing
# ══════════════════════════════════════════════════════════════════════════════

def _parse_seq_arg(arg: str) -> str:
    """Accept raw AA string or path to FASTA file; return single sequence."""
    if not arg:
        return ""
    p = Path(arg)
    if p.is_file():
        seqs = _read_fasta(p)
        if seqs:
            return list(seqs.values())[0]
        return ""
    return arg.strip()


def _read_fasta(path: Path) -> Dict[str, str]:
    """Parse FASTA file → {header: sequence}."""
    records: Dict[str, str] = {}
    current_header = ""
    buf: List[str] = []
    for line in path.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if not line:
            continue
        if line.startswith(">"):
            if current_header:
                records[current_header] = "".join(buf)
            current_header = line[1:].split()[0]
            buf = []
        else:
            buf.append(line)
    if current_header:
        records[current_header] = "".join(buf)
    return records


# ══════════════════════════════════════════════════════════════════════════════
# CMC metrics (basic; full-panel via core engines when available)
# ══════════════════════════════════════════════════════════════════════════════

def _compute_cmc_basic(seq: str) -> Dict[str, Any]:
    """Compute pI, GRAVY, instability_index, aggregation motif count."""
    metrics: Dict[str, Any] = {
        "pi": None, "gravy": None, "instability_index": None,
        "agg_motifs": 0, "seq_len": len(seq),
    }
    try:
        from Bio.SeqUtils.ProtParam import ProteinAnalysis  # type: ignore
        pa = ProteinAnalysis(seq.replace("X", "A"))
        metrics["pi"] = round(pa.isoelectric_point(), 2)
        metrics["gravy"] = round(pa.gravy(), 4)
        metrics["instability_index"] = round(pa.instability_index(), 2)
    except Exception:
        pass

    # Aggregation motifs: hydrophobic patches VYFIL × 4
    import re
    agg_pattern = r"[VYFIL]{4,}"
    metrics["agg_motifs"] = len(re.findall(agg_pattern, seq))
    return metrics


# ══════════════════════════════════════════════════════════════════════════════
# Germline Frequency Score (GFS)
# ══════════════════════════════════════════════════════════════════════════════

def _load_freq_archive(path: str) -> Dict[str, Dict[str, float]]:
    """
    Load {kabat_pos: {aa: freq}} from species frequency JSON.
    Supports both:
    - v2 format: {positions: {pos: {aa: freq}}}
    - v3 combined format: {positions: {pos: {combined_freq: {aa: freq}, ...}}}
    """
    try:
        data = json.loads(Path(path).read_text(encoding="utf-8"))
        positions = data.get("positions", data)
        result: Dict[str, Dict[str, float]] = {}
        for k, v in positions.items():
            if isinstance(v, dict):
                # v3 combined: has combined_freq key
                if "combined_freq" in v:
                    result[str(k)] = v["combined_freq"]
                else:
                    # v2: direct {aa: freq}
                    result[str(k)] = {aa: float(f) for aa, f in v.items() if isinstance(f, (int, float))}
        return result
    except Exception:
        return {}


def _load_9mer_contexts(species: str) -> Dict[str, List[str]]:
    """
    Load per-position 9-mer context sets from v3 combined profile.
    Returns {pos_key: [9mer_str, ...]} or {} if v3 not available.
    """
    path = _SPECIES_COMBINED_VH.get(species, "")
    if not path or not Path(path).is_file():
        return {}
    try:
        data = json.loads(Path(path).read_text(encoding="utf-8"))
        return {k: v.get("9mer_contexts", []) for k, v in data.get("positions", {}).items()}
    except Exception:
        return {}


def _gfs(seq: str, freq_archive: Dict[str, Dict[str, float]]) -> float:
    """
    Germline Frequency Score — mean residue frequency at each FR Kabat position.
    Returns 0.0 if archive empty or numbering fails.
    Requires anarcii conda env for ANARCI import.
    """
    if not freq_archive:
        return 0.0
    try:
        from anarci import anarci  # type: ignore
        results, _, _ = anarci([("q", seq)], scheme="kabat", output=False)
        if not results or results[0] is None:
            return 0.0
        numbered = results[0][0][0]  # list of ((pos, ins), aa)
        freqs: List[float] = []
        for (pos, ins), aa in numbered:
            if aa == "-" or not aa.isalpha():
                continue
            key = str(pos) if not ins.strip() else f"{pos}{ins.strip()}"
            pos_freqs = freq_archive.get(key, {})
            freqs.append(pos_freqs.get(aa, 0.0))
        if not freqs:
            return 0.0
        return round(sum(freqs) / len(freqs), 5)
    except Exception:
        return 0.0


# ══════════════════════════════════════════════════════════════════════════════
# Guard function
# ══════════════════════════════════════════════════════════════════════════════

def _check_9mer_context(
    seq: str,
    species: str,
    contexts_db: Dict[str, List[str]],
    half: int = 4,
) -> List[str]:
    """
    For each mutated FR position in the candidate, check whether the resulting
    9-mer is present in the clinical/scaffold 9-mer context database.
    Returns list of positions where 9-mer context is NOT found (novel / unseen).
    Requires ANARCI; silently returns [] on failure.
    """
    if not contexts_db:
        return []
    try:
        from anarci import anarci  # type: ignore
        results, _, _ = anarci([("q", seq)], scheme="kabat", output=False)
        if not results or results[0] is None:
            return []
        numbered = [(pos, ins.strip(), aa) for (pos, ins), aa in results[0][0][0] if aa != "-" and aa.isalpha()]
    except Exception:
        return []

    novel_positions: List[str] = []
    n = len(numbered)
    for i, (pos, ins, aa) in enumerate(numbered):
        pos_key = f"{pos}{ins}" if ins else str(pos)
        known_mers = contexts_db.get(pos_key, [])
        if not known_mers:
            continue  # no reference → skip check
        start = max(0, i - half)
        end = min(n, i + half + 1)
        window = "".join(a for _, _, a in numbered[start:end])
        n_left = half - (i - start)
        n_right = half - (end - i - 1)
        window = "-" * n_left + window + "-" * n_right
        # Check exact match or Hamming-1 match
        matched = any(
            sum(a != b for a, b in zip(window, ref)) <= 1
            for ref in known_mers
        )
        if not matched:
            novel_positions.append(pos_key)
    return novel_positions


def _compute_pgc_safe(species: str, vh: str, vl: str) -> Optional[float]:
    """Compute combined CGC/FGC; return combined score or None on failure."""
    if compute_pet_germline_coefficient is None:
        return None
    try:
        result = compute_pet_germline_coefficient(species, vh=vh, vl=vl)
        return result.get("combined", {}).get("score")
    except Exception:
        return None


def _guard_candidate(
    cand_vh: str,
    cand_vl: str,
    donor_metrics_vh: Dict[str, Any],
    donor_metrics_vl: Optional[Dict[str, Any]],
    donor_gfs_vh: float,
    donor_gfs_vl: float,
    species: str,
    ref_stats: Optional[Dict[str, Any]],
    contexts_db: Optional[Dict[str, List[str]]] = None,
    donor_pgc: Optional[float] = None,
    freq_vh_archive: Optional[Dict[str, Dict[str, float]]] = None,
    freq_vl_archive: Optional[Dict[str, Dict[str, float]]] = None,
) -> Dict[str, Any]:
    """
    Evaluate a single petized candidate against guard constraints.
    Returns {pass: bool, flags: [...], metrics_vh: {...}, metrics_vl: {...}}.
    """
    cand_m_vh = _compute_cmc_basic(cand_vh)
    cand_m_vl = _compute_cmc_basic(cand_vl) if cand_vl else None

    pi_bounds = _SPECIES_PI_BOUNDS.get(species, _SPECIES_PI_BOUNDS["dog"])
    flags: List[str] = []

    # Use provided archives (passed from main) — must be the SAME source the
    # donor baseline was computed against to avoid false-positive drops
    if freq_vh_archive is None:
        freq_vh_archive = _load_freq_archive(_SPECIES_FREQ_IGHV.get(species, ""))
    if freq_vl_archive is None:
        freq_vl_archive = _load_freq_archive(_SPECIES_FREQ_IGKV.get(species, ""))

    cand_gfs_vh = _gfs(cand_vh, freq_vh_archive)
    cand_gfs_vl = _gfs(cand_vl, freq_vl_archive) if cand_vl else 0.0

    # 1. GFS non-regression (tolerance: ±0.002)
    if cand_gfs_vh < donor_gfs_vh - 0.002:
        flags.append(f"GFS_VH_drop: {donor_gfs_vh:.4f} → {cand_gfs_vh:.4f}")
    if cand_vl and cand_gfs_vl < donor_gfs_vl - 0.002:
        flags.append(f"GFS_VL_drop: {donor_gfs_vl:.4f} → {cand_gfs_vl:.4f}")

    # 2. pI within species reference
    pi_vh = cand_m_vh.get("pi")
    if pi_vh is not None:
        lo, hi = pi_bounds["VH"]
        if not (lo <= pi_vh <= hi):
            flags.append(f"pI_VH_out_of_range: {pi_vh:.2f} (target {lo}–{hi})")

    # 3. Aggregation motifs non-increase
    if cand_m_vh.get("agg_motifs", 0) > donor_metrics_vh.get("agg_motifs", 0):
        flags.append(f"AggMotif_VH_increase: {donor_metrics_vh['agg_motifs']} → {cand_m_vh['agg_motifs']}")

    # 4. 9-mer context check (WARN only, not hard FAIL — novel ≤ 2 tolerated)
    novel_positions: List[str] = []
    if contexts_db:
        novel_positions = _check_9mer_context(cand_vh, species, contexts_db)
        if len(novel_positions) > 2:
            flags.append(f"Novel_9mer_context_{len(novel_positions)}_positions: {novel_positions[:5]}")

    # 5. CGC/FGC non-regression and floor check
    cand_pgc = _compute_pgc_safe(species, cand_vh, cand_vl)
    pgc_metric = "CGC" if species == "dog" else "FGC"
    if cand_pgc is not None:
        if donor_pgc is not None and cand_pgc < donor_pgc - PGC_DROP_TOLERANCE:
            flags.append(f"{pgc_metric}_drop: {donor_pgc:.4f} → {cand_pgc:.4f} (tolerance {PGC_DROP_TOLERANCE})")
        if cand_pgc < PGC_FLOOR:
            flags.append(f"{pgc_metric}_below_floor: {cand_pgc:.4f} < {PGC_FLOOR}")

    passed = len(flags) == 0
    return {
        "pass": passed,
        "flags": flags,
        "metrics_vh": cand_m_vh,
        "metrics_vl": cand_m_vl,
        "gfs_vh": cand_gfs_vh,
        "gfs_vl": cand_gfs_vl,
        "gfs_donor_vh": donor_gfs_vh,
        "gfs_donor_vl": donor_gfs_vl,
        "novel_9mer_positions": novel_positions,
        "pgc_score": cand_pgc,
        "pgc_donor": donor_pgc,
        "pgc_metric": pgc_metric,
    }


# ══════════════════════════════════════════════════════════════════════════════
# Main
# ══════════════════════════════════════════════════════════════════════════════

def main() -> None:
    ap = argparse.ArgumentParser(
        description="DeepFreq-PET-CMC Guard — dog/cat petization CMC non-regression screen",
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    ap.add_argument("--donor-vh", required=True,
                    help="Donor VH sequence (raw AA string) or path to FASTA file")
    ap.add_argument("--donor-vl", default="",
                    help="Donor VL sequence or FASTA path (optional)")
    ap.add_argument("--candidates", required=True,
                    help="Petized candidate FASTA file from run_petization_pipeline.py")
    ap.add_argument("--species", choices=["dog", "cat"], default="dog",
                    help="Target species for petization")
    ap.add_argument("--out-dir", default=".",
                    help="Output directory for JSON + MD + FASTA")
    ap.add_argument("--top-n", type=int, default=3,
                    help="Maximum passing candidates to emit")
    args = ap.parse_args()

    out = Path(args.out_dir)
    out.mkdir(parents=True, exist_ok=True)

    donor_vh = _parse_seq_arg(args.donor_vh)
    donor_vl = _parse_seq_arg(args.donor_vl)

    if not donor_vh:
        sys.exit("ERROR: --donor-vh is empty or file not found.")

    candidates = _read_fasta(Path(args.candidates))
    if not candidates:
        sys.exit(f"ERROR: no sequences found in {args.candidates}")

    # Load species reference stats (optional; used for percentile comment)
    ref_stats_path = _SPECIES_CMC_STATS.get(args.species, "")
    ref_stats: Optional[Dict[str, Any]] = None
    if Path(ref_stats_path).is_file():
        try:
            ref_stats = json.loads(Path(ref_stats_path).read_text(encoding="utf-8"))
        except Exception:
            pass

    # Load three-tier combined profile (v3); fallback to v2 germline
    combined_path = _SPECIES_COMBINED_VH.get(args.species, "")
    if Path(combined_path).is_file():
        freq_vh_archive = _load_freq_archive(combined_path)
        print(f"[DeepFreq-PET-CMC Guard] Using v3 three-tier combined profile: {combined_path}")
    else:
        freq_vh_archive = _load_freq_archive(_SPECIES_FREQ_IGHV.get(args.species, ""))
        print(f"[DeepFreq-PET-CMC Guard] v3 combined profile not found; falling back to v2 germline")

    contexts_db = _load_9mer_contexts(args.species)
    print(f"[DeepFreq-PET-CMC Guard] 9-mer context positions loaded: {len(contexts_db)}")

    freq_vl_archive = _load_freq_archive(_SPECIES_FREQ_IGKV.get(args.species, ""))
    donor_m_vh = _compute_cmc_basic(donor_vh)
    donor_m_vl = _compute_cmc_basic(donor_vl) if donor_vl else None
    donor_gfs_vh = _gfs(donor_vh, freq_vh_archive)
    donor_gfs_vl = _gfs(donor_vl, freq_vl_archive) if donor_vl else 0.0
    donor_pgc = _compute_pgc_safe(args.species, donor_vh, donor_vl or "")
    pgc_metric = "CGC" if args.species == "dog" else "FGC"
    print(f"[DeepFreq-PET-CMC Guard] Donor {pgc_metric}: {donor_pgc}")

    # Screen each candidate
    results: List[Dict[str, Any]] = []
    for header, seq in candidates.items():
        # Expect candidates to be VH sequences; if header encodes chain, split here
        guard = _guard_candidate(
            cand_vh=seq,
            cand_vl=donor_vl,
            donor_metrics_vh=donor_m_vh,
            donor_metrics_vl=donor_m_vl,
            donor_gfs_vh=donor_gfs_vh,
            donor_gfs_vl=donor_gfs_vl,
            species=args.species,
            ref_stats=ref_stats,
            contexts_db=contexts_db,
            donor_pgc=donor_pgc,
            freq_vh_archive=freq_vh_archive,
            freq_vl_archive=freq_vl_archive,
        )
        guard["header"] = header
        guard["seq"] = seq
        results.append(guard)

    passing = [r for r in results if r["pass"]]
    failing = [r for r in results if not r["pass"]]

    # Sort passing by GFS (descending)
    passing.sort(key=lambda r: r["gfs_vh"], reverse=True)
    selected = passing[: args.top_n]

    # ── Output JSON ───────────────────────────────────────────────────────────
    payload: Dict[str, Any] = {
        "schema": "deepfreq_pet_cmc_guard_v1",
        "species": args.species,
        "donor_baseline": {
            "metrics_vh": donor_m_vh,
            "metrics_vl": donor_m_vl,
            "gfs_vh": donor_gfs_vh,
            "gfs_vl": donor_gfs_vl,
            "pgc_score": donor_pgc,
            "pgc_metric": pgc_metric,
        },
        "guard_thresholds": {
            "pgc_drop_tolerance": PGC_DROP_TOLERANCE,
            "pgc_floor": PGC_FLOOR,
            "gfs_drop_tolerance": 0.002,
        },
        "n_candidates": len(results),
        "n_passing": len(passing),
        "n_failing": len(failing),
        "selected": selected,
        "failing": failing,
    }
    json_path = out / "deepfreq_pet_cmc_guard_result.json"
    json_path.write_text(json.dumps(payload, indent=2, ensure_ascii=False), encoding="utf-8")

    # ── Output FASTA (selected) ───────────────────────────────────────────────
    fasta_path = out / "pet_cmc_selected.fasta"
    with fasta_path.open("w", encoding="utf-8") as fh:
        for r in selected:
            fh.write(f">{r['header']}|GFS_VH={r['gfs_vh']:.4f}|pI={r['metrics_vh'].get('pi')}\n")
            fh.write(r["seq"] + "\n")

    # ── Audit Markdown ────────────────────────────────────────────────────────
    md_lines: List[str] = [
        "# DeepFreq-PET-CMC Guard — Audit Report",
        f"**Species:** {args.species.capitalize()}  ",
        f"**Screened:** {len(results)}  |  **Passing:** {len(passing)}  |  **Selected:** {len(selected)}",
        "",
        "## Donor Baseline",
        f"| Metric | VH | VL |",
        f"|---|---|---|",
        f"| pI | {donor_m_vh.get('pi', 'N/A')} | {donor_m_vl.get('pi', 'N/A') if donor_m_vl else '—'} |",
        f"| GRAVY | {donor_m_vh.get('gravy', 'N/A')} | {donor_m_vl.get('gravy', 'N/A') if donor_m_vl else '—'} |",
        f"| GFS | {donor_gfs_vh:.4f} | {donor_gfs_vl:.4f} |",
        f"| {pgc_metric} (combined) | {donor_pgc if donor_pgc is not None else 'N/A'} | (chains pooled) |",
        f"| Agg Motifs | {donor_m_vh.get('agg_motifs', 0)} | {donor_m_vl.get('agg_motifs', 0) if donor_m_vl else '—'} |",
        "",
        "## Selected Candidates",
    ]
    for i, r in enumerate(selected, 1):
        status = "PASS"
        md_lines += [
            f"### Candidate {i}: {r['header']}",
            f"- **GFS_VH:** {r['gfs_vh']:.4f} (donor: {r['gfs_donor_vh']:.4f})",
            f"- **{r.get('pgc_metric', 'PGC')}:** {r.get('pgc_score', 'N/A')} (donor: {r.get('pgc_donor', 'N/A')})",
            f"- **pI_VH:** {r['metrics_vh'].get('pi', 'N/A')}",
            f"- **Agg Motifs:** {r['metrics_vh'].get('agg_motifs', 0)}",
            f"- **Guard:** {status}",
            "",
        ]
    md_lines += ["## Failing Candidates", ""]
    for r in failing:
        md_lines += [
            f"- **{r['header']}**: " + "; ".join(r["flags"]),
        ]
    md_path = out / "PET_CMC_AUDIT.md"
    md_path.write_text("\n".join(md_lines), encoding="utf-8")

    print(f"[DeepFreq-PET-CMC Guard] {args.species.upper()} | "
          f"Screened={len(results)} Passing={len(passing)} Selected={len(selected)}")
    print(f"  JSON   → {json_path}")
    print(f"  FASTA  → {fasta_path}")
    print(f"  Audit  → {md_path}")


if __name__ == "__main__":
    main()
