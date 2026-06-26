#!/usr/bin/env python3
"""
enhanced_web_structure_viewer.py

， 3Dmol.js 
：
  1. /
  2. （/）
  3. 
  4. 
  5. 

： HTML ，
"""

import json
from pathlib import Path
from typing import Dict, List, Optional


class EnhancedStructureViewer:
    """。"""
    
    def __init__(self, pdb_path: str):
        self.pdb_path = Path(pdb_path)
        with open(self.pdb_path, 'r') as f:
            self.pdb_content = f.read()
        
        # 
        self.regions = {
            "vhh_fr": {"name": "VHH FR", "color": "#9966FF", "type": "framework"},
            "cdr1": {"name": "CDR1", "color": "#FF3366", "type": "cdr"},
            "cdr2": {"name": "CDR2", "color": "#00CCFF", "type": "cdr"},
            "cdr3": {"name": "CDR3", "color": "#FF00FF", "type": "cdr"},
            "fr_contact": {"name": "FR Contact (R45)", "color": "#00FF99", "type": "contact"},
            "her2_ecd": {"name": "HER2 ECD", "color": "#FFAA00", "type": "antigen"},
            "shared": {"name": "Shared w/ trastuzumab", "color": "#CCCC00", "type": "shared"},
            "unique": {"name": "VHH-unique", "color": "#00FFFF", "type": "unique"},
        }
    
    def generate_html(self) -> str:
        """ HTML 。"""
        
        regions_json = json.dumps(self.regions, indent=2)
        pdb_escaped = self.pdb_content.replace('`', '\\`').replace('$', '\\$')
        
        html = f"""<!DOCTYPE html>
<html lang="zh-CN">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title> - VHH-HER2 </title>
    <script src="https://3Dmol.org/build/3Dmol-min.js"></script>
    <style>
        * {{
            margin: 0;
            padding: 0;
            box-sizing: border-box;
        }}
        
        body {{
            font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, Arial, sans-serif;
            background: #1a1a2e;
            color: #eee;
            padding: 10px;
            min-height: 100vh;
        }}
        
        .main-container {{
            display: grid;
            grid-template-columns: 1fr 280px;
            gap: 15px;
            max-width: 1800px;
            margin: 0 auto;
            height: calc(100vh - 20px);
        }}
        
        .viewer-container {{
            background: #0f3460;
            border-radius: 8px;
            overflow: hidden;
            display: flex;
            flex-direction: column;
            box-shadow: 0 8px 32px rgba(0,0,0,0.3);
        }}
        
        .title {{
            padding: 15px 20px;
            background: linear-gradient(135deg, #e94560 0%, #f39c12 100%);
            color: white;
            font-size: 1.2em;
            font-weight: bold;
        }}
        
        #viewer {{
            flex: 1;
            width: 100%;
            background: white;
        }}
        
        .info-bar {{
            padding: 10px 20px;
            background: #16213e;
            border-top: 1px solid #444;
            font-size: 0.9em;
            color: #aaa;
        }}
        
        .sidebar {{
            background: #0f3460;
            border-radius: 8px;
            padding: 15px;
            display: flex;
            flex-direction: column;
            gap: 15px;
            overflow-y: auto;
            box-shadow: 0 8px 32px rgba(0,0,0,0.3);
        }}
        
        .section-title {{
            font-weight: 600;
            color: #f39c12;
            font-size: 0.95em;
            margin-bottom: 8px;
            text-transform: uppercase;
            letter-spacing: 1px;
        }}
        
        .legend {{
            display: flex;
            flex-direction: column;
            gap: 8px;
        }}
        
        .legend-item {{
            display: flex;
            align-items: center;
            gap: 10px;
            padding: 8px;
            border-radius: 6px;
            cursor: pointer;
            transition: all 0.2s;
            background: rgba(255,255,255,0.05);
        }}
        
        .legend-item:hover {{
            background: rgba(255,255,255,0.1);
            transform: translateX(4px);
        }}
        
        .legend-item.active {{
            background: rgba(255,255,255,0.15);
            border-left: 3px solid #f39c12;
        }}
        
        .color-dot {{
            width: 18px;
            height: 18px;
            border-radius: 3px;
            flex-shrink: 0;
            border: 1px solid rgba(255,255,255,0.2);
        }}
        
        .legend-label {{
            font-size: 0.85em;
            flex: 1;
            user-select: none;
        }}
        
        .legend-toggle {{
            width: 18px;
            height: 18px;
            border-radius: 2px;
            border: 1px solid #666;
            display: flex;
            align-items: center;
            justify-content: center;
            font-size: 0.7em;
            background: rgba(255,255,255,0.1);
            flex-shrink: 0;
        }}
        
        .legend-item.active .legend-toggle {{
            background: #f39c12;
            border-color: #f39c12;
            color: #0f3460;
        }}
        
        .controls {{
            display: flex;
            flex-direction: column;
            gap: 8px;
        }}
        
        .control-btn {{
            padding: 8px 12px;
            border: 1px solid #f39c12;
            background: transparent;
            color: #f39c12;
            border-radius: 4px;
            cursor: pointer;
            font-size: 0.85em;
            transition: all 0.2s;
            text-align: left;
        }}
        
        .control-btn:hover {{
            background: rgba(243, 156, 18, 0.1);
        }}
        
        .control-btn.active {{
            background: #f39c12;
            color: #0f3460;
            font-weight: 600;
        }}
        
        .view-modes {{
            display: flex;
            flex-direction: column;
            gap: 6px;
        }}
        
        .view-btn {{
            padding: 6px 10px;
            background: rgba(243, 156, 18, 0.1);
            border: 1px solid #f39c12;
            color: #f39c12;
            border-radius: 4px;
            cursor: pointer;
            font-size: 0.8em;
            transition: all 0.2s;
        }}
        
        .view-btn:hover {{
            background: rgba(243, 156, 18, 0.2);
        }}
        
        .view-btn.active {{
            background: #f39c12;
            color: #0f3460;
        }}
        
        .divider {{
            height: 1px;
            background: rgba(255,255,255,0.1);
            margin: 10px 0;
        }}
        
        .opacity-control {{
            display: flex;
            flex-direction: column;
            gap: 6px;
        }}
        
        .opacity-label {{
            font-size: 0.85em;
            color: #aaa;
        }}
        
        input[type="range"] {{
            width: 100%;
            cursor: pointer;
        }}
        
        .help-text {{
            font-size: 0.75em;
            color: #888;
            margin-top: 10px;
            padding-top: 10px;
            border-top: 1px solid rgba(255,255,255,0.1);
        }}
        
        .help-item {{
            margin-bottom: 4px;
        }}
        
        .key {{
            background: rgba(255,255,255,0.1);
            padding: 1px 4px;
            border-radius: 2px;
            font-family: monospace;
            font-size: 0.75em;
        }}
        
        @media (max-width: 1024px) {{
            .main-container {{
                grid-template-columns: 1fr;
            }}
            
            .sidebar {{
                max-height: 300px;
            }}
        }}
    </style>
</head>
<body>
    <div class="main-container">
        <div class="viewer-container">
            <div class="title">🧬 VHH-HER2 </div>
            <div id="viewer"></div>
            <div class="info-bar">
                💡  •  • Shift+ • /
            </div>
        </div>
        
        <div class="sidebar">
            <div>
                <div class="section-title">📍 </div>
                <div class="legend" id="legendContainer"></div>
            </div>
            
            <div class="divider"></div>
            
            <div>
                <div class="section-title">🎨 </div>
                <div class="view-modes" id="viewModes"></div>
            </div>
            
            <div class="divider"></div>
            
            <div>
                <div class="section-title">⚙️ </div>
                <div class="controls">
                    <label style="display: flex; gap: 8px; align-items: center; cursor: pointer;">
                        <input type="checkbox" id="showSidechains" onchange="toggleSidechains()">
                        <span style="font-size: 0.9em;"></span>
                    </label>
                    <label style="display: flex; gap: 8px; align-items: center; cursor: pointer;">
                        <input type="checkbox" id="showCartoon" checked onchange="toggleCartoon()">
                        <span style="font-size: 0.9em;"></span>
                    </label>
                </div>
            </div>
            
            <div>
                <div class="section-title">🌫️ </div>
                <div class="opacity-control">
                    <input type="range" id="opacitySlider" min="0" max="1" step="0.1" value="1" onchange="setOpacity(this.value)">
                    <div class="opacity-label" id="opacityValue">100%</div>
                </div>
            </div>
            
            <div>
                <button class="control-btn" onclick="resetView()" style="width: 100%; margin-top: 10px;">
                    🔄 
                </button>
            </div>
            
            <div class="help-text">
                <strong>⌨️ :</strong>
                <div class="help-item">
                    <span class="key">L</span> - /
                </div>
                <div class="help-item">
                    <span class="key">S</span> - 
                </div>
                <div class="help-item">
                    <span class="key">R</span> - 
                </div>
            </div>
        </div>
    </div>
    
    <script>
        let viewer;
        let regions = {regions_json};
        let visibleRegions = {{}};
        let currentMode = 'full';
        
        // 
        Object.keys(regions).forEach(k => visibleRegions[k] = true);
        
        function initViewer() {{
            let element = document.getElementById('viewer');
            let config = {{ backgroundColor: 'white' }};
            viewer = $3Dmol.createViewer(element, config);
            
            let pdbData = `{pdb_escaped}`;
            viewer.addModel(pdbData, "pdb");
            viewer.getModel().setStyle({{}}, {{cartoon: {{colorscheme: 'ssCartoon'}}}});
            viewer.zoomTo();
            
            initLegend();
            initViewModes();
            applyStyle();
        }}
        
        function initLegend() {{
            let container = document.getElementById('legendContainer');
            container.innerHTML = '';
            
            Object.entries(regions).forEach(([key, region]) => {{
                let item = document.createElement('div');
                item.className = 'legend-item active';
                item.onclick = () => toggleRegion(key, item);
                
                item.innerHTML = `
                    <div class="color-dot" style="background-color: ${{region.color}};"></div>
                    <div class="legend-label">${{region.name}}</div>
                    <div class="legend-toggle">✓</div>
                `;
                
                container.appendChild(item);
            }});
        }}
        
        function initViewModes() {{
            let container = document.getElementById('viewModes');
            let modes = [
                {{ id: 'full', name: 'Full View' }},
                {{ id: 'cdr', name: 'CDR Only' }},
                {{ id: 'interface', name: 'Interface' }},
                {{ id: 'cartoon', name: 'Cartoon' }},
            ];
            
            modes.forEach(mode => {{
                let btn = document.createElement('button');
                btn.className = 'view-btn';
                if (mode.id === currentMode) btn.classList.add('active');
                btn.textContent = mode.name;
                btn.onclick = () => setViewMode(mode.id, btn);
                container.appendChild(btn);
            }});
        }}
        
        function toggleRegion(key, element) {{
            visibleRegions[key] = !visibleRegions[key];
            element.classList.toggle('active');
            applyStyle();
        }}
        
        function toggleSidechains() {{
            applyStyle();
        }}
        
        function toggleCartoon() {{
            applyStyle();
        }}
        
        function setOpacity(value) {{
            document.getElementById('opacityValue').textContent = Math.round(value * 100) + '%';
            viewer.setStyle({{}}, {{opacity: parseFloat(value)}});
            viewer.render();
        }}
        
        function setViewMode(mode, btn) {{
            currentMode = mode;
            document.querySelectorAll('.view-btn').forEach(b => b.classList.remove('active'));
            btn.classList.add('active');
            applyStyle();
        }}
        
        function applyStyle() {{
            let showSidechains = document.getElementById('showSidechains').checked;
            let showCartoon = document.getElementById('showCartoon').checked;
            
            // 
            viewer.setStyle({{}}, {{cartoon: {{hidden: !showCartoon}}}});
            
            // 
            if (showSidechains) {{
                viewer.setStyle({{}}, {{stick: {{}}}});
            }} else {{
                viewer.setStyle({{}}, {{stick: {{hidden: true}}}});
            }}
            
            // 
            switch(currentMode) {{
                case 'cdr':
                    //  CDR
                    ['cdr1', 'cdr2', 'cdr3'].forEach(key => {{
                        if (visibleRegions[key]) {{
                            viewer.setStyle({{ss: 'c'}}, {{cartoon: {{color: regions[key].color}}}});
                        }}
                    }});
                    break;
                    
                case 'interface':
                    // 
                    Object.entries(regions).forEach(([key, region]) => {{
                        if (visibleRegions[key] && region.type.includes('contact')) {{
                            viewer.setStyle({{}}, {{cartoon: {{color: region.color}}}});
                        }}
                    }});
                    break;
                    
                case 'cartoon':
                    // 
                    viewer.setStyle({{}}, {{cartoon: {{colorscheme: 'ssCartoon'}}}});
                    break;
                    
                case 'full':
                default:
                    // 
                    Object.entries(regions).forEach(([key, region]) => {{
                        if (visibleRegions[key]) {{
                            // /
                            // ：
                            viewer.setStyle({{}}, {{cartoon: {{color: region.color}}}});
                        }}
                    }});
            }}
            
            viewer.render();
        }}
        
        function resetView() {{
            viewer.zoomTo();
            viewer.render();
        }}
        
        // 
        document.addEventListener('keydown', (e) => {{
            switch(e.key.toLowerCase()) {{
                case 's':
                    document.getElementById('showSidechains').click();
                    break;
                case 'r':
                    resetView();
                    break;
            }}
        }});
        
        window.addEventListener('load', initViewer);
    </script>
</body>
</html>
"""
        return html
    
    def save(self, output_path: str) -> None:
        """ HTML 。"""
        html = self.generate_html()
        with open(output_path, 'w', encoding='utf-8') as f:
            f.write(html)
        print(f"✅ : {output_path}")
        print(f"   : file:///{Path(output_path).absolute()}")


if __name__ == "__main__":
    import argparse
    
    parser = argparse.ArgumentParser(description="")
    parser.add_argument("--pdb", required=True, help="PDB ")
    parser.add_argument("--output", default="enhanced_viewer.html", help=" HTML ")
    
    args = parser.parse_args()
    
    viewer = EnhancedStructureViewer(args.pdb)
    viewer.save(args.output)
