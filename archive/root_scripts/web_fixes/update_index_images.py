import os

file_path = r'D:\InSynBio-AI-Research\Antibody_Engineer_Suite\docs\therasik_index.html'

with open(file_path, 'r', encoding='utf-8') as f:
    content = f.read

#  CDR Redesign
old_cdr = """<picture>
              <source srcset="images/case-cdr-redesign.webp" type="image/webp">
              <source srcset="images/case-cdr-redesign.jpg" type="image/jpeg">
              <img src="images/case-cdr-redesign.svg" alt="CDR " loading="lazy">
            </picture>"""
new_cdr = '<img src="images/case-cdr-redesign.png" alt="CDR " loading="lazy">'

#  Fentanyl VAM
old_fentanyl = """<picture>
              <source srcset="images/case-fentanyl-vam.webp" type="image/webp">
              <source srcset="images/case-fentanyl-vam.jpg" type="image/jpeg">
              <img src="images/case-fentanyl-vam.svg" alt="" loading="lazy">
            </picture>"""
new_fentanyl = '<img src="images/case-fentanyl-vam.png" alt="" loading="lazy">'

# 
import re

def fuzzy_replace(text, old_block, new_block):
    #  old_block 
    pattern = re.escape(old_block).replace(r'\ ', r'\s+')
    return re.sub(pattern, new_block, text, flags=re.DOTALL)

content = fuzzy_replace(content, old_cdr, new_cdr)
content = fuzzy_replace(content, old_fentanyl, new_fentanyl)

with open(file_path, 'w', encoding='utf-8') as f:
    f.write(content)

print("Updated therasik_index.html successfully.")
