#!/usr/bin/env python3
"""Validate SEED_FAMOUS_V1 PMIDs against PubMed title/journal."""
from __future__ import annotations

import json
import re
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO))

from services.writing_memory.references.pubmed_client import efetch

SEED = REPO / "services" / "writing_memory" / "data" / "article_type_cohorts" / "SEED_FAMOUS_V1.json"

# Keywords expected from seed label (lowercase fragments)
_LABEL_HINTS = [
    (r"nat rev immunol", ["nat rev immunol", "nature reviews immunology"]),
    (r"nat rev cancer", ["nat rev cancer", "nature reviews cancer"]),
    (r"nat rev drug", ["nat rev drug", "nature reviews drug"]),
    (r"nat rev mol", ["nat rev mol", "nature reviews molecular"]),
    (r"nat rev clin", ["nat rev clin", "nature reviews clinical"]),
    (r"prisma", ["prisma"]),
    (r"nejm", ["n engl j med", "nejm"]),
    (r"lancet", ["lancet"]),
    (r"bmj", ["bmj"]),
    (r"nature protocol", ["nat protoc", "nature protocols"]),
    (r"plos med", ["plos med"]),
    (r"elife", ["elife"]),
    (r"science", ["science"]),
    (r"cell", ["cell"]),
    (r"nat med", ["nat med"]),
    (r"sci transl", ["sci transl med"]),
]


def _expected_from_label(label: str) -> list[str]:
    ll = label.lower()
    out: list[str] = []
    for pat, hints in _LABEL_HINTS:
        if re.search(pat, ll):
            out.extend(hints)
    return out


def main() -> int:
    doc = json.loads(SEED.read_text(encoding="utf-8"))
    pmids: list[str] = []
    meta: dict[str, tuple[str, str]] = {}
    for ctype, ents in doc["seeds"].items():
        for e in ents:
            pmids.append(str(e["pmid"]))
            meta[str(e["pmid"])] = (ctype, e.get("label", ""))

    bad = []
    for rec in efetch(pmids):
        label = meta[rec.pmid][1]
        hints = _expected_from_label(label)
        blob = f"{rec.journal} {rec.journal_abbrev} {rec.title}".lower()
        ok = not hints or any(h in blob for h in hints)
        if not ok:
            bad.append((rec.pmid, label, rec.journal_abbrev, rec.title[:70]))
        print(f"{'OK' if ok else 'BAD':3} {rec.pmid} | {label[:45]:45} | {rec.journal_abbrev[:25]:25} | {rec.title[:50]}")

    print(f"\nMismatch count: {len(bad)}/{len(pmids)}")
    return 1 if bad else 0


if __name__ == "__main__":
    raise SystemExit(main())
