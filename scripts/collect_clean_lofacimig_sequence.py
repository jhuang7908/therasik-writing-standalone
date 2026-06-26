#!/usr/bin/env python3
"""
Collect and clean the authoritative Lofacimig sequence from NCATS/GSRS.

Source endpoint:
  https://drugs.ncats.io/api/v1/substances(L55HB62LXD)

Outputs:
  data/sequence_provenance/lofacimig/lofacimig_ncats_gsrs_full_chain_v1.json
  data/sequence_provenance/lofacimig/lofacimig_ncats_gsrs_full_chain_v1.fasta

The cleaned chain is a 493 aa VH1-GAP-VH2-G1(h-CH2-CH3) heavy chain.
Observed boundaries from the NCATS sequence are VH1(130)-GAP(3)-VH2(126)-G1(234).
This is not a single-domain VHH cohort row and must not be merged into VHH42.
"""
from __future__ import annotations

import argparse
import json
import re
import sys
import urllib.request
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Tuple


SUITE = Path(__file__).resolve().parents[1]
if str(SUITE) not in sys.path:
    sys.path.insert(0, str(SUITE))

from core.numbering.imgt_anarcii import IMGTNumberingError, imgt_number_anarcii
from core.vhh_humanization import split_regions


NCATS_URL = "https://drugs.ncats.io/api/v1/substances(L55HB62LXD)"
UNII = "L55HB62LXD"
GAP_LINKER = "GAP"
G1_START = "GSEPKSSDKTHTCPPCPAPE"


def _fetch_ncats_json(url: str = NCATS_URL) -> Dict[str, Any]:
    with urllib.request.urlopen(url, timeout=30) as response:
        return json.loads(response.read().decode("utf-8"))


def _clean_aa(seq: str) -> str:
    cleaned = re.sub(r"[^A-Za-z]", "", seq or "").upper()
    if not cleaned or re.search(r"[^ACDEFGHIKLMNPQRSTVWY]", cleaned):
        raise ValueError("Sequence contains non-canonical amino acid characters after cleaning")
    return cleaned


def _extract_subunit_sequences(payload: Dict[str, Any]) -> List[Dict[str, Any]]:
    protein = payload.get("protein") or {}
    subunits = protein.get("subunits") or []
    out = []
    for sub in subunits:
        seq = _clean_aa(sub.get("sequence") or "")
        out.append(
            {
                "subunit_index": sub.get("subunitIndex"),
                "length_reported": sub.get("length"),
                "sequence": seq,
                "length_cleaned": len(seq),
            }
        )
    if not out:
        raise ValueError("No protein subunits found in NCATS payload")
    return out


def _split_chain(seq: str) -> Dict[str, str]:
    """Split VH1-GAP-VH2-Fc using NCATS boundaries and observed Fc start."""
    if len(seq) != 493:
        raise ValueError(f"Expected Lofacimig chain length 493, got {len(seq)}")
    vh1 = seq[:130]
    linker = seq[130:133]
    rest = seq[133:]
    if linker != GAP_LINKER:
        raise ValueError(f"Expected GAP linker at 131-133, got {linker!r}")
    fc_idx = rest.find(G1_START)
    if fc_idx < 0:
        raise ValueError(f"Could not find Fc/G1 start motif {G1_START!r}")
    vh2 = rest[:fc_idx]
    fc = rest[fc_idx:]
    if len(vh2) < 110:
        raise ValueError(f"VH2 before Fc motif is too short for an antibody VH domain: {len(vh2)}")
    return {
        "VH1": vh1,
        "linker_GAP": linker,
        "VH2": vh2,
        "G1_h_CH2_CH3": fc,
    }


def _imgt_regions(seq: str) -> Tuple[Dict[str, str], Dict[str, int]]:
    rows = imgt_number_anarcii(seq)
    regions = split_regions(rows)
    lengths = {k: len(regions[k]) for k in ("CDR1", "CDR2", "CDR3")}
    return regions, lengths


def _write_fasta(path: Path, records: List[Tuple[str, str]]) -> None:
    lines: List[str] = []
    for header, seq in records:
        lines.append(f">{header}")
        for i in range(0, len(seq), 80):
            lines.append(seq[i : i + 80])
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def main() -> None:
    ap = argparse.ArgumentParser(description="Collect and clean Lofacimig sequence from NCATS/GSRS")
    ap.add_argument("--out-dir", type=Path, default=SUITE / "data/sequence_provenance/lofacimig")
    ap.add_argument("--source-url", default=NCATS_URL)
    args = ap.parse_args()

    args.out_dir.mkdir(parents=True, exist_ok=True)
    payload = _fetch_ncats_json(args.source_url)
    subunits = _extract_subunit_sequences(payload)

    unique_sequences = sorted({s["sequence"] for s in subunits})
    if len(unique_sequences) != 1:
        raise SystemExit(f"Expected identical homodimer subunits; got {len(unique_sequences)} distinct sequences")

    chain = unique_sequences[0]
    parts = _split_chain(chain)

    vh_regions: Dict[str, Any] = {}
    for domain in ("VH1", "VH2"):
        try:
            regions, cdr_lengths = _imgt_regions(parts[domain])
        except IMGTNumberingError as e:
            raise SystemExit(f"IMGT numbering failed for {domain}: {e}") from e
        vh_regions[domain] = {
            "sequence": parts[domain],
            "length": len(parts[domain]),
            "imgt_regions": regions,
            "cdr_lengths": cdr_lengths,
        }

    cleaned = {
        "record_id": "lofacimig_ncats_gsrs_full_chain_v1",
        "inn": "Lofacimig",
        "unii": UNII,
        "generated_at_utc": datetime.now(timezone.utc).isoformat(),
        "source": {
            "url": args.source_url,
            "source_type": "NCATS/GSRS API",
            "approval_id": payload.get("approvalID"),
            "substance_class": payload.get("substanceClass"),
            "protein_type": (payload.get("protein") or {}).get("proteinType"),
            "sequence_origin": (payload.get("protein") or {}).get("sequenceOrigin"),
            "sequence_type": (payload.get("protein") or {}).get("sequenceType"),
            "definition_level": payload.get("definitionLevel"),
        },
        "classification": {
            "entity_class": "humanized_camelid_tandem_vh_fc",
            "modality": "VH1-GAP-VH2-G1(h-CH2-CH3) homodimer",
            "not_single_domain_vhh": True,
            "do_not_merge_into_vhh42": True,
        },
        "subunits": [
            {
                "subunit_index": s["subunit_index"],
                "length_reported": s["length_reported"],
                "length_cleaned": s["length_cleaned"],
                "matches_consensus_chain": s["sequence"] == chain,
            }
            for s in subunits
        ],
        "chain": {
            "sequence": chain,
            "length": len(chain),
            "segments": {
                "VH1": {"start_1based": 1, "end_1based": 130, "length": len(parts["VH1"])},
                "linker_GAP": {"start_1based": 131, "end_1based": 133, "sequence": parts["linker_GAP"]},
            "VH2": {"start_1based": 134, "end_1based": 133 + len(parts["VH2"]), "length": len(parts["VH2"])},
            "G1_h_CH2_CH3": {
                "start_1based": 134 + len(parts["VH2"]),
                "end_1based": 493,
                "length": len(parts["G1_h_CH2_CH3"]),
            },
            },
        },
        "domains": vh_regions,
        "constant_region": {
            "G1_h_CH2_CH3": parts["G1_h_CH2_CH3"],
            "length": len(parts["G1_h_CH2_CH3"]),
        },
        "notes": [
            "NCATS/GSRS provides two identical 493 aa subunits, consistent with a homodimer.",
            "N-terminal Q->pidolic acid and C-terminal K removal are structural modifications; raw AA chain is retained here for sequence provenance.",
            "This artifact resolves the earlier metadata-only status for full-chain collection, but the molecule remains excluded from single-domain VHH cohort statistics.",
        ],
    }

    json_path = args.out_dir / "lofacimig_ncats_gsrs_full_chain_v1.json"
    json_path.write_text(json.dumps(cleaned, indent=2, ensure_ascii=False), encoding="utf-8")

    records: List[Tuple[str, str]] = [
        ("Lofacimig_full_chain_493aa|NCATS_GSRS|VH1-GAP-VH2-G1", chain),
        ("Lofacimig_VH1_1-130|IMGT", parts["VH1"]),
        ("Lofacimig_linker_131-133|GAP", parts["linker_GAP"]),
        ("Lofacimig_VH2_134-263|IMGT", parts["VH2"]),
        ("Lofacimig_G1_h_CH2_CH3_264-493", parts["G1_h_CH2_CH3"]),
    ]
    for domain in ("VH1", "VH2"):
        for region, region_seq in vh_regions[domain]["imgt_regions"].items():
            records.append((f"Lofacimig_{domain}_{region}|IMGT", region_seq))
    fasta_path = args.out_dir / "lofacimig_ncats_gsrs_full_chain_v1.fasta"
    _write_fasta(fasta_path, records)

    readme_path = args.out_dir / "README.md"
    readme_path.write_text(
        "# Lofacimig — sequence provenance\n\n"
        "Primary cleaned artifact: `lofacimig_ncats_gsrs_full_chain_v1.json`.\n\n"
        f"Source: `{args.source_url}` (NCATS/GSRS API, UNII `{UNII}`).\n\n"
        "The NCATS/GSRS record provides two identical 493 aa heavy-chain subunits. "
        "The cleaned sequence is segmented as VH1(1-130)-GAP(131-133)-VH2(134-259)-G1(h-CH2-CH3)(260-493).\n\n"
        "This is a humanized camelid-derived tandem VH-Fc clinical molecule, not a single-domain VHH cohort row. "
        "Do not merge it into VHH42 or single-domain VHH CMC calibration without an explicit governance decision.\n",
        encoding="utf-8",
    )

    print(f"Wrote {json_path.relative_to(SUITE)}")
    print(f"Wrote {fasta_path.relative_to(SUITE)}")
    print("VH1 CDR lengths:", vh_regions["VH1"]["cdr_lengths"])
    print("VH2 CDR lengths:", vh_regions["VH2"]["cdr_lengths"])
    print("Full chain length:", len(chain))


if __name__ == "__main__":
    main()
