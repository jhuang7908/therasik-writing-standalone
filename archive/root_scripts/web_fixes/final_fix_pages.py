import re
import os

def update_case_page(path, img_name):
    if not os.path.exists(path):
        print(f"File not found: {path}")
        return
        
    with open(path, 'r', encoding='utf-8') as f:
        text = f.read()
    
    # Check if image already exists
    if f'images/{img_name}' in text:
        print(f"Image already exists in {path}")
        return

    # Image container HTML
    img_tag = f'<div style="margin: 32px auto 40px; max-width: 800px; border-radius: 16px; overflow: hidden; box-shadow: 0 20px 50px rgba(0,0,0,0.3); border: 1px solid rgba(255,255,255,0.1);"><img src="images/{img_name}" alt="Structure" style="width: 100%; display: block;"></div>'
    
    # Insert after the subtitle paragraph
    pattern = r'(<p class="subtitle">.*?</p>)'
    if re.search(pattern, text, re.S):
        text = re.sub(pattern, r'\1\n      ' + img_tag, text, count=1, flags=re.S)
        with open(path, 'w', encoding='utf-8') as f:
            f.write(text)
        print(f"Successfully updated {path}")
    else:
        print(f"Subtitle pattern not found in {path}")

# Paths
base_dir = r"D:\InSynBio-AI-Research\Antibody_Engineer_Suite\docs"
update_case_page(os.path.join(base_dir, "case_pdl1_epitope_analysis.html"), "case-pdl1-panel.png")
update_case_page(os.path.join(base_dir, "case_ab278_fentanyl_affinity_maturation.html"), "case-fentanyl-vam.png")
update_case_page(os.path.join(base_dir, "case_cdr_denovo_redesign.html"), "case-cdr-redesign.png")
