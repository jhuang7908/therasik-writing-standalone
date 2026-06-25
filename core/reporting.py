"""


humanize_vhh()JSONMarkdownHTML
"""

from __future__ import annotations

import json
import yaml
from datetime import datetime
from pathlib import Path
from typing import Dict, Any, Optional, Literal, List, Tuple

from core.config import get_config


def generate_markdown_report(
    result: Dict[str, Any],
    include_details: bool = True
) -> str:
    """
    Markdown
    
    Args:
        result: humanize_vhh()
        include_details: 
    
    Returns:
        Markdown
    """
    lines = []
    
    # 
    lines.append("# VHH Humanization Report")
    lines.append("")
    lines.append(f"**Generated:** {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    lines.append("")
    
    # 
    if not result.get("success", False):
        lines.append("## ❌ Humanization Failed")
        lines.append("")
        lines.append(f"**Error:** {result.get('error', 'Unknown error')}")
        return "\n".join(lines)
    
    # VHH
    lines.append("## Input VHH Sequence")
    lines.append("")
    
    input_info = result.get("input", {})
    vhh_seq = input_info.get("sequence", "")
    lines.append(f"- **Length:** {len(vhh_seq)} amino acids")
    lines.append(f"- **Source:** {input_info.get('source', 'Unknown')}")
    
    # VHH hallmark（FR2 only: IMGT 44/45/47; pos37 is CDR1, preserved by graft）
    hallmark = input_info.get("vhh_hallmark", {})
    if hallmark:
        lines.append("- **VHH Hallmark Positions (IMGT 44/45/47):**")
        lines.append(f"  - Position 44: {hallmark.get('aa44', 'N/A')}")
        lines.append(f"  - Position 45: {hallmark.get('aa45', 'N/A')}")
        lines.append(f"  - Position 47: {hallmark.get('aa47', 'N/A')}")
        lines.append(f"  - VHH Score: {hallmark.get('score', 0):.2f}")
    
    lines.append("")
    
    # 
    best_match = result.get("best_match")
    if best_match:
        lines.append("## Best Match Template")
        lines.append("")
        
        template = best_match.get("template", {})
        lines.append(f"- **Template ID:** `{template.get('template_id', 'N/A')}`")
        lines.append(f"- **Panel:** {template.get('panel', 'N/A')}")
        lines.append(f"- **Scaffold ID:** `{template.get('scaffold_id', 'N/A')}`")
        
        # Fallback
        if template.get("fallback", False):
            lines.append(f"- **⚠️ Fallback:** {template.get('fallback_reason', 'Unknown reason')}")
        
        # Developability
        dev = best_match.get("developability", {})
        if dev:
            grade = dev.get("grade", "N/A")
            grade_emoji = {"A": "✅", "B": "⚠️", "C": "❌"}.get(grade, "❓")
            lines.append(f"- **Developability Grade:** {grade_emoji} {grade}")
            lines.append(f"  - Score: {dev.get('score', 0):.2f}")
        
        # FR
        immuno = best_match.get("immunogenicity", {})
        if immuno:
            risk = immuno.get("fr_immuno_risk", "N/A")
            risk_emoji = {"low": "✅", "medium": "⚠️", "high": "❌"}.get(risk, "❓")
            lines.append(f"- **FR Immunogenicity Risk:** {risk_emoji} {risk}")
            lines.append(f"  - Hotspot Count: {immuno.get('fr_hotspot_count', 0)}")
        
        lines.append("")
        
        # 
        scoring = best_match.get("scoring", {})
        if scoring:
            lines.append("### Scoring Breakdown")
            lines.append("")
            lines.append("| Metric | Score |")
            lines.append("|--------|-------|")
            lines.append(f"| Framework Identity | {scoring.get('framework_identity', 0):.3f} |")
            lines.append(f"| CDR Compatibility | {scoring.get('cdr_compatibility_score', 0):.3f} |")
            lines.append(f"| Key Position Score | {scoring.get('key_position_score', 0):.3f} |")
            lines.append(f"| Developability Score | {scoring.get('developability_score', 0):.3f} |")
            
            penalty = scoring.get("fallback_penalty_factor", 1.0)
            if penalty < 1.0:
                lines.append(f"| Fallback Penalty | {penalty:.2f} |")
            
            lines.append(f"| **Combined Score** | **{scoring.get('combined_score', 0):.3f}** |")
            lines.append("")
        
        # 
        humanized = best_match.get("humanized_sequence", "")
        if humanized:
            lines.append("### Humanized Sequence")
            lines.append("")
            lines.append("```")
            lines.append(humanized)
            lines.append("```")
            lines.append("")
        
        # CDR
        cdrs = best_match.get("cdrs", {})
        if cdrs:
            lines.append("### CDR Information")
            lines.append("")
            for cdr_name in ["CDR1", "CDR2", "CDR3"]:
                cdr_info = cdrs.get(cdr_name.lower(), {})
                if cdr_info:
                    canonical = cdr_info.get("canonical_class", "Unknown")
                    length = cdr_info.get("length", 0)
                    lines.append(f"- **{cdr_name}:** Length={length}, Canonical={canonical}")
            lines.append("")
    
    # Framework Selection Rationale ()
    framework_rationale = _generate_framework_selection_rationale(result)
    if framework_rationale:
        lines.append(framework_rationale)
        lines.append("")
    
    # 
    quality_flags = result.get("quality_flags", {})
    risk_flags = result.get("risk_flags", {})
    
    warnings = []
    if quality_flags.get("cdr_compatibility_fallback"):
        warnings.append("⚠️ CDR compatibility fallback: Selected template has low CDR compatibility")
    
    if risk_flags.get("long_cdr3"):
        warnings.append("⚠️ Long CDR3 detected: May require special handling")
    
    if risk_flags.get("noncanonical_disulfide_suspected"):
        warnings.append("⚠️ Non-canonical disulfide bonds suspected in CDR3")
    
    dev_risk = best_match.get("developability", {}).get("risk", "")
    if dev_risk in ("medium", "high"):
        warnings.append(f"⚠️ Developability risk: {dev_risk}")
    
    immuno_risk = best_match.get("immunogenicity", {}).get("fr_immuno_risk", "")
    if immuno_risk in ("medium", "high"):
        warnings.append(f"⚠️ FR immunogenicity risk: {immuno_risk} - needs further validation")
    
    if warnings:
        lines.append("## ⚠️ Warnings and Risks")
        lines.append("")
        for warning in warnings:
            lines.append(f"- {warning}")
        lines.append("")
    
    # （）
    if include_details:
        lines.append("## Detailed Information")
        lines.append("")
        lines.append("<details>")
        lines.append("<summary>Click to expand</summary>")
        lines.append("")
        lines.append("```json")
        lines.append(json.dumps(result, indent=2, ensure_ascii=False))
        lines.append("```")
        lines.append("")
        lines.append("</details>")
    
    return "\n".join(lines)


def generate_html_report(
    result: Dict[str, Any],
    include_details: bool = True
) -> str:
    """
    HTML（SaaS）
    
    Args:
        result: humanize_vhh()
        include_details: 
    
    Returns:
        HTML
    """
    # markdown，
    try:
        import markdown
        HAS_MARKDOWN = True
    except ImportError:
        HAS_MARKDOWN = False
    
    md = generate_markdown_report(result, include_details)
    
    # markdown
    if HAS_MARKDOWN:
        html_body = markdown.markdown(
            md,
            extensions=['tables', 'fenced_code', 'codehilite', 'nl2br']
        )
    else:
        # 
        html_body = _markdown_to_html_simple(md)
    
    # HTML
    html = f"""<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>VHH Humanization Report</title>
    <style>
        body {{
            font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
            max-width: 1200px;
            margin: 0 auto;
            padding: 20px;
            line-height: 1.6;
            background-color: #f5f5f5;
        }}
        .container {{
            background-color: white;
            padding: 30px;
            border-radius: 8px;
            box-shadow: 0 2px 4px rgba(0,0,0,0.1);
        }}
        h1 {{ color: #2c3e50; border-bottom: 3px solid #3498db; padding-bottom: 10px; }}
        h2 {{ color: #34495e; margin-top: 30px; border-left: 4px solid #3498db; padding-left: 15px; }}
        h3 {{ color: #7f8c8d; }}
        table {{
            border-collapse: collapse;
            width: 100%;
            margin: 15px 0;
            box-shadow: 0 1px 3px rgba(0,0,0,0.1);
        }}
        th, td {{
            border: 1px solid #ddd;
            padding: 12px;
            text-align: left;
        }}
        th {{
            background-color: #3498db;
            color: white;
            font-weight: 600;
        }}
        tr:nth-child(even) {{
            background-color: #f9f9f9;
        }}
        code {{
            background-color: #f4f4f4;
            padding: 2px 6px;
            border-radius: 3px;
            font-family: 'Courier New', monospace;
            font-size: 0.9em;
        }}
        pre {{
            background-color: #f4f4f4;
            padding: 15px;
            border-radius: 5px;
            overflow-x: auto;
            border-left: 4px solid #3498db;
        }}
        .warning {{ color: #e67e22; font-weight: 600; }}
        .error {{ color: #e74c3c; font-weight: 600; }}
        .success {{ color: #27ae60; font-weight: 600; }}
        .badge {{
            display: inline-block;
            padding: 4px 8px;
            border-radius: 4px;
            font-size: 0.85em;
            font-weight: 600;
        }}
        .badge-success {{
            background-color: #27ae60;
            color: white;
        }}
        .badge-warning {{
            background-color: #e67e22;
            color: white;
        }}
        .badge-error {{
            background-color: #e74c3c;
            color: white;
        }}
    </style>
</head>
<body>
<div class="container">
{html_body}
</div>
</body>
</html>"""
    
    return html


def _markdown_to_html_simple(md: str) -> str:
    """MarkdownHTML（）"""
    html = md
    
    # 
    html = html.replace("# ", "<h1>").replace("\n# ", "</h1>\n<h1>")
    html = html.replace("## ", "<h2>").replace("\n## ", "</h2>\n<h2>")
    html = html.replace("### ", "<h3>").replace("\n### ", "</h3>\n<h3>")
    
    # 
    html = html.replace("**", "<strong>").replace("**", "</strong>")
    
    # 
    import re
    html = re.sub(r'```([^`]+)```', r'<pre><code>\1</code></pre>', html, flags=re.DOTALL)
    html = re.sub(r'`([^`]+)`', r'<code>\1</code>', html)
    
    # 
    html = html.replace("\n- ", "\n<li>")
    html = re.sub(r'(<li>.*</li>)', r'<ul>\1</ul>', html, flags=re.DOTALL)
    
    # 
    html = re.sub(r'\|(.+)\|', r'<tr><td>\1</td></tr>', html)
    html = html.replace("|", "</td><td>")
    
    # 
    html = html.replace("\n", "<br>\n")
    
    return html


def save_report(
    result: Dict[str, Any],
    output_path: Optional[Path] = None,
    format: Literal["markdown", "html", "json"] = "markdown"
) -> Path:
    """
    
    
    Args:
        result: humanize_vhh()
        output_path: （None，）
        format: 
    
    Returns:
        
    """
    cfg = get_config()
    
    if output_path is None:
        # 
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        template_id = result.get("best_match", {}).get("template", {}).get("template_id", "unknown")
        filename = f"vhh_humanization_{template_id}_{timestamp}.{format}"
        output_path = cfg.reporting.output_dir / filename
    
    # 
    output_path.parent.mkdir(parents=True, exist_ok=True)
    
    # 
    if format == "markdown":
        content = generate_markdown_report(result)
        output_path = output_path.with_suffix(".md")
    elif format == "html":
        content = generate_html_report(result)
        output_path = output_path.with_suffix(".html")
    elif format == "json":
        content = json.dumps(result, indent=2, ensure_ascii=False)
        output_path = output_path.with_suffix(".json")
    else:
        raise ValueError(f"Unsupported format: {format}")
    
    # 
    with open(output_path, "w", encoding="utf-8") as f:
        f.write(content)
    
    return output_path


def _generate_framework_selection_rationale(result: Dict[str, Any]) -> str:
    """
     Framework Selection Rationale 
    
    Args:
        result: humanize_vhh()，ANARCII
        
    Returns:
        Markdown
    """
    lines = []
    lines.append("## Framework Selection Rationale")
    lines.append("")
    lines.append("**Note:** FR4 (J segments) are NOT part of the framework definition. ")
    lines.append("FR4 is selected separately as a compatible component based on selection rules.")
    lines.append("")
    
    # 
    input_info = result.get("input", {})
    query_seq = input_info.get("sequence", "")
    if not query_seq:
        lines.append("*Framework selection rationale requires query sequence information.*")
        return "\n".join(lines)
    
    # ANARCII（）
    numbering_result = result.get("numbering", {})
    if not numbering_result:
        # 
        numbering_result = result.get("anarcii_result", {})
    
    # 
    features = {
        "CDR-H3_length": _extract_cdr3_length(result),
        "predicted_pI": result.get("features", {}).get("predicted_pI"),
        "aggregation_risk": result.get("risk_flags", {}).get("aggregation_risk", False),
        "target_conc_mg_ml": result.get("features", {}).get("target_conc_mg_ml"),
        "format": result.get("features", {}).get("format"),
    }
    
    # 
    try:
        vh_frameworks, vl_frameworks = _load_framework_libraries()
        canonical_envelopes = _load_canonical_envelopes()
        fr4_segments = _load_fr4_segments()
        selection_rules = _load_selection_rules()
    except Exception as e:
        lines.append(f"*Error loading framework library: {e}*")
        return "\n".join(lines)
    
    # VHTop3
    vh_candidates = _generate_framework_candidates(
        chain="VH",
        query_seq=query_seq,
        numbering_result=numbering_result,
        frameworks=vh_frameworks,
        canonical_envelopes=canonical_envelopes.get("vh", {}),
        top_k=3
    )
    
    # VLTop3
    vl_candidates = _generate_framework_candidates(
        chain="VL",
        query_seq=query_seq,
        numbering_result=numbering_result,
        frameworks=vl_frameworks,
        canonical_envelopes=canonical_envelopes.get("vl", {}),
        top_k=3
    )
    
    # VH
    if vh_candidates:
        lines.append("### VH Framework Candidates (Top 3)")
        lines.append("")
        lines.append("| Rank | Framework ID | FR Identity | Canonical Match | Tags | Reason |")
        lines.append("|------|--------------|-------------|-----------------|------|--------|")
        for i, cand in enumerate(vh_candidates[:3], 1):
            framework_id = cand.get("framework_id", "N/A")
            fr_identity = cand.get("fr_identity", 0.0)
            canonical_match = cand.get("canonical_match", "TODO")
            tags = ", ".join(cand.get("tags", [])) or "—"
            reason = cand.get("reason", "—")
            lines.append(f"| {i} | `{framework_id}` | {fr_identity:.3f} | {canonical_match} | {tags} | {reason} |")
        lines.append("")
    
    # VL
    if vl_candidates:
        lines.append("### VL Framework Candidates (Top 3)")
        lines.append("")
        lines.append("| Rank | Framework ID | FR Identity | Canonical Match | Tags | Reason |")
        lines.append("|------|--------------|-------------|-----------------|------|--------|")
        for i, cand in enumerate(vl_candidates[:3], 1):
            framework_id = cand.get("framework_id", "N/A")
            fr_identity = cand.get("fr_identity", 0.0)
            canonical_match = cand.get("canonical_match", "TODO")
            tags = ", ".join(cand.get("tags", [])) or "—"
            reason = cand.get("reason", "—")
            lines.append(f"| {i} | `{framework_id}` | {fr_identity:.3f} | {canonical_match} | {tags} | {reason} |")
        lines.append("")
    
    # ，
    final_selection = _apply_selection_rules(
        vh_candidates=vh_candidates,
        vl_candidates=vl_candidates,
        features=features,
        selection_rules=selection_rules,
        fr4_segments=fr4_segments
    )
    
    # 
    lines.append("### Final Framework Selection")
    lines.append("")
    if final_selection.get("vh"):
        vh_sel = final_selection["vh"]
        lines.append(f"- **VH Framework:** `{vh_sel.get('framework_id', 'N/A')}`")
        lines.append(f"  - Selection reason: {vh_sel.get('reason', 'N/A')}")
    if final_selection.get("vl"):
        vl_sel = final_selection["vl"]
        lines.append(f"- **VL Framework:** `{vl_sel.get('framework_id', 'N/A')}`")
        lines.append(f"  - Selection reason: {vl_sel.get('reason', 'N/A')}")
    lines.append("")
    
    # FR4/J
    lines.append("### FR4/J Segment Selection")
    lines.append("")
    lines.append("**Important:** FR4 (J segments) are NOT part of the framework definition. ")
    lines.append("They are selected separately as compatible components based on selection rules.")
    lines.append("")
    if final_selection.get("fr4"):
        fr4_sel = final_selection["fr4"]
        if fr4_sel.get("heavy_j"):
            hj = fr4_sel["heavy_j"]
            lines.append(f"- **Heavy J Segment:** `{hj.get('j_segment_id', 'N/A')}`")
            lines.append(f"  - Reason: {hj.get('reason', 'N/A')}")
        if fr4_sel.get("light_j"):
            lj = fr4_sel["light_j"]
            lines.append(f"- **Light J Segment:** `{lj.get('j_segment_id', 'N/A')}`")
            lines.append(f"  - Reason: {lj.get('reason', 'N/A')}")
    lines.append("")
    
    return "\n".join(lines)


def _extract_cdr3_length(result: Dict[str, Any]) -> Optional[int]:
    """resultCDR-H3"""
    cdrs = result.get("best_match", {}).get("cdrs", {})
    cdr3_info = cdrs.get("cdr3", {}) or cdrs.get("CDR3", {})
    if cdr3_info:
        return cdr3_info.get("length")
    
    # segments
    segments = result.get("segments", {})
    cdr3_seq = segments.get("CDR3", "") or segments.get("cdr3", "")
    if cdr3_seq:
        return len(cdr3_seq)
    
    return None


def _load_framework_libraries() -> Tuple[List[Dict[str, Any]], List[Dict[str, Any]]]:
    """VHVL"""
    cfg = get_config()
    project_root = Path(cfg.paths.project_root) if hasattr(cfg.paths, "project_root") else Path(__file__).resolve().parents[1]
    
    vh_path = project_root / "core" / "data" / "framework_library" / "vh_frameworks.yaml"
    vl_path = project_root / "core" / "data" / "framework_library" / "vl_frameworks.yaml"
    
    vh_frameworks = []
    vl_frameworks = []
    
    if vh_path.exists():
        with open(vh_path, "r", encoding="utf-8") as f:
            data = yaml.safe_load(f)
            if data and "frameworks" in data:
                vh_frameworks = data["frameworks"]
    
    if vl_path.exists():
        with open(vl_path, "r", encoding="utf-8") as f:
            data = yaml.safe_load(f)
            if data and "frameworks" in data:
                vl_frameworks = data["frameworks"]
    
    return vh_frameworks, vl_frameworks


def _load_canonical_envelopes() -> Dict[str, Dict[str, Any]]:
    """canonical envelopes"""
    cfg = get_config()
    project_root = Path(cfg.paths.project_root) if hasattr(cfg.paths, "project_root") else Path(__file__).resolve().parents[1]
    
    path = project_root / "core" / "data" / "framework_library" / "canonical_envelopes.yaml"
    
    if not path.exists():
        return {"vh": {}, "vl": {}}
    
    with open(path, "r", encoding="utf-8") as f:
        data = yaml.safe_load(f)
        if data and "canonical_envelopes" in data:
            return {
                "vh": data["canonical_envelopes"].get("vh", {}),
                "vl": data["canonical_envelopes"].get("vl", {})
            }
    
    return {"vh": {}, "vl": {}}


def _load_fr4_segments() -> Dict[str, List[Dict[str, Any]]]:
    """FR4/J segments"""
    cfg = get_config()
    project_root = Path(cfg.paths.project_root) if hasattr(cfg.paths, "project_root") else Path(__file__).resolve().parents[1]
    
    path = project_root / "core" / "data" / "framework_library" / "fr4_j_segments.yaml"
    
    if not path.exists():
        return {"vh": [], "vl": []}
    
    with open(path, "r", encoding="utf-8") as f:
        data = yaml.safe_load(f)
        if data and "fr4_j_segments" in data:
            return {
                "vh": data["fr4_j_segments"].get("vh", []),
                "vl": data["fr4_j_segments"].get("vl", [])
            }
    
    return {"vh": [], "vl": []}


def _load_selection_rules() -> Dict[str, Any]:
    """"""
    cfg = get_config()
    project_root = Path(cfg.paths.project_root) if hasattr(cfg.paths, "project_root") else Path(__file__).resolve().parents[1]
    
    path = project_root / "core" / "policies" / "framework_selection_rules.yaml"
    
    if not path.exists():
        return {}
    
    with open(path, "r", encoding="utf-8") as f:
        return yaml.safe_load(f) or {}


def _generate_framework_candidates(
    chain: str,
    query_seq: str,
    numbering_result: Dict[str, Any],
    frameworks: List[Dict[str, Any]],
    canonical_envelopes: Dict[str, Any],
    top_k: int = 3
) -> List[Dict[str, Any]]:
    """
    （family -> canonical envelope -> FR identity）
    
    Args:
        chain: "VH"  "VL"
        query_seq: 
        numbering_result: ANARCII
        frameworks: 
        canonical_envelopes: canonical envelopes
        top_k: Top K
        
    Returns:
        ， framework_id, fr_identity, canonical_match, tags, reason
    """
    candidates = []
    
    # queryFR1-FR3（）
    query_fr_seq = _extract_query_fr1_fr3(query_seq, numbering_result)
    
    # querycanonical class（）
    query_canonical = _extract_query_canonical(numbering_result)
    
    for fw in frameworks:
        if fw.get("chain") != chain:
            continue
        
        framework_id = fw.get("framework_id", "")
        if not framework_id:
            continue
        
        # 1. Family（chain）
        family = fw.get("family", "")
        
        # 2. Canonical envelope
        canonical_match = "TODO"
        if framework_id in canonical_envelopes:
            fw_canonical = canonical_envelopes[framework_id].get("canonical", {})
            if query_canonical and fw_canonical:
                cdr1_match = query_canonical.get("cdr1") == fw_canonical.get("cdr1", {}).get("class")
                cdr2_match = query_canonical.get("cdr2") == fw_canonical.get("cdr2", {}).get("class")
                if cdr1_match and cdr2_match:
                    canonical_match = "✓ Match"
                elif cdr1_match or cdr2_match:
                    canonical_match = "Partial"
                else:
                    canonical_match = "No match"
            else:
                canonical_match = "TODO (canonical data unavailable)"
        else:
            canonical_match = "TODO (canonical envelope not defined)"
        
        # 3. FR1-3 identity
        fr_identity = 0.0
        fw_fr_seq = fw.get("fr_sequence_fr1_fr3", "")
        if query_fr_seq and fw_fr_seq and fw_fr_seq != "TODO":
            fr_identity = _calculate_fr_identity(query_fr_seq, fw_fr_seq)
        else:
            # ，
            fr_identity = 0.0
        
        # tags
        tags = fw.get("tags", [])
        
        # reason
        reason_parts = []
        if family:
            reason_parts.append(f"Family: {family}")
        if canonical_match.startswith("✓"):
            reason_parts.append("Canonical match")
        elif canonical_match == "TODO":
            reason_parts.append("Canonical: TODO")
        reason = "; ".join(reason_parts) if reason_parts else "Default selection"
        
        candidates.append({
            "framework_id": framework_id,
            "family": family,
            "fr_identity": fr_identity,
            "canonical_match": canonical_match,
            "tags": tags,
            "reason": reason
        })
    
    # FR identity
    candidates.sort(key=lambda x: x["fr_identity"], reverse=True)
    
    return candidates[:top_k]


def _extract_query_fr1_fr3(query_seq: str, numbering_result: Dict[str, Any]) -> Optional[str]:
    """queryFR1-FR3"""
    # numbering_resultsegments，
    segments = numbering_result.get("segments", {})
    if segments:
        fr1 = segments.get("FR1", "")
        fr2 = segments.get("FR2", "")
        fr3 = segments.get("FR3", "")
        if fr1 and fr2 and fr3:
            return fr1 + fr2 + fr3
    
    # 
    # ，IMGT
    return None


def _extract_query_canonical(numbering_result: Dict[str, Any]) -> Optional[Dict[str, str]]:
    """canonical class"""
    # numbering_resultcanonical，
    canonical = numbering_result.get("canonical", {})
    if canonical:
        return {
            "cdr1": canonical.get("cdr1", {}).get("class"),
            "cdr2": canonical.get("cdr2", {}).get("class")
        }
    
    return None


def _calculate_fr_identity(seq1: str, seq2: str) -> float:
    """identity"""
    if not seq1 or not seq2:
        return 0.0
    
    L = min(len(seq1), len(seq2))
    if L == 0:
        return 0.0
    
    same = sum(1 for i in range(L) if seq1[i] == seq2[i])
    return same / L


def _apply_selection_rules(
    vh_candidates: List[Dict[str, Any]],
    vl_candidates: List[Dict[str, Any]],
    features: Dict[str, Any],
    selection_rules: Dict[str, Any],
    fr4_segments: Dict[str, List[Dict[str, Any]]]
) -> Dict[str, Any]:
    """
    ，FR4/J
    
    Returns:
        {
            "vh": {...},
            "vl": {...},
            "fr4": {
                "heavy_j": {...},
                "light_j": {...}
            }
        }
    """
    result = {
        "vh": None,
        "vl": None,
        "fr4": {
            "heavy_j": {"j_segment_id": "hJH4", "reason": "Default selection"},
            "light_j": {"j_segment_id": "hJK1", "reason": "Default selection"}
        }
    }
    
    # （）
    rules = selection_rules.get("framework_selection_rules", {}).get("rules", [])
    
    # priority
    rules.sort(key=lambda r: r.get("priority", 999), reverse=False)
    
    # long_h3
    if features.get("CDR-H3_length", 0) > 18:
        for rule in rules:
            if rule.get("id") == "long_h3":
                action = rule.get("action", {})
                if action.get("type") == "override_fr4":
                    fr4 = action.get("fr4", {})
                    if fr4.get("heavy_j", {}).get("j_segment_id"):
                        result["fr4"]["heavy_j"] = {
                            "j_segment_id": fr4["heavy_j"]["j_segment_id"],
                            "reason": rule.get("reason", "Long H3 rule")
                        }
                break
    
    # high_concentration_or_aggregation
    if features.get("aggregation_risk") or features.get("target_conc_mg_ml", 0) >= 100:
        for rule in rules:
            if rule.get("id") == "high_concentration_or_aggregation":
                # VL
                result["fr4"]["light_j"]["reason"] = rule.get("reason", "High concentration/aggregation rule")
                break
    
    # ：Top1
    if vh_candidates:
        result["vh"] = {
            "framework_id": vh_candidates[0]["framework_id"],
            "reason": selection_rules.get("framework_selection_rules", {}).get("default_success", {}).get("reason", "Top candidate by FR identity")
        }
    
    if vl_candidates:
        result["vl"] = {
            "framework_id": vl_candidates[0]["framework_id"],
            "reason": selection_rules.get("framework_selection_rules", {}).get("default_success", {}).get("reason", "Top candidate by FR identity")
        }
    
    return result

