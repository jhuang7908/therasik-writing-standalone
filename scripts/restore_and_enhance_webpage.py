#!/usr/bin/env python3
"""
restore_and_enhance_webpage.py

 3D 
：
  1.  3Dmol.js 
  2.  PDB 
  3. 
  4. 

：
  python restore_and_enhance_webpage.py \
      --html d:/path/to/case_mumab4d5_vhh_en.html \
      --pdb d:/path/to/vhh_her2_view.pdb
"""

import argparse
from pathlib import Path
from typing import Optional


def restore_and_enhance_webpage(html_path: str, pdb_path: Optional[str] = None) -> str:
    """ 3D 。"""
    
    with open(html_path, 'r', encoding='utf-8') as f:
        html_content = f.read()
    
    #  3Dmol ，
    enhanced_script = """
    <script>
    //  3D 
    (function() {
        //  3Dmol 
        function init3DViewer() {
            if (typeof $3Dmol === 'undefined') {
                setTimeout(init3DViewer, 200);
                return;
            }
            
            const el = document.getElementById('viewer3d');
            if (!el) return;
            
            //  3D 
            const viewer = $3Dmol.createViewer(el, {
                backgroundColor: '#0f172a',
                antialias: true,
                defaultcolors: $3Dmol.elementColors.rasmol
            });
            
            //  PDB 
            const pdbPath = 'vhh_her2_view.pdb';
            
            fetch(pdbPath)
                .then(response => response.text())
                .then(data => {
                    viewer.addModel(data, 'pdb');
                    
                    // =====  =====
                    
                    // VHH  (A) - 
                    viewer.setStyle({chain: 'A'}, {
                        cartoon: {
                            color: '#9933FF',      // 
                            thickness: 0.8,
                            opacity: 0.85
                        }
                    });
                    
                    // CDR  - 
                    const cdr_colors = {
                        'CDR1': { residues: [24, 34], color: '#FF3333', rgb: 0xFF3333 },      // 
                        'CDR2': { residues: [50, 56], color: '#00DDFF', rgb: 0x00DDFF },      // 
                        'CDR3': { residues: [89, 97], color: '#FF00FF', rgb: 0xFF00FF }       // 
                    };
                    
                    Object.values(cdr_colors).forEach(cdr => {
                        const [start, end] = cdr.residues;
                        for (let r = start; r <= end; r++) {
                            viewer.setStyle({chain: 'A', resi: r}, {
                                cartoon: {
                                    color: cdr.color,
                                    thickness: 1.2,
                                    opacity: 0.95
                                },
                                stick: {
                                    colorscheme: 'cyanCarbon',
                                    radius: 0.25
                                }
                            });
                        }
                    });
                    
                    //  - 
                    const frContactResi = [45];  // FR contact positions
                    frContactResi.forEach(r => {
                        viewer.setStyle({chain: 'A', resi: r}, {
                            cartoon: {
                                color: '#00FF99',    // 
                                thickness: 1.0,
                                opacity: 0.95
                            },
                            stick: {
                                colorscheme: 'greenCarbon',
                                radius: 0.25
                            }
                        });
                    });
                    
                    // HER2 ECD  (B) - 
                    viewer.setStyle({chain: 'B'}, {
                        cartoon: {
                            color: '#FFAA00',      // 
                            thickness: 0.7,
                            opacity: 0.65
                        }
                    });
                    
                    // HER2  - 
                    const her2Contact = [77, 78, 79, 80];
                    her2Contact.forEach(r => {
                        viewer.setStyle({chain: 'B', resi: r}, {
                            cartoon: {
                                color: '#FFFF33',    // 
                                thickness: 0.9,
                                opacity: 0.95
                            },
                            stick: {
                                colorscheme: 'orangeCarbon',
                                radius: 0.25
                            }
                        });
                    });
                    
                    // 
                    viewer.zoomTo();
                    viewer.zoom(0.9);
                    viewer.render();
                    
                    // 
                    const loadingEl = document.getElementById('viewer3d-loading');
                    if (loadingEl) loadingEl.style.display = 'none';
                    
                    const labelsEl = document.getElementById('viewer3d-labels');
                    if (labelsEl) labelsEl.style.display = 'flex';
                    
                    //  viewer 
                    window._viewer3d = viewer;
                    
                })
                .catch(err => {
                    console.error('Failed to load PDB:', err);
                    
                    // 
                    $3Dmol.download('url:vhh_her2_view.pdb', viewer, {}, function() {
                        viewer.zoomTo();
                        viewer.zoom(0.9);
                        viewer.render();
                        
                        const loadingEl = document.getElementById('viewer3d-loading');
                        if (loadingEl) loadingEl.style.display = 'none';
                        
                        window._viewer3d = viewer;
                    });
                });
        }
        
        // 
        if (document.readyState === 'loading') {
            document.addEventListener('DOMContentLoaded', init3DViewer);
        } else {
            init3DViewer();
        }
    })();
    </script>
    """
    
    # 
    legend_css = """
    <style>
        /*  */
        #viewer3d-labels {
            background: rgba(15, 23, 42, 0.95) !important;
            backdrop-filter: blur(8px);
            border: 1px solid rgba(148, 163, 184, 0.3);
            border-radius: 10px;
            padding: 12px 14px !important;
        }
        
        .viewer-label {
            display: flex;
            align-items: center;
            gap: 8px;
            font-size: 12px !important;
        }
        
        .label-color {
            width: 16px;
            height: 16px;
            border-radius: 3px;
            flex-shrink: 0;
            border: 1px solid rgba(255, 255, 255, 0.2);
        }
        
        /* 3D  */
        #viewer3d {
            border: 1px solid rgba(13, 148, 136, 0.2);
            border-radius: 12px;
            overflow: hidden;
            background: linear-gradient(135deg, #0f172a 0%, #1a2d2d 100%);
            box-shadow: 0 8px 32px rgba(0, 0, 0, 0.3);
        }
        
        /*  */
        #viewer3d-loading {
            background: linear-gradient(135deg, #0f172a 0%, #1a2d2d 100%) !important;
        }
    </style>
    """
    
    # 1.  <head> 
    if '</head>' in html_content:
        html_content = html_content.replace(
            '</head>',
            legend_css + '\n</head>'
        )
    
    # 2.  </body>  3D 
    if '</body>' in html_content:
        html_content = html_content.replace(
            '</body>',
            enhanced_script + '\n</body>'
        )
    else:
        html_content += enhanced_script
    
    return html_content


def main():
    parser = argparse.ArgumentParser(
        description=" 3D "
    )
    parser.add_argument(
        "--html",
        required=True,
        help="HTML "
    )
    parser.add_argument(
        "--pdb",
        help="PDB （）"
    )
    parser.add_argument(
        "--output",
        help=" HTML （）"
    )
    
    args = parser.parse_args()
    
    html_path = args.html
    pdb_path = args.pdb
    output_path = args.output or html_path
    
    print(f"📖 : {html_path}")
    
    enhanced_html = restore_and_enhance_webpage(html_path, pdb_path)
    
    with open(output_path, 'w', encoding='utf-8') as f:
        f.write(enhanced_html)
    
    print(f"✅ : {output_path}")
    print(f"\n✨ ：")
    print(f"  •  3D ")
    print(f"  • （8 ）")
    print(f"  • VHH ： #9933FF")
    print(f"  • CDR1： #FF3333")
    print(f"  • CDR2： #00DDFF")
    print(f"  • CDR3： #FF00FF")
    print(f"  • FR ： #00FF99")
    print(f"  • HER2： #FFAA00")
    print(f"  • HER2 ： #FFFF33")
    print(f"\n🔗 。")


if __name__ == "__main__":
    main()
