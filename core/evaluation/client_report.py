"""
client_report.py — InSynBio AbEngineCore Evaluation Module
===========================================================
Converts AbEvaluator results into client-facing 4-section developability reports.

Report sections (client language — no technical jargon):
  Section 1:     Production feasibility
  Section 2:     Storage stability
  Section 3:   Chemical degradation risk
  Section 4:     Immunogenicity safety

Design principles (algorithm / database confidentiality)
---------------------------------------------------------
  ✗ NEVER expose: SAP, GRAVY, p5–p95, AbRef-458, IEDB, SASA, ADI algorithm,
                  RMSD, Kabat, IMGT, ANARCII, pI acronym without explanation,
                  any ML model names, internal score names
  ✓ ALWAYS use:   plain-language descriptions of biological meaning
                  pass/warn/fail rendered as actionable conclusions
                  comparison framed as "versus marketed antibody standard"
                  professional bilingual (Chinese + English) where helpful

Entry points
------------
    generate_client_report(result, comparison=None, **kwargs) -> str (Markdown)
    write_client_report(result, path, comparison=None, **kwargs) -> Path
"""
from __future__ import annotations

from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional

# ─────────────────────────────────────────────────────────────────────────────
# Internal helpers
# ─────────────────────────────────────────────────────────────────────────────

_GATE_ICON = {"PASS": "✅", "WARN": "⚠️", "FAIL": "❌", "—": "—"}


def _gate_icon(gate: str) -> str:
    return _GATE_ICON.get(gate, "—")


def _fmt_val(v: Any, ndigits: int = 2) -> str:
    if v is None:
        return "—"
    if isinstance(v, list):
        return str(len(v))
    try:
        return str(round(float(v), ndigits))
    except (TypeError, ValueError):
        return str(v)


def _extract_cmc(result: Any) -> Dict[str, Any]:
    """Pull annotated metrics dict from an EvaluationResult."""
    cmc = result.results.get("cmc_advisor", {})
    return cmc.get("annotated", {})


def _extract_adi(result: Any) -> Optional[float]:
    cmc = result.results.get("cmc_advisor", {})
    return cmc.get("adi")


def _get_val(ann: Dict, metric: str) -> Optional[float]:
    entry = ann.get(metric, {})
    v = entry.get("value")
    if isinstance(v, list):
        return float(len(v))
    if v is None:
        return None
    try:
        return float(v)
    except (TypeError, ValueError):
        return None


def _get_gate(ann: Dict, metric: str) -> str:
    return ann.get(metric, {}).get("gate", "—")


def _immuno(result: Any) -> Dict[str, Any]:
    return result.results.get("immunogenicity", {})


def _cdr_scan(result: Any) -> Dict[str, Any]:
    return result.results.get("cdr_scan", {})


# ─────────────────────────────────────────────────────────────────────────────
# Section generators
# ─────────────────────────────────────────────────────────────────────────────

def _section_production(
    ann: Dict, ann_ref: Optional[Dict],
    ab_name: str, ref_name: str,
) -> List[str]:
    """Section 1: Production feasibility (pI, solubility, charge)."""
    lines: List[str] = ["## 、", ""]

    pi_val  = _get_val(ann, "pI")
    pi_gate = _get_gate(ann, "pI")
    nc_val  = _get_val(ann, "net_charge_pH7")
    nc_gate = _get_gate(ann, "net_charge_pH7")
    cp_val  = _get_val(ann, "charge_patch_max7")
    cp_gate = _get_gate(ann, "charge_patch_max7")

    # Human-readable pI interpretation
    if pi_val is not None:
        if 5.5 <= pi_val <= 9.5:
            pi_desc = "（5.5–9.5），"
        elif pi_val < 5.5:
            pi_desc = "（<5.5），"
        else:
            pi_desc = "（>9.5），"
    else:
        pi_desc = ""

    lines += [
        f"**（pI）** {_gate_icon(pi_gate)}: {_fmt_val(pi_val)} — {pi_desc}",
        "",
    ]

    if ann_ref and _get_val(ann_ref, "pI") is not None:
        pi_ref = _get_val(ann_ref, "pI")
        lines.append(f"> （{ref_name}）pI = {_fmt_val(pi_ref)}")
        lines.append("")

    # Net charge
    if nc_val is not None:
        if abs(nc_val) <= 5:
            nc_desc = f" {_fmt_val(nc_val, 1)}，，"
        elif nc_val > 5:
            nc_desc = f" +{_fmt_val(nc_val, 1)}，，"
        else:
            nc_desc = f" {_fmt_val(nc_val, 1)}，，"
        lines += [
            f"**（pH 7）** {_gate_icon(nc_gate)}: {nc_desc}",
            "",
        ]

    # Charge patches
    if cp_val is not None:
        if cp_gate == "PASS":
            cp_desc = "，"
        elif cp_gate == "WARN":
            cp_desc = "，"
        else:
            cp_desc = "，A"
        lines += [
            f"**** {_gate_icon(cp_gate)}: {cp_desc}",
            "",
        ]

    return lines


def _section_storage(
    ann: Dict, ann_ref: Optional[Dict],
    ab_name: str, ref_name: str,
) -> List[str]:
    """Section 2: Storage stability (instability index, hydrophobicity, charge symmetry, SAP)."""
    lines: List[str] = ["## 、", ""]

    ii_val  = _get_val(ann, "instability_index")
    ii_gate = _get_gate(ann, "instability_index")
    gr_val  = _get_val(ann, "GRAVY")
    gr_gate = _get_gate(ann, "GRAVY")
    hp_val  = _get_val(ann, "hydro_patch_max9")
    hp_gate = _get_gate(ann, "hydro_patch_max9")
    sap_val = _get_val(ann, "SAP_score")
    sap_gate= _get_gate(ann, "SAP_score")
    fa_val  = _get_val(ann, "Fv_charge_asymmetry")
    fa_gate = _get_gate(ann, "Fv_charge_asymmetry")

    # Instability index
    if ii_val is not None:
        if ii_val < 40:
            ii_desc = f"{_fmt_val(ii_val)} — ， 4°C  2 "
        elif ii_val < 50:
            ii_desc = f"{_fmt_val(ii_val)} — ，（、80），"
        else:
            ii_desc = f"{_fmt_val(ii_val)} — ，"
        lines += [
            f"**** {_gate_icon(ii_gate)}: {ii_desc}",
            "",
        ]

    # Hydrophobicity (GRAVY)
    if gr_val is not None:
        if -0.5 <= gr_val <= 0.0:
            gr_desc = f" {_fmt_val(gr_val)}，，"
        elif gr_val < -0.5:
            gr_desc = f"（{_fmt_val(gr_val)}），，"
        else:
            gr_desc = f"（{_fmt_val(gr_val)}），"
        lines += [
            f"**** {_gate_icon(gr_gate)}: {gr_desc}",
            "",
        ]

    # Surface hydrophobic patches
    if sap_val is not None:
        if sap_val <= 0.01:
            sap_desc = "，（95%）"
        elif sap_val < 0.30:
            sap_desc = "，"
        else:
            sap_desc = "，（>100 mg/mL），"
        lines += [
            f"**（）** {_gate_icon(sap_gate)}: {sap_desc}",
            "",
        ]
    elif hp_val is not None:
        if hp_gate == "PASS":
            hp_desc = f" {_fmt_val(hp_val)}，"
        else:
            hp_desc = f" {_fmt_val(hp_val)}，，"
        lines += [
            f"**** {_gate_icon(hp_gate)}: {hp_desc}",
            "",
        ]

    # Charge symmetry (Fv)
    if fa_val is not None:
        if fa_val <= 0.05:
            fa_desc = "VH/VL ，（95%）"
        elif fa_val < 0.20:
            fa_desc = "VH/VL ，"
        else:
            fa_desc = "VH/VL ，"
        lines += [
            f"**VH/VL ** {_gate_icon(fa_gate)}: {fa_desc}",
            "",
        ]

    if ann_ref:
        ref_ii = _get_val(ann_ref, "instability_index")
        ref_gr = _get_val(ann_ref, "GRAVY")
        if ref_ii is not None or ref_gr is not None:
            lines.append(f"> （{ref_name}）： {_fmt_val(ref_ii)}， {_fmt_val(ref_gr)}")
            lines.append("")

    return lines


def _section_chemical(
    ann: Dict, ann_ref: Optional[Dict],
    ab_name: str, ref_name: str,
) -> List[str]:
    """Section 3: Chemical degradation risk (deamidation, isomerization, oxidation, free_cys)."""
    lines: List[str] = ["## 、", ""]

    deam_val  = _get_val(ann, "deamidation_sites")
    deam_gate = _get_gate(ann, "deamidation_sites")
    isom_val  = _get_val(ann, "isomerization_sites")
    isom_gate = _get_gate(ann, "isomerization_sites")
    oxid_val  = _get_val(ann, "oxidation_sites")
    oxid_gate = _get_gate(ann, "oxidation_sites")
    fcys_val  = _get_val(ann, "free_cys")
    fcys_gate = _get_gate(ann, "free_cys")
    glyc_val  = _get_val(ann, "glycosylation_sites")
    glyc_gate = _get_gate(ann, "glycosylation_sites")

    # Deamidation (NG/NS motifs — Asn → Asp/isoAsp)
    if deam_val is not None:
        n = int(deam_val)
        if n == 0:
            d_desc = "（）"
        elif n <= 1:
            d_desc = f" {n} ，"
        elif n <= 3:
            d_desc = f" {n} ，（40°C/4）"
        else:
            d_desc = f" {n} （），CDR"
        lines += [
            f"**（）** {_gate_icon(deam_gate)}: {d_desc}",
            "",
        ]

    # Isomerization (DG/DS — Asp → isoAsp)
    if isom_val is not None:
        n = int(isom_val)
        if n == 0:
            i_desc = ""
        elif n <= 2:
            i_desc = f" {n} ，，pH"
        else:
            i_desc = f" {n} ，CDRDG/DS"
        lines += [
            f"**（）** {_gate_icon(isom_gate)}: {i_desc}",
            "",
        ]

    # Oxidation (Met/Trp)
    if oxid_val is not None:
        n = int(oxid_val)
        if n <= 2:
            o_desc = f" {n} ，，"
        elif n <= 6:
            o_desc = f" {n} ，（0.1–1 mM）"
        else:
            o_desc = f" {n} （），"
        lines += [
            f"**** {_gate_icon(oxid_gate)}: {o_desc}",
            "",
        ]

    # Free cysteines
    if fcys_val is not None:
        n = int(fcys_val)
        if n == 0:
            c_desc = "，"
        else:
            c_desc = f"{n} ，，"
        lines += [
            f"**** {_gate_icon(fcys_gate)}: {c_desc}",
            "",
        ]

    # Glycosylation (if applicable)
    if glyc_val is not None and glyc_val > 0:
        lines += [
            f"**** {_gate_icon(glyc_gate)}:  {int(glyc_val)} ，"
            "CHO",
            "",
        ]

    if ann_ref:
        ref_d = _get_val(ann_ref, "deamidation_sites")
        ref_i = _get_val(ann_ref, "isomerization_sites")
        if ref_d is not None or ref_i is not None:
            lines.append(
                f"> （{ref_name}）： {_fmt_val(ref_d, 0)}，"
                f" {_fmt_val(ref_i, 0)}"
            )
            lines.append("")

    return lines


def _section_immunogenicity(
    result: Any,
    ref_result: Optional[Any],
    ab_name: str,
    ref_name: str,
    evidence_context: Optional[Any] = None,
) -> List[str]:
    """Section 4: Immunogenicity safety — with evidence-gating integration."""
    lines: List[str] = ["## 、", ""]

    immuno = _immuno(result)
    cdr    = _cdr_scan(result)

    # ADA Evidence subsection (from EvidenceGate)
    if evidence_context is not None:
        tier = evidence_context.ada_tier
        tier_labels = {
            "TIER1": "Tier 1（）",
            "TIER2": "Tier 2（）",
            "TIER3": "Tier 3（）",
            "NOT_FOUND": "",
            "OFFLINE": "（）",
        }
        tier_label = tier_labels.get(tier, tier)
        lines += [
            "### （ADA）",
            "",
            f"****: {tier_label}",
            "",
        ]
        if evidence_context.ada_value:
            lines.append(f"** ADA **: {evidence_context.ada_value}")
            lines.append("")
        if evidence_context.ada_evidence:
            lines.append(f"****: {evidence_context.ada_evidence}")
            lines.append("")
        if tier == "TIER2":
            lines += [
                ("> ⚠️ ： ADA ，。"
                 "\u201c\u201d。"),
                "",
            ]
        elif tier == "TIER3":
            lines += [
                ("> ℹ️  ADA 。"
                 "，。"),
                "",
            ]
        elif tier in ("NOT_FOUND", "OFFLINE"):
            lines += [
                "> ℹ️  ADA 。",
                "",
            ]

    # Risk level from immunogenicity module
    risk_level = immuno.get("risk_level") or immuno.get("tcia_risk") or immuno.get("overall_risk")
    n_high     = immuno.get("n_high_risk_epitopes") or immuno.get("n_high", 0)
    n_med      = immuno.get("n_medium_risk_epitopes") or immuno.get("n_medium", 0)
    n_tol      = immuno.get("n_tolerated") or immuno.get("n_low", 0)
    action     = immuno.get("recommended_action") or immuno.get("action")

    if risk_level:
        risk_map = {
            "low":      ("", ""),
            "moderate": ("", "I"),
            "high":     ("", "IND"),
        }
        rl_lower = risk_level.lower().replace(" ", "_")
        rl_label, rl_advice = risk_map.get(rl_lower, (risk_level, ""))
        lines += [
            "### ",
            "",
            f"****: **{rl_label}**",
            "",
            f"- T: {n_high} ",
            f"- （）: {n_med} ",
            f"- : {n_tol} ",
            "",
            f"****: {rl_advice}",
            "",
        ]
        if action:
            lines += [f"****: {action}", ""]
    elif immuno.get("status") in ("SKIPPED", "PLANNED", None):
        lines += [
            "。INDT。",
            "",
        ]
    else:
        lines += [
            "，。",
            "",
        ]

    # CDR liabilities
    cdr_flags = cdr.get("flags", [])
    cdr_liabilities = [f for f in cdr_flags if "liability" in f.lower() or "WARN" in f or "FAIL" in f]
    if cdr_liabilities:
        lines += [
            "**CDR **:",
            "",
        ]
        for flag in cdr_liabilities[:5]:
            lines.append(f"- {flag}")
        lines.append("")

    # Reference comparison
    if ref_result:
        ref_immuno = _immuno(ref_result)
        ref_risk = ref_immuno.get("risk_level") or ref_immuno.get("tcia_risk") or ref_immuno.get("overall_risk")
        if ref_risk:
            lines.append(f"> （{ref_name}）: {ref_risk}")
            lines.append("")

    return lines


def _section_evidence_traceability(
    evidence_context: Optional[Any] = None,
) -> List[str]:
    """Section 5: Evidence traceability — data provenance for all cited references."""
    if evidence_context is None:
        return []

    lines: List[str] = [
        "---",
        "",
        "## 、",
        "",
    ]

    tier = evidence_context.ada_tier
    if tier == "TIER1":
        lines += [
            "**ADA **: Tier 1 \u2014 ",
            "",
            (" ADA （PMID） FDA ，"
             "，。"),
            "",
        ]
    elif tier == "TIER2":
        lines += [
            "**ADA **: Tier 2 \u2014 ",
            "",
            (" ADA  AI ，"
             "。 IND ，"
             "。"),
            "",
        ]
    elif tier == "TIER3":
        lines += [
            "**ADA **: Tier 3 \u2014 ",
            "",
            (" ADA 。"
             "\u201c\u201d，。"),
            "",
        ]
    else:
        lines += [
            "**ADA **: ",
            "",
            " InSynBio ADA 。",
            "",
        ]

    if evidence_context.pubmed_hits:
        lines += ["### （）", ""]
        for i, hit in enumerate(evidence_context.pubmed_hits[:3], 1):
            title = hit.get("title", "Unknown")
            pmid  = hit.get("pmid", "")
            lines.append(f"{i}. {title} (PMID: {pmid})")
        lines.append("")

    return lines


# ─────────────────────────────────────────────────────────────────────────────
# Main entry points
# ─────────────────────────────────────────────────────────────────────────────

def generate_client_report(
    result: Any,
    *,
    ref_result: Optional[Any] = None,
    ab_name: str = "",
    ref_name: str = "",
    client_name: str = "",
    project_id: str = "",
    date_str: Optional[str] = None,
    evidence_context: Optional[Any] = None,
) -> str:
    """
    Generate a 4-section client-facing developability report in Markdown.

    Parameters
    ----------
    result : EvaluationResult
        Primary antibody evaluation result (original or optimized).
    ref_result : EvaluationResult, optional
        Clinical reference antibody result for comparison rows.
    ab_name : str
        Display name of the candidate antibody.
    ref_name : str
        Display name of the reference/clinical antibody.
    client_name : str
        Client organisation name (for header).
    project_id : str
        Project identifier (for header).
    date_str : str, optional
        Report date string; defaults to today.
    evidence_context : EvidenceContext, optional
        Pre-flight evidence from EvidenceGate. When provided, Section 4
        renders Tier labels, PMID/FDA references, and data disclaimers.

    Returns
    -------
    str : Markdown text of the full client report.
    """
    date = date_str or datetime.now().strftime("%Y-%m-%d")

    ann     = _extract_cmc(result)
    ann_ref = _extract_cmc(ref_result) if ref_result else None
    adi     = _extract_adi(result)
    adi_ref = _extract_adi(ref_result) if ref_result else None

    from core.cmc.adi_score import adi_interpretation
    adi_label     = adi_interpretation(adi)     if adi     is not None else "—"
    adi_ref_label = adi_interpretation(adi_ref) if adi_ref is not None else "—"

    # ── Gate summary counts ────────────────────────────────────────────────
    gates = [ann.get(m, {}).get("gate", "—") for m in ann]
    n_pass = gates.count("PASS")
    n_warn = gates.count("WARN")
    n_fail = gates.count("FAIL")

    overall_icon = "✅" if n_fail == 0 and n_warn <= 2 else ("⚠️" if n_fail == 0 else "❌")

    # ── Header ────────────────────────────────────────────────────────────
    header = [
        f"# ",
        "",
        f"****: {ab_name}  ",
        f"****: {date}  ",
    ]
    if client_name:
        header.append(f"****: {client_name}  ")
    if project_id:
        header.append(f"****: {project_id}  ")
    header += [
        f"****: {ref_name}  ",
        "",
        "---",
        "",
    ]

    # ── Executive summary ─────────────────────────────────────────────────
    summary = [
        "## ",
        "",
        f"15， **{ab_name}** ，"
        f" **{ref_name}**（）。",
        "",
        f"|  | {ab_name} | {ref_name} |",
        "|---|---|---|",
        f"|  | **{_fmt_val(adi, 1)}** / 100（{adi_label}） "
        f"| {_fmt_val(adi_ref, 1)} / 100（{adi_ref_label}） |",
        f"|  | {n_pass}/{n_pass + n_warn + n_fail}  PASS "
        f"| — |",
        f"|  | {n_warn}  WARN，{n_fail}  FAIL | — |",
        f"|  | {overall_icon} | — |",
        "",
        "---",
        "",
    ]

    # ── Four sections ─────────────────────────────────────────────────────
    s1 = _section_production(ann, ann_ref, ab_name, ref_name)
    s2 = _section_storage(ann, ann_ref, ab_name, ref_name)
    s3 = _section_chemical(ann, ann_ref, ab_name, ref_name)
    s4 = _section_immunogenicity(result, ref_result, ab_name, ref_name,
                                  evidence_context=evidence_context)

    # ── Evidence traceability section ─────────────────────────────────────
    s5 = _section_evidence_traceability(evidence_context)

    # ── Footer ────────────────────────────────────────────────────────────
    footer = [
        "",
        "---",
        "",
        "## ",
        "",
        "- ，（SEC-HPLC、DLS、DSF、）。",
        "- 458。",
        "- ，。",
    ]
    if evidence_context and evidence_context.needs_disclaimer:
        footer += [
            "",
            ("> ****: （ADA）。"
             "\u201cTier 2\u201d，，。"
             "\u201cTier 3\u201d\u201c\u201d，"
             "。。"),
        ]
    footer += [
        "",
        f"*InSynBio AbEngineCore — : {datetime.now().strftime('%Y-%m-%d %H:%M')}*",
    ]

    all_lines: List[str] = (
        header + summary
        + s1 + ["---", ""]
        + s2 + ["---", ""]
        + s3 + ["---", ""]
        + s4
        + s5 + footer
    )
    return "\n".join(all_lines)


def write_client_report(
    result: Any,
    path: "str | Path",
    *,
    ref_result: Optional[Any] = None,
    ab_name: str = "",
    ref_name: str = "",
    client_name: str = "",
    project_id: str = "",
    date_str: Optional[str] = None,
    evidence_context: Optional[Any] = None,
) -> Path:
    """
    Write client report to *path* and return the resolved Path.

    All keyword arguments are forwarded to `generate_client_report`.
    """
    text = generate_client_report(
        result,
        ref_result=ref_result,
        ab_name=ab_name,
        ref_name=ref_name,
        client_name=client_name,
        project_id=project_id,
        date_str=date_str,
        evidence_context=evidence_context,
    )
    out = Path(path)
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(text, encoding="utf-8")
    print(f"[client_report] Written: {out}")
    return out
