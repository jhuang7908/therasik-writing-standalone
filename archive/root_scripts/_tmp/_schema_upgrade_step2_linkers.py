"""
Step 2: Enrich all 22 linkers with critical missing fields.
Fields: plasma_t12, cleavage_enzyme, tumor_cleavage_efficiency,
        compatible_payload_chemistry, compatible_conjugation_sites,
        hydrophilicity_note, optimal_dar_range_note
"""
import json, pathlib

fp = pathlib.Path('data/adc_atlas/adc_components.json')
comp = json.loads(fp.read_text())

linker_enrichment = {
    "mc-val-cit-PABC": {
        "data_confidence": "high",
        "plasma_t12": ">7 days (very stable in human plasma)",
        "cleavage_enzyme": "Cathepsin B (lysosomal cysteine protease; highly expressed in tumor cells)",
        "tumor_cleavage_efficiency": "High — Cathepsin B upregulated 2–5× in solid tumors vs normal tissue",
        "compatible_payload_chemistry": "Free amine required on payload (PABC spacer self-immolates to release NH₂-payload after Cathepsin B cleavage)",
        "compatible_conjugation_sites": ["Cysteine (maleimide)", "Lysine (NHS ester variant)"],
        "hydrophilicity_note": "Moderately hydrophobic (causes aggregation at high DAR >4 without PEGylation); PEG2/PEG4 variants significantly improve solubility",
        "optimal_dar_range_note": "DAR 3–4 optimal for MMAE; high-DAR variants require PEG spacers",
        "key_refs": ["PMID:12873544", "FDA label: Adcetris, Polivy, Padcev"],
        "needs_expert_review": False
    },
    "GGFG": {
        "data_confidence": "high",
        "plasma_t12": ">7 days (highly stable in human plasma; lysosomal-only cleavage)",
        "cleavage_enzyme": "Lysosomal cathepsins (B, L, S) — requires complete ADC internalization and lysosomal trafficking",
        "tumor_cleavage_efficiency": "High — requires full lysosomal delivery; no extracellular cleavage",
        "compatible_payload_chemistry": "Direct DXd release (no self-immolative group); DXd is released as active free drug after amide bond hydrolysis",
        "compatible_conjugation_sites": ["Cysteine (maleimide)", "Site-specific (Daiichi Sankyo proprietary)"],
        "hydrophilicity_note": "Relatively hydrophilic due to GGFG peptide; supports DAR 7–8 without aggregation (key advantage for high-DAR DXd ADCs)",
        "optimal_dar_range_note": "Designed for DAR 7–8; supports High-DAR strategy of Daiichi Sankyo platform",
        "key_refs": ["PMID:26058450", "FDA label: Enhertu, Dato-DXd"],
        "needs_expert_review": False
    },
    "Sulfo-SMCC": {
        "data_confidence": "high",
        "plasma_t12": ">10 days (non-cleavable thioether; no enzymatic degradation)",
        "cleavage_enzyme": "None — non-cleavable. Requires complete lysosomal proteolysis of antibody backbone to release Lys-SMCC-payload adduct",
        "tumor_cleavage_efficiency": "N/A — payload release driven by antibody catabolism rate (t1/2 ~7–21 days)",
        "compatible_payload_chemistry": "Thiol group required on payload (maleimide-thiol reaction); or amine group with NHS variant",
        "compatible_conjugation_sites": ["Lysine (NHS-SMCC)", "Cysteine (Sulfo-SMCC)"],
        "hydrophilicity_note": "Hydrophobic thioether linker; constrains DAR to 3–4 (DAR >4 causes rapid clearance by increased hydrophobicity)",
        "optimal_dar_range_note": "DAR 3.5 is the clinical standard for T-DM1/Kadcyla",
        "key_refs": ["PMID:16814772 (T-DM1 design)", "FDA label: Kadcyla"],
        "needs_expert_review": False
    },
    "Glucuronide-MMAE": {
        "data_confidence": "high",
        "plasma_t12": ">7 days (beta-glucuronidase not present in blood)",
        "cleavage_enzyme": "β-Glucuronidase (lysosomal UGP; also secreted extracellularly in necrotic tumor regions)",
        "tumor_cleavage_efficiency": "High in lysosome; also effective in tumor stroma (extracellular β-glucuronidase from necrotic cells promotes bystander killing)",
        "compatible_payload_chemistry": "Free hydroxyl or amine on payload; typically MMAE or other amine-bearing payloads",
        "compatible_conjugation_sites": ["Cysteine (maleimide)", "Site-specific variants"],
        "hydrophilicity_note": "Highly hydrophilic (glucuronic acid moiety); allows DAR 6–8 without significant aggregation. Superior PK compared to vc-PABC at same DAR.",
        "optimal_dar_range_note": "DAR 6–8 feasible due to high hydrophilicity",
        "key_refs": ["PMID:16955513 (beta-glucuronide linker)", "PMID:21478267"],
        "needs_expert_review": False
    },
    "VA-PABC": {
        "data_confidence": "high",
        "plasma_t12": ">7 days (similar stability to vc-PABC)",
        "cleavage_enzyme": "Cathepsin B (slightly faster cleavage kinetics than Val-Cit for some substrates)",
        "tumor_cleavage_efficiency": "High — comparable to vc-PABC",
        "compatible_payload_chemistry": "Free amine required (PABC self-immolative spacer)",
        "compatible_conjugation_sites": ["Cysteine (maleimide)", "Site-specific"],
        "hydrophilicity_note": "More hydrophilic than vc-PABC (Ala vs Cit); reduces ADC aggregation. Preferred for highly hydrophobic payloads like PBDs and indolinobenzazepines.",
        "optimal_dar_range_note": "DAR 4 standard; supports slightly higher DAR than vc-PABC due to improved hydrophilicity",
        "key_refs": ["PMID:26700026 (Val-Ala design)", "FDA label: Zynlonta (loncastuximab tesirine uses SG3249 VA linker)"],
        "needs_expert_review": False
    },
    "Pyrophosphate-diester": {
        "data_confidence": "moderate",
        "plasma_t12": "Moderate (hours to days; hydrolysis-sensitive)",
        "cleavage_enzyme": "Phosphodiesterase (intracellular) + spontaneous hydrolysis in lysosomes",
        "tumor_cleavage_efficiency": "Moderate",
        "compatible_payload_chemistry": "Hydroxyl-bearing payloads",
        "compatible_conjugation_sites": ["Lysine"],
        "hydrophilicity_note": "Hydrophilic; improves ADC PK",
        "optimal_dar_range_note": "DAR 4–6",
        "needs_expert_review": True
    },
    "Legumain-cleavable": {
        "data_confidence": "moderate",
        "plasma_t12": ">7 days (legumain not present in blood)",
        "cleavage_enzyme": "Legumain (Asn-specific cysteine protease; expressed in tumor-associated macrophages and acidic tumor stroma)",
        "tumor_cleavage_efficiency": "High in tumor microenvironment (TME-specific); activated in hypoxic/acidic tumor regions",
        "compatible_payload_chemistry": "Free amine payload (Asn-Pro dipeptide with PABC spacer)",
        "compatible_conjugation_sites": ["Cysteine", "Site-specific"],
        "hydrophilicity_note": "Moderate hydrophilicity",
        "optimal_dar_range_note": "DAR 3–4",
        "needs_expert_review": True
    },
    "beta-galactoside-cleavable": {
        "data_confidence": "moderate",
        "plasma_t12": ">7 days (beta-galactosidase absent from plasma)",
        "cleavage_enzyme": "β-Galactosidase (lysosomal; also expressed extracellularly by senescent tumor cells)",
        "tumor_cleavage_efficiency": "High in lysosomes; emerging interest in senolytic ADC strategy",
        "compatible_payload_chemistry": "Free amine or hydroxyl payload",
        "compatible_conjugation_sites": ["Cysteine", "Lysine"],
        "hydrophilicity_note": "Highly hydrophilic (galactose moiety); excellent for high DAR",
        "optimal_dar_range_note": "DAR 4–8",
        "needs_expert_review": False
    },
    "Sulfatase-cleavable": {
        "data_confidence": "low",
        "plasma_t12": ">7 days",
        "cleavage_enzyme": "Sulfatase (lysosomal arylsulfatase A/B)",
        "tumor_cleavage_efficiency": "Moderate — limited tumor selectivity vs normal lysosomal expression",
        "compatible_payload_chemistry": "Sulfate ester-bearing payloads",
        "compatible_conjugation_sites": ["Lysine"],
        "hydrophilicity_note": "Highly hydrophilic",
        "optimal_dar_range_note": "DAR 4–6",
        "needs_expert_review": True
    },
    "Phosphatase-cleavable": {
        "data_confidence": "low",
        "plasma_t12": "Short (hours) — phosphatases present in blood; major stability concern",
        "cleavage_enzyme": "Alkaline/acid phosphatase (widespread expression — poor tumor selectivity)",
        "tumor_cleavage_efficiency": "Low selectivity — premature cleavage in blood is the major issue",
        "compatible_payload_chemistry": "Phosphate ester-bearing payloads",
        "compatible_conjugation_sites": ["Cysteine", "Lysine"],
        "hydrophilicity_note": "Highly hydrophilic",
        "optimal_dar_range_note": "Experimental only",
        "needs_expert_review": True
    },
    "Mal-PEG2-V-Cit-PAB": {
        "data_confidence": "moderate",
        "plasma_t12": ">7 days",
        "cleavage_enzyme": "Cathepsin B",
        "tumor_cleavage_efficiency": "High",
        "compatible_payload_chemistry": "Free amine (PABC self-immolation)",
        "compatible_conjugation_sites": ["Cysteine (maleimide)"],
        "hydrophilicity_note": "PEG2 spacer significantly improves solubility over standard vc-PABC; allows higher DAR without aggregation",
        "optimal_dar_range_note": "DAR 4–6 feasible",
        "needs_expert_review": False
    },
    "Hydrazone-disulfide": {
        "data_confidence": "moderate",
        "plasma_t12": "Short (hours) — hydrazone is acid-labile, pH-sensitive. t1/2 ~1–4 h at pH 5.5 (lysosome), ~24–72 h at pH 7.4 (blood). Early ADCs (Mylotarg) used this — premature release was a safety issue.",
        "cleavage_enzyme": "pH-dependent hydrolysis (no enzyme required); disulfide component also cleaved by intracellular glutathione (GSH)",
        "tumor_cleavage_efficiency": "Moderate — relies on endosomal/lysosomal acidification; can also cleave extracellularly in acidic TME",
        "compatible_payload_chemistry": "Ketone or aldehyde group required on payload for hydrazone formation",
        "compatible_conjugation_sites": ["Lysine (NHS ester)", "Cysteine (disulfide component)"],
        "hydrophilicity_note": "Moderate; hydrazone contributes some polarity",
        "optimal_dar_range_note": "DAR 2–4 (limited by hydrazone instability at higher loading)",
        "needs_expert_review": False
    },
    "Thioether-cleavable": {
        "data_confidence": "low",
        "plasma_t12": "Variable",
        "cleavage_enzyme": "Intracellular thiol (GSH-mediated reduction)",
        "tumor_cleavage_efficiency": "Moderate — relies on elevated intracellular GSH (~10 mM) vs extracellular (~2–10 μM); provides selectivity window",
        "compatible_payload_chemistry": "Thiol-reactive payload",
        "compatible_conjugation_sites": ["Cysteine", "Engineered Cys"],
        "hydrophilicity_note": "Hydrophobic",
        "optimal_dar_range_note": "DAR 2–4",
        "needs_expert_review": True
    },
    "Peptide-MMAF": {
        "data_confidence": "moderate",
        "plasma_t12": ">7 days",
        "cleavage_enzyme": "Cathepsin B or other lysosomal peptidases",
        "tumor_cleavage_efficiency": "High",
        "compatible_payload_chemistry": "MMAF (charged, membrane-impermeable; no bystander effect)",
        "compatible_conjugation_sites": ["Cysteine"],
        "hydrophilicity_note": "Moderate; MMAF's charge improves overall hydrophilicity vs MMAE linker-payloads",
        "optimal_dar_range_note": "DAR 2–4",
        "needs_expert_review": False
    },
    "PEG8-vc-PABC": {
        "data_confidence": "moderate",
        "plasma_t12": ">7 days",
        "cleavage_enzyme": "Cathepsin B",
        "tumor_cleavage_efficiency": "High",
        "compatible_payload_chemistry": "Free amine payload (PABC self-immolation)",
        "compatible_conjugation_sites": ["Cysteine (maleimide)"],
        "hydrophilicity_note": "PEG8 provides excellent hydrophilicity; supports DAR 6–8 with minimal aggregation; significant PK improvement over vc-PABC at high DAR",
        "optimal_dar_range_note": "DAR 6–8 feasible",
        "needs_expert_review": False
    },
    "Val-Cit-PAB-OH": {
        "data_confidence": "moderate",
        "plasma_t12": ">7 days",
        "cleavage_enzyme": "Cathepsin B",
        "tumor_cleavage_efficiency": "High",
        "compatible_payload_chemistry": "Hydroxyl-bearing payload (carbamate or carbonate conjugation)",
        "compatible_conjugation_sites": ["Cysteine", "Lysine"],
        "hydrophilicity_note": "Moderate",
        "optimal_dar_range_note": "DAR 3–4",
        "needs_expert_review": False
    },
    "mc-Val-Cit-PAB-PNP": {
        "data_confidence": "moderate",
        "plasma_t12": ">7 days",
        "cleavage_enzyme": "Cathepsin B",
        "tumor_cleavage_efficiency": "High",
        "compatible_payload_chemistry": "Activated carbonate; used as reactive intermediate for amine or hydroxyl-bearing payloads",
        "compatible_conjugation_sites": ["Cysteine (maleimide precursor)"],
        "hydrophilicity_note": "Moderate",
        "optimal_dar_range_note": "DAR 3–4",
        "needs_expert_review": False
    },
    "Mal-PEG4-NHS": {
        "data_confidence": "moderate",
        "plasma_t12": ">7 days (non-cleavable crosslinker with maleimide-NHS heterobifunctional)",
        "cleavage_enzyme": "None (non-cleavable spacer/crosslinker)",
        "tumor_cleavage_efficiency": "N/A",
        "compatible_payload_chemistry": "Amine group on payload (NHS ester) + thiol on Ab (maleimide)",
        "compatible_conjugation_sites": ["Cysteine + Lysine (heterobifunctional)", "Used in SMAC technology"],
        "hydrophilicity_note": "PEG4 provides good hydrophilicity",
        "optimal_dar_range_note": "DAR 2–4",
        "needs_expert_review": False
    },
    "SMPEG24": {
        "data_confidence": "moderate",
        "plasma_t12": ">7 days (non-cleavable)",
        "cleavage_enzyme": "None (non-cleavable PEG-maleimide crosslinker)",
        "tumor_cleavage_efficiency": "N/A — payload released by complete Ab catabolism",
        "compatible_payload_chemistry": "Thiol-bearing payload",
        "compatible_conjugation_sites": ["Lysine (NHS ester end)", "Cysteine (maleimide end)"],
        "hydrophilicity_note": "PEG24 provides excellent hydrophilicity; enables DAR >8 without aggregation. Used in Zynlonta formulation variants.",
        "optimal_dar_range_note": "DAR 4–8 feasible",
        "needs_expert_review": False
    },
    "Fmoc-vc-PABC": {
        "data_confidence": "low",
        "plasma_t12": "Unknown — Fmoc is base-labile; not intended for systemic stability",
        "cleavage_enzyme": "Cathepsin B (after Fmoc deprotection)",
        "tumor_cleavage_efficiency": "Low — primarily used as a synthetic intermediate, not for in vivo ADC",
        "compatible_payload_chemistry": "Free amine payload",
        "compatible_conjugation_sites": ["Cysteine"],
        "hydrophilicity_note": "Hydrophobic (Fmoc group)",
        "optimal_dar_range_note": "Research/synthesis use only",
        "needs_expert_review": True
    },
    "Dde-vc-PABC": {
        "data_confidence": "low",
        "plasma_t12": "Unknown — Dde is hydrazine-labile protecting group; research use",
        "cleavage_enzyme": "Cathepsin B (after Dde deprotection)",
        "tumor_cleavage_efficiency": "Low — research/synthesis intermediate",
        "compatible_payload_chemistry": "Free amine payload",
        "compatible_conjugation_sites": ["Cysteine"],
        "hydrophilicity_note": "Moderate",
        "optimal_dar_range_note": "Research/synthesis use only",
        "needs_expert_review": True
    },
    "PEG4-vc-PABC": {
        "data_confidence": "moderate",
        "plasma_t12": ">7 days",
        "cleavage_enzyme": "Cathepsin B",
        "tumor_cleavage_efficiency": "High",
        "compatible_payload_chemistry": "Free amine payload (PABC self-immolation)",
        "compatible_conjugation_sites": ["Cysteine (maleimide)"],
        "hydrophilicity_note": "PEG4 substantially improves hydrophilicity over standard vc-PABC; supports DAR 5–6",
        "optimal_dar_range_note": "DAR 4–6 feasible",
        "needs_expert_review": False
    }
}

updated = 0
not_found = []
for c in comp:
    if 'type' in c and 'class' not in c:  # linker
        name = c.get('name','')
        if name in linker_enrichment:
            c.update(linker_enrichment[name])
            updated += 1
        elif 'plasma_t12' not in c:
            not_found.append(name)

fp.write_text(json.dumps(comp, indent=2, ensure_ascii=False))
print(f'Updated {updated} linkers.')
if not_found:
    print(f'Not enriched ({len(not_found)}): {not_found}')
