"""
Suite-wide report format version (config/version_control.json) plus per-service
report versions. HTML generators should show suite version first, then service
name and its own report version, then protocol | analysis.
"""
from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Dict, List, Optional

_ROOT = Path(__file__).resolve().parents[1]
_VERSION_CONTROL = _ROOT / "config" / "version_control.json"

# Per-service *content* report versions (independent of suite shell in version_control).
# Bump when that service’s report sections / logic change.
_SERVICE_CATALOG: Dict[str, Dict[str, str]] = {
    # 2026-05-11: external-disclosure hardening:
    # - hide cohort IDs and cohort sizes in client-facing provenance block
    # - use panel type + frozen release ID only
    "vhvl_humanization": {
        "display": "VH/VL Humanization",
        "service_report_version": "v5.5.3",
    },
    "vhh_humanization": {
        "display": "VHH Humanization",
        "service_report_version": "v3.5",
    },
    "recheck_vhvl": {
        "display": "VH/VL Customer Recheck",
        "service_report_version": "v6.2",
    },
    "recheck_vhh": {
        "display": "VHH Customer Recheck",
        "service_report_version": "v6.2",
    },
    "vh_to_vhh": {
        "display": "VH→VHH Conversion",
        "service_report_version": "v1.8.17",
    },
    "cmc_igg": {
        "display": "IgG / VH+VL CMC Developability",
        "service_report_version": "v1.5",
    },
    "cmc_vhh": {
        "display": "VHH CMC Developability",
        "service_report_version": "v1.5",
    },
    "cmc_bispecific": {
        "display": "Bispecific VHH-linker-VHH CMC",
        "service_report_version": "v1.3",
    },
}


def export_service_report_versions() -> Dict[str, str]:
    """Keys match `_SERVICE_CATALOG` (underscore form); values are service report versions."""
    return {k: v["service_report_version"] for k, v in _SERVICE_CATALOG.items()}


def load_suite_versions() -> Dict[str, str]:
    """Read frozen suite identifiers from version_control.json (best-effort)."""
    defaults = {
        "protocol_version": "—",
        "analysis_version": "—",
        "report_format_version": "—",
        "build_id": "—",
        "environment": "—",
    }
    try:
        data = json.loads(_VERSION_CONTROL.read_text(encoding="utf-8"))
        out = dict(defaults)
        for k in defaults:
            if data.get(k) is not None:
                out[k] = str(data.get(k))
        return out
    except Exception:
        return defaults


def service_catalog_entry(service_key: str) -> Dict[str, str]:
    if service_key not in _SERVICE_CATALOG:
        return {"display": service_key, "service_report_version": "—"}
    return dict(_SERVICE_CATALOG[service_key])


def suite_service_meta_html(
    service_key: str,
    *,
    protocol_ver: Optional[str] = None,
    analysis_ver: Optional[str] = None,
    content_variant: Optional[str] = None,
    extra_inner_divs: Optional[List[str]] = None,
) -> str:
    """
    Return a `.header-meta` block: suite report format first, then service +
    service report version, then protocol | analysis, then optional lines.
    """
    import html as html_mod

    def esc(x: Any) -> str:
        return html_mod.escape(str(x if x is not None else "—"))

    suite = load_suite_versions()
    suite_rf = esc(suite["report_format_version"])
    pv = esc(protocol_ver if protocol_ver is not None else suite["protocol_version"])
    av = esc(analysis_ver if analysis_ver is not None else suite["analysis_version"])
    bd = esc(suite["build_id"])
    env = esc(suite["environment"])
    cat = service_catalog_entry(service_key)
    disp = esc(cat["display"])
    svr = esc(cat["service_report_version"])
    line2 = (
        f"<div><strong>Service</strong>: {disp} &nbsp;·&nbsp; "
        f"<strong>Service report</strong>: {svr}"
    )
    if content_variant:
        line2 += f" &nbsp;·&nbsp; <strong>Content variant</strong>: {esc(content_variant)}"
    line2 += "</div>"
    parts: List[str] = [
        f"<div><strong>Report format (suite)</strong>: {suite_rf}</div>",
        line2,
        f"<div><strong>Protocol</strong>: {pv} &nbsp;|&nbsp; <strong>Analysis</strong>: {av} "
        f"&nbsp;|&nbsp; <strong>Build</strong>: {bd} "
        f"&nbsp;|&nbsp; <strong>Environment</strong>: {env}</div>",
    ]
    if extra_inner_divs:
        parts.extend(extra_inner_divs)
    inner = "\n        ".join(parts)
    return f"""        <div class="header-meta">
        {inner}
        </div>"""


# ── Client-facing panel provenance (no cohort size/name disclosure) ────────
_BENCHMARK_RELEASE_ID = "R2026.05"

_SERVICE_PANEL_PROVENANCE: Dict[str, List[Dict[str, str]]] = {
    "vhvl_humanization": [
        {"panel_type": "Natural VH/VL benchmark panel", "purpose": "Human IgG natural-baseline VH/VL CMC distribution"},
        {"panel_type": "Engineered VH/VL benchmark panel", "purpose": "Engineered/clinical VH/VL reference"},
    ],
    "vhh_humanization": [
        {"panel_type": "Clinical VHH benchmark panel", "purpose": "Clinical/approved VHH developability baseline"},
        {"panel_type": "Structural VHH benchmark panel", "purpose": "VHH hallmark and structural context"},
    ],
    "recheck_vhvl": [
        {"panel_type": "Natural VH/VL benchmark panel", "purpose": "Human IgG natural-baseline VH/VL distribution"},
        {"panel_type": "Engineered VH/VL benchmark panel", "purpose": "Engineered/clinical VH/VL comparison"},
    ],
    "recheck_vhh": [
        {"panel_type": "Clinical VHH benchmark panel", "purpose": "Clinical/approved VHH cohort"},
        {"panel_type": "Structural VHH benchmark panel", "purpose": "Extended VHH structural context"},
    ],
    "vh_to_vhh": [
        {"panel_type": "Engineered single-domain benchmark panel", "purpose": "Autonomous VH/VHH-like framework reference"},
        {"panel_type": "Clinical VHH benchmark panel", "purpose": "Post-conversion single-domain comparison"},
        {"panel_type": "Structural VHH benchmark panel", "purpose": "Extended structural context"},
    ],
    "cmc_igg": [
        {"panel_type": "Engineered VH/VL benchmark panel", "purpose": "Engineered/clinical IgG VH/VL CMC reference"},
        {"panel_type": "Natural VH/VL benchmark panel", "purpose": "Human IgG natural-baseline distribution"},
    ],
    "cmc_vhh": [
        {"panel_type": "Clinical VHH benchmark panel", "purpose": "Clinical/approved VHH developability"},
        {"panel_type": "Structural VHH benchmark panel", "purpose": "VHH hallmark / FR2 / CDR context"},
        {"panel_type": "SASA VHH benchmark panel", "purpose": "SASA-based structural reference (psh / ppc / pnc / SAP-SASA)"},
    ],
    "cmc_bispecific": [
        {"panel_type": "Clinical VHH benchmark panel", "purpose": "Per-arm clinical VHH developability"},
        {"panel_type": "Structural VHH benchmark panel", "purpose": "Per-arm hallmark / FR2 context"},
    ],
}


def cohort_provenance_html(service_key: str) -> str:
    """
    Return a client-safe provenance block listing panel types only.
    Cohort IDs and cohort sizes are intentionally hidden.
    """
    import html as html_mod

    def esc(x: Any) -> str:
        return html_mod.escape(str(x if x is not None else "—"))

    panels = _SERVICE_PANEL_PROVENANCE.get(service_key) or []
    if not panels:
        return ""
    rows = "".join(
        f"<tr><td><strong>{esc(p['panel_type'])}</strong></td>"
        f"<td>{esc(_BENCHMARK_RELEASE_ID)}</td>"
        f"<td>{esc(p['purpose'])}</td></tr>"
        for p in panels
    )
    return (
        '<div class="cohort-provenance" '
        'style="margin:10px 0;padding:10px 14px;border:1px solid #cbd5e1;'
        'border-radius:6px;background:#f8fafc;font-size:.78rem;color:#1f2937">'
        '<div style="font-weight:600;color:#1e3a8a;margin-bottom:6px">'
        'Reference cohort provenance</div>'
        '<table style="width:100%;border-collapse:collapse;color:#1f2937">'
        f'<tr style="color:#475569;font-size:.72rem;text-align:left">'
        f'<th style="padding:2px 4px;color:#1e3a8a">Panel type</th>'
        f'<th style="padding:2px 4px;color:#1e3a8a">Release ID</th>'
        f'<th style="padding:2px 4px;color:#1e3a8a">Purpose in this report</th></tr>'
        f'<tbody style="color:#1f2937">{rows}</tbody>'
        '</table>'
        '<div style="margin-top:6px;color:#64748b;font-size:.72rem">'
        'Reference range derived from internal source-matched benchmark panel '
        f'(frozen release: {esc(_BENCHMARK_RELEASE_ID)}). Detailed cohort '
        'composition is confidential.'
        '</div></div>'
    )


def cmc_version_banner_html(
    service_key: str,
    *,
    protocol_ver: Optional[str] = None,
    analysis_ver: Optional[str] = None,
    content_variant: Optional[str] = None,
    extra_inner_divs: Optional[List[str]] = None,
    header_title: Optional[str] = None,
    header_subtitle: Optional[str] = None,
    right_stamp_html: Optional[str] = None,
) -> str:
    """VHH-humanization-style header shell for standalone CMC HTML."""
    inner = suite_service_meta_html(
        service_key,
        protocol_ver=protocol_ver,
        analysis_ver=analysis_ver,
        content_variant=content_variant,
        extra_inner_divs=extra_inner_divs,
    )
    title = header_title or "InSynBio AbEngineCore"
    subtitle = header_subtitle or service_catalog_entry(service_key).get("display", service_key)
    right = right_stamp_html or '<span style="font-size:.7rem;opacity:.6">CONFIDENTIAL</span>'
    return (
        '<div class="report-header" style="margin-bottom:20px">'
        '<div>'
        f'<h1>{title}</h1>'
        f'<div class="sub">{subtitle}</div>'
        f"{inner}"
        "</div>"
        f'<div class="ts">{right}</div>'
        "</div>"
    )
