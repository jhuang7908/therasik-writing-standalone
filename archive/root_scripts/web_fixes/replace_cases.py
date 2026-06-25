import re

html_content = """
    <!-- 1 -->
    <div class="case-card">
      <span class="case-badge cb-demo">Case Demo</span>
      <div class="case-hd">
        <span class="case-type ct-ab">Humanization</span>
        <div class="case-title">muMAb4D5 → Herceptin Humanization</div>
      </div>
      <div class="case-body">
        <div class="case-result">4 Back-mutations · 15/15 CMC ✓</div>
        <div class="case-detail">Systematic re-humanization using AbEngineCore V4.5.1 — 4 back-mutations, 100% CDR retention.</div>
        <div class="case-impact">Avoid wrong frameworks entering synthesis, saving 2–4 weeks of rework and re-commissioning costs</div>
      </div>
    </div>

    <!-- 2 -->
    <div class="case-card">
      <span class="case-badge cb-demo">Case Demo</span>
      <div class="case-hd">
        <span class="case-type ct-ab">CMC Assessment</span>
        <div class="case-title">muMAb4D5 CMC Optimization</div>
      </div>
      <div class="case-body">
        <div class="case-result">All 15 Parameters Passed · AbRef-458</div>
        <div class="case-detail">15-parameter evaluation benchmarked against AbRef-458 — all metrics passed.</div>
        <div class="case-impact">Pre-clinically confirm candidate developability, reducing Phase I immunogenicity risks</div>
      </div>
    </div>

    <!-- 3 -->
    <div class="case-card">
      <span class="case-badge cb-demo">Case Demo</span>
      <div class="case-hd">
        <span class="case-type ct-ab">VH → VHH</span>
        <div class="case-title">muMAb4D5 VH → Humanized VHH Nanobody</div>
      </div>
      <div class="case-body">
        <div class="case-result">HER2 Affinity Retained · VGRW_SR_R2</div>
        <div class="case-detail">HER2-targeting nanobody engineered from muMAb4D5 VH — 100% CDR retention, SASA-guided surface reshaping.</div>
        <div class="case-impact">Structure and function combined: affinity retained + thermal stability improved, directly advancing pre-IND optimization</div>
      </div>
    </div>

    <!-- 4 -->
    <div class="case-card">
      <span class="case-badge cb-demo">Case Demo</span>
      <div class="case-hd">
        <span class="case-type ct-ab">Affinity Maturation</span>
        <div class="case-title">HER2 VHH Affinity Maturation</div>
      </div>
      <div class="case-body">
        <div class="case-result">Exhaustive interface scanning · 247 mutations</div>
        <div class="case-detail">Binding energy improved −3.32 kcal/mol via epistatic double mutant G49A+F112L.</div>
        <div class="case-impact">Computational pre-screening replaces random mutation library screening, saving 60–80% in synthesis and expression costs</div>
      </div>
    </div>

    <!-- 5 -->
    <div class="case-card">
      <span class="case-badge cb-demo">Case Demo</span>
      <div class="case-hd">
        <span class="case-type ct-ab">CDR Redesign</span>
        <div class="case-title">Structure-Guided CDR Redesign</div>
      </div>
      <div class="case-body">
        <div class="case-result">De novo CDR2/CDR3 sequence reconstruction</div>
        <div class="case-detail">De novo sequence reconstruction + re-maturation to recover 3.75 nM affinity.</div>
        <div class="case-impact">87 diverse candidate sequences, avoiding sequence diversity bottlenecks and patent infringement</div>
      </div>
    </div>

    <!-- 6 -->
    <div class="case-card">
      <span class="case-badge cb-demo">Case Demo</span>
      <div class="case-hd">
        <span class="case-type ct-ab">Bispecific Engineering</span>
        <div class="case-title">Bispecific VHH Expression Optimization</div>
      </div>
      <div class="case-body">
        <div class="case-result">Expression Optimization · Multivalent Format</div>
        <div class="case-detail">pI engineering with linker tuning delivered stronger cross-variant expression profile.</div>
        <div class="case-impact">Rapid response to viral mutations through modular nanobody assembly and expression tuning</div>
      </div>
    </div>

    <!-- 7 -->
    <div class="case-card">
      <span class="case-badge cb-demo">Case Demo</span>
      <div class="case-hd">
        <span class="case-type ct-ab">Cell Therapy Design</span>
        <div class="case-title">Anti-CIDRα1 CAR-Macrophage Design</div>
      </div>
      <div class="case-body">
        <div class="case-result">High-Parasitemia P. falciparum Malaria</div>
        <div class="case-detail">Dual-binder CAR-M architecture for malaria antigen targeting and functional activation.</div>
        <div class="case-impact">Novel CAR-M modality for infectious diseases, expanding beyond traditional oncology applications</div>
      </div>
    </div>

    <!-- 8 -->
    <div class="case-card">
      <span class="case-badge cb-clt">Client Project</span>
      <div class="case-hd">
        <span class="case-type ct-ab">Hapten VAM</span>
        <div class="case-title">Fentanyl Hapten Virtual Affinity Maturation</div>
      </div>
      <div class="case-body">
        <div class="case-result">ΔΔG Consensus −5.53 kcal/mol</div>
        <div class="case-detail">Scenario D optimization — achieved −5.53 kcal/mol improvement in binding energy.</div>
        <div class="case-impact">Identified a synergistic pair, saving 60–80% in synthesis and expression costs</div>
      </div>
    </div>

    <!-- 9 -->
    <div class="case-card">
      <span class="case-badge cb-clt">Client Project</span>
      <div class="case-hd">
        <span class="case-type ct-clt">Epitope Analysis</span>
        <div class="case-title">PD-L1 Dual-Clone Epitope Mapping</div>
      </div>
      <div class="case-body">
        <div class="case-result">Lateral (non-blocking) vs. frontal (blocking)</div>
        <div class="case-detail">Classification of blocking vs. non-blocking clones via structural modeling.</div>
        <div class="case-impact">Exposed shortcomings 3–6 months early, completing fixes before IND, avoiding passive pre-clinical elimination</div>
      </div>
    </div>
"""

filepath = 'd:/InSynBio-AI-Research/Antibody_Engineer_Suite/insynbio-web-source/whitepaper_insynbio_en.html'
with open(filepath, 'r', encoding='utf-8') as f:
    text = f.read()

# Find the cases9 div and replace its inner content
pattern = r'(<div class="cases9">).*?(</div>\s*<p style="font-size:11px;color:var\(--g5\);margin-top:12px;text-align:center;font-style:italic;">)'
new_text = re.sub(pattern, r'\1\n' + html_content + r'\n  \2', text, flags=re.DOTALL)

with open(filepath, 'w', encoding='utf-8') as f:
    f.write(new_text)

print("Replaced cases successfully.")
