"""
EGFR VHHCRO

CRO
"""

import sys
from pathlib import Path
from datetime import datetime
import json

PROJECT_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT_ROOT))

from core.vhh_humanization import humanize_vhh
from core.audit import get_audit_logger

# EGFR VHH
EGFR_VHH_SEQ = "QVQLVESGGGLVQVGGSLRLSRALSGFWYNHMGWFRQAPGKEREGVAVITADSGSTTYADSVKGRFTISRDDARNTVYLQMNSLKPEDTAVYYCAAGGVGWPYFDYWGQGTQVTVSS"

def generate_cro_report():
    """CRO"""
    
    print("[INFO] EGFR VHH...")
    
    # （，top_k）
    result = humanize_vhh(
        EGFR_VHH_SEQ,
        panel="all",
        top_k=10,  # top_k
        scoring_profile="default"
    )
    
    if not result.get("success"):
        print(f"[WARN] : {result.get('error')}")
        print("[INFO] ...")
        # CDR
        result = humanize_vhh(
            EGFR_VHH_SEQ,
            panel="all",
            top_k=15,
            scoring_profile="default"
        )
    
    if not result.get("success"):
        print(f"[ERROR] : {result.get('error')}")
        # 
        output_id = f"FAILED_{int(datetime.now().timestamp())}"
        html_report = generate_cro_html_report_failed(result, output_id)
    else:
        # （best_match）
        output_id = f"REPORT_{int(datetime.now().timestamp())}"
        if result.get("best_match"):
            try:
                logger = get_audit_logger()
                output_id = logger.log_humanization(
                    sequence=EGFR_VHH_SEQ,
                    result=result,
                    panel="all",
                    project_name="EGFR_7D12_VHH",
                    user_id="CRO_REPORT_GENERATOR"
                )
            except Exception as e:
                print(f"[WARN] : {e}")
                # output_id
        
        html_report = generate_cro_html_report(result, output_id)
    
    # HTML
    html_report = generate_cro_html_report(result, output_id)
    
    # 
    output_dir = PROJECT_ROOT / "projects" / "EGFR_7D12_VHH" / "cro_report"
    output_dir.mkdir(parents=True, exist_ok=True)
    
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    report_path = output_dir / f"EGFR_VHH_Humanization_CRO_Report_{timestamp}.html"
    
    with open(report_path, "w", encoding="utf-8") as f:
        f.write(html_report)
    
    print(f"[INFO] CRO: {report_path}")
    
    return report_path


def generate_cro_html_report_failed(result: dict, output_id: str) -> str:
    """CRO"""
    error_msg = result.get('error', 'Unknown error')
    input_info = result.get('input', {})
    
    html = f"""<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>EGFR VHH Humanization Report | Analysis Failed</title>
    <style>
        * {{ margin: 0; padding: 0; box-sizing: border-box; }}
        body {{
            font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif;
            line-height: 1.6;
            color: #2c3e50;
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            padding: 20px;
        }}
        .container {{
            max-width: 1200px;
            margin: 0 auto;
            background: white;
            box-shadow: 0 10px 40px rgba(0,0,0,0.2);
            border-radius: 12px;
            overflow: hidden;
        }}
        .header {{
            background: linear-gradient(135deg, #e74c3c 0%, #c0392b 100%);
            color: white;
            padding: 60px 40px;
            text-align: center;
        }}
        .header h1 {{ font-size: 2.5em; margin-bottom: 10px; }}
        .content {{ padding: 40px; }}
        .error-box {{
            background: #fee;
            border-left: 4px solid #e74c3c;
            padding: 30px;
            border-radius: 8px;
            margin: 20px 0;
        }}
        .error-box h2 {{ color: #c0392b; margin-bottom: 15px; }}
    </style>
</head>
<body>
    <div class="container">
        <div class="header">
            <h1>EGFR VHH Humanization Analysis</h1>
            <div style="margin-top: 20px;">Analysis Failed</div>
        </div>
        <div class="content">
            <div class="error-box">
                <h2>Analysis Could Not Be Completed</h2>
                <p><strong>Error:</strong> {error_msg}</p>
                <p style="margin-top: 20px;">
                    The humanization analysis could not be completed due to the above error. 
                    This may be due to CDR compatibility issues, template library limitations, 
                    or sequence characteristics that prevent successful matching.
                </p>
            </div>
            <h2 style="margin-top: 40px;">Input Sequence</h2>
            <p><strong>Length:</strong> {input_info.get('length', len(EGFR_VHH_SEQ))} amino acids</p>
            <pre style="background: #f4f4f4; padding: 20px; border-radius: 8px; overflow-x: auto;">{EGFR_VHH_SEQ}</pre>
        </div>
    </div>
</body>
</html>"""
    return html


def generate_cro_html_report(result: dict, output_id: str) -> str:
    """CRO HTML"""
    
    best_match = result.get("best_match")
    if best_match is None:
        # best_match，best_by_plan
        best_by_plan = result.get("best_by_plan", {})
        if best_by_plan:
            # plan
            for plan_result in best_by_plan.values():
                if plan_result:
                    best_match = plan_result
                    break
        
        if best_match is None:
            # ，
            return generate_cro_html_report_failed(result, output_id)
    
    best_by_plan = result.get("best_by_plan", {})
    input_info = result.get("input", {})
    
    # （get）
    template = best_match.get("template", {}) if best_match else {}
    scoring = best_match.get("scoring", {}) if best_match else {}
    developability = best_match.get("developability", {}) if best_match else {}
    immunogenicity = best_match.get("immunogenicity", {}) if best_match else {}
    cdrs = result.get("cdrs", {})
    cdr_canonical = result.get("cdr_canonical", {})
    quality_flags = result.get("quality_flags", {})
    risk_flags = result.get("risk_flags", {})
    
    # ANARCII
    query_numbering = result.get("numbering", []) or result.get("sequence_analysis", {}).get("imgt_numbering", [])
    framework_selection_result = None
    if query_numbering:
        try:
            from core.framework_selection.selector import select_frameworks
            framework_selection_result = select_frameworks(query_numbering)
        except Exception:
            framework_selection_result = None
    
    # FR
    strategy_note = "FR：FR（0.6），CDR（0.15），CDR。"
    
    # 
    html = f"""<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>EGFR VHH Humanization Report | CRO Analysis</title>
    <style>
        * {{
            margin: 0;
            padding: 0;
            box-sizing: border-box;
        }}
        
        body {{
            font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif;
            line-height: 1.6;
            color: #2c3e50;
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            padding: 20px;
        }}
        
        .container {{
            max-width: 1400px;
            margin: 0 auto;
            background: white;
            box-shadow: 0 10px 40px rgba(0,0,0,0.2);
            border-radius: 12px;
            overflow: hidden;
        }}
        
        /* Header */
        .header {{
            background: linear-gradient(135deg, #1e3c72 0%, #2a5298 100%);
            color: white;
            padding: 60px 40px;
            text-align: center;
        }}
        
        .header h1 {{
            font-size: 2.5em;
            margin-bottom: 10px;
            font-weight: 300;
            letter-spacing: 2px;
        }}
        
        .header .subtitle {{
            font-size: 1.2em;
            opacity: 0.9;
            font-weight: 300;
        }}
        
        .header .meta {{
            margin-top: 30px;
            font-size: 0.95em;
            opacity: 0.8;
        }}
        
        /* Content */
        .content {{
            padding: 40px;
        }}
        
        .section {{
            margin-bottom: 50px;
        }}
        
        .section-title {{
            font-size: 1.8em;
            color: #1e3c72;
            margin-bottom: 20px;
            padding-bottom: 10px;
            border-bottom: 3px solid #2a5298;
            display: flex;
            align-items: center;
        }}
        
        .section-title::before {{
            content: "▸";
            margin-right: 10px;
            color: #667eea;
            font-size: 1.2em;
        }}
        
        /* Executive Summary */
        .exec-summary {{
            background: linear-gradient(135deg, #f5f7fa 0%, #c3cfe2 100%);
            padding: 30px;
            border-radius: 8px;
            margin-bottom: 30px;
        }}
        
        .summary-grid {{
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(250px, 1fr));
            gap: 20px;
            margin-top: 20px;
        }}
        
        .summary-card {{
            background: white;
            padding: 20px;
            border-radius: 8px;
            box-shadow: 0 2px 10px rgba(0,0,0,0.1);
        }}
        
        .summary-card h3 {{
            color: #667eea;
            font-size: 0.9em;
            text-transform: uppercase;
            letter-spacing: 1px;
            margin-bottom: 10px;
        }}
        
        .summary-card .value {{
            font-size: 2em;
            font-weight: bold;
            color: #2c3e50;
        }}
        
        .summary-card .label {{
            font-size: 0.85em;
            color: #7f8c8d;
            margin-top: 5px;
        }}
        
        /* Tables */
        .data-table {{
            width: 100%;
            border-collapse: collapse;
            margin: 20px 0;
            box-shadow: 0 2px 10px rgba(0,0,0,0.1);
            border-radius: 8px;
            overflow: hidden;
        }}
        
        .data-table th {{
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            color: white;
            padding: 15px;
            text-align: left;
            font-weight: 600;
            font-size: 0.95em;
            text-transform: uppercase;
            letter-spacing: 0.5px;
        }}
        
        .data-table td {{
            padding: 12px 15px;
            border-bottom: 1px solid #e0e0e0;
        }}
        
        .data-table tr:hover {{
            background: #f8f9fa;
        }}
        
        .data-table tr:last-child td {{
            border-bottom: none;
        }}
        
        /* Badges */
        .badge {{
            display: inline-block;
            padding: 5px 12px;
            border-radius: 20px;
            font-size: 0.85em;
            font-weight: 600;
            text-transform: uppercase;
            letter-spacing: 0.5px;
        }}
        
        .badge-success {{
            background: #27ae60;
            color: white;
        }}
        
        .badge-warning {{
            background: #f39c12;
            color: white;
        }}
        
        .badge-error {{
            background: #e74c3c;
            color: white;
        }}
        
        .badge-info {{
            background: #3498db;
            color: white;
        }}
        
        /* Score Bars */
        .score-bar {{
            background: #ecf0f1;
            height: 30px;
            border-radius: 15px;
            overflow: hidden;
            position: relative;
            margin: 10px 0;
        }}
        
        .score-fill {{
            height: 100%;
            background: linear-gradient(90deg, #27ae60 0%, #2ecc71 100%);
            display: flex;
            align-items: center;
            justify-content: center;
            color: white;
            font-weight: bold;
            font-size: 0.9em;
            transition: width 0.3s ease;
        }}
        
        .score-fill.warning {{
            background: linear-gradient(90deg, #f39c12 0%, #e67e22 100%);
        }}
        
        .score-fill.error {{
            background: linear-gradient(90deg, #e74c3c 0%, #c0392b 100%);
        }}
        
        /* Sequence Display */
        .sequence-box {{
            background: #2c3e50;
            color: #ecf0f1;
            padding: 20px;
            border-radius: 8px;
            font-family: 'Courier New', monospace;
            font-size: 0.9em;
            line-height: 1.8;
            overflow-x: auto;
            margin: 20px 0;
        }}
        
        .sequence-box .label {{
            color: #95a5a6;
            font-size: 0.85em;
            margin-bottom: 10px;
            text-transform: uppercase;
            letter-spacing: 1px;
        }}
        
        /* Warning Box */
        .warning-box {{
            background: #fff3cd;
            border-left: 4px solid #f39c12;
            padding: 20px;
            margin: 20px 0;
            border-radius: 4px;
        }}
        
        .warning-box h4 {{
            color: #856404;
            margin-bottom: 10px;
        }}
        
        .warning-box ul {{
            margin-left: 20px;
            color: #856404;
        }}
        
        /* Footer */
        .footer {{
            background: #2c3e50;
            color: white;
            padding: 30px 40px;
            text-align: center;
        }}
        
        .footer .logo {{
            font-size: 1.5em;
            font-weight: bold;
            margin-bottom: 10px;
        }}
        
        .footer .meta {{
            font-size: 0.9em;
            opacity: 0.8;
        }}
        
        /* Two Column Layout */
        .two-column {{
            display: grid;
            grid-template-columns: 1fr 1fr;
            gap: 30px;
            margin: 20px 0;
        }}
        
        @media (max-width: 768px) {{
            .two-column {{
                grid-template-columns: 1fr;
            }}
        }}
        
        /* Comparison Table */
        .comparison-table {{
            margin: 20px 0;
        }}
        
        .comparison-table th {{
            background: #34495e;
        }}
        
        .metric-cell {{
            text-align: center;
        }}
        
        .metric-value {{
            font-size: 1.3em;
            font-weight: bold;
            color: #2c3e50;
        }}
        
        .metric-label {{
            font-size: 0.85em;
            color: #7f8c8d;
        }}
    </style>
</head>
<body>
    <div class="container">
        <!-- Header -->
        <div class="header">
            <h1>EGFR VHH Humanization</h1>
            <div class="subtitle">Comprehensive CRO Analysis Report</div>
            <div class="meta">
                Report ID: {output_id}<br>
                Generated: {datetime.now().strftime("%B %d, %Y at %H:%M:%S")}<br>
                        Analysis Platform: VHH Humanization Engine v2.2.0 (FR-Priority Strategy)
            </div>
        </div>
        
        <!-- Content -->
        <div class="content">
            <!-- Executive Summary -->
            <div class="section">
                <h2 class="section-title">Executive Summary</h2>
                <div class="exec-summary">
                    <p style="font-size: 1.1em; margin-bottom: 20px; line-height: 1.8;">
                        This report presents a comprehensive humanization analysis of the EGFR-targeting VHH 
                        (Variable Heavy-chain-only antibody) sequence. The analysis employed our proprietary 
                        VHH-SAFE humanization platform, which utilizes a curated library of 90 human VH3-derived 
                        frameworks engineered for optimal VHH compatibility. The selected humanized variant 
                        demonstrates excellent framework identity, CDR compatibility, and developability scores, 
                        positioning it as a strong candidate for further development.
                    </p>
                    <div class="summary-grid">
                        <div class="summary-card">
                            <h3>Framework Identity</h3>
                            <div class="value">{scoring.get('framework_identity', 0):.1%}</div>
                            <div class="label">Human Framework Similarity</div>
                        </div>
                        <div class="summary-card">
                            <h3>Combined Score</h3>
                            <div class="value">{scoring.get('combined_score', 0):.3f}</div>
                            <div class="label">Overall Quality Metric</div>
                        </div>
                        <div class="summary-card">
                            <h3>Developability</h3>
                            <div class="value">
                                <span class="badge {'badge-success' if developability.get('grade') == 'A' else 'badge-warning' if developability.get('grade') == 'B' else 'badge-error'}">
                                    Grade {developability.get('grade', 'N/A')}
                                </span>
                            </div>
                            <div class="label">CMC Risk Assessment</div>
                        </div>
                        <div class="summary-card">
                            <h3>Template ID</h3>
                            <div class="value" style="font-size: 1.2em;">{template.get('template_id', 'N/A')}</div>
                            <div class="label">Selected Framework</div>
                        </div>
                    </div>
                </div>
            </div>
            
            <!-- Input Sequence Analysis -->
            <div class="section">
                <h2 class="section-title">Input Sequence Analysis</h2>
                
                <table class="data-table">
                    <thead>
                        <tr>
                            <th>Property</th>
                            <th>Value</th>
                            <th>Assessment</th>
                        </tr>
                    </thead>
                    <tbody>
                        <tr>
                            <td><strong>Sequence Length</strong></td>
                            <td>{input_info.get('length', len(EGFR_VHH_SEQ))} amino acids</td>
                            <td><span class="badge badge-success">Normal</span></td>
                        </tr>
                        <tr>
                            <td><strong>Source Species</strong></td>
                            <td>{input_info.get('source', 'Alpaca').title()}</td>
                            <td><span class="badge badge-info">VHH Native</span></td>
                        </tr>
                        <tr>
                            <td><strong>VHH Hallmark Score</strong></td>
                            <td>{input_info.get('vhh_hallmark', {}).get('score', 0):.2f}</td>
                            <td><span class="badge {'badge-success' if input_info.get('vhh_hallmark', {}).get('score', 0) >= 2 else 'badge-warning'}">
                                {'Canonical VHH' if input_info.get('vhh_hallmark', {}).get('score', 0) >= 2 else 'VH-like'}
                            </span></td>
                        </tr>
                        <tr>
                            <td><strong>CDR3 Length</strong></td>
                            <td>{len(cdrs.get('CDR3', ''))} amino acids</td>
                            <td><span class="badge {'badge-warning' if len(cdrs.get('CDR3', '')) >= 20 else 'badge-success'}">
                                {'Long CDR3' if len(cdrs.get('CDR3', '')) >= 20 else 'Standard'}
                            </span></td>
                        </tr>
                    </tbody>
                </table>
                
                <div class="sequence-box">
                    <div class="label">Input VHH Sequence</div>
                    {format_sequence(EGFR_VHH_SEQ)}
                </div>
                
                <h3 style="margin-top: 30px; color: #34495e;">VHH Hallmark Positions (FR2)</h3>
                <table class="data-table">
                    <thead>
                        <tr>
                            <th>IMGT Position</th>
                            <th>Residue</th>
                            <th>VHH Characteristic</th>
                            <th>Status</th>
                        </tr>
                    </thead>
                    <tbody>
                        <tr>
                            <td>37</td>
                            <td><strong>{input_info.get('vhh_hallmark', {}).get('aa37', 'N/A')}</strong></td>
                            <td>Hydrophilic/small (Y, S, N, T, H, Q)</td>
                            <td>{'<span class="badge badge-success">VHH-like</span>' if input_info.get('vhh_hallmark', {}).get('aa37', '') in ['Y', 'S', 'N', 'T', 'H', 'Q'] else '<span class="badge badge-warning">VH-like</span>'}</td>
                        </tr>
                        <tr>
                            <td>44</td>
                            <td><strong>{input_info.get('vhh_hallmark', {}).get('aa44', 'N/A')}</strong></td>
                            <td>Q/E (typical VHH)</td>
                            <td>{'<span class="badge badge-success">VHH-like</span>' if input_info.get('vhh_hallmark', {}).get('aa44', '') in ['Q', 'E'] else '<span class="badge badge-warning">VH-like</span>'}</td>
                        </tr>
                        <tr>
                            <td>45</td>
                            <td><strong>{input_info.get('vhh_hallmark', {}).get('aa45', 'N/A')}</strong></td>
                            <td>R (very typical)</td>
                            <td>{'<span class="badge badge-success">VHH-like</span>' if input_info.get('vhh_hallmark', {}).get('aa45', '') == 'R' else '<span class="badge badge-warning">VH-like</span>'}</td>
                        </tr>
                        <tr>
                            <td>47</td>
                            <td><strong>{input_info.get('vhh_hallmark', {}).get('aa47', 'N/A')}</strong></td>
                            <td>G/L (common)</td>
                            <td>{'<span class="badge badge-success">VHH-like</span>' if input_info.get('vhh_hallmark', {}).get('aa47', '') in ['G', 'L'] else '<span class="badge badge-warning">VH-like</span>'}</td>
                        </tr>
                    </tbody>
                </table>
            </div>
            
            <!-- Humanization Results -->
            <div class="section">
                <h2 class="section-title">Humanization Results</h2>
                
                <h3 style="margin-top: 20px; color: #34495e;">Selected Human Framework</h3>
                <table class="data-table">
                    <thead>
                        <tr>
                            <th>Property</th>
                            <th>Value</th>
                        </tr>
                    </thead>
                    <tbody>
                        <tr>
                            <td><strong>Template ID</strong></td>
                            <td><code>{template.get('template_id', 'N/A')}</code></td>
                        </tr>
                        <tr>
                            <td><strong>VHH-SAFE Panel</strong></td>
                            <td><span class="badge badge-info">Panel {template.get('panel', 'N/A')}</span></td>
                        </tr>
                        <tr>
                            <td><strong>Source Scaffold</strong></td>
                            <td><code>{template.get('scaffold_id', 'N/A')}</code></td>
                        </tr>
                        <tr>
                            <td><strong>Framework Identity</strong></td>
                            <td><strong>{scoring.get('framework_identity', 0):.1%}</strong></td>
                        </tr>
                        <tr>
                            <td><strong>CDR Compatibility</strong></td>
                            <td><strong>{scoring.get('cdr_compatibility_score', 0):.3f}</strong></td>
                        </tr>
                    </tbody>
                </table>
                
                <h3 style="margin-top: 30px; color: #34495e;">Humanized Sequence</h3>
                <div class="sequence-box">
                    <div class="label">Humanized VHH Sequence</div>
                    {format_sequence(best_match.get('humanized_sequence', ''))}
                </div>
                
                {generate_cdr_section(cdrs, cdr_canonical)}
            </div>
            
            {generate_framework_selection_section_en(query_numbering, framework_selection_result) if framework_selection_result else ""}
            
            <!-- Scoring Details -->
            <div class="section">
                <h2 class="section-title">Comprehensive Scoring Analysis</h2>
                
                <div style="background: #e3f2fd; padding: 20px; border-radius: 8px; margin-bottom: 20px; border-left: 4px solid #2196f3;">
                    <h3 style="color: #1565c0; margin-bottom: 10px;">FR-Priority Scoring Strategy</h3>
                    <p style="margin-bottom: 10px;">
                        The scoring formula prioritizes framework identity (weight: 0.6) as the primary factor, 
                        with CDR compatibility (weight: 0.15) and developability (weight: 0.25) serving as 
                        optimization factors. This ensures that templates with excellent FR matching are not 
                        excluded due to CDR canonical structure uncertainties.
                    </p>
                    <p style="margin: 0;">
                        <strong>Formula:</strong> Combined Score = 0.6 × FR Identity + 0.15 × CDR Compatibility + 0.25 × Developability
                    </p>
                </div>
                
                <div class="two-column">
                    <div>
                        <h3 style="color: #34495e; margin-bottom: 15px;">Scoring Components</h3>
                        <table class="data-table">
                            <thead>
                                <tr>
                                    <th>Metric</th>
                                    <th>Score</th>
                                </tr>
                            </thead>
                            <tbody>
                                <tr>
                                    <td>Framework Identity</td>
                                    <td class="metric-cell">
                                        <div class="metric-value">{scoring.get('framework_identity', 0):.3f}</div>
                                        <div class="score-bar">
                                            <div class="score-fill" style="width: {scoring.get('framework_identity', 0) * 100}%">
                                                {scoring.get('framework_identity', 0):.1%}
                                            </div>
                                        </div>
                                    </td>
                                </tr>
                                <tr>
                                    <td>CDR Compatibility</td>
                                    <td class="metric-cell">
                                        <div class="metric-value">{scoring.get('cdr_compatibility_score', 0):.3f}</div>
                                        <div class="score-bar">
                                            <div class="score-fill" style="width: {scoring.get('cdr_compatibility_score', 0) * 100}%">
                                                {scoring.get('cdr_compatibility_score', 0):.1%}
                                            </div>
                                        </div>
                                    </td>
                                </tr>
                                <tr>
                                    <td>Key Position Score</td>
                                    <td class="metric-cell">
                                        <div class="metric-value">{scoring.get('key_position_score', 0):.3f}</div>
                                        <div class="score-bar">
                                            <div class="score-fill" style="width: {scoring.get('key_position_score', 0) * 100}%">
                                                {scoring.get('key_position_score', 0):.1%}
                                            </div>
                                        </div>
                                    </td>
                                </tr>
                                <tr>
                                    <td>Developability Score</td>
                                    <td class="metric-cell">
                                        <div class="metric-value">{scoring.get('developability_score', 0):.3f}</div>
                                        <div class="score-bar">
                                            <div class="score-fill {'warning' if scoring.get('developability_score', 0) < 0.6 else 'error' if scoring.get('developability_score', 0) < 0.4 else ''}" style="width: {scoring.get('developability_score', 0) * 100}%">
                                                {scoring.get('developability_score', 0):.1%}
                                            </div>
                                        </div>
                                    </td>
                                </tr>
                                <tr style="background: #f8f9fa; font-weight: bold;">
                                    <td>Combined Score</td>
                                    <td class="metric-cell">
                                        <div class="metric-value" style="font-size: 1.5em; color: #2a5298;">
                                            {scoring.get('combined_score', 0):.3f}
                                        </div>
                                    </td>
                                </tr>
                            </tbody>
                        </table>
                    </div>
                    
                    <div>
                        <h3 style="color: #34495e; margin-bottom: 15px;">Panel Comparison</h3>
                        {generate_panel_comparison(best_by_plan)}
                    </div>
                </div>
            </div>
            
            <!-- Developability Assessment -->
            <div class="section">
                <h2 class="section-title">Developability Assessment</h2>
                
                <div class="summary-grid" style="margin-top: 20px;">
                    <div class="summary-card">
                        <h3>Overall Grade</h3>
                        <div class="value">
                            <span class="badge {'badge-success' if developability.get('grade') == 'A' else 'badge-warning' if developability.get('grade') == 'B' else 'badge-error'}">
                                Grade {developability.get('grade', 'N/A')}
                            </span>
                        </div>
                        <div class="label">CMC Risk Level</div>
                    </div>
                    <div class="summary-card">
                        <h3>Developability Score</h3>
                        <div class="value">{developability.get('score', 0):.3f}</div>
                        <div class="label">0.0 (High Risk) - 1.0 (Low Risk)</div>
                    </div>
                    <div class="summary-card">
                        <h3>High-Risk Liabilities</h3>
                        <div class="value">{len(developability.get('liabilities', []))}</div>
                        <div class="label">Identified Issues</div>
                    </div>
                    <div class="summary-card">
                        <h3>FR2 Aggregation Risk</h3>
                        <div class="value">{developability.get('fr2_risk', 0):.2f}</div>
                        <div class="label">0.0 (Low) - 1.0 (High)</div>
                    </div>
                </div>
                
                {generate_liabilities_table(developability.get('liabilities', []))}
            </div>
            
            <!-- Immunogenicity Assessment -->
            <div class="section">
                <h2 class="section-title">Immunogenicity Assessment</h2>
                
                <table class="data-table">
                    <thead>
                        <tr>
                            <th>Assessment Type</th>
                            <th>Result</th>
                            <th>Risk Level</th>
                        </tr>
                    </thead>
                    <tbody>
                        <tr>
                            <td><strong>FR Region Immunogenicity</strong></td>
                            <td>{immunogenicity.get('fr_hotspot_count', 0)} HLA hotspots detected</td>
                            <td>
                                <span class="badge {'badge-success' if immunogenicity.get('fr_immuno_risk') == 'low' else 'badge-warning' if immunogenicity.get('fr_immuno_risk') == 'medium' else 'badge-error'}">
                                    {immunogenicity.get('fr_immuno_risk', 'N/A').upper()}
                                </span>
                            </td>
                        </tr>
                        <tr>
                            <td><strong>Assessment Method</strong></td>
                            <td>Static FR-only HLA hotspot analysis</td>
                            <td><span class="badge badge-info">Screening</span></td>
                        </tr>
                    </tbody>
                </table>
                
                {generate_immuno_warning(immunogenicity.get('fr_immuno_risk', 'low'))}
            </div>
            
            <!-- Risk Assessment -->
            <div class="section">
                <h2 class="section-title">Risk Assessment & Quality Flags</h2>
                
                {generate_risk_assessment(quality_flags, risk_flags, developability, immunogenicity)}
                
                {generate_cdr_warnings_section(quality_flags.get('cdr_warnings', []))}
            </div>
            
            <!-- Recommendations -->
            <div class="section">
                <h2 class="section-title">Recommendations & Next Steps</h2>
                
                <div style="background: #e8f5e9; padding: 25px; border-radius: 8px; border-left: 4px solid #4caf50;">
                    <h3 style="color: #2e7d32; margin-bottom: 15px;">✓ Recommended Actions</h3>
                    <ol style="margin-left: 20px; line-height: 2;">
                        <li><strong>Expression & Purification</strong>: Proceed with recombinant expression of the humanized variant for functional validation.</li>
                        <li><strong>Binding Affinity Assessment</strong>: Perform SPR or BLI analysis to confirm target binding is maintained post-humanization.</li>
                        <li><strong>Stability Studies</strong>: Conduct accelerated stability studies to validate developability predictions, particularly focusing on FR2 aggregation propensity.</li>
                        <li><strong>Immunogenicity Validation</strong>: If FR immunogenicity risk is medium or high, consider in vitro T-cell activation assays or further deimmunization.</li>
                        <li><strong>Alternative Variants</strong>: Review Panel B and C variants if Panel A shows suboptimal performance in experimental validation.</li>
                    </ol>
                </div>
                
                {generate_next_steps_section(best_by_plan)}
            </div>
            
            <!-- Technical Details -->
            <div class="section">
                <h2 class="section-title">Technical Specifications</h2>
                
                <table class="data-table">
                    <thead>
                        <tr>
                            <th>Parameter</th>
                            <th>Value</th>
                        </tr>
                    </thead>
                    <tbody>
                        <tr>
                            <td><strong>Analysis Platform</strong></td>
                            <td>VHH Humanization Engine v2.1.0</td>
                        </tr>
                        <tr>
                            <td><strong>Template Library</strong></td>
                            <td>Human VH3 VHH-SAFE Templates (90 variants)</td>
                        </tr>
                        <tr>
                            <td><strong>Scoring Profile</strong></td>
                            <td>Default (balanced)</td>
                        </tr>
                        <tr>
                            <td><strong>IMGT Numbering</strong></td>
                            <td>ANARCII (Language Model-based)</td>
                        </tr>
                        <tr>
                            <td><strong>CDR Classification</strong></td>
                            <td>Canonical structure-based compatibility</td>
                        </tr>
                        <tr>
                            <td><strong>Developability Method</strong></td>
                            <td>CMC liability scanning + FR aggregation risk</td>
                        </tr>
                        <tr>
                            <td><strong>Report ID</strong></td>
                            <td><code>{output_id}</code></td>
                        </tr>
                    </tbody>
                </table>
            </div>
        </div>
        
        <!-- Footer -->
        <div class="footer">
            <div class="logo">VHH Humanization Platform</div>
            <div class="meta">
                This report was generated using proprietary algorithms and curated template libraries.<br>
                For questions or additional analysis, please contact the platform administrator.<br>
                Report Confidential - For Internal Use Only
            </div>
        </div>
    </div>
</body>
</html>"""
    
    return html


def format_sequence(seq: str, line_length: int = 60) -> str:
    """"""
    if not seq:
        return "N/A"
    lines = []
    for i in range(0, len(seq), line_length):
        chunk = seq[i:i+line_length]
        lines.append(chunk)
    return "<br>".join(lines)


def generate_framework_selection_section_en(query_numbering: list, selection_result: dict = None) -> str:
    """Generate Framework Selection Rationale section (English)"""
    if not selection_result:
        return ""
    
    try:
        from core.framework_selection.report_renderer import render_framework_selection_section_en
        return render_framework_selection_section_en(query_numbering, selection_result)
    except Exception:
        return ""


def generate_cdr_section(cdrs: dict, cdr_canonical: dict) -> str:
    """CDR"""
    html = """
    <h3 style="margin-top: 30px; color: #34495e;">CDR Analysis</h3>
    <table class="data-table">
        <thead>
            <tr>
                <th>CDR</th>
                <th>Sequence</th>
                <th>Length</th>
                <th>Canonical Class</th>
                <th>Compatibility</th>
            </tr>
        </thead>
        <tbody>"""
    
    for cdr_name in ['CDR1', 'CDR2', 'CDR3']:
        cdr_seq = cdrs.get(cdr_name, '')
        cdr_info = cdr_canonical.get(cdr_name.lower(), {})
        canonical = cdr_info.get('canonical_class', 'Unknown')
        compat = cdr_info.get('compatibility_score', 0)
        
        html += f"""
            <tr>
                <td><strong>{cdr_name}</strong></td>
                <td><code>{cdr_seq}</code></td>
                <td>{len(cdr_seq)} aa</td>
                <td>{canonical}</td>
                <td>
                    <span class="badge {'badge-success' if compat >= 0.7 else 'badge-warning' if compat >= 0.5 else 'badge-error'}">
                        {compat:.2f}
                    </span>
                </td>
            </tr>"""
    
    html += """
        </tbody>
    </table>"""
    
    return html


def generate_panel_comparison(best_by_plan: dict) -> str:
    """Panel"""
    if not best_by_plan:
        return "<p>Panel comparison not available (single panel analysis).</p>"
    
    html = """
    <table class="data-table">
        <thead>
            <tr>
                <th>Panel</th>
                <th>Template ID</th>
                <th>Combined Score</th>
                <th>Framework Identity</th>
            </tr>
        </thead>
        <tbody>"""
    
    for panel, plan_result in best_by_plan.items():
        if plan_result:
            plan_template = plan_result.get('template', {})
            plan_scoring = plan_result.get('scoring', {})
            html += f"""
            <tr>
                <td><strong>Panel {panel}</strong></td>
                <td><code>{plan_template.get('template_id', 'N/A')}</code></td>
                <td><strong>{plan_scoring.get('combined_score', 0):.3f}</strong></td>
                <td>{plan_scoring.get('framework_identity', 0):.1%}</td>
            </tr>"""
    
    html += """
        </tbody>
    </table>"""
    
    return html


def generate_liabilities_table(liabilities: list) -> str:
    """Liabilities"""
    if not liabilities:
        return """
        <div style="background: #e8f5e9; padding: 20px; border-radius: 8px; margin-top: 20px;">
            <strong style="color: #2e7d32;">✓ No high-risk CMC liabilities detected</strong>
        </div>"""
    
    html = """
    <h3 style="margin-top: 30px; color: #34495e;">Identified CMC Liabilities</h3>
    <table class="data-table">
        <thead>
            <tr>
                <th>Position</th>
                <th>Residue</th>
                <th>Liability Type</th>
                <th>Risk Level</th>
            </tr>
        </thead>
        <tbody>"""
    
    for liability in liabilities[:10]:  # 10
        html += f"""
            <tr>
                <td>{liability.get('position', 'N/A')}</td>
                <td><strong>{liability.get('residue', 'N/A')}</strong></td>
                <td>{liability.get('type', 'N/A')}</td>
                <td>
                    <span class="badge {'badge-error' if liability.get('risk') == 'high' else 'badge-warning'}">
                        {liability.get('risk', 'medium').upper()}
                    </span>
                </td>
            </tr>"""
    
    html += """
        </tbody>
    </table>"""
    
    return html


def generate_immuno_warning(risk: str) -> str:
    """"""
    if risk == 'low':
        return """
        <div style="background: #e8f5e9; padding: 20px; border-radius: 8px; margin-top: 20px;">
            <strong style="color: #2e7d32;">✓ Low immunogenicity risk</strong> - FR region shows minimal HLA hotspot density. 
            Standard immunogenicity monitoring recommended during development.
        </div>"""
    elif risk == 'medium':
        return """
        <div class="warning-box">
            <h4>⚠️ Medium Immunogenicity Risk</h4>
            <p>FR region contains moderate HLA hotspot density. Consider:</p>
            <ul>
                <li>In vitro T-cell activation assays</li>
                <li>Further deimmunization if needed</li>
                <li>Enhanced monitoring during clinical development</li>
            </ul>
        </div>"""
    else:
        return """
        <div class="warning-box" style="background: #f8d7da; border-left-color: #e74c3c;">
            <h4 style="color: #721c24;">⚠️ High Immunogenicity Risk</h4>
            <p>FR region shows high HLA hotspot density. Strongly recommend:</p>
            <ul>
                <li>Immediate deimmunization engineering</li>
                <li>Comprehensive in vitro T-cell assays</li>
                <li>Consider alternative framework selection</li>
            </ul>
        </div>"""


def generate_cdr_warnings_section(cdr_warnings: list) -> str:
    """CDR"""
    if not cdr_warnings:
        return ""
    
    # 
    unique_warnings = list(set(cdr_warnings))
    
    html = """
    <h3 style="margin-top: 30px; color: #34495e;">CDR Compatibility Warnings</h3>
    <div class="warning-box">
        <h4>⚠️ CDR Compatibility Notes (FR-Priority Strategy)</h4>
        <p style="margin-bottom: 10px;">
            The following CDR compatibility warnings were detected. Under the FR-Priority Strategy, 
            these templates were allowed to pass (not filtered) but require experimental validation:
        </p>
        <ul style="margin-left: 20px; line-height: 2;">"""
    
    for warning in unique_warnings[:10]:  # 10
        html += f"<li>{warning}</li>"
    
    html += """
        </ul>
        <p style="margin-top: 15px; font-style: italic;">
            <strong>Note:</strong> These warnings do not indicate failure. The FR-Priority Strategy 
            allows templates with uncertain CDR canonical structures to pass, as FR matching is the 
            primary determinant of structural stability. Experimental validation is recommended.
        </p>
    </div>"""
    
    return html


def generate_risk_assessment(quality_flags: dict, risk_flags: dict, developability: dict, immunogenicity: dict) -> str:
    """"""
    warnings = []
    
    if quality_flags.get('cdr_compatibility_fallback'):
        warnings.append({
            'type': 'warning',
            'title': 'CDR Compatibility Fallback',
            'message': 'Selected template has lower CDR compatibility than optimal. Consider alternative frameworks if binding is compromised.'
        })
    
    if risk_flags.get('long_cdr3'):
        warnings.append({
            'type': 'info',
            'title': 'Long CDR3 Detected',
            'message': 'CDR3 length exceeds typical range. May require special handling during expression and purification.'
        })
    
    if risk_flags.get('noncanonical_disulfide_suspected'):
        warnings.append({
            'type': 'warning',
            'title': 'Non-canonical Disulfide Bonds',
            'message': 'Multiple cysteine residues detected in CDR3. Verify disulfide bond formation and stability.'
        })
    
    dev_risk = developability.get('risk', '')
    if dev_risk in ('medium', 'high'):
        warnings.append({
            'type': 'warning',
            'title': f'Developability Risk: {dev_risk.upper()}',
            'message': f'CMC risk assessment indicates {dev_risk} risk level. Enhanced stability monitoring recommended.'
        })
    
    immuno_risk = immunogenicity.get('fr_immuno_risk', '')
    if immuno_risk in ('medium', 'high'):
        warnings.append({
            'type': 'warning',
            'title': f'FR Immunogenicity Risk: {immuno_risk.upper()}',
            'message': 'Framework region shows elevated immunogenicity risk. Further validation recommended.'
        })
    
    if not warnings:
        return """
        <div style="background: #e8f5e9; padding: 20px; border-radius: 8px;">
            <strong style="color: #2e7d32;">✓ No significant risk flags detected</strong>
            <p style="margin-top: 10px; color: #2e7d32;">The humanized variant shows acceptable risk profile for further development.</p>
        </div>"""
    
    html = ""
    for warning in warnings:
        bg_color = '#fff3cd' if warning['type'] == 'warning' else '#d1ecf1'
        border_color = '#f39c12' if warning['type'] == 'warning' else '#3498db'
        text_color = '#856404' if warning['type'] == 'warning' else '#0c5460'
        
        html += f"""
        <div style="background: {bg_color}; border-left: 4px solid {border_color}; padding: 20px; margin: 15px 0; border-radius: 4px;">
            <h4 style="color: {text_color}; margin-bottom: 10px;">{warning['title']}</h4>
            <p style="color: {text_color}; margin: 0;">{warning['message']}</p>
        </div>"""
    
    return html


def generate_next_steps_section(best_by_plan: dict) -> str:
    """"""
    html = """
    <h3 style="margin-top: 30px; color: #34495e;">Alternative Variants</h3>
    <p style="margin-bottom: 15px;">
        The following alternative humanized variants are available for consideration:
    </p>"""
    
    if best_by_plan:
        html += """
        <table class="data-table">
            <thead>
                <tr>
                    <th>Panel</th>
                    <th>Description</th>
                    <th>Template ID</th>
                    <th>Combined Score</th>
                    <th>Recommendation</th>
                </tr>
            </thead>
            <tbody>"""
        
        panel_descriptions = {
            'A': 'Most conservative - Minimal FR2 modifications (44→Q, 45→R)',
            'B': 'Moderate - Balanced VHH-like characteristics',
            'C': 'Aggressive - Full VHH hallmark pattern (37=Y, 44=Q, 45=R, 47=G)'
        }
        
        for panel, plan_result in best_by_plan.items():
            if plan_result:
                plan_template = plan_result.get('template', {})
                plan_scoring = plan_result.get('scoring', {})
                score = plan_scoring.get('combined_score', 0)
                
                recommendation = "Primary candidate" if score >= 0.8 else "Alternative option" if score >= 0.7 else "Backup option"
                badge_class = "badge-success" if score >= 0.8 else "badge-warning" if score >= 0.7 else "badge-info"
                
                html += f"""
                <tr>
                    <td><strong>Panel {panel}</strong></td>
                    <td>{panel_descriptions.get(panel, 'N/A')}</td>
                    <td><code>{plan_template.get('template_id', 'N/A')}</code></td>
                    <td><strong>{score:.3f}</strong></td>
                    <td><span class="badge {badge_class}">{recommendation}</span></td>
                </tr>"""
        
        html += """
            </tbody>
        </table>"""
    else:
        html += "<p>Single panel analysis performed. Alternative variants not generated.</p>"
    
    return html


if __name__ == "__main__":
    report_path = generate_cro_report()
    if report_path:
        print(f"\n{'='*80}")
        print("CRO Report Generated Successfully!")
        print(f"{'='*80}")
        print(f"Report location: {report_path}")
        print(f"\nOpen the HTML file in your browser to view the full report.")

