#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Build a non-redundant panel of anti-human CD3ε binders (humanized VH/VL + scFv)
for VH→VHH (engineered single-domain / " VH") conversion.

- Source-of-truth sequences are frozen from in-repo references (engineered_459_atlas,
  SP34 fasta, ACTES canonical scFv).
- Dedupe key: Kabat VH CDR3 amino-acid string (one engineered-VH target per distinct CDR3).

Governance: does NOT modify locked config/*.json. Outputs data/reference JSON only.

Usage:
  python scripts/build_cd3_engineered_vh_panel.py
  python scripts/build_cd3_engineered_vh_panel.py --out-json data/reference/cd3_engineered_vh_panel_v1.json

Optional conversion (requires anarcii env + full vh_to_vhh stack):
  python scripts/build_cd3_engineered_vh_panel.py --run-conversion

See docs/STANDARDS_INDEX.md → VH → VHH Conversion Standard before production runs.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import re
import sys
from dataclasses import dataclass, asdict
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

ROOT = Path(__file__).resolve().parents[1]

G4S3 = "GGGGSGGGGSGGGGS"

# ── Frozen sequences (in-repo; anti-human CD3 / CD3ε clinical lineages) ─────

# Blinatumomab CD3 arm — murine SP34-class (reference fasta)
SP34_VH_MURINE = (
    "DIKLQSGAELARPGASVKMSCKTSGYTFTRYTMHWVKQRPGQGLEWIGYINPSRGYTNYNQKFKDKATLTTDKSSSTAYMQLSSLTSEDSAVYYCARYYDDHYCLDYWGQGTTLTVSS"
)
SP34_VL = (
    "DIQLTQSPAIMSASPGEKVTMTCRASSSVSYMNWYQQKSGTSPKRWIYDTSKVASGVPYRFSGSGSGTSYSLTISSMEAEDAATYYCQQWSSNPLTFGAGTKLELK"
)

# Engineered / clinical IgG-derived VH+VL (data/engineered_459_atlas/master_table.csv)
TEPLIZUMAB_VH = (
    "QVQLVQSGGGVVQPGRSLRLSCKASGYTFTRYTMHWVRQAPGKGLEWIGYINPSRGYTNYNQKVKDRFTISRDNSKNTAFLQMDSLRPEDTGVYFCARYYDDHYCLDYWGQGTPVTVSS"
)
TEPLIZUMAB_VL = (
    "DIQMTQSPSSLSASVGDRVTITCSASSSVSYMNWYQQTPGKAPKRWIYDTSKLASGVPSRFSGSGSGTDYTFTISSLQPEDIATYYCQQWSSNPFTFGQGTKLQIT"
)

VISILIZUMAB_VH = (
    "QVQLVQSGAEVKKPGASVKVSCKASGYTFISYTMHWVRQAPGQGLEWMGYINPRSGYTHYNQKLKDKATLTADKSASTAYMELSSLRSEDTAVYYCARSAYYDYDGFAYWGQGTLVTVSS"
)
VISILIZUMAB_VL = (
    "DIQMTQSPSSLSASVGDRVTITCSASSSVSYMNWYQQKPGKAPKRLIYDTSKLASGVPSRFSGSGSGTDFTLTISSLQPEDFATYYCQQWSSNPPTFGGGTKVEIK"
)

OTELIXIZUMAB_VH = (
    "EVQLLESGGGLVQPGGSLRLSCAASGFTFSSFPMAWVRQAPGKGLEWVSTISTSGGRTYYRDSVKGRFTISRDNSKNTLYLQMNSLRAEDTAVYYCAKFRQYSGGFDYWGQGTLVTVSS"
)
OTELIXIZUMAB_VL = (
    "DIQLTQPNSVSTSLGSTVKLSCTLSSGNIENNYVHWYQLYEGRSPTTMIYDDDKRPDGVPDRFSGSIDRSSNSAFLTIHNVAIEDEAIYFCHSYVSSFNVFGGGTKLTVL"
)

FORALUMAB_VH = (
    "QVQLVESGGGVVQPGRSLRLSCAASGFKFSGYGMHWVRQAPGKGLEWVAVIWYDGSKKYYVDSVKGRFTISRDNSKNTLYLQMNSLRAEDTAVYYCARQMGYWHFDLWGRGTLVTVSS"
)
FORALUMAB_VL = (
    "EIVLTQSPATLSLSPGERATLSCRASQSVSSYLAWYQQKPGQAPRLLIYDASNRATGIPARFSGSGSGTDFTLTISSLEPEDFAVYYCQQRSNWPPLTFGGGTKVEIK"
)

# ACTES OKT3_scFv — VH-linker-VL (humanized OKT3 class; PDB 1SY6 / NCBI lineage in library notes)
OKT3_HU_SCFV = (
    "QVQLVQSGAEVKKPGASVKVSCKASGYTFTRYTMHWVRQAPGQGLEWIGYINPSRGYTNYNQKFKDRVTMTRDTSTSTVYMELSSLRSEDTAVYYCARYYDDHYCLDYWGQGTLVTVSS"
    + G4S3
    + "DIQMTQSPSSLSASVGDRVTITCSASSSVSYMNWYQQKPGKAPKRLIYDTSKLASGVPSRFSGSGSGTDFTLTISSLQPEDFATYYCQQWSSNPFTFGQGTKVEIK"
)


def _kabat_cdr3_vh(vh: str, anarcii_engine: Any = None) -> Tuple[str, str]:
    """
    Return (cdr3_aa, method). Prefer ANARCI+KabatUtils; fallback regex on VH string.
    """
    vh = (vh or "").strip().upper().replace(" ", "")
    method = "regex_fallback"
    try:
        from anarcii import Anarcii  # noqa: PLC0415
        from core.humanization.kabat_utils import cdr_span, kabat_from_anarcii  # noqa: PLC0415

        a = anarcii_engine if anarcii_engine is not None else Anarcii(seq_type="antibody", mode="accuracy")
        a.number([vh])
        entry = a.to_scheme("kabat").get("Sequence 1", {})
        if not entry.get("error") and entry.get("chain_type") == "H":
            kd = kabat_from_anarcii(entry["numbering"])
            c3 = cdr_span(kd, 95, 102)
            if c3:
                return c3.strip(), "anarcii_kabat"
    except Exception:
        pass

    # Fallback: last C…WG[QKR]G / WGRG span before the constant tail (handles WGQG and WGRG FR4)
    for pat in (r"C([A-Z]{3,28}?)WG[QRK]G", r"C([A-Z]{3,28}?)WGRG"):
        matches = list(re.finditer(pat, vh))
        if matches:
            return matches[-1].group(1).strip(), method
    return "", method


def _scfv_vh_vl_teplizumab() -> str:
    return TEPLIZUMAB_VH + G4S3 + TEPLIZUMAB_VL


def _lineage_key(cdr3: str) -> str:
    return hashlib.sha256(cdr3.encode()).hexdigest()[:16]


@dataclass
class RawBinder:
    entry_id: str
    display_name: str
    genetics: str
    input_format: str
    vh_aa: str
    vl_aa: Optional[str]
    scfv_aa: Optional[str]
    source_note: str


def _collect_raw() -> List[RawBinder]:
    return [
        RawBinder(
            "sp34_murine_vh_blinatumomab",
            "SP34 CD3 arm (murine, Blinatumomab)",
            "murine",
            "VH",
            SP34_VH_MURINE,
            SP34_VL,
            SP34_VH_MURINE + G4S3 + SP34_VL,
            "data/reference/SP34_CD3mab_Blinatumomab_CD3_arm_vh_vl_v1.fasta",
        ),
        RawBinder(
            "teplizumab_vh_vl",
            "Teplizumab (humanized murine, Tzield)",
            "humanized",
            "VH_VL",
            TEPLIZUMAB_VH,
            TEPLIZUMAB_VL,
            _scfv_vh_vl_teplizumab(),
            "data/engineered_459_atlas/master_table.csv",
        ),
        RawBinder(
            "visilizumab_vh_vl",
            "Visilizumab (humanized murine)",
            "humanized",
            "VH_VL",
            VISILIZUMAB_VH,
            VISILIZUMAB_VL,
            VISILIZUMAB_VH + G4S3 + VISILIZUMAB_VL,
            "data/engineered_459_atlas + ada curation",
        ),
        RawBinder(
            "otelixizumab_vh_vl",
            "Otelixizumab (humanized murine)",
            "humanized",
            "VH_VL",
            OTELIXIZUMAB_VH,
            OTELIXIZUMAB_VL,
            OTELIXIZUMAB_VH + G4S3 + OTELIXIZUMAB_VL,
            "data/engineered_459_atlas/master_table.csv",
        ),
        RawBinder(
            "foralumab_vh_vl",
            "Foralumab / NI-0401 (fully human)",
            "fully_human",
            "VH_VL",
            FORALUMAB_VH,
            FORALUMAB_VL,
            FORALUMAB_VH + G4S3 + FORALUMAB_VL,
            "data/humanization_assay/384_antibody_germline_assignment.csv",
        ),
        RawBinder(
            "okt3_humanized_scfv_actes",
            "OKT3-class humanized scFv (ACTES canonical)",
            "humanized",
            "scFv",
            OKT3_HU_SCFV.split(G4S3)[0],
            OKT3_HU_SCFV.split(G4S3)[1],
            OKT3_HU_SCFV,
            "data/actes_sequences/ACTES_sequences_canonical.fasta (OKT3_scFv)",
        ),
    ]


def build_panel(run_conversion: bool = False) -> Dict[str, Any]:
    raw = _collect_raw()
    groups: Dict[str, Dict[str, Any]] = {}

    try:
        from anarcii import Anarcii  # noqa: PLC0415

        _an_engine = Anarcii(seq_type="antibody", mode="accuracy")
    except Exception:
        _an_engine = None

    for row in raw:
        cdr3, cdr3_method = _kabat_cdr3_vh(row.vh_aa, _an_engine)
        if not cdr3:
            cdr3 = f"_INVALID_{row.entry_id}"
        key = cdr3
        if key not in groups:
            groups[key] = {
                "cdrh3_kabat": cdr3,
                "cdrh3_annotation_method": cdr3_method,
                "lineage_key": _lineage_key(cdr3),
                "lineage_members": [],
                "vh_for_conversion": None,
                "vh_source_entry_id": None,
                "source_class_for_vh2vhh": None,
            }
        entry = asdict(row)
        entry["cdrh3_kabat"] = cdr3
        entry["cdrh3_annotation_method"] = cdr3_method
        groups[key]["lineage_members"].append(entry)

    # Pick canonical VH for conversion: prefer humanized > fully_human > murine
    rank = {"humanized": 0, "fully_human": 1, "murine": 2}

    for _cdr3, g in groups.items():
        members = sorted(
            g["lineage_members"],
            key=lambda m: (rank.get(m["genetics"], 9), m["entry_id"]),
        )
        canonical = members[0]
        g["vh_for_conversion"] = canonical["vh_aa"]
        g["vh_source_entry_id"] = canonical["entry_id"]
        # Map to VhToVhhRequest source_class
        sc_map = {
            "humanized": "humanized_mab",
            "fully_human": "human_mab",
            "murine": "murine_mab",
        }
        g["source_class_for_vh2vhh"] = sc_map.get(canonical["genetics"], "conventional_vh")
        g["lineage_members"] = members

    out: Dict[str, Any] = {
        "panel_id": "cd3_engineered_vh_panel_v1",
        "panel_version": "1.0.0",
        "target_antigen": "human CD3E (CD3ε; TCR–CD3 complex)",
        "dedupe_rule": "Distinct Kabat VH CDR-H3 amino-acid sequence; one conversion input per CDR-H3.",
        "n_unique_cdrh3": len(groups),
        "n_raw_entries": len(raw),
        "groups": list(groups.values()),
    }

    if run_conversion:
        try:
            from api.job_store import jobs  # noqa: PLC0415
            from api.routers.vh_to_vhh import VhToVhhRequest, _vh2vhh_impl  # noqa: PLC0415
        except ImportError as e:
            out["conversion_error"] = f"Import failed: {e}"
            return out

        conversions = []
        for g in out["groups"]:
            job_id = f"cd3_panel_{g['lineage_key']}"
            jobs[job_id] = {
                "id": job_id,
                "status": "running",
                "progress": 0,
                "progress_note": "cd3 engineered VH panel batch",
                "result": None,
            }
            req = VhToVhhRequest(
                vh_sequence=g["vh_for_conversion"],
                source_class=g["source_class_for_vh2vhh"],
                sequence_name=f"CD3_panel_{g['lineage_key']}",
            )
            try:
                _vh2vhh_impl(job_id, req)
                conversions.append(
                    {
                        "lineage_key": g["lineage_key"],
                        "cdrh3_kabat": g["cdrh3_kabat"],
                        "job_id": job_id,
                        "result": jobs.get(job_id, {}).get("result"),
                    }
                )
            except Exception as ex:  # noqa: BLE001
                conversions.append(
                    {
                        "lineage_key": g["lineage_key"],
                        "error": str(ex),
                    }
                )
        out["conversions"] = conversions

    return out


def main() -> int:
    ap = argparse.ArgumentParser(description="Build CD3 binder → engineered VH panel JSON")
    ap.add_argument(
        "--out-json",
        type=Path,
        default=ROOT / "data" / "reference" / "cd3_engineered_vh_panel_v1.json",
        help="Output JSON path",
    )
    ap.add_argument(
        "--run-conversion",
        action="store_true",
        help="Run full VH→VHH pipeline per group (slow; needs anarcii/optional tools)",
    )
    args = ap.parse_args()

    sys.path.insert(0, str(ROOT))
    panel = build_panel(run_conversion=args.run_conversion)
    args.out_json.parent.mkdir(parents=True, exist_ok=True)
    with open(args.out_json, "w", encoding="utf-8") as f:
        json.dump(panel, f, ensure_ascii=False, indent=2)
    print(f"Wrote {args.out_json} ({panel['n_unique_cdrh3']} unique CDR-H3, {panel['n_raw_entries']} raw rows)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
