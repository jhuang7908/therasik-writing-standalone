#!/usr/bin/env python3
"""
Translate IMGT nucleotide germline FASTA → amino acid FASTA.

IG (V/D/J, κ/λ V/J)
  Source: data/germlines/IMGT_V-QUEST_reference_directory/<Species_binomial>/IG/*.fasta
  Species processed by default:
    Homo_sapiens, Mus_musculus, Canis_lupus_familiaris, Oryctolagus_cuniculus, Vicugna_pacos

Fc (constant regions: IGHC, IGKC, IGLC — nucleotide FASTA)
  The V-QUEST *reference directory* tree does not include constant-region files.
  Populate from IMGT/GENE-DB automatically:
    python scripts/download_imgt_fc_nt.py
  Or place nucleotide FASTA manually under:
    data/germlines/fc_nt/<Species_binomial>/*.fasta
  Default Fc species: Homo_sapiens, Mus_musculus, Canis_lupus_familiaris, Felis_catus

Output:
  data/germlines/aa_translated/IG/<Species>/   — mirrors input basenames with _aa.fasta
  data/germlines/aa_translated/Fc/<Species>/   — same for fc_nt inputs

IMGT FASTA: headers like >M99641|IGHV1-18*01|Homo sapiens|... ; sequence may use '.' gaps
and span multiple lines (lowercase DNA). Gaps are removed before translation; trailing
1–2 nt that do not form a full codon are omitted (not translated).
"""
from __future__ import annotations

import argparse
import re
from pathlib import Path

SUITE = Path(__file__).resolve().parents[1]
DEFAULT_IMGT = SUITE / "data/germlines/IMGT_V-QUEST_reference_directory"
DEFAULT_OUT = SUITE / "data/germlines/aa_translated"
DEFAULT_FC_NT = SUITE / "data/germlines/fc_nt"

IG_SPECIES = (
    "Homo_sapiens",
    "Mus_musculus",
    "Canis_lupus_familiaris",
    "Oryctolagus_cuniculus",
    "Vicugna_pacos",
)
FC_SPECIES = (
    "Homo_sapiens",
    "Mus_musculus",
    "Canis_lupus_familiaris",
    "Felis_catus",
)

_GENETIC_CODE: dict[str, str] = {}
for triplet, aa in [
    ("TTT", "F"), ("TTC", "F"), ("TTA", "L"), ("TTG", "L"),
    ("TCT", "S"), ("TCC", "S"), ("TCA", "S"), ("TCG", "S"),
    ("TAT", "Y"), ("TAC", "Y"), ("TAA", "*"), ("TAG", "*"),
    ("TGT", "C"), ("TGC", "C"), ("TGA", "*"), ("TGG", "W"),
    ("CTT", "L"), ("CTC", "L"), ("CTA", "L"), ("CTG", "L"),
    ("CCT", "P"), ("CCC", "P"), ("CCA", "P"), ("CCG", "P"),
    ("CAT", "H"), ("CAC", "H"), ("CAA", "Q"), ("CAG", "Q"),
    ("CGT", "R"), ("CGC", "R"), ("CGA", "R"), ("CGG", "R"),
    ("ATT", "I"), ("ATC", "I"), ("ATA", "I"), ("ATG", "M"),
    ("ACT", "T"), ("ACC", "T"), ("ACA", "T"), ("ACG", "T"),
    ("AAT", "N"), ("AAC", "N"), ("AAA", "K"), ("AAG", "K"),
    ("AGT", "S"), ("AGC", "S"), ("AGA", "R"), ("AGG", "R"),
    ("GTT", "V"), ("GTC", "V"), ("GTA", "V"), ("GTG", "V"),
    ("GCT", "A"), ("GCC", "A"), ("GCA", "A"), ("GCG", "A"),
    ("GAT", "D"), ("GAC", "D"), ("GAA", "E"), ("GAG", "E"),
    ("GGT", "G"), ("GGC", "G"), ("GGA", "G"), ("GGG", "G"),
]:
    _GENETIC_CODE[triplet] = aa


def clean_dna(raw: str) -> str:
    s = raw.upper().replace(" ", "").replace("\n", "")
    s = re.sub(r"\.+", "", s)
    return "".join(c for c in s if c in "ACGT")


def dna_to_aa(dna: str, stop_at_first_stop: bool = True) -> str:
    dna = clean_dna(dna)
    n = (len(dna) // 3) * 3
    dna = dna[:n]
    out: list[str] = []
    for i in range(0, len(dna), 3):
        codon = dna[i : i + 3]
        aa = _GENETIC_CODE.get(codon, "X")
        if stop_at_first_stop and aa == "*":
            break
        if aa != "*":
            out.append(aa)
    return "".join(out)


def parse_fasta(path: Path) -> list[tuple[str, str]]:
    """Return list of (header_line_without_gt, concatenated sequence string)."""
    text = path.read_text(encoding="utf-8", errors="replace")
    records: list[tuple[str, str]] = []
    header: str | None = None
    chunks: list[str] = []
    for line in text.splitlines():
        line = line.strip()
        if not line:
            continue
        if line.startswith(">"):
            if header is not None:
                records.append((header, "".join(chunks)))
            header = line[1:].strip()
            chunks = []
        else:
            chunks.append(line)
    if header is not None:
        records.append((header, "".join(chunks)))
    return records


def write_aa_fasta(
    out_path: Path,
    records: list[tuple[str, str]],
) -> tuple[int, int]:
    """Write translated records; return (n_written, n_skipped_empty)."""
    out_path.parent.mkdir(parents=True, exist_ok=True)
    skipped = 0
    written = 0
    lines: list[str] = []
    for hdr, nt in records:
        aa = dna_to_aa(nt, stop_at_first_stop=True)
        if not aa:
            skipped += 1
            continue
        written += 1
        lines.append(f">{hdr} |nt_len={len(clean_dna(nt))}|aa_len={len(aa)}")
        for i in range(0, len(aa), 80):
            lines.append(aa[i : i + 80])
    out_path.write_text("\n".join(lines) + ("\n" if lines else ""), encoding="utf-8")
    return written, skipped


def process_ig_dir(imgt_root: Path, species: str, out_root: Path) -> list[str]:
    log: list[str] = []
    ig_dir = imgt_root / species / "IG"
    if not ig_dir.is_dir():
        log.append(f"[skip] {species}: no IG dir {ig_dir}")
        return log
    fastas = sorted(ig_dir.glob("*.fasta"))
    if not fastas:
        log.append(f"[skip] {species}: no .fasta in {ig_dir}")
        return log
    dest = out_root / "IG" / species
    for fp in fastas:
        recs = parse_fasta(fp)
        out_name = fp.stem + "_aa.fasta"
        n_ok, n_skip = write_aa_fasta(dest / out_name, recs)
        log.append(f"  {species}/{fp.name} -> {out_name}  ({n_ok} seq, {n_skip} empty/skip)")
    return log


def process_fc_dir(fc_nt_root: Path, species: str, out_root: Path) -> list[str]:
    log: list[str] = []
    sp_dir = fc_nt_root / species
    if not sp_dir.is_dir():
        log.append(
            f"[Fc] {species}: no nucleotide dir {sp_dir} — add IGHC/IGKC/IGLC .fasta from IMGT"
        )
        return log
    fastas = sorted(sp_dir.glob("*.fasta"))
    if not fastas:
        log.append(f"[Fc] {species}: no .fasta in {sp_dir}")
        return log
    dest = out_root / "Fc" / species
    for fp in fastas:
        recs = parse_fasta(fp)
        out_name = fp.stem + "_aa.fasta"
        n_ok, n_skip = write_aa_fasta(dest / out_name, recs)
        log.append(f"  Fc {species}/{fp.name} -> {out_name}  ({n_ok} seq, {n_skip} empty/skip)")
    return log


def main() -> None:
    ap = argparse.ArgumentParser(description="IMGT nt FASTA -> AA FASTA (IG + optional Fc)")
    ap.add_argument(
        "--imgt-root",
        type=Path,
        default=DEFAULT_IMGT,
        help="IMGT_V-QUEST_reference_directory",
    )
    ap.add_argument(
        "--fc-nt-root",
        type=Path,
        default=DEFAULT_FC_NT,
        help="Nucleotide constant-region FASTA per species subfolder",
    )
    ap.add_argument("--out", type=Path, default=DEFAULT_OUT, help="Output root aa_translated")
    ap.add_argument("--ig-only", action="store_true", help="Skip Fc pass")
    ap.add_argument("--fc-only", action="store_true", help="Skip IG pass")
    args = ap.parse_args()

    print("IMGT nt -> AA")
    print(f"  IMGT root: {args.imgt_root}")
    print(f"  Fc nt root: {args.fc_nt_root}")
    print(f"  Output:    {args.out}\n")

    if not args.fc_only:
        print("=== IG ===")
        for sp in IG_SPECIES:
            for line in process_ig_dir(args.imgt_root, sp, args.out):
                print(line)

    if not args.ig_only:
        print("\n=== Fc (requires fc_nt nucleotide files) ===")
        for sp in FC_SPECIES:
            for line in process_fc_dir(args.fc_nt_root, sp, args.out):
                print(line)

    print("\nDone.")


if __name__ == "__main__":
    main()
