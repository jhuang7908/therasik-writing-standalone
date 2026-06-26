import json
import shutil
from datetime import datetime
from pathlib import Path

REGISTRY_PATH = Path("data/germlines/canis_lupus_familiaris_ig_aa/dog_scaffold_cmc_optimization_tier1_tier2_v1.json")

def upgrade_dog_registry():
    if not REGISTRY_PATH.exists():
        print(f"Error: {REGISTRY_PATH} not found")
        return

    # Backup
    backup_path = REGISTRY_PATH.with_suffix(f".bak_v1.1_{datetime.now().strftime('%Y%m%d_%H%M%S')}")
    shutil.copy2(REGISTRY_PATH, backup_path)
    print(f"Backup created: {backup_path.name}")

    data = json.loads(REGISTRY_PATH.read_text(encoding="utf-8"))
    
    # Update version and changelog
    data["version"] = "1.2"
    data["built_at"] = datetime.now().isoformat(timespec="seconds") + "Z"
    new_changelog = "V1.2 (2026-04-29): Dual-entry upgrade. Promoted IGHV3-23*01 to Tier 1 based on superior CMC profile (Flags=4). Formalized Clinical Anchor + CMC Optimized ranking system."
    if "changelog" in data:
        data["changelog"] = new_changelog + "\n" + data["changelog"]
    else:
        data["changelog"] = new_changelog

    # Promote IGHV3-23*01 to Tier 1
    promoted_count = 0
    for row in data.get("rows", []):
        if row.get("gene") == "IGHV3-23*01":
            if row.get("tier") != "tier1":
                row["tier"] = "tier1"
                promoted_count += 1
                print(f"Promoted {row.get('gene')} to Tier 1")

    # Save
    REGISTRY_PATH.write_text(json.dumps(data, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    print(f"Upgrade complete. Promoted {promoted_count} entries. Version bumped to 1.2.")

if __name__ == "__main__":
    upgrade_dog_registry()
