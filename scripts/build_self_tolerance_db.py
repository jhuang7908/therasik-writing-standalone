"""
scripts/build_self_tolerance_db.py
───────────────────────────────────
OPTIONAL — heavy offline build.  SelfToleranceFilter works without this:
it uses a small seed peptide list + DAI/WT rules by default.

Only run when you need full human-proteome exact k-mer matching (~tens of
millions of 8–11mers, large disk/RAM).  After building, enable at runtime:

    set INSYNBIO_USE_PROTEOME_KMER_DB=1   # Windows
    export INSYNBIO_USE_PROTEOME_KMER_DB=1  # Unix

Downloads UniProt human reference proteome (UP000005640), generates all
8–11mer peptides, saves to:
    ~/.insynbio/human_proteome_kmers.pkl.gz

Usage:
    conda run -n vaccine python scripts/build_self_tolerance_db.py
    conda run -n vaccine python scripts/build_self_tolerance_db.py --dry-run

Rough cost: ~5–15 min download + processing; ~80 MB compressed on disk;
hundreds of MB RAM when loaded by Python.

Version: 1.0.0
"""
from __future__ import annotations

import argparse
import gzip
import logging
import os
import pickle
import time
from pathlib import Path

__version__ = "1.0.0"

logging.basicConfig(level=logging.INFO,
                    format="%(asctime)s [%(levelname)s] %(message)s",
                    datefmt="%H:%M:%S")
log = logging.getLogger("build_tolerance_db")

OUT_DIR = Path.home() / ".insynbio"
OUT_PATH = OUT_DIR / "human_proteome_kmers.pkl.gz"
META_PATH = OUT_DIR / "human_proteome_kmers_meta.json"

UNIPROT_URL = (
    "https://ftp.uniprot.org/pub/databases/uniprot/current_release/"
    "knowledgebase/reference_proteomes/Eukaryota/"
    "UP000005640/UP000005640_9606.fasta.gz"
)

PEPTIDE_LENGTHS = [8, 9, 10, 11]


def _download_fasta(out_fasta: Path) -> None:
    import urllib.request
    log.info("Downloading UniProt human reference proteome …")
    log.info("  Source: %s", UNIPROT_URL)
    urllib.request.urlretrieve(UNIPROT_URL, out_fasta)
    size_mb = out_fasta.stat().st_size / 1e6
    log.info("  Downloaded %.1f MB → %s", size_mb, out_fasta)


def _parse_fasta_gz(fasta_gz: Path):
    """Yield protein sequences from a gzip-compressed FASTA."""
    import re
    seq_buf = []
    with gzip.open(fasta_gz, "rt", encoding="utf-8", errors="replace") as fh:
        for line in fh:
            line = line.rstrip()
            if line.startswith(">"):
                if seq_buf:
                    yield "".join(seq_buf)
                seq_buf = []
            else:
                seq_buf.append(re.sub(r"[^A-Z]", "", line.upper()))
        if seq_buf:
            yield "".join(seq_buf)


def _generate_kmers(sequences, lengths=PEPTIDE_LENGTHS):
    """Generate all k-mers from a list of protein sequences."""
    kmers: set[str] = set()
    for seq in sequences:
        for plen in lengths:
            for i in range(len(seq) - plen + 1):
                kmer = seq[i:i + plen]
                if "X" not in kmer and "*" not in kmer and "U" not in kmer:
                    kmers.add(kmer)
    return kmers


def build(dry_run: bool = False) -> None:
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    tmp_fasta = OUT_DIR / "UP000005640_9606.fasta.gz"

    if dry_run:
        log.info("[DRY RUN] Would download to %s", tmp_fasta)
        log.info("[DRY RUN] Would write k-mer DB to %s", OUT_PATH)
        return

    t0 = time.time()
    if not tmp_fasta.exists():
        _download_fasta(tmp_fasta)
    else:
        log.info("FASTA already cached at %s — skipping download", tmp_fasta)

    log.info("Parsing FASTA and generating %s-mers …", "/".join(map(str, PEPTIDE_LENGTHS)))
    sequences = list(_parse_fasta_gz(tmp_fasta))
    n_seqs = len(sequences)
    log.info("  Parsed %d protein sequences", n_seqs)

    log.info("  Generating k-mers (this may take several minutes) …")
    kmers = _generate_kmers(sequences)
    n_kmers = len(kmers)
    log.info("  Generated %d unique k-mers", n_kmers)

    log.info("Compressing and saving to %s …", OUT_PATH)
    with gzip.open(OUT_PATH, "wb", compresslevel=6) as fh:
        pickle.dump(kmers, fh, protocol=4)
    size_mb = OUT_PATH.stat().st_size / 1e6
    log.info("  Saved %.1f MB", size_mb)

    elapsed = time.time() - t0
    log.info("Done in %.0f s", elapsed)

    # Write metadata
    import json
    meta = {
        "version": __version__,
        "n_sequences": n_seqs,
        "n_kmers": n_kmers,
        "peptide_lengths": PEPTIDE_LENGTHS,
        "source": UNIPROT_URL,
        "output_path": str(OUT_PATH),
        "build_time_s": round(elapsed, 1),
    }
    META_PATH.write_text(json.dumps(meta, indent=2), encoding="utf-8")
    log.info("Metadata → %s", META_PATH)
    log.info("")
    log.info("SelfToleranceFilter will now use the full human proteome k-mer DB.")
    log.info("Verify: python -c \"from core.vaccine_design.epitope_prioritizer "
             "import _load_kmer_db; db=_load_kmer_db(); print(len(db))\"")


def main():
    ap = argparse.ArgumentParser(
        prog="build_self_tolerance_db",
        description="Build human proteome k-mer DB for SelfToleranceFilter",
    )
    ap.add_argument("--dry-run", action="store_true", dest="dry_run",
                    help="Show what would be done without downloading or building")
    ap.add_argument("--force", action="store_true",
                    help="Re-download even if FASTA is already cached")
    args = ap.parse_args()

    if args.force:
        fasta = OUT_DIR / "UP000005640_9606.fasta.gz"
        if fasta.exists():
            fasta.unlink()
            log.info("Removed cached FASTA for fresh download")

    build(dry_run=args.dry_run)


if __name__ == "__main__":
    main()
