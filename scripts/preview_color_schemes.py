#!/usr/bin/env python3
"""
preview_color_schemes.py

Generate a visual preview of all color schemes.
Creates an HTML file showing all 8 schemes side-by-side.
"""

import json
from pathlib import Path
from datetime import datetime
from color_scheme_manager import SchemeManager, SchemeType


def generate_html_preview(output_path: str = "color_schemes_preview.html"):
    """Generate HTML preview of all color schemes."""
    
    schemes = {
        name: SchemeManager.get_scheme(name)
        for name in SchemeManager.BUILTIN_SCHEMES.keys()
    }
    
    html = """<!DOCTYPE html>
<html lang="zh-CN">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>- — </title>
    <style>
        * {
            margin: 0;
            padding: 0;
            box-sizing: border-box;
        }
        
        body {
            font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, "Helvetica Neue", Arial, sans-serif;
            background: linear-gradient(135deg, #f5f7fa 0%, #c3cfe2 100%);
            padding: 20px;
            min-height: 100vh;
        }
        
        .container {
            max-width: 1400px;
            margin: 0 auto;
        }
        
        h1 {
            text-align: center;
            color: #333;
            margin-bottom: 10px;
            font-size: 2.5em;
        }
        
        .subtitle {
            text-align: center;
            color: #666;
            margin-bottom: 40px;
            font-size: 1.1em;
        }
        
        .schemes-grid {
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(350px, 1fr));
            gap: 20px;
            margin-bottom: 40px;
        }
        
        .scheme-card {
            background: white;
            border-radius: 12px;
            box-shadow: 0 8px 16px rgba(0,0,0,0.1);
            overflow: hidden;
            transition: transform 0.3s, box-shadow 0.3s;
        }
        
        .scheme-card:hover {
            transform: translateY(-5px);
            box-shadow: 0 12px 24px rgba(0,0,0,0.15);
        }
        
        .scheme-header {
            padding: 15px;
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            color: white;
        }
        
        .scheme-name {
            font-size: 1.5em;
            font-weight: bold;
            margin-bottom: 5px;
        }
        
        .scheme-type {
            font-size: 0.9em;
            opacity: 0.9;
        }
        
        .scheme-colors {
            padding: 20px;
            display: flex;
            flex-direction: column;
            gap: 12px;
        }
        
        .color-row {
            display: flex;
            align-items: center;
            gap: 15px;
        }
        
        .color-box {
            width: 60px;
            height: 40px;
            border-radius: 6px;
            border: 1px solid #ddd;
            box-shadow: 0 2px 4px rgba(0,0,0,0.1);
        }
        
        .color-info {
            flex: 1;
        }
        
        .color-name {
            font-weight: 600;
            color: #333;
            font-size: 0.95em;
        }
        
        .color-spec {
            font-size: 0.85em;
            color: #666;
            font-family: monospace;
        }
        
        .bfactor-range {
            font-size: 0.8em;
            color: #999;
            margin-top: 2px;
        }
        
        .scheme-commands {
            padding: 15px;
            background: #f8f9fa;
            border-top: 1px solid #eee;
        }
        
        .command-label {
            font-size: 0.85em;
            font-weight: 600;
            color: #666;
            margin-bottom: 8px;
        }
        
        .command-box {
            background: white;
            border: 1px solid #ddd;
            border-radius: 4px;
            padding: 8px;
            font-family: monospace;
            font-size: 0.8em;
            color: #333;
            overflow-x: auto;
            line-height: 1.4;
        }
        
        .reference-section {
            background: white;
            border-radius: 12px;
            padding: 30px;
            box-shadow: 0 8px 16px rgba(0,0,0,0.1);
            margin-bottom: 20px;
        }
        
        .reference-section h2 {
            color: #333;
            margin-bottom: 20px;
            font-size: 1.5em;
            border-bottom: 2px solid #667eea;
            padding-bottom: 10px;
        }
        
        .usage-table {
            width: 100%;
            border-collapse: collapse;
            margin-bottom: 20px;
        }
        
        .usage-table th,
        .usage-table td {
            padding: 12px;
            text-align: left;
            border-bottom: 1px solid #eee;
        }
        
        .usage-table th {
            background: #f8f9fa;
            font-weight: 600;
            color: #333;
        }
        
        .usage-table tr:hover {
            background: #f8f9fa;
        }
        
        .scheme-tag {
            display: inline-block;
            padding: 4px 8px;
            border-radius: 4px;
            font-size: 0.85em;
            font-weight: 500;
        }
        
        .tag-popular { background: #fff3cd; color: #856404; }
        .tag-academic { background: #d1ecf1; color: #0c5460; }
        .tag-print { background: #d4edda; color: #155724; }
        .tag-special { background: #f8d7da; color: #721c24; }
        
        .command-section {
            background: #f8f9fa;
            border-left: 4px solid #667eea;
            padding: 15px;
            border-radius: 4px;
            margin-bottom: 15px;
        }
        
        .command-section code {
            background: white;
            border: 1px solid #ddd;
            border-radius: 4px;
            padding: 2px 6px;
            font-family: monospace;
            color: #d63384;
        }
        
        .footer {
            text-align: center;
            color: #999;
            margin-top: 40px;
            font-size: 0.9em;
        }
        
        .legend {
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(200px, 1fr));
            gap: 15px;
            margin-top: 20px;
        }
        
        .legend-item {
            display: flex;
            align-items: center;
            gap: 10px;
        }
        
        .legend-box {
            width: 40px;
            height: 30px;
            border-radius: 4px;
            border: 1px solid #ddd;
        }
        
        .legend-text {
            flex: 1;
        }
        
        .legend-title {
            font-weight: 600;
            color: #333;
        }
        
        .legend-desc {
            font-size: 0.85em;
            color: #666;
        }
    </style>
</head>
<body>
    <div class="container">
        <h1>🎨  — </h1>
        <p class="subtitle"></p>
        
        <div class="schemes-grid">
"""
    
    # Add each scheme
    scheme_descriptions = {
        "rainbow": ("🌈 Rainbow", "Classic rainbow gradient", "tag-popular"),
        "scientific": ("🔬 Scientific", "Energy-style gradient", "tag-academic"),
        "publication": ("📊 Publication", "Publication-grade colors", "tag-popular"),
        "dark": ("🌙 Dark", "Dark theme optimized", "tag-special"),
        "thermal": ("🔥 Thermal", "Thermal gradient", "tag-academic"),
        "pastel": ("🍰 Pastel", "Soft pastel colors", "tag-popular"),
        "grayscale": ("⬜ Grayscale", "B&W printing", "tag-print"),
        "contrasting": ("🎯 Contrasting", "High contrast", "tag-special"),
    }
    
    for scheme_name, scheme in schemes.items():
        desc, subtitle, tag = scheme_descriptions[scheme_name]
        
        html += f"""
        <div class="scheme-card">
            <div class="scheme-header">
                <div class="scheme-name">{desc}</div>
                <div class="scheme-type">{subtitle}</div>
            </div>
            
            <div class="scheme-colors">
"""
        
        # Add color rows
        for role_name, role in sorted(
            scheme.roles.items(),
            key=lambda x: x[1].bfactor_range[0],
            reverse=True
        ):
            b_min, b_max = role.bfactor_range
            html += f"""
                <div class="color-row">
                    <div class="color-box" style="background-color: {role.color.hex_code};"></div>
                    <div class="color-info">
                        <div class="color-name">{role.color.name}</div>
                        <div class="color-spec">{role.color.pymol_name} / {role.color.hex_code}</div>
                        <div class="bfactor-range">B-factor: {b_min}–{b_max}</div>
                    </div>
                </div>
"""
        
        html += """
            </div>
            
            <div class="scheme-commands">
                <div class="command-label">PyMOL Command:</div>
                <div class="command-box">"""
        
        html += scheme.to_pymol_spectrum()
        
        html += """</div>
            </div>
        </div>
"""
    
    html += """
        </div>
        
        <!-- Reference Section -->
        <div class="reference-section">
            <h2>📋 </h2>
            
            <h3 style="color: #667eea; margin-top: 20px; margin-bottom: 10px;"></h3>
            <table class="usage-table">
                <thead>
                    <tr>
                        <th></th>
                        <th></th>
                        <th></th>
                        <th></th>
                    </tr>
                </thead>
                <tbody>
                    <tr>
                        <td><strong>Publication</strong></td>
                        <td></td>
                        <td>，</td>
                        <td><span class="scheme-tag tag-popular">⭐⭐⭐</span></td>
                    </tr>
                    <tr>
                        <td><strong>Grayscale</strong></td>
                        <td></td>
                        <td>，</td>
                        <td><span class="scheme-tag tag-print">⭐⭐⭐</span></td>
                    </tr>
                    <tr>
                        <td><strong>Rainbow</strong></td>
                        <td></td>
                        <td>，</td>
                        <td><span class="scheme-tag tag-popular">⭐⭐</span></td>
                    </tr>
                    <tr>
                        <td><strong>Scientific</strong></td>
                        <td></td>
                        <td>，</td>
                        <td><span class="scheme-tag tag-academic">⭐⭐</span></td>
                    </tr>
                    <tr>
                        <td><strong>Dark</strong></td>
                        <td></td>
                        <td>，</td>
                        <td><span class="scheme-tag tag-special">⭐⭐</span></td>
                    </tr>
                    <tr>
                        <td><strong>Thermal</strong></td>
                        <td></td>
                        <td>-，</td>
                        <td><span class="scheme-tag tag-academic">⭐</span></td>
                    </tr>
                    <tr>
                        <td><strong>Pastel</strong></td>
                        <td></td>
                        <td>，</td>
                        <td><span class="scheme-tag tag-popular">⭐</span></td>
                    </tr>
                    <tr>
                        <td><strong>Contrasting</strong></td>
                        <td></td>
                        <td>，</td>
                        <td><span class="scheme-tag tag-special">⭐</span></td>
                    </tr>
                </tbody>
            </table>
            
            <h3 style="color: #667eea; margin-top: 30px; margin-bottom: 10px;"></h3>
            
            <div class="command-section">
                <strong>：</strong>
                <br><code>python scripts/colorize_interface_pdb.py --scheme publication --pdb complex.pdb --ab_chains A --ag_chain B --output result.pdb</code>
            </div>
            
            <div class="command-section">
                <strong>：</strong>
                <br><code>python scripts/color_scheme_manager.py list</code>
            </div>
            
            <div class="command-section">
                <strong>：</strong>
                <br><code>python scripts/color_scheme_manager.py template my_scheme.json</code>
            </div>
            
            <div class="command-section">
                <strong>：</strong>
                <br><code>python scripts/color_scheme_manager.py show publication</code>
            </div>
            
            <h3 style="color: #667eea; margin-top: 30px; margin-bottom: 10px;"></h3>
            
            <div class="legend">
                <div class="legend-item">
                    <div class="legend-box" style="background: #FF0000;"></div>
                    <div class="legend-text">
                        <div class="legend-title"></div>
                        <div class="legend-desc">CDR </div>
                    </div>
                </div>
                <div class="legend-item">
                    <div class="legend-box" style="background: #0000FF;"></div>
                    <div class="legend-text">
                        <div class="legend-title"></div>
                        <div class="legend-desc"></div>
                    </div>
                </div>
                <div class="legend-item">
                    <div class="legend-box" style="background: #00AA00;"></div>
                    <div class="legend-text">
                        <div class="legend-title"></div>
                        <div class="legend-desc"></div>
                    </div>
                </div>
                <div class="legend-item">
                    <div class="legend-box" style="background: #CCCCCC;"></div>
                    <div class="legend-text">
                        <div class="legend-title"></div>
                        <div class="legend-desc"></div>
                    </div>
                </div>
            </div>
        </div>
        
        <div class="footer">
            <p>Generated: """ + datetime.now().strftime("%Y-%m-%d %H:%M:%S") + """</p>
            <p>- v1.0</p>
        </div>
    </div>
</body>
</html>
"""
    
    with open(output_path, 'w', encoding='utf-8') as f:
        f.write(html)
    
    print(f"✅ HTML preview generated: {output_path}")
    print(f"   Open in browser: file:///{Path(output_path).absolute()}")


if __name__ == "__main__":
    import sys
    output = sys.argv[1] if len(sys.argv) > 1 else "color_schemes_preview.html"
    generate_html_preview(output)
