import json, pathlib

fp = pathlib.Path('data/adc_atlas/adc_components.json')
comp = json.loads(fp.read_text())

# Linker enrichment
linker_evidence = {
    'mc-val-cit-PABC': {
        'data_confidence': 'high',
        'evidence_note': 'Industry standard protease-cleavable linker. Highly stable in human plasma but rapidly cleaved by lysosomal Cathepsin B. PABC spacer allows self-immolation to release free amine payload.',
        'key_refs': ['PMID:12873544 (Original vc-PABC paper)', 'FDA label: Adcetris, Polivy, Padcev']
    },
    'GGFG': {
        'data_confidence': 'high',
        'evidence_note': 'Tetrapeptide linker used in Daiichi Sankyo DXd platform. Cleaved by lysosomal cathepsins (upregulated in tumor cells). Highly stable in circulation. Lacks PABC self-immolative group; relies on direct cleavage to release DXd.',
        'key_refs': ['PMID:26058450 (DXd linker-payload design)', 'FDA label: Enhertu']
    },
    'Sulfo-SMCC': {
        'data_confidence': 'high',
        'evidence_note': 'Classic non-cleavable thioether linker. Requires complete lysosomal degradation of the antibody to release payload (typically as Lys-SMCC-payload adduct). Very high plasma stability.',
        'key_refs': ['PMID:16814772 (T-DM1 design)', 'FDA label: Kadcyla']
    },
    'Glucuronide-MMAE': {
        'data_confidence': 'high',
        'evidence_note': 'Cleaved by beta-glucuronidase (highly expressed in lysosomes and tumor microenvironment). Highly hydrophilic, reducing ADC aggregation and improving PK compared to dipeptide linkers.',
        'key_refs': ['PMID:16955513 (Beta-glucuronide linkers)']
    },
    'VA-PABC': {
        'data_confidence': 'high',
        'evidence_note': 'Valine-Alanine dipeptide. Cleaved by Cathepsin B. More hydrophilic and less prone to aggregation than Val-Cit, often used with highly hydrophobic payloads like PBDs.',
        'key_refs': ['PMID:26700026 (Val-Ala vs Val-Cit comparison)', 'FDA label: Zynlonta']
    }
}

# Payload enrichment
payload_evidence = {
    'MMAE': {
        'data_confidence': 'high',
        'evidence_note': 'Monomethyl auristatin E. Highly potent tubulin inhibitor (IC50 ~0.1-1 nM). Membrane-permeable, causing strong bystander killing effect. Dose-limiting toxicity: peripheral neuropathy and neutropenia.',
        'key_refs': ['PMID:12873544 (MMAE ADC development)', 'FDA label: Adcetris, Polivy, Padcev']
    },
    'DXd': {
        'data_confidence': 'high',
        'evidence_note': 'Exatecan derivative (Topoisomerase I inhibitor). IC50 ~0.3 nM. Highly membrane-permeable (strong bystander effect) but has a short systemic half-life, reducing off-target toxicity. DLT: Interstitial lung disease (ILD).',
        'key_refs': ['PMID:26058450 (DXd discovery)', 'FDA label: Enhertu']
    },
    'MMAF': {
        'data_confidence': 'high',
        'evidence_note': 'Monomethyl auristatin F. Contains a charged C-terminal phenylalanine, rendering it membrane-impermeable (no bystander effect). Lower systemic toxicity than MMAE. DLT: Ocular toxicity.',
        'key_refs': ['PMID:16450923 (MMAF vs MMAE)', 'FDA label: Blenrep']
    },
    'Auristatin F': {
        'data_confidence': 'high',
        'evidence_note': 'Charged tubulin inhibitor. Membrane-impermeable (no bystander effect). Lower systemic toxicity than MMAE. DLT: Ocular toxicity (corneal epithelial changes).',
        'key_refs': ['PMID:16450923 (MMAF vs MMAE)', 'FDA label: Blenrep']
    },
    'DGN462': {
        'data_confidence': 'moderate',
        'evidence_note': 'Indolinobenzodiazepine DNA-alkylating agent (IGN). Extremely potent (IC50 ~pM range). Causes DNA strand breaks. Associated with veno-occlusive disease (VOD) and delayed toxicities.',
        'key_refs': ['PMID:26013320 (IGN payloads)']
    },
    'Alpha-amanitin': {
        'data_confidence': 'moderate',
        'evidence_note': 'RNA Polymerase II inhibitor. Induces apoptosis independent of cell cycle (effective in slow-growing tumors). High potency (pM). Liver toxicity is a major historical concern, requiring stable linkers.',
        'key_refs': ['PMID:22406981 (Amanitin ADCs)']
    },
    'Thorium-227': {
        'data_confidence': 'moderate',
        'evidence_note': 'Targeted Alpha Therapy (TAT) payload. High linear energy transfer (LET) causes double-strand DNA breaks independent of cell cycle or oxygenation. Half-life 18.7 days.',
        'key_refs': ['PMID:26187766 (Thorium-227 TTCs)']
    },
    'Actinium-225': {
        'data_confidence': 'moderate',
        'evidence_note': 'Alpha-emitter. Half-life 10 days. Extremely potent localized cell killing (range ~50-80 µm). Requires specialized chelation chemistry (e.g., DOTA, Macropa).',
        'key_refs': ['PMID:21245055 (Actinium-225 targeted therapy)']
    }
}

updated = 0
for c in comp:
    name = c.get('name', '')
    if 'type' in c:  # It's a linker
        if name in linker_evidence:
            c.update(linker_evidence[name])
            updated += 1
        elif 'data_confidence' not in c:
            c['data_confidence'] = 'low'
            c['evidence_note'] = 'General structural class. Specific plasma stability and cleavage kinetics depend on exact conjugate context. Needs expert review.'
            c['needs_expert_review'] = True
            updated += 1
    elif 'class' in c:  # It's a payload
        if name in payload_evidence:
            c.update(payload_evidence[name])
            updated += 1
        elif 'data_confidence' not in c:
            c['data_confidence'] = 'low'
            c['evidence_note'] = 'Preclinical or investigational payload. Potency and bystander permeability are estimates. Needs expert review.'
            c['needs_expert_review'] = True
            updated += 1

fp.write_text(json.dumps(comp, indent=2, ensure_ascii=False))

high = sum(1 for c in comp if c.get('data_confidence')=='high')
mod  = sum(1 for c in comp if c.get('data_confidence')=='moderate')
low  = sum(1 for c in comp if c.get('data_confidence')=='low')

print(f'Updated {updated} components.')
print(f'Confidence High: {high}  Moderate: {mod}  Low/needs-review: {low}')
