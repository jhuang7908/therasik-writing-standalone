import os

targets = {
    'ADA/Clinical': ['ada_master','clinical_ada','confirmed_ada','ada_curation','ada_evidence',
                     'immunogenicity_panel','ada_reliable','ada_v2_pred','ada_review'],
    'HLA/MHC-II':  ['hla','tcia','epitope','immuno_','immuno_panel','immuno_study',
                     'immunogenicity_study','immunogenicity_report'],
    'Structure/PDB':['structure','sasa','surf_','vhh_her2','_pdb','vhh_her2_view',
                     'vhh_her2_haddock','test_7vke'],
    'Clinical-meta':['confounder','route_and_context','curated_66','clinical_metadata',
                     'calibrat','clinical_confounders','curated_clinical'],
    'Evidence/Docs':['evidence_report','review_discussion','ada_master_136','ada_master_table',
                     'vhh_database_summary','vhh_design_analysis'],
}

skip = ('node_modules','.git','__pycache__','.cursor','delivery_','insynbio-web',
        'actes_cart','ppt_extract','images\\','reports\\')

found = {k: [] for k in targets}

for root, dirs, files in os.walk('.'):
    # prune directories we don't want
    dirs[:] = [d for d in dirs if not any(s in os.path.join(root, d) for s in skip)]
    for f in files:
        path = os.path.join(root, f).replace('.\\','').replace('\\','/')
        pl = path.lower()
        for cat, kws in targets.items():
            if any(kw in pl for kw in kws):
                found[cat].append(path)
                break

for cat, files in found.items():
    print('\n[{}] ({} files)'.format(cat, len(files)))
    for p in sorted(set(files)):
        print('  {}'.format(p))
