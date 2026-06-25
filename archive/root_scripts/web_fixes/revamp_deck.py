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

    # --- 1. Fix dark text in Slide 2 ---
    # `color:#111827;` inside Slide 2 makes it invisible on dark mode. Change to `#fff`.
    # Our white theme css takes over anyway on bright mode.
    html = html.replace('strong style="color:#111827;"', 'strong style="color:#fff;"')

    # --- 2. Remove Education from Cover Slide ---
    # The schools div is structured as '<div class="school-row"'
    html = re.sub(r'<div class="school-row"[^>]*>.*?</div>\s*', '', html, flags=re.DOTALL)

    # --- 3. Update Education strings in Slide 2 & English Cover Typography ---
    if lang == "zh":
        html = html.replace("• · (Albert Einstein College of Medicine)", "•  (Chinese Academy of Sciences)")
    else:
        # English: drop Einstein, keep Columbia & Rockefeller
        html = html.replace("<strong style=\"color:#fff;\">• Albert Einstein College of Medicine</strong>", "")
        # Tweak Cover slide typography to balance lines
        html = html.replace("Clinical Data-Guided<br><em>AI Biotherapeutic Decision System</em>", 
                            "Clinical Data-Guided AI<br><em>Biotherapeutic Strategy System</em>")
        html = html.replace("margin:0 auto 28px;text-align:center;max-width:960px;", 
                            "margin:0 auto 28px;text-align:center;max-width:800px;")

    # --- 4. Section Splitting & Reordering ---
    # We will split the HTML by `<section class="slide` and extract all 15 slides.
    # The head goes from start to the first <section
    parts = re.split(r'(?=<section class="slide)', html)
    header = parts[0]
    slides = parts[1:16] # there are exactly 15 slides
    footer = parts[16:] if len(parts) > 16 else []

    # Slide 3 (idx 2) is Pain Points
    # Slide 5 (idx 4) is Data Moat
    # Slide 13 (idx 12) is Tech Arsenal
    # We want Tech Arsenal to move to idx 5 (right after Data Moat).
    tech_arsenal_slide = slides.pop(12) 
    slides.insert(5, tech_arsenal_slide)

    # Re-assign IDs and Slide Numbers sequentially
    for i in range(len(slides)):
        # replace id="sX" with id="s(i+1)"
        slides[i] = re.sub(r'id="s\d+"', f'id="s{i+1}"', slides[i])
        # replace slide-num e.g. 03 / 15 -> 0(i+1) / 15
        slides[i] = re.sub(r'<div class="slide-num">\d+\s*/\s*15</div>', f'<div class="slide-num">{i+1:02d} / 15</div>', slides[i])

    # --- 5. Rewrite Pain Points (now slides[2]) ---
    if lang == "zh":
        pain_points_zh = """<section class="slide bg-white" id="s3">
  <div class="slide-inner">
    <span class="label label-teal">Industry Challenge</span>
    <h2 class="slide-title" style="font-size:54px;"><span></span></h2>
    <p class="slide-subtitle" style="font-size:22px; max-width:960px;"></p>
    <div class="card-grid g3">
      <div class="card card-accent card-red">
        <div class="pain-icon pain-red">🧬</div>
        <h3 style="font-size:20px;"></h3>
        <p style="font-size:16px;">。<br><br><strong style="color:#fff">：</strong><br>（、CDR、V），100% 。</p>
      </div>
      <div class="card card-accent card-amber">
        <div class="pain-icon pain-amber">⚠️</div>
        <h3 style="font-size:20px;">""</h3>
        <p style="font-size:16px;">， IND 。<br><br><strong style="color:#fff">：</strong><br> 15 “”，。</p>
      </div>
      <div class="card card-accent card-violet">
        <div class="pain-icon pain-violet">⏳</div>
        <h3 style="font-size:20px;"></h3>
        <p style="font-size:16px;">/ADC/CAR/，。<br><br><strong style="color:#fff">：</strong><br>。， AI 。</p>
      </div>
    </div>
  </div>
  <div class="slide-num">03 / 15</div>
</section>"""
        slides[2] = pain_points_zh
    else:
        pain_points_en = """<section class="slide bg-white" id="s3">
  <div class="slide-inner">
    <span class="label label-teal">Industry Challenge</span>
    <h2 class="slide-title" style="font-size:54px;">Three Major <span>"Black Boxes"</span> in Biologics</h2>
    <p class="slide-subtitle" style="font-size:22px; max-width:960px;">Identifying critical failure points and delivering systematic AI-driven solutions.</p>
    <div class="card-grid g3">
      <div class="card card-accent card-red">
        <div class="pain-icon pain-red">🧬</div>
        <h3 style="font-size:20px;">Humanization Success vs Affinity</h3>
        <p style="font-size:16px;">Standard humanization attempts frequently result in a catastrophic drop in affinity.<br><br><strong style="color:#fff">Our Solution:</strong><br>Multi-metric indexing (structural deviation loops, polymorphism conservation, and golden VH-VL pairing) ensuring 100% CDR retention.</p>
      </div>
      <div class="card card-accent card-amber">
        <div class="pain-icon pain-amber">⚠️</div>
        <h3 style="font-size:20px;">No Clinical Baselines for Dev</h3>
        <p style="font-size:16px;">Isolated algorithms provide scores, but liabilities only erupt during late-stage IND IND testing.<br><br><strong style="color:#fff">Our Solution:</strong><br>An exclusive 15-parameter "Clinical Checkup", benchmarking your candidate against thousands of historically proven, marketed drugs.</p>
      </div>
      <div class="card card-accent card-violet">
        <div class="pain-icon pain-violet">⏳</div>
        <h3 style="font-size:20px;">Blind Trial-and-Error in Complex Modalities</h3>
        <p style="font-size:16px;">Long dev cycles for ADCs/CARs rely heavily on luck and massive empirical screening.<br><br><strong style="color:#fff">Our Solution:</strong><br>Intelligent Immune Drug Design Ecosystem. Melding deep learning frameworks with immune proprietary datasets for deterministic AI logic inference.</p>
      </div>
    </div>
  </div>
  <div class="slide-num">03 / 15</div>
</section>"""
        slides[2] = pain_points_en


    # --- 6. Update CMC Text on Slide 7 (Used to be 6, shifted by TechArsenal) ---
    # We just explicitly cite Antibody Guide for cmc parameters
    if lang == "zh":
        slides[6] = slides[6].replace("。", "。 <a href='Therasik_Antibody_Guide.html?tab=dev' target='_blank' style='color:#5eead4;'>(Antibody Guide)</a>")
    else:
        slides[6] = slides[6].replace("。", "Benchmarking rigorously against thousands of clinical assets. See our <a href='Therasik_Antibody_Guide.html?tab=dev' target='_blank' style='color:#5eead4;'>Antibody Dev Guide</a>")


    # --- 7. Mark Proprietary Tools in Tech Arsenal ---
    if lang == "zh":
        prop_str = """
      <div class="card" style="text-align:center;padding:16px; border:2px dashed #0d9488;">
        <div style="font-size:14px;color:#5eead4;font-weight:700;margin-bottom:6px;">Therasik </div>
        <div style="font-size:14px;font-weight:700;color:#fff;">ACTES (CAR-M)</div>
        <div style="font-size:14px;font-weight:700;color:#fff;"></div>
      </div>"""
    else:
        prop_str = """
      <div class="card" style="text-align:center;padding:16px; border:2px dashed #0d9488;">
        <div style="font-size:14px;color:#5eead4;font-weight:700;margin-bottom:6px;">Self-Developed Systems</div>
        <div style="font-size:14px;font-weight:700;color:#fff;">ACTES (CAR-M)</div>
        <div style="font-size:14px;font-weight:700;color:#fff;">Immune Knowledge Graph</div>
      </div>"""
      
    # Replace one of the generic cards in the second row of tech arsenal (Slide 5 now)
    # the second row begins with <div class="card-grid g4">
    # we replace the IEDB API card (Immunogenicity) since it's just IEDB API, with this robust proprietary one.
    # actually, why not grid g5 and add it? Yes, changing g4 to g5 is cooler.
    slides[5] = slides[5].replace('<div class="card-grid g4">', '<div class="card-grid g5">')
    # insert proprietary card at the end of the second grid
    closing_div_idx = slides[5].rfind("</div>\n    </div>")
    if closing_div_idx != -1:
        slides[5] = slides[5][:closing_div_idx] + prop_str + "\n" + slides[5][closing_div_idx:]


    # Recombine HTML
    final_html = header + "".join(slides) + "".join(footer)
    with open(fpath, "w", encoding="utf-8") as f:
        f.write(final_html)

print("Deck restructuring successful!")
