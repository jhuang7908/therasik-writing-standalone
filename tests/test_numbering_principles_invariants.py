"""
Test numbering and functional sites principles invariants

 schema/invariant ，。
， pipeline、action  runtime 。
"""

import pytest
import yaml
import sys
from pathlib import Path
from typing import Dict, List, Any

# Add project root to path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))


def load_functional_sites_yaml -> Dict[str, Any]:
    """Load functional_sites.yaml without any runtime dependencies."""
    yaml_path = project_root / "kb" / "10_parameters" / "functional_sites.yaml"
    if not yaml_path.exists:
        pytest.skip(f"YAML file not found: {yaml_path}")
    
    with open(yaml_path, 'r', encoding='utf-8') as f:
        data = yaml.safe_load(f)
    
    return data


def test_no_kabat_fields_in_site_definitions:
    """
    ： kabat_* 
    
     schema ，。
    """
    data = load_functional_sites_yaml
    functional_sites = data.get('functional_sites', [])
    
    forbidden_fields = []
    for site in functional_sites:
        for key in site.keys:
            if key.startswith('kabat_'):
                forbidden_fields.append({
                    'site_id': site.get('site_id', 'unknown'),
                    'field': key
                })
    
    assert len(forbidden_fields) == 0, (
        f"Found forbidden kabat_* fields in site definitions: {forbidden_fields}"
    )


def test_all_sites_have_anchor_scheme:
    """
    ： anchor_scheme 
    
     schema 。
    """
    data = load_functional_sites_yaml
    functional_sites = data.get('functional_sites', [])
    
    missing_anchor_scheme = []
    for site in functional_sites:
        if 'anchor_scheme' not in site:
            missing_anchor_scheme.append(site.get('site_id', 'unknown'))
    
    assert len(missing_anchor_scheme) == 0, (
        f"Sites missing anchor_scheme field: {missing_anchor_scheme}"
    )


def test_all_sites_have_chain_scope:
    """
    ： chain_scope 
    
     schema 。
    """
    data = load_functional_sites_yaml
    functional_sites = data.get('functional_sites', [])
    
    missing_chain_scope = []
    for site in functional_sites:
        if 'chain_scope' not in site:
            missing_chain_scope.append(site.get('site_id', 'unknown'))
    
    assert len(missing_chain_scope) == 0, (
        f"Sites missing chain_scope field: {missing_chain_scope}"
    )


def test_anchor_scheme_is_imgt:
    """
    ： anchor_scheme  "imgt"
    
     schema 。
    """
    data = load_functional_sites_yaml
    functional_sites = data.get('functional_sites', [])
    
    invalid_anchor_scheme = []
    for site in functional_sites:
        anchor_scheme = site.get('anchor_scheme')
        if anchor_scheme != 'imgt':
            invalid_anchor_scheme.append({
                'site_id': site.get('site_id', 'unknown'),
                'anchor_scheme': anchor_scheme
            })
    
    assert len(invalid_anchor_scheme) == 0, (
        f"Sites with invalid anchor_scheme (must be 'imgt'): {invalid_anchor_scheme}"
    )


def test_chain_scope_is_list:
    """
    ：chain_scope 
    
     schema 。
    """
    data = load_functional_sites_yaml
    functional_sites = data.get('functional_sites', [])
    
    invalid_chain_scope = []
    for site in functional_sites:
        chain_scope = site.get('chain_scope')
        if not isinstance(chain_scope, list):
            invalid_chain_scope.append({
                'site_id': site.get('site_id', 'unknown'),
                'chain_scope': chain_scope,
                'type': type(chain_scope).__name__
            })
    
    assert len(invalid_chain_scope) == 0, (
        f"Sites with invalid chain_scope type (must be list): {invalid_chain_scope}"
    )


def test_all_sites_have_imgt_positions:
    """
    ： imgt_positions 
    
     schema 。
    """
    data = load_functional_sites_yaml
    functional_sites = data.get('functional_sites', [])
    
    missing_imgt_positions = []
    for site in functional_sites:
        if 'imgt_positions' not in site:
            missing_imgt_positions.append(site.get('site_id', 'unknown'))
    
    assert len(missing_imgt_positions) == 0, (
        f"Sites missing imgt_positions field: {missing_imgt_positions}"
    )


def test_imgt_positions_is_list:
    """
    ：imgt_positions 
    
     schema 。
    """
    data = load_functional_sites_yaml
    functional_sites = data.get('functional_sites', [])
    
    invalid_imgt_positions = []
    for site in functional_sites:
        imgt_positions = site.get('imgt_positions')
        if not isinstance(imgt_positions, list):
            invalid_imgt_positions.append({
                'site_id': site.get('site_id', 'unknown'),
                'imgt_positions': imgt_positions,
                'type': type(imgt_positions).__name__
            })
    
    assert len(invalid_imgt_positions) == 0, (
        f"Sites with invalid imgt_positions type (must be list): {invalid_imgt_positions}"
    )


def test_required_fields_present:
    """
    ：
    
    ：site_id, role, imgt_positions, anchor_scheme, chain_scope
     schema 。
    """
    data = load_functional_sites_yaml
    functional_sites = data.get('functional_sites', [])
    
    required_fields = ['site_id', 'role', 'imgt_positions', 'anchor_scheme', 'chain_scope']
    
    missing_fields = []
    for site in functional_sites:
        site_id = site.get('site_id', 'unknown')
        for field in required_fields:
            if field not in site:
                missing_fields.append({
                    'site_id': site_id,
                    'missing_field': field
                })
    
    assert len(missing_fields) == 0, (
        f"Sites missing required fields: {missing_fields}"
    )


if __name__ == "__main__":
    pytest.main([__file__, "-v"])








