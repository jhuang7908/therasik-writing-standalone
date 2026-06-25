"""Patch SSOT from V1.8.15 to V1.8.16."""
import json
from pathlib import Path

p = Path("config/standards_ssot.json")
content = p.read_text(encoding="utf-8")

# find the vh_to_vhh block
idx = content.find('"id": "vh_to_vhh_conversion_path_b2_c"')
assert idx != -1, "Block not found"

# find the closing brace of this block (next "},")
end = content.find('\n    }', idx)
block = content[idx:end+6]

new_block = block
new_block = new_block.replace('"version": "V1.8.15"', '"version": "V1.8.16"')
new_block = new_block.replace('"release_id": "V1.8.15_VH_to_VHH_Conversion"', '"release_id": "V1.8.16_VH_to_VHH_Conversion"')
new_block = new_block.replace('"supersedes": "V1.8.14_VH_to_VHH_Conversion"', '"supersedes": "V1.8.15_VH_to_VHH_Conversion"')

# Replace config_files
old_cfg = '"scripts/run_cd3_v1815.py",\n        "scripts/v1814_cohort_validation.py",\n        "scripts/rejudge_v1814.py",\n        "data/_v1814_design/v1814_classification_by_category.json"'
new_cfg = '"scripts/run_cd3_v1815.py",\n        "scripts/structure_sasa_v1816.py",\n        "scripts/v1814_cohort_validation.py"'
if old_cfg in new_block:
    new_block = new_block.replace(old_cfg, new_cfg)

# Replace config_note
note_start = new_block.find('"config_note": "V1.8.15')
if note_start != -1:
    note_end = new_block.find('Owner approved 2026-05-16."', note_start) + len('Owner approved 2026-05-16."')
    old_note = new_block[note_start:note_end]
    new_note = ('"config_note": "V1.8.16 (2026-05-16): Structure-based SASA gate (Section 1a.2). '
                'NanoBodyBuilder2 + BioPython ShrakeRupley measures actual SASA of k45/k47/k37 after sequence engineering. '
                'Gate rule: k45 in {L,V,I,M,A,F,W} AND k45 SASA > 50 A^2 -> apply Hallmark. '
                'Calibration: Teplizumab V1.8.13 k45=L SASA=99.5 A^2 (dangerous); V1.8.15 k45=R SASA=127.1 A^2 (safe). '
                'Key: R has HIGHER raw SASA than L but is hydrophilic -> gate must check aa type, not raw SASA alone. '
                'CD3 panel n=6 all PASS. Script: structure_sasa_v1816.py. Owner approved 2026-05-16."')
    new_block = new_block[:note_start] + new_note + new_block[note_end:]

content2 = content[:idx] + new_block + content[idx+len(block):]
p.write_text(content2, encoding="utf-8")

# validate JSON
data = json.loads(content2)
# find the patched entry
for s in data["standards"]:
    if s.get("id") == "vh_to_vhh_conversion_path_b2_c":
        print(f"version: {s['version']}")
        print(f"supersedes: {s['supersedes']}")
        print(f"config_files: {s['config_files']}")
        break
print("SSOT patched OK")
