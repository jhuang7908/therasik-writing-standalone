"""
journal_gateway.py — Proprietary journal database access layer.

SECURITY CONTRACT:
  Raw journal JSON files (10,452 items) are InSynBio IP.
  This module is the ONLY permitted access point in cloud mode.

  Rules enforced here:
    1. Strip all internal/structural fields (_file, _slug, _source_url, _scraped_at, _raw_*)
    2. Strip file-system paths that reveal DB structure
    3. Return only formatted, human-readable requirement fields
    4. Never return a field that allows reconstructing the full JSON file
    5. Add _source: "insynbio_journal_db" (brand attribution, no structural info)

  The calling tool (get_journal_requirements) returns this sanitised dict.
  Raw dict from _search_journal_files must NEVER be returned directly in cloud mode.
"""
from __future__ import annotations

import os
from typing import Any

# ── Fields that must never leave the server ───────────────────────────────────
_STRIP_FIELDS: set[str] = {
    "_file",            # exposes filename = slug = DB key
    "_slug",
    "_raw",
    "_raw_html",
    "_source_url",      # exact crawl URL reveals DB provenance
    "_scraped_at",
    "_scrape_version",
    "_internal",
    "_id",
    "_db_path",
    "_file_path",
    "_index",
}

# Prefix-based strip (any field starting with these)
_STRIP_PREFIXES: tuple[str, ...] = ("_raw_", "_internal_", "_debug_")

# ── Fields we actively WANT to return (allowlist for extra safety) ─────────────
# If a journal JSON has unexpected new fields, they are blocked by default.
_ALLOW_FIELDS: set[str] = {
    # Identity
    "title", "name", "abbreviation", "issn", "eissn", "publisher",
    "journal_url", "submission_system", "submission_url",
    # Scope
    "scope", "subject_areas", "article_types",
    # Word / page limits
    "word_limit", "word_limits", "abstract_limit", "abstract_word_limit",
    "title_word_limit", "max_pages",
    # Structure
    "required_sections", "optional_sections", "section_order",
    # References
    "reference_limit", "citation_style", "reference_format",
    "reference_management",
    # Figures / tables
    "figure_limit", "table_limit", "figure_formats", "figure_resolution",
    "supplementary_allowed",
    # Open access
    "open_access", "apc_usd", "apc_notes",
    # Review type
    "peer_review_type", "review_timeline_weeks",
    # Ethics / data
    "data_availability_required", "ethics_statement_required",
    "conflict_of_interest_required", "author_contributions_required",
    # Formatting
    "formatting_style", "line_spacing", "font", "margin_cm",
    "cover_letter_required", "highlights_required",
    # Availability metadata (safe)
    "requirements_available", "last_updated",
    # Suggestions / extras
    "_also_matched",
    # Cloud meta
    "_source",
}


def sanitise(raw: dict[str, Any], journal_name: str = "") -> dict[str, Any]:
    """
    Filter a raw journal dict to only safe, client-facing fields.

    Args:
        raw:          Full dict loaded from journal JSON file.
        journal_name: Original query string (for error messages).

    Returns:
        Sanitised dict safe to return to cloud clients.
    """
    out: dict[str, Any] = {}

    for k, v in raw.items():
        # Hard strip
        if k in _STRIP_FIELDS:
            continue
        # Prefix strip
        if any(k.startswith(p) for p in _STRIP_PREFIXES):
            continue
        # Allowlist gate: only known fields pass
        if k not in _ALLOW_FIELDS:
            continue
        # Recursively sanitise nested dicts (e.g. word_limits dict)
        if isinstance(v, dict):
            v = {sk: sv for sk, sv in v.items()
                 if not sk.startswith("_") and sk not in _STRIP_FIELDS}
        out[k] = v

    # Always tag source (brand, not structural info)
    out["_source"] = "insynbio_journal_db"

    # Warn if result is suspiciously thin (journal JSON may have unexpected structure)
    if len(out) <= 2 and raw:
        out["_warning"] = (
            "Limited information available for this journal. "
            "Contact support@insynbio.com to request a data update."
        )

    return out


def sanitise_list(raw_list: list[dict], journal_name: str = "") -> list[dict]:
    """Sanitise a list of journal dicts (for list_journals results)."""
    return [sanitise(r, journal_name) for r in raw_list]


# ── Cloud-mode override check ─────────────────────────────────────────────────
CLOUD_MODE = os.environ.get("THERASIK_CLOUD_MODE", "0") == "1"


def enforce_cloud_gate(result: dict) -> dict:
    """
    Call this on any raw journal result before returning it to the client.
    In cloud mode: always sanitise.
    In local dev mode: pass through (owner has full access).
    """
    if not CLOUD_MODE:
        return result
    return sanitise(result)
