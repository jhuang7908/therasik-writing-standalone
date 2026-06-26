"""
Post-rewrite safety: plagiarism vs style exemplars and generic AI-tone markers.

Style learning uses exemplars for cadence only — output must not copy phrases
or read like generic LLM prose.
"""

from __future__ import annotations

import re
from typing import Any

# Subset aligned with prompts/reduce_ai_tone.system.md
AI_MARKER_PHRASES = (
    "leverages", "underscores", "pivotal", "intricate", "paramount", "robustly",
    "key insights", "ushering in", "transformative", "comprehensive understanding",
    "it is worth noting", "it is important to highlight", "in summary,",
    "furthermore, it is", "plays a crucial role", "sheds light on",
    "a growing body of", "highlights the importance", "paves the way",
)

DEFAULT_PLAGIARISM_SIM_THRESHOLD = 0.58
DEFAULT_PLAGIARISM_NGRAM_THRESHOLD = 0.14
DEFAULT_AI_MARKER_WARN = 2
DEFAULT_AI_MARKER_FAIL = 5


def _sentences(text: str) -> list[str]:
    parts = re.split(r"(?<=[.!?])\s+", text.strip())
    return [p.strip() for p in parts if len(p.strip()) >= 40]


def _word_ngrams(text: str, n: int = 5) -> set[str]:
    words = re.findall(r"[a-zA-Z0-9']+", text.lower())
    if len(words) < n:
        return set()
    return {" ".join(words[i : i + n]) for i in range(len(words) - n + 1)}


def ngram_overlap_ratio(a: str, b: str, n: int = 5) -> float:
    """Fraction of n-grams in `a` that also appear in `b`."""
    ga = _word_ngrams(a, n)
    if not ga:
        return 0.0
    gb = _word_ngrams(b, n)
    return len(ga & gb) / len(ga)


def _max_embedding_similarity(
    text: str,
    exemplars: list[str],
    openai_client: Any,
) -> tuple[float, str | None]:
    from .user_style import _embed_texts

    sentences = _sentences(text)
    if not sentences or not exemplars:
        return 0.0, None
    ex_sents: list[str] = []
    for ex in exemplars:
        ex_sents.extend(_sentences(ex)[:40])
    if not ex_sents:
        ex_sents = [ex[:2000] for ex in exemplars if ex]
    if not ex_sents:
        return 0.0, None

    vecs = _embed_texts(sentences[:24] + ex_sents[:48], openai_client)
    n = len(sentences[:24])
    q_vecs = vecs[:n]
    ex_vecs = vecs[n:]
    best = 0.0
    best_snip: str | None = None
    for q in q_vecs:
        scores = ex_vecs @ q
        i = int(scores.argmax())
        sim = float(scores[i])
        if sim > best:
            best = sim
            best_snip = ex_sents[i][:160]
    return best, best_snip


def check_plagiarism_vs_exemplars(
    text: str,
    exemplars: list[str],
    *,
    openai_client: Any | None = None,
    max_embedding_sim: float = DEFAULT_PLAGIARISM_SIM_THRESHOLD,
    max_ngram_overlap: float = DEFAULT_PLAGIARISM_NGRAM_THRESHOLD,
) -> dict[str, Any]:
    exemplars = [e for e in exemplars if (e or "").strip()]
    if not exemplars:
        return {
            "verdict": "pass",
            "reason": "No exemplars supplied for plagiarism check.",
            "max_ngram_overlap": 0.0,
            "max_embedding_similarity": None,
            "flagged_excerpt": None,
        }

    max_ngram = 0.0
    flagged: str | None = None
    for ex in exemplars:
        ratio = ngram_overlap_ratio(text, ex)
        if ratio > max_ngram:
            max_ngram = ratio
            flagged = ex[:200]

    max_embed = 0.0
    embed_snip: str | None = None
    if openai_client:
        try:
            max_embed, embed_snip = _max_embedding_similarity(text, exemplars, openai_client)
        except Exception:
            pass

    verdict = "pass"
    reasons: list[str] = []
    if max_ngram >= max_ngram_overlap:
        verdict = "fail" if max_ngram >= max_ngram_overlap * 1.35 else "warn"
        reasons.append(f"5-gram overlap {max_ngram:.2f} vs exemplars (limit {max_ngram_overlap}).")
    if max_embed >= max_embedding_sim:
        if max_embed >= max_embedding_sim + 0.08:
            verdict = "fail"
        elif verdict == "pass":
            verdict = "warn"
        reasons.append(
            f"Embedding similarity {max_embed:.2f} to exemplar prose (limit {max_embedding_sim})."
        )

    return {
        "verdict": verdict,
        "reason": " ".join(reasons) if reasons else "No close copying detected vs exemplars.",
        "max_ngram_overlap": round(max_ngram, 4),
        "max_embedding_similarity": round(max_embed, 4) if openai_client else None,
        "flagged_excerpt": embed_snip or flagged,
        "thresholds": {
            "max_ngram_overlap": max_ngram_overlap,
            "max_embedding_similarity": max_embedding_sim,
        },
    }


def check_ai_tone_markers(
    text: str,
    *,
    warn_count: int = DEFAULT_AI_MARKER_WARN,
    fail_count: int = DEFAULT_AI_MARKER_FAIL,
) -> dict[str, Any]:
    lower = text.lower()
    found = [p for p in AI_MARKER_PHRASES if p in lower]
    count = len(found)
    if count >= fail_count:
        verdict = "fail"
    elif count >= warn_count:
        verdict = "warn"
    else:
        verdict = "pass"
    return {
        "verdict": verdict,
        "ai_marker_count": count,
        "ai_markers_found": found[:12],
        "reason": (
            f"{count} generic AI phrase(s) detected."
            if found
            else "No common generic-AI phrase markers detected."
        ),
        "thresholds": {"warn": warn_count, "fail": fail_count},
    }


def style_safety_audit(
    *,
    original: str,
    rewritten: str,
    exemplar_texts: list[str],
    openai_client: Any | None = None,
    check_plagiarism: bool = True,
    check_ai_tone: bool = True,
    check_grammar: bool = True,
    check_readability: bool = True,
    plagiarism_max_sim: float = DEFAULT_PLAGIARISM_SIM_THRESHOLD,
    plagiarism_max_ngram: float = DEFAULT_PLAGIARISM_NGRAM_THRESHOLD,
) -> dict[str, Any]:
    """
    Run all enabled checks; overall PASS / WARN / FAIL.
    Now includes:
      - plagiarism (n-gram + embedding)
      - ai_tone (marker phrases)
      - grammar (LanguageTool, graceful degradation)
      - readability (textstat Flesch-Kincaid / Gunning-Fog, graceful degradation)
    """
    checks: dict[str, Any] = {}
    verdicts: list[str] = []

    if check_plagiarism:
        pl = check_plagiarism_vs_exemplars(
            rewritten,
            exemplar_texts,
            openai_client=openai_client,
            max_embedding_sim=plagiarism_max_sim,
            max_ngram_overlap=plagiarism_max_ngram,
        )
        checks["plagiarism"] = pl
        verdicts.append(pl["verdict"])

    if check_ai_tone:
        ai = check_ai_tone_markers(rewritten)
        checks["ai_tone"] = ai
        verdicts.append(ai["verdict"])

    if check_grammar:
        try:
            from .language_tool import grammar_summary
            gm = grammar_summary(rewritten[:8000])
            checks["grammar"] = gm
            v = gm.get("verdict", "unavailable")
            if v not in ("unavailable",):
                verdicts.append(v)
        except Exception as exc:
            checks["grammar"] = {"available": False, "error": str(exc)[:80]}

    if check_readability:
        try:
            from .article_type_benchmarks import compute_readability, readability_verdict
            rd = compute_readability(rewritten)
            rv = readability_verdict(rd)
            checks["readability"] = {**rd.dict(), "verdict": rv}
            if rv not in ("unavailable",):
                verdicts.append(rv)
        except Exception as exc:
            checks["readability"] = {"available": False, "error": str(exc)[:80]}

    if "fail" in verdicts:
        overall = "fail"
    elif "warn" in verdicts:
        overall = "warn"
    else:
        overall = "pass"

    return {
        "overall_verdict": overall,
        "checks": checks,
        "disclaimer": (
            "Automated style-safety screen only — not a legal plagiarism report. "
            "Exemplars are for cadence; do not reproduce their wording."
        ),
    }
