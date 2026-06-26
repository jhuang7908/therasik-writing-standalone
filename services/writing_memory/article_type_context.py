"""
Article-type deep structure + journal surface constraints.

Loads JSON schemas from schemas/ — no LLM, no YAML dependency.
Inject via build_combined_context_block() into draft_section / plan_paper.
"""
from __future__ import annotations

import json
import re
import threading
from pathlib import Path
from typing import Any

_HERE = Path(__file__).resolve().parent
_SCHEMAS = _HERE / "schemas"
_TYPES_DIR = _SCHEMAS / "article_types"

_LOCK = threading.Lock()
_INDEX_CACHE: dict[str, Any] | None = None
_SURFACE_CACHE: dict[str, Any] | None = None
_TYPE_CACHE: dict[str, dict[str, Any] | None] = {}


def _safe_load(path: Path) -> dict[str, Any] | None:
    try:
        if not path.exists():
            return None
        return json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError, UnicodeDecodeError):
        return None


def _index() -> dict[str, Any]:
    global _INDEX_CACHE
    if _INDEX_CACHE is not None:
        return _INDEX_CACHE
    with _LOCK:
        _INDEX_CACHE = _safe_load(_SCHEMAS / "article_types_index.json") or {}
        return _INDEX_CACHE


def _surface() -> dict[str, Any]:
    global _SURFACE_CACHE
    if _SURFACE_CACHE is not None:
        return _SURFACE_CACHE
    with _LOCK:
        _SURFACE_CACHE = _safe_load(_SCHEMAS / "journal_surface.json") or {}
        return _SURFACE_CACHE


def canonical_article_type(article_type: str | None) -> str:
    """Map legacy aliases (research, review, letter) to canonical type id."""
    raw = (article_type or "original_research").strip().lower()
    idx = _index()
    aliases = idx.get("aliases") or {}
    canonical = aliases.get(raw, raw)
    allowed = set(idx.get("canonical_types") or [])
    if allowed and canonical not in allowed:
        return "original_research"
    return canonical


def list_article_types() -> dict[str, Any]:
    idx = _index()
    return {
        "version": idx.get("version"),
        "canonical_types": idx.get("canonical_types") or [],
        "aliases": idx.get("aliases") or {},
        "priority_implemented": idx.get("priority_implemented") or [],
    }


def _type_schema(canonical: str) -> dict[str, Any] | None:
    if canonical in _TYPE_CACHE:
        return _TYPE_CACHE[canonical]
    with _LOCK:
        data = _safe_load(_TYPES_DIR / f"{canonical}.json")
        _TYPE_CACHE[canonical] = data
        return data


def _journal_surface(journal_key: str | None) -> dict[str, Any]:
    if not journal_key:
        return {}
    key = journal_key.strip().lower()
    journals = (_surface().get("journals") or {})
    return journals.get(key) or journals.get("generic") or {}


def _render_abstract_rules(surface: dict[str, Any], type_schema: dict[str, Any]) -> list[str]:
    lines: list[str] = []
    fmt = surface.get("abstract_format") or "single_paragraph"
    words = surface.get("abstract_words") or {}
    wmin, wmax = words.get("min"), words.get("max")

    if fmt == "bmrc_subheadings":
        subs = surface.get("abstract_subheadings") or [
            "Background", "Methods", "Results", "Conclusion"
        ]
        lines.append(
            f"    ABSTRACT_FORMAT: mandatory labeled sub-paragraphs: "
            + " / ".join(subs) + " (each on its own line with label + colon)."
        )
        lines.append("    No inline citations in Background or Conclusion.")
        abs_logic = (type_schema.get("abstract") or {})
        if abs_logic.get("mechanism_required"):
            lines.append(
                f"    End Conclusion with mechanistic insight: "
                f"{abs_logic.get('mechanism_template', 'one non-obvious biological conclusion')}."
            )
        ex = (type_schema.get("exemplar_patterns") or {}).get("abstract_bmrc")
        if isinstance(ex, dict):
            for label, hint in ex.items():
                if label != "note":
                    lines.append(f"    Pattern — {label}: {hint}")
    elif fmt == "structured":
        subs = surface.get("abstract_subheadings") or []
        lines.append(f"    ABSTRACT_FORMAT: structured subheadings: {', '.join(subs)}.")
    else:
        lines.append(
            "    ABSTRACT_FORMAT: single continuous paragraph (no subheadings); "
            "implicit order: background → approach → findings → conclusion."
        )

    if wmin and wmax:
        lines.append(f"    ABSTRACT_LENGTH: {wmin}–{wmax} words.")
    if surface.get("significance_statement"):
        sw = surface.get("significance_words") or {}
        lines.append(
            f"    Also produce a separate Significance Statement "
            f"({sw.get('min', 100)}–{sw.get('max', 120)} words) if requested."
        )
    return lines


def _render_section_rules(
    sec: str,
    type_schema: dict[str, Any],
) -> list[str]:
    lines: list[str] = []
    intro = type_schema.get("introduction") or {}
    results = type_schema.get("results") or {}
    discussion = type_schema.get("discussion") or {}
    methods = type_schema.get("methods") or {}
    exemplars = type_schema.get("exemplar_patterns") or {}

    if sec == "introduction" and intro:
        flow = intro.get("flow") or []
        if flow:
            lines.append("    INTRODUCTION_FUNNEL (one paragraph each):")
            for i, step in enumerate(flow, 1):
                lines.append(f"      {i}. {step}")
        forbidden = intro.get("forbidden_openers") or []
        if forbidden:
            lines.append(f"    Forbidden openers: {', '.join(forbidden)}")
        if intro.get("citation_density"):
            lines.append(f"    Citation density: {intro['citation_density']}")

    if sec == "results" and results:
        if results.get("subsection_pattern"):
            lines.append(f"    RESULTS_STRUCTURE: {results['subsection_pattern']}")
        per = results.get("per_finding") or []
        for p in per:
            lines.append(f"      - {p}")
        forbidden = results.get("forbidden_closers") or []
        if forbidden:
            lines.append(f"    Forbidden closers: {', '.join(forbidden)}")
        if exemplars.get("results_sentence"):
            lines.append(f"    Sentence pattern (adapt): {exemplars['results_sentence']}")

    if sec == "discussion" and discussion:
        if discussion.get("open_with"):
            lines.append(f"    DISCUSSION_OPEN: {discussion['open_with']}")
        if discussion.get("open_template"):
            lines.append(f"    {discussion['open_template']}")
        if discussion.get("compare_to_prior_models_by_name"):
            lines.append(
                "    Name prior models explicitly when contrasting (e.g. NSG-SGM3 vs this model)."
            )
        if discussion.get("clinical_implication_paragraph"):
            lines.append("    Include a short clinical/translation implication paragraph.")
        if exemplars.get("discussion_opener"):
            lines.append(f"    Opener pattern (adapt): {exemplars['discussion_opener']}")

    if sec == "methods" and methods:
        if methods.get("emphasis"):
            lines.append(f"    METHODS_EMPHASIS: {methods['emphasis']}")
        if exemplars.get("methods_opener"):
            lines.append(f"    Opener pattern: {exemplars['methods_opener']}")

    targets = type_schema.get("word_targets_default") or {}
    if sec in targets:
        lines.append(f"    SECTION_WORD_TARGET_DEFAULT: {targets[sec]} words (override if user sets section_word_target).")

    return lines


def build_article_type_context_block(
    article_type: str | None,
    section_key: str | None = None,
    journal_key: str | None = None,
) -> str:
    """Return <article_type_context> XML block for prompt injection."""
    canonical = canonical_article_type(article_type)
    schema = _type_schema(canonical)
    if not schema:
        return ""

    sec = (section_key or "").strip().lower()
    sec_aliases = {
        "intro": "introduction",
        "background": "introduction",
        "result": "results",
        "method": "methods",
        "discuss": "discussion",
    }
    sec = sec_aliases.get(sec, sec)

    surface = _journal_surface(journal_key)
    lines: list[str] = [
        f'<article_type_context type="{canonical}" display="{schema.get("display", canonical)}">',
        "  DEEP_STRUCTURE (content from user data only; patterns are cadence templates):",
    ]

    if sec == "abstract" or not sec:
        abs_rules = _render_abstract_rules(surface, schema)
        lines.extend(abs_rules if abs_rules else [])

    if sec:
        sec_rules = _render_section_rules(sec, schema)
        if sec_rules:
            lines.append(f"  SECTION_RULES section=\"{sec}\":")
            lines.extend(sec_rules)

    if not sec:
        required = schema.get("sections_required") or []
        if required:
            lines.append(f"    REQUIRED_SECTIONS: {', '.join(required)}")
        targets = schema.get("word_targets_default") or {}
        if targets:
            lines.append("    DEFAULT_WORD_TARGETS:")
            for k, v in targets.items():
                lines.append(f"      {k}: {v}")

    # Inject per-article-type quality rules (override system-prompt defaults Q1-Q6)
    qr = schema.get("quality_rules") or {}
    if qr:
        lines.append("  QUALITY_RULES_OVERRIDE (these override default Q1-Q6 rules for this article type):")
        if "paragraph_words_max" in qr:
            lines.append(f"    Q1_paragraph_words_max: {qr['paragraph_words_max']}")
        voice = qr.get("voice") or {}
        if sec and sec in voice:
            lines.append(f"    Q3_voice_this_section: {voice[sec]}")
        elif not sec and voice:
            for s, v in voice.items():
                lines.append(f"    Q3_voice_{s}: {v}")
        if "sentence_length_mean_max" in qr:
            lines.append(f"    Q2_sentence_length_mean_max: {qr['sentence_length_mean_max']} words")
        cd = qr.get("citation_density") or {}
        if sec and sec in cd:
            lines.append(f"    Q4_citation_density_this_section: {cd[sec]}")
        pv = qr.get("preferred_verbs") or []
        if pv:
            lines.append(f"    Q5_preferred_verbs: {', '.join(pv)}")
        fv = qr.get("forbidden_verbs") or []
        if fv:
            lines.append(f"    Q5_forbidden_verbs: {', '.join(fv)}")
        tri = qr.get("triplet_parallel_max_per_section")
        if tri is not None:
            lines.append(f"    Q6_triplet_parallel_max_per_section: {tri}")

    lines.append("</article_type_context>")
    lines.append("")
    lines.append(
        "Deep structure rules in <article_type_context> define WHAT to say in each section. "
        "QUALITY_RULES_OVERRIDE in <article_type_context> override the default Q1-Q6 English quality rules. "
        "Journal rules in <journal_context> define citation format and forbidden phrases. "
        "Never copy exemplar sentences verbatim — adapt patterns to user-supplied facts only."
    )
    return "\n".join(lines)


def build_combined_context_block(
    journal_key: str | None,
    section_key: str | None,
    article_type: str | None,
    journal_block_fn,
) -> str:
    """Merge article-type + journal context (journal_block_fn = build_journal_context_block)."""
    parts: list[str] = []
    at = build_article_type_context_block(article_type, section_key, journal_key)
    if at:
        parts.append(at)
    if journal_key and journal_block_fn:
        canonical = canonical_article_type(article_type)
        # Legacy journal_context still uses simplified atype for citation notes
        legacy = (schema_legacy_alias(canonical))
        j = journal_block_fn(journal_key, section_key, legacy)
        if j:
            parts.append(j)
    return "\n\n".join(parts)


def schema_legacy_alias(canonical: str) -> str:
    """Map canonical type back to legacy 4-type keys for journal_context citation notes."""
    schema = _type_schema(canonical) or {}
    return schema.get("legacy_alias") or canonical


def _split_sentences(text: str) -> list[str]:
    parts = re.split(r"(?<=[.!?])\s+(?=[A-Z(])", text.strip())
    return [p.strip() for p in parts if p.strip()]


def _has_bmrc_labels(text: str, labels: tuple[str, ...]) -> bool:
    return all(lab in text for lab in labels)


def ensure_bmrc_abstract_format(
    prose: str,
    journal_key: str | None,
    *,
    subheadings: list[str] | None = None,
) -> tuple[str, dict[str, Any]]:
    """
    If journal_surface requires BMRC subheadings but prose is a single block,
    re-segment by sentence cadence (Background ~2, Methods ~2, Results bulk, Conclusion ~1).
    """
    surface = _journal_surface(journal_key)
    if (surface.get("abstract_format") or "") != "bmrc_subheadings":
        return prose, {"enforced": False, "reason": "not_bmrc_journal"}

    subs = subheadings or surface.get("abstract_subheadings") or [
        "Background", "Methods", "Results", "Conclusion"
    ]
    labels = tuple(f"{s}:" for s in subs)
    if _has_bmrc_labels(prose, labels):
        return prose, {"enforced": False, "reason": "already_labeled"}

    sents = _split_sentences(prose)
    meta: dict[str, Any] = {"enforced": True, "n_sentences": len(sents)}
    if len(sents) < 4:
        meta["reason"] = "too_few_sentences"
        meta["enforced"] = False
        return prose, meta

    bg_n = min(2, len(sents) - 3)
    meth_n = min(2, max(1, len(sents) - bg_n - 2))
    res_end = len(sents) - 1
    meth_end = bg_n + meth_n
    blocks = [
        f"{labels[0]} {' '.join(sents[:bg_n])}",
        f"{labels[1]} {' '.join(sents[bg_n:meth_end])}",
        f"{labels[2]} {' '.join(sents[meth_end:res_end])}",
        f"{labels[3]} {sents[res_end]}",
    ]
    meta["reason"] = "sentence_split"
    return "\n\n".join(blocks), meta


def abstract_format_for_journal(journal_key: str | None) -> str:
    return (_journal_surface(journal_key).get("abstract_format") or "single_paragraph")


__all__ = [
    "canonical_article_type",
    "list_article_types",
    "build_article_type_context_block",
    "build_combined_context_block",
    "schema_legacy_alias",
    "ensure_bmrc_abstract_format",
    "abstract_format_for_journal",
]
