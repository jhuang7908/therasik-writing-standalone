"""
Add verified PubMed source links to epitopes not found in IEDB,
and mark remaining unverified entries with unconfirmed=True.
"""
import json

VERIFIED = {
    # Only PMIDs directly confirmed by fetching the PubMed page
    "GVALQTMKQ": {
        "pmid": "11290817",
        "source_url": "https://pubmed.ncbi.nlm.nih.gov/11290817/",
        "source_note": "Butterfield et al. J Immunol 2001 — AFP542-550 HLA-A*02:01 CTL epitope"
    },
    "PQPELPYPQPE": {
        "pmid": "12198706",
        "source_url": "https://pubmed.ncbi.nlm.nih.gov/12198706/",
        "source_note": "Vader et al. Gastroenterology 2002 — DQ2.5-glia-alpha2 celiac epitope"
    },
    "VLLKEFTVSGNI": {
        "pmid": "10878395",
        "source_url": "https://pubmed.ncbi.nlm.nih.gov/10878395/",
        "source_note": "Zeng et al. J Immunol 2000 — NY-ESO-1 p116-135 HLA-DR4 CD4 epitope"
    },
    "RIHMVYSKRSGKPRG": {
        "pmid": "21868195",
        "source_url": "https://pubmed.ncbi.nlm.nih.gov/21868195/",
        "source_note": "Deshmukh et al. J Autoimmun 2011 — SmD79-93 HLA-DR3 lupus epitope"
    },
}

# Epitopes that remain unverified - mark unconfirmed
# (no IEDB ID AND no confirmed PMID — IEDB search link provided but sequence not independently verified)
UNCONFIRMED = {
    "SGQARMFPNAPYLPSC", "PGSTAPPAHGVTSA", "DKKQRFHNIRGR",
    "PESFDGDPASNTAPLQP", "WNRQLYPEWTEAQRL", "VVRCPHERCTEGAT",
    "GWVKPIIIGHHAYGD", "EYLNKIQNSLSTEWSP", "MEVGWYRSPFSRVVH",
    "IPPSLRTLEDNER", "QQYPSGEGSFQPSQE",
}

json_path = "D:/InSynBio-AI-Research/Antibody_Engineer_Suite/docs/vaccine_kb_data.json"
with open(json_path, encoding="utf-8") as f:
    data = json.load(f)

def fix_list(epis):
    for e in epis:
        p = e.get("peptide", "")
        if p in VERIFIED:
            info = VERIFIED[p]
            e["pmid"] = info["pmid"]
            e["source_url"] = info["source_url"]
            e["source_note"] = info["source_note"]
            print(f"  +PMID {info['pmid']}: {p}")
        elif not e.get("iedb_id") and p in UNCONFIRMED:
            e["unconfirmed"] = True
            print(f"  MARK unconfirmed: {p}")

for t in data.get("taa", []):
    fix_list(t.get("known_epitopes_mhc1", []))
    fix_list(t.get("known_epitopes_mhc2", []))
for a in data.get("infectious", []):
    fix_list(a.get("known_epitopes_mhc1", []))
    fix_list(a.get("known_epitopes_mhc2", []))
for a in data.get("autoimmune", []):
    fix_list(a.get("known_epitopes", []))

with open(json_path, "w", encoding="utf-8") as f:
    json.dump(data, f, ensure_ascii=False, indent=1)
print("\nDone.")
