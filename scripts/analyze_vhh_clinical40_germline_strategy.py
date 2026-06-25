#!/usr/bin/env python3
"""
analyze_vhh_clinical40_germline_strategy.py
==========================================
 data/vhh_39_clinical_atlas/master_table.csv（40  VHH）：

1.  **14 **（ humanize_vhh ：FR  identity）
2.  **human_vs_alpaca_scaffold_alignment**  **framework_identity **（ panel A/B/C）
3.  **Human_Identity_pct、CDR3 、Classification（North class）**  **S1/S2/S3 ↔ panel A/B/C** 

：
  - data/vhh_39_clinical_atlas/clinical40_germline_strategy.json
  - docs/VHH_CLINICAL40_GERMLINE_STRATEGY.md

：
  cd Antibody_Engineer_Suite
  python scripts/analyze_vhh_clinical40_germline_strategy.py
"""
from __future__ import annotations

import csv
import json
import sys
from collections import Counter
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

SUITE_ROOT = Path(__file__).resolve().parents[1]
if str(SUITE_ROOT) not in sys.path:
    sys.path.insert(0, str(SUITE_ROOT))


def _parse_float(x: str) -> Optional[float]:
    x = (x or "").strip()
    if not x:
        return None
    try:
        return float(x)
    except ValueError:
        return None


def _parse_int(x: str) -> Optional[int]:
    x = (x or "").strip()
    if not x:
        return None
    try:
        return int(float(x))
    except ValueError:
        return None


def recommend_tier(
    human_identity_pct: Optional[float],
    cdr3_len: Optional[int],
    classification: str,
    scaffold_fr_identity: float,
) -> Tuple[str, str, List[str]]:
    """
     (S1|S2|S3, A|B|C, reasons)
    ：S1↔A, S2↔B, S3↔C
    """
    reasons: List[str] = []
    cls = (classification or "").strip()

    #  → 
    if human_identity_pct is not None:
        if human_identity_pct >= 90:
            reasons.append(f"Human_Identity_pct={human_identity_pct:.1f}%≥90 → ")
            return "S1", "A", reasons
        if human_identity_pct >= 82:
            reasons.append(f"Human_Identity_pct={human_identity_pct:.1f}%  → ")
            return "S2", "B", reasons
        if human_identity_pct < 75:
            reasons.append(f"Human_Identity_pct={human_identity_pct:.1f}%<75 →  hallmark ")
            return "S3", "C", reasons

    #  CDR3：， FR 
    if cdr3_len is not None and cdr3_len >= 19:
        reasons.append(f"CDR3_len={cdr3_len}≥19 →  + ")
        if cdr3_len >= 22:
            return "S3", "C", reasons + [" CDR3 → S3/C + "]
        return "S2", "B", reasons

    # North class（）
    if "Class 3" in cls or cls.strip() == "3":
        reasons.append(f"Classification={cls!r} → Class3 ")
        return "S3", "C", reasons
    if "Class 2" in cls:
        reasons.append("Class 2 → ")
        return "S2", "B", reasons
    if "Class 1" in cls:
        reasons.append("Class 1 → ")
        return "S1", "A", reasons

    #  FR ：，
    if scaffold_fr_identity < 0.82:
        reasons.append(f"scaffold_FR_identity={scaffold_fr_identity:.3f}<0.82 → ")
        return "S2", "B", reasons

    reasons.append("：（S2/B）")
    return "S2", "B", reasons


def best_human_per_panel(
    alignment_index: Dict[str, Dict[str, Dict[str, Any]]],
    alpaca_id: str,
) -> Dict[str, Tuple[str, float]]:
    """ panel (A/B/C)  framework_identity  ID。"""
    out = {"A": ("", 0.0), "B": ("", 0.0), "C": ("", 0.0)}
    sub = alignment_index.get(alpaca_id) or {}
    for tid, scores in sub.items():
        fi = float(scores.get("framework_identity") or 0)
        if tid.endswith("_SAFE_A"):
            if fi > out["A"][1]:
                out["A"] = (tid, fi)
        elif tid.endswith("_SAFE_B"):
            if fi > out["B"][1]:
                out["B"] = (tid, fi)
        elif tid.endswith("_SAFE_C"):
            if fi > out["C"][1]:
                out["C"] = (tid, fi)
    return out


def _framework_from_csv_row(row: Dict[str, str]) -> Optional[str]:
    """Atlas  Anarcii（40 ）。"""
    if (row.get("has_segment") or "").upper() != "Y":
        return None
    parts = [row.get(k) or "" for k in ("FR1", "FR2", "FR3", "FR4")]
    if not any(parts):
        return None
    return "".join(parts)


def _pick_scaffold_by_framework(
    vhh_framework: str,
    scaffolds: List[Dict[str, Any]],
) -> Tuple[Optional[Dict[str, Any]], float]:
    best_scaffold = None
    best_identity = 0.0
    for scaffold in scaffolds:
        sc_fw = scaffold["consensus"]["framework_full"]
        L = min(len(vhh_framework), len(sc_fw))
        if L == 0:
            continue
        same = sum(1 for i in range(L) if vhh_framework[i] == sc_fw[i])
        identity = same / L
        if identity > best_identity:
            best_identity = identity
            best_scaffold = scaffold
    return best_scaffold, best_identity


def main() -> None:
    from core.scaffolds import load_alpaca_vhh_scaffolds, load_alignment_matrix
    from core.vhh_humanization import find_best_matching_scaffold

    csv_path = SUITE_ROOT / "data" / "vhh_39_clinical_atlas" / "master_table.csv"
    out_json = SUITE_ROOT / "data" / "vhh_39_clinical_atlas" / "clinical40_germline_strategy.json"
    out_md = SUITE_ROOT / "docs" / "VHH_CLINICAL40_GERMLINE_STRATEGY.md"

    scaffolds = load_alpaca_vhh_scaffolds()
    alignment_index = load_alignment_matrix()

    rows: List[Dict[str, str]] = []
    with csv_path.open(encoding="utf-8") as f:
        rows = list(csv.DictReader(f))

    per_row: List[Dict[str, Any]] = []
    scaffold_counts: Counter = Counter()
    tier_counts: Counter = Counter()
    panel_counts: Counter = Counter()

    for row in rows:
        name = row.get("Name") or row.get("antibody_id") or "unknown"
        seq = (row.get("Sequence") or "").strip()
        if not seq:
            continue
        fw_csv = _framework_from_csv_row(row)
        if fw_csv:
            best_sc, sc_iden = _pick_scaffold_by_framework(fw_csv, scaffolds)
        else:
            best_sc, sc_iden = find_best_matching_scaffold(seq, scaffolds)
        alpaca_id = (best_sc or {}).get("scaffold_id", "UNKNOWN")
        scaffold_counts[alpaca_id] += 1

        hi = _parse_float(row.get("Human_Identity_pct") or "")
        cdr3 = _parse_int(row.get("CDR3_len") or row.get("CDR3_Length_aa") or "")
        cls = row.get("Classification") or ""

        strat, panel, reasons = recommend_tier(hi, cdr3, cls, sc_iden)
        tier_counts[strat] += 1
        panel_counts[panel] += 1

        best_h = best_human_per_panel(alignment_index, alpaca_id)
        chosen_tid, chosen_fi = best_h.get(panel, ("", 0.0))

        per_row.append({
            "name": name,
            "cdr3_len": cdr3,
            "human_identity_pct": hi,
            "classification": cls or None,
            "cdr2_fold": row.get("CDR2_Fold") or None,
            "clinical_phase": row.get("Clinical_Phase") or None,
            "target": row.get("Target") or None,
            "best_alpaca_scaffold_id": alpaca_id,
            "scaffold_fr_identity": round(sc_iden, 4),
            "recommended_strategy": strat,
            "recommended_panel": panel,
            "recommended_human_template_top": chosen_tid,
            "framework_identity_to_chosen_template": round(chosen_fi, 4),
            "best_human_by_panel": {
                k: {"template_id": v[0], "framework_identity": round(v[1], 4)}
                for k, v in best_h.items()
            },
            "strategy_reasons": reasons,
        })

    summary = {
        "n_sequences_analyzed": len(per_row),
        "scaffold_usage_top": scaffold_counts.most_common(14),
        "recommended_tier_counts": dict(tier_counts),
        "recommended_panel_counts": dict(panel_counts),
        "rules_version": "clinical40_v1",
        "data_source": str(csv_path.relative_to(SUITE_ROOT)).replace("\\", "/"),
    }

    payload = {"summary": summary, "per_antibody": per_row}
    out_json.parent.mkdir(parents=True, exist_ok=True)
    out_json.write_text(json.dumps(payload, indent=2, ensure_ascii=False), encoding="utf-8")

    # Markdown report
    lines = [
        "# 40  VHH：Germline / 「」",
        "",
        "****：`scripts/analyze_vhh_clinical40_germline_strategy.py`",
        f"****：`{summary['data_source']}`",
        f"****：{summary['n_sequences_analyzed']}",
        "",
        "## 1. （）",
        "",
        "|  |  |",
        "|------|------|",
        "| ** germline / ** |  `humanize_vhh` ： **14 ** **FR1+FR2+FR3+FR4**  **identity **  |",
        "| **** |  `human_vs_alpaca_scaffold_alignment.json` ， **panel A/B/C**  **framework_identity **  `human_vh3_vhh_safe_templates`  |",
        "| **FR vs CDR** |  `select_human_templates` ：**FR **；CDR  ** warning**， **** |",
        "",
        "## 2.  VHH ",
        "",
        "### 2.1  Tier（S1/S2/S3）",
        "",
        "| Tier |  |  |",
        "|------|------|------|",
    ]
    for t in ("S1", "S2", "S3"):
        c = tier_counts.get(t, 0)
        lines.append(f"| **{t}** | {c} | S1↔panel A ；S2↔B ；S3↔C  hallmark |")
    lines += [
        "",
        "### 2.2  Panel（A/B/C）",
        "",
        "| Panel |  |",
        "|------|------|",
    ]
    for p in ("A", "B", "C"):
        lines.append(f"| {p} | {panel_counts.get(p, 0)} |")
    lines += [
        "",
        "### 2.3  Top（ cluster）",
        "",
        "| scaffold_id |  |",
        "|-------------|----------|",
    ]
    for sid, cnt in scaffold_counts.most_common(14):
        lines.append(f"| `{sid}` | {cnt} |")

    lines += [
        "",
        "## 3. （ 40 ）",
        "",
        " ****， ****； `HumanizationEngine(workflow=\"vhh\")` + /。",
        "",
        "1. **Human_Identity_pct ≥ 90%** → **S1 / panel A**（≈7， `tier_system_config` ）",
        "2. **Human_Identity_pct 82–90%**  **CDR3 &lt; 19**  scaffold FR identity  → **S2 / B**",
        "3. **Human_Identity_pct &lt; 75%**  **North Class 3**  **CDR3 ≥ 22** → **S3 / C**",
        "4. **CDR3 19–21** →  **S2/B**， ** + CDR **",
        "5. **scaffold FR identity &lt; 0.82** →  **S2/B**， hallmark",
        "",
        "## 4. （JSON）",
        "",
        f"：`{out_json.relative_to(SUITE_ROOT).as_posix()}`（ `recommended_human_template_top` ）。",
        "",
        "---",
        "",
        "*，。*",
        "",
    ]
    out_md.write_text("\n".join(lines), encoding="utf-8")

    print(f"[clinical40] wrote {out_json}")
    print(f"[clinical40] wrote {out_md}")
    print(f"[clinical40] tier_counts: {dict(tier_counts)} panel_counts: {dict(panel_counts)}")


if __name__ == "__main__":
    main()
