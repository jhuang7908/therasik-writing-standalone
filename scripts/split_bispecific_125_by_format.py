#!/usr/bin/env python3
"""
Split the 125 bispecific antibodies into two parts:
  1. scFv-like (with linker): format_class == bispecific_scFv_like
  2. IgG-like: format_class == bispecific_IgG_like

Reads: data/design_rules/bispecific_125_knowledge.json
Writes: data/design_rules/bispecific_125_scfv_like.json
        data/design_rules/bispecific_125_igg_like.json
"""
import json
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent
KNOWLEDGE_PATH = PROJECT_ROOT / "data" / "design_rules" / "bispecific_125_knowledge.json"
OUT_DIR = PROJECT_ROOT / "data" / "design_rules"


def main():
    with open(KNOWLEDGE_PATH, encoding="utf-8") as f:
        data = json.load(f)

    records = data.get("records", [])
    scfv_like = [r for r in records if r.get("format_class") == "bispecific_scFv_like"]
    igg_like = [r for r in records if r.get("format_class") == "bispecific_IgG_like"]
    other = [r for r in records if r.get("format_class") not in ("bispecific_scFv_like", "bispecific_IgG_like")]

    def dump_part(name: str, part_records: list, description: str):
        out = {
            "meta": {
                "source": "slice_4_bispecific_engineering",
                "subset": name,
                "description": description,
                "count": len(part_records),
            },
            "antibody_ids": [r["antibody_id"] for r in part_records],
            "records": part_records,
        }
        path = OUT_DIR / f"bispecific_125_{name}.json"
        with open(path, "w", encoding="utf-8") as f:
            json.dump(out, f, ensure_ascii=False, indent=2)
        print(f"Wrote {path.name}: {len(part_records)} antibodies")

    dump_part(
        "scfv_like",
        scfv_like,
        "Bispecific scFv-like (with linker): BiTE, Tandem scFv, Mixed mAb+scFv, etc.",
    )
    dump_part(
        "igg_like",
        igg_like,
        "Bispecific IgG-like: KiH, CrossMab, DVD-Ig, Whole mAb, etc.",
    )
    if other:
        print(f"Skipped {len(other)} records with format_class not scFv-like/IgG-like: {set(r.get('format_class') for r in other)}")

    print(f"Total: scFv-like {len(scfv_like)} + IgG-like {len(igg_like)} = {len(scfv_like) + len(igg_like)}")


if __name__ == "__main__":
    main()
