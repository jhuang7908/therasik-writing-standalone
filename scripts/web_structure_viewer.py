#!/usr/bin/env python3
"""
web_structure_viewer.py

Generate interactive 3D structure viewer for antibody-antigen complexes.
Solves visualization issues:
  1. Chain color distinction (ECD vs VHH FR)
  2. Sidechain visibility control
  3. Interface highlighting
  4. Interactive rotation/zoom

Output: Self-contained HTML file using 3Dmol.js (free, no server needed)

USAGE:
    python web_structure_viewer.py \
        --pdb complex.pdb \
        --config viewer_config.json \
        --output viewer.html
"""

import argparse
import json
import logging
from pathlib import Path
from typing import Dict, List, Optional

logging.basicConfig(level=logging.INFO, format="[%(levelname)s] %(message)s")
logger = logging.getLogger(__name__)


class WebStructureViewer:
    """Generate interactive 3Dmol.js HTML viewer."""
    
    def __init__(self, pdb_path: str):
        self.pdb_path = Path(pdb_path)
        if not self.pdb_path.exists():
            raise FileNotFoundError(f"PDB file not found: {pdb_path}")
        
        # Read PDB content
        with open(self.pdb_path, 'r') as f:
            self.pdb_content = f.read()
        
        # Default configuration
        self.config = {
            "title": self.pdb_path.stem,
            "height": 800,
            "width": 1200,
            "chains": {},
            "interfaces": [],
            "views": []
        }
    
    def add_chain_style(self, chain_id: str, color: str, 
                       representation: str = "cartoon",
                       name: str = "") -> None:
        """Add chain visualization style."""
        self.config["chains"][chain_id] = {
            "color": color,
            "representation": representation,
            "name": name or f"Chain {chain_id}"
        }
    
    def add_interface_highlight(self, chain1: str, chain2: str,
                                color: str = "yellow",
                                contact_distance: float = 4.5) -> None:
        """Add interface highlighting."""
        self.config["interfaces"].append({
            "chain1": chain1,
            "chain2": chain2,
            "color": color,
            "distance": contact_distance
        })
    
    def add_preset_config(self, preset: str) -> None:
        """Apply preset configuration."""
        presets = {
            "vhh_her2": {
                "title": "VHH-HER2 Complex",
                "chains": {
                    "A": {"color": "#FF00FF", "representation": "cartoon", "name": "VHH"},
                    "B": {"color": "#00CCFF", "representation": "cartoon", "name": "HER2 ECD"},
                },
                "interfaces": [
                    {
                        "chain1": "A",
                        "chain2": "B",
                        "color": "#FFFF00",
                        "distance": 4.5
                    }
                ],
                "views": [
                    {
                        "name": "Overall",
                        "style": "all",
                        "sidechain": False
                    },
                    {
                        "name": "VHH Only",
                        "style": "A",
                        "sidechain": True
                    },
                    {
                        "name": "HER2 Only",
                        "style": "B",
                        "sidechain": False
                    },
                    {
                        "name": "Interface",
                        "style": "interface",
                        "sidechain": True
                    }
                ]
            },
            "fab_antigen": {
                "title": "FAB-Antigen Complex",
                "chains": {
                    "A": {"color": "#FF0000", "representation": "cartoon", "name": "VH"},
                    "B": {"color": "#0000FF", "representation": "cartoon", "name": "VL"},
                    "C": {"color": "#00AA00", "representation": "cartoon", "name": "Antigen"},
                },
                "interfaces": [
                    {"chain1": "A", "chain2": "C", "color": "#FFFF00", "distance": 4.5},
                    {"chain1": "B", "chain2": "C", "color": "#FFFF00", "distance": 4.5}
                ],
                "views": [
                    {
                        "name": "Overall",
                        "style": "all",
                        "sidechain": False
                    },
                    {
                        "name": "CDR Sidechains",
                        "style": "all",
                        "sidechain": True
                    },
                    {
                        "name": "Interface",
                        "style": "interface",
                        "sidechain": True
                    }
                ]
            }
        }
        
        if preset in presets:
            self.config.update(presets[preset])
        else:
            logger.warning(f"Unknown preset: {preset}")
    
    def generate_html(self) -> str:
        """Generate HTML with 3Dmol.js viewer."""
        
        chains_config = self._generate_chains_config()
        views_config = self._generate_views_config()
        
        html = f"""<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>3D Structure Viewer - {self.config['title']}</title>
    <script src="https://3Dmol.org/build/3Dmol-min.js"></script>
    <style>
        * {{
            margin: 0;
            padding: 0;
            box-sizing: border-box;
        }}
        
        body {{
            font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, 'Helvetica Neue', Arial, sans-serif;
            background: linear-gradient(135deg, #f5f7fa 0%, #c3cfe2 100%);
            padding: 20px;
            min-height: 100vh;
        }}
        
        .container {{
            max-width: 1600px;
            margin: 0 auto;
            display: grid;
            grid-template-columns: 1fr 250px;
            gap: 20px;
        }}
        
        .viewer-section {{
            background: white;
            border-radius: 12px;
            box-shadow: 0 8px 16px rgba(0,0,0,0.1);
            overflow: hidden;
            display: flex;
            flex-direction: column;
        }}
        
        .title-bar {{
            padding: 15px 20px;
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            color: white;
            font-size: 1.3em;
            font-weight: bold;
        }}
        
        #viewer {{
            width: 100%;
            height: {self.config['height']}px;
            position: relative;
            flex: 1;
        }}
        
        .info-bar {{
            padding: 12px 20px;
            background: #f8f9fa;
            border-top: 1px solid #eee;
            font-size: 0.9em;
            color: #666;
        }}
        
        .control-panel {{
            background: white;
            border-radius: 12px;
            box-shadow: 0 8px 16px rgba(0,0,0,0.1);
            padding: 15px;
            display: flex;
            flex-direction: column;
            gap: 15px;
            height: fit-content;
            max-height: calc(100vh - 40px);
            overflow-y: auto;
        }}
        
        .panel-section {{
            border-bottom: 1px solid #eee;
            padding-bottom: 12px;
        }}
        
        .panel-section:last-child {{
            border-bottom: none;
            padding-bottom: 0;
        }}
        
        .section-title {{
            font-weight: 600;
            color: #333;
            margin-bottom: 10px;
            font-size: 0.95em;
        }}
        
        .btn-group {{
            display: flex;
            flex-direction: column;
            gap: 6px;
        }}
        
        button {{
            padding: 8px 12px;
            border: 1px solid #ddd;
            border-radius: 6px;
            background: white;
            cursor: pointer;
            font-size: 0.85em;
            transition: all 0.2s;
            text-align: left;
        }}
        
        button:hover {{
            background: #f0f0f0;
            border-color: #999;
        }}
        
        button.active {{
            background: #667eea;
            color: white;
            border-color: #667eea;
        }}
        
        .checkbox-group {{
            display: flex;
            flex-direction: column;
            gap: 6px;
        }}
        
        .checkbox-item {{
            display: flex;
            align-items: center;
            gap: 8px;
        }}
        
        .checkbox-item input {{
            cursor: pointer;
        }}
        
        .checkbox-item label {{
            cursor: pointer;
            font-size: 0.9em;
            user-select: none;
            flex: 1;
        }}
        
        .color-legend {{
            background: #f8f9fa;
            border-radius: 6px;
            padding: 10px;
            margin-top: 10px;
        }}
        
        .legend-item {{
            display: flex;
            align-items: center;
            gap: 8px;
            font-size: 0.85em;
            margin-bottom: 6px;
        }}
        
        .legend-item:last-child {{
            margin-bottom: 0;
        }}
        
        .color-box {{
            width: 20px;
            height: 20px;
            border-radius: 3px;
            border: 1px solid #ddd;
        }}
        
        .slider-group {{
            display: flex;
            flex-direction: column;
            gap: 6px;
        }}
        
        .slider-label {{
            font-size: 0.85em;
            color: #666;
        }}
        
        input[type="range"] {{
            width: 100%;
            cursor: pointer;
        }}
        
        .status {{
            padding: 10px;
            background: #e8f5e9;
            border-radius: 6px;
            border-left: 3px solid #4caf50;
            font-size: 0.85em;
            color: #2e7d32;
        }}
        
        .keyboard-shortcuts {{
            font-size: 0.75em;
            color: #999;
            margin-top: 15px;
            padding-top: 12px;
            border-top: 1px solid #eee;
        }}
        
        .shortcut {{
            margin-bottom: 4px;
        }}
        
        .key {{
            display: inline-block;
            background: #f0f0f0;
            border: 1px solid #ccc;
            border-radius: 3px;
            padding: 2px 6px;
            font-family: monospace;
            font-weight: bold;
            font-size: 0.8em;
            margin-right: 4px;
        }}
    </style>
</head>
<body>
    <div class="container">
        <div class="viewer-section">
            <div class="title-bar">🧬 {self.config['title']}</div>
            <div id="viewer"></div>
            <div class="info-bar">
                💡 Use mouse to rotate, scroll to zoom, right-click to pan
            </div>
        </div>
        
        <div class="control-panel">
            {chains_config}
            {views_config}
            
            <div class="panel-section">
                <div class="section-title">Display Options</div>
                <div class="checkbox-group">
                    <div class="checkbox-item">
                        <input type="checkbox" id="showSidechain" onchange="toggleSidechain()">
                        <label for="showSidechain">Show Sidechains</label>
                    </div>
                    <div class="checkbox-item">
                        <input type="checkbox" id="showHydrogen" onchange="toggleHydrogen()">
                        <label for="showHydrogen">Show Hydrogens</label>
                    </div>
                </div>
            </div>
            
            <div class="panel-section">
                <div class="section-title">Opacity</div>
                <div class="slider-group">
                    <input type="range" id="opacitySlider" min="0" max="1" step="0.1" 
                           value="1" onchange="setOpacity(this.value)">
                    <div class="slider-label" id="opacityValue">100%</div>
                </div>
            </div>
            
            <div class="panel-section">
                <div class="section-title">Reset View</div>
                <button onclick="resetView()">Reset to Default</button>
            </div>
            
            <div class="keyboard-shortcuts">
                <strong>⌨️ Keyboard:</strong>
                <div class="shortcut"><span class="key">Scroll</span> Zoom</div>
                <div class="shortcut"><span class="key">Drag</span> Rotate</div>
                <div class="shortcut"><span class="key">Shift+Drag</span> Pan</div>
            </div>
        </div>
    </div>
    
    <script>
        let viewer;
        let currentStyle = 'all';
        
        function initViewer() {{
            let element = document.getElementById('viewer');
            let config = {{ backgroundColor: 'white' }};
            viewer = $3Dmol.createViewer(element, config);
            
            // Load PDB data
            let pdbData = `{self.pdb_content}`;
            viewer.addModel(pdbData, "pdb");
            
            // Apply default styles
            applyStyle('all');
            viewer.zoomTo();
        }}
        
        function applyStyle(style) {{
            currentStyle = style;
            let data = viewer.getModel().atomsForVisualization({{}});
            viewer.setStyle({{}}, {{cartoon: {{}}}});
            
            let chainStyles = {json.dumps({k: v for k, v in self.config['chains'].items()})};
            
            for (let chain in chainStyles) {{
                let style = chainStyles[chain];
                viewer.setStyle({{chain: chain}}, {{
                    cartoon: {{color: style.color, style: 'trace'}}
                }});
            }}
            
            // Show sidechains if needed
            if (document.getElementById('showSidechain').checked) {{
                viewer.setStyle({{}}, {{stick: {{}}}});
            }}
            
            viewer.render();
        }}
        
        function toggleSidechain() {{
            let checked = document.getElementById('showSidechain').checked;
            if (checked) {{
                viewer.setStyle({{}}, {{stick: {{}}}});
            }} else {{
                viewer.setStyle({{}}, {{stick: {{hidden: true}}}});
            }}
            viewer.render();
        }}
        
        function toggleHydrogen() {{
            let checked = document.getElementById('showHydrogen').checked;
            if (checked) {{
                viewer.setStyle({{}}, {{cartoonStroke: {{}}}});
            }}
            viewer.render();
        }}
        
        function setOpacity(value) {{
            document.getElementById('opacityValue').textContent = Math.round(value * 100) + '%';
            viewer.setStyle({{}}, {{opacity: parseFloat(value)}});
            viewer.render();
        }}
        
        function resetView() {{
            viewer.zoomTo();
            viewer.render();
        }}
        
        function selectView(viewName) {{
            // Reset all buttons
            document.querySelectorAll('.view-btn').forEach(btn => {{
                btn.classList.remove('active');
            }});
            
            // Activate clicked button
            event.target.classList.add('active');
            
            // Apply view
            applyStyle('all');
        }}
        
        // Initialize viewer on load
        window.addEventListener('load', initViewer);
    </script>
</body>
</html>
"""
        return html
    
    def _generate_chains_config(self) -> str:
        """Generate HTML for chain controls."""
        html = '<div class="panel-section">\n'
        html += '    <div class="section-title">Chains</div>\n'
        html += '    <div class="color-legend">\n'
        
        for chain_id, style in self.config["chains"].items():
            color = style.get("color", "#FFFFFF")
            name = style.get("name", f"Chain {chain_id}")
            html += f'        <div class="legend-item">\n'
            html += f'            <div class="color-box" style="background: {color};"></div>\n'
            html += f'            <span>{name}</span>\n'
            html += f'        </div>\n'
        
        html += '    </div>\n'
        html += '</div>\n'
        
        return html
    
    def _generate_views_config(self) -> str:
        """Generate HTML for view controls."""
        if not self.config.get("views"):
            return ""
        
        html = '<div class="panel-section">\n'
        html += '    <div class="section-title">Quick Views</div>\n'
        html += '    <div class="btn-group">\n'
        
        for i, view in enumerate(self.config["views"]):
            active = 'active' if i == 0 else ''
            html += f'        <button class="view-btn {active}" onclick="selectView(\'{view["name"]}\')">\n'
            html += f'            {view["name"]}\n'
            html += f'        </button>\n'
        
        html += '    </div>\n'
        html += '</div>\n'
        
        return html
    
    def save_html(self, output_path: str) -> None:
        """Save HTML to file."""
        html = self.generate_html()
        
        with open(output_path, 'w', encoding='utf-8') as f:
            f.write(html)
        
        logger.info(f"✅ HTML viewer saved: {output_path}")
        logger.info(f"   Open in browser: file:///{Path(output_path).absolute()}")


def main():
    parser = argparse.ArgumentParser(
        description="Generate interactive 3D structure viewer using 3Dmol.js"
    )
    parser.add_argument("--pdb", required=True, help="Input PDB file")
    parser.add_argument("--preset", choices=["vhh_her2", "fab_antigen"],
                        help="Use preset configuration")
    parser.add_argument("--output", default="structure_viewer.html",
                        help="Output HTML file")
    parser.add_argument("--title", help="Viewer title")
    
    args = parser.parse_args()
    
    viewer = WebStructureViewer(args.pdb)
    
    if args.preset:
        viewer.add_preset_config(args.preset)
    
    if args.title:
        viewer.config["title"] = args.title
    
    viewer.save_html(args.output)


if __name__ == "__main__":
    main()
