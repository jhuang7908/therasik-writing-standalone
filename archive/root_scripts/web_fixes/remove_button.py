import os

files = [
    r"d:\InSynBio-AI-Research\Antibody_Engineer_Suite\insynbio-web-source\InSynBio_Pitch_Deck.html",
    r"d:\InSynBio-AI-Research\Antibody_Engineer_Suite\therasik-web-source\Therasik_Pitch_Deck.html"
]

for fpath in files:
    if not os.path.exists(fpath):
        continue
    with open(fpath, "r", encoding="utf-8") as f:
        html = f.read

    # Remove English button
    html = html.replace('<a href="#s2" style="display:inline-block;padding:12px 30px;background:#5eead4;color:#0d4a44;font-size:16px;font-weight:700;border-radius:30px;text-decoration:none;">Enter Overview →</a>', '')
    
    # Remove Chinese button
    html = html.replace('<a href="#s2" style="display:inline-block;padding:12px 30px;background:#5eead4;color:#0d4a44;font-size:16px;font-weight:700;border-radius:30px;text-decoration:none;"> →</a>', '')

    with open(fpath, "w", encoding="utf-8") as f:
        f.write(html)

print("Buttons removed successfully.")
