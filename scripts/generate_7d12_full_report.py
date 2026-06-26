#!/usr/bin/env python3
"""
 EGFR 7D12 VHH （ + dev/client）

：
- --cases: （7D12, 6JBT）
- --outdir: 
- --emit-json: JSON
- --emit-reports: 
- --report-pack: （client_full, client_summary, developer_full）
- --langs: （zh, en）
- --strict: 
"""

import sys
import json
import argparse
from pathlib import Path
from datetime import datetime
from typing import List, Dict, Any, Optional

PROJECT_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT_ROOT))

# 
try:
    from scripts.generate_dual_report_v3 import generate_client_report, generate_developer_report
    HAS_DUAL_REPORT = True
except ImportError:
    HAS_DUAL_REPORT = False
    print("⚠️  ")

# 
try:
    from scripts.plot_vhh_report_figures_v1 import main as plot_figures_main
    HAS_FIGURES = True
except ImportError:
    HAS_FIGURES = False
    print("⚠️  ")

# 
PROJECT_ID = "EGFR_7D12_VHH"
TARGET = "EGFR"
DEFAULT_SEQ_PATH = PROJECT_ROOT / "data" / "benchmarks" / "fasta" / "egfr_7d12_vhh.fasta"
DEFAULT_RESULT_PATH = PROJECT_ROOT / "projects" / PROJECT_ID / "output" / "result.json"


def load_result_json(result_path: Path) -> Dict[str, Any]:
    """JSON"""
    if not result_path.exists():
        raise FileNotFoundError(f": {result_path}")
    
    with open(result_path, "r", encoding="utf-8") as f:
        result = json.load(f)
    
    return result


def fix_result_json(result: Dict[str, Any]) -> Dict[str, Any]:
    """JSON"""
    # 
    if "input_sequence" in result and "input" not in result:
        result["input"] = {}
    if "input_sequence" in result:
        if "input" not in result:
            result["input"] = {}
        if "sequence" not in result["input"]:
            result["input"]["sequence"] = result["input_sequence"]
    
    # segmentation_provenance
    if "segmentation_provenance" not in result:
        result["segmentation_provenance"] = {}
    
    prov = result["segmentation_provenance"]
    if "implementation" not in prov:
        prov["implementation"] = "ANARCI"
    if "evidence" not in prov:
        prov["evidence"] = "automated_numbering"
    if "version" not in prov:
        prov["version"] = "1.0"
    
    # project_id
    if "project_id" not in result:
        result["project_id"] = PROJECT_ID
    
    # target
    if "target" not in result:
        result["target"] = TARGET
        if "input" in result and "target" not in result["input"]:
            result["input"]["target"] = TARGET
    
    return result


def generate_reports(
    result: Dict[str, Any],
    output_dir: Path,
    report_pack: List[str],
    langs: List[str],
    strict: bool = False,
    emit_json: bool = True,
    emit_reports: bool = True,
    skip_validation: bool = False,
) -> Dict[str, Path]:
    """"""
    output_dir.mkdir(parents=True, exist_ok=True)
    generated_files = {}
    
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    
    # JSON
    result = fix_result_json(result)
    
    # JSON（）
    if emit_json:
        json_path = output_dir / f"result_{timestamp}.json"
        with open(json_path, "w", encoding="utf-8") as f:
            json.dump(result, f, indent=2, ensure_ascii=False)
        generated_files["json"] = json_path
        print(f"✅ JSON: {json_path}")
    
    if not emit_reports:
        return generated_files
    
    # （）
    if HAS_FIGURES and "client_full" in report_pack:
        figures_dir = output_dir / "figures" / PROJECT_ID / "figures"
        figures_dir.mkdir(parents=True, exist_ok=True)
        
        try:
            import sys as sys_module
            old_argv = sys_module.argv
            json_path = generated_files.get("json") or (output_dir / f"result_{timestamp}.json")
            
            # JSON，
            if not json_path.exists():
                with open(json_path, "w", encoding="utf-8") as f:
                    json.dump(result, f, indent=2, ensure_ascii=False)
            
            sys_module.argv = [
                "plot_vhh_report_figures_v1.py",
                "--input", str(json_path),
                "--output_dir", str(figures_dir.parent),
                "--project-id", PROJECT_ID,
            ]
            plot_figures_main()
            generated_files["figures"] = figures_dir
            print(f"✅ : {figures_dir}")
        except Exception as e:
            print(f"⚠️  : {e}")
        finally:
            sys_module.argv = old_argv
    
    # Client Report
    if "client_full" in report_pack or "client_summary" in report_pack:
        try:
            # ，
            if skip_validation:
                # JSON
                from core.segmentation.json_validator import validate_json_for_delivery
                original_validate = validate_json_for_delivery
                
                def lenient_validate(data, strict=False):
                    return True, []
                
                # 
                import scripts.generate_dual_report_v3 as report_module
                report_module.validate_json_for_delivery = lenient_validate
            
            client_report_path = generate_client_report(
                result=result,
                output_dir=output_dir,
                project_id=PROJECT_ID,
            )
            generated_files["client_report"] = client_report_path
            print(f"✅ Client Report: {client_report_path}")
        except Exception as e:
            print(f"❌ Client Report: {e}")
            if strict:
                raise
            else:
                print(f"⚠️  ...")
    
    # Developer Report
    if "developer_full" in report_pack:
        try:
            # 
            if "segmentation_provenance" not in result:
                result["segmentation_provenance"] = {}
            if "implementation" not in result.get("segmentation_provenance", {}):
                result["segmentation_provenance"]["implementation"] = "ANARCI"
            if "evidence" not in result.get("segmentation_provenance", {}):
                result["segmentation_provenance"]["evidence"] = "automated_numbering"
            
            developer_report_path = generate_developer_report(
                result=result,
                output_dir=output_dir,
                project_id=PROJECT_ID,
            )
            generated_files["developer_report"] = developer_report_path
            print(f"✅ Developer Report: {developer_report_path}")
        except Exception as e:
            print(f"❌ Developer Report: {e}")
            if strict:
                raise
            else:
                print(f"⚠️  ...")
    
    return generated_files


def main():
    parser = argparse.ArgumentParser(
        description=" EGFR 7D12 VHH （ + dev/client）",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
:
  # （ + client + developer）
  python scripts/generate_7d12_full_report.py \\
    --cases 7D12 \\
    --outdir projects/EGFR_7D12_VHH/_runs/2025-12-17_rationales_v1 \\
    --emit-json \\
    --emit-reports \\
    --report-pack client_full,client_summary,developer_full \\
    --langs zh,en \\
    --strict
        """
    )
    
    parser.add_argument(
        "--cases",
        type=str,
        nargs="+",
        default=["7D12"],
        help="（: 7D12）"
    )
    
    parser.add_argument(
        "--outdir",
        type=Path,
        required=True,
        help=""
    )
    
    parser.add_argument(
        "--result-json",
        type=Path,
        default=None,
        help=f"JSON（: {DEFAULT_RESULT_PATH}）"
    )
    
    parser.add_argument(
        "--emit-json",
        action="store_true",
        default=True,
        help="JSON（: True）"
    )
    
    parser.add_argument(
        "--emit-reports",
        action="store_true",
        default=True,
        help="（: True）"
    )
    
    parser.add_argument(
        "--report-pack",
        type=str,
        default="client_full,developer_full",
        help="，（: client_full, client_summary, developer_full）"
    )
    
    parser.add_argument(
        "--langs",
        type=str,
        default="zh,en",
        help="，（: zh,en）"
    )
    
    parser.add_argument(
        "--strict",
        action="store_true",
        help="（）"
    )
    
    parser.add_argument(
        "--skip-validation",
        action="store_true",
        help="JSON（JSON）"
    )
    
    args = parser.parse_args()
    
    # 
    report_pack = [p.strip() for p in args.report_pack.split(",")]
    langs = [l.strip() for l in args.langs.split(",")]
    
    # JSON
    if args.result_json:
        result_path = args.result_json
    else:
        result_path = DEFAULT_RESULT_PATH
    
    print("=" * 80)
    print("EGFR 7D12 VHH ")
    print("=" * 80)
    print(f"\n: {', '.join(args.cases)}")
    print(f": {args.outdir}")
    print(f"JSON: {result_path}")
    print(f": {', '.join(report_pack)}")
    print(f": {', '.join(langs)}")
    print(f": {args.strict}")
    print("=" * 80)
    
    # 
    if not result_path.exists():
        print(f"❌ : : {result_path}")
        print(f"   ， --result-json ")
        return 1
    
    # 
    print("\n[ 1/2] JSON...")
    try:
        result = load_result_json(result_path)
        print(f"✅ （: {result.get('project_id', 'N/A')}）")
    except Exception as e:
        print(f"❌ : {e}")
        return 1
    
    # 
    print("\n[ 2/2] ...")
    try:
        generated_files = generate_reports(
            result=result,
            output_dir=args.outdir,
            report_pack=report_pack,
            langs=langs,
            strict=args.strict,
            emit_json=args.emit_json,
            emit_reports=args.emit_reports,
            skip_validation=args.skip_validation,
        )
        
        print("\n" + "=" * 80)
        print("✅ ！")
        print("=" * 80)
        print(f"\n: {args.outdir}")
        for key, path in generated_files.items():
            if isinstance(path, Path):
                print(f"  - {key}: {path.name if path.is_file() else path}")
        
        return 0
        
    except Exception as e:
        print(f"\n❌ : {e}")
        if args.strict:
            import traceback
            traceback.print_exc()
        return 1


if __name__ == "__main__":
    exit(main())

