#!/usr/bin/env python3
"""Quick summary of functional sites mapping status"""

import yaml
from pathlib import Path

project_root = Path(__file__).parent.parent
report_file = project_root / "kb" / "10_parameters" / "functional_sites_mapping_report.yaml"

with open(report_file, 'r', encoding='utf-8') as f:
    data = yaml.safe_load(f)

print("=" * 80)
print("FUNCTIONAL SITES MAPPING STATUS SUMMARY")
print("=" * 80)

print("\n📊 DUAL MAP STATUS:")
print("-" * 80)
status = data['dual_map_status']
for key, value in status.items():
    print(f"  {key}: {value}")

print("\n🏷️  HALLMARK MAPPING STATISTICS:")
print("-" * 80)
h_stats = data['hallmark_mapping_stats']
for key, value in h_stats.items():
    if key != 'sites':
        print(f"  {key}: {value}")

print("\n⚙️  VERNIER MAPPING STATISTICS:")
print("-" * 80)
v_stats = data['vernier_mapping_stats']
for key, value in v_stats.items():
    if key != 'sites':
        print(f"  {key}: {value}")

print("\n⚠️  CONFLICT EXAMPLE (Typical Pattern):")
print("-" * 80)
if data['conflict_examples']:
    example = data['conflict_examples'][0]
    print(f"  Type: {example['type']}")
    print(f"  Description: {example['description']}")
    print(f"\n  Example Site:")
    ex_site = example['example_site']
    print(f"    site_id: {ex_site['site_id']}")
    print(f"    role: {ex_site['role']}")
    print(f"    imgt_positions: {ex_site['imgt_positions']}")
    print(f"    kabat_positions: {ex_site['kabat_positions']}")
    print(f"    notes: {ex_site['notes']}")
    print(f"\n  Impact:")
    for impact in example['impact']:
        print(f"    - {impact}")

print("\n" + "=" * 80)










