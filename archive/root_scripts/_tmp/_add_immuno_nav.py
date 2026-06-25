"""
Add Immunogenicity Research link to the Clinical Reference Library dropdown
in all InSynBio HTML pages. Handles multiple nav patterns.
"""
from pathlib import Path
import re

SRC = Path("D:/InSynBio-AI-Research/Antibody_Engineer_Suite/insynbio-web-source")

# Pattern A: multi-line with 10-space indent + closing </div>
OLD_A = '          <a href="vaccine_kb_data.html">\n          <span class="menu-title">Vaccine Knowledge Base</span>\n          <span class="menu-desc">Antigens &amp; Adjuvant Data</span>\n        </a>\n      </div>'
NEW_A = '          <a href="vaccine_kb_data.html">\n          <span class="menu-title">Vaccine Knowledge Base</span>\n          <span class="menu-desc">Antigens &amp; Adjuvant Data</span>\n        </a>\n          <a href="immunogenicity_study.html">\n          <span class="menu-title">Immunogenicity Research</span>\n          <span class="menu-desc">138-Antibody ADA Study &amp; Prediction</span>\n        </a>\n      </div>'

# Pattern B: inline with </a>\n      < (next dropdown or end)
OLD_B = '<a href="vaccine_kb_data.html"><span class="menu-title">Vaccine Knowledge Base</span><span class="menu-desc">Antigens &amp; Adjuvant Data</span></a>\n      <'
NEW_B = '<a href="vaccine_kb_data.html"><span class="menu-title">Vaccine Knowledge Base</span><span class="menu-desc">Antigens &amp; Adjuvant Data</span></a>\n        <a href="immunogenicity_study.html"><span class="menu-title">Immunogenicity Research</span><span class="std-md">138-Antibody ADA Study &amp; Prediction</span></a>\n      <'

fixed = 0
for f in sorted(SRC.glob("*.html")):
    content = f.read_text(encoding="utf-8")
    if "immunogenicity_study.html" in content and "Immunogenicity Research" in content:
        continue
    original = content
    content = content.replace(OLD_A, NEW_A)
    content = content.replace(OLD_B, NEW_B)
    if content != original:
        f.write_text(content, encoding="utf-8")
        fixed += 1
        print(f"  Added: {f.name}")
    elif "Vaccine Knowledge Base" in content:
        # Fallback: regex approach for any remaining variant
        # Find the vaccine_kb_data.html anchor and insert after it
        new_content, n = re.subn(
            r'(<a href="vaccine_kb_data\.html"[^>]*>.*?</a>)',
            r'\1\n          <a href="immunogenicity_study.html"><span class="menu-title">Immunogenicity Research</span><span class="menu-desc">138-Antibody ADA Study &amp; Prediction</span></a>',
            content,
            count=1,
            flags=re.DOTALL
        )
        if n > 0 and new_content != content:
            f.write_text(new_content, encoding="utf-8")
            fixed += 1
            print(f"  Added (regex): {f.name}")
        else:
            print(f"  SKIP (no pattern match): {f.name}")

print(f"\nDone. {fixed} files updated.")
