import os

BASE = r"D:\InSynBio-AI-Research\Antibody_Engineer_Suite\insynbio-web-source"

PAGES = [
    "case_bispecific_vhvl_pairing.html",
    "case_bispecific_vhh_expression_optimization.html",
    "case_malaria_carm_design.html",
    "case_mumab4d5_humanization_en.html",
    "case_mumab4d5_cmc.html",
    "case_mumab4d5_vhh_en.html",
    "case_vgrw_sr_r2_affinity_maturation.html",
    "immunogenicity_study.html",
]

OLD = "linear-gradient(135deg, #0d4a44 0%, #0d7a70 55%, #0d9488 100%)"
NEW = "url('images/hero-bg.svg') center/cover no-repeat, linear-gradient(135deg, #0d4a44 0%, #0d7a70 55%, #0d9488 100%)"

for fname in PAGES:
    path = os.path.join(BASE, fname)
    content = open(path, encoding="utf-8").read()
    if OLD in content:
        content = content.replace(OLD, NEW)
        open(path, "w", encoding="utf-8").write(content)
        print("Fixed: " + fname)
    else:
        print("No match: " + fname)
