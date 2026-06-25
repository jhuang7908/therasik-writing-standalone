"""Fix immunogenicity nav link for pages with varying HTML formatting."""
import os, re

BASE = "D:/InSynBio-AI-Research/Antibody_Engineer_Suite/insynbio-web-source"

PAGES = [
    "case_bispecific_vhh_expression_optimization.html",
    "case_vgrw_sr_r2_affinity_maturation.html",
    "case_mumab4d5_vhh_en.html",
    "case_mumab4d5_cmc.html",
    "case_malaria_carm_design.html",
]

IMMUNO_BLOCK_MULTI = """
          <a href="immunogenicity_study.html">
            <span class="menu-title">Immunogenicity</span>
            <span class="menu-desc">ADA Prediction &amp; Reference DB</span>
          </a>"""

IMMUNO_BLOCK_SINGLE = '<a href="immunogenicity_study.html"><span class="menu-title">Immunogenicity</span><span class="menu-desc">ADA Prediction &amp; Reference DB</span></a>'

for page in PAGES:
    path = os.path.join(BASE, page)
    if not os.path.exists(path):
        print(f"NOT FOUND: {page}")
        continue
    with open(path, encoding="utf-8") as f:
        content = f.read()

    if "immunogenicity_study.html" in content:
        print(f"ALREADY FIXED: {page}")
        continue

    # Pattern 1: multi-line format (InSynBio_Bispecific_Antibody_Design_Page.html on its own line)
    # Matches the Bispecific link block followed by closing </div>
    pattern_multi = re.compile(
        r'(<a href="InSynBio_Bispecific_Antibody_Design_Page\.html">\s*'
        r'<span class="menu-title">Bispecific</span>\s*'
        r'<span class="menu-desc">Multispecific Engineering</span>\s*'
        r'</a>)(\s*</div>)',
        re.DOTALL
    )

    match = pattern_multi.search(content)
    if match:
        # Determine indentation from the closing </div>
        closing = match.group(2)
        indent = re.match(r'(\s*)', closing).group(1).replace('\n', '')
        immuno = f"""
{indent}  <a href="immunogenicity_study.html">
{indent}    <span class="menu-title">Immunogenicity</span>
{indent}    <span class="menu-desc">ADA Prediction &amp; Reference DB</span>
{indent}  </a>"""
        new_content = content[:match.start(2)] + immuno + closing + content[match.end():]
        with open(path, "w", encoding="utf-8") as f:
            f.write(new_content)
        print(f"FIXED (multi-line): {page}")
    else:
        print(f"PATTERN NOT MATCHED: {page}")
