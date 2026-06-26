#!/usr/bin/env python
"""
Build per-clone CDR numbering crosswalk for PAG-1 VAM (001 / 008 / 7M16).

Maps every CDR residue across:
  - linear (0-based seq index)
  - PDB residue number (Boltz chain H/L/A)
  - IMGT position (fingerprint prior / CHECK 6)
  - Kabat position (V5.1 union — humanization canonical)
  - Chothia loop position (structure/HADDOCK annotation)

Also emits Stage-2 Ala-scan mutation list for ALL six CDR loops (VH+VL).
CDR priority for saturation mutagenesis is determined AFTER Ala scan — no VAM
protocol change; this script supplies clone-specific coordinates only.

Usage:
  conda run -n anarcii python scripts/build_pag1_clone_numbering.py
  conda run -n anarcii python scripts/build_pag1_clone_numbering.py --clone 001
"""

from __future__ import annotations

import argparse
import json
import re
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from core.humanization.kabat_utils import (  # noqa: E402
    CDR_RANGES_VH,
    CDR_RANGES_VL,
    kabat_from_anarcii,
)
from core.numbering.dual_map import build_dual_map  # noqa: E402
from core.numbering.vhvl_scheme_regions import (  # noqa: E402
    split_regions_chothia_vh,
    split_regions_chothia_vl,
    split_regions_kabat_vh,
    split_regions_kabat_vl,
)

MANIFEST = ROOT / "projects/PAG project/numbering/clones_manifest.json"
OUT_DIR = ROOT / "projects/PAG project/numbering"

AA3_TO_1 = {
    "ALA": "A", "ARG": "R", "ASN": "N", "ASP": "D", "CYS": "C",
    "GLN": "Q", "GLU": "E", "GLY": "G", "HIS": "H", "ILE": "I",
    "LEU": "L", "LYS": "K", "MET": "M", "PHE": "F", "PRO": "P",
    "SER": "S", "THR": "T", "TRP": "W", "TYR": "Y", "VAL": "V",
}

# IMGT CDR boundaries (VAM CHECK 6 / fingerprint prior)
IMGT_CDR_VH = [("vh_cdr1", 25, 31), ("vh_cdr2", 48, 56), ("vh_cdr3", 94, 106)]
IMGT_CDR_VL = [("vl_cdr1", 24, 34), ("vl_cdr2", 48, 56), ("vl_cdr3", 89, 97)]

# Chothia loop bands on Kabat-position keys (ANARCII chothia scheme)
CHOTHIA_CDR_VH = [("vh_cdr1", 26, 32), ("vh_cdr2", 52, 56), ("vh_cdr3", 95, 102)]
CHOTHIA_CDR_VL = [("vl_cdr1", 24, 34), ("vl_cdr2", 50, 56), ("vl_cdr3", 89, 97)]

KABAT_CDR_VH = [
    (name, lo, hi)
    for name, (lo, hi) in zip(["vh_cdr1", "vh_cdr2", "vh_cdr3"], CDR_RANGES_VH)
]
KABAT_CDR_VL = [
    (name, lo, hi)
    for name, (lo, hi) in zip(["vl_cdr1", "vl_cdr2", "vl_cdr3"], CDR_RANGES_VL)
]

BOLTZ = {"vh": "H", "vl": "L", "antigen": "A"}
HADDOCK = {"vh": "A", "vl": "B", "antigen": "C"}


def _parse_pdb_chain(pdb_path: Path) -> dict[str, list[dict[str, Any]]]:
    chains: dict[str, list[dict[str, Any]]] = {}
    seen: set[tuple[str, int, str]] = set()
    with pdb_path.open(encoding="utf-8", errors="replace") as fh:
        for line in fh:
            if line[:6].strip() != "ATOM":
                continue
            chain = line[21].strip()
            if not chain:
                continue
            try:
                resi = int(line[22:26].strip())
            except ValueError:
                continue
            icode = line[26].strip()
            key = (chain, resi, icode)
            if key in seen:
                continue
            seen.add(key)
            aa = AA3_TO_1.get(line[17:20].strip().upper(), "X")
            linear_idx = len(chains.setdefault(chain, []))
            chains[chain].append({
                "linear_idx": linear_idx,
                "pdb_resi": resi,
                "icode": icode,
                "aa": aa,
            })
    return chains


def _imgt_int(label: str | None) -> int | None:
    if not label:
        return None
    m = re.match(r"^(\d+)", str(label))
    return int(m.group(1)) if m else None


def _kabat_int(label: str | None) -> int | None:
    return _imgt_int(label)


def _in_range(pos: int | None, lo: int, hi: int) -> bool:
    return pos is not None and lo <= pos <= hi


def _region_for(pos: int | None, bands: list[tuple[str, int, int]]) -> str | None:
    if pos is None:
        return None
    for name, lo, hi in bands:
        if lo <= pos <= hi:
            return name
    return None


def _anarcii_kabat_dict(seq: str) -> dict:
    from anarcii import Anarcii

    eng = Anarcii(seq_type="antibody", mode="accuracy", cpu=True, verbose=False)
    eng.number(seq.strip().upper())
    result = eng.to_scheme("kabat")
    key = next(iter(result))
    entry = result[key]
    return kabat_from_anarcii(entry["numbering"])


def _region_strings(kd, chain_kind: str) -> dict[str, str]:
    if chain_kind == "VH":
        return {
            "kabat": split_regions_kabat_vh(kd),
            "chothia": split_regions_chothia_vh(kd),
        }
    return {
        "kabat": split_regions_kabat_vl(kd),
        "chothia": split_regions_chothia_vl(kd),
    }


def _build_chain_table(
    seq: str,
    pdb_records: list[dict[str, Any]],
    chain_role: str,
    boltz_chain: str,
    haddock_chain: str,
) -> dict[str, Any]:
    pdb_seq = "".join(r["aa"] for r in pdb_records)
    if pdb_seq != seq:
        raise ValueError(
            f"Sequence mismatch on chain {boltz_chain}: "
            f"PDB len={len(pdb_seq)} ANARCII len={len(seq)}"
        )

    dual_map, status, chain_type = build_dual_map(seq)
    kd = _anarcii_kabat_dict(seq)
    regions = _region_strings(kd, chain_role)

    imgt_bands = IMGT_CDR_VH if chain_role == "VH" else IMGT_CDR_VL
    kabat_bands = KABAT_CDR_VH if chain_role == "VH" else KABAT_CDR_VL
    chothia_bands = CHOTHIA_CDR_VH if chain_role == "VH" else CHOTHIA_CDR_VL

    residues: list[dict[str, Any]] = []
    scheme_groups: dict[str, dict[str, list[dict[str, Any]]]] = {
        "kabat": {},
        "chothia": {},
        "imgt": {},
    }

    for entry in dual_map:
        idx = entry["seq_idx"]
        rec = pdb_records[idx]
        imgt_i = _imgt_int(entry.get("imgt_pos"))
        kabat_i = _kabat_int(entry.get("kabat_pos"))

        imgt_region = _region_for(imgt_i, imgt_bands)
        kabat_region = _region_for(kabat_i, kabat_bands)
        chothia_region = _region_for(kabat_i, chothia_bands)

        row = {
            "linear_idx": idx,
            "pdb_resi": rec["pdb_resi"],
            "icode": rec["icode"],
            "aa": entry["aa"],
            "imgt_pos": entry.get("imgt_pos"),
            "kabat_pos": entry.get("kabat_pos"),
            "imgt_cdr": imgt_region,
            "kabat_cdr": kabat_region,
            "chothia_cdr": chothia_region,
            "boltz_chain": boltz_chain,
            "haddock_chain": haddock_chain,
            "mutation_key": f"{boltz_chain}:{rec['pdb_resi']}:{entry['aa']}",
        }
        residues.append(row)

        for scheme, region in (
            ("kabat", kabat_region),
            ("chothia", chothia_region),
            ("imgt", imgt_region),
        ):
            if region:
                scheme_groups[scheme].setdefault(region, []).append(row)

    loci_order = (
        ["vh_cdr1", "vh_cdr2", "vh_cdr3"]
        if chain_role == "VH"
        else ["vl_cdr1", "vl_cdr2", "vl_cdr3"]
    )

    def _summarize_cdr(scheme: str, name: str) -> dict[str, Any]:
        rows = scheme_groups[scheme].get(name, [])
        if not rows:
            return {"locus": name, "scheme": scheme, "present": False}
        return {
            "locus": name,
            "scheme": scheme,
            "present": True,
            "sequence": "".join(r["aa"] for r in rows),
            "length": len(rows),
            "linear_range": [rows[0]["linear_idx"], rows[-1]["linear_idx"]],
            "pdb_resi_range": [rows[0]["pdb_resi"], rows[-1]["pdb_resi"]],
            "pdb_resi_list": [r["pdb_resi"] for r in rows],
            "kabat_pos_list": [r["kabat_pos"] for r in rows],
            "imgt_pos_list": [r["imgt_pos"] for r in rows],
            "boltz_chain": boltz_chain,
            "haddock_chain": haddock_chain,
        }

    cdr_by_scheme = {
        scheme: {loc: _summarize_cdr(scheme, loc) for loc in loci_order}
        for scheme in ("kabat", "chothia", "imgt")
    }
    cdr_summary = cdr_by_scheme["kabat"]

    # Operational union: residue in locus if ANY scheme assigns it (VAM Stage-2 Ala scan)
    operational: dict[str, list[dict[str, Any]]] = {loc: [] for loc in loci_order}
    seen_op: dict[str, set[int]] = {loc: set() for loc in loci_order}
    for row in residues:
        for loc in loci_order:
            if row.get("imgt_cdr") == loc or row.get("kabat_cdr") == loc or row.get("chothia_cdr") == loc:
                if row["pdb_resi"] not in seen_op[loc]:
                    seen_op[loc].add(row["pdb_resi"])
                    operational[loc].append(row)

    cdr_operational = {}
    for loc in loci_order:
        rows = operational[loc]
        if not rows:
            cdr_operational[loc] = {"locus": loc, "scheme": "union", "present": False}
        else:
            cdr_operational[loc] = {
                "locus": loc,
                "scheme": "union",
                "present": True,
                "sequence": "".join(r["aa"] for r in rows),
                "length": len(rows),
                "linear_range": [rows[0]["linear_idx"], rows[-1]["linear_idx"]],
                "pdb_resi_range": [rows[0]["pdb_resi"], rows[-1]["pdb_resi"]],
                "pdb_resi_list": [r["pdb_resi"] for r in rows],
                "kabat_pos_list": [r["kabat_pos"] for r in rows],
                "imgt_pos_list": [r["imgt_pos"] for r in rows],
                "boltz_chain": boltz_chain,
                "haddock_chain": haddock_chain,
            }

    ala_scan = []
    for loc in loci_order:
        for row in operational[loc]:
            if row["aa"] == "A":
                continue
            ala_scan.append({
                "chain": boltz_chain,
                "haddock_chain": haddock_chain,
                "pdb_resi": row["pdb_resi"],
                "wt": row["aa"],
                "mut": "A",
                "locus": loc,
                "scheme": "union",
                "kabat_pos": row["kabat_pos"],
                "imgt_pos": row["imgt_pos"],
                "cli_mutation": f"{boltz_chain}:{row['pdb_resi']}:{row['aa']}:A",
                "stage": "2_ala_scan",
            })

    return {
        "chain_role": chain_role,
        "chain_type_anarcii": chain_type,
        "dual_map_status": status,
        "sequence": seq,
        "length": len(seq),
        "boltz_chain": boltz_chain,
        "haddock_chain": haddock_chain,
        "region_strings": regions,
        "cdr_by_scheme": cdr_by_scheme,
        "cdr_operational": cdr_operational,
        "cdr_summary": cdr_summary,
        "residues": residues,
        "ala_scan": ala_scan,
    }


def _haddock_air(vh_operational: dict[str, dict[str, Any]]) -> dict[str, Any]:
    """Default AIR template; operational CDR3 active until Ala scan reranks loops."""

    def _list(summary: dict[str, dict[str, Any]], locus: str) -> list[int]:
        s = summary.get(locus, {})
        return s.get("pdb_resi_list", []) if s.get("present") else []

    vh_cdr3 = _list(vh_operational, "vh_cdr3")
    vh_passive = _list(vh_operational, "vh_cdr1") + _list(vh_operational, "vh_cdr2")
    return {
        "note": "Default pre-Ala-scan AIR (operational CDR union). After Stage-2 Ala scan, promote highest-impact CDR loop to active.",
        "vh_active_default": vh_cdr3,
        "vh_passive_default": vh_passive,
        "vl_passive_all_cdrs": True,
        "ag_active_pdb_resi": list(range(1, 9)),
        "ag_passive_pdb_resi": list(range(9, 16)),
        "haddock_sampling_scenario_a": 200,
        "haddock_seletop_scenario_a": 100,
    }


def build_clone(clone_cfg: dict[str, Any]) -> dict[str, Any]:
    pdb_path = ROOT / clone_cfg["boltz_pdb"]
    if not pdb_path.exists():
        raise FileNotFoundError(pdb_path)

    chains = _parse_pdb_chain(pdb_path)
    for role, bid in BOLTZ.items():
        if bid not in chains:
            raise KeyError(f"Missing Boltz chain {bid} in {pdb_path}")

    vh_seq = clone_cfg.get("vh_seq_ref") or "".join(r["aa"] for r in chains[BOLTZ["vh"]])
    vl_seq = clone_cfg.get("vl_seq_ref") or "".join(r["aa"] for r in chains[BOLTZ["vl"]])
    ag_seq = "".join(r["aa"] for r in chains[BOLTZ["antigen"]])

    vh_table = _build_chain_table(
        vh_seq, chains[BOLTZ["vh"]], "VH", BOLTZ["vh"], HADDOCK["vh"]
    )
    vl_table = _build_chain_table(
        vl_seq, chains[BOLTZ["vl"]], "VL", BOLTZ["vl"], HADDOCK["vl"]
    )

    all_ala = vh_table["ala_scan"] + vl_table["ala_scan"]
    cdr_summary_all = {**vh_table["cdr_summary"], **vl_table["cdr_summary"]}
    cdr_by_scheme_all = {
        "vh": vh_table["cdr_by_scheme"],
        "vl": vl_table["cdr_by_scheme"],
    }

    return {
        "clone_id": clone_cfg["clone_id"],
        "boltz_pdb": str(pdb_path.relative_to(ROOT)).replace("\\", "/"),
        "boltz_model_rank": clone_cfg.get("boltz_model_rank"),
        "chains": {
            "boltz": BOLTZ,
            "haddock": HADDOCK,
            "ab_chains_vam": [BOLTZ["vh"], BOLTZ["vl"]],
            "ag_chains_vam": [BOLTZ["antigen"]],
        },
        "sequences": {
            "vh": vh_seq,
            "vl": vl_seq,
            "antigen": ag_seq,
        },
        "vh": vh_table,
        "vl": vl_table,
        "cdr_summary": cdr_summary_all,
        "cdr_by_scheme": cdr_by_scheme_all,
        "ala_scan": {
            "count": len(all_ala),
            "mutations": all_ala,
            "vam_stage": "2",
            "protocol_note": (
                "Run all Ala mutations with EvoEF2 (+ ThermoMPNN veto). "
                "Sum |ΔΔG| or count detrimental (ΔΔG>0) per locus; "
                "top 1-2 CDR loops proceed to Stage-3 saturation. "
                "No change to VAM V1.6 Scenario A gate order."
            ),
        },
        "haddock_air": _haddock_air(vh_table["cdr_operational"]),
        "tool_overrides_scenario_a": {
            "prodigy": "skip",
            "haddock3_sampling": 200,
        },
    }


def main(argv: list[str] | None = None) -> int:
    p = argparse.ArgumentParser(description="Build PAG-1 clone CDR numbering crosswalk")
    p.add_argument("--manifest", type=Path, default=MANIFEST)
    p.add_argument("--out-dir", type=Path, default=OUT_DIR)
    p.add_argument("--clone", action="append", help="Limit to clone id(s): 001, 008, 7M16")
    args = p.parse_args(argv)

    manifest = json.loads(args.manifest.read_text(encoding="utf-8"))
    OUT_DIR.mkdir(parents=True, exist_ok=True)

    selected = set(args.clone) if args.clone else None
    built: list[dict[str, Any]] = []

    for clone_cfg in manifest["clones"]:
        cid = clone_cfg["clone_id"]
        if selected and cid not in selected:
            continue
        print(f"[build] {cid} ...", flush=True)
        result = build_clone(clone_cfg)
        out_path = args.out_dir / f"{cid}_numbering.json"
        out_path.write_text(json.dumps(result, indent=2, ensure_ascii=False), encoding="utf-8")
        built.append(result)
        print(f"  -> {out_path.name}  ala_scan={result['ala_scan']['count']}", flush=True)

    combined = {
        "_meta": {
            **manifest["_meta"],
            "generated_at": datetime.now(timezone.utc).isoformat(),
            "clone_count": len(built),
        },
        "clones": {
            r["clone_id"]: {
                "boltz_pdb": r["boltz_pdb"],
                "cdr_operational": {
                    **r["vh"]["cdr_operational"],
                    **r["vl"]["cdr_operational"],
                },
                "ala_scan_count": r["ala_scan"]["count"],
                "numbering_json": f"projects/PAG project/numbering/{r['clone_id']}_numbering.json",
            }
            for r in built
        },
    }
    combined_path = args.out_dir / "clones_numbering_index.json"
    combined_path.write_text(json.dumps(combined, indent=2, ensure_ascii=False), encoding="utf-8")
    print(f"[done] index -> {combined_path}", flush=True)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
