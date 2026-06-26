#!/usr/bin/env python3
"""
Summarize Tier A/B/C antibody counts and deduplicated https sources with host labels.
Writes JSON next to curated ada_curated_all_with_ada.json.
"""

from __future__ import annotations

import json
from collections import defaultdict
from pathlib import Path
from urllib.parse import urlparse

REPO = Path(__file__).resolve().parents[1]
ALL_JSON = (
    REPO / "data" / "ADA_reliable_package" / "curated" / "ada_curated_all_with_ada.json"
)
OUT_JSON = REPO / "data" / "ADA_reliable_package" / "curated" / "ada_tier_https_audit.json"


def host_label(url: str) -> str:
    h = urlparse(url).netloc.lower()
    lu = url.lower()
    if "accessdata.fda.gov" in lu:
        return "FDA_accessdata"
    if "clinicaltrials.gov" in h:
        return "ClinicalTrials_gov"
    if "pubmed.ncbi.nlm.nih.gov" in h:
        return "PubMed"
    if "pmc.ncbi.nlm.nih.gov" in lu:
        return "PMC"
    if "ncbi.nlm.nih.gov" in h:
        return "NCBI_other"
    if "ema.europa.eu" in h:
        return "EMA"
    if "springer.com" in h or "link.springer" in lu:
        return "Springer"
    if "frontiersin.org" in h:
        return "Frontiers"
    if "sciencedirect.com" in h:
        return "ScienceDirect"
    if "oup.com" in h or "academic.oup" in h:
        return "OUP"
    if "nejm.org" in h:
        return "NEJM"
    if "drugs.com" in h:
        return "Drugs_com"
    if "rxlist.com" in h:
        return "RxList"
    if "medpagetoday" in h:
        return "MedPageToday"
    if h:
        return h
    return "unknown"


def main() -> None:
    if not ALL_JSON.is_file():
        raise SystemExit(f"Missing {ALL_JSON}")

    bundle = json.loads(ALL_JSON.read_text(encoding="utf-8"))
    rows = bundle.get("antibodies", [])

    tier_antibody_count: dict[str, int] = defaultdict(int)
    tier_unique_urls: dict[str, set[str]] = defaultdict(set)
    tier_by_label: dict[str, dict[str, set[str]]] = defaultdict(lambda: defaultdict(set))

    for ab in rows:
        t = ab.get("evidence_tier") or "?"
        tier_antibody_count[t] += 1
        for u in ab.get("citation_urls") or []:
            if not isinstance(u, str) or not u.startswith("http"):
                continue
            tier_unique_urls[t].add(u)
            tier_by_label[t][host_label(u)].add(u)

    audit = {
        "description": "Per-tier antibody counts (one INN per row, non-duplicate). https URLs deduplicated per tier.",
        "tier_antibody_counts": {k: int(tier_antibody_count.get(k, 0)) for k in ("A", "B", "C")},
        "tier_unique_https_url_counts": {k: len(tier_unique_urls.get(k, set())) for k in ("A", "B", "C")},
        "tier_A_urls_by_source": {
            label: sorted(urls) for label, urls in sorted(tier_by_label["A"].items(), key=lambda x: (-len(x[1]), x[0]))
        },
        "tier_B_urls_by_source": {
            label: sorted(urls) for label, urls in sorted(tier_by_label["B"].items(), key=lambda x: (-len(x[1]), x[0]))
        },
        "tier_C_urls_by_source": {
            label: sorted(urls) for label, urls in sorted(tier_by_label["C"].items(), key=lambda x: (-len(x[1]), x[0]))
        },
    }

    OUT_JSON.parent.mkdir(parents=True, exist_ok=True)
    OUT_JSON.write_text(json.dumps(audit, ensure_ascii=False, indent=2), encoding="utf-8")
    print(json.dumps(audit["tier_antibody_counts"], indent=2))
    print("unique https:", audit["tier_unique_https_url_counts"])
    print(f"Wrote {OUT_JSON}")


if __name__ == "__main__":
    main()
