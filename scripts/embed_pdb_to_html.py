#!/usr/bin/env python3
"""
embed_pdb_to_html.py

 PDB  HTML ，
"""

import sys
from pathlib import Path

def embed_pdb_in_html(html_path, pdb_path, output_path=None):
    """ PDB  HTML 。"""
    
    if not Path(pdb_path).exists():
        print(f"❌ PDB : {pdb_path}")
        return False
    
    if not Path(html_path).exists():
        print(f"❌ HTML : {html_path}")
        return False
    
    #  PDB 
    with open(pdb_path, 'r') as f:
        pdb_data = f.read()
    
    #  HTML
    with open(html_path, 'r', encoding='utf-8') as f:
        html_content = f.read()
    
    # 
    embed_script = f"""
        <script>
        // PDB （）
        const embeddedPdbData = `{pdb_data}`;
        
        // 
        (function() {{
            const originalFetch = window.fetch;
            window.fetch = function(url) {{
                if (url.includes('vhh_her2_view.pdb')) {{
                    //  PDB 
                    return Promise.resolve(new Response(embeddedPdbData));
                }}
                return originalFetch.apply(this, arguments);
            }};
        }})();
        </script>
    """
    
    #  </head> 
    if '</head>' in html_content:
        html_content = html_content.replace(
            '</head>',
            embed_script + '\n</head>'
        )
    else:
        html_content = embed_script + html_content
    
    #  HTML
    output = output_path or html_path
    with open(output, 'w', encoding='utf-8') as f:
        f.write(html_content)
    
    print(f"✅ PDB : {output}")
    print(f"   : {len(html_content) / 1024 / 1024:.1f} MB")
    return True

if __name__ == "__main__":
    html_file = r"d:\InSynBio-AI-Research\Antibody_Engineer_Suite\docs\case_mumab4d5_vhh_en.html"
    pdb_file = r"d:\InSynBio-AI-Research\Antibody_Engineer_Suite\docs\vhh_her2_view.pdb"
    
    embed_pdb_in_html(html_file, pdb_file)
