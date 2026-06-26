#!/usr/bin/env python3
"""
Functional Sites Validation Script

Validates that:
1. All required fields are present for each functional site
2. site_id values are unique
3. Position fields (imgt_positions, kabat_positions) are valid (lists of integers)
4. Required fields: site_id, role, imgt_positions, kabat_positions, scope, notes

Exit code: 0 if all validations pass, non-zero otherwise
"""

import sys
import yaml
from pathlib import Path
from typing import List, Dict, Any, Set

# Add project root to path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))


def validate_functional_sites(file_path: Path, has_lambda_sequences: bool = False) -> tuple[bool, List[str], Dict[str, Any]]:
    """
    Validate functional sites YAML file.
    
    Args:
        file_path: Path to functional_sites.yaml
        has_lambda_sequences: Whether lambda sequences are provided for mapping validation
        
    Returns:
        Tuple of (is_valid, error_messages, report)
        report contains:
        - vl_lambda_sites: List of VL_LAMBDA_* site_ids
        - skipped_sites: Sites skipped from mapping_status (if no λ sequences)
    """
    errors = []
    report = {
        "vl_lambda_sites": [],
        "skipped_sites": []
    }
    
    if not file_path.exists():
        return False, [f"File not found: {file_path}"], report
    
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            data = yaml.safe_load(f)
    except yaml.YAMLError as e:
        return False, [f"YAML parse error: {e}"], report
    except Exception as e:
        return False, [f"File read error: {e}"], report
    
    # Check top-level structure
    if 'functional_sites' not in data:
        return False, ["Missing required top-level key: 'functional_sites'"], report
    
    functional_sites = data['functional_sites']
    
    if not isinstance(functional_sites, list):
        return False, ["'functional_sites' must be a list"], report
    
    if len(functional_sites) == 0:
        return False, ["'functional_sites' list is empty"], report
    
    # Required fields for each site
    required_fields = ['site_id', 'role', 'imgt_positions', 'kabat_positions', 'scope', 'notes']
    
    # Optional fields (new in v1.1)
    optional_fields = ['chain_type', 'light_chain_type', 'imgt_anchor_positions', 'needs_calibration']
    
    # chain_type and light_chain_type are recommended but not strictly required for backward compatibility
    # However, VL_LAMBDA_* sites must have both chain_type="VL" and light_chain_type="lambda"
    
    # Track site_ids for uniqueness check
    site_ids: Set[str] = set()
    
    # Validate each site
    for idx, site in enumerate(functional_sites):
        if not isinstance(site, dict):
            errors.append(f"Site at index {idx} is not a dictionary")
            continue
        
        # Check required fields
        for field in required_fields:
            if field not in site:
                errors.append(f"Site at index {idx}: missing required field '{field}'")
        
        # Validate site_id
        if 'site_id' in site:
            site_id = site['site_id']
            if not isinstance(site_id, str):
                errors.append(f"Site at index {idx}: 'site_id' must be a string")
            elif site_id in site_ids:
                errors.append(f"Site at index {idx}: duplicate 'site_id' '{site_id}'")
            else:
                site_ids.add(site_id)
        
        # Validate role
        if 'role' in site:
            role = site['role']
            valid_roles = ['hallmark', 'vernier', 'fr_cdr_boundary', 'anchor']
            if role not in valid_roles:
                errors.append(
                    f"Site at index {idx} (site_id: {site.get('site_id', 'unknown')}): "
                    f"invalid 'role' '{role}'. Must be one of: {valid_roles}"
                )
        
        # Validate chain_type (optional but recommended)
        site_id = site.get('site_id', 'unknown')
        if 'chain_type' in site:
            chain_type = site['chain_type']
            valid_chain_types = ['VHH', 'VH', 'VL']
            if chain_type not in valid_chain_types:
                errors.append(
                    f"Site at index {idx} (site_id: {site_id}): "
                    f"invalid 'chain_type' '{chain_type}'. Must be one of: {valid_chain_types}"
                )
        
        # Validate light_chain_type (optional but required for VL_LAMBDA_* sites)
        if 'light_chain_type' in site:
            light_chain_type = site['light_chain_type']
            if light_chain_type is not None and light_chain_type not in ['kappa', 'lambda']:
                errors.append(
                    f"Site at index {idx} (site_id: {site_id}): "
                    f"invalid 'light_chain_type' '{light_chain_type}'. Must be one of: kappa, lambda, null"
                )
        
        # Special validation for VL_LAMBDA_* sites
        if site_id.startswith('VL_LAMBDA_'):
            if site.get('chain_type') != 'VL':
                errors.append(
                    f"Site at index {idx} (site_id: {site_id}): "
                    f"VL_LAMBDA_* sites must have chain_type='VL'"
                )
            if site.get('light_chain_type') != 'lambda':
                errors.append(
                    f"Site at index {idx} (site_id: {site_id}): "
                    f"VL_LAMBDA_* sites must have light_chain_type='lambda'"
                )
            if 'needs_calibration' not in site or not site.get('needs_calibration'):
                # Warn but don't error - needs_calibration is recommended for placeholder sites
                pass
        
        # Validate imgt_anchor_positions (optional, for VL-λ sites)
        if 'imgt_anchor_positions' in site:
            imgt_anchor_positions = site['imgt_anchor_positions']
            if not isinstance(imgt_anchor_positions, list):
                errors.append(
                    f"Site at index {idx} (site_id: {site.get('site_id', 'unknown')}): "
                    f"'imgt_anchor_positions' must be a list"
                )
            else:
                for pos_idx, pos in enumerate(imgt_anchor_positions):
                    if not isinstance(pos, int):
                        errors.append(
                            f"Site at index {idx} (site_id: {site.get('site_id', 'unknown')}): "
                            f"'imgt_anchor_positions[{pos_idx}]' must be an integer, got {type(pos).__name__}"
                        )
                    elif pos < 1 or pos > 150:
                        errors.append(
                            f"Site at index {idx} (site_id: {site.get('site_id', 'unknown')}): "
                            f"'imgt_anchor_positions[{pos_idx}]' = {pos} is out of valid range [1, 150]"
                        )
        
        # Validate needs_calibration (optional, boolean)
        if 'needs_calibration' in site:
            needs_calibration = site['needs_calibration']
            if not isinstance(needs_calibration, bool):
                errors.append(
                    f"Site at index {idx} (site_id: {site.get('site_id', 'unknown')}): "
                    f"'needs_calibration' must be a boolean"
                )
        
        # Check for VL_LAMBDA_* sites (will be collected after validation loop)
        
        # Validate imgt_positions
        if 'imgt_positions' in site:
            imgt_positions = site['imgt_positions']
            if not isinstance(imgt_positions, list):
                errors.append(
                    f"Site at index {idx} (site_id: {site.get('site_id', 'unknown')}): "
                    f"'imgt_positions' must be a list"
                )
            else:
                for pos_idx, pos in enumerate(imgt_positions):
                    if not isinstance(pos, int):
                        errors.append(
                            f"Site at index {idx} (site_id: {site.get('site_id', 'unknown')}): "
                            f"'imgt_positions[{pos_idx}]' must be an integer, got {type(pos).__name__}"
                        )
                    elif pos < 1 or pos > 150:
                        errors.append(
                            f"Site at index {idx} (site_id: {site.get('site_id', 'unknown')}): "
                            f"'imgt_positions[{pos_idx}]' = {pos} is out of valid range [1, 150]"
                        )
        
        # Validate kabat_positions
        if 'kabat_positions' in site:
            kabat_positions = site['kabat_positions']
            if not isinstance(kabat_positions, list):
                errors.append(
                    f"Site at index {idx} (site_id: {site.get('site_id', 'unknown')}): "
                    f"'kabat_positions' must be a list"
                )
            else:
                for pos_idx, pos in enumerate(kabat_positions):
                    if not isinstance(pos, int):
                        errors.append(
                            f"Site at index {idx} (site_id: {site.get('site_id', 'unknown')}): "
                            f"'kabat_positions[{pos_idx}]' must be an integer, got {type(pos).__name__}"
                        )
                    elif pos < 1 or pos > 150:
                        errors.append(
                            f"Site at index {idx} (site_id: {site.get('site_id', 'unknown')}): "
                            f"'kabat_positions[{pos_idx}]' = {pos} is out of valid range [1, 150]"
                        )
        
        # Validate scope
        if 'scope' in site:
            scope = site['scope']
            if not isinstance(scope, list):
                errors.append(
                    f"Site at index {idx} (site_id: {site.get('site_id', 'unknown')}): "
                    f"'scope' must be a list"
                )
        
        # Validate notes
        if 'notes' in site:
            notes = site['notes']
            if not isinstance(notes, str):
                errors.append(
                    f"Site at index {idx} (site_id: {site.get('site_id', 'unknown')}): "
                    f"'notes' must be a string"
                )
    
    # Collect VL_LAMBDA_* sites after validation loop
    # These sites are allowed to exist but will be skipped from mapping_status statistics
    # if no lambda sequences are provided
    for site in functional_sites:
        if not isinstance(site, dict):
            continue
        site_id = site.get('site_id', '')
        if site_id.startswith('VL_LAMBDA_'):
            report["vl_lambda_sites"].append(site_id)
            if not has_lambda_sequences:
                report["skipped_sites"].append({
                    "site_id": site_id,
                    "skipped_reason": "no_lambda_sequences_provided",
                    "note": "VL_LAMBDA_* sites are excluded from mapping_status statistics when no λ sequences are provided"
                })
    
    is_valid = len(errors) == 0
    return is_valid, errors, report


def main():
    """Main validation logic."""
    import argparse
    
    parser = argparse.ArgumentParser(
        description="Validate functional sites YAML file",
        formatter_class=argparse.RawDescriptionHelpFormatter
    )
    parser.add_argument(
        '--has_lambda_sequences',
        action='store_true',
        help='Indicate that lambda sequences are provided (affects VL_LAMBDA_* site validation)'
    )
    args = parser.parse_args()
    
    # Path to functional_sites.yaml
    sites_file = project_root / "kb" / "10_parameters" / "functional_sites.yaml"
    
    # Validate
    is_valid, errors, report = validate_functional_sites(sites_file, has_lambda_sequences=args.has_lambda_sequences)
    
    # Print results
    print("=" * 80)
    print("Functional Sites Validation Report")
    print("=" * 80)
    print(f"\nFile: {sites_file}")
    
    if is_valid:
        print("\n✅ All validations passed!")
        print("\nFunctional sites file is valid.")
        
        # Report VL-λ sites
        if report["vl_lambda_sites"]:
            print(f"\n📋 VL-λ sites found: {len(report['vl_lambda_sites'])}")
            for site_id in report["vl_lambda_sites"]:
                print(f"    - {site_id}")
            
            if report["skipped_sites"]:
                print(f"\n⚠️  Skipped sites (no λ sequences provided): {len(report['skipped_sites'])}")
                for skipped in report["skipped_sites"]:
                    print(f"    - {skipped['site_id']}: {skipped['skipped_reason']}")
    else:
        print("\n❌ VALIDATION ERRORS:")
        for error in errors:
            print(f"  - {error}")
    
    print("=" * 80)
    
    # Exit with error code if validation failed
    if not is_valid:
        sys.exit(1)
    
    sys.exit(0)


if __name__ == "__main__":
    main()










