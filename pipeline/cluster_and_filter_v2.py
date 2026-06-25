"""
cluster_and_filter_v2.py — T0.5 Multi-CDR Diversity Filter & Clustering (V2)
=============================================================================
Handles CDR2-only, CDR3-only, and CDR2+CDR3 co-design modes from mask_strategy.json.

Changes vs V1:
  1. Multi-CDR identity computed as combined CDR sequence identity, not just CDR2.
  2. Mode-aware: "patent_escape" vs "affinity_rescue" choose different thresholds.
  3. Hamming clustering now operates over the *combined* designed CDR string.
  4. Max survivors configurable (default 50).
  5. Outputs AbLang score, combined CDR identity, per-CDR mutations, and mode tag.

Usage:
    conda run -n affmat python pipeline/cluster_and_filter_v2.py \\
        --project_dir <path> \\
        [--mode patent_escape|affinity_rescue|custom] \\
        [--cdr_identity_max 0.65] \\
        [--min_cdr_mutations 5] \\
        [--hamming_frac 0.30] \\
        [--max_survivors 50]
"""

from __future__ import annotations

import argparse
import json
import os
from pathlib import Path
from typing import NamedTuple

os.environ["KMP_DUPLICATE_LIB_OK"] = "TRUE"

# coord_utils: cdr_linear_ranges() / get_combined_cdr_string() use linear
# 0-indexed coords (correct for sequence operations).
try:
    from pipeline.coord_utils import cdr_linear_ranges, get_combined_cdr_string as _cu_cdr_str, validate_mask_coords
except ModuleNotFoundError:
    import importlib.util, pathlib as _pl
    _cu = _pl.Path(__file__).parent / "coord_utils.py"
    _spec = importlib.util.spec_from_file_location("coord_utils", _cu)
    _mod = importlib.util.module_from_spec(_spec); _spec.loader.exec_module(_mod)
    cdr_linear_ranges     = _mod.cdr_linear_ranges
    _cu_cdr_str           = _mod.get_combined_cdr_string
    validate_mask_coords  = _mod.validate_mask_coords


# ── Mode presets ──────────────────────────────────────────────────────────────

class FilterPreset(NamedTuple):
    cdr_identity_max:  float
    min_cdr_mutations: int
    hamming_frac:      float   # fraction of combined CDR length for cluster radius
    max_survivors:     int


MODE_PRESETS: dict[str, FilterPreset] = {
    "patent_escape":    FilterPreset(0.65, 5,  0.30, 50),
    "affinity_rescue":  FilterPreset(0.95, 1,  0.15, 50),
    "broad_diversity":  FilterPreset(0.55, 7,  0.25, 50),
    "custom":           FilterPreset(0.65, 5,  0.30, 50),  # overridden by CLI args
}


# ── I/O helpers ───────────────────────────────────────────────────────────────

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


def load_jsonl(path: Path) -> list[dict]:
    if not path.exists():
        return []
    return [
        json.loads(ln)
        for ln in path.read_text(encoding="utf-8").strip().split("\n")
        if ln.strip()
    ]


# ── CDR helpers ───────────────────────────────────────────────────────────────

def get_combined_cdr_string(seq: str, cdr_ranges: list[tuple[int, int]]) -> str:
    """Concatenate CDR sub-strings from designed regions."""
    parts = [seq[s:e + 1] for s, e in cdr_ranges if e < len(seq)]
    return "".join(parts)


def cdr_identity(seq: str, wt_seq: str, cdr_ranges: list[tuple[int, int]]) -> float:
    """Fraction of designed CDR positions that are identical to WT."""
    total  = sum(e - s + 1 for s, e in cdr_ranges)
    if total == 0:
        return 1.0
    match = sum(
        1
        for s, e in cdr_ranges
        for i in range(s, e + 1)
        if i < len(seq) and i < len(wt_seq) and seq[i] == wt_seq[i]
    )
    return match / total


def cdr_mutations_per_cdr(
    seq: str,
    wt_seq: str,
    cdr_regions: dict[str, dict],
    redesign_cdrs: list[str],
) -> dict[str, int]:
    """Return dict {cdr_key: n_mutations} for each redesigned CDR."""
    result = {}
    for cdr_key in redesign_cdrs:
        cdr = cdr_regions.get(cdr_key, {})
        ls  = cdr.get("linear_start")
        le  = cdr.get("linear_end")
        if ls is None or le is None:
            continue
        n_mut = sum(
            1 for i in range(ls, le + 1)
            if i < len(seq) and i < len(wt_seq) and seq[i] != wt_seq[i]
        )
        result[cdr_key] = n_mut
    return result


def hamming(a: str, b: str) -> int:
    return sum(x != y for x, y in zip(a, b))


# ── Main ──────────────────────────────────────────────────────────────────────

def run_cluster(
    project_dir: Path,
    mode: str = "patent_escape",
    cdr_identity_max_override: float | None = None,
    min_cdr_mutations_override: int | None = None,
    hamming_frac_override: float | None = None,
    max_survivors_override: int | None = None,
) -> None:
    mask_path = project_dir / "config" / "mask_strategy.json"
    mask      = json.loads(mask_path.read_text(encoding="utf-8"))
    validate_mask_coords(mask, abort=True)      # coordinate consistency gate
    wt_seq    = mask["wt_sequence"]
    p1_dir    = project_dir / "phase1_generation"

    redesign_cdrs  = mask["design_mask"].get("redesign_cdrs", [])
    cdr_regions    = mask["cdr_regions"]

    # CDR ranges (linear 0-indexed) for sequence-level identity / mutation ops
    _ranges_dict   = cdr_linear_ranges(mask, redesign_cdrs)
    cdr_ranges     = list(_ranges_dict.values())

    combined_cdr_len = sum(e - s + 1 for s, e in cdr_ranges)
    wt_combined_cdr  = get_combined_cdr_string(wt_seq, cdr_ranges)  # linear coords ✓

    # Select preset
    preset = MODE_PRESETS.get(mode, MODE_PRESETS["patent_escape"])
    cdr_id_max   = cdr_identity_max_override   or preset.cdr_identity_max
    min_muts     = min_cdr_mutations_override  or preset.min_cdr_mutations
    h_frac       = hamming_frac_override       or preset.hamming_frac
    max_surv     = max_survivors_override      or preset.max_survivors
    hamming_dist = max(1, int(combined_cdr_len * h_frac))

    print("=" * 65)
    print(f"  cluster_and_filter_v2 — mode: {mode}")
    print(f"  Redesigned CDRs:   {redesign_cdrs}")
    print(f"  Combined CDR len:  {combined_cdr_len} aa")
    print(f"  WT combined CDR:   {wt_combined_cdr}")
    print(f"  CDR identity max:  {cdr_id_max}")
    print(f"  Min CDR mutations: {min_muts}")
    print(f"  Hamming dist:      {hamming_dist} aa")
    print(f"  Max survivors:     {max_surv}")
    print("=" * 65)

    # Load sequences: prefer T0.0 passed raw FASTA
    raw_fasta_candidates = [
        p1_dir / "mpnn_raw_sequences.fasta",
        p1_dir / "t0_passed.fasta",
        p1_dir / "t00_passed.fasta",
    ]
    raw_fasta = next((p for p in raw_fasta_candidates if p.exists()), None)
    if not raw_fasta:
        print("[ERROR] No input FASTA found. Run run_mpnn_v2.py first.")
        raise SystemExit(1)

    seq_map = load_fasta(raw_fasta)
    print(f"\nStarting pool: {len(seq_map)} sequences ({raw_fasta.name})")

    # Load AbLang scores (T1) if available
    ablang_scores: dict[str, float] = {}
    t1_path = p1_dir / "t1_ablang_scores.jsonl"
    if t1_path.exists():
        for rec in load_jsonl(t1_path):
            if rec.get("pass"):
                ablang_scores[rec["seq_id"]] = rec.get(
                    "ablang_mean_logp", rec.get("score", 0.0)
                )
        print(f"AbLang scores available: {len(ablang_scores)}")
        seqs = {sid: seq_map[sid] for sid in ablang_scores if sid in seq_map}
        print(f"T1-passed pool: {len(seqs)}")
    else:
        print("[WARN] No T1 AbLang scores found; using all T0.0-passed sequences.")
        seqs = dict(seq_map)

    if not seqs:
        print("[ERROR] No sequences to cluster.")
        raise SystemExit(1)

    # Step 1: CDR identity filter + minimum mutations
    with_idn = []
    for sid, seq in seqs.items():
        idn  = cdr_identity(seq, wt_seq, cdr_ranges)
        n_m  = cdr_mutations_per_cdr(seq, wt_seq, cdr_regions, redesign_cdrs)
        total_muts = sum(n_m.values())
        with_idn.append((sid, seq, idn, total_muts, n_m))

    # Sort: most diverse first
    with_idn.sort(key=lambda x: x[2])

    # Auto-fallback: if strict threshold yields too few, relax
    filtered = [row for row in with_idn
                if row[2] < cdr_id_max and row[3] >= min_muts]

    if len(filtered) < 10 and cdr_id_max < 0.95:
        relaxed_id = min(cdr_id_max + 0.10, 0.95)
        relaxed_mut = max(min_muts - 1, 1)
        print(f"  Strict filter yields only {len(filtered)} — relaxing to "
              f"identity < {relaxed_id}, min_mut >= {relaxed_mut}")
        filtered = [row for row in with_idn
                    if row[2] < relaxed_id and row[3] >= relaxed_mut]

    print(f"\nAfter identity/mutation filter: {len(filtered)}")
    if filtered:
        print(f"  Identity range: {filtered[0][2]:.3f} – {filtered[-1][2]:.3f}")
        print(f"  Mutation range: {filtered[0][3]} – {filtered[-1][3]}")

    # Step 2: exact combined-CDR deduplication
    seen_cdr: dict[str, str] = {}
    deduped: list[tuple] = []
    for row in filtered:
        sid, seq = row[0], row[1]
        cdr_str = get_combined_cdr_string(seq, cdr_ranges)
        if cdr_str not in seen_cdr:
            seen_cdr[cdr_str] = sid
            deduped.append(row + (cdr_str,))
        elif ablang_scores.get(sid, -9999) > ablang_scores.get(seen_cdr[cdr_str], -9999):
            seen_cdr[cdr_str] = sid
            deduped = [
                r if r[5] != cdr_str else row + (cdr_str,)
                for r in deduped
            ]

    print(f"After exact CDR deduplication: {len(deduped)}")

    # Step 3: Hamming clustering on combined CDR string
    clusters: list[list[tuple]] = []
    unassigned = list(deduped)
    while unassigned:
        center = unassigned[0]
        cluster = [center]
        remaining = []
        for item in unassigned[1:]:
            if hamming(item[5], center[5]) <= hamming_dist:
                cluster.append(item)
            else:
                remaining.append(item)
        clusters.append(cluster)
        unassigned = remaining

    print(f"Hamming clustering (dist ≤ {hamming_dist}):")
    print(f"  Clusters formed:    {len(clusters)}")
    print(f"  Largest cluster:    {max(len(c) for c in clusters)}")
    singletons = sum(1 for c in clusters if len(c) == 1)
    print(f"  Singletons:         {singletons}")

    # Step 4: pick representative (best AbLang or most diverse)
    representatives = []
    for cluster in clusters:
        if ablang_scores:
            rep = max(cluster, key=lambda x: ablang_scores.get(x[0], -9999))
        else:
            rep = min(cluster, key=lambda x: x[2])  # most diverse
        representatives.append(rep)

    representatives.sort(key=lambda x: x[2])  # most diverse first

    # Trim to max_survivors
    if len(representatives) > max_surv:
        representatives = representatives[:max_surv]

    print(f"\nFinal diverse candidates: {len(representatives)}")

    # Print top 10
    header = f"  {'#':>3}  {'Seq ID':<42}  {'CDR_id':>7}  {'Muts':>5}  Combined CDR"
    print(header)
    for i, row in enumerate(representatives[:10]):
        sid, seq, idn, tot_muts, n_m_dict, cdr_str = row
        mut_label = "+".join(f"{k}:{v}" for k, v in n_m_dict.items())
        print(f"  {i+1:>3}  {sid:<42}  {idn:>7.3f}  {tot_muts:>5}  {cdr_str} [{mut_label}]")

    # Output FASTA
    out_fasta = p1_dir / "t05_clustered.fasta"
    with open(out_fasta, "w") as f:
        for row in representatives:
            sid, seq, idn, tot_muts, n_m_dict, cdr_str = row
            mut_label = "+".join(f"{k}:{v}" for k, v in n_m_dict.items())
            f.write(f">{sid} | CDR_id={idn:.3f} | CDR_muts={tot_muts} | {mut_label}\n{seq}\n")

    # Output JSONL
    out_jsonl = p1_dir / "t05_clustered.jsonl"
    with open(out_jsonl, "w") as f:
        for row in representatives:
            sid, seq, idn, tot_muts, n_m_dict, cdr_str = row
            rec = {
                "seq_id":         sid,
                "sequence":       seq,
                "combined_cdr":   cdr_str,
                "cdr_identity":   round(idn, 4),
                "total_cdr_muts": tot_muts,
                "per_cdr_muts":   n_m_dict,
                "ablang_score":   ablang_scores.get(sid),
                "cluster_rep":    True,
                "filter_mode":    mode,
            }
            f.write(json.dumps(rec) + "\n")

    print(f"\nWritten: {out_fasta}  ({len(representatives)} sequences)")
    print(f"Written: {out_jsonl}")

    # Update manifest
    manifest_path = project_dir / "project_manifest.json"
    if manifest_path.exists():
        with open(manifest_path) as f:
            m = json.load(f)
        m.setdefault("stats", {}).update({
            "after_t05_cluster":          len(representatives),
            "t05_cdr_identity_max":       cdr_id_max,
            "t05_hamming_dist":           hamming_dist,
            "t05_mode":                   mode,
        })
        m.setdefault("phase_status", {})["t05_clustering"] = "DONE"
        with open(manifest_path, "w") as f:
            json.dump(m, f, indent=2)

    print(f"\nManifest updated. Ready for Phase 2 with {len(representatives)} candidates.")


# ── CLI ───────────────────────────────────────────────────────────────────────

def main() -> None:
    ap = argparse.ArgumentParser(description="T0.5 Multi-CDR Clustering V2")
    ap.add_argument("--project_dir",         required=True)
    ap.add_argument("--mode",                default="patent_escape",
                    choices=["patent_escape", "affinity_rescue", "broad_diversity", "custom"])
    ap.add_argument("--cdr_identity_max",    type=float, default=None)
    ap.add_argument("--min_cdr_mutations",   type=int,   default=None)
    ap.add_argument("--hamming_frac",        type=float, default=None,
                    help="Fraction of combined CDR length for cluster radius")
    ap.add_argument("--max_survivors",       type=int,   default=None)
    args = ap.parse_args()

    run_cluster(
        project_dir               = Path(args.project_dir),
        mode                      = args.mode,
        cdr_identity_max_override = args.cdr_identity_max,
        min_cdr_mutations_override= args.min_cdr_mutations,
        hamming_frac_override     = args.hamming_frac,
        max_survivors_override    = args.max_survivors,
    )


if __name__ == "__main__":
    main()
