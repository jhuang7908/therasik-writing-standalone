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

    # --------------- 1. Cover Detail (EN) ----------
    if lang == "en":
        old_cover_sub = "Integrating immunology expertise, clinical benchmarking libraries, and an expansive AI toolchain<br>to provide actionable decision support for biotherapeutic development—beyond isolated algorithm scoring."
        new_cover_sub = "Fusing immunology logic, clinical data benchmarking, and private AI inference<br>to deliver actionable drug design—not just isolated algorithm scores."
        html = html.replace(old_cover_sub, new_cover_sub)
        
        # Another variant it might be under if it was stripped
        html = html.replace(
            "Integrating immunology expertise, clinical benchmarking libraries, and an expansive AI toolchain，<br>——。", 
            new_cover_sub
        )

    # --------------- 2. Academic Pedigree (Slide 2) ----------
    if lang == "en":
        # Introduce Einstein back + clarify Postdoc
        old_pedigree_en = "Extensive research and training at the world's most elite biomedical institutions.<br><br>\n        <strong style=\"color:#111827;\">• Columbia University</strong><br>\n        <strong style=\"color:#111827;\">• Rockefeller University</strong><br>"
        # It's better to just regex replace the paragraph to be safe
        html = re.sub(
            r'Extensive research and training at the world\'s most elite biomedical institutions\.<br><br>.*?Rockefeller University</strong>(</p>|<br>)',
            r'Postdoctoral Research & Fellowships at elite US institutions.<br><br><strong style="color:#fff;">• Columbia University</strong><br><strong style="color:#fff;">• Rockefeller University</strong><br><strong style="color:#fff;">• Albert Einstein College of Medicine</strong>\1',
            html,
            flags=re.DOTALL
        )
        # Fix the color just in case
        html = html.replace('<strong style="color:#111827;">• Columbia', '<strong style="color:#fff;">• Columbia')

    # --------------- 3. Positioning "Not a tool vendor" (Slide 4) ----------
    if lang == "zh":
        old_quote_zh = '<p>"，；，； AI ，。"</p>'
        new_quote_zh = '<p><strong style="color:#fff">：</strong><br>1️⃣ <br>2️⃣ <br>3️⃣ ， AI ，。</p>'
        html = html.replace(old_quote_zh, new_quote_zh)
    else:
        old_quote_en = '<p>"，；，； AI ，。"</p>' # just in case this was not fully translated initially
        old_quote_en_true = '<p>"Clinically traceable, not relying on synthetic data; expert review, not black-box output; dozens of AI tools combined by scenario, not relying on a single model."</p>'
        new_quote_en = '<p><strong style="color:#fff">Our 3 Core Pillars:</strong><br>1️⃣ Deep empirical Immunology foundation.<br>2️⃣ Exclusive, high-quality clinical databases.<br>3️⃣ Private Machine Learning driving deterministic drug design, rigorously benchmarked against actual clinical data landscapes.</p>'
        
        if old_quote_en_true in html:
            html = html.replace(old_quote_en_true, new_quote_en)
        else:
            html = re.sub(r'<div class="quote-box">\s*<p>.*?</p>\s*</div>', f'<div class="quote-box">\n      {new_quote_en}\n    </div>', html, count=1, flags=re.DOTALL)


    # --------------- 4. Tech Arsenal Vaccine Tools (Slide 6) ----------
    vaccine_zh = '<div style="font-size:14px;font-weight:700;color:#fff;">Vaccine Design Suite</div>'
    vaccine_en = '<div style="font-size:14px;font-weight:700;color:#fff;">Vaccine Design Suite</div>'
    
    # Adding the vaccine toolkit into the proprietary block
    if "ACTES (CAR-M)" in html:
        html = html.replace("ACTES (CAR-M)</div>", f"ACTES (CAR-M)</div>\n        {vaccine_zh}")


    # --------------- 5. CMC Developability Benchmarking ~1000 (Slide 7) ----------
    if lang == "zh":
        old_cmc_zh = ""
        new_cmc_zh = "。 <strong style=\"color:#fff; font-size:1.1em;\">100015</strong>，『』"
        if "" in html:
            html = html.replace("", new_cmc_zh)
        else:
             html = re.sub(r'.*?', new_cmc_zh + '。', html)
    else:
        # replace the quote box content in CMC slide
        if "Benchmarking rigorously against thousands of clinical assets" in html:
            html = html.replace(
                "Benchmarking rigorously against thousands of clinical assets", 
                "We computed 15 parameters across nearly <strong style=\"color:#fff;\">1,000 marketed clinical antibodies</strong> to establish an exclusive Developability Index as the true north baseline"
            )


    # --------------- 6. ADA Database Links & 138 Highlight (Slide 8) ----------
    if lang == "zh":
        old_ada_zh = " 138  ADA  · / · MOA "
        new_ada_zh = " <strong style=\"color:#fff;\">138  ADA </strong>。<br>。<br><a href='https://insynbio.com/antibody-guide.html?tab=dev' target='_blank' style='color:#5eead4;'>[ ADA ]</a> · <a href='https://www.therasik.com/Therasik_Immunogenicity.html' target='_blank' style='color:#5eead4;'>[ ADA ]</a>"
        html = html.replace(old_ada_zh, new_ada_zh)
    else:
        old_ada_en = " 138  ADA  · / · MOA " # check translated status
        old_ada_en_2 = "Horizontal comparison with 138 rare ADA record libraries"
        new_ada_en = "Based on an exceptionally rare database of <strong style=\"color:#fff;\">138 actual antibody drugs with clinical ADA data</strong>. Multi-parameter comparison uncovers critical causatives.<br><a href='https://insynbio.com/antibody-guide.html?tab=dev' target='_blank' style='color:#5eead4;'>[Explore ADA Mechanisms Guide]</a> · <a href='https://insynbio.com/ada_database.html' target='_blank' style='color:#5eead4;'>[View ADA Database Report]</a>"
        
        # Regex to find the ADA list item containing 138
        html = re.sub(r'<p>.*?138\s*(rare|).*?</p>', f'<p>{new_ada_en}</p>', html, flags=re.DOTALL)
        # fallback if regex failed
        if new_ada_en not in html:
           idx = html.find("138 ")
           if idx != -1:
               start_p = html.rfind("<p>", 0, idx)
               end_p = html.find("</p>", idx)
               if start_p != -1 and end_p != -1:
                   html = html[:start_p] + "<p>" + new_ada_en + "</p>" + html[end_p+4:]


    with open(fpath, "w", encoding="utf-8") as f:
        f.write(html)

print("Deck content refinement successfully applied!")
