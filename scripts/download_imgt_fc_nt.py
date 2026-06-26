#!/usr/bin/env python3
"""
Download IMGT/GENE-DB reference nucleotide FASTA for constant regions (Fc).

Uses public GENElect query 7.2 (F+ORF+all P, nucleotide FASTA) and parses the
HTML response (FASTA is embedded in a <pre> block after "Number of results").

Species (output folder names → IMGT species query string):
  Homo_sapiens / Homo+sapiens
  Mus_musculus / Mus+musculus
  Canis_lupus_familiaris / Canis+lupus+familiaris
  Felis_catus / Felis+catus

Gene groups: IGHC, IGKC, IGLC

Writes:  data/germlines/fc_nt/<Species>/<GROUP>.fasta

Cat (Felis_catus): IMGT GENE-DB returns 0 rows for IGHC (no curated germline there yet),
but cats do express Fc. After IMGT passes, this script optionally fetches GenBank
nucleotide FASTA (IgG + “constant” in title, Felis catus[Organism]) into:
  fc_nt/Felis_catus/IGHC_NCBI_supplement.fasta
Cite NCBI + original publications for those accessions.

Respect IMGT: polite delay between requests; cite IMGT in publications.

Terms: https://www.imgt.org/about/termsofuse.php
"""
from __future__ import annotations

import argparse
import re
import time
import urllib.error
import urllib.parse
import urllib.request
import xml.etree.ElementTree as ET
from pathlib import Path

SUITE = Path(__file__).resolve().parents[1]
DEFAULT_OUT = SUITE / "data/germlines/fc_nt"

# (folder_name, IMGT species parameter with + for spaces)
SPECIES = (
    ("Homo_sapiens", "Homo+sapiens"),
    ("Mus_musculus", "Mus+musculus"),
    ("Canis_lupus_familiaris", "Canis+lupus+familiaris"),
    ("Felis_catus", "Felis+catus"),
)

GENE_GROUPS = ("IGHC", "IGKC", "IGLC")

BASE_URL = "https://www.imgt.org/genedb/GENElect"
USER_AGENT = (
    "InSynBio-AntibodyEngineerSuite/1.0 "
    "(educational research; +https://github.com/)"
)

_DELAY_SEC = 2.0


def _fetch(url: str) -> str:
    req = urllib.request.Request(url, headers={"User-Agent": USER_AGENT})
    with urllib.request.urlopen(req, timeout=120) as resp:
        return resp.read().decode("utf-8", errors="replace")


def extract_fasta_block(html: str) -> tuple[int, str]:
    """
    Return (result_count, fasta_text). fasta_text empty if count==0 or parse fail.
    """
    m_count = re.search(
        r"Number of results\s*=\s*(\d+)\s*</b>",
        html,
        re.IGNORECASE,
    )
    if not m_count:
        return -1, ""
    n = int(m_count.group(1))
    if n == 0:
        return 0, ""

    m_pre = re.search(
        r"Number of results\s*=\s*\d+\s*</b><br\s*/>\s*<pre>\s*\r?\n(.*?)\r?\n</pre>",
        html,
        re.DOTALL | re.IGNORECASE,
    )
    if not m_pre:
        return n, ""
    body = m_pre.group(1).strip()
    if not body.startswith(">"):
        return n, ""
    return n, body


def download_all(out_root: Path, delay: float) -> None:
    out_root.mkdir(parents=True, exist_ok=True)
    for folder, species_q in SPECIES:
        sp_dir = out_root / folder
        sp_dir.mkdir(parents=True, exist_ok=True)
        for gene in GENE_GROUPS:
            url = f"{BASE_URL}?query=7.2+{gene}&species={species_q}"
            print(f"GET {gene} {folder} …", flush=True)
            try:
                html = _fetch(url)
            except urllib.error.HTTPError as e:
                print(f"  HTTP {e.code} — skip")
                continue
            except OSError as e:
                print(f"  error {e} — skip")
                continue

            count, fasta = extract_fasta_block(html)
            if count < 0:
                print("  (could not parse result count)")
                time.sleep(delay)
                continue
            if count == 0 or not fasta:
                print(f"  0 sequences — no file written")
                time.sleep(delay)
                continue

            out_path = sp_dir / f"{gene}.fasta"
            out_path.write_text(fasta + "\n", encoding="utf-8")
            print(f"  → {out_path.relative_to(SUITE)}  ({count} IMGT rows, {fasta.count('>')} FASTA records)")
            time.sleep(delay)

    print("\nSource: IMGT/GENE-DB — cite: https://www.imgt.org/IMGTcitation/")


def _ncbi_esearch_nucleotide_ids(term: str, retmax: int = 25) -> list[str]:
    base = "https://eutils.ncbi.nlm.nih.gov/entrez/eutils/esearch.fcgi"
    q = urllib.parse.urlencode(
        {
            "db": "nucleotide",
            "term": term,
            "retmax": str(retmax),
            "retmode": "xml",
            "tool": "insynbio_abenginecore",
        }
    )
    req = urllib.request.Request(f"{base}?{q}", headers={"User-Agent": USER_AGENT})
    with urllib.request.urlopen(req, timeout=90) as resp:
        xml_txt = resp.read().decode("utf-8", errors="replace")
    root = ET.fromstring(xml_txt)
    return [el.text for el in root.findall(".//IdList/Id") if el.text]


def _ncbi_efetch_fasta(ids: list[str]) -> str:
    if not ids:
        return ""
    base = "https://eutils.ncbi.nlm.nih.gov/entrez/eutils/efetch.fcgi"
    q = urllib.parse.urlencode(
        {
            "db": "nucleotide",
            "id": ",".join(ids),
            "rettype": "fasta",
            "retmode": "text",
            "tool": "insynbio_abenginecore",
        }
    )
    req = urllib.request.Request(f"{base}?{q}", headers={"User-Agent": USER_AGENT})
    with urllib.request.urlopen(req, timeout=120) as resp:
        return resp.read().decode("utf-8", errors="replace")


def supplement_felis_ighc_from_ncbi(out_root: Path, retmax: int = 25) -> None:
    """
    IMGT has no Felis_catus IGHC in GENE-DB query 7.2; pull partial mRNA / constant cds from NCBI.
    """
    sp_dir = out_root / "Felis_catus"
    sp_dir.mkdir(parents=True, exist_ok=True)
    term = "Felis catus[Organism] AND IgG[Title] AND constant[Title]"
    print(f"NCBI nucleotide search (cat IgG constant): {term!r} …", flush=True)
    try:
        ids = _ncbi_esearch_nucleotide_ids(term, retmax=retmax)
    except OSError as e:
        print(f"  NCBI esearch failed: {e}")
        return
    if not ids:
        print("  no IDs — skip")
        return
    try:
        fasta = _ncbi_efetch_fasta(ids)
    except OSError as e:
        print(f"  NCBI efetch failed: {e}")
        return
    if not fasta.strip():
        print("  empty FASTA — skip")
        return
    out = sp_dir / "IGHC_NCBI_supplement.fasta"
    out.write_text(fasta.strip() + "\n", encoding="utf-8")
    n = fasta.count(">")
    print(f"  → {out.relative_to(SUITE)}  ({n} records, {len(ids)} IDs requested)")
    print("  Cite NCBI + each accession’s reference (not IMGT).")


def main() -> None:
    ap = argparse.ArgumentParser(description="Download IMGT Fc nucleotide FASTA")
    ap.add_argument("--out", type=Path, default=DEFAULT_OUT, help="fc_nt root")
    ap.add_argument("--delay", type=float, default=_DELAY_SEC, help="Seconds between requests")
    ap.add_argument(
        "--skip-ncbi-felis",
        action="store_true",
        help="Do not add Felis_catus IGHC from NCBI when IMGT has no IGHC",
    )
    ap.add_argument(
        "--felis-ncbi-retmax",
        type=int,
        default=25,
        help="Max GenBank records for cat IgG constant supplement",
    )
    ap.add_argument(
        "--only-ncbi-felis",
        action="store_true",
        help="Only run NCBI Felis IGHC supplement (skip IMGT downloads)",
    )
    args = ap.parse_args()
    if args.only_ncbi_felis:
        supplement_felis_ighc_from_ncbi(args.out, retmax=args.felis_ncbi_retmax)
        return
    download_all(args.out, args.delay)
    if not args.skip_ncbi_felis:
        print()
        supplement_felis_ighc_from_ncbi(args.out, retmax=args.felis_ncbi_retmax)


if __name__ == "__main__":
    main()
