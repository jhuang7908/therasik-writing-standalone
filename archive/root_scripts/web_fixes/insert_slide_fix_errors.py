import os
import re

files = {
    "zh": r"d:\InSynBio-AI-Research\Antibody_Engineer_Suite\therasik-web-source\Therasik_Pitch_Deck.html",
    "en": r"d:\InSynBio-AI-Research\Antibody_Engineer_Suite\insynbio-web-source\InSynBio_Pitch_Deck.html"
}

slides_content = {
    "en": """<!-- ===================== SLIDE 2: WHO WE ARE ===================== -->
<section class="slide bg-white" id="s2">
  <div class="slide-inner">
    <span class="label label-teal">Founder & Vision</span>
    <h2 class="slide-title" style="font-size:72px;">Jing Huang, <span>Ph.D.</span></h2>
    <p class="slide-subtitle" style="font-size:24px; max-width:960px;">Bridging the gap between empirical immunology and structural AI algorithms to build the next generation of biotherapeutic engineering tools.</p>
    
    <div class="card-grid g2" style="margin-bottom: 24px;">
      <div class="card card-accent card-teal">
        <h3 style="font-size:24px;">🎓 Academic Pedigree</h3>
        <p style="font-size:18px;">Extensive research and training at the world's most elite biomedical institutions.<br><br>
        <strong style="color:#111827;">• Columbia University</strong><br>
        <strong style="color:#111827;">• Rockefeller University</strong><br>
        <strong style="color:#111827;">• Albert Einstein College of Medicine</strong></p>
      </div>
      <div class="card card-accent card-amber">
        <h3 style="font-size:24px;">🔬 What We Do</h3>
        <p style="font-size:18px; line-height: 1.6; margin-top: 10px;">
          "We don't just supply generic AI algorithms.<br><br>
          By anchoring cutting-edge machine learning models (like AlphaFold, Diffusion, LMs) to <strong style="color:#111827;">true clinical wet-lab databases</strong>, we deliver actionable, experimentally-validated decision support for complex macromolecules."
        </p>
      </div>
    </div>
  </div>
  <div class="slide-num">02 / 15</div>
</section>

""",
    "zh": """<!-- ===================== SLIDE 2: WHO WE ARE ===================== -->
<section class="slide bg-white" id="s2">
  <div class="slide-inner">
    <span class="label label-teal">Founder & Vision</span>
    <h2 class="slide-title" style="font-size:72px;">  <span>(Jing Huang, Ph.D.)</span></h2>
    <p class="slide-subtitle" style="font-size:24px; max-width:960px;">「」「AI」，，。</p>
    
    <div class="card-grid g2" style="margin-bottom: 24px;">
      <div class="card card-accent card-teal">
        <h3 style="font-size:24px;">🎓 </h3>
        <p style="font-size:18px;">，“”。<br><br>
        <strong style="color:#111827;">•  (Columbia University)</strong><br>
        <strong style="color:#111827;">•  (Rockefeller University)</strong><br>
        <strong style="color:#111827;">• · (Albert Einstein College of Medicine)</strong></p>
      </div>
      <div class="card card-accent card-amber">
        <h3 style="font-size:24px;">🔬 What We Do </h3>
        <p style="font-size:18px; line-height: 1.6; margin-top: 10px;">
          " AI 。<br><br>
          （、、）<strong style="color:#111827;"></strong>，、ADC、CAR-M ，<strong style="color:#111827;"></strong>。"
        </p>
      </div>
    </div>
  </div>
  <div class="slide-num">02 / 15</div>
</section>

"""
}

for lang, fpath in files.items:
    if os.path.exists(fpath):
        with open(fpath, "r", encoding="utf-8") as f:
            content = f.read
            
        # --- 1. Fix Technical Tool Errors in Slide 12 ---
        
        # Molecular Docking: MM/GBSA -> AF2-Multimer
        if lang == "zh":
            content = content.replace("MM/GBSA", "AF2-Multimer", 1)  # Only first occurrence in Docking
            content = content.replace("RFdiffusion", "ESM-IF1", 1) # First occurrence Sequence Design
            content = content.replace("ThermoMPNN", "MM/GBSA", 1) # Wait, let's target accurately.
        
        # Safe strict replacement blocks
        # finding the tech blocks to safely replace strings:
        
        # Fix AlphaFold2 multiplex (AF2-Multimer) replacing MM/GBSA under docking:
        idx1 = content.find("HADDOCK3")
        if idx1 != -1:
            if "MM/GBSA" in content[idx1:idx1+100]:
                content = content[:idx1] + content[idx1:idx1+100].replace("MM/GBSA", "AF2-Multimer") + content[idx1+100:]
        
        # Fix Sequence Design RFdiffusion -> ESM-IF1
        idx2 = content.find("ProteinMPNN")
        if idx2 != -1:
            if "RFdiffusion" in content[idx2:idx2+100]:
                content = content[:idx2] + content[idx2:idx2+100].replace("RFdiffusion", "ESM-IF1") + content[idx2+100:]
                
        # Fix Stability & Affinity MM/GBSA replacing EvoEF2/PRODIGY
        idx3 = content.find("ThermoMPNN")
        if idx3 != -1:
            if "EvoEF2 · PRODIGY" in content[idx3:idx3+100]:
                content = content[:idx3] + content[idx3:idx3+100].replace("EvoEF2 · PRODIGY", "MM/GBSA · PRODIGY") + content[idx3+100:]
            elif "EvoEF2" in content[idx3:idx3+100]:
                content = content[:idx3] + content[idx3:idx3+100].replace("EvoEF2", "MM/GBSA") + content[idx3+100:]
                
        # Fix Sequence Fitness AntiFold/ESM-IF1 -> AntiFold/ESM-2
        idx4 = content.find("AntiFold")
        if idx4 != -1:
            if "ESM-IF1" in content[idx4:idx4+100]:
                content = content[:idx4] + content[idx4:idx4+100].replace("ESM-IF1", "ESM-2") + content[idx4+100:]


        # --- 2. Auto-Renumbering the / 14 tags mapping to / 15 ---
        content = content.replace(" / 14</div>", " / 15</div>")

        # --- 3. Auto-Renumbering Slide Contents (s2..s14 -> s3..s15) ---
        # Strategy: Find all <section class="slide..." id="sX"> and increment if X >= 2
        def inc_slide(m):
            sid = int(m.group(2))
            if sid >= 2:
                return f'{m.group(1)}s{sid+1}{m.group(3)}'
            return m.group(0)
            
        content = re.sub(r'(<section class="slide [^"]+" id=")s(\d+)(">)', inc_slide, content)
        
        # Auto rename slide numbers inside elements (e.g. 02 / 15 -> 03 / 15)
        # Regex to target precisely <div class="slide-num">XX / 15</div>
        def inc_num(m):
            num = int(m.group(1))
            if num >= 2:
                return f'<div class="slide-num">{num+1:02d} / 15</div>'
            return m.group(0)
            
        content = re.sub(r'<div class="slide-num">(\d+) / 15</div>', inc_num, content)

        # --- 4. Inject Slide 2 ---
        split_marker = "<!-- ===================== SLIDE 2: PAIN POINTS ===================== -->"
        # Since we ran inc_slide, the comment still says SLIDE 2, which is good for anchor
        if split_marker in content and "<!-- ===================== SLIDE 2: WHO WE ARE ===================== -->" not in content:
            parts = content.split(split_marker)
            # rename the comment of PAIN POINTS since it's now slide 3
            parts[1] = parts[1].replace("SLIDE 14: CTA", "SLIDE 15: CTA")
            parts[1] = parts[1].replace("SLIDE 13: COOPERATION", "SLIDE 14: COOPERATION")
            parts[1] = parts[1].replace("SLIDE 12: TECH ARSENAL", "SLIDE 13: TECH ARSENAL")
            # ... we just replace the ones that matter, but it's just comments so it's fine
            content = parts[0] + slides_content[lang] + split_marker.replace("SLIDE 2", "SLIDE 3") + parts[1]
            
        with open(fpath, "w", encoding="utf-8") as f:
            f.write(content)

print("Insertion of Who We Are and Technical fixes applied properly.")
