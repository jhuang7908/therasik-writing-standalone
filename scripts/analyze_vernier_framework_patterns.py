#!/usr/bin/env python3
"""
Analyze Vernier zone and framework subtype () patterns from structure metrics.

Reads structure_metrics_summary.json (from structure_metrics_humanization.py --dir),
computes distributions by canonical class / framework subtype, and writes:
  - data/humanization_assay/vernier_framework_patterns.json  (distributions + counts)
  - data/humanization_assay/vernier_framework_patterns_report.md (humanization guidance)

Usage:
  python scripts/analyze_vernier_framework_patterns.py [--metrics path/to/structure_metrics_summary.json]
"""

from __future__ import annotations

import argparse
import json
from collections import defaultdict
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

import numpy as np

PROJECT_ROOT = Path(__file__).resolve().parent.parent
DEFAULT_METRICS = PROJECT_ROOT / "data/humanization_assay/structure_metrics_summary.json"
OUT_JSON = PROJECT_ROOT / "data/humanization_assay/vernier_framework_patterns.json"
OUT_MD = PROJECT_ROOT / "data/humanization_assay/vernier_framework_patterns_report.md"

# Key Vernier positions for summary stats
KEY_VERNIER = ["VH_71", "VH_94", "VL_71", "VL_49"]
KEY_CDR_DIST = ["Vernier_to_H2", "Vernier_to_H3", "Vernier_to_any_CDR"]


def load_metrics(path: Path) -> List[Dict[str, Any]]:
    with open(path, encoding="utf-8") as f:
        data = json.load(f)
    return data if isinstance(data, list) else [data]


def safe_float(x: Any) -> Optional[float]:
    if x is None:
        return None
    try:
        v = float(x)
        return v if np.isfinite(v) else None
    except (TypeError, ValueError):
        return None


def stats(values: List[float]) -> Dict[str, float]:
    if not values:
        return {}
    a = np.array(values)
    return {
        "n": len(a),
        "mean": float(np.nanmean(a)),
        "std": float(np.nanstd(a)) if len(a) > 1 else 0.0,
        "min": float(np.nanmin(a)),
        "p5": float(np.nanpercentile(a, 5)),
        "p50": float(np.nanpercentile(a, 50)),
        "p95": float(np.nanpercentile(a, 95)),
        "max": float(np.nanmax(a)),
    }


def framework_subtype(rec: Dict) -> str:
    """Composite key: H1_H2_L1 (main canonical classes for framework )."""
    c = rec.get("canonical") or {}
    h1 = c.get("H1", "?")
    h2 = c.get("H2", "?")
    l1 = c.get("L1", "?")
    return f"{h1}|{h2}|{l1}"


def run_analysis(metrics_path: Path) -> Tuple[Dict[str, Any], List[Dict]]:
    records = load_metrics(metrics_path)
    # Drop failed
    ok = [r for r in records if not (r.get("errors") and len(r.get("errors", [])) > 0)]
    if not ok:
        return {"error": "No valid records", "total": len(records), "valid": 0}, []

    out: Dict[str, Any] = {
        "source": str(metrics_path),
        "total_pdbs": len(records),
        "valid_pdbs": len(ok),
        "by_framework_subtype": {},
        "by_canonical": defaultdict(lambda: {"count": 0, "metrics": defaultdict(list)}),
        "overall": defaultdict(list),
        "distributions_overall": {},
        "distributions_by_subtype": {},
        "distributions_by_H2": {},
    }

    for rec in ok:
        subtype = framework_subtype(rec)
        out["by_framework_subtype"][subtype] = out["by_framework_subtype"].get(subtype, 0) + 1

        c = rec.get("canonical") or {}
        for k, v in c.items():
            out["by_canonical"][k]["count"] += 1

        v = safe_float(rec.get("vh_vl_angle_deg"))
        if v is not None:
            out["overall"]["vh_vl_angle_deg"].append(v)
            out["by_canonical"]["_angle"].setdefault("list", []).append(v)
        v = safe_float(rec.get("interface_mean_dist_A"))
        if v is not None:
            out["overall"]["interface_mean_dist_A"].append(v)
        v = safe_float(rec.get("interface_min_dist_A"))
        if v is not None:
            out["overall"]["interface_min_dist_A"].append(v)
        v = safe_float(rec.get("vernier_sasa_total"))
        if v is not None:
            out["overall"]["vernier_sasa_total"].append(v)

        vp = rec.get("vernier_packing") or {}
        for pos in KEY_VERNIER:
            v = safe_float(vp.get(pos))
            if v is not None:
                out["overall"][f"packing_{pos}"].append(v)

        vd = rec.get("vernier_cdr_distances") or {}
        for k in KEY_CDR_DIST:
            v = safe_float(vd.get(k))
            if v is not None:
                out["overall"][f"dist_{k}"].append(v)

    # Overall distributions
    for key, vals in out["overall"].items():
        if vals:
            out["distributions_overall"][key] = stats(vals)

    # By framework subtype (only for subtypes with n>=5)
    by_sub = defaultdict(lambda: defaultdict(list))
    for rec in ok:
        subtype = framework_subtype(rec)
        v = safe_float(rec.get("vh_vl_angle_deg"))
        if v is not None:
            by_sub[subtype]["vh_vl_angle_deg"].append(v)
        v = safe_float(rec.get("vernier_sasa_total"))
        if v is not None:
            by_sub[subtype]["vernier_sasa_total"].append(v)
        vp = rec.get("vernier_packing") or {}
        for pos in KEY_VERNIER:
            v = safe_float(vp.get(pos))
            if v is not None:
                by_sub[subtype][f"packing_{pos}"].append(v)
        vd = rec.get("vernier_cdr_distances") or {}
        v = safe_float(vd.get("Vernier_to_any_CDR"))
        if v is not None:
            by_sub[subtype]["dist_Vernier_to_any_CDR"].append(v)

    for subtype, sub_vals in by_sub.items():
        if out["by_framework_subtype"].get(subtype, 0) < 5:
            continue
        out["distributions_by_subtype"][subtype] = {
            k: stats(v) for k, v in sub_vals.items() if v
        }

    # By H2 canonical (key for Vernier VH_71)
    by_h2 = defaultdict(lambda: defaultdict(list))
    for rec in ok:
        h2 = (rec.get("canonical") or {}).get("H2", "?")
        vp = rec.get("vernier_packing") or {}
        v = safe_float(vp.get("VH_71"))
        if v is not None:
            by_h2[h2]["VH_71"].append(v)
        v = safe_float(vp.get("VH_94"))
        if v is not None:
            by_h2[h2]["VH_94"].append(v)
        v = safe_float(rec.get("vh_vl_angle_deg"))
        if v is not None:
            by_h2[h2]["vh_vl_angle_deg"].append(v)
    for h2, sub_vals in by_h2.items():
        out["distributions_by_H2"][h2] = {k: stats(v) for k, v in sub_vals.items() if v}

    # CDR Northern/Canonical （）
    out["canonical_northern_summary"] = {
        k: v.get("count", 0) for k, v in out["by_canonical"].items()
        if k in ("H1", "H2", "H3", "L1", "L2", "L3") and isinstance(v, dict)
    }

    # North  (phi/psi): Standard vs Outlier 
    north_counts: Dict[str, Dict[str, int]] = defaultdict(lambda: {"Standard": 0, "Outlier": 0, "N/A": 0})
    north_scores: Dict[str, List[float]] = defaultdict(list)
    for rec in ok:
        cn = rec.get("canonical_north") or {}
        cs = rec.get("canonical_north_score") or {}
        for cdr in ("H1", "H2", "H3", "L1", "L2", "L3"):
            label = cn.get(cdr, "N/A")
            if label in ("Standard", "Outlier", "N/A"):
                north_counts[cdr][label] += 1
            else:
                north_counts[cdr]["N/A"] += 1
            sc = safe_float(cs.get(cdr))
            if sc is not None:
                north_scores[cdr].append(sc)
    out["north_structure_counts"] = dict(north_counts)
    out["north_structure_scores"] = {k: stats(v) for k, v in north_scores.items() if v}

    # VH/VL （）
    out["vh_vl_angle_by_subtype"] = {}
    for subtype, sub_vals in by_sub.items():
        if "vh_vl_angle_deg" in sub_vals and sub_vals["vh_vl_angle_deg"]:
            out["vh_vl_angle_by_subtype"][subtype] = stats(sub_vals["vh_vl_angle_deg"])

    # ： H1|H2|L1  + /
    pairing_rules: List[Dict[str, Any]] = []
    for subtype, count in out["by_framework_subtype"].items():
        if count < 3:
            continue
        sub_vals = by_sub.get(subtype, {})
        angle_vals = sub_vals.get("vh_vl_angle_deg", [])
        iface_mean_vals = []
        iface_min_vals = []
        for rec in ok:
            if framework_subtype(rec) != subtype:
                continue
            v = safe_float(rec.get("interface_mean_dist_A"))
            if v is not None:
                iface_mean_vals.append(v)
            v = safe_float(rec.get("interface_min_dist_A"))
            if v is not None:
                iface_min_vals.append(v)
        entry: Dict[str, Any] = {
            "framework_subtype": subtype,
            "count": count,
            "vh_vl_angle_deg": stats(angle_vals) if angle_vals else {},
            "interface_mean_dist_A": stats(iface_mean_vals) if iface_mean_vals else {},
            "interface_min_dist_A": stats(iface_min_vals) if iface_min_vals else {},
        }
        pairing_rules.append(entry)
    out["framework_pairing_rules"] = sorted(pairing_rules, key=lambda x: -x["count"])[:25]

    # Convert defaultdict for JSON
    out["by_canonical"] = dict(out["by_canonical"])
    return out, ok


def write_report(report: Dict, out_md: Path) -> None:
    lines = [
        "# Vernier Zone &  ",
        "",
        " Engineered  PDB ，****。",
        "：**CDR North **、**VH/VL **、****、Vernier 。",
        "",
        f"- ****: {report.get('valid_pdbs', 0)} / {report.get('total_pdbs', 0)}",
        "",
        "---",
        "",
        "## 1. CDR North （Canonical ）",
        "",
        "North/Chothia  CDR （）。。",
        "",
    ]
    northern = report.get("canonical_northern_summary") or {}
    if northern:
        lines.append("|  |  |")
        lines.append("|:---|---:|")
        for k in ["H1", "H2", "H3", "L1", "L2", "L3"]:
            lines.append(f"| {k} | {northern.get(k, 0)} |")
        lines.append("")
    by_c = report.get("by_canonical", {})
    for k in ["H1", "H2", "H3", "L1", "L2", "L3"]:
        if k in by_c and isinstance(by_c[k], dict) and k not in northern:
            lines.append(f"- **{k}**:  {by_c[k].get('count', 0)}")
    lines.extend(["", "###  (H1|H2|L1) ", ""])
    by_sub = report.get("by_framework_subtype", {})
    for sub, count in sorted(by_sub.items(), key=lambda x: -x[1])[:15]:
        lines.append(f"- `{sub}`: {count}")
    north_counts = report.get("north_structure_counts", {})
    if north_counts:
        lines.extend(["", "### North  (phi/psi)", "", " CDR  φ/ψ  Standard（）vs Outlier 。", ""])
        lines.append("| CDR | Standard | Outlier | N/A |")
        lines.append("|:---|---:|---:|---:|")
        for cdr in ("H1", "H2", "H3", "L1", "L2", "L3"):
            d = north_counts.get(cdr, {})
            lines.append(f"| {cdr} | {d.get('Standard', 0)} | {d.get('Outlier', 0)} | {d.get('N/A', 0)} |")
        lines.append("")
    lines.extend(["", "---", "", "## 2. VH/VL ", "", "（°）。。", ""])
    dist_all = report.get("distributions_overall", {})
    if "vh_vl_angle_deg" in dist_all:
        s = dist_all["vh_vl_angle_deg"]
        lines.append(f"- ****:  {s['mean']:.2f}°,  {s['std']:.2f}°, P5–P95 {s['p5']:.2f}° – {s['p95']:.2f}°")
        lines.append("")
    angle_by_sub = report.get("vh_vl_angle_by_subtype") or {}
    if angle_by_sub:
        lines.append("###  (H1|H2|L1) ")
        lines.append("")
        for sub in sorted(angle_by_sub.keys(), key=lambda x: -report.get("by_framework_subtype", {}).get(x, 0))[:10]:
            s = angle_by_sub[sub]
            n = report.get("by_framework_subtype", {}).get(sub, 0)
            lines.append(f"- **{sub}** (n={n}): mean={s['mean']:.2f}°, P50={s['p50']:.2f}°, P5–P95={s['p5']:.2f}°–{s['p95']:.2f}°")
        lines.append("")
    lines.extend(["", "---", "", "## 3. ", ""])
    lines.append(" (H1|H2|L1)  VH/VL ，。")
    lines.append("")
    pairing = report.get("framework_pairing_rules") or []
    if pairing:
        lines.append("|  (H1|H2|L1) |  |  mean(°) |  P50(°) | (Å) | (Å) |")
        lines.append("|:---|---:|---:|---:|---:|---:|")
        for p in pairing[:15]:
            sub = p.get("framework_subtype", "")
            cnt = p.get("count", 0)
            a = p.get("vh_vl_angle_deg") or {}
            im = p.get("interface_mean_dist_A") or {}
            iq = p.get("interface_min_dist_A") or {}
            lines.append(
                f"| {sub} | {cnt} | {a.get('mean', 0):.1f} | {a.get('p50', 0):.1f} | {im.get('mean', 0):.2f} | {iq.get('mean', 0):.2f} |"
            )
        lines.append("")
    lines.extend(["", "---", "", "## 4. （）", ""])

    dist_all = report.get("distributions_overall", {})
    for name, label in [
        ("interface_mean_dist_A", "VH/VL  (Å)"),
        ("interface_min_dist_A", "VH/VL  (Å)"),
        ("vernier_sasa_total", "Vernier  SASA (Å²)"),
    ]:
        if name not in dist_all:
            continue
        s = dist_all[name]
        lines.append(f"### {label}")
        lines.append(f"- : {s['mean']:.2f}, : {s['std']:.2f}")
        lines.append(f"- P5–P95: {s['p5']:.2f} – {s['p95']:.2f}")
        lines.append("")

    lines.extend(["", "### Vernier  (Contact Number)", ""])
    for pos in KEY_VERNIER:
        key = f"packing_{pos}"
        if key not in dist_all:
            continue
        s = dist_all[key]
        lines.append(f"- **{pos}**:  {s['mean']:.1f}, P5–P95 {s['p5']:.1f} – {s['p95']:.1f}")
    lines.extend(["", "### Vernier ↔ CDR  (Å)", ""])
    for k in KEY_CDR_DIST:
        key = f"dist_{k}"
        if key not in dist_all:
            continue
        s = dist_all[key]
        lines.append(f"- **{k}**:  {s['mean']:.2f}, P5–P95 {s['p5']:.2f} – {s['p95']:.2f}")
    lines.extend(["", "---", "", "## 5.  H2 Canonical  Vernier/", ""])
    lines.append("H2  VH 71 ， H2 。")
    lines.append("")
    for h2, d in sorted(report.get("distributions_by_H2", {}).items()):
        lines.append(f"### {h2}")
        for metric, s in d.items():
            lines.append(f"- {metric}: n={s['n']}, mean={s['mean']:.2f}, P5–P95={s['p5']:.2f}–{s['p95']:.2f}")
        lines.append("")
    lines.extend(["", "---", "", "## 6. （）", ""])
    lines.append("1. **CDR North **:  H1/H2/L1 ，「」；")
    lines.append("2. **VH/VL **: / P5–P95 ；")
    lines.append("3. **Vernier  (VH_71, VH_94 )**:  H2 ，；")
    lines.append("4. **Vernier–CDR **: 「Vernier_to_any_CDR」， CDR ；")
    lines.append("5. **Vernier  (SASA)**:  SASA ， Vernier 。")
    lines.append("")
    lines.append("* `analyze_vernier_framework_patterns.py` 。*")
    out_md.write_text("\n".join(lines), encoding="utf-8")


def main():
    ap = argparse.ArgumentParser(description="Analyze Vernier & framework patterns from structure metrics")
    ap.add_argument("--metrics", default=str(DEFAULT_METRICS), help="Path to structure_metrics_summary.json")
    args = ap.parse_args()
    path = Path(args.metrics)
    if not path.is_file():
        print(f"Metrics file not found: {path}")
        print("Run first: python scripts/structure_metrics_humanization.py --dir data/structures/engineered --out data/humanization_assay/structure_metrics_summary.json")
        return 1
    report, _ = run_analysis(path)
    if report.get("error"):
        print(report["error"])
        return 1
    OUT_JSON.parent.mkdir(parents=True, exist_ok=True)
    # JSON-serializable: remove numpy if any
    def to_serializable(obj):
        if isinstance(obj, dict):
            return {k: to_serializable(v) for k, v in obj.items()}
        if isinstance(obj, list):
            return [to_serializable(x) for x in obj]
        if isinstance(obj, (np.integer, np.floating)):
            return float(obj)
        return obj
    with open(OUT_JSON, "w", encoding="utf-8") as f:
        json.dump(to_serializable(report), f, indent=2, ensure_ascii=False)
    write_report(report, OUT_MD)
    print(f"Wrote {OUT_JSON}")
    print(f"Wrote {OUT_MD}")
    print(f"Valid structures: {report['valid_pdbs']}, framework subtypes: {len(report.get('by_framework_subtype', {}))}")
    return 0


if __name__ == "__main__":
    exit(main())
