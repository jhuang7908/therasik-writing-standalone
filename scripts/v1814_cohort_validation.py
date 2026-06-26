"""
V1.8.13 In-Silico Validation Suite
====================================
Path D (Reverse-engineering / classification accuracy):
  - Apply V1.8.13 thresholds (pI/AbNatiV) to all 160 cohort sequences
  - Per-category PASS/WARN/FAIL classification rates
  - True positive rate on Clinical_VHH + EngVH (should be high)
  - True negative rate on Neg_Control_VH (should be high)

Path A (IGHV-family-specific threshold extraction):
  - Detect IGHV family from each sequence (pattern match)
  - Group cohort by family x category
  - Compute per-family statistics for AbNatiV Δ, pI, GRAVY
  - Propose family-specific thresholds for V1.8.14
"""
from __future__ import annotations
import csv
import json
import re
import statistics
from pathlib import Path
from collections import defaultdict

ROOT = Path(__file__).resolve().parent.parent
SEQ_FILE = ROOT / "data" / "vhh_master_seq_list.csv"
METRICS_FILE = ROOT / "data" / "vhh_master_benchmarks_v3.csv"
AUTO_VH_CSV = ROOT / "data" / "reference" / "AutonomousHumanVH_Cohort_v1.csv"

OUT_DIR = ROOT / "data" / "_v1814_design"
OUT_DIR.mkdir(parents=True, exist_ok=True)


# ─── V1.8.13 IGHV family detection (sequence pattern matching) ───────────────
def detect_ighv_family(seq: str) -> str:
    if not seq or len(seq) < 25:
        return "IGHV_unknown"
    head = seq[:25]
    # IGHV1: KKPGAS / RPGAS or KKPG motif at N-term
    if re.search(r'V[KR][KR]PG[AS]S', head):
        return "IGHV1"
    if re.search(r'ARPG[AS]S', head):
        return "IGHV1"
    # IGHV3: SGGG[L/V]VQ
    if re.search(r'SGGG[LV][VL]Q', head):
        return "IGHV3"
    if re.search(r'ESGGG[LV]', head):
        return "IGHV3"
    # IGHV4: QQPG
    if re.search(r'QQPG.[GA]L', head):
        return "IGHV4"
    if re.search(r'.QLQESG', head[:8]) and 'QPGE' in head:
        return "IGHV4"
    # IGHV2: QGE / QLVES
    if head.startswith(("QITLKES", "QVTLKES")):
        return "IGHV2"
    return "IGHV_unknown"


# ─── V1.8.13 verdict gates ────────────────────────────────────────────────────
def label_pi_v1813(pI):
    try: v = float(pI)
    except: return "UNKNOWN"
    if v <= 9.0: return "PASS"
    if v <= 9.5: return "WARN"
    return "FAIL"


def label_abnativ_v1813(d):
    try: v = float(d)
    except: return "UNKNOWN"
    if v >= 0:     return "EXCELLENT"
    if v >= -0.12: return "PASS"
    if v >= -0.20: return "WARN"
    return "FAIL"


def composite_v1813(pi_l, an_l):
    if pi_l == "FAIL" or an_l == "FAIL": return "FAIL"
    if pi_l == "WARN" or an_l == "WARN": return "WARN"
    if pi_l == "PASS" and an_l in ("PASS", "EXCELLENT"):
        return "PASS" if an_l == "PASS" else "EXCELLENT"
    return "UNKNOWN"


# ─── V1.8.14 verdict gates ────────────────────────────────────────────────────
def label_pi_v1814(pI):
    try: v = float(pI)
    except: return "UNKNOWN"
    if v <= 9.4: return "PASS"
    if v <= 9.6: return "WARN"
    return "FAIL"


def label_abnativ_v1814(d, ighv):
    """IGHV3 high-confidence; IGHV1/4/unknown low-confidence track."""
    try: v = float(d)
    except: return "UNKNOWN"
    if ighv == "IGHV3":
        if v >= 0:     return "EXCELLENT"
        if v >= -0.13: return "PASS"
        if v >= -0.20: return "WARN"
        return "FAIL"
    else:
        if v >= 0:     return "EXCELLENT_lowconf"
        if v >= -0.13: return "PASS_lowconf"
        if v >= -0.20: return "WARN_lowconf"
        if v >= -0.30: return "WARN_lowconf_strict"
        return "FAIL_lowconf_strict"


def composite_v1814(pi_l, an_l, pI, ighv):
    # Override: high AbNatiV + pI within PASS bound → PASS
    if "EXCELLENT" in an_l and pi_l == "PASS":
        return "EXCELLENT" if "lowconf" not in an_l else "PASS_lowconf"
    if "EXCELLENT" in an_l and pi_l == "WARN" and pI is not None and pI <= 9.4:
        return "PASS_override"  # AbNatiV dominant
    if "FAIL" in an_l or pi_l == "FAIL":
        return "FAIL"
    if "WARN" in an_l or pi_l == "WARN":
        return "WARN"
    if "PASS" in an_l and pi_l == "PASS":
        return "PASS"
    return "UNKNOWN"


# legacy alias for compatibility
label_pi = label_pi_v1813
label_abnativ = label_abnativ_v1813
composite_verdict = composite_v1813


# ─── Load all data ────────────────────────────────────────────────────────────
def load_cohort():
    """Merge seq + metrics by id."""
    seqs = {}
    with SEQ_FILE.open(encoding="utf-8") as f:
        r = csv.DictReader(f)
        for row in r:
            seqs[row["id"]] = {
                "id": row["id"],
                "sequence": row["sequence"],
                "category": row["category"],
                "source": row.get("source", ""),
            }

    with METRICS_FILE.open(encoding="utf-8") as f:
        r = csv.DictReader(f)
        for row in r:
            if row["id"] not in seqs:
                continue
            seqs[row["id"]].update({
                "pI": float(row["pI"]) if row.get("pI") else None,
                "GRAVY": float(row["GRAVY"]) if row.get("GRAVY") else None,
                "abnativ_delta": float(row["abnativ_delta"]) if row.get("abnativ_delta") else None,
                "abnativ_vh2": float(row["abnativ_vh2"]) if row.get("abnativ_vh2") else None,
                "abnativ_vhh2": float(row["abnativ_vhh2"]) if row.get("abnativ_vhh2") else None,
                "compactness_A": float(row["compactness_A"]) if row.get("compactness_A") else None,
            })
    return list(seqs.values())


# ─── Path D: Classification accuracy ──────────────────────────────────────────
def _bucket(): return defaultdict(int)

def path_d_classification(cohort, version="v1813"):
    """Apply V1.8.13 or V1.8.14 thresholds and measure per-category verdicts."""
    by_cat = defaultdict(_bucket)
    detail_rows = []
    for r in cohort:
        cat = r["category"]
        ighv = detect_ighv_family(r["sequence"])
        pI = r.get("pI")
        d = r.get("abnativ_delta")
        if version == "v1813":
            pi_l = label_pi_v1813(pI)
            an_l = label_abnativ_v1813(d)
            verdict = composite_v1813(pi_l, an_l)
        else:
            pi_l = label_pi_v1814(pI)
            an_l = label_abnativ_v1814(d, ighv)
            verdict = composite_v1814(pi_l, an_l, pI, ighv)
        # Normalize verdict to PASS_GROUP for rate calc
        pg = "PASS" if any(s in verdict for s in ["PASS", "EXCELLENT"]) else verdict
        by_cat[cat][pg] += 1
        by_cat[cat]["total"] += 1
        detail_rows.append({
            "id": r["id"], "category": cat, "ighv": ighv,
            "pI": pI, "abnativ_delta": d,
            "pI_label": pi_l, "abnativ_label": an_l,
            "composite_verdict": verdict,
        })
    return dict(by_cat), detail_rows


# ─── Path A: Family x Category statistics ────────────────────────────────────
def percentile(values, p):
    if not values:
        return None
    s = sorted(values)
    k = (len(s) - 1) * p / 100
    f = int(k)
    if f >= len(s) - 1:
        return s[-1]
    return s[f] + (s[f+1] - s[f]) * (k - f)


def path_a_family_thresholds(cohort):
    """Group by IGHV family x category, compute distributions."""
    # We focus on positive cohorts (Clinical_VHH + EngVH) and negative cohort
    # For each IGHV family, extract abnativ_delta + pI quartiles
    family_data = defaultdict(lambda: defaultdict(list))
    for r in cohort:
        cat = r["category"]
        ighv = detect_ighv_family(r["sequence"])
        ad = r.get("abnativ_delta")
        pi_ = r.get("pI")
        if ad is None or pi_ is None:
            continue
        family_data[ighv][cat].append({"id": r["id"], "abnativ_delta": ad, "pI": pi_})

    summary = {}
    for fam, cats in family_data.items():
        summary[fam] = {}
        for cat, vals in cats.items():
            deltas = [v["abnativ_delta"] for v in vals]
            pis = [v["pI"] for v in vals]
            summary[fam][cat] = {
                "n": len(vals),
                "abnativ_delta": {
                    "min": min(deltas), "p10": percentile(deltas, 10),
                    "p25": percentile(deltas, 25), "median": percentile(deltas, 50),
                    "p75": percentile(deltas, 75), "p90": percentile(deltas, 90),
                    "max": max(deltas), "mean": statistics.mean(deltas),
                },
                "pI": {
                    "min": min(pis), "p10": percentile(pis, 10),
                    "median": percentile(pis, 50), "p90": percentile(pis, 90),
                    "max": max(pis), "mean": statistics.mean(pis),
                },
            }
    return summary


# ─── Output ──────────────────────────────────────────────────────────────────
def main():
    cohort = load_cohort()
    print(f"Loaded {len(cohort)} sequences with metrics.")

    # IGHV breakdown by category
    fam_x_cat = defaultdict(lambda: defaultdict(int))
    for r in cohort:
        fam = detect_ighv_family(r["sequence"])
        fam_x_cat[r["category"]][fam] += 1

    print("\n[IGHV family × category]")
    print(f"  {'Category':<28} {'IGHV1':>6} {'IGHV3':>6} {'IGHV4':>6} {'Unknown':>8} {'Total':>6}")
    for cat in sorted(fam_x_cat.keys()):
        fc = fam_x_cat[cat]
        total = sum(fc.values())
        print(f"  {cat:<28} {fc.get('IGHV1',0):>6} {fc.get('IGHV3',0):>6} "
              f"{fc.get('IGHV4',0):>6} {fc.get('IGHV_unknown',0):>8} {total:>6}")

    for version in ("v1813", "v1814"):
        by_cat, detail_rows = path_d_classification(cohort, version=version)
        print(f"\n[Path D: V1.8.{version[-2:]} verdict classification per category]")
        print(f"  {'Category':<28} {'PASS':>6} {'WARN':>6} {'FAIL':>6} {'Total':>6} {'PASS_rate':>10}")
        for cat in sorted(by_cat.keys()):
            c = by_cat[cat]
            print(f"  {cat:<28} {c.get('PASS',0):>6} {c.get('WARN',0):>6} {c.get('FAIL',0):>6} "
                  f"{c['total']:>6} {c.get('PASS',0)/c['total']*100:>9.1f}%")
        (OUT_DIR / f"{version}_classification_detail.json").write_text(
            json.dumps(detail_rows, indent=2, ensure_ascii=False), encoding="utf-8")
        (OUT_DIR / f"{version}_classification_by_category.json").write_text(
            json.dumps({k: dict(v) for k,v in by_cat.items()}, indent=2, ensure_ascii=False), encoding="utf-8")

    # Path A: family x category statistics
    fam_summary = path_a_family_thresholds(cohort)
    print("\n[Path A: IGHV-family-specific AbNatiV Δ statistics (positive cohorts only)]")
    pos_cats = ["Clinical_VHH", "Engineered_Human_VH"]
    for fam in ["IGHV1", "IGHV3", "IGHV4", "IGHV_unknown"]:
        if fam not in fam_summary:
            continue
        for cat in pos_cats:
            if cat not in fam_summary[fam]:
                continue
            s = fam_summary[fam][cat]
            d = s["abnativ_delta"]
            print(f"  {fam:<8} {cat:<22} n={s['n']:>3}  "
                  f"AbΔ p10={d['p10']:+.4f}  median={d['median']:+.4f}  p90={d['p90']:+.4f}")

    print("\n[Path A: IGHV-family-specific AbNatiV Δ statistics (negative cohort)]")
    for fam in ["IGHV1", "IGHV3", "IGHV4", "IGHV_unknown"]:
        if fam in fam_summary and "Negative_Control_VH" in fam_summary[fam]:
            s = fam_summary[fam]["Negative_Control_VH"]
            d = s["abnativ_delta"]
            print(f"  {fam:<8} {'Negative_Control_VH':<22} n={s['n']:>3}  "
                  f"AbΔ p10={d['p10']:+.4f}  median={d['median']:+.4f}  max={d['max']:+.4f}")

    (OUT_DIR / "ighv_family_x_category_count.json").write_text(
        json.dumps({c: dict(d) for c, d in fam_x_cat.items()}, indent=2, ensure_ascii=False),
        encoding="utf-8")
    (OUT_DIR / "ighv_family_stats.json").write_text(
        json.dumps(fam_summary, indent=2, ensure_ascii=False), encoding="utf-8")

    print(f"\nDetailed outputs written to: {OUT_DIR}")


if __name__ == "__main__":
    main()
