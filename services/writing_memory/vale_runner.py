"""Vale prose-linter wrapper for the writing_memory service.

Calls the locally-installed `vale` CLI with the AbEngineCore style pack
(see `.vale.ini` and `vale_styles/`).

Public API:
    lint_text(text, fmt="md") -> list[ValeFinding]
    purge_ai_boilerplate(text) -> tuple[str, list[str]]
    lint_summary(text) -> ValeSummary
"""
from __future__ import annotations

import json
import os
import re
import shutil
import subprocess
import tempfile
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

SERVICE_ROOT = Path(__file__).resolve().parent
VALE_INI = SERVICE_ROOT / ".vale.ini"

# Common fallback locations for the Vale binary (Windows winget install does
# not always propagate PATH to subprocess parents).
_VALE_FALLBACKS: tuple[Path, ...] = (
    Path("/usr/local/bin/vale"),
    Path("/usr/bin/vale"),
    Path.home()
    / "AppData/Local/Microsoft/WinGet/Packages/errata-ai.Vale_Microsoft.Winget.Source_8wekyb3d8bbwe/vale.exe",
    Path.home() / "AppData/Local/Microsoft/WinGet/Links/vale.exe",
    Path("C:/Program Files/Vale/vale.exe"),
    Path("/opt/homebrew/bin/vale"),
)


def _resolve_vale_binary() -> str | None:
    cli = shutil.which("vale")
    if cli:
        return cli
    for cand in _VALE_FALLBACKS:
        if cand.is_file():
            return str(cand)
    return None


@dataclass
class ValeFinding:
    line: int
    column: int
    check: str
    severity: str
    message: str
    match: str

    @classmethod
    def from_json(cls, entry: dict[str, Any]) -> "ValeFinding":
        return cls(
            line=int(entry.get("Line", 0)),
            column=int((entry.get("Span") or [0])[0]),
            check=str(entry.get("Check", "")),
            severity=str(entry.get("Severity", "warning")),
            message=str(entry.get("Message", "")),
            match=str(entry.get("Match", "")),
        )


@dataclass
class ValeSummary:
    findings: list[ValeFinding] = field(default_factory=list)
    counts_by_rule: dict[str, int] = field(default_factory=dict)
    counts_by_severity: dict[str, int] = field(default_factory=dict)
    vale_available: bool = True
    error: str | None = None

    @property
    def total(self) -> int:
        return len(self.findings)

    def as_dict(self) -> dict[str, Any]:
        return {
            "total": self.total,
            "by_rule": self.counts_by_rule,
            "by_severity": self.counts_by_severity,
            "vale_available": self.vale_available,
            "error": self.error,
            "findings": [f.__dict__ for f in self.findings],
        }


def is_vale_available() -> bool:
    return _resolve_vale_binary() is not None


def lint_text(text: str, fmt: str = "md") -> ValeSummary:
    """Run Vale on raw text and return structured findings."""
    vale_bin = _resolve_vale_binary()
    if not vale_bin:
        return ValeSummary(
            vale_available=False,
            error="vale CLI not found on PATH or known install locations",
        )

    suffix = f".{fmt}" if fmt in {"md", "txt", "qmd"} else ".md"
    with tempfile.NamedTemporaryFile(
        mode="w", suffix=suffix, delete=False, encoding="utf-8"
    ) as tmp:
        tmp.write(text)
        tmp_path = tmp.name
    try:
        result = subprocess.run(
            [vale_bin, "--output=JSON", "--config", str(VALE_INI), tmp_path],
            capture_output=True,
            text=True,
            timeout=60,
            cwd=str(SERVICE_ROOT),
        )
        raw = result.stdout.strip()
        if not raw:
            return ValeSummary()
        payload = json.loads(raw)
        all_findings: list[ValeFinding] = []
        for _path, entries in payload.items():
            for entry in entries or []:
                all_findings.append(ValeFinding.from_json(entry))

        by_rule: dict[str, int] = {}
        by_sev: dict[str, int] = {}
        for f in all_findings:
            by_rule[f.check] = by_rule.get(f.check, 0) + 1
            by_sev[f.severity] = by_sev.get(f.severity, 0) + 1

        return ValeSummary(
            findings=all_findings,
            counts_by_rule=by_rule,
            counts_by_severity=by_sev,
        )
    except subprocess.TimeoutExpired:
        return ValeSummary(vale_available=True, error="vale timed out (60 s)")
    except json.JSONDecodeError as exc:
        return ValeSummary(vale_available=True, error=f"vale JSON parse: {exc}")
    finally:
        try:
            os.unlink(tmp_path)
        except OSError:
            pass


_BOILERPLATE_PATTERNS = [
    r"\bFurthermore,\s*",
    r"\bMoreover,\s*",
    r"\bAdditionally,\s*",
    r"\bIn addition,\s*",
    r"\bNotably,\s*",
    r"\bImportantly,\s*",
    r"\bInterestingly,\s*",
    r"\bConsequently,\s*",
    r"\bTherefore,\s+",
    r"Taken together,?\s*",
    r"Collectively,?\s*",
    r"These findings demonstrate that[^\.]+\.",
    r"These results suggest that[^\.]+\.",
    r"These data indicate that[^\.]+\.",
    r"Together, these (?:findings|results|observations)[^\.]+\.",
    r"It is worth noting that\s*",
    r"It is important to note that\s*",
    r"In conclusion,\s*",
    r"To summarize,?\s*",
    r"In summary,?\s*",
]


def purge_ai_boilerplate(text: str) -> tuple[str, list[str]]:
    """Strip AI-style boilerplate transitions and summary phrases.

    Returns the cleaned text and a list of removed snippets (for audit).
    Idempotent — safe to call multiple times.
    """
    removed: list[str] = []

    def _capture(match: re.Match) -> str:
        removed.append(match.group(0))
        return ""

    cleaned = text
    for pat in _BOILERPLATE_PATTERNS:
        cleaned = re.sub(pat, _capture, cleaned, flags=re.IGNORECASE)

    cleaned = re.sub(r"[ \t]+", " ", cleaned)
    cleaned = re.sub(r" *\n *", "\n", cleaned)
    cleaned = re.sub(r"\n{3,}", "\n\n", cleaned)

    return cleaned.strip(), removed


__all__ = [
    "ValeFinding",
    "ValeSummary",
    "is_vale_available",
    "lint_text",
    "purge_ai_boilerplate",
]
