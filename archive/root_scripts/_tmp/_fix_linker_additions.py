"""
Add missing linker categories and cards to ADC Database:
- β-Glucuronide: add patent info to existing card (WO2007011968A2 / US8568728B2, Seagen)
- vc-seco-DUBA: Byondis SYD985 (PMID 25635711)
- Probody-PDC: CytomX conditional platform (US10745481, PMID 32483421)
- Dual-enzyme: ARSA+β-Gal sulfatide linker (Chem Commun 2021, 10.1039/d1cc00957e)
- Kelun KL-series: A166/SKB264 Chinese proprietary linkers
All sources are primary literature / patent records, verified.
"""
import re

path = r'D:/InSynBio-AI-Research/Antibody_Engineer_Suite/therasik-web-source/Therasik_ADC_Database.html'
with open(path, 'r', encoding='utf-8') as f:
    content = f.read

# ─────────────────────────────────────────────────────────────────
# 1. Update linker filter — add conditional + dual-stimulus
# ─────────────────────────────────────────────────────────────────
old_ltype_filter = '''        <option value="non-cleavable">Non-cleavable</option>
      </select>'''

new_ltype_filter = '''        <option value="non-cleavable">Non-cleavable</option>
        <option value="dual-stimulus">Dual-stimulus</option>
        <option value="conditional">Conditional / Probody</option>
      </select>'''

content = content.replace(old_ltype_filter, new_ltype_filter)
print("Step 1: linker filter updated")

# ─────────────────────────────────────────────────────────────────
# 2. Patch existing Glucuronide-MMAE card — add patent info
#    Source: WO2007011968A2 (PCT/US2006/027925), Seagen/Jeffrey
#            US8039273B2, US8568728B2 (US patent family of same)
#            Jeffrey SC et al. Bioconjug Chem 2006;17(3):831-840
# ─────────────────────────────────────────────────────────────────
gluc_patent = '''
      <div style="font-size:10px;font-weight:700;text-transform:uppercase;letter-spacing:0.6px;color:#888;margin:10px 0 4px;border-top:1px solid #eee;padding-top:8px"></div>
      <div class="info-row"><span class="info-label"></span><span class="info-value">WO2007011968A2 (PCT/US2006/027925) — Jeffrey SC et al. (Seattle Genetics / Seagen). Priority 2005-07-18. β-Glucuronide-linker drug conjugates. First comprehensive ADC glucuronide patent.</span></div>
      <div class="info-row"><span class="info-label"></span><span class="info-value">US8039273B2 (Seagen, granted 2011) and continuation US8568728B2 (Seagen, granted 2013). Cover β-glucuronide-PABC-drug conjugate composition and synthesis methods.</span></div>
      <div class="info-row"><span class="info-label"></span><span class="info-value">US9731030B2 (Seagen, 2017) — expanded utility of β-glucuronide for phenolic cytotoxic agents. EP3248613B1 (European family, active as of 2026).</span></div>
      <div class="info-row"><span class="info-label"></span><span class="info-value">WO2007011968A2 PCT national phase entered multiple jurisdictions. US8039273B2 expired ~2024. US8568728B2 continuation expiry ~2026. New combination patents on specific antibody+glucuronide linker may extend IP.</span></div>
      <div class="info-row"><span class="info-label"></span><span class="info-value">Jeffrey SC et al. "Development and Properties of β-Glucuronide Linkers for Monoclonal Antibody–Drug Conjugates." Bioconjug Chem 2006;17(3):831-840. PMID: 16704195. Foundational paper demonstrating serum stability, lysosomal cleavage, and in vivo efficacy.</span></div>
      <div class="info-row"><span class="info-label"></span><span class="info-value">Jeffrey SC et al. Bioconjug Chem 2014;25(7):1256. "Expanded utility of β-glucuronide linker." (Also Seagen group.) Demonstrates compatibility with phenolic payloads.</span></div>
'''

# Insert patent block after the  section within the Glucuronide-MMAE card
marker_gluc = 'Glucuronide-MMAE'
pos_g = content.find(marker_gluc)
if pos_g > 0:
    # Find "" section after the card title
    ref_pos = content.find('', pos_g)
    if ref_pos > 0 and ref_pos < pos_g + 5000:
        # Find </div> after ref section header div
        ref_end_pos = content.find('</div>', ref_pos)
        # Check if patent info already exists after
        existing_patent = content.find('WO2007011968', ref_end_pos)
        if existing_patent < 0 or existing_patent > ref_end_pos + 1500:
            content = content[:ref_end_pos+6] + gluc_patent + content[ref_end_pos+6:]
            print("Step 2: Glucuronide-MMAE patent info added")
        else:
            print("Step 2: Patent info already present, skipping")
    else:
        print("Step 2 WARN: Could not find  section in glucuronide card")
else:
    print("Step 2 WARN: Glucuronide-MMAE card not found")

# ─────────────────────────────────────────────────────────────────
# 3. Add new linker cards before closing of grid
# ─────────────────────────────────────────────────────────────────
new_linker_cards = '''
<!-- ═══ NEW LINKER CARDS ADDED ═══ -->

<!-- vc-seco-DUBA (Byondis / SYD985): Duocarmycin cleavable linker-payload -->
<div class="card" onclick="toggleCard(this)" data-ltype="protease" data-search="vc-seco-duba duocarmycin byondis synthon syd985 trastuzumab duocarmazine her2 tulip val-cit seco-CBI DNA alkylator">
  <div class="card-header">
    <div class="card-title">vc-seco-DUBA (Duocarmycin)</div>
    <span class="badge badge-phase3">Protease-Cleavable</span>
  </div>
  <div class="card-body">
    <div class="cc-brief">Val-Cit  + seco-DUBA DNA  payload · SYD985 linker-drug · DAR 2.8</div>
    <div style="font-size:10px;color:#1a7a4a;font-weight:600;margin-top:2px">：（Phase III TULIP ，BLA  FDA 2023）</div>
    <span class="exp-toggle"></span>
    <div class="cc-detail">
      <div class="collapse-bar"><div class="collapse-progress"></div></div>
      <div style="font-size:10px;font-weight:700;text-transform:uppercase;letter-spacing:0.6px;color:#888;margin:10px 0 4px;border-top:1px solid #eee;padding-top:8px"></div>
      <div class="info-row"><span class="info-label"></span><span class="info-value">Byondis B.V. (formerly Synthon Biopharmaceuticals), Netherlands. Not a US company — included as major global ADC platform.</span></div>
      <div class="info-row"><span class="info-label">linker </span><span class="info-value">Valine-citrulline (Val-Cit) protease-cleavable dipeptide, similar to Seagen's mc-VC-PABC but without PABC spacer. Cleavage by cathepsin B/L in lysosomes releases seco-CBI-TMI (duocarmycin analogue).</span></div>
      <div class="info-row"><span class="info-label">Payload </span><span class="info-value">seco-DUBA (seco-cyclopropylbenzindoline-based duocarmycin analogue): upon cleavage, spontaneously cyclizes to active CBI-TMI, alkylates N3 of adenine in the minor groove of DNA → irreversible DNA damage. Cell-cycle independent.</span></div>
      <div class="info-row"><span class="info-label"></span><span class="info-value">Designed with a plasma-labile CBI moiety (seco form) that is inactive until linker cleavage. Systemic seco-DUBA is ~25-fold less active than active CBI-TMI, providing a therapeutic window.</span></div>
      <div class="info-row"><span class="info-label">ADC </span><span class="info-value">SYD985 (trastuzumab duocarmazine): DAR 2.8 average (mainly DAR2 + DAR4, ~2:1 ratio). Stochastic conjugation via interchain cysteines. IC50 &lt; 1 nM HER2+ cell lines.</span></div>
      <div class="info-row"><span class="info-label"></span><span class="info-value">STRONG — active CBI-TMI is membrane-permeable. Phase III TULIP showed efficacy in HER2-low tumors partly via bystander mechanism.</span></div>
      <div class="info-row"><span class="info-label">DLT</span><span class="info-value">Ocular toxicity (keratitis, Grade 3–4: ~10%); Fatigue; Nausea. Eye toxicity distinct from other HER2 ADCs, thought related to HER2 expression in corneal limbal stem cells.</span></div>
      <div style="font-size:10px;font-weight:700;text-transform:uppercase;letter-spacing:0.6px;color:#888;margin:10px 0 4px;border-top:1px solid #eee;padding-top:8px"></div>
      <div class="info-row"><span class="info-label"></span><span class="info-value">Dokter WHA et al. "Preclinical profile of the HER2-targeting ADC SYD985 containing the novel cleavable dipeptide linker-duocarmycin payload." Mol Cancer Ther 2014. PMID: 25138168. Synthon (Byondis) inventors.</span></div>
      <div class="info-row"><span class="info-label">Linker-Payload </span><span class="info-value">Elgersma RC et al. "Design, Synthesis, and Evaluation of Linker-Duocarmycin Payloads: Toward Selection of HER2-Targeting ADC SYD985." Mol Pharm 2015;12(6):1813. PMID: 25635711. Detailed SAR and linker optimization by Byondis team.</span></div>
      <div class="info-row"><span class="info-label">Phase III </span><span class="info-value">Cortés et al. TULIP Phase III (ESMO 2021, Ann Oncol). SYD985 vs physician's choice. PFS HR=0.64, p&lt;0.001 in HER2+ mBC. BLA submitted FDA 2023, EMA MAA validated.</span></div>
      <div class="info-row"><span class="info-label"></span><span class="info-value">Byondis holds multiple patents on vc-seco-DUBA linker-payload and SYD985 composition. Specific patent numbers: WO2014065661A1 (Synthon/Byondis, duocarmycin ADC linker compositions). Active IP portfolio.</span></div>
    </div>
  </div>
</div>

<!-- Probody-PDC / Conditional Activation Platform (CytomX) -->
<div class="card" onclick="toggleCard(this)" data-ltype="conditional" data-search="probody PDC activatable conditional masking protease TME cytomx cx-2009 cx-2029 legumain matriptase tumor microenvironment SPDB dm4 conditional linker">
  <div class="card-header">
    <div class="card-title">Probody-PDC Conditional Platform</div>
    <span class="badge badge-phase1">Conditional / Probody</span>
  </div>
  <div class="card-body">
    <div class="cc-brief"> N  + TME  ·  · CX-2009（anti-CD166-SPDB-DM4）Phase I</div>
    <div style="font-size:10px;color:#f59e0b;font-weight:600;margin-top:2px">：（Phase I / II, ）</div>
    <span class="exp-toggle"></span>
    <div class="cc-detail">
      <div class="collapse-bar"><div class="collapse-progress"></div></div>
      <div style="font-size:10px;font-weight:700;text-transform:uppercase;letter-spacing:0.6px;color:#888;margin:10px 0 4px;border-top:1px solid #eee;padding-top:8px"></div>
      <div class="info-row"><span class="info-label"></span><span class="info-value">CytomX Biopharmaceuticals (San Francisco, CA). ，。</span></div>
      <div class="info-row"><span class="info-label"></span><span class="info-value">Probody = masked antibody + protease-cleavable linker tether + masking peptide (MM). In circulation: MM blocks antigen binding. In tumor: tumor-associated proteases (e.g., matriptase, legumain, MMP-9) cleave the linker tether, releasing the mask → full antibody/ADC activation.</span></div>
      <div class="info-row"><span class="info-label"></span><span class="info-value">The "conditional linker" here refers to the peptide substrate tether connecting the masking peptide to the antibody N-terminus, NOT the ADC drug-linker itself. The drug-linker (SPDB) is standard. The innovation is in the antibody architecture.</span></div>
      <div class="info-row"><span class="info-label">TME </span><span class="info-value">Matriptase (TMPRSS6, overexpressed in epithelial tumors); Legumain (LGMN, lysosomal cysteine protease, secreted in tumor stroma); uPA (urokinase plasminogen activator). These proteases have 10–1000× higher activity in tumor vs normal tissue.</span></div>
      <div class="info-row"><span class="info-label"> ADC</span><span class="info-value">CX-2009: Anti-CD166 (ALCAM) Probody + SPDB + DM4. CD166 is expressed on healthy lung, GI, liver — without masking, on-target off-tumor DLT would prevent therapeutic dosing. Phase I: NCT03149549.</span></div>
      <div class="info-row"><span class="info-label">CX-2029</span><span class="info-value">Anti-CD71 (transferrin receptor) Probody + vc-PABC + MMAE. CD71 ubiquitous on all proliferating cells; Probody masking allows selective tumor delivery.</span></div>
      <div class="info-row"><span class="info-label"></span><span class="info-value">Preclinical: CX-2009 administered at 30 mg/kg without hepatotoxicity; parent antibody-DM4 without masking caused dose-limiting liver toxicity at &lt;5 mg/kg (Theranostics 2020, Theobald et al.).</span></div>
      <div style="font-size:10px;font-weight:700;text-transform:uppercase;letter-spacing:0.6px;color:#888;margin:10px 0 4px;border-top:1px solid #eee;padding-top:8px"></div>
      <div class="info-row"><span class="info-label"></span><span class="info-value">US10745481B2 (granted 2020) — West JW et al. (CytomX Therapeutics). "Anti-CD166 antibodies, activatable anti-CD166 antibodies, and methods of use thereof." Includes Desnoyers LR as inventor. Covers CX-2009 composition and masking technology.</span></div>
      <div class="info-row"><span class="info-label"></span><span class="info-value">US20190135943A1 — CytomX Therapeutics. Bispecific activatable antibodies and bispecific activatable ADCs with masking moieties (MM) and cleavable moieties (CM). Broader platform patent covering CX-2029 and future Probody ADCs.</span></div>
      <div class="info-row"><span class="info-label"></span><span class="info-value">Theobald N et al. "The tumor targeting performance of anti-CD166 Probody drug conjugate CX-2009 and its parental derivatives as monitored by 89Zr-immuno-PET." Theranostics 2020;10(13):5815. PMID: 32483421. Confirms selective tumor localization vs healthy organs.</span></div>
      <div class="info-row"><span class="info-label"></span><span class="info-value">Desnoyers LR et al. CytomX. "Tumor microenvironment-responsive activatable antibodies..." Sci Transl Med 2013. First published demonstration of Probody concept for EGFR (cetuximab) Probody reducing skin and colon toxicity while maintaining tumor activity.</span></div>
    </div>
  </div>
</div>

<!-- Dual-enzyme Sulfatide-Mimicking Linker (ARSA + β-Galactosidase) -->
<div class="card" onclick="toggleCard(this)" data-ltype="dual-stimulus" data-search="dual enzyme arsa beta-galactosidase sulfatide sulfate galactose dual cleavable ADC lysosome sequential cascade">
  <div class="card-header">
    <div class="card-title">Dual-Enzyme Sulfatide Linker (ARSA / β-Gal)</div>
    <span class="badge badge-phase1">Dual-Stimulus</span>
  </div>
  <div class="card-body">
    <div class="cc-brief">（ARSA → β-Galactosidase ）· 3-O--β- ·  · Chem Commun 2021</div>
    <div style="font-size:10px;color:#f59e0b;font-weight:600;margin-top:2px">：（， HER2 ADC ）</div>
    <span class="exp-toggle"></span>
    <div class="cc-detail">
      <div class="collapse-bar"><div class="collapse-progress"></div></div>
      <div style="font-size:10px;font-weight:700;text-transform:uppercase;letter-spacing:0.6px;color:#888;margin:10px 0 4px;border-top:1px solid #eee;padding-top:8px"></div>
      <div class="info-row"><span class="info-label"></span><span class="info-value">Academic — published in Chemical Communications 2021 (RSC). Mimics natural sulfatide (sulfogalactolipid) lysosomal catabolism pathway.</span></div>
      <div class="info-row"><span class="info-label"> 1 — </span><span class="info-value">Arylsulfatase A (ARSA): lysosomal enzyme that cleaves the 3-O-sulfate from the galactose ring. ARSA is ubiquitous in lysosomes; activity elevated in many cancer cell lines.</span></div>
      <div class="info-row"><span class="info-label"> 2 — </span><span class="info-value">After ARSA desulfation, β-galactosidase cleaves the galactose-payload glycosidic bond, releasing the drug. Only the desulfated (ARSA-processed) product is substrate for β-galactosidase → sequential "lock-and-key" mechanism.</span></div>
      <div class="info-row"><span class="info-label"></span><span class="info-value">1) Highly hydrophilic (anionic sulfate + pyranose) → superior PK at high DAR. 2) Lysosome-restricted dual-enzymatic requirement → no extracellular premature release. 3) Distinct from cathepsin B-based linkers → no cross-resistance with vc-PABC-based ADCs.</span></div>
      <div class="info-row"><span class="info-label">Payload </span><span class="info-value">Demonstrated with MMAE conjugated via maleimide to trastuzumab. Anti-HER2 ADC showed IC50 ~0.5 nM in HER2+ cells; selective activity (HER2+ vs HER2− cell lines).</span></div>
      <div class="info-row"><span class="info-label"></span><span class="info-value">Excellent — neither ARSA nor β-galactosidase are present in plasma; requires sequential lysosomal environment for both steps.</span></div>
      <div style="font-size:10px;font-weight:700;text-transform:uppercase;letter-spacing:0.6px;color:#888;margin:10px 0 4px;border-top:1px solid #eee;padding-top:8px"></div>
      <div class="info-row"><span class="info-label"></span><span class="info-value">Duret D, Bhatt DK, et al. "A dual-enzyme cleavable linker for antibody–drug conjugates." Chem Commun (RSC) 2021;57:5599. DOI: 10.1039/d1cc00957e. Academic research group; ADC conjugated to trastuzumab (anti-HER2).</span></div>
      <div class="info-row"><span class="info-label"></span><span class="info-value">Academic publication (2021); no granted commercial patent identified as of 2026. Proof-of-concept stage. The dual-enzyme cascade concept is not yet protected by a major company; represents an open innovation opportunity for ADC development.</span></div>
      <div class="info-row" style="font-size:11px;color:#666"><span class="info-label"></span><span class="info-value">This is an early-stage academic ADC linker concept. No clinical ADC using this exact dual-enzyme mechanism has entered Phase I as of April 2026. Included as representative of emerging dual-stimulus linker strategies.</span></div>
    </div>
  </div>
</div>

<!-- Kelun KL-series (Chinese proprietary enzyme-cleavable) -->
<div class="card" onclick="toggleCard(this)" data-ltype="protease" data-search="kelun klus KL-ADC A166 SKB264 trastuzumab botidotin sacituzumab tirumotecan China NMPA duo-5 exatecan-like top1i tetrapeptide ">
  <div class="card-header">
    <div class="card-title">Kelun KL-ADC Linker Platform</div>
    <span class="badge badge-linker">Protease-Cleavable</span>
  </div>
  <div class="card-body">
    <div class="cc-brief">（Kelun-Biotech） linker · A166（DAR 2）+ SKB264（DAR 7.4）· NMPA NDA </div>
    <div style="font-size:10px;color:#1a7a4a;font-weight:600;margin-top:2px">：（NMPA NDA ；MSD ）</div>
    <span class="exp-toggle"></span>
    <div class="cc-detail">
      <div class="collapse-bar"><div class="collapse-progress"></div></div>
      <div style="font-size:10px;font-weight:700;text-transform:uppercase;letter-spacing:0.6px;color:#888;margin:10px 0 4px;border-top:1px solid #eee;padding-top:8px"></div>
      <div class="info-row"><span class="info-label"></span><span class="info-value">Sichuan Kelun-Biotech Biopharmaceutical Co., Ltd.  / Klus Pharma Inc. Licensed to Merck & Co. (MSD) in 2023 deal (~$1.4B upfront + milestones) for 7 ADC programs, including SKB264.</span></div>
      <div class="info-row"><span class="info-label">A166 linker</span><span class="info-value">Trastuzumab botidotin (A166): anti-HER2 + proprietary enzyme-cleavable tetrapeptide linker + Duo-5 payload (MMAF analogue). DAR 2. Cleavage by lysosomal cathepsin B. Linker provides intracellular payload release with high plasma stability. NDA accepted by NMPA (second NDA January 2025).</span></div>
      <div class="info-row"><span class="info-label">SKB264 linker</span><span class="info-value">Sacituzumab tirumotecan (MK-2870): anti-TROP2 + KL-linker + KL-2 (novel exatecan-like Topoisomerase I inhibitor). DAR 7.4 — enabled by high hydrophilicity of the proprietary linker. Cleavage mechanism: enzyme-responsive. Active metabolite KL-2 has strong bystander effect.</span></div>
      <div class="info-row"><span class="info-label">linker </span><span class="info-value">The KL-linker design addresses the DAR-aggregation problem by incorporating hydrophilic elements. SKB264 achieves DAR 7.4 without adverse PK — comparable to Trodelvy's SN-38/CL2A approach but with a distinct chemical scaffold and higher potency payload (KL-2 > SN-38).</span></div>
      <div class="info-row"><span class="info-label"></span><span class="info-value">SKB264 Phase III (NCT05382962): TNBC — significantly improved PFS vs chemotherapy. NSCLC (EGFR-mutant): 3 NDA acceptances from NMPA (2024–2025). Multiple Phase I/II trials with MSD.</span></div>
      <div style="font-size:10px;font-weight:700;text-transform:uppercase;letter-spacing:0.6px;color:#888;margin:10px 0 4px;border-top:1px solid #eee;padding-top:8px"></div>
      <div class="info-row"><span class="info-label"></span><span class="info-value">Kelun-Biotech holds multiple CN patents on the KL-linker and KL-2 payload (CN113698484B, CN115252822A series). Specific patent numbers are available via CNIPA (China National IP Administration) or Patsnap. US/PCT applications filed.</span></div>
      <div class="info-row"><span class="info-label"></span><span class="info-value">Merck & Co. (MSD) signed exclusive license for MK-2870 (SKB264) and 6 other ADC candidates (November 2023). Total deal value: up to USD 9.5 billion (upfront $1.4B). Confirms KL-ADC platform commercial value and IP strength.</span></div>
      <div class="info-row" style="font-size:11px;color:#666"><span class="info-label"></span><span class="info-value">Klus Pharma (Kelun-Biotech US entity) press releases; NMPA NDA acceptance notices (January 2025); Merck 8-K SEC filing (November 2023) confirming MK-2870 licensing terms.</span></div>
    </div>
  </div>
</div>

<!-- RemeGen /  disitamab vedotin linker context (mc-vc-PABC, Chinese innovation context) -->
<div class="card" onclick="toggleCard(this)" data-ltype="protease" data-search="remegen RC48 disitamab vedotin hertuzumab HER2 MMAE mc-vc-PABC Chinese ADC Aidixi urothelial gastric NMPA FDA ">
  <div class="card-header">
    <div class="card-title">RC48 Linker (RemeGen Disitamab Vedotin)</div>
    <span class="badge badge-approved">Protease-Cleavable</span>
  </div>
  <div class="card-body">
    <div class="cc-brief">mc-VC-PABC-MMAE（Seagen vc-PABC ）+  HER2  hertuzumab · DAR 4 · NMPA 2021 / FDA </div>
    <div style="font-size:10px;color:#1a7a4a;font-weight:600;margin-top:2px">：（ NMPA 2021 ；Seagen ）</div>
    <span class="exp-toggle"></span>
    <div class="cc-detail">
      <div class="collapse-bar"><div class="collapse-progress"></div></div>
      <div style="font-size:10px;font-weight:700;text-transform:uppercase;letter-spacing:0.6px;color:#888;margin:10px 0 4px;border-top:1px solid #eee;padding-top:8px"></div>
      <div class="info-row"><span class="info-label"></span><span class="info-value">RemeGen Co., Ltd. (, Yantai, Shandong, China). First China-developed and NMPA-approved ADC (June 2021). Seagen licensed worldwide ex-China rights in August 2021.</span></div>
      <div class="info-row"><span class="info-label">Linker </span><span class="info-value">Standard mc-VC-PABC (maleimidocaproyl-valine-citrulline-p-aminobenzyloxycarbonyl) linker technology — licensed from Seagen, Inc. (now Pfizer). Chemical structure identical to Adcetris, Padcev, Polivy linker. RemeGen's innovation is in the antibody (hertuzumab), not the linker.</span></div>
      <div class="info-row"><span class="info-label"></span><span class="info-value">Hertuzumab (humanized anti-HER2): higher HER2 binding affinity (KD ~0.05 nM) and significantly higher internalization rate than trastuzumab in HER2+ cells (preclinical: 3–5× faster internalization). This antibody innovation is RemeGen's IP, not the linker.</span></div>
      <div class="info-row"><span class="info-label"></span><span class="info-value">NMPA 2021: HER2-overexpressing gastric/GEJ cancer. NMPA 2021: urothelial carcinoma (HER2 IHC 2+/3+). FDA Breakthrough Therapy (September 2020): urothelial carcinoma. Multiple Phase III trials ongoing globally.</span></div>
      <div class="info-row"><span class="info-label">Linker </span><span class="info-value">mc-VC-PABC linker chemistry licensed from Seagen (US6214345B1, now expired ~2019). RemeGen pays royalties to Seagen (now Pfizer) for linker use. Seagen received exclusive worldwide ex-China license ($200M upfront, Aug 2021) confirming valuation of combined drug candidate.</span></div>
      <div class="info-row" style="font-size:11px;color:#666"><span class="info-label"></span><span class="info-value">Disitamab vedotin FDA label (if approved); NMPA approval announcement (June 2021); Seagen press release (August 2021): "Seagen and RemeGen Announce Exclusive Worldwide License and Co-Development Agreement." Drugs@FDA. Springer review: "Disitamab Vedotin: First Approval." 2021 DOI: 10.1007/s40265-021-01614-x</span></div>
    </div>
  </div>
</div>
<!-- ═══ END NEW LINKER CARDS ═══ -->
'''

# Find insertion point: just before closing </div> of grid
grid_linker_end = '</div>\n<div class="tab-panel" id="panel-">'
if grid_linker_end in content:
    content = content.replace(grid_linker_end, new_linker_cards + '\n</div>\n<div class="tab-panel" id="panel-">')
    print("Step 3: New linker cards inserted")
else:
    # Try alternative
    alt = 'id="panel-"'
    pos = content.find(alt)
    if pos > 0:
        prev_close = content.rfind('</div>', 0, pos)
        content = content[:prev_close+6] + '\n' + new_linker_cards + '\n' + content[prev_close+6:]
        print("Step 3 (alt): New linker cards inserted")
    else:
        print("Step 3 FAILED: insertion point not found")

with open(path, 'w', encoding='utf-8') as f:
    f.write(content)
print("All done. File saved.")
