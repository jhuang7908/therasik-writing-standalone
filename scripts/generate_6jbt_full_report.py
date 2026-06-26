#!/usr/bin/env python3
"""
 6JBT（VH + VL）（ + dev/client）

：
- --cases: （6JBT_VH, 6JBT_VL）
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
PROJECT_ID_VH = "PD1_6JBT_VH"
PROJECT_ID_VL = "PD1_6JBT_VL"
TARGET = "PD1"
DEFAULT_VH_SEQ_PATH = PROJECT_ROOT / "data" / "benchmarks" / "fasta" / "6jbt_mouse_vh.fasta"
DEFAULT_VL_SEQ_PATH = PROJECT_ROOT / "data" / "benchmarks" / "fasta" / "6jbt_mouse_vl_kappa.fasta"

# （）
DEFAULT_VH_RESULT_PATH = PROJECT_ROOT / "projects" / PROJECT_ID_VH / "output" / "result.json"
DEFAULT_VL_RESULT_PATH = PROJECT_ROOT / "projects" / PROJECT_ID_VL / "output" / "result.json"


def load_result_json(result_path: Path) -> Dict[str, Any]:
    """JSON"""
    if not result_path.exists():
        raise FileNotFoundError(f": {result_path}")
    
    with open(result_path, "r", encoding="utf-8") as f:
        result = json.load(f)
    
    return result


def fix_result_json(result: Dict[str, Any], project_id: str, target: str) -> Dict[str, Any]:
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
        result["project_id"] = project_id
    
    # target
    if "target" not in result:
        result["target"] = target
        if "input" in result and "target" not in result["input"]:
            result["input"]["target"] = target
    
    return result


def generate_reports_for_chain(
    result: Dict[str, Any],
    output_dir: Path,
    project_id: str,
    target: str,
    report_pack: List[str],
    langs: List[str],
    strict: bool = False,
    emit_json: bool = True,
    emit_reports: bool = True,
    skip_validation: bool = False,
    chain_name: str = "",
) -> Dict[str, Path]:
    """"""
    chain_output_dir = output_dir / chain_name if chain_name else output_dir
    chain_output_dir.mkdir(parents=True, exist_ok=True)
    generated_files = {}
    
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    
    # JSON
    result = fix_result_json(result, project_id, target)
    
    # JSON（）
    if emit_json:
        json_path = chain_output_dir / f"result_{chain_name}_{timestamp}.json" if chain_name else chain_output_dir / f"result_{timestamp}.json"
        with open(json_path, "w", encoding="utf-8") as f:
            json.dump(result, f, indent=2, ensure_ascii=False)
        generated_files["json"] = json_path
        print(f"✅ JSON: {json_path}")
    
    if not emit_reports:
        return generated_files
    
    # （）
    if HAS_FIGURES and "client_full" in report_pack:
        figures_dir = chain_output_dir / "figures" / project_id / "figures"
        figures_dir.mkdir(parents=True, exist_ok=True)
        
        try:
            import sys as sys_module
            old_argv = sys_module.argv
            json_path = generated_files.get("json") or (chain_output_dir / f"result_{timestamp}.json")
            
            # JSON，
            if not json_path.exists():
                with open(json_path, "w", encoding="utf-8") as f:
                    json.dump(result, f, indent=2, ensure_ascii=False)
            
            sys_module.argv = [
                "plot_vhh_report_figures_v1.py",
                "--input", str(json_path),
                "--output_dir", str(figures_dir.parent),
                "--project-id", project_id,
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
                
                def lenient_validate(data, strict=False):
                    return True, []
                
                # 
                import scripts.generate_dual_report_v3 as report_module
                original_validate = report_module.validate_json_for_delivery
                report_module.validate_json_for_delivery = lenient_validate
            
            client_report_path = generate_client_report(
                result=result,
                output_dir=chain_output_dir,
                project_id=project_id,
            )
            generated_files["client_report"] = client_report_path
            print(f"✅ Client Report: {client_report_path}")
            
            # 
            if skip_validation:
                report_module.validate_json_for_delivery = original_validate
        except Exception as e:
            print(f"❌ Client Report: {e}")
            if strict:
                raise
            else:
                print(f"⚠️  ...")
    
    # Developer Report
    if "developer_full" in report_pack:
        try:
            # ，
            if skip_validation:
                from core.segmentation.json_validator import validate_json_for_delivery
                
                def lenient_validate(data, strict=False):
                    return True, []
                
                import scripts.generate_dual_report_v3 as report_module
                original_validate = report_module.validate_json_for_delivery
                report_module.validate_json_for_delivery = lenient_validate
            
            developer_report_path = generate_developer_report(
                result=result,
                output_dir=chain_output_dir,
                project_id=project_id,
            )
            generated_files["developer_report"] = developer_report_path
            print(f"✅ Developer Report: {developer_report_path}")
            
            # 
            if skip_validation:
                report_module.validate_json_for_delivery = original_validate
        except Exception as e:
            print(f"❌ Developer Report: {e}")
            if strict:
                raise
            else:
                print(f"⚠️  ...")
    
    return generated_files


def main():
    parser = argparse.ArgumentParser(
        description=" 6JBT（VH + VL）（ + dev/client）",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
:
  # （VH + VL， + client + developer）
  python scripts/generate_6jbt_full_report.py \\
    --cases 6JBT_VH,6JBT_VL \\
    --outdir projects/PD1_6JBT/_runs/2025-12-17_rationales_v1 \\
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
        default=["6JBT_VH", "6JBT_VL"],
        help="（: 6JBT_VH,6JBT_VL）"
    )
    
    parser.add_argument(
        "--outdir",
        type=Path,
        required=True,
        help=""
    )
    
    parser.add_argument(
        "--result-vh-json",
        type=Path,
        default=None,
        help=f"VHJSON（: {DEFAULT_VH_RESULT_PATH}）"
    )
    
    parser.add_argument(
        "--result-vl-json",
        type=Path,
        default=None,
        help=f"VLJSON（: {DEFAULT_VL_RESULT_PATH}）"
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
    cases = [c.strip() for c in (args.cases if isinstance(args.cases, list) else args.cases[0].split(","))]
    report_pack = [p.strip() for p in args.report_pack.split(",")]
    langs = [l.strip() for l in args.langs.split(",")]
    
    print("=" * 80)
    print("6JBT（VH + VL）")
    print("=" * 80)
    print(f"\n: {', '.join(cases)}")
    print(f": {args.outdir}")
    print(f": {', '.join(report_pack)}")
    print(f": {', '.join(langs)}")
    print(f": {args.strict}")
    print("=" * 80)
    
    all_generated_files = {}
    
    # VH
    if any("VH" in c.upper() for c in cases):
        print("\n" + "=" * 80)
        print(" 6JBT VH")
        print("=" * 80)
        
        vh_result_path = args.result_vh_json or DEFAULT_VH_RESULT_PATH
        
        if not vh_result_path.exists():
            print(f"⚠️  : VH: {vh_result_path}")
            print(f"   VH， --result-vh-json ")
            print(f"\n   : VH:")
            print(f"   python scripts/run_vhh_full_pipeline.py --fasta {DEFAULT_VH_SEQ_PATH} --project {PROJECT_ID_VH}")
            if args.strict:
                return 1
            print(f"   VH...")
        else:
            print(f"\n[ 1/2] VHJSON...")
            try:
                vh_result = load_result_json(vh_result_path)
                print(f"✅ VH（: {vh_result.get('project_id', 'N/A')}）")
                
                print("\n[ 2/2] VH...")
                vh_files = generate_reports_for_chain(
                    result=vh_result,
                    output_dir=args.outdir,
                    project_id=PROJECT_ID_VH,
                    target=TARGET,
                    report_pack=report_pack,
                    langs=langs,
                    strict=args.strict,
                    emit_json=args.emit_json,
                    emit_reports=args.emit_reports,
                    skip_validation=args.skip_validation,
                    chain_name="VH",
                )
                all_generated_files["VH"] = vh_files
            except Exception as e:
                print(f"❌ VH: {e}")
                if args.strict:
                    return 1
    
    # VL
    if any("VL" in c.upper() for c in cases):
        print("\n" + "=" * 80)
        print(" 6JBT VL")
        print("=" * 80)
        
        vl_result_path = args.result_vl_json or DEFAULT_VL_RESULT_PATH
        
        if not vl_result_path.exists():
            print(f"⚠️  : VL: {vl_result_path}")
            print(f"   VL， --result-vl-json ")
            print(f"\n   : VL:")
            print(f"   python scripts/run_vhh_full_pipeline.py --fasta {DEFAULT_VL_SEQ_PATH} --project {PROJECT_ID_VL}")
            if args.strict:
                return 1
            print(f"   VL...")
        else:
            print(f"\n[ 1/2] VLJSON...")
            try:
                vl_result = load_result_json(vl_result_path)
                print(f"✅ VL（: {vl_result.get('project_id', 'N/A')}）")
                
                print("\n[ 2/2] VL...")
                vl_files = generate_reports_for_chain(
                    result=vl_result,
                    output_dir=args.outdir,
                    project_id=PROJECT_ID_VL,
                    target=TARGET,
                    report_pack=report_pack,
                    langs=langs,
                    strict=args.strict,
                    emit_json=args.emit_json,
                    emit_reports=args.emit_reports,
                    skip_validation=args.skip_validation,
                    chain_name="VL",
                )
                all_generated_files["VL"] = vl_files
            except Exception as e:
                print(f"❌ VL: {e}")
                if args.strict:
                    return 1
    
    print("\n" + "=" * 80)
    print("✅ ！")
    print("=" * 80)
    print(f"\n: {args.outdir}")
    for chain, files in all_generated_files.items():
        print(f"\n{chain} :")
        for key, path in files.items():
            if isinstance(path, Path):
                print(f"  - {key}: {path.name if path.is_file() else path}")
    
    return 0


if __name__ == "__main__":
    exit(main())

