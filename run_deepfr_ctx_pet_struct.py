"""
Structure-guided DeepFR-CTX-Pet v2.8 for Tanezumab caninization (V3c + V4b).

Phases: graft → structure gate → pet 9-mer CTX → Pet-native Guard → CMC micro-tune → validation.
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

SUITE = Path(__file__).resolve().parent
sys.path.insert(0, str(SUITE))

from core.evaluation import AbEvaluator, AntibodyType
from core.humanization.deepfr_ctx_pet import (
    DOG_FR4,
    DISPLAY_NAME,
    PROTOCOL_VERSION,
    apply_cmc_micro_tune,
    run_deepfr_ctx_pet_chain,
    validate_conserved_cys,
)
from core.humanization.structure_protection import compute_structure_protection

DEFAULT_PDB = (
    SUITE
    / ".agent/Dog_NGF_Ab_V2/boltz_results_Dog_NGF_Ab_V2/predictions/Dog_NGF_Ab_V2/Dog_NGF_Ab_V2_model_0.pdb"
)

TANEZUMAB_VH = (
    "QVQLQESGPGLVRPSQTLSLTCTVSGFSLIGYDLNWVRQPPGRGLEWIGIIWGDGTTDYNSAVKSRVTMLKDTSKNQFSLRLSSVTAADTAVYYCARGGYWYATSYYFDYWGQGTLVTVSS"
)
TANEZUMAB_VL = (
    "DIQMTQSPSSLSASVGDRVTITCRASQSISNNLNWYQQKPGKAPKLLIYYTSRFHSGVPSRFSGSGSGTDFTFTISSLQPEDIATYYCQQEHTLPYTFGQGTKLEIK"
)

SCAFFOLDS = {
    "V3c": {
        "vh": "EVQLVESGGDLVKPGGSLRLSCVASGFTFSSYGMHWVRQAPGKGLQWVAVISYDGSNKYYADAVKGRFTISKDSAKNTLYLQMNSLRAEDTAVYYCAR",
        "vl": "EIVLTQSPASLSLSQEEKVTITCRASQSIGSSLNWYQQKPGQAPKLLIYYATSRLHSGVPSRFSGSGSGTDFSFTISSLEPEDVAVYYCQQGYS",
        "vl_fr4": "VL_KAPPA",
        "vh_anchors": {},
        "germline_vh": "IGHV3-9",
        "germline_vl": "IGKV3-18",
    },
    "V4b": {
        "vh": "EVQLVESGGDLVKPGGSLRLSCVASGFTFSSYGMHWVRQAPGKGLQWVAVISYDGSNKYYADSVKGRFTISRDNAKNTVYLQMNSLRAEDTAMYYCAK",
        "vl": "QSVLTQPTSVSGSLGQRVTISCSGSSSNIGNNAVSWYQQLPGKAPKLLVYYDDDLRPSGVPDRFSGSKSGTSASLTITGLQAEDEADYYC",
        "vl_fr4": "VL_LAMBDA",
        "vh_anchors": {71: "K", 78: "F"},
        "germline_vh": "IGHV3-19",
        "germline_vl": "IGLV1-141",
    },
}


def _design_variant(
    name: str,
    pdb_path: Path,
    use_structure: bool,
    skip_guard: bool,
    skip_cmc_tune: bool,
) -> dict:
    cfg = SCAFFOLDS[name]
    struct_reports = {}

    if use_structure:
        vh_prot = compute_structure_protection(
            pdb_path, "H", "VH", antigen_chain_ids=("A",), fv_partner_chain_id="L"
        )
        vl_prot = compute_structure_protection(
            pdb_path, "L", "VL", antigen_chain_ids=("A",), fv_partner_chain_id="H"
        )
        struct_reports = {"VH": vh_prot, "VL": vl_prot}
        vh_lock, vh_elig = vh_prot["locked_kabat"], vh_prot["ctx_eligible_kabat"]
        vl_lock, vl_elig = vl_prot["locked_kabat"], vl_prot["ctx_eligible_kabat"]
    else:
        vh_lock = vl_lock = vh_elig = vl_elig = None

    vh_fr4 = DOG_FR4["VH"]
    vl_fr4 = DOG_FR4[cfg["vl_fr4"]]

    vh, vh_pipe = run_deepfr_ctx_pet_chain(
        TANEZUMAB_VH,
        cfg["vh"],
        "VH",
        vh_fr4,
        species="dog",
        germline=cfg["germline_vh"],
        anchors=cfg["vh_anchors"],
        struct_lock_kabat=vh_lock,
        struct_eligible_kabat=vh_elig,
        apply_pet_guard=not skip_guard,
    )
    vl, vl_pipe = run_deepfr_ctx_pet_chain(
        TANEZUMAB_VL,
        cfg["vl"],
        "VL",
        vl_fr4,
        species="dog",
        germline=cfg["germline_vl"],
        anchors={},
        struct_lock_kabat=vl_lock,
        struct_eligible_kabat=vl_elig,
        apply_pet_guard=not skip_guard,
    )

    cmc_tune_meta = {"skipped": True}
    if not skip_cmc_tune:
        vh, vl, cmc_changes, cmc_tune_meta = apply_cmc_micro_tune(
            vh,
            vl,
            pdb_path=pdb_path if use_structure else None,
            vh_anchors=cfg["vh_anchors"],
            vh_lock=vh_lock,
            vl_lock=vl_lock,
            vh_eligible=vh_elig,
            vl_eligible=vl_elig,
            max_mutations=3,
        )
        cmc_tune_meta["changes"] = cmc_changes

    for chain, seq in [("VH", vh), ("VL", vl)]:
        errs = validate_conserved_cys(seq, chain)
        if errs:
            raise RuntimeError(f"{name} {chain}: {'; '.join(errs)}")

    ev = AbEvaluator(
        project_name=f"{name}_struct" if use_structure else name,
        vh_seq=vh,
        vl_seq=vl,
        ab_type=AntibodyType.DOG,
        germline_species="Canis_lupus_familiaris",
        strict_qa=False,
    )
    cmc = ev.run(modules=["developability", "cdr_scan", "cmc_advisor"])

    return {
        "variant": name,
        "protocol_version": PROTOCOL_VERSION,
        "algorithm_id": DISPLAY_NAME,
        "structure_guided": use_structure,
        "pdb": str(pdb_path) if use_structure else None,
        "vh": vh,
        "vl": vl,
        "vh_pipeline": vh_pipe,
        "vl_pipeline": vl_pipe,
        "cmc_tune": cmc_tune_meta,
        "structure_protection": {
            k: {
                "summary": v.get("summary"),
                "locked_kabat": sorted(v.get("locked_kabat", set())),
                "ctx_eligible_kabat": sorted(v.get("ctx_eligible_kabat", set())),
                "reasons": v.get("reasons"),
            }
            for k, v in struct_reports.items()
        },
        "cmc": {
            "pI": cmc.results["developability"]["pI_fab_estimate"],
            "instability": cmc.results["developability"]["instability_index"],
            "status": cmc.overall_status,
            "advisor_status": cmc.results.get("cmc_advisor", {}).get("status"),
        },
    }


def main() -> None:
    ap = argparse.ArgumentParser(description="DeepFR-CTX-Pet v2.8 with structure + guard + CMC tune")
    ap.add_argument("--pdb", type=Path, default=DEFAULT_PDB, help="Tanezumab–dog NGF complex PDB")
    ap.add_argument("--variant", choices=["V3c", "V4b", "both"], default="both")
    ap.add_argument("--no-structure", action="store_true", help="Sequence-only mode (no PDB locks)")
    ap.add_argument("--skip-guard", action="store_true", help="Skip Pet-native Guard (P4)")
    ap.add_argument("--skip-cmc-tune", action="store_true", help="Skip CMC micro-tune phase")
    ap.add_argument("--out-dir", type=Path, default=SUITE)
    args = ap.parse_args()

    use_structure = not args.no_structure
    if use_structure and not args.pdb.exists():
        raise SystemExit(f"PDB not found: {args.pdb}")

    variants = ["V3c", "V4b"] if args.variant == "both" else [args.variant]
    results = {}
    for v in variants:
        print(f"\n=== {DISPLAY_NAME} v{PROTOCOL_VERSION} — {v} (structure={use_structure}) ===")
        res = _design_variant(v, args.pdb, use_structure, args.skip_guard, args.skip_cmc_tune)
        out_name = f"{v.lower()}_design_results.json"
        out_path = args.out_dir / out_name
        with open(out_path, "w", encoding="utf-8") as f:
            json.dump(res, f, indent=2)
        print(f"Saved {out_path}")

        vh_ctx = len(res["vh_pipeline"]["ctx_voting"].get("changes", []))
        vl_ctx = len(res["vl_pipeline"]["ctx_voting"].get("changes", []))
        vh_rb = len(res["vh_pipeline"].get("pet_native_guard", {}).get("rollbacks", []))
        vl_rb = len(res["vl_pipeline"].get("pet_native_guard", {}).get("rollbacks", []))
        cmc_n = res["cmc_tune"].get("n_applied", 0)
        print(f"  9-mer subs: VH={vh_ctx}, VL={vl_ctx}")
        print(f"  Pet-native Guard rollbacks: VH={vh_rb}, VL={vl_rb}")
        print(f"  CMC tune mutations: {cmc_n}")
        if use_structure:
            sp = res["structure_protection"]
            print(f"  VH locked/eligible: {len(sp['VH']['locked_kabat'])}/{len(sp['VH']['ctx_eligible_kabat'])}")
            print(f"  VL locked/eligible: {len(sp['VL']['locked_kabat'])}/{len(sp['VL']['ctx_eligible_kabat'])}")
        print(f"  CMC: {res['cmc']['status']}, pI={res['cmc']['pI']}")
        results[v] = res

    summary_path = args.out_dir / "deepfr_ctx_struct_summary.json"
    with open(summary_path, "w", encoding="utf-8") as f:
        json.dump({
            "protocol_version": PROTOCOL_VERSION,
            "pdb": str(args.pdb),
            "variants": results,
        }, f, indent=2)
    print(f"\nSummary → {summary_path}")


if __name__ == "__main__":
    main()
