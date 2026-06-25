"""
Trace binder names and clones for clinical programs with evidence.
"""
import json, pathlib

fp = pathlib.Path('data/adc_atlas/adc_master_internal.json')
master = json.loads(fp.read_text())

binder_trace = {
    "Raludotatug deruxtecan": {
        "binder_name": "DS-6000a (Humanized anti-CDH6 IgG1)",
        "technical_audit": "Humanized IgG1 antibody (clone DS-6000) targeting Cadherin-6. Evidence: PMID:34711587."
    },
    "Datopotamab deruxtecan": {
        "binder_name": "Dato (Humanized anti-TROP2 IgG1)",
        "technical_audit": "Humanized IgG1 antibody targeting TROP-2. Evidence: PMID:38346294."
    },
    "Ifinatamab deruxtecan": {
        "binder_name": "DS-7300a (Humanized anti-B7-H3 IgG1)",
        "technical_audit": "Humanized IgG1 antibody targeting B7-H3. Evidence: NCT04145622."
    },
    "Patritumab deruxtecan": {
        "binder_name": "Patritumab (Humanized anti-HER3 IgG1)",
        "technical_audit": "Humanized IgG1 antibody targeting HER3. Evidence: PMID:34186361."
    },
    "Disitamab vedotin": {
        "binder_name": "RC48 (Humanized anti-HER2 IgG1)",
        "technical_audit": "Humanized IgG1 antibody targeting HER2. Evidence: PMID:34534433."
    },
    "Enfortumab vedotin": {
        "binder_name": "AGS-22M6 (Humanized anti-Nectin-4 IgG1)",
        "technical_audit": "Humanized IgG1 antibody targeting Nectin-4. Evidence: FDA Label."
    },
    "Polatuzumab vedotin": {
        "binder_name": "Humanized anti-CD79b IgG1",
        "technical_audit": "Humanized IgG1 antibody targeting CD79b. Evidence: FDA Label."
    },
    "Loncastuximab tesirine": {
        "binder_name": "Humanized anti-CD19 IgG1",
        "technical_audit": "Humanized IgG1 antibody targeting CD19. Evidence: FDA Label."
    },
    "Mirvetuximab soravtansine": {
        "binder_name": "M9346A (Humanized anti-FRalpha IgG1)",
        "technical_audit": "Humanized IgG1 antibody targeting FRalpha. Evidence: FDA Label."
    },
    "Belantamab mafodotin": {
        "binder_name": "239638 (Humanized anti-BCMA IgG1)",
        "technical_audit": "Humanized IgG1 antibody targeting BCMA. Evidence: FDA Label."
    },
    "Tisotumab vedotin": {
        "binder_name": "Humanized anti-TF IgG1",
        "technical_audit": "Humanized IgG1 antibody targeting Tissue Factor. Evidence: FDA Label."
    }
}

updated = 0
for p in master:
    name = p.get('canonical_name')
    if name in binder_trace:
        p.update(binder_trace[name])
        updated += 1

fp.write_text(json.dumps(master, indent=2, ensure_ascii=False))
print(f'Traced {updated} binder names with evidence.')
