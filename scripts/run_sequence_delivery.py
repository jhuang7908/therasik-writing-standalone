#!/usr/bin/env python3
"""
run_sequence_delivery.py — CLI facade for core/sequence_delivery.

Subcommands:
  fetch       Retrieve a sequence from internal data or external databases.
  assemble    Assemble full-length HC/LC/scFv from parts.
  optimize    Codon-optimize an AA sequence to CHO DNA.
  translate   Translate DNA → AA or AA → DNA.
  qa          Run QA checks on an assembled AA (+ optional DNA).

Usage examples:
  # Codon-optimize an AA from a file
  python scripts/run_sequence_delivery.py optimize --aa EVQLVESGG... --name MyVH

  # Fetch from PDB
  python scripts/run_sequence_delivery.py fetch --source pdb --id 4EDW

  # QA an AA file vs a reference
  python scripts/run_sequence_delivery.py qa --aa-file my_hc.fasta --ref-file v1_payload.json --chain HC

  # Assemble HC from parts (JSON parts file)
  python scripts/run_sequence_delivery.py assemble --parts hc_parts.json --type HC --name MyHC-IgGB

  # Translate DNA file to AA
  python scripts/run_sequence_delivery.py translate --dna ATGGAGTTC... --direction dna2aa
"""

import argparse
import json
import sys
from pathlib import Path

# Ensure repo root on path
_REPO = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(_REPO))

from core.sequence_delivery import codon_optimizer, retrieval, assembler, translator, qa
from core.sequence_delivery import __version__


# ── Subcommand: fetch ──────────────────────────────────────────────────────

def cmd_fetch(args):
    if args.source == "pdb":
        entries = retrieval.fetch_pdb_fasta(args.id, chain_id=args.chain)
        for h, s in entries.items():
            print(f">{h}\n{s}")
    elif args.source == "uniprot":
        seq = retrieval.fetch_uniprot(args.id)
        print(f">UniProt|{args.id}\n{seq}")
    elif args.source == "fasta":
        seq = retrieval.get_from_fasta(args.file, args.header)
        print(seq)
    elif args.source == "payload":
        seq = retrieval.get_from_payload(args.file, chain=args.chain or "H")
        print(seq)
    elif args.source == "germline":
        seq = retrieval.get_constant_region(args.species, args.allele)
        print(f">{args.species}|{args.allele}\n{seq}")
    else:
        print(f"Unknown source: {args.source}", file=sys.stderr)
        sys.exit(1)


# ── Subcommand: optimize ───────────────────────────────────────────────────

def cmd_optimize(args):
    if args.aa_file:
        text = Path(args.aa_file).read_text(encoding="utf-8")
        aa = "".join(l.strip() for l in text.splitlines() if not l.startswith(">"))
    else:
        aa = args.aa
    dna = codon_optimizer.optimize(aa, add_stop=not args.no_stop)
    gc = codon_optimizer.gc_content(dna)
    name = args.name or "optimized"
    print(f">{name}-DNA (CHO, {codon_optimizer.CODON_TABLE_VERSION})")
    print(dna)
    print(f"; AA length: {len(aa)} | DNA length: {len(dna)} bp | GC: {gc*100:.1f}%",
          file=sys.stderr)
    if args.out:
        Path(args.out).write_text(f">{name}-DNA\n{dna}\n", encoding="utf-8")
        print(f"Saved → {args.out}", file=sys.stderr)


# ── Subcommand: translate ──────────────────────────────────────────────────

def cmd_translate(args):
    if args.direction == "dna2aa":
        seq = args.dna or Path(args.dna_file).read_text(encoding="utf-8").strip()
        seq = "".join(l for l in seq.splitlines() if not l.startswith(">"))
        aa = translator.translate(seq)
        print(aa)
    else:  # aa2dna
        seq = args.aa or Path(args.aa_file).read_text(encoding="utf-8").strip()
        seq = "".join(l for l in seq.splitlines() if not l.startswith(">"))
        dna = translator.back_translate(seq)
        print(dna)


# ── Subcommand: assemble ───────────────────────────────────────────────────

def cmd_assemble(args):
    parts_data = json.loads(Path(args.parts).read_text(encoding="utf-8"))
    chain_type = args.type.upper()
    name = args.name or parts_data.get("name", "assembled")

    if chain_type == "HC":
        chain = assembler.assemble_heavy_chain(
            name,
            sp=parts_data["SP"],
            vh=parts_data["VH"],
            ch1=parts_data["CH1"],
            hinge=parts_data["Hinge"],
            ch2=parts_data["CH2"],
            ch3=parts_data["CH3"],
        )
    elif chain_type == "LC":
        chain = assembler.assemble_light_chain(
            name, sp=parts_data["SP"], vl=parts_data["VL"], cl=parts_data["CL"],
        )
    elif chain_type == "SCFV":
        chain = assembler.assemble_scfv(
            name,
            sp=parts_data["SP"],
            vh=parts_data["VH"],
            vl=parts_data["VL"],
            linker=parts_data.get("linker", "G4S3"),
            orientation=parts_data.get("orientation", "VH-VL"),
        )
    else:
        order = parts_data.get("order", list(parts_data.keys()))
        chain = assembler.assemble_custom(name, parts=parts_data, order=order)

    print(chain.to_fasta())
    if args.out:
        Path(args.out).write_text(chain.to_fasta() + "\n", encoding="utf-8")
        print(f"Saved → {args.out}", file=sys.stderr)


# ── Subcommand: qa ────────────────────────────────────────────────────────

def cmd_qa(args):
    # Load AA
    if args.aa_file:
        text = Path(args.aa_file).read_text(encoding="utf-8")
        entries = retrieval.parse_fasta(args.aa_file) if text.startswith(">") else {}
        if entries:
            name, full_aa = next(iter(entries.items()))
        else:
            name, full_aa = args.aa_file, text.strip()
    else:
        name, full_aa = "query", args.aa

    # Load DNA (optional)
    dna = None
    if args.dna_file:
        dna_text = Path(args.dna_file).read_text(encoding="utf-8")
        dna_entries = retrieval.parse_fasta(args.dna_file) if dna_text.startswith(">") else {}
        dna = next(iter(dna_entries.values())) if dna_entries else dna_text.strip()

    # Load reference (optional)
    ref_fv = None
    ref_label = "reference"
    if args.ref_file:
        ref_path = Path(args.ref_file)
        if ref_path.suffix == ".json":
            ref_data = json.loads(ref_path.read_text(encoding="utf-8"))
            chain_key = "H" if args.chain.upper() in ("HC", "H", "VH") else "L"
            ref_fv = ref_data.get(chain_key, "")
            ref_label = str(ref_path.name)
        else:
            ref_fv = retrieval.get_from_fasta(ref_path, args.ref_header or "")
            ref_label = args.ref_file

    sp = args.sp or None

    report = qa.run_all_checks(
        chain_name=name,
        full_aa=full_aa,
        dna=dna,
        reference_fv=ref_fv,
        reference_label=ref_label,
        sp=sp,
        chain_type=args.chain,
        expected_aa_len=args.expected_len,
    )

    print(report.summary())
    if args.out:
        Path(args.out).write_text(json.dumps(report.to_dict(), indent=2, ensure_ascii=False))
        print(f"QA JSON saved → {args.out}", file=sys.stderr)
    if report.overall == qa.FAIL:
        sys.exit(2)
    elif report.overall == qa.WARN:
        sys.exit(1)


# ── Main ──────────────────────────────────────────────────────────────────

def build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(
        prog="run_sequence_delivery",
        description=f"AbEngineCore Sequence Delivery CLI (v{__version__})",
    )
    p.add_argument("--version", action="version", version=f"sequence_delivery {__version__}")
    sub = p.add_subparsers(dest="cmd", required=True)

    # fetch
    pf = sub.add_parser("fetch", help="Retrieve a sequence from internal/external source")
    pf.add_argument("--source", required=True,
                    choices=["pdb", "uniprot", "fasta", "payload", "germline"])
    pf.add_argument("--id", help="PDB ID or UniProt accession")
    pf.add_argument("--file", help="Path to local FASTA or payload JSON")
    pf.add_argument("--header", help="Substring to match in FASTA header")
    pf.add_argument("--chain", help="Chain letter (PDB) or H/L (payload)")
    pf.add_argument("--species", help="Species for germline lookup (e.g. dog)")
    pf.add_argument("--allele", help="Allele substring for germline lookup (e.g. IGHG2)")

    # optimize
    po = sub.add_parser("optimize", help="Codon-optimize AA → CHO DNA")
    po.add_argument("--aa", help="Inline AA sequence")
    po.add_argument("--aa-file", help="Path to AA FASTA or plain text")
    po.add_argument("--name", help="Sequence name for FASTA header")
    po.add_argument("--no-stop", action="store_true", help="Omit terminal stop codon")
    po.add_argument("--out", help="Output FASTA path")

    # translate
    pt = sub.add_parser("translate", help="DNA ↔ AA translation")
    pt.add_argument("--direction", choices=["dna2aa", "aa2dna"], default="dna2aa")
    pt.add_argument("--dna", help="Inline DNA")
    pt.add_argument("--dna-file", help="DNA FASTA / text file")
    pt.add_argument("--aa", help="Inline AA")
    pt.add_argument("--aa-file", help="AA FASTA / text file")

    # assemble
    pa = sub.add_parser("assemble", help="Assemble full-length chain from parts JSON")
    pa.add_argument("--parts", required=True, help="JSON file with region sequences")
    pa.add_argument("--type", required=True, choices=["HC", "LC", "scFv", "custom"])
    pa.add_argument("--name", help="Output chain name")
    pa.add_argument("--out", help="Output FASTA path")

    # qa
    pq = sub.add_parser("qa", help="Run QA checks on an assembled sequence")
    pq.add_argument("--aa", help="Inline AA sequence")
    pq.add_argument("--aa-file", help="AA FASTA or text file")
    pq.add_argument("--dna-file", help="Optional: CHO DNA FASTA for DNA-level checks")
    pq.add_argument("--ref-file", help="Reference payload JSON or FASTA")
    pq.add_argument("--ref-header", help="Header substring to match in ref FASTA")
    pq.add_argument("--chain", default="HC", choices=["HC", "LC", "VH", "VL", "H", "L"],
                    help="Chain type (HC/LC for FR4 and ref key selection)")
    pq.add_argument("--sp", help="Signal peptide AA (for SP-prefix check)")
    pq.add_argument("--expected-len", type=int, help="Expected AA length")
    pq.add_argument("--out", help="Save QA JSON to this path")

    return p


if __name__ == "__main__":
    parser = build_parser()
    args = parser.parse_args()
    {
        "fetch":     cmd_fetch,
        "optimize":  cmd_optimize,
        "translate": cmd_translate,
        "assemble":  cmd_assemble,
        "qa":        cmd_qa,
    }[args.cmd](args)
