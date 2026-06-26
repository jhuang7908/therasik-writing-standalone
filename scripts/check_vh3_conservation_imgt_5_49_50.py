"""
Check conservation of selected IMGT positions within human IGHV3 germlines.

Data source:
  data/germlines/vhh_v1/vhh_germline_assets_clean.jsonl

Output:
  output/vh3_conservation_imgt_5_49_50.md
  output/vh3_conservation_imgt_5_49_50.json
"""

from __future__ import annotations

import json
import math
from collections import Counter
from pathlib import Path


def shannon_entropy_bits(counts: Counter[str]) -> float:
    n = sum(counts.values())
    if n <= 0:
        return 0.0
    h = 0.0
    for cnt in counts.values():
        p = cnt / n
        if p > 0:
            h -= p * math.log(p, 2)
    return h


def main() -> None:
    root = Path(__file__).resolve().parents[1]
    assets = root / "data" / "germlines" / "vhh_v1" / "vhh_germline_assets_clean.jsonl"
    out_dir = root / "output"
    out_dir.mkdir(parents=True, exist_ok=True)

    # NOTE: In this dataset, identifiers look like:
    #   <accession>|<IGHV...*..>|Homo
    # and per-position residues are in obj["imgt_map"] with string IMGT keys.
    positions = ["5", "49", "50"]

    vh3_rows: list[dict] = []
    all_human = 0

    with assets.open("r", encoding="utf-8") as f:
        for line in f:
            obj = json.loads(line)
            sid = obj.get("sequence_id", "")
            if "Homo" not in sid:
                continue
            all_human += 1

            parts = sid.split("|")
            gene = parts[1] if len(parts) > 1 else ""
            if not gene.startswith("IGHV3-"):
                continue

            imgt_map = obj.get("imgt_map") or {}
            vh3_rows.append({"sequence_id": sid, "gene": gene, "imgt_map": imgt_map})

    n_vh3 = len(vh3_rows)

    summary_lines: list[str] = [
        f"Human germlines total (Homo in sequence_id): {all_human}",
        f"Human IGHV3 germlines used: {n_vh3}",
    ]

    out_rows: list[dict] = []
    for pos in positions:
        counts: Counter[str] = Counter()
        missing = 0
        for r in vh3_rows:
            aa = r["imgt_map"].get(pos)
            if aa is None:
                missing += 1
            else:
                counts[aa] += 1

        n_with_aa = sum(counts.values())
        entropy_bits = shannon_entropy_bits(counts)
        if counts:
            most_aa, most_cnt = counts.most_common(1)[0]
            most_freq = most_cnt / n_with_aa if n_with_aa else 0.0
        else:
            most_aa, most_cnt, most_freq = "", 0, 0.0

        out_rows.append(
            {
                "imgt_pos": int(pos),
                "n_total_vh3": n_vh3,
                "n_with_aa": n_with_aa,
                "n_missing": missing,
                "most_common_aa": most_aa,
                "most_common_cnt": most_cnt,
                "most_common_freq": most_freq,
                "entropy_bits": entropy_bits,
                "aa_counts": dict(counts),
            }
        )

        if n_with_aa:
            summary_lines.append(
                f"IMGT {pos}: n={n_with_aa} (missing={missing}); most={most_aa} ({most_cnt}/{n_with_aa}={most_freq:.3f}); entropy={entropy_bits:.4f} bits"
            )
        else:
            summary_lines.append(
                f"IMGT {pos}: n=0 (missing={missing}); most=NA; entropy={entropy_bits:.4f} bits"
            )

    md_path = out_dir / "vh3_conservation_imgt_5_49_50.md"
    json_path = out_dir / "vh3_conservation_imgt_5_49_50.json"

    md_lines: list[str] = []
    md_lines.append("# VH3 germline conservation (IMGT 5/49/50)")
    md_lines.append("")
    md_lines.extend(["- " + x for x in summary_lines])
    md_lines.append("")
    md_lines.append("## Per-position amino-acid counts")
    md_lines.append("")
    for r in out_rows:
        md_lines.append(f"### IMGT {r['imgt_pos']}")
        md_lines.append("")
        md_lines.append(
            f"- n_with_aa: {r['n_with_aa']} / n_total_vh3: {r['n_total_vh3']} (missing={r['n_missing']})"
        )
        md_lines.append(
            f"- most_common: {r['most_common_aa']} ({r['most_common_cnt']}/{r['n_with_aa']}={r['most_common_freq']:.3f})"
            if r["n_with_aa"]
            else "- most_common: NA"
        )
        md_lines.append(f"- entropy_bits: {r['entropy_bits']:.4f}")
        md_lines.append(f"- aa_counts: {r['aa_counts']}")
        md_lines.append("")

    md_path.write_text("\n".join(md_lines) + "\n", encoding="utf-8")
    json_path.write_text(
        json.dumps({"summary": summary_lines, "rows": out_rows}, indent=2, ensure_ascii=False)
        + "\n",
        encoding="utf-8",
    )

    print("\n".join(summary_lines))
    print("WROTE", md_path)
    print("WROTE", json_path)


if __name__ == "__main__":
    main()

