#!/usr/bin/env python3
"""
Analyze relationship between VHH framework regions and CDR lengths (39 clinical VHH).
Reference: paper/Submission_Package/FR3_CDR2_ANALYSIS_SUPPLEMENT.md, _.md,
           MANUSCRIPT_ADDITIONS_REQUIRED.md.
Output: data/vhh_clinical_39_union/fr_cdr_analysis_report.md, fr_cdr_metrics.csv
"""
import json
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent
UNION_DIR = PROJECT_ROOT / "data" / "vhh_clinical_39_union"
SEGMENTS_JSON = UNION_DIR / "vhh_39_cdr_fr_segments.json"
VALIDATED_JSON = UNION_DIR / "vhh_39_sequences_clinical_validated.json"
OUT_REPORT = UNION_DIR / "fr_cdr_analysis_report.md"
OUT_CSV = UNION_DIR / "fr_cdr_metrics.csv"


def spearman_r(x, y):
    """Spearman correlation and approximate p-value (n<50)."""
    n = len(x)
    if n < 3 or len(y) != n:
        return None, None
    try:
        from scipy import stats
        import warnings
        with warnings.catch_warnings():
            warnings.simplefilter("ignore", category=RuntimeWarning)
            r, p = stats.spearmanr(x, y)
        if r is None or (isinstance(r, float) and (r != r)):  # nan
            return None, None
        return round(float(r), 4), round(float(p), 4) if p is not None else None
    except ImportError:
        # Fallback: no scipy - compute rank correlation manually (simplified)
        def rank(v):
            order = sorted(range(n), key=lambda i: v[i])
            r = [0] * n
            for i, j in enumerate(order):
                r[j] = i + 1
            return r
        rx, ry = rank(x), rank(y)
        mx, my = sum(rx) / n, sum(ry) / n
        num = sum((rx[i] - mx) * (ry[i] - my) for i in range(n))
        den_x = (sum((rx[i] - mx) ** 2 for i in range(n)) ** 0.5) or 1
        den_y = (sum((ry[i] - my) ** 2 for i in range(n)) ** 0.5) or 1
        r = num / (den_x * den_y)
        return round(r, 4), None


def main():
    with open(SEGMENTS_JSON, encoding="utf-8") as f:
        seg_data = json.load(f)
    with open(VALIDATED_JSON, encoding="utf-8") as f:
        val_data = json.load(f)
    segments = {s["Name"]: s for s in seg_data["segments"]}
    validated = {v["Name"]: v for v in val_data["vhh"]}

    rows = []
    for name, seg in segments.items():
        if seg.get("has_segment") != "Y":
            continue
        clin = validated.get(name, {})
        fr1_len = len(seg.get("FR1", ""))
        fr2_len = len(seg.get("FR2", ""))
        fr3_len = len(seg.get("FR3", ""))
        fr4_len = len(seg.get("FR4", ""))
        cdr1_len = seg.get("CDR1_len") or 0
        cdr2_len = seg.get("CDR2_len") or 0
        cdr3_len = seg.get("CDR3_len") or 0
        total_fr = fr1_len + fr2_len + fr3_len + fr4_len
        total_cdr = cdr1_len + cdr2_len + cdr3_len
        cdr2_fold = (clin.get("CDR2_Fold") or "").strip() or f"H2-{cdr2_len}-1"  # infer if missing
        rows.append({
            "Name": name,
            "FR1_len": fr1_len, "FR2_len": fr2_len, "FR3_len": fr3_len, "FR4_len": fr4_len,
            "total_FR_len": total_fr,
            "CDR1_len": cdr1_len, "CDR2_len": cdr2_len, "CDR3_len": cdr3_len,
            "total_CDR_len": total_cdr,
            "CDR2_fold": cdr2_fold,
            "In_Paper_Table1": clin.get("In_Paper_Table1", ""),
        })

    n = len(rows)
    if n == 0:
        print("No segments found.")
        return 1

    # Metrics for correlation
    fr1 = [r["FR1_len"] for r in rows]
    fr2 = [r["FR2_len"] for r in rows]
    fr3 = [r["FR3_len"] for r in rows]
    fr4 = [r["FR4_len"] for r in rows]
    total_fr = [r["total_FR_len"] for r in rows]
    c1 = [r["CDR1_len"] for r in rows]
    c2 = [r["CDR2_len"] for r in rows]
    c3 = [r["CDR3_len"] for r in rows]

    # Correlations
    corr_fr3_cdr2 = spearman_r(fr3, c2)
    corr_fr3_cdr3 = spearman_r(fr3, c3)
    corr_fr4_cdr3 = spearman_r(fr4, c3)
    corr_cdr2_cdr3 = spearman_r(c2, c3)
    corr_total_fr_cdr3 = spearman_r(total_fr, c3)
    corr_fr1_cdr1 = spearman_r(fr1, c1)

    # CDR2 length groups (mirror H2-9-1 vs H2-10-1)
    cdr2_8 = [r for r in rows if r["CDR2_len"] == 8]
    cdr2_9 = [r for r in rows if r["CDR2_len"] == 9]
    cdr2_10 = [r for r in rows if r["CDR2_len"] == 10]
    cdr3_short = [r for r in rows if r["CDR3_len"] <= 11]
    cdr3_long = [r for r in rows if r["CDR3_len"] > 11]

    # Summary stats
    def avg_len(lst, key):
        if not lst:
            return None
        return round(sum(r[key] for r in lst) / len(lst), 2)

    report_lines = [
        "# VHH  CDR （39  VHH）",
        "",
        "## 1. ",
        "",
        "- ****：39  VHH，IMGT （vhh_39_cdr_fr_segments.json + validated ）。",
        "- ****：",
        "  - `paper/Submission_Package/FR3_CDR2_ANALYSIS_SUPPLEMENT.md`：FR3 N  **CDR2 ** （ CDR2→Tyr， CDR2→Thr），CDR2-FR3 junction 。",
        "  - `paper/Submission_Package/MANUSCRIPT_ADDITIONS_REQUIRED.md`：FR4 N （IMGT 118） **CDR3 ** （ CDR3→Trp 100%）。",
        "  - `paper/raw data/_.md`：FR  BM/SR/Native；H2 。",
        "",
        "## 2. ",
        "",
        "|  |  |  |  |",
        "|------|------|--------|--------|"
    ]
    for key, label in [
        ("FR1_len", "FR1"), ("FR2_len", "FR2"), ("FR3_len", "FR3"), ("FR4_len", "FR4"),
        ("total_FR_len", " FR"), ("CDR1_len", "CDR1"), ("CDR2_len", "CDR2"), ("CDR3_len", "CDR3"), ("total_CDR_len", " CDR")
    ]:
        vals = [r[key] for r in rows if r[key] != "" and r[key] is not None]
        if vals:
            report_lines.append(f"| {label} | {round(sum(vals)/len(vals), 2)} | {min(vals)} | {max(vals)} |")

    report_lines.extend([
        "",
        "## 3.  CDR （Spearman）",
        "",
        "|  | ρ | P |",
        "|--------|---|---|"
    ])
    for (a, b), label in [
        ((fr3, c3), "FR3_len vs CDR3_len"),
        ((fr3, c2), "FR3_len vs CDR2_len"),
        ((fr4, c3), "FR4_len vs CDR3_len"),
        ((c2, c3), "CDR2_len vs CDR3_len"),
        ((total_fr, c3), "total_FR_len vs CDR3_len"),
        ((fr1, c1), "FR1_len vs CDR1_len"),
    ]:
        r, p = spearman_r(a, b)
        if r is not None:
            report_lines.append(f"| {label} | {r} | {p if p is not None else '—'} |")

    report_lines.extend([
        "",
        "## 4.  CDR2 （ H2-9-1 / H2-10-1）",
        "",
        "| CDR2  | N |  CDR3  |  FR3  |",
        "|------------|---|----------------|----------------|"
    ])
    for group, label in [(cdr2_8, "8"), (cdr2_9, "9"), (cdr2_10, "10")]:
        if group:
            report_lines.append(f"| {label} | {len(group)} | {avg_len(group, 'CDR3_len') or '—'} | {avg_len(group, 'FR3_len') or '—'} |")
    report_lines.extend([
        "",
        "| CDR3  | N |  FR4  |  FR3  |",
        "|------------|---|----------------|----------------|"
    ])
    for group, label in [(cdr3_short, "≤11 aa"), (cdr3_long, ">11 aa")]:
        if group:
            report_lines.append(f"| {label} | {len(group)} | {avg_len(group, 'FR4_len') or '—'} | {avg_len(group, 'FR3_len') or '—'} |")

    report_lines.extend([
        "",
        "## 5.  19 ",
        "",
        "- **FR3–CDR2**： FR3 N ****（Tyr/Thr） CDR2 canonical class （P=0.013）。 FR3**** CDR2 ，**** FR3 。",
        "- **FR4–CDR3**： FR4 N （IMGT 118） CDR3 （Trp ）。 FR4  CDR3 。",
        "- **CDR2–CDR3**： CDR2_len  CDR3_len ，「 CDR2 +  CDR3 」。",
        "",
        "## 6. ",
        "",
        "|  |  |  |",
        "|------|------|------|",
        "| **** |  | n=39，；/。 |",
        "| **** |  | FR1–4 、CDR1–3 、CDR2_fold（）， 8–10 。 |",
        "| **** |  | (1)  FR/CDR  CDR2_fold；(2)  CDR2/CDR3  FR ；(3) /。 |",
        "| **** |  | （CDR2→FR3 ，CDR3→FR4 ）****，。 |",
        "| **** |  +  ML |  junction （FR3-1  CDR2 ，IMGT 118  CDR3 ）； ML，/ + ， Spearman 。 |",
        "",
        "---",
        "：`scripts/analyze_vhh39_fr_cdr_relationship.py`",
        ""
    ])

    report_text = "\n".join(report_lines)
    OUT_REPORT.parent.mkdir(parents=True, exist_ok=True)
    with open(OUT_REPORT, "w", encoding="utf-8") as f:
        f.write(report_text)
    print(f"Wrote {OUT_REPORT}")

    # CSV
    import csv
    fieldnames = ["Name", "FR1_len", "FR2_len", "FR3_len", "FR4_len", "total_FR_len",
                  "CDR1_len", "CDR2_len", "CDR3_len", "total_CDR_len", "CDR2_fold", "In_Paper_Table1"]
    with open(OUT_CSV, "w", encoding="utf-8", newline="") as f:
        w = csv.DictWriter(f, fieldnames=fieldnames)
        w.writeheader()
        w.writerows(rows)
    print(f"Wrote {OUT_CSV}")

    # Print summary
    r_c2_c3, p_c2_c3 = spearman_r(c2, c3)
    r_fr4_c3, p_fr4_c3 = spearman_r(fr4, c3)
    print(f"39 VHH: FR–CDR analysis done. CDR2 vs CDR3 len: ρ={r_c2_c3}, p={p_c2_c3}; FR4 vs CDR3: ρ={r_fr4_c3}, p={p_fr4_c3}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
