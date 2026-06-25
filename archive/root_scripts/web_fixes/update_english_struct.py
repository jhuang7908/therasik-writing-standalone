import os
import re

file_path = r"d:\InSynBio-AI-Research\Antibody_Engineer_Suite\insynbio-web-source\InSynBio_Pitch_Deck.html"

with open(file_path, "r", encoding="utf-8") as f:
    html = f.read()

def replace_section(slide_id, new_content, html_content):
    # Regex to find the whole section
    pattern = r'(<section[^>]*id="' + slide_id + r'"[^>]*>).*?(</section>)'
    # Use re.DOTALL to match across newlines
    match = re.search(pattern, html_content, re.DOTALL)
    if match:
        # replace the inner content between the tags, or replace the whole tags if provided
        return html_content[:match.start()] + new_content + html_content[match.end():]
    return html_content

# --- 1. Slide 1 (Cover) ---
s1_content = """<section class="slide bg-dark hero-grid-bg" id="s1" style="background-image: radial-gradient(#0d9488 1px, transparent 1px), radial-gradient(circle at center, #0a3632 0%, #061815 100%); background-size: 40px 40px, 100% 100%;">
  <div class="slide-inner" style="justify-content:center; align-items:center; text-align:center;">
    <h1 class="hero-title" style="margin-top:24px; font-size:76px;">
      Clinical Data-Guided AI<br><em>Biotherapeutic Strategy System</em>
    </h1>
    <p class="slide-subtitle" style="margin:0 auto 28px;text-align:center;max-width:960px; font-size:22px;">
      Fusing immunology logic, clinical data benchmarking, and private AI inference<br>to deliver actionable drug design—not just isolated algorithm scores.
    </p>
    <a href="#s2" style="display:inline-block;padding:12px 30px;background:#5eead4;color:#0d4a44;font-size:16px;font-weight:700;border-radius:30px;text-decoration:none;">Enter Overview →</a>
    
    <div style="margin-top: 60px; font-size: 18px; color: rgba(255,255,255,0.7); line-height: 1.8; text-align:center;">
      <div><strong style="color:#ffffff;">Presenter:</strong> [Name / Title]</div>
      <div><strong style="color:#ffffff;">Date:</strong> [YYYY-MM-DD]</div>
      <div><strong style="color:#ffffff;">Location:</strong> [Event / Online]</div>
    </div>
  </div>
  <div class="slide-num">01 / 15</div>
</section>"""
html = replace_section("s1", s1_content, html)


# --- 2. Slide 4 (Positioning) ---
s4_content = """<section class="slide bg-dark" id="s4">
  <div class="slide-inner">
    <span class="label label-teal">Value & Position</span>
    <h2 class="slide-title" style="font-size:54px;">A Decision System. <span>Not a Tool Vendor.</span></h2>
    <p class="slide-subtitle" style="font-size:22px; max-width:960px;">Blending the absolute reliability of traditional physical labs with the extreme logic of AI to drastically de-risk your biologics investment.</p>
    
    <div class="quote-box" style="margin-top: 20px;">
      <p style="font-size:18px;"><strong style="color:#fff">Our 3 Core Pillars:</strong><br>1️⃣ Deep empirical Immunology foundation, bridging "dry" computational blind spots.<br>2️⃣ Exclusive, high-quality clinical databases functioning as absolute biological benchmarks.<br>3️⃣ Private Machine Learning driving deterministic drug design, acting as an architect rather than just software.</p>
    </div>

    <div class="card-grid g3">
      <div class="card">
        <h3 style="font-size:24px;color:var(--text-muted)">General AI Software Vendors</h3>
        <p style="font-size:18px; color:var(--text-muted)">Sell isolated tools without wet-lab expertise. Forces your teams to guess the implications of "black-box" scores without guaranteeing physiological viability.</p>
      </div>
      <div class="card card-accent card-teal" style="transform:scale(1.05); box-shadow:0 10px 30px rgba(13,148,136,0.2);">
        <h3 style="font-size:24px;">The InSynBio System</h3>
        <p style="font-size:18px;">Minimizes blind wet-lab budgets. We supply <strong>actionable blueprints</strong> evaluated against thousands of late-stage clinical assets to guarantee translative manufacturability.</p>
      </div>
      <div class="card">
        <h3 style="font-size:24px;color:var(--text-muted)">Traditional Wet-Lab CROs</h3>
        <p style="font-size:18px; color:var(--text-muted)">Unbearably long cycles (>9 months), staggering capital requirements, and massive trial-and-error costs. But their physical results are generally reliable.</p>
      </div>
    </div>
  </div>
  <div class="slide-num">04 / 15</div>
</section>"""
html = replace_section("s4", s4_content, html)


# --- 3. Slide 6 (Tech Arsenal - Inject Vaccine Class) ---
vaccine_arsenal_insertion = """
      <div class="card" style="text-align:center;padding:16px;">
        <div style="font-size:14px;color:#5eead4;font-weight:700;margin-bottom:6px;">Vaccine Systems</div>
        <div style="font-size:14px;font-weight:700;color:#fff;">Neoantigen Evaluator</div>
        <div style="font-size:14px;font-weight:700;color:#fff;">mRNA Toolkit</div>
      </div>
"""
# Find Immunogenicity card and insert vaccine immediately after it
vaccine_flag = '<div style="font-size:14px;color:#5eead4;font-weight:700;margin-bottom:6px;">Vaccine Systems</div>'
if vaccine_flag not in html:
    iem_str = '<div style="font-size:14px;color:#fde68a;font-weight:700;margin-bottom:6px;">Immunogenicity</div>'
    if iem_str in html:
        # Find closing div of this card
        idx1 = html.find(iem_str)
        idx2 = html.find('</div>\n      </div>', idx1)
        if idx2 != -1:
            idx2 += 18
            html = html[:idx2] + vaccine_arsenal_insertion + html[idx2:]


# --- 4. Slide 7 (CMC) ---
html = html.replace('15 parameters across nearly <strong style="color:#fff;">1,000 marketed clinical antibodies</strong>',
                    '15 strict parameters across a proprietary database of nearly <strong style="color:#fff;">1,000 marketed clinical-stage antibodies</strong> for unparalleled 1v1 empirical benchmarking')

html = html.replace('We computed 15 parameters', 'We perform systemic profiling targeting 15 parameters')


# --- 5. Slide 10 (Deliverables) ---
s10_content = """<section class="slide bg-dark" id="s10">
  <div class="slide-inner">
    <span class="label label-teal">Deliverables</span>
    <h2 class="slide-title" style="font-size:54px;">Comprehensive Deliverables — <span>Beyond Raw Data</span></h2>
    <div class="pipe" style="margin-bottom:40px; overflow-x:auto;">
      <div class="pipe-step"><div class="step-n" style="font-size:18px;width:30px;height:30px;line-height:26px;">1</div><span style="font-size:12px;">Seq Analysis</span></div>
      <div class="pipe-step gap">></div>
      <div class="pipe-step"><div class="step-n" style="font-size:18px;width:30px;height:30px;line-height:26px;">2</div><span style="font-size:12px;">Humanization</span></div>
      <div class="pipe-step gap">></div>
      <div class="pipe-step"><div class="step-n" style="font-size:18px;width:30px;height:30px;line-height:26px;">3</div><span style="font-size:12px;">Structure & Epi.</span></div>
      <div class="pipe-step gap">></div>
      <div class="pipe-step"><div class="step-n" style="font-size:18px;width:30px;height:30px;line-height:26px;">4</div><span style="font-size:12px;">Affinity VAM</span></div>
      <div class="pipe-step gap">></div>
      <div class="pipe-step"><div class="step-n" style="font-size:18px;width:30px;height:30px;line-height:26px;">5</div><span style="font-size:12px;">CMC Check</span></div>
      <div class="pipe-step gap">></div>
      <div class="pipe-step"><div class="step-n" style="font-size:18px;width:30px;height:30px;line-height:26px;">6</div><span style="font-size:12px;">Clinical Bench</span></div>
      <div class="pipe-step gap">></div>
      <div class="pipe-step"><div class="step-n" style="font-size:18px;width:30px;height:30px;line-height:26px;">7</div><span style="font-size:12px;">Final Report</span></div>
    </div>
    <div class="card-grid g2">
      <div class="card" style="text-align:center;">
        <h3 style="font-size:24px;justify-content:center;">⚖️ Structural Stability Priority</h3>
        <p style="font-size:18px; line-height: 1.6;">Leveraging structural integrity algorithms to guarantee subsequent <strong style="color:var(--text);">affinity rescue (VAM)</strong> and ensuring CDR loop conformation remains perfectly undisturbed.</p>
      </div>
      <div class="card" style="text-align:center;">
        <h3 style="font-size:24px;justify-content:center;">📊 1,000+ Clinical Benchmarks</h3>
        <p style="font-size:18px; line-height: 1.6;">Your molecule's properties aren't measured in a vacuum. We actively plot its metrics alongside CMC thresholds derived from ~1,000 globally approved antibodies.</p>
      </div>
    </div>
  </div>
  <div class="slide-num">10 / 15</div>
</section>"""
html = replace_section("s10", s10_content, html)


# --- 6. Slides 11 and 12 (Case Studies Separated) ---
s11_content = """<section class="slide bg-dark" id="s11">
  <div class="slide-inner">
    <span class="label label-amber">True Client Partnerships</span>
    <h2 class="slide-title" style="font-size:54px;">Real-world Success Cases — <span>Commercial Deployments</span></h2>
    
    <div class="card-grid g3" style="gap:12px;">
      <div class="case-mini" style="border-left-color:#0ea5e9;">
        <h4 style="font-size:20px;"><a href="case_bispecific_vhh_expression_optimization.html" target="_blank" style="color:inherit;text-decoration:none;">Bispecific VHH Formats <span style="font-size:0.8em">↗</span></a></h4>
        <ul>
          <li style="font-size:18px;">pI engineering: 8.2 → 6.8 colloidal stability</li>
          <li style="font-size:18px;">4.8× IC90 expression increment via GS-8 linker</li>
        </ul>
      </div>

      <div class="case-mini" style="border-left-color:#f59e0b;">
        <h4 style="font-size:20px;"><a href="case_fentanyl_hapten_vam.html" target="_blank" style="color:inherit;text-decoration:none;">Small Molecule (Fentanyl) Affinity <span style="font-size:0.8em">↗</span></a></h4>
        <ul>
          <li style="font-size:18px;">Affinity matched precisely for diagnostic resolution</li>
          <li style="font-size:18px;">Optimized specifically for commercial assay thresholds</li>
        </ul>
      </div>

      <div class="case-mini" style="border-left-color:#10b981;">
        <h4 style="font-size:20px;"><a href="case_pdl1_epitope_analysis.html" target="_blank" style="color:inherit;text-decoration:none;">PD-L1 Epitope Mapping <span style="font-size:0.8em">↗</span></a></h4>
        <ul>
          <li style="font-size:18px;">Unveiled precise sterical blocking domains</li>
          <li style="font-size:18px;">Validated downstream MOA translational efficacy</li>
        </ul>
      </div>
    </div>
  </div>
  <div class="slide-num">11 / 15</div>
</section>"""
html = replace_section("s11", s11_content, html)

s12_content = """<section class="slide bg-dark" id="s12">
  <div class="slide-inner">
    <span class="label label-teal">Internal Validations</span>
    <h2 class="slide-title" style="font-size:54px;">R&D & PoC Architectures — <span>Demonstration Workflows</span></h2>
    
    <div class="card-grid g4" style="gap:12px;">
      <div class="case-mini" style="border-left-color:#8b5cf6;">
        <h4 style="font-size:20px;"><a href="case_vgrw_cdr_redesign_remat.html" target="_blank" style="color:inherit;text-decoration:none;"><span style="color:#e879f9;">*Key Highlight*</span><br> De novo CDR Design <span style="font-size:0.8em">↗</span></a></h4>
        <ul>
          <li style="font-size:16px;">Shatters rigid competitor IP moats</li>
          <li style="font-size:16px;">Derives completely novel backbone topologies</li>
        </ul>
      </div>

      <div class="case-mini" style="border-left-color:#ec4899;">
        <h4 style="font-size:20px;"><a href="case_mumab4d5_humanization_en.html" target="_blank" style="color:inherit;text-decoration:none;">muMAb4D5 Humanization <span style="font-size:0.8em">↗</span></a></h4>
        <ul>
          <li style="font-size:16px;">Full structural binding preservation</li>
          <li style="font-size:16px;">Conserved polymorphic configurations</li>
        </ul>
      </div>

      <div class="case-mini" style="border-left-color:#14b8a6;">
        <h4 style="font-size:20px;"><a href="case_mumab4d5_cmc.html" target="_blank" style="color:inherit;text-decoration:none;">muMAb4D5 CMC Metrics <span style="font-size:0.8em">↗</span></a></h4>
        <ul>
          <li style="font-size:16px;">Passed 15 parameters with flying colors</li>
          <li style="font-size:16px;">Achieved ADI score of 77/100</li>
        </ul>
      </div>

      <div class="case-mini" style="border-left-color:#ef4444;">
        <h4 style="font-size:20px;"><a href="case_malaria_carm_design.html" target="_blank" style="color:inherit;text-decoration:none;">CAR-M Engager Target <span style="font-size:0.8em">↗</span></a></h4>
        <ul>
          <li style="font-size:16px;">Modeling of ultra-complex macrophage signaling</li>
          <li style="font-size:16px;">Validates InSynBio ACTES DB</li>
        </ul>
      </div>
    </div>
  </div>
  <div class="slide-num">12 / 15</div>
</section>"""
html = replace_section("s12", s12_content, html)


with open(file_path, "w", encoding="utf-8") as f:
    f.write(html)

print("Comprehensive English deck restructuring executed!")
