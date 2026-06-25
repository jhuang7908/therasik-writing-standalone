"""
run_t0_t1_phase1.py — T0 OASis + T1 AbLang for any De Novo project with mask_strategy.json
===========================================================================================
Reads WT / redesign CDRs from config/mask_strategy.json. FASTA seq_id = first token after '>'
(same convention as cluster_and_filter_v2.load_fasta).

Usage:
  conda run -n anarcii python pipeline/run_t0_t1_phase1.py --project_dir <path> --step t0_oasis
  conda run -n affmat python pipeline/run_t0_t1_phase1.py --project_dir <path> --step t1_ablang
  conda run -n affmat python pipeline/run_t0_t1_phase1.py --project_dir <path> --step summary
"""

from __future__ import annotations

import argparse
import json
import os
import sys
from datetime import datetime, timezone
from pathlib import Path

# coord_utils: linear coords are correct for sequence scoring operations here
try:
    from pipeline.coord_utils import validate_mask_coords
except ModuleNotFoundError:
    import importlib.util, pathlib as _pl
    _spec = importlib.util.spec_from_file_location(
        "coord_utils", _pl.Path(__file__).parent / "coord_utils.py")
    _mod = importlib.util.module_from_spec(_spec); _spec.loader.exec_module(_mod)
    validate_mask_coords = _mod.validate_mask_coords


def timestamp() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


def append_jsonl(path: Path, record: dict) -> None:
    with open(path, "a", encoding="utf-8") as f:
        f.write(json.dumps(record, ensure_ascii=False) + "\n")
        f.flush()
        os.fsync(f.fileno())


def load_finished_set(path: Path, key: str = "seq_id") -> set[str]:
    finished: set[str] = set()
    if path.exists():
        for line in path.read_text(encoding="utf-8").splitlines():
            line = line.strip()
            if not line:
                continue
            try:
                finished.add(json.loads(line)[key])
            except (json.JSONDecodeError, KeyError):
                pass
    return finished


def parse_fasta_seq_ids(path: Path) -> dict[str, str]:
    """seq_id = first whitespace-separated token after '>' (matches cluster_and_filter_v2)."""
    seqs: dict[str, str] = {}
    sid, buf = None, []
    for line in path.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if line.startswith(">"):
            if sid and buf:
                seqs[sid] = "".join(buf)
            rest = line[1:].strip()
            sid = rest.split()[0] if rest else ""
            buf = []
        elif line and sid:
            buf.append(line.upper())
    if sid and buf:
        seqs[sid] = "".join(buf)
    return seqs


def design_eligible_0indexed(mask: dict) -> list[int]:
    """Linear indices where MPNN may change sequence: CDR span minus root-fixed."""
    redesign = mask["design_mask"].get("redesign_cdrs", [])
    regions = mask["cdr_regions"]
    root_cfg = mask.get("root_constraints", {})
    pos: list[int] = []
    for k in redesign:
        c = regions.get(k, {})
        ls, le = c.get("linear_start"), c.get("linear_end")
        if ls is None or le is None:
            continue
        fixed = set(root_cfg.get(k, {}).get("fixed_0indexed", []))
        for i in range(int(ls), int(le) + 1):
            if i not in fixed:
                pos.append(i)
    return sorted(pos)


def design_loop_body_0indexed(mask: dict) -> list[int]:
    """Design-eligible minus semiopen (identity gate: diversity in fully open loop only)."""
    eligible = design_eligible_0indexed(mask)
    semi: set[int] = set()
    for k in mask["design_mask"].get("redesign_cdrs", []):
        for p in mask.get("root_constraints", {}).get(k, {}).get("semiopen_0indexed", []):
            semi.add(int(p))
    return [i for i in eligible if i not in semi]


def redesign_cdr_identity(seq: str, wt_seq: str, positions: list[int]) -> float:
    if not positions:
        return 1.0
    n = sum(
        1
        for i in positions
        if i < len(seq) and i < len(wt_seq) and seq[i] == wt_seq[i]
    )
    return n / len(positions)


def load_mask(project_dir: Path) -> dict:
    p = project_dir / "config" / "mask_strategy.json"
    if not p.exists():
        print(f"[ERROR] {p} not found")
        sys.exit(1)
    mask = json.loads(p.read_text(encoding="utf-8"))
    validate_mask_coords(mask, abort=True)   # coordinate consistency gate
    return mask


def step_t0_oasis(project_dir: Path) -> None:
    try:
        import promb
    except ImportError:
        print("[ERROR] promb not installed. Use: conda run -n anarcii ...")
        sys.exit(1)

    mask = load_mask(project_dir)
    wt_seq = mask["wt_sequence"]
    # Identity gate: fully open loop body only (roots + semiopen excluded).
    idn_pos = design_loop_body_0indexed(mask)
    ft = mask.get("filter_thresholds", {})
    oasis_frac = float(ft.get("oasis_min_fraction_of_wt", 0.80))
    max_redesign_idn = float(ft.get("t0_max_redesign_cdr_identity", 0.70))

    p1 = project_dir / "phase1_generation"
    raw_fasta = p1 / "mpnn_raw_sequences.fasta"
    if not raw_fasta.exists():
        print(f"[ERROR] {raw_fasta} missing. Run run_mpnn_v2.py first.")
        sys.exit(1)

    seqs = parse_fasta_seq_ids(raw_fasta)
    checkpoint = p1 / "t0_oasis_blast.jsonl"
    finished = load_finished_set(checkpoint)
    print(f"[T0-OASis] {len(seqs)} sequences in FASTA, {len(finished)} already in checkpoint")

    db = promb.init_db("human-oas", verbose=False)
    wt_peptides = db.chop_seq_peptides(wt_seq)
    wt_found = sum(1 for p in wt_peptides if db.contains(p))
    wt_coverage = wt_found / len(wt_peptides) if wt_peptides else 0.0
    oasis_threshold = wt_coverage * oasis_frac
    print(f"[T0-OASis] WT coverage {wt_found}/{len(wt_peptides)} = {wt_coverage:.4f}")
    print(f"[T0-OASis] Pass threshold coverage >= {oasis_threshold:.4f} ({oasis_frac:.2f}×WT)")
    print(
        f"[T0-OASis] Max identity on loop-body positions < {max_redesign_idn:.2f} "
        f"({len(idn_pos)} positions, roots + semiopen excluded)"
    )

    scored = 0
    for seq_id, sequence in seqs.items():
        if seq_id in finished:
            continue
        peptides = db.chop_seq_peptides(sequence)
        if not peptides:
            append_jsonl(
                checkpoint,
                {
                    "seq_id": seq_id,
                    "phase": "t0_oasis",
                    "oasis_coverage": 0.0,
                    "pass": False,
                    "reason": "too_short",
                    "timestamp": timestamp(),
                },
            )
            finished.add(seq_id)
            continue

        found = sum(1 for p in peptides if db.contains(p))
        coverage = found / len(peptides)
        global_identity = sum(a == b for a, b in zip(sequence, wt_seq)) / len(wt_seq)
        rid = redesign_cdr_identity(sequence, wt_seq, idn_pos)

        passed = coverage >= oasis_threshold and rid < max_redesign_idn
        reason = ""
        if coverage < oasis_threshold:
            reason = f"oasis_low ({coverage:.3f} < {oasis_threshold:.3f})"
        elif rid >= max_redesign_idn:
            reason = f"design_eligible_identity_high ({rid:.3f})"

        append_jsonl(
            checkpoint,
            {
                "seq_id": seq_id,
                "phase": "t0_oasis",
                "oasis_coverage": round(coverage, 4),
                "wt_identity": round(global_identity, 4),
                "redesign_cdr_identity": round(rid, 4),
                "cdr_identity": round(rid, 4),
                "identity_positions_n": len(idn_pos),
                "pass": passed,
                "reason": reason if not passed else "ok",
                "timestamp": timestamp(),
            },
        )
        finished.add(seq_id)
        scored += 1
        if scored % 50 == 0:
            print(f"  … scored {scored} new")

    all_records = load_jsonl_all(checkpoint)
    passed = [r for r in all_records if r["pass"]]
    failed = [r for r in all_records if not r["pass"]]
    print(f"[T0-OASis] {len(passed)} PASS / {len(failed)} FAIL / {len(all_records)} total")


def load_jsonl_all(path: Path) -> list[dict]:
    if not path.exists():
        return []
    out = []
    for line in path.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if line:
            out.append(json.loads(line))
    return out


def step_t1_ablang(project_dir: Path) -> None:
    try:
        import ablang
    except ImportError:
        print("[ERROR] ablang not installed. Use: conda run -n affmat ...")
        sys.exit(1)

    mask = load_mask(project_dir)
    wt_seq = mask["wt_sequence"]
    ft = mask.get("filter_thresholds", {})
    ratio_min = float(ft.get("ablang_score_ratio_min", 1.5))

    p1 = project_dir / "phase1_generation"
    t0_path = p1 / "t0_oasis_blast.jsonl"
    if not t0_path.exists():
        print("[ERROR] Run --step t0_oasis first.")
        sys.exit(1)

    t0_passed: dict[str, dict] = {}
    for rec in load_jsonl_all(t0_path):
        if rec.get("pass"):
            t0_passed[rec["seq_id"]] = rec

    raw_fasta = p1 / "mpnn_raw_sequences.fasta"
    seqs = parse_fasta_seq_ids(raw_fasta)
    candidates = {sid: seqs[sid] for sid in t0_passed if sid in seqs}
    missing = len(t0_passed) - len(candidates)
    if missing:
        print(f"[WARN] {missing} T0-pass ids not found in FASTA")

    t1_path = p1 / "t1_ablang_scores.jsonl"
    finished = load_finished_set(t1_path)
    print(f"[T1-AbLang] {len(candidates)} T0-passed, {len(finished)} already scored")

    print("[T1-AbLang] Loading model…")
    heavy_model = ablang.pretrained("heavy")
    heavy_model.freeze()

    wt_logits = heavy_model([wt_seq], mode="likelihood")
    wt_score = float(wt_logits.mean())
    score_threshold = wt_score * ratio_min
    print(f"  WT mean logP: {wt_score:.4f}")
    print(f"  Threshold (WT × {ratio_min}): {score_threshold:.4f}")

    scored = 0
    for seq_id, sequence in candidates.items():
        if seq_id in finished:
            continue
        logits = heavy_model([sequence], mode="likelihood")
        score = float(logits.mean())
        passed = score >= score_threshold
        append_jsonl(
            t1_path,
            {
                "seq_id": seq_id,
                "phase": "t1_ablang",
                "ablang_mean_logp": round(score, 4),
                "wt_score": round(wt_score, 4),
                "score_ratio": round(score / wt_score, 4) if wt_score != 0 else 0.0,
                "pass": passed,
                "reason": "ok"
                if passed
                else f"score_low ({score:.4f} < {score_threshold:.4f})",
                "timestamp": timestamp(),
            },
        )
        finished.add(seq_id)
        scored += 1
        if scored % 20 == 0:
            print(f"  … scored {scored} new")

    all_records = load_jsonl_all(t1_path)
    passed = [r for r in all_records if r["pass"]]
    print(f"[T1-AbLang] {len(passed)} PASS / {len(all_records)} scored total")


def step_summary(project_dir: Path) -> None:
    p1 = project_dir / "phase1_generation"
    raw_fasta = p1 / "mpnn_raw_sequences.fasta"
    t0_path = p1 / "t0_oasis_blast.jsonl"
    t1_path = p1 / "t1_ablang_scores.jsonl"
    manifest_path = project_dir / "project_manifest.json"

    n_raw = 0
    if raw_fasta.exists():
        n_raw = sum(1 for ln in raw_fasta.read_text().splitlines() if ln.startswith(">"))

    t0_pass = sum(1 for r in load_jsonl_all(t0_path) if r.get("pass"))
    t1_pass = sum(1 for r in load_jsonl_all(t1_path) if r.get("pass"))

    print("=" * 60)
    print(f"  Phase 1 T0/T1 summary — {project_dir.name}")
    print("=" * 60)
    print(f"  MPNN raw (headers): {n_raw}")
    print(f"  After T0 (OASis):    {t0_pass}")
    print(f"  After T1 (AbLang):   {t1_pass}")
    if n_raw:
        print(f"  T1 survival:         {t1_pass}/{n_raw} = {100 * t1_pass / n_raw:.1f}%")
    print("=" * 60)

    if manifest_path.exists():
        m = json.loads(manifest_path.read_text(encoding="utf-8"))
        m["last_updated"] = timestamp()
        stats = m.setdefault("stats", {})
        stats["total_generated"] = n_raw
        stats["after_t0_oasis"] = t0_pass
        stats["after_t1_ablang"] = t1_pass
        ps = m.setdefault("phase_status", {})
        ps["t0_oasis"] = "DONE" if t0_path.exists() else ps.get("t0_oasis", "PENDING")
        ps["t1_ablang"] = "DONE" if t1_path.exists() else ps.get("t1_ablang", "PENDING")
        manifest_path.write_text(json.dumps(m, indent=2), encoding="utf-8")
        print(f"  Updated {manifest_path.name}")


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--project_dir", type=Path, required=True)
    ap.add_argument(
        "--step",
        required=True,
        choices=["t0_oasis", "t1_ablang", "summary"],
    )
    args = ap.parse_args()
    project_dir = args.project_dir.resolve()
    (project_dir / "phase1_generation").mkdir(parents=True, exist_ok=True)

    if args.step == "t0_oasis":
        step_t0_oasis(project_dir)
    elif args.step == "t1_ablang":
        step_t1_ablang(project_dir)
    else:
        step_summary(project_dir)


if __name__ == "__main__":
    main()
