"""
Journal Context Builder — v15.44 (B1)

Produces a single <journal_context> block ready to inject as `extra_system`
into Claude calls (rewrite / reduce_ai_tone / draft_section).

Reads from three sources, lazily and cached:

    1. journal_profiles/{key}.json
         → hedge level, opening style, preferred verbs
    2. journal_profiles/{key}.section_phrases.json  (optional, populated by A1)
         → per-section opening / transition / limitation phrases
    3. journal_specs/specs/{key}.json
         → reference_style_id  → citation_format_rule
         → reference_limit       → reference_limit_total

Plus one hard constant inlined from style_safety.AI_MARKER_PHRASES:

    → forbidden_phrases  (B4 will move this to a stronger front-of-prompt slot)

Design rules
------------
- Pure-Python, no LLM call.
- Tolerant: if any file is missing or malformed, the block degrades
  gracefully (returns a shorter block or an empty string).
- Caching: file reads are cached at import-time and on first access;
  reload requires process restart (acceptable — these files are static
  release artefacts).
- The function NEVER raises — it returns "" on any unexpected failure,
  so calling code can always do `extra_system = build_journal_context_block(...)`
  without try/except.
"""

from __future__ import annotations

import json
import os
import threading
from pathlib import Path
from typing import Any

from .style_safety import AI_MARKER_PHRASES

# ---------------------------------------------------------------------------
# Paths
# ---------------------------------------------------------------------------

_HERE = Path(__file__).resolve().parent
_PROFILES_DIR = Path(
    os.environ.get("WM_PROFILES_DIR", str(_HERE / "journal_profiles"))
)
_SPECS_DIR = _HERE / "journal_specs" / "specs"

# ---------------------------------------------------------------------------
# Caches (filled lazily — protected by lock for thread-safety under uvicorn workers)
# ---------------------------------------------------------------------------

_LOCK = threading.Lock()
_PROFILE_CACHE: dict[str, dict[str, Any] | None] = {}
_PHRASE_CACHE:  dict[str, dict[str, Any] | None] = {}
_SPEC_CACHE:    dict[str, dict[str, Any] | None] = {}


def _safe_load(path: Path) -> dict[str, Any] | None:
    """Return parsed JSON or None on any error. Never raises."""
    try:
        if not path.exists():
            return None
        return json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError, UnicodeDecodeError):
        return None


def _profile(key: str) -> dict[str, Any] | None:
    if key in _PROFILE_CACHE:
        return _PROFILE_CACHE[key]
    with _LOCK:
        data = _safe_load(_PROFILES_DIR / f"{key}.json")
        _PROFILE_CACHE[key] = data
        return data


def _phrases(key: str) -> dict[str, Any] | None:
    if key in _PHRASE_CACHE:
        return _PHRASE_CACHE[key]
    with _LOCK:
        data = _safe_load(_PROFILES_DIR / f"{key}.section_phrases.json")
        _PHRASE_CACHE[key] = data
        return data


def _spec(key: str) -> dict[str, Any] | None:
    if key in _SPEC_CACHE:
        return _SPEC_CACHE[key]
    with _LOCK:
        data = _safe_load(_SPECS_DIR / f"{key}.json")
        _SPEC_CACHE[key] = data
        return data


# ---------------------------------------------------------------------------
# Citation-format mapping (B2 preview — minimal version inlined here so
#   B1 can show divergence; B2 may expand the rule text per article_type).
# ---------------------------------------------------------------------------

_CITATION_RULES: dict[str, str] = {
    "nature_superscript":
        "NUMBERED SUPERSCRIPT only (¹²,³ after punctuation). "
        "Keep placeholders as `[CITE: <topic>]`. "
        "FORBIDDEN in prose: `(Smith 2024)`, `(Smith et al., 2020)`, bare `[1]` before resolution.",
    "cell_numbered":
        "NUMBERED square brackets `[1]` only. "
        "Keep placeholders as `[CITE: <topic>]`. "
        "FORBIDDEN: author-year `(Smith 2024)` form.",
    "science_numbered":
        "NUMBERED round parentheses `(1)` only. "
        "Keep placeholders as `[CITE: <topic>]`. "
        "FORBIDDEN: author-year form.",
    "lancet_numbered_vancouver":
        "Vancouver NUMBERED `[1]`; list ordered by first citation. "
        "Keep placeholders as `[CITE: <topic>]`. "
        "FORBIDDEN: author-year form.",
    "nejm_numbered_vancouver":
        "NEJM Vancouver — SUPERSCRIPT numbers in text. "
        "Keep placeholders as `[CITE: <topic>]`. "
        "FORBIDDEN: author-year `(Smith 2024)` form.",
    "pnas_numbered":
        "PNAS NUMBERED `(1)` in parentheses. "
        "Keep placeholders as `[CITE: <topic>]`. "
        "FORBIDDEN: author-year form.",
    "plos_vancouver":
        "PLOS Vancouver NUMBERED `[1]`; list by appearance. "
        "Keep placeholders as `[CITE: <topic>]`. "
        "FORBIDDEN: author-year form.",
    "elife_author_year":
        "AUTHOR-YEAR only: `(Smith 2024)`, `(Smith and Jones 2024)`, `(Smith et al., 2024)`. "
        "Keep placeholders as `[CITE: <topic>]`. "
        "FORBIDDEN: numbered `[1]`, `[12,13]`, or superscript citation marks.",
}

# B2 — article-type modifiers appended to citation rule
_ARTICLE_TYPE_CITATION_NOTES: dict[str, str] = {
    "research":  "Research article: cite at every strong claim and background gap.",
    "review":    "Review: denser citations in Introduction/Discussion; synthesise prior work.",
    "case_report": "Case report: cite diagnostic criteria and prior cases; Methods lighter.",
    "letter":    "Letter/brief: minimal citations; compressed prose; no lengthy Discussion.",
}


# ---------------------------------------------------------------------------
# Section-key normalisation — journals use different labels
# ---------------------------------------------------------------------------

_SECTION_ALIASES = {
    "intro": "introduction",
    "background": "introduction",
    "result": "results",
    "method": "methods",
    "materials_and_methods": "methods",
    "discuss": "discussion",
    "conclusions": "conclusion",
    "limitations": "discussion",
}


def _normalise_section(s: str | None) -> str | None:
    if not s:
        return None
    s = s.lower().strip()
    return _SECTION_ALIASES.get(s, s)


# ---------------------------------------------------------------------------
# Forbidden phrases — for B4 the front-of-prompt move; for now we inject
# them into the journal_context block.
# ---------------------------------------------------------------------------

def _render_forbidden_phrases() -> str:
    quoted = []
    for p in AI_MARKER_PHRASES:
        # Quote multi-word phrases for readability
        quoted.append(f'"{p}"' if " " in p else p)
    return ", ".join(quoted)


# ---------------------------------------------------------------------------
# Block assembly
# ---------------------------------------------------------------------------

def _phrases_for_section(
    phrases_doc: dict[str, Any] | None,
    section_key: str | None,
) -> dict[str, list[str]]:
    """Return a {slot: [phrases]} dict for the given section, or empty."""
    if not phrases_doc or not section_key:
        return {}
    sec = (phrases_doc.get("sections") or {}).get(section_key)
    if not isinstance(sec, dict):
        return {}
    out: dict[str, list[str]] = {}
    for slot, items in sec.items():
        if isinstance(items, list) and items:
            # Keep only short string entries, max 8 per slot
            cleaned = [str(x).strip() for x in items if isinstance(x, str) and x.strip()]
            if cleaned:
                out[slot] = cleaned[:8]
    return out


def _render_phrases_block(phrases_by_slot: dict[str, list[str]]) -> str:
    if not phrases_by_slot:
        return ""
    lines = []
    for slot, phrases in phrases_by_slot.items():
        lines.append(f"  {slot}:")
        for p in phrases:
            lines.append(f'    - "{p}"')
    return "\n".join(lines)


def build_journal_context_block(
    journal_key: str | None,
    section_key: str | None = None,
    article_type: str = "research",
) -> str:
    """
    Assemble the <journal_context> block. Returns "" if no useful data is
    available (so callers can always do `extra_system = build_journal_context_block(...)`).
    """
    if not journal_key:
        return ""

    key = journal_key.strip().lower()
    if not key or key.startswith("learned:") or key.startswith("user:"):
        # Learned packs handle their own context elsewhere
        return ""

    profile = _profile(key)
    spec = _spec(key)
    phrases_doc = _phrases(key)

    if not profile and not spec and not phrases_doc:
        return ""

    sec_norm = _normalise_section(section_key)
    atype = (article_type or "research").strip().lower()
    lines: list[str] = []

    # ── Header ──
    attrs = [f'journal="{key}"', f'article_type="{atype}"']
    if sec_norm:
        attrs.append(f'section="{sec_norm}"')
    lines.append(f"<journal_context {' '.join(attrs)}>")

    # ── B4: HARD CONSTRAINTS first (model reads top of system prompt) ──
    lines.append("  HARD_CONSTRAINTS (violating any = generation failure):")
    lines.append("  1. FORBIDDEN_PHRASES — never write any of:")
    lines.append(f"     {_render_forbidden_phrases()}")
    lines.append(
        "     Also avoid generic openers: 'In this study, we', 'We set out to', "
        "'We sought to', 'Here, we report that' unless the journal phrase bank "
        "below provides a better opening."
    )

    ref_style = (spec or {}).get("reference_style_id")
    if ref_style and ref_style in _CITATION_RULES:
        lines.append("  2. CITATION_FORMAT (mandatory for this journal):")
        lines.append(f"     id: {ref_style}")
        lines.append(f"     rule: {_CITATION_RULES[ref_style]}")
        atype_note = _ARTICLE_TYPE_CITATION_NOTES.get(atype)
        if atype_note:
            lines.append(f"     article_type_note: {atype_note}")

    lines.append("  3. NO_NEW_REFERENCES — do not invent PMIDs, DOIs, or 'et al.' strings.")
    lines.append("     Use `[CITE: <specific PubMed-searchable topic>]` placeholders only.")

    # ── Style guidance (soft — after hard constraints) ──
    lines.append("  STYLE_GUIDANCE:")

    ref_limit_node = (spec or {}).get("reference_limit") or {}
    if isinstance(ref_limit_node, dict):
        v = ref_limit_node.get("value")
        if isinstance(v, int) and v > 0:
            lines.append(f"    reference_limit_total: {v}")

    rhet = (profile or {}).get("rhetoric_profile") or {}
    rhet_val = rhet.get("value") if isinstance(rhet, dict) and "value" in rhet else rhet
    if isinstance(rhet_val, dict):
        if rhet_val.get("tone"):
            lines.append(f"    hedge_level: {rhet_val['tone']}")
        if rhet_val.get("opening_style"):
            lines.append(f"    opening_style: {rhet_val['opening_style']}")
        verbs = rhet_val.get("top_verbs")
        if isinstance(verbs, list) and verbs:
            lines.append(f"    preferred_verbs: {', '.join(verbs[:8])}")

    claim = (profile or {}).get("claim_strength_profile") or {}
    claim_val = claim.get("value") if isinstance(claim, dict) and "value" in claim else claim
    if isinstance(claim_val, dict):
        pat = claim_val.get("typical_pattern")
        if pat:
            lines.append(f"    typical_claim_pattern: {str(pat).strip().replace(chr(10), ' ')[:200]}")

    sec_phrases = _phrases_for_section(phrases_doc, sec_norm)
    if sec_phrases:
        lines.append(f"    corpus_phrases_{sec_norm} (cadence templates — adapt, do not copy >8 words):")
        lines.append(_render_phrases_block(sec_phrases))

    lines.append("</journal_context>")
    lines.append("")
    lines.append(
        "The HARD_CONSTRAINTS in <journal_context> override all default writing habits. "
        "Match citation format and forbidden-phrase rules before optimising flow."
    )

    return "\n".join(lines)


# ---------------------------------------------------------------------------
# Diagnostics (used by /health and tests)
# ---------------------------------------------------------------------------

def context_diagnostics(journal_key: str) -> dict[str, Any]:
    """Return what data is available for a journal — for health checks."""
    key = (journal_key or "").lower()
    profile = _profile(key)
    spec = _spec(key)
    phrases_doc = _phrases(key)
    sections_with_phrases = []
    if isinstance(phrases_doc, dict):
        sections_with_phrases = sorted((phrases_doc.get("sections") or {}).keys())
    return {
        "journal_key":            key,
        "profile_loaded":         profile is not None,
        "spec_loaded":            spec is not None,
        "phrase_bank_loaded":     phrases_doc is not None,
        "sections_with_phrases":  sections_with_phrases,
        "reference_style_id":     (spec or {}).get("reference_style_id"),
        "forbidden_phrase_count": len(AI_MARKER_PHRASES),
    }
