#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
scripts/export_policy_yaml_to_json.py

Export the YAML policy file to JSON for programmatic consumption.
Ensures consistency between YAML and JSON versions of the fit rules.
"""

import json
import yaml
from pathlib import Path

# Project root
PROJECT_ROOT = Path(__file__).resolve().parents[1]

# Paths
POLICIES = [
    {
        "yaml": PROJECT_ROOT / "core" / "data" / "policy" / "template_target_fit_rules.yaml",
        "json": PROJECT_ROOT / "core" / "data" / "policy" / "template_target_fit_rules.json"
    },
    {
        "yaml": PROJECT_ROOT / "core" / "data" / "policy" / "framework_cdr_target_rulebook_v1.yaml",
        "json": PROJECT_ROOT / "core" / "data" / "policy" / "framework_cdr_target_rulebook_v1.json"
    },
    {
        "yaml": PROJECT_ROOT / "core" / "data" / "policy" / "humanization_strategies_v1.yaml",
        "json": PROJECT_ROOT / "core" / "data" / "policy" / "humanization_strategies_v1.json"
    }
]

def export_yaml_to_json():
    for policy in POLICIES:
        yaml_path = policy["yaml"]
        json_path = policy["json"]
        
        print(f"📖 Reading YAML: {yaml_path}")
        if not yaml_path.exists():
            print(f"❌ Error: YAML file not found at {yaml_path}")
            continue

        try:
            with open(yaml_path, "r", encoding="utf-8") as f:
                data = yaml.safe_load(f)
            
            print(f"💾 Writing JSON: {json_path}")
            with open(json_path, "w", encoding="utf-8") as f:
                json.dump(data, f, indent=2, ensure_ascii=False)
            
            print(f"✅ Export completed: {json_path.name}")
        except Exception as e:
            print(f"❌ Error during export of {yaml_path.name}: {e}")

if __name__ == "__main__":
    export_yaml_to_json()
