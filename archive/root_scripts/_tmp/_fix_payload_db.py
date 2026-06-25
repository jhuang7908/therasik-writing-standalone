"""Fix ADC Database payload tab: standardize data-cls, fix filter, add missing payloads + patents."""
import re

path = r'D:/InSynBio-AI-Research/Antibody_Engineer_Suite/therasik-web-source/Therasik_ADC_Database.html'
with open(path, 'r', encoding='utf-8') as f:
    content = f.read

# ─────────────────────────────────────────────────────────────────
# 1. Standardize data-cls values (fix plural/case/lang mismatches)
# ─────────────────────────────────────────────────────────────────
cls_normalize = {
    'data-cls=""':         'data-cls="Protein Toxin"',
    'data-cls=""':         'data-cls="Radionuclide"',
    'data-cls="Protein Toxins"':    'data-cls="Protein Toxin"',
    'data-cls="Dna Damaging Agents"':'data-cls="DNA Damaging Agent"',
    'data-cls="Topoisomerase I Inhibitors"':'data-cls="Topoisomerase I Inhibitor"',
    'data-cls="Tubulin Inhibitors"': 'data-cls="Tubulin Inhibitor"',
    'data-cls="Ksp Inhibitors"':    'data-cls="KSP Inhibitor"',
    'data-cls="Spliceosome Inhibitor"':'data-cls="Spliceosome Inhibitor"',  # already ok
    'data-cls="Immunostimulatory Agonist"':'data-cls="Immunostimulatory Agonist"',  # ok
}
for old, new in cls_normalize.items:
    content = content.replace(old, new)
print("Step 1: data-cls normalized")

# ─────────────────────────────────────────────────────────────────
# 2. Fix the payload filter dropdown
# ─────────────────────────────────────────────────────────────────
old_filter = '''      <select class="filter-sel" id="filterPayloadCls">
        <option value="">All Mechanisms</option>
    <option value="Bcl-xL Inhibitor">Bcl-xL Inhibitor</option>
    <option value="DNA Damaging Agent">DNA Damaging Agent</option>
    <option value="Dna Damaging Agents">Dna Damaging Agents</option>
    <option value="Ksp Inhibitors">Ksp Inhibitors</option>
    <option value="Protein Toxins">Protein Toxins</option>
    <option value="RNA Pol II Inhibitor">RNA Pol II Inhibitor</option>
    <option value="Topoisomerase I Inhibitors">Topoisomerase I Inhibitors</option>
    <option value="Tubulin Inhibitors">Tubulin Inhibitors</option>
    <option value="Immunostimulatory Agonist">Immunostimulatory Agonist</option>
    <option value="Spliceosome Inhibitor">Spliceosome Inhibitor</option>
    <option value="Tubulin Inhibitor">Tubulin Inhibitor</option>
    <option value="Topoisomerase I Inhibitor">Topoisomerase I Inhibitor</option>
    <option value="radionuclide">Radionuclide</option>
    <option value="protein_toxin">Protein Toxin</option>
      </select>'''

new_filter = '''      <select class="filter-sel" id="filterPayloadCls">
        <option value="">All Mechanisms</option>
        <option value="Tubulin Inhibitor">Tubulin Inhibitor</option>
        <option value="Topoisomerase I Inhibitor">Topoisomerase I Inhibitor（TOP1 ）</option>
        <option value="DNA Damaging Agent">DNA Damaging Agent（DNA ）</option>
        <option value="Maytansinoid">Maytansinoid</option>
        <option value="Immunostimulatory Agonist">Immunostimulatory Agonist</option>
        <option value="RNA Pol II Inhibitor">RNA Pol II Inhibitor（RNA ）</option>
        <option value="Spliceosome Inhibitor">Spliceosome Inhibitor</option>
        <option value="KSP Inhibitor">KSP Inhibitor</option>
        <option value="Bcl-xL Inhibitor">Bcl-xL Inhibitor</option>
        <option value="Protein Toxin">Protein Toxin</option>
        <option value="Radionuclide">Radionuclide</option>
        <option value="Protein Degrader">Protein Degrader / PROTAC</option>
      </select>'''

if old_filter in content:
    content = content.replace(old_filter, new_filter)
    print("Step 2: payload filter replaced")
else:
    # Try partial match - replace from filterPayloadCls to next </select>
    pattern = r'<select class="filter-sel" id="filterPayloadCls">.*?</select>'
    content = re.sub(pattern, new_filter.strip, content, flags=re.DOTALL)
    print("Step 2: payload filter replaced (regex fallback)")

# ─────────────────────────────────────────────────────────────────
# 3. Fix conjugation tab filter - add homogeneity options
# ─────────────────────────────────────────────────────────────────
old_conj_filter = '''<option value="">All homogeneity</option>'''
new_conj_filter = '''<option value="">All homogeneity</option>
        <option value=""> (Very High, DAR CV&lt;5%)</option>
        <option value=""> (High, DAR CV 5–10%)</option>
        <option value=""> (Medium, DAR CV 10–20%)</option>
        <option value=""> (Low, DAR CV&gt;20%)</option>'''
content = content.replace(old_conj_filter, new_conj_filter)
print("Step 3: conjugation filter fixed")

# ─────────────────────────────────────────────────────────────────
# 4. Add missing major payload cards before </div> of grid
# ─────────────────────────────────────────────────────────────────
missing_payloads = '''
<!-- ═══ MISSING PAYLOADS ADDED ═══ -->

<!-- DM1 (Maytansinoid) -->
<div class="card" onclick="toggleCard(this)" data-cls="Maytansinoid" data-search="dm1 maytansinoid emtansine maytansine immunogen kadcyla t-dm1 thioether non-cleavable">
  <div class="card-header">
    <div class="card-title">DM1 (Emtansine)</div>
    <span class="badge badge-approved">Maytansinoid</span>
  </div>
  <div class="card-body">
    <div class="cc-brief">IC50: 0.01–0.1 nM · :  · LogP: 2.0 · Kadcyla（T-DM1） payload</div>
    <div style="font-size:10px;color:#1a7a4a;font-weight:600;margin-top:2px">：（ ADC）</div>
    <span class="exp-toggle"></span>
    <div class="cc-detail">
      <div class="collapse-bar"><div class="collapse-progress"></div></div>
      <div style="font-size:10px;font-weight:700;text-transform:uppercase;letter-spacing:0.6px;color:#888;margin:10px 0 4px;border-top:1px solid #eee;padding-top:8px"></div>
      <div class="info-row"><span class="info-label"></span><span class="info-value">Maytansinoid</span></div>
      <div class="info-row"><span class="info-label">MoA</span><span class="info-value">Binds tubulin at the vinca alkaloid binding site, inhibiting microtubule polymerization and causing mitotic arrest (G2/M).</span></div>
      <div class="info-row"><span class="info-label">IC50</span><span class="info-value">0.01–0.1 nM (10× more potent than MMAE in some cell lines)</span></div>
      <div class="info-row"><span class="info-label"></span><span class="info-value">G2/M phase only; limited activity in quiescent cells</span></div>
      <div style="font-size:10px;font-weight:700;text-transform:uppercase;letter-spacing:0.6px;color:#888;margin:10px 0 4px;border-top:1px solid #eee;padding-top:8px"></div>
      <div class="info-row"><span class="info-label">DLT</span><span class="info-value">Peripheral neuropathy (grade 3–4: ~5%); Hepatotoxicity (AST/ALT elevation); Thrombocytopenia</span></div>
      <div class="info-row"><span class="info-label"></span><span class="info-value">DM1-Lys (active) after complete lysosomal antibody degradation; does NOT diffuse through membranes → no bystander effect</span></div>
      <div style="font-size:10px;font-weight:700;text-transform:uppercase;letter-spacing:0.6px;color:#888;margin:10px 0 4px;border-top:1px solid #eee;padding-top:8px">ADC </div>
      <div class="info-row"><span class="info-label">log P</span><span class="info-value">2.0 (moderate hydrophobicity; DAR ≤4 recommended for thioether-SMCC conjugation)</span></div>
      <div class="info-row"><span class="info-label"> DAR</span><span class="info-value">3–4 (with SMCC non-cleavable linker); higher DAR causes aggregation</span></div>
      <div class="info-row"><span class="info-label"></span><span class="info-value">ABSENT — DM1-Lys metabolite is charged, membrane-impermeable. Requires homogeneous antigen expression.</span></div>
      <div class="info-row"><span class="info-label"></span><span class="info-value">SMCC (non-cleavable thioether); SPDB (cleavable disulfide, for DM4 variant); N-succinimidyl pyridyldithiopropionate</span></div>
      <div style="font-size:10px;font-weight:700;text-transform:uppercase;letter-spacing:0.6px;color:#888;margin:10px 0 4px;border-top:1px solid #eee;padding-top:8px"></div>
      <div class="info-row"><span class="info-label"></span><span class="info-value">US5208020A — Chari et al. (ImmunoGen), 1993. Maytansinoid-thiol-antibody conjugates via SMCC. Pioneer ADC patent.</span></div>
      <div class="info-row"><span class="info-label">DM1 </span><span class="info-value">US5416064A — Chari et al. (ImmunoGen), 1995. DM1 thiol derivative synthesis and purification.</span></div>
      <div class="info-row"><span class="info-label">Kadcyla </span><span class="info-value">US7371376B2 — Phillips et al. (Genentech/ImmunoGen). T-DM1 (trastuzumab-SMCC-DM1). Filed 2003.</span></div>
      <div class="info-row"><span class="info-label"></span><span class="info-value">US5208020A expired (~2010). DM1 chemistry broadly available. Kadcyla composition patent US7371376B2 active until ~2024; supplementary protection may extend.</span></div>
      <div class="info-row"><span class="info-label">PubChem CID</span><span class="info-value"><a href="https://pubchem.ncbi.nlm.nih.gov/compound/5289200" target="_blank" onclick="event.stopPropagation" style="color:var(--primary)">5289200</a></span></div>
      <div class="info-row" style="font-size:11px;color:#666"><span class="info-label"></span><span class="info-value">PMID:1956059 (Chari 1992 DM1 original); PMID:22003127 (Kadcyla phase III EMILIA)</span></div>
    </div>
  </div>
</div>

<!-- DM4 (Maytansinoid) -->
<div class="card" onclick="toggleCard(this)" data-cls="Maytansinoid" data-search="dm4 maytansinoid ravtansine immunogen elahere mirvetuximab spdb disulfide cleavable">
  <div class="card-header">
    <div class="card-title">DM4 (Ravtansine)</div>
    <span class="badge badge-approved">Maytansinoid</span>
  </div>
  <div class="card-body">
    <div class="cc-brief">IC50: 0.01–0.1 nM · LogP: 2.8 ·  SPDB  linker · Elahere（mirvetuximab soravtansine）</div>
    <div style="font-size:10px;color:#1a7a4a;font-weight:600;margin-top:2px">：（FDA 2022 ，FRα+）</div>
    <span class="exp-toggle"></span>
    <div class="cc-detail">
      <div class="collapse-bar"><div class="collapse-progress"></div></div>
      <div class="info-row"><span class="info-label"></span><span class="info-value">Maytansinoid（DM4 = C-3  DM1 ）</span></div>
      <div class="info-row"><span class="info-label">MoA</span><span class="info-value">Same as DM1: tubulin vinca-domain binding, mitotic arrest. DM4 has a bulkier side chain improving SPDB-linker compatibility.</span></div>
      <div class="info-row"><span class="info-label">IC50</span><span class="info-value">0.01–0.1 nM</span></div>
      <div class="info-row"><span class="info-label"></span><span class="info-value">WEAK (thiol metabolite DM4-me partially membrane-permeable compared to DM1-Lys; limited bystander activity)</span></div>
      <div class="info-row"><span class="info-label"></span><span class="info-value">SPDB (cleavable disulfide); SPP (disulfide); DM4 requires hindered disulfide for optimal intracellular release</span></div>
      <div style="font-size:10px;font-weight:700;text-transform:uppercase;letter-spacing:0.6px;color:#888;margin:10px 0 4px;border-top:1px solid #eee;padding-top:8px"></div>
      <div class="info-row"><span class="info-label"></span><span class="info-value">US7303749B2 — Kovtun et al. (ImmunoGen), 2007. DM4-SPDB disulfide conjugates; improved cleavable linker strategy.</span></div>
      <div class="info-row"><span class="info-label">Elahere </span><span class="info-value">US8877901B2 — AbDev / ImmunoGen. Mirvetuximab soravtansine (anti-FRα-SPDB-DM4). FDA 2022 accelerated approval.</span></div>
      <div class="info-row"><span class="info-label"></span><span class="info-value">Active. US8877901B2 expires ~2030. SPDB-DM4 platform broadly licensed by ImmunoGen.</span></div>
      <div class="info-row" style="font-size:11px;color:#666"><span class="info-label"></span><span class="info-value">PMID:20685660 (Elahere preclinical); FDA label: Elahere 2022</span></div>
    </div>
  </div>
</div>

<!-- MMAF (Tubulin Inhibitor) -->
<div class="card" onclick="toggleCard(this)" data-cls="Tubulin Inhibitor" data-search="mmaf monomethyl auristatin f tubulin non-bystander charged membrane-impermeant seagen besylomab">
  <div class="card-header">
    <div class="card-title">MMAF (Monomethyl Auristatin F)</div>
    <span class="badge badge-linker">Tubulin Inhibitor</span>
  </div>
  <div class="card-body">
    <div class="cc-brief">IC50: 0.1–5 nM · LogP: 1.8  · ： ·  MMAE </div>
    <div style="font-size:10px;color:#1a7a4a;font-weight:600;margin-top:2px">：</div>
    <span class="exp-toggle"></span>
    <div class="cc-detail">
      <div class="collapse-bar"><div class="collapse-progress"></div></div>
      <div class="info-row"><span class="info-label"></span><span class="info-value">Tubulin Inhibitor (Auristatin family)</span></div>
      <div class="info-row"><span class="info-label">MoA</span><span class="info-value">Tubulin vinca-domain binding (same as MMAE). C-terminal phenylalanine adds negative charge, preventing membrane permeation.</span></div>
      <div class="info-row"><span class="info-label">IC50</span><span class="info-value">0.1–5 nM (less potent than MMAE 0.1–1 nM)</span></div>
      <div class="info-row"><span class="info-label">log P</span><span class="info-value">1.8 (charged at physiological pH; membrane-impermeant → no bystander effect)</span></div>
      <div class="info-row"><span class="info-label"></span><span class="info-value">ABSENT — MMAF is charged and cannot cross cell membranes. Ideal for homogeneous antigen expression; avoids off-target killing.</span></div>
      <div class="info-row"><span class="info-label"></span><span class="info-value">Polatuzumab vedotin-MMAF variants; Glofitamab-MMAF (Phase II); anti-BCMA ADC (Besylomab inotuzumab ozogamicin contains calicheamicin not MMAF — correction: MMAF used in GSK2857916 glofitamab)</span></div>
      <div style="font-size:10px;font-weight:700;text-transform:uppercase;letter-spacing:0.6px;color:#888;margin:10px 0 4px;border-top:1px solid #eee;padding-top:8px"></div>
      <div class="info-row"><span class="info-label"></span><span class="info-value">US6884869B2 — Doronina et al. (Seagen), 2005. MMAF synthesis and auristatin ADC with non-cleavable maleimide linker (mc-MMAF).</span></div>
      <div class="info-row"><span class="info-label">mc-MMAF </span><span class="info-value">US7750116B1 — Senter et al. (Seagen). mc-MMAF conjugation via cysteine maleimide, non-cleavable format.</span></div>
      <div class="info-row"><span class="info-label"></span><span class="info-value">US6884869B2 expires ~2022 (may be expired). MMAF chemistry becoming more accessible; specific ADC compositions still protected.</span></div>
      <div class="info-row" style="font-size:11px;color:#666"><span class="info-label"></span><span class="info-value">PMID:16537434 (Doronina 2006 MMAF); PMID:22399561 (MMAF ADC clinical)</span></div>
    </div>
  </div>
</div>

<!-- SN-38 (TOP1i) -->
<div class="card" onclick="toggleCard(this)" data-cls="Topoisomerase I Inhibitor" data-search="sn-38 sn38 irinotecan trodelvy sacituzumab govitecan trop2 tnbc cl2a hydrophilic bystander top1i">
  <div class="card-header">
    <div class="card-title">SN-38</div>
    <span class="badge badge-linker">Topoisomerase I Inhibitor</span>
  </div>
  <div class="card-body">
    <div class="cc-brief">IC50: 1–10 nM · LogP: −0.37· ： · Trodelvy（Sacituzumab govitecan） payload</div>
    <div style="font-size:10px;color:#1a7a4a;font-weight:600;margin-top:2px">：（FDA 2020  TNBC）</div>
    <span class="exp-toggle"></span>
    <div class="cc-detail">
      <div class="collapse-bar"><div class="collapse-progress"></div></div>
      <div class="info-row"><span class="info-label"></span><span class="info-value">Topoisomerase I Inhibitor (Camptothecin derivative)</span></div>
      <div class="info-row"><span class="info-label">MoA</span><span class="info-value">Stabilizes topoisomerase I-DNA cleavage complex, causing replication fork collapse and double-strand breaks. Cell-cycle independent (active in S-phase cells).</span></div>
      <div class="info-row"><span class="info-label">IC50</span><span class="info-value">1–10 nM (less potent than DXd but sufficient at high DAR 7–8)</span></div>
      <div class="info-row"><span class="info-label">log P</span><span class="info-value">−0.37 (highly hydrophilic; allows DAR 6–8 without aggregation — key CMC advantage)</span></div>
      <div class="info-row"><span class="info-label"></span><span class="info-value">STRONG — Papp ≈ 15 × 10⁻⁶ cm/s (high membrane permeability). ~30% TROP2(−) bystander cells killed in co-culture. Overcomes tumor heterogeneity.</span></div>
      <div class="info-row"><span class="info-label"></span><span class="info-value">Glucuronidation to SN-38G (inactive). SN-38G cannot re-enter cells; limits systemic bystander toxicity.</span></div>
      <div class="info-row"><span class="info-label">DLT</span><span class="info-value">Diarrhea (Grade 3–4: 11% in Trodelvy); Neutropenia; Alopecia. GI epithelial TROP2 expression drives diarrhea.</span></div>
      <div style="font-size:10px;font-weight:700;text-transform:uppercase;letter-spacing:0.6px;color:#888;margin:10px 0 4px;border-top:1px solid #eee;padding-top:8px"></div>
      <div class="info-row"><span class="info-label">SN-38 </span><span class="info-value">US5004758A — Sawada et al. (Dainippon Pharmaceutical), 1991. SN-38 and camptothecin analogues. Foundational patent.</span></div>
      <div class="info-row"><span class="info-label">CL2A-SN38 ADC</span><span class="info-value">US7999083B2 — Goldenberg et al. (Immunomedics/Gilead). CL2A linker + SN-38 ADC conjugation method. Core Trodelvy patent.</span></div>
      <div class="info-row"><span class="info-label">Trodelvy </span><span class="info-value">US10814020B2 — Immunomedics/Gilead. SN-38+CL2A+hRS7 (sacituzumab govitecan). Expires ~2034.</span></div>
      <div class="info-row"><span class="info-label"></span><span class="info-value">SN-38 molecule patent expired. CL2A-SN38 linker method (US7999083) active. Combination composition US10814020B2 active to 2034. New antibody clone would need different linker or payload modification.</span></div>
      <div class="info-row"><span class="info-label">PubChem CID</span><span class="info-value"><a href="https://pubchem.ncbi.nlm.nih.gov/compound/104842" target="_blank" onclick="event.stopPropagation" style="color:var(--primary)">104842</a></span></div>
      <div class="info-row" style="font-size:11px;color:#666"><span class="info-label"></span><span class="info-value">PMID:12810617 (Goldenberg SN-38 ADC); PMID:33471906 (Trodelvy ASCENT TNBC)</span></div>
    </div>
  </div>
</div>

<!-- Calicheamicin (DNA Damaging) -->
<div class="card" onclick="toggleCard(this)" data-cls="DNA Damaging Agent" data-search="calicheamicin calicheamicin-gamma1 enediyne dna double strand break mylotarg gemtuzumab besylomab inotuzumab aml all hydrazone">
  <div class="card-header">
    <div class="card-title">Calicheamicin (γ1I)</div>
    <span class="badge badge-payload">DNA Damaging Agent</span>
  </div>
  <div class="card-body">
    <div class="cc-brief">IC50: &lt;0.01 nM（pM ）· DAR 2–2.5 ·  pH  · Mylotarg / Besylomab  payload</div>
    <div style="font-size:10px;color:#1a7a4a;font-weight:600;margin-top:2px">：（2  ADC）</div>
    <span class="exp-toggle"></span>
    <div class="cc-detail">
      <div class="collapse-bar"><div class="collapse-progress"></div></div>
      <div class="info-row"><span class="info-label"></span><span class="info-value">DNA Damaging Agent — Enediyne（， DNA ）</span></div>
      <div class="info-row"><span class="info-label">MoA</span><span class="info-value">Calicheamicin undergoes Bergman cyclization activated by intracellular glutathione (disulfide reduction), generating a 1,4-diradical that abstracts H from DNA sugar backbone → double-strand breaks → apoptosis. Cell-cycle independent.</span></div>
      <div class="info-row"><span class="info-label">IC50</span><span class="info-value">&lt;0.01 nM (sub-pM potency; requires DAR ≤2.5 to avoid systemic toxicity)</span></div>
      <div class="info-row"><span class="info-label"></span><span class="info-value">WEAK — high reactivity limits membrane diffusion; active only intracellularly after reduction</span></div>
      <div class="info-row"><span class="info-label">DLT</span><span class="info-value">Severe hepatotoxicity (VOD/SOS: veno-occlusive disease, up to 25% in early use); Bleeding; Myelosuppression. Led to Mylotarg withdrawal in 2010, re-approval 2017 with lower dose (3 mg/m²).</span></div>
      <div class="info-row"><span class="info-label"> DAR</span><span class="info-value">2.0–2.5 average (stochastic hydrazone conjugation to lysine; higher DAR intolerable)</span></div>
      <div style="font-size:10px;font-weight:700;text-transform:uppercase;letter-spacing:0.6px;color:#888;margin:10px 0 4px;border-top:1px solid #eee;padding-top:8px"></div>
      <div class="info-row"><span class="info-label"></span><span class="info-value">US4970198A — Lee et al. (Lederle Laboratories/AHP), 1990. Calicheamicin isolation, structure, and derivatives. Foundational natural product patent.</span></div>
      <div class="info-row"><span class="info-label">ADC </span><span class="info-value">US6630579B2 — Hamann et al. (Wyeth/Pfizer). AcBut hydrazone-calicheamicin conjugation method. Core Mylotarg patent.</span></div>
      <div class="info-row"><span class="info-label">Besylomab </span><span class="info-value">US7557189B2 — Ricart et al. (Pfizer/Wyeth). Anti-CD22-calicheamicin (inotuzumab ozogamicin). Besylomab clinical data.</span></div>
      <div class="info-row"><span class="info-label"></span><span class="info-value">US4970198A expired. US6630579B2 may be near expiry (~2020). Specific ADC composition patents (Mylotarg, Besylomab) remain active for product lifecycle.</span></div>
      <div class="info-row" style="font-size:11px;color:#666"><span class="info-label"></span><span class="info-value">PMID:11477157 (Mylotarg phase II AML); PMID:27880961 (re-approval 2017); PMID:27040725 (Besylomab inotuzumab ALL)</span></div>
    </div>
  </div>
</div>

<!-- PBD Dimer (DNA Damaging / Alkylator) -->
<div class="card" onclick="toggleCard(this)" data-cls="DNA Damaging Agent" data-search="pbd pyrrolobenzodiazepine pbd dimer tesirine sg3199 dna alkylator rovalpituzumab loncastuximab zynlonta">
  <div class="card-header">
    <div class="card-title">PBD Dimer (SG3199 / Tesirine)</div>
    <span class="badge badge-payload">DNA Damaging Agent</span>
  </div>
  <div class="card-body">
    <div class="cc-brief">IC50: &lt;0.001 nM（fM ）· DAR 2 · DNA  · Zynlonta（loncastuximab tesirine）</div>
    <div style="font-size:10px;color:#1a7a4a;font-weight:600;margin-top:2px">：（FDA 2021  DLBCL）</div>
    <span class="exp-toggle"></span>
    <div class="cc-detail">
      <div class="collapse-bar"><div class="collapse-progress"></div></div>
      <div class="info-row"><span class="info-label"></span><span class="info-value">DNA Damaging Agent — Pyrrolobenzodiazepine (PBD) dimer alkylator</span></div>
      <div class="info-row"><span class="info-label">MoA</span><span class="info-value">PBD dimers form sequence-selective interstrand DNA cross-links (imine bond at guanine N2), causing persistent DNA damage independent of cell cycle. Extremely potent (fM range).</span></div>
      <div class="info-row"><span class="info-label">IC50</span><span class="info-value">&lt;0.001 nM (femtomolar — most potent ADC payload class)</span></div>
      <div class="info-row"><span class="info-label"></span><span class="info-value">MODERATE — PBD dimers are membrane-permeable; some bystander effect observed in vitro</span></div>
      <div class="info-row"><span class="info-label">DLT</span><span class="info-value">Pleural effusion; Photosensitivity; Edema; Myelosuppression. High potency requires very low dose (microgram range).</span></div>
      <div class="info-row"><span class="info-label"> DAR</span><span class="info-value">2.0 (valine-alanine vc-type protease-cleavable linker; always low DAR due to extreme potency)</span></div>
      <div class="info-row"><span class="info-label"> ADC</span><span class="info-value">Loncastuximab tesirine (Zynlonta, CD19, FDA 2021 DLBCL); Rovalpituzumab tesirine (DLL3, discontinued — lung); ADCT-402 (CD19)</span></div>
      <div style="font-size:10px;font-weight:700;text-transform:uppercase;letter-spacing:0.6px;color:#888;margin:10px 0 4px;border-top:1px solid #eee;padding-top:8px"></div>
      <div class="info-row"><span class="info-label"></span><span class="info-value">US7049311B1 — Hartley et al. (Spirogen/AstraZeneca), 2006. PBD dimer conjugates for ADC. Foundational PBD ADC patent.</span></div>
      <div class="info-row"><span class="info-label">Tesirine </span><span class="info-value">US9745303B2 — Hartley et al. (ADC Therapeutics). SG3199 PBD dimer ADC payload. Covers loncastuximab tesirine chemistry.</span></div>
      <div class="info-row"><span class="info-label"></span><span class="info-value">ADC Therapeutics / AstraZeneca hold active PBD ADC patents. US9745303B2 expires ~2033. PBD chemistry requires licensing from ADC Therapeutics for commercial ADC development.</span></div>
      <div class="info-row" style="font-size:11px;color:#666"><span class="info-label"></span><span class="info-value">PMID:33602685 (Zynlonta LOTIS-2 DLBCL); PMID:25542856 (Rovalpituzumab preclinical)</span></div>
    </div>
  </div>
</div>

<!-- Lu-177 (Radionuclide) -->
<div class="card" onclick="toggleCard(this)" data-cls="Radionuclide" data-search="lu-177 lutetium-177 psma rdc radioimmunotherapy pluvicto prostate cancer dotatate">
  <div class="card-header">
    <div class="card-title">Lutetium-177 (¹⁷⁷Lu)</div>
    <span class="badge badge-phase3">Radionuclide</span>
  </div>
  <div class="card-body">
    <div class="cc-brief">β  · : 0.5–2 mm ·  · Pluvicto（Lu-177-PSMA-617）FDA 2022</div>
    <div style="font-size:10px;color:#1a7a4a;font-weight:600;margin-top:2px">：（FDA 2022 ）</div>
    <span class="exp-toggle"></span>
    <div class="cc-detail">
      <div class="collapse-bar"><div class="collapse-progress"></div></div>
      <div class="info-row"><span class="info-label"></span><span class="info-value">Radionuclide — β emitter (RDC: Radioligand Drug Conjugate)</span></div>
      <div class="info-row"><span class="info-label">MoA</span><span class="info-value">β-particle emission causes DNA double-strand breaks in targeted cells AND neighboring cells (crossfire effect). No internalization required — surface binding sufficient.</span></div>
      <div class="info-row"><span class="info-label"></span><span class="info-value">6.7 days (t½); β-max energy 0.498 MeV; tissue range 0.5–2 mm</span></div>
      <div class="info-row"><span class="info-label"></span><span class="info-value">DOTA (1,4,7,10-tetraazacyclododecane-1,4,7,10-tetraacetic acid) — stable Lu-177 chelation in vivo; DOTAGA for some variants</span></div>
      <div class="info-row"><span class="info-label"></span><span class="info-value">STRONG — β particles kill 2–5 cells beyond targeted cell; overcomes antigen heterogeneity; also active against antigen-negative bystander tumors</span></div>
      <div class="info-row"><span class="info-label"></span><span class="info-value">Pluvicto (Lu-177-PSMA-617, FDA 2022 mCRPC); Lutathera (Lu-177-DOTATATE, NET, FDA 2018); Multiple CD33/HER2 RDC programs</span></div>
      <div class="info-row"><span class="info-label">DLT</span><span class="info-value">Dry mouth (salivary gland uptake); Renal toxicity (dose-limiting); Myelosuppression (grade 3–4: ~5–10%)</span></div>
      <div style="font-size:10px;font-weight:700;text-transform:uppercase;letter-spacing:0.6px;color:#888;margin:10px 0 4px;border-top:1px solid #eee;padding-top:8px"></div>
      <div class="info-row"><span class="info-label">DOTA </span><span class="info-value">US4678667A — Meares et al. (UC Davis), 1987. DOTA metal chelation for radioimmunoconjugates. Foundational; now expired.</span></div>
      <div class="info-row"><span class="info-label">PSMA-617 </span><span class="info-value">WO2015140154A1 — Benesová et al. (DKFZ/ABX). PSMA-617 small molecule ligand structure. Licensed to Novartis (Pluvicto).</span></div>
      <div class="info-row"><span class="info-label"></span><span class="info-value">DOTA chelator expired. PSMA-617 ligand WO2015140154A1 active (~2035). Lu-177 radionuclide itself is not patentable; production process patents exist (ITG, Isotopen Technologien München).</span></div>
      <div class="info-row" style="font-size:11px;color:#666"><span class="info-label"></span><span class="info-value">PMID:35263501 (VISION trial Pluvicto NEJM 2022); PMID:29860922 (Lutathera NETTER-1)</span></div>
    </div>
  </div>
</div>

<!-- BET PROTAC / ARV-471 type (Protein Degrader) -->
<div class="card" onclick="toggleCard(this)" data-cls="Protein Degrader" data-search="protac protein degrader targeted protein degradation tpd arvinas dac-tpd arv-471 er breast cancer ubiquitin-proteasome">
  <div class="card-header">
    <div class="card-title">PROTAC-ADC Payload (DAC-TPD)</div>
    <span class="badge badge-phase1">Protein Degrader</span>
  </div>
  <div class="card-body">
    <div class="cc-brief">（PROTAC）· - ·  · DAC-TPD </div>
    <div style="font-size:10px;color:#f59e0b;font-weight:600;margin-top:2px">：（ / ）</div>
    <span class="exp-toggle"></span>
    <div class="cc-detail">
      <div class="collapse-bar"><div class="collapse-progress"></div></div>
      <div class="info-row"><span class="info-label"></span><span class="info-value">Protein Degrader — PROTAC (PROteolysis TArgeting Chimera) as ADC payload</span></div>
      <div class="info-row"><span class="info-label">MoA</span><span class="info-value">PROTAC is a bifunctional molecule: one arm binds target protein (e.g., ER, BET, BTK), the other recruits E3 ubiquitin ligase (CRBN or VHL). Ubiquitin tagging leads to proteasomal degradation of target. Catalytic — single PROTAC molecule can degrade multiple copies of target (sub-stoichiometric). Resistant to overexpression-based drug resistance.</span></div>
      <div class="info-row"><span class="info-label">ADC </span><span class="info-value">ADC delivery concentrates PROTAC in tumor cell; overcomes PROTAC poor cell permeability and PK limitations; enables tissue-selective target degradation</span></div>
      <div class="info-row"><span class="info-label"> payload</span><span class="info-value">ARV-471-type (ER degrader, Arvinas); dBET6 (BET-CRBN degrader); ARV-110 analog (BTK degrader)</span></div>
      <div class="info-row"><span class="info-label"></span><span class="info-value">DAC-TPD platform: Arvinas/Pfizer (ARV-471 as standalone ER PROTAC Phase III); ADC-PROTAC conjugates in preclinical/early Phase I. No approved DAC-PROTAC ADC as of 2026.</span></div>
      <div class="info-row"><span class="info-label">DAR</span><span class="info-value">2–4 (PROTAC molecules are large, MW ~700–1000 Da; high DAR increases aggregation risk)</span></div>
      <div class="info-row"><span class="info-label"></span><span class="info-value">POTENTIAL — released PROTAC molecules may diffuse to neighboring cells (similar to small molecule permeability)</span></div>
      <div style="font-size:10px;font-weight:700;text-transform:uppercase;letter-spacing:0.6px;color:#888;margin:10px 0 4px;border-top:1px solid #eee;padding-top:8px"></div>
      <div class="info-row"><span class="info-label">PROTAC </span><span class="info-value">US20030232737A1 — Crews et al. (Yale/Arvinas), 2003. Original PROTAC concept using E3 ligase recruitment for targeted protein degradation.</span></div>
      <div class="info-row"><span class="info-label">CRBN-PROTAC </span><span class="info-value">US9694084B2 — Ciulli et al. (Dundee/C4 Therapeutics). Cereblon-recruiting PROTAC design. Covers thalidomide-E3-recruiter warhead.</span></div>
      <div class="info-row"><span class="info-label">DAC-TPD </span><span class="info-value">WO2021202981A1 — Arvinas/Pfizer. Antibody-PROTAC conjugate (DAC-TPD) delivery concept. Emerging platform patent family (2021).</span></div>
      <div class="info-row"><span class="info-label"></span><span class="info-value">Active and rapidly expanding. PROTAC space is heavily patented (Arvinas, C4 Therapeutics, Kymera, Nurix). DAC-PROTAC ADC patents are emerging (2020–2026 filings). High FTO complexity.</span></div>
      <div class="info-row" style="font-size:11px;color:#666"><span class="info-label"></span><span class="info-value">PMID:12968521 (Sakamoto 2003 original PROTAC); PMID:34384543 (Pillow 2022 DAC-PROTAC ADC); PMID:36206765 (ARV-471 Phase I/II)</span></div>
    </div>
  </div>
</div>
<!-- ═══ END MISSING PAYLOADS ═══ -->
'''

# Insert before the closing </div> of grid
grid_end = '</div>\n<div class="tab-panel" id="panel-">'
if grid_end in content:
    content = content.replace(grid_end, missing_payloads + '\n</div>\n<div class="tab-panel" id="panel-">')
    print("Step 4: Missing payloads inserted (8 new cards)")
else:
    # Try alternative
    alt_end = 'id="panel-"'
    pos = content.find(alt_end)
    if pos > 0:
        # Insert before this panel
        prev_div = content.rfind('</div>', 0, pos)
        content = content[:prev_div+6] + '\n' + missing_payloads + '\n' + content[prev_div+6:]
        print("Step 4 (alt): Missing payloads inserted")
    else:
        print("Step 4 FAILED: could not find insertion point")

# ─────────────────────────────────────────────────────────────────
# 5. Add patent info to existing MMAE card
# ─────────────────────────────────────────────────────────────────
mmae_patent_block = '''
      <div style="font-size:10px;font-weight:700;text-transform:uppercase;letter-spacing:0.6px;color:#888;margin:10px 0 4px;border-top:1px solid #eee;padding-top:8px"></div>
      <div class="info-row"><span class="info-label"></span><span class="info-value">US6884869B2 — Doronina et al. (Seagen), 2005. Monomethyl auristatin E (MMAE) and MMAE-ADC. Foundational Seagen auristatin patent.</span></div>
      <div class="info-row"><span class="info-label">vc-PABC-MMAE</span><span class="info-value">US6214345B1 — Doronina et al. (Seagen), 2001. Val-Cit-PABC linker + MMAE. Expired ~2019; MMAE-vc platform now broadly used.</span></div>
      <div class="info-row"><span class="info-label">PEG-MMAE </span><span class="info-value">US8703714B2 — Senter et al. (Seagen). PEGylated vc-PABC-MMAE ADC for improved solubility at high DAR.</span></div>
      <div class="info-row"><span class="info-label"></span><span class="info-value">MMAE molecule patent (US6884869B2) expired ~2022. vc-PABC-MMAE chemistry broadly available. Product-specific ADC compositions (Adcetris, Padcev, Polivy) retain composition patents.</span></div>'''

# Find MMAE card evidence section and insert patent after it
mmae_pos = content.find('<div class="card-title">MMAE</div>')
if mmae_pos > 0:
    mmae_evid_pos = content.find('', mmae_pos)
    if mmae_evid_pos > 0:
        mmae_end1 = content.find('</div>', mmae_evid_pos)
        mmae_end2 = content.find('</div>', mmae_end1 + 6)
        # Find the SMILES row end 
        mmae_smiles_pos = content.find('SMILES', mmae_pos)
        if mmae_smiles_pos > 0:
            mmae_smiles_end = content.find('</div>', mmae_smiles_pos)
            mmae_smiles_end2 = content.find('</div>', mmae_smiles_end + 6)
            content = content[:mmae_smiles_end2+6] + mmae_patent_block + content[mmae_smiles_end2+6:]
            print("Step 5: MMAE patent info added")

# Save
with open(path, 'w', encoding='utf-8') as f:
    f.write(content)
print("All done. File saved.")
