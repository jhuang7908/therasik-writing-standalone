"""
VHH 

：
- （A/B/C）
- （ vs ）
- 
- （FR/CDR）
-  HTML 

：
- 
- （）
- 
"""

from __future__ import annotations

import html
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple


@dataclass
class SequencePanel:
    """"""
    name: str
    sequence: str
    regions: Dict[str, str]  # {"FR1": "...", "CDR1": "...", ...}
    mutations: List[Dict[str, Any]]  # 
    scores: Dict[str, float]  # 


@dataclass
class PanelComparison:
    """"""
    original: SequencePanel
    panel_a: SequencePanel
    panel_b: SequencePanel
    panel_c: SequencePanel


def extract_panel_from_result(
    result: Dict[str, Any],
    panel: str = "A",
) -> Optional[SequencePanel]:
    """
     result.json 
    
    Args:
        result: 
        panel: （"A", "B", "C"）
    
    Returns:
        SequencePanel ， None
    """
    #  result 
    #  result  panels 
    panels = result.get("panels", {}) or {}
    panel_data = panels.get(panel.upper(), {}) or {}
    
    #  panels， best_match
    if not panel_data:
        if panel.upper() == "A":
            #  A  best_match
            best_match = result.get("best_match", {}) or {}
            humanized_seq = best_match.get("humanized_sequence", "")
            humanized_regions = result.get("sequence_analysis", {}).get("humanized_regions", {}) or {}
        else:
            #  B/C （ result ）
            return None
    else:
        humanized_seq = panel_data.get("humanized_sequence", "")
        humanized_regions = panel_data.get("regions", {}) or {}
    
    # 
    seq_analysis = result.get("sequence_analysis", {}) or {}
    orig_regions = seq_analysis.get("original_regions", {}) or {}
    orig_seq = "".join([
        orig_regions.get("FR1", ""),
        orig_regions.get("CDR1", ""),
        orig_regions.get("FR2", ""),
        orig_regions.get("CDR2", ""),
        orig_regions.get("FR3", ""),
        orig_regions.get("CDR3", ""),
        orig_regions.get("FR4", ""),
    ])
    
    # 
    mutations = result.get("mutations", {}).get("list", []) or []
    
    # 
    scores = {}
    if panel_data:
        scores = {
            "fr_identity": panel_data.get("fr_identity", 0.0),
            "developability": panel_data.get("developability", {}).get("score", 0.0),
            "structural_risk": panel_data.get("structural_risk", 0.0),
        }
    else:
        best_match = result.get("best_match", {}) or {}
        best_scores = best_match.get("scores", {}) or {}
        scores = {
            "fr_identity": best_scores.get("fr_identity", 0.0),
            "developability": best_match.get("developability", {}).get("score", 0.0),
            "structural_risk": best_scores.get("structural_risk", 0.0),
        }
    
    return SequencePanel(
        name=f" {panel.upper()}",
        sequence=humanized_seq,
        regions=humanized_regions,
        mutations=mutations,
        scores=scores,
    )


def extract_original_panel(result: Dict[str, Any]) -> SequencePanel:
    """"""
    seq_analysis = result.get("sequence_analysis", {}) or {}
    orig_regions = seq_analysis.get("original_regions", {}) or {}
    
    orig_seq = "".join([
        orig_regions.get("FR1", ""),
        orig_regions.get("CDR1", ""),
        orig_regions.get("FR2", ""),
        orig_regions.get("CDR2", ""),
        orig_regions.get("FR3", ""),
        orig_regions.get("CDR3", ""),
        orig_regions.get("FR4", ""),
    ])
    
    return SequencePanel(
        name="",
        sequence=orig_seq,
        regions=orig_regions,
        mutations=[],
        scores={},
    )


def build_panel_comparison(result: Dict[str, Any]) -> PanelComparison:
    """"""
    original = extract_original_panel(result)
    panel_a = extract_panel_from_result(result, "A")
    panel_b = extract_panel_from_result(result, "B")
    panel_c = extract_panel_from_result(result, "C")
    
    # ，
    if panel_a is None:
        panel_a = SequencePanel(
            name=" A",
            sequence=original.sequence,
            regions=original.regions,
            mutations=[],
            scores={},
        )
    
    if panel_b is None:
        panel_b = SequencePanel(
            name=" B",
            sequence=original.sequence,
            regions=original.regions,
            mutations=[],
            scores={},
        )
    
    if panel_c is None:
        panel_c = SequencePanel(
            name=" C",
            sequence=original.sequence,
            regions=original.regions,
            mutations=[],
            scores={},
        )
    
    return PanelComparison(
        original=original,
        panel_a=panel_a,
        panel_b=panel_b,
        panel_c=panel_c,
    )


def render_sequence_html(
    panel: SequencePanel,
    highlight_mutations: bool = True,
    show_regions: bool = True,
) -> str:
    """
     HTML
    
    Args:
        panel: 
        highlight_mutations: 
        show_regions: 
    
    Returns:
        HTML 
    """
    seq = panel.sequence
    mutations = panel.mutations
    
    # 
    mutation_positions = {}
    for m in mutations:
        pos = m.get("position", 0)
        mutation_positions[pos] = m
    
    # 
    region_colors = {
        "FR1": "#E8F4F8",
        "CDR1": "#FFE6E6",
        "FR2": "#E8F4F8",
        "CDR2": "#FFE6E6",
        "FR3": "#E8F4F8",
        "CDR3": "#FFE6E6",
        "FR4": "#E8F4F8",
    }
    
    #  HTML
    html_parts = [f'<div class="sequence-panel" data-name="{html.escape(panel.name)}">']
    html_parts.append(f'<div class="sequence-header"><strong>{html.escape(panel.name)}</strong></div>')
    
    # （）
    if panel.scores:
        scores_html = []
        for key, value in panel.scores.items():
            scores_html.append(f'<span class="score">{key}: {value:.3f}</span>')
        html_parts.append(f'<div class="scores">{" | ".join(scores_html)}</div>')
    
    # 
    html_parts.append('<div class="sequence-display">')
    
    # 
    if show_regions and panel.regions:
        regions_order = ["FR1", "CDR1", "FR2", "CDR2", "FR3", "CDR3", "FR4"]
        current_pos = 1
        
        for region_name in regions_order:
            region_seq = panel.regions.get(region_name, "")
            if not region_seq:
                continue
            
            region_color = region_colors.get(region_name, "#FFFFFF")
            html_parts.append(f'<span class="region" data-region="{region_name}" style="background-color: {region_color};">')
            
            for i, aa in enumerate(region_seq):
                pos = current_pos + i
                is_mutation = pos in mutation_positions
                
                if is_mutation and highlight_mutations:
                    mutation = mutation_positions[pos]
                    from_aa = mutation.get("from", "")
                    to_aa = mutation.get("to", "")
                    html_parts.append(
                        f'<span class="aa mutation" data-pos="{pos}" title="Mutation: {from_aa}→{to_aa}">{html.escape(aa)}</span>'
                    )
                else:
                    html_parts.append(f'<span class="aa" data-pos="{pos}">{html.escape(aa)}</span>')
            
            html_parts.append('</span>')
            current_pos += len(region_seq)
    else:
        # 
        for i, aa in enumerate(seq, 1):
            is_mutation = i in mutation_positions
            
            if is_mutation and highlight_mutations:
                mutation = mutation_positions[i]
                from_aa = mutation.get("from", "")
                to_aa = mutation.get("to", "")
                html_parts.append(
                    f'<span class="aa mutation" data-pos="{i}" title="Mutation: {from_aa}→{to_aa}">{html.escape(aa)}</span>'
                )
            else:
                html_parts.append(f'<span class="aa" data-pos="{i}">{html.escape(aa)}</span>')
    
    html_parts.append('</div>')
    html_parts.append('</div>')
    
    return "\n".join(html_parts)


def render_comparison_html(comparison: PanelComparison) -> str:
    """ HTML"""
    html_parts = [
        '<div class="panel-comparison">',
        '<h2></h2>',
        '<div class="panels-grid">',
    ]
    
    # 
    html_parts.append(render_sequence_html(comparison.original, highlight_mutations=False))
    
    # 
    html_parts.append(render_sequence_html(comparison.panel_a))
    html_parts.append(render_sequence_html(comparison.panel_b))
    html_parts.append(render_sequence_html(comparison.panel_c))
    
    html_parts.append('</div>')
    html_parts.append('</div>')
    
    return "\n".join(html_parts)


def render_sequence_text(
    panel: SequencePanel,
    line_width: int = 80,
    show_mutations: bool = True,
) -> str:
    """
    
    
    Args:
        panel: 
        line_width: 
        show_mutations: 
    
    Returns:
        
    """
    lines = [f"{panel.name}:"]
    
    if panel.scores:
        scores_str = ", ".join([f"{k}: {v:.3f}" for k, v in panel.scores.items()])
        lines.append(f"  : {scores_str}")
    
    # （）
    seq = panel.sequence
    for i in range(0, len(seq), line_width):
        chunk = seq[i:i+line_width]
        pos_start = i + 1
        pos_end = min(i + line_width, len(seq))
        lines.append(f"  {pos_start:4d}-{pos_end:4d}: {chunk}")
    
    # 
    if show_mutations and panel.mutations:
        lines.append("  :")
        for m in panel.mutations:
            region = m.get("region", "N/A")
            pos = m.get("position", 0)
            from_aa = m.get("from", "")
            to_aa = m.get("to", "")
            lines.append(f"    {region} {pos}: {from_aa} → {to_aa}")
    
    return "\n".join(lines)


def render_comparison_text(comparison: PanelComparison) -> str:
    """"""
    lines = [
        "=" * 80,
        "VHH ",
        "=" * 80,
        "",
    ]
    
    lines.append(render_sequence_text(comparison.original, show_mutations=False))
    lines.append("")
    lines.append(render_sequence_text(comparison.panel_a))
    lines.append("")
    lines.append(render_sequence_text(comparison.panel_b))
    lines.append("")
    lines.append(render_sequence_text(comparison.panel_c))
    lines.append("")
    lines.append("=" * 80)
    
    return "\n".join(lines)


def save_panel_comparison_html(
    comparison: PanelComparison,
    output_path: Path,
    include_css: bool = True,
):
    """ HTML """
    html_content = render_comparison_html(comparison)
    
    if include_css:
        css = """
        <style>
        .panel-comparison {
            font-family: 'Courier New', monospace;
            margin: 20px;
        }
        .panels-grid {
            display: grid;
            grid-template-columns: 1fr;
            gap: 20px;
        }
        .sequence-panel {
            border: 1px solid #ddd;
            border-radius: 8px;
            padding: 15px;
            background: #f9f9f9;
        }
        .sequence-header {
            font-size: 16px;
            font-weight: bold;
            margin-bottom: 10px;
            color: #333;
        }
        .scores {
            font-size: 12px;
            color: #666;
            margin-bottom: 10px;
        }
        .score {
            margin-right: 15px;
        }
        .sequence-display {
            font-family: 'Courier New', monospace;
            font-size: 12px;
            line-height: 1.6;
            word-break: break-all;
        }
        .region {
            padding: 2px 4px;
            margin: 1px;
            border-radius: 3px;
        }
        .aa {
            display: inline-block;
            padding: 2px;
            margin: 1px;
        }
        .aa.mutation {
            background-color: #FFD700;
            font-weight: bold;
            border: 1px solid #FFA500;
        }
        </style>
        """
        html_content = f"<!DOCTYPE html>\n<html>\n<head>\n<meta charset='UTF-8'>\n{css}\n</head>\n<body>\n{html_content}\n</body>\n</html>"
    
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(html_content, encoding="utf-8")
    print(f"✅ Panel comparison HTML saved: {output_path}")


def save_panel_comparison_text(
    comparison: PanelComparison,
    output_path: Path,
):
    """"""
    text_content = render_comparison_text(comparison)
    
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(text_content, encoding="utf-8")
    print(f"✅ Panel comparison text saved: {output_path}")


def _build_sequence_block(name: str, seq: str) -> str:
    """"""
    if not seq:
        return f"### {name}\n\n```text\n()\n```\n"
    return f"### {name}\n\n```text\n{seq}\n```\n"


def _build_mutation_summary_row(
    name: str,
    strategy: Dict[str, Any],
    original_seq: str,
) -> str:
    """"""
    seq = strategy.get("sequence", "") or strategy.get("humanized_sequence", "")
    
    if not seq or not original_seq or len(seq) != len(original_seq):
        return f"| {name} | NA | NA | NA |"
    
    total = len(seq)
    mut_count = sum(1 for a, b in zip(seq, original_seq) if a != b)
    mut_pct = mut_count / total * 100 if total > 0 else 0
    
    # 
    structural_risk = strategy.get("structural_risk", {})
    if isinstance(structural_risk, dict):
        risk = structural_risk.get("total_risk", "NA")
    else:
        risk = structural_risk if structural_risk else "NA"
    
    if risk != "NA" and isinstance(risk, (int, float)):
        risk = f"{risk:.3f}"
    
    immuno = strategy.get("immunogenicity", {})
    if isinstance(immuno, dict):
        immuno_score = immuno.get("score", immuno.get("risk_level", "NA"))
    else:
        immuno_score = immuno if immuno else "NA"
    
    return f"| {name} | {mut_count}/{total} ({mut_pct:.1f}%) | {risk} | {immuno_score} |"


def build_triple_panel_markdown(result: Dict[str, Any]) -> str:
    """
    ""Markdown 。
    
    Args:
        result: 
    
    Returns:
        Markdown 
    """
    strategies = result.get("humanization_strategies", {}) or {}
    original_data = result.get("input", {}) or {}
    original_seq = original_data.get("sequence", "")
    
    #  original_seq， sequence_analysis 
    if not original_seq:
        seq_analysis = result.get("sequence_analysis", {}) or {}
        orig_regions = seq_analysis.get("original_regions", {}) or {}
        original_seq = "".join([
            orig_regions.get("FR1", ""),
            orig_regions.get("CDR1", ""),
            orig_regions.get("FR2", ""),
            orig_regions.get("CDR2", ""),
            orig_regions.get("FR3", ""),
            orig_regions.get("CDR3", ""),
            orig_regions.get("FR4", ""),
        ])
    
    cons = strategies.get("conservative", {}) or {}
    bal = strategies.get("balanced", {}) or {}
    aggr = strategies.get("aggressive", {}) or {}
    
    #  strategies， panels 
    if not cons and not bal and not aggr:
        panels = result.get("panels", {}) or {}
        if panels:
            cons = panels.get("A", {}) or {}
            bal = panels.get("B", {}) or {}
            aggr = panels.get("C", {}) or {}
    
    # ， best_match （ conservative）
    if not cons:
        best_match = result.get("best_match", {}) or {}
        if best_match:
            cons = best_match
    
    parts: List[str] = []
    
    parts.append("## \n")
    
    parts.append("#### \n")
    if cons:
        cons_seq = cons.get("sequence", "") or cons.get("humanized_sequence", "")
        if cons_seq:
            parts.append(_build_sequence_block("Conservative", cons_seq))
    
    if bal:
        bal_seq = bal.get("sequence", "") or bal.get("humanized_sequence", "")
        if bal_seq:
            parts.append(_build_sequence_block("Balanced", bal_seq))
    
    if aggr:
        aggr_seq = aggr.get("sequence", "") or aggr.get("humanized_sequence", "")
        if aggr_seq:
            parts.append(_build_sequence_block("Aggressive", aggr_seq))
    
    parts.append("\n#### \n")
    parts.append("|  | / | Total structural risk | Immunogenicity score |")
    parts.append("|------|----------------|-----------------------|----------------------|")
    parts.append(_build_mutation_summary_row("Conservative", cons, original_seq))
    parts.append(_build_mutation_summary_row("Balanced", bal, original_seq))
    parts.append(_build_mutation_summary_row("Aggressive", aggr, original_seq))
    
    return "\n".join(parts)


# 
if __name__ == "__main__":
    # ： result.json 
    import json
    from pathlib import Path
    
    #  result.json
    result_path = Path("result.json")
    if result_path.exists():
        with open(result_path, "r", encoding="utf-8") as f:
            result = json.load(f)
        
        # 
        comparison = build_panel_comparison(result)
        
        #  HTML
        save_panel_comparison_html(comparison, Path("panel_comparison.html"))
        
        # 
        save_panel_comparison_text(comparison, Path("panel_comparison.txt"))
        
        # 
        print("\n" + render_comparison_text(comparison))
    else:
        print("⚠️  result.json not found, creating example...")
        
        # 
        example_result = {
            "sequence_analysis": {
                "original_regions": {
                    "FR1": "EVQLVESGGGLVQPGGSLRLSCAAS",
                    "CDR1": "GFNIKDTY",
                    "FR2": "MHWVRQRPGKGLEWVSA",
                    "CDR2": "YISYSGST",
                    "FR3": "YYADSVKGRFTISRDNSKNTLYLQMGSLRAEDMAVYYC",
                    "CDR3": "AAGGVGWPYFDY",
                    "FR4": "WGQGTQVTVSS"
                },
                "humanized_regions": {
                    "FR1": "EVQLVESGGGLVQPGGSLRLSCAAS",
                    "CDR1": "GFNIKDTY",
                    "FR2": "MHWVRQRPGKGLEWVSA",
                    "CDR2": "YISYSGST",
                    "FR3": "YYADSVKGRFTISRDNSKNTLYLQMGSLRAEDMAVYYC",
                    "CDR3": "AAGGVGWPYFDY",
                    "FR4": "WGQGTQVTVSS"
                }
            },
            "mutations": {
                "list": [
                    {"region": "FR1", "position": 5, "from": "L", "to": "V"},
                    {"region": "FR2", "position": 45, "from": "R", "to": "K"},
                ]
            },
            "best_match": {
                "humanized_sequence": "EVQLVESGGGLVQPGGSLRLSCAASGFNIKDTYMHWVRQRPGKGLEWVSAYISYSGSTYYADSVKGRFTISRDNSKNTLYLQMGSLRAEDMAVYYCAAGGVGWPYFDYWGQGTQVTVSS",
                "scores": {
                    "fr_identity": 0.92,
                    "structural_risk": 0.15,
                }
            }
        }
        
        comparison = build_panel_comparison(example_result)
        print("\n" + render_comparison_text(comparison))

