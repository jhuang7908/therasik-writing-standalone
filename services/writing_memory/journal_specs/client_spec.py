"""
Client-safe submission spec loader and format-readiness checks.

Curated specs only — never LLM-generated. Surfaces verified fields to UI/API;
unverified fields are omitted from client payloads but counted in coverage stats.
"""

from __future__ import annotations

import json
import re
from pathlib import Path
from typing import Any

_HERE = Path(__file__).resolve().parent
SPECS_DIR = _HERE / "specs"

_VERIFIED_AT_MVP = "2026-05-26T12:00:00Z"
_VERIFIED_BY_MVP = "writing_memory_mvp"


def _is_field_envelope(node: Any) -> bool:
    return isinstance(node, dict) and "verification_status" in node and "value" in node


# Statuses considered as "trustworthy enough to ship to the client".
# - verified            → human-confirmed
# - published_guideline → quoted from official journal author guidelines (URL required)
_VERIFIED_STATUSES = {"verified", "published_guideline"}


def _client_field(field: dict[str, Any]) -> dict[str, Any] | None:
    if field.get("verification_status") not in _VERIFIED_STATUSES:
        return None
    if field.get("value") is None:
        return None
    out: dict[str, Any] = {"value": field["value"]}
    if field.get("source_url"):
        out["source_url"] = field["source_url"]
    if field.get("notes"):
        out["notes"] = field["notes"]
    # Surface the provenance so audit/UI can show "from official guideline" vs "human-verified"
    out["verification_status"] = field.get("verification_status")
    return out


def _filter_verified(node: Any) -> Any:
    if _is_field_envelope(node):
        return _client_field(node)
    if isinstance(node, dict):
        out: dict[str, Any] = {}
        for k, v in node.items():
            filtered = _filter_verified(v)
            if filtered is not None:
                out[k] = filtered
        return out or None
    if isinstance(node, list):
        items = [_filter_verified(v) for v in node]
        items = [i for i in items if i is not None]
        return items or None
    return node


def _count_fields(node: Any, counts: dict[str, int]) -> None:
    if _is_field_envelope(node):
        counts["total"] += 1
        st = node.get("verification_status", "unverified")
        if st in _VERIFIED_STATUSES and node.get("value") is not None:
            counts["verified"] += 1
        elif st == "unverified":
            counts["unverified"] += 1
        elif st == "out_of_date":
            counts["out_of_date"] += 1
        return
    if isinstance(node, dict):
        for v in node.values():
            _count_fields(v, counts)
    elif isinstance(node, list):
        for v in node:
            _count_fields(v, counts)


def load_raw_spec(spec_key: str) -> dict[str, Any] | None:
    path = SPECS_DIR / f"{spec_key}.json"
    if not path.exists():
        return None
    return json.loads(path.read_text(encoding="utf-8"))


def spec_coverage(spec: dict[str, Any]) -> dict[str, int]:
    counts = {"total": 0, "verified": 0, "unverified": 0, "out_of_date": 0}
    _count_fields(spec, counts)
    return counts


def client_safe_spec(spec: dict[str, Any]) -> dict[str, Any]:
    """Return spec with only verified, non-null field values."""
    filtered = _filter_verified(spec)
    if not isinstance(filtered, dict):
        return {}
    return {
        "schema_version": spec.get("schema_version"),
        "journal": spec.get("journal"),
        "spec_version": spec.get("spec_version"),
        "reference_style_id": spec.get("reference_style_id"),
        "sourced_from": spec.get("sourced_from", []),
        **{k: v for k, v in filtered.items() if k not in {
            "schema_version", "journal", "spec_version", "reference_style_id", "sourced_from",
        } and v is not None},
    }


def list_spec_keys() -> list[str]:
    return sorted(p.stem for p in SPECS_DIR.glob("*.json"))


def resolve_spec_key(
    journal_key: str,
    journal_map: dict[str, dict[str, Any]] | None = None,
) -> str | None:
    """Map UI journal key → curated spec file key."""
    if load_raw_spec(journal_key):
        return journal_key
    if journal_map:
        entry = journal_map.get(journal_key) or {}
        sk = entry.get("spec_key")
        if sk and load_raw_spec(sk):
            return sk
        pk = entry.get("profile_key")
        if pk and load_raw_spec(pk):
            return pk
    return None


# Product word/ref limits (Phase 1–2); used when spec field still unverified.
_FALLBACK_LIMITS: dict[str, dict[str, dict[str, int]]] = {
    "generic": {
        "research":    {"max_words": 5000, "max_references": 60},
        "review":      {"max_words": 8000, "max_references": 100},
        "case_report": {"max_words": 3000, "max_references": 30},
        "letter":      {"max_words": 800,  "max_references": 15},
    },
    "pnas": {
        "research":    {"max_words": 6000, "max_references": 50},
        "review":      {"max_words": 8000, "max_references": 100},
        "case_report": {"max_words": 3000, "max_references": 30},
        "letter":      {"max_words": 500,  "max_references": 10},
    },
    "elife": {
        "research":    {"max_words": 8000, "max_references": 80},
        "review":      {"max_words": 10000,"max_references": 150},
        "case_report": {"max_words": 4000, "max_references": 40},
        "letter":      {"max_words": 800,  "max_references": 15},
    },
    "plos_med": {
        "research":    {"max_words": 4000, "max_references": 60},
        "review":      {"max_words": 6000, "max_references": 80},
        "case_report": {"max_words": 2000, "max_references": 20},
        "letter":      {"max_words": 600,  "max_references": 12},
    },
    "nature": {
        "research":    {"max_words": 5000, "max_references": 50},
        "review":      {"max_words": 6000, "max_references": 80},
        "letter":      {"max_words": 2000, "max_references": 30},
    },
    "cell": {
        "research":    {"max_words": 7500, "max_references": 80},
        "review":      {"max_words": 8000, "max_references": 120},
        "letter":      {"max_words": 2500, "max_references": 30},
    },
    "science": {
        "research":    {"max_words": 4500, "max_references": 60},
        "review":      {"max_words": 6000, "max_references": 80},
        "letter":      {"max_words": 2500, "max_references": 40},
    },
    "nejm": {
        "research":    {"max_words": 2700, "max_references": 40},
        "review":      {"max_words": 4500, "max_references": 120},
        "case_report": {"max_words": 2700, "max_references": 30},
        "letter":      {"max_words": 400,  "max_references": 5},
    },
    "lancet": {
        "research":    {"max_words": 4500, "max_references": 50},
        "review":      {"max_words": 6000, "max_references": 80},
        "case_report": {"max_words": 3000, "max_references": 30},
        "letter":      {"max_words": 350,  "max_references": 5},
    },
    "nature_medicine": {
        "research":    {"max_words": 4500, "max_references": 70},
        "review":      {"max_words": 6000, "max_references": 100},
        "letter":      {"max_words": 2000, "max_references": 30},
    },
}


def _word_count(text: str) -> int:
    return len(re.findall(r"\b\w+\b", text or ""))


def check_submission_readiness(
    *,
    spec_key: str,
    article_type: str,
    full_text: str | None = None,
    abstract_text: str | None = None,
    reference_count: int | None = None,
    figure_count: int | None = None,
    fallback_limits: dict[str, dict[str, dict[str, int]]] | None = None,
) -> dict[str, Any]:
    """
    Compare user-supplied counts against verified spec fields and product fallbacks.
    Returns PASS/WARN checklist items — not a prediction of acceptance.
    """
    raw = load_raw_spec(spec_key)
    safe = client_safe_spec(raw) if raw else {}
    limits_src = "none"
    max_words: int | None = None
    max_refs: int | None = None
    abstract_limit: Any = None

    no_word_limit_official = False
    if raw:
        mt_raw = (raw.get("main_text") or {}).get("word_limit") or {}
        if mt_raw.get("verification_status") in _VERIFIED_STATUSES and mt_raw.get("value") is None:
            no_word_limit_official = True
            limits_src = "verified_spec"
            max_words = None

    mt = safe.get("main_text") or {}
    if not no_word_limit_official and isinstance(mt, dict) and mt.get("word_limit"):
        wl = mt["word_limit"].get("value")
        if isinstance(wl, int):
            max_words = wl
            limits_src = "verified_spec"

    ab = safe.get("abstract") or {}
    if isinstance(ab, dict) and ab.get("word_limit"):
        abstract_limit = ab["word_limit"].get("value")

    fb_table = fallback_limits or _FALLBACK_LIMITS
    fb = (fb_table.get(spec_key) or {}).get(article_type)
    if fb and not no_word_limit_official:
        if max_words is None and fb.get("max_words"):
            max_words = fb["max_words"]
            if limits_src == "none":
                limits_src = "product_fallback"
        if max_refs is None and fb.get("max_references"):
            max_refs = fb["max_references"]
            if limits_src == "none":
                limits_src = "product_fallback"
    elif fb and no_word_limit_official and max_refs is None and fb.get("max_references"):
        max_refs = fb["max_references"]
        limits_src = "product_fallback_refs_only"

    items: list[dict[str, Any]] = []
    overall = "PASS"

    wc = _word_count(full_text) if full_text else None
    if full_text is None:
        items.append({
            "check": "main_text_word_count",
            "status": "INFO",
            "message": "Provide full manuscript text to run word-count check.",
        })
    elif no_word_limit_official:
        items.append({
            "check": "main_text_word_count",
            "status": "PASS",
            "message": f"Main text ~{wc} words — no official word-count limit for this journal.",
            "observed": wc,
        })
    elif wc is not None and max_words:
        if wc > max_words:
            items.append({
                "check": "main_text_word_count",
                "status": "WARN",
                "message": f"Main text ~{wc} words exceeds limit {max_words} ({limits_src}).",
                "observed": wc,
                "limit": max_words,
            })
            overall = "WARN"
        else:
            items.append({
                "check": "main_text_word_count",
                "status": "PASS",
                "message": f"Main text ~{wc} words within limit {max_words}.",
                "observed": wc,
                "limit": max_words,
            })

    awc = _word_count(abstract_text) if abstract_text else None
    if awc is not None and abstract_limit is not None:
        if isinstance(abstract_limit, dict):
            pref = abstract_limit.get("preferred")
            hard = abstract_limit.get("max", pref)
            if hard and awc > hard:
                items.append({
                    "check": "abstract_word_count",
                    "status": "WARN",
                    "message": f"Abstract ~{awc} words exceeds maximum {hard}.",
                    "observed": awc,
                    "limit": hard,
                })
                overall = "WARN"
            elif pref and awc > pref:
                items.append({
                    "check": "abstract_word_count",
                    "status": "WARN",
                    "message": f"Abstract ~{awc} words above preferred {pref} (max {hard}).",
                    "observed": awc,
                    "limit": pref,
                })
                if overall == "PASS":
                    overall = "WARN"
            else:
                items.append({
                    "check": "abstract_word_count",
                    "status": "PASS",
                    "message": f"Abstract ~{awc} words within guidelines.",
                    "observed": awc,
                })
        elif isinstance(abstract_limit, int) and awc > abstract_limit:
            items.append({
                "check": "abstract_word_count",
                "status": "WARN",
                "message": f"Abstract ~{awc} words exceeds limit {abstract_limit}.",
                "observed": awc,
                "limit": abstract_limit,
            })
            overall = "WARN"

    if reference_count is not None and max_refs:
        if reference_count > max_refs:
            items.append({
                "check": "reference_count",
                "status": "WARN",
                "message": f"{reference_count} references exceeds suggested cap {max_refs}.",
                "observed": reference_count,
                "limit": max_refs,
            })
            overall = "WARN"
        else:
            items.append({
                "check": "reference_count",
                "status": "PASS",
                "message": f"{reference_count} references within cap {max_refs}.",
                "observed": reference_count,
                "limit": max_refs,
            })

    struct = safe.get("abstract") or {}
    if isinstance(struct, dict) and struct.get("structured"):
        st_val = struct["structured"].get("value")
        if st_val is True and abstract_text and article_type == "research":
            lower = abstract_text.lower()
            for sec in ("background", "methods", "conclusions"):
                if sec not in lower:
                    items.append({
                        "check": "structured_abstract_sections",
                        "status": "WARN",
                        "message": f"Structured abstract may be missing '{sec}' section heading.",
                    })
                    if overall == "PASS":
                        overall = "WARN"
                    break
            else:
                items.append({
                    "check": "structured_abstract_sections",
                    "status": "PASS",
                    "message": "Structured abstract section headings detected.",
                })

    coverage = spec_coverage(raw) if raw else {"total": 0, "verified": 0, "unverified": 0, "out_of_date": 0}

    return {
        "overall_status": overall,
        "spec_key": spec_key,
        "article_type": article_type,
        "limits_source": limits_src,
        "checklist": items,
        "verified_spec": safe,
        "coverage": coverage,
        "disclaimer": (
            "Format-readiness checks only. Does not predict editorial acceptance, "
            "scope fit, or impact tier."
        ),
    }
