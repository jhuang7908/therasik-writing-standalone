import os
import re

files = {
    "zh": r"d:\InSynBio-AI-Research\Antibody_Engineer_Suite\therasik-web-source\Therasik_Pitch_Deck.html",
    "en": r"d:\InSynBio-AI-Research\Antibody_Engineer_Suite\insynbio-web-source\InSynBio_Pitch_Deck.html"
}

for lang, fpath in files.items:
    if not os.path.exists(fpath):
        continue
    with open(fpath, "r", encoding="utf-8") as f:
        html = f.read

    # --------------- 1. Deliverables Slide (s10) ----------------
    if lang == "zh":
        old_human_card = """<h3 style="font-size:24px;justify-content:center;">🔬 </h3>
        <p style="font-size:18px;"> ( Vernier +  + )</p>"""
        new_human_card = """<h3 style="font-size:24px;justify-content:center;">🔬 </h3>
        <p style="font-size:18px; line-height:1.6;"><strong style="color:var(--red);"></strong>，<br> <strong> +  (VAM)</strong>，。</p>"""
        html = html.replace(old_human_card, new_human_card)
    else:
        # Match English loosely in case translation varies
        match = re.search(r'<h3[^>]*>🔬[^<]*Humanization.*?</p>', html, re.DOTALL)
        if match:
            new_human_card_en = """<h3 style="font-size:24px;justify-content:center;">🔬 Genetic Humanization</h3>
        <p style="font-size:18px; line-height:1.6;">Addressing the inevitable <strong style="color:var(--red);">affinity drop</strong> hurdle. <br>Integrating <strong>Rational Humanization Design + Virtual Affinity Maturation (VAM)</strong> to fully rescue and enhance binding metrics.</p>"""
            html = html.replace(match.group(0), new_human_card_en)


    # --------------- 2. Bispecific Card (s9) Smart Linker Link ----------------
    if lang == "zh":
        # Find the bispecific h3
        bispec_h3 = r'<h3 style="font-size:24px;">↔️ </h3>'
        bispec_p = r'<p style="font-size:18px;">134\+  ·  \+ CMC  \+  · pI  · Linker </p>'
        
        # We replace the <p> content
        new_bispec_p = """<p style="font-size:18px; line-height:1.6;">。134+  · AI  · pI  Linker 。<br>
        <a href="case_bispecific_vhh_expression_optimization.html" target="_blank" style="color:var(--primary); font-weight:700;">[：scVHH Smart Linker  ↗]</a></p>"""
        
        # Safe replace
        html = re.sub(r'<p[^>]*>134\+ .*?Linker </p>', new_bispec_p, html)

    else:
         match_p = re.search(r'<p[^>]*>134\+ clinical bispecific formats.*?Linker optimization</p>', html, re.DOTALL)
         if match_p:
             new_bispec_p_en = """<p style="font-size:18px; line-height:1.6;">Solving chain mispairing and CMC crashes. AI pair predictions + 134+ clinical format benchmarking + Intelligent Linker & pI engineering.<br>
        <a href="case_bispecific_vhh_expression_optimization.html" target="_blank" style="color:var(--primary); font-weight:700;">[View Case Study: scVHH Smart Linker Optimization ↗]</a></p>"""
             html = html.replace(match_p.group(0), new_bispec_p_en)

    with open(fpath, "w", encoding="utf-8") as f:
        f.write(html)

print("Deliverables upgraded successfully!")
