import re

file_path = r"d:\InSynBio-AI-Research\Antibody_Engineer_Suite\insynbio-web-source\InSynBio_Pitch_Deck.html"

with open(file_path, "r", encoding="utf-8") as f:
    html = f.read()

# Regex to find the opening <section class="slide ... id="s1" ...> tag
pattern = r'(<section class="slide[^"]*" id="s1")[^>]*>'

# New rich background style identical to the case study hero but merged into one inline property
new_style = r'\1 style="background: radial-gradient(ellipse at 60% 40%, rgba(99,255,210,0.12) 0%, transparent 50%), url(\'images/hero-bg.svg\') center/cover no-repeat, linear-gradient(135deg, #042f2e 0%, #065f46 45%, #0d9488 100%); position: relative;">'

html = re.sub(pattern, new_style, html)

with open(file_path, "w", encoding="utf-8") as f:
    f.write(html)

print("Cover background correctly updated with hero-bg.svg!")
