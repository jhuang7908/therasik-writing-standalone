#!/usr/bin/env python3
"""
Build a production-oriented Felis catus VH/VL scaffold registry.

This script turns raw feline IGHV candidates and local IMGT light-chain
references into a ranked scaffold JSON suitable for petization routing.
It deliberately does not mutate germlines; it filters, normalizes, annotates,
and ranks them by simple developability features.

Cleaning pipeline (normative order — owner policy 2026-04-29):
  1. Signal peptide removal — VH: ``normalize_vh_candidate`` (canonical N-term
     motifs; records trim in ``normalization_notes``). Light chains: IMGT
     V-REGION entries are usually pre-clipped; no extra trim unless invalid AA.
  2. Length gates — min length after trim; successful Kabat numbering; non-empty
     FR1/FR2/FR3; full variable-domain span for scaffold (see ``process_sequence``).
  3. Deduplication — drop second and later rows with identical
     ``FR1+FR2+FR3`` (``fr1_3_concat``) within each chain class (VH / VL).
  4. Segmentation — ``extract_fr_segments`` + ``extract_cdr_lengths`` from
     Kabat numbering on the retained sequence.
  5. Per-template triage — ``scan_cmc_liabilities`` (full domain + FR13-only)
     and ``simple_developability`` (pI, instability, GRAVY, etc.); tier from flags.
"""

from __future__ import annotations

import argparse
import json
import re
import sys
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, Iterable, List, Optional, Tuple

from Bio.SeqUtils.ProtParam import ProteinAnalysis

SUITE = Path(__file__).resolve().parents[1]
if str(SUITE) not in sys.path:
    sys.path.insert(0, str(SUITE))

from core.cmc.generic_cmc_scanner import scan_cmc_liabilities  # noqa: E402
from core.humanization.kabat_utils import get_kabat_numbering, is_in_cdr, sorted_keys  # noqa: E402


CAT_DIR = SUITE / "data" / "germlines" / "felis_catus_ig_aa"
DEFAULT_VH_FASTA = (
    SUITE / "data" / "germlines" / "fc_aa" / "fc_database" / "cat" / "IGHC_cat_vh_candidates.fasta"
)
DEFAULT_IGKV_JSON = CAT_DIR / "IGKV_aa.json"
DEFAULT_IGLV_JSON = CAT_DIR / "IGLV_aa.json"
DEFAULT_OUT = CAT_DIR / "cat_scaffold_cmc_optimization_tier1_tier2_v1.json"
DEFAULT_AUDIT = CAT_DIR / "cat_scaffold_cmc_optimization_tier1_tier2_v1_audit.json"

FR_RANGES = {
    "VH": {"FR1": (1, 25), "FR2": (36, 49), "FR3": (66, 94)},
    "VL": {"FR1": (1, 23), "FR2": (35, 49), "FR3": (57, 88)},
}

VH_START_PATTERNS = ("EVQL", "DVQL", "QVQL", "QVLL", "EQLV", "QLTL", "PTLRES", "TLRES")
CONSTANT_TAIL_MARKERS = (
    "ASTTAPSV",
    "ASPKAPSV",
    "SSETSSR",
    "RTVAAPSV",
    "TVAAPSV",
)
VALID_AA = set("ACDEFGHIKLMNPQRSTVWY")

# Documented in module docstring; echoed in build audit JSON.
CLEANING_PIPELINE_STEPS: List[str] = [
    "1_signal_peptide_and_nterm_trim",
    "2_length_and_kabat_gates",
    "3_dedupe_by_fr1_fr2_fr3",
    "4_kabat_segmentation_fr_and_cdr",
    "5_cmc_and_developability_per_template",
]


def parse_fasta(path: Path) -> List[Tuple[str, str]]:
    records: List[Tuple[str, str]] = []
    if not path.exists():
        return records
    header = ""
    seq_parts: List[str] = []
    for raw in path.read_text(encoding="utf-8").splitlines():
        line = raw.strip()
        if not line:
            continue
        if line.startswith(">"):
            if header:
                records.append((header, "".join(seq_parts).upper()))
            header = line[1:].strip()
            seq_parts = []
        else:
            seq_parts.append(line)
    if header:
        records.append((header, "".join(seq_parts).upper()))
    return records


def normalize_vh_candidate(raw_seq: str) -> Tuple[str, List[str]]:
    notes: List[str] = []
    seq = "".join(aa for aa in raw_seq.upper() if aa.isalpha())
    if any(aa not in VALID_AA for aa in seq):
        bad = sorted({aa for aa in seq if aa not in VALID_AA})
        return "", [f"invalid_aa:{','.join(bad)}"]

    start = -1
    for motif in VH_START_PATTERNS:
        pos = seq.find(motif)
        if pos >= 0 and (start < 0 or pos < start):
            start = pos
    if start > 0:
        notes.append(f"signal_peptide_trimmed:{start}")
        seq = seq[start:]
    elif start < 0:
        notes.append("no_canonical_vh_start")

    tail_positions = [seq.find(marker) for marker in CONSTANT_TAIL_MARKERS if seq.find(marker) > 0]
    if tail_positions:
        cut = min(tail_positions)
        notes.append(f"constant_tail_trimmed:{cut}")
        seq = seq[:cut]

    return seq, notes


def normalize_light_candidate(raw_seq: str) -> Tuple[str, List[str]]:
    seq = "".join(aa for aa in raw_seq.upper() if aa.isalpha())
    if any(aa not in VALID_AA for aa in seq):
        bad = sorted({aa for aa in seq if aa not in VALID_AA})
        return "", [f"invalid_aa:{','.join(bad)}"]
    return seq, []


def extract_fr_segments(kd: Dict[Tuple[int, str], str], chain: str) -> Dict[str, str]:
    out = {"FR1": "", "FR2": "", "FR3": ""}
    for region, (lo, hi) in FR_RANGES[chain].items():
        out[region] = "".join(
            kd[key]
            for key in sorted_keys(kd)
            if lo <= key[0] <= hi and not is_in_cdr(key[0], chain)
        )
    return out


def extract_cdr_lengths(kd: Dict[Tuple[int, str], str], chain: str) -> Dict[str, int]:
    ranges = {
        "VH": {"1": (26, 35), "2": (50, 65), "3": (95, 102)},
        "VL": {"1": (24, 34), "2": (50, 56), "3": (89, 97)},
    }
    return {
        cdr: sum(1 for key in kd if lo <= key[0] <= hi)
        for cdr, (lo, hi) in ranges[chain].items()
    }


def simple_developability(seq: str) -> Dict[str, Any]:
    analysis = ProteinAnalysis(seq)
    return {
        "length": len(seq),
        "pI": round(float(analysis.isoelectric_point()), 2),
        "instability_index": round(float(analysis.instability_index()), 2),
        "gravy": round(float(analysis.gravy()), 3),
        "aromaticity": round(float(analysis.aromaticity()), 3),
    }


def tier_from_metrics(flags: int, p_i: float, instability: float) -> str:
    if flags <= 4 and 5.5 <= p_i <= 9.0 and instability < 55:
        return "tier1"
    if flags <= 8 and 4.8 <= p_i <= 9.5 and instability < 70:
        return "tier2"
    return "tier3"


def cmc_rank_key(row: Dict[str, Any]) -> Tuple[int, float, float, str]:
    metrics = row["developability"]
    p_i = float(metrics["pI"])
    p_i_penalty = min(abs(p_i - 7.5), abs(p_i - 8.0))
    return (
        int(row["cmc_full"]["summary"]["total_flags"]),
        float(metrics["instability_index"]),
        p_i_penalty,
        str(row["gene"]),
    )


def process_sequence(
    header: str,
    seq: str,
    chain: str,
    locus: str,
    gene: str,
    source: str,
    normalization_notes: Optional[List[str]] = None,
) -> Tuple[Optional[Dict[str, Any]], Optional[str]]:
    normalization_notes = normalization_notes or []
    if len(seq) < (85 if chain == "VH" else 75):
        return None, "too_short_after_normalization"

    kd = get_kabat_numbering(seq)
    if not kd:
        return None, "kabat_numbering_failed"

    fr_segments = extract_fr_segments(kd, chain)
    if not all(fr_segments.values()):
        return None, "missing_fr_segment"

    max_scaffold_pos = 113 if chain == "VH" else 107
    scaffold_seq = "".join(kd[key] for key in sorted_keys(kd) if key[0] <= max_scaffold_pos)
    if len(scaffold_seq) < (95 if chain == "VH" else 85):
        return None, "incomplete_variable_domain"

    fr123 = fr_segments["FR1"] + fr_segments["FR2"] + fr_segments["FR3"]
    cmc_full = scan_cmc_liabilities(scaffold_seq)
    # Framework-only scan: FR1+FR2+FR3 (no CDR); legacy builds skipped FR2 — fixed 2026-04-29.
    cmc_fr13 = scan_cmc_liabilities(fr123)
    developability = simple_developability(scaffold_seq)
    tier = tier_from_metrics(
        int(cmc_full["summary"]["total_flags"]),
        float(developability["pI"]),
        float(developability["instability_index"]),
    )
    row = {
        "tier": tier,
        "chain": chain,
        "locus": locus,
        "gene": gene,
        "imgt_functionality": "candidate",
        "source": source,
        "raw_header": header,
        "normalization_notes": normalization_notes,
        "sequence_aa_kabat_norm": scaffold_seq,
        "fr_segments": fr_segments,
        "fr1_3_concat": fr123,
        "cdr_lengths": extract_cdr_lengths(kd, chain),
        "developability": developability,
        "cmc_full": cmc_full,
        "cmc_fr13_only": cmc_fr13,
        "optimization": {
            "sequence_aa_opt": scaffold_seq,
            "mutations": [],
            "note": "No germline mutation applied; production registry ranks native feline candidates.",
        },
    }
    return row, None


def load_light_entries(path: Path) -> Iterable[Tuple[str, str]]:
    data = json.loads(path.read_text(encoding="utf-8"))
    for entry in data.get("entries", []):
        gid = str(entry.get("id") or entry.get("gene") or "").strip()
        seq = str(entry.get("sequence_aa") or "").strip()
        if gid and seq:
            yield gid, seq


def build_registry(vh_fasta: Path, igkv_json: Path, iglv_json: Path) -> Tuple[Dict[str, Any], Dict[str, Any]]:
    rows: List[Dict[str, Any]] = []
    audit: Dict[str, Any] = {
        "built_at": datetime.now().isoformat(timespec="seconds"),
        "cleaning_pipeline": CLEANING_PIPELINE_STEPS,
        "inputs": {
            "vh_fasta": str(vh_fasta),
            "igkv_json": str(igkv_json),
            "iglv_json": str(iglv_json),
        },
        "rejected": [],
        "counts": {},
    }

    seen_vh_fr123: set = set()
    seen_vl_fr123: set = set()
    vh_idx = 1
    for header, raw_seq in parse_fasta(vh_fasta):
        normalized, notes = normalize_vh_candidate(raw_seq)
        if not normalized:
            audit["rejected"].append({"header": header, "reason": ";".join(notes)})
            continue
        row, reason = process_sequence(
            header=header,
            seq=normalized,
            chain="VH",
            locus="IGHV",
            gene=f"IGHV-Cat-{vh_idx:03d}",
            source="NCBI Protein feline IGHV candidate",
            normalization_notes=notes,
        )
        if reason or row is None:
            audit["rejected"].append({"header": header, "reason": reason})
            continue
        key123 = row["fr1_3_concat"]
        if key123 in seen_vh_fr123:
            audit["rejected"].append({"header": header, "reason": "duplicate_fr1_fr2_fr3"})
            continue
        seen_vh_fr123.add(key123)
        rows.append(row)
        vh_idx += 1

    for locus, json_path in (("IGKV", igkv_json), ("IGLV", iglv_json)):
        if not json_path.exists():
            continue
        for gid, raw_seq in load_light_entries(json_path):
            normalized, notes = normalize_light_candidate(raw_seq)
            row, reason = process_sequence(
                header=gid,
                seq=normalized,
                chain="VL",
                locus=locus,
                gene=gid,
                source=f"IMGT Felis catus {locus}",
                normalization_notes=notes,
            )
            if reason or row is None:
                audit["rejected"].append({"header": gid, "reason": reason})
                continue
            key123 = row["fr1_3_concat"]
            if key123 in seen_vl_fr123:
                audit["rejected"].append({"header": gid, "reason": "duplicate_vl_fr1_fr2_fr3"})
                continue
            seen_vl_fr123.add(key123)
            rows.append(row)

    rows.sort(key=lambda row: (row["chain"], row["locus"], cmc_rank_key(row)))
    for rank, row in enumerate([r for r in rows if r["chain"] == "VH"], start=1):
        row["rank_within_chain"] = rank
    for rank, row in enumerate([r for r in rows if r["chain"] == "VL"], start=1):
        row["rank_within_chain"] = rank

    payload = {
        "artifact_id": "cat_scaffold_cmc_optimization_tier1_tier2_v1",
        "version": "1.0.2",
        "built_at": audit["built_at"],
        "builder": "scripts/build_cat_production_germline_library_v2.py",
        "cleaning_pipeline": CLEANING_PIPELINE_STEPS,
        "status": "production_candidate",
        "notes": [
            "VH candidates are NCBI feline IGHV protein records normalized to Kabat variable domains.",
            "VL candidates are local IMGT Felis catus IGKV/IGLV references.",
            "Developability metrics are sequence-only triage; structural QC remains mandatory at design time.",
            "Cleaning pipeline (ordered): signal peptide / N-term trim → length+Kabat gates → dedupe by FR1+FR2+FR3 → Kabat FR/CDR split → per-row CMC + developability (see audit.cleaning_pipeline).",
        ],
        "selection_guidance": {
            "preferred_tiers": ["tier1", "tier2"],
            "avoid_for_production": "tier3 unless no scaffold is compatible and surface-reshaping route is selected.",
            "fc_recommendation": "Use native cat IgG2 for effector-silent programs; do not use Merck-claimed IgG1 D151A/N183A.",
            "human_fc_mutation_reference_only": [
                "LALA-PG",
                "LS",
                "YTE",
            ],
        },
        "rows": rows,
    }

    audit["counts"] = {
        "rows_total": len(rows),
        "vh": sum(1 for row in rows if row["chain"] == "VH"),
        "vl": sum(1 for row in rows if row["chain"] == "VL"),
        "tier1": sum(1 for row in rows if row["tier"] == "tier1"),
        "tier2": sum(1 for row in rows if row["tier"] == "tier2"),
        "tier3": sum(1 for row in rows if row["tier"] == "tier3"),
        "rejected": len(audit["rejected"]),
    }
    return payload, audit


def main() -> None:
    parser = argparse.ArgumentParser(description="Build production candidate Felis catus VH/VL scaffold registry")
    parser.add_argument("--vh-fasta", type=Path, default=DEFAULT_VH_FASTA)
    parser.add_argument("--igkv-json", type=Path, default=DEFAULT_IGKV_JSON)
    parser.add_argument("--iglv-json", type=Path, default=DEFAULT_IGLV_JSON)
    parser.add_argument("--out", type=Path, default=DEFAULT_OUT)
    parser.add_argument("--audit", type=Path, default=DEFAULT_AUDIT)
    args = parser.parse_args()

    payload, audit = build_registry(args.vh_fasta, args.igkv_json, args.iglv_json)
    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text(json.dumps(payload, indent=2, ensure_ascii=False), encoding="utf-8")
    args.audit.write_text(json.dumps(audit, indent=2, ensure_ascii=False), encoding="utf-8")

    counts = audit["counts"]
    print(
        "Built cat scaffold registry: "
        f"{counts['rows_total']} rows ({counts['vh']} VH, {counts['vl']} VL), "
        f"tier1={counts['tier1']}, tier2={counts['tier2']}, tier3={counts['tier3']}, "
        f"rejected={counts['rejected']}"
    )
    print(f"Output: {args.out}")


if __name__ == "__main__":
    main()
