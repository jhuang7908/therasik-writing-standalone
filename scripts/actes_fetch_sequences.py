#!/usr/bin/env python3
"""
ACTES Appendix A sequence fetcher: UniProt + NCBI RefSeq dual-source fetch and pairwise alignment.
Each entry is verified by >=2 independent sources where possible; results written to
data/actes_sequences/sources/, alignments/, and sequence_db.json.

Usage:
  python scripts/actes_fetch_sequences.py
  python scripts/actes_fetch_sequences.py --config data/actes_sequences/config.json --out data/actes_sequences
"""

from __future__ import annotations

import argparse
import hashlib
import json
import re
import sys
import time
from pathlib import Path

try:
    import requests
except ImportError:
    print("Install: pip install requests", file=sys.stderr)
    sys.exit(1)

# Optional: Biopython for proper alignment
try:
    from Bio.Align import PairwiseAligner
    from Bio.Seq import Seq
    HAS_BIO = True
except ImportError:
    HAS_BIO = False

# -----------------------------------------------------------------------------
# Paths
# -----------------------------------------------------------------------------
SCRIPT_DIR = Path(__file__).resolve().parent
SUITE_ROOT = SCRIPT_DIR.parent
DEFAULT_CONFIG = SUITE_ROOT / "data" / "actes_sequences" / "config.json"
DEFAULT_OUT = SUITE_ROOT / "data" / "actes_sequences"

UNIPROT_URL = "https://rest.uniprot.org/uniprotkb/{accession}.json"
NCBI_EFETCH = "https://eutils.ncbi.nlm.nih.gov/entrez/eutils/efetch.fcgi"

# -----------------------------------------------------------------------------
# Fetch
# -----------------------------------------------------------------------------


def fetch_uniprot(accession: str) -> dict:
    r = requests.get(UNIPROT_URL.format(accession=accession), timeout=30)
    r.raise_for_status()
    return r.json()


def get_uniprot_sequence_and_refseq(data: dict) -> tuple[str, str | None]:
    seq = data.get("sequence", {}).get("value") or ""
    refseq_id = None
    for xref in data.get("uniProtKBCrossReferences") or []:
        if xref.get("database") == "RefSeq":
            refseq_id = xref.get("id")
            if refseq_id and refseq_id.startswith("NP_"):
                break
    return seq, refseq_id


def get_signal_peptide_range(data: dict) -> tuple[int, int] | None:
    for f in data.get("features") or []:
        if f.get("type") == "Signal":
            loc = f.get("location", {})
            start = loc.get("start", {}).get("value")
            end = loc.get("end", {}).get("value")
            if start is not None and end is not None:
                return (int(start), int(end))
    return None


def slice_sequence(seq: str, range_1based: list[int] | None, *, signal_from_uniprot: bool, uniprot_data: dict | None) -> str:
    if range_1based is not None and len(range_1based) == 2:
        start, end = range_1based[0], range_1based[1]
        return seq[start - 1 : end]
    if signal_from_uniprot and uniprot_data:
        sig = get_signal_peptide_range(uniprot_data)
        if sig:
            start, end = sig[0], sig[1]
            return seq[start - 1 : end]
    return seq


def fetch_ncbi_protein(refseq_id: str) -> str:
    params = {"db": "protein", "id": refseq_id, "rettype": "fasta", "retmode": "text"}
    r = requests.get(NCBI_EFETCH, params=params, timeout=30)
    r.raise_for_status()
    text = r.text
    lines = [l for l in text.strip().split("\n") if l and not l.startswith(">")]
    return re.sub(r"[\s\n\r]", "", "".join(lines))


def sequence_identity(seq1: str, seq2: str) -> tuple[float, str, str]:
    """Pairwise alignment and identity. Returns (identity_ratio, aligned1, aligned2)."""
    s1 = re.sub(r"[\s\n\r*]", "", seq1.upper())
    s2 = re.sub(r"[\s\n\r*]", "", seq2.upper())
    if not s1 or not s2:
        return 0.0, s1, s2
    if HAS_BIO:
        try:
            aligner = PairwiseAligner(mode="global", open_gap_score=-10, extend_gap_score=-0.5)
            alns = list(aligner.align(Seq(s1), Seq(s2)))
            if alns:
                a = alns[0]
                aln1 = str(a[0])
                aln2 = str(a[1])
                matches = sum(1 for x, y in zip(aln1, aln2) if x == y and x != "-")
                length = max(len(s1), len(s2))
                identity = matches / length if length else 0.0
                return identity, aln1, aln2
        except Exception:
            pass
    # Fallback: same-length match count
    n = min(len(s1), len(s2))
    matches = sum(1 for i in range(n) if s1[i] == s2[i])
    identity = matches / n if n else 0.0
    return identity, s1[:n], s2[:n]


def canonical_sequence(seq: str) -> str:
    return re.sub(r"[^ACDEFGHIKLMNPQRSTVWY]", "", seq.upper())


def seq_hash(seq: str) -> str:
    return hashlib.sha256(canonical_sequence(seq).encode()).hexdigest()[:16]


# -----------------------------------------------------------------------------
# Main
# -----------------------------------------------------------------------------


def main() -> None:
    ap = argparse.ArgumentParser(description="ACTES dual-source sequence fetch and align")
    ap.add_argument("--config", type=Path, default=DEFAULT_CONFIG, help="Config JSON path")
    ap.add_argument("--out", type=Path, default=DEFAULT_OUT, help="Output directory")
    ap.add_argument("--no-ncbi", action="store_true", help="Skip NCBI second source (UniProt only)")
    args = ap.parse_args()

    out = args.out
    sources_dir = out / "sources"
    alignments_dir = out / "alignments"
    sources_dir.mkdir(parents=True, exist_ok=True)
    alignments_dir.mkdir(parents=True, exist_ok=True)

    with open(args.config, encoding="utf-8") as f:
        config = json.load(f)

    db = {
        "version": config.get("version", "1.0"),
        "generated_by": "actes_fetch_sequences.py",
        "entries": [],
        "static_sequences": [],
    }

    entries = config.get("entries", [])
    for i, ent in enumerate(entries):
        entry_id = ent.get("entry_id") or f"entry_{i}"
        uniprot_id = ent.get("uniprot_id")
        range_1based = ent.get("range")
        use_signal = ent.get("use_uniprot_signal_feature", False)
        name = ent.get("name", entry_id)

        rec = {
            "entry_id": entry_id,
            "name": name,
            "sources": [],
            "alignment": None,
            "status": "pending",
            "canonical_sequence": None,
            "sequence_sha256_16": None,
        }

        try:
            # Source 1: UniProt
            data = fetch_uniprot(uniprot_id)
            full_seq, refseq_id = get_uniprot_sequence_and_refseq(data)
            seq1 = slice_sequence(full_seq, range_1based, signal_from_uniprot=use_signal, uniprot_data=data)
            if not seq1:
                rec["status"] = "error"
                rec["error"] = "Empty sequence after slice"
                db["entries"].append(rec)
                continue

            source1 = {
                "name": "UniProt",
                "id": uniprot_id,
                "sequence": seq1,
                "length": len(seq1),
                "range": range_1based,
            }
            rec["sources"].append(source1)
            rec["canonical_sequence"] = canonical_sequence(seq1)
            rec["sequence_sha256_16"] = seq_hash(seq1)

            # Write FASTA
            (sources_dir / f"{entry_id}_UniProt.fasta").write_text(
                f">{entry_id} UniProt {uniprot_id}\n{seq1}\n", encoding="utf-8"
            )

            # Source 2: NCBI RefSeq (if available)
            seq2 = None
            if not args.no_ncbi and refseq_id:
                time.sleep(0.4)  # NCBI rate limit
                try:
                    refseq_seq = fetch_ncbi_protein(refseq_id)
                    seq2 = slice_sequence(refseq_seq, range_1based, signal_from_uniprot=use_signal, uniprot_data=data)
                except Exception as e:
                    rec["refseq_error"] = str(e)
                if seq2:
                    source2 = {
                        "name": "RefSeq",
                        "id": refseq_id,
                        "sequence": seq2,
                        "length": len(seq2),
                    }
                    rec["sources"].append(source2)
                    (sources_dir / f"{entry_id}_RefSeq.fasta").write_text(
                        f">{entry_id} RefSeq {refseq_id}\n{seq2}\n", encoding="utf-8"
                    )

            # Align if two sources
            if seq2 is not None:
                identity, aln1, aln2 = sequence_identity(seq1, seq2)
                rec["alignment"] = {
                    "identity_ratio": round(identity, 4),
                    "length_source1": len(seq1),
                    "length_source2": len(seq2),
                    "verified": identity >= 0.99,
                }
                rec["status"] = "verified" if identity >= 0.99 else "mismatch_review"
                report = [
                    f"# {entry_id} dual-source alignment",
                    f"Identity: {identity:.2%}",
                    f"UniProt ({uniprot_id}) length: {len(seq1)}",
                    f"RefSeq ({refseq_id}) length: {len(seq2)}",
                    "",
                    "Aligned (first 80 chars per line):",
                ]
                width = 80
                for j in range(0, max(len(aln1), len(aln2)), width):
                    report.append(f"1: {aln1[j:j+width]}")
                    report.append(f"2: {aln2[j:j+width]}")
                    report.append("")
                (alignments_dir / f"{entry_id}_alignment.txt").write_text("\n".join(report), encoding="utf-8")
            else:
                rec["status"] = "single_source"
                rec["alignment"] = None

        except Exception as e:
            rec["status"] = "error"
            rec["error"] = str(e)
            rec["sources"] = rec.get("sources", [])

        db["entries"].append(rec)

    # Static sequences (one source only)
    for st in config.get("static_sequences", []):
        eid = st.get("entry_id", "")
        seq = st.get("sequence", "")
        db["static_sequences"].append({
            "entry_id": eid,
            "name": st.get("name", eid),
            "source": st.get("source", "static"),
            "sequence": seq,
            "length": len(seq),
            "sequence_sha256_16": seq_hash(seq),
            "status": "static_single_source",
        })
        (sources_dir / f"{eid}_static.fasta").write_text(f">{eid} static\n{seq}\n", encoding="utf-8")

    out_db = out / "sequence_db.json"
    with open(out_db, "w", encoding="utf-8") as f:
        json.dump(db, f, indent=2, ensure_ascii=False)

    verified = sum(1 for e in db["entries"] if e.get("status") == "verified")
    single = sum(1 for e in db["entries"] if e.get("status") == "single_source")
    errors = sum(1 for e in db["entries"] if e.get("status") == "error")
    mismatch = sum(1 for e in db["entries"] if e.get("status") == "mismatch_review")
    print(f"Wrote {out_db}")
    print(f"Entries: {verified} verified (2 sources), {single} single_source, {mismatch} mismatch_review, {errors} errors")
    print(f"Static: {len(db['static_sequences'])}")
    if not HAS_BIO:
        print("Tip: pip install biopython for full pairwise alignment", file=sys.stderr)


if __name__ == "__main__":
    main()
