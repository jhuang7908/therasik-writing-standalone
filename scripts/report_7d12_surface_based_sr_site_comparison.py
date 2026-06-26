"""
Generate a structure-first comparison table:

1) 7D12 (PDB 4KRL chain B) per-residue surface metrics (SASA/relSASA/is_surface)
2) strict SR surface-plasticity whitelist (22 IMGT positions)
3) library-wide SR mutation frequencies (Slice-3 N=19; plus clinical SR subset n=7)
4) SR forbidden "blacklist" / restricted positions (Tier0/Tier1 + CDR1/2/3)

Outputs:
- output/7D12/7d12_strict22_surface_vs_library_freq.csv
- output/7D12/7d12_strict22_surface_vs_library_freq.md
"""

from __future__ import annotations

import json
from pathlib import Path

import pandas as pd
import yaml


PROJECT_ROOT = Path(__file__).resolve().parent.parent

STRICT_YAML = PROJECT_ROOT / "output" / "surface_plasticity_positions_v1_strict.yaml"
SSOT_YAML = PROJECT_ROOT / "core" / "data" / "position_sets" / "imgt_position_sets.yaml"
SURFACE_CSV = PROJECT_ROOT / "output" / "7D12" / "7d12_4krl_per_residue_surface_metrics.csv"
MUTATIONS_JSONL = PROJECT_ROOT / "output" / "slice3_vhh_variant_mutations.jsonl"
META_CSV = PROJECT_ROOT / "reports" / "slice3_vhh_comprehensive_functional_library.csv"

OUT_CSV = PROJECT_ROOT / "output" / "7D12" / "7d12_strict22_surface_vs_library_freq.csv"
OUT_MD = PROJECT_ROOT / "output" / "7D12" / "7d12_strict22_surface_vs_library_freq.md"

# 7D12 SR sites shown in structure figures / report
SR_7D12_IMGT = [12, 40, 42, 83, 96, 101]


def load_strict22() -> list[int]:
    obj = yaml.safe_load(STRICT_YAML.read_text(encoding="utf-8"))
    return sorted(int(x) for x in obj["surface_plasticity_positions_v1_strict"])


def load_blacklist_sets() -> dict[str, set[int]]:
    ssot = yaml.safe_load(SSOT_YAML.read_text(encoding="utf-8"))
    ps = ssot["imgt_position_sets"]
    anchors = set(int(x) for x in ps["imgt_anchor_positions"])
    vernier = set(int(x) for x in ps["vernier_anchor_positions"])
    hallmark = set(int(x) for x in ps["vhh_hallmark_positions"])

    # Aggregate ND-dependent v2-lite (may be empty; still compute generically)
    nd = ssot.get("north_dunbrack", {}).get("dependent_positions_v2_lite", {})
    nd_core: set[int] = set()
    nd_cand: set[int] = set()
    for grp in ("H1", "H2"):
        for _cls, rec in (nd.get(grp, {}) or {}).items():
            nd_core |= set(int(x) for x in (rec.get("core", []) or []))
            nd_cand |= set(int(x) for x in (rec.get("candidate", []) or []))

    tier0 = anchors | vernier | nd_core
    tier1 = hallmark | nd_cand

    # Paper convention CDR ranges
    cdr1 = set(range(27, 39))
    cdr2 = set(range(56, 66))
    cdr3 = set(range(105, 118))

    big_blacklist = tier0 | tier1 | cdr1 | cdr2 | cdr3
    return {
        "tier0": tier0,
        "tier1": tier1,
        "cdr1": cdr1,
        "cdr2": cdr2,
        "cdr3": cdr3,
        "big_blacklist": big_blacklist,
    }


def load_surface_metrics() -> pd.DataFrame:
    df = pd.read_csv(SURFACE_CSV)
    # keep chain B only, one row per IMGT position (first occurrence)
    df = df[df["chain"].astype(str) == "B"].copy()
    df["imgt_pos"] = df["imgt_pos"].astype(int)
    df = (
        df.sort_values(["imgt_pos", "seq_idx"])
        .drop_duplicates(subset=["imgt_pos"], keep="first")
        .rename(
            columns={
                "imgt_pos": "IMGT",
                "aa": "aa_4krl",
                "sasa": "sasa_A2",
                "rel_sasa": "relSASA",
                "is_surface": "is_surface_relSASA_ge_0p25",
            }
        )
    )
    return df[["IMGT", "aa_4krl", "sasa_A2", "relSASA", "is_surface_relSASA_ge_0p25"]]


def load_library_sr_frequencies(strict22: list[int]) -> pd.DataFrame:
    meta = pd.read_csv(META_CSV).rename(
        columns={"Drug Name": "antibody_id", "Humanization Strategy": "strategy"}
    )
    clinical_sr = set(
        meta.loc[meta["strategy"].astype(str).str.startswith("SR"), "antibody_id"].astype(str)
    )

    cnt_all = {p: 0 for p in strict22}
    cnt_sr7 = {p: 0 for p in strict22}
    for line in MUTATIONS_JSONL.read_text(encoding="utf-8").splitlines():
        r = json.loads(line)
        if r.get("variant") != "sr":
            continue
        p = int(r["imgt_pos"])
        if p not in cnt_all:
            continue
        cnt_all[p] += 1
        if str(r.get("antibody_id")) in clinical_sr:
            cnt_sr7[p] += 1

    return pd.DataFrame(
        [{"IMGT": p, "SR_mut_freq_all19": cnt_all[p], "SR_mut_freq_clinical_SR7": cnt_sr7[p]} for p in strict22]
    )


def main() -> None:
    OUT_CSV.parent.mkdir(parents=True, exist_ok=True)

    strict22 = load_strict22()
    black = load_blacklist_sets()
    surf = load_surface_metrics()
    freq = load_library_sr_frequencies(strict22)

    base = pd.DataFrame({"IMGT": strict22})
    df = base.merge(surf, on="IMGT", how="left").merge(freq, on="IMGT", how="left")

    df["is_7d12_SR_site"] = df["IMGT"].isin(SR_7D12_IMGT)
    df["in_tier0"] = df["IMGT"].isin(black["tier0"])
    df["in_tier1"] = df["IMGT"].isin(black["tier1"])
    df["in_any_CDR"] = df["IMGT"].isin(black["cdr1"] | black["cdr2"] | black["cdr3"])
    df["in_big_blacklist"] = df["IMGT"].isin(black["big_blacklist"])

    # A practical "structure-first SR candidate" flag:
    # must be in strict22 AND surface by relSASA >= 0.25 AND not in blacklist (should be true for strict22)
    df["structure_first_SR_candidate"] = (
        df["is_surface_relSASA_ge_0p25"].fillna(False) & (~df["in_big_blacklist"])
    )

    # Save CSV (for downstream plotting)
    df.to_csv(OUT_CSV, index=False)

    # Write markdown summary
    lines: list[str] = []
    lines.append("# 7D12：（relSASA）（SR）\n")
    lines.append("## 1) （）\n")
    lines.append("- ：4KRL（chain B）\n")
    lines.append("- ：Shrake–Rupley per-residue SASA， relSASA\n")
    lines.append("- ：`relSASA >= 0.25`（ `output/7D12/7d12_4krl_per_residue_surface_metrics.csv` ）\n")
    lines.append("## 2) strict（22）“ vs ”\n")
    lines.append(df.to_markdown(index=False))
    lines.append("\n## 3) 7D12 （）\n")

    sub = df[df["is_7d12_SR_site"]].copy()
    # rank within strict22
    sub["rank_all19"] = (
        df.sort_values(["SR_mut_freq_all19", "IMGT"], ascending=[False, True])
        .reset_index(drop=True)
        .reset_index()
        .set_index("IMGT")["index"]
        .reindex(sub["IMGT"])
        .values
        + 1
    )
    sub["rank_clinical_SR7"] = (
        df.sort_values(["SR_mut_freq_clinical_SR7", "IMGT"], ascending=[False, True])
        .reset_index(drop=True)
        .reset_index()
        .set_index("IMGT")["index"]
        .reindex(sub["IMGT"])
        .values
        + 1
    )
    lines.append(sub[["IMGT", "relSASA", "is_surface_relSASA_ge_0p25", "SR_mut_freq_all19", "rank_all19", "SR_mut_freq_clinical_SR7", "rank_clinical_SR7"]].to_markdown(index=False))
    lines.append("\n### \n")
    lines.append("- **40/42**：（19 16/19；SR 7/7、6/7），“”。\n")
    lines.append("- **12/101**：19（5/19、4/19），SR 0/7，“SR”。\n")
    lines.append("- ****： relSASA ；（relSASA），。\n")

    OUT_MD.write_text("\n".join(lines) + "\n", encoding="utf-8")

    print(f"Wrote: {OUT_CSV}")
    print(f"Wrote: {OUT_MD}")


if __name__ == "__main__":
    main()

