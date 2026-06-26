"""
Per-account writing style store.

Each logged-in account gets its own isolated profile at:
  data/account_styles/<username>.json

Profile captures:
  - terminology:    preferred + forbidden terms, field-specific names
  - writing_habits: hedge level, voice preference, sentence length preference
  - phrase_bank:    up to 30 short phrases learned from the user's own uploads
  - feedback_log:   lightweight record of AI→human edits (signals for future learning)

This is SEPARATE from the community journal packs (user_style.py) which are
shared across all users of the same journal.  Per-account profiles override or
augment journal defaults when injected into prompts.
"""

from __future__ import annotations

import json
import re
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

_HERE = Path(__file__).resolve().parent
_ROOT = Path(__import__("os").environ.get("WM_ACCOUNT_STYLES_DIR",
                                           str(_HERE / "data" / "account_styles")))

_MAX_TERMS = 200
_MAX_PHRASES = 30
_MAX_FEEDBACK = 100
_MAX_PREFERRED_VERBS = 40


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


def _path(username: str) -> Path:
    _ROOT.mkdir(parents=True, exist_ok=True)
    safe = re.sub(r"[^\w\-]", "_", username)[:64]
    return _ROOT / f"{safe}.json"


# ── Read ──────────────────────────────────────────────────────────────────────

def load_profile(username: str) -> dict[str, Any]:
    """Return the account profile, or an empty skeleton if not yet created."""
    p = _path(username)
    if p.exists():
        try:
            return json.loads(p.read_text(encoding="utf-8"))
        except Exception:
            pass
    return _empty_profile(username)


def _empty_profile(username: str) -> dict[str, Any]:
    return {
        "username": username,
        "created_at": _now(),
        "updated_at": _now(),
        "terminology": {
            "preferred": {},   # {"human CD45+": "preferred over hCD45+"}
            "forbidden": [],   # terms the user never wants in output
            "field_terms": []  # authoritative names: cell types, assays, strains
        },
        "writing_habits": {
            "hedge_level":         "moderate",   # low | moderate | high
            "voice_preference":    "active",      # active | passive | mixed
            "sentence_length":     "medium",      # short | medium | long
            "citation_style":      "author_year", # author_year | numbered
            "paragraph_length":    "short",       # short(≤80w) | medium(≤120w) | long
        },
        "preferred_verbs": [],    # e.g. ["showed", "revealed"]
        "forbidden_phrases": [],  # overrides journal defaults too
        "phrase_bank": [],        # learned from uploads: [{phrase, category, source}]
        "feedback_log": [],       # [{original, edited, section, diff_type, logged_at}]
        "upload_count": 0,
        "feedback_count": 0,
    }


# ── Write (atomic) ─────────────────────────────────────────────────────────────

def _save(profile: dict[str, Any]) -> None:
    profile["updated_at"] = _now()
    p = _path(profile["username"])
    p.write_text(json.dumps(profile, indent=2, ensure_ascii=False), encoding="utf-8")


# ── Update terminology ─────────────────────────────────────────────────────────

def update_terminology(
    username: str,
    *,
    preferred: dict[str, str] | None = None,   # {term: note}
    forbidden: list[str] | None = None,
    field_terms: list[str] | None = None,
) -> dict[str, Any]:
    """Add/replace terminology entries for this account."""
    prof = load_profile(username)
    t = prof["terminology"]

    if preferred:
        t["preferred"].update(preferred)
        # Trim to max
        if len(t["preferred"]) > _MAX_TERMS:
            # Keep most recent
            keys = list(t["preferred"].keys())
            t["preferred"] = {k: t["preferred"][k] for k in keys[-_MAX_TERMS:]}

    if forbidden is not None:
        existing = set(t["forbidden"])
        existing.update(forbidden)
        t["forbidden"] = list(existing)[:_MAX_TERMS]

    if field_terms is not None:
        existing = set(t["field_terms"])
        existing.update(field_terms)
        t["field_terms"] = list(existing)[:_MAX_TERMS]

    _save(prof)
    return {"status": "ok", "terminology_counts": {
        "preferred": len(t["preferred"]),
        "forbidden": len(t["forbidden"]),
        "field_terms": len(t["field_terms"]),
    }}


def update_writing_habits(
    username: str,
    *,
    hedge_level: str | None = None,
    voice_preference: str | None = None,
    sentence_length: str | None = None,
    citation_style: str | None = None,
    paragraph_length: str | None = None,
    preferred_verbs: list[str] | None = None,
    forbidden_phrases: list[str] | None = None,
) -> dict[str, Any]:
    prof = load_profile(username)
    wh = prof["writing_habits"]

    if hedge_level in ("low", "moderate", "high"):
        wh["hedge_level"] = hedge_level
    if voice_preference in ("active", "passive", "mixed"):
        wh["voice_preference"] = voice_preference
    if sentence_length in ("short", "medium", "long"):
        wh["sentence_length"] = sentence_length
    if citation_style in ("author_year", "numbered"):
        wh["citation_style"] = citation_style
    if paragraph_length in ("short", "medium", "long"):
        wh["paragraph_length"] = paragraph_length
    if preferred_verbs is not None:
        existing = set(prof["preferred_verbs"])
        existing.update(preferred_verbs)
        prof["preferred_verbs"] = list(existing)[:_MAX_PREFERRED_VERBS]
    if forbidden_phrases is not None:
        existing = set(prof["forbidden_phrases"])
        existing.update(forbidden_phrases)
        prof["forbidden_phrases"] = list(existing)[:_MAX_TERMS]

    _save(prof)
    return {"status": "ok", "writing_habits": prof["writing_habits"]}


def add_phrase_bank_entries(
    username: str,
    phrases: list[dict[str, str]],  # [{phrase, category, source}]
) -> dict[str, Any]:
    """Merge phrases from user uploads into the account phrase bank."""
    prof = load_profile(username)
    existing_phrases = {p["phrase"] for p in prof["phrase_bank"]}
    added = 0
    for entry in phrases:
        phrase = (entry.get("phrase") or "").strip()
        if phrase and phrase not in existing_phrases:
            prof["phrase_bank"].append({
                "phrase":   phrase,
                "category": entry.get("category") or "other",
                "source":   entry.get("source") or "user_upload",
                "added_at": _now(),
            })
            existing_phrases.add(phrase)
            added += 1
    # Trim to max, keep most recent
    if len(prof["phrase_bank"]) > _MAX_PHRASES:
        prof["phrase_bank"] = prof["phrase_bank"][-_MAX_PHRASES:]
    prof["upload_count"] = prof.get("upload_count", 0) + 1
    _save(prof)
    return {"status": "ok", "phrases_added": added, "phrase_bank_size": len(prof["phrase_bank"])}


def log_feedback(
    username: str,
    *,
    original: str,
    edited: str,
    section: str,
    diff_type: str = "style",   # style | fact | structure | terminology
) -> dict[str, Any]:
    """Record an AI→human edit as a training signal (lightweight, no ML yet)."""
    prof = load_profile(username)
    entry = {
        "original_preview": original[:200],
        "edited_preview":   edited[:200],
        "section":          section,
        "diff_type":        diff_type,
        "logged_at":        _now(),
    }
    prof["feedback_log"].append(entry)
    if len(prof["feedback_log"]) > _MAX_FEEDBACK:
        prof["feedback_log"] = prof["feedback_log"][-_MAX_FEEDBACK:]
    prof["feedback_count"] = prof.get("feedback_count", 0) + 1
    _save(prof)
    return {"status": "ok", "feedback_count": prof["feedback_count"]}


# ── Prompt injection ───────────────────────────────────────────────────────────

def build_account_context_block(username: str | None) -> str:
    """
    Return an <account_style> XML block for injection into draft/rewrite prompts.
    Returns empty string if username is None or profile has no meaningful content.
    """
    if not username:
        return ""
    prof = load_profile(username)
    t = prof.get("terminology") or {}
    wh = prof.get("writing_habits") or {}
    pv = prof.get("preferred_verbs") or []
    fp = prof.get("forbidden_phrases") or []
    pb = prof.get("phrase_bank") or []

    has_content = (
        t.get("preferred") or t.get("forbidden") or t.get("field_terms")
        or pv or fp or pb
        or wh.get("hedge_level") != "moderate"
        or wh.get("voice_preference") != "active"
    )
    if not has_content:
        return ""

    lines: list[str] = [f'<account_style username="{username}">']

    if wh:
        lines.append("  WRITING_HABITS:")
        for k, v in wh.items():
            lines.append(f"    {k}: {v}")

    if pv:
        lines.append(f"  PREFERRED_VERBS: {', '.join(pv[:20])}")

    if fp:
        lines.append(f"  FORBIDDEN_PHRASES: {', '.join(fp[:20])}")

    if t.get("preferred"):
        lines.append("  PREFERRED_TERMINOLOGY (use these exact forms):")
        for term, note in list(t["preferred"].items())[:30]:
            lines.append(f"    \"{term}\"" + (f"  # {note}" if note else ""))

    if t.get("forbidden"):
        lines.append(f"  FORBIDDEN_TERMS: {', '.join(t['forbidden'][:20])}")

    if t.get("field_terms"):
        lines.append(f"  FIELD_TERMS (authoritative names): {', '.join(t['field_terms'][:30])}")

    if pb:
        lines.append("  PHRASE_BANK (natural phrasing from user's own writing):")
        for entry in pb[:12]:
            lines.append(f"    [{entry.get('category','?')}] {entry.get('phrase','')}")

    lines.append("</account_style>")
    lines.append("")
    lines.append(
        "Rules in <account_style> OVERRIDE journal defaults. "
        "Always use preferred terminology exactly as written. "
        "Never use any forbidden phrase or term."
    )
    return "\n".join(lines)


__all__ = [
    "load_profile",
    "update_terminology",
    "update_writing_habits",
    "add_phrase_bank_entries",
    "log_feedback",
    "build_account_context_block",
]
