import pandas as pd
from pathlib import Path
import sys

PROJECT_ROOT = Path(__file__).resolve().parent.parent

def analyze_stats():
    data_path = PROJECT_ROOT / "data" / "humanization_assay" / "thera_human_igG_germline_analysis.xlsx"
    if not data_path.exists():
        print(f"Error: {data_path} not found.")
        return

    df = pd.read_excel(data_path)
    
    origin_groups = {
        'Natural Human': 'natural_human_repertoire',
        'Engineered Humanization': 'engineered_humanisation'
    }

    report_path = PROJECT_ROOT / "data" / "humanization_assay" / "germline_analysis_summary.txt"
    
    with open(report_path, 'w', encoding='utf-8') as f:
        f.write("=" * 80 + "\n")
        f.write("GERMLINE PROPORTION ANALYSIS REPORT\n")
        f.write("=" * 80 + "\n\n")

        for label, mode in origin_groups.items():
            sub_df = df[df['human_origin_mode'] == mode]
            total = len(sub_df)
            f.write(f"Origin Mode: {label} (Total: {total})\n")
            f.write("-" * 40 + "\n")
            
            # VH Top 10
            f.write("\nTop 10 VH Germlines:\n")
            vh_counts = sub_df['Best_VH_Germline'].value_counts().head(10)
            for gid, count in vh_counts.items():
                pct = (count / total) * 100
                f.write(f"  - {gid}: {count} ({pct:.1f}%)\n")
                
            # VL Top 10
            f.write("\nTop 10 VL Germlines:\n")
            vl_counts = sub_df['Best_VL_Germline'].value_counts().head(10)
            for gid, count in vl_counts.items():
                pct = (count / total) * 100
                f.write(f"  - {gid}: {count} ({pct:.1f}%)\n")
            f.write("\n")

        f.write("=" * 80 + "\n")
        f.write("TARGET CORRELATION ANALYSIS (Top Targets)\n")
        f.write("=" * 80 + "\n\n")

        if 'targets_meta' in df.columns:
            target_counts = df['targets_meta'].value_counts().head(15)
            f.write(f"Analyzing top {len(target_counts)} targets:\n")
            
            for target, count in target_counts.items():
                t_df = df[df['targets_meta'] == target]
                f.write(f"\nTarget: {target} (Total: {count})\n")
                
                top_vh = t_df['Best_VH_Germline'].value_counts().head(3)
                f.write(f"  Top VH: " + ", ".join([f"{gid}({c})" for gid, c in top_vh.items()]) + "\n")
                
                top_vl = t_df['Best_VL_Germline'].value_counts().head(3)
                f.write(f"  Top VL: " + ", ".join([f"{gid}({c})" for gid, c in top_vl.items()]) + "\n")
        else:
            f.write("'targets_meta' column not found.\n")

    print(f"Report saved to {report_path}")

if __name__ == "__main__":
    analyze_stats()
