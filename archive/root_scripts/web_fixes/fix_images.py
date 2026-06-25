import re

path = r"D:\InSynBio-AI-Research\Antibody_Engineer_Suite\docs\therasik_index.html"
with open(path, 'r', encoding='utf-8') as f:
    text = f.read

#  CDR
text = re.sub(r'<picture>\s*<source[^>]*case-cdr-redesign\.webp[^>]*>\s*<source[^>]*case-cdr-redesign\.jpg[^>]*>\s*<img[^>]*case-cdr-redesign\.svg[^>]*>\s*</picture>', 
              '<img src="images/case-cdr-redesign.png" alt="CDR " loading="lazy">', text, flags=re.S)

#  Fentanyl
text = re.sub(r'<picture>\s*<source[^>]*case-fentanyl-vam\.webp[^>]*>\s*<source[^>]*case-fentanyl-vam\.jpg[^>]*>\s*<img[^>]*case-fentanyl-vam\.svg[^>]*>\s*</picture>', 
              '<img src="images/case-fentanyl-vam.png" alt="" loading="lazy">', text, flags=re.S)

with open(path, 'w', encoding='utf-8') as f:
    f.write(text)
print("Updated therasik_index.html")
