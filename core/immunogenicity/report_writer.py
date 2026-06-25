"""
immunogenicity/report_writer.py — InSynBio AbEngineCore v1.4
=============================================================
Results-only report formatter for MHC-II immunogenicity analysis.

OUTPUT CONTRACT
---------------
Client-facing sections contain ONLY:
  • Overall risk verdict
  • Risk position count and location (chain / region)
  • Tolerated position count
  • Cluster count (hotspot map)
  • Recommended action

Sections that are EXCLUDED from client output:
  • Algorithm names and versions
  • Prediction scores / IC50 / percent-rank values
  • Allele panel details
  • Hydrophilicity / tolerance numeric values
  • Pipeline step descriptions

Internal (JSON) output retains full data for audit purposes.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from core.immunogenicity.mhcii_analyzer import MHCII_Result

# ─────────────────────────────────────────────────────────────────────────────
# Risk labels
# ─────────────────────────────────────────────────────────────────────────────

_RISK_EMOJI = {"HIGH": "🔴", "MEDIUM": "🟡", "LOW": "🟢", "UNKNOWN": "⚪"}

_RISK_ACTION = {
    "HIGH": (
        "，，"
        "。"
    ),
    "MEDIUM": (
        "，T，"
        "。"
    ),
    "LOW": (
        "，。"
        "。"
    ),
    "UNKNOWN": "（API），。",
}


# ─────────────────────────────────────────────────────────────────────────────
# Public API
# ─────────────────────────────────────────────────────────────────────────────

def format_immunogenicity_section(result: "MHCII_Result") -> str:
    """
    Return a Markdown section (str) containing ONLY result values.
    No algorithm details, no numeric scores, no pipeline descriptions.
    """
    risk = result.risk_level
    icon = _RISK_EMOJI.get(risk, "⚪")

    # ── Counts ──────────────────────────────────────────────────────────────
    # High/Medium risk positions in hydrophilic FR (non-germline)
    risk_eps = [
        e for e in result.all_epitopes
        if not e.is_germline
        and e.risk in ("HIGH", "MEDIUM")
        and "FR" in e.region
        and e.hydrophilicity > -0.5
    ]
    n_high = sum(1 for e in risk_eps if e.risk == "HIGH")
    n_med  = sum(1 for e in risk_eps if e.risk == "MEDIUM")

    # Tolerated positions (germline-matching strong binders)
    n_tolerated = sum(
        1 for e in result.all_epitopes
        if e.is_germline and e.risk in ("HIGH", "MEDIUM")
    )

    # Cluster count (hotspots in FR surface)
    n_clusters = sum(
        1 for cid, d in result.cluster_summary.items()
        if d.get("cluster_risk") in ("HIGH", "MEDIUM")
    )

    # ── Risk position table ──────────────────────────────────────────────────
    position_rows: list[str] = []
    seen: set[str] = set()
    for e in sorted(risk_eps, key=lambda x: (x.risk != "HIGH", x.chain, x.start)):
        key = f"{e.chain}-{e.region}-{e.start}"
        if key in seen:
            continue
        seen.add(key)
        position_rows.append(
            f"| {e.chain} | {e.region} |  {e.start + 1}–{e.start + len(e.peptide)} | {e.risk} |"
        )
        if len(position_rows) >= 20:
            break

    # ── Assembly ────────────────────────────────────────────────────────────
    # VHH-specific logic: check for AUDIT flags (stability-induced epitopes)
    is_vhh_audit = any("AUDIT:" in f for f in result.flags)
    
    if is_vhh_audit:
        risk_label = "AUDIT (Stability-Induced)"
        icon = "ℹ️"
        risk_action = (
            "（Hallmark/Stealth）。 VHH ，"
            "。。"
        )
    else:
        risk_label = risk
        risk_action = _RISK_ACTION.get(risk, "")

    lines = [
        "## ",
        "",
        f"****: {icon} **{risk_label}**",
        "",
        "|  |  |",
        "|------|------|",
        f"| （FR） | {n_high} |",
        f"| （FR） | {n_med} |",
        f"| （，） | {n_tolerated} |",
        f"|  | {n_clusters} |",
        "",
    ]

    if position_rows:
        lines += [
            "### ",
            "",
            "|  |  |  |  |",
            "|----|------|------|------|",
        ]
        lines += position_rows
        lines.append("")

    lines += [
        "### ",
        "",
        risk_action,
        "",
    ]

    return "\n".join(lines)


def format_immunogenicity_json(result: "MHCII_Result") -> dict:
    """
    Return a compact JSON-serialisable dict for internal storage.
    Full data retained (audit trail), but structured for downstream use.
    """
    risk_eps = [
        e for e in result.all_epitopes
        if not e.is_germline
        and e.risk in ("HIGH", "MEDIUM")
        and "FR" in e.region
        and e.hydrophilicity > -0.5
    ]
    return {
        "risk_level": result.risk_level,
        "tcia_score": round(result.tcia_score, 4),
        "method": result.method,
        "n_alleles": len(result.alleles_used),
        "n_risk_positions_high": sum(1 for e in risk_eps if e.risk == "HIGH"),
        "n_risk_positions_medium": sum(1 for e in risk_eps if e.risk == "MEDIUM"),
        "n_tolerated": sum(
            1 for e in result.all_epitopes
            if e.is_germline and e.risk in ("HIGH", "MEDIUM")
        ),
        "n_clusters_high_medium": sum(
            1 for d in result.cluster_summary.values()
            if d.get("cluster_risk") in ("HIGH", "MEDIUM")
        ),
        "risk_positions": [
            {
                "chain": e.chain,
                "region": e.region,
                "start_1based": e.start + 1,
                "end_1based": e.start + len(e.peptide),
                "risk": e.risk,
                "cluster_id": e.cluster_id,
            }
            for e in risk_eps[:30]
        ],
        "flags": result.flags,
    }
