"""
LanguageTool free public API wrapper for writing_memory service.

Uses the free public endpoint https://api.languagetoolplus.com/v2/check
- Rate limit: ~20 req/min on free tier (no key)
- Graceful degradation: if unavailable, returns available=False (never blocks main flow)
- Complements Vale: Vale = style/academic rules; LT = grammar/collocation/syntax errors

Public API:
    is_lt_available()  -> bool  (does a quick probe; cached for 5 min)
    check_grammar(text, language="en-US", max_chars=10000) -> LTResult
    grammar_summary(text) -> dict  (simplified for UI / QA scoring)
"""
from __future__ import annotations

import re
import time
from dataclasses import dataclass, field
from typing import Any

import requests

_LT_URL = "https://api.languagetoolplus.com/v2/check"
_TIMEOUT = 15  # seconds
_MAX_CHARS = 10_000  # LT free tier hard limit

# Cache availability probe (avoid hammering on every request)
_avail_cache: dict[str, Any] = {"ok": None, "ts": 0.0}
_AVAIL_TTL = 300  # seconds


# ─── Data classes ──────────────────────────────────────────────────────────────

@dataclass
class LTMatch:
    message: str
    short_message: str
    offset: int
    length: int
    rule_id: str
    rule_category: str
    severity: str           # "error" | "warning" | "hint" (derived from category)
    context_text: str       # surrounding text snippet
    replacements: list[str] = field(default_factory=list)

    @classmethod
    def from_raw(cls, m: dict[str, Any]) -> "LTMatch":
        rule = m.get("rule") or {}
        cat = (rule.get("category") or {}).get("id", "")
        # Map LT categories to error/warning/hint
        if cat in ("TYPOS", "GRAMMAR", "PUNCTUATION"):
            sev = "error"
        elif cat in ("STYLE", "REDUNDANCY", "COLLOQUIALISMS"):
            sev = "warning"
        else:
            sev = "hint"
        ctx = (m.get("context") or {})
        snippet = ctx.get("text", "")
        repl = [r["value"] for r in (m.get("replacements") or [])[:3]]
        return cls(
            message=m.get("message", ""),
            short_message=m.get("shortMessage", ""),
            offset=m.get("offset", 0),
            length=m.get("length", 0),
            rule_id=rule.get("id", ""),
            rule_category=cat,
            severity=sev,
            context_text=snippet[:120],
            replacements=repl,
        )


@dataclass
class LTResult:
    available: bool
    matches: list[LTMatch] = field(default_factory=list)
    language_detected: str = ""
    error: str | None = None

    @property
    def errors(self) -> list[LTMatch]:
        return [m for m in self.matches if m.severity == "error"]

    @property
    def warnings(self) -> list[LTMatch]:
        return [m for m in self.matches if m.severity == "warning"]

    @property
    def error_count(self) -> int:
        return len(self.errors)

    @property
    def warning_count(self) -> int:
        return len(self.warnings)

    def as_dict(self) -> dict[str, Any]:
        return {
            "available": self.available,
            "error_count": self.error_count,
            "warning_count": self.warning_count,
            "hint_count": len(self.matches) - self.error_count - self.warning_count,
            "language_detected": self.language_detected,
            "error": self.error,
            "top_errors": [
                {
                    "rule": m.rule_id,
                    "category": m.rule_category,
                    "severity": m.severity,
                    "message": m.message,
                    "context": m.context_text,
                    "suggestions": m.replacements,
                }
                for m in self.errors[:8]
            ],
            "top_warnings": [
                {
                    "rule": m.rule_id,
                    "message": m.message,
                    "context": m.context_text,
                    "suggestions": m.replacements,
                }
                for m in self.warnings[:5]
            ],
        }


# ─── Core functions ─────────────────────────────────────────────────────────────

def is_lt_available() -> bool:
    now = time.time()
    if _avail_cache["ok"] is not None and (now - _avail_cache["ts"]) < _AVAIL_TTL:
        return bool(_avail_cache["ok"])
    try:
        r = requests.post(
            _LT_URL,
            data={"text": "This are a test.", "language": "en-US"},
            timeout=8,
        )
        ok = r.status_code == 200
    except Exception:
        ok = False
    _avail_cache["ok"] = ok
    _avail_cache["ts"] = now
    return ok


def check_grammar(
    text: str,
    language: str = "en-US",
    *,
    max_chars: int = _MAX_CHARS,
    disabled_rules: list[str] | None = None,
) -> LTResult:
    """
    Call LanguageTool public API and return structured grammar findings.
    Gracefully returns LTResult(available=False) on any failure.
    """
    text = text[:max_chars]
    if not text.strip():
        return LTResult(available=True)

    params: dict[str, Any] = {
        "text": text,
        "language": language,
        "enabledOnly": "false",
    }
    if disabled_rules:
        params["disabledRules"] = ",".join(disabled_rules)

    # Disable overly noisy rules for academic text
    params["disabledRules"] = ",".join(
        (disabled_rules or []) + [
            "WHITESPACE_RULE",          # line-break false positives in draft text
            "COMMA_PARENTHESIS_WHITESPACE",
            "EN_QUOTES",               # smart quotes
            "UPPERCASE_SENTENCE_START", # citations start with [1]
        ]
    )

    try:
        r = requests.post(_LT_URL, data=params, timeout=_TIMEOUT)
        if r.status_code != 200:
            return LTResult(available=False, error=f"HTTP {r.status_code}")
        data = r.json()
        matches = [LTMatch.from_raw(m) for m in (data.get("matches") or [])]
        lang = (data.get("language") or {}).get("name", "")
        return LTResult(available=True, matches=matches, language_detected=lang)
    except requests.Timeout:
        return LTResult(available=False, error="LanguageTool API timeout")
    except Exception as exc:
        return LTResult(available=False, error=str(exc)[:120])


def grammar_summary(text: str, language: str = "en-US") -> dict[str, Any]:
    """
    High-level dict for QA scoring and UI display.
    Returns verdict = 'pass' / 'warn' / 'fail' based on error density.
    """
    result = check_grammar(text, language=language)
    d = result.as_dict()

    if not result.available:
        d["verdict"] = "unavailable"
        d["grammar_score"] = None  # do not penalise QA if LT is down
        return d

    words = len(re.findall(r"\w+", text))
    error_density = result.error_count / max(1, words) * 1000  # errors per 1000 words

    if error_density >= 15 or result.error_count >= 20:
        verdict = "fail"
        grammar_score = max(0.0, 1.0 - error_density / 30)
    elif error_density >= 6 or result.error_count >= 8:
        verdict = "warn"
        grammar_score = max(0.0, 1.0 - error_density / 20)
    else:
        verdict = "pass"
        grammar_score = min(1.0, 1.0 - error_density / 12)

    d["verdict"] = verdict
    d["grammar_score"] = round(grammar_score, 3)
    d["error_density_per_1000w"] = round(error_density, 2)
    return d


__all__ = ["is_lt_available", "check_grammar", "grammar_summary", "LTResult", "LTMatch"]
