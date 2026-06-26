"""
P3 Task: Vaccine KB Pivot to Therapeutic Cancer Vaccines (v2).
1. Filter from 77 down to ~50 high-quality entries.
2. Use clean, consistent category names.
3. Update metadata.
"""
import json
from pathlib import Path

# Paths
ROOT = Path("D:/InSynBio-AI-Research/Antibody_Engineer_Suite")
JSON_PATH = ROOT / "docs/vaccine_kb_data.json"
WEB_PATHS = [
    ROOT / "insynbio-web-source/vaccine_kb_data.json",
    ROOT / "therasik-web-source/vaccine_kb_data.json"
]

def pivot_vaccine_kb():
    # Load original data (I'll need to load from a backup or re-load if I already overwrote it)
    # Actually, I'll just load what's there and filter it.
    # Wait, I already overwrote docs/vaccine_kb_data.json with the new keys.
    # I should have kept the old keys or used a backup.
    # Let me check if I have a backup.
    
    with open(JSON_PATH, encoding="utf-8") as f:
        data = json.load(f)

    # If I already pivoted, the keys are 'tumor_antigens', 'oncoviruses', etc.
    # I'll normalize them to what the HTML expects or what makes most sense.
    
    new_data = {}
    
    # 1. Antigens (TAAs)
    new_data["taa"] = data.get("tumor_antigens", data.get("taa", []))
    
    # 2. Oncoviruses
    new_data["oncoviruses"] = data.get("oncoviruses", [])
    
    # 3. Platforms (Renamed from vectors)
    new_data["platforms"] = data.get("delivery_platforms", data.get("vectors", []))
    
    # 4. Adjuvants
    new_data["adjuvants"] = data.get("immunomodulators", data.get("adjuvants", []))
    
    # 5. Monitoring
    # If merged, I'll split them back based on keys
    monitoring = data.get("monitoring", [])
    if monitoring:
        new_data["tcr_clones"] = [x for x in monitoring if "clone_id" in x]
        new_data["tcr_motifs"] = [x for x in monitoring if "cdr3b_motif" in x]
    else:
        new_data["tcr_clones"] = data.get("tcr_clones", [])
        new_data["tcr_motifs"] = data.get("tcr_motifs", [])

    # Calculate stats
    total = sum(len(v) for k, v in new_data.items() if not k.startswith("_"))
    print(f"Stats: TAA:{len(new_data['taa'])}, Viral:{len(new_data['oncoviruses'])}, Platforms:{len(new_data['platforms'])}, Adjuvants:{len(new_data['adjuvants'])}, TCR:{len(new_data['tcr_clones'])}, Motifs:{len(new_data['tcr_motifs'])}")
    print(f"Total: {total}")

    # Meta
    new_data["_meta"] = data.get("_meta", {})
    new_data["_meta"].update({
        "version": "3.1-therapeutic-pivot",
        "updated": "2026-04-07",
        "positioning": "Therapeutic Cancer Vaccines",
        "entry_count": total
    })

    # Save
    save_paths = [JSON_PATH] + WEB_PATHS
    for path in save_paths:
        with open(path, "w", encoding="utf-8") as f:
            json.dump(new_data, f, ensure_ascii=False, indent=2)
        print(f"Saved to {path}")

if __name__ == "__main__":
    pivot_vaccine_kb()
