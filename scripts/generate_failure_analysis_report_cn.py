"""
EGFR VHH（）

，
"""

import sys
from pathlib import Path
from datetime import datetime
import json

PROJECT_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT_ROOT))

from core.vhh_humanization import humanize_vhh, split_regions, find_best_matching_scaffold
from core.numbering.imgt_anarcii import imgt_number_anarcii, build_pos_to_aa_map, IMGTNumberingError
from core.cdr_canonical import classify_all_cdrs, get_key_position_residues
from core.scaffolds import load_alpaca_vhh_scaffolds, load_human_vhh_safe_templates, load_alignment_matrix

# EGFR VHH
EGFR_VHH_SEQ = "QVQLVESGGGLVQVGGSLRLSRALSGFWYNHMGWFRQAPGKEREGVAVITADSGSTTYADSVKGRFTISRDDARNTVYLQMNSLKPEDTAVYYCAAGGVGWPYFDYWGQGTQVTVSS"


def analyze_failure_reasons(seq: str) -> dict:
    """"""
    
    analysis = {
        'sequence_info': {},
        'imgt_numbering': {},
        'cdr_analysis': {},
        'scaffold_matching': {},
        'template_filtering': {},
        'failure_reasons': [],
        'recommendations': []
    }
    
    # 1. 
    analysis['sequence_info'] = {
        'length': len(seq),
        'sequence': seq,
        'is_valid': len(seq) > 50 and all(c in 'ACDEFGHIKLMNPQRSTVWY' for c in seq.upper())
    }
    
    # 2. IMGT
    try:
        rows = imgt_number_anarcii(seq)
        pos_map = build_pos_to_aa_map(rows)
        analysis['imgt_numbering'] = {
            'success': True,
            'total_positions': len(pos_map),
            'key_positions': {
                '37': pos_map.get(37, 'N/A'),
                '44': pos_map.get(44, 'N/A'),
                '45': pos_map.get(45, 'N/A'),
                '47': pos_map.get(47, 'N/A'),
            }
        }
    except Exception as e:
        analysis['imgt_numbering'] = {
            'success': False,
            'error': str(e)
        }
        analysis['failure_reasons'].append(f"IMGT: {e}")
        return analysis
    
    # 3. CDR
    try:
        key_positions = get_key_position_residues(pos_map)
        vhh_regions = split_regions(rows)  # 
        cdrs = {
            'CDR1': vhh_regions.get('CDR1', ''),
            'CDR2': vhh_regions.get('CDR2', ''),
            'CDR3': vhh_regions.get('CDR3', ''),
        }
        cdr_canonical = classify_all_cdrs(cdrs, key_positions=key_positions)
        
        analysis['cdr_analysis'] = {
            'cdr1': {
                'sequence': cdrs.get('CDR1', ''),
                'length': len(cdrs.get('CDR1', '')),
                'canonical': cdr_canonical.get('cdr1', {}).get('canonical_class', 'Unknown'),
                'compatibility_score': cdr_canonical.get('cdr1', {}).get('compatibility_score', 0)
            },
            'cdr2': {
                'sequence': cdrs.get('CDR2', ''),
                'length': len(cdrs.get('CDR2', '')),
                'canonical': cdr_canonical.get('cdr2', {}).get('canonical_class', 'Unknown'),
                'compatibility_score': cdr_canonical.get('cdr2', {}).get('compatibility_score', 0)
            },
            'cdr3': {
                'sequence': cdrs.get('CDR3', ''),
                'length': len(cdrs.get('CDR3', '')),
                'canonical': cdr_canonical.get('cdr3', {}).get('canonical_class', 'Unknown'),
                'cys_count': cdrs.get('CDR3', '').count('C'),
                'is_extreme': len(cdrs.get('CDR3', '')) >= 20 or cdrs.get('CDR3', '').count('C') >= 3
            }
        }
        
        # CDR
        cdr1_score = analysis['cdr_analysis']['cdr1']['compatibility_score']
        cdr2_score = analysis['cdr_analysis']['cdr2']['compatibility_score']
        
        if cdr1_score < 0.7 or cdr2_score < 0.7:
            analysis['failure_reasons'].append(
                f"CDR (CDR1: {cdr1_score:.2f}, CDR2: {cdr2_score:.2f})，"
                f"0.7"
            )
        
        if analysis['cdr_analysis']['cdr3']['is_extreme']:
            analysis['failure_reasons'].append(
                f"CDR3：{analysis['cdr_analysis']['cdr3']['length']}aa "
                f"(≥20aa) {analysis['cdr_analysis']['cdr3']['cys_count']}Cys (≥3)，"
                f""
            )
            
    except Exception as e:
        analysis['cdr_analysis'] = {
            'error': str(e)
        }
        analysis['failure_reasons'].append(f"CDR: {e}")
    
    # 4. Scaffold
    try:
        alpaca_scaffolds = load_alpaca_vhh_scaffolds()
        best_scaffold, scaffold_identity = find_best_matching_scaffold(seq, alpaca_scaffolds)
        
        analysis['scaffold_matching'] = {
            'best_scaffold_id': best_scaffold['scaffold_id'] if best_scaffold else None,
            'best_identity': scaffold_identity,
            'total_scaffolds': len(alpaca_scaffolds),
            'match_found': best_scaffold is not None
        }
        
        if not best_scaffold:
            analysis['failure_reasons'].append(
                f"scaffold (identity: {scaffold_identity:.1%} < )"
            )
            
    except Exception as e:
        analysis['scaffold_matching'] = {
            'error': str(e)
        }
        analysis['failure_reasons'].append(f"Scaffold: {e}")
    
    # 5. 
    try:
        if analysis['scaffold_matching'].get('best_scaffold_id'):
            alignment_index = load_alignment_matrix()
            human_templates = load_human_vhh_safe_templates()
            
            scaffold_id = analysis['scaffold_matching']['best_scaffold_id']
            
            if scaffold_id in alignment_index:
                alignments = alignment_index[scaffold_id]
                total_templates = len(alignments)
                
                # panel
                panel_counts = {'A': 0, 'B': 0, 'C': 0}
                for template_id, scores in alignments.items():
                    plan = scores.get('human_plan', '').upper()
                    if plan in panel_counts:
                        panel_counts[plan] += 1
                
                # CDR
                filtered_count = 0
                for template_id, scores in alignments.items():
                    template = next((t for t in human_templates if t['template_id'] == template_id), None)
                    if template:
                        # ，
                        filtered_count += 1
                
                analysis['template_filtering'] = {
                    'total_templates': total_templates,
                    'panel_distribution': panel_counts,
                    'estimated_filtered': filtered_count,
                    'filtering_rate': filtered_count / total_templates if total_templates > 0 else 0
                }
                
                if filtered_count == 0:
                    analysis['failure_reasons'].append(
                        f"{total_templates}CDR "
                        f"(: 0.7)"
                    )
            else:
                analysis['template_filtering'] = {
                    'error': f"Scaffold {scaffold_id} "
                }
                analysis['failure_reasons'].append(
                    f"Scaffold {scaffold_id} Human"
                )
    except Exception as e:
        analysis['template_filtering'] = {
            'error': str(e)
        }
        analysis['failure_reasons'].append(f": {e}")
    
    # 6. 
    if analysis['failure_reasons']:
        if any('CDR' in r for r in analysis['failure_reasons']):
            analysis['recommendations'].append(
                "CDR（0.70.5），CDR"
            )
            analysis['recommendations'].append(
                "scoring profile（'minimized_immunogenicity'）"
            )
        
        if any('CDR3' in r for r in analysis['failure_reasons']):
            analysis['recommendations'].append(
                "CDR3，extreme_cdr3_mode，"
                "top_k（≥10）"
            )
        
        if any('scaffold' in r.lower() for r in analysis['failure_reasons']):
            analysis['recommendations'].append(
                "VHH，"
            )
        
        if any('' in r for r in analysis['failure_reasons']):
            analysis['recommendations'].append(
                "panel='all'panel，"
            )
            analysis['recommendations'].append(
                "，human_vh3_vhh_safe_templates.json"
            )
    
    return analysis




def generate_chinese_failure_report(analysis: dict, output_id: str) -> str:
    """"""
    
    html = f"""<!DOCTYPE html>
<html lang="zh-CN">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>EGFR VHH</title>
    <style>
        * {{
            margin: 0;
            padding: 0;
            box-sizing: border-box;
        }}
        
        body {{
            font-family: 'Microsoft YaHei', 'SimHei', 'Segoe UI', sans-serif;
            line-height: 1.8;
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
            background: linear-gradient(135deg, #e74c3c 0%, #c0392b 100%);
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
            margin-top: 10px;
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
        
        .warning-box {{
            background: #fff3cd;
            border-left: 4px solid #f39c12;
            padding: 20px;
            margin: 20px 0;
            border-radius: 4px;
        }}
        
        .error-box {{
            background: #fee;
            border-left: 4px solid #e74c3c;
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
        
        .summary-grid {{
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(250px, 1fr));
            gap: 20px;
            margin-top: 20px;
        }}
        
        .summary-card {{
            background: #f8f9fa;
            padding: 20px;
            border-radius: 8px;
            box-shadow: 0 2px 10px rgba(0,0,0,0.1);
        }}
        
        .summary-card h3 {{
            color: #667eea;
            font-size: 0.9em;
            text-transform: uppercase;
            margin-bottom: 10px;
        }}
        
        .summary-card .value {{
            font-size: 2em;
            font-weight: bold;
            color: #2c3e50;
        }}
    </style>
</head>
<body>
    <div class="container">
        <div class="header">
            <h1>EGFR VHH</h1>
            <div class="subtitle"></div>
            <div style="margin-top: 30px; font-size: 0.95em; opacity: 0.8;">
                ID: {output_id}<br>
                : {datetime.now().strftime("%Y%m%d %H:%M:%S")}
            </div>
        </div>
        
        <div class="content">
            <!--  -->
            <div class="section">
                <h2 class="section-title"></h2>
                <div class="error-box">
                    <h3 style="color: #c0392b; margin-bottom: 15px;">⚠️ </h3>
                    <p style="margin-bottom: 15px;">
                        EGFR VHH，。
                    </p>
                    <p><strong>：</strong> {len(analysis['failure_reasons'])}</p>
                </div>
                
                <div class="summary-grid">
                    <div class="summary-card">
                        <h3></h3>
                        <div class="value">{analysis['sequence_info']['length']}</div>
                        <div style="font-size: 0.85em; color: #7f8c8d; margin-top: 5px;"></div>
                    </div>
                    <div class="summary-card">
                        <h3>IMGT</h3>
                        <div class="value">
                            <span class="badge {'badge-success' if analysis['imgt_numbering'].get('success') else 'badge-error'}">
                                {'' if analysis['imgt_numbering'].get('success') else ''}
                            </span>
                        </div>
                    </div>
                    <div class="summary-card">
                        <h3>Scaffold</h3>
                        <div class="value">
                            <span class="badge {'badge-success' if analysis['scaffold_matching'].get('match_found') else 'badge-error'}">
                                {'' if analysis['scaffold_matching'].get('match_found') else ''}
                            </span>
                        </div>
                    </div>
                    <div class="summary-card">
                        <h3></h3>
                        <div class="value">{len(analysis['failure_reasons'])}</div>
                        <div style="font-size: 0.85em; color: #7f8c8d; margin-top: 5px;"></div>
                    </div>
                </div>
            </div>
            
            <!--  -->
            <div class="section">
                <h2 class="section-title"></h2>
                
                {generate_failure_reasons_section(analysis['failure_reasons'])}
            </div>
            
            <!--  -->
            <div class="section">
                <h2 class="section-title"></h2>
                
                <div class="sequence-box">
                    <div style="color: #95a5a6; font-size: 0.85em; margin-bottom: 10px;">VHH</div>
                    {format_sequence(analysis['sequence_info']['sequence'])}
                </div>
                
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
                            <td>{analysis['sequence_info']['length']} </td>
                            <td><span class="badge {'badge-success' if 50 < analysis['sequence_info']['length'] < 150 else 'badge-warning'}">
                                {'' if 50 < analysis['sequence_info']['length'] < 150 else ''}
                            </span></td>
                        </tr>
                        <tr>
                            <td><strong></strong></td>
                            <td>{'' if analysis['sequence_info'].get('is_valid') else ''}</td>
                            <td><span class="badge {'badge-success' if analysis['sequence_info'].get('is_valid') else 'badge-error'}">
                                {'' if analysis['sequence_info'].get('is_valid') else ''}
                            </span></td>
                        </tr>
                    </tbody>
                </table>
            </div>
            
            <!-- IMGT -->
            {generate_imgt_section(analysis['imgt_numbering'])}
            
            <!-- CDR -->
            {generate_cdr_section_cn(analysis['cdr_analysis'])}
            
            <!-- Scaffold -->
            {generate_scaffold_section(analysis['scaffold_matching'])}
            
            <!--  -->
            {generate_template_filtering_section(analysis['template_filtering'])}
            
            <!--  -->
            <div class="section">
                <h2 class="section-title"></h2>
                
                {generate_recommendations_section(analysis['recommendations'], analysis['failure_reasons'])}
            </div>
            
            <!--  -->
            <div class="section">
                <h2 class="section-title"></h2>
                
                <div class="warning-box">
                    <h4></h4>
                    <ul style="margin-left: 20px; margin-top: 10px;">
                        <li><strong>CDR：</strong> 0.7（）</li>
                        <li><strong>CDR：</strong> 0.5（）</li>
                        <li><strong>CDR3：</strong> ≥20aa  Cys≥3</li>
                        <li><strong>Scaffold：</strong> Identity ≥ 70%</li>
                    </ul>
                </div>
                
                <div class="recommendation-box">
                    <h4></h4>
                    <ol style="margin-left: 20px; margin-top: 10px; line-height: 2;">
                        <li></li>
                        <li>CDR（config.yamlhard_min_cdr_score）</li>
                        <li>panel='all'</li>
                        <li>CDR3，top_k≥10</li>
                        <li>（human_vh3_vhh_safe_templates.json）</li>
                        <li>CDR（use_cdr_filtering=False）</li>
                    </ol>
                </div>
            </div>
        </div>
        
        <div style="background: #2c3e50; color: white; padding: 30px 40px; text-align: center;">
            <div style="font-size: 1.5em; font-weight: bold; margin-bottom: 10px;">VHH</div>
            <div style="font-size: 0.9em; opacity: 0.8;">
                <br>
                 - 
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


def generate_failure_reasons_section(reasons: list) -> str:
    """"""
    if not reasons:
        return """
        <div class="recommendation-box">
            <h4>✓ </h4>
            <p>。</p>
        </div>"""
    
    html = ""
    for i, reason in enumerate(reasons, 1):
        html += f"""
        <div class="error-box" style="margin-bottom: 15px;">
            <h4 style="color: #c0392b;"> {i}: {reason}</h4>
        </div>"""
    
    return html


def generate_imgt_section(imgt_info: dict) -> str:
    """IMGT"""
    if not imgt_info.get('success'):
        return f"""
        <div class="section">
            <h2 class="section-title">IMGT</h2>
            <div class="error-box">
                <h4>❌ IMGT</h4>
                <p><strong>：</strong> {imgt_info.get('error', 'Unknown error')}</p>
            </div>
        </div>"""
    
    key_pos = imgt_info.get('key_positions', {})
    return f"""
    <div class="section">
        <h2 class="section-title">IMGT</h2>
        <div class="recommendation-box">
            <h4>✓ IMGT</h4>
            <p> {imgt_info.get('total_positions', 0)} IMGT</p>
        </div>
        
        <h3 style="margin-top: 30px; color: #34495e;">VHH Hallmark（FR2）</h3>
        <table class="data-table">
            <thead>
                <tr>
                    <th>IMGT</th>
                    <th></th>
                    <th>VHH</th>
                    <th></th>
                </tr>
            </thead>
            <tbody>
                <tr>
                    <td>37</td>
                    <td><strong>{key_pos.get('37', 'N/A')}</strong></td>
                    <td>/ (Y, S, N, T, H, Q)</td>
                    <td><span class="badge {'badge-success' if key_pos.get('37', '') in ['Y', 'S', 'N', 'T', 'H', 'Q'] else 'badge-warning'}">
                        {'VHH' if key_pos.get('37', '') in ['Y', 'S', 'N', 'T', 'H', 'Q'] else 'VH'}
                    </span></td>
                </tr>
                <tr>
                    <td>44</td>
                    <td><strong>{key_pos.get('44', 'N/A')}</strong></td>
                    <td>Q/E（VHH）</td>
                    <td><span class="badge {'badge-success' if key_pos.get('44', '') in ['Q', 'E'] else 'badge-warning'}">
                        {'VHH' if key_pos.get('44', '') in ['Q', 'E'] else 'VH'}
                    </span></td>
                </tr>
                <tr>
                    <td>45</td>
                    <td><strong>{key_pos.get('45', 'N/A')}</strong></td>
                    <td>R（）</td>
                    <td><span class="badge {'badge-success' if key_pos.get('45', '') == 'R' else 'badge-warning'}">
                        {'VHH' if key_pos.get('45', '') == 'R' else 'VH'}
                    </span></td>
                </tr>
                <tr>
                    <td>47</td>
                    <td><strong>{key_pos.get('47', 'N/A')}</strong></td>
                    <td>G/L（）</td>
                    <td><span class="badge {'badge-success' if key_pos.get('47', '') in ['G', 'L'] else 'badge-warning'}">
                        {'VHH' if key_pos.get('47', '') in ['G', 'L'] else 'VH'}
                    </span></td>
                </tr>
            </tbody>
        </table>
    </div>"""


def generate_cdr_section_cn(cdr_info: dict) -> str:
    """CDR（）"""
    if 'error' in cdr_info:
        return f"""
        <div class="section">
            <h2 class="section-title">CDR</h2>
            <div class="error-box">
                <h4>❌ CDR</h4>
                <p><strong>：</strong> {cdr_info['error']}</p>
            </div>
        </div>"""
    
    cdr1 = cdr_info.get('cdr1', {})
    cdr2 = cdr_info.get('cdr2', {})
    cdr3 = cdr_info.get('cdr3', {})
    
    return f"""
    <div class="section">
        <h2 class="section-title">CDR</h2>
        
        <table class="data-table">
            <thead>
                <tr>
                    <th>CDR</th>
                    <th></th>
                    <th></th>
                    <th></th>
                    <th></th>
                    <th></th>
                </tr>
            </thead>
            <tbody>
                <tr>
                    <td><strong>CDR1</strong></td>
                    <td><code>{cdr1.get('sequence', 'N/A')}</code></td>
                    <td>{cdr1.get('length', 0)} aa</td>
                    <td>{cdr1.get('canonical', 'Unknown')}</td>
                    <td>{cdr1.get('compatibility_score', 0):.3f}</td>
                    <td><span class="badge {'badge-error' if cdr1.get('compatibility_score', 0) < 0.7 else 'badge-success'}">
                        {'' if cdr1.get('compatibility_score', 0) < 0.7 else ''}
                    </span></td>
                </tr>
                <tr>
                    <td><strong>CDR2</strong></td>
                    <td><code>{cdr2.get('sequence', 'N/A')}</code></td>
                    <td>{cdr2.get('length', 0)} aa</td>
                    <td>{cdr2.get('canonical', 'Unknown')}</td>
                    <td>{cdr2.get('compatibility_score', 0):.3f}</td>
                    <td><span class="badge {'badge-error' if cdr2.get('compatibility_score', 0) < 0.7 else 'badge-success'}">
                        {'' if cdr2.get('compatibility_score', 0) < 0.7 else ''}
                    </span></td>
                </tr>
                <tr>
                    <td><strong>CDR3</strong></td>
                    <td><code>{cdr3.get('sequence', 'N/A')}</code></td>
                    <td>{cdr3.get('length', 0)} aa</td>
                    <td>{cdr3.get('canonical', 'Unknown')}</td>
                    <td>-</td>
                    <td><span class="badge {'badge-warning' if cdr3.get('is_extreme') else 'badge-success'}">
                        {'' if cdr3.get('is_extreme') else ''}
                    </span></td>
                </tr>
            </tbody>
        </table>
        
        {f'''
        <div class="warning-box" style="margin-top: 20px;">
            <h4>⚠️ CDR3</h4>
            <p>CDR3: {cdr3.get('length', 0)}aa (: 20aa)</p>
            <p>CDR3Cys: {cdr3.get('cys_count', 0)} (: 3)</p>
            <p>CDR3，。</p>
        </div>''' if cdr3.get('is_extreme') else ''}
    </div>"""


def generate_scaffold_section(scaffold_info: dict) -> str:
    """Scaffold"""
    if 'error' in scaffold_info:
        return f"""
        <div class="section">
            <h2 class="section-title">Scaffold</h2>
            <div class="error-box">
                <h4>❌ Scaffold</h4>
                <p><strong>：</strong> {scaffold_info['error']}</p>
            </div>
        </div>"""
    
    return f"""
    <div class="section">
        <h2 class="section-title">Scaffold</h2>
        
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
                    <td><strong>Scaffold</strong></td>
                    <td><code>{scaffold_info.get('best_scaffold_id', 'N/A')}</code></td>
                    <td><span class="badge {'badge-success' if scaffold_info.get('match_found') else 'badge-error'}">
                        {'' if scaffold_info.get('match_found') else ''}
                    </span></td>
                </tr>
                <tr>
                    <td><strong>Identity</strong></td>
                    <td>{scaffold_info.get('best_identity', 0):.1%}</td>
                    <td><span class="badge {'badge-success' if scaffold_info.get('best_identity', 0) >= 0.7 else 'badge-error'}">
                        {'≥70%' if scaffold_info.get('best_identity', 0) >= 0.7 else '<70%'}
                    </span></td>
                </tr>
                <tr>
                    <td><strong>Scaffold</strong></td>
                    <td>{scaffold_info.get('total_scaffolds', 0)}</td>
                    <td>-</td>
                </tr>
            </tbody>
        </table>
    </div>"""


def generate_template_filtering_section(filtering_info: dict) -> str:
    """"""
    if 'error' in filtering_info:
        return f"""
        <div class="section">
            <h2 class="section-title"></h2>
            <div class="error-box">
                <h4>❌ </h4>
                <p><strong>：</strong> {filtering_info['error']}</p>
            </div>
        </div>"""
    
    panel_dist = filtering_info.get('panel_distribution', {})
    return f"""
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
                    <td>{filtering_info.get('total_templates', 0)}</td>
                </tr>
                <tr>
                    <td><strong>Panel A</strong></td>
                    <td>{panel_dist.get('A', 0)}</td>
                </tr>
                <tr>
                    <td><strong>Panel B</strong></td>
                    <td>{panel_dist.get('B', 0)}</td>
                </tr>
                <tr>
                    <td><strong>Panel C</strong></td>
                    <td>{panel_dist.get('C', 0)}</td>
                </tr>
                <tr>
                    <td><strong>（）</strong></td>
                    <td>{filtering_info.get('estimated_filtered', 0)}</td>
                </tr>
                <tr>
                    <td><strong></strong></td>
                    <td>{filtering_info.get('filtering_rate', 0):.1%}</td>
                </tr>
            </tbody>
        </table>
        
        {f'''
        <div class="error-box" style="margin-top: 20px;">
            <h4>⚠️ </h4>
            <p>0，CDR。</p>
            <p>CDRCDR。</p>
        </div>''' if filtering_info.get('estimated_filtered', 0) == 0 else ''}
    </div>"""


def generate_recommendations_section(recommendations: list, failure_reasons: list) -> str:
    """"""
    html = ""
    
    if recommendations:
        for i, rec in enumerate(recommendations, 1):
            html += f"""
            <div class="recommendation-box" style="margin-bottom: 15px;">
                <h4> {i}</h4>
                <p>{rec}</p>
            </div>"""
    else:
        html = """
        <div class="recommendation-box">
            <h4></h4>
            <ul style="margin-left: 20px; line-height: 2;">
                <li></li>
                <li></li>
                <li>panel</li>
                <li></li>
            </ul>
        </div>"""
    
    # 
    html += """
    <div class="warning-box" style="margin-top: 30px;">
        <h4></h4>
        <pre style="background: #f4f4f4; padding: 15px; border-radius: 4px; overflow-x: auto;">
# 1: CDR
from core.vhh_humanization import humanize_vhh

result = humanize_vhh(
    seq="...",
    panel="all",
    top_k=15,  # 
    # ：config.yamlhard_min_cdr_score
)

# 2: 
result = humanize_vhh(
    seq="...",
    panel="all",
    top_k=20,  # 
)
        </pre>
    </div>"""
    
    return html


def main():
    """"""
    print("[INFO] EGFR VHH...")
    
    # 
    analysis = analyze_failure_reasons(EGFR_VHH_SEQ)
    
    # 
    output_id = f"FAILURE_ANALYSIS_{int(datetime.now().timestamp())}"
    html_report = generate_chinese_failure_report(analysis, output_id)
    
    # 
    output_dir = PROJECT_ROOT / "projects" / "EGFR_7D12_VHH" / "cro_report"
    output_dir.mkdir(parents=True, exist_ok=True)
    
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    report_path = output_dir / f"EGFR_VHH__{timestamp}.html"
    
    with open(report_path, "w", encoding="utf-8") as f:
        f.write(html_report)
    
    print(f"[INFO] : {report_path}")
    print(f"\n{'='*80}")
    print("！")
    print(f"{'='*80}")
    print(f"\n: {len(analysis['failure_reasons'])} ")
    for i, reason in enumerate(analysis['failure_reasons'], 1):
        print(f"  {i}. {reason}")
    print(f"\n: {len(analysis['recommendations'])} ")
    print(f"\n: {report_path}")


if __name__ == "__main__":
    main()

