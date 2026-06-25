base = 'Antibody_Engineer_Suite/data/immunogenicity_knowledge_base'
text_c = open(f'{base}/ada_evidence/confirmed_ada.md', encoding='utf-8').read()
text_full = open(f'{base}/reports/clinical_ada_full_evidence_report.md', encoding='utf-8').read()
text_eng = open(f'{base}/reports/clinical_ada_engineered_evidence_report.md', encoding='utf-8').read()
for name in ['Nipocalimab', 'Epcoritamab', 'Elranatamab']:
    print(f'{name}: confirmed={name in text_c}, full={name in text_full}, eng={name in text_eng}')
