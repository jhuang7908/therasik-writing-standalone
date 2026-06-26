"""
P3 Task: Vaccine KB Pivot to Therapeutic Cancer Vaccines.
1. Filter from 77 down to ~45 high-quality entries.
2. Restructure categories for therapeutic cancer vaccine positioning.
3. Update metadata.
"""
import json
import os
from pathlib import Path

# Paths
ROOT = Path("D:/InSynBio-AI-Research/Antibody_Engineer_Suite")
JSON_PATH = ROOT / "docs/vaccine_kb_data.json"
WEB_PATHS = [
    ROOT / "insynbio-web-source/vaccine_kb_data.json",
    ROOT / "therasik-web-source/vaccine_kb_data.json"
]

def pivot_vaccine_kb():
    if not JSON_PATH.exists():
        print(f"Error: {JSON_PATH} not found")
        return

    with open(JSON_PATH, encoding="utf-8") as f:
        data = json.load(f)

    new_data = {}

    # 1. Tumor Antigens (Keep all 30 TAAs)
    new_data["tumor_antigens"] = data.get("taa", [])
    print(f"Kept {len(new_data['tumor_antigens'])} tumor antigens.")

    # 2. Oncoviruses (Filter infectious for HPV and HBV)
    infectious = data.get("infectious", [])
    oncoviruses = [x for x in infectious if any(v in x.get("pathogen", "").upper() for v in ["HPV", "HBV", "EBV"])]
    new_data["oncoviruses"] = oncoviruses
    print(f"Kept {len(new_data['oncoviruses'])} oncoviruses (HPV/HBV).")

    # 3. Delivery Platforms (Filter vectors for cancer relevant platforms)
    # Platforms to keep: mRNA, DNA, Adenovirus, MVA, VLP, VSV (maybe?)
    vectors = data.get("vectors", [])
    keep_platforms = ["mRNA-LNP", "DNA vaccine", "Adenovirus vector", "Modified Vaccinia Ankara", "Virus-Like Particle", "VSV"]
    delivery_platforms = [x for x in vectors if any(p in x.get("name", "") for p in keep_platforms)]
    new_data["delivery_platforms"] = delivery_platforms
    print(f"Kept {len(new_data['delivery_platforms'])} delivery platforms.")

    # 4. Immunomodulators (Filter adjuvants for therapeutic relevance)
    # Keep: STING, Poly-ICLC, AS01B, CpG, LNP
    adjuvants = data.get("adjuvants", [])
    keep_adjuvants = ["STING agonists", "Poly-ICLC", "AS01B", "CpG-1018", "LNP"]
    immunomodulators = [x for x in adjuvants if any(a in x.get("name", "") for a in keep_adjuvants)]
    new_data["immunomodulators"] = immunomodulators
    print(f"Kept {len(new_data['immunomodulators'])} immunomodulators.")

    # 5. Monitoring & TCR (Merge TCR clones and motifs)
    monitoring = data.get("tcr_clones", []) + data.get("tcr_motifs", [])
    new_data["monitoring"] = monitoring
    print(f"Merged {len(new_data['monitoring'])} monitoring entries (TCR clones/motifs).")

    # Calculate total entries
    total_entries = sum(len(v) for k, v in new_data.items() if not k.startswith("_"))
    print(f"Total entries: {total_entries}")

    # 6. Update Meta
    new_data["_meta"] = data.get("_meta", {})
    new_data["_meta"].update({
        "version": "3.0-therapeutic-pivot",
        "updated": "2026-04-07",
        "positioning": "Therapeutic Cancer Vaccines",
        "cleanup_notes": f"Cleaned and restructured for therapeutic cancer vaccine focus. Reduced from 77 to {total_entries} entries. Removed autoimmune and non-oncogenic infectious categories."
    })

    # Save to all locations
    save_paths = [JSON_PATH] + WEB_PATHS
    for path in save_paths:
        path.parent.mkdir(parents=True, exist_ok=True)
        with open(path, "w", encoding="utf-8") as f:
            json.dump(new_data, f, ensure_ascii=False, indent=2)
        print(f"Saved to {path}")

if __name__ == "__main__":
    pivot_vaccine_kb()
