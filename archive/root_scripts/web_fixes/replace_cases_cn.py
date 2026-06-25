import re

html_content = """
    <!-- 1 -->
    <div class="case-card">
      <span class="case-badge cb-demo">Case Demo</span>
      <div class="case-hd">
        <span class="case-type ct-ab"></span>
        <div class="case-title">muMAb4D5 → </div>
      </div>
      <div class="case-body">
        <div class="case-result">4  · 15/15 CMC ✓</div>
        <div class="case-detail"> AbEngineCore V4.5.1  —  4 ，CDR 100% 。</div>
        <div class="case-impact">， 2–4 </div>
      </div>
    </div>

    <!-- 2 -->
    <div class="case-card">
      <span class="case-badge cb-demo">Case Demo</span>
      <div class="case-hd">
        <span class="case-type ct-ab">CMC / </span>
        <div class="case-title">muMAb4D5 CMC </div>
      </div>
      <div class="case-body">
        <div class="case-result">15  · AbRef-458</div>
        <div class="case-detail"> AbRef-458  15  CMC  — ，®。</div>
        <div class="case-impact">，</div>
      </div>
    </div>

    <!-- 3 -->
    <div class="case-card">
      <span class="case-badge cb-demo">Case Demo</span>
      <div class="case-hd">
        <span class="case-type ct-ab">VH → VHH</span>
        <div class="case-title">muMAb4D5 VH →  VHH </div>
      </div>
      <div class="case-body">
        <div class="case-result">100% CDR  · SASA </div>
        <div class="case-detail"> muMAb4D5 VH  HER2  — 100% CDR ，SASA ， CMC  HER2 VHH 。</div>
        <div class="case-impact">： + ， IND </div>
      </div>
    </div>

    <!-- 4 -->
    <div class="case-card">
      <span class="case-badge cb-demo">Case Demo</span>
      <div class="case-hd">
        <span class="case-type ct-ab"></span>
        <div class="case-title">VGRW-SR-R2 HER2 VHH </div>
      </div>
      <div class="case-body">
        <div class="case-result"> 5  · 247 </div>
        <div class="case-detail"> G49A+F112L， −3.32 kcal/mol， 70%， RMSD  0.000 Å。</div>
        <div class="case-impact">， 60–80% </div>
      </div>
    </div>

    <!-- 5 -->
    <div class="case-card">
      <span class="case-badge cb-demo">Case Demo</span>
      <div class="case-hd">
        <span class="case-type ct-ab">CDR </span>
        <div class="case-title">CDR </div>
      </div>
      <div class="case-body">
        <div class="case-result"> · 13× </div>
        <div class="case-detail"> SR-R2 ， AI  CDR2/CDR3 ， 49.75 nM  3.75 nM。</div>
        <div class="case-impact">87 ，</div>
      </div>
    </div>

    <!-- 6 -->
    <div class="case-card">
      <span class="case-badge cb-demo">Case Demo</span>
      <div class="case-hd">
        <span class="case-type ct-ab"> VHH</span>
        <div class="case-title"></div>
      </div>
      <div class="case-body">
        <div class="case-result"> (pI)  · </div>
        <div class="case-detail">SmartLink™ + VirtualCMC  VHH-GS-VHH 。</div>
        <div class="case-impact">，</div>
      </div>
    </div>

    <!-- 7 -->
    <div class="case-card">
      <span class="case-badge cb-demo">Case Demo</span>
      <div class="case-hd">
        <span class="case-type ct-ab">CAR‑M </span>
        <div class="case-title"> CIDRα1 CAR-</div>
      </div>
      <div class="case-body">
        <div class="case-result">ACTES 11  · </div>
        <div class="case-detail"> 6  CIDRα1  CAR-M —  mRNA-LNP  4 。</div>
        <div class="case-impact"> CAR-M ，</div>
      </div>
    </div>

    <!-- 8 -->
    <div class="case-card">
      <span class="case-badge cb-clt">Client Project</span>
      <div class="case-hd">
        <span class="case-type ct-ab">Half-Hapten VAM</span>
        <div class="case-title">Ab278 </div>
      </div>
      <div class="case-body">
        <div class="case-result"> · 100+ </div>
        <div class="case-detail">， 5 ，。</div>
        <div class="case-impact">， 60–80% </div>
      </div>
    </div>

    <!-- 9 -->
    <div class="case-card">
      <span class="case-badge cb-clt">Client Project</span>
      <div class="case-hd">
        <span class="case-type ct-clt">Anti-PD-L1 Panel</span>
        <div class="case-title"> PD-L1 </div>
      </div>
      <div class="case-body">
        <div class="case-result">Side-binding vs. Top blocking</div>
        <div class="case-detail">、， side-binding / ADC  blocking clone， human / cyno PD-L1 。</div>
        <div class="case-impact"> 3–6 ， IND ，</div>
      </div>
    </div>
"""

filepath = 'd:/InSynBio-AI-Research/Antibody_Engineer_Suite/therasik-web-source/whitepaper_therasik_cn.html'
with open(filepath, 'r', encoding='utf-8') as f:
    text = f.read

# Find the cases9 div and replace its inner content
pattern = r'(<div class="cases9">).*?(</div>\s*<p style="font-size:11px;color:var\(--g5\);margin-top:12px;text-align:center;font-style:italic;">)'
new_text = re.sub(pattern, r'\1\n' + html_content + r'\n  \2', text, flags=re.DOTALL)

with open(filepath, 'w', encoding='utf-8') as f:
    f.write(new_text)

print("Replaced cases successfully in Chinese version.")
