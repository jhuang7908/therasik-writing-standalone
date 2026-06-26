"""
Manuscript QC — multi-dimension quality scoring for full submissions.

Dimensions scored (each 0-100, with verdict pass/warn/fail):

  1. journal_compliance   — word limits, section presence, reference count
                            (uses journal_specs.check_submission_readiness).
  2. style_match          — n-gram + embedding similarity to journal exemplars.
                            High = matches journal cadence; very high also
                            triggers anti-copy warning.
  3. ai_tone              — AI-marker density (uses style_safety.check_ai_tone_markers).
  4. repetition           — n-gram repetition rate across the whole manuscript.
                            High repetition lowers the score.
  5. logic_grounding      — Claude evaluates how many "strong claims" lack an
                            adjacent reference / hedge / data anchor.
  6. reference_integrity  — % of references successfully fetched from PubMed
                            (or DOI when PMID is absent). Optional.
  7. subjective_language  — heuristic regex for "we believe", "perhaps",
                            "interestingly", "remarkably", etc.

Returns one structured scorecard ready for /export_docx or UI rendering.
"""

from __future__ import annotations

import json
import re
import time
from typing import Any

from .style_safety import check_ai_tone_markers, check_plagiarism_vs_exemplars

# Shared [FILL: ...] regex (must match the one in app.py)
_FILL_RE = re.compile(r"(\[FILL:[^\]]*\])")


# ---------------------------------------------------------------------------
# Thresholds (kept here so callers can tune later without editing call sites).
# ---------------------------------------------------------------------------
SCORE_PASS = 80
SCORE_WARN = 60

SUBJECTIVE_PATTERNS = [
    r"\b(?:we|i)\s+(?:believe|think|feel|suspect|argue|propose|hypothes\w+)\b",
    r"\binterestingly\b", r"\bremarkably\b", r"\bsurprisingly\b",
    r"\belegantly\b", r"\bclearly\s+(?:demonstrates?|shows?)\b",
    r"\bobvious(?:ly)?\b", r"\bperhaps\b", r"\bpresumably\b",
    r"\bit\s+is\s+(?:clear|obvious|evident)\s+that\b",
    r"\bone\s+might\s+(?:argue|expect|imagine)\b",
    r"\bunprecedented\b", r"\bnovel\s+(?:and|with)\b",
    r"\bgame[- ]changing\b", r"\brevolutionary\b",
]
SUBJECTIVE_RE = re.compile("|".join(SUBJECTIVE_PATTERNS), re.IGNORECASE)

STRONG_CLAIM_PATTERNS = [
    r"\b(?:significantly|consistently|uniquely|exclusively)\b",
    r"\bfor\s+the\s+first\s+time\b",
    r"\b(?:abolish|eliminat|prevent|cure|inhibit)\w*\b",
    r"\b(?:greatly|dramatically|markedly)\s+(?:increase|decrease|reduce|improve)\w*\b",
]
STRONG_CLAIM_RE = re.compile("|".join(STRONG_CLAIM_PATTERNS), re.IGNORECASE)

# Recognise inline citations: (Smith 2021), [1], [12,13], (Smith et al., 2020)
INLINE_CITE_RE = re.compile(
    r"(?:\([A-Z][A-Za-z\-']+(?:\s+et\s+al\.)?(?:,)?\s+\d{4}[a-z]?\))"
    r"|(?:\[\d+(?:[\s,;\-]\d+)*\])"
)
# Unresolved PubMed-search placeholders from draft_section (count as grounded)
CITE_PLACEHOLDER_RE = re.compile(r"\[CITE:\s*[^\]]+\]", re.IGNORECASE)
FIGURE_REF_RE = re.compile(r"\b(?:Fig\.?|Figure)\s*\d+[A-Za-z]?", re.IGNORECASE)


def _has_citation_or_data_anchor(window: str) -> bool:
    """True if the text window has a citation or quantitative / figure anchor."""
    if CITE_PLACEHOLDER_RE.search(window):
        return True
    if INLINE_CITE_RE.search(window):
        return True
    if FIGURE_REF_RE.search(window):
        return True
    if re.search(r"\b\d[\d\.,]*\s*(?:%|±|×|\bn\s*=|\bp\s*[=<>])", window, re.I):
        return True
    return False


def _verdict_from_score(score: float) -> str:
    if score >= SCORE_PASS:
        return "pass"
    if score >= SCORE_WARN:
        return "warn"
    return "fail"


def _word_count(text: str) -> int:
    return len(re.findall(r"\b[A-Za-z][A-Za-z\-']*\b", text or ""))


# ---------------------------------------------------------------------------
# Evidence helpers — locate the sentence and section that contain a hit so the
# UI can surface concrete "fix this sentence" suggestions.
# ---------------------------------------------------------------------------

# Simple sentence splitter — handles common abbreviations conservatively.
_SENT_SPLIT_RE = re.compile(r"(?<=[\.\?\!])\s+(?=[A-Z\[\(])")


def _sentence_around(text: str, offset: int, max_chars: int = 280) -> str:
    """Return the sentence in *text* that contains character *offset*."""
    if not text or offset < 0 or offset >= len(text):
        return ""
    # Walk backward to last sentence terminator
    start = max(0, offset - max_chars)
    chunk = text[start: min(len(text), offset + max_chars)]
    rel = offset - start
    # Find sentence boundaries on either side of the offset
    left = chunk.rfind(". ", 0, rel)
    left = max(left, chunk.rfind("? ", 0, rel))
    left = max(left, chunk.rfind("! ", 0, rel))
    left = left + 2 if left >= 0 else 0
    right_candidates = [chunk.find(s, rel) for s in (". ", "? ", "! ") if chunk.find(s, rel) > 0]
    right = min(right_candidates) if right_candidates else len(chunk)
    return chunk[left: right + 1].strip().replace("\n", " ")


def _section_of(sections: list[dict] | None, fragment: str) -> str | None:
    """Return the section key whose text contains *fragment* (best match)."""
    if not sections or not fragment:
        return None
    frag = fragment[:80].lower().strip()
    if not frag:
        return None
    for sec in sections:
        body = (sec.get("text") or "").lower()
        if frag in body:
            return sec.get("key") or sec.get("title")
    return None


# Per-marker suggestion bank for subjective / AI-tone phrases.
_SUGGESTIONS_SUBJECTIVE: dict[str, str] = {
    "we believe": "Replace with a data-anchored statement (e.g., 'these data indicate …').",
    "we think": "Replace with an evidence-based phrasing.",
    "interestingly": "Remove the adverb; let the result speak for itself.",
    "remarkably": "Remove or replace with a quantitative descriptor (e.g., 'a 2-fold increase').",
    "surprisingly": "Remove unless framed as an unexpected statistical finding with a p-value.",
    "clearly demonstrates": "Replace with 'show(s) that …' and cite the supporting figure.",
    "obvious": "Remove; restate the finding directly.",
    "perhaps": "Replace with a hedge tied to data limitation (e.g., 'consistent with …').",
    "unprecedented": "Replace with a comparable benchmark; cite the closest prior report.",
    "novel": "Specify what is novel ('a previously unreported …').",
    "revolutionary": "Remove; use neutral framing.",
}

_SUGGESTIONS_AI_TONE: dict[str, str] = {
    "delve": "Replace with 'examine', 'investigate', or 'analyze'.",
    "underscore": "Replace with 'highlight' or 'show'.",
    "in conclusion": "Replace with a section-specific connector (or remove if already in Discussion).",
    "importantly": "Remove; convey importance via data, not adverbs.",
    "moreover": "Use 'in addition' or rewrite the connector.",
    "furthermore": "Use 'in addition' or 'we also …'.",
    "leverage": "Replace with 'use' or 'apply'.",
    "robust": "Replace with a quantitative descriptor where possible.",
    "comprehensive": "Replace with a specific scope ('covering N samples …').",
    "tapestry": "Remove; use plain technical language.",
    "intricate": "Replace with 'multi-step' or remove.",
}


def _suggest_for(marker: str, bank: dict[str, str], default: str) -> str:
    key = (marker or "").lower().strip()
    for term, advice in bank.items():
        if term in key:
            return advice
    return default


# ---------------------------------------------------------------------------
# Dimension scorers
# ---------------------------------------------------------------------------
def score_journal_compliance(
    *,
    full_text: str,
    abstract_text: str,
    reference_count: int,
    article_type: str,
    spec_key: str,
    submission_check_fn,
    fallback_limits: dict,
) -> dict[str, Any]:
    """Wrap check_submission_readiness into a 0-100 score."""
    try:
        result = submission_check_fn(
            spec_key=spec_key,
            article_type=article_type,
            full_text=full_text,
            abstract_text=abstract_text,
            reference_count=reference_count,
            fallback_limits=fallback_limits,
        )
    except Exception as exc:
        return {
            "score": 50, "verdict": "warn",
            "summary": f"Format check unavailable: {exc}",
            "issues": [],
        }

    status = (result or {}).get("overall_status", "WARN").upper()
    issues = []
    for chk in (result or {}).get("checklist", []):
        st = (chk.get("status") or "").upper()
        if st in ("FAIL", "WARN"):
            issues.append({
                "label": chk.get("label") or chk.get("rule_id") or chk.get("name") or "check",
                "status": st.lower(),
                "detail": chk.get("message") or chk.get("detail") or "",
            })

    if status == "PASS":
        score = 100 if not issues else 92
    elif status == "WARN":
        score = 70
    else:
        score = 45
    score = max(0, score - 5 * len([i for i in issues if i["status"] == "fail"]))

    return {
        "score": score, "verdict": _verdict_from_score(score),
        "summary": f"{status.upper()} · {len(issues)} item(s) flagged",
        "issues": issues[:10],
        "raw": result,
    }


def score_style_match(
    *,
    full_text: str,
    exemplar_texts: list[str],
    openai_client: Any | None,
) -> dict[str, Any]:
    """
    Run plagiarism-style overlap; INVERT the verdict so that mild overlap
    is "matches journal cadence" but heavy overlap is still flagged.
    """
    if not exemplar_texts:
        return {
            "score": 70, "verdict": "warn",
            "summary": "No exemplars loaded for this journal — style match unknown.",
            "issues": [],
        }

    try:
        pl = check_plagiarism_vs_exemplars(
            full_text[:6000],
            exemplar_texts,
            openai_client=openai_client,
        )
    except Exception as exc:
        return {
            "score": 60, "verdict": "warn",
            "summary": f"Style match unavailable: {exc}",
            "issues": [],
        }

    sim = pl.get("max_embedding_similarity") or 0.0
    ngram = pl.get("max_ngram_overlap") or 0.0
    pl_verdict = pl.get("verdict", "pass")

    # Score peaks when embedding sim is in a healthy band (~0.45–0.65)
    # No exemplar embedding available (openai client missing) → use n-gram only.
    if sim == 0.0 and not pl.get("max_embedding_similarity"):
        # n-gram only: low overlap (0.05–0.25) is healthy, > 0.35 starts to copy
        if ngram > 0.35:
            style_band_score = 50
        elif ngram > 0.25:
            style_band_score = 72
        else:
            style_band_score = 88
    else:
        style_band_score = 100 - min(100, 200 * abs(sim - 0.55))

    if pl_verdict == "fail":
        style_band_score = min(style_band_score, 45)
    elif pl_verdict == "warn":
        style_band_score = min(style_band_score, 70)

    summary = (
        f"Embedding similarity {sim:.2f} · n-gram overlap {ngram:.2f} · "
        f"safety verdict: {pl_verdict}"
    )
    score = round(style_band_score)
    return {
        "score": score, "verdict": _verdict_from_score(score),
        "summary": summary,
        "issues": [pl.get("flagged_excerpt")] if pl.get("flagged_excerpt") else [],
        "details": {"embedding_sim": sim, "ngram_overlap": ngram, "pl_verdict": pl_verdict},
    }


def score_ai_tone(
    *,
    full_text: str,
    sections: list[dict] | None = None,
) -> dict[str, Any]:
    out = check_ai_tone_markers(full_text)
    count = int(out.get("ai_marker_count", 0))
    verdict_raw = out.get("verdict", "pass")
    wc = max(1, _word_count(full_text))
    rate = count / wc * 1000  # markers per 1000 words
    score = max(0, min(100, round(100 - rate * 20)))
    if verdict_raw == "fail":
        score = min(score, 50)
    elif verdict_raw == "warn":
        score = min(score, 75)
    markers = out.get("ai_markers_found", [])

    # Locate each marker in the text → attach section + sentence + suggestion
    evidence = []
    seen_offsets: set[int] = set()
    for marker in markers[:20]:
        # find first occurrence of the marker phrase (case-insensitive)
        m = re.search(re.escape(marker), full_text, re.IGNORECASE)
        if not m or m.start() in seen_offsets:
            continue
        seen_offsets.add(m.start())
        sentence = _sentence_around(full_text, m.start())
        evidence.append({
            "marker": marker,
            "sentence": sentence,
            "section": _section_of(sections, sentence),
            "suggestion": _suggest_for(
                marker, _SUGGESTIONS_AI_TONE,
                "Replace AI-marker phrasing with plain scientific wording.",
            ),
        })

    return {
        "score": score, "verdict": _verdict_from_score(score),
        "summary": f"{count} AI-marker phrase(s) per {wc} words ({rate:.2f}/1k)",
        "issues": markers[:12],
        "evidence": evidence,
    }


def score_repetition(*, sections: list[dict]) -> dict[str, Any]:
    """Count repeated 4-grams across the whole manuscript."""
    combined = " ".join((s.get("text") or "") for s in sections).lower()
    words = re.findall(r"\b[a-z][a-z\-']{2,}\b", combined)
    if len(words) < 80:
        return {"score": 90, "verdict": "pass",
                "summary": "Text too short to evaluate repetition.",
                "issues": [], "evidence": []}

    n = 4
    counts: dict[str, int] = {}
    for i in range(len(words) - n + 1):
        gram = " ".join(words[i:i + n])
        counts[gram] = counts.get(gram, 0) + 1

    repeated = [(g, c) for g, c in counts.items() if c >= 3]
    repeated.sort(key=lambda x: -x[1])
    total = max(1, len(counts))
    repeat_rate = sum(c for _, c in repeated) / total
    score = max(0, min(100, round(100 - repeat_rate * 600)))
    issues = [{"phrase": g, "count": c} for g, c in repeated[:12]]

    # Evidence: locate first occurrence of each repeated 4-gram in section text
    evidence = []
    for gram, c in repeated[:8]:
        for sec in sections:
            body = sec.get("text") or ""
            m = re.search(re.escape(gram), body, re.IGNORECASE)
            if m:
                sentence = _sentence_around(body, m.start())
                evidence.append({
                    "marker": gram,
                    "count": c,
                    "sentence": sentence,
                    "section": sec.get("key"),
                    "suggestion": f"This 4-word phrase appears {c}×. Vary phrasing across paragraphs.",
                })
                break
    return {
        "score": score, "verdict": _verdict_from_score(score),
        "summary": f"{len(repeated)} 4-gram(s) appear ≥3× (rate {repeat_rate:.3f})",
        "issues": issues,
        "evidence": evidence,
    }


def score_subjective_language(
    *,
    full_text: str,
    sections: list[dict] | None = None,
) -> dict[str, Any]:
    matches = list(SUBJECTIVE_RE.finditer(full_text or ""))
    n = len(matches)
    wc = max(1, _word_count(full_text))
    rate = n / wc * 1000  # hits per 1000 words
    score = max(0, min(100, round(100 - rate * 10)))

    samples = []
    evidence = []
    for m in matches[:15]:
        marker = m.group(0)
        start = max(0, m.start() - 30)
        end = min(len(full_text), m.end() + 30)
        samples.append(full_text[start:end].replace("\n", " ").strip())
        sentence = _sentence_around(full_text, m.start())
        evidence.append({
            "marker": marker,
            "sentence": sentence,
            "section": _section_of(sections, sentence),
            "suggestion": _suggest_for(
                marker, _SUGGESTIONS_SUBJECTIVE,
                "Remove or replace with a data-anchored, neutral statement.",
            ),
        })
    return {
        "score": score, "verdict": _verdict_from_score(score),
        "summary": f"{n} subjective marker(s) per {wc} words ({rate:.2f}/1k)",
        "issues": samples,
        "evidence": evidence,
    }


def score_logic_grounding(
    *,
    sections: list[dict],
    full_text: str,
) -> dict[str, Any]:
    """
    Heuristic: count strong claims and check if each is followed (within 200
    chars) by an inline citation or numeric anchor. Returns ungrounded claims.
    """
    ungrounded = []
    evidence: list[dict] = []
    grounded = 0
    total = 0
    for sec in sections:
        text = sec.get("text") or ""
        for m in STRONG_CLAIM_RE.finditer(text):
            total += 1
            window = text[m.start():m.start() + 250]
            if _has_citation_or_data_anchor(window):
                grounded += 1
            else:
                phrase = text[max(0, m.start() - 20):m.end() + 100].strip().replace("\n", " ")
                ungrounded.append({
                    "section": sec.get("key"),
                    "phrase": phrase,
                })
                if len(evidence) < 10:
                    evidence.append({
                        "marker": m.group(0),
                        "sentence": _sentence_around(text, m.start()),
                        "section": sec.get("key"),
                        "suggestion": (
                            "Anchor this claim: cite a supporting reference "
                            "(e.g., [Smith 2020]) or add quantitative evidence "
                            "(p-value, n, effect size)."
                        ),
                    })
    if total == 0:
        return {"score": 90, "verdict": "pass",
                "summary": "No strong claims detected.",
                "issues": [], "evidence": []}
    ratio = grounded / total
    score = round(ratio * 100)
    return {
        "score": score, "verdict": _verdict_from_score(score),
        "summary": f"{grounded}/{total} strong claims have a citation or data anchor",
        "issues": ungrounded[:12],
        "evidence": evidence,
    }


def score_reference_integrity(
    *,
    reference_list: list[str],
    max_verify: int = 12,
    timeout_per_ref: float = 4.0,
) -> dict[str, Any]:
    """
    Reverse-fetch each reference's PMID/DOI from PubMed/Crossref and tally
    success rate. Only the first `max_verify` are checked to keep latency low.
    """
    if not reference_list:
        return {
            "score": 60, "verdict": "warn",
            "summary": "No references provided — cannot verify integrity.",
            "issues": [],
        }

    try:
        from .references.pubmed_client import fetch_by_pmid
    except Exception as exc:
        return {
            "score": 70, "verdict": "warn",
            "summary": f"PubMed client unavailable: {exc}",
            "issues": [],
        }

    ok = 0
    fail = []
    checked = 0
    for ref in reference_list[:max_verify]:
        m = re.search(r"PMID[:\s]*(\d{4,9})", ref) or re.search(r"\b(\d{7,9})\b", ref)
        if not m:
            fail.append({"ref": ref[:140], "reason": "no PMID parsed"})
            continue
        pmid = m.group(1)
        checked += 1
        try:
            t0 = time.time()
            rec = fetch_by_pmid(pmid)
            if time.time() - t0 > timeout_per_ref:
                fail.append({"ref": ref[:140], "pmid": pmid, "reason": "slow PubMed"})
                continue
            if rec is None:
                fail.append({"ref": ref[:140], "pmid": pmid, "reason": "not found"})
            else:
                ok += 1
        except Exception as exc:
            fail.append({"ref": ref[:140], "pmid": pmid, "reason": f"error: {exc}"})

    total = max(1, checked + len([f for f in fail if "no PMID" in f.get("reason", "")]))
    ratio = ok / total
    score = round(ratio * 100)
    return {
        "score": score, "verdict": _verdict_from_score(score),
        "summary": f"{ok}/{total} references verified via PubMed",
        "issues": fail[:10],
        "checked_subset": min(len(reference_list), max_verify),
        "total_refs": len(reference_list),
    }


def score_fill_marker_residual(
    *,
    full_text: str,
    sections: list[dict] | None = None,
) -> dict[str, Any]:
    """Gate check: any remaining [FILL: ...] placeholder means the manuscript
    is incomplete and cannot be submitted. Returns FAIL if any found."""
    markers = _FILL_RE.findall(full_text or "")
    unique = sorted(set(markers))
    n = len(markers)
    score = 0 if n > 0 else 100

    # Evidence: locate every distinct placeholder + which section it's in
    evidence = []
    for marker in unique[:25]:
        sec_key = None
        sentence = ""
        for sec in (sections or []):
            body = sec.get("text") or ""
            idx = body.find(marker)
            if idx >= 0:
                sec_key = sec.get("key")
                sentence = _sentence_around(body, idx)
                break
        evidence.append({
            "marker": marker,
            "section": sec_key,
            "sentence": sentence,
            "suggestion": (
                "Replace this placeholder with the actual value before submission "
                "(e.g., catalog number, dose, protocol ID)."
            ),
        })

    return {
        "score": score,
        "verdict": "fail" if n > 0 else "pass",
        "summary": (
            f"{n} [FILL: ...] placeholder(s) remain — replace before submission."
            if n > 0 else "No unfilled placeholders detected."
        ),
        "issues": unique[:20],
        "evidence": evidence,
        "is_hard_gate": True,
    }


def _cosine(a: list[float], b: list[float]) -> float:
    """Cosine similarity of two equal-length float vectors."""
    if not a or not b or len(a) != len(b):
        return 0.0
    dot = 0.0; na = 0.0; nb = 0.0
    for x, y in zip(a, b):
        dot += x * y; na += x * x; nb += y * y
    if na <= 0.0 or nb <= 0.0:
        return 0.0
    import math
    return dot / (math.sqrt(na) * math.sqrt(nb))


def _embed_batch(openai_client: Any, texts: list[str], model: str = "text-embedding-3-small") -> list[list[float]] | None:
    """Batch-embed a list of strings via OpenAI. Returns None on any failure."""
    try:
        # OpenAI v1.x SDK
        resp = openai_client.embeddings.create(model=model, input=texts)
        return [d.embedding for d in resp.data]
    except Exception:
        return None


def score_reference_relevance(
    *,
    reference_list: list[str],
    abstract_text: str,
    openai_client: Any | None = None,
) -> dict[str, Any]:
    """Check semantic relevance of reference titles to the manuscript abstract.

    Two scoring modes (mode is reported in summary):
    - **embedding** (preferred): cosine similarity of (abstract embedding) vs (each ref title embedding) via OpenAI text-embedding-3-small. Far more accurate than lexical overlap.
    - **lexical fallback**: Jaccard / overlap-ratio over content words.

    Per ref:
      - if embedding cosine ≥ 0.55 → fully relevant (score 1.0)
      - if 0.40-0.55                → moderately relevant (linearly scaled)
      - if < 0.40                   → low relevance (flagged in evidence)
    """
    if not reference_list:
        return {
            "score": 50, "verdict": "warn",
            "summary": "No references to evaluate.",
            "issues": [],
        }
    if not abstract_text or len(abstract_text) < 30:
        return {
            "score": 60, "verdict": "warn",
            "summary": "Abstract too short for relevance check.",
            "issues": [],
        }

    # Tokenise abstract to a set of significant words (>3 chars, not stopwords)
    _STOP = {
        "the","and","for","with","from","that","this","are","was","were","have",
        "has","been","into","its","their","they","also","can","not","but","our",
        "these","those","which","when","then","than","each","both","more","such",
    }

    def content_words(text: str) -> set[str]:
        return {
            w.lower() for w in re.findall(r"[A-Za-z]{4,}", text)
            if w.lower() not in _STOP
        }

    abs_words = content_words(abstract_text)

    def _ref_title_snippet(ref: str) -> str:
        # Heuristic: title is usually before the journal name or the year.
        # Take the first 180 chars, drop leading numbering like "1. " or "[1] ".
        s = re.sub(r"^\s*\[?\d+\]?\.?\s*", "", ref).strip()
        return s[:200]

    scores_per_ref: list[float] = []
    low_relevance: list[str] = []
    evidence: list[dict] = []
    mode = "lexical"

    titles = [_ref_title_snippet(ref) for ref in reference_list]

    # ── Try embedding mode first ─────────────────────────────────────
    embeddings_used = False
    if openai_client is not None:
        all_vecs = _embed_batch(openai_client, [abstract_text] + titles)
        if all_vecs and len(all_vecs) == 1 + len(titles):
            embeddings_used = True
            mode = "embedding"
            abs_vec = all_vecs[0]
            for ref, title, ref_vec in zip(reference_list, titles, all_vecs[1:]):
                sim = _cosine(abs_vec, ref_vec)
                if sim >= 0.55:
                    norm = 1.0
                elif sim >= 0.40:
                    norm = 0.5 + (sim - 0.40) * (0.5 / 0.15)  # 0.40 → 0.5, 0.55 → 1.0
                else:
                    norm = max(0.0, sim / 0.40 * 0.5)  # 0 → 0.0, 0.40 → 0.5
                scores_per_ref.append(norm)
                if norm < 0.5:
                    low_relevance.append(ref[:120])
                    evidence.append({
                        "marker": ref[:120],
                        "sentence": title,
                        "section": "references",
                        "score": round(norm * 100),
                        "embedding_cosine": round(sim, 3),
                        "suggestion": (
                            f"Low semantic similarity (cosine {sim:.2f} < 0.40). Either: "
                            "(a) replace with a more directly relevant paper, "
                            "(b) cite only in a tangential paragraph, "
                            "or (c) re-run /insert_citations with sharper keywords."
                        ),
                    })

    # ── Lexical fallback (when no OpenAI client OR embedding call failed) ──
    if not embeddings_used:
        for ref, title in zip(reference_list, titles):
            ref_words = content_words(title)
            if not ref_words:
                scores_per_ref.append(0.5)
                continue
            intersection = abs_words & ref_words
            union = abs_words | ref_words
            jaccard = len(intersection) / max(1, len(union))
            overlap_ratio = len(intersection) / max(1, len(ref_words))
            boosted = min(1.0, max(jaccard * 6, overlap_ratio * 4))
            scores_per_ref.append(boosted)
            if boosted < 0.2:
                low_relevance.append(ref[:120])
                evidence.append({
                    "marker": ref[:120],
                    "sentence": title,
                    "section": "references",
                    "score": round(boosted * 100),
                    "overlap_words": sorted(intersection)[:8],
                    "suggestion": (
                        "Low lexical overlap with abstract. Re-run /insert_citations "
                        "with sharper keywords or replace this reference."
                    ),
                })

    mean_score = sum(scores_per_ref) / max(1, len(scores_per_ref))
    raw_score = round(mean_score * 100)
    # Reference relevance is a soft signal based on word-overlap; short abstracts
    # naturally have low vocabulary overlap even with correct refs.
    # Apply a floor so relevant refs are at worst "warn" (never "fail") unless
    # fewer than 30% of refs have any overlap at all.
    zero_overlap = sum(1 for s in scores_per_ref if s < 0.05)
    completely_off = zero_overlap / max(1, len(scores_per_ref)) > 0.5
    score = max(raw_score, 50) if not completely_off else raw_score
    # Custom verdict: fail only when clearly off-topic (score < 35)
    if score >= SCORE_PASS:
        verdict = "pass"
    elif score >= 35:
        verdict = "warn"
    else:
        verdict = "fail"

    pct_low = round(len(low_relevance) / max(1, len(reference_list)) * 100)

    return {
        "score": score,
        "verdict": verdict,
        "summary": (
            f"Mean relevance {mean_score:.2f} across {len(reference_list)} refs "
            f"({mode} mode). {len(low_relevance)} ({pct_low}%) appear loosely related."
        ),
        "issues": low_relevance[:8],
        "evidence": evidence[:10],
        "scoring_mode": mode,
    }


def score_grammar_correctness(
    *,
    full_text: str,
    claude_call_fn: Any | None = None,
) -> dict[str, Any]:
    """Estimate grammar quality via Claude or a fast heuristic.

    When *claude_call_fn* is supplied: sample up to 800 words and ask Claude
    to count grammar errors. Otherwise fall back to a simple heuristic
    (repeated words, double spaces, sentence-final comma, etc.).
    """
    if not full_text or len(full_text.strip()) < 100:
        return {
            "score": 80, "verdict": "pass",
            "summary": "Text too short to evaluate grammar.",
            "issues": [],
        }

    # --- Heuristic path (always run; Claude path is additive) ---
    heuristic_issues: list[str] = []

    # Double words ("the the")
    for m in re.finditer(r"\b(\w{3,})\s+\1\b", full_text, re.IGNORECASE):
        heuristic_issues.append(f"Repeated word: '{m.group()}'")

    # Missing space after period (e.g. "cell.The")
    for m in re.finditer(r"[a-z]\.[A-Z][a-z]", full_text):
        heuristic_issues.append(f"Missing space: '…{full_text[max(0,m.start()-5):m.end()+5]}…'")

    # Sentence-final comma before period ("result, .")
    for m in re.finditer(r",\s*\.", full_text):
        heuristic_issues.append(f"Comma before period at offset {m.start()}")

    # Numbers without spaces before common units ("5ml", "37C", "100ug")
    UNIT_RE = re.compile(r"\b\d+(?:\.\d+)?(ml|ul|ng|ug|mg|kg|nm|um|mm|cm|°C|kDa|Da|bp|kb|rpm|min|sec|hr)\b", re.IGNORECASE)
    for m in UNIT_RE.finditer(full_text):
        val = m.group()
        if re.search(r"\d[A-Za-z]", val):
            heuristic_issues.append(f"Possible missing space: '{val}'")

    h_count = len(heuristic_issues)

    # --- Claude path ---
    claude_errors: list[str] = []
    if claude_call_fn is not None:
        sample = full_text[:3000]  # ~800 words, keeps cost low
        prompt = (
            "Review the following scientific manuscript excerpt for GRAMMAR errors only. "
            "List up to 10 grammar issues as brief JSON array of strings. "
            "Ignore style preferences. Return only the JSON array, no other text.\n\n"
            + sample
        )
        try:
            raw = claude_call_fn(prompt)
            parsed = json.loads(re.sub(r"^```.*?\n|```$", "", raw.strip(), flags=re.S))
            if isinstance(parsed, list):
                claude_errors = [str(x) for x in parsed[:10]]
        except Exception:
            pass  # fall back to heuristic only

    total_issues = heuristic_issues + claude_errors
    total_count = len(total_issues)

    wc = max(1, _word_count(full_text))
    rate = total_count / wc * 1000
    score = max(0, min(100, round(100 - rate * 15)))

    return {
        "score": score,
        "verdict": _verdict_from_score(score),
        "summary": (
            f"{total_count} grammar issue(s) detected "
            f"({h_count} heuristic"
            + (f", {len(claude_errors)} Claude" if claude_errors else "")
            + f") per {wc} words."
        ),
        "issues": total_issues[:12],
    }


def score_novelty_support(
    *,
    plan_novelty_points: list[dict] | None,
    full_text: str,
) -> dict[str, Any]:
    """Check that each novelty/innovation claim in the plan is anchored by
    either an inline citation or a [CITE: ...] placeholder in the full text.

    Intended to flag "we are the first to show X" claims that lack any
    supporting (or contrasting) citation nearby.
    """
    if not plan_novelty_points:
        # No plan available — fall back to scanning text for "first time / novel" phrases
        novel_re = re.compile(
            r"\b(?:for\s+the\s+first\s+time|first\s+to\s+show|novel\s+(?:approach|finding|model|tool)|"
            r"previously\s+unreported|hitherto\s+unknown)\b",
            re.IGNORECASE,
        )
        hits = list(novel_re.finditer(full_text or ""))
        if not hits:
            return {
                "score": 85, "verdict": "pass",
                "summary": "No novelty claims detected without plan context.",
                "issues": [],
            }
        unsupported = []
        for m in hits:
            window = full_text[m.start(): m.start() + 300]
            has_cite = _has_citation_or_data_anchor(window)
            if not has_cite:
                unsupported.append(
                    full_text[max(0, m.start() - 20): m.end() + 120].strip()
                )
        n = len(unsupported)
        score = max(0, 100 - n * 20)
        return {
            "score": score,
            "verdict": _verdict_from_score(score),
            "summary": (
                f"{n}/{len(hits)} novelty claim(s) lack a citation anchor. "
                "(Plan not available — scanning text only.)"
            ),
            "issues": unsupported[:8],
        }

    unsupported: list[str] = []
    for np_item in plan_novelty_points:
        point = np_item.get("point") or ""
        if not point:
            continue
        # Look for key words from the novelty point in the text
        keywords = [w.lower() for w in re.findall(r"[A-Za-z]{5,}", point)][:5]
        # Find the passage in full_text that mentions those keywords
        found_passage = ""
        for kw in keywords:
            idx = full_text.lower().find(kw)
            if idx >= 0:
                found_passage = full_text[idx: idx + 350]
                break
        if not found_passage:
            unsupported.append(f"Claim not found in text: {point[:100]}")
            continue
        has_cite = _has_citation_or_data_anchor(found_passage)
        if not has_cite:
            unsupported.append(
                f"No citation near novelty claim — '{point[:80]}...'"
            )

    n_total = len(plan_novelty_points)
    n_bad = len(unsupported)
    score = round((1 - n_bad / max(1, n_total)) * 100)
    return {
        "score": score,
        "verdict": _verdict_from_score(score),
        "summary": (
            f"{n_total - n_bad}/{n_total} novelty claim(s) have a citation anchor."
        ),
        "issues": unsupported[:8],
    }


# ---------------------------------------------------------------------------
# Aggregation
# ---------------------------------------------------------------------------

# fill_marker_residual is a hard gate — not included in weighted average
# but always forces overall_verdict to "fail" when score < 100.
DIMENSION_WEIGHTS = {
    "journal_compliance":  0.18,
    "style_match":         0.10,
    "ai_tone":             0.14,
    "repetition":          0.08,
    "logic_grounding":     0.14,
    "reference_integrity": 0.12,
    "subjective_language": 0.08,
    "reference_relevance": 0.10,
    "grammar_correctness": 0.06,
    # novelty_support is advisory only (plan may not always be present)
}


def aggregate(dimensions: dict[str, dict[str, Any]]) -> dict[str, Any]:
    """Compute weighted overall score + verdict.

    fill_marker_residual is a HARD GATE: if it fails (score < 100), the
    overall verdict is forced to "fail" regardless of other scores.
    novelty_support is ADVISORY: contributes to score but not to verdict gate.
    """
    total_w = 0.0
    total_s = 0.0
    for k, w in DIMENSION_WEIGHTS.items():
        d = dimensions.get(k)
        if not d:
            continue
        total_w += w
        total_s += w * float(d.get("score", 0))
    overall = round(total_s / max(0.001, total_w))

    fails = [k for k, v in dimensions.items() if v.get("verdict") == "fail"]
    warns = [k for k, v in dimensions.items() if v.get("verdict") == "warn"]

    # Hard gate: any unfilled placeholder → always fail
    fill_dim = dimensions.get("fill_marker_residual")
    hard_gate_fail = fill_dim is not None and fill_dim.get("score", 100) < 100

    if hard_gate_fail or (fails and "fill_marker_residual" not in fails):
        # Ensure fill gate appears in fails list
        if hard_gate_fail and "fill_marker_residual" not in fails:
            fails = ["fill_marker_residual"] + [f for f in fails if f != "fill_marker_residual"]
    if fails or hard_gate_fail or overall < SCORE_WARN:
        verdict = "fail"
    elif warns or overall < SCORE_PASS:
        verdict = "warn"
    else:
        verdict = "pass"

    return {
        "overall_score": overall,
        "overall_verdict": verdict,
        "dimensions_failed": fails,
        "dimensions_warned": warns,
        "hard_gate_triggered": hard_gate_fail,
    }
