"""
Paragraph Structure QA
======================
Reads the manuscript and computes objective statistics to detect:
  - Overly uniform sentence length (AI rhythm)
  - Fragmented paragraphs (too many single-sentence paragraphs)
  - Repetitive sentence openers

Writes 03_QA/paragraph_structure_QA.md with Status: PASS or FAIL.
Exit code 0 = PASS, 1 = FAIL.
"""
from __future__ import annotations

import argparse
import re
import statistics
from collections import Counter
from pathlib import Path


# ── Thresholds ────────────────────────────────────────────────────────────────
AVG_LEN_MAX = 35          # average sentence word count above this -> AI-like
STDEV_MIN = 5             # sentence length std dev below this -> too uniform
STDEV_MIN_N = 10          # only apply stdev check when ≥ N sentences
SHORT_PARA_RATIO_MAX = 0.6  # >60% paragraphs with <3 sentences -> fragmented
SINGLE_SENT_RATIO_MAX = 0.30  # >30% single-sentence paragraphs -> fragmented
OPENER_RATIO_MAX = 0.30   # >30% sentences start with same word -> repetitive
# ──────────────────────────────────────────────────────────────────────────────


def split_sentences(text: str) -> list[str]:
    """Naive sentence splitter that works on academic prose."""
    # Remove markdown-ish artifacts first
    text = re.sub(r"\*+", "", text)
    text = re.sub(r"`[^`]+`", "CODE", text)
    # Split on .!? followed by whitespace or end-of-string
    raw = re.split(r"(?<=[.!?])\s+", text.strip())
    # Keep only segments with ≥3 words (filter headers/captions)
    return [s for s in raw if len(s.split()) >= 3]


def analyze(text: str) -> dict:
    # Strip code blocks
    text = re.sub(r"```[\s\S]*?```", "", text)
    # Split into paragraphs
    paragraphs = [p.strip() for p in re.split(r"\n{2,}", text) if p.strip()]
    # Keep only body paragraphs (skip headings, figure captions, tables)
    body = [
        p for p in paragraphs
        if not p.startswith("#")
        and not p.startswith("|")
        and not p.startswith("!")
        and len(p.split()) >= 10
    ]

    if not body:
        return {"error": "No body paragraphs found (manuscript may be empty or only headings)"}

    all_sentences: list[str] = []
    para_sent_counts: list[int] = []
    for para in body:
        sents = split_sentences(para)
        para_sent_counts.append(len(sents))
        all_sentences.extend(sents)

    if not all_sentences:
        return {"error": "No sentences detected"}

    word_counts = [len(s.split()) for s in all_sentences]
    avg_len = statistics.mean(word_counts)
    stdev_len = statistics.stdev(word_counts) if len(word_counts) > 1 else 0.0

    short_para = sum(1 for c in para_sent_counts if c < 3)
    single_sent = sum(1 for c in para_sent_counts if c == 1)

    first_words = [
        re.split(r"\W+", s)[0].lower()
        for s in all_sentences
        if re.split(r"\W+", s)
    ]
    counter = Counter(first_words)
    top_word, top_count = counter.most_common(1)[0] if counter else ("", 0)
    opener_ratio = top_count / len(all_sentences) if all_sentences else 0.0

    return {
        "paragraph_count": len(body),
        "sentence_count": len(all_sentences),
        "avg_sentence_word_count": round(avg_len, 1),
        "sentence_length_stdev": round(stdev_len, 1),
        "short_paragraph_ratio": round(short_para / len(body), 2),
        "single_sentence_paragraph_ratio": round(single_sent / len(body), 2),
        "most_common_opener": top_word,
        "repetitive_opener_ratio": round(opener_ratio, 2),
    }


def evaluate(stats: dict) -> tuple[str, list[str]]:
    failures: list[str] = []
    avg = stats.get("avg_sentence_word_count", 0)
    if avg > AVG_LEN_MAX:
        failures.append(
            f"Average sentence length {avg} words (threshold {AVG_LEN_MAX}) — overly long, AI-like prose"
        )
    stdev = stats.get("sentence_length_stdev", 999)
    n = stats.get("sentence_count", 0)
    if n >= STDEV_MIN_N and stdev < STDEV_MIN:
        failures.append(
            f"Sentence length std dev {stdev} (threshold >{STDEV_MIN}) — too uniform, AI rhythm"
        )
    short_r = stats.get("short_paragraph_ratio", 0)
    if short_r > SHORT_PARA_RATIO_MAX:
        failures.append(
            f"{short_r*100:.0f}% of paragraphs have <3 sentences (threshold ≤{SHORT_PARA_RATIO_MAX*100:.0f}%) — fragmented"
        )
    single_r = stats.get("single_sentence_paragraph_ratio", 0)
    if single_r > SINGLE_SENT_RATIO_MAX:
        failures.append(
            f"{single_r*100:.0f}% of paragraphs are single sentences (threshold ≤{SINGLE_SENT_RATIO_MAX*100:.0f}%) — fragmented"
        )
    opener_r = stats.get("repetitive_opener_ratio", 0)
    opener_w = stats.get("most_common_opener", "")
    if opener_r > OPENER_RATIO_MAX:
        failures.append(
            f"'{opener_w}' opens {opener_r*100:.0f}% of sentences (threshold ≤{OPENER_RATIO_MAX*100:.0f}%) — repetitive AI pattern"
        )
    return ("FAIL" if failures else "PASS"), failures


def build_report(stats: dict, status: str, failures: list[str]) -> str:
    lines = [f"Status: {status}", "", "## Paragraph Structure QA", ""]
    if "error" in stats:
        lines += [f"**Error:** {stats['error']}", ""]
    else:
        lines += [
            f"| Metric | Value |",
            f"| --- | --- |",
            f"| Body paragraphs | {stats['paragraph_count']} |",
            f"| Sentences | {stats['sentence_count']} |",
            f"| Avg sentence length | {stats['avg_sentence_word_count']} words |",
            f"| Sentence length std dev | {stats['sentence_length_stdev']} |",
            f"| Short paragraph ratio (<3 sentences) | {stats['short_paragraph_ratio']} |",
            f"| Single-sentence paragraph ratio | {stats['single_sentence_paragraph_ratio']} |",
            f"| Most common opener | '{stats['most_common_opener']}' ({stats['repetitive_opener_ratio']} ratio) |",
            "",
        ]
    if failures:
        lines += ["## Failures", ""]
        for f in failures:
            lines.append(f"- {f}")
        lines.append("")
    else:
        lines += ["All paragraph structure checks passed.", ""]
    return "\n".join(lines)


def main() -> int:
    parser = argparse.ArgumentParser(description="Paragraph structure QA gate")
    parser.add_argument("--project-root", required=True)
    parser.add_argument("--manuscript", default="01_manuscript/manuscript.md")
    parser.add_argument("--qa-dir", default="03_QA")
    args = parser.parse_args()

    project_root = Path(args.project_root).resolve()
    manuscript_path = project_root / args.manuscript
    qa_dir = project_root / args.qa_dir
    qa_dir.mkdir(parents=True, exist_ok=True)
    out_path = qa_dir / "paragraph_structure_QA.md"

    if not manuscript_path.exists():
        status = "FAIL"
        report = f"Status: FAIL\n\nManuscript not found: {manuscript_path}\n"
    else:
        text = manuscript_path.read_text(encoding="utf-8", errors="ignore")
        stats = analyze(text)
        if "error" in stats:
            status = "FAIL"
            failures = [stats["error"]]
        else:
            status, failures = evaluate(stats)
        report = build_report(stats, status, failures)

    out_path.write_text(report, encoding="utf-8")
    print(f"paragraph_structure_QA: {status} -> {out_path}")
    return 0 if status == "PASS" else 1


if __name__ == "__main__":
    raise SystemExit(main())
