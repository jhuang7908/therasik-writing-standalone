#!/usr/bin/env python3
"""
web_color_enhancer.py

 3Dmol.js 

：
  1.  HTML 
  2.  3Dmol.js 
  3. 
  4. 

：
  python web_color_enhancer.py --input original.html --output enhanced.html
"""

import re
import argparse
from pathlib import Path
from typing import Dict, Optional


class WebColorEnhancer:
    """。"""
    
    # （）
    REGION_COLORS = {
        "VHH_FR": "#9933FF",        # 
        "CDR1": "#FF3333",          # 
        "CDR2": "#00DDFF",          # 
        "CDR3": "#FF00FF",          # 
        "FR_CONTACT": "#00FF99",    # 
        "HER2_ECD": "#FFAA00",      # 
        "SHARED": "#FFFF33",        # 
        "UNIQUE": "#33FFFF",        # 
    }
    
    # 3Dmol.js 
    ENHANCED_VIEWER_SCRIPT = """
    <script>
    //  3Dmol.js 
    (function() {{
        const regionColors = {{
            "VHH_FR": 0x9933FF,
            "CDR1": 0xFF3333,
            "CDR2": 0x00DDFF,
            "CDR3": 0xFF00FF,
            "FR_CONTACT": 0x00FF99,
            "HER2_ECD": 0xFFAA00,
            "SHARED": 0xFFFF33,
            "UNIQUE": 0x33FFFF,
        }};
        
        //  3Dmol viewer 
        if (window.$3Dmol && window.$3Dmol.viewers) {{
            Object.values(window.$3Dmol.viewers).forEach(viewer => {{
                if (viewer && viewer.getModel()) {{
                    // 
                    viewer.setStyle({{}}, {{
                        cartoon: {{
                            color: "spectrum",
                            thickness: 0.8,
                            arrows: true,
                            tubes: true,
                            helixScale: 1.3,
                            style: "trace"
                        }}
                    }});
                    
                    // 
                    const chains = ['A', 'B', 'C', 'D'];
                    const colors = [0x9933FF, 0x00DDFF, 0xFFAA00, 0xFF3333];
                    
                    chains.forEach((chain, idx) => {{
                        if (idx < colors.length) {{
                            viewer.setStyle({{chain: chain}}, {{
                                cartoon: {{
                                    color: colors[idx],
                                    style: 'trace',
                                    thickness: 1.0
                                }}
                            }});
                        }}
                    }});
                    
                    viewer.render();
                }}
            }});
        }}
    }})();
    </script>
    """
    
    #  HTML
    COLOR_CONTROL_PANEL = """
    <div style="position: fixed; right: 10px; top: 10px; background: rgba(0,0,0,0.8); 
                color: white; padding: 15px; border-radius: 8px; z-index: 9999; 
                font-family: Arial, sans-serif; font-size: 12px; max-width: 250px;">
        <div style="font-weight: bold; margin-bottom: 10px; font-size: 14px;">🎨 </div>
        <div style="display: grid; grid-template-columns: 20px 1fr; gap: 8px; align-items: center;">
            <div style="width: 20px; height: 20px; background: #9933FF; border-radius: 3px;"></div>
            <div>VHH  (VHH FR)</div>
            
            <div style="width: 20px; height: 20px; background: #FF3333; border-radius: 3px;"></div>
            <div>CDR1 </div>
            
            <div style="width: 20px; height: 20px; background: #00DDFF; border-radius: 3px;"></div>
            <div>CDR2 </div>
            
            <div style="width: 20px; height: 20px; background: #FF00FF; border-radius: 3px;"></div>
            <div>CDR3 </div>
            
            <div style="width: 20px; height: 20px; background: #00FF99; border-radius: 3px;"></div>
            <div></div>
            
            <div style="width: 20px; height: 20px; background: #FFAA00; border-radius: 3px;"></div>
            <div>HER2 ECD</div>
            
            <div style="width: 20px; height: 20px; background: #FFFF33; border-radius: 3px;"></div>
            <div></div>
            
            <div style="width: 20px; height: 20px; background: #33FFFF; border-radius: 3px;"></div>
            <div>VHH </div>
        </div>
        
        <div style="margin-top: 15px; padding-top: 10px; border-top: 1px solid #555;">
            <div style="margin-bottom: 8px;">
                <label style="display: flex; align-items: center; gap: 8px; cursor: pointer;">
                    <input type="checkbox" id="enhanceContrast" checked 
                           onchange="toggleContrastEnhance(this.checked)">
                    <span></span>
                </label>
            </div>
            <div style="margin-bottom: 8px;">
                <label style="display: flex; align-items: center; gap: 8px; cursor: pointer;">
                    <input type="checkbox" id="showSidechains" 
                           onchange="toggleSidechains(this.checked)">
                    <span></span>
                </label>
            </div>
            <div>
                <label style="display: flex; align-items: center; gap: 8px; cursor: pointer;">
                    <input type="checkbox" id="smoothCartoon" checked 
                           onchange="toggleSmoothCartoon(this.checked)">
                    <span></span>
                </label>
            </div>
        </div>
        
        <div style="margin-top: 10px; font-size: 11px; color: #aaa;">
            💡  |  | 
        </div>
    </div>
    
    <script>
        // 
        let dragElement = document.querySelector('div[style*="position: fixed"]');
        if (dragElement) {{
            let pos1 = 0, pos2 = 0, pos3 = 0, pos4 = 0;
            dragElement.onmousedown = dragMouseDown;
            
            function dragMouseDown(e) {{
                pos3 = e.clientX;
                pos4 = e.clientY;
                document.onmouseup = closeDragElement;
                document.onmousemove = elementDrag;
            }}
            
            function elementDrag(e) {{
                pos1 = pos3 - e.clientX;
                pos2 = pos4 - e.clientY;
                pos3 = e.clientX;
                pos4 = e.clientY;
                dragElement.style.top = (dragElement.offsetTop - pos2) + "px";
                dragElement.style.right = (dragElement.offsetRight + pos1) + "px";
            }}
            
            function closeDragElement() {{
                document.onmouseup = null;
                document.onmousemove = null;
            }}
        }}
        
        function toggleContrastEnhance(checked) {{
            if (window.$3Dmol && window.$3Dmol.viewers) {{
                Object.values(window.$3Dmol.viewers).forEach(viewer => {{
                    if (viewer && viewer.getModel()) {{
                        if (checked) {{
                            viewer.setStyle({{}}, {{cartoon: {{thickness: 1.2}}}});
                        }} else {{
                            viewer.setStyle({{}}, {{cartoon: {{thickness: 0.8}}}});
                        }}
                        viewer.render();
                    }}
                }});
            }}
        }}
        
        function toggleSidechains(checked) {{
            if (window.$3Dmol && window.$3Dmol.viewers) {{
                Object.values(window.$3Dmol.viewers).forEach(viewer => {{
                    if (viewer && viewer.getModel()) {{
                        if (checked) {{
                            viewer.setStyle({{}}, {{stick: {{}}}});
                        }} else {{
                            viewer.setStyle({{}}, {{stick: {{hidden: true}}}});
                        }}
                        viewer.render();
                    }}
                }});
            }}
        }}
        
        function toggleSmoothCartoon(checked) {{
            if (window.$3Dmol && window.$3Dmol.viewers) {{
                Object.values(window.$3Dmol.viewers).forEach(viewer => {{
                    if (viewer && viewer.getModel()) {{
                        viewer.setStyle({{}}, {{
                            cartoon: {{
                                style: checked ? 'trace' : 'cartoon',
                                color: 'spectrum'
                            }}
                        }});
                        viewer.render();
                    }}
                }});
            }}
        }}
    </script>
    """
    
    def __init__(self, html_path: str):
        self.html_path = Path(html_path)
        with open(self.html_path, 'r', encoding='utf-8') as f:
            self.html_content = f.read()
    
    def enhance(self) -> str:
        """ HTML 。"""
        
        # 1.  3Dmol 
        enhanced_html = self.html_content
        
        #  </body> 
        if '</body>' in enhanced_html:
            enhanced_html = enhanced_html.replace(
                '</body>',
                self.ENHANCED_VIEWER_SCRIPT + '\n</body>'
            )
        else:
            enhanced_html += self.ENHANCED_VIEWER_SCRIPT
        
        # 2.  </body> 
        if '</body>' in enhanced_html:
            enhanced_html = enhanced_html.replace(
                '</body>',
                self.COLOR_CONTROL_PANEL + '\n</body>'
            )
        
        # 3.  CSS 
        css_enhancement = """
        <style>
            /* 3Dmol  */
            [id*="viewer"], [class*="viewer"], [class*="GLViewer"] {
                filter: brightness(1.05) contrast(1.15) !important;
                background: white !important;
            }
            
            /*  */
            canvas {
                filter: drop-shadow(0 0 2px rgba(0,0,0,0.2));
            }
            
            /*  */
            [class*="legend"], [class*="Legend"] {
                background: rgba(255,255,255,0.95) !important;
                border: 2px solid #333 !important;
                border-radius: 8px !important;
                padding: 12px !important;
                box-shadow: 0 4px 12px rgba(0,0,0,0.15) !important;
            }
            
            /*  */
            .legend-color-vhh-fr { background: #9933FF !important; }
            .legend-color-cdr1 { background: #FF3333 !important; }
            .legend-color-cdr2 { background: #00DDFF !important; }
            .legend-color-cdr3 { background: #FF00FF !important; }
            .legend-color-fr-contact { background: #00FF99 !important; }
            .legend-color-her2 { background: #FFAA00 !important; }
            .legend-color-shared { background: #FFFF33 !important; }
            .legend-color-unique { background: #33FFFF !important; }
        </style>
        """
        
        if '<head>' in enhanced_html:
            enhanced_html = enhanced_html.replace(
                '</head>',
                css_enhancement + '\n</head>'
            )
        elif '<body>' in enhanced_html:
            enhanced_html = enhanced_html.replace(
                '<body>',
                '<head>' + css_enhancement + '</head>\n<body>'
            )
        else:
            enhanced_html = css_enhancement + '\n' + enhanced_html
        
        return enhanced_html
    
    def save(self, output_path: str) -> None:
        """ HTML。"""
        enhanced = self.enhance()
        
        with open(output_path, 'w', encoding='utf-8') as f:
            f.write(enhanced)
        
        print(f"✅ : {output_path}")
        print(f"   • ")
        print(f"   • ")
        print(f"   • ")
        print(f"\n。")


def main():
    parser = argparse.ArgumentParser(
        description=""
    )
    parser.add_argument(
        "--input", 
        required=True, 
        help=" HTML "
    )
    parser.add_argument(
        "--output",
        default="enhanced_structure.html",
        help=" HTML "
    )
    
    args = parser.parse_args()
    
    enhancer = WebColorEnhancer(args.input)
    enhancer.save(args.output)


if __name__ == "__main__":
    main()
