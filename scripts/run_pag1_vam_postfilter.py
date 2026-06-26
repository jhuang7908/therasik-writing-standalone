#!/usr/bin/env python
"""
PAG-1 VAM Stage-4 sequential post-filter (V1.6.1, MM/GBSA deferred).

Reads Stage-3 ``stage3_recommended.json`` per clone and applies gates in order:
  1. CHECK 6  — CDR design-prior fingerprint (AbRef-458)
  2. Stage 2.5 — structural integrity veto (geometry + antigen contact)
  3. CHECK 7  — sequence-level CMC liability (CDR motifs / hydrophobic run)
  4. ThermoMPNN — stability veto (ΔΔG > +0.5 kcal/mol)
  5. AntiFold — CDR inverse-folding veto (ΔΔG proxy > +0.5)
  6. CMC + AbLang2 — Fv developability vs AbRef-458 + paired pseudo-LL delta (HPR skipped)
  7. CHECK 8  — OpenMM relax + vdW clash (skipped with --skip-check8)

Usage (repo root, conda env affmat):
  conda run -n affmat python scripts/run_pag1_vam_postfilter.py
  conda run -n affmat python scripts/run_pag1_vam_postfilter.py --clone 001 --resume
  conda run -n affmat python scripts/run_pag1_vam_postfilter.py --skip-check8
  conda run -n affmat python scripts/run_pag1_vam_postfilter.py --limit 5 --dry-run
"""

from __future__ import annotations

import argparse
import csv
import dataclasses
import gzip
import json
import sys
import time
from datetime import datetime, timezone
from pathlib import Path
from types import SimpleNamespace
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from core.cmc.cmc_metrics import CMCMetricEngine  # noqa: E402
from core.evaluation.clinical_rule_engine import get_engine  # noqa: E402
from core.structure.affinity_energy_toolkit import (  # noqa: E402
    AffinityEnergyToolkit,
    _evoef2_build,
)
from core.structure.cdr_fingerprint_prior import design_prior_audit, load_fingerprint  # noqa: E402
from core.structure.structural_integrity_veto import run_stage2_5  # noqa: E402
from scripts.affinity_energy_cli import (  # noqa: E402
    EVOEF2_DEFAULT,
    THERMOMPNN_DEFAULT,
    _parse_pdb_sequences,
)

HADDOCK_RESULTS = ROOT / "projects/PAG project/haddock3_results"
NUMBERING_DIR = ROOT / "projects/PAG project/numbering"
VAM_DIR = ROOT / "projects/PAG project/vam_ala_scan"

AB_CHAINS = ["A", "B"]
AG_CHAINS = ["C"]
CLONES = ["001", "008", "7M16"]

RANK1: dict[str, dict[str, str]] = {
    "001": {"emref": "emref_31.pdb"},
    "008": {"emref": "emref_4.pdb"},
    "7M16": {"emref": "emref_7.pdb"},
}

THERMO_VETO = 0.5
ANTIFOLD_VETO = 0.5
ABLANG_VETO_DELTA = -0.5  # pseudo-LL drop vs WT
MIN_FREQ = 0.005
_ABLANG2_MODEL_CACHE: dict[str, Any] = {}
PROTOCOL_VERSION = "VAM V1.6.1"
STAGE = "4_sequential_postfilter"


def _utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()


def _rank1_pdb(clone_id: str) -> Path:
    info = RANK1[clone_id]
    pdb = HADDOCK_RESULTS / clone_id / "run" / "4_emref" / info["emref"]
    if not pdb.is_file():
        gz = Path(str(pdb) + ".gz")
        if gz.is_file():
            pdb.parent.mkdir(parents=True, exist_ok=True)
            with gzip.open(gz, "rb") as fin, open(pdb, "wb") as fout:
                fout.write(fin.read())
        else:
            raise FileNotFoundError(f"Missing rank-1 PDB for {clone_id}: {pdb}")
    return pdb


def _load_numbering(clone_id: str) -> dict[str, Any]:
    return json.loads((NUMBERING_DIR / f"{clone_id}_numbering.json").read_text(encoding="utf-8"))


def _mut_key(row: dict[str, Any]) -> str:
    return row.get("mutation") or f"{row['chain']}:{row['pdb_resi']}:{row['wt']}:{row['mut']}"


def _to_gate_mut(row: dict[str, Any]) -> dict[str, Any]:
    return {
        "chain": row["chain"],
        "resi": int(row["pdb_resi"]),
        "wt": row["wt"],
        "mut": row["mut"],
    }


def _out_paths(clone_id: str) -> dict[str, Path]:
    base = VAM_DIR / clone_id / "stage4_postfilter"
    base.mkdir(parents=True, exist_ok=True)
    return {
        "dir": base,
        "json": base / "stage4_vam_gated.json",
        "csv": base / "stage4_vam_gated.csv",
        "shortlist": base / "stage4_shortlist.json",
        "checkpoint": base / "checkpoint.json",
    }


def _load_recommended(clone_id: str) -> list[dict[str, Any]]:
    path = VAM_DIR / clone_id / "stage3_saturation" / "stage3_recommended.json"
    if not path.is_file():
        raise FileNotFoundError(f"Missing Stage-3 recommended list: {path}")
    data = json.loads(path.read_text(encoding="utf-8"))
    return list(data.get("mutations") or [])


def _gate_verdict(gates: dict[str, Any]) -> str:
    if any(g.get("verdict") == "VETO" for g in gates.values()):
        return "FAIL"
    if any(g.get("verdict") == "WARN" for g in gates.values()):
        return "WARN"
    if any(g.get("verdict") in ("NOT_RUN", "ERROR") for g in gates.values()):
        return "INCOMPLETE"
    return "PASS"


def _locus_context(
    numbering: dict[str, Any],
    row: dict[str, Any],
    chain_records: dict[str, list[dict]] | None = None,
) -> dict[str, Any] | None:
    """Map Stage-3 row to CHECK 7 context using authoritative PDB coordinates.

    Coordinate fix: the true linear index of the mutated residue is resolved from
    the parsed PDB ``chain_records`` (resi -> ordinal index), which is the exact
    sequence/numbering EvoEF2 and the liability filter operate on. The previous
    implementations anchored on Stage-3 ``position_index`` (wrong origin) or on the
    operational CDR ``pdb_resi_list`` (Chothia numbering); both diverge from the
    Boltz PDB author numbering for the light chain and produced spurious
    ``apply_mutation_error`` VETOs. ``numbering["sequences"][prefix]`` is verified
    to equal the chain_records sequence, so the CDR ``linear_range`` stays valid.
    """
    locus = row.get("locus")
    if not locus:
        return None
    prefix = locus.split("_", 1)[0]
    table = numbering.get(prefix, {})
    op = (table.get("cdr_operational") or {}).get(locus)
    if not op or not op.get("present"):
        return None
    full_seq = numbering["sequences"][prefix]
    lr = op["linear_range"]
    cdr_start = int(lr[0])
    cdr_end = int(lr[1]) + 1
    wt = row.get("wt")

    lin_idx: int | None = None
    chain = row.get("chain")
    if chain_records is not None and chain in chain_records:
        try:
            resi = int(row["pdb_resi"])
            lin_idx = next(
                i for i, r in enumerate(chain_records[chain]) if r["resi"] == resi
            )
        except (StopIteration, KeyError, TypeError, ValueError):
            lin_idx = None
    if lin_idx is None:
        # Fallback: operational CDR offset (valid when PDB numbering == Chothia).
        resi_list = op.get("pdb_resi_list") or []
        try:
            lin_idx = cdr_start + resi_list.index(int(row["pdb_resi"]))
        except (ValueError, TypeError, KeyError):
            lin_idx = None
    if lin_idx is None or not (
        0 <= lin_idx < len(full_seq) and (not wt or full_seq[lin_idx] == wt)
    ):
        # Mapping could not be validated against WT — signal coord error so the
        # caller reports NOT_RUN instead of letting CHECK 7 mis-VETO.
        return {"locus": locus, "coord_error": True, "lin_idx": lin_idx, "wt": wt}
    return {
        "locus": locus,
        "position_index": lin_idx - cdr_start,
        "chain_sequence": full_seq,
        "cdr_start": cdr_start,
        "cdr_end": cdr_end,
    }


# IMGT-segmented CDR boundaries (the fingerprint aa_freq_by_position is built per
# these segments). index into fingerprint = imgt_pos - cdr_start.
_IMGT_CDR_BOUNDS = {
    "cdr1": (27, 38),
    "cdr2": (56, 65),
    "cdr3": (105, 117),
}


def _imgt_cdr_index(numbering: dict[str, Any], row: dict[str, Any]) -> dict[str, Any]:
    """Map a mutation to the IMGT-segmented CDR index used by the fingerprint.

    Returns {"index": int} when the residue lies inside the IMGT CDR, otherwise
    {"outside": reason}. The operational-union sequence index must NOT be used
    here — it over-extends into the framework flank and is offset from the
    IMGT-segmented fingerprint array.
    """
    locus = row.get("locus") or ""
    prefix = locus.split("_", 1)[0]
    cdr_tag = locus.split("_", 1)[1] if "_" in locus else ""
    bounds = _IMGT_CDR_BOUNDS.get(cdr_tag)
    if bounds is None:
        return {"outside": f"unknown_cdr_tag:{cdr_tag}"}
    op = (numbering.get(prefix, {}).get("cdr_operational") or {}).get(locus)
    if not op:
        return {"outside": "locus_unmapped"}
    resi_list = op.get("pdb_resi_list") or []
    imgt_list = op.get("imgt_pos_list") or []
    if len(resi_list) != len(imgt_list):
        return {"outside": "resi_imgt_length_mismatch"}
    try:
        i = resi_list.index(int(row["pdb_resi"]))
    except (ValueError, KeyError, TypeError):
        return {"outside": "pdb_resi_not_in_operational_block"}
    imgt_raw = str(imgt_list[i])
    imgt_int = int("".join(ch for ch in imgt_raw if ch.isdigit()) or "-1")
    lo, hi = bounds
    if not (lo <= imgt_int <= hi):
        return {"outside": f"imgt_{imgt_raw}_outside_cdr_{lo}_{hi}"}
    return {"index": imgt_int - lo, "imgt_pos": imgt_raw}


def _run_check6(row: dict[str, Any], fp, numbering: dict[str, Any]) -> dict[str, Any]:
    locus = row.get("locus")
    if not locus:
        return {"verdict": "NOT_RUN", "reason": "locus_unmapped"}
    mapped = _imgt_cdr_index(numbering, row)
    if "index" not in mapped:
        # Position is outside the IMGT-segmented CDR (framework flank of the
        # union, or unmapped). The CDR fingerprint cannot vouch for it.
        return {
            "verdict": "NOT_RUN",
            "rule": "position_outside_imgt_cdr",
            "reason": mapped.get("outside"),
            "locus": locus,
            "proposed_aa": row["mut"],
        }
    audit = design_prior_audit(
        fp,
        locus=locus,
        position_index=mapped["index"],
        proposed_aa=row["mut"],
        min_freq=MIN_FREQ,
    )
    # design_prior_audit returns PASS-by-absence when the IMGT index is in-bounds
    # but the fingerprint has no observation column there; demote to NOT_RUN so
    # the verdict is not silently inflated.
    if audit.get("rule") == "no_natural_observation_at_this_position":
        return {"verdict": "NOT_RUN", "imgt_index": mapped["index"], **audit}
    verdict = audit.get("verdict", "NOT_RUN")
    audit["imgt_index"] = mapped["index"]
    audit["imgt_pos"] = mapped.get("imgt_pos")
    return {"verdict": verdict, **audit}


def _build_stage25_maps(
    stage25_result,
) -> tuple[set[str], dict[str, dict[str, Any]]]:
    """Return pass keys and per-key stage25 audit snippets."""
    pass_keys: set[str] = set()
    audit_by_key: dict[str, dict[str, Any]] = {}

    def _key_from_mut(m: dict) -> str:
        return f"{m['chain']}:{m['resi']}:{m['wt']}:{m['mut']}"

    for cand in stage25_result.passed:
        if isinstance(cand, dict):
            muts = [cand]
        else:
            muts = list(cand)
        for m in muts:
            pass_keys.add(_key_from_mut(m))

    for rc in stage25_result.rescued or []:
        for m in rc.get("original_mutations") or []:
            k = _key_from_mut(m)
            pass_keys.add(k)
            audit_by_key[k] = {
                "verdict": "RESCUED",
                "rescue_type": rc.get("rescue_type"),
                "affinity_ddg": rc.get("affinity_ddg"),
            }

    for vr in stage25_result.vetoed:
        m = vr.mutation if isinstance(vr.mutation, dict) else vr.mutation[0]
        k = _key_from_mut(m)
        audit_by_key[k] = {
            "verdict": "VETO",
            "veto_type": vr.veto_type,
            "reason": vr.reason,
        }

    for wr in stage25_result.warned:
        m = wr.mutation if isinstance(wr.mutation, dict) else wr.mutation[0]
        k = _key_from_mut(m)
        if k not in audit_by_key:
            audit_by_key[k] = {"verdict": "WARN", "veto_type": wr.veto_type, "reason": wr.reason}

    return pass_keys, audit_by_key


def _run_check7(
    row: dict[str, Any],
    numbering: dict[str, Any],
    chain_records: dict[str, list[dict]] | None = None,
) -> dict[str, Any]:
    from core.cmc.sequence_liability_filter import filter_candidates

    mut = _to_gate_mut(row)
    ctx = _locus_context(numbering, row, chain_records)
    if ctx is None:
        return {"verdict": "NOT_RUN", "reason": "locus_unmapped"}
    if ctx.get("coord_error"):
        return {
            "verdict": "NOT_RUN",
            "reason": "coord_error",
            "lin_idx": ctx.get("lin_idx"),
            "wt": ctx.get("wt"),
        }
    seq_cand = dict(mut)
    seq_cand["index_in_cdr"] = ctx["position_index"]
    res = filter_candidates(
        wt_full_seq=ctx["chain_sequence"],
        candidates=[seq_cand],
        locus=ctx["locus"],
        cdr_start=ctx["cdr_start"],
        cdr_end=ctx["cdr_end"],
        antibody_format="vh_vl",
        keep_warnings=True,
    )
    if res.vetoed:
        item = res.vetoed[0]
        return {
            "verdict": "VETO",
            "findings": [dataclasses.asdict(f) for f in item.findings],
        }
    if res.warned:
        item = res.warned[0]
        return {
            "verdict": "WARN",
            "findings": [dataclasses.asdict(f) for f in item.findings],
        }
    return {"verdict": "PASS", "findings": []}


def _mutate_fv_sequences(
    chain_records: dict[str, list[dict]],
    row: dict[str, Any],
) -> tuple[str, str]:
    vh = "".join(r["aa"] for r in chain_records[AB_CHAINS[0]])
    vl = "".join(r["aa"] for r in chain_records[AB_CHAINS[1]])
    mut = _to_gate_mut(row)
    chain = mut["chain"]
    records = chain_records[chain]
    idx = next(i for i, r in enumerate(records) if r["resi"] == mut["resi"])
    if chain == AB_CHAINS[0]:
        seq = list(vh)
    else:
        seq = list(vl)
    if seq[idx] != mut["wt"]:
        raise ValueError(
            f"WT mismatch {mut['chain']}:{mut['resi']} pdb={seq[idx]} expected={mut['wt']}"
        )
    seq[idx] = mut["mut"]
    if chain == AB_CHAINS[0]:
        return "".join(seq), vl
    return vh, "".join(seq)


def _compute_ablang2_score(vh: str, vl: str) -> tuple[float | None, str | None]:
    vh = (vh or "").strip().upper()
    vl = (vl or "").strip().upper()
    if not vh or not vl:
        return None, "missing_vh_or_vl"
    try:
        import numpy as np  # type: ignore
        import ablang2  # type: ignore

        if "ablang2-paired" not in _ABLANG2_MODEL_CACHE:
            _ABLANG2_MODEL_CACHE["ablang2-paired"] = ablang2.pretrained("ablang2-paired")
        model = _ABLANG2_MODEL_CACHE["ablang2-paired"]
        pll = model([(vh, vl)], mode="pseudo_log_likelihood")
        return round(float(np.squeeze(pll)), 3), None
    except Exception as exc:  # noqa: BLE001
        return None, f"{type(exc).__name__}: {exc}"


def _run_cmc_ablang(
    vh: str,
    vl: str,
    wt_ablang_score: float | None,
    clinical_engine,
    skip_ablang: bool = False,
) -> dict[str, Any]:
    metrics = CMCMetricEngine.compute_metrics(vh, vl)

    clinical = None
    clinical_verdict = "PASS"
    if clinical_engine is not None:
        clinical = clinical_engine.evaluate(metrics)
        if clinical.gate_summary.get("FAIL", 0) > 0 or clinical.gate_summary.get("WARN", 0) > 0:
            clinical_verdict = "WARN"

    if skip_ablang:
        mut_ab, ablang_error = None, "deferred_to_shortlist_backfill"
    else:
        mut_ab, ablang_error = _compute_ablang2_score(vh, vl)
    ablang_delta = None
    ablang_verdict = "PASS"
    if wt_ablang_score is not None and mut_ab is not None:
        ablang_delta = round(mut_ab - wt_ablang_score, 3)
        if ablang_delta <= ABLANG_VETO_DELTA:
            ablang_verdict = "VETO"

    if ablang_verdict == "VETO":
        overall = "VETO"
    elif ablang_error and mut_ab is None:
        overall = "NOT_RUN"
    elif clinical_verdict == "WARN":
        overall = "WARN"
    else:
        overall = "PASS"

    return {
        "verdict": overall,
        "clinical_verdict": clinical_verdict,
        "ablang_verdict": ablang_verdict,
        "hpr": "skipped_by_policy",
        "ablang_score": mut_ab,
        "ablang_delta": ablang_delta,
        "clinical_score": clinical.clinical_score if clinical else None,
        "clinical_gate_summary": clinical.gate_summary if clinical else None,
        "cmc_metrics": metrics,
        "ablang_error": ablang_error,
    }


def _run_check8(
    pdb_path: Path,
    row: dict[str, Any],
    evoef2_exe: str,
    out_dir: Path,
    *,
    minimize: bool,
    max_iterations: int,
) -> dict[str, Any]:
    from core.structure.relax_and_clash_gate import relax_and_clash_check

    mut = [_to_gate_mut(row)]
    with __import__("tempfile").TemporaryDirectory(prefix="pag1_check8_") as tmp:
        mutant_pdb = _evoef2_build(evoef2_exe, str(pdb_path), mut, AB_CHAINS[0], tmp)
        if mutant_pdb is None:
            return {"verdict": "VETO", "notes": "EvoEF2 BuildMutant failed before CHECK 8"}
        result = relax_and_clash_check(
            pdb_path=mutant_pdb,
            ab_chains=AB_CHAINS,
            antigen_chains=AG_CHAINS,
            minimize=minimize,
            max_iterations=max_iterations,
            out_dir=str(out_dir),
        )
    payload = dataclasses.asdict(result)
    payload["verdict"] = result.verdict
    return payload


def _process_candidate(
    row: dict[str, Any],
    *,
    clone_id: str,
    numbering: dict[str, Any],
    fp,
    chain_records: dict,
    stage25_pass: set[str],
    stage25_audit: dict[str, dict],
    toolkit: AffinityEnergyToolkit,
    wt_antifold_logp: float | None,
    wt_ablang_score: float | None,
    clinical_engine,
    pdb_path: Path,
    evoef2_exe: str,
    check8_dir: Path,
    skip_check8: bool,
    check8_iterations: int,
    check8_no_minimize: bool,
    dry_run: bool,
    skip_ablang: bool = False,
) -> dict[str, Any]:
    key = _mut_key(row)
    t0 = time.time()
    gates: dict[str, Any] = {}
    stop = False

    # Gate 1 — CHECK 6
    if stop:
        pass
    else:
        g6 = _run_check6(row, fp, numbering)
        gates["check_6_design_prior"] = g6
        if g6["verdict"] == "VETO":
            stop = True

    # Gate 2 — Stage 2.5 (batch precomputed)
    if not stop:
        s25 = stage25_audit.get(key)
        if key not in stage25_pass:
            gates["stage_2_5_integrity"] = s25 or {"verdict": "VETO", "reason": "not_in_pass_set"}
            if gates["stage_2_5_integrity"].get("verdict") != "RESCUED":
                stop = True
        else:
            gates["stage_2_5_integrity"] = s25 or {"verdict": "PASS"}

    # Gate 3 — CHECK 7
    if not stop:
        g7 = _run_check7(row, numbering, chain_records)
        gates["check_7_seq_liability"] = g7
        if g7["verdict"] == "VETO":
            stop = True

    if dry_run:
        gates["thermompnn"] = {"verdict": "NOT_RUN", "reason": "dry_run"}
        gates["antifold"] = {"verdict": "NOT_RUN", "reason": "dry_run"}
        gates["cmc_ablang"] = {"verdict": "NOT_RUN", "reason": "dry_run"}
        gates["check_8_relax_clash"] = {"verdict": "NOT_RUN", "reason": "dry_run"}
    else:
        mut_list = [_to_gate_mut(row)]

        # Gate 4 — ThermoMPNN
        if not stop:
            tr = toolkit.run_thermompnn(mut_list)
            thermo_ddg = tr.get("ddg")
            if tr.get("error"):
                gates["thermompnn"] = {"verdict": "ERROR", "error": tr["error"]}
            elif thermo_ddg is not None and thermo_ddg > THERMO_VETO:
                gates["thermompnn"] = {
                    "verdict": "VETO",
                    "thermo_ddg": thermo_ddg,
                    "threshold": THERMO_VETO,
                    "elapsed_s": tr.get("elapsed"),
                }
                stop = True
            else:
                gates["thermompnn"] = {
                    "verdict": "PASS",
                    "thermo_ddg": thermo_ddg,
                    "threshold": THERMO_VETO,
                    "elapsed_s": tr.get("elapsed"),
                }

        # Gate 5 — AntiFold
        if not stop:
            af = toolkit.run_antifold(mut_list, wt_logp=wt_antifold_logp)
            af_ddg = af.get("ddg")
            if af.get("error"):
                gates["antifold"] = {"verdict": "ERROR", "error": af["error"]}
            elif af_ddg is not None and af_ddg > ANTIFOLD_VETO:
                gates["antifold"] = {
                    "verdict": "VETO",
                    "af_ddg": af_ddg,
                    "threshold": ANTIFOLD_VETO,
                    "wt_logp": af.get("wt_logp"),
                    "mut_logp": af.get("mut_logp"),
                    "elapsed_s": af.get("elapsed"),
                }
                stop = True
            else:
                gates["antifold"] = {
                    "verdict": "PASS",
                    "af_ddg": af_ddg,
                    "threshold": ANTIFOLD_VETO,
                    "wt_logp": af.get("wt_logp"),
                    "mut_logp": af.get("mut_logp"),
                    "elapsed_s": af.get("elapsed"),
                }

        # Gate 6 — CMC + AbLang2 (HPR skipped)
        if not stop:
            vh, vl = _mutate_fv_sequences(chain_records, row)
            g_cmc = _run_cmc_ablang(
                vh, vl, wt_ablang_score, clinical_engine, skip_ablang=skip_ablang
            )
            gates["cmc_ablang"] = g_cmc
            if g_cmc["verdict"] == "VETO":
                stop = True

        # Gate 7 — CHECK 8
        if skip_check8:
            gates["check_8_relax_clash"] = {"verdict": "NOT_RUN", "reason": "skipped_by_flag"}
        elif not stop:
            g8 = _run_check8(
                pdb_path,
                row,
                evoef2_exe,
                check8_dir,
                minimize=not check8_no_minimize,
                max_iterations=check8_iterations,
            )
            gates["check_8_relax_clash"] = g8
            if g8.get("verdict") == "VETO":
                stop = True

    overall = _gate_verdict(gates)
    return {
        **row,
        "clone": clone_id,
        "mutation_key": key,
        "overall_status": overall,
        "gates": gates,
        "stopped_at_gate": next(
            (name for name, g in gates.items() if g.get("verdict") == "VETO"),
            None,
        ),
        "elapsed_s": round(time.time() - t0, 2),
    }


def _write_csv(path: Path, records: list[dict[str, Any]]) -> None:
    if not records:
        return
    fieldnames = [
        "clone",
        "variant",
        "mutation_key",
        "locus",
        "chain",
        "pdb_resi",
        "wt",
        "mut",
        "evoef2_ddg",
        "overall_status",
        "stopped_at_gate",
        "check6",
        "stage25",
        "check7",
        "thermo_ddg",
        "thermo_verdict",
        "af_ddg",
        "af_verdict",
        "ablang_delta",
        "cmc_verdict",
        "check8_verdict",
        "elapsed_s",
    ]
    with path.open("w", newline="", encoding="utf-8") as fh:
        w = csv.DictWriter(fh, fieldnames=fieldnames, extrasaction="ignore")
        w.writeheader()
        for rec in records:
            g = rec.get("gates") or {}
            w.writerow(
                {
                    "clone": rec.get("clone"),
                    "variant": rec.get("variant"),
                    "mutation_key": rec.get("mutation_key"),
                    "locus": rec.get("locus"),
                    "chain": rec.get("chain"),
                    "pdb_resi": rec.get("pdb_resi"),
                    "wt": rec.get("wt"),
                    "mut": rec.get("mut"),
                    "evoef2_ddg": rec.get("evoef2_ddg"),
                    "overall_status": rec.get("overall_status"),
                    "stopped_at_gate": rec.get("stopped_at_gate"),
                    "check6": (g.get("check_6_design_prior") or {}).get("verdict"),
                    "stage25": (g.get("stage_2_5_integrity") or {}).get("verdict"),
                    "check7": (g.get("check_7_seq_liability") or {}).get("verdict"),
                    "thermo_ddg": (g.get("thermompnn") or {}).get("thermo_ddg"),
                    "thermo_verdict": (g.get("thermompnn") or {}).get("verdict"),
                    "af_ddg": (g.get("antifold") or {}).get("af_ddg"),
                    "af_verdict": (g.get("antifold") or {}).get("verdict"),
                    "ablang_delta": (g.get("cmc_ablang") or {}).get("ablang_delta"),
                    "cmc_verdict": (g.get("cmc_ablang") or {}).get("verdict"),
                    "check8_verdict": (g.get("check_8_relax_clash") or {}).get("verdict"),
                    "elapsed_s": rec.get("elapsed_s"),
                }
            )


def _save_outputs(
    paths: dict[str, Path],
    *,
    clone_id: str,
    records: list[dict[str, Any]],
    stage25_summary: dict[str, Any],
    meta: dict[str, Any],
) -> None:
    shortlist = [r for r in records if r.get("overall_status") in ("PASS", "WARN")]
    payload = {
        "generated_at": _utc_now(),
        "protocol_version": PROTOCOL_VERSION,
        "stage": STAGE,
        "clone": clone_id,
        "mmgbsa": "deferred",
        "meta": meta,
        "stage2_5_batch_summary": stage25_summary,
        "n_input": len(records),
        "n_pass": sum(1 for r in records if r.get("overall_status") == "PASS"),
        "n_warn": sum(1 for r in records if r.get("overall_status") == "WARN"),
        "n_fail": sum(1 for r in records if r.get("overall_status") == "FAIL"),
        "n_incomplete": sum(1 for r in records if r.get("overall_status") == "INCOMPLETE"),
        "records": records,
    }
    paths["json"].write_text(json.dumps(payload, indent=2), encoding="utf-8")
    paths["shortlist"].write_text(
        json.dumps(
            {
                "generated_at": payload["generated_at"],
                "clone": clone_id,
                "n_shortlist": len(shortlist),
                "mutations": shortlist,
            },
            indent=2,
        ),
        encoding="utf-8",
    )
    _write_csv(paths["csv"], records)


def process_clone(
    clone_id: str,
    *,
    resume: bool,
    dry_run: bool,
    limit: int | None,
    skip_check8: bool,
    check8_iterations: int,
    check8_no_minimize: bool,
    evoef2_exe: str,
    thermompnn_dir: str,
    skip_ablang: bool = False,
) -> dict[str, Any]:
    paths = _out_paths(clone_id)
    recommended = _load_recommended(clone_id)
    if limit is not None:
        recommended = recommended[:limit]

    done_keys: set[str] = set()
    existing_records: list[dict[str, Any]] = []
    if resume and paths["checkpoint"].is_file():
        ck = json.loads(paths["checkpoint"].read_text(encoding="utf-8"))
        existing_records = ck.get("records") or []
        done_keys = {r["mutation_key"] for r in existing_records}

    pdb_path = _rank1_pdb(clone_id)
    numbering = _load_numbering(clone_id)
    chain_records = _parse_pdb_sequences(str(pdb_path))
    fp = load_fingerprint("vh_vl")
    clinical_engine = get_engine("humanized_458")

    wt_vh = numbering["sequences"]["vh"]
    wt_vl = numbering["sequences"]["vl"]
    if skip_ablang:
        wt_ablang_score, wt_ablang_error = None, "deferred_to_shortlist_backfill"
        print(f"[{clone_id}] WT AbLang2 baseline: deferred (bulk skip)", flush=True)
    else:
        wt_ablang_score, wt_ablang_error = _compute_ablang2_score(wt_vh, wt_vl)
        if wt_ablang_error:
            print(f"[{clone_id}] WT AbLang2 baseline: {wt_ablang_error}", flush=True)
        else:
            print(f"[{clone_id}] WT AbLang2 baseline: {wt_ablang_score}", flush=True)

    toolkit = AffinityEnergyToolkit(
        complex_pdb=str(pdb_path),
        ab_chains=AB_CHAINS,
        ag_chains=AG_CHAINS,
        evoef2_exe=evoef2_exe,
        thermompnn_dir=thermompnn_dir,
    )

    # Batch Stage 2.5 once per clone
    candidates = [_to_gate_mut(r) for r in recommended]
    affinity_ddg = {
        f"{m['chain']}:{m['resi']}:{m['wt']}:{m['mut']}": float(r["evoef2_ddg"])
        for m, r in zip(candidates, recommended)
        if r.get("evoef2_ddg") is not None
    }
    print(f"[{clone_id}] Stage 2.5 batch on {len(candidates)} candidates...", flush=True)
    stage25_result = run_stage2_5(
        pdb_path=str(pdb_path),
        ab_chains=AB_CHAINS,
        candidates=candidates,
        affinity_ddg=affinity_ddg,
        rescue=True,
        antigen_chains=AG_CHAINS,
    )
    stage25_pass, stage25_audit = _build_stage25_maps(stage25_result)
    print(
        f"[{clone_id}] Stage 2.5: passed={len(stage25_pass)} "
        f"vetoed={len(stage25_result.vetoed)} rescued={len(stage25_result.rescued)}",
        flush=True,
    )

    wt_af = toolkit.run_antifold([], wt_logp=None)
    wt_antifold_logp = wt_af.get("wt_logp")

    check8_dir = paths["dir"] / "check8_pdbs"
    check8_dir.mkdir(parents=True, exist_ok=True)

    records = list(existing_records)
    pending = [r for r in recommended if _mut_key(r) not in done_keys]
    print(f"[{clone_id}] Post-filter pending={len(pending)} (done={len(done_keys)})", flush=True)

    for i, row in enumerate(pending, 1):
        key = _mut_key(row)
        print(f"[{clone_id}] [{i}/{len(pending)}] {row.get('variant', key)}", flush=True)
        rec = _process_candidate(
            row,
            clone_id=clone_id,
            numbering=numbering,
            fp=fp,
            chain_records=chain_records,
            stage25_pass=stage25_pass,
            stage25_audit=stage25_audit,
            toolkit=toolkit,
            wt_antifold_logp=wt_antifold_logp,
            wt_ablang_score=wt_ablang_score,
            clinical_engine=clinical_engine,
            pdb_path=pdb_path,
            evoef2_exe=evoef2_exe,
            check8_dir=check8_dir,
            skip_check8=skip_check8,
            check8_iterations=check8_iterations,
            check8_no_minimize=check8_no_minimize,
            dry_run=dry_run,
            skip_ablang=skip_ablang,
        )  # skip_ablang threaded from process_clone
        records.append(rec)
        paths["checkpoint"].write_text(
            json.dumps(
                {
                    "updated_at": _utc_now(),
                    "clone": clone_id,
                    "n_done": len(records),
                    "records": records,
                },
                indent=2,
            ),
            encoding="utf-8",
        )
        _save_outputs(
            paths,
            clone_id=clone_id,
            records=records,
            stage25_summary=stage25_result.summary,
            meta={
                "rank1_pdb": str(pdb_path),
                "skip_check8": skip_check8,
                "dry_run": dry_run,
                "gate_thresholds": {
                    "thermompnn_veto": THERMO_VETO,
                    "antifold_veto": ANTIFOLD_VETO,
                    "ablang_veto_delta": ABLANG_VETO_DELTA,
                    "hpr": "skipped",
                },
            },
        )

    summary = {
        "clone": clone_id,
        "n_input": len(recommended),
        "n_pass": sum(1 for r in records if r.get("overall_status") == "PASS"),
        "n_warn": sum(1 for r in records if r.get("overall_status") == "WARN"),
        "n_fail": sum(1 for r in records if r.get("overall_status") == "FAIL"),
        "output_json": str(paths["json"]),
    }
    return summary


def build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(description="PAG-1 VAM Stage-4 sequential post-filter (no MM/GBSA)")
    p.add_argument("--clone", choices=CLONES, action="append", help="Limit to clone(s)")
    p.add_argument("--resume", action="store_true", help="Resume from checkpoint.json")
    p.add_argument("--dry-run", action="store_true", help="Run CHECK 6/7/2.5 only")
    p.add_argument("--limit", type=int, default=None, help="Max candidates per clone (debug)")
    p.add_argument("--skip-check8", action="store_true", help="Skip OpenMM relax/clash gate")
    p.add_argument("--check8-iterations", type=int, default=500)
    p.add_argument("--check8-no-minimize", action="store_true")
    p.add_argument("--evoef2", default=EVOEF2_DEFAULT)
    p.add_argument("--thermompnn-dir", default=THERMOMPNN_DEFAULT)
    p.add_argument(
        "--skip-ablang",
        action="store_true",
        help="Defer AbLang2 in bulk gate run (slow on CPU); backfill on shortlist after.",
    )
    return p


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    clones = args.clone or CLONES

    batch_summary: dict[str, Any] = {
        "generated_at": _utc_now(),
        "protocol_version": PROTOCOL_VERSION,
        "stage": STAGE,
        "mmgbsa": "deferred_to_vps",
        "clones": {},
    }

    for clone_id in clones:
        print(f"\n=== PAG-1 Stage-4 post-filter clone {clone_id} ===", flush=True)
        batch_summary["clones"][clone_id] = process_clone(
            clone_id,
            resume=args.resume,
            dry_run=args.dry_run,
            limit=args.limit,
            skip_check8=args.skip_check8,
            check8_iterations=args.check8_iterations,
            check8_no_minimize=args.check8_no_minimize,
            evoef2_exe=args.evoef2,
            thermompnn_dir=args.thermompnn_dir,
            skip_ablang=args.skip_ablang,
        )

    summary_path = VAM_DIR / "stage4_batch_summary.json"
    summary_path.write_text(json.dumps(batch_summary, indent=2), encoding="utf-8")
    print(f"\nBatch summary: {summary_path}", flush=True)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
