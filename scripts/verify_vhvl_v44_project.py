#!/usr/bin/env python3
"""
verify_vhvl_v44_project.py — InSynBio AbEngineCore
===================================================


----
 VH/VL “ + （fix）”，、、。

（）
-------------------
1) results.json  single source of truth 
2) Dual-scheme numbering gate：ABARCII(IMGT)+ABARCII(Kabat)  seq_index （VH/VL）
3) ：structure_13param  vernier_dual_numbering =22
4) ：render_vhvl_v44_reports  Pre-Delivery Gate checks ，
5) ：delivery_{id} （README + FASTA + 2PDB + PDF）

（--fix）
---------------
-  MD
-  PDF（md_to_pdf）
-  delivery_{id}（package_delivery ，）


----
  python scripts/verify_vhvl_v44_project.py 9c1 projects/9c1_Redesign
  python scripts/verify_vhvl_v44_project.py 9c1 projects/9c1_Redesign --fix
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple
from datetime import datetime


SUITE = Path(__file__).resolve().parents[1]
CFG_V44 = SUITE / "config" / "vh_vl_humanization_v490.json"

# When executed as `python scripts/verify_...py`, sys.path[0] is `scripts/`,
# so we must add SUITE to import `core.*` and `scripts.*` reliably.
if str(SUITE) not in sys.path:
    sys.path.insert(0, str(SUITE))

FORBIDDEN_TERMS = ("ANARCII", "Anarcii", "ColabFold", "colabfold")

_CFG_V44_CACHE: Optional[Dict[str, Any]] = None


def _cfg_v44() -> Dict[str, Any]:
    """Lazy-load V4.4 checklist config (read-only)."""
    global _CFG_V44_CACHE
    if _CFG_V44_CACHE is None:
        try:
            _CFG_V44_CACHE = _load_json(CFG_V44)
        except Exception:
            _CFG_V44_CACHE = {}
    return _CFG_V44_CACHE or {}


def _load_imgt_germline_seq(gene_id: str, chain: str) -> str:
    """
    Load V-region AA sequence from IMGT JSON by gene_id.
    chain: "VH" or "VL" (kappa light).
    """
    gene_id = str(gene_id or "").strip()
    if not gene_id:
        return ""
    if chain == "VH":
        db = SUITE / "data" / "germlines" / "human_ig_aa" / "IGHV_aa.json"
    else:
        db = SUITE / "data" / "germlines" / "human_ig_aa" / "IGKV_aa.json"
    if not db.exists():
        return ""
    try:
        data = _load_json(db)
    except Exception:
        return ""
    for e in (data.get("entries") or []):
        if isinstance(e, dict) and str(e.get("id") or "") == gene_id:
            return str(e.get("sequence_aa") or "").strip()
    return ""


def _parse_checklist_item(s: str) -> Tuple[str, str]:
    """
    Parse '1.3 Dual-scheme numbering QA ...' -> ('1.3', 'Dual-scheme numbering QA ...')
    """
    s0 = str(s or "").strip()
    if not s0:
        return ("", "")
    parts = s0.split(" ", 1)
    if len(parts) == 1:
        return ("", s0)
    item_id = parts[0].strip()
    desc = parts[1].strip()
    return (item_id, desc)


def _v44_checklist_items(cfg: Dict[str, Any]) -> List[Dict[str, Any]]:
    """
    Expand v44 checklist_v4_4 into a flat list of items with fields:
      phase, item_id, description
    """
    out: List[Dict[str, Any]] = []
    cl = cfg.get("checklist_v4_4") if isinstance(cfg.get("checklist_v4_4"), dict) else {}
    if not isinstance(cl, dict):
        return out
    for phase_key, items in cl.items():
        if not isinstance(items, list):
            continue
        phase = str(phase_key).replace("_", " ").strip()
        for it in items:
            item_id, desc = _parse_checklist_item(str(it))
            out.append({"phase": phase, "item_id": item_id or "—", "description": desc or str(it)})
    return out


def _v44_deliverables_checklist(cfg: Dict[str, Any]) -> List[Dict[str, Any]]:
    rc = cfg.get("report_config") if isinstance(cfg.get("report_config"), dict) else {}
    lst = rc.get("deliverables_audit_checklist") if isinstance(rc.get("deliverables_audit_checklist"), list) else []
    out: List[Dict[str, Any]] = []
    for it in lst:
        if not isinstance(it, dict):
            continue
        out.append({"id": str(it.get("id") or "—"), "check": str(it.get("check") or "")})
    return out


def _audit_eval_metrics(results: Dict[str, Any], version: str) -> Dict[str, Any]:
    internal = results.get("_internal") if isinstance(results.get("_internal"), dict) else {}
    ev = internal.get(f"evaluation_{version}") if isinstance(internal, dict) else None
    res = ev.get("results") if isinstance(ev, dict) and isinstance(ev.get("results"), dict) else {}
    s13 = res.get("structure_13param") if isinstance(res.get("structure_13param"), dict) else {}
    met = s13.get("metrics") if isinstance(s13.get("metrics"), dict) else {}
    dvm = res.get("delta_vs_mouse") if isinstance(res.get("delta_vs_mouse"), dict) else {}
    delta = dvm.get("delta") if isinstance(dvm.get("delta"), dict) else {}
    qa = ev.get("_qa") if isinstance(ev, dict) and isinstance(ev.get("_qa"), dict) else {}
    imm = res.get("immunogenicity") if isinstance(res.get("immunogenicity"), dict) else {}
    dev = res.get("developability") if isinstance(res.get("developability"), dict) else {}
    return {
        "evaluation_present": bool(ev),
        "qa_present": bool(qa),
        "structure_metrics": met,
        "delta": delta,
        "immunogenicity": imm,
        "developability": dev,
    }


def _build_v44_checklist_audit(
    *,
    ab_id: str,
    project_dir: Path,
    results: Dict[str, Any],
    cfg: Dict[str, Any],
) -> Tuple[List[Dict[str, Any]], Dict[str, Any]]:
    """
    Return:
      - checklist_rows: list of {phase,item_id,description,status,evidence}
      - summary: {n_pass,n_warn,n_fail}
    """
    seqs = results.get("sequences") if isinstance(results.get("sequences"), dict) else {}
    mouse_vh = str(seqs.get("mouse_VH") or "")
    mouse_vl = str(seqs.get("mouse_VL") or "")
    final_vh, final_vl = _read_sequences_from_results(results)

    meta = results.get("_meta") if isinstance(results.get("_meta"), dict) else {}
    final_v = str(meta.get("final_version") or "").strip() or "v2"
    base_v = final_v if final_v in ("v1", "v2", "v3") else "v2"
    ev = _audit_eval_metrics(results, base_v)

    # Phase4 backmutation evidence
    p4 = _phase4_json_path(project_dir, ab_id)
    p4_obj: Dict[str, Any] = {}
    if p4 is not None:
        try:
            p4_obj = _load_json(p4)
        except Exception:
            p4_obj = {}
    p4_rows = p4_obj.get("backmutation_decisions") if isinstance(p4_obj.get("backmutation_decisions"), list) else []

    def _row(phase: str, item_id: str, desc: str, status: str, evidence: str) -> Dict[str, Any]:
        return {
            "phase": phase,
            "item_id": item_id,
            "description": desc,
            "status": status,
            "evidence": evidence,
        }

    def _file_ok(path: Path) -> bool:
        try:
            return path.exists() and path.is_file()
        except Exception:
            return False

    # Deterministic evidence checks (no heavy recompute)
    try:
        from core.numbering.dual_scheme import compute_dual_scheme_numbering  # noqa: PLC0415
        dual_ok = True
        for seq, ch in [(mouse_vh, "VH"), (mouse_vl, "VL"), (final_vh, "VH"), (final_vl, "VL")]:
            compute_dual_scheme_numbering(seq, chain_label=ch)
    except Exception as e:
        dual_ok = False
        dual_err = str(e)
    else:
        dual_err = ""

    # CDR union preservation (IMGT) — already the delivery hard gate
    cdr_union_probs = _cdr_union_gate_or_problem(results=results, cfg=cfg)
    cdr_union_ok = not cdr_union_probs

    # Kabat CDR exact match (fallback check; ensures CDRs preserved at Kabat definition too)
    try:
        from core.humanization.kabat_utils import get_kabat_numbering, verify_cdr_preservation  # noqa: PLC0415
        kd_mh = get_kabat_numbering(mouse_vh)
        kd_ml = get_kabat_numbering(mouse_vl)
        kd_hh = get_kabat_numbering(final_vh)
        kd_hl = get_kabat_numbering(final_vl)
        kabat_cdr_errs = verify_cdr_preservation(kd_hh, kd_mh, "VH") + verify_cdr_preservation(kd_hl, kd_ml, "VL")
    except Exception as e:
        kabat_cdr_errs = [f"kabat_cdr_check_error:{e}"]

    # Germline validation (2.0): ensure gene exists + no FR4 contamination pattern at tail
    gl = results.get("germline") if isinstance(results.get("germline"), dict) else {}
    vh_gene = str(gl.get("VH_gene") or "")
    vl_gene = str(gl.get("VL_gene") or "")
    germ_vh_seq = _load_imgt_germline_seq(vh_gene, "VH")
    germ_vl_seq = _load_imgt_germline_seq(vl_gene, "VL")
    def _fr4_contaminated(seq: str) -> bool:
        tail = (seq or "")[-12:].upper()
        return ("WGQGT" in tail) or ("FGGGT" in tail) or ("FGQGT" in tail)
    germ_ok = bool(germ_vh_seq and germ_vl_seq) and (not _fr4_contaminated(germ_vh_seq)) and (not _fr4_contaminated(germ_vl_seq))

    # Phase 3/5 structure file presence
    pdb_mouse = _find_version_pdb(project_dir, ab_id, "mouse") or _find_best_pdb(project_dir, ab_id, "mouse")
    pdb_final = _find_version_pdb(project_dir, ab_id, base_v) or _find_best_pdb(project_dir, ab_id, "humanized")

    # Structure metrics completeness (Vernier evidence)
    met = ev.get("structure_metrics") if isinstance(ev.get("structure_metrics"), dict) else {}
    vdn = met.get("vernier_dual_numbering")
    vdn_ok = isinstance(vdn, list) and len(vdn) == 22
    vernier_sasa_ok = (
        (isinstance(met.get("vernier_sasa"), dict) and bool(met.get("vernier_sasa")))
        or (isinstance(met.get("vernier_sasa_per_residue"), dict) and bool(met.get("vernier_sasa_per_residue")))
    )
    vernier_pack_ok = isinstance(met.get("vernier_packing"), dict) and bool(met.get("vernier_packing"))
    vernier_dist_ok = (
        (isinstance(met.get("vernier_cdr_dist"), dict) and bool(met.get("vernier_cdr_dist")))
        or (isinstance(met.get("vernier_cdr_distances"), dict) and bool(met.get("vernier_cdr_distances")))
    )

    # Phase4 log completeness
    p4_ok = bool(p4) and isinstance(p4_rows, list) and len(p4_rows) == 22
    p4_in_cdr_union_ok = p4_ok and all(isinstance(r, dict) and ("in_cdr_union" in r) for r in p4_rows)

    # Phase5 delta checks (if present)
    delta = ev.get("delta") if isinstance(ev.get("delta"), dict) else {}
    cdr_rmsd_pass = bool(delta.get("cdr_rmsd_pass")) if "cdr_rmsd_pass" in delta else None
    angle_pass = bool(delta.get("angle_pass")) if "angle_pass" in delta else None
    canon_pass = bool(delta.get("canonical_match_h1_h2_l1")) if "canonical_match_h1_h2_l1" in delta else None
    conclusion = str(delta.get("conclusion") or "")

    # Developability / immunogenicity presence (not disclosing internals to customer)
    dev_top = results.get("developability") if isinstance(results.get("developability"), dict) else {}
    pi_block = dev_top.get("pI") if isinstance(dev_top.get("pI"), dict) else {}
    pi_ok = bool(pi_block.get(f"{base_v}_pass")) if isinstance(pi_block.get(f"{base_v}_pass"), bool) else None
    imm_present = isinstance(ev.get("immunogenicity"), dict) and bool(ev.get("immunogenicity"))

    checklist_rows: List[Dict[str, Any]] = []
    for it in _v44_checklist_items(cfg):
        phase = str(it.get("phase") or "—")
        item_id = str(it.get("item_id") or "—")
        desc = str(it.get("description") or "")

        status = "WARN"
        evidence = "evidence:missing"

        if item_id == "1.1":
            status = "PASS" if cdr_union_ok else "FAIL"
            evidence = "cdr_union_preserved(IMGT)" if cdr_union_ok else (";".join(cdr_union_probs) or "cdr_union_gate_fail")
        elif item_id == "1.2":
            status = "PASS" if isinstance(met.get("canonical"), dict) and bool(met.get("canonical")) else "WARN"
            evidence = "canonical_present" if status == "PASS" else "canonical_missing_in_eval"
        elif item_id == "1.3":
            status = "PASS" if dual_ok else "FAIL"
            evidence = "dual_scheme_numbering_ok" if dual_ok else f"dual_scheme_numbering_error:{dual_err}"
        elif item_id == "2.0":
            status = "PASS" if germ_ok else "FAIL"
            evidence = f"VH={vh_gene},VL={vl_gene},fr4_contam={_fr4_contaminated(germ_vh_seq) or _fr4_contaminated(germ_vl_seq)}"
        elif item_id == "2.1":
            # We rely on Phase4/assembly CDR hard check rather than re-scoring germline gate here.
            status = "PASS" if (not kabat_cdr_errs) else "FAIL"
            evidence = "kabat_cdr_exact_match_mouse" if status == "PASS" else (";".join(kabat_cdr_errs)[:240])
        elif item_id == "2.2":
            cand = results.get("germline_candidates") if isinstance(results.get("germline_candidates"), dict) else {}
            ok = bool(cand.get("golden_pair_exception_documented")) or bool((results.get("_internal") or {}).get("pairing_lookup"))
            status = "PASS" if ok else "WARN"
            evidence = "golden_pair_checked_or_exception_documented" if ok else "missing_pairing_evidence"
        elif item_id == "2.3":
            status = "PASS" if (p4_ok and p4_in_cdr_union_ok) else "FAIL"
            evidence = f"phase4_rows={len(p4_rows)} in_cdr_union_annotated={p4_in_cdr_union_ok}"
        elif item_id == "2.4":
            cand = results.get("germline_candidates") if isinstance(results.get("germline_candidates"), dict) else {}
            vh_c = cand.get("VH_candidates") if isinstance(cand.get("VH_candidates"), list) else []
            vl_c = cand.get("VL_candidates") if isinstance(cand.get("VL_candidates"), list) else []
            status = "PASS" if (vh_c and vl_c) else "WARN"
            evidence = f"candidates:VH={len(vh_c)},VL={len(vl_c)}"
        elif item_id == "2.5":
            status = "WARN"
            evidence = "human_review_not_machine_verifiable"
        elif item_id == "3.1":
            status = "PASS" if (pdb_mouse is not None and _file_ok(pdb_mouse)) else "FAIL"
            evidence = f"mouse_pdb={pdb_mouse}" if pdb_mouse else "mouse_pdb_missing"
        elif item_id in ("3.2a", "3.2b", "3.2c", "3.2d", "3.2e"):
            ok_map = {
                "3.2a": met.get("vh_vl_angle_deg") is not None,
                "3.2b": vernier_sasa_ok,
                "3.2c": vernier_pack_ok,
                "3.2d": vernier_dist_ok,
                "3.2e": vdn_ok,
            }
            ok = bool(ok_map.get(item_id))
            status = "PASS" if ok else "FAIL"
            evidence = f"eval_{base_v}_structure_metrics_ok={ok}"
        elif item_id in ("4.1", "4.2", "4.3", "4.4", "4.5", "4.6", "4.SC1", "4.SC2", "4.SC3", "4.SC4", "4.SC5"):
            status = "PASS" if p4_ok else "FAIL"
            evidence = f"phase4_log={p4} rows={len(p4_rows)}"
        elif item_id == "4.7":
            status = "PASS" if (final_vh and final_vl) else "FAIL"
            evidence = f"final_version={base_v} len(VH)={len(final_vh)} len(VL)={len(final_vl)}"
        elif item_id == "4.8":
            status = "PASS" if (not kabat_cdr_errs and cdr_union_ok) else "FAIL"
            evidence = "cdr_preserved(kabat+imgt_union)" if status == "PASS" else (";".join(kabat_cdr_errs + cdr_union_probs)[:240])
        elif item_id == "4.9":
            status = "PASS" if (p4_ok and ("bm_vl_count" in p4_obj)) else "WARN"
            evidence = f"bm_vl_count={p4_obj.get('bm_vl_count','—')}"
        elif item_id == "5.1":
            status = "PASS" if (pdb_final is not None and _file_ok(pdb_final)) else "FAIL"
            evidence = f"humanized_pdb={pdb_final}" if pdb_final else "humanized_pdb_missing"
        elif item_id == "5.2":
            if cdr_rmsd_pass is True:
                status = "PASS"
            else:
                status = "FAIL"
            evidence = f"conclusion={conclusion} cdr_rmsd_pass={cdr_rmsd_pass}"
        elif item_id == "5.2b":
            status = "PASS" if canon_pass is True else "FAIL"
            evidence = f"canonical_match_h1_h2_l1={canon_pass}"
        elif item_id == "5.3":
            status = "PASS" if angle_pass is True else "FAIL"
            evidence = f"angle_pass={angle_pass}"
        elif item_id == "5.4":
            status = "PASS" if vernier_pack_ok else "FAIL"
            evidence = "vernier_packing_present" if vernier_pack_ok else "vernier_packing_missing"
        elif item_id == "5.5":
            # SAP: Strict check. If missing, FAIL.
            sap_val = None
            # Check structure metrics for SAP
            if "structure_13param" in results.get("results", {}):
                sap_val = results["results"]["structure_13param"].get("metrics", {}).get("sap_score")
            
            if sap_val is not None:
                status = "PASS"
                evidence = f"sap_score={sap_val}"
            else:
                status = "FAIL"
                evidence = "sap_score_missing_in_ssot"

        elif item_id == "5.6":
            status = "PASS" if pi_ok is True else "FAIL"
            evidence = f"pI_pass={pi_ok} pI={pi_block.get(base_v,'—')} gate={pi_block.get('gate_min','—')}-{pi_block.get('gate_max','—')}"

        elif item_id == "5.7":
            # Liabilities: Strict check.
            # If liabilities list is present and not empty, FAIL (unless whitelisted).
            liabs = dev_block.get("liabilities", [])
            # Filter out known false positives (e.g. canonical Cys) if logic allows, 
            # but here we just check raw list. If raw list has HIGH severity, FAIL.
            high_risk = [l for l in liabs if l.get("severity") == "HIGH"]
            
            if not liabs:
                status = "PASS"
                evidence = "no_liabilities_found"
            elif high_risk:
                status = "FAIL"
                evidence = f"high_risk_liabilities_found={len(high_risk)}"
            else:
                status = "WARN"
                evidence = f"low_risk_liabilities_found={len(liabs)}"
        elif item_id == "5.8":
            status = "PASS" if imm_present else "FAIL"
            evidence = "immunogenicity_present_in_evaluation" if imm_present else "missing_evaluation_immunogenicity"

        checklist_rows.append(_row(phase, item_id, desc, status, evidence))

    # Deliverables audit (D.*) — internal completeness, not customer package
    report_dir = project_dir / "reports"
    for d in _v44_deliverables_checklist(cfg):
        did = str(d.get("id") or "D.?")
        chk = str(d.get("check") or "")
        status = "WARN"
        evidence = ""
        # Map expected files
        if did == "D.1":
            f = project_dir / f"{ab_id}_sequences.fasta"
            status = "PASS" if _file_ok(f) else "FAIL"
            evidence = str(f)
        elif did == "D.2":
            f = project_dir / f"{ab_id}_results.json"
            required_keys = ["developability", "immunogenicity", "germline", "structure"]
            ok = _file_ok(f) and all(k in results for k in required_keys)
            status = "PASS" if ok else "FAIL"
            evidence = f"keys_ok={ok}"
        elif did == "D.3":
            f = report_dir / f"{ab_id}_V44_Audit.md"
            status = "PASS" if _file_ok(f) else "FAIL"
            evidence = str(f)
        elif did == "D.4":
            f = report_dir / f"{ab_id}_V44_Audit.pdf"
            status = "PASS" if _file_ok(f) else "WARN"
            evidence = str(f)
        elif did == "D.5":
            f = report_dir / f"{ab_id}_Client_zh.md"
            status = "PASS" if _file_ok(f) else "FAIL"
            evidence = str(f)
        elif did == "D.6":
            f = report_dir / f"{ab_id}_Client_zh.pdf"
            status = "PASS" if _file_ok(f) else "FAIL"
            evidence = str(f)
        elif did == "D.7":
            f = project_dir / "structures" / f"{ab_id}_mouse.pdb"
            status = "PASS" if _file_ok(f) else "FAIL"
            evidence = str(f)
        elif did == "D.8":
            # Check final PDB by SSOT final version mapping
            f = project_dir / "structures" / f"{ab_id}_humanized_{base_v}.pdb"
            status = "PASS" if _file_ok(f) else "FAIL"
            evidence = str(f)
        checklist_rows.append(_row("deliverables", did, chk, status, evidence))

    # Summary counts
    n_pass = sum(1 for r in checklist_rows if r.get("status") == "PASS")
    n_warn = sum(1 for r in checklist_rows if r.get("status") == "WARN")
    n_fail = sum(1 for r in checklist_rows if r.get("status") == "FAIL")
    return checklist_rows, {"n_pass": n_pass, "n_warn": n_warn, "n_fail": n_fail}

def _vernier_positions_from_cfg(chain: str) -> set[int]:
    """
    Return Vernier Kabat positions set for VH/VL from v44 config.
    Used for internal audit (CMC candidate filtering, etc.).
    """
    cfg = _cfg_v44()
    proto = cfg.get("framework_selection_protocol") if isinstance(cfg.get("framework_selection_protocol"), dict) else {}
    step = proto.get("step_2_3_vernier_score") if isinstance(proto.get("step_2_3_vernier_score"), dict) else {}
    tiers = step.get("tiers") if isinstance(step.get("tiers"), dict) else {}
    out: set[int] = set()
    for t in tiers.values():
        if not isinstance(t, dict):
            continue
        key = "positions_VH" if chain == "VH" else "positions_VL"
        for p in (t.get(key) or []):
            try:
                out.add(int(p))
            except Exception:
                continue
    return out


def _in_cdr_union_kabat(kabat_pos: int, chain: str, *, seq: str = "") -> bool:
    """
    Return True if a Kabat base position falls inside the **IMGT** CDR-union ranges (v44 config).

    Why this exists:
    - `config/vh_vl_humanization_v490.json` defines `cdr_union_ranges` in **IMGT** coordinates (e.g. 105–117).
    - Many internal audit artifacts (Phase4 logs / Vernier positions / KabatDict) are in **Kabat** integers.
    - Therefore: Kabat→IMGT mapping MUST be explicit. We do this via dual-scheme numbering aligned by seq_index.
    """
    kabat_pos = int(kabat_pos)
    seq = (seq or "").strip().upper()
    if not seq:
        # Conservative default: if we can't map, treat as protected.
        return True
    try:
        from core.numbering.dual_scheme import compute_dual_scheme_numbering  # noqa: PLC0415
    except Exception:
        return True

    # Build Kabat(base) → IMGT(pos) map for this sequence
    d = compute_dual_scheme_numbering(seq, chain_label=chain)
    kab_to_imgt: Dict[int, int] = {}
    for i in range(len(seq)):
        k = d.kabat[i]
        im = d.imgt[i]
        if k.ins == "" and int(k.pos) not in kab_to_imgt:
            kab_to_imgt[int(k.pos)] = int(im.pos)

    imgt_pos = kab_to_imgt.get(kabat_pos)
    if imgt_pos is None:
        # If a Kabat position doesn't exist in numbering, treat as protected (safer).
        return True

    cfg = _cfg_v44()
    unions = cfg.get("cdr_union_ranges") if isinstance(cfg.get("cdr_union_ranges"), dict) else {}
    ch = unions.get(chain) if isinstance(unions.get(chain), dict) else {}
    for k in ("CDR1_union", "CDR2_union", "CDR3_union"):
        span = ch.get(k)
        if isinstance(span, list) and len(span) == 2:
            try:
                lo, hi = int(span[0]), int(span[1])
                if lo <= int(imgt_pos) <= hi:
                    return True
            except Exception:
                continue
    return False


def _compute_pi_fab(vh: str, vl: str) -> Optional[float]:
    """Compute pI from concatenated VH+VL (Fab proxy), best-effort."""
    try:
        from Bio.SeqUtils.ProtParam import ProteinAnalysis  # type: ignore

        seq = (vh or "") + (vl or "")
        if not seq:
            return None
        return float(ProteinAnalysis(seq).isoelectric_point())
    except Exception:
        return None


def _load_json(path: Path) -> Dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def _write_text(path: Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8")


def _write_json(path: Path, payload: Dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with open(path, "w", encoding="utf-8") as f:
        json.dump(payload, f, indent=2, ensure_ascii=False)


def _eval_to_payload(result: Any) -> Dict[str, Any]:
    """
    Convert AbEvaluator.EvaluationResult to a JSON-serializable payload.
    (Mirrors core.evaluation.evaluator.EvaluationResult.save payload structure.)
    """
    if isinstance(result, dict):
        return result
    # duck-typing to avoid importing evaluator types at module import time
    ab_type = getattr(getattr(result, "ab_type", None), "value", None) or getattr(result, "ab_type", None) or "—"
    payload = {
        "abenginecore_version": "1.0.0",
        "project_name": getattr(result, "project_name", "—"),
        "ab_type": ab_type,
        "overall_status": getattr(result, "overall_status", "—"),
        "modules_run": getattr(result, "modules_run", []) or [],
        "overall_flags": getattr(result, "overall_flags", []) or [],
        "generated_at": getattr(result, "generated_at", ""),
        "results": getattr(result, "results", {}) or {},
    }
    return payload


def _extract_vernier_dual_numbering_len(eval_payload: Any) -> Optional[int]:
    """
    Best-effort extraction of vernier_dual_numbering length from an evaluation payload.
    Returns None if not present / malformed.
    """
    if not isinstance(eval_payload, dict):
        return None
    res = eval_payload.get("results") if isinstance(eval_payload.get("results"), dict) else {}
    s13 = res.get("structure_13param") if isinstance(res.get("structure_13param"), dict) else {}
    met = s13.get("metrics") if isinstance(s13.get("metrics"), dict) else {}
    vdn = met.get("vernier_dual_numbering")
    if isinstance(vdn, list):
        return len(vdn)
    return None


def _pdb_paths_match(p0: str, pdb_path: Path) -> bool:
    """
    Compare stored PDB path string against actual Path, tolerant to relative/absolute differences.
    Require either full resolve match or filename match.
    """
    p0 = str(p0 or "").strip()
    if not p0:
        return False
    try:
        if Path(p0).resolve() == pdb_path.resolve():
            return True
    except Exception:
        pass
    return Path(p0).name == pdb_path.name


def _can_reuse_structure_eval(results: Dict[str, Any], base_version: str, pdb_h: Path) -> bool:
    """
    Reuse existing evaluation payload if:
    - results._internal.evaluation_{base_version} exists
    - results.structure.{base_version}_pdb matches pdb_h (or filename matches)
    - evaluation contains vernier_dual_numbering with 22 rows

    This avoids recomputation while still enforcing the structural gate.
    """
    internal = results.get("_internal") if isinstance(results.get("_internal"), dict) else {}
    if not isinstance(internal, dict):
        return False
    ev = internal.get(f"evaluation_{base_version}")
    if _extract_vernier_dual_numbering_len(ev) != 22:
        return False

    struct = results.get("structure") if isinstance(results.get("structure"), dict) else {}
    if not isinstance(struct, dict):
        return False
    p0 = struct.get(f"{base_version}_pdb") or struct.get("v3_pdb") or struct.get("v2_pdb") or struct.get("v1_pdb")
    if not _pdb_paths_match(str(p0 or ""), pdb_h):
        return False

    return True


def _phase4_json_path(project_dir: Path, ab_id: str) -> Optional[Path]:
    candidates = [
        project_dir / "internal" / f"phase4_backmutation_{ab_id}.json",
        project_dir / "internal" / f"phase4_backmutation_{ab_id.lower()}.json",
        project_dir / "reports" / f"phase4_backmutation_{ab_id}.json",
        project_dir / "reports" / f"phase4_backmutation_{ab_id.lower()}.json",
        SUITE / f"phase4_backmutation_{ab_id}.json",
        SUITE / f"phase4_backmutation_{ab_id.lower()}.json",
    ]
    return next((p for p in candidates if p.exists()), None)


def _parse_chain_and_kabat_pos(position_label: str) -> Tuple[str, int]:
    """
    position label examples: "VH_71", "VL_98"
    Returns: ("VH"/"VL", kabat_pos)
    """
    p = str(position_label).strip()
    if p.startswith("VH_"):
        return ("VH", int(p.split("_", 1)[1]))
    if p.startswith("VL_"):
        return ("VL", int(p.split("_", 1)[1]))
    raise ValueError(f"Unrecognized vernier position label: {position_label!r}")


def _unify_phase4_rows(phase4: Dict[str, Any]) -> List[Dict[str, Any]]:
    """
    Normalize different historical schemas of phase4_backmutation_*.json to a common row format.

    Output row keys:
      position_label, chain, kabat_pos, decision, mouse_aa, human_aa, rule_hits, reasons,
      sasa, contact, dist_to_cdr, in_cdr_union, same_class
    """
    rows_in = phase4.get("backmutation_decisions") or []
    if not isinstance(rows_in, list):
        return []

    out: List[Dict[str, Any]] = []
    for r in rows_in:
        if not isinstance(r, dict):
            continue
        pos = r.get("position") or r.get("pos") or ""
        if not pos:
            continue
        try:
            chain, kabat_pos = _parse_chain_and_kabat_pos(str(pos))
        except Exception:
            # Some very old records might provide chain+imgt only; skip rather than guess.
            continue

        out.append({
            "position_label": str(pos),
            "chain": str(r.get("chain") or chain),
            "kabat_pos": int(r.get("kabat_pos") or kabat_pos),
            "decision": str(r.get("decision") or "—"),
            "mouse_aa": str(r.get("mouse_aa") or "—"),
            "human_aa": str(r.get("human_aa") or "—"),
            "rule_hits": r.get("rule_hits") if isinstance(r.get("rule_hits"), list) else [],
            "reasons": r.get("reasons") if isinstance(r.get("reasons"), list) else [],
            "sasa": r.get("sasa"),
            "contact": r.get("contact"),
            "dist_to_cdr": r.get("dist_to_cdr"),
            "in_cdr_union": bool(r.get("in_cdr_union")) if "in_cdr_union" in r else None,
            "same_class": bool(r.get("same_class")) if "same_class" in r else None,
        })
    return out


def _as_float(x: Any) -> Optional[float]:
    try:
        if x is None:
            return None
        return float(x)
    except Exception:
        return None


def _get_vernier_tier(chain: str, kabat_pos: int, cfg: Optional[Dict] = None) -> int:
    """
     V4.4  Vernier  tier：1=T1 ，2=T2，3=T3。
    ，。
    """
    tiers = _tier_positions_from_config(cfg)
    label = f"{str(chain).upper()}_{kabat_pos}"
    if label in tiers.get("T1", []):
        return 1
    if label in tiers.get("T2", []):
        return 2
    return 3


def _tier_positions_from_config(cfg: Optional[Dict] = None) -> Dict[str, List[str]]:
    """ V4.4  Vernier 。"""
    t1, t2, t3 = [], [], []
    if isinstance(cfg, dict):
        step = cfg.get("framework_selection_protocol", {}).get("step_2_3_vernier_score", {})
        for tier_name, spec in (step.get("tiers") or {}).items():
            for ch, poses in [("VH", spec.get("positions_VH", [])), ("VL", spec.get("positions_VL", []))]:
                for p in poses:
                    lb = f"{ch}_{p}"
                    if tier_name == "T1":
                        t1.append(lb)
                    elif tier_name == "T2":
                        t2.append(lb)
                    else:
                        t3.append(lb)
    if not t1:
        t1 = ["VH_71", "VL_71"]
    if not t2:
        t2 = ["VH_2", "VH_27", "VH_28", "VH_29", "VH_30", "VH_69", "VH_93", "VH_94", "VL_36", "VL_46"]
    return {"T1": t1, "T2": t2, "T3": t3}


def _score_vernier_candidate(row: Dict[str, Any], cfg: Optional[Dict] = None) -> float:
    """
     Vernier （）。
    ：（SASA/contact/dist_to_cdr）+ V4.4 Vernier tier + HC/SC 。
    """
    sasa = _as_float(row.get("sasa"))
    contact = _as_float(row.get("contact"))
    dist = _as_float(row.get("dist_to_cdr"))
    buried = 0.0 if sasa is None else max(0.0, min(1.0, (20.0 - sasa) / 20.0))
    packed = 0.0 if contact is None else max(0.0, min(1.0, contact / 35.0))
    near_cdr = 0.0 if dist is None else max(0.0, min(1.0, (4.5 - dist) / 4.5))
    rule_hits = row.get("rule_hits") or []
    reasons = row.get("reasons") or []
    rh = [str(x) for x in rule_hits] + [str(x) for x in reasons]
    hard = any(h in " ".join(rh) for h in ("HC4", "HC5", "HC6", "SC1", "SC2", "SC3", "SC4", "SC5"))
    missing = any("missing_residue" in x for x in rh)
    score = 0.40 * packed + 0.35 * buried + 0.25 * near_cdr
    if hard:
        score += 0.10
    if missing:
        score -= 0.20
    tier = _get_vernier_tier(row.get("chain", ""), int(row.get("kabat_pos") or 0), cfg)
    if tier == 1:
        score += 0.15
    elif tier == 2:
        score += 0.08
    return float(score)


def _diagnose_failure_type(delta: Dict[str, Any]) -> str:
    """
    S2: Structural diagnosis from delta. Returns ANGLE | CDR_RMSD | INTERFACE | MULTI.
    Deterministic, rule-based.
    """
    if not isinstance(delta, dict) or not delta:
        return "MULTI"
    angle_pass = delta.get("angle_pass") is True
    rmsd_pass = delta.get("cdr_rmsd_pass") is True
    ang = (delta.get("vh_vl_angle") or {}) if isinstance(delta.get("vh_vl_angle"), dict) else {}
    angle_delta = _as_float(ang.get("delta"))
    angle_fail = not angle_pass or (angle_delta is not None and angle_delta > 3.0)
    rmsd_fail = not rmsd_pass
    if angle_fail and rmsd_fail:
        return "MULTI"
    if angle_fail:
        return "ANGLE"
    if rmsd_fail:
        return "CDR_RMSD"
    return "MULTI"


def _position_label_to_chain_pos(label: str) -> Tuple[str, int]:
    """Parse 'VH_71' -> ('VH', 71)."""
    s = str(label or "").strip()
    if "_" in s:
        chain, pos_s = s.split("_", 1)
        try:
            return (chain.strip().upper(), int(pos_s.strip()))
        except ValueError:
            pass
    return ("", 0)


def _vernier_hc_gate(row: Dict[str, Any], mouse_aa: str) -> bool:
    """
    S3: HC gate. Returns True if position should be EXCLUDED from Round 2 mutation.
    Exclude: HC1 mouse G/P (backbone constraints - we restore mouse, but avoid destabilizing),
    HC2 Cys (disulfide), or missing/invalid data.
    Note: HC4/HC5 say KEEP_MOUSE = we WANT to back-mutate, so they do NOT exclude.
    """
    if not mouse_aa or len(mouse_aa) != 1:
        return True
    # HC1: mouse G or P - industry practice: avoid mutating to G/P if it changes backbone; 
    # actually we're reverting TO mouse, so G/P is the target. Allow.
    # HC2: Cys in Vernier is rare; exclude to be safe (disulfide uncertainty)
    if mouse_aa == "C":
        return True
    # Skip if human_aa is '-' (missing germline)
    human_aa = str(row.get("human_aa") or "").strip()
    if human_aa == "-" and not row.get("mouse_aa"):
        return True
    return False


def _priority_groups_by_failure_type(
    failure_type: str, candidates: List[Dict[str, Any]], cfg: Dict[str, Any]
) -> List[List[Dict[str, Any]]]:
    """
    S4: （）。 V4.4 backmutation_rules、vernier_ml_report、SC/ coupling_table。
    """
    coupling = cfg.get("backmutation_rules", {}).get("coupling_table") or []
    soft = cfg.get("backmutation_rules", {}).get("soft_constraints") or []

    # Build position label -> candidate map
    by_label: Dict[str, Dict[str, Any]] = {}
    for c in candidates:
        ch = str(c.get("chain") or "").upper()
        kp = int(c.get("kabat_pos") or 0)
        if ch and kp:
            by_label[f"{ch}_{kp}"] = c

    def _append_from_labels(labels: List[str]) -> List[Dict[str, Any]]:
        out = []
        for lb in labels:
            c = by_label.get(lb)
            if c and c not in out:
                out.append(c)
        return out

    # SC1 angle interface: VH_71, VH_94, VL_49（vernier_ml_report: ）
    angle_labels = ["VH_71", "VH_94", "VL_49"]
    # Coupling (V4.4): VH_71->VH_73,VH_78; VH_94->VH_93,VL_4
    angle_group1 = _append_from_labels(angle_labels)
    angle_group2 = _append_from_labels(["VH_73", "VH_78", "VH_93", "VL_4"])

    # INTERFACE (458): VH48, VH49, VL36, VL_49
    interface_labels = ["VH_48", "VH_49", "VL_36", "VL_49"]
    interface_group = _append_from_labels(interface_labels)

    # CDR_RMSD:  — dist_to_cdr （ CDR ）， tier+score
    cdr_sorted = sorted(
        [c for c in candidates],
        key=lambda x: (
            float(x.get("dist_to_cdr")) if x.get("dist_to_cdr") is not None else 999.0,
            _get_vernier_tier(str(x.get("chain") or ""), int(x.get("kabat_pos") or 0), cfg),
            -float(x.get("score") or 0.0),
        ),
    )

    def _sort_rest_by_tier_score(lst: List[Dict]) -> None:
        lst.sort(key=lambda x: (_get_vernier_tier(str(x.get("chain") or ""), int(x.get("kabat_pos") or 0), cfg), -float(x.get("score") or 0.0)))

    if failure_type == "ANGLE":
        groups = [angle_group1, angle_group2]
        used = set(id(x) for g in groups for x in g)
        rest = [c for c in candidates if id(c) not in used]
        if rest:
            _sort_rest_by_tier_score(rest)
            groups.append(rest)
        return groups
    if failure_type == "CDR_RMSD":
        return [cdr_sorted]
    if failure_type == "INTERFACE":
        groups = [interface_group]
        used = set(id(x) for x in interface_group)
        rest = [c for c in candidates if id(c) not in used]
        if rest:
            _sort_rest_by_tier_score(rest)
            groups.append(rest)
        return groups
    # MULTI: ANGLE ， CDR +tier 
    groups = [angle_group1, angle_group2]
    used = set(id(x) for g in groups for x in g)
    rest = [c for c in cdr_sorted if id(c) not in used]
    if rest:
        groups.append(rest)
    return groups


def _find_version_pdb(project_dir: Path, ab_id: str, version: str) -> Optional[Path]:
    """
    Find a PDB for given version: 'mouse', 'v1', 'v2', 'v3'.
    """
    if version == "mouse":
        return _find_best_pdb(project_dir, ab_id, "mouse")
    if version in ("v1", "v2", "v3"):
        p = project_dir / "structures" / f"{ab_id}_humanized_{version}.pdb"
        if p.exists():
            return p
        # fallback patterns
        pats = [
            f"*{ab_id}*humanized*{version}*.pdb",
            f"*{ab_id}*{version}*humanized*.pdb",
        ]
        for pat in pats:
            m = list(project_dir.rglob(pat))
            if m:
                return m[0]
    return None


def _predict_humanized_pdb(vh_seq: str, vl_seq: str, out_pdb: Path) -> None:
    from ImmuneBuilder import ABodyBuilder2  # type: ignore  # noqa: PLC0415

    predictor = ABodyBuilder2()
    ab = predictor.predict({"H": vh_seq, "L": vl_seq})
    out_pdb.parent.mkdir(parents=True, exist_ok=True)
    ab.save(str(out_pdb))


def _eval_delta_vs_mouse(
    project_name: str,
    pdb_path: Path,
    ref_pdb_path: Path,
    vh_seq: str,
    vl_seq: str,
) -> Dict[str, Any]:
    from core.evaluation.evaluator import AbEvaluator, AntibodyType  # noqa: PLC0415

    ev = AbEvaluator(
        project_name=project_name,
        pdb_path=str(pdb_path),
        ref_pdb_path=str(ref_pdb_path),
        vh_chain="H",
        vl_chain="L",
        vh_seq=vh_seq,
        vl_seq=vl_seq,
        ab_type=AntibodyType.HUMANIZED,
        strict_qa=False,
    )
    r = ev.run(modules=["structure_13param", "delta_vs_mouse"])
    return _eval_to_payload(r)


def _round2_vernier_rescue(
    ab_id: str,
    project_dir: Path,
    results: Dict[str, Any],
    base_version: str,
    max_steps: int = 4,
    max_rounds: int = 3,
    max_per_round: int = 3,
) -> Tuple[Optional[Dict[str, Any]], List[str]]:
    """
    Vernier Round 2 rescue — S1–S7 （）。

    ：V4.4 backmutation_rules、vernier_ml_report、coupling_table、SASA/contact/dist_to_cdr 。
    ：failure_type → （SC1  / CDR  / ）→ Vernier tier → 。

    S1:  config (HC/SC, coupling_table)。
    S2:  → failure_type (ANGLE | CDR_RMSD | INTERFACE | MULTI)。
    S3: HC gate （Cys ）。
    S4:  failure_type  SC  tier 。
    S5:  (max_per_round)。
    S6:  + 。
    S7: ； PASS ； FAIL  round < max_rounds，。

    Returns: (payload_or_None, notes)
    """
    notes: List[str] = []

    # S1: Load config
    cfg = _cfg_v44()
    if not cfg:
        notes.append("vernier_round2:skip:no_v44_config")
        return (None, notes)

    internal = results.get("_internal") or {}
    ev_key = f"evaluation_{base_version}"
    ev0 = internal.get(ev_key) if isinstance(internal, dict) else None
    d0 = _audit_extract_delta(ev0)
    if _delta_pass(d0):
        notes.append("vernier_round2:skip:base_delta_pass")
        return (None, notes)

    seqs = results.get("sequences") or {}
    mouse_vh = str(seqs.get("mouse_VH") or "")
    mouse_vl = str(seqs.get("mouse_VL") or "")
    base_vh = str(seqs.get(f"{base_version}_VH") or "")
    base_vl = str(seqs.get(f"{base_version}_VL") or "")
    if not (mouse_vh and mouse_vl and base_vh and base_vl):
        notes.append("vernier_round2:skip:missing_sequences")
        return (None, notes)

    pdb_mouse = _find_version_pdb(project_dir, ab_id, "mouse")
    pdb_base = _find_version_pdb(project_dir, ab_id, base_version)
    if pdb_mouse is None or pdb_base is None:
        notes.append(f"vernier_round2:skip:missing_pdbs mouse={pdb_mouse} base={pdb_base}")
        return (None, notes)

    p4_path = _phase4_json_path(project_dir, ab_id)
    if p4_path is None:
        notes.append("vernier_round2:skip:missing_phase4_json")
        return (None, notes)

    phase4 = _load_json(p4_path)
    rows = _unify_phase4_rows(phase4)
    if not rows:
        notes.append("vernier_round2:skip:empty_phase4_rows")
        return (None, notes)

    from core.humanization.kabat_utils import get_kabat_numbering  # noqa: PLC0415
    kd_mouse_vh = get_kabat_numbering(mouse_vh)
    kd_mouse_vl = get_kabat_numbering(mouse_vl)
    if not (kd_mouse_vh and kd_mouse_vl):
        notes.append("vernier_round2:skip:kabat_numbering_failed")
        return (None, notes)

    try:
        from ImmuneBuilder import ABodyBuilder2  # noqa: F401  # type: ignore
    except Exception as e:
        notes.append(f"vernier_round2:skip:ImmuneBuilder_missing:{e}")
        return (None, notes)

    # Build candidate list (mouse != current, not CDR union). Uses cur_vh/cur_vl as "base" each round.
    def _candidates_from_rows(cur_vh_seq: str, cur_vl_seq: str) -> List[Dict[str, Any]]:
        kd_b_vh = get_kabat_numbering(cur_vh_seq)
        kd_b_vl = get_kabat_numbering(cur_vl_seq)
        if not (kd_b_vh and kd_b_vl):
            return []
        out = []
        for r in rows:
            chain = str(r.get("chain") or "").upper()
            kabat_pos = int(r.get("kabat_pos") or 0)
            if kabat_pos <= 0 or chain not in ("VH", "VL"):
                continue
            if r.get("decision") == "CDR_GRAFT" or r.get("in_cdr_union") is True:
                continue
            kd_m = kd_mouse_vh if chain == "VH" else kd_mouse_vl
            kd_b = kd_b_vh if chain == "VH" else kd_b_vl
            m = kd_m.get((kabat_pos, ""))
            b = kd_b.get((kabat_pos, ""))
            if not m or not b or str(m) == str(b):
                continue
            r2 = {**r, "chain": chain, "kabat_pos": kabat_pos}
            r2["position_label"] = r2.get("position_label") or f"{chain}_{kabat_pos}"
            r2["mouse_aa_seq"] = str(m)
            r2["base_aa_seq"] = str(b)
            r2["score"] = _score_vernier_candidate(r2, cfg)
            if not _vernier_hc_gate(r2, str(m)):
                out.append(r2)
        return out

    all_candidates = _candidates_from_rows(base_vh, base_vl)
    if not all_candidates:
        notes.append("vernier_round2:skip:no_candidates_after_hc_gate")
        return (None, notes)
    notes.append(f"vernier_round2:candidates={len(all_candidates)}")

    cur_vh, cur_vl = base_vh, base_vl
    applied: List[Dict[str, Any]] = []
    attempts: List[Dict[str, Any]] = []
    step = 0
    last_round = 0
    current_delta = d0
    failure_type = _diagnose_failure_type(current_delta)
    notes.append(f"vernier_round2:diagnosis={failure_type}")

    for round_idx in range(max_rounds):
        last_round = round_idx + 1
        # Refresh candidates (current sequence may have changed from prior round)
        candidates = _candidates_from_rows(cur_vh, cur_vl)
        if not candidates:
            break

        # S4: Priority groups by failure_type
        priority_groups = _priority_groups_by_failure_type(failure_type, candidates, cfg)

        # S5: Build batch (max_per_round)
        batch: List[Dict[str, Any]] = []
        seen_key: set = set()
        for group in priority_groups:
            for c in group:
                key = (c.get("chain"), c.get("kabat_pos"))
                if key in seen_key:
                    continue
                seen_key.add(key)
                batch.append(c)
                if len(batch) >= max_per_round:
                    break
            if len(batch) >= max_per_round:
                break

        if not batch:
            notes.append(f"vernier_round2:round{round_idx+1}:no_batch")
            break

        # Apply batch mutations (accumulate)
        for cand in batch:
            chain = str(cand.get("chain"))
            kabat_pos = int(cand.get("kabat_pos"))
            mouse_aa = str(cand.get("mouse_aa_seq"))
            try:
                if chain == "VH":
                    cur_vh = _kabat_mutate_base(cur_vh, kabat_pos, mouse_aa)
                else:
                    cur_vl = _kabat_mutate_base(cur_vl, kabat_pos, mouse_aa)
                step += 1
                applied.append({
                    "step": step,
                    "position": cand.get("position_label"),
                    "chain": chain,
                    "kabat_pos": kabat_pos,
                    "from": cand.get("base_aa_seq"),
                    "to": mouse_aa,
                    "score": float(cand.get("score") or 0.0),
                    "sasa": cand.get("sasa"),
                    "contact": cand.get("contact"),
                    "dist_to_cdr": cand.get("dist_to_cdr"),
                    "rule_hits": cand.get("rule_hits") or [],
                    "reasons": cand.get("reasons") or [],
                    "failure_type": failure_type,
                    "round": round_idx + 1,
                })
            except Exception as e:
                notes.append(f"vernier_round2:step{step}:mutate_failed:{e}")
                continue

        if step > max_steps:
            notes.append(f"vernier_round2:max_steps_reached:{max_steps}")
            break

        out_pdb = project_dir / "structures" / f"{ab_id}_humanized_{base_version}_vernier_round2_step{step}.pdb"
        try:
            _predict_humanized_pdb(cur_vh, cur_vl, out_pdb)
        except Exception as e:
            notes.append(f"vernier_round2:step{step}:predict_failed:{e}")
            break

        try:
            payload = _eval_delta_vs_mouse(
                project_name=f"{ab_id}_{base_version}_vernier_round2_step{step}",
                pdb_path=out_pdb,
                ref_pdb_path=pdb_mouse,
                vh_seq=cur_vh,
                vl_seq=cur_vl,
            )
            current_delta = _audit_extract_delta(payload)
            attempts.append({
                "step": step,
                "round": round_idx + 1,
                "pdb": str(out_pdb),
                "applied": list(applied),
                "delta": current_delta,
                "pass": _delta_pass(current_delta),
                "overall_status": payload.get("overall_status"),
                "failure_type": failure_type,
            })
            if _delta_pass(current_delta):
                payload.setdefault("_internal_note", {})
                if isinstance(payload["_internal_note"], dict):
                    payload["_internal_note"]["vernier_round2"] = {
                        "base_version": base_version,
                        "trigger": f"{base_version}_delta_fail",
                        "phase4_source": str(p4_path),
                        "max_steps": max_steps,
                        "max_rounds": max_rounds,
                        "max_per_round": max_per_round,
                        "chosen_steps": step,
                        "chosen_rounds": round_idx + 1,
                        "failure_type": failure_type,
                        "flow": "S1-S7_unified",
                        "applied": list(applied),
                        "attempts": attempts,
                        "pdb_mouse": str(pdb_mouse),
                        "pdb_base": str(pdb_base),
                    }
                notes.append(f"vernier_round2:success:step{step}_round{round_idx+1}")
                return (payload, notes)
            # S7: Re-diagnose for next round
            failure_type = _diagnose_failure_type(current_delta)
            notes.append(f"vernier_round2:round{round_idx+1}:retry diagnosis={failure_type}")
        except Exception as e:
            notes.append(f"vernier_round2:step{step}:eval_failed:{e}")
            break

    notes.append("vernier_round2:exhausted:no_pass")
    if attempts:
        last = attempts[-1]
        payload = {
            "project_name": f"{ab_id}_{base_version}_vernier_round2_exhausted",
            "overall_status": "FAIL",
            "results": {"delta_vs_mouse": {"delta": last.get("delta")}},
            "_internal_note": {
                "vernier_round2": {
                    "base_version": base_version,
                    "trigger": f"{base_version}_delta_fail",
                    "phase4_source": str(p4_path),
                    "max_steps": max_steps,
                    "max_rounds": max_rounds,
                    "chosen_steps": len(applied),
                    "chosen_rounds": last_round,
                    "failure_type": failure_type,
                    "flow": "S1-S7_unified",
                    "applied": list(applied),
                    "attempts": attempts,
                    "pdb_mouse": str(pdb_mouse),
                    "pdb_base": str(pdb_base),
                    "note": "no attempt achieved PASS at gate level",
                }
            },
        }
        return (payload, notes)
    return (None, notes)


def _summarize_rule_hits(rule_hits: Any) -> str:
    if not isinstance(rule_hits, list):
        return "—"
    hits = [str(x) for x in rule_hits if str(x).strip()]
    return ", ".join(hits) if hits else "—"


def _render_phase4_md(phase4: Dict[str, Any], results: Optional[Dict[str, Any]] = None) -> str:
    rows = phase4.get("backmutation_decisions") or []
    if not isinstance(rows, list):
        rows = []

    def _chain(pos: str) -> str:
        return pos.split("_", 1)[0] if "_" in pos else "—"

    # counts
    counts: Dict[str, int] = {}
    for r in rows:
        if isinstance(r, dict):
            d = str(r.get("decision") or "—")
            counts[d] = counts.get(d, 0) + 1

    out: List[str] = []
    out.append(f"# Phase 4 Vernier （{phase4.get('antibody','—')}）")
    out.append("")
    out.append(f"- checklist: `{phase4.get('checklist_version','—')}`")
    out.append(f"- phase: `{phase4.get('phase','—')}`")
    out.append(f"- VH : `{phase4.get('recommended_vh','—')}` | VL : `{phase4.get('recommended_vk','—')}`")
    out.append(f"- （Back-mutation）: VH={phase4.get('bm_vh_count','—')} | VL={phase4.get('bm_vl_count','—')}")
    out.append("")
    out.append("## ")
    out.append("")
    out.append("| decision | count |")
    out.append("|---|---:|")
    for k in sorted(counts.keys()):
        out.append(f"| `{k}` | {counts[k]} |")
    out.append("")
    out.append("## 22 ")
    out.append("")
    out.append("> ：， rule_hits /，。")
    out.append("")
    # Optional: show the actually assembled AA in FINAL humanized sequence (includes J/FR4),
    # to avoid confusion when germline V-gene reference doesn't cover FR4 (e.g. Kabat 98 in VL).
    final_v = "—"
    seqs: Dict[str, Any] = {}
    if isinstance(results, dict):
        meta = results.get("_meta") or {}
        final_v = str((meta.get("final_version") or "—")).strip() or "—"
        seqs = results.get("sequences") or {}

    kd_vh = None
    kd_vl = None
    try:
        if isinstance(seqs, dict) and final_v not in ("—", ""):
            from core.humanization.kabat_utils import get_kabat_numbering  # type: ignore
            vh_seq = str(seqs.get(f"{final_v}_VH") or "")
            vl_seq = str(seqs.get(f"{final_v}_VL") or "")
            kd_vh = get_kabat_numbering(vh_seq) if vh_seq else None
            kd_vl = get_kabat_numbering(vl_seq) if vl_seq else None
    except Exception:
        kd_vh = None
        kd_vl = None

    out.append("| # |  |  | Kabat | IMGT | AA | AA(V) | AA() |  | （） | rule_hits | SASA | contact | same_class |")
    out.append("|---:|---|---|---:|---:|---|---|---|---|---|---|---:|---:|---|")

    def _reason(r: Dict[str, Any]) -> str:
        dec = str(r.get("decision") or "—")
        mouse = str(r.get("mouse_aa") or "—")
        human = str(r.get("human_aa") or "—")
        hits_raw = r.get("rule_hits")
        hits = set(str(x) for x in hits_raw) if isinstance(hits_raw, list) else set()
        sasa = float(r.get("sasa") or 0.0)
        contact = float(r.get("contact") or 0.0)

        if dec == "CDR_GRAFT" or bool(r.get("in_cdr_union")):
            return "CDR ：（ Vernier ）"
        if "MATCH" in hits or (mouse == human and mouse not in ("—", "-", "")):
            return "/（MATCH）："
        if "missing_residue" in hits:
            return " V （ J/FR4）； V ，"

        exposed = sasa >= 30.0
        buried = sasa <= 5.0
        high_contact = contact >= 20.0

        if dec == "BACK_MUTATE":
            if buried or high_contact:
                return "/："
            return "："

        if dec == "HUMAN":
            if exposed and contact < 15.0:
                return "：（）"
            if "ACCEPT_HUMAN_no_hard_hits" in hits:
                return "：（）"
            return "（）"

        return "—"
    for i, r in enumerate(rows, start=1):
        if not isinstance(r, dict):
            continue
        pos = str(r.get("position") or "—")
        chain = _chain(pos)
        kabat_pos = r.get("kabat_pos")
        try:
            kabat_i = int(kabat_pos)
        except Exception:
            kabat_i = None

        final_aa = "—"
        try:
            if kabat_i is not None:
                if chain == "VH" and isinstance(kd_vh, dict):
                    final_aa = str(kd_vh.get((kabat_i, ""), "—"))
                if chain == "VL" and isinstance(kd_vl, dict):
                    final_aa = str(kd_vl.get((kabat_i, ""), "—"))
        except Exception:
            final_aa = "—"

        out.append(
            "| {i} | {chain} | `{pos}` | {kabat} | {imgt} | `{m}` | `{h}` | `{fa}` | `{dec}` | {reason} | {hits} | {sasa:.2f} | {contact:.0f} | {sc} |".format(
                i=i,
                chain=chain,
                pos=pos,
                kabat=int(r.get("kabat_pos") or 0) if str(r.get("kabat_pos") or "").isdigit() else "—",
                imgt=int(r.get("imgt_pos") or 0) if str(r.get("imgt_pos") or "").isdigit() else "—",
                m=str(r.get("mouse_aa") or "—"),
                h=str(r.get("human_aa") or "—"),
                fa=final_aa,
                dec=str(r.get("decision") or "—"),
                reason=_reason(r),
                hits=f"`{_summarize_rule_hits(r.get('rule_hits'))}`",
                sasa=float(r.get("sasa") or 0.0),
                contact=float(r.get("contact") or 0.0),
                sc="True" if bool(r.get("same_class")) else "False",
            )
        )

    out.append("")
    out.append("## （）")
    out.append("")
    out.append("- `decision=CDR_GRAFT`： CDR ，（ Vernier ）。")
    out.append("- `decision=BACK_MUTATE`：，。")
    out.append("- `decision=HUMAN`：（/ MATCH ）。")
    return "\n".join(out) + "\n"


def _audit_extract_delta(ev_payload: Any) -> Dict[str, Any]:
    if not isinstance(ev_payload, dict):
        return {}
    r = ev_payload.get("results") or {}
    if not isinstance(r, dict):
        return {}
    dvm = r.get("delta_vs_mouse") or {}
    if not isinstance(dvm, dict):
        return {}
    d = dvm.get("delta") or {}
    return d if isinstance(d, dict) else {}


def _audit_extract_dev(ev_payload: Any) -> Dict[str, Any]:
    if not isinstance(ev_payload, dict):
        return {}
    r = ev_payload.get("results") or {}
    if not isinstance(r, dict):
        return {}
    dev = r.get("developability") or {}
    return dev if isinstance(dev, dict) else {}


def _audit_extract_imm(ev_payload: Any) -> Dict[str, Any]:
    if not isinstance(ev_payload, dict):
        return {}
    r = ev_payload.get("results") or {}
    if not isinstance(r, dict):
        return {}
    imm = r.get("immunogenicity") or {}
    return imm if isinstance(imm, dict) else {}


def _build_annotation_from_sequence(seq: str, chain: str, fr_source: str) -> List[Dict[str, Any]]:
    """ Kabat  annotation 。 sequence_annotation  sequences 。"""
    if not seq:
        return []
    try:
        from core.humanization.kabat_utils import get_kabat_numbering, sorted_keys  # noqa: PLC0415
    except Exception:
        return []
    kd = get_kabat_numbering(seq)
    if not kd:
        return []

    def span(lo: int, hi: int) -> str:
        return "".join(kd[k] for k in sorted_keys(kd) if lo <= k[0] <= hi)

    if chain == "VH":
        ranges = [("FR1", 1, 25), ("CDR1", 26, 35), ("FR2", 36, 49), ("CDR2", 50, 65), ("FR3", 66, 94), ("CDR3", 95, 102)]
        fr4_lo, fr4_hi = 103, max(k[0] for k in kd.keys()) if kd else 103
    else:
        ranges = [("FR1", 1, 23), ("CDR1", 24, 34), ("FR2", 35, 49), ("CDR2", 50, 56), ("FR3", 57, 88), ("CDR3", 89, 97)]
        fr4_lo, fr4_hi = 98, max(k[0] for k in kd.keys()) if kd else 98

    rows: List[Dict[str, Any]] = []
    for name, lo, hi in ranges:
        src = "** CDR**" if name.startswith("CDR") else fr_source
        rows.append({"region": name, "kabat": f"{lo}-{hi}", "seq": span(lo, hi), "source": src})
    rows.append({"region": "FR4", "kabat": f"{fr4_lo}-{fr4_hi}", "seq": span(fr4_lo, fr4_hi), "source": fr_source})
    return rows


def _reconcile_v2_sequence(results: Dict[str, Any]) -> bool:
    """
    ： mutations.v1_to_v2  sequences.v2 「v1 + v1_to_v2」，
     v1  v1_to_v2  v2， v2 = v1  Round 2 。

     True 。
    """
    muts = results.get("mutations") or {}
    v1_to_v2 = muts.get("v1_to_v2") or []
    if not v1_to_v2 or not isinstance(v1_to_v2, list):
        return False

    seqs = results.get("sequences") or {}
    v1_vh = str(seqs.get("v1_VH") or "")
    v1_vl = str(seqs.get("v1_VL") or "")
    v2_vh_cur = str(seqs.get("v2_VH") or "")
    v2_vl_cur = str(seqs.get("v2_VL") or "")
    if not v1_vh or not v1_vl:
        return False

    try:
        from core.humanization.kabat_utils import get_kabat_numbering, sorted_keys  # noqa: PLC0415
    except Exception:
        return False

    def _apply_muts(seq: str, chain: str) -> str:
        kd = get_kabat_numbering(seq)
        if not kd:
            return seq
        changed = False
        for m in v1_to_v2:
            if str(m.get("chain") or "").upper() != chain:
                continue
            pos = m.get("kabat_pos")
            to_aa = m.get("to")
            if pos is None or not to_aa:
                continue
            key = (int(pos), "")
            if key in kd:
                kd = dict(kd)
                kd[key] = str(to_aa)
                changed = True
        if not changed:
            return seq
        return "".join(kd[k] for k in sorted_keys(kd))

    v2_vh_new = _apply_muts(v1_vh, "VH")
    v2_vl_new = _apply_muts(v1_vl, "VL")
    if v2_vh_new == v2_vh_cur and v2_vl_new == v2_vl_cur:
        return False

    results.setdefault("sequences", {})
    if isinstance(results["sequences"], dict):
        results["sequences"]["v2_VH"] = v2_vh_new
        results["sequences"]["v2_VL"] = v2_vl_new
        #  v2_to_v3 ，v3  v2； v3  v3 = v1 
        v2_to_v3 = (muts.get("v2_to_v3") or [])
        if not v2_to_v3:
            results["sequences"]["v3_VH"] = v2_vh_new
            results["sequences"]["v3_VL"] = v2_vl_new
    return True


def _reconcile_sequence_annotation(results: Dict[str, Any]) -> None:
    """
    ： sequences  SSOT， sequence_annotation  sequences ，
     Kabat  sequence_annotation， CDR 。
     results 。
    """
    seqs = results.get("sequences") or {}
    meta = results.get("_meta") or {}
    final_v = str(meta.get("final_version") or "v3").strip() or "v3"
    vh_ssot = seqs.get("vernier_round2_VH") or seqs.get(f"{final_v}_VH") or seqs.get("v3_VH", "")
    vl_ssot = seqs.get("vernier_round2_VL") or seqs.get(f"{final_v}_VL") or seqs.get("v3_VL", "")
    if not vh_ssot or not vl_ssot:
        return

    ann = results.get("sequence_annotation") or {}
    vh_ann = ann.get("VH") or {}
    vl_ann = ann.get("VL") or {}
    need_update = False
    if vh_ann.get("sequence") != vh_ssot:
        need_update = True
    if vl_ann.get("sequence") != vl_ssot:
        need_update = True
    if not need_update:
        return

    vh_rows = _build_annotation_from_sequence(vh_ssot, "VH", "（ pI ）")
    vl_rows = _build_annotation_from_sequence(vl_ssot, "VL", "")
    vh_cdr = {r["region"]: len(r["seq"]) for r in vh_rows if r["region"].startswith("CDR")}
    vl_cdr = {r["region"]: len(r["seq"]) for r in vl_rows if r["region"].startswith("CDR")}
    results["sequence_annotation"] = {
        "_note": "Kabat  FR/CDR ，。 verify  sequences 。",
        "numbering_scheme": "Kabat",
        "VH": {
            "sequence": vh_ssot,
            "annotation": vh_rows,
            "cdr_lengths": vh_cdr,
        },
        "VL": {
            "sequence": vl_ssot,
            "annotation": vl_rows,
            "cdr_lengths": vl_cdr,
        },
    }


def _delta_pass(d: Dict[str, Any]) -> bool:
    """Structural fidelity pass criteria used for auto-rescue decisions."""
    if not isinstance(d, dict) or not d:
        return False
    return (
        d.get("cdr_rmsd_pass") is True
        and d.get("angle_pass") is True
        and d.get("canonical_match_h1_h2_l1") is True
    )


def _run_cmc_liability_design_if_needed(
    ab_id: str,
    project_dir: Path,
    results: Dict[str, Any],
    results_path: Path,
    fr_only: bool = True,
) -> Tuple[Dict[str, Any], List[str]]:
    """
    Run CMC liability design (N-gly, deamidation, etc.) if enabled.
    """
    notes: List[str] = []
    
    # Check if we have liabilities
    dev = results.get("developability") or {}
    liabilities = dev.get("liabilities") or []
    
    # Filter for actionable types in FR
    # We only care if there are liabilities that design_v3_liabilities can handle
    actionable_types = {"N-glycosylation", "deamidation", "isomerization"}
    has_actionable = False
    for item in liabilities:
        if item.get("type") in actionable_types:
            has_actionable = True
            break
            
    if not has_actionable:
        notes.append("cmc_liability_design:skip:no_actionable_liabilities")
        return results, notes

    # Load sequences (v3 might have been updated by pI design)
    seqs = results.get("sequences") or {}
    v3_vh = seqs.get("v3_VH")
    v3_vl = seqs.get("v3_VL")
    mouse_vh = seqs.get("mouse_VH")
    mouse_vl = seqs.get("mouse_VL")
    
    if not v3_vh or not v3_vl or not mouse_vh or not mouse_vl:
        notes.append("cmc_liability_design:skip:missing_sequences")
        return results, notes

    # Need mouse Kabat for CDR preservation check
    try:
        from core.humanization.kabat_utils import get_kabat_numbering  # noqa: PLC0415
        mouse_vh_kd = get_kabat_numbering(mouse_vh)
        mouse_vl_kd = get_kabat_numbering(mouse_vl)
    except Exception as e:
        notes.append(f"cmc_liability_design:skip:kabat_error:{e}")
        return results, notes

    # Run design
    try:
        from core.cmc.cmc_design import design_v3_liabilities  # noqa: PLC0415
        
        new_vh, new_vl, new_muts = design_v3_liabilities(
            v2_vh=v3_vh,
            v2_vl=v3_vl,
            mouse_vh_kd=mouse_vh_kd,
            mouse_vl_kd=mouse_vl_kd,
            liabilities=liabilities,
            fr_only=fr_only,
        )
        
        if not new_muts:
            notes.append("cmc_liability_design:no_safe_mutations_found")
            return results, notes
            
        # Update results
        results["sequences"]["v3_VH"] = new_vh
        results["sequences"]["v3_VL"] = new_vl
        
        # Append mutations
        results.setdefault("mutations", {})
        results["mutations"].setdefault("v2_to_v3", [])
        results["mutations"]["v2_to_v3"].extend(new_muts)
        
        # Write back to SSOT
        _write_json(results_path, results)
        notes.append(f"cmc_liability_design:applied_{len(new_muts)}_mutations")
        
        # Re-eval v3
        from core.evaluation.evaluator import AbEvaluator, AntibodyType  # noqa: PLC0415
        ev = AbEvaluator(
            project_name=ab_id,
            ab_type=AntibodyType.HUMANIZED,
            vh_seq=new_vh,
            vl_seq=new_vl,
            strict_qa=False
        )
        # Run modules
        modules = ["cdr_scan", "developability", "immunogenicity", "germline"]
        res_v3 = ev.run(modules=modules)
        
        # Update developability block
        dev = results.get("developability") or {}
        
        # Update pI
        pi_block = dev.get("pI") or {}
        # The evaluator returns pI in developability.pI (float)
        # But verify structure expects pI block with v1/v2/v3 keys
        # We need to extract pI from res_v3
        new_pi = (res_v3.results.get("developability") or {}).get("pI")
        pi_block["v3"] = new_pi
        
        # Check pass
        if new_pi is not None:
            pi_block["v3_pass"] = 5.5 <= float(new_pi) <= 8.5
        dev["pI"] = pi_block
        
        # Update metrics
        dev["metrics_final"] = (res_v3.results.get("developability") or {}).get("metrics")
        
        # Update liabilities
        # Note: new liabilities list might be smaller!
        dev["liabilities"] = (res_v3.results.get("cdr_scan") or {}).get("liabilities") or []
        
        # Update immunogenicity
        results["immunogenicity"] = res_v3.results.get("immunogenicity") or {}
        
        results["developability"] = dev
        _write_json(results_path, results)
        notes.append("cmc_liability_design:re_evaluated_v3")

    except Exception as e:
        notes.append(f"cmc_liability_design:error:{e}")
        import traceback
        traceback.print_exc()
        
    return results, notes


def _run_cmc_design_if_needed(
    ab_id: str,
    project_dir: Path,
    results: Dict[str, Any],
    results_path: Path,
    *,
    target_pi_max: float = 8.5,
    use_iedb: bool = False,
) -> Tuple[Dict[str, Any], List[str]]:
    """
    When final version pI > 8.5, design v3 via FR-only pI-lowering mutations.
    Runs full evaluation (developability + immunogenicity) for v3.
    Returns: (updated_results, notes)
    """
    notes: List[str] = []
    meta = results.get("_meta") or {}
    final_v = str(meta.get("final_version") or "").strip() or "v2"
    seqs = results.get("sequences") or {}

    # Current final version pI
    dev_top = results.get("developability") or {}
    pi_block = dev_top.get("pI") if isinstance(dev_top.get("pI"), dict) else {}
    pi_val = pi_block.get(final_v) if isinstance(pi_block, dict) else None
    if pi_val is None:
        # Recompute from sequences
        vh = str(seqs.get(f"{final_v}_VH") or seqs.get("v3_VH") or "")
        vl = str(seqs.get(f"{final_v}_VL") or seqs.get("v3_VL") or "")
        if vh and vl:
            try:
                from Bio.SeqUtils.ProtParam import ProteinAnalysis  # noqa: PLC0415
                pi_val = float(ProteinAnalysis((vh + vl)).isoelectric_point())
            except Exception:
                pass
        # Fallback: use v2/v1 pI when final version pI unknown (e.g. v3 never evaluated)
        if pi_val is None and isinstance(pi_block, dict):
            pi_val = pi_block.get("v2") or pi_block.get("v1")
    if pi_val is None or float(pi_val) <= target_pi_max:
        notes.append("cmc_design:skip:pI_ok_or_unknown")
        return (results, notes)

    # Base for CMC design: v2 preferred, else v1
    base_v = "v2" if (seqs.get("v2_VH") and seqs.get("v2_VL")) else "v1"
    base_vh = str(seqs.get(f"{base_v}_VH") or "")
    base_vl = str(seqs.get(f"{base_v}_VL") or "")
    mouse_vh = str(seqs.get("mouse_VH") or "")
    mouse_vl = str(seqs.get("mouse_VL") or "")
    if not (base_vh and base_vl and mouse_vh and mouse_vl):
        notes.append("cmc_design:skip:missing_seq")
        return (results, notes)

    try:
        from core.humanization.kabat_utils import get_kabat_numbering  # noqa: PLC0415
        from core.cmc.cmc_design import design_v3_pi  # noqa: PLC0415

        mouse_vh_kd = get_kabat_numbering(mouse_vh)
        mouse_vl_kd = get_kabat_numbering(mouse_vl)
        if not mouse_vh_kd or not mouse_vl_kd:
            notes.append("cmc_design:skip:kabat_failed")
            return (results, notes)

        v3_vh, v3_vl, v2_to_v3_muts = design_v3_pi(
            base_vh, base_vl,
            mouse_vh_kd, mouse_vl_kd,
            target_pi_max=target_pi_max,
            max_mutations=4,
        )
    except RuntimeError as e:
        notes.append(f"cmc_design:failed:{e}")
        return (results, notes)

    # Update results
    seqs = dict(results.get("sequences") or {})
    seqs["v3_VH"] = v3_vh
    seqs["v3_VL"] = v3_vl
    results["sequences"] = seqs
    results.setdefault("mutations", {})
    results["mutations"]["v2_to_v3"] = v2_to_v3_muts
    results.setdefault("_meta", {})
    results["_meta"]["final_version"] = "v3"

    # Run full evaluation for v3 (developability + immunogenicity + cdr_scan + germline; structure if PDB)
    pdb_v3 = _find_version_pdb(project_dir, ab_id, "v3") or _find_best_pdb(project_dir, ab_id, "humanized")
    pdb_mouse = _find_version_pdb(project_dir, ab_id, "mouse") or _find_best_pdb(project_dir, ab_id, "mouse")
    modules = ["cdr_scan", "developability", "immunogenicity", "germline"]
    if pdb_v3 and pdb_v3.exists():
        modules.insert(0, "structure_13param")
        if pdb_mouse and pdb_mouse.exists():
            modules.append("delta_vs_mouse")

    try:
        from core.evaluation.evaluator import AbEvaluator, AntibodyType  # noqa: PLC0415

        ev = AbEvaluator(
            project_name=f"{ab_id}_v3_cmc",
            pdb_path=str(pdb_v3) if pdb_v3 and pdb_v3.exists() else None,
            ref_pdb_path=str(pdb_mouse) if pdb_mouse and pdb_mouse.exists() else None,
            vh_chain="H", vl_chain="L",
            vh_seq=v3_vh, vl_seq=v3_vl,
            ab_type=AntibodyType.HUMANIZED,
            strict_qa=True,
            use_iedb=use_iedb,
        )
        r = ev.run(modules=modules)
        payload = _eval_to_payload(r)
    except Exception as e:
        notes.append(f"cmc_design:eval_v3_error:{e}")
        _write_json(results_path, results)
        return (results, notes)

    # Merge evaluation_v3, developability, immunogenicity
    results.setdefault("_internal", {})
    if isinstance(results["_internal"], dict):
        results["_internal"]["evaluation_v3"] = payload

    res = payload.get("results") or {}
    dev = res.get("developability") or {}
    cdr = res.get("cdr_scan") or {}
    imm = res.get("immunogenicity") or {}
    gate_min, gate_max = 5.5, 8.5
    pi_v3 = dev.get("pI_fab_estimate")
    _pi_prev = dict(results.get("developability", {}).get("pI") or {})
    _metrics = {k: dev[k] for k in ("GRAVY", "instability_index", "net_charge_pH7", "hydro_patch_max9", "charge_patch_max7") if dev.get(k) is not None}
    results["developability"] = {
        "pI": _pi_prev,
        "liabilities": cdr.get("liabilities", []),
    }
    if _metrics:
        results["developability"]["metrics_final"] = _metrics
    pi_d = results["developability"]["pI"]
    pi_d["v3"] = pi_v3
    pi_d["v3_pass"] = bool(gate_min <= float(pi_v3) <= gate_max) if isinstance(pi_v3, (int, float)) else False
    pi_d.setdefault("gate_min", gate_min)
    pi_d.setdefault("gate_max", gate_max)

    rl_v3 = imm.get("risk_level") or imm.get("mhcii_risk")
    imm_prev = results.get("immunogenicity") or {}
    rl_prev = imm_prev.get("risk_level") if isinstance(imm_prev.get("risk_level"), dict) else {}
    results["immunogenicity"] = {
        "method": imm.get("method", "offline_heuristic"),
        "risk_level": {"v1": rl_prev.get("v1"), "v2": rl_prev.get("v2"), "v3": rl_v3},
        "recommended_followup": "PBMC T （）",
    }

    _write_json(results_path, results)
    notes.append(f"cmc_design:done:v3_pI={pi_v3}")
    return (results, notes)


def _compute_vernier_packing(pdb_path: Path) -> Dict[str, float]:
    """
    Return vernier packing contact-number dict from structure_metrics_humanization.analyze_structure.
    Keys like "VL_98".
    """
    # Ensure `scripts/` is importable when called from anywhere
    if str(SUITE) not in sys.path:
        sys.path.insert(0, str(SUITE))
    from scripts.structure_metrics_humanization import analyze_structure  # noqa: PLC0415

    m = analyze_structure(pdb_path, chain_vh="H", chain_vl="L", skip_sasa=True)
    vp = getattr(m, "vernier_packing", None) or {}
    return dict(vp) if isinstance(vp, dict) else {}


def _kabat_mutate_base(seq: str, kabat_pos: int, new_aa: str) -> str:
    """Mutate base Kabat residue (pos,'') and return reassembled sequence."""
    from core.humanization.kabat_utils import get_kabat_numbering, sorted_keys  # noqa: PLC0415

    kd = get_kabat_numbering(seq)
    if not kd:
        raise ValueError("Kabat numbering failed for sequence")
    key = (int(kabat_pos), "")
    if key not in kd:
        raise KeyError(f"Kabat key missing: {key}")
    kd[key] = str(new_aa)
    return "".join(kd[k] for k in sorted_keys(kd))


def _try_vl98_fr4_rescue(
    ab_id: str,
    project_dir: Path,
    results: Dict[str, Any],
    pdb_mouse: Path,
    pdb_v2: Path,
) -> Tuple[Optional[Dict[str, Any]], List[str]]:
    """
    Auto-introduce VL98 FR4 Vernier rescue ONLY if v2 structural fidelity fails.

    Returns:
      (evaluation_payload or None, notes)
    """
    notes: List[str] = []

    internal = results.get("_internal") or {}
    ev2 = internal.get("evaluation_v2") if isinstance(internal, dict) else None
    d2 = _audit_extract_delta(ev2)
    if _delta_pass(d2):
        notes.append("vl98_rescue:skip:v2_delta_pass")
        return (None, notes)

    seqs = results.get("sequences") or {}
    mouse_vl = str(seqs.get("mouse_VL") or "")
    v2_vh = str(seqs.get("v2_VH") or "")
    v2_vl = str(seqs.get("v2_VL") or "")
    if not (mouse_vl and v2_vh and v2_vl):
        notes.append("vl98_rescue:skip:missing_mouse_or_v2_seq")
        return (None, notes)

    from core.humanization.kabat_utils import get_kabat_numbering  # noqa: PLC0415
    kd_mouse_vl = get_kabat_numbering(mouse_vl)
    kd_v2_vl = get_kabat_numbering(v2_vl)
    if not kd_mouse_vl or not kd_v2_vl:
        notes.append("vl98_rescue:skip:kabat_numbering_failed")
        return (None, notes)

    mouse_aa = kd_mouse_vl.get((98, ""))
    v2_aa = kd_v2_vl.get((98, ""))
    if not mouse_aa or not v2_aa:
        notes.append("vl98_rescue:skip:missing_kabat98")
        return (None, notes)
    if mouse_aa == v2_aa:
        notes.append("vl98_rescue:skip:already_match_mouse")
        return (None, notes)

    # Evidence: packing delta at VL_98 (structure-only observable)
    pack_delta = None
    try:
        vp_m = _compute_vernier_packing(pdb_mouse)
        vp_2 = _compute_vernier_packing(pdb_v2)
        if "VL_98" in vp_m and "VL_98" in vp_2:
            pack_delta = float(vp_2["VL_98"]) - float(vp_m["VL_98"])
        notes.append(f"vl98_rescue:evidence:packing_delta_contact_number={pack_delta}")
    except Exception as e:
        notes.append(f"vl98_rescue:evidence_failed:{e}")

    # Build v3 candidate: back-mutate VL Kabat98 to mouse residue
    try:
        v3_vl = _kabat_mutate_base(v2_vl, 98, mouse_aa)
    except Exception as e:
        notes.append(f"vl98_rescue:skip:mutation_failed:{e}")
        return (None, notes)

    # Predict PDB for rescue candidate
    out_pdb = project_dir / "structures" / f"{ab_id}_humanized_v3_fr4_vl98_rescue.pdb"
    try:
        from ImmuneBuilder import ABodyBuilder2  # type: ignore
    except Exception as e:
        notes.append(f"vl98_rescue:skip:ImmuneBuilder_missing:{e}")
        return (None, notes)

    try:
        predictor = ABodyBuilder2()
        ab = predictor.predict({"H": v2_vh, "L": v3_vl})
        out_pdb.parent.mkdir(parents=True, exist_ok=True)
        ab.save(str(out_pdb))
        notes.append(f"vl98_rescue:pdb:{out_pdb}")
    except Exception as e:
        notes.append(f"vl98_rescue:skip:pdb_predict_failed:{e}")
        return (None, notes)

    # Re-evaluate structure vs mouse
    try:
        from core.evaluation.evaluator import AbEvaluator, AntibodyType  # noqa: PLC0415
        ev = AbEvaluator(
            project_name=f"{ab_id}_v44_v3_fr4_vl98_rescue",
            pdb_path=str(out_pdb),
            ref_pdb_path=str(pdb_mouse),
            vh_chain="H",
            vl_chain="L",
            vh_seq=v2_vh,
            vl_seq=v3_vl,
            ab_type=AntibodyType.HUMANIZED,
            strict_qa=False,
        )
        r = ev.run(modules=["structure_13param", "delta_vs_mouse"])
        payload = _eval_to_payload(r)
        payload.setdefault("_internal_note", {})
        payload["_internal_note"]["vl98_rescue"] = {
            "trigger": "v2_delta_fail",
            "kabat_pos": 98,
            "v2_aa": v2_aa,
            "mouse_aa": mouse_aa,
            "packing_delta_contact_number": pack_delta,
            "pdb": str(out_pdb),
        }
        return (payload, notes)
    except Exception as e:
        notes.append(f"vl98_rescue:skip:eval_failed:{e}")
        return (None, notes)


def _render_v44_audit_md(ab_id: str, project_dir: Path, results: Dict[str, Any]) -> str:
    meta = results.get("_meta") or {}
    internal = results.get("_internal") or {}
    final_v = str((meta.get("final_version") or "—")).strip() or "—"

    ev1 = internal.get("evaluation_v1") if isinstance(internal, dict) else None
    ev2 = internal.get("evaluation_v2") if isinstance(internal, dict) else None
    ev3 = internal.get("evaluation_v3") if isinstance(internal, dict) else None

    d1, d2, d3 = _audit_extract_delta(ev1), _audit_extract_delta(ev2), _audit_extract_delta(ev3)
    dev3 = _audit_extract_dev(ev3)
    imm3 = _audit_extract_imm(ev3)

    out: List[str] = []
    out.append(f"# {ab_id.upper()} — V4.4 Internal QA Audit（/）")
    out.append("")
    out.append(f"- Generated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    out.append(f"- Project dir: `{project_dir}`")
    out.append(f"- Final version (SSOT): `{final_v}`")
    out.append("")

    # Phase 3 modeling / reproducibility
    out.append("## Phase 3 — Structure modeling（）")
    out.append("")
    st = results.get("structure") or {}
    if isinstance(st, dict) and st:
        out.append(f"- tool: `{st.get('tool','—')}`")
        out.append(f"- mouse_pdb: `{st.get('mouse_pdb','—')}`")
        out.append(f"- v1_pdb: `{st.get('v1_pdb','—')}`")
        out.append(f"- v2_pdb: `{st.get('v2_pdb','—')}`")
        out.append(f"- v3_pdb: `{st.get('v3_pdb','—')}`")
        out.append("")
        out.append("> ：“ PDB ID/”。，/。")
    else:
        out.append("- (missing) results.structure")
    out.append("")

    # Phase 2 germline selection
    gl = results.get("germline") or {}
    out.append("## Phase 2 — Germline selection（）")
    out.append("")
    out.append(f"- Selected: VH=`{gl.get('VH_gene','—')}`, VL=`{gl.get('VL_gene','—')}`")
    cand = results.get("germline_candidates") or {}
    if isinstance(cand, dict):
        vh_c = cand.get("VH_candidates") or []
        vl_c = cand.get("VL_candidates") or []
        if isinstance(vh_c, list) and vh_c:
            out.append("")
            out.append("### VH （Top）")
            out.append("")
            out.append("| gene | fr_identity_pct | composite_score | selected | clinical_precedent (n) |")
            out.append("|---|---:|---:|---|---:|")
            for it in vh_c[:8]:
                if not isinstance(it, dict):
                    continue
                cp = it.get("clinical_precedent") if isinstance(it.get("clinical_precedent"), list) else []
                out.append(f"| `{it.get('gene','—')}` | {it.get('fr_identity_pct','—')} | {it.get('composite_score','—')} | {it.get('selected',False)} | {len(cp)} |")
        if isinstance(vl_c, list) and vl_c:
            out.append("")
            out.append("### VL （Top）")
            out.append("")
            out.append("| gene | fr_identity_pct | composite_score | selected | clinical_precedent (n) |")
            out.append("|---|---:|---:|---|---:|")
            for it in vl_c[:8]:
                if not isinstance(it, dict):
                    continue
                cp = it.get("clinical_precedent") if isinstance(it.get("clinical_precedent"), list) else []
                out.append(f"| `{it.get('gene','—')}` | {it.get('fr_identity_pct','—')} | {it.get('composite_score','—')} | {it.get('selected',False)} | {len(cp)} |")
    out.append("")

    # FR4 / J evidence (do not guess)
    out.append("## FR4 / J （）")
    out.append("")
    try:
        from core.humanization.kabat_utils import get_kabat_numbering, sorted_keys  # type: ignore

        seqs = results.get("sequences") or {}
        vh_seq = str(seqs.get(f"{final_v}_VH") or "")
        vl_seq = str(seqs.get(f"{final_v}_VL") or "")

        def _tail(seq: str, start_pos: int) -> str:
            kd = get_kabat_numbering(seq)
            keys = sorted_keys(kd)
            return "".join(kd[k] for k in keys if k[0] >= start_pos)

        vh_fr4 = _tail(vh_seq, 103) if vh_seq else ""
        vl_fr4 = _tail(vl_seq, 98) if vl_seq else ""
        out.append(f"- VH FR4（Kabat≥103）: `{vh_fr4 or '—'}`")
        out.append(f"- VL FR4（Kabat≥98）: `{vl_fr4 or '—'}`")
        out.append("")

        def _load_entries(p: Path) -> List[Dict[str, str]]:
            obj = json.loads(p.read_text(encoding="utf-8"))
            ent = obj.get("entries") if isinstance(obj, dict) else None
            return ent if isinstance(ent, list) else []

        # Try match VH FR4 tail to IGHJ sequences (suffix match)
        ig_hj = SUITE / "data" / "germlines" / "human_ig_aa" / "IGHJ_aa.json"
        if ig_hj.exists() and vh_fr4:
            hits = []
            for e in _load_entries(ig_hj):
                if not isinstance(e, dict):
                    continue
                sid = str(e.get("id") or "")
                s = str(e.get("sequence_aa") or "")
                if s and s.endswith(vh_fr4):
                    hits.append(sid)
            out.append(
                f"- IGHJ （suffix == VH FR4）: {', '.join('`'+h+'`' for h in hits) if hits else ''}"
            )
        else:
            out.append("- IGHJ ：（ IGHJ_aa.json  VH FR4 ）")

        # Try match VL FR4 tail to IGKJ/IGLJ (substring match; definitions may differ)
        ig_kj = SUITE / "data" / "germlines" / "human_ig_aa" / "IGKJ_aa.json"
        ig_lj = SUITE / "data" / "germlines" / "human_ig_aa" / "IGLJ_aa.json"
        if vl_fr4:
            kj_hit = False
            lj_hit = False
            if ig_kj.exists():
                for e in _load_entries(ig_kj):
                    if isinstance(e, dict) and vl_fr4 in str(e.get("sequence_aa") or ""):
                        kj_hit = True
                        break
            if ig_lj.exists():
                for e in _load_entries(ig_lj):
                    if isinstance(e, dict) and vl_fr4 in str(e.get("sequence_aa") or ""):
                        lj_hit = True
                        break
            out.append(
                f"- IGKJ/IGLJ （VL FR4 in J-REGION AA）: IGKJ={'' if kj_hit else ''} | IGLJ={'' if lj_hit else ''}"
            )
            if not (kj_hit or lj_hit):
                out.append(
                    "  - ： pipeline  VL FR4  IMGT  J-REGION AA ， J ；。"
                )

    except Exception as e:
        out.append(f"- FR4/J ：{e}")
    out.append("")

    # Phase 4 Vernier decisions
    p4 = _phase4_json_path(project_dir, ab_id)
    out.append("## Phase 4 — Vernier 22 （）")
    out.append("")
    out.append(f"- Source: `{p4}`" if p4 else "- Source: (missing)")
    out.append("- ： `internal/phase4_backmutation_<id>.md`（）。")
    out.append("")

    # Phase 5 structure fidelity (numeric)
    out.append("## Phase 5 — Structural fidelity（ + ）")
    out.append("")
    out.append("### QA （V4.4）")
    out.append("")
    out.append("- VH/VL angle delta: `< 3.0°`")
    out.append("- CDR RMSD max: `< 1.5 Å`（ H1/H2/H3/L1/L2/L3 ）")
    out.append("- Canonical match: `H1/H2/L1` （True/False）")
    out.append("")
    out.append("### （vs mouse）")
    out.append("")
    out.append("| version | angle_delta (°) | angle_pass | cdr_rmsd_max (Å) | cdr_rmsd_pass | canonical_match_h1_h2_l1 | conclusion |")
    out.append("|---|---:|---|---:|---|---|---|")

    def _row(d: Dict[str, Any]) -> str:
        ang = (d.get("vh_vl_angle") or {}) if isinstance(d.get("vh_vl_angle"), dict) else {}
        return "| {ver} | {ad:.3f} | {ap} | {rm:.3f} | {rp} | {cm} | {cc} |".format(
            ver="—",
            ad=float(ang.get("delta") or 0.0) if ang.get("delta") is not None else 0.0,
            ap=str(ang.get("pass")),
            rm=float(d.get("cdr_rmsd_max") or 0.0) if d.get("cdr_rmsd_max") is not None else 0.0,
            rp=str(d.get("cdr_rmsd_pass")),
            cm=str(d.get("canonical_match_h1_h2_l1")),
            cc=str(d.get("conclusion") or "—"),
        )

    if d1:
        out.append(_row({**d1, "_ver": "v1"}).replace("| — |", "| v1 |", 1))
    if d2:
        out.append(_row({**d2, "_ver": "v2"}).replace("| — |", "| v2 |", 1))
    if d3:
        out.append(_row({**d3, "_ver": "v3"}).replace("| — |", "| v3 |", 1))
    out.append("")

    # Vernier evidence + Phase4→5 closed-loop policy (458 engineered dataset)
    out.append("## Vernier（：Phase 4→5）")
    out.append("")
    out.append("- ： Vernier /。")
    out.append("- ：`data/humanization_assay/structure_metrics_summary.json`（458 engineered ） `data/humanization_assay/vernier_ml_report.md` ， Vernier 22 （/packing/CDR/）。")
    out.append("- ： Phase4 （SASA/packing/）+ ，。")
    out.append("- ：“”（angle/CDR RMSD/canonical ），： back-mutate→→， PASS 。")
    out.append("")

    # If a round2 rescue evaluation exists, print its headline summary
    if isinstance(internal, dict):
        ev_round2 = None
        for k in ("evaluation_v3_vernier_round2", "evaluation_v2_vernier_round2", "evaluation_v1_vernier_round2"):
            if isinstance(internal.get(k), dict):
                ev_round2 = internal.get(k)
                break
        if isinstance(ev_round2, dict) and ev_round2:
            drr = _audit_extract_delta(ev_round2)
            note = (ev_round2.get("_internal_note") or {}).get("vernier_round2") if isinstance(ev_round2.get("_internal_note"), dict) else None
            if isinstance(note, dict):
                out.append(f"- ：`{note.get('trigger','—')}`；base_version=`{note.get('base_version','—')}`；phase4_source=`{note.get('phase4_source','—')}`")
                out.append(f"- ：max_steps={note.get('max_steps','—')}；chosen_steps={note.get('chosen_steps','—')}")
                applied = note.get("applied") if isinstance(note.get("applied"), list) else []
                if applied:
                    out.append("")
                    out.append("###  Vernier （）")
                    out.append("")
                    out.append("| step | position | chain | kabat_pos | from | to | score | sasa | contact | dist_to_cdr |")
                    out.append("|---:|---|---|---:|---|---|---:|---:|---:|---:|")
                    for it in applied:
                        if not isinstance(it, dict):
                            continue
                        out.append("| {step} | `{pos}` | {ch} | {kp} | {fr} | {to} | {sc:.3f} | {sa} | {co} | {di} |".format(
                            step=int(it.get("step") or 0),
                            pos=str(it.get("position") or "—"),
                            ch=str(it.get("chain") or "—"),
                            kp=str(it.get("kabat_pos") or "—"),
                            fr=str(it.get("from") or "—"),
                            to=str(it.get("to") or "—"),
                            sc=float(it.get("score") or 0.0),
                            sa=str(it.get("sasa") if it.get("sasa") is not None else "—"),
                            co=str(it.get("contact") if it.get("contact") is not None else "—"),
                            di=str(it.get("dist_to_cdr") if it.get("dist_to_cdr") is not None else "—"),
                        ))
            if drr:
                out.append("")
                out.append("### （vs mouse）")
                out.append("")
                out.append("| version | angle_delta (°) | angle_pass | cdr_rmsd_max (Å) | cdr_rmsd_pass | canonical_match_h1_h2_l1 | conclusion |")
                out.append("|---|---:|---|---:|---|---|---|")
                out.append(_row({**drr, "_ver": "vernier_round2"}).replace("| — |", "| vernier_round2 |", 1))
    out.append("")

    # Developability numeric
    out.append("## CMC / Developability（ + ）")
    out.append("")
    pI = (results.get("developability") or {}).get("pI") if isinstance(results.get("developability"), dict) else {}
    if isinstance(pI, dict):
        out.append(f"- pI(v1)={pI.get('v1','—')} | pI(v2)={pI.get('v2','—')} | pI(v3)={pI.get('v3','—')}  （gate: {pI.get('gate_min','—')}–{pI.get('gate_max','—')}）")
        out.append(f"- pass: v1={pI.get('v1_pass','—')} | v2={pI.get('v2_pass','—')} | v3={pI.get('v3_pass','—')}")
    out.append("")
    muts = (results.get("mutations") or {}).get("v2_to_v3") or []
    out.append("### v2→v3 （）")
    out.append("")
    out.append("| chain | kabat_pos | from | to | rationale |")
    out.append("|---|---:|---|---|---|")
    if isinstance(muts, list) and muts:
        for it in muts:
            if not isinstance(it, dict):
                continue
            out.append(f"| {it.get('chain','—')} | {it.get('kabat_pos','—')} | {it.get('from','—')} | {it.get('to','—')} | {it.get('rationale','—')} |")
    else:
        out.append("| — | — | — | — | — |")
    out.append("")

    # Immunogenicity internal details (not for customer)
    out.append("## Immunogenicity（）")
    out.append("")

    def _imm_row(ver: str, ev_payload: Any) -> str:
        imm = _audit_extract_imm(ev_payload)
        summ = imm.get("summary") if isinstance(imm.get("summary"), dict) else {}
        return "| {ver} | {method} | {risk} | {tcia} | {nh} | {nm} | {nc} |".format(
            ver=ver,
            method=str(imm.get("method") or "—"),
            risk=str((summ or {}).get("risk_level") or imm.get("mhcii_risk") or "—"),
            tcia=str((summ or {}).get("tcia_score") or "—"),
            nh=str((summ or {}).get("n_risk_positions_high") or "—"),
            nm=str((summ or {}).get("n_risk_positions_medium") or "—"),
            nc=str((summ or {}).get("n_clusters_high_medium") or "—"),
        )

    out.append("| version | method | risk_level | tcia_score | n_high | n_medium | n_clusters |")
    out.append("|---|---|---|---:|---:|---:|---:|")
    out.append(_imm_row("v1", ev1))
    out.append(_imm_row("v2", ev2))
    out.append(_imm_row("v3", ev3))
    out.append("")

    if imm3:
        out.append(f"- method: `{imm3.get('method','—')}` | status: `{imm3.get('status','—')}`")
        summ = imm3.get("summary") if isinstance(imm3.get("summary"), dict) else {}
        if isinstance(summ, dict) and summ:
            out.append(f"- risk_level: `{summ.get('risk_level','—')}` | n_alleles: {summ.get('n_alleles','—')} | n_high: {summ.get('n_risk_positions_high','—')} | n_medium: {summ.get('n_risk_positions_medium','—')} | n_clusters: {summ.get('n_clusters_high_medium','—')}")
        flags = imm3.get("flags") if isinstance(imm3.get("flags"), list) else []
        if flags:
            out.append("")
            out.append("### flags")
            out.append("")
            for f in flags:
                out.append(f"- {f}")
    else:
        out.append("- (missing) evaluation_v3.results.immunogenicity")

    out.append("")
    out.append("## ")
    out.append("")
    out.append("-  PASS/WARN/FAIL ，；，。")
    return "\n".join(out) + "\n"


def _find_best_pdb(project_dir: Path, ab_id: str, kind: str) -> Optional[Path]:
    """
    kind: 'mouse' or 'humanized'
    Preference:
      humanized: v3 > v2 > v1 > fallback
      mouse: exact match first
    """
    if kind == "mouse":
        pats = [f"{ab_id}_mouse.pdb", f"*{ab_id}*mouse*.pdb"]
    else:
        pats = [
            f"{ab_id}_humanized_v3.pdb",
            f"{ab_id}_humanized_v2.pdb",
            f"{ab_id}_humanized_v1.pdb",
            f"{ab_id}_humanized_final.pdb",
            f"{ab_id}_humanized.pdb",
            f"*{ab_id}*humanized*.pdb",
        ]
    for pat in pats:
        for p in project_dir.rglob(pat):
            if p.is_file():
                return p
    return None


def _read_sequences_from_results(results: Dict[str, Any]) -> Tuple[str, str]:
    """
    Return (VH, VL) sequences for the SSOT final version.

    IMPORTANT:
    - Prefer `_meta.final_version` (v1/v2/v3) when present.
    - Fallback to v3→v2→v1 for legacy payloads.
    """
    seqs = results.get("sequences") if isinstance(results.get("sequences"), dict) else {}
    meta = results.get("_meta") if isinstance(results.get("_meta"), dict) else {}
    final_v = str(meta.get("final_version") or "").strip().lower()
    if final_v in ("v1", "v2", "v3"):
        vh = seqs.get(f"{final_v}_VH") or ""
        vl = seqs.get(f"{final_v}_VL") or ""
        return (str(vh), str(vl))
    vh = seqs.get("v3_VH") or seqs.get("v2_VH") or seqs.get("v1_VH") or ""
    vl = seqs.get("v3_VL") or seqs.get("v2_VL") or seqs.get("v1_VL") or ""
    return (str(vh), str(vl))


def _extract_imgt_span(seq: str, *, chain: str, lo: int, hi: int) -> str:
    """
    Extract residues by IMGT integer range [lo, hi] using dual-scheme numbering aligned by seq_index.
    Includes insertion residues whose integer IMGT position is within the range.
    """
    if not seq:
        return ""
    try:
        from core.numbering.dual_scheme import compute_dual_scheme_numbering  # noqa: PLC0415
    except Exception:
        return ""
    d = compute_dual_scheme_numbering(seq, chain_label=chain)
    return "".join(r.aa for r in d.imgt if lo <= int(r.pos) <= hi)


def _cdr_union_gate_or_problem(
    *,
    results: Dict[str, Any],
    cfg: Dict[str, Any],
) -> List[str]:
    """
    HARD gate for delivery:
    - IMGT CDR union segments must be non-empty AND identical between mouse parent and final humanized.

    Rationale:
    - Prevents silently losing CDR residues (e.g., empty VH CDR3) while still producing reports/packages.
    - Uses IMGT ranges from v44 config, not Kabat integer ranges.
    """
    problems: List[str] = []
    seqs = results.get("sequences") if isinstance(results.get("sequences"), dict) else {}
    mouse_vh = str(seqs.get("mouse_VH") or "")
    mouse_vl = str(seqs.get("mouse_VL") or "")
    final_vh, final_vl = _read_sequences_from_results(results)

    unions = cfg.get("cdr_union_ranges") if isinstance(cfg.get("cdr_union_ranges"), dict) else {}
    for chain, mouse_seq, hum_seq in [
        ("VH", mouse_vh, final_vh),
        ("VL", mouse_vl, final_vl),
    ]:
        ch = unions.get(chain) if isinstance(unions.get(chain), dict) else {}
        for cdr_name in ("CDR1_union", "CDR2_union", "CDR3_union"):
            span = ch.get(cdr_name)
            if not (isinstance(span, list) and len(span) == 2):
                continue
            try:
                lo, hi = int(span[0]), int(span[1])
            except Exception:
                continue
            m = _extract_imgt_span(mouse_seq, chain=chain, lo=lo, hi=hi)
            h = _extract_imgt_span(hum_seq, chain=chain, lo=lo, hi=hi)
            if not m:
                problems.append(f"cdr_union_empty:mouse:{chain}:{cdr_name}:{lo}-{hi}")
                continue
            if not h:
                problems.append(f"cdr_union_empty:humanized:{chain}:{cdr_name}:{lo}-{hi}")
                continue
            if m.upper() != h.upper():
                problems.append(f"cdr_union_mismatch:{chain}:{cdr_name}:{lo}-{hi}")
    return problems


def _render_internal_md_germline(germ: Dict, cand: Dict, ab_id: str) -> str:
    lines = [f"#  — {ab_id}", ""]
    lines.append(" VH、VL （ fr_identity、vernier、composite），。** Top3×Top3  9 **，“”。")
    lines.append("")
    lines.append(f"** VH**：`{germ.get('VH_gene', '—')}`")
    lines.append(f"** VL**：`{germ.get('VL_gene', '—')}`")
    lines.append("")
    vh_c = cand.get("VH_candidates") or []
    vl_c = cand.get("VL_candidates") or []
    if vh_c:
        lines.append("## VH ")
        lines.append("| gene | fr_identity% | vernier% | composite | selected | clinical_precedent |")
        lines.append("|---|---:|---:|---:|---|---|")
        for x in vh_c:
            sel = "✓" if x.get("selected") else ""
            prec = ", ".join((x.get("clinical_precedent") or [])[:3])
            lines.append(f"| {x.get('gene','—')} | {x.get('fr_identity_pct','—')} | {x.get('vernier_similarity_pct','—')} | {x.get('composite_score','—')} | {sel} | {prec} |")
        lines.append("")
    if vl_c:
        lines.append("## VL ")
        lines.append("| gene | fr_identity% | vernier% | composite | selected | clinical_precedent |")
        lines.append("|---|---:|---:|---:|---|---|")
        for x in vl_c:
            sel = "✓" if x.get("selected") else ""
            prec = ", ".join((x.get("clinical_precedent") or [])[:3])
            lines.append(f"| {x.get('gene','—')} | {x.get('fr_identity_pct','—')} | {x.get('vernier_similarity_pct','—')} | {x.get('composite_score','—')} | {sel} | {prec} |")
    return "\n".join(lines) + "\n"


def _render_internal_md_cmc(muts: List, results: Optional[Dict[str, Any]] = None) -> str:
    lines = ["# CMC （v2→v3）", ""]
    lines.append("（ pI、），。")
    lines.append("")
    # ：
    lines.append("## ：")
    lines.append("")
    lines.append("- ****: v2 （VH+VL）、base_pI、target_pi_max=8.5")
    lines.append("- ****: `aa∈{K,R}`  ** CDR union**  ** Vernier **； base residue `(pos,'')`（）")
    lines.append("- ****: ，「 pI 」， pI≤8.5 ")
    lines.append("- ****: K/R→E ， CDR， Vernier")
    lines.append("- **Liability **（）：， FR  N-gly/deamidation/isomerization （N→Q, D→E）")

    seqs = (results or {}).get("sequences") if isinstance((results or {}).get("sequences"), dict) else {}
    v2_vh = str(seqs.get("v2_VH") or "")
    v2_vl = str(seqs.get("v2_VL") or "")
    v3_vh = str(seqs.get("v3_VH") or "")
    v3_vl = str(seqs.get("v3_VL") or "")

    # Prefer SSOT pI values if available
    dev = (results or {}).get("developability") or {}
    pi = dev.get("pI") if isinstance(dev.get("pI"), dict) else {}
    v2_pi = pi.get("v2") if pi else None
    v3_pi = pi.get("v3") if pi else None
    if v2_pi is None and (v2_vh or v2_vl):
        v2_pi = _compute_pi_fab(v2_vh, v2_vl)
    if v3_pi is None and (v3_vh or v3_vl):
        v3_pi = _compute_pi_fab(v3_vh, v3_vl)
    if v2_pi is not None:
        lines.append(f"- **v2 base_pI**: {round(float(v2_pi), 3)}")
    if v3_pi is not None:
        lines.append(f"- **v3 final_pI**: {round(float(v3_pi), 3)}")

    # Candidate inventory (lightweight; uses Kabat numbering only)
    try:
        from core.humanization.kabat_utils import get_kabat_numbering  # noqa: PLC0415

        vh_vernier = _vernier_positions_from_cfg("VH")
        vl_vernier = _vernier_positions_from_cfg("VL")

        def _cands(seq: str, chain: str) -> List[Dict[str, Any]]:
            kd = get_kabat_numbering(seq) if seq else None
            if not kd:
                return []
            vernier = vh_vernier if chain == "VH" else vl_vernier
            out: List[Dict[str, Any]] = []
            for (pos, ins), aa in kd.items():
                if ins != "":
                    continue
                if aa not in ("K", "R"):
                    continue
                if _in_cdr_union_kabat(int(pos), chain, seq=seq):
                    continue
                if int(pos) in vernier:
                    continue
                out.append({"chain": chain, "kabat_pos": int(pos), "aa": str(aa)})
            out.sort(key=lambda x: (x["chain"], x["kabat_pos"]))
            return out

        vh_cands = _cands(v2_vh, "VH")
        vl_cands = _cands(v2_vl, "VL")
        lines.append("")
        lines.append("### （ v2 Kabat ）")
        lines.append("")
        lines.append(f"- VH candidates: {len(vh_cands)}")
        lines.append(f"- VL candidates: {len(vl_cands)}")
        if (vh_cands or vl_cands):
            lines.append("")
            lines.append("| chain | kabat_pos | aa |")
            lines.append("|:---:|---:|:---:|")
            for it in (vh_cands + vl_cands)[:30]:
                lines.append(f"| {it.get('chain','—')} | {it.get('kabat_pos','—')} | {it.get('aa','—')} |")
            if len(vh_cands) + len(vl_cands) > 30:
                lines.append(f"| … | … | （ {len(vh_cands) + len(vl_cands)} ） |")
    except Exception:
        pass
    lines.append("")
    if not muts:
        # Try to provide a deterministic reason
        if v2_pi is not None and float(v2_pi) <= 8.5:
            lines.append(" CMC ：v2 pI （≤8.5）。")
        else:
            lines.append(" CMC ： v2→v3 （、/）。")
        return "\n".join(lines) + "\n"
    lines.append("### ")
    lines.append("")
    lines.append("| step | chain | kabat_pos | from | to | pI_before | pI_after | rationale |")
    lines.append("|---:|:---:|---:|:---:|:---:|---:|---:|---|")
    cur_vh, cur_vl = v2_vh, v2_vl
    cur_pi = _compute_pi_fab(cur_vh, cur_vl)
    for i, it in enumerate(muts, start=1):
        if not isinstance(it, dict):
            continue
        ch = str(it.get("chain") or "—")
        kp = int(it.get("kabat_pos") or 0)
        to_aa = str(it.get("to") or "")
        pi_before = cur_pi
        try:
            if ch == "VH":
                cur_vh = _kabat_mutate_base(cur_vh, kp, to_aa)
            elif ch == "VL":
                cur_vl = _kabat_mutate_base(cur_vl, kp, to_aa)
        except Exception:
            # still print the record even if local reconstruction fails
            pass
        cur_pi = _compute_pi_fab(cur_vh, cur_vl)
        lines.append(
            "| {i} | {ch} | {kp} | {fr} | {to} | {pb} | {pa} | {ra} |".format(
                i=i,
                ch=ch,
                kp=kp or "—",
                fr=str(it.get("from") or "—"),
                to=str(it.get("to") or "—"),
                pb=round(float(pi_before), 3) if isinstance(pi_before, (int, float)) else "—",
                pa=round(float(cur_pi), 3) if isinstance(cur_pi, (int, float)) else "—",
                ra=str(it.get("rationale") or "—"),
            )
        )
    return "\n".join(lines) + "\n"


def _render_internal_md_developability(dev: Dict, results: Optional[Dict[str, Any]] = None) -> str:
    lines = ["# （Developability）", ""]
    lines.append("（pI、liabilities ）， CMC （）。")
    lines.append("")
    pi = (dev or {}).get("pI") if isinstance(dev, dict) else {}
    if isinstance(pi, dict):
        lines.append("## pI")
        lines.append(f"- v1: {pi.get('v1','—')} (pass: {pi.get('v1_pass','—')})")
        lines.append(f"- v2: {pi.get('v2','—')} (pass: {pi.get('v2_pass','—')})")
        lines.append(f"- v3: {pi.get('v3','—')} (pass: {pi.get('v3_pass','—')})")
        lines.append(f"- : [{pi.get('gate_min','—')}, {pi.get('gate_max','—')}]")
        lines.append("")
    mf = (dev or {}).get("metrics_final") if isinstance(dev, dict) else {}
    if isinstance(mf, dict) and mf:
        lines.append("## CMC/（）")
        lines.append("")
        lines.append("|  |  |")
        lines.append("|:---|---:|")
        for k in ("GRAVY", "instability_index", "net_charge_pH7", "hydro_patch_max9", "charge_patch_max7"):
            v = mf.get(k)
            if v is not None:
                lines.append(f"| {k} | {v} |")
        lines.append("")
    liab = (dev or {}).get("liabilities") if isinstance(dev, dict) else []
    if isinstance(liab, list) and liab:
        lines.append("## liabilities")
        # `cdr_scan` reports `pos` as 0-based offset in concatenated (VH+VL) sequence.
        vh_seq, vl_seq = ("", "")
        try:
            if results:
                vh_seq, vl_seq = _read_sequences_from_results(results)
        except Exception:
            pass
        full_seq = (vh_seq or "") + (vl_seq or "")
        vh_len = len(vh_seq or "")
        lines.append("")
        lines.append("| type | severity | pattern | pos0 | pos1 | chain | chain_pos1 | context |")
        lines.append("|:---|:---:|:---:|---:|---:|:---:|---:|:---|")
        for it in liab[:60]:
            if not isinstance(it, dict):
                continue
            typ = str(it.get("type") or "—")
            sev = str(it.get("severity") or "—")
            pat = str(it.get("pattern") or "—")
            pos0 = it.get("pos")
            pos1 = (int(pos0) + 1) if isinstance(pos0, int) else None
            chain = "—"
            chain_pos1 = None
            ctx = "—"
            if isinstance(pos0, int) and full_seq:
                chain = "VH" if pos0 < vh_len else "VL"
                chain_pos1 = (pos0 + 1) if chain == "VH" else (pos0 - vh_len + 1)
                lo = max(0, pos0 - 6)
                hi = min(len(full_seq), pos0 + 7)
                ctx = full_seq[lo:hi]
            lines.append(
                f"| {typ} | {sev} | `{pat}` | {pos0 if isinstance(pos0,int) else '—'} | {pos1 if pos1 is not None else '—'} | {chain} | {chain_pos1 if chain_pos1 is not None else '—'} | `{ctx}` |"
            )
        if len(liab) > 60:
            lines.append(f"| … | … | … | … | … | … | … | （ {len(liab)} ） |")
        lines.append("")
    # ：
    lines.append("## ：")
    lines.append("")
    lines.append("### pI")
    lines.append("- ****: BioPython `ProteinAnalysis(seq).isoelectric_point()`")
    lines.append("- ****: VH+VL （Fab ）")
    lines.append("")
    lines.append("### liabilities（cdr_scan）")
    lines.append("- ****:  VH+VL ")
    lines.append("- ****: `NG/NS`→deamidation, `DG/DS`→isomerization, `N[^P][ST]`→N-glycosylation, `C`→free_Cys_candidate")
    lines.append("- ****: `pos0`  VH+VL  0-based offset；`pos1`  1-based；`chain_pos1`  1-based")
    ev_detail = _get_developability_detail(results)
    if ev_detail:
        lines.append("")
        lines.append("### （ evaluation）")
        lines.append("")
        lines.append("|  | pI_fab | GRAVY | II | net_charge | hp9 | cp7 | liabilities |")
        lines.append("|:---|---:|---:|---:|---:|---:|---:|---:|")
        for row in ev_detail.get("rows", [])[:5]:
            lines.append(
                f"| {row.get('version','—')} | {row.get('pi','—')} | {row.get('gravy','—')} | "
                f"{row.get('ii','—')} | {row.get('net_charge','—')} | {row.get('hp9','—')} | "
                f"{row.get('cp7','—')} | {row.get('n_liab','—')} |"
            )
    # （）
    recs = _liability_recommendations_internal(liab or [])
    if recs:
        lines.append("")
        lines.append("## （）")
        lines.append("")
        lines.append("|  | / |  |  |")
        lines.append("|:---|---|:---|:---|")
        for r in recs:
            lines.append(f"| {r.get('type','—')} | {r.get('location','—')} | {r.get('mutation','—')} | {r.get('experiment','—')} |")
    return "\n".join(lines) + "\n"


def _liability_recommendations_internal(liab: List) -> List[Dict[str, str]]:
    """Map liabilities to mutation + experiment recommendations."""
    recs: List[Dict[str, str]] = []
    for it in liab:
        if not isinstance(it, dict):
            continue
        typ = str(it.get("type") or "").strip()
        sev = str(it.get("severity") or "").strip()
        motif = str(it.get("motif") or it.get("pattern") or "").strip()
        loc = str(it.get("location") or it.get("region") or "—").strip()
        if not loc and motif:
            loc = motif

        mut = "—"
        exp = "—"
        if typ == "N-glycosylation":
            mut = "N→Q  Y→F（NYS→NQS ）；CDR  SPR/ELISA "
            exp = "LC-MS ；CHO "
        elif typ == "deamidation":
            mut = "N→Q  S→A（）；FR "
            exp = "（40°C/）；/"
        elif typ == "isomerization":
            mut = "D→E（）；"
            exp = "/；RP-HPLC  Asp "
        elif typ == "free_Cys_candidate":
            mut = "C→S  C→A（）；"
            exp = "；SEC/cIEF "
        else:
            if sev in ("HIGH", "MEDIUM"):
                exp = " CMC "
        recs.append({"type": typ, "location": loc, "mutation": mut, "experiment": exp})
    return recs


def _get_developability_detail(results: Optional[Dict[str, Any]]) -> Optional[Dict[str, Any]]:
    """Extract developability + cdr_scan from evaluation for developer process."""
    if not results:
        return None
    internal = results.get("_internal") or {}
    if not isinstance(internal, dict):
        return None
    rows: List[Dict[str, Any]] = []
    for evk in ("evaluation_v1", "evaluation_v2", "evaluation_v3"):
        ev = internal.get(evk) or {}
        res = ev.get("results") or {}
        dev = res.get("developability") or {}
        cdr = res.get("cdr_scan") or {}
        if not dev and not cdr:
            continue
        ver = evk.replace("evaluation_", "")
        pi = dev.get("pI_fab_estimate") if isinstance(dev.get("pI_fab_estimate"), (int, float)) else "—"
        gravy = dev.get("GRAVY") if isinstance(dev.get("GRAVY"), (int, float)) else "—"
        ii = dev.get("instability_index") if isinstance(dev.get("instability_index"), (int, float)) else "—"
        net_charge = dev.get("net_charge_pH7") if dev.get("net_charge_pH7") is not None else "—"
        hp9 = dev.get("hydro_patch_max9") if dev.get("hydro_patch_max9") is not None else "—"
        cp7 = dev.get("charge_patch_max7") if dev.get("charge_patch_max7") is not None else "—"
        liab = cdr.get("liabilities") or []
        n_liab = len(liab) if isinstance(liab, list) else "—"
        rows.append({"version": ver, "pi": pi, "gravy": gravy, "ii": ii, "net_charge": net_charge, "hp9": hp9, "cp7": cp7, "n_liab": n_liab})
    return {"rows": rows} if rows else None


def _render_internal_md_immunogenicity(
    imm: Dict,
    results: Optional[Dict[str, Any]] = None,
    enrich: bool = False,
) -> str:
    lines = ["# ", ""]
    lines.append(" pipeline 5.8 （MHC-II 27 、 15-mer、FR 、TCIA 、），。")
    lines.append("")
    if not imm:
        lines.append("（）")
        return "\n".join(lines) + "\n"
    rl = imm.get("risk_level") if isinstance(imm.get("risk_level"), dict) else {}
    lines.append("## ")
    lines.append("")
    lines.append(f"- method: {imm.get('method','—')}")
    lines.append(f"- v1: {rl.get('v1','—')} | v2: {rl.get('v2','—')} | v3: {rl.get('v3','—')}")
    lines.append(f"- : {imm.get('recommended_followup','—')}")
    # Pull computation evidence from _internal when available
    det = _get_immunogenicity_detail(results, enrich=enrich)
    if det:
        lines.append("")
        lines.append("## （ evaluation ）")
        lines.append("")
        lines.append(f"- ****: {det.get('n_alleles','—')}")
        lines.append(f"- **TCIA **: {det.get('tcia_score','—')}")
        if det.get("n_epitopes") is not None:
            lines.append(f"- **（， VH+VL）**: {det.get('n_epitopes','—')}")
        if det.get("n_clusters") is not None:
            lines.append(f"- **（）**: {det.get('n_clusters','—')}")
        lines.append(f"- ****: {det.get('n_risk_positions_high','—')}")
        lines.append(f"- ****: {det.get('n_risk_positions_medium','—')}")
        lines.append(f"- ****（，）: {det.get('n_tolerated','—')}")
        lines.append(f"- ****: {det.get('n_clusters_high_medium','—')}")

        # Funnel stats (layer-by-layer)
        fstats = det.get("funnel_stats") or {}
        stages = fstats.get("stages") if isinstance(fstats, dict) else None
        if isinstance(stages, list) and stages:
            lines.append("")
            lines.append("### （）")
            lines.append("")
            lines.append("| stage | total | VH | VL |")
            lines.append("|:---|---:|---:|---:|")
            for st in stages:
                if not isinstance(st, dict):
                    continue
                lines.append(
                    f"| {st.get('stage','—')} | {st.get('total','—')} | {st.get('VH','—')} | {st.get('VL','—')} |"
                )

        # Cluster expansion (bottom set)
        cs = det.get("cluster_summary") or {}
        if isinstance(cs, dict) and cs:
            rows = []
            for cid_raw, d in cs.items():
                if not isinstance(d, dict):
                    continue
                cr = str(d.get("cluster_risk") or "—")
                if cr not in ("HIGH", "MEDIUM"):
                    continue
                span = d.get("span_by_chain") if isinstance(d.get("span_by_chain"), dict) else {}
                def _span(ch: str) -> str:
                    x = span.get(ch) if isinstance(span, dict) else None
                    if isinstance(x, dict) and x.get("start_1based_min") is not None and x.get("end_1based_max") is not None:
                        return f"{x.get('start_1based_min')}–{x.get('end_1based_max')}"
                    return "—"

                regs = d.get("regions") if isinstance(d.get("regions"), dict) else {}
                reg_txt = "—"
                if regs:
                    try:
                        reg_txt = ", ".join(sorted(regs.keys(), key=lambda k: int(regs.get(k, 0)), reverse=True)[:4])
                    except Exception:
                        reg_txt = ", ".join(list(regs.keys())[:4])

                rows.append({
                    "cid": str(cid_raw),
                    "cluster_risk": cr,
                    "n_peptides": d.get("n_peptides", "—"),
                    "vh_span": _span("VH"),
                    "vl_span": _span("VL"),
                    "regions": reg_txt,
                    "top_peptide": d.get("top_peptide", "—"),
                    "top_region": d.get("top_region", "—"),
                })
            if rows:
                lines.append("")
                lines.append("### ：（ cluster）")
                lines.append("")
                lines.append("| cluster_id | cluster_risk | n_peptides | VH span | VL span | regions | top_peptide | top_region |")
                lines.append("|:---:|:---:|---:|:---|:---|:---|:---|:---|")
                for r in rows:
                    lines.append(
                        "| {cid} | {cluster_risk} | {n_peptides} | {vh_span} | {vl_span} | {regions} | `{top_peptide}` | {top_region} |".format(
                            **r
                        )
                    )
        rps = det.get("risk_positions") or []
        if rps:
            lines.append("")
            lines.append("### （chain / region /  / risk / cluster）")
            lines.append("")
            lines.append("| chain | region |  | risk | cluster_id |")
            lines.append("|:---|:---|:---|:---|---:|")
            for e in rps[:20]:
                lo = e.get("start_1based", "—")
                hi = e.get("end_1based", "—")
                lines.append(f"| {e.get('chain','—')} | {e.get('region','—')} | {lo}–{hi} | {e.get('risk','—')} | {e.get('cluster_id','—')} |")
            if len(rps) > 20:
                lines.append(f"| … | … | … | … | （ {len(rps)} ） |")
        tops = det.get("top_epitopes") or []
        if tops:
            lines.append("")
            lines.append("### Top （peptide / chain / n_alleles / risk）")
            lines.append("")
            lines.append("| peptide | chain | region | n_alleles/27 | risk |")
            lines.append("|:---|:---|:---|---:|---|")
            for ep in tops[:5]:
                lines.append(f"| `{ep.get('peptide','—')}` | {ep.get('chain','—')} | {ep.get('region','—')} | {ep.get('n_alleles','—')} | {ep.get('risk','—')} |")
        flgs = det.get("flags") or []
        if flgs:
            lines.append("")
            lines.append("### ")
            for f in flgs:
                lines.append(f"- {f}")
    return "\n".join(lines) + "\n"


def _get_immunogenicity_detail(
    results: Optional[Dict[str, Any]],
    enrich: bool = False,
) -> Optional[Dict[str, Any]]:
    """Extract immunogenicity computation detail from _internal.evaluation_*.results.immunogenicity."""
    if not results:
        return None
    internal = results.get("_internal") or {}
    if not isinstance(internal, dict):
        return None
    final = str(results.get("_meta", {}).get("final_version", "v3") or "v3")
    ev_key = f"evaluation_{final}"
    ev = internal.get(ev_key) or {}
    res = ev.get("results") or {}
    imm = res.get("immunogenicity") or ev.get("immunogenicity") or {}
    if not imm:
        for k in ("evaluation_v3", "evaluation_v2", "evaluation_v1"):
            ev = internal.get(k) or {}
            res = ev.get("results") or {}
            imm = res.get("immunogenicity") or ev.get("immunogenicity") or {}
            if imm:
                break
    if not imm:
        return None
    summary = imm.get("summary") if isinstance(imm.get("summary"), dict) else {}
    out: Dict[str, Any] = dict(summary) if summary else {}
    if imm.get("top_epitopes"):
        out["top_epitopes"] = imm["top_epitopes"]
    if imm.get("tcia_score") is not None:
        out["tcia_score"] = round(imm["tcia_score"], 4)
    if imm.get("n_epitopes") is not None:
        out["n_epitopes"] = imm["n_epitopes"]
    if imm.get("n_clusters") is not None:
        out["n_clusters"] = imm["n_clusters"]
    if imm.get("cluster_summary") is not None:
        out["cluster_summary"] = imm["cluster_summary"]
    if imm.get("funnel_stats") is not None:
        out["funnel_stats"] = imm["funnel_stats"]

    # IMPORTANT: export-internal must be "no recompute" by default.
    # Enrichment (offline recompute) is only allowed when explicitly requested.
    if enrich and (not out.get("funnel_stats")) and results:
        try:
            vh_seq, vl_seq = _read_sequences_from_results(results)
            if vh_seq:
                from core.immunogenicity.mhcii_analyzer import MHCII_Analyzer  # noqa: PLC0415

                # Prefer the same cluster count as the snapshot, if present
                ncl = imm.get("n_clusters")
                analyzer = MHCII_Analyzer(
                    vh_seq=vh_seq,
                    vl_seq=vl_seq,
                    use_iedb=False,
                    n_clusters=int(ncl) if isinstance(ncl, int) and ncl > 0 else 5,
                )
                rr = analyzer.run()
                out["funnel_stats"] = getattr(rr, "funnel_stats", {}) or {}
                # Enriched cluster_summary contains spans/regions (developer audit)
                out["cluster_summary"] = getattr(rr, "cluster_summary", {}) or out.get("cluster_summary", {})
        except Exception:
            pass
    return out if out else None


def _render_internal_md_structures(struct: Dict, results: Optional[Dict[str, Any]] = None) -> str:
    lines = ["# ", ""]
    for k, v in (struct or {}).items():
        if v:
            lines.append(f"- **{k}**: `{v}`")
    # ：
    detail = _get_structure_detail(results)
    if detail:
        lines.append("")
        lines.append("## ：")
        lines.append("")
        lines.append("- ****: ABodyBuilder2（IMGT numbering）")
        lines.append("- ****: `scripts/structure_metrics_humanization.analyze_structure`")
        lines.append("- ****: PDB 、VH/VL chain ID")
        lines.append("")
        lines.append("### （ evaluation ）")
        lines.append("")
        lines.append("| version | PDB | vh_vl_angle_deg | interface_n_pairs | vernier_sasa_total | vdn_len | angle_delta | cdr_rmsd_max | cdr_rmsd_pass | canonical_match | conclusion |")
        lines.append("|:---|:---|---:|---:|---:|---:|---:|---:|:---:|:---:|:---|")
        for row in detail.get("rows", [])[:6]:
            lines.append(
                "| {ver} | {pdb} | {ang} | {np} | {sasa} | {vdn} | {ad} | {rm} | {rp} | {cm} | {cc} |".format(
                    ver=row.get("version", "—"),
                    pdb=row.get("pdb_short", "—"),
                    ang=row.get("angle", "—"),
                    np=row.get("n_pairs", "—"),
                    sasa=row.get("sasa", "—"),
                    vdn=row.get("vdn_len", "—"),
                    ad=row.get("angle_delta", "—"),
                    rm=row.get("cdr_rmsd_max", "—"),
                    rp=row.get("cdr_rmsd_pass", "—"),
                    cm=row.get("canonical_match", "—"),
                    cc=row.get("conclusion", "—"),
                )
            )
        can = detail.get("canonical")
        if isinstance(can, dict):
            lines.append("")
            lines.append("**Canonical classes**（ v1）: " + ", ".join(f"{k}={v}" for k, v in list(can.items())[:6]))

        # Vernier per-position evidence table (final version preferred)
        vtab = detail.get("vernier_table")
        if isinstance(vtab, list) and vtab:
            lines.append("")
            lines.append("### Vernier 22 （final ）")
            lines.append("")
            lines.append("| pos | tier | kabat | imgt | SASA | contact |")
            lines.append("|:---|:---:|---:|---:|---:|---:|")
            for r in vtab[:30]:
                if not isinstance(r, dict):
                    continue
                lines.append(
                    "| `{pos}` | {tier} | {kp} | {ip} | {sa} | {co} |".format(
                        pos=r.get("pos", "—"),
                        tier=r.get("tier", "—"),
                        kp=r.get("kabat_pos", "—"),
                        ip=r.get("imgt_pos", "—"),
                        sa=r.get("sasa", "—"),
                        co=r.get("contact", "—"),
                    )
                )
    return "\n".join(lines) + "\n"


def _get_structure_detail(results: Optional[Dict[str, Any]]) -> Optional[Dict[str, Any]]:
    """Extract structure metrics from _internal.evaluation_* for developer process."""
    if not results:
        return None
    internal = results.get("_internal") or {}
    if not isinstance(internal, dict):
        return None
    rows: List[Dict[str, Any]] = []
    vtab: List[Dict[str, Any]] = []
    for evk in ("evaluation_v1", "evaluation_v2", "evaluation_v3"):
        ev = internal.get(evk) or {}
        res = ev.get("results") or {}
        s13 = res.get("structure_13param") or {}
        m = s13.get("metrics") if isinstance(s13.get("metrics"), dict) else {}
        if not m:
            continue
        pdb = str(m.get("pdb_path", ""))
        pdb_short = pdb.split("/")[-1] if "/" in pdb else pdb.split("\\")[-1] if "\\" in pdb else pdb[-40:]
        ver = evk.replace("evaluation_", "")
        d = _audit_extract_delta(ev)
        angd = (d.get("vh_vl_angle") or {}) if isinstance(d.get("vh_vl_angle"), dict) else {}
        rows.append({
            "version": ver,
            "pdb_short": pdb_short[:50],
            "angle": round(m.get("vh_vl_angle_deg", 0), 1) if isinstance(m.get("vh_vl_angle_deg"), (int, float)) else "—",
            "n_pairs": m.get("interface_n_pairs", "—"),
            "sasa": round(m.get("vernier_sasa_total", 0), 1) if isinstance(m.get("vernier_sasa_total"), (int, float)) else "—",
            "vdn_len": len(m.get("vernier_dual_numbering") or []) if isinstance(m.get("vernier_dual_numbering"), list) else "—",
            "angle_delta": round(float(angd.get("delta")), 2) if isinstance(angd.get("delta"), (int, float)) else "—",
            "cdr_rmsd_max": round(float(d.get("cdr_rmsd_max")), 3) if isinstance(d.get("cdr_rmsd_max"), (int, float)) else "—",
            "cdr_rmsd_pass": d.get("cdr_rmsd_pass", "—"),
            "canonical_match": d.get("canonical_match_h1_h2_l1", "—"),
            "conclusion": d.get("conclusion", "—"),
        })
    can = None
    for evk in ("evaluation_v1", "evaluation_v2", "evaluation_v3"):
        ev = internal.get(evk) or {}
        m = (ev.get("results") or {}).get("structure_13param", {}).get("metrics") or {}
        if m.get("canonical"):
            can = m["canonical"]
            break

    # Build Vernier table from final version if possible (else v2→v1)
    final_v = str((results.get("_meta") or {}).get("final_version") or "v3")
    pick = None
    for k in (f"evaluation_{final_v}", "evaluation_v3", "evaluation_v2", "evaluation_v1"):
        ev = internal.get(k) or {}
        m = (ev.get("results") or {}).get("structure_13param", {}).get("metrics") or {}
        if isinstance(m, dict) and m.get("vernier_dual_numbering") and (m.get("vernier_sasa_per_residue") or m.get("vernier_packing")):
            pick = m
            break
    if isinstance(pick, dict):
        vdn = pick.get("vernier_dual_numbering") if isinstance(pick.get("vernier_dual_numbering"), list) else []
        sasa = pick.get("vernier_sasa_per_residue") if isinstance(pick.get("vernier_sasa_per_residue"), dict) else {}
        pack = pick.get("vernier_packing") if isinstance(pick.get("vernier_packing"), dict) else {}
        for it in vdn:
            if not isinstance(it, dict):
                continue
            ch = str(it.get("chain") or "—")
            kp = it.get("kabat_pos")
            try:
                kp_i = int(kp)
            except Exception:
                kp_i = None
            label = f"{ch}_{kp_i}" if kp_i is not None else "—"
            vtab.append({
                "pos": label,
                "tier": it.get("tier", "—"),
                "kabat_pos": kp_i if kp_i is not None else "—",
                "imgt_pos": it.get("imgt_pos", "—"),
                "sasa": round(float(sasa.get(label)), 2) if isinstance(sasa.get(label), (int, float)) else "—",
                "contact": round(float(pack.get(label)), 1) if isinstance(pack.get(label), (int, float)) else "—",
            })
        vtab.sort(key=lambda x: (str(x.get("pos", ""))))

    return {"rows": rows, "canonical": can, "vernier_table": vtab} if rows else None


def _render_internal_md_pairing(vh: str, vl: str, row: Any) -> str:
    lines = ["# VH/VL ", ""]
    lines.append(" Top3×Top3 ； VH+VL 。，。")
    lines.append("")
    lines.append(f"- **VH**：`{vh or '—'}`")
    lines.append(f"- **VL**：`{vl or '—'}`")
    lines.append("")
    if row:
        lines.append(f"- ****：（count={row.get('count','—')}）")
    else:
        lines.append("- ****：（，，）")
    return "\n".join(lines) + "\n"


def _render_internal_md_pairing_with_nine_table(
    cand: Dict, germ: Dict, ab_id: str, lookup_fn: Any,
) -> tuple[str, List[Dict[str, Any]]]:
    """Render pairing MD with full 9-combo table; return (md_str, json_rows)."""
    lines = ["# VH/VL （）", ""]
    vh_gene = str((germ or {}).get("VH_gene") or "")
    vl_gene = str((germ or {}).get("VL_gene") or "")
    vh_top = [x for x in (cand.get("VH_candidates") or [])[:3] if x.get("gene")]
    vl_top = [x for x in (cand.get("VL_candidates") or [])[:3] if x.get("gene")]
    PAIRING_BONUS = 5.0
    rows: List[Dict[str, Any]] = []
    lines.append("## Top3×Top3 ")
    lines.append("")
    lines.append("| # | VH | VL | composite_sum |  | count | score | selected |")
    lines.append("|---|:---|:---|---:|---|---|---:|:---|")
    for i, vh in enumerate(vh_top):
        for j, vl in enumerate(vl_top):
            vh_g = vh.get("gene", "")
            vl_g = vl.get("gene", "")
            composite_base = (vh.get("composite_score") or 0.0) + (vl.get("composite_score") or 0.0)
            pair_row = lookup_fn(vh_g, vl_g) if (vh_g and vl_g) else None
            hit = "" if pair_row else ""
            cnt = pair_row.get("count", "—") if pair_row else "—"
            sc = composite_base + (PAIRING_BONUS if pair_row else 0)
            sel = "✓" if (vh_g == vh_gene and vl_g == vl_gene) else ""
            lines.append(f"| {i*3+j+1} | {vh_g} | {vl_g} | {composite_base:.2f} | {hit} | {cnt} | {sc:.2f} | {sel} |")
            rows.append({"vh": vh_g, "vl": vl_g, "composite_sum": round(composite_base, 2), "pairing_hit": bool(pair_row), "count": pair_row.get("count") if pair_row else None, "score": round(sc, 2), "selected": sel == "✓"})
    lines.append("")
    lines.append(f"****：VH=`{vh_gene}` + VL=`{vl_gene}`")
    pair_row = lookup_fn(vh_gene, vl_gene) if (vh_gene and vl_gene) else None
    if pair_row:
        lines.append(f"- ：（count={pair_row.get('count','—')}）")
    else:
        lines.append("- ：（，，）")
    return "\n".join(lines) + "\n", rows


def _try_render_pdf(md_path: Path) -> None:
    """Best-effort PDF generation from MD."""
    try:
        from scripts.md_to_pdf import render_pdf  # noqa: PLC0415

        render_pdf(str(md_path))
    except Exception:
        pass


def _export_internal_snapshots(
    ab_id: str,
    project_dir: Path,
    results: Dict[str, Any],
    *,
    enrich_immuno: bool = False,
    skip_pdf: bool = True,
) -> None:
    """
    Export key intermediate artifacts to `project_dir/internal/` WITHOUT recomputation.
    Writes JSON + MD; optionally PDF when skip_pdf=False.
    """
    internal_dir = project_dir / "internal"
    internal_dir.mkdir(parents=True, exist_ok=True)

    germ = results.get("germline") if isinstance(results.get("germline"), dict) else {}
    vh_gene = str((germ or {}).get("VH_gene") or "")
    vl_gene = str((germ or {}).get("VL_gene") or "")

    muts = results.get("mutations") if isinstance(results.get("mutations"), dict) else {}
    dev = results.get("developability") if isinstance(results.get("developability"), dict) else {}
    imm = results.get("immunogenicity") if isinstance(results.get("immunogenicity"), dict) else {}
    struct = results.get("structure") if isinstance(results.get("structure"), dict) else {}
    cand = results.get("germline_candidates") if isinstance(results.get("germline_candidates"), dict) else {}

    def _write_md_pdf(base: str, md_content: str) -> None:
        md_path = internal_dir / f"{base}.md"
        _write_text(md_path, md_content)
        if not skip_pdf:
            _try_render_pdf(md_path)

    snapshot_payload = {
        "ab_id": ab_id,
        "generated_at": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        "germline": germ,
        "germline_candidates": cand,
        "mutations": muts,
        "developability": dev,
        "immunogenicity": imm,
        "structure": struct,
        "_internal_eval_keys": sorted(list((results.get("_internal") or {}).keys())) if isinstance(results.get("_internal"), dict) else [],
    }

    # 1) Consolidated snapshot — JSON, MD, PDF
    _write_json(internal_dir / f"{ab_id}_internal_snapshot.json", snapshot_payload)
    snapshot_md = [
        f"#  — {ab_id}",
        "",
        "、CMC、、、。",
        "",
        "---",
        "",
    ]
    snapshot_md.append(_render_internal_md_germline(germ, cand, ab_id).replace("# ", "## "))
    snapshot_md.append("---\n\n" + _render_internal_md_cmc((muts or {}).get("v2_to_v3") or [], results).replace("# CMC ", "## CMC "))
    snapshot_md.append("---\n\n" + _render_internal_md_developability(dev, results).replace("# ", "## "))
    snapshot_md.append(
        "---\n\n"
        + _render_internal_md_immunogenicity(imm, results, enrich=enrich_immuno).replace("# ", "## ")
    )
    snapshot_md.append("---\n\n" + _render_internal_md_structures(struct, results).replace("# ", "## "))
    try:
        from scripts.render_vhvl_v44_reports import _lookup_pairing as _pl  # noqa: PLC0415

        if cand and (cand.get("VH_candidates") or [])[:3] and (cand.get("VL_candidates") or [])[:3]:
            pm, _ = _render_internal_md_pairing_with_nine_table(cand, germ, ab_id, _pl)
            snapshot_md.append("---\n\n" + pm.replace("# VH/VL （）", "## VH/VL （）"))
        else:
            row = _pl(vh_gene, vl_gene) if (vh_gene and vl_gene) else None
            snapshot_md.append("---\n\n" + _render_internal_md_pairing(vh_gene, vl_gene, row).replace("# VH/VL ", "## VH/VL "))
    except Exception:
        snapshot_md.append("---\n\n## VH/VL \n\n（）")
    _write_md_pdf(f"{ab_id}_internal_snapshot", "\n".join(snapshot_md))

    # 2) Focused exports — each: JSON + MD (PDF skipped for speed)
    germ_payload = {"germline": germ, "germline_candidates": cand}
    _write_json(internal_dir / f"germline_selection_{ab_id}.json", germ_payload)
    _write_text(internal_dir / f"germline_selection_{ab_id}.md", _render_internal_md_germline(germ, cand, ab_id))

    cmc_payload = {"v2_to_v3": (muts or {}).get("v2_to_v3", [])}
    _write_json(internal_dir / f"cmc_mutations_{ab_id}.json", cmc_payload)
    _write_text(internal_dir / f"cmc_mutations_{ab_id}.md", _render_internal_md_cmc(cmc_payload.get("v2_to_v3") or [], results))

    _write_json(internal_dir / f"developability_{ab_id}.json", dev or {})
    _write_text(internal_dir / f"developability_{ab_id}.md", _render_internal_md_developability(dev, results))

    imm_detail = _get_immunogenicity_detail(results, enrich=enrich_immuno)
    imm_payload = dict(imm or {})
    if imm_detail:
        imm_payload["_computation_detail"] = imm_detail
    _write_json(internal_dir / f"immunogenicity_{ab_id}.json", imm_payload)
    _write_text(internal_dir / f"immunogenicity_{ab_id}.md", _render_internal_md_immunogenicity(imm, results, enrich=enrich_immuno))

    _write_json(internal_dir / f"structures_{ab_id}.json", struct or {})
    _write_text(internal_dir / f"structures_{ab_id}.md", _render_internal_md_structures(struct, results))

    # 3) Pairing lookup — with full 9-combo table when germline_candidates available
    try:
        from scripts.render_vhvl_v44_reports import _lookup_pairing as _pair_lookup  # noqa: PLC0415

        row = _pair_lookup(vh_gene, vl_gene) if (vh_gene and vl_gene) else None
        if cand and (cand.get("VH_candidates") or [])[:3] and (cand.get("VL_candidates") or [])[:3]:
            pairing_md, nine_rows = _render_internal_md_pairing_with_nine_table(cand, germ, ab_id, _pair_lookup)
            pairing_payload = {
                "vh_gene": vh_gene,
                "vl_gene": vl_gene,
                "match": row,
                "nine_combinations": nine_rows,
                "note": "match==None means not found. nine_combinations = Top3×Top3 lookup results.",
            }
            _write_text(internal_dir / f"pairing_lookup_{ab_id}.md", pairing_md)
        else:
            pairing_payload = {
                "vh_gene": vh_gene,
                "vl_gene": vl_gene,
                "match": row,
                "note": "match==None means not found in this pairing database (evidence missing; not a negative clinical conclusion).",
            }
            _write_text(internal_dir / f"pairing_lookup_{ab_id}.md", _render_internal_md_pairing(vh_gene, vl_gene, row))
        _write_json(internal_dir / f"pairing_lookup_{ab_id}.json", pairing_payload)
    except Exception as e:
        pairing_payload = {"vh_gene": vh_gene, "vl_gene": vl_gene, "match": None, "error": str(e)}
        _write_json(internal_dir / f"pairing_lookup_{ab_id}.json", pairing_payload)
        _write_text(internal_dir / f"pairing_lookup_{ab_id}.md", _render_internal_md_pairing(vh_gene, vl_gene, None))


def export_internal_only(ab_id: str, project_dir: Path, *, enrich_immuno: bool = False) -> int:
    """
    Export `project_dir/internal/` artifacts from existing `{ab_id}_results.json`.

    This is a **lightweight** developer/audit action:
    - reads results.json
    - renders internal JSON + MD + PDF (and phase4 md/pdf when available)
    - does NOT run verify gates, does NOT call AbEvaluator, does NOT run round2 rescue
    """
    project_dir = Path(project_dir)
    results_path = project_dir / f"{ab_id}_results.json"
    if not results_path.exists():
        print(f"[export-internal] missing results json: {results_path}")
        return 2

    results = _load_json(results_path)

    # Phase4 backmutation log → MD/PDF (if present)
    try:
        p4 = _phase4_json_path(project_dir, ab_id)
        if p4 is not None:
            phase4 = _load_json(p4)
            md_text = _render_phase4_md(phase4, results=results)
            md_path = project_dir / "internal" / f"phase4_backmutation_{ab_id}.md"
            _write_text(md_path, md_text)
            _try_render_pdf(md_path)
    except Exception as e:
        print(f"[export-internal] phase4 render failed: {e}")

    # Core internal exports
    try:
        _export_internal_snapshots(
            ab_id=ab_id,
            project_dir=project_dir,
            results=results,
            enrich_immuno=bool(enrich_immuno),
        )
    except Exception as e:
        print(f"[export-internal] internal snapshot export failed: {e}")
        return 2

    return 0


def _fix_progress(step: int, total: int, msg: str) -> None:
    print(f"[fix] {step}/{total} {msg}", flush=True)


def _fix_stage_result(msg: str) -> None:
    """Print stage result summary (human-readable)."""
    print(f"  → {msg}", flush=True)


def verify(
    ab_id: str,
    project_dir: Path,
    fix: bool = False,
    use_iedb: bool = False,
    skip_pdf: bool = True,
) -> int:
    problems: List[str] = []
    warnings: List[str] = []

    project_dir = Path(project_dir)
    results_path = project_dir / f"{ab_id}_results.json"
    if not results_path.exists():
        problems.append(f"missing_results_json:{results_path}")
        print("\n".join(problems))
        return 2

    if not CFG_V44.exists():
        problems.append(f"missing_v44_config:{CFG_V44}")
        print("\n".join(problems))
        return 2

    results = _load_json(results_path)
    cfg = _load_json(CFG_V44)

    def _write_verify_audit_record(status: str) -> None:
        """
        Always write a machine-readable audit record for this verify run.
        This is developer-only (internal), not shipped to customers.
        """
        try:
            out = project_dir / "internal" / f"verify_audit_{ab_id}.json"
            v44_rows, v44_sum = _build_v44_checklist_audit(
                ab_id=ab_id,
                project_dir=project_dir,
                results=results,
                cfg=cfg,
            )
            payload = {
                "antibody_id": ab_id,
                "generated_at": datetime.now().isoformat(timespec="seconds"),
                "fix_mode": bool(fix),
                "status": status,
                "problems": list(problems),
                "warnings": list(warnings),
                "final_version": str((results.get("_meta") or {}).get("final_version") or ""),
                "structure_paths": results.get("structure") if isinstance(results.get("structure"), dict) else {},
                "mutations_v2_to_v3_count": len(((results.get("mutations") or {}).get("v2_to_v3") or [])),
                "v44_checklist": {
                    "summary": v44_sum,
                    "items": v44_rows,
                },
            }
            _write_json(out, payload)
        except Exception:
            # Best effort: audit record must not crash verification.
            pass

    # HARD GATE (pre-fix): CDR union must be present and preserved.
    # This must run BEFORE report/PDF/package generation so invalid projects do not produce deliverables.
    try:
        problems.extend(_cdr_union_gate_or_problem(results=results, cfg=cfg))
    except Exception as e:
        problems.append(f"cdr_union_gate_error:{e}")
    if problems:
        # Fail fast in fix mode to avoid producing reports on invalid sequences.
        if fix:
            print("❌ V4.4 （）：")
            for x in problems:
                print(" - " + x)
            _write_verify_audit_record(status="FAIL")
            return 1

        # (Optional) fix: render report + package (+ optional PDF)
    if fix:
        _fix_progress(1, 11, "CDR ")
        # ：v2  = v1 + v1_to_v2， v2=v1  Round 2 
        try:
            if _reconcile_v2_sequence(results):
                _write_json(results_path, results)
                warnings.append("sequences:v2_reconciled_from_v1_to_v2")
        except Exception as e:
            warnings.append(f"v2_reconcile_error:{e}")
        # CMC design: when pI > 8.5, design v3 via FR-only pI-lowering; run full developability + immunogenicity
        _fix_progress(2, 11, "CMC pI …")
        try:
            results, cmc_notes = _run_cmc_design_if_needed(
                ab_id=ab_id,
                project_dir=project_dir,
                results=results,
                results_path=results_path,
                target_pi_max=8.5,
                use_iedb=use_iedb,
            )
            warnings.extend(cmc_notes)
            pi_block = (results.get("developability") or {}).get("pI") or {}
            pi_v3 = pi_block.get("v3") or pi_block.get("v2") or pi_block.get("v1")
            if any("cmc_design:done" in str(n) for n in cmc_notes):
                n_mut = len((results.get("mutations") or {}).get("v2_to_v3") or [])
                _fix_stage_result(f"CMC pI  v3，{n_mut} ，pI≈{pi_v3}" if pi_v3 else f"CMC pI  v3，{n_mut} ")
            elif any("skip" in str(n) for n in cmc_notes) or (pi_v3 and float(pi_v3) <= 8.5):
                _fix_stage_result("pI ，" if pi_v3 else "pI ，")
            else:
                _fix_stage_result(f"pI {pi_v3}（ 5.5–8.5），" if pi_v3 else "pI ，")
        except Exception as e:
            warnings.append(f"cmc_design_error:{e}")
            _fix_stage_result(f": {e}")

        _fix_progress(3, 11, "CMC liability …")
        # CMC liability design (new in V4.4 extension):
        # If enabled (default True), automatically mitigate FR liabilities (N-gly, deamidation, isomerization).
        # This runs AFTER pI design, so it modifies the v3 sequence further.
        try:
            results, liab_notes = _run_cmc_liability_design_if_needed(
                ab_id=ab_id,
                project_dir=project_dir,
                results=results,
                results_path=results_path,
                fr_only=True,
            )
            warnings.extend(liab_notes)
            if any("applied" in str(n) for n in liab_notes):
                n_mut = next((int(n.split("_")[-1].split(":")[0]) for n in liab_notes if "applied_" in str(n)), 0)
                _fix_stage_result(f"FR ，{n_mut} ")
            elif any("skip" in str(n) for n in liab_notes):
                _fix_stage_result(" FR ，")
            else:
                _fix_stage_result(" liability ")
        except Exception as e:
            warnings.append(f"cmc_liability_design_error:{e}")
            _fix_stage_result(f": {e}")

        _fix_progress(4, 11, "Phase4 …")
        # Always refresh internal audit artifacts for developer traceability
        try:
            p4 = _phase4_json_path(project_dir, ab_id)
            if p4 is not None:
                phase4 = _load_json(p4)
                md_text = _render_phase4_md(phase4, results=results)
                md_path = project_dir / "internal" / f"phase4_backmutation_{ab_id}.md"
                _write_text(md_path, md_text)
                _fix_stage_result(" phase4 ")
            else:
                _fix_stage_result(" phase4 ，")
        except Exception as e:
            warnings.append(f"phase4_md_write_failed:{e}")
            _fix_stage_result(f": {e}")

        _fix_progress(5, 11, "…")
        # Export other internal artifacts (template selection / CMC / immunogenicity / structure paths / pairing evidence)
        try:
            _export_internal_snapshots(
                ab_id=ab_id,
                project_dir=project_dir,
                results=results,
                enrich_immuno=False,
                skip_pdf=skip_pdf,
            )
        except Exception as e:
            warnings.append(f"internal_snapshot_export_failed:{e}")
        _fix_stage_result("internal/ （germline、CMC、developability、immunogenicity、structure、pairing）")

        _fix_progress(6, 11, "Vernier Round 2 （）…")
        # Phase 4–5 closed-loop: if structural fidelity fails, enable a second-round Vernier rescue.
        try:
            meta = results.get("_meta") or {}
            final_v = str(meta.get("final_version") or "").strip() or "v2"
            base_v = final_v if final_v in ("v1", "v2", "v3") else "v2"
            existing_round2 = None
            try:
                internal0 = results.get("_internal") if isinstance(results.get("_internal"), dict) else {}
                existing_round2 = internal0.get(f"evaluation_{base_v}_vernier_round2") if isinstance(internal0, dict) else None
            except Exception:
                existing_round2 = None

            should_run_round2 = True
            if isinstance(existing_round2, dict):
                note0 = (existing_round2.get("_internal_note") or {}).get("vernier_round2") if isinstance(existing_round2.get("_internal_note"), dict) else {}
                p4_now = _phase4_json_path(project_dir, ab_id)
                pdb_base_now = _find_version_pdb(project_dir, ab_id, base_v)
                if isinstance(note0, dict):
                    ok_base = str(note0.get("base_version") or "") == str(base_v)
                    ok_p4 = (p4_now is None) or (str(note0.get("phase4_source") or "") == str(p4_now))
                    ok_pdb = True
                    if pdb_base_now is not None:
                        ok_pdb = Path(str(note0.get("pdb_base") or "")).name == pdb_base_now.name
                    if ok_base and ok_p4 and ok_pdb:
                        warnings.append("vernier_round2:reuse_existing")
                        should_run_round2 = False
                        _fix_stage_result(" Vernier Round 2 ")

            payload2, notes2 = (None, [])
            if should_run_round2:
                payload2, notes2 = _round2_vernier_rescue(
                    ab_id=ab_id,
                    project_dir=project_dir,
                    results=results,
                    base_version=base_v,
                    max_steps=24,  # ：CDR/Vernier 
                    max_rounds=8,
                    max_per_round=4,
                )
                warnings.extend(notes2)
                if payload2:
                    d2 = _audit_extract_delta(payload2)
                    _fix_stage_result("Vernier Round 2： PASS" if _delta_pass(d2) else "Vernier Round 2：， WARN（）")
                else:
                    _fix_stage_result("Vernier Round 2：（ warnings）")
            if payload2 is not None:
                results.setdefault("_internal", {})
                if isinstance(results["_internal"], dict):
                    results["_internal"][f"evaluation_{base_v}_vernier_round2"] = payload2
                # If round2 reaches PASS, we store candidate v3_round2 sequences but do not rename customer-facing versions.
                d0 = _audit_extract_delta((results.get("_internal") or {}).get(f"evaluation_{base_v}"))
                d2 = _audit_extract_delta(payload2)
                if (not _delta_pass(d0)) and _delta_pass(d2):
                    note = (payload2.get("_internal_note") or {}).get("vernier_round2") if isinstance(payload2.get("_internal_note"), dict) else {}
                    if isinstance(note, dict):
                        results.setdefault("structure", {})
                        if isinstance(results["structure"], dict) and note.get("attempts"):
                            # point to the last PASS attempt pdb
                            for a in reversed(note.get("attempts") or []):
                                if isinstance(a, dict) and a.get("pass") and a.get("pdb"):
                                    results["structure"]["vernier_round2_pdb"] = str(a.get("pdb"))
                                    break
                    # Store sequences for developer traceability
                    try:
                        # The last attempt that passed contains applied steps, but not sequences; recompute deterministically from base.
                        seqs = results.get("sequences") or {}
                        mouse_vh = str(seqs.get("mouse_VH") or "")
                        mouse_vl = str(seqs.get("mouse_VL") or "")
                        base_vh = str(seqs.get(f"{base_v}_VH") or "")
                        base_vl = str(seqs.get(f"{base_v}_VL") or "")
                        if mouse_vh and mouse_vl and base_vh and base_vl:
                            from core.humanization.kabat_utils import get_kabat_numbering  # noqa: PLC0415
                            kd_mh = get_kabat_numbering(mouse_vh)
                            kd_ml = get_kabat_numbering(mouse_vl)
                            applied = (payload2.get("_internal_note") or {}).get("vernier_round2", {}).get("applied") if isinstance(payload2.get("_internal_note"), dict) else None
                            cur_vh, cur_vl = base_vh, base_vl
                            if isinstance(applied, list):
                                for it in applied:
                                    if not isinstance(it, dict):
                                        continue
                                    chain = it.get("chain")
                                    kp = int(it.get("kabat_pos") or 0)
                                    if chain == "VH" and kd_mh and kp:
                                        aa = kd_mh.get((kp, ""))
                                        if aa:
                                            cur_vh = _kabat_mutate_base(cur_vh, kp, aa)
                                    if chain == "VL" and kd_ml and kp:
                                        aa = kd_ml.get((kp, ""))
                                        if aa:
                                            cur_vl = _kabat_mutate_base(cur_vl, kp, aa)
                            seqs["vernier_round2_VH"] = cur_vh
                            seqs["vernier_round2_VL"] = cur_vl
                            results["sequences"] = seqs
                    except Exception as e:
                        warnings.append(f"vernier_round2:store_seq_failed:{e}")
                _write_json(results_path, results)
        except Exception as e:
            warnings.append(f"vernier_round2_error:{e}")

        # ：CDR/Vernier 
        meta_gate = results.get("_meta") or {}
        base_v_gate = str(meta_gate.get("final_version") or "").strip() or "v3"
        base_v_gate = base_v_gate if base_v_gate in ("v1", "v2", "v3") else "v3"
        internal_gate = results.get("_internal") or {}
        ev_r2 = internal_gate.get(f"evaluation_{base_v_gate}_vernier_round2") if isinstance(internal_gate, dict) else None
        ev_base = internal_gate.get(f"evaluation_{base_v_gate}") if isinstance(internal_gate, dict) else None
        effective_ev = ev_r2 if isinstance(ev_r2, dict) else ev_base
        d_gate = _audit_extract_delta(effective_ev)
        if not _delta_pass(d_gate):
            problems.append("structure_fidelity_gate_FAIL:CDR_or_Vernier_not_PASS")
            print("❌ （CDR/Vernier），。 Vernier 。")
            _write_verify_audit_record(status="FAIL")
            return 1

        # ：sequence_annotation  sequences ， CDR 
        try:
            _reconcile_sequence_annotation(results)
            _write_json(results_path, results)
        except Exception as e:
            warnings.append(f"sequence_annotation_reconcile_error:{e}")

        _fix_progress(7, 11, "V44 Audit MD…")
        _fix_stage_result("reports/*_V44_Audit.md")
        try:
            audit_text = _render_v44_audit_md(ab_id, project_dir, results)
            audit_path = project_dir / "reports" / f"{ab_id}_V44_Audit.md"
            _write_text(audit_path, audit_text)
            if not skip_pdf:
                try:
                    from scripts.md_to_pdf import render_pdf  # noqa: PLC0415
                    audit_pdf = project_dir / "reports" / f"{ab_id}_V44_Audit.pdf"
                    try:
                        if audit_pdf.exists():
                            audit_pdf.unlink()
                    except PermissionError:
                        pass
                    try:
                        render_pdf(str(audit_path), str(audit_pdf))
                    except PermissionError:
                        audit_pdf2 = project_dir / "reports" / f"{ab_id}_V44_Audit__new.pdf"
                        render_pdf(str(audit_path), str(audit_pdf2))
                except Exception as e:
                    warnings.append(f"audit_pdf_failed:{e}")
        except Exception as e:
            warnings.append(f"audit_md_write_failed:{e}")

        _fix_progress(8, 11, " MD…")
        _fix_stage_result("reports/*_Client_zh.md")
        try:
            from scripts.render_vhvl_v44_reports import main as _render_main  # noqa: PLC0415
            # Reuse CLI main by emulating argv
            old = sys.argv[:]
            # Always pass an absolute path so render_vhvl_v44_reports.py won't double-join SUITE.
            sys.argv = ["render_vhvl_v44_reports.py", ab_id, str(project_dir.resolve()), "--write"]
            _render_main()
            sys.argv = old
        except Exception as e:
            problems.append(f"fix_render_failed:{e}")

        if not skip_pdf:
            _fix_progress(9, 11, " PDF…")
            try:
                from scripts.md_to_pdf import render_pdf  # noqa: PLC0415
                md = project_dir / "reports" / f"{ab_id}_Client_zh.md"
                pdf = project_dir / "reports" / f"{ab_id}_Client_zh.pdf"
                if md.exists():
                    try:
                        try:
                            if pdf.exists():
                                pdf.unlink()
                        except PermissionError:
                            pass
                        try:
                            pdf2_old = project_dir / "reports" / f"{ab_id}_Client_zh__new.pdf"
                            if pdf2_old.exists():
                                pdf2_old.unlink()
                        except PermissionError:
                            pass
                        render_pdf(str(md), str(pdf))
                    except PermissionError:
                        pdf2 = project_dir / "reports" / f"{ab_id}_Client_zh__new.pdf"
                        render_pdf(str(md), str(pdf2))
                else:
                    problems.append(f"fix_missing_client_md:{md}")
            except Exception as e:
                problems.append(f"fix_pdf_failed:{e}")
        else:
            _fix_progress(9, 11, " PDF（）")
            _fix_stage_result("PDF （， --pdf ）")

        _fix_progress(10, 11, "…")
        try:
            from scripts.package_delivery import package_delivery  # noqa: PLC0415
            out_dir = package_delivery(ab_id, project_dir, make_zip=False)
            try:
                rel = out_dir.relative_to(project_dir)
            except ValueError:
                rel = out_dir
            _fix_stage_result(f": {rel}")
        except Exception as e:
            problems.append(f"fix_package_failed:{e}")
            _fix_stage_result(f": {e}")

        _fix_progress(11, 11, "…")

    # 1) Dual-scheme numbering QA (sequence-level)
    try:
        from core.qa.pipeline_qa import PipelineQA  # noqa: PLC0415
        vh_seq, vl_seq = _read_sequences_from_results(results)
        qa = PipelineQA(project=ab_id, step="verify_dual_scheme_numbering")
        ok1 = qa.check_dual_scheme_numbering("vh", vh_seq, chain="VH")
        ok2 = qa.check_dual_scheme_numbering("vl", vl_seq, chain="VL")
        rep = qa.finalize(output_seq=vh_seq + "|" + vl_seq)
        if not (ok1 and ok2) or rep.n_fail:
            problems.append("dual_scheme_numbering_FAIL")
    except Exception as e:
        problems.append(f"dual_scheme_numbering_error:{e}")

    # 2) Structure metrics vernier dual numbering
    try:
        meta = results.get("_meta") or {}
        final_v = str(meta.get("final_version") or "").strip() or "v3"
        base_v = final_v if final_v in ("v1", "v2", "v3") else "v3"

        # Prefer the *base version* PDB to avoid mismatched reuse checks
        pdb_h = _find_version_pdb(project_dir, ab_id, base_v) or _find_best_pdb(project_dir, ab_id, "humanized")
        pdb_m = _find_version_pdb(project_dir, ab_id, "mouse") or _find_best_pdb(project_dir, ab_id, "mouse")
        if pdb_h is None or pdb_m is None:
            problems.append(f"missing_pdbs:humanized={pdb_h},mouse={pdb_m}")
        else:
            # Prefer reuse of existing evaluation_{base_v} to avoid recomputation.
            if _can_reuse_structure_eval(results, base_v, pdb_h):
                pass
            else:
                # Or reuse existing evaluation_verify_struct if it matches this PDB and has full dual numbering.
                internal = results.get("_internal") if isinstance(results.get("_internal"), dict) else {}
                ev_vs = internal.get("evaluation_verify_struct") if isinstance(internal, dict) else None
                can_reuse_vs = False
                if _extract_vernier_dual_numbering_len(ev_vs) == 22:
                    try:
                        m0 = (((ev_vs or {}).get("results") or {}).get("structure_13param") or {}).get("metrics") or {}
                        if isinstance(m0, dict) and _pdb_paths_match(str(m0.get("pdb_path") or ""), pdb_h):
                            can_reuse_vs = True
                    except Exception:
                        can_reuse_vs = False

                if can_reuse_vs:
                    pass
                else:
                    from core.evaluation.evaluator import AbEvaluator, AntibodyType  # noqa: PLC0415

                    ev = AbEvaluator(
                        project_name=f"{ab_id}_verify_struct",
                        pdb_path=str(pdb_h),
                        vh_chain="H",
                        vl_chain="L",
                        ab_type=AntibodyType.HUMANIZED,
                        strict_qa=False,
                    )
                    r = ev.run(modules=["structure_13param"])
                    m = (r.results.get("structure_13param") or {}).get("metrics") or {}
                    vdn = m.get("vernier_dual_numbering") or []
                    if len(vdn) != 22:
                        problems.append(f"vernier_dual_numbering_incomplete:{len(vdn)}")

                    # Persist verification run for future reuse
                    results.setdefault("_internal", {})
                    if isinstance(results.get("_internal"), dict):
                        results["_internal"]["evaluation_verify_struct"] = _eval_to_payload(r)
                    _write_json(results_path, results)
    except Exception as e:
        problems.append(f"structure_13param_error:{e}")

    # 3) Client report gate checks
    try:
        from scripts.render_vhvl_v44_reports import render_client_zh, run_pre_delivery_gate_report_checks  # noqa: PLC0415
        md_text = render_client_zh(results, cfg)
        fails = run_pre_delivery_gate_report_checks(results, md_text)
        if fails:
            problems.append("client_report_gate_FAIL:" + ",".join(fails))
        for t in FORBIDDEN_TERMS:
            if t in md_text:
                problems.append(f"client_report_forbidden_term:{t}")
    except Exception as e:
        problems.append(f"client_report_error:{e}")

    # 3b) Internal traceability: Phase 4 Vernier/back-mutation decision log
    # Not delivered to customer, but should exist for auditability.
    try:
        p4_candidates = []
        # Prefer project-local fixed path if present
        p4_candidates.append(project_dir / "internal" / f"phase4_backmutation_{ab_id}.json")
        p4_candidates.append(project_dir / "internal" / f"phase4_backmutation_{ab_id.lower()}.json")
        p4_candidates.append(project_dir / "reports" / f"phase4_backmutation_{ab_id}.json")
        p4_candidates.append(project_dir / "reports" / f"phase4_backmutation_{ab_id.lower()}.json")
        # Backward-compatibility: root-level legacy
        p4_candidates.append(SUITE / f"phase4_backmutation_{ab_id}.json")
        p4_candidates.append(SUITE / f"phase4_backmutation_{ab_id.lower()}.json")

        p4 = next((p for p in p4_candidates if p.exists()), None)
        if p4 is None:
            warnings.append("missing_phase4_backmutation_log")
        else:
            obj = _load_json(p4)
            rows = obj.get("backmutation_decisions") or []
            if len(rows) != 22:
                warnings.append(f"phase4_backmutation_decisions_not_22:{len(rows)}:{p4.relative_to(SUITE)}")
    except Exception as e:
        warnings.append(f"phase4_backmutation_log_error:{e}")

    # 4) Delivery directory whitelist
    final_delivery_dir = SUITE / f"delivery_{ab_id}"
    build_delivery_dir = SUITE / f"delivery_{ab_id}__build"

    def _check_delivery_dir(root: Path) -> List[str]:
        errs: List[str] = []
        required = {
            root / "README.md",
            root / "sequences" / f"{ab_id}_sequences.fasta",
            root / "structures" / f"{ab_id}_mouse.pdb",
            root / "structures" / f"{ab_id}_humanized_final.pdb",
            root / "reports" / f"{ab_id}_Client_zh.pdf",
        }
        optional = {root / "reports" / f"{ab_id}_Client_en.pdf"}
        allowed = set(required) | set(optional)
        #  structures/  PDB（）
        struct_dir = root / "structures"
        if struct_dir.exists():
            for st in struct_dir.glob("*.pdb"):
                allowed.add(st)

        for p in sorted(required):
            if not p.exists():
                errs.append(f"delivery_missing_required:{p.relative_to(SUITE)}")

        for p in root.rglob("*"):
            if p.is_file() and p not in allowed:
                errs.append(f"delivery_extra_file:{p.relative_to(SUITE)}")

        return errs

    final_errs: List[str] = []
    if final_delivery_dir.exists():
        final_errs = _check_delivery_dir(final_delivery_dir)
        problems.extend(final_errs)
    else:
        problems.append(f"missing_delivery_dir:{final_delivery_dir}")

    # If final delivery dir cannot be refreshed (Windows file lock), allow build dir as fallback
    if problems and build_delivery_dir.exists():
        build_errs = _check_delivery_dir(build_delivery_dir)
        if not build_errs:
            # Only allow fallback when final dir issues are missing/absent, not "extra file leakage"
            has_extra = any("delivery_extra_file:" in p for p in final_errs)
            if not has_extra:
                problems = [p for p in problems if not (p.startswith("delivery_missing_required:") or p.startswith("missing_delivery_dir:"))]
                warnings.append(f"delivery_fallback_in_use:{build_delivery_dir.relative_to(SUITE)}")

    if problems:
        print("❌ V4.4 ：")
        for x in problems:
            print(" - " + x)
        _write_verify_audit_record(status="FAIL")
        return 1

    if warnings:
        print("⚠️  ，：")
        for w in warnings:
            print(" - " + w)

    print("✅ V4.4 ")
    _write_verify_audit_record(status="PASS" if not warnings else "PASS_WITH_WARN")
    return 0


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("antibody_id")
    ap.add_argument("project_dir")
    ap.add_argument("--fix", action="store_true")
    ap.add_argument("--use-iedb", action="store_true", help="Enable live IEDB API for immunogenicity (CMC design eval)")
    args = ap.parse_args()
    return verify(args.antibody_id, Path(args.project_dir), fix=args.fix, use_iedb=getattr(args, "use_iedb", False))


if __name__ == "__main__":
    raise SystemExit(main())

