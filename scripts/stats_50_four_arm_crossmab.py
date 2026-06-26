#!/usr/bin/env python3
"""
 CrossMab /  CrossMab  50 （chain_class = 4_two_arms）。

：format_raw  "Domain Crossover"  "Crossover"  CrossMab， CrossMab。
VHH-like（ Lunsekimig） 50 ，。

: data/design_rules/igg_like_50_four_arm_names.txt, bispecific_125_igg_like.json
: data/design_rules/igg_like_50_four_arm_crossmab_stats.json
      data/design_rules/igg_like_50_four_arm_crossmab_report.md

Usage:
  python scripts/stats_50_four_arm_crossmab.py
"""
import json
import re
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent
DATA_DIR = PROJECT_ROOT / "data" / "design_rules"
NAMES_FILE = DATA_DIR / "igg_like_50_four_arm_names.txt"
IGG_LIKE_JSON = DATA_DIR / "bispecific_125_igg_like.json"
OUT_JSON = DATA_DIR / "igg_like_50_four_arm_crossmab_stats.json"
OUT_MD = DATA_DIR / "igg_like_50_four_arm_crossmab_report.md"

CROSSMAB_PATTERN = re.compile(r"Domain\s*Crossover|Crossover", re.I)


def is_crossmab(format_raw: str) -> bool:
    if not format_raw or not isinstance(format_raw, str):
        return False
    return bool(CROSSMAB_PATTERN.search(format_raw))


def load_50_four_arm_ids() -> list[str]:
    ids = []
    with open(NAMES_FILE, encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if line and not line.startswith("#"):
                ids.append(line)
    return ids


def main():
    fifty_ids = load_50_four_arm_ids()
    with open(IGG_LIKE_JSON, encoding="utf-8") as f:
        data = json.load(f)
    rec_by_id = {r["antibody_id"]: r for r in data["records"]}

    crossmab_list = []
    non_crossmab_list = []
    missing = []

    for aid in fifty_ids:
        rec = rec_by_id.get(aid)
        if not rec:
            missing.append(aid)
            continue
        fmt = rec.get("format_raw") or ""
        if is_crossmab(fmt):
            crossmab_list.append({"antibody_id": aid, "format_raw": fmt})
        else:
            non_crossmab_list.append({"antibody_id": aid, "format_raw": fmt})

    n_cross = len(crossmab_list)
    n_non = len(non_crossmab_list)
    n_miss = len(missing)

    out = {
        "meta": {
            "source_50": "igg_like_50_four_arm_names.txt",
            "source_format": "bispecific_125_igg_like.json",
            "rule": "CrossMab = format_raw contains 'Domain Crossover' or 'Crossover'",
        },
        "summary": {
            "total_four_arm": 50,
            "with_format_info": n_cross + n_non,
            "missing_in_json": n_miss,
            "crossmab_count": n_cross,
            "non_crossmab_count": n_non,
        },
        "crossmab": [x["antibody_id"] for x in crossmab_list],
        "non_crossmab": [x["antibody_id"] for x in non_crossmab_list],
        "crossmab_details": crossmab_list,
        "non_crossmab_details": non_crossmab_list,
        "missing": missing,
        "vhh_like_note": "VHH-like bispecific (e.g. Lunsekimig) are not in the 50 four-arm list; they are in chain_class 'other' (2 entries) and excluded from Fab CH1/CL pairing pipeline.",
    }

    DATA_DIR.mkdir(parents=True, exist_ok=True)
    with open(OUT_JSON, "w", encoding="utf-8") as f:
        json.dump(out, f, ensure_ascii=False, indent=2)

    # Report
    lines = [
        "# 50 ：CrossMab vs  CrossMab ",
        "",
        "****：`igg_like_50_four_arm_names.txt` + `bispecific_125_igg_like.json`  `format_raw`。",
        "****：`format_raw`  “Domain Crossover”  “Crossover”  **CrossMab**， ** CrossMab**。",
        "",
        "## ",
        "",
        "|  |  |  |",
        "|------|------|------|",
        f"| **CrossMab** | **{n_cross}** | （CH1/CL ） |",
        f"| ** CrossMab** | **{n_non}** |  KiH、、 CH1:CL  |",
        f"|  | {n_cross + n_non} | （H1,L1,H2,L2） |",
        "",
        "## CrossMab ",
        "",
    ]
    for x in crossmab_list:
        lines.append(f"- **{x['antibody_id']}** — `{x['format_raw'][:60]}{'…' if len(x['format_raw'])>60 else ''}`")
    lines.extend([
        "",
        "##  CrossMab ",
        "",
    ])
    for x in non_crossmab_list:
        lines.append(f"- **{x['antibody_id']}** — `{x['format_raw'][:60]}{'…' if len(x['format_raw'])>60 else ''}`")
    lines.extend([
        "",
        "## ",
        "",
        "- ****：23 （3-arm， CH1/CL，）。",
        "- **scFv **：（linker  / 84 ）。",
        "- **50 **： CrossMab /  CrossMab ； CrossMab  CH1:CL  KiH 。",
        "",
        "## VHH-like ",
        "",
        "**50  VHH-like**。VHH-like （ Lunsekimig，sc-5-VH ） 75  IgG-like  `chain_class = other`（2 ），/ Fab CH1/CL  8 ， VHH-like。",
        "",
        "---",
        "",
        "** JSON**：`igg_like_50_four_arm_crossmab_stats.json`",
    ])

    with open(OUT_MD, "w", encoding="utf-8") as f:
        f.write("\n".join(lines))

    print("50 four-arm CrossMab / non-CrossMab stats")
    print(f"  CrossMab:    {n_cross}")
    print(f"  Non-CrossMab: {n_non}")
    if missing:
        print(f"  Missing in JSON: {missing}")
    print(f"  Wrote {OUT_JSON.name} and {OUT_MD.name}")


if __name__ == "__main__":
    main()
