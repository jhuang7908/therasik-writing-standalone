import os
import glob
import re

files = glob.glob("docs/Therasik_*.html") + ["docs/therasik_index.html"]

for f in files:
    with open(f, "r", encoding="utf-8") as file:
        content = file.read
    
    # We want to replace the content of the knowledge base dropdown.
    # Find the block starting with <a href=".*#knowledge-base"></a>
    # and ending with the closing </div> of the dropdown-menu.
    
    pattern = re.compile(r'(<div class="nav-dropdown"[^>]*>\s*<a href="[^"]*#knowledge-base"></a>\s*<div class="dropdown-menu">)(.*?)(</div>\s*</div>)', re.DOTALL)
    
    new_inner = """
          <a href="Therasik_Antibody_Guide.html">
            <span class="menu-title"></span>
            <span class="menu-desc"></span>
          </a>
          <a href="Therasik_ADA_Database.html">
            <span class="menu-title">ADA </span>
            <span class="menu-desc">138 </span>
          </a>
          <a href="Therasik_ADC_Database.html">
            <span class="menu-title">ADC </span>
            <span class="menu-desc">100+  ADC </span>
          </a>
          <a href="Therasik_Component_Browser.html">
            <span class="menu-title">CAR </span>
            <span class="menu-desc">237  CAR-T </span>
          </a>
          <a href="Therasik_Vaccine_KB.html">
            <span class="menu-title"></span>
            <span class="menu-desc"></span>
          </a>
        """
    
    new_content = pattern.sub(r'\1' + new_inner + r'\3', content)
    
    if new_content != content:
        with open(f, "w", encoding="utf-8") as file:
            file.write(new_content)
        print(f"Updated {f}")
    else:
        print(f"No match found in {f}")
