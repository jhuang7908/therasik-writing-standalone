import re

filepath = 'd:/InSynBio-AI-Research/Antibody_Engineer_Suite/therasik-web-source/pitch desk/Therasik_Pitch_Deck.html'
with open(filepath, 'r', encoding='utf-8') as f:
    content = f.read()

# Replace links to point to the root directory
files_to_fix = [
    'Therasik_Immunogenicity.html',
    'case_bispecific_vhh_expression_optimization.html',
    'case_fentanyl_hapten_vam.html',
    'case_pdl1_epitope_analysis.html',
    'case_mumab4d5_humanization_zh.html',
    'case_mumab4d5_cmc_zh.html',
    'case_vgrw_cdr_redesign_remat.html',
    'Therasik_ADC_Design_Page.html',
    'case_malaria_carm_design.html',
    'Therasik_Vaccine_Design.html'
]

for file in files_to_fix:
    content = content.replace(f'href="{file}"', f'href="../{file}"')

with open(filepath, 'w', encoding='utf-8') as f:
    f.write(content)

print("Links fixed successfully in Chinese pitch deck.")
