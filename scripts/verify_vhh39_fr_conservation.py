#!/usr/bin/env python3
"""
Verify prior experience on 39 VHH:
  - FR1: human/alpaca highly conserved -> 39 should have very similar FR1
  - FR4: highly conserved, influenced by CDR3 length; FR4 N-terminal vs CDR3 length
  - FR2: hallmark positions - report FR2 diversity (full IMGT 37,44,45,47 need numbering)
Output: data/vhh_clinical_39_union/fr_conservation_verification_report.md
"""
import json
from collections import Counter
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent
UNION_DIR = PROJECT_ROOT / "data" / "vhh_clinical_39_union"
SEGMENTS_JSON = UNION_DIR / "vhh_39_cdr_fr_segments.json"
OUT_REPORT = UNION_DIR / "fr_conservation_verification_report.md"


def position_wise_stats(seqs):
    if not seqs:
        return []
    n = len(seqs)
    L = len(seqs[0])
    if any(len(s) != L for s in seqs):
        return []
    out = []
    for pos in range(L):
        col = [s[pos] for s in seqs]
        cnt = Counter(col)
        maj, count = cnt.most_common(1)[0]
        out.append({"pos": pos, "aa": maj, "count": count, "freq": round(100 * count / n, 1)})
    return out


def main():
    with open(SEGMENTS_JSON, encoding="utf-8") as f:
        data = json.load(f)
    segments = [s for s in data["segments"] if s.get("has_segment") == "Y"]
    n = len(segments)

    fr1_seqs = [s["FR1"] for s in segments]
    fr2_seqs = [s["FR2"] for s in segments]
    fr4_seqs = [s["FR4"] for s in segments]
    cdr3_lens = [s["CDR3_len"] for s in segments]

    fr1_pos = position_wise_stats(fr1_seqs)
    fr1_mean_id = sum(p["freq"] for p in fr1_pos) / len(fr1_pos) if fr1_pos else 0
    unique_fr1 = set(fr1_seqs)

    fr4_pos = position_wise_stats(fr4_seqs)
    fr4_mean_id = sum(p["freq"] for p in fr4_pos) / len(fr4_pos) if fr4_pos else 0
    unique_fr4 = set(fr4_seqs)

    short_cdr3 = 11
    fr4_first = [s["FR4"][0] if s["FR4"] else "" for s in segments]
    long_cdr3 = [(fr4_first[i], cdr3_lens[i]) for i in range(n) if cdr3_lens[i] > short_cdr3]
    short_cdr3_list = [(fr4_first[i], cdr3_lens[i]) for i in range(n) if cdr3_lens[i] <= short_cdr3]
    aa_long = Counter(a for a, _ in long_cdr3 if a)
    aa_short = Counter(a for a, _ in short_cdr3_list if a)

    unique_fr2 = set(fr2_seqs)
    fr2_pos = position_wise_stats(fr2_seqs)
    fr2_mean_id = sum(p["freq"] for p in fr2_pos) / len(fr2_pos) if fr2_pos else 0

    lines = [
        "# 39 VHH （）",
        "",
        "## 1. FR1： -> 39 ",
        "",
        f"- ** FR1 **：{len(unique_fr1)} / 39",
        f"- **（）**：{round(fr1_mean_id, 1)}%",
        "",
        "## 2. FR4：， CDR3 ；FR4 N  CDR3 ",
        "",
        f"- ** FR4 **：{len(unique_fr4)} / 39",
        f"- **（）**：{round(fr4_mean_id, 1)}%",
        "",
        f"### FR4 N  1 （IMGT 118） CDR3 （ {short_cdr3} aa）",
        "",
        f"- **CDR3 > {short_cdr3} aa**：N = {len(long_cdr3)}，：{dict(aa_long)}",
        f"- **CDR3 <= {short_cdr3} aa**：N = {len(short_cdr3_list)}，：{dict(aa_short)}",
        "",
        "## 3. FR2：hallmark ",
        "",
        f"- ** FR2 **：{len(unique_fr2)} / 39，：{round(fr2_mean_id, 1)}%",
        "",
        "---",
        "：scripts/verify_vhh39_fr_conservation.py",
        ""
    ]

    OUT_REPORT.parent.mkdir(parents=True, exist_ok=True)
    with open(OUT_REPORT, "w", encoding="utf-8") as f:
        f.write("\n".join(lines))
    print("Wrote", OUT_REPORT)
    print("FR1 unique:", len(unique_fr1), "mean pos%:", round(fr1_mean_id, 1))
    print("FR4 unique:", len(unique_fr4), "mean pos%:", round(fr4_mean_id, 1))
    print("FR4 N-term: long CDR3", dict(aa_long), "short", dict(aa_short))
    print("FR2 unique:", len(unique_fr2), "mean pos%:", round(fr2_mean_id, 1))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
