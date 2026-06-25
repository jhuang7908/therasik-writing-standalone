import re

filepath = 'd:/InSynBio-AI-Research/Antibody_Engineer_Suite/insynbio-web-source/pitch desk/InSynBio_Pitch_Deck.html'
with open(filepath, 'r', encoding='utf-8') as f:
    content = f.read()

# Replace links to point to the root directory
# E.g., href="case_bispecific_vhh_expression_optimization.html" -> href="../case_bispecific_vhh_expression_optimization.html"
files_to_fix = [
    'case_bispecific_vhh_expression_optimization.html',
    'case_fentanyl_hapten_vam.html',
    'case_pdl1_epitope_analysis.html',
    'case_mumab4d5_humanization_en.html',
    'case_mumab4d5_cmc.html',
    'case_malaria_carm_design.html',
    'case_vgrw_cdr_redesign_remat.html',
    'InSynBio_ADC_Design_Page.html',
    'vaccine_design.html'
]

for file in files_to_fix:
    content = content.replace(f'href="{file}"', f'href="../{file}"')

with open(filepath, 'w', encoding='utf-8') as f:
    f.write(content)

print("Links fixed successfully.")
