#!/usr/bin/env python3
"""
Reliability gate for formal analysis reports.

Checks required sections and minimum evidence/adversarial structure:
  - ## Verification Status
  - ## Adversarial Checks
  - ## Sources
"""

from __future__ import annotations

import argparse
import re
from pathlib import Path

VERIFICATION_TAGS = {
    "[verified]",
    "[estimated]",
    "[user-provided]",
    "[inferred]",
    "[unverified]",
}

ADVERSARIAL_OUTCOMES = {"PASS", "WARN", "FAIL"}

FORBIDDEN_ALGO_TERMS = [
    # Generic
    "algorithm",
    "workflow",
    "pipeline",
    "chain-of-thought",
    "",
    "",
    "",
    # Tool/model names commonly considered implementation detail for clients
    "EvoEF2",
    "PRODIGY",
    "MM/GBSA",
    "ThermoMPNN",
    "AntiFold",
    "ESM-IF1",
    "ProteinMPNN",
    "HADDOCK3",
    "ImmuneBuilder",
    "AbLang",
    "AF2",
]

SELF_TALK_PATTERNS = [
    r"\bI think\b",
    r"\bI believe\b",
    r"\bI analyzed\b",
    r"\bI guess\b",
    r"AI",
    r"",
    r"",
    r"",
    r"",
]


def _read_text(path: Path) -> str:
    return path.read_text(encoding="utf-8", errors="replace")


def _extract_section(content: str, heading: str) -> str:
    # Match markdown heading block until next heading of same or higher level.
    pattern = re.compile(
        rf"(?ms)^##\s+{re.escape(heading)}\s*$\n(.*?)(?=^##\s+|\Z)"
    )
    match = pattern.search(content)
    return match.group(1).strip() if match else ""


def _count_bullets(section_text: str) -> int:
    return len(
        re.findall(r"(?m)^\s*[-*]\s+", section_text)
    )


def validate_report(path: Path, client_facing: bool = False) -> tuple[bool, list[str]]:
    errors: list[str] = []
    content = _read_text(path)

    ver = _extract_section(content, "Verification Status")
    adv = _extract_section(content, "Adversarial Checks")
    src = _extract_section(content, "Sources")

    if not ver:
        errors.append("Missing required section: '## Verification Status'")
    if not adv:
        errors.append("Missing required section: '## Adversarial Checks'")
    if not src:
        errors.append("Missing required section: '## Sources'")

    if ver:
        tag_hits = sum(content.count(tag) for tag in VERIFICATION_TAGS)
        if tag_hits < 3:
            errors.append(
                "Verification tags too few: require >=3 tagged claims "
                f"using {sorted(VERIFICATION_TAGS)}"
            )

    if adv:
        bullets = _count_bullets(adv)
        if bullets < 3:
            errors.append("Adversarial checks too few: require >=3 bullet checks")

        outcomes = re.findall(r"\b(PASS|WARN|FAIL)\b", adv)
        if len(outcomes) < 3:
            errors.append("Adversarial checks need PASS/WARN/FAIL outcomes (>=3)")

    if src:
        urls = re.findall(r"https?://[^\s)>\"]+", src)
        if len(urls) < 2:
            errors.append("Sources too few: require >=2 URLs in '## Sources'")

    if client_facing:
        found_algo = [t for t in FORBIDDEN_ALGO_TERMS if t in content]
        if found_algo:
            preview = ", ".join(found_algo[:6])
            errors.append(
                "Client-facing mode forbids algorithm/tool disclosure; found terms: "
                f"{preview}"
            )

        found_self_talk: list[str] = []
        for pat in SELF_TALK_PATTERNS:
            if re.search(pat, content, flags=re.IGNORECASE):
                found_self_talk.append(pat)
        if found_self_talk:
            errors.append(
                "Client-facing mode forbids self-talk wording "
                f"(matched {len(found_self_talk)} pattern(s))."
            )

    return (len(errors) == 0), errors


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Validate report reliability gate sections and evidence tags."
    )
    parser.add_argument(
        "--file",
        required=True,
        help="Path to markdown report file",
    )
    parser.add_argument(
        "--client",
        action="store_true",
        help=(
            "Enable client-facing checks: forbid algorithm/tool disclosure and "
            "self-talk phrasing."
        ),
    )
    args = parser.parse_args()
    path = Path(args.file)

    if not path.exists():
        print(f"[FAIL] File not found: {path}")
        return 2

    ok, errors = validate_report(path, client_facing=args.client)
    if ok:
        mode = "client-facing" if args.client else "standard"
        print(f"[PASS] Reliability gate passed ({mode}): {path}")
        return 0

    print(f"[FAIL] Reliability gate failed: {path}")
    for idx, err in enumerate(errors, 1):
        print(f"  {idx}. {err}")
    return 1


if __name__ == "__main__":
    raise SystemExit(main())

