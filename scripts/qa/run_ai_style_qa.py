"""
AI Style / Human Voice QA
=========================
Detects linguistic patterns characteristic of LLM-generated academic prose:

  1. Hedge-word overuse ("notably", "importantly", "it is worth noting", ...)
  2. Transition-word density ("furthermore", "moreover", "additionally", ...)
  3. Self-commentary phrases ("in this review", "in this paper", "we aim to")
     used in excessive frequency
  4. Filler openers that LLMs favour as sentence starters
  5. Bullet-point contamination in body prose (lines starting with "-" or "•"
     that are not inside a recognised list section)

Writes 03_QA/ai_style_human_voice_QA.md with Status: PASS or FAIL.
Exit code 0 = PASS, 1 = FAIL.
"""
from __future__ import annotations

import argparse
import re
from pathlib import Path

# ── Pattern lists ─────────────────────────────────────────────────────────────

HEDGE_WORDS = [
    r"\bnotably\b", r"\bimportantly\b",
    r"\bit is worth noting\b", r"\bit is important to note\b",
    r"\bit should be noted\b", r"\bof note\b", r"\binterestingly\b",
    # NOTE: "significantly" is intentionally excluded — in biomedical prose it
    # almost always denotes statistical significance, not a vague emphasis hedge.
]

TRANSITION_WORDS = [
    r"\bfurthermore\b", r"\bmoreover\b", r"\badditionally\b",
    r"\bin addition\b", r"\bin conclusion\b", r"\bin summary\b",
    r"\boverall\b", r"\btaken together\b", r"\bcollectively\b",
    r"\bto summarize\b", r"\bto conclude\b",
]

SELF_COMMENTARY = [
    r"\bin this review\b", r"\bin this paper\b", r"\bin this study\b",
    r"\bin this article\b", r"\bthis review (aims|seeks|provides|discusses)\b",
    r"\bwe (aim|seek|provide|discuss|present|demonstrate)\b",
    r"\bthe (purpose|goal|aim|objective) of this\b",
]

FILLER_OPENERS = [
    r"^(furthermore|moreover|additionally|in addition|notably|importantly"
    r"|interestingly|overall|taken together|collectively),",
]

# ── Thresholds ────────────────────────────────────────────────────────────────
HEDGE_RATE_MAX = 0.04          # >4 % of sentences contain a hedge word
TRANSITION_RATE_MAX = 0.15     # >15 % of sentences open with a transition word
SELF_COMMENTARY_COUNT_MAX = 6  # >6 occurrences — lower counts are normal in original research
BULLET_IN_PROSE_MAX = 5        # >5 bullet-like lines inside non-list paragraphs
# ──────────────────────────────────────────────────────────────────────────────


def _count_pattern_hits(text: str, patterns: list[str]) -> int:
    count = 0
    for pat in patterns:
        count += len(re.findall(pat, text, re.IGNORECASE))
    return count


def _sentences(text: str) -> list[str]:
    """Split text into sentences, avoiding over-splitting on abbreviations."""
    text = re.sub(r"```[\s\S]*?```", "", text)
    text = re.sub(r"\*+", "", text)
    # Protect abbreviations using lambda replacements (avoids invalid regex escape in repl string)
    PLACEHOLDER = "\x01"
    abbrev_pats = [
        r"(?i)(e\.g)\.(\s)",
        r"(?i)(i\.e)\.(\s)",
        r"(?i)(et al)\.(\s)",
        r"(?i)(Fig|fig)\.(\s)",
        r"(?i)(Table|Suppl|Dr|Prof|Mr|Mrs|vol|pp|vs|no)\.(\s)",
        r"(\d+\.\d+)\.(\s)",
    ]
    protected = text
    for pat in abbrev_pats:
        protected = re.sub(pat, lambda m: m.group(1) + PLACEHOLDER + m.group(2), protected)
    raw = re.split(r"(?<=[.!?])\s+(?=[A-Z\(\"\'])", protected)
    result = []
    for s in raw:
        s = s.replace(PLACEHOLDER, ".")
        if len(s.split()) >= 4:
            result.append(s)
    return result


def analyze(text: str) -> dict:
    # Strip code blocks and headings for sentence-level analysis
    clean = re.sub(r"```[\s\S]*?```", "", text)
    # Remove heading lines
    body_lines = [ln for ln in clean.splitlines() if not ln.startswith("#")]
    body = " ".join(body_lines)

    sentences = _sentences(body)
    n = len(sentences) or 1

    hedge_hits = _count_pattern_hits(body, HEDGE_WORDS)
    transition_hits = sum(
        1 for s in sentences
        if any(re.match(pat, s.strip(), re.IGNORECASE) for pat in FILLER_OPENERS)
    )
    self_commentary_hits = _count_pattern_hits(body, SELF_COMMENTARY)

    # Bullet contamination: lines starting with - or • not inside a table
    bullet_lines = [
        ln for ln in text.splitlines()
        if re.match(r"^\s*[-•]\s+\S", ln) and not ln.strip().startswith("|")
    ]

    return {
        "sentence_count": n,
        "hedge_word_hits": hedge_hits,
        "hedge_rate": round(hedge_hits / n, 3),
        "transition_opener_hits": transition_hits,
        "transition_opener_rate": round(transition_hits / n, 3),
        "self_commentary_hits": self_commentary_hits,
        "bullet_in_prose_count": len(bullet_lines),
        "bullet_examples": bullet_lines[:3],
    }


def evaluate(stats: dict) -> tuple[str, list[str]]:
    failures: list[str] = []
    rate = stats["hedge_rate"]
    if rate > HEDGE_RATE_MAX:
        failures.append(
            f"Hedge-word rate {rate:.1%} (threshold ≤{HEDGE_RATE_MAX:.0%}) — "
            f"{stats['hedge_word_hits']} hits in {stats['sentence_count']} sentences"
        )
    tr = stats["transition_opener_rate"]
    if tr > TRANSITION_RATE_MAX:
        failures.append(
            f"Transition-word sentence openers {tr:.1%} (threshold ≤{TRANSITION_RATE_MAX:.0%})"
        )
    sc = stats["self_commentary_hits"]
    if sc > SELF_COMMENTARY_COUNT_MAX:
        failures.append(
            f"Self-commentary phrases appear {sc}× (threshold ≤{SELF_COMMENTARY_COUNT_MAX}) — "
            "reads like an AI meta-description of its own output"
        )
    bp = stats["bullet_in_prose_count"]
    if bp > BULLET_IN_PROSE_MAX:
        failures.append(
            f"{bp} bullet-style lines detected in prose body (threshold ≤{BULLET_IN_PROSE_MAX}) — "
            "convert to integrated paragraph prose"
        )
    return ("FAIL" if failures else "PASS"), failures


def build_report(stats: dict, status: str, failures: list[str]) -> str:
    lines = [f"Status: {status}", "", "## AI Style / Human Voice QA", ""]
    lines += [
        "| Metric | Value |",
        "| --- | --- |",
        f"| Sentences analysed | {stats['sentence_count']} |",
        f"| Hedge-word hits | {stats['hedge_word_hits']} (rate {stats['hedge_rate']:.1%}) |",
        f"| Transition-opener sentences | {stats['transition_opener_hits']} (rate {stats['transition_opener_rate']:.1%}) |",
        f"| Self-commentary phrases | {stats['self_commentary_hits']} |",
        f"| Bullet lines in prose | {stats['bullet_in_prose_count']} |",
        "",
    ]
    if stats["bullet_examples"]:
        lines += ["**Bullet examples:**", ""]
        for ex in stats["bullet_examples"]:
            lines.append(f"    {ex.strip()}")
        lines.append("")
    if failures:
        lines += ["## Failures", ""]
        for f in failures:
            lines.append(f"- {f}")
        lines.append("")
    else:
        lines += ["All AI-style checks passed.", ""]
    return "\n".join(lines)


def main() -> int:
    parser = argparse.ArgumentParser(description="AI style / human voice QA gate")
    parser.add_argument("--project-root", required=True)
    parser.add_argument("--manuscript", default="01_manuscript/manuscript.md")
    parser.add_argument("--qa-dir", default="03_QA")
    args = parser.parse_args()

    project_root = Path(args.project_root).resolve()
    manuscript_path = project_root / args.manuscript
    qa_dir = project_root / args.qa_dir
    qa_dir.mkdir(parents=True, exist_ok=True)
    out_path = qa_dir / "ai_style_human_voice_QA.md"

    if not manuscript_path.exists():
        status, report = "FAIL", f"Status: FAIL\n\nManuscript not found: {manuscript_path}\n"
    else:
        text = manuscript_path.read_text(encoding="utf-8", errors="ignore")
        stats = analyze(text)
        status, failures = evaluate(stats)
        report = build_report(stats, status, failures)

    out_path.write_text(report, encoding="utf-8")
    print(f"ai_style_human_voice_QA: {status} -> {out_path}")
    return 0 if status == "PASS" else 1


if __name__ == "__main__":
    raise SystemExit(main())
