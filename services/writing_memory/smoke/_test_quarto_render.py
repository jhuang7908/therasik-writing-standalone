"""Local smoke test: render revised manuscript JSON via Quarto."""
from __future__ import annotations
import json, sys, os
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent.parent.parent))

os.environ["PATH"] = (
    r"C:\Program Files\Quarto\bin;"
    + os.environ.get("PATH", "")
)

from services.writing_memory.quarto_runner import (
    is_quarto_available, render_manuscript,
)

SRC = Path(__file__).parent / "huNSG_QUAD_revised.json"
OUT_DIR = Path(__file__).parent / "_quarto_out"
OUT_DIR.mkdir(exist_ok=True)

print(f"quarto available: {is_quarto_available()}")
if not is_quarto_available():
    sys.exit(1)

d = json.loads(SRC.read_text(encoding="utf-8"))

manuscript = {
    "title":           "Development of human innate immune responses in a humanized mouse model "
                       "expressing four human myelopoiesis transgenes",
    "target_journal":  "frontiers_immunology",
    "article_type":    "research",
    "authors":         "[FILL: Author names, affiliations]",
    "abstract_text":   next(s["text"] for s in d["sections"] if s["key"] == "abstract"),
    "sections": [
        {"key": s["key"], "title": s["key"].title(), "text": s["text"]}
        for s in d["sections"] if s["key"] != "abstract"
    ],
    "reference_list":  d.get("merged_reference_list") or [],
    "declarations": {
        "data_availability": "[FILL: accession numbers / repository]",
        "competing_interests": "The authors declare no competing interests.",
        "ethics_statement": (
            "All procedures were approved by the Institutional Animal Ethics Committee."
        ),
    },
}

for fmt in ("docx", "html"):
    print(f"\n=== Rendering {fmt} ===")
    rendered = render_manuscript(manuscript, fmt=fmt, workdir=OUT_DIR / fmt)
    print(f"  exit_code: {rendered.get('exit_code')}")
    print(f"  output: {rendered.get('output_path')}")
    if rendered.get("stderr"):
        print(f"  stderr (tail):\n    {rendered['stderr'][-500:]}")
