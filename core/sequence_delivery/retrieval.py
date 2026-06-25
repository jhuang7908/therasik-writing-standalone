"""
sequence_delivery.retrieval — Sequence lookup from internal repositories
and thin wrappers for external databases (PDB, UniProt, NCBI).

Internal priority order (no network required):
  1. project payload JSON  (H/L keys)
  2. FASTA file (by header substring)
  3. data/germlines/fc_aa/<species>/<file>.fasta (constant regions)

External (requires network):
  4. PDB RCSB REST API  -> FASTA
  5. UniProt REST API   -> FASTA
  6. NCBI Entrez        -> GenBank / FASTA

All functions return plain strings (AA or DNA).
Raise KeyError / FileNotFoundError / RuntimeError on failure.
"""

from __future__ import annotations
import json
import re
import urllib.request
import urllib.error
from pathlib import Path
from typing import Optional

_WORKSPACE = Path(__file__).resolve().parents[2]
_GERMLINE_DIR = _WORKSPACE / "data" / "germlines" / "fc_aa"


# ---------------------------------------------------------------------------
# Internal — FASTA parsing helpers
# ---------------------------------------------------------------------------

def parse_fasta(path: str | Path) -> dict[str, str]:
    """Return {header: sequence} from a FASTA file."""
    entries: dict[str, str] = {}
    current: Optional[str] = None
    buf: list[str] = []
    for line in Path(path).read_text(encoding="utf-8", errors="ignore").splitlines():
        if line.startswith(">"):
            if current is not None:
                entries[current] = "".join(buf)
            current = line[1:].strip()
            buf = []
        elif current is not None:
            buf.append(line.strip())
    if current is not None:
        entries[current] = "".join(buf)
    return entries


def get_from_fasta(path: str | Path, header_contains: str) -> str:
    """Return the first sequence whose header contains *header_contains*."""
    entries = parse_fasta(path)
    for h, s in entries.items():
        if header_contains.lower() in h.lower():
            return s
    raise KeyError(f"No FASTA entry containing '{header_contains}' in {path}")


# ---------------------------------------------------------------------------
# Internal — project payload JSON  {H:…, L:…}
# ---------------------------------------------------------------------------

def get_from_payload(path: str | Path, chain: str = "H") -> str:
    """Read VH/VL Fv-only sequence from a project payload JSON.

    Args:
        path:  path to a JSON file with at least one of {"H", "L"} keys.
        chain: "H" (VH) or "L" (VL).
    """
    data = json.loads(Path(path).read_text(encoding="utf-8"))
    key = chain.upper()
    if key not in data:
        raise KeyError(f"Key '{key}' not found in {path}. Available: {list(data.keys())}")
    return data[key]


# ---------------------------------------------------------------------------
# Internal — germline constant-region library
# ---------------------------------------------------------------------------

def list_constant_regions(species: Optional[str] = None) -> list[str]:
    """List available germline constant-region FASTA files.

    Args:
        species: optional subdirectory filter (e.g. "dog", "human", "mouse").
    Returns:
        List of file paths (relative to workspace) as strings.
    """
    root = _GERMLINE_DIR / species if species else _GERMLINE_DIR
    if not root.exists():
        return []
    return [str(p.relative_to(_WORKSPACE)) for p in root.rglob("*.fasta")]


def get_constant_region(species: str, allele_contains: str) -> str:
    """Fetch a constant-region AA sequence from the germline library.

    Args:
        species:         e.g. "dog", "human", "mouse".
        allele_contains: substring of the FASTA header, e.g. "IGHG2", "IGKC".
    """
    species_dir = _GERMLINE_DIR / species
    if not species_dir.exists():
        raise FileNotFoundError(f"No germline directory for species '{species}': {species_dir}")
    for fasta_path in sorted(species_dir.rglob("*.fasta")):
        try:
            return get_from_fasta(fasta_path, allele_contains)
        except KeyError:
            continue
    raise KeyError(
        f"No constant-region entry containing '{allele_contains}' "
        f"under {species_dir}. Run list_constant_regions('{species}') to see options."
    )


# ---------------------------------------------------------------------------
# External — PDB via RCSB REST
# ---------------------------------------------------------------------------

_PDB_FASTA_URL = "https://www.rcsb.org/fasta/entry/{pdb_id}"


def fetch_pdb_fasta(pdb_id: str, chain_id: Optional[str] = None) -> dict[str, str]:
    """Download FASTA for *pdb_id* from RCSB.

    Args:
        pdb_id:   4-letter PDB code (case-insensitive).
        chain_id: optional single-letter chain filter.
    Returns:
        {header: sequence} dict (filtered to *chain_id* if given).
    Raises:
        RuntimeError on network failure.
    """
    url = _PDB_FASTA_URL.format(pdb_id=pdb_id.upper())
    try:
        with urllib.request.urlopen(url, timeout=15) as resp:
            text = resp.read().decode("utf-8")
    except urllib.error.URLError as e:
        raise RuntimeError(f"PDB fetch failed for {pdb_id}: {e}")
    entries = {}
    current = None
    buf: list[str] = []
    for line in text.splitlines():
        if line.startswith(">"):
            if current:
                entries[current] = "".join(buf)
            current = line[1:].strip()
            buf = []
        elif current:
            buf.append(line.strip())
    if current:
        entries[current] = "".join(buf)
    if chain_id:
        filtered = {h: s for h, s in entries.items()
                    if re.search(rf"\bChains?\s+{chain_id}\b", h, re.IGNORECASE)
                    or f"|{chain_id}|" in h
                    or h.endswith(f"Chain {chain_id}")}
        return filtered if filtered else entries
    return entries


# ---------------------------------------------------------------------------
# External — UniProt REST
# ---------------------------------------------------------------------------

_UNIPROT_FASTA_URL = "https://rest.uniprot.org/uniprotkb/{accession}.fasta"


def fetch_uniprot(accession: str) -> str:
    """Download AA FASTA sequence for a UniProt accession.

    Returns:
        Single AA string (no header).
    """
    url = _UNIPROT_FASTA_URL.format(accession=accession)
    try:
        with urllib.request.urlopen(url, timeout=15) as resp:
            text = resp.read().decode("utf-8")
    except urllib.error.URLError as e:
        raise RuntimeError(f"UniProt fetch failed for {accession}: {e}")
    lines = text.splitlines()
    return "".join(l for l in lines if not l.startswith(">"))
