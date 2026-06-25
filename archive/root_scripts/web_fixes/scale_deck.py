import os
import re

files = [
    r"d:\InSynBio-AI-Research\Antibody_Engineer_Suite\insynbio-web-source\InSynBio_Pitch_Deck.html",
    r"d:\InSynBio-AI-Research\Antibody_Engineer_Suite\therasik-web-source\Therasik_Pitch_Deck.html"
]

for fpath in files:
    if os.path.exists(fpath):
        with open(fpath, "r", encoding="utf-8") as f:
            content = f.read()

        # 1. Darken the green gradient to ensure white text pops much better (from #0d9488 base to #0f766e base)
        content = content.replace(
            "linear-gradient(135deg,#0d4a44 0%,#0d7a70 55%,#0d9488 100%)", 
            "linear-gradient(135deg,#0a3632 0%,#0c5e56 60%,#0f766e 100%)"
        )
        
        # 2. Increase opacities to ensure high readability
        content = content.replace("rgba(255,255,255,0.4)", "rgba(255,255,255,0.65)")
        content = content.replace("rgba(255,255,255,0.45)", "rgba(255,255,255,0.65)")
        content = content.replace("rgba(255,255,255,0.5)", "rgba(255,255,255,0.75)")
        content = content.replace("rgba(255,255,255,0.55)", "rgba(255,255,255,0.75)")
        content = content.replace("rgba(255,255,255,0.6)", "rgba(255,255,255,0.8)")
        content = content.replace("rgba(255,255,255,0.65)", "rgba(255,255,255,0.85)")
        content = content.replace("rgba(255,255,255,0.7)", "rgba(255,255,255,0.9)")
        content = content.replace("rgba(255,255,255,0.8)", "rgba(255,255,255,0.95)")
        
        # 3. Increase all font sizes by ~1.35x globally so text fills the 'white space' naturally
        def scale_font(m):
            num = float(m.group(1))
            new_num = round(num * 1.35)
            # Cap hero titles so they don't break lines awkwardly
            if new_num > 80: new_num = 80
            return f"font-size:{new_num}px"
            
        content = re.sub(r"font-size:([\d\.]+)px", scale_font, content)

        # 4. Give the layout more room horizontally
        content = content.replace("max-width:700px", "max-width:960px")
        content = content.replace("max-width:640px", "max-width:960px")
        content = content.replace("max-width:1100px", "max-width:1300px")
        
        with open(fpath, "w", encoding="utf-8") as f:
            f.write(content)

print("Scaling and Contrast Enhancement completed.")
