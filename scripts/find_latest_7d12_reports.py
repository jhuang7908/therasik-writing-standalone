#!/usr/bin/env python3
"""
7D12

：
- 7D12
- 
- 
"""

import json
from pathlib import Path
from datetime import datetime
from typing import List, Dict, Tuple

PROJECT_ROOT = Path(__file__).parent.parent
PROJECT_DIR = PROJECT_ROOT / "projects" / "EGFR_7D12_VHH"


def find_all_reports() -> List[Dict]:
    """7D12"""
    reports = []
    
    # 
    report_dirs = [
        PROJECT_DIR / "reports_7d12_final",
        PROJECT_DIR / "reports_v4_1_final",
        PROJECT_DIR / "reports_v4_1_latest",
        PROJECT_DIR / "reports_v3_final",
        PROJECT_DIR / "reports_v3",
    ]
    
    for report_dir in report_dirs:
        if not report_dir.exists():
            continue
        
        # .md.xlsx
        for file_path in report_dir.rglob("*"):
            if file_path.is_file() and file_path.suffix in [".md", ".xlsx", ".json"]:
                if "7D12" in file_path.name.upper() or "EGFR" in file_path.name.upper():
                    stat = file_path.stat()
                    reports.append({
                        "path": file_path,
                        "name": file_path.name,
                        "size": stat.st_size,
                        "modified": datetime.fromtimestamp(stat.st_mtime),
                        "relative_path": file_path.relative_to(PROJECT_ROOT),
                    })
    
    return reports


def find_audit_logs() -> List[Dict]:
    """"""
    audit_dir = PROJECT_ROOT / "audit_logs"
    logs = []
    
    if audit_dir.exists():
        for log_file in audit_dir.glob("audit_*.jsonl"):
            stat = log_file.stat()
            logs.append({
                "path": log_file,
                "name": log_file.name,
                "size": stat.st_size,
                "modified": datetime.fromtimestamp(stat.st_mtime),
                "relative_path": log_file.relative_to(PROJECT_ROOT),
            })
    
    return logs


def format_size(size: int) -> str:
    """"""
    if size < 1024:
        return f"{size} B"
    elif size < 1024 * 1024:
        return f"{size / 1024:.1f} KB"
    else:
        return f"{size / (1024 * 1024):1f} MB"


def print_report_summary():
    """"""
    print("=" * 80)
    print("7D12 ")
    print("=" * 80)
    print()
    
    # 
    reports = find_all_reports()
    
    if not reports:
        print("❌ ")
        return
    
    # 
    reports.sort(key=lambda x: x["modified"], reverse=True)
    
    print(f"📊  {len(reports)} \n")
    
    # 5
    print("🆕 （）:")
    print("-" * 80)
    for i, report in enumerate(reports[:5], 1):
        print(f"\n{i}. {report['name']}")
        print(f"   : {report['modified'].strftime('%Y-%m-%d %H:%M:%S')}")
        print(f"   : {format_size(report['size'])}")
        print(f"   : {report['relative_path']}")
    
    # 
    print("\n" + "=" * 80)
    print("📁 :")
    print("-" * 80)
    
    client_reports = [r for r in reports if "Client_Report" in r["name"]]
    developer_reports = [r for r in reports if "Developer_Report" in r["name"]]
    excel_reports = [r for r in reports if r["name"].endswith(".xlsx")]
    json_reports = [r for r in reports if r["name"].endswith(".json")]
    
    if client_reports:
        print(f"\n📄  ({len(client_reports)} ):")
        for report in sorted(client_reports, key=lambda x: x["modified"], reverse=True)[:3]:
            print(f"   • {report['name']} ({report['modified'].strftime('%Y-%m-%d %H:%M:%S')})")
    
    if developer_reports:
        print(f"\n🔧  ({len(developer_reports)} ):")
        for report in sorted(developer_reports, key=lambda x: x["modified"], reverse=True)[:3]:
            print(f"   • {report['name']} ({report['modified'].strftime('%Y-%m-%d %H:%M:%S')})")
    
    if excel_reports:
        print(f"\n📊 Excel ({len(excel_reports)} ):")
        for report in sorted(excel_reports, key=lambda x: x["modified"], reverse=True)[:3]:
            print(f"   • {report['name']} ({report['modified'].strftime('%Y-%m-%d %H:%M:%S')})")
    
    if json_reports:
        print(f"\n📦 JSON ({len(json_reports)} ):")
        for report in sorted(json_reports, key=lambda x: x["modified"], reverse=True)[:3]:
            print(f"   • {report['name']} ({report['modified'].strftime('%Y-%m-%d %H:%M:%S')})")
    
    # 
    print("\n" + "=" * 80)
    print("📋 :")
    print("-" * 80)
    
    logs = find_audit_logs()
    if logs:
        logs.sort(key=lambda x: x["modified"], reverse=True)
        for log in logs[:5]:
            print(f"   • {log['name']} ({log['modified'].strftime('%Y-%m-%d %H:%M:%S')})")
            
            # 
            try:
                with open(log["path"], "r", encoding="utf-8") as f:
                    lines = f.readlines()
                    if lines:
                        last_entry = json.loads(lines[-1].strip())
                        print(f"     : {last_entry.get('timestamp', 'N/A')}")
                        print(f"     : {last_entry.get('project_name', 'N/A')}")
                        print(f"     : {last_entry.get('best_template_id', 'N/A')}")
            except Exception as e:
                print(f"     : {e}")
    else:
        print("   ❌ ")
    
    # 
    print("\n" + "=" * 80)
    print("💡 :")
    print("-" * 80)
    
    if client_reports:
        latest_client = max(client_reports, key=lambda x: x["modified"])
        print(f"\n1. :")
        print(f"   {latest_client['relative_path']}")
    
    if developer_reports:
        latest_dev = max(developer_reports, key=lambda x: x["modified"])
        print(f"\n2. :")
        print(f"   {latest_dev['relative_path']}")
    
    # 
    result_json = PROJECT_DIR / "output" / "result.json"
    if result_json.exists():
        stat = result_json.stat()
        print(f"\n3. JSON:")
        print(f"   {result_json.relative_to(PROJECT_ROOT)}")
        print(f"   : {format_size(stat.st_size)}")
        print(f"   : {datetime.fromtimestamp(stat.st_mtime).strftime('%Y-%m-%d %H:%M:%S')}")
    
    print("\n" + "=" * 80)
    print("✅ ")
    print("=" * 80)


if __name__ == "__main__":
    print_report_summary()




