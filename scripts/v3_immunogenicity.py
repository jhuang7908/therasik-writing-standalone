#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
v3_immunogenicity.py

V3 。

 v2_cmc_repair  V2 ，，
 IEDB API 。

：
    python scripts/v3_immunogenicity.py --project EGFR_7D12_VHH
    python scripts/v3_immunogenicity.py --project EGFR_7D12_VHH --use-iedb
"""

import argparse
import json
import sys
from pathlib import Path
from typing import Dict, List, Any, Optional

# Add project root to path
project_root = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(project_root))

# Try to import IEDB client
try:
    from scripts.iedb_client import predict_mhcii_binding, IEDBRequestConfig, IEDBError
    IEDB_AVAILABLE = True
except ImportError:
    IEDB_AVAILABLE = False
    print("[WARN] IEDB client not available. Install requests library if needed.")


# ---------------------------------------------------------------------------
# HLA Class II panels for immunogenicity analysis
# ---------------------------------------------------------------------------

#  15 （ ~90%，）
CORE15_HLA_ALLELES = [
    "HLA-DRB1*01:01",
    "HLA-DRB1*03:01",
    "HLA-DRB1*04:01",
    "HLA-DRB1*07:01",
    "HLA-DRB1*08:02",
    "HLA-DRB1*09:01",
    "HLA-DRB1*10:01",
    "HLA-DRB1*11:01",
    "HLA-DRB1*12:01",
    "HLA-DRB1*13:01",
    "HLA-DRB1*14:01",
    "HLA-DRB1*15:01",
    "HLA-DRB1*16:01",
    "HLA-DRB3*02:02",
    "HLA-DRB5*01:01",
]

#  27 （ ≥97%，）
EXT27_HLA_ALLELES = [
    "HLA-DRB1*01:01",
    "HLA-DRB1*01:02",
    "HLA-DRB1*03:01",
    "HLA-DRB1*03:02",
    "HLA-DRB1*04:01",
    "HLA-DRB1*04:02",
    "HLA-DRB1*04:04",
    "HLA-DRB1*04:05",
    "HLA-DRB1*07:01",
    "HLA-DRB1*08:01",
    "HLA-DRB1*08:02",
    "HLA-DRB1*09:01",
    "HLA-DRB1*10:01",
    "HLA-DRB1*11:01",
    "HLA-DRB1*12:01",
    "HLA-DRB1*13:01",
    "HLA-DRB1*13:02",
    "HLA-DRB1*14:01",
    "HLA-DRB1*14:04",
    "HLA-DRB1*15:01",
    "HLA-DRB1*15:02",
    "HLA-DRB1*16:01",
    "HLA-DRB3*01:01",
    "HLA-DRB3*02:02",
    "HLA-DRB4*01:01",
    "HLA-DRB5*01:01",
    "HLA-DRB5*02:02",
]

#  27 
DEFAULT_HLA_ALLELES = EXT27_HLA_ALLELES


def load_v2_library(project_name: str, base_dir: Optional[Path] = None) -> Dict[str, Any]:
    """
     V2 。
    
    Args:
        project_name: 
        base_dir: （：）
        
    Returns:
        V2 
        
    Raises:
        FileNotFoundError: 
        ValueError:  JSON 
    """
    if base_dir is None:
        base_dir = project_root
    
    v2_file = base_dir / "projects" / project_name / "v2_cmc_repair" / "result_v2.json"
    
    if not v2_file.exists():
        raise FileNotFoundError(f"V2 library not found: {v2_file}")
    
    try:
        with open(v2_file, 'r', encoding='utf-8') as f:
            data = json.load(f)
    except json.JSONDecodeError as e:
        raise ValueError(f"Failed to parse V2 library JSON: {e}")
    
    return data


def analyze_immunogenicity_offline(sequence: str) -> Dict[str, Any]:
    """
    （）。
    
    Args:
        sequence: 
        
    Returns:
        
    """
    # 
    # 、
    
    human_aa = set('ACDEFGHIKLMNPQRSTVWY')
    camelid_typical = {'F', 'R', 'Q', 'K'}  # 
    
    non_human_count = sum(1 for aa in sequence if aa in camelid_typical)
    total_aa = len(sequence)
    non_human_ratio = non_human_count / total_aa if total_aa > 0 else 0
    
    # 
    if non_human_ratio > 0.15:
        risk_level = "high"
    elif non_human_ratio > 0.08:
        risk_level = "medium"
    else:
        risk_level = "low"
    
    return {
        "method": "offline_heuristic",
        "non_human_aa_count": non_human_count,
        "non_human_aa_ratio": round(non_human_ratio, 4),
        "risk_level": risk_level,
        "tcell_epitopes": [],  # 
        "hla_binding_predictions": []
    }


def analyze_immunogenicity_iedb(sequence: str, alleles: List[str]) -> Dict[str, Any]:
    """
     IEDB API 。
    
    Args:
        sequence: 
        alleles: HLA 
        
    Returns:
        
        
    Raises:
        IEDBError:  IEDB API 
    """
    try:
        config = IEDBRequestConfig(method="recommended", length="15")
        predictions = predict_mhcii_binding(sequence, alleles, config)
        
        # 
        strong_binders = []
        weak_binders = []
        
        for pred in predictions:
            # IEDB  rank, ic50 
            percent_rank = float(pred.get('rank', '999'))
            ic50 = float(pred.get('ic50', '99999'))
            
            #  IEDB ：percent_rank < 2% ，< 10% 
            if percent_rank < 2.0:
                strong_binders.append(pred)
            elif percent_rank < 10.0:
                weak_binders.append(pred)
        
        # 
        if len(strong_binders) > 5:
            risk_level = "high"
        elif len(strong_binders) > 2:
            risk_level = "medium"
        else:
            risk_level = "low"
        
        return {
            "method": "iedb_online",
            "alleles_tested": alleles,
            "total_predictions": len(predictions),
            "strong_binders": len(strong_binders),
            "weak_binders": len(weak_binders),
            "risk_level": risk_level,
            "tcell_epitopes": strong_binders[:10],  # 10
            "hla_binding_predictions": predictions[:20]  # 20
        }
        
    except IEDBError as e:
        print(f"[WARN] IEDB API error: {e}", file=sys.stderr)
        # 
        return analyze_immunogenicity_offline(sequence)


def process_v2_variants(v2_library: Dict[str, Any], use_iedb: bool = False, 
                       alleles: Optional[List[str]] = None) -> Dict[str, Any]:
    """
     V2 ，。
    
    Args:
        v2_library: V2 
        use_iedb:  IEDB API
        alleles: HLA （ None，）
        
    Returns:
        
    """
    if alleles is None:
        alleles = DEFAULT_HLA_ALLELES
    
    results = {
        "source_v2_library": v2_library.get("source_result", "unknown"),
        "analysis_method": "iedb_online" if use_iedb else "offline_heuristic",
        "hla_alleles": alleles if use_iedb else [],
        "variants": []
    }
    
    v2_lib = v2_library.get("v2_library", [])
    
    for parent in v2_lib:
        parent_id = parent.get("parent_id", "unknown")
        parent_seq = parent.get("parent_sequence", "")
        v2_variants = parent.get("v2_variants", {})
        
        parent_result = {
            "parent_id": parent_id,
            "parent_sequence": parent_seq,
            "parent_analysis": {},
            "v2_variants_analysis": {}
        }
        
        #  parent 
        if use_iedb and IEDB_AVAILABLE:
            try:
                parent_result["parent_analysis"] = analyze_immunogenicity_iedb(parent_seq, alleles)
            except Exception as e:
                print(f"[WARN] Failed to analyze parent {parent_id} with IEDB: {e}", file=sys.stderr)
                parent_result["parent_analysis"] = analyze_immunogenicity_offline(parent_seq)
        else:
            parent_result["parent_analysis"] = analyze_immunogenicity_offline(parent_seq)
        
        #  V2 
        for v2_name, v2_data in v2_variants.items():
            v2_seq = v2_data.get("sequence", "")
            
            if use_iedb and IEDB_AVAILABLE:
                try:
                    v2_analysis = analyze_immunogenicity_iedb(v2_seq, alleles)
                except Exception as e:
                    print(f"[WARN] Failed to analyze {v2_name} with IEDB: {e}", file=sys.stderr)
                    v2_analysis = analyze_immunogenicity_offline(v2_seq)
            else:
                v2_analysis = analyze_immunogenicity_offline(v2_seq)
            
            parent_result["v2_variants_analysis"][v2_name] = {
                "sequence": v2_seq,
                "mutations": v2_data.get("mutations", []),
                "immunogenicity": v2_analysis
            }
        
        results["variants"].append(parent_result)
    
    return results


def main():
    parser = argparse.ArgumentParser(
        description="Perform immunogenicity analysis on V2 variants",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  %(prog)s --project EGFR_7D12_VHH
  %(prog)s --project EGFR_7D12_VHH --use-iedb
  %(prog)s --project EGFR_7D12_VHH --use-iedb --alleles HLA-DRB1*01:01 HLA-DRB1*04:01
        """
    )
    
    parser.add_argument(
        "--project", "-p",
        type=str,
        required=True,
        help="， EGFR_7D12_VHH"
    )
    
    parser.add_argument(
        "--base-dir", "-b",
        type=str,
        default=str(project_root),
        help="（：）"
    )
    
    parser.add_argument(
        "--use-iedb",
        action="store_true",
        help=" IEDB API （）"
    )
    
    parser.add_argument(
        "--hla-panel",
        choices=["core15", "ext27"],
        default="ext27",
        help=" HLA ：core15  ext27（：ext27）。 --alleles， --alleles 。"
    )
    
    parser.add_argument(
        "--alleles",
        nargs="+",
        default=None,
        help="HLA （：）"
    )
    
    parser.add_argument(
        "--output", "-o",
        type=str,
        default=None,
        help="（：/v3_immunogenicity/result_v3.json）"
    )
    
    args = parser.parse_args()
    
    try:
        # Load V2 library
        base_dir = Path(args.base_dir).resolve()
        print(f"Loading V2 library for project: {args.project}")
        v2_library = load_v2_library(args.project, base_dir)
        
        #  HLA ： --alleles， --hla-panel 
        if args.alleles is not None:
            selected_alleles = args.alleles
        else:
            if args.hla_panel == "core15":
                selected_alleles = CORE15_HLA_ALLELES
            else:
                selected_alleles = EXT27_HLA_ALLELES
        
        # Process variants
        print(f"Analyzing immunogenicity (method: {'IEDB online' if args.use_iedb else 'offline heuristic'})...")
        print(f"Using HLA panel: {args.hla_panel} ({len(selected_alleles)} alleles)")
        results = process_v2_variants(
            v2_library,
            use_iedb=args.use_iedb,
            alleles=selected_alleles
        )
        
        # Determine output path
        if args.output:
            output_path = Path(args.output)
        else:
            output_path = base_dir / "projects" / args.project / "v3_immunogenicity" / "result_v3.json"
        
        output_path.parent.mkdir(parents=True, exist_ok=True)
        
        # Write results
        print(f"Writing results to: {output_path}")
        with open(output_path, 'w', encoding='utf-8') as f:
            json.dump(results, f, indent=2, ensure_ascii=False)
        
        # Print summary
        print("\n" + "=" * 60)
        print("Immunogenicity Analysis Summary")
        print("=" * 60)
        print(f"Method: {results['analysis_method']}")
        print(f"Total parent variants: {len(results['variants'])}")
        
        for variant in results['variants']:
            parent_id = variant['parent_id']
            parent_risk = variant['parent_analysis'].get('risk_level', 'unknown')
            print(f"\n{parent_id}:")
            print(f"  Parent risk: {parent_risk}")
            for v2_name, v2_data in variant['v2_variants_analysis'].items():
                v2_risk = v2_data['immunogenicity'].get('risk_level', 'unknown')
                print(f"  {v2_name}: {v2_risk}")
        
        print("=" * 60)
        print(f"Results saved to: {output_path}")
        
    except FileNotFoundError as e:
        print(f"Error: {e}", file=sys.stderr)
        sys.exit(1)
    except ValueError as e:
        print(f"Error: {e}", file=sys.stderr)
        sys.exit(1)
    except KeyboardInterrupt:
        print("\nInterrupted by user", file=sys.stderr)
        sys.exit(1)
    except Exception as e:
        print(f"Unexpected error: {e}", file=sys.stderr)
        import traceback
        traceback.print_exc()
        sys.exit(1)


if __name__ == "__main__":
    main()

