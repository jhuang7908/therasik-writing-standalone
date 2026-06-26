#!/usr/bin/env python3
"""Build Review B reference library (JSON + MD) for manuscript revision.

Maps each numbered reference in the AT de novo review to local corpus tier,
file paths, and manual-PDF status. Output is internal only — not for ScholarOne.

Usage:
  python scripts/build_review_b_reference_library.py
  python scripts/build_review_b_reference_library.py --manuscript paper/Submission_Package/Manuscript_DeNovo_AI_Landscape_Review_AT.md
"""
from __future__ import annotations

import argparse
import json
import re
from datetime import datetime, timezone
from pathlib import Path
from xml.sax.saxutils import escape as xml_escape
from xml.sax.saxutils import quoteattr

REPO = Path(__file__).resolve().parents[1]
DEFAULT_MD = REPO / "paper" / "Submission_Package" / "Manuscript_DeNovo_AI_Landscape_Review_AT.md"
CORPUS_RAW = REPO / "data" / "denovo_literature" / "papers_raw"
MANUAL_PDF = REPO / "data" / "denovo_literature" / "manual_pdfs"
OUT_DIR = REPO / "paper" / "Submission_Package" / "submission_internal" / "Literature_Library"
DEFAULT_LIT_EXPORT = (
    REPO / "paper" / "Submission_Package" / "ScholarOne_Upload" / "Review_B_DeNovo" / "03_Literature"
)

# Ref number → corpus id when DOI match is ambiguous or absent
REF_CORPUS_OVERRIDE: dict[int, str] = {
    1: "kaplon_mabs_2025",
    2: "raybould_pnas_developability_2019",
    4: "alphafold2_nature_2021",
    3: "diffab_2022",
    13: "bindcraft_nature_2025",
    14: "companion_vhh_manuscript",
    15: "jam2_nabla_report_2025",
    17: "mmdesign_zenodo_2026",
    18: "germinal_biorxiv_2025",
    19: "biomap_lgr5_vhh_2025",
    20: "inventcures_comparison_2025",
    21: "fimmu_cpd_antibody_review_2025",
    22: "thera_sabdab_nar_2020",
    25: "rfantibody_github_readme",
    27: "alphafold3_nature_2024",
    29: "diffab_2022",
    30: "dyab_aaai_2025",
    31: "dymean_icml_2023",
    32: "boltz2_biorxiv_2025",
    33: "antifold_bioadv_2025",
    34: "fitness_landscape_ab2_2025",
    35: "aintibody_challenge_announce",
    37: "bruggemann_transgenic_2015",
}

REF_SOURCE_OVERRIDE: dict[int, dict] = {
    14: {
        "source_type": "companion_manuscript",
        "local_path": "paper/Submission_Package/Manuscript_VHH_Humanization.md",
        "tier": "FULL",
        "notes": "Same author group; submitted companion OR",
    },
    23: {
        "source_type": "clinical_registry",
        "url": "https://clinicaltrials.gov/study/NCT07050511",
        "tier": "WEB",
        "notes": "GB-0669 Phase I registry entry",
    },
    24: {
        "source_type": "clinical_registry",
        "url": "https://anzctr.org.au/Trial/Registration/TrialReview.aspx?id=385123",
        "tier": "WEB",
        "notes": "ABS-101 Australia Phase I",
    },
    36: {
        "source_type": "trade_press",
        "url": "https://www.genengnews.com/topics/drug-discovery/",
        "tier": "WEB",
        "notes": "Partnership news; verify URL at revision",
    },
}


def tier(chars: int) -> str:
    if chars >= 20_000:
        return "FULL"
    if chars >= 5_000:
        return "PARTIAL"
    if chars > 0:
        return "ABSTRACT"
    return "NONE"


def norm_doi(s: str | None) -> str | None:
    if not s:
        return None
    s = s.strip().lower()
    s = s.replace("https://doi.org/", "").replace("http://doi.org/", "")
    s = s.replace("doi:", "").strip().rstrip(".")
    return s


def parse_references(md_text: str) -> list[dict]:
    block = md_text.split("## References")[-1].split("\n---\n")[0]
    rows: list[dict] = []
    for line in block.splitlines():
        m = re.match(r"^(\d+)\.\s+(.+)$", line.strip())
        if not m:
            continue
        num = int(m.group(1))
        cite = m.group(2).strip()
        doi_m = re.search(r"doi:?(10\.\S+)", cite, re.I)
        doi = norm_doi(doi_m.group(1).rstrip(".") if doi_m else None)
        if not doi:
            ax = re.search(r"arXiv:([\d.]+)", cite, re.I)
            if ax:
                doi = f"10.48550/arxiv.{ax.group(1)}"
        rows.append({"ref": num, "citation": cite, "doi": doi})
    return rows


def load_corpus_index() -> dict[str, dict]:
    """DOI → best corpus record from papers_raw/*.json"""
    by_doi: dict[str, dict] = {}
    by_id: dict[str, dict] = {}
    for p in CORPUS_RAW.glob("*.json"):
        try:
            o = json.loads(p.read_text(encoding="utf-8"))
        except Exception:
            continue
        cid = p.stem
        o["_corpus_file"] = str(p.relative_to(REPO)).replace("\\", "/")
        o["_corpus_id"] = cid
        ft = o.get("full_text") or o.get("abstract") or ""
        o["_char_count"] = len(ft)
        o["_tier"] = tier(len(o.get("full_text") or ""))
        by_id[cid] = o
        d = norm_doi(o.get("doi"))
        if d and (d not in by_doi or o["_char_count"] > by_doi[d].get("_char_count", 0)):
            by_doi[d] = o
    return {"by_doi": by_doi, "by_id": by_id}


def manual_pdf_for(corpus_id: str, doi: str | None) -> str | None:
    for base in (corpus_id, doi.replace("/", "_") if doi else ""):
        if not base:
            continue
        for ext in (".pdf", ".PDF"):
            p = MANUAL_PDF / f"{base}{ext}"
            if p.exists():
                return str(p.relative_to(REPO)).replace("\\", "/")
    if doi:
        slug = doi.split("/")[-1]
        for p in MANUAL_PDF.glob(f"*{slug}*"):
            return str(p.relative_to(REPO)).replace("\\", "/")
    return None


def build_entry(ref: dict, index: dict) -> dict:
    n = ref["ref"]
    doi = ref["doi"]
    entry: dict = {
        "ref": n,
        "citation": ref["citation"],
        "doi": doi,
        "corpus_id": None,
        "corpus_file": None,
        "text_tier": "NONE",
        "char_count": 0,
        "provenance": None,
        "manual_pdf": None,
        "source_type": "peer_literature",
        "revision_notes": "",
    }

    if n in REF_SOURCE_OVERRIDE:
        entry.update({k: v for k, v in REF_SOURCE_OVERRIDE[n].items() if k != "tier"})
        if "tier" in REF_SOURCE_OVERRIDE[n]:
            entry["text_tier"] = REF_SOURCE_OVERRIDE[n]["tier"]
        return entry

    corpus_id = REF_CORPUS_OVERRIDE.get(n)
    rec = None
    if corpus_id:
        rec = index["by_id"].get(corpus_id)
    elif doi:
        rec = index["by_doi"].get(doi)

    if rec:
        entry["corpus_id"] = rec["_corpus_id"]
        entry["corpus_file"] = rec["_corpus_file"]
        entry["text_tier"] = rec["_tier"]
        entry["char_count"] = rec["_char_count"]
        entry["provenance"] = rec.get("text_provenance") or rec.get("provenance")
        entry["manual_pdf"] = manual_pdf_for(rec["_corpus_id"], doi)
        if entry["text_tier"] in ("ABSTRACT", "NONE", "PARTIAL") and not entry["manual_pdf"]:
            entry["revision_notes"] = "Consider manual PDF → data/denovo_literature/manual_pdfs/"
    elif doi:
        entry["text_tier"] = "MISSING"
        entry["revision_notes"] = "Not in papers_raw; run fetch_papers or ingest_manual_pdfs"
    else:
        entry["source_type"] = "non_doi"
        entry["text_tier"] = "WEB"
        entry["revision_notes"] = "No DOI in reference line"

    return entry


def render_md(lib: dict) -> str:
    lines = [
        "# Review B — Reference Library (修稿用)",
        "",
        f"> **Manuscript:** `{lib['manuscript']}` · **{lib['manuscript_version']}**",
        f"> **Generated:** {lib['generated_at'][:10]} · **Refs:** {lib['summary']['total']}",
        f"> **Corpus:** `data/denovo_literature/papers_raw/` · Refresh: `python scripts/build_review_b_reference_library.py`",
        "",
        "## Summary",
        "",
        "| Tier | Count | Use in revision |",
        "|------|-------|-----------------|",
    ]
    for t, label in (
        ("FULL", "Primary source for numbers/methods"),
        ("PARTIAL", "Supplement with PDF if editing that section"),
        ("ABSTRACT", "Intro/citation only unless PDF added"),
        ("WEB", "Registry / web / press — verify live"),
        ("MISSING", "Fetch or drop PDF into manual_pdfs/"),
        ("NONE", "No local text"),
    ):
        c = lib["summary"]["by_tier"].get(t, 0)
        if c:
            lines.append(f"| **{t}** | {c} | {label} |")
    lines.extend([
        "",
        "## All references",
        "",
        "| Ref | Tier | DOI | Corpus / source | Chars | Notes |",
        "|-----|------|-----|-----------------|-------|-------|",
    ])
    for e in lib["entries"]:
        doi = e.get("doi") or "—"
        src = e.get("corpus_file") or e.get("local_path") or e.get("url") or "—"
        if len(src) > 48:
            src = "…" + src[-45:]
        cite = e["citation"][:70] + ("…" if len(e["citation"]) > 70 else "")
        notes = e.get("revision_notes") or e.get("notes") or ""
        if e.get("manual_pdf"):
            notes = (notes + "; " if notes else "") + f"PDF: `{e['manual_pdf']}`"
        lines.append(
            f"| [{e['ref']}] | **{e['text_tier']}** | `{doi}` | `{src}` | {e.get('char_count', 0)} | {notes} |"
        )
    lines.extend([
        "",
        "## Maintenance",
        "",
        "Local bundle exports **RIS**, **Zotero RDF**, and **BibTeX** under `03_Literature/`.",
        "",
        "```powershell",
        "# Re-fetch open-access text",
        "python scripts/denovo_literature/fetch_papers.py --force",
        "# Drop PDFs (basename = corpus id or biorxiv id)",
        "# data/denovo_literature/manual_pdfs/",
        "python scripts/denovo_literature/ingest_manual_pdfs.py",
        "python scripts/build_review_b_reference_library.py",
        "```",
        "",
    ])
    return "\n".join(lines)


def _strip_md_italics(s: str) -> str:
    return re.sub(r"\*([^*]+)\*", r"\1", s)


def _ris_type(citation: str, entry: dict) -> str:
    lc = citation.lower()
    st = entry.get("source_type", "")
    if st in ("clinical_registry", "trade_press") or any(
        x in lc for x in ("clinicaltrials.gov", "anzctr", "genengnews", "github")
    ):
        return "GEN"
    if any(x in lc for x in ("technical report", "version 7 report", "readme", "challenge materials")):
        return "RPRT"
    if any(x in lc for x in ("biorxiv", "arxiv", "preprint", "submitted", "zenodo")):
        return "UNPB"
    if st == "companion_manuscript":
        return "UNPB"
    return "JOUR"


def _parse_citation_fields(citation: str) -> dict:
    cite = _strip_md_italics(citation.strip())
    parts = [p.strip() for p in re.split(r"\.\s+", cite) if p.strip()]
    authors = parts[0] if parts and "," in parts[0] else ""
    title = parts[1] if len(parts) > 1 else cite
    journal = parts[2] if len(parts) > 2 else ""
    year_m = re.search(r"\b(19|20)\d{2}\b", cite)
    year = year_m.group(0) if year_m else ""
    vol_m = re.search(r";\s*(\d+)\(", cite) or re.search(r";\s*(\d+):", cite)
    volume = vol_m.group(1) if vol_m else ""
    return {"authors": authors, "title": title, "journal": journal, "year": year, "volume": volume}


def _ris_authors(author_str: str) -> list[str]:
    if not author_str:
        return []
    out: list[str] = []
    for chunk in re.split(r",\s*(?=[A-Z])", author_str):
        chunk = chunk.strip().rstrip(".")
        if chunk and chunk.lower() not in ("et al", "etc"):
            out.append(chunk)
    return out[:12]


def entry_to_ris(entry: dict) -> str:
    cite = entry.get("citation", "")
    fields = _parse_citation_fields(cite)
    ty = _ris_type(cite, entry)
    lines = [f"TY  - {ty}", f"ID  - {entry['ref']}"]
    for au in _ris_authors(fields["authors"]):
        lines.append(f"AU  - {au}")
    if fields["title"]:
        lines.append(f"TI  - {fields['title']}")
    if fields["journal"]:
        if ty == "JOUR":
            lines.append(f"JO  - {fields['journal']}")
        else:
            lines.append(f"T2  - {fields['journal']}")
    if fields["year"]:
        lines.append(f"PY  - {fields['year']}")
    if fields["volume"]:
        lines.append(f"VL  - {fields['volume']}")
    doi = entry.get("doi")
    if doi:
        doi = doi.rstrip(".")
        lines.append(f"DO  - {doi}")
        lines.append(f"UR  - https://doi.org/{doi}")
    url = entry.get("url")
    if url and not doi:
        lines.append(f"UR  - {url}")
    local = entry.get("corpus_file") or entry.get("local_path") or entry.get("manual_pdf")
    if local:
        lines.append(f"N1  - Local corpus: {local}")
    tier = entry.get("text_tier")
    if tier:
        lines.append(f"N2  - Text tier: {tier}")
    notes = entry.get("revision_notes") or entry.get("notes") or ""
    if notes:
        lines.append(f"N3  - {notes}")
    lines.append(f"Y2  - {cite}")
    lines.extend(["ER  - ", ""])
    return "\n".join(lines)


def export_ris(lib: dict, ris_path: Path) -> None:
    ris_path.parent.mkdir(parents=True, exist_ok=True)
    blocks = [
        f"Provider: InSynBio AbEngineCore",
        f"Database: Review B Reference Library",
        f"Version: {lib.get('manuscript_version', '')}",
        f"Generated: {lib.get('generated_at', '')[:10]}",
        "",
    ]
    for e in lib["entries"]:
        blocks.append(entry_to_ris(e))
    ris_path.write_text("\n".join(blocks), encoding="utf-8")


def _bib_key(entry: dict) -> str:
    fields = _parse_citation_fields(entry.get("citation", ""))
    author = "unknown"
    if fields["authors"]:
        author = fields["authors"].split(",")[0].split()[-1].lower()
        author = re.sub(r"[^a-z]", "", author) or "unknown"
    year = fields["year"] or "nd"
    return f"ref{entry['ref']}_{author}{year}"


def entry_to_bibtex(entry: dict) -> str:
    cite = entry.get("citation", "")
    fields = _parse_citation_fields(cite)
    key = _bib_key(entry)
    ty = _ris_type(cite, entry)
    btype = "misc"
    if ty == "JOUR":
        btype = "article"
    elif ty == "RPRT":
        btype = "techreport"
    elif ty == "UNPB":
        btype = "unpublished"
    lines = [f"@{btype}{{{key},"]
    if fields["authors"]:
        lines.append(f"  author = {{{fields['authors']}}},")
    if fields["title"]:
        lines.append(f"  title = {{{fields['title']}}},")
    if fields["journal"]:
        lines.append(f"  journal = {{{fields['journal']}}},")
    if fields["year"]:
        lines.append(f"  year = {{{fields['year']}}},")
    if fields["volume"]:
        lines.append(f"  volume = {{{fields['volume']}}},")
    if entry.get("doi"):
        lines.append(f"  doi = {{{entry['doi']}}},")
    if entry.get("url"):
        lines.append(f"  url = {{{entry['url']}}},")
    lines.append(f"  note = {{Ref [{entry['ref']}] · tier {entry.get('text_tier', '')}}},")
    lines.append("}")
    return "\n".join(lines)


def export_bibtex(lib: dict, bib_path: Path) -> None:
    bib_path.parent.mkdir(parents=True, exist_ok=True)
    body = "\n\n".join(entry_to_bibtex(e) for e in lib["entries"])
    bib_path.write_text(body + "\n", encoding="utf-8")


ZOTERO_RDF_NS = {
    "rdf": "http://www.w3.org/1999/02/22-rdf-syntax-ns#",
    "z": "http://www.zotero.org/namespaces/export#",
    "dcterms": "http://purl.org/dc/terms/",
    "bib": "http://purl.org/net/biblio#",
    "foaf": "http://xmlns.com/foaf/0.1/",
    "dc": "http://purl.org/dc/elements/1.1/",
    "prism": "http://prismstandard.org/namespaces/basic/2.0/",
}


def _zotero_article_about(entry: dict) -> str:
    doi = (entry.get("doi") or "").rstrip(".")
    if doi:
        return f"https://doi.org/{doi}"
    return f"urn:insynbio:review-b:ref:{entry['ref']}"


def _zotero_journal_resource(journal: str) -> str:
    slug = re.sub(r"[^a-z0-9]+", "-", journal.lower()).strip("-") or "unknown"
    return f"urn:insynbio:journal:{slug[:48]}"


def entry_to_zotero_rdf_blocks(entry: dict) -> tuple[str, str | None]:
    fields = _parse_citation_fields(entry.get("citation", ""))
    about = _zotero_article_about(entry)
    journal = fields["journal"]
    journal_resource = _zotero_journal_resource(journal) if journal else None

    lines = [f'    <bib:Article rdf:about={quoteattr(about)}>']
    if fields["title"]:
        lines.append(f"        <dc:title>{xml_escape(fields['title'])}</dc:title>")
    if journal_resource:
        lines.append(f"        <dcterms:isPartOf rdf:resource={quoteattr(journal_resource)}/>")
    authors = _ris_authors(fields["authors"])
    if authors:
        lines.extend(["        <bib:authors>", "            <rdf:Seq>"])
        for au in authors:
            surname = au.split()[-1] if au.split() else au
            lines.extend([
                "                <rdf:li>",
                "                    <foaf:Person>",
                f"                        <foaf:surname>{xml_escape(surname)}</foaf:surname>",
                "                    </foaf:Person>",
                "                </rdf:li>",
            ])
        lines.extend(["            </rdf:Seq>", "        </bib:authors>"])
    if fields["year"]:
        lines.extend([
            "        <dc:date>",
            f"            <rdf:Seq><rdf:li>{xml_escape(fields['year'])}</rdf:li></rdf:Seq>",
            "        </dc:date>",
        ])
    doi = (entry.get("doi") or "").rstrip(".")
    if doi:
        lines.extend([
            "        <dc:identifier>",
            f'            <dcterms:URI><rdf:value>{xml_escape(f"https://doi.org/{doi}")}</rdf:value></dcterms:URI>',
            "        </dc:identifier>",
        ])
    lines.append(f"        <z:citationKey>ref{entry['ref']}</z:citationKey>")
    lines.append("    </bib:Article>")

    journal_block = None
    if journal_resource and journal:
        journal_block = (
            f"    <bib:Journal rdf:about={quoteattr(journal_resource)}>\n"
            f"        <dc:title>{xml_escape(journal)}</dc:title>\n"
            f"    </bib:Journal>"
        )
    return "\n".join(lines), journal_block


def build_zotero_rdf_document(lib: dict) -> str:
    root = "<rdf:RDF" + "".join(f' xmlns:{k}="{v}"' for k, v in ZOTERO_RDF_NS.items()) + ">"
    articles: list[str] = []
    journals: dict[str, str] = {}
    for entry in lib["entries"]:
        article, journal = entry_to_zotero_rdf_blocks(entry)
        articles.append(article)
        if journal:
            resource = _zotero_journal_resource(_parse_citation_fields(entry.get("citation", ""))["journal"])
            journals[resource] = journal
    return "\n".join([root, *articles, *journals.values(), "</rdf:RDF>"])


def export_zotero_rdf(lib: dict, rdf_path: Path) -> None:
    rdf_path.parent.mkdir(parents=True, exist_ok=True)
    rdf_path.write_text(build_zotero_rdf_document(lib), encoding="utf-8")


def export_literature_bundle(lib: dict, export_dir: Path) -> None:
    """Export Zotero/EndNote-ready reference files to 03_Literature (local staging, not uploaded)."""
    export_dir.mkdir(parents=True, exist_ok=True)
    ris = export_dir / "Review_B_Reference_Library.ris"
    rdf = export_dir / "Review_B_Reference_Library.rdf"
    bib = export_dir / "Review_B_Reference_Library.bib"
    export_ris(lib, ris)
    export_zotero_rdf(lib, rdf)
    export_bibtex(lib, bib)
    legacy_xlsx = export_dir / "Review_B_Reference_Library.xlsx"
    if legacy_xlsx.exists():
        legacy_xlsx.unlink()
    print(f"Wrote {ris}")
    print(f"Wrote {rdf}")
    print(f"Wrote {bib}")


def main() -> int:
    ap = argparse.ArgumentParser(description="Build Review B reference library for revision")
    ap.add_argument("--manuscript", type=Path, default=DEFAULT_MD)
    ap.add_argument("--out-dir", type=Path, default=OUT_DIR)
    ap.add_argument(
        "--literature-dir",
        type=Path,
        default=DEFAULT_LIT_EXPORT,
        help="Export RIS/BibTeX reference library for local 03_Literature folder",
    )
    ap.add_argument("--no-literature-export", action="store_true")
    args = ap.parse_args()

    md_path = args.manuscript.resolve()
    text = md_path.read_text(encoding="utf-8")
    version = "unknown"
    vm = re.search(r"\*\*v([\d.]+)\*\*", text)
    if vm:
        version = f"v{vm.group(1)}"

    refs = parse_references(text)
    index = load_corpus_index()
    entries = [build_entry(r, index) for r in refs]

    by_tier: dict[str, int] = {}
    for e in entries:
        by_tier[e["text_tier"]] = by_tier.get(e["text_tier"], 0) + 1

    lib = {
        "schema": "review_b_reference_library.v1",
        "manuscript": str(md_path.relative_to(REPO)).replace("\\", "/"),
        "manuscript_version": version,
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "corpus_root": "data/denovo_literature/papers_raw",
        "manual_pdf_dir": "data/denovo_literature/manual_pdfs",
        "summary": {
            "total": len(entries),
            "by_tier": by_tier,
            "full_text_count": by_tier.get("FULL", 0),
            "with_corpus_file": sum(1 for e in entries if e.get("corpus_file")),
        },
        "entries": entries,
    }

    out = args.out_dir.resolve()
    out.mkdir(parents=True, exist_ok=True)
    json_path = out / "Review_B_Reference_Library.json"
    md_out = out / "Review_B_Reference_Library.md"
    json_path.write_text(json.dumps(lib, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    md_out.write_text(render_md(lib), encoding="utf-8")

    if not args.no_literature_export:
        export_literature_bundle(lib, args.literature_dir.resolve())

    print(f"Wrote {json_path}")
    print(f"Wrote {md_out}")
    print(f"Summary: {lib['summary']['total']} refs · FULL={by_tier.get('FULL', 0)} · "
          f"ABSTRACT={by_tier.get('ABSTRACT', 0)} · MISSING={by_tier.get('MISSING', 0)} · "
          f"WEB={by_tier.get('WEB', 0)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
