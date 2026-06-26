"""
EGFR VHHCRO（）

FR，CRO
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


def generate_cro_report_cn():
    """CRO（）"""
    
    print("[INFO] EGFR VHH（FR）...")
    
    # （，FR）
    result = humanize_vhh(
        EGFR_VHH_SEQ,
        panel="all",
        top_k=10,
        scoring_profile="default"
    )
    
    if not result.get("success"):
        print(f"[ERROR] : {result.get('error')}")
        output_id = f"FAILED_{int(datetime.now().timestamp())}"
        html_report = generate_cro_html_report_failed_cn(result, output_id)
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
                    user_id="CRO_REPORT_GENERATOR_CN"
                )
            except Exception as e:
                print(f"[WARN] : {e}")
        
        html_report = generate_cro_html_report_cn(result, output_id)
    
    # 
    output_dir = PROJECT_ROOT / "projects" / "EGFR_7D12_VHH" / "cro_report"
    output_dir.mkdir(parents=True, exist_ok=True)
    
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    report_path = output_dir / f"EGFR_VHHCRO_{timestamp}.html"
    
    with open(report_path, "w", encoding="utf-8") as f:
        f.write(html_report)
    
    print(f"[INFO] CRO: {report_path}")
    
    return report_path


def generate_cro_html_report_cn(result: dict, output_id: str) -> str:
    """CRO HTML（）"""
    
    best_match = result.get("best_match")
    if best_match is None:
        best_by_plan = result.get("best_by_plan", {})
        if best_by_plan:
            for plan_result in best_by_plan.values():
                if plan_result:
                    best_match = plan_result
                    break
        
        if best_match is None:
            return generate_cro_html_report_failed_cn(result, output_id)
    
    best_by_plan = result.get("best_by_plan", {})
    input_info = result.get("input", {})
    
    # 
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
        except Exception as e:
            # If framework selection fails, continue without it
            framework_selection_result = None
    
    # FR
    strategy_note = "FR：FR（0.6），CDR（0.15），CDR。"
    
    # （HTML，）
    html = f"""<!DOCTYPE html>
<html lang="zh-CN">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>EGFR VHH | CRO</title>
    <style>
        * {{
            margin: 0;
            padding: 0;
            box-sizing: border-box;
        }}
        
        body {{
            font-family: 'Microsoft YaHei', 'SimHei', 'Segoe UI', sans-serif;
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
        }}
        
        .data-table td {{
            padding: 12px 15px;
            border-bottom: 1px solid #e0e0e0;
        }}
        
        .data-table tr:hover {{
            background: #f8f9fa;
        }}
        
        .badge {{
            display: inline-block;
            padding: 5px 12px;
            border-radius: 20px;
            font-size: 0.85em;
            font-weight: 600;
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
        }}
        
        .score-fill.warning {{
            background: linear-gradient(90deg, #f39c12 0%, #e67e22 100%);
        }}
        
        .score-fill.error {{
            background: linear-gradient(90deg, #e74c3c 0%, #c0392b 100%);
        }}
        
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
        
        .warning-box {{
            background: #fff3cd;
            border-left: 4px solid #f39c12;
            padding: 20px;
            margin: 20px 0;
            border-radius: 4px;
        }}
        
        .recommendation-box {{
            background: #e8f5e9;
            border-left: 4px solid #4caf50;
            padding: 20px;
            margin: 20px 0;
            border-radius: 4px;
        }}
        
        .strategy-box {{
            background: #e3f2fd;
            border-left: 4px solid #2196f3;
            padding: 20px;
            margin: 20px 0;
            border-radius: 4px;
        }}
        
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
    </style>
</head>
<body>
    <div class="container">
        <div class="header">
            <h1>EGFR VHH</h1>
            <div class="subtitle">CRO</div>
            <div class="meta">
                ID: {output_id}<br>
                : {datetime.now().strftime("%Y%m%d %H:%M:%S")}<br>
                : VHH v2.2.0 (FR)
            </div>
        </div>
        
        <div class="content">
            <!--  -->
            <div class="section">
                <h2 class="section-title"></h2>
                <div class="exec-summary">
                    <p style="font-size: 1.1em; margin-bottom: 20px; line-height: 1.8;">
                        EGFRVHH（）。
                        <strong>FR</strong>：，（FR）CDR。
                        90VH3VHH-SAFE。，
                        CDRdevelopability，。
                    </p>
                    <div class="strategy-box">
                        <strong style="color: #1565c0;">：</strong> 
                        <span style="color: #1565c0;">{strategy_note}</span>
                    </div>
                    <div class="summary-grid">
                        <div class="summary-card">
                            <h3></h3>
                            <div class="value">{scoring.get('framework_identity', 0):.1%}</div>
                            <div class="label"></div>
                        </div>
                        <div class="summary-card">
                            <h3></h3>
                            <div class="value">{scoring.get('combined_score', 0):.3f}</div>
                            <div class="label"></div>
                        </div>
                        <div class="summary-card">
                            <h3>Developability</h3>
                            <div class="value">
                                <span class="badge {'badge-success' if developability.get('grade') == 'A' else 'badge-warning' if developability.get('grade') == 'B' else 'badge-error'}">
                                     {developability.get('grade', 'N/A')}
                                </span>
                            </div>
                            <div class="label">CMC</div>
                        </div>
                        <div class="summary-card">
                            <h3>ID</h3>
                            <div class="value" style="font-size: 1.2em;">{template.get('template_id', 'N/A')}</div>
                            <div class="label"></div>
                        </div>
                    </div>
                </div>
            </div>
            
            <!--  -->
            <div class="section">
                <h2 class="section-title"></h2>
                
                <table class="data-table">
                    <thead>
                        <tr>
                            <th></th>
                            <th></th>
                            <th></th>
                        </tr>
                    </thead>
                    <tbody>
                        <tr>
                            <td><strong></strong></td>
                            <td>{input_info.get('length', len(EGFR_VHH_SEQ))} </td>
                            <td><span class="badge badge-success"></span></td>
                        </tr>
                        <tr>
                            <td><strong></strong></td>
                            <td>{input_info.get('source', '').title()}</td>
                            <td><span class="badge badge-info">VHH</span></td>
                        </tr>
                        <tr>
                            <td><strong>CDR3</strong></td>
                            <td>{len(cdrs.get('CDR3', ''))} </td>
                            <td><span class="badge {'badge-warning' if len(cdrs.get('CDR3', '')) >= 20 else 'badge-success'}">
                                {'CDR3' if len(cdrs.get('CDR3', '')) >= 20 else ''}
                            </span></td>
                        </tr>
                    </tbody>
                </table>
                
                <div class="sequence-box">
                    <div style="color: #95a5a6; font-size: 0.85em; margin-bottom: 10px;">VHH</div>
                    {format_sequence(EGFR_VHH_SEQ)}
                </div>
            </div>
            
            <!--  -->
            <div class="section">
                <h2 class="section-title"></h2>
                
                <h3 style="margin-top: 20px; color: #34495e;"></h3>
                <table class="data-table">
                    <thead>
                        <tr>
                            <th></th>
                            <th></th>
                        </tr>
                    </thead>
                    <tbody>
                        <tr>
                            <td><strong>ID</strong></td>
                            <td><code>{template.get('template_id', 'N/A')}</code></td>
                        </tr>
                        <tr>
                            <td><strong>VHH-SAFE</strong></td>
                            <td><span class="badge badge-info"> {template.get('panel', 'N/A')}</span></td>
                        </tr>
                        <tr>
                            <td><strong></strong></td>
                            <td><strong>{scoring.get('framework_identity', 0):.1%}</strong></td>
                        </tr>
                        <tr>
                            <td><strong>CDR</strong></td>
                            <td><strong>{scoring.get('cdr_compatibility_score', 0):.3f}</strong></td>
                        </tr>
                    </tbody>
                </table>
                
                <h3 style="margin-top: 30px; color: #34495e;"></h3>
                <div class="sequence-box">
                    <div style="color: #95a5a6; font-size: 0.85em; margin-bottom: 10px;">VHH</div>
                    {format_sequence(best_match.get('humanized_sequence', ''))}
                </div>
                
                {generate_cdr_section_cn(cdrs, cdr_canonical)}
            </div>
            
            {generate_framework_selection_section_cn(query_numbering, framework_selection_result) if framework_selection_result else ""}
            
            <!--  -->
            <div class="section">
                <h2 class="section-title"></h2>
                
                <div class="strategy-box">
                    <h3 style="color: #1565c0; margin-bottom: 10px;">FR</h3>
                    <p style="margin-bottom: 10px;">
                        （：0.6），CDR（：0.15）
                        developability（：0.25）。FR
                        CDR。
                    </p>
                    <p style="margin: 0;">
                        <strong>：</strong>  = 0.6 × FR + 0.15 × CDR + 0.25 × Developability
                    </p>
                </div>
                
                <div class="two-column">
                    <div>
                        <h3 style="color: #34495e; margin-bottom: 15px;"></h3>
                        <table class="data-table">
                            <thead>
                                <tr>
                                    <th></th>
                                    <th></th>
                                </tr>
                            </thead>
                            <tbody>
                                <tr>
                                    <td></td>
                                    <td>
                                        <div style="text-align: center;">
                                            <div style="font-size: 1.3em; font-weight: bold;">{scoring.get('framework_identity', 0):.3f}</div>
                                            <div class="score-bar">
                                                <div class="score-fill" style="width: {scoring.get('framework_identity', 0) * 100}%">
                                                    {scoring.get('framework_identity', 0):.1%}
                                                </div>
                                            </div>
                                        </div>
                                    </td>
                                </tr>
                                <tr>
                                    <td>CDR</td>
                                    <td>
                                        <div style="text-align: center;">
                                            <div style="font-size: 1.3em; font-weight: bold;">{scoring.get('cdr_compatibility_score', 0):.3f}</div>
                                            <div class="score-bar">
                                                <div class="score-fill" style="width: {scoring.get('cdr_compatibility_score', 0) * 100}%">
                                                    {scoring.get('cdr_compatibility_score', 0):.1%}
                                                </div>
                                            </div>
                                        </div>
                                    </td>
                                </tr>
                                <tr>
                                    <td>Developability</td>
                                    <td>
                                        <div style="text-align: center;">
                                            <div style="font-size: 1.3em; font-weight: bold;">{scoring.get('developability_score', 0):.3f}</div>
                                            <div class="score-bar">
                                                <div class="score-fill {'warning' if scoring.get('developability_score', 0) < 0.6 else 'error' if scoring.get('developability_score', 0) < 0.4 else ''}" style="width: {scoring.get('developability_score', 0) * 100}%">
                                                    {scoring.get('developability_score', 0):.1%}
                                                </div>
                                            </div>
                                        </div>
                                    </td>
                                </tr>
                                <tr style="background: #f8f9fa; font-weight: bold;">
                                    <td></td>
                                    <td>
                                        <div style="text-align: center; font-size: 1.5em; color: #2a5298; font-weight: bold;">
                                            {scoring.get('combined_score', 0):.3f}
                                        </div>
                                    </td>
                                </tr>
                            </tbody>
                        </table>
                    </div>
                    
                    <div>
                        <h3 style="color: #34495e; margin-bottom: 15px;"></h3>
                        {generate_panel_comparison_cn(best_by_plan)}
                    </div>
                </div>
            </div>
            
            <!-- Developability -->
            <div class="section">
                <h2 class="section-title">Developability</h2>
                
                <div class="summary-grid" style="margin-top: 20px;">
                    <div class="summary-card">
                        <h3></h3>
                        <div class="value">
                            <span class="badge {'badge-success' if developability.get('grade') == 'A' else 'badge-warning' if developability.get('grade') == 'B' else 'badge-error'}">
                                 {developability.get('grade', 'N/A')}
                            </span>
                        </div>
                        <div class="label">CMC</div>
                    </div>
                    <div class="summary-card">
                        <h3>Developability</h3>
                        <div class="value">{developability.get('score', 0):.3f}</div>
                        <div class="label">0.0 () - 1.0 ()</div>
                    </div>
                    <div class="summary-card">
                        <h3>Liabilities</h3>
                        <div class="value">{len(developability.get('liabilities', []))}</div>
                        <div class="label"></div>
                    </div>
                </div>
            </div>
            
            <!--  -->
            <div class="section">
                <h2 class="section-title"></h2>
                
                {generate_risk_assessment_cn(quality_flags, risk_flags, developability, immunogenicity)}
                
                {generate_cdr_warnings_section_cn(quality_flags.get('cdr_warnings', []))}
            </div>
            
            <!--  -->
            <div class="section">
                <h2 class="section-title"></h2>
                
                <div class="recommendation-box">
                    <h3 style="color: #2e7d32; margin-bottom: 15px;">✓ </h3>
                    <ol style="margin-left: 20px; line-height: 2;">
                        <li><strong></strong>：</li>
                        <li><strong></strong>：SPRBLI</li>
                        <li><strong></strong>：developability，FR2</li>
                        <li><strong></strong>：FR，T</li>
                        <li><strong></strong>：A，BC</li>
                    </ol>
                </div>
            </div>
            
            <!--  -->
            <div class="section">
                <h2 class="section-title"></h2>
                
                <table class="data-table">
                    <thead>
                        <tr>
                            <th></th>
                            <th></th>
                        </tr>
                    </thead>
                    <tbody>
                        <tr>
                            <td><strong></strong></td>
                            <td>VHH v2.2.0 (FR)</td>
                        </tr>
                        <tr>
                            <td><strong></strong></td>
                            <td>VH3 VHH-SAFE（90）</td>
                        </tr>
                        <tr>
                            <td><strong></strong></td>
                            <td>FR（FR 0.6, CDR 0.15, Dev 0.25）</td>
                        </tr>
                        <tr>
                            <td><strong>IMGT</strong></td>
                            <td>ANARCII（）</td>
                        </tr>
                        <tr>
                            <td><strong>ID</strong></td>
                            <td><code>{output_id}</code></td>
                        </tr>
                    </tbody>
                </table>
            </div>
        </div>
        
        <div style="background: #2c3e50; color: white; padding: 30px 40px; text-align: center;">
            <div style="font-size: 1.5em; font-weight: bold; margin-bottom: 10px;">VHH</div>
            <div style="font-size: 0.9em; opacity: 0.8;">
                。<br>
                ，。<br>
                 - 
            </div>
        </div>
    </div>
</body>
</html>"""
    
    return html


def generate_cro_html_report_failed_cn(result: dict, output_id: str) -> str:
    """CRO（）"""
    error_msg = result.get('error', '')
    input_info = result.get('input', {})
    
    html = f"""<!DOCTYPE html>
<html lang="zh-CN">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>EGFR VHH | </title>
    <style>
        * {{ margin: 0; padding: 0; box-sizing: border-box; }}
        body {{
            font-family: 'Microsoft YaHei', 'SimHei', sans-serif;
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
            <h1>EGFR VHH</h1>
            <div style="margin-top: 20px;"></div>
        </div>
        <div class="content">
            <div class="error-box">
                <h2></h2>
                <p><strong>：</strong> {error_msg}</p>
                <p style="margin-top: 20px;">
                    。CDR、
                    。
                </p>
            </div>
            <h2 style="margin-top: 40px;"></h2>
            <p><strong>：</strong> {input_info.get('length', len(EGFR_VHH_SEQ))} </p>
            <pre style="background: #f4f4f4; padding: 20px; border-radius: 8px; overflow-x: auto;">{EGFR_VHH_SEQ}</pre>
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


def generate_framework_selection_section_cn(query_numbering: list, selection_result: dict = None) -> str:
    """（）"""
    if not selection_result:
        return ""
    
    try:
        from core.framework_selection.report_renderer import render_framework_selection_section_cn
        return render_framework_selection_section_cn(query_numbering, selection_result)
    except Exception:
        return ""


def generate_cdr_section_cn(cdrs: dict, cdr_canonical: dict) -> str:
    """CDR（）"""
    html = """
    <h3 style="margin-top: 30px; color: #34495e;">CDR</h3>
    <table class="data-table">
        <thead>
            <tr>
                <th>CDR</th>
                <th></th>
                <th></th>
                <th></th>
                <th></th>
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
                    <span class="badge {'badge-success' if compat >= 0.7 else 'badge-warning' if compat >= 0.5 else 'badge-info'}">
                        {compat:.2f}
                    </span>
                </td>
            </tr>"""
    
    html += """
        </tbody>
    </table>"""
    
    return html


def generate_panel_comparison_cn(best_by_plan: dict) -> str:
    """Panel（）"""
    if not best_by_plan:
        return "<p>（）。</p>"
    
    html = """
    <table class="data-table">
        <thead>
            <tr>
                <th></th>
                <th>ID</th>
                <th></th>
                <th></th>
            </tr>
        </thead>
        <tbody>"""
    
    for panel, plan_result in best_by_plan.items():
        if plan_result:
            plan_template = plan_result.get('template', {})
            plan_scoring = plan_result.get('scoring', {})
            html += f"""
            <tr>
                <td><strong> {panel}</strong></td>
                <td><code>{plan_template.get('template_id', 'N/A')}</code></td>
                <td><strong>{plan_scoring.get('combined_score', 0):.3f}</strong></td>
                <td>{plan_scoring.get('framework_identity', 0):.1%}</td>
            </tr>"""
    
    html += """
        </tbody>
    </table>"""
    
    return html


def generate_risk_assessment_cn(quality_flags: dict, risk_flags: dict, developability: dict, immunogenicity: dict) -> str:
    """（）"""
    warnings = []
    
    if risk_flags.get('long_cdr3'):
        warnings.append({
            'type': 'info',
            'title': 'CDR3',
            'message': 'CDR3。。'
        })
    
    if risk_flags.get('noncanonical_disulfide_suspected'):
        warnings.append({
            'type': 'warning',
            'title': '',
            'message': 'CDR3。。'
        })
    
    dev_risk = developability.get('risk', '')
    if dev_risk in ('medium', 'high'):
        warnings.append({
            'type': 'warning',
            'title': f'Developability：{dev_risk.upper()}',
            'message': f'CMC{dev_risk}。。'
        })
    
    immuno_risk = immunogenicity.get('fr_immuno_risk', '')
    if immuno_risk in ('medium', 'high'):
        warnings.append({
            'type': 'warning',
            'title': f'FR：{immuno_risk.upper()}',
            'message': '。。'
        })
    
    if not warnings:
        return """
        <div style="background: #e8f5e9; padding: 20px; border-radius: 8px;">
            <strong style="color: #2e7d32;">✓ </strong>
            <p style="margin-top: 10px; color: #2e7d32;">，。</p>
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


def generate_cdr_warnings_section_cn(cdr_warnings: list) -> str:
    """CDR（）"""
    if not cdr_warnings:
        return ""
    
    # 
    unique_warnings = list(set(cdr_warnings))
    
    html = """
    <h3 style="margin-top: 30px; color: #34495e;">CDR</h3>
    <div class="warning-box">
        <h4>⚠️ CDR（FR）</h4>
        <p style="margin-bottom: 10px;">
            CDR。FR，（），
            ：
        </p>
        <ul style="margin-left: 20px; line-height: 2;">"""
    
    for warning in unique_warnings[:10]:  # 10
        html += f"<li>{warning}</li>"
    
    html += """
        </ul>
        <p style="margin-top: 15px; font-style: italic;">
            <strong>：</strong> 。FRCDR，
            FR。。
        </p>
    </div>"""
    
    return html


if __name__ == "__main__":
    report_path = generate_cro_report_cn()
    if report_path:
        print(f"\n{'='*80}")
        print("CRO（）！")
        print(f"{'='*80}")
        print(f": {report_path}")
        print(f"\nHTML。")


















