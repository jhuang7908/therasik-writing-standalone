"""Audit Vale coverage on final frontiers manuscript."""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from vale_runner import lint_text

txt = (Path(__file__).parent / "huNSG_QUAD_frontiers_final.txt").read_text(encoding="utf-8")
r = lint_text(txt)
d = r.as_dict()

meta = d.get("_meta") or {}
print(f"Total findings : {d['total']}")
print(f"Vale available : {meta.get('vale_available')}")
print(f"By rule        : {d['by_rule']}")
print(f"By severity    : {d['by_severity']}")
print()
for f in (d.get("findings") or [])[:15]:
    print(f"  [{f.get('severity','?'):10s}] {f.get('rule','?'):30s} {str(f.get('message',''))[:70]}")
