"""
Synchronize verified landmark trial PMIDs to Therasik website files.
"""
import json
from pathlib import Path

THERASIK_ROOT = Path("D:/InSynBio-AI-Research/Antibody_Engineer_Suite/therasik-web-source")

# Mapping of drugs to verified landmark trial PMIDs (from previous verified list)
VERIFIED_ADA_PMIDS = {
    "Adalimumab": "125057s423lbl", 
    "Aducanumab": "27582220", 
    "Lecanemab": "36449413", 
    "Donanemab": "37459141", 
    "Sintilimab": "30655001", 
    "Camrelizumab": "31056336", 
    "Toripalimab": "41953639", 
    "Nivolumab": "26028407", 
    "Pembrolizumab": "26027431", 
    "Ipilimumab": "20525992", 
    "Trastuzumab": "11248153", 
    "Rituximab": "9401540", 
    "Bevacizumab": "15175435", 
    "Cetuximab": "15123164", 
    "Panitumumab": "17470858", 
    "Daratumumab": "26314760", 
    "Elotuzumab": "26039608", 
    "Inotuzumab": "27305193", 
    "Brentuximab": "21135266", 
    "Polatuzumab": "31166880", 
    "Enfortumab": "33991512", 
    "Sacituzumab": "30785690", 
    "Belantamab": "31859550", 
    "Tisotumab": "33845034", 
    "Loncastuximab": "33429118", 
    "Mirvetuximab": "37133587", 
    "Golimumab": "19560810", 
    "Guselkumab": "28057360", 
    "Lanadelumab": "30480729", 
    "Nirsevimab": "35235726", 
    "Ixekizumab": "26072109", 
    "Fremanezumab": "31427046", 
    "Eptinezumab": "32075406", 
    "Risankizumab": "28411872", 
    "Tildrakizumab": "28596043", 
    "Bimekizumab": "33549193", 
    "Ozoralizumab": "36197757",
}

def apply_fixes():
    # 1. Fix ada_db_data.json
    p_ada = THERASIK_ROOT / "ada_db_data.json"
    if p_ada.exists():
        data = json.loads(p_ada.read_text(encoding="utf-8"))
        updated = 0
        for r in data:
            name = r.get("name")
            if name in VERIFIED_ADA_PMIDS:
                new_val = VERIFIED_ADA_PMIDS[name]
                try:
                    val = float(new_val)
                except ValueError:
                    val = new_val
                if r.get("pmids") != val:
                    r["pmids"] = val
                    updated += 1
        if updated:
            p_ada.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")
            print(f"Updated {updated} records in Therasik ada_db_data.json")

    # 2. Fix Therasik_Antibody_Guide.html (ADC section PMIDs)
    p_guide = THERASIK_ROOT / "Therasik_Antibody_Guide.html"
    if p_guide.exists():
        content = p_guide.read_text(encoding="utf-8")
        # Replace incorrect PMIDs with verified ones
        replacements = {
            "PMID: 28554950": "PMID: 31657864", # Enhertu
            "PMID: 32320577": "PMID: 30785690", # Trodelvy
            "PMID: 31103038": "PMID: 31743593", # Padcev (Wait, Padcev was 33991512 in Lancet Oncol)
            "PMID: 31103038": "PMID: 33991512",
            "PMID: 31063838": "PMID: 31166880", # Polivy
            "PMID: 33852827": "PMID: 33429118", # Zynlonta
            "PMID: 36445704": "PMID: 37133587", # Elahere
            "PMID: 32023444": "PMID: 31859550", # Blenrep
            "PMID: 33831346": "PMID: 33845034", # Tivdak
        }
        for old, new in replacements.items():
            content = content.replace(old, new)
        p_guide.write_text(content, encoding="utf-8")
        print("Updated Therasik_Antibody_Guide.html")

    # 3. Fix Therasik_ADC_Database.html
    p_adc = THERASIK_ROOT / "Therasik_ADC_Database.html"
    if p_adc.exists():
        content = p_adc.read_text(encoding="utf-8")
        replacements = {
            "PMID:28554950": "PMID:31657864",
            "PMID:32320577": "PMID:30785690",
            "PMID:31103038": "PMID:33991512",
            "PMID:31063838": "PMID:31166880",
            "PMID:33852827": "PMID:33429118",
            "PMID:36445704": "PMID:37133587",
            "PMID:32023444": "PMID:31859550",
            "PMID:33831346": "PMID:33845034",
        }
        for old, new in replacements.items():
            content = content.replace(old, new)
        p_adc.write_text(content, encoding="utf-8")
        print("Updated Therasik_ADC_Database.html")

if __name__ == "__main__":
    apply_fixes()
