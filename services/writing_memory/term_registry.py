"""
Field Terminology Registry
==========================

A growing, per-field glossary that accumulates from every full-text upload.
Unlike user_style.py (which learns cadence/rhythm), this module captures
WHAT the field calls things — authoritative names, accepted abbreviations,
co-occurring term clusters, and example sentences showing professional usage.

Storage layout (per field key):
  data/term_registry/<field_key>.json

Each entry (TermEntry):
  term          : canonical form (e.g. "NLRP3 inflammasome")
  aliases       : accepted abbreviations/synonyms (e.g. ["NLRP3", "NACHT domain protein 3"])
  domain        : sub-field tag (e.g. "innate_immunity", "flow_cytometry")
  freq          : cumulative occurrence count across all source texts
  co_terms      : list of terms frequently co-occurring (top 10)
  example_sents : up to 3 verbatim sentences from uploaded texts showing professional usage
  sources       : list of source SHA hashes (for traceability, not for display)
  first_seen    : ISO timestamp
  last_updated  : ISO timestamp

The registry is:
- Populated by extract_and_merge() called from upload_intake
- Queried by build_term_context_block() for prompt injection in draft_section / rewrite

Field key derivation:
  From the journal_display_name slug when the text is uploaded to a journal pack.
  Falls back to "general_biomedical" if no field can be inferred.
"""

from __future__ import annotations

import hashlib
import json
import re
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

_HERE = Path(__file__).resolve().parent
_ROOT = Path(
    __import__("os").environ.get(
        "WM_TERM_REGISTRY_DIR",
        str(_HERE / "data" / "term_registry"),
    )
)
PROMPTS_DIR = _HERE / "prompts"

# Limits per registry file
_MAX_ENTRIES = 2000
_MAX_CO_TERMS = 10
_MAX_EXAMPLE_SENTS = 3
_MAX_ALIASES = 6

# Injection limits (keep prompts short)
_INJECT_TOP_N = 30
_INJECT_EXAMPLE_SENTS_PER_TERM = 1


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


def _slug(text: str) -> str:
    s = re.sub(r"[^a-z0-9]+", "_", (text or "").strip().lower()).strip("_")
    return (s[:64] or "general_biomedical")


def _registry_path(field_key: str) -> Path:
    _ROOT.mkdir(parents=True, exist_ok=True)
    return _ROOT / f"{_slug(field_key)}.json"


def _hash(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8", errors="ignore")).hexdigest()[:12]


# ── Load / Save ──────────────────────────────────────────────────────────────

def _load(field_key: str) -> dict[str, Any]:
    p = _registry_path(field_key)
    if p.exists():
        try:
            return json.loads(p.read_text(encoding="utf-8"))
        except Exception:
            pass
    return {"field_key": _slug(field_key), "entries": {}, "created_at": _now(), "updated_at": _now()}


def _save(registry: dict[str, Any]) -> None:
    registry["updated_at"] = _now()
    p = _registry_path(registry["field_key"])
    # Trim if over limit
    entries: dict[str, Any] = registry.get("entries") or {}
    if len(entries) > _MAX_ENTRIES:
        # Keep the most frequent
        sorted_keys = sorted(entries, key=lambda k: entries[k].get("freq", 0), reverse=True)
        registry["entries"] = {k: entries[k] for k in sorted_keys[:_MAX_ENTRIES]}
    p.write_text(json.dumps(registry, indent=2, ensure_ascii=False), encoding="utf-8")


# ── Extraction helpers ────────────────────────────────────────────────────────

def _merge_entry(
    existing: dict[str, Any] | None,
    new_entry: dict[str, Any],
    source_hash: str,
) -> dict[str, Any]:
    """Merge a newly extracted entry into an existing one."""
    if not existing:
        entry = dict(new_entry)
        entry["freq"] = 1
        entry["sources"] = [source_hash]
        entry["first_seen"] = _now()
        entry["last_updated"] = _now()
        return entry

    existing["freq"] = existing.get("freq", 0) + 1
    existing["last_updated"] = _now()

    # Merge aliases (deduplicate, cap)
    old_aliases: list[str] = existing.get("aliases") or []
    new_aliases: list[str] = new_entry.get("aliases") or []
    merged_aliases = list(dict.fromkeys(old_aliases + new_aliases))[:_MAX_ALIASES]
    existing["aliases"] = merged_aliases

    # Merge co_terms (deduplicate, cap by cumulative freq preference)
    old_co: list[str] = existing.get("co_terms") or []
    new_co: list[str] = new_entry.get("co_terms") or []
    merged_co = list(dict.fromkeys(old_co + new_co))[:_MAX_CO_TERMS]
    existing["co_terms"] = merged_co

    # Add example sentences (deduplicate by hash, cap)
    old_sents: list[str] = existing.get("example_sents") or []
    new_sents: list[str] = new_entry.get("example_sents") or []
    seen_hashes = {_hash(s) for s in old_sents}
    for s in new_sents:
        if len(old_sents) >= _MAX_EXAMPLE_SENTS:
            break
        if _hash(s) not in seen_hashes:
            old_sents.append(s)
            seen_hashes.add(_hash(s))
    existing["example_sents"] = old_sents

    # Track sources (cap at 20)
    sources: list[str] = existing.get("sources") or []
    if source_hash not in sources:
        sources.append(source_hash)
    existing["sources"] = sources[-20:]

    return existing


def extract_and_merge(
    *,
    field_key: str,
    text: str,
    source_id: str = "",
    call_claude: Any | None = None,
) -> dict[str, Any]:
    """
    Extract terminology from a full text and merge into the field registry.

    call_claude(system: str, user: str) -> str  (returns raw text response)

    Returns a summary: {field_key, terms_added, terms_updated, total_terms}
    """
    if not text or len(text.strip()) < 300:
        return {"field_key": field_key, "skipped": True, "reason": "text_too_short"}

    src_hash = _hash(text[:8000] + source_id)
    registry = _load(field_key)

    # Check if already processed (idempotent)
    all_sources = set()
    for entry in (registry.get("entries") or {}).values():
        all_sources.update(entry.get("sources") or [])
    if src_hash in all_sources:
        return {"field_key": field_key, "skipped": True, "reason": "already_processed", "source_hash": src_hash}

    if not call_claude:
        return {"field_key": field_key, "skipped": True, "reason": "no_claude_client"}

    # Sample at most 12k chars from the text for extraction
    sample = text[:12_000]

    prompt_path = PROMPTS_DIR / "extract_terms.system.md"
    system = prompt_path.read_text(encoding="utf-8") if prompt_path.exists() else _DEFAULT_SYSTEM

    user_content = (
        f"## field_key\n{field_key}\n\n"
        f"## source_text\n{sample}\n\n"
        "Output ONE JSON array only. No markdown fences."
    )

    try:
        raw = call_claude(system, user_content)
        # Strip markdown fences if model adds them
        raw = re.sub(r"^```(?:json)?\s*", "", raw.strip())
        raw = re.sub(r"\s*```$", "", raw)
        extracted: list[dict[str, Any]] = json.loads(raw)
        if not isinstance(extracted, list):
            extracted = []
    except Exception as exc:
        return {"field_key": field_key, "error": str(exc), "terms_added": 0}

    entries: dict[str, Any] = registry.get("entries") or {}
    added = updated = 0
    for item in extracted:
        canonical = (item.get("term") or "").strip()
        if not canonical or len(canonical) < 2:
            continue
        key = canonical.lower()
        existing = entries.get(key)
        merged = _merge_entry(existing, item, src_hash)
        if existing is None:
            added += 1
        else:
            updated += 1
        entries[key] = merged

    registry["entries"] = entries
    _save(registry)

    return {
        "field_key": field_key,
        "terms_added": added,
        "terms_updated": updated,
        "total_terms": len(entries),
        "source_hash": src_hash,
    }


# ── Query / injection ─────────────────────────────────────────────────────────

def query_terms(
    field_key: str,
    *,
    keywords: list[str] | None = None,
    domain: str | None = None,
    top_n: int = _INJECT_TOP_N,
) -> list[dict[str, Any]]:
    """
    Return up to top_n terms relevant to the given keywords or domain.
    Without keywords, returns the most frequent terms.
    """
    registry = _load(field_key)
    entries: dict[str, Any] = registry.get("entries") or {}
    if not entries:
        return []

    scored: list[tuple[float, dict[str, Any]]] = []
    kw_lower = [k.lower() for k in (keywords or [])]

    for key, entry in entries.items():
        base_score = float(entry.get("freq", 1))

        if domain and entry.get("domain") and domain.lower() not in entry["domain"].lower():
            continue

        if kw_lower:
            # Boost if term or co-terms contain any keyword
            term_text = (entry.get("term") or key).lower()
            aliases_text = " ".join(entry.get("aliases") or []).lower()
            co_text = " ".join(entry.get("co_terms") or []).lower()
            match_score = sum(
                3.0 if kw in term_text else (1.5 if kw in aliases_text else (1.0 if kw in co_text else 0.0))
                for kw in kw_lower
            )
            if match_score == 0:
                continue
            base_score = base_score * 0.1 + match_score * 10.0

        scored.append((base_score, entry))

    scored.sort(key=lambda x: x[0], reverse=True)
    return [e for _, e in scored[:top_n]]


def build_term_context_block(
    field_key: str,
    *,
    keywords: list[str] | None = None,
    section_key: str | None = None,
    domain: str | None = None,
    top_n: int = _INJECT_TOP_N,
) -> str:
    """
    Return a <term_registry> XML block for prompt injection.
    Returns empty string if no terms available.
    """
    terms = query_terms(field_key, keywords=keywords, domain=domain, top_n=top_n)
    if not terms:
        return ""

    lines: list[str] = [
        f'<term_registry field="{_slug(field_key)}" section="{section_key or "all"}" terms="{len(terms)}">',
        "  Use these authoritative terms and their co-occurring vocabulary when writing.",
        "  Prefer the canonical form shown. Aliases are acceptable variants.",
        "  Example sentences show professional usage — do NOT copy verbatim.",
        "",
    ]

    for entry in terms:
        canonical = entry.get("term") or list(entry.keys())[0]
        aliases = entry.get("aliases") or []
        co = entry.get("co_terms") or []
        domain_tag = entry.get("domain") or ""
        sents = (entry.get("example_sents") or [])[:_INJECT_EXAMPLE_SENTS_PER_TERM]

        alias_str = f" [{', '.join(aliases[:3])}]" if aliases else ""
        co_str = f" | co: {', '.join(co[:5])}" if co else ""
        dom_str = f" ({domain_tag})" if domain_tag else ""

        lines.append(f"  TERM: {canonical}{alias_str}{dom_str}{co_str}")
        for s in sents:
            # Truncate long example sentences
            s_short = s[:200] + ("…" if len(s) > 200 else "")
            lines.append(f"    EX: {s_short}")

    lines.append("</term_registry>")
    lines.append("")
    lines.append(
        "Terms in <term_registry> are extracted from peer-reviewed literature in this field. "
        "Use canonical forms consistently. Never introduce terminology NOT supported by user data."
    )
    return "\n".join(lines)


def list_registries() -> list[dict[str, Any]]:
    """List all available field registries with counts."""
    out: list[dict[str, Any]] = []
    if not _ROOT.exists():
        return out
    for p in sorted(_ROOT.glob("*.json")):
        try:
            data = json.loads(p.read_text(encoding="utf-8"))
            out.append({
                "field_key": data.get("field_key", p.stem),
                "total_terms": len(data.get("entries") or {}),
                "updated_at": data.get("updated_at"),
            })
        except Exception:
            continue
    return out


# ── Fallback system prompt (used if prompts/extract_terms.system.md is missing) ──

_DEFAULT_SYSTEM = """\
Extract professional terminology from a scientific text.

Output a JSON array. Each item:
{
  "term": "canonical form (noun phrase, ≤6 words)",
  "aliases": ["abbrev1", "synonym2"],
  "domain": "sub-field (e.g. flow_cytometry, innate_immunity, pharmacology)",
  "co_terms": ["term frequently mentioned nearby"],
  "example_sents": ["verbatim sentence ≤120 words showing correct usage"]
}

Rules:
- Only extract terms a domain expert would recognise as field-specific vocabulary.
- Canonical form: prefer full scientific name over abbreviation.
- Exclude generic verbs (showed, found), generic nouns (cells, data, model), author names.
- Target: gene names, protein complexes, assay names, cell subtypes, animal models,
  drug/compound names, pathway names, anatomical terms, disease names, statistical methods.
- Max 40 terms per call. Output array only — no markdown fences, no prose.
"""


__all__ = [
    "extract_and_merge",
    "query_terms",
    "build_term_context_block",
    "list_registries",
]
