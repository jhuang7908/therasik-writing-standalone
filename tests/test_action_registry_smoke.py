"""
Smoke test for Action Registry

Minimal test to ensure:
1. ACTION_REGISTRY can be imported
2. run_actions() function works
3. Actions can be executed (even if they return empty patches)
"""

import pytest
from pipeline.actions import ACTION_REGISTRY, run_actions


def test_action_registry_import():
    """Test that ACTION_REGISTRY can be imported."""
    assert ACTION_REGISTRY is not None
    assert isinstance(ACTION_REGISTRY, dict)
    assert len(ACTION_REGISTRY) > 0


def test_action_registry_has_actions():
    """Test that ACTION_REGISTRY contains expected actions."""
    # Check for a few key actions
    expected_actions = [
        "extract_variable_domain_best_effort",
        "renumber_primary_imgt",
        "annotate_epitopes_with_regions_and_interface_adjacency",
        "propose_repair_mutations_from_policy",
        "emit_topn",
    ]
    
    for action_name in expected_actions:
        assert action_name in ACTION_REGISTRY, f"Action '{action_name}' not found in registry"


def test_run_actions_basic():
    """Test that run_actions() can execute actions without errors."""
    context = {
        "project_id": "test_project",
        "input": {
            "sequence": {
                "aa": "EVQLVESGGGLVQPGGSLRLSCAAS"
            }
        }
    }
    
    # Test with a simple action that should work even as stub
    actions = ["extract_variable_domain_best_effort"]
    
    try:
        result = run_actions(context, actions)
        assert result is not None
        assert isinstance(result, dict)
    except KeyError as e:
        pytest.fail(f"Action execution failed: {e}")
    except Exception as e:
        pytest.fail(f"Unexpected error during action execution: {e}")


def test_run_actions_multiple():
    """Test that run_actions() can execute multiple actions in sequence."""
    context = {
        "project_id": "test_project",
        "input": {
            "sequence": {
                "aa": "EVQLVESGGGLVQPGGSLRLSCAAS"
            }
        }
    }
    
    actions = [
        "extract_variable_domain_best_effort",
        "renumber_primary_imgt"
    ]
    
    try:
        result = run_actions(context, actions)
        assert result is not None
        assert isinstance(result, dict)
    except KeyError as e:
        pytest.fail(f"Action execution failed: {e}")
    except Exception as e:
        pytest.fail(f"Unexpected error during action execution: {e}")


def test_run_actions_invalid_action():
    """Test that run_actions() raises KeyError for invalid action names."""
    context = {"project_id": "test"}
    
    with pytest.raises(KeyError):
        run_actions(context, ["nonexistent_action_xyz"])


def test_action_naming_standard():
    """Test that all action names conform to [a-z0-9_]+ standard."""
    import re
    pattern = re.compile(r'^[a-z0-9_]+$')
    
    invalid_names = [
        name for name in ACTION_REGISTRY.keys()
        if not pattern.match(name)
    ]
    
    if invalid_names:
        pytest.fail(
            f"Action names do not conform to [a-z0-9_]+ standard: {invalid_names}"
        )










