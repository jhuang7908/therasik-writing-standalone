#!/usr/bin/env python3
"""
Action Registry Validation Script

Validates that:
1. All actions referenced in kb/20_rules/*.yaml exist in ACTION_REGISTRY
2. All ACTION_REGISTRY keys conform to [a-z0-9_]+ naming standard
3. No orphan actions (in registry but not referenced in rules)

Exit code: 0 if all validations pass, non-zero otherwise

Options:
  --strict: Enable strict mode (orphan actions become errors)
"""

import argparse
import re
import sys
import yaml
from pathlib import Path
from typing import Set, List, Dict, Tuple

# Add project root to path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

# Import ACTION_REGISTRY
try:
    from pipeline.actions import ACTION_REGISTRY
except ImportError as e:
    print(f"ERROR: Failed to import ACTION_REGISTRY: {e}", file=sys.stderr)
    sys.exit(1)


def extract_actions_from_rules(rules_dir: Path) -> Tuple[Set[str], List[str]]:
    """
    Extract all action names from rule YAML files.
    
    Returns:
        Tuple of (actions_set, parse_errors_list)
    """
    actions = set()
    parse_errors = []
    
    for rule_file in rules_dir.glob("*.yaml"):
        try:
            with open(rule_file, 'r', encoding='utf-8') as f:
                data = yaml.safe_load(f)
            
            # Navigate through rules structure
            if 'rules' in data:
                for rule in data['rules']:
                    # Check decision.action (can be list or single string)
                    if 'decision' in rule and 'action' in rule['decision']:
                        action_value = rule['decision']['action']
                        if isinstance(action_value, list):
                            for action in action_value:
                                if isinstance(action, str):
                                    actions.add(action)
                        elif isinstance(action_value, str):
                            actions.add(action_value)
                    
                    # Check alternatives
                    if 'alternatives' in rule:
                        for alt in rule['alternatives']:
                            if 'decision' in alt and 'action' in alt['decision']:
                                action_value = alt['decision']['action']
                                if isinstance(action_value, list):
                                    for action in action_value:
                                        if isinstance(action, str):
                                            actions.add(action)
                                elif isinstance(action_value, str):
                                    actions.add(action_value)
        except Exception as e:
            error_msg = f"Failed to parse {rule_file}: {e}"
            parse_errors.append(error_msg)
    
    return actions, parse_errors


def validate_action_name(name: str) -> bool:
    """Check if action name conforms to [a-z0-9_]+ standard."""
    pattern = re.compile(r'^[a-z0-9_]+$')
    return bool(pattern.match(name))


def main():
    """Main validation logic."""
    # Parse command line arguments
    parser = argparse.ArgumentParser(
        description="Validate Action Registry against rule files",
        formatter_class=argparse.RawDescriptionHelpFormatter
    )
    parser.add_argument(
        '--strict',
        action='store_true',
        help='Enable strict mode: orphan actions become errors'
    )
    args = parser.parse_args()
    
    strict_mode = args.strict
    
    # Paths
    rules_dir = project_root / "kb" / "20_rules"
    
    if not rules_dir.exists():
        print(f"ERROR: Rules directory not found: {rules_dir}", file=sys.stderr)
        sys.exit(1)
    
    # Extract actions from rules
    rule_actions, parse_errors = extract_actions_from_rules(rules_dir)
    
    # Get registry actions
    registry_actions = set(ACTION_REGISTRY.keys())
    
    # Find missing actions (in rules but not in registry)
    missing_actions = rule_actions - registry_actions
    
    # Find orphan actions (in registry but not in rules)
    orphan_actions = registry_actions - rule_actions
    
    # Find invalid action names (in registry)
    invalid_action_names = [
        name for name in registry_actions
        if not validate_action_name(name)
    ]
    
    # Find invalid action names (in rules)
    invalid_rule_action_names = [
        name for name in rule_actions
        if not validate_action_name(name)
    ]
    
    # Report results
    errors = []
    warnings = []
    
    # YAML parse errors are always errors
    if parse_errors:
        for error in parse_errors:
            errors.append(error)
    
    if missing_actions:
        errors.append(f"Missing actions (in rules but not in registry): {sorted(missing_actions)}")
    
    if invalid_action_names:
        errors.append(f"Invalid action names in registry (must be [a-z0-9_]+): {sorted(invalid_action_names)}")
    
    if invalid_rule_action_names:
        errors.append(f"Invalid action names in rules (must be [a-z0-9_]+): {sorted(invalid_rule_action_names)}")
    
    if orphan_actions:
        if strict_mode:
            errors.append(f"Orphan actions (in registry but not referenced in rules): {sorted(orphan_actions)}")
        else:
            warnings.append(f"Orphan actions (in registry but not referenced in rules): {sorted(orphan_actions)}")
    
    # Print results
    print("=" * 80)
    print("Action Registry Validation Report")
    print("=" * 80)
    print(f"\nRules directory: {rules_dir}")
    print(f"Strict mode: {'ON' if strict_mode else 'OFF'}")
    print(f"Actions found in rules: {len(rule_actions)}")
    print(f"Actions in registry: {len(registry_actions)}")
    
    if errors:
        print("\n❌ ERRORS:")
        for error in errors:
            print(f"  - {error}")
    
    if warnings:
        print("\n⚠️  WARNINGS:")
        for warning in warnings:
            print(f"  - {warning}")
    
    if not errors and not warnings:
        print("\n✅ All validations passed!")
        print(f"\nAll {len(registry_actions)} actions are valid and referenced.")
    
    print("=" * 80)
    
    # Exit with error code if there are errors
    if errors:
        sys.exit(1)
    
    sys.exit(0)


if __name__ == "__main__":
    main()










