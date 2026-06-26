#!/usr/bin/env python3
"""
VHVL
"""

import json
import argparse
from pathlib import Path
from typing import Dict, Any


def merge_feature_dictionaries(vh_json_path: str, vl_json_path: str, out_json_path: str) -> Dict[str, Any]:
    """
    VHVL
    
    Args:
        vh_json_path: VHJSON
        vl_json_path: VLJSON
        out_json_path: JSON
    
    Returns:
        
    """
    with open(vh_json_path, 'r', encoding='utf-8') as f:
        vh_data = json.load(f)
    
    with open(vl_json_path, 'r', encoding='utf-8') as f:
        vl_data = json.load(f)
    
    # 
    assert vh_data["antibody"] == vl_data["antibody"]
    assert vh_data["pdb_id"] == vl_data["pdb_id"]
    assert vh_data["species"] == vl_data["species"]
    
    # chains
    merged_chains = {}
    merged_chains.update(vh_data["chains"])
    merged_chains.update(vl_data["chains"])
    
    result = {
        "antibody": vh_data["antibody"],
        "pdb_id": vh_data["pdb_id"],
        "species": vh_data["species"],
        "version": vh_data["version"],
        "chains": merged_chains
    }
    
    # 
    output_path = Path(out_json_path)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    
    with open(output_path, 'w', encoding='utf-8') as f:
        json.dump(result, f, indent=2, ensure_ascii=False)
    
    return result


def main:
    parser = argparse.ArgumentParser(
        description="Merge VH and VL feature dictionaries into a complete antibody feature dictionary"
    )
    parser.add_argument(
        "--vh_json",
        type=str,
        required=True,
        help="Path to VH feature dictionary JSON"
    )
    parser.add_argument(
        "--vl_json",
        type=str,
        required=True,
        help="Path to VL feature dictionary JSON"
    )
    parser.add_argument(
        "--out_json",
        type=str,
        required=True,
        help="Output merged JSON file path"
    )
    
    args = parser.parse_args
    
    print(f"📖 Reading VH features: {args.vh_json}")
    print(f"📖 Reading VL features: {args.vl_json}")
    
    result = merge_feature_dictionaries(args.vh_json, args.vl_json, args.out_json)
    
    print(f"✅ Merged feature dictionary generated: {args.out_json}")
    print(f"   Chains: {', '.join(result['chains'].keys)}")
    
    for chain_name, chain_data in result["chains"].items:
        num_features = len(chain_data["features"])
        print(f"   {chain_name}: {num_features} residues")


if __name__ == "__main__":
    main








