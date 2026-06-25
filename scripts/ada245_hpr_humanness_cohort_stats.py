#!/usr/bin/env python3
"""
Batch-compute HPR Index + Humanness (AbLang2 PLL) for ADA245 subsets and print
correlations / simple ADA-risk associations.

Reads: data/ada245/database/ada_master_245_curated.csv
Uses: core.humanization.hpr_index.compute_hpr_index + ablang2-paired (model loaded once).

Requires runtime deps for full metrics: promb (HPR), ablang2 (Humanness).

**Reuse:** If a row exists in a cache TSV with both `hpr_combined` and `humanness_pll`,
that antibody is skipped (no HPR/AbLang recomputation). By default, existing files under
`projects/ada245_hpr_humanness*.tsv` are merged as cache sources when present.
"""
from __future__ import annotations

import argparse
import math
import sys
from pathlib import Path
from typing import Any, Dict, List, Optional

import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))


def _seq_ok(row: pd.Series, min_vh: int = 90, min_vl: int = 85) -> bool:
    vh = str(row.get("vh_seq") or "").strip()
    vl = str(row.get("vl_seq") or "").strip()
    return len(vh) >= min_vh and len(vl) >= min_vl


def _hpr_combined(hpr: Any) -> Optional[float]:
    if not isinstance(hpr, dict):
        return None
    comb = (hpr.get("combined") or {}) if hpr else {}
    s = comb.get("score")
    try:
        return float(s) if s is not None else None
    except (TypeError, ValueError):
        return None


def _pearson(x: List[float], y: List[float]) -> Optional[float]:
    n = len(x)
    if n < 3 or n != len(y):
        return None
    mx = sum(x) / n
    my = sum(y) / n
    num = sum((xi - mx) * (yi - my) for xi, yi in zip(x, y))
    denx = math.sqrt(sum((xi - mx) ** 2 for xi in x))
    deny = math.sqrt(sum((yi - my) ** 2 for yi in y))
    if denx == 0 or deny == 0:
        return None
    return num / (denx * deny)


def _spearman(x: List[float], y: List[float]) -> Optional[float]:
    """Spearman via rank correlation (ties broken by average rank)."""
    n = len(x)
    if n < 3 or n != len(y):
        return None

    def ranks(vals: List[float]) -> List[float]:
        sorted_idx = sorted(range(n), key=lambda i: vals[i])
        r = [0.0] * n
        i = 0
        while i < n:
            j = i
            while j + 1 < n and vals[sorted_idx[j + 1]] == vals[sorted_idx[i]]:
                j += 1
            avg = (i + j) / 2.0 + 1.0  # 1-based mid rank
            for k in range(i, j + 1):
                r[sorted_idx[k]] = avg
            i = j + 1
        return r

    rx = ranks(x)
    ry = ranks(y)
    return _pearson(rx, ry)


def _logistic_or_high_ada(
    hpr: List[float],
    hum: List[float],
    ada_pct: List[float],
    threshold: float = 10.0,
) -> Dict[str, Any]:
    """Univariate logistic regression OR per SD for high ADA (ada >= threshold)."""
    try:
        import numpy as np
        from sklearn.linear_model import LogisticRegression
    except Exception as e:  # noqa: BLE001
        return {"error": str(e)}

    y = np.array([1 if a >= threshold else 0 for a in ada_pct], dtype=float)
    if y.sum() == 0 or y.sum() == len(y):
        return {"note": "constant_outcome", "n_high": int(y.sum()), "n": len(y)}

    out: Dict[str, Any] = {}
    for name, xraw in [("hpr", hpr), ("humanness_pll", hum)]:
        x = np.array(xraw, dtype=float)
        sx = float(x.std(ddof=1)) if len(x) > 2 else 0.0
        if sx == 0:
            out[name] = {"or_per_sd": None, "note": "zero_variance"}
            continue
        X = ((x - x.mean()) / sx).reshape(-1, 1)
        clf = LogisticRegression(solver="lbfgs", max_iter=200)
        clf.fit(X, y)
        coef = float(clf.coef_.ravel()[0])
        or_per_sd = math.exp(coef)
        out[name] = {"or_per_sd": round(or_per_sd, 4), "log_or_per_sd": round(coef, 4)}
    return out


def _load_ablang_paired_model():  # noqa: ANN201
    import ablang2  # type: ignore

    return ablang2.pretrained("ablang2-paired")


def _pll_paired(model: Any, vh: str, vl: str) -> Optional[float]:
    import numpy as np  # type: ignore

    pll = model([(vh, vl)], mode="pseudo_log_likelihood")
    return round(float(np.squeeze(pll)), 3)


def _parse_float_cell(val: Any) -> Optional[float]:
    if val is None or (isinstance(val, float) and pd.isna(val)):
        return None
    try:
        return float(val)
    except (TypeError, ValueError):
        return None


def _load_hpr_humanness_cache(paths: List[Path]) -> Dict[str, Dict[str, Any]]:
    """
    Merge TSV/CSV files keyed by antibody_name. Later paths override earlier.
    Expected columns: antibody_name, hpr_combined, humanness_pll
    (optional: hpr_error, ablang_error)
    """
    merged: Dict[str, Dict[str, Any]] = {}
    for p in paths:
        if not p.is_file():
            continue
        sep = "\t" if p.suffix.lower() in {".tsv", ".tab"} else ","
        try:
            cdf = pd.read_csv(p, sep=sep)
        except Exception:  # noqa: BLE001
            continue
        if "antibody_name" not in cdf.columns:
            continue
        for _, r in cdf.iterrows():
            name = str(r.get("antibody_name") or "").strip()
            if not name:
                continue
            hpr_c = _parse_float_cell(r.get("hpr_combined"))
            pll = _parse_float_cell(r.get("humanness_pll"))
            merged[name] = {
                "hpr_combined": hpr_c,
                "humanness_pll": pll,
                "hpr_error": r.get("hpr_error") if pd.notna(r.get("hpr_error")) else None,
                "ablang_error": r.get("ablang_error") if pd.notna(r.get("ablang_error")) else None,
            }
    return merged


def _row_has_both_metrics(row: Dict[str, Any]) -> bool:
    return (
        _parse_float_cell(row.get("hpr_combined")) is not None
        and _parse_float_cell(row.get("humanness_pll")) is not None
    )


def _load_cohort_resume_map(out_path: Path) -> Dict[str, Dict[str, Any]]:
    """Rows from a previous run of this cohort TSV (both metrics present)."""
    if not out_path.is_file():
        return {}
    try:
        pdf = pd.read_csv(out_path, sep="\t")
    except Exception:  # noqa: BLE001
        return {}
    if "antibody_name" not in pdf.columns:
        return {}
    out: Dict[str, Dict[str, Any]] = {}
    for _, r in pdf.iterrows():
        d = {k: (None if (isinstance(v, float) and pd.isna(v)) else v) for k, v in r.items()}
        name = str(d.get("antibody_name") or "").strip()
        if name and _row_has_both_metrics(d):
            out[name] = d
    return out


def _default_cache_paths(explicit: List[Path]) -> List[Path]:
    """Prefer user paths, then known project exports if files exist."""
    defaults = [
        ROOT / "projects" / "ada245_hpr_humanness_cache.tsv",
        ROOT / "projects" / "ada245_hpr_humanness_gene_engineered_humanized_seqbacked.tsv",
        ROOT / "projects" / "ada245_hpr_humanness_transgenic_mice_fully_human_seqbacked.tsv",
    ]
    seen: set = set()
    out: List[Path] = []
    for p in explicit + defaults:
        rp = p.resolve()
        if rp in seen:
            continue
        seen.add(rp)
        if p.is_file():
            out.append(p)
    return out


def run(
    csv_path: Path,
    ada_high_thr: float,
    *,
    cache_paths: List[Path],
    no_cache: bool,
) -> None:
    from core.humanization.hpr_index import compute_hpr_index

    cache_sources = [] if no_cache else _default_cache_paths(cache_paths)
    cache = _load_hpr_humanness_cache(cache_sources)
    if cache_sources:
        print(
            f"HPR/Humanness cache: {len(cache)} antibody names from {len(cache_sources)} file(s).",
            flush=True,
        )
    elif not no_cache:
        print("No cache TSV found under projects/ (run once to generate).", flush=True)

    df = pd.read_csv(csv_path)
    df["_seq_ok"] = df.apply(_seq_ok, axis=1)

    cls = df["thera_genetics_class"].fillna("").astype(str).str.strip().str.lower()
    plat = df["discovery_platform"].fillna("").astype(str).str.strip()

    mask_eng = cls.isin(["humanized", "humanised", "humanised_engineered"]) & df["_seq_ok"]
    mask_tm_fh = (plat == "Transgenic Mice") & (cls == "fully_human") & df["_seq_ok"]

    # Smaller cohort first so a partial run still yields one complete TSV sooner.
    cohorts: Dict[str, pd.DataFrame] = {
        "transgenic_mice_fully_human_seqbacked": df.loc[mask_tm_fh].copy(),
        "gene_engineered_humanized_seqbacked": df.loc[mask_eng].copy(),
    }

    ablang_model: Any = None

    def _get_ablang() -> Any:
        nonlocal ablang_model
        if ablang_model is None:
            print("Loading AbLang2 paired model once (may take ~30–120 s)...", flush=True)
            ablang_model = _load_ablang_paired_model()
        return ablang_model

    for cohort_name, sub in cohorts.items():
        out_path = ROOT / "projects" / f"ada245_hpr_humanness_{cohort_name}.tsv"
        out_path.parent.mkdir(parents=True, exist_ok=True)
        resume_map = {} if no_cache else _load_cohort_resume_map(out_path)
        if resume_map:
            print(f"Resume: {len(resume_map)} complete row(s) from {out_path.name}", flush=True)

        rows_out: List[Dict[str, Any]] = []
        n_cache = 0
        n_resume = 0
        for _, row in sub.iterrows():
            ab_name = str(row.get("antibody_name") or "").strip()
            vh = str(row.get("vh_seq") or "").strip().upper()
            vl = str(row.get("vl_seq") or "").strip().upper()
            hpr_err = None
            ab_err = None
            hpr_c: Optional[float] = None
            pll_f: Optional[float] = None
            source = "computed"

            hit = cache.get(ab_name) if cache else None
            if hit is not None:
                hc = hit.get("hpr_combined")
                pl = hit.get("humanness_pll")
                if hc is not None and pl is not None:
                    hpr_c = float(hc)
                    pll_f = float(pl)
                    hpr_err = hit.get("hpr_error")
                    ab_err = hit.get("ablang_error")
                    source = "cache"
                    n_cache += 1

            if source == "computed" and ab_name in resume_map:
                rec = resume_map[ab_name]
                hpr_c = _parse_float_cell(rec.get("hpr_combined"))
                pll_f = _parse_float_cell(rec.get("humanness_pll"))
                hpr_err = rec.get("hpr_error")
                ab_err = rec.get("ablang_error")
                source = "resume_tsv"
                n_resume += 1

            if source == "computed":
                try:
                    hpr_idx = compute_hpr_index(vh, vl)
                    hpr_c = _hpr_combined(hpr_idx)
                except Exception as exc:  # noqa: BLE001
                    hpr_err = f"{type(exc).__name__}: {exc}"
                if vh and vl:
                    try:
                        pll_f = _pll_paired(_get_ablang(), vh, vl)
                    except Exception as exc:  # noqa: BLE001
                        ab_err = f"{type(exc).__name__}: {exc}"
                else:
                    ab_err = "missing_vh_or_vl"
            ada = row.get("ada_first_pct")
            try:
                ada_f = float(ada) if ada == ada and ada is not None else None
            except (TypeError, ValueError):
                ada_f = None
            rows_out.append(
                {
                    "antibody_name": row.get("antibody_name"),
                    "hpr_combined": hpr_c,
                    "humanness_pll": pll_f,
                    "ada_first_pct": ada_f,
                    "metric_source": source,
                    "hpr_error": hpr_err,
                    "ablang_error": ab_err,
                }
            )
            pd.DataFrame(rows_out).to_csv(out_path, sep="\t", index=False)

        ok = [
            r
            for r in rows_out
            if r["hpr_combined"] is not None
            and r["humanness_pll"] is not None
            and r["ada_first_pct"] is not None
        ]
        hprs = [float(r["hpr_combined"]) for r in ok]
        hums = [float(r["humanness_pll"]) for r in ok]
        adas = [float(r["ada_first_pct"]) for r in ok]

        print(f"\n=== {cohort_name} ===")
        print(f"rows_selected: {len(sub)}")
        print(f"rows_from_global_cache: {n_cache}  rows_resumed_from_tsv: {n_resume}")
        print(f"rows_with_hpr_humanness_ada: {len(ok)}")
        n_hpr_fail = sum(1 for r in rows_out if r["hpr_combined"] is None)
        n_ab_fail = sum(1 for r in rows_out if r["humanness_pll"] is None)
        print(f"missing_hpr: {n_hpr_fail}  missing_humanness: {n_ab_fail}")

        if len(hprs) >= 3:
            print(f"HPR mean±sd: {sum(hprs)/len(hprs):.4f} ± {pd.Series(hprs).std(ddof=1):.4f}")
            print(f"Humanness PLL mean±sd: {sum(hums)/len(hums):.4f} ± {pd.Series(hums).std(ddof=1):.4f}")
            print(f"ADA first % mean±sd: {sum(adas)/len(adas):.4f} ± {pd.Series(adas).std(ddof=1):.4f}")
            print(f"Pearson(HPR, Humanness): {_pearson(hprs, hums)}")
            print(f"Spearman(HPR, Humanness): {_spearman(hprs, hums)}")
            print(f"Pearson(HPR, ADA%): {_pearson(hprs, adas)}")
            print(f"Pearson(Humanness, ADA%): {_pearson(hums, adas)}")
            or_info = _logistic_or_high_ada(hprs, hums, adas, threshold=ada_high_thr)
            print(f"Logistic high-ADA (>={ada_high_thr}%): {or_info}")
        else:
            print("Not enough complete rows for correlation (need >=3 with all three numeric fields).")

        print(f"Final TSV: {out_path}")


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument(
        "--csv",
        type=Path,
        default=ROOT / "data" / "ada245" / "database" / "ada_master_245_curated.csv",
    )
    ap.add_argument("--ada-high-thr", type=float, default=10.0)
    ap.add_argument(
        "--cache-tsv",
        type=Path,
        action="append",
        default=[],
        help="Additional cache table(s); merged with default projects/ada245_hpr_humanness*.tsv when present.",
    )
    ap.add_argument(
        "--no-cache",
        action="store_true",
        help="Ignore all cache files; always recompute HPR and AbLang2.",
    )
    args = ap.parse_args()
    run(args.csv, args.ada_high_thr, cache_paths=list(args.cache_tsv), no_cache=args.no_cache)


if __name__ == "__main__":
    main()
