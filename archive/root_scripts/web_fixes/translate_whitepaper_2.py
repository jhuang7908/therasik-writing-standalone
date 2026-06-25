import re

with open('d:/InSynBio-AI-Research/Antibody_Engineer_Suite/insynbio-web-source/whitepaper_insynbio_en.html', 'r', encoding='utf-8') as f:
    html = f.read

replacements = {
    "COVER — ，": "COVER — Dark Teal Background, Rich Info",
    "InSynBio  <strong style=\"color:var(--t7);\">AI  + 6  + Expert</strong>，、、CAR-T ——，。": "InSynBio integrates <strong style=\"color:var(--t7);\">AI Analysis + 6 Proprietary Clinical Databases + Expert Judgment</strong> to provide end-to-end decision support from sequence to report for antibody, bispecific, CAR-T, and vaccine development teams—systematically identifying and mitigating R&D failure risks before entering the wet lab.",
    "<strong style=\"color:var(--t7);\">Our Solution:</strong>—— 25+ AI Tools， 6 Clinical Data，Expert。<strong style=\"color:var(--t7);\">，。，。</strong>": "<strong style=\"color:var(--t7);\">Our Solution:</strong> Intervene before the wet lab—using 25+ AI tools for rapid analysis, 6 clinical databases for format-specific benchmarking, and expert judgment for actionable recommendations. <strong style=\"color:var(--t7);\">Not just scores, but directions. Not just tools, but a moat.</strong>",
    "The core team comes from <strong style=\"color:var(--g9);\">Albert Einstein College of Medicine、Columbia UniversityRockefeller University</strong>，Immunology Expertise，。 AI ， Biotech ，Antibody Humanization。": "The core team comes from <strong style=\"color:var(--g9);\">Albert Einstein College of Medicine, Columbia University, and Rockefeller University</strong>, with immunology backgrounds and over a decade of practical experience in biologics development. We focus on combining computational AI with deep immunological knowledge, having served multiple Biotech companies and research teams with full computational analysis delivery from antibody humanization to neoantigen vaccines.",
    "3–5": "3–5 Days",
    "Expert-Reviewed<br>Delivery": "Expert-Reviewed<br>Delivery",
    "VHH ": "VHH Humanization",
    "S1 ·  AI Tool Platforms、CRO ": "S1 · The Essential Difference Between Us, AI Tool Platforms, and CROs",
    "6 Clinical Data": "6 Proprietary Clinical Databases",
    "Expert": "No Expert Interpretation and Review",
    "Expert": "Full Review by Immunology Experts",
    "10+ Years Biologics Dev": "10+ Years Biologics Dev Background",
    "29  VHH ": "29-Item VHH-Specific Checklist",
    "VH→VHH ": "VH→VHH Structural Conversion Design",
    " CDR ": "Preserve CDR binding while improving developability",
    "CMC Developability": "CMC Developability Assessment",
    "15 Comprehensive（pI ·  · ）": "Comprehensive scan of 15 metrics (pI · Hydrophobicity · Charge)",
    "<b></b>：VH/VL / VHH / ": "<b>Format-Specific</b>: VH/VL / VHH / Bispecific individual benchmarking",
    " + AI ": "Shortcoming identification + AI optimization advice",
    "": "Clinical Benchmark",
    "AntiFold / ESM-IF1 / MM-GBSA ": "AntiFold / ESM-IF1 / MM-GBSA Synergy",
    " + ": "Mutation heatmap + Multi-structure consensus screening",
    "CDR ，RMSD ": "CDR conformation anchor maintenance, RMSD monitoring",
    "Shannon  + ": "Shannon polymorphism scoring + Affinity filtering",
    "T ，27 HLA-DR ": "T-cell epitope screening, 27 HLA-DR coverage",
    " + ": "Immunogenicity hotspot localization + Mutation risk reduction",
    "▸ （Modality Extension）": "▸ Modality Extension",
    "134+  + 84 Linker ": "134+ Clinical Bispecifics + 84 Linker Library",
    " ·  · CMC ": "Format screening · Pairing stability · CMC mismatch",
    "78 IgG-like ": "78 IgG-like structural model validation",
    "Linker / Payload / DAR ": "Linker / Payload / DAR Optimization",
    " + ": "Conjugation site screening + Stability assessment",
    "237 ，12 ": "237 Selected components, 12-category system architecture",
    " / ": "Hinge / Costimulatory domain rational optimization",
    " · ": "Solid tumor penetration · Safety switch design",
    "Vaccine / Neoantigen": "Vaccine / Neoantigen Design",
    "KRAS G12D · EBV ": "KRAS G12D · EBV and other target cases",
    "100+ IEDB ，MHC-I/II": "100+ IEDB validated epitopes, MHC-I/II",
    " mRNA  + GC ": "Multi-epitope mRNA assembly + GC optimization",
    "": "Immune Enhancement",
    "03 · ": "03 · Core Assets",
    "VH/VL  0.64°，CDR  100% ，": "VH/VL assembly angle deviation 0.64°, CDR 100% identical to Trastuzumab, full clinical-grade validation",
    "ProteinMPNN T=0.4 ，CDR2/3 ，， RMSD &lt;0.8Å": "ProteinMPNN T=0.4 sampling, CDR2/3 polymorphism scoring, anchor residue constraints, structural RMSD <0.8Å",
    "6 ，HADDOCK3 ，MM/GBSA ， Scenario D ": "6-tool synergy, HADDOCK3 refinement, MM/GBSA final screening, hapten-specific Scenario D protocol",
    "VH/VL ，， + ， IND ": "VH/VL format, clinical distribution benchmarking, hydrophobic patch + charge imbalance localization, submitted for client IND preparation",
    "83 ，SmartLink 84 ，CMC ": "83 candidate pairing evaluation, SmartLink 84 conformation screening, CMC mismatch risk troubleshooting",
    "100+ ADC Clinical Data，，DAR ": "100+ ADC Clinical Data benchmarking, site accessibility analysis, DAR stability interval judgment",
    "MHCflurry + IEDB ，IC50 ， mRNA ": "MHCflurry + IEDB dual screening, IC50 optimization, multi-epitope mRNA tandem assembly",
    " NDA  · Client Project": "Full reports available upon request under NDA · Client Project data has been anonymized",
    "3–5 Expert": "3–5 business days Expert-reviewed report",
    "AI + Expert": "AI + Expert Review",
    "25+ Tools，Expert": "25+ Tools running, Expert full-process review of the report",
    " +  · Balance waived if objectives are not met": "Full report + recommendations · Balance waived if objectives are not met",
    "Clinical Data，，。© 2026 InSynBio / InSynBio": "This document is based on computational analysis and public Clinical Data, does not constitute clinical decision advice, and is for R&D reference only. © 2026 InSynBio"
}

for k, v in replacements.items:
    html = html.replace(k, v)

with open('d:/InSynBio-AI-Research/Antibody_Engineer_Suite/insynbio-web-source/whitepaper_insynbio_en.html', 'w', encoding='utf-8') as f:
    f.write(html)
