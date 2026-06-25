import os
from bs4 import BeautifulSoup

directory = 'd:/InSynBio-AI-Research/Antibody_Engineer_Suite/insynbio-web-source'
files = [
    'case_bispecific_vhh_expression_optimization.html',
    'case_bispecific_vhvl_pairing.html',
    'case_fentanyl_hapten_vam.html',
    'case_malaria_carm_design.html',
    'case_mumab4d5_cmc.html',
    'case_mumab4d5_humanization_en.html',
    'case_mumab4d5_vhh_en.html',
    'case_pdl1_epitope_analysis.html',
    'case_vgrw_cdr_redesign_remat.html',
    'case_vgrw_sr_r2_affinity_maturation.html'
]

for file in files:
    filepath = os.path.join(directory, file)
    with open(filepath, 'r', encoding='utf-8') as f:
        soup = BeautifulSoup(f.read(), 'html.parser')
        
        # Try to find some description or key points to summarize
        h1 = soup.find('h1')
        title = h1.text.strip() if h1 else soup.title.string
        
        print(f"--- {file} ---")
        print(f"Title: {title}")
        
        # Get some content
        paragraphs = soup.find_all('p', limit=2)
        for p in paragraphs:
            print(p.text.strip()[:150])
        print()
