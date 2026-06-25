"""
Shared IgG / VH+VL CMC pipeline: same computation path as ``POST /cmc/igg``.

Used by ``api/routers/cmc.py`` and offline batch scripts (three-source demos, CI smoke tests).
"""
from __future__ import annotations

from pathlib import Path
from typing import Any, Dict, List, Optional

from core.evaluation.evaluator import AbEvaluator, AntibodyType


def _ab_type_map() -> Dict[str, AntibodyType]:
    return {
        "IgG1": AntibodyType.HUMANIZED,
        "IgG2": AntibodyType.HUMANIZED,
        "IgG4": AntibodyType.HUMANIZED,
        "humanized": AntibodyType.HUMANIZED,
        "humanized_transgenic": AntibodyType.HUMANIZED,
        "fully_human": AntibodyType.FULLY_HUMAN,
        "therapeutic_regular_antibody": AntibodyType.FULLY_HUMAN,
        "phage_display": AntibodyType.FULLY_HUMAN,
        "b_cell_derived": AntibodyType.FULLY_HUMAN,
        "b_cell": AntibodyType.FULLY_HUMAN,
        "human_b_cell": AntibodyType.FULLY_HUMAN,
        "natural384_transgenic_animal": AntibodyType.FULLY_HUMAN,
        "natural384_phage_display": AntibodyType.FULLY_HUMAN,
        "natural384_human_b_cell_derived": AntibodyType.FULLY_HUMAN,
        "scFv": AntibodyType.SCFV,
    }


def run_igg_cmc_pipeline(
    *,
    vh_sequence: str,
    vl_sequence: str,
    antibody_type: str,
    project_name: str,
    out_dir: Path,
    job_id_for_urls: Optional[str] = None,
    progress: Optional[Dict[str, Any]] = None,
    run_structure: bool = True,
    smart_cmc: bool = False,
) -> Dict[str, Any]:
    """
    Execute fast AbEvaluator modules + regular_ab_developability + optional Fv modeling / SASA / structural gates.

    Parameters
    ----------
    out_dir:
        Job directory (writes ``Fv_ABodyBuilder2.pdb`` when ``run_structure``).
    job_id_for_urls:
        When set, ``fv_structure.pdb_url`` uses ``/files/{job_id}/...`` (console).
        When omitted, uses relative ``Fv_ABodyBuilder2.pdb`` for standalone HTML folders.
    progress:
        Optional mutable dict with key ``progress`` (int) — updated like the FastAPI job store.
    run_structure:
        If False, skips ImmuneBuilder Fv prediction and structural metric patching (faster offline smoke).
    """

    def _prog(val: int) -> None:
        if progress is not None:
            progress["progress"] = val

    ab_type_map = _ab_type_map()
    ab_type = ab_type_map.get(antibody_type, AntibodyType.HUMANIZED)

    _prog(15)
    evaluator = AbEvaluator(
        project_name=project_name,
        ab_type=ab_type,
        vh_seq=vh_sequence.strip().upper(),
        vl_seq=vl_sequence.strip().upper(),
        strict_qa=False,
    )
    _prog(30)
    modules = ["developability", "cdr_scan", "germline"]
    if smart_cmc:
        modules.append("cmc_advisor")
    
    result = evaluator.run(modules=modules)
    _prog(75)

    summary = result._executive_summary()
    dev = result.results.get("developability", {})
    cdr = result.results.get("cdr_scan", {})
    cmc_adv = result.results.get("cmc_advisor", {})
    germ = result.results.get("germline", {})

    liab_list = cdr.get("liabilities", [])

    def _count_type(t: str) -> int:
        return sum(1 for x in liab_list if x.get("type", "").startswith(t))

    adv_metrics = cmc_adv.get("metrics", {}) if isinstance(cmc_adv, dict) else {}
    raw_metrics = {
        k: (v.get("value") if isinstance(v, dict) else v)
        for k, v in adv_metrics.items()
    }

    # Always populate base sequence metrics from the developability module and
    # CMCMetricEngine so compute_adi() receives real values even when
    # smart_cmc=False (cmc_advisor not run). Without this, raw_metrics is
    # empty and ADI collapses to 0; SAP/FvAsym/agg/hydro_cluster remain N/A.
    _seq_all: Dict[str, Any] = {}
    try:
        from core.cmc.cmc_metrics import CMCMetricEngine
        # vh_in / vl_in defined later; use the source strings directly here.
        _seq_all = CMCMetricEngine.compute_metrics(
            vh_sequence.strip().upper(), vl_sequence.strip().upper()
        ) or {}
    except Exception:
        pass

    _dev_base: Dict[str, Any] = {
        # dev module gives higher-fidelity pI (Fab estimate) vs. combined seq
        "pI": dev.get("pI_fab_estimate"),
        "GRAVY": dev.get("GRAVY"),
        "instability_index": dev.get("instability_index"),
        "hydro_patch_max9": dev.get("hydro_patch_max9"),
        "charge_patch_max7": dev.get("charge_patch_max7"),
        "net_charge_pH7": dev.get("net_charge_pH7"),
        # CDR scan counts for chemical liabilities
        "deamidation_sites": _count_type("deamidation"),
        "isomerization_sites": _count_type("isomerization"),
        "oxidation_sites": _count_type("oxidation"),
        "glycosylation_sites": _count_type("glycosylation"),
        # Sequence-derived metrics not provided by the developability module
        "SAP_score": _seq_all.get("SAP_score"),
        "Fv_charge_asymmetry": _seq_all.get("Fv_charge_asymmetry"),
        "agg_motifs": _seq_all.get("agg_motifs"),
        "hydro_cluster_count": _seq_all.get("hydro_cluster_count"),
        "free_cys": _seq_all.get("free_cys"),
    }
    for _k, _v in _dev_base.items():
        if _v is not None and _k not in raw_metrics:
            raw_metrics[_k] = _v

    def _merge_suggestions_from_gates() -> list:
        base: list = list(cmc_adv.get("mutation_suggestions", []) or [])
        if base:
            return base
        out: list = []
        for mkey, minfo in (adv_metrics or {}).items():
            if not isinstance(minfo, dict):
                continue
            g = str(minfo.get("gate", "")).upper()
            if g in ("WARN", "FAIL"):
                out.append({"metric": mkey, "target_metric": mkey, "gate": g})
        return out

    merged_suggestions = _merge_suggestions_from_gates()

    abref_pct: Optional[float] = None
    if dev.get("abref_percentile") is not None:
        try:
            abref_pct = round(float(dev["abref_percentile"]), 1)
        except (TypeError, ValueError):
            abref_pct = None
    if abref_pct is None and result.clinical_score is not None:
        try:
            abref_pct = round(float(result.clinical_score), 1)
        except (TypeError, ValueError):
            abref_pct = None

    regular_ab_block = None
    if antibody_type != "scFv":
        try:
            from core.cmc.regular_ab_developability import build_regular_ab_developability

            regular_ab_block = build_regular_ab_developability(
                vh_seq=vh_sequence.strip().upper(),
                vl_seq=vl_sequence.strip().upper(),
                origin=antibody_type,
                raw_metrics=raw_metrics,
                cdr_liabilities=liab_list,
                germline=germ,
                mutation_suggestions=merged_suggestions,
            )
        except Exception as e:  # noqa: BLE001
            regular_ab_block = {
                "status": "WARN",
                "message": "Regular antibody developability layer was not available.",
                "detail": f"{type(e).__name__}: {e}",
            }

    vh_in = vh_sequence.strip().upper()
    vl_in = vl_sequence.strip().upper()

    _prog(32)
    from core.cmc.igg_cmc_segmentation import segment_vh_vl_imgt

    imgt_seg = segment_vh_vl_imgt(vh_in, vl_in)

    hpr_ablang: Dict[str, Any] = {
        "hpr_index": None,
        "hpr_error": None,
        "ablang_score": None,
        "ablang_error": None,
    }
    try:
        from core.cmc.igg_hpr_ablang import compute_igg_cmc_hpr_ablang

        hpr_ablang = compute_igg_cmc_hpr_ablang(vh_in, vl_in)
    except Exception as e:  # noqa: BLE001
        hpr_ablang = {
            "hpr_index": None,
            "hpr_error": f"{type(e).__name__}: {e}",
            "ablang_score": None,
            "ablang_error": f"{type(e).__name__}: {e}",
        }

    # 4) p-AbNatiV2 Pairing Guard & Humanness
    p_abnativ: Dict[str, Any] = {
        "vh_humanness": None,
        "vl_humanness": None,
        "paired_humanness": None,
        "pairing_likelihood": None,
        "error": None,
        "warning": None,
    }
    try:
        from core.humanization.p_abnativ_layer import score_paired_humanness
        _pres = score_paired_humanness(vh_in, vl_in)
        p_abnativ = {
            "vh_humanness": round(float(_pres.vh_humanness), 4) if _pres.vh_humanness is not None else None,
            "vl_humanness": round(float(_pres.vl_humanness), 4) if _pres.vl_humanness is not None else None,
            "paired_humanness": round(float(_pres.paired_humanness), 4) if _pres.paired_humanness is not None else None,
            "pairing_likelihood": round(float(_pres.pairing_likelihood), 4) if _pres.pairing_likelihood is not None else None,
            "error": _pres.error,
            "warning": getattr(_pres, "warning", None),
        }
    except Exception as e:  # noqa: BLE001
        p_abnativ["error"] = f"{type(e).__name__}: {e}"

    # TCIA (MHC-II sequence immunogenicity index) — offline/heuristic when IEDB off
    tcia_score: Optional[float] = None
    tcia_risk_level: Optional[str] = None
    tcia_error: Optional[str] = None
    immuno_risk = "not_run"
    try:
        from core.immunogenicity.mhcii_analyzer import MHCII_Analyzer

        _mh = MHCII_Analyzer(vh_seq=vh_in, vl_seq=vl_in, use_iedb=False)
        _mres = _mh.run(is_vhh=False)
        tcia_score = round(float(_mres.tcia_score), 4)
        tcia_risk_level = str(_mres.risk_level)
        immuno_risk = tcia_risk_level
    except Exception as e:  # noqa: BLE001
        tcia_error = f"{type(e).__name__}: {e}"

    payload: Dict[str, Any] = {
        "abenginecore_version": "1.3.0",
        "cmc_policy_version": "CMC_MUTATION_POLICY_V1.2",
        "project_name": project_name,
        "vh_sequence": vh_in,
        "vl_sequence": vl_in,
        "imgt_segmentation": imgt_seg,
        "hpr_index": hpr_ablang.get("hpr_index"),
        "hpr_error": hpr_ablang.get("hpr_error"),
        "ablang_score": hpr_ablang.get("ablang_score"),
        "ablang_error": hpr_ablang.get("ablang_error"),
        "p_abnativ2": p_abnativ,
        "tcia_score": tcia_score,
        "tcia_risk_level": tcia_risk_level,
        "tcia_error": tcia_error,
        "pI_fab": dev.get("pI_fab_estimate"),
        "GRAVY": dev.get("GRAVY"),
        "instability_index": dev.get("instability_index"),
        "hydro_patch_max9": dev.get("hydro_patch_max9"),
        "charge_patch_max7": dev.get("charge_patch_max7"),
        "net_charge_pH7": dev.get("net_charge_pH7"),
        "n_deamidation": _count_type("deamidation"),
        "n_isomerization": _count_type("isomerization"),
        "n_oxidation": _count_type("oxidation"),
        "n_glycosylation": _count_type("glycosylation"),
        "liability_flags": cdr.get("flags", []),
        "total_liabilities": cdr.get("total_liabilities", 0),
        "germline_identity_vh": (germ.get("VH") or {}).get("top_match_identity"),
        "germline_identity_vl": (germ.get("VL") or {}).get("top_match_identity"),
        "closest_vh_germline": (germ.get("VH") or {}).get("top_match"),
        "closest_vl_germline": (germ.get("VL") or {}).get("top_match"),
        "immunogenicity_risk": immuno_risk,
        "n_mhcii_clusters_high_medium": 0,
        "clinical_score": result.clinical_score,
        "clinical_population": dev.get("clinical_population", "humanized_458"),
        "abref_percentile": abref_pct,
        "overall_status": result.overall_status,
        "overall_flags": result.overall_flags,
        "cmc_n_warn": summary.get("cmc_n_warn", 0),
        "cmc_n_fail": summary.get("cmc_n_fail", 0),
        "mutation_suggestions": (
            regular_ab_block.get("fr_modification_suggestions", [])
            if isinstance(regular_ab_block, dict)
            else []
        ),
        "developability_index": (
            (regular_ab_block or {}).get("developability_index")
            if isinstance(regular_ab_block, dict)
            else None
        ),
        "regular_ab_developability": regular_ab_block,
        "_modules": result.results,
    }

    _prog(78)
    if run_structure:
        try:
            from core.cmc.igg_fv_structure import predict_fv_to_pdb

            dest_pdb = out_dir / "Fv_ABodyBuilder2.pdb"
            pv = predict_fv_to_pdb(vh_in, vl_in, dest_pdb)
            if pv.get("ok"):
                pdb_rel = "Fv_ABodyBuilder2.pdb"
                pdb_url = (
                    f"/files/{job_id_for_urls}/{pdb_rel}"
                    if job_id_for_urls
                    else pdb_rel
                )
                payload["fv_structure"] = {
                    "plddt_eq": pv.get("plddt_eq"),
                    "vh_vl_angle_deg": pv.get("vh_vl_angle_deg"),
                    "pdb_url": pdb_url,
                    "pdb_filename": pdb_rel,
                    "note": "In-silico Fv model for visualization and manual review of FR candidate sites; not a crystal structure.",
                }
                try:
                    from core.cmc.fr_mutation_sites import (
                        build_candidate_payload_for_metric,
                        build_mutation_summary,
                    )

                    pdb_path_str = str(dest_pdb)
                    _label_to_key = {
                        "charge balance": "pI",
                        "charge patch": "charge_patch_max7",
                        "hydrophobicity": "GRAVY",
                        "hydrophobic patch": "hydro_patch_max9",
                        "surface hydrophobicity": "SAP_score",
                        "sequence stability": "instability_index",
                        "aggregation motif": "agg_motifs",
                    }
                    sasa_worked = False
                    rab = payload.get("regular_ab_developability")
                    if isinstance(rab, dict):
                        fr_suggs = rab.get("fr_modification_suggestions") or []
                        for sugg in fr_suggs:
                            _target_l = str(sugg.get("target") or sugg.get("metric") or "").lower()
                            mkey = str(sugg.get("metric_key") or "").strip()
                            dir_s = str(sugg.get("direction") or "").strip().lower()
                            if dir_s not in ("too_high", "too_low"):
                                dir_s = "too_high"
                            if not mkey:
                                mkey = _label_to_key.get(_target_l, "")
                            if not mkey:
                                if "negative charge patch" in _target_l:
                                    mkey = "pnc"
                                elif "positive charge patch" in _target_l:
                                    mkey = "ppc"
                                elif "surface hydrophobic patch" in _target_l:
                                    mkey = "psh"
                                elif "charge balance" in _target_l:
                                    mkey = "net_charge_pH7" if "net charge" in _target_l else "pI"
                                elif "sequence stability" in _target_l:
                                    mkey = "instability_index"
                                elif _target_l == "charge patch":
                                    mkey = "charge_patch_max7"
                            if not mkey:
                                continue
                            refined = build_candidate_payload_for_metric(
                                mkey, dir_s, vh_in, vl_in, pdb_path=pdb_path_str
                            )
                            if refined.get("sasa_filter_applied"):
                                sasa_worked = True
                            slim: Dict[str, Any] = {}
                            for k in (
                                "fr_positive_charge_sites",
                                "fr_negative_charge_sites",
                                "fr_hydrophobic_runs",
                                "fr_instability_sites",
                                "enumeration_note",
                                "sasa_filter_applied",
                                "sasa_threshold",
                                "vernier_filter_applied",
                                "mutation_policy",
                            ):
                                if k in refined and refined[k] not in (None, [], {}):
                                    slim[k] = refined[k]
                            if slim:
                                sugg["sequence_candidates"] = slim
                                ms = build_mutation_summary(vh_in, vl_in, slim)
                                if ms:
                                    sugg["mutation_sequences"] = ms
                    payload["fr_candidate_filter"] = {
                        "vernier_excluded": True,
                        "sasa_filtered": sasa_worked,
                        "sasa_threshold": 0.30,
                        "structure_used": True,
                    }
                except Exception:  # noqa: BLE001
                    payload["fr_candidate_filter"] = {
                        "vernier_excluded": True,
                        "sasa_filtered": False,
                        "structure_used": True,
                        "note": "SASA computation failed; Vernier mask still applied.",
                    }
                try:
                    from core.cmc.igg_structural_metrics import compute_igg_structural_metrics
                    from core.cmc.regular_ab_developability import (
                        _gate_from_risk,
                        _gate_policy_summary,
                        _hard_gate_failures,
                        _metric_interpretation,
                        _range_label,
                        _range_definition,
                        _range_type,
                        _risk_from_index_and_parameters,
                        _risk_position,
                        load_effective_primary_reference,
                        refresh_regular_ab_fr_suggestions,
                    )

                    structural_metrics = compute_igg_structural_metrics(str(dest_pdb), vh_in, vl_in)
                    if pv.get("vh_vl_angle_deg") is not None:
                        structural_metrics["vh_vl_angle_deg"] = pv.get("vh_vl_angle_deg")
                    payload["structural_cmc_metrics"] = structural_metrics
                    if isinstance(payload.get("regular_ab_developability"), dict):
                        _rab = payload["regular_ab_developability"]
                        _origin_raw = str(antibody_type or _rab.get("antibody_origin") or "")
                        _ref_data = load_effective_primary_reference(_origin_raw)
                        _ref_metrics = (_ref_data.get("metrics") or {}) if isinstance(_ref_data, dict) else {}
                        _params = _rab.get("parameters") or []
                        _by_key = {_p.get("key"): _p for _p in _params if isinstance(_p, dict)}
                        for _key, _val in structural_metrics.items():
                            if _key.startswith("_") or _val is None or _key not in _by_key:
                                continue
                            _ref_m = _ref_metrics.get(_key, {})
                            _risk, _pos = _risk_position(_key, float(_val), _ref_m)
                            _p = _by_key[_key]
                            _p["value"] = round(float(_val), 3)
                            _p["reference_position"] = _pos
                            _p["risk"] = _risk
                            _p["gate_status"] = _gate_from_risk(_risk)
                            _p["range_type"] = _range_type(_key)
                            _p["range_definition"] = _range_definition(_key)
                            _p["interpretation"] = _metric_interpretation(_key, _risk)
                            _p["normal_range"] = _range_label(_ref_m.get("p5"), _ref_m.get("p95"))
                            _p["preferred_range"] = _range_label(_ref_m.get("p25"), _ref_m.get("p75"))
                            _p["normal_low"] = _ref_m.get("p5")
                            _p["normal_high"] = _ref_m.get("p95")
                            _p["preferred_low"] = _ref_m.get("p25")
                            _p["preferred_high"] = _ref_m.get("p75")
                            _p["reference_mode"] = _ref_m.get("reference_mode") or "single_panel"
                        _rab["risk_level"] = _risk_from_index_and_parameters(
                            _rab.get("developability_index"), _params
                        )
                        _rab["overall_gate_status"] = _gate_from_risk(_rab["risk_level"])
                        _rab["hard_gate_failures"] = _hard_gate_failures(_params)
                        _rab["gate_policy"] = _gate_policy_summary()
                        refresh_regular_ab_fr_suggestions(
                            _rab,
                            vh_seq=vh_in,
                            vl_seq=vl_in,
                            origin=str(antibody_type or ""),
                            cdr_liabilities=liab_list,
                            base_mutation_suggestions=merged_suggestions,
                            ref_metrics=_ref_metrics,
                            pdb_path=str(dest_pdb) if dest_pdb.exists() else None,
                        )
                        payload["mutation_suggestions"] = _rab.get("fr_modification_suggestions") or []
                except Exception as e:  # noqa: BLE001
                    payload["structural_cmc_metrics"] = {"_struct_cmc_error": f"{type(e).__name__}: {e}"}
            else:
                payload["fv_structure"] = {"available": False, "error": pv.get("error", "unknown")}
                payload["fr_candidate_filter"] = {
                    "vernier_excluded": True,
                    "sasa_filtered": False,
                    "structure_used": False,
                }
        except Exception as e:  # noqa: BLE001
            payload["fv_structure"] = {"available": False, "error": f"{type(e).__name__}: {e}"}
            payload["fr_candidate_filter"] = {
                "vernier_excluded": True,
                "sasa_filtered": False,
                "structure_used": False,
            }
    else:
        payload["fv_structure"] = {
            "available": False,
            "note": "Structure modeling skipped (--fast mode or run_structure=False).",
        }
        payload["fr_candidate_filter"] = {
            "vernier_excluded": True,
            "sasa_filtered": False,
            "structure_used": False,
        }
        # Even without structure, generate sequence-level FR suggestions when Smart-CMC is on.
        if smart_cmc and isinstance(payload.get("regular_ab_developability"), dict):
            try:
                from core.cmc.regular_ab_developability import (
                    load_effective_primary_reference,
                    refresh_regular_ab_fr_suggestions,
                )
                _rab_ns = payload["regular_ab_developability"]
                _origin_raw_ns = str(antibody_type or _rab_ns.get("antibody_origin") or "")
                _ref_data_ns = load_effective_primary_reference(_origin_raw_ns)
                _ref_metrics_ns = (_ref_data_ns.get("metrics") or {}) if isinstance(_ref_data_ns, dict) else {}
                refresh_regular_ab_fr_suggestions(
                    _rab_ns,
                    vh_seq=vh_in,
                    vl_seq=vl_in,
                    origin=_origin_raw_ns,
                    cdr_liabilities=liab_list,
                    base_mutation_suggestions=merged_suggestions,
                    ref_metrics=_ref_metrics_ns,
                    pdb_path=None,
                )
                payload["mutation_suggestions"] = _rab_ns.get("fr_modification_suggestions") or []
            except Exception:  # noqa: BLE001
                pass

    _prog(85)

    # When smart_cmc is disabled, strip all FR mutation suggestions from the
    # payload so the UI does not show them. The regular_ab_developability block
    # still computes FR candidates internally (needed for SASA-filtered
    # parameters), but the consolidated suggestion list must be empty.
    if not smart_cmc:
        payload["mutation_suggestions"] = []
        _rab2 = payload.get("regular_ab_developability")
        if isinstance(_rab2, dict):
            _rab2["fr_modification_suggestions"] = []

    return payload
