"""
Optimize 7D12-SR CMC/dev risk to be closer to clinical SR molecules.

Goal (practical):
  - Reduce hydrophobic patch peak (hp_max9 / hydro_patch_max9) while keeping SR philosophy:
    * Do not mutate CDRs (default)
    * Do not mutate anchors / vernier / hallmark / ND-dependent positions
    * Prefer structure-confirmed surface-exposed positions (relSASA>=0.25 in 4KRL)
    * Prefer substitutions toward the chosen human template residue when it is less hydrophobic
  - Recompute immunogenicity + developability for candidate sequences (cached IEDB calls)

Inputs:
  - output/7D12/7d12_4krl_decision_tree_recompute.md (SR sequence)
  - output/7D12/7d12_4krl_per_residue_surface_metrics.csv (relSASA by IMGT position)
  - core/data/position_sets/imgt_position_sets.yaml (protected sets)
  - core/data/framework_library/vh_frameworks.with_cdr12.canonical_input.yaml (template residues)

Outputs:
  - output/7D12/7d12_sr_cmc_optimization_candidates.csv
  - output/7D12/7d12_sr_cmc_optimization.md
"""

from __future__ import annotations

import hashlib
import io
import json
import re
import time
from dataclasses import dataclass
from pathlib import Path

import pandas as pd
import requests
import yaml

PROJECT_ROOT = Path(__file__).resolve().parent.parent
OUT_DIR = PROJECT_ROOT / "output" / "7D12"
OUT_DIR.mkdir(parents=True, exist_ok=True)

DECISION_MD = OUT_DIR / "7d12_4krl_decision_tree_recompute.md"
SURFACE_CSV = OUT_DIR / "7d12_4krl_per_residue_surface_metrics.csv"

SSOT_YAML = PROJECT_ROOT / "core" / "data" / "position_sets" / "imgt_position_sets.yaml"
FRAMEWORK_YAML = PROJECT_ROOT / "core" / "data" / "framework_library" / "vh_frameworks.with_cdr12.canonical_input.yaml"

CACHE_DIR = OUT_DIR / "iedb_cache"
CACHE_DIR.mkdir(parents=True, exist_ok=True)

OUT_CSV = OUT_DIR / "7d12_sr_cmc_optimization_candidates.csv"
OUT_MD = OUT_DIR / "7d12_sr_cmc_optimization.md"

IEDB_API_URL = "https://tools-cluster-interface.iedb.org/tools_api/mhcii/"
DEFAULT_ALLELES = (
    "HLA-DRB1*01:01,HLA-DRB1*03:01,HLA-DRB1*04:01,HLA-DRB1*04:05,"
    "HLA-DRB1*07:01,HLA-DRB1*08:02,HLA-DRB1*09:01,HLA-DRB1*11:01,"
    "HLA-DRB1*12:01,HLA-DRB1*13:02,HLA-DRB1*15:01"
)

HYDROPHOBIC = set("AVILMFWY")
AROMATIC = set("FWY")

# User constraint: do NOT mutate CDRs (default).
ALLOW_CDR_MUTATIONS = False


# IMGT CDR ranges (approx, heavy chain IMGT). Used only for "do not mutate CDRs".
CDR_RANGES = [
    (27, 38),   # CDR1
    (56, 65),   # CDR2
    (105, 117), # CDR3 (FR4 starts ~118)
]


def is_in_cdr(imgt_pos: int) -> bool:
    return any(a <= imgt_pos <= b for a, b in CDR_RANGES)


def _extract_sr_sequence(md_text: str) -> str:
    m = re.search(r"### SR \(strict surface only\)\n([A-Z]+)\n", md_text)
    if not m:
        raise RuntimeError("Could not find SR sequence block in decision_tree_recompute.md")
    return m.group(1).strip()


def cached_iedb_predict(sequence: str, alleles: str, method: str = "recommended", length: int = 15) -> pd.DataFrame:
    key = hashlib.sha256(f"{sequence}|{alleles}|{method}|{length}".encode("utf-8")).hexdigest()[:24]
    path = CACHE_DIR / f"{key}.tsv"
    if path.exists():
        return pd.read_csv(path, sep="\t")

    payload = {"method": method, "sequence_text": sequence, "allele": alleles, "length": length}
    for attempt in range(3):
        try:
            r = requests.post(IEDB_API_URL, data=payload, timeout=90)
            if r.status_code == 200:
                df = pd.read_csv(io.StringIO(r.text), sep="\t")
                df.to_csv(path, sep="\t", index=False)
                time.sleep(1.5)
                return df
        except Exception:
            pass
        time.sleep(2 ** (attempt + 1))
    raise RuntimeError("IEDB request failed after retries")


def normalize_rank_col(df: pd.DataFrame) -> tuple[pd.DataFrame, str]:
    df = df.copy()
    df.columns = [c.lower().replace(" ", "_") for c in df.columns]
    if "percentile_rank" in df.columns:
        return df, "percentile_rank"
    if "rank" in df.columns:
        return df, "rank"
    for c in df.columns:
        if "rank" in c:
            return df, c
    raise RuntimeError(f"No rank-like column found in IEDB output columns: {df.columns.tolist()}")


def compute_immuno_features(df: pd.DataFrame, rank_col: str, rank1: float = 1.0, rank2: float = 2.0) -> dict:
    s1 = df[df[rank_col] <= rank1]
    s2 = df[df[rank_col] <= rank2]
    allele_col = "allele" if "allele" in df.columns else None
    return {
        "B_total_1pct": int(len(s1)),
        "B_total_2pct": int(len(s2)),
        "B_breadth_1pct": int(s1[allele_col].nunique()) if allele_col else 0,
        "B_breadth_2pct": int(s2[allele_col].nunique()) if allele_col else 0,
        "min_rank": float(df[rank_col].min()),
    }


def compute_developability(seq: str) -> dict:
    ngly = list(re.finditer(r"N[^P][ST]", seq))
    deamid = list(re.finditer(r"N[GSNQ]|Q[GS]", seq))
    iso = list(re.finditer(r"D[GS]", seq))
    ox_m = seq.count("M")
    ox_w = seq.count("W")
    cys = seq.count("C")
    extra_cys_flag = int(cys > 2)

    L = len(seq)
    net_charge = sum(seq.count(x) for x in "KR") + 0.1 * seq.count("H") - sum(seq.count(x) for x in "DE")
    hydro = sum(1 for a in seq if a in HYDROPHOBIC) / L
    arom = sum(1 for a in seq if a in AROMATIC) / L

    def hydro_frac(s: str) -> float:
        return sum(1 for a in s if a in HYDROPHOBIC) / len(s)

    def abs_charge(s: str) -> float:
        return abs(sum(s.count(x) for x in "KR") + 0.1 * s.count("H") - sum(s.count(x) for x in "DE"))

    def slide(seq_: str, w: int, fn):
        if len(seq_) < w:
            return 0.0, 0
        vals = [fn(seq_[i:i + w]) for i in range(len(seq_) - w + 1)]
        if fn is hydro_frac:
            cnt = sum(1 for v in vals if v >= 0.6)
        else:
            cnt = sum(1 for v in vals if v >= 4)
        return float(max(vals)), int(cnt)

    hp9, hp9_cnt = slide(seq, 9, hydro_frac)
    cp7, cp7_cnt = slide(seq, 7, abs_charge)

    p = {}
    p["ngly"] = 8 * len(ngly)
    if extra_cys_flag:
        p["extra_cys"] = 15
    p["deamid"] = 2 * len(deamid)
    p["iso"] = 3 * len(iso)
    if hp9 >= 0.7:
        p["hydro_patch"] = 10
    elif hp9 >= 0.6:
        p["hydro_patch"] = 6
    if cp7 >= 7:
        p["charge_patch"] = 10
    elif cp7 >= 5:
        p["charge_patch"] = 6

    dev_score = max(0, 100 - sum(p.values()))
    dev_risk_tier = "Low" if dev_score >= 80 else "Medium" if dev_score >= 60 else "High"

    return {
        "dev_score": int(dev_score),
        "dev_risk_tier": dev_risk_tier,
        "dev_penalty_breakdown": json.dumps(p, ensure_ascii=False),
        "ngly_count": int(len(ngly)),
        "deamid_count": int(len(deamid)),
        "isoasp_count": int(len(iso)),
        "ox_m_count": int(ox_m),
        "ox_w_count": int(ox_w),
        "cysteine_count": int(cys),
        "extra_cys_flag": int(extra_cys_flag),
        "net_charge": float(net_charge),
        "hydrophobic_frac_global": float(hydro),
        "aromatic_frac_global": float(arom),
        "hydro_patch_max9": float(hp9),
        "charge_patch_max7": float(cp7),
        "total_len": int(L),
    }


def hydrophobic_windows(seq: str, w: int = 9) -> list[dict]:
    rows = []
    for i in range(len(seq) - w + 1):
        win = seq[i:i + w]
        frac = sum(1 for a in win if a in HYDROPHOBIC) / w
        rows.append({"start_idx": i, "end_idx": i + w - 1, "window": win, "hydro_frac": float(frac)})
    return rows


def load_protected_sets(ssot_yaml: Path) -> dict[str, set[int]]:
    obj = yaml.safe_load(ssot_yaml.read_text(encoding="utf-8"))
    pos_sets = obj.get("imgt_position_sets", {})
    anchors = set(int(x) for x in pos_sets.get("imgt_anchor_positions", []) or [])
    vernier = set(int(x) for x in pos_sets.get("vernier_anchor_positions", []) or [])
    hallmark = set(int(x) for x in pos_sets.get("vhh_hallmark_positions", []) or [])

    nd = obj.get("north_dunbrack", {}).get("dependent_positions_v2_lite", {}) or {}
    nd_all: set[int] = set()
    if isinstance(nd, dict):
        for _, bucket in nd.items():
            if isinstance(bucket, dict):
                for _, arr in bucket.items():
                    if isinstance(arr, list):
                        nd_all |= set(int(x) for x in arr)

    protected = anchors | vernier | hallmark | nd_all
    return {
        "anchors": anchors,
        "vernier": vernier,
        "hallmark": hallmark,
        "nd_all": nd_all,
        "protected_all": protected,
    }


def load_template_positions(framework_yaml: Path, germline: str = "IGHV3-23*01") -> dict[int, str]:
    obj = yaml.safe_load(framework_yaml.read_text(encoding="utf-8"))
    recs = obj.get("frameworks", [])
    rec = next((r for r in recs if r.get("germline") == germline), None)
    if rec is None:
        raise RuntimeError(f"Template germline not found in framework YAML: {germline}")
    pos_map = rec.get("numbering_evidence", {}).get("positions", {})
    out: dict[int, str] = {}
    for k, v in pos_map.items():
        if str(k).isdigit():
            out[int(k)] = str(v)
    return out


def load_surface_by_imgt(surface_csv: Path) -> pd.DataFrame:
    df = pd.read_csv(surface_csv)
    # Keep only rows with an IMGT position (int) and rel_sasa
    df = df[df["imgt_pos"].notna()].copy()
    df["imgt_pos"] = df["imgt_pos"].astype(int)
    # There can be multiple residues mapping to the same IMGT position due to insertions/alignments.
    # For "is this IMGT position surface-exposed?" we take the maximum relSASA observed.
    agg = (
        df.groupby("imgt_pos", as_index=False)
        .agg(
            rel_sasa=("rel_sasa", "max"),
            is_surface=("is_surface", "max"),
            kd_hydropathy=("kd_hydropathy", "mean"),
        )
        .copy()
    )
    return agg


def main() -> None:
    if not DECISION_MD.exists():
        raise RuntimeError(f"Missing: {DECISION_MD}")
    if not SURFACE_CSV.exists():
        raise RuntimeError(f"Missing: {SURFACE_CSV} (run compute_7d12_4krl_surface_hydrophilicity.py)")
    if not SSOT_YAML.exists():
        raise RuntimeError(f"Missing: {SSOT_YAML}")
    if not FRAMEWORK_YAML.exists():
        raise RuntimeError(f"Missing: {FRAMEWORK_YAML}")

    sr_seq = _extract_sr_sequence(DECISION_MD.read_text(encoding="utf-8"))
    protected = load_protected_sets(SSOT_YAML)
    template = load_template_positions(FRAMEWORK_YAML, germline="IGHV3-23*01")
    surf = load_surface_by_imgt(SURFACE_CSV)
    surf_by_pos = surf.drop_duplicates("imgt_pos").set_index("imgt_pos")

    # Map SR sequence residues to IMGT positions
    import sys

    sys.path.append(str(PROJECT_ROOT))
    from core.numbering.imgt_anarcii import imgt_number_anarcii_indexed

    numbered = imgt_number_anarcii_indexed(sr_seq)
    pos_by_idx: dict[int, int] = {}
    aa_by_pos: dict[int, str] = {}
    for r in numbered["rows"]:
        p = int(r["pos"])
        i = int(r["seq_idx"])
        pos_by_idx[i] = p
        aa_by_pos[p] = str(r["aa"])

    # Identify the worst hydrophobic windows (global max)
    wins = hydrophobic_windows(sr_seq, w=9)
    max_h = max(w["hydro_frac"] for w in wins)
    top = [w for w in wins if w["hydro_frac"] >= max_h - 1e-9]

    # Candidate mutation sites (single mutants):
    #   - Focus on residues inside the worst hydrophobic 9-mer window(s)
    #   - Must be surface-exposed in structure (relSASA>=0.25)
    #   - Must not be protected (anchors/vernier/hallmark/ND-dependent)
    #   - By default, do NOT mutate CDRs; however, we will separately consider a minimal CDR3 option
    #     if the only surface-exposed residue in the window lies in CDR3.
    candidates: list[dict] = []
    POLAR_OPTIONS = ["S", "T", "N", "Q", "E", "D"]
    for w in top:
        for idx in range(w["start_idx"], w["end_idx"] + 1):
            if idx not in pos_by_idx:
                continue
            p = pos_by_idx[idx]
            aa = sr_seq[idx]
            if aa not in HYDROPHOBIC:
                continue
            in_cdr = is_in_cdr(p)
            if p in protected["protected_all"]:
                continue
            if p not in surf_by_pos.index:
                continue
            rel = float(surf_by_pos.loc[p, "rel_sasa"])
            if rel < 0.25:
                continue
            hu = template.get(p)

            # Build a short list of target residues:
            # 1) If human template residue exists and is non-hydrophobic, prefer it (keeps "human-like").
            # 2) Otherwise, propose conservative polar surface-solubilizing options (S/T first).
            targets: list[str] = []
            if hu and hu != aa and hu not in HYDROPHOBIC:
                targets.append(hu)
            for t in POLAR_OPTIONS:
                if t != aa and t not in targets:
                    targets.append(t)

            for t in targets:
                # Default: only FR mutations
                if in_cdr:
                    continue
                candidates.append(
                    {
                        "imgt_pos": p,
                        "seq_idx": idx,
                        "from": aa,
                        "to": t,
                        "rel_sasa": rel,
                        "in_cdr": in_cdr,
                        "window_start_idx": w["start_idx"],
                        "window": w["window"],
                        "window_hydro_frac": w["hydro_frac"],
                        "reason": (
                            "surface_exposed_hydrophobic_in_top_patch_to_template"
                            if t == hu
                            else "surface_exposed_hydrophobic_in_top_patch_to_polar"
                        ),
                    }
                )

    # Optionally collect CDR-surface candidates inside top window(s) (for optional double mutants).
    cdr_surface_candidates: list[dict] = []
    if ALLOW_CDR_MUTATIONS:
        for w in top:
            for idx in range(w["start_idx"], w["end_idx"] + 1):
                if idx not in pos_by_idx:
                    continue
                p = pos_by_idx[idx]
                aa = sr_seq[idx]
                if aa not in HYDROPHOBIC:
                    continue
                if p in protected["protected_all"]:
                    continue
                if p not in surf_by_pos.index:
                    continue
                rel = float(surf_by_pos.loc[p, "rel_sasa"])
                if rel < 0.25:
                    continue
                if not is_in_cdr(p):
                    continue
                # Keep options minimal to reduce functional risk.
                for t in ["S", "T"]:
                    if t == aa:
                        continue
                    cdr_surface_candidates.append(
                        {
                            "imgt_pos": p,
                            "seq_idx": idx,
                            "from": aa,
                            "to": t,
                            "rel_sasa": rel,
                            "in_cdr": True,
                            "window_start_idx": w["start_idx"],
                            "window": w["window"],
                            "window_hydro_frac": w["hydro_frac"],
                            "reason": "cdr_surface_exposed_hydrophobic_in_top_patch_to_polar (higher functional risk)",
                        }
                    )

    # Build candidate sequences (baseline + single mutants + a few double mutants (FR + CDR) if needed)
    @dataclass
    class Variant:
        name: str
        sequence: str
        mutation: str

    vars_: list[Variant] = [Variant("sr_baseline", sr_seq, mutation="")]
    single_vars: list[Variant] = []
    for c in candidates[:16]:  # cap to keep IEDB calls manageable
        s = list(sr_seq)
        s[c["seq_idx"]] = c["to"]
        tag = "CDR" if c.get("in_cdr") else "FR"
        single_vars.append(
            Variant(
                f"sr_opt_{tag}_{c['imgt_pos']}{c['from']}>{c['to']}",
                "".join(s),
                mutation=f"{c['imgt_pos']}:{c['from']}>{c['to']}",
            )
        )
    vars_.extend(single_vars)

    # If baseline hp_max9 is very high and single FR edits cannot push it below 0.7,
    # try one additional surface CDR edit *in the same top window* (double mutant).
    # This is explicitly a higher functional risk option.
    def hp9_of(seq: str) -> float:
        return max(w["hydro_frac"] for w in hydrophobic_windows(seq, w=9))

    best_single_hp9 = hp9_of(sr_seq)
    best_single_name = "sr_baseline"
    best_single_seq = sr_seq
    for v in single_vars:
        h = hp9_of(v.sequence)
        if h < best_single_hp9:
            best_single_hp9 = h
            best_single_name = v.name
            best_single_seq = v.sequence

    double_vars: list[Variant] = []
    if ALLOW_CDR_MUTATIONS and best_single_hp9 >= 0.7 and cdr_surface_candidates:
        # only combine the best single FR candidate with up to 2 CDR options
        for c in cdr_surface_candidates[:2]:
            s = list(best_single_seq)
            s[c["seq_idx"]] = c["to"]
            double_vars.append(
                Variant(
                    f"{best_single_name}__plus_CDR_{c['imgt_pos']}{c['from']}>{c['to']}",
                    "".join(s),
                    mutation=f"{best_single_name} + {c['imgt_pos']}:{c['from']}>{c['to']}",
                )
            )
    vars_.extend(double_vars)

    # Evaluate each variant (immuno + dev)
    rows = []
    for v in vars_:
        df_raw = cached_iedb_predict(v.sequence, DEFAULT_ALLELES, method="recommended", length=15)
        df_norm, rank_col = normalize_rank_col(df_raw)
        immuno = compute_immuno_features(df_norm, rank_col, rank1=1.0, rank2=2.0)
        dev = compute_developability(v.sequence)
        rows.append({"variant": v.name, "mutation": v.mutation, **immuno, **dev})
    df_eval = pd.DataFrame(rows)

    # Join candidate metadata for interpretability
    df_cand = pd.DataFrame(candidates)
    df_cdr_cand = pd.DataFrame(cdr_surface_candidates)
    df_eval.to_csv(OUT_CSV, index=False)

    # Recommend: minimize hydro_patch_max9, then keep/improve immuno, then maximize dev_score
    df_rank = df_eval.copy()
    df_rank["rank_key"] = list(range(len(df_rank)))
    df_rank = df_rank.sort_values(
        ["hydro_patch_max9", "B_total_1pct", "B_breadth_1pct", "dev_score"],
        ascending=[True, True, True, False],
    )
    best = df_rank.iloc[0].to_dict()

    with open(OUT_MD, "w", encoding="utf-8") as f:
        f.write("# 7D12-SR CMC Optimization (structure-guided)\n\n")
        f.write("## Baseline SR\n\n")
        f.write(f"- Source: `{DECISION_MD}`\n")
        f.write(f"- Sequence: {sr_seq}\n\n")

        f.write("## Worst hydrophobic 9-mer window(s) in SR (proxy for hp_max9)\n\n")
        f.write(f"- hydro_patch_max9 (by definition) = **{max_h:.6f}**\n")
        f.write(pd.DataFrame(top).to_markdown(index=False) + "\n\n")

        f.write("## Candidate mutation sites (surface-exposed, not protected, not CDR; to human template non-hydrophobic AA)\n\n")
        if df_cand.empty:
            f.write("No candidates found under the strict constraints. This usually means the top hydrophobic window is dominated by CDR residues or protected/buried residues.\n\n")
        else:
            f.write(df_cand.to_markdown(index=False) + "\n\n")

        f.write("### Optional CDR-surface candidates (disabled by default)\n\n")
        f.write(f"- ALLOW_CDR_MUTATIONS={ALLOW_CDR_MUTATIONS}\n\n")
        if df_cdr_cand.empty:
            f.write("None evaluated.\n\n")
        else:
            f.write(df_cdr_cand.to_markdown(index=False) + "\n\n")

        f.write("## Evaluated candidates (immuno + dev)\n\n")
        show_cols = [
            "variant",
            "mutation",
            "B_total_1pct",
            "B_total_2pct",
            "B_breadth_1pct",
            "min_rank",
            "dev_score",
            "dev_risk_tier",
            "hydro_patch_max9",
            "charge_patch_max7",
            "ngly_count",
            "extra_cys_flag",
            "ox_w_count",
        ]
        f.write(df_eval[show_cols].to_markdown(index=False) + "\n\n")

        f.write("## Recommended candidate (ranking: lower hydro_patch_max9 → lower immuno burden → higher dev_score)\n\n")
        f.write("```text\n")
        f.write(f"{best['variant']} ({best['mutation']})\n")
        f.write(f"hydro_patch_max9={best['hydro_patch_max9']}, dev_score={best['dev_score']}, B_total_1pct={best['B_total_1pct']}\n")
        f.write("```\n\n")

        f.write("### Disclaimer\n")
        f.write("In silico binding prediction and sequence-based developability proxies; experimental validation required.\n")

    print(f"Wrote: {OUT_CSV}")
    print(f"Wrote: {OUT_MD}")


if __name__ == "__main__":
    main()

