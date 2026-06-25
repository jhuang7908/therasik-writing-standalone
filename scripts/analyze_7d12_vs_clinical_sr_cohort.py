"""
Compare 7D12 (4KRL) variants (native/SR/BM) to the *clinical SR* cohort (Slice-3).

Outputs:
  - output/7D12/7d12_4krl_vs_clinical_sr_cohort.md

Notes:
  - Clinical cohort metrics are taken from Slice-3 (native variants only), then filtered by
    Humanization Strategy starting with "SR" from reports/slice3_vhh_comprehensive_functional_library.csv
  - 7D12 variant metrics are taken from output/7D12/7d12_4krl_eval_table.csv
  - "Humanization degree" here is reported as IMGT-position identity vs the selected template germline
    (IGHV3-23*01) across overlapping IMGT positions.
"""

from __future__ import annotations

import re
from pathlib import Path

import pandas as pd
import yaml

PROJECT_ROOT = Path(__file__).resolve().parent.parent

OUT_DIR = PROJECT_ROOT / "output" / "7D12"
OUT_DIR.mkdir(parents=True, exist_ok=True)

DECISION_MD = OUT_DIR / "7d12_4krl_decision_tree_recompute.md"
EVAL_TABLE = OUT_DIR / "7d12_4krl_eval_table.csv"

SLICE3_IMM = PROJECT_ROOT / "reports" / "slice3_vhh_immunogenicity_features.csv"
SLICE3_DEV = PROJECT_ROOT / "reports" / "slice3_vhh_developability_features_native_sr_bm.csv"
SLICE3_META = PROJECT_ROOT / "reports" / "slice3_vhh_comprehensive_functional_library.csv"

FRAMEWORK_YAML = PROJECT_ROOT / "core" / "data" / "framework_library" / "vh_frameworks.with_cdr12.canonical_input.yaml"

OUT_MD = OUT_DIR / "7d12_4krl_vs_clinical_sr_cohort.md"


def _extract_sequences_from_recompute_md(md_text: str) -> dict[str, str]:
    out = {}
    blocks = [
        ("native", "### Native"),
        ("sr", "### SR (strict surface only)"),
        ("bm", "### BM (framework humanize excluding tier0/tier1)"),
    ]
    for key, hdr in blocks:
        m = re.search(re.escape(hdr) + r"\n([A-Z]+)\n", md_text)
        if not m:
            raise RuntimeError(f"Could not find sequence block in recompute MD: {hdr}")
        out[key] = m.group(1).strip()
    return out


def ecdf(series: pd.Series, value: float) -> float:
    s = series.dropna()
    if s.empty:
        return float("nan")
    return float((s <= value).mean())


def load_template_imgt_positions(framework_yaml: Path, germline: str) -> dict[int, str]:
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
    if not out:
        raise RuntimeError(f"Empty IMGT position map for germline: {germline}")
    return out


def imgt_identity_vs_template(seq: str, template_pos: dict[int, str]) -> tuple[int, int, float]:
    # Lazy import to keep this script lightweight if ANARCII isn't used elsewhere
    import sys

    sys.path.append(str(PROJECT_ROOT))
    from core.numbering.imgt_anarcii import imgt_number_anarcii_indexed

    numbered = imgt_number_anarcii_indexed(seq)
    q_pos = {int(r["pos"]): str(r["aa"]) for r in numbered["rows"]}
    common = sorted(set(q_pos).intersection(template_pos))
    if not common:
        return 0, 0, float("nan")
    ident = sum(1 for p in common if q_pos[p] == template_pos[p])
    return ident, len(common), float(ident) / float(len(common))


def main() -> None:
    # 1) 7D12 (freshly recomputed metrics table)
    if not DECISION_MD.exists():
        raise RuntimeError(f"Missing: {DECISION_MD}")
    if not EVAL_TABLE.exists():
        raise RuntimeError(f"Missing: {EVAL_TABLE} (run scripts/evaluate_7d12_4krl_variants.py)")

    decision_txt = DECISION_MD.read_text(encoding="utf-8")
    seqs = _extract_sequences_from_recompute_md(decision_txt)
    df_7d12 = pd.read_csv(EVAL_TABLE)

    # 2) Clinical SR cohort = Slice-3 clinical molecules (native variants only) filtered by strategy label
    for p in (SLICE3_IMM, SLICE3_DEV, SLICE3_META):
        if not p.exists():
            raise RuntimeError(f"Missing: {p}")

    df_meta = pd.read_csv(SLICE3_META).rename(
        columns={"Drug Name": "antibody_id", "Humanization Strategy": "strategy"}
    )
    df_imm = pd.read_csv(SLICE3_IMM)
    df_dev = pd.read_csv(SLICE3_DEV)

    df_imm_n = df_imm[df_imm["variant"] == "native"].merge(
        df_meta[["antibody_id", "strategy"]], on="antibody_id", how="left"
    )
    df_dev_n = df_dev[df_dev["variant"] == "native"].merge(
        df_meta[["antibody_id", "strategy"]], on="antibody_id", how="left"
    )

    df_imm_sr = df_imm_n[df_imm_n["strategy"].astype(str).str.startswith("SR")]
    df_dev_sr = df_dev_n[df_dev_n["strategy"].astype(str).str.startswith("SR")]

    # 3) Humanization degree vs template (IMGT-position identity)
    template_germline = "IGHV3-23*01"
    template_pos = load_template_imgt_positions(FRAMEWORK_YAML, template_germline)
    id_rows = []
    for v, seq in seqs.items():
        ident, npos, frac = imgt_identity_vs_template(seq, template_pos)
        id_rows.append(
            {
                "variant": v,
                "template": template_germline,
                "imgt_overlap_positions": npos,
                "imgt_identical_positions": ident,
                "imgt_identity": frac,
            }
        )
    df_id = pd.DataFrame(id_rows)

    # 4) Percentiles vs SR clinical cohort (native molecules)
    pct_rows = []
    for _, r in df_7d12.iterrows():
        pct_rows.append(
            {
                "variant": r["variant"],
                "B_total_1pct": int(r["B_total_1pct"]),
                "pct_in_SR_B_total_1pct": ecdf(df_imm_sr["B_total_1pct"], float(r["B_total_1pct"])),
                "dev_score": int(r["dev_score"]),
                "pct_in_SR_dev_score": ecdf(df_dev_sr["score"], float(r["dev_score"])),
            }
        )
    df_pct = pd.DataFrame(pct_rows)

    # 5) Write report
    with open(OUT_MD, "w", encoding="utf-8") as f:
        f.write("# 7D12 (4KRL) vs Clinical SR Cohort (Slice-3)\n\n")
        f.write("## Inputs\n")
        f.write(f"- 7D12 sequences: `{DECISION_MD}`\n")
        f.write(f"- 7D12 metrics: `{EVAL_TABLE}`\n")
        f.write(f"- Slice-3 immunogenicity: `{SLICE3_IMM}` (native rows only)\n")
        f.write(f"- Slice-3 developability: `{SLICE3_DEV}` (native rows only)\n")
        f.write(f"- Slice-3 clinical strategy meta: `{SLICE3_META}` (filter: strategy startswith 'SR')\n")
        f.write(f"- Template framework YAML: `{FRAMEWORK_YAML}` (template: {template_germline})\n\n")

        f.write("## 1) 7D12 sequences (current recompute)\n\n")
        for v in ("native", "sr", "bm"):
            f.write(f"- **{v}**: {seqs[v]}\n")
        f.write("\n")

        f.write("## 2) Humanization degree (IMGT identity vs template)\n\n")
        f.write(df_id.to_markdown(index=False) + "\n\n")
        f.write(
            "- `imgt_identity` is computed across IMGT positions that overlap between the query and template numbering.\n\n"
        )

        f.write("## 3) Clinical SR cohort sizes\n\n")
        f.write(f"- SR cohort (immuno, native): n={len(df_imm_sr)}\n")
        f.write(f"- SR cohort (dev, native): n={len(df_dev_sr)}\n\n")

        f.write("## 4) 7D12 vs SR cohort (percentiles)\n\n")
        f.write(df_pct.to_markdown(index=False) + "\n\n")
        f.write("- `pct_in_SR_B_total_1pct`: ECDF vs SR cohort (lower is better; smaller percentile means fewer binders than most SR drugs)\n")
        f.write("- `pct_in_SR_dev_score`: ECDF vs SR cohort (higher is better; larger percentile means better dev score than most SR drugs)\n")

    print(f"Wrote: {OUT_MD}")


if __name__ == "__main__":
    main()

