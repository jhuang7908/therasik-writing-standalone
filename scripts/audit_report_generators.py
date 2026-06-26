"""
audit_report_generators.py — InSynBio Report Style Drift Detector
==================================================================
Scans the codebase for report-generation scripts that define their own
color constants, font registrations, table style helpers, or page-chrome
functions instead of importing from the shared framework.

Usage:
    python scripts/audit_report_generators.py

Exit code:
    0   All generators use the shared framework (or no violations found).
    1   Drift detected — see report for details.
"""
from __future__ import annotations

import os
import re
import sys
from pathlib import Path

SUITE_ROOT = Path(__file__).resolve().parents[1]

ALLOWED_SHARED_FILES = {
    str(SUITE_ROOT / "core" / "reporting" / "theme.py"),
    str(SUITE_ROOT / "core" / "reporting" / "theme_reportlab.py"),
    str(SUITE_ROOT / "core" / "reporting" / "render.py"),
}

COLOR_HEX_RE = re.compile(
    r"""(?:colors\.HexColor|HexColor)\(\s*["']#(?:1F3864|2E5496|EEF2F9|BBBBBB|AAAAAA|C00000|222222|555555|F5F5F5|F0F4F0)["']""",
    re.IGNORECASE,
)
FONT_REG_RE = re.compile(
    r"""(?:registerFont|TTFont)\s*\(\s*["'](?:MainFont|MainFontBd)""",
)
TABLE_STYLE_RE = re.compile(
    r"""def\s+make_table\s*\(""",
)
PAGE_CHROME_RE = re.compile(
    r"""def\s+page_header_footer\s*\(""",
)
COLOR_TUPLE_RE = re.compile(
    r"""(?:TABLE_HEADER_BG|TABLE_ALT_BG|TABLE_BORDER|H_COLORS|CODE_BG)\s*=""",
)

PATTERNS = [
    ("Hardcoded InSynBio hex color", COLOR_HEX_RE),
    ("Local font registration (MainFont/MainFontBd)", FONT_REG_RE),
    ("Local make_table() definition", TABLE_STYLE_RE),
    ("Local page_header_footer() definition", PAGE_CHROME_RE),
    ("Hardcoded RGB color tuple constant", COLOR_TUPLE_RE),
]

SCAN_GLOBS = [
    "projects/*/generate_*report*.py",
    "projects/*/**/*report*.py",
    "scripts/*report*.py",
    "scripts/md_to_pdf.py",
    "core/evaluation/client_report.py",
]


DELEGATION_RE = re.compile(r"""RL\.|_T\.|THEME\.""")

def _is_thin_wrapper(lines: list[str], def_line_idx: int) -> bool:
    """Check if a function def is a thin wrapper delegating to RL."""
    for offset in range(1, min(4, len(lines) - def_line_idx)):
        body_line = lines[def_line_idx + offset].strip()
        if not body_line or body_line.startswith("#"):
            continue
        if DELEGATION_RE.search(body_line):
            return True
        break
    return False


def scan_file(path: Path) -> list[tuple[str, int, str]]:
    violations: list[tuple[str, int, str]] = []
    norm = str(path.resolve())
    if norm in ALLOWED_SHARED_FILES:
        return violations
    try:
        text = path.read_text(encoding="utf-8", errors="replace")
    except Exception:
        return violations
    lines = text.splitlines()
    in_fallback = False
    for line_no, line in enumerate(lines, 1):
        stripped = line.strip()
        if stripped == "else:":
            in_fallback = True
        elif in_fallback and stripped and not stripped.startswith("#") and not line[0].isspace():
            in_fallback = False

        if DELEGATION_RE.search(line):
            continue
        if in_fallback:
            continue

        for desc, pattern in PATTERNS:
            if pattern.search(line):
                if pattern is TABLE_STYLE_RE or pattern is PAGE_CHROME_RE:
                    if _is_thin_wrapper(lines, line_no - 1):
                        continue
                violations.append((desc, line_no, stripped[:120]))
    return violations


def main():
    all_paths: set[Path] = set()
    for g in SCAN_GLOBS:
        all_paths.update(SUITE_ROOT.glob(g))

    total_violations = 0
    files_with_issues = 0

    for p in sorted(all_paths):
        v = scan_file(p)
        if v:
            files_with_issues += 1
            rel = p.relative_to(SUITE_ROOT)
            print(f"\n{'='*72}")
            print(f"  {rel}  ({len(v)} violation{'s' if len(v)>1 else ''})")
            print(f"{'='*72}")
            for desc, lineno, snippet in v:
                total_violations += 1
                print(f"  L{lineno:>4}  [{desc}]")
                print(f"        {snippet}")

    print(f"\n{'─'*72}")
    if total_violations == 0:
        print("  ✅  No style-drift violations found.")
        print(f"      Scanned {len(all_paths)} file(s).")
    else:
        print(f"  ⚠️  {total_violations} violation(s) in {files_with_issues} file(s).")
        print(f"      Scanned {len(all_paths)} file(s).")
        print()
        print("  Fix: replace local definitions with imports from core.reporting:")
        print("    from core.reporting.theme_reportlab import RL")
        print("    from core.reporting.theme import THEME")
    print(f"{'─'*72}")

    return 1 if total_violations > 0 else 0


if __name__ == "__main__":
    sys.exit(main())
