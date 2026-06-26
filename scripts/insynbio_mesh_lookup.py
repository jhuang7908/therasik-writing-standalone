"""
InSynBio MeSH Lookup CLI — query NLM MeSH API to resolve a keyword to its official
MeSH tree position, scope note, and related biomedical domain(s).

API: NCBI E-utilities (esearch + efetch on MeSH database)
No API key required; key optional to raise rate limit from 3 to 10 req/s.

Usage:
    python scripts/insynbio_mesh_lookup.py query "CRISPR-Cas"
    python scripts/insynbio_mesh_lookup.py query "checkpoint inhibitor" --top 5
    python scripts/insynbio_mesh_lookup.py detect --title "Structural basis of PD-L1 inhibition"
    python scripts/insynbio_mesh_lookup.py detect --abstract-file paper/abstract.txt
    python scripts/insynbio_mesh_lookup.py tree-path "D000906"   # lookup by MeSH UI
"""

from __future__ import annotations

import argparse
import json
import os
import sys
import time
from pathlib import Path
from typing import Any

try:
    import requests
except ImportError:
    sys.exit("ERROR: 'requests' not installed. Run: pip install requests")

EUTILS_BASE = "https://eutils.ncbi.nlm.nih.gov/entrez/eutils"
MESH_BROWSER_API = "https://id.nlm.nih.gov/mesh/sparql"

NCBI_API_KEY = os.environ.get("NCBI_API_KEY", "")
NCBI_EMAIL = os.environ.get("NCBI_EMAIL", "research@insynbio.com")


# ── MeSH Tree prefix → human-readable category ──────────────────────────────
MESH_TREE_CATEGORIES = {
    "A": "Anatomy",
    "B": "Organisms",
    "C": "Diseases",
    "D": "Chemicals and Drugs",
    "E": "Analytical, Diagnostic and Therapeutic Techniques",
    "F": "Psychiatry and Psychology",
    "G": "Phenomena and Processes",
    "H": "Disciplines and Occupations",
    "I": "Anthropology, Education, Sociology",
    "J": "Technology, Industry, Agriculture",
    "K": "Humanities",
    "L": "Information Science",
    "M": "Named Groups",
    "N": "Health Care",
    "V": "Publication Characteristics",
    "Z": "Geographicals",
}

# Map MeSH tree prefixes → InSynBio platform domain labels
TREE_TO_DOMAIN = {
    "C04": "Oncology",
    "C20": "Immunology / Autoimmunity",
    "C01": "Infectious Disease",
    "C14": "Cardiovascular Disease",
    "C08": "Pulmonary / Respiratory",
    "C10": "Neurology",
    "F03": "Psychiatry / Mental Health",
    "C19": "Endocrinology / Metabolic",
    "C06": "Gastroenterology / Hepatology",
    "C12": "Nephrology / Urology",
    "C05": "Musculoskeletal / Rheumatology",
    "C17": "Dermatology",
    "C11": "Ophthalmology",
    "C15": "Hematology",
    "C13": "Reproductive Medicine",
    "C16": "Pediatrics / Congenital",
    "C18": "Rare / Metabolic Disease",
    "D": "Chemicals / Therapeutics / Drug Development",
    "E": "Analytical / Diagnostic / Therapeutic Techniques",
    "G01": "Bioinformatics / Mathematical Modeling",
    "G02": "Structural Biology / Biochemistry",
    "G04": "Cell Biology",
    "G05": "Genetics / Genomics",
    "G07": "Nutrition / Physiology",
    "H01": "Natural Sciences (Biology, Chemistry)",
    "J": "Technology / Industry / Biomedical Engineering",
    "L01": "Information Science / Bioinformatics",
    "N": "Health Care / Epidemiology / Public Health",
}


def _base_params() -> dict[str, Any]:
    p: dict[str, Any] = {"tool": "insynbio_mesh_lookup", "email": NCBI_EMAIL}
    if NCBI_API_KEY:
        p["api_key"] = NCBI_API_KEY
    return p


def _get_json(url: str, params: dict) -> Any:
    p = {**_base_params(), "retmode": "json", **params}
    for attempt in range(3):
        resp = requests.get(url, params=p, timeout=15)
        if resp.status_code == 429:
            time.sleep(3 * (attempt + 1))
            continue
        resp.raise_for_status()
        return resp.json()
    raise RuntimeError(f"NCBI JSON API failed: {url}")


def _get_text(url: str, params: dict) -> str:
    """For efetch MeSH — returns plain text (XML/MEDLINE format)."""
    p = {**_base_params(), **params}
    for attempt in range(3):
        resp = requests.get(url, params=p, timeout=15)
        if resp.status_code == 429:
            time.sleep(3 * (attempt + 1))
            continue
        resp.raise_for_status()
        return resp.text
    raise RuntimeError(f"NCBI text API failed: {url}")


def esearch_mesh(term: str, retmax: int = 5) -> list[str]:
    """Search MeSH for a term, return list of MeSH UIDs."""
    data = _get_json(f"{EUTILS_BASE}/esearch.fcgi", {
        "db": "mesh", "term": term, "retmax": retmax,
    })
    return data.get("esearchresult", {}).get("idlist", [])


def efetch_mesh(uid: str) -> dict:
    """Fetch MeSH record details via esummary (JSON) — includes tree numbers."""
    data = _get_json(f"{EUTILS_BASE}/esummary.fcgi", {
        "db": "mesh", "id": uid,
    })
    doc = data.get("result", {}).get(uid, {})
    if not doc:
        return {"uid": uid, "heading": "(not found)", "tree_numbers": [], "synonyms": []}

    # Extract tree numbers from ds_idxlinks
    tree_numbers: list[str] = []
    for link in doc.get("ds_idxlinks", []):
        tn = link.get("treenum", "")
        if tn:
            tree_numbers.append(tn)

    # Primary heading is first entry in ds_meshterms
    terms = doc.get("ds_meshterms", [])
    heading = terms[0] if terms else "(unknown)"

    return {
        "uid": uid,
        "mesh_ui": doc.get("ds_meshui", uid),
        "heading": heading,
        "tree_numbers": tree_numbers,
        "scope_note": doc.get("ds_scopenote", ""),
        "synonyms": terms[1:6],           # first few synonyms
        "year_introduced": doc.get("ds_yearintroduced", ""),
    }


def mesh_to_domain(tree_numbers: list[str]) -> list[str]:
    """Map MeSH tree numbers to InSynBio platform domain labels."""
    domains = set()
    for tn in tree_numbers:
        if not tn or not tn[0].isalpha():
            continue  # skip supplementary concept records (@, Y, etc.)
        matched = False
        # Try longest prefix first (C04 before C)
        for length in (3, 1):
            prefix = tn[:length]
            if prefix in TREE_TO_DOMAIN:
                domains.add(TREE_TO_DOMAIN[prefix])
                matched = True
                break
        if not matched:
            cat = tn[0]
            label = MESH_TREE_CATEGORIES.get(cat)
            if label:
                domains.add(label)
    return sorted(domains)


def cmd_query(args: argparse.Namespace) -> None:
    """Search MeSH for a keyword and show tree position + domain mapping."""
    term = args.term
    print(f"[MeSH] Searching: '{term}' …")
    uids = esearch_mesh(term, retmax=args.top)
    if not uids:
        print(f"[MeSH] No results for '{term}'.")
        return

    results = []
    for uid in uids:
        record = efetch_mesh(uid)
        tree_numbers = record.get("tree_numbers", [])
        domains = mesh_to_domain(tree_numbers)
        category_names = sorted(set(
            MESH_TREE_CATEGORIES.get(tn[0], "Unknown") for tn in tree_numbers
        ))
        results.append({
            "uid": uid,
            "mesh_ui": record.get("mesh_ui", uid),
            "heading": record.get("heading", "(unknown)"),
            "scope_note": record.get("scope_note", "")[:200],
            "tree_numbers": tree_numbers,
            "mesh_categories": category_names,
            "insynbio_domains": domains,
            "synonyms": record.get("synonyms", [])[:5],
        })
        time.sleep(0.35)  # polite

    _output(results, args.out)
    if not args.out:
        for r in results:
            print(f"\n  MeSH: {r['heading']} [{r['mesh_ui']}]")
            print(f"  Tree: {', '.join(r['tree_numbers']) or 'N/A'}")
            print(f"  Category: {', '.join(r['mesh_categories'])}")
            print(f"  Platform domain: {', '.join(r['insynbio_domains']) or '(general)'}")
            if r["scope_note"]:
                print(f"  Scope: {r['scope_note'][:120]}…")


def cmd_detect(args: argparse.Namespace) -> None:
    """
    Auto-detect PubMed domains from a manuscript title / abstract.
    Extracts candidate terms, searches MeSH for each, returns domain list.
    """
    if args.abstract_file:
        text = Path(args.abstract_file).read_text(encoding="utf-8", errors="replace")
    elif args.title:
        text = args.title
    else:
        sys.exit("ERROR: provide --title 'text' or --abstract-file path")

    import re
    # Extract biomedical candidate terms:
    #  1. Drug names: ends in -mab, -nib, -zumab, -lib, -tide, -stat
    #  2. All-caps abbreviations (CRISPR, GWAS, mRNA, ADC, VHH, etc.)
    #  3. Capitalized noun phrases
    #  4. Disease keywords: cancer, tumor, carcinoma, lymphoma, sarcoma, leukemia
    #  5. Key biomedical nouns (>5 chars, lowercase)
    candidates_raw: list[str] = []
    # drug names
    candidates_raw += re.findall(r"\b\w+(?:mab|nib|zumab|lib|tide|stat|xib|kin|cin)\b", text, re.I)
    # abbreviations
    candidates_raw += re.findall(r"\b(?:CRISPR|mRNA|siRNA|scRNA|CAR-T|PD-L1|PD-1|CTLA-4|ADC|VHH|GWAS|ADMET|iPSC|NLP|EHR|AUC|HTS|NGS|WGS|scATAC|ctDNA|IHC|FISH|ELISA|PCR|qPCR|MRI|PET|CT|ARDS|ICU)\b", text)
    # disease-class words
    candidates_raw += re.findall(r"\b\w*(?:cancer|tumor|tumour|carcinoma|lymphoma|sarcoma|leukemia|glioma|melanoma|adenoma|neoplasm)\w*\b", text, re.I)
    # capitalized multi-word terms
    candidates_raw += re.findall(r"\b[A-Z][a-z]{3,}(?:\s[A-Z][a-z]{3,})?\b", text)
    # key long lowercase terms (anatomy, physiology, disease)
    candidates_raw += re.findall(r"\b(?:randomized|metastatic|pembrolizumab|immunotherapy|checkpoint|antibody|biomarker|genomics|transcriptomics|proteomics|microbiome|mitochondria|apoptosis|autophagy|senescence|fibrosis|inflammation|angiogenesis|thrombosis|ischemia|nephropathy|neuropathy|cardiomyopathy|hepatitis|cirrhosis|diabetes|hypertension|arrhythmia|atherosclerosis|osteoporosis|arthritic|rheumatoid|psoriasis|dermatitis|glaucoma|retinopathy|schizophrenia|depression|epilepsy|dementia|alzheimer|parkinson)\b", text, re.I)
    candidates = list(dict.fromkeys(t.strip() for t in candidates_raw if len(t.strip()) >= 4))[:12]

    print(f"[MeSH] Auto-detect from text. Candidate terms ({len(candidates)}): {candidates}")

    domain_votes: dict[str, int] = {}
    mesh_hits: list[dict] = []

    for term in candidates[:8]:  # limit to 8 searches to be polite
        uids = esearch_mesh(term, retmax=1)
        if uids:
            record = efetch_mesh(uids[0])
            tree_numbers = record.get("tree_numbers", [])
            domains = mesh_to_domain(tree_numbers)
            for d in domains:
                domain_votes[d] = domain_votes.get(d, 0) + 1
            mesh_hits.append({
                "term": term,
                "heading": record.get("heading", ""),
                "tree_numbers": tree_numbers,
                "domains": domains,
            })
        time.sleep(0.4)

    ranked_domains = sorted(domain_votes.items(), key=lambda x: -x[1])
    result = {
        "input_text": text[:200],
        "candidate_terms": candidates[:8],
        "mesh_hits": mesh_hits,
        "detected_domains": [d for d, _ in ranked_domains],
        "top_domain": ranked_domains[0][0] if ranked_domains else "general_biomedical",
    }

    _output(result, args.out)
    if not args.out:
        print(f"\n[MeSH] Detected domains (ranked by evidence):")
        for domain, votes in ranked_domains:
            print(f"  {votes:2d}x  {domain}")
        print(f"\n[MeSH] Top domain: {result['top_domain']}")


def cmd_tree_path(args: argparse.Namespace) -> None:
    """Fetch a MeSH record by UID and show its tree path."""
    record = efetch_mesh(args.uid)
    tree_numbers = record.get("tree_numbers", [])
    domains = mesh_to_domain(tree_numbers)
    result = {
        "uid": args.uid,
        "heading": record.get("heading", ""),
        "mesh_ui": record.get("mesh_ui", args.uid),
        "tree_numbers": tree_numbers,
        "mesh_categories": sorted(set(MESH_TREE_CATEGORIES.get(tn[0], "?") for tn in tree_numbers)),
        "insynbio_domains": domains,
        "scope_note": record.get("scope_note", ""),
        "synonyms": record.get("synonyms", []),
    }
    _output(result, args.out)
    if not args.out:
        print(json.dumps(result, indent=2, ensure_ascii=False))


def _output(data: Any, out_path: str | None) -> None:
    text = json.dumps(data, indent=2, ensure_ascii=False)
    if out_path:
        Path(out_path).write_text(text, encoding="utf-8")
        print(f"[MeSH] Written → {out_path}")
    # always print JSON when out_path specified (for piping)


def main() -> None:
    parser = argparse.ArgumentParser(
        prog="insynbio_mesh_lookup",
        description="Query NLM MeSH API — resolve keywords to official MeSH tree + InSynBio domain",
    )
    sub = parser.add_subparsers(dest="cmd", required=True)

    # query
    p_q = sub.add_parser("query", help="Search MeSH for a keyword")
    p_q.add_argument("term", help="Search term (e.g. 'CRISPR-Cas', 'checkpoint inhibitor')")
    p_q.add_argument("--top", type=int, default=3, help="Max results (default 3)")
    p_q.add_argument("--out", default=None, help="Write JSON to file")

    # detect
    p_d = sub.add_parser("detect", help="Auto-detect domain from title or abstract")
    p_d.add_argument("--title", default=None, help="Manuscript title string")
    p_d.add_argument("--abstract-file", default=None, help="Path to abstract text file")
    p_d.add_argument("--out", default=None, help="Write JSON to file")

    # tree-path
    p_t = sub.add_parser("tree-path", help="Fetch MeSH record by UID")
    p_t.add_argument("uid", help="MeSH UID (e.g. D000906) or numeric ID")
    p_t.add_argument("--out", default=None, help="Write JSON to file")

    args = parser.parse_args()
    dispatch = {"query": cmd_query, "detect": cmd_detect, "tree-path": cmd_tree_path}
    dispatch[args.cmd](args)


if __name__ == "__main__":
    main()
