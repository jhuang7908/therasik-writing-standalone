"""Local smoke test of the new Vale integration.

Calls vale_runner directly (no server) so we don't depend on a redeployed
FastAPI instance.
"""
from __future__ import annotations
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent.parent.parent))

from services.writing_memory.vale_runner import (
    is_vale_available, lint_text, purge_ai_boilerplate,
)

AI_TEXT = (
    "Furthermore, the results demonstrate robust engraftment. "
    "Moreover, IL-1β was significantly elevated. "
    "Taken together, these findings suggest a novel mechanism. "
    "Importantly, MCC950 inhibited inflammasome activation. "
    "In conclusion, the model is suitable for translational research."
)

CLEAN_TEXT = (
    "The huNSG-QUAD platform engrafts human myeloid lineages by week 6. "
    "IP LPS elicited serum TNF at 50 ng/mL and IL-1β at 12-fold over baseline."
)

print(f"vale available: {is_vale_available()}\n")

for label, text in [("AI_BOILERPLATE", AI_TEXT), ("CLEAN", CLEAN_TEXT)]:
    print(f"=== Linting: {label} ===")
    summary = lint_text(text)
    print(f"  total findings: {summary.total}")
    print(f"  by_rule: {summary.counts_by_rule}")
    print(f"  by_severity: {summary.counts_by_severity}")
    if summary.findings:
        for f in summary.findings[:5]:
            print(f"    L{f.line}:C{f.column}  [{f.severity}]  {f.check}: '{f.match}'")
    print()

print("=== Purging boilerplate from AI text ===")
cleaned, removed = purge_ai_boilerplate(AI_TEXT)
print(f"  removed {len(removed)} snippets:")
for s in removed:
    print(f"    - {s!r}")
print(f"\n  cleaned text:\n  {cleaned}\n")

print("=== Re-linting cleaned text ===")
summary2 = lint_text(cleaned)
print(f"  remaining findings: {summary2.total}")
print(f"  by_rule: {summary2.counts_by_rule}")
