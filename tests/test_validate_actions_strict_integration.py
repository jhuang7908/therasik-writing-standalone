"""
Integration test for validate_actions.py strict mode with orphan actions.

This test creates a scenario where orphan actions exist to verify strict mode behavior.
"""

import subprocess
import sys
import tempfile
import pytest
from pathlib import Path
import shutil


def test_strict_mode_orphan_actions_fail():
    """
    Test that strict mode fails when orphan actions exist.
    
    This test temporarily backs up real rules, creates minimal rules,
    then restores, to test orphan action detection.
    """
    script_path = Path(__file__).parent.parent / "tools" / "validate_actions.py"
    rules_dir = Path(__file__).parent.parent / "kb" / "20_rules"
    backup_dir = rules_dir.parent / "20_rules_backup_test"
    
    # Backup existing rules
    if backup_dir.exists():
        shutil.rmtree(backup_dir)
    shutil.copytree(rules_dir, backup_dir)
    
    try:
        # Create a minimal rules file with only one action
        # This will make most registry actions appear as orphans
        minimal_rules_file = rules_dir / "test_minimal_rules.yaml"
        minimal_rules_file.write_text("""meta:
  id: "TEST_MINIMAL"
  title: "Test Minimal Rules"
  scope: [general]
  confidence: "S"
  owner: "test"
  reviewer: "test"
  created: "2025-01-01"
  updated: "2025-01-01"
  status: "active"

rules:
  - id: "TEST_RULE_001"
    scope: [general]
    confidence: "S"
    trigger:
      eq: ["test.field", true]
    decision:
      action:
        - "extract_variable_domain_best_effort"
      set:
        test.status: "ok"
    rationale: "Test rule"
    alternatives: []
    deprecated: false

evidence:
  rationale: "Test"
  sources: []
  internal_validation: []

governance:
  change_log:
    - change_type: "create"
      change_summary: "Test rule"
      owner: "test"
      reviewer: "test"
      date: "2025-01-01"
""", encoding='utf-8')
        
        # Temporarily move real rules out of the way
        real_rules = [f for f in rules_dir.glob("*.yaml") if f.name != "test_minimal_rules.yaml"]
        temp_rules_dir = rules_dir.parent / "20_rules_temp"
        if temp_rules_dir.exists():
            shutil.rmtree(temp_rules_dir)
        temp_rules_dir.mkdir()
        
        for rule_file in real_rules:
            shutil.move(str(rule_file), str(temp_rules_dir / rule_file.name))
        
        try:
            # Test default mode - should pass (orphan actions are warnings)
            result_default = subprocess.run(
                [sys.executable, str(script_path)],
                capture_output=True,
                text=True,
                cwd=Path(__file__).parent.parent
            )
            
            # Default mode should pass even with orphan actions
            assert result_default.returncode == 0, "Default mode should pass with orphan actions"
            assert "Strict mode: OFF" in result_default.stdout
            assert "Orphan actions" in result_default.stdout
            assert "WARNINGS:" in result_default.stdout or "⚠️  WARNINGS:" in result_default.stdout
            
            # Test strict mode - should fail (orphan actions are errors)
            result_strict = subprocess.run(
                [sys.executable, str(script_path), "--strict"],
                capture_output=True,
                text=True,
                cwd=Path(__file__).parent.parent
            )
            
            # Strict mode should fail with orphan actions
            assert result_strict.returncode != 0, "Strict mode should fail when orphan actions exist"
            assert "Strict mode: ON" in result_strict.stdout
            assert "Orphan actions" in result_strict.stdout
            assert "ERRORS:" in result_strict.stdout or "❌ ERRORS:" in result_strict.stdout
            
        finally:
            # Restore real rules
            for rule_file in temp_rules_dir.glob("*.yaml"):
                shutil.move(str(rule_file), str(rules_dir / rule_file.name))
            shutil.rmtree(temp_rules_dir)
            if minimal_rules_file.exists():
                minimal_rules_file.unlink()
            
            # Clean up any test files that might have been created
            for f in rules_dir.glob("test_*.yaml"):
                try:
                    f.unlink()
                except Exception:
                    pass
            
            # Clean up backup directory (ignore errors on Windows)
            if backup_dir.exists():
                try:
                    shutil.rmtree(backup_dir)
                except (PermissionError, OSError):
                    # On Windows, sometimes files are locked
                    # This is okay for a test cleanup
                    pass










