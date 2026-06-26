#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
7D12MDExcel

：
1. result.json
2. Markdown
3. Excel（）
"""

import sys
import json
from pathlib import Path
from datetime import datetime
from typing import Dict, Any, List

PROJECT_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT_ROOT))

try:
    import pandas as pd
    PANDAS_AVAILABLE = True
except ImportError:
    PANDAS_AVAILABLE = False
    print("  ⚠️  Warning: pandas ， Excel ")

from scripts.generate_dual_report_v3 import (
    generate_client_report,
    generate_developer_report,
)

PROJECT_ID = "EGFR_7D12_VHH"


def extract_data_for_excel(result: Dict[str, Any]) -> Dict[str, Any]:
    """result.jsonExcel"""
    data = {}
    
    # 
    input_data = result.get("input", {}) or {}
    input_seq = input_data.get("sequence", result.get("input_sequence", ""))
    data[""] = {
        "ID": PROJECT_ID,
        "": result.get("target") or input_data.get("target", "Unknown"),
        "": len(input_seq),
        "": input_seq,
        "": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
    }
    
    # IMGT
    segmentation = result.get("segmentation", {}) or {}
    regions = segmentation.get("regions", {}) or {}
    data["IMGT"] = {
        "FR1": regions.get("FR1", ""),
        "CDR1": regions.get("CDR1", ""),
        "FR2": regions.get("FR2", ""),
        "CDR2": regions.get("CDR2", ""),
        "FR3": regions.get("FR3", ""),
        "CDR3": regions.get("CDR3", ""),
        "FR4": regions.get("FR4", ""),
    }
    
    # Germline
    best_match = result.get("best_match", {}) or {}
    template = best_match.get("template", {}) or {}
    alignment_scores = best_match.get("alignment_scores", {}) or {}
    
    data["Germline"] = {
        "ID": template.get("template_id", "N/A"),
        "Identity": round(alignment_scores.get("framework_identity", 0.0), 4),
        "FR1 Identity": round(alignment_scores.get("fr1_identity", 0.0), 4),
        "FR2 Identity": round(alignment_scores.get("fr2_identity", 0.0), 4),
        "FR3 Identity": round(alignment_scores.get("fr3_identity", 0.0), 4),
        "FR4 Identity": round(alignment_scores.get("fr4_identity", 0.0), 4),
        "": best_match.get("humanized_sequence", ""),
    }
    
    # 
    mutations = result.get("mutations", {}) or {}
    mut_list = mutations.get("list", [])
    
    if not mut_list:
        # 
        humanized_seq = best_match.get("humanized_sequence", "")
        if input_seq and humanized_seq and len(input_seq) == len(humanized_seq):
            mut_list = []
            for i, (orig, hum) in enumerate(zip(input_seq, humanized_seq), 1):
                if orig != hum:
                    # 
                    region = "FR1"
                    if 27 <= i <= 38:
                        region = "CDR1"
                    elif 39 <= i <= 55:
                        region = "FR2"
                    elif 56 <= i <= 65:
                        region = "CDR2"
                    elif 66 <= i <= 104:
                        region = "FR3"
                    elif 105 <= i <= 117:
                        region = "CDR3"
                    elif i >= 118:
                        region = "FR4"
                    
                    mut_list.append({
                        "position": i,
                        "from": orig,
                        "to": hum,
                        "region": region,
                    })
    
    data[""] = mut_list
    
    # CMC
    cmc = result.get("cmc", {}) or {}
    cmc_hotspots = cmc.get("hotspots", []) or []
    data["CMC"] = {
        "": len(cmc_hotspots),
        "": cmc_hotspots,
    }
    
    # 
    immunogenicity = result.get("immunogenicity", {}) or {}
    data[""] = {
        "": immunogenicity.get("risk_level", "unknown"),
        "": len(immunogenicity.get("high_risk_epitopes", []) or []),
    }
    
    # Developability
    developability = result.get("developability", {}) or {}
    data["Developability"] = {
        "": round(developability.get("score", 0.0), 4),
        "": developability.get("level", "unknown"),
    }
    
    # QA
    qa = result.get("qa", {}) or {}
    data["QA"] = {
        "": qa.get("ok", False),
        "": qa.get("version", "N/A"),
    }
    
    # 10
    germline_selection = result.get("germline_selection_proof", {}) or {}
    ranked_top10 = germline_selection.get("ranked_top10", []) or []
    data["10"] = ranked_top10
    
    return data


def generate_excel_report(result: Dict[str, Any], output_path: Path) -> None:
    """Excel"""
    if not PANDAS_AVAILABLE:
        print("  ⚠️  Warning: pandas ， Excel ")
        return
    
    data = extract_data_for_excel(result)
    
    output_path.parent.mkdir(parents=True, exist_ok=True)
    
    with pd.ExcelWriter(output_path, engine='openpyxl') as writer:
        # 
        if "" in data:
            df_basic = pd.DataFrame([data[""]])
            df_basic.to_excel(writer, sheet_name='', index=False)
        
        # IMGT
        if "IMGT" in data:
            df_imgt = pd.DataFrame([data["IMGT"]])
            df_imgt.to_excel(writer, sheet_name='IMGT', index=False)
        
        # Germline
        if "Germline" in data:
            df_germline = pd.DataFrame([data["Germline"]])
            df_germline.to_excel(writer, sheet_name='Germline', index=False)
        
        # 
        if "" in data and data[""]:
            df_mutations = pd.DataFrame(data[""])
            df_mutations.to_excel(writer, sheet_name='', index=False)
        
        # CMC
        if "CMC" in data:
            df_cmc = pd.DataFrame([{
                "": data["CMC"][""],
            }])
            df_cmc.to_excel(writer, sheet_name='CMC', index=False)
            
            # CMC
            if data["CMC"][""]:
                df_cmc_details = pd.DataFrame(data["CMC"][""])
                df_cmc_details.to_excel(writer, sheet_name='CMC', index=False)
        
        # 
        if "" in data:
            df_immuno = pd.DataFrame([data[""]])
            df_immuno.to_excel(writer, sheet_name='', index=False)
        
        # Developability
        if "Developability" in data:
            df_dev = pd.DataFrame([data["Developability"]])
            df_dev.to_excel(writer, sheet_name='Developability', index=False)
        
        # QA
        if "QA" in data:
            df_qa = pd.DataFrame([data["QA"]])
            df_qa.to_excel(writer, sheet_name='QA', index=False)
        
        # 10
        if "10" in data and data["10"]:
            df_top10 = pd.DataFrame(data["10"])
            df_top10.to_excel(writer, sheet_name='10', index=False)
    
    print(f"✅ Excel : {output_path}")


def main():
    """"""
    print("=" * 80)
    print("7D12MDExcel")
    print("=" * 80)
    print()
    
    # result.json
    result_json_path = PROJECT_ROOT / "projects" / PROJECT_ID / "output" / "result.json"
    
    if not result_json_path.exists():
        # 
        alt_paths = [
            PROJECT_ROOT / "projects" / PROJECT_ID / "reports_v4_1_latest" / "result_20251211_081127.json",
            PROJECT_ROOT / "projects" / PROJECT_ID / "cro_report" / "full_result_with_all_fields.json",
        ]
        
        for alt_path in alt_paths:
            if alt_path.exists():
                result_json_path = alt_path
                break
        else:
            print(f"❌ result.json")
            print(f"   :")
            print(f"   - {result_json_path}")
            for alt_path in alt_paths:
                print(f"   - {alt_path}")
            return 1
    
    print(f"📂 : {result_json_path}")
    
    # JSON
    with open(result_json_path, "r", encoding="utf-8") as f:
        result = json.load(f)
    
    # （input.sequence）
    if "input_sequence" in result and "input" not in result:
        result["input"] = {}
    if "input_sequence" in result:
        if "input" not in result:
            result["input"] = {}
        if "sequence" not in result["input"]:
            result["input"]["sequence"] = result["input_sequence"]
    
    # JSON（）
    try:
        from core.json_data_preparer import prepare_json_data
        result = prepare_json_data(result, "REPORT")
        print("✅ JSON")
    except Exception as e:
        print(f"⚠️  JSON: {e}，...")
    
    # 
    output_dir = PROJECT_ROOT / "projects" / PROJECT_ID / "reports_7d12_final"
    output_dir.mkdir(parents=True, exist_ok=True)
    
    print(f"📁 : {output_dir}")
    print()
    
    # 1: Markdown
    print("[ 1/2] Markdown...")
    print("-" * 80)
    
    client_report_path = None
    developer_report_path = None
    
    try:
        # Client Report
        client_report_path = generate_client_report(result, output_dir, PROJECT_ID)
        print(f"✅ Client Report: {client_report_path}")
    except Exception as e:
        print(f"⚠️  Client Report: {e}")
        print("   ...")
        # ，
        try:
            from scripts.generate_dual_report_v3 import _build_client_report_data, _fill_template, _get_client_report_template
            from pathlib import Path as PathLib
            output_dir.mkdir(parents=True, exist_ok=True)
            template_path = PROJECT_ROOT / "reports" / "templates" / "vhh_client_report_template.md"
            if not template_path.exists():
                template = _get_client_report_template()
            else:
                template = template_path.read_text(encoding="utf-8")
            report_data = _build_client_report_data(result, PROJECT_ID)
            report_content = _fill_template(template, report_data)
            client_report_path = output_dir / f"{PROJECT_ID}_Client_Report_{datetime.now().strftime('%Y%m%d_%H%M%S')}.md"
            client_report_path.write_text(report_content, encoding="utf-8")
            print(f"✅ Client Report (): {client_report_path}")
        except Exception as e2:
            print(f"❌ Client Report: {e2}")
            import traceback
            traceback.print_exc()
    
    try:
        # Developer Report
        developer_report_path = generate_developer_report(result, output_dir, PROJECT_ID)
        print(f"✅ Developer Report: {developer_report_path}")
    except Exception as e:
        print(f"⚠️  Developer Report: {e}")
        print("   ...")
        try:
            from scripts.generate_dual_report_v3 import _build_developer_report_data, _fill_template, _get_developer_report_template
            output_dir.mkdir(parents=True, exist_ok=True)
            template_path = PROJECT_ROOT / "reports" / "templates" / "vhh_developer_report_template.md"
            if not template_path.exists():
                template = _get_developer_report_template()
            else:
                template = template_path.read_text(encoding="utf-8")
            report_data = _build_developer_report_data(result, PROJECT_ID)
            report_content = _fill_template(template, report_data)
            developer_report_path = output_dir / f"{PROJECT_ID}_Developer_Report_{datetime.now().strftime('%Y%m%d_%H%M%S')}.md"
            developer_report_path.write_text(report_content, encoding="utf-8")
            print(f"✅ Developer Report (): {developer_report_path}")
        except Exception as e2:
            print(f"❌ Developer Report: {e2}")
            import traceback
            traceback.print_exc()
    
    if not client_report_path and not developer_report_path:
        print("❌ Markdown")
        return 1
    
    print()
    
    # 2: Excel
    print("[ 2/2] Excel...")
    print("-" * 80)
    
    if PANDAS_AVAILABLE:
        excel_path = output_dir / f"{PROJECT_ID}_Report_{datetime.now().strftime('%Y%m%d_%H%M%S')}.xlsx"
        try:
            generate_excel_report(result, excel_path)
        except Exception as e:
            print(f"❌ Excel: {e}")
            import traceback
            traceback.print_exc()
            return 1
    else:
        print("⚠️  Excel（pandas）")
        print("   pandas: pip install pandas openpyxl")
    
    print()
    print("=" * 80)
    print("✅ ！")
    print("=" * 80)
    print(f"\n:")
    print(f"  - Client Report: {client_report_path}")
    print(f"  - Developer Report: {developer_report_path}")
    if PANDAS_AVAILABLE:
        print(f"  - Excel Report: {excel_path}")
    print(f"\n: {output_dir}")
    print("=" * 80)
    
    return 0


if __name__ == "__main__":
    exit(main())










