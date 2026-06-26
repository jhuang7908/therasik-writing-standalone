"""Render full manuscript text from figdraft JSON."""
import json, re
from pathlib import Path

src = Path(
    r"d:\InSynBio-AI-Research\Antibody_Engineer_Suite\services\writing_memory\smoke"
    r"\huNSG_QUAD_figdraft_20260527T011815Z.json"
)
d = json.loads(src.read_text(encoding="utf-8"))
secs = {s["key"]: s for s in d["sections"]}
plan = d.get("plan") or {}
refs = d.get("merged_reference_list") or []

title = (
    plan.get("suggested_title")
    or "Development of human innate immune responses in a humanized mouse model "
       "expressing four human myelopoiesis transgenes"
)

out = []
out.append("=" * 80)
out.append(title.upper())
out.append("=" * 80)
out.append("")
out.append("Target journal: eLife (style) / Frontiers in Immunology (scope)")
out.append(f"Total words (body): {sum(len(re.findall(chr(39)+'|[A-Za-z0-9-]+', s['text'])) for s in d['sections'])}")
out.append(f"References: {len(refs)}")
out.append("")
out.append("─" * 80)

for key in ("abstract", "introduction", "methods", "results", "discussion"):
    sec = secs.get(key)
    if not sec:
        continue
    wc = len(re.findall(r"[A-Za-z0-9'-]+", sec["text"]))
    out.append("")
    out.append(f"{'─'*80}")
    out.append(f"{key.upper()}  [{wc} words]")
    out.append("─" * 80)
    out.append("")
    out.append(sec["text"].strip())
    out.append("")

out.append("")
out.append("─" * 80)
out.append(f"REFERENCES  [{len(refs)} entries]")
out.append("─" * 80)
out.append("")
for i, ref in enumerate(refs, 1):
    out.append(f"{i}. {ref}")
    out.append("")

manuscript = "\n".join(out)
out_path = src.parent / "huNSG_QUAD_figdraft_manuscript.txt"
out_path.write_text(manuscript, encoding="utf-8")
print(manuscript)
print(f"\n[Saved to {out_path}]")
