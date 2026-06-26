import json
import hashlib
import difflib
import argparse
from pathlib import Path

import yaml

PROJECT_ROOT = Path(__file__).resolve().parent.parent


def sha256_file(path: Path) -> str:
    h = hashlib.sha256()
    with open(path, "rb") as f:
        h.update(f.read())
    return h.hexdigest()


def load_ighv3_23_imgt_pos_map() -> dict[int, str]:
    fw_path = (
        PROJECT_ROOT
        / "core"
        / "data"
        / "framework_library"
        / "vh_frameworks.with_cdr12.canonical_input.yaml"
    )
    data = yaml.safe_load(fw_path.read_text(encoding="utf-8"))
    for fw in data.get("frameworks", []):
        if fw.get("germline") == "IGHV3-23*01":
            positions = fw.get("numbering_evidence", {}).get("positions", {})
            return {int(k): v for k, v in positions.items()}
    raise RuntimeError("IGHV3-23*01 not found in framework library YAML")


def build_native_idx_to_imgt_pos(native_seq: str, human_pos_map: dict[int, str]) -> dict[int, int]:
    human_pos_list = sorted([p for p, aa in human_pos_map.items() if aa != "-"])
    human_seq = "".join(human_pos_map[p] for p in human_pos_list)
    s = difflib.SequenceMatcher(None, native_seq, human_seq)
    mapping: dict[int, int] = {}
    for tag, i1, i2, j1, j2 in s.get_opcodes():
        if tag == "equal":
            for k in range(i2 - i1):
                mapping[i1 + k] = human_pos_list[j1 + k]
        elif tag == "replace" and (i2 - i1) == (j2 - j1):
            # heuristic: treat equal-length replace as aligned block
            for k in range(i2 - i1):
                mapping[i1 + k] = human_pos_list[j1 + k]
    return mapping


def apply_subs_by_imgt_positions(
    native_seq: str,
    idx_to_pos: dict[int, int],
    human_pos_map: dict[int, str],
    target_positions: set[int],
) -> tuple[str, list[dict]]:
    res = list(native_seq)
    muts: list[dict] = []
    for idx, pos in idx_to_pos.items():
        if pos in target_positions and pos in human_pos_map:
            to_aa = human_pos_map[pos]
            if to_aa != "-" and res[idx] != to_aa:
                muts.append({"imgt_pos": pos, "from": res[idx], "to": to_aa})
                res[idx] = to_aa
    return "".join(res), sorted(muts, key=lambda x: x["imgt_pos"])


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Recompute 7D12 humanization using decision tree (IMGT-only)."
    )
    parser.add_argument(
        "--native-seq",
        default=None,
        help="Override native sequence (e.g., 4KRL chain sequence). If omitted, uses checkpoint_01_numbering.json",
    )
    parser.add_argument(
        "--out-prefix",
        default="7d12",
        help="Output file prefix under output/7D12/",
    )
    args = parser.parse_args()

    out_dir = PROJECT_ROOT / "output" / "7D12"
    out_dir.mkdir(parents=True, exist_ok=True)

    # Native 7D12 source-of-truth for this repo (already IMGT-numbered in checkpoint)
    checkpoint = PROJECT_ROOT / "output" / "7d12_verified_run" / "checkpoint_01_numbering.json"
    if args.native_seq:
        native_seq = args.native_seq.strip().replace(" ", "").replace("\n", "").replace("\r", "")
        native_source = "cli(--native-seq)"
    else:
        if not checkpoint.exists():
            raise FileNotFoundError(f"Missing required file: {checkpoint}")
        native_seq = json.loads(checkpoint.read_text(encoding="utf-8"))["input_sequence"]
        native_source = str(checkpoint)

    # Position sets / strict surface
    strict_surface_path = PROJECT_ROOT / "output" / "surface_plasticity_positions_v1_strict.yaml"
    if not strict_surface_path.exists():
        raise FileNotFoundError(f"Missing required file: {strict_surface_path}")
    strict_surface = set(
        yaml.safe_load(strict_surface_path.read_text(encoding="utf-8"))[
            "surface_plasticity_positions_v1_strict"
        ]
    )

    # Decision tree guardrails (IMGT-only, from docs + SSOT)
    anchors = {26, 39, 55, 66, 104, 118}
    hallmarks = {37, 44, 45, 47}
    vernier = {28, 29, 94}

    # ND-dependent v2-lite currently empty in SSOT (slice-3-only inference fallback)
    nd_core: set[int] = set()
    nd_candidate: set[int] = set()

    tier0 = anchors | vernier | nd_core
    tier1 = hallmarks | nd_candidate
    fr_pos = set(range(1, 27)) | set(range(39, 56)) | set(range(66, 105))

    human_pos_map = load_ighv3_23_imgt_pos_map()
    idx_to_pos = build_native_idx_to_imgt_pos(native_seq, human_pos_map)
    mapping_coverage = len(idx_to_pos) / max(1, len(native_seq))

    # SR constructor: start from native; substitute only strict surface positions
    sr_seq, sr_muts = apply_subs_by_imgt_positions(
        native_seq=native_seq,
        idx_to_pos=idx_to_pos,
        human_pos_map=human_pos_map,
        target_positions=strict_surface,
    )

    # Quality gate: SR must not touch anchors/vernier/hallmarks/nd-dependent
    restricted = anchors | vernier | hallmarks | nd_core | nd_candidate
    bad = [m for m in sr_muts if m["imgt_pos"] in restricted]
    if bad:
        raise RuntimeError(f"SR violated restricted positions: {bad}")

    # BM constructor: start from native; humanize FR positions except tier0/tier1 (CDRs untouched)
    bm_targets = fr_pos - tier0 - tier1
    bm_seq, bm_muts = apply_subs_by_imgt_positions(
        native_seq=native_seq,
        idx_to_pos=idx_to_pos,
        human_pos_map=human_pos_map,
        target_positions=bm_targets,
    )

    # Audit mutation lists
    mut_jsonl = out_dir / f"{args.out_prefix}_variant_mutations.jsonl"
    with open(mut_jsonl, "w", encoding="utf-8") as f:
        for variant, muts in [("sr", sr_muts), ("bm", bm_muts)]:
            for m in muts:
                m_out = dict(m)
                m_out["variant"] = variant
                if variant == "sr":
                    m_out["reason"] = "surface_resurfacing_strict"
                else:
                    m_out["reason"] = "bm_framework_humanize_excluding_tier0_tier1"
                f.write(json.dumps(m_out, ensure_ascii=False) + "\n")

    # Markdown summary
    md = out_dir / f"{args.out_prefix}_decision_tree_recompute.md"
    with open(md, "w", encoding="utf-8") as f:
        f.write("# 7D12 Humanization (Decision Tree Recompute, IMGT-only)\n\n")
        f.write("## Inputs\n")
        f.write(f"- Native source: `{native_source}`\n")
        f.write(f"- Native length: {len(native_seq)}\n")
        f.write(f"- Native sha256: {hashlib.sha256(native_seq.encode('utf-8')).hexdigest()}\n")
        f.write(f"- Native->IMGT mapping coverage: {mapping_coverage:.3f}\n")
        f.write(f"- Template germline: IGHV3-23*01\n")
        f.write(f"- Strict surface set: `{strict_surface_path}` (n={len(strict_surface)})\n")
        f.write(f"- SSOT YAML: `{PROJECT_ROOT / 'core/data/position_sets/imgt_position_sets.yaml'}`\n")
        f.write(f"- SSOT sha256: {sha256_file(PROJECT_ROOT / 'core/data/position_sets/imgt_position_sets.yaml')}\n\n")

        f.write("## Decision Tree (docs/vhh_humanization_decision_tree_imgt.md)\n")
        f.write("- Step 1 (H2-driven): using H2 length=8 heuristic → treat as **H2-10-1** stable basin.\n")
        f.write("- Step 2 Pool: **Pool-S** (VH3-based; template IGHV3-23*01).\n")
        f.write("- Step 3 Strategy: **SR** recommended (stable basin; CDR3 GP fraction high; avoid over-BM).\n")
        f.write("- Step 4 BM tiers (plan only; experimental validation required):\n")
        f.write(f"  - Tier0: {sorted(tier0)}\n")
        f.write(f"  - Tier1: {sorted(tier1)}\n")
        f.write(f"  - Tier2: {sorted(strict_surface)}\n")
        f.write("  - Tier3: all other FR positions.\n\n")

        f.write("## Sequences\n")
        f.write("### Native\n")
        f.write(native_seq + "\n\n")
        f.write("### SR (strict surface only)\n")
        f.write(sr_seq + "\n")
        f.write(f"- SR mutation count: {len(sr_muts)}\n\n")
        f.write("### BM (framework humanize excluding tier0/tier1)\n")
        f.write(bm_seq + "\n")
        f.write(f"- BM mutation count: {len(bm_muts)}\n\n")

    print(f"Wrote: {md}")
    print(f"Wrote: {mut_jsonl}")
    print(f"SR muts: {len(sr_muts)} | BM muts: {len(bm_muts)}")


if __name__ == "__main__":
    main()

