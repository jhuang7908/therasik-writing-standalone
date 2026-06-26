#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Rulebook v1.0
"""

import json
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT_ROOT))

from core.humanize.rulebook_v1 import RULEBOOK_V1, RuleLayer, RuleMode, RiskLevel, TargetRegion


def verify_rulebook_requirements():
    """Rulebook"""
    print("=" * 80)
    print("Rulebook v1.0 ")
    print("=" * 80)
    print()
    
    all_passed = True
    
    # 1. 
    print("1. ...")
    required_fields = [
        "rule_id", "layer", "target_region", "purpose", "evidence_level",
        "trigger_conditions", "action", "default_mode", "risk_level", "rationale_template"
    ]
    
    for rule_id, rule_def in RULEBOOK_V1.items():
        for field in required_fields:
            if not hasattr(rule_def, field):
                print(f"  ❌ {rule_id} : {field}")
                all_passed = False
            else:
                value = getattr(rule_def, field)
                if value is None and field not in ["excluded_positions", "excluded_rationale"]:
                    print(f"  ⚠️  {rule_id}  {field}  None")
    
    if all_passed:
        print("  ✅ ")
    print()
    
    # 2. Layer A
    print("2. Layer A...")
    layer_a_rules = [r for r in RULEBOOK_V1.values() if r.layer == RuleLayer.A]
    for rule in layer_a_rules:
        if not rule.rationale_explanation:
            print(f"  ❌ {rule.rule_id}  rationale_explanation")
            all_passed = False
        if not rule.excluded_positions:
            print(f"  ❌ {rule.rule_id}  excluded_positions")
            all_passed = False
        if not rule.excluded_rationale:
            print(f"  ❌ {rule.rule_id}  excluded_rationale")
            all_passed = False
    
    if all_passed:
        print("  ✅ Layer A")
    print()
    
    # 3. Layer B
    print("3. Layer B...")
    layer_b_rules = [r for r in RULEBOOK_V1.values() if r.layer == RuleLayer.B]
    anchor_rules = [r for r in layer_b_rules if "ANCHOR" in r.rule_id]
    tuning_rules = [r for r in layer_b_rules if "TUNING" in r.rule_id]
    
    print(f"  Vernier-Anchor: {len(anchor_rules)} ")
    for rule in anchor_rules:
        if rule.default_mode != RuleMode.EXPERT:
            print(f"  ⚠️  {rule.rule_id}  EXPERT， {rule.default_mode.value}")
        if rule.risk_level != RiskLevel.MEDIUM:
            print(f"  ⚠️  {rule.rule_id}  MEDIUM， {rule.risk_level.value}")
    
    print(f"  Vernier-Tuning: {len(tuning_rules)} ")
    for rule in tuning_rules:
        if rule.default_mode != RuleMode.MVP:
            print(f"  ⚠️  {rule.rule_id}  MVP， {rule.default_mode.value}")
        if rule.risk_level != RiskLevel.LOW:
            print(f"  ⚠️  {rule.rule_id}  LOW， {rule.risk_level.value}")
    
    print("  ✅ Layer B")
    print()
    
    # 4. JSON
    print("4. JSON...")
    json_path = Path("output/regression_test_7d12/classic_panel_rulebook_v1/vhh_classic_panel.json")
    if json_path.exists():
        with open(json_path, encoding="utf-8") as f:
            data = json.load(f)
        
        entry = data.get("classic_panel", [{}])[0]
        mutations = entry.get("mutations", [])
        
        required_mutation_fields = [
            "layer", "rule_id", "risk_level", "purpose", "evidence_level", "trigger_explanation"
        ]
        
        for mut in mutations:
            for field in required_mutation_fields:
                if field not in mut:
                    print(f"  ❌  {mut.get('rule_id')} : {field}")
                    all_passed = False
        
        if "rulebook_summary" not in data:
            print("  ❌ JSON rulebook_summary ")
            all_passed = False
        
        if all_passed:
            print("  ✅ JSON")
    else:
        print("  ⚠️  JSON")
    print()
    
    # 5. Markdown
    print("5. Markdown...")
    md_path = Path("output/regression_test_7d12/classic_panel_rulebook_v1/vhh_classic_panel.md")
    if md_path.exists():
        with open(md_path, encoding="utf-8") as f:
            content = f.read()
        
        if "## Rulebook Summary" not in content:
            print("  ❌ Markdown Rulebook Summary ")
            all_passed = False
        else:
            print("  ✅ Markdown Rulebook Summary ")
    else:
        print("  ⚠️  Markdown")
    print()
    
    # 
    print("=" * 80)
    if all_passed:
        print("✅ ！")
    else:
        print("❌ ，")
    print("=" * 80)
    
    return all_passed


if __name__ == "__main__":
    success = verify_rulebook_requirements()
    sys.exit(0 if success else 1)

