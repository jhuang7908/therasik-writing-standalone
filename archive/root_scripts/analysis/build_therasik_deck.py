import os

source_html = r"d:\InSynBio-AI-Research\Antibody_Engineer_Suite\insynbio-web-source\InSynBio_Pitch_Deck.html"
target_html = r"d:\InSynBio-AI-Research\Antibody_Engineer_Suite\therasik-web-source\Therasik_Pitch_Deck.html"
translation_script = r"d:\InSynBio-AI-Research\Antibody_Engineer_Suite\translate_pitch_deck.py"

# Read the translation script to get the dict
with open(translation_script, "r", encoding="utf-8") as f:
    exec_scope = {}
    exec(f.read(), exec_scope)
    translations = exec_scope.get("translations", {})

# Reverse the translations: English -> Chinese
reverse_translations = {v: k for k, v in translations.items()}

# Read the current English HTML
with open(source_html, "r", encoding="utf-8") as f:
    content = f.read()

# 1. Reverse translate to Chinese
for en, ch in reverse_translations.items():
    content = content.replace(en, ch)

# 2. Replaces InSynBio with Therasik
content = content.replace("InSynBio", "Therasik")
content = content.replace("insynbio", "therasik")
# Note: "InSynBio" has cases like In<span class="accent">Syn</span>Bio
content = content.replace("In<span class=\"accent\">Syn</span>Bio", "Thera<span class=\"accent\">sik</span>")

# Fix URLs and emails
content = content.replace("contact@therasik.com", "contact@therasik.com") # just to be sure
content = content.replace("www.therasik.com", "www.therasik.com")

with open(target_html, "w", encoding="utf-8") as f:
    f.write(content)

print("Created Therasik Pitch Deck with Chinese text.")
