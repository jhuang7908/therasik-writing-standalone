import json
import time
import hashlib
import requests
import re
from pathlib import Path

import pandas as pd
import yaml


PROJECT_ROOT = Path(__file__).resolve().parent.parent

OUT_DIR = PROJECT_ROOT / "output" / "7D12"
OUT_DIR.mkdir(parents=True, exist_ok=True)

REPORT_MD = OUT_DIR / "7d12_4krl_eval_summary.md"
AUDIT_MD = OUT_DIR / "7d12_4krl_eval_audit.md"
OUT_TABLE = OUT_DIR / "7d12_4krl_eval_table.csv"

CACHE_DIR = OUT_DIR / "iedb_cache"
CACHE_DIR.mkdir(parents=True, exist_ok=True)

IEDB_API_URL = "https://tools-cluster-interface.iedb.org/tools_api/mhcii/"
DEFAULT_ALLELES = (
    "HLA-DRB1*01:01,HLA-DRB1*03:01,HLA-DRB1*04:01,HLA-DRB1*04:05,"
    "HLA-DRB1*07:01,HLA-DRB1*08:02,HLA-DRB1*09:01,HLA-DRB1*11:01,"
    "HLA-DRB1*12:01,HLA-DRB1*13:02,HLA-DRB1*15:01"
)

HYDROPHOBIC = set("AVILMFWY")
AROMATIC = set("FWY")


def read_variants_from_md(md_path: Path) -> dict[str, str]:
    txt = md_path.read_text(encoding="utf-8")

    def grab(header_regex: str) -> str:
        m = re.search(rf"### {header_regex}\n([A-Z]+)\n", txt)
        if not m:
            raise RuntimeError(f"Could not find sequence block for: {header_regex}")
        return m.group(1).strip()

    return {
        "native": grab("Native"),
        "sr": grab(r"SR \(strict surface only\)"),
        "bm": grab(r"BM \(framework humanize excluding tier0/tier1\)"),
    }


def cached_iedb_predict(
    sequence: str,
    alleles: str,
    method: str = "recommended",
    length: int = 15,
) -> tuple[pd.DataFrame, bool]:
    key = hashlib.sha256(f"{sequence}|{alleles}|{method}|{length}".encode("utf-8")).hexdigest()[:24]
    path = CACHE_DIR / f"{key}.tsv"
    if path.exists():
        return pd.read_csv(path, sep="\t"), True

    payload = {"method": method, "sequence_text": sequence, "allele": alleles, "length": length}
    for attempt in range(3):
        try:
            r = requests.post(IEDB_API_URL, data=payload, timeout=90)
            if r.status_code == 200:
                import io
                df = pd.read_csv(io.StringIO(r.text), sep="\t")
                df.to_csv(path, sep="\t", index=False)
                time.sleep(1.5)
                return df, False
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

    hp7, hp7_cnt = slide(seq, 7, hydro_frac)
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
        "net_charge_norm": float(net_charge) / L,
        "hydrophobic_frac_global": float(hydro),
        "aromatic_frac_global": float(arom),
        "hydro_patch_max7": float(hp7),
        "hydro_patch_count7": int(hp7_cnt),
        "hydro_patch_max9": float(hp9),
        "hydro_patch_count9": int(hp9_cnt),
        "charge_patch_max7": float(cp7),
        "charge_patch_count7": int(cp7_cnt),
        "total_len": int(L),
    }


def ecdf(series: pd.Series, value: float) -> float:
    if series.empty:
        return float("nan")
    return float((series <= value).mean())


def main() -> None:
    md_path = OUT_DIR / "7d12_4krl_decision_tree_recompute.md"
    variants = read_variants_from_md(md_path)

    audit = {
        "timestamp_start": time.strftime("%Y-%m-%d %H:%M:%S"),
        "endpoint": IEDB_API_URL,
        "method": "recommended",
        "alleles": DEFAULT_ALLELES,
        "peptide_len": 15,
        "rank_very_strong": 1.0,
        "rank_strong": 2.0,
        "requests": 0,
        "cache_hits": 0,
    }

    rows = []
    for vname, seq in variants.items():
        df_raw, cached = cached_iedb_predict(seq, DEFAULT_ALLELES, method="recommended", length=15)
        audit["requests"] += 1
        audit["cache_hits"] += int(cached)
        df_norm, rank_col = normalize_rank_col(df_raw)
        immuno = compute_immuno_features(df_norm, rank_col, rank1=1.0, rank2=2.0)
        dev = compute_developability(seq)
        rows.append({"variant": vname, "sequence": seq, **immuno, **dev})

    df = pd.DataFrame(rows)

    # Compare to Slice-3 clinical cohort (native rows)
    slice_immuno = pd.read_csv(PROJECT_ROOT / "reports" / "slice3_vhh_immunogenicity_features.csv")
    slice_dev = pd.read_csv(PROJECT_ROOT / "reports" / "slice3_vhh_developability_features_native_sr_bm.csv")
    slice_immuno_native = slice_immuno[slice_immuno["variant"] == "native"]
    slice_dev_native = slice_dev[slice_dev["variant"] == "native"]

    df["pct_B_total_1pct_vs_slice3_native"] = [
        ecdf(slice_immuno_native["B_total_1pct"], v) for v in df["B_total_1pct"]
    ]
    df["pct_dev_score_vs_slice3_native"] = [
        ecdf(slice_dev_native["score"], v) for v in df["dev_score"]
    ]

    df.to_csv(OUT_TABLE, index=False)

    # Decision: minimize immunogenicity first; tie-break by dev_score
    best = (
        df.sort_values(["B_total_1pct", "B_breadth_1pct", "dev_score"], ascending=[True, True, False])
        .iloc[0]["variant"]
    )

    audit["timestamp_end"] = time.strftime("%Y-%m-%d %H:%M:%S")
    with open(AUDIT_MD, "w", encoding="utf-8") as f:
        f.write("# 7D12 (4KRL) Variant Evaluation Audit\n\n")
        for k, v in audit.items():
            f.write(f"- **{k}**: {v}\n")
        f.write("\n### Disclaimer\n")
        f.write("In silico binding prediction and sequence-based developability proxies; experimental validation required.\n")

    with open(REPORT_MD, "w", encoding="utf-8") as f:
        f.write("# 7D12 (4KRL) — Native vs SR vs BM (Immunogenicity + Developability)\n\n")
        f.write(f"- **Best (rule: lowest MHC-II burden, then highest dev_score)**: **{best}**\n\n")
        f.write("## Variant table\n\n")
        f.write(df.drop(columns=["sequence"]).to_markdown(index=False) + "\n\n")
        f.write("## Slice-3 clinical VHH comparison\n\n")
        f.write(f"- Slice-3 native n={len(slice_immuno_native)} (immuno) and n={len(slice_dev_native)} (dev)\n")
        f.write("- `pct_B_total_1pct_vs_slice3_native`: empirical CDF (lower is better)\n")
        f.write("- `pct_dev_score_vs_slice3_native`: empirical CDF (higher is better)\n")

    print(f"Wrote: {REPORT_MD}")
    print(f"Wrote: {AUDIT_MD}")
    print(f"Wrote: {OUT_TABLE}")
    print(f"Best variant: {best}")


if __name__ == "__main__":
    main()

