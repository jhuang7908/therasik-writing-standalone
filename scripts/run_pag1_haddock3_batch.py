#!/usr/bin/env python
"""
PAG-1 HADDOCK3 batch — prepare three Boltz clones (001 / 008 / 7M16).

Reads numbering JSON + clones_manifest, splits Boltz PDB (H/L/A) into three
HADDOCK molecules (segids A/B/C), writes per-clone AIR + cfg (Scenario A:
sampling=200, seletop=100).

Usage:
  python scripts/run_pag1_haddock3_batch.py --prepare
  python scripts/run_pag1_haddock3_batch.py --prepare --clone 001
  python scripts/run_pag1_haddock3_batch.py --prepare --out-dir "projects/PAG project/haddock3_batch"
"""

from __future__ import annotations

import argparse
import json
import shutil
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

MANIFEST = ROOT / "projects/PAG project/numbering/clones_manifest.json"
NUMBERING_DIR = ROOT / "projects/PAG project/numbering"
DEFAULT_OUT = ROOT / "projects/PAG project/haddock3_batch"

BOLTZ = {"vh": "H", "vl": "L", "antigen": "A"}
HADDOCK_SEG = {"vh": "A", "vl": "B", "antigen": "C"}

SCENARIO_A_SAMPLING = 200
SCENARIO_A_SELETOP = 100
NCORES = 8

AG_ACTIVE = list(range(1, 9))
AG_PASSIVE = list(range(9, 16))


def _load_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def _cdr_pdb_list(numbering: dict[str, Any], chain_key: str, scheme: str, locus: str) -> list[int]:
    block = numbering[chain_key]["cdr_by_scheme"][scheme].get(locus, {})
    if not block.get("present"):
        return []
    return list(block["pdb_resi_list"])


def _air_resi_lists(numbering: dict[str, Any]) -> tuple[list[int], list[int], list[int], list[int]]:
    air = numbering.get("haddock_air", {})
    vh_active = list(air.get("vh_active_default") or [])
    vh_passive = list(air.get("vh_passive_default") or [])
    ag_active = list(air.get("ag_active_pdb_resi") or AG_ACTIVE)
    ag_passive = list(air.get("ag_passive_pdb_resi") or AG_PASSIVE)

    if not vh_active:
        chothia = "chothia"
        vh_active = _cdr_pdb_list(numbering, "vh", chothia, "vh_cdr3")
        if len(vh_active) < 6:
            vh_active = numbering["vh"]["cdr_operational"].get("vh_cdr3", {}).get("pdb_resi_list", [])
    if not vh_passive:
        vh_passive = (
            _cdr_pdb_list(numbering, "vh", "chothia", "vh_cdr1")
            + _cdr_pdb_list(numbering, "vh", "chothia", "vh_cdr2")
        )
    return vh_active, vh_passive, ag_active, ag_passive


def extract_chain(pdb_path: Path, src_chain: str, out_path: Path, out_chain: str = "A") -> int:
    lines: list[str] = []
    with pdb_path.open(encoding="utf-8", errors="replace") as fh:
        for line in fh:
            if not line.startswith(("ATOM", "HETATM")):
                continue
            if line[21].strip() != src_chain:
                continue
            lines.append(line[:21] + out_chain + line[22:])
    if not lines:
        raise ValueError(f"Chain {src_chain!r} not found in {pdb_path}")
    out_path.write_text("".join(lines) + "END\n", encoding="utf-8")
    return len(lines)


def generate_air_tbl(
    out_path: Path,
    vh_active: list[int],
    vh_passive: list[int],
    ag_active: list[int],
    ag_passive: list[int],
    clone_id: str,
) -> None:
    vh_seg, ag_seg = HADDOCK_SEG["vh"], HADDOCK_SEG["antigen"]
    all_ag = sorted(set(ag_active + ag_passive))
    all_vh = sorted(set(vh_active + vh_passive))
    lines = [
        f"! PAG-1 HADDOCK3 AIR — clone {clone_id}",
        f"! VH mol1 segid {vh_seg}; antigen mol3 segid {ag_seg}",
        f"! VH active CDR3: {vh_active[0]}-{vh_active[-1]} ({len(vh_active)} res)",
        "!",
    ]

    def _or_block(segid: str, resis: list[int]) -> str:
        return " or\n        ".join(f"(resid {r} and segid {segid})" for r in resis)

    ag_or = _or_block(ag_seg, all_ag)
    vh_or = _or_block(vh_seg, all_vh)

    for r in vh_active:
        lines += [
            f"assign (resid {r} and segid {vh_seg})",
            "       (",
            f"        {ag_or}",
            "       ) 2.0 2.0 0.0",
        ]

    for r in ag_active:
        lines += [
            f"assign (resid {r} and segid {ag_seg})",
            "       (",
            f"        {vh_or}",
            "       ) 2.0 2.0 0.0",
        ]

    out_path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def generate_haddock_cfg(out_path: Path, clone_id: str) -> None:
    cfg = f"""# PAG-1 HADDOCK3 — clone {clone_id} (Scenario A)
# Boltz complex → 3-molecule flexible refinement

run_dir = "./run"
mode = "local"
ncores = {NCORES}

molecules = [
    "./vh.pdb",
    "./vl.pdb",
    "./ag.pdb",
]

[topoaa]
autohis = false

[rigidbody]
ambig_fname = "./ambig_restraints.tbl"
sampling = {SCENARIO_A_SAMPLING}
mol_fix_origin_1 = false
mol_fix_origin_2 = false
mol_fix_origin_3 = false

[seletop]
select = {SCENARIO_A_SELETOP}

[flexref]
ambig_fname = "./ambig_restraints.tbl"
tolerance = 20

[emref]
ambig_fname = "./ambig_restraints.tbl"

[clustfcc]
clust_cutoff = 0.6
min_population = 2

[caprieval]
"""
    out_path.write_text(cfg, encoding="utf-8", newline="\n")


def prepare_clone(clone_cfg: dict[str, Any], out_root: Path) -> dict[str, Any]:
    clone_id = clone_cfg["clone_id"]
    numbering_path = NUMBERING_DIR / f"{clone_id}_numbering.json"
    if not numbering_path.exists():
        raise FileNotFoundError(
            f"Missing {numbering_path.name}. Run: "
            "conda run -n anarcii python scripts/build_pag1_clone_numbering.py"
        )

    numbering = _load_json(numbering_path)
    boltz_pdb = ROOT / clone_cfg["boltz_pdb"]
    if not boltz_pdb.exists():
        raise FileNotFoundError(boltz_pdb)

    work = out_root / clone_id
    work.mkdir(parents=True, exist_ok=True)
    for old in work.glob("*"):
        if old.is_file():
            old.unlink()

    extract_chain(boltz_pdb, BOLTZ["vh"], work / "vh.pdb", HADDOCK_SEG["vh"])
    extract_chain(boltz_pdb, BOLTZ["vl"], work / "vl.pdb", HADDOCK_SEG["vl"])
    extract_chain(boltz_pdb, BOLTZ["antigen"], work / "ag.pdb", HADDOCK_SEG["antigen"])

    vh_act, vh_pass, ag_act, ag_pass = _air_resi_lists(numbering)
    if not vh_act:
        raise RuntimeError(f"{clone_id}: empty VH CDR3 active list")

    generate_air_tbl(work / "ambig_restraints.tbl", vh_act, vh_pass, ag_act, ag_pass, clone_id)
    generate_haddock_cfg(work / "haddock3.cfg", clone_id)

    meta = {
        "clone_id": clone_id,
        "boltz_pdb": str(boltz_pdb.relative_to(ROOT)).replace("\\", "/"),
        "prepared_at": datetime.now(timezone.utc).isoformat(),
        "vam_scenario": "A",
        "haddock_sampling": SCENARIO_A_SAMPLING,
        "haddock_seletop": SCENARIO_A_SELETOP,
        "ncores": NCORES,
        "air": {
            "vh_active_cdr3_pdb": vh_act,
            "vh_passive_cdr12_pdb": vh_pass,
            "ag_active_pdb": ag_act,
            "ag_passive_pdb": ag_pass,
        },
        "molecules": ["vh.pdb", "vl.pdb", "ag.pdb"],
        "haddock_segid": HADDOCK_SEG,
    }
    (work / "metadata.json").write_text(json.dumps(meta, indent=2), encoding="utf-8")
    print(f"  [{clone_id}] prepared -> {work}")
    print(f"    VH CDR3 active: {vh_act[0]}-{vh_act[-1]} ({len(vh_act)} res)")
    return meta


def prepare_all(out_dir: Path, clone_filter: list[str] | None) -> dict[str, Any]:
    manifest = _load_json(MANIFEST)
    out_dir.mkdir(parents=True, exist_ok=True)
    selected = set(clone_filter) if clone_filter else None
    metas: dict[str, Any] = {}

    for clone_cfg in manifest["clones"]:
        cid = clone_cfg["clone_id"]
        if selected and cid not in selected:
            continue
        metas[cid] = prepare_clone(clone_cfg, out_dir)

    index = {
        "_meta": {
            "prepared_at": datetime.now(timezone.utc).isoformat(),
            "out_dir": str(out_dir.relative_to(ROOT)).replace("\\", "/"),
            "vps_remote": "/srv/projects/pag1_haddock3",
            "clone_count": len(metas),
        },
        "clones": metas,
    }
    (out_dir / "batch_index.json").write_text(json.dumps(index, indent=2), encoding="utf-8")
    print(f"[done] batch_index.json ({len(metas)} clones)")
    return index


def build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(description="Prepare PAG-1 HADDOCK3 batch inputs")
    p.add_argument("--prepare", action="store_true", help="Generate inputs under --out-dir")
    p.add_argument("--out-dir", type=Path, default=DEFAULT_OUT)
    p.add_argument("--clone", action="append", help="Limit to clone id(s): 001, 008, 7M16")
    return p


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    if not args.prepare:
        build_parser().print_help()
        return 1
    prepare_all(args.out_dir, args.clone)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
