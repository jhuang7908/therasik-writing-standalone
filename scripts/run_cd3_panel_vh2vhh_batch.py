#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Run full VH→VHH (Path C1/C2) for each raw anti-CD3ε binder in the CD3 reference panel.

- One job per distinct *input VH sequence* (6 rows: SP34, Teplizumab, Visilizumab,
  Otelixizumab, Foralumab, OKT3-class scFv VH).
- Captures original molecular format and a conservative mechanism *program framing*
  (regulatory vs activation / TCE context); all such polarity labels are [inferred]
  from public drug/class narratives — not assay-derived agonism scores.

Outputs:
  data/reference/cd3_vh_to_vhh_batch_manifest_v1.json

Per-job artifacts remain under .job_storage/{job_id}/ (result.json, sequences.fasta, …).

Usage:
  conda run -n anarcii python scripts/run_cd3_panel_vh2vhh_batch.py
"""

from __future__ import annotations

import argparse
import hashlib
import json
import re
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

ROOT = Path(__file__).resolve().parents[1]

# Frozen clinical/program framing — polarity is NOT an in silico prediction.
# verification_status is always treated as inferred for client-facing honesty.
CD3_BINDER_CONTEXT: Dict[str, Dict[str, Any]] = {
    "sp34_murine_vh_blinatumomab": {
        "functional_polarity": "t_cell_engager_arm_cytolytic_context",
        "note": (
            "Murine SP34-class binder used as the CD3 arm in blinatumomab (BiTE); "
            "cytolytic outcome is context- and format-dependent (co-target, avidity, dose). "
            "[inferred from public modality class]"
        ),
    },
    "teplizumab_vh_vl": {
        "functional_polarity": "immunomodulatory_regulatory_leaning",
        "note": (
            "Anti-CD3 mAb developed for T1D with immunomodulatory / partial agonist framing in program narratives. "
            "[inferred from public indication/clinical class]"
        ),
    },
    "visilizumab_vh_vl": {
        "functional_polarity": "mixed_context_dependent",
        "note": (
            "Humanized CD3 mAb with historical apoptosis / immune-suppression use cases; "
            "not equivalent to a TCE arm nor a single clean agonist label. "
            "[inferred]"
        ),
    },
    "otelixizumab_vh_vl": {
        "functional_polarity": "immunomodulatory_regulatory_leaning",
        "note": (
            "Humanized CD3 mAb evaluated in MS with modulation-oriented program framing. "
            "[inferred]"
        ),
    },
    "foralumab_vh_vl": {
        "functional_polarity": "tolerance_oral_anti_CD3_regulatory_leaning",
        "note": (
            "Fully human anti-CD3 (NI-0401 / foralumab) with tolerance / regulatory-style positioning in public materials. "
            "[inferred]"
        ),
    },
    "okt3_humanized_scfv_actes": {
        "functional_polarity": "strong_pan_T_cell_CD3_engagement_risk",
        "note": (
            "OKT3-class CD3 binders are associated with broad T cell activation and CRS risk as intact mAbs; "
            "scFv fragment removes Fc but retains epitope/affinity context. "
            "[inferred from class history]"
        ),
    },
}


def _fmt_label(inp: str) -> str:
    if inp == "VH":
        return "VH_only"
    if inp == "VH_VL":
        return "IgG_VH_VL_pair"
    if inp == "scFv":
        return "scFv_VH_linker_VL"
    return inp


def _genetics_to_source_class(genetics: str) -> str:
    return {
        "humanized": "humanized_mab",
        "fully_human": "human_mab",
        "murine": "murine_mab",
    }.get(genetics, "human_mab")


def _safe_job_id(entry_id: str) -> str:
    s = re.sub(r"[^a-zA-Z0-9._-]+", "_", entry_id).strip("_")
    return f"cd3_v2v_{s}"[:80]


def _slim_from_payload(payload: Optional[Dict[str, Any]]) -> Dict[str, Any]:
    if not payload:
        return {}
    return {
        "converted_sequence": payload.get("converted_sequence")
        or payload.get("best_converted_sequence"),
        "input_vh_used": payload.get("input_sequence"),
        "verdict_severity": payload.get("verdict_severity"),
        "primary_recommendation": payload.get("primary_recommendation"),
        "expressibility_verdict": payload.get("expressibility_verdict"),
        "cdr3_length": payload.get("cdr3_length"),
        "feasibility_verdict": payload.get("feasibility_verdict"),
        "cmc_status": payload.get("cmc_status"),
        "mutations_applied": payload.get("mutations_applied", []),
    }


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument(
        "--out-json",
        type=Path,
        default=ROOT / "data" / "reference" / "cd3_vh_to_vhh_batch_manifest_v1.json",
    )
    args = ap.parse_args()

    sys.path.insert(0, str(ROOT))

    from scripts.build_cd3_engineered_vh_panel import (  # noqa: PLC0415
        RawBinder,
        _collect_raw,
        _kabat_cdr3_vh,
    )

    try:
        from anarcii import Anarcii  # noqa: PLC0415

        _an = Anarcii(seq_type="antibody", mode="accuracy")
    except Exception:
        _an = None

    try:
        from api.job_store import job_dir, jobs  # noqa: PLC0415
        from api.routers.vh_to_vhh import VhToVhhRequest, _vh2vhh_impl  # noqa: PLC0415
    except ImportError as e:
        print("Import error (run from repo root; use conda env with deps):", e)
        return 1

    raw: List[RawBinder] = _collect_raw()
    manifest: Dict[str, Any] = {
        "batch_id": "cd3_vh_to_vhh_batch_manifest_v1",
        "batch_version": "1.0.0",
        "target_antigen": "human CD3E (CD3ε)",
        "generated_at_utc": datetime.now(timezone.utc).isoformat(),
        "n_entries": len(raw),
        "polarity_label_policy": (
            "Functional polarity strings are program/class narratives marked verification_status=inferred; "
            "they are not agonist/treg assay readouts."
        ),
        "entries": [],
    }

    def _flush() -> None:
        manifest["generated_at_utc"] = datetime.now(timezone.utc).isoformat()
        manifest["n_completed"] = sum(
            1 for e in manifest["entries"] if e.get("job_status") == "done"
        )
        args.out_json.write_text(
            json.dumps(manifest, indent=2, ensure_ascii=False), encoding="utf-8"
        )

    for row in raw:
        ctx = CD3_BINDER_CONTEXT.get(row.entry_id, {})
        cdr3, cdr_meth = _kabat_cdr3_vh(row.vh_aa, _an)
        job_id = _safe_job_id(row.entry_id)
        seq_name = f"CD3_batch_{row.entry_id}"

        jobs[job_id] = {
            "id": job_id,
            "status": "running",
            "progress": 0,
            "progress_note": "CD3 panel VH→VHH batch",
            "result": None,
        }

        req = VhToVhhRequest(
            vh_sequence=row.vh_aa,
            source_class=_genetics_to_source_class(row.genetics),
            sequence_name=seq_name,
        )

        entry_out: Dict[str, Any] = {
            "entry_id": row.entry_id,
            "display_name": row.display_name,
            "original_antibody_format": _fmt_label(row.input_format),
            "genetics_class": row.genetics,
            "has_reconstructed_scfv_in_panel": bool(row.scfv_aa),
            "cdr3_kabat": cdr3,
            "cdr3_annotation_method": cdr_meth,
            "vh_aa_sha256": hashlib.sha256(row.vh_aa.encode()).hexdigest(),
            "cd3_program_framing": {
                "functional_polarity": ctx.get("functional_polarity", "unknown"),
                "note": ctx.get("note", ""),
                "verification_status": "inferred",
            },
            "vh_to_vhh_job_id": job_id,
            "source_class_request": req.source_class,
            "output_dir_relative": str(job_dir(job_id).relative_to(ROOT)).replace("\\", "/"),
        }

        try:
            _vh2vhh_impl(job_id, req)
            st = jobs.get(job_id, {})
            entry_out["job_status"] = st.get("status")
            entry_out["elapsed_sec"] = st.get("elapsed_sec")
            payload = st.get("result")
            entry_out["result_slim"] = _slim_from_payload(payload if isinstance(payload, dict) else None)
            if st.get("status") == "failed":
                entry_out["error"] = st.get("error")
        except Exception as ex:  # noqa: BLE001
            entry_out["job_status"] = "failed"
            entry_out["error"] = f"{type(ex).__name__}: {ex}"

        manifest["entries"].append(entry_out)
        args.out_json.parent.mkdir(parents=True, exist_ok=True)
        _flush()

    print(f"Wrote {args.out_json}")
    ok = sum(1 for e in manifest["entries"] if e.get("job_status") == "done")
    print(f"Completed {ok}/{len(manifest['entries'])} jobs OK.")
    return 0 if ok == len(manifest["entries"]) else 2


if __name__ == "__main__":
    raise SystemExit(main())
