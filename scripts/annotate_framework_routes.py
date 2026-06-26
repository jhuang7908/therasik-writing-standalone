import pandas as pd
import argparse
import os
import sys
from pathlib import Path

# Add project root to sys.path
PROJECT_ROOT = Path(__file__).resolve().parents[1]
sys.path.append(str(PROJECT_ROOT))

from core.policy.framework_router import FrameworkRouter

def annotate_parquet(in_path, out_path, summary_path, examples_path, dry_run=False):
    print(f"📖 Reading input parquet: {in_path}")
    df = pd.read_parquet(in_path)
    
    # Check required columns for routing
    routing_cols = [
        "vh_delta_identity", "vl_delta_identity", 
        "vh_out_of_library_flag", "vl_out_of_library_flag",
        "vh_fr1", "vh_fr2", "vh_fr3", "vl_fr1", "vl_fr2", "vl_fr3"
    ]
    for col in routing_cols:
        if col not in df.columns:
            if "identity" in col:
                df[col] = None
            elif "flag" in col:
                df[col] = False
            else:
                df[col] = None
            
    # Add cdrh3_length if missing
    if "cdrh3_length" not in df.columns:
        if "vh_cdr3" in df.columns:
            df["cdrh3_length"] = df["vh_cdr3"].str.len()
        else:
            df["cdrh3_length"] = None
            
    router = FrameworkRouter()
    
    print("🧠 Routing records...")
    routed_data = []
    for _, row in df.iterrows():
        input_data = row.to_dict()
        
        # Clean up input types for router
        for k in ["vh_delta_identity", "vl_delta_identity"]:
            if input_data.get(k) is not None:
                input_data[k] = float(input_data[k])
        
        if input_data.get("cdrh3_length") is not None:
            input_data["cdrh3_length"] = int(input_data["cdrh3_length"])

        res = router.route(input_data)
        
        # Flatten risk overrides for parquet/csv
        risk_notes = [r["note_cn"] for r in res["risk_overrides"]]
        res["risk_notes_cn"] = " | ".join(risk_notes)
        
        risk_levels = [r["risk_level"] for r in res["risk_overrides"]]
        res["risk_level"] = max(risk_levels + ["NORMAL"]) if risk_levels else "NORMAL"
        
        routed_data.append(res)
        
    routed_df = pd.DataFrame(routed_data)
    final_df = pd.concat([df.reset_index(drop=True), routed_df], axis=1)
    
    # Generate Summary Statistics
    summary = final_df.groupby(["framework_band", "route_id", "route_name"]).size().reset_index(name="count")
    summary["ratio"] = (summary["count"] / len(final_df)).round(4)
    
    print("\nSummary Statistics:")
    print(summary)
    
    if dry_run:
        print("\n🚀 Dry run complete. No files written.")
        return

    print(f"💾 Saving routed parquet: {out_path}")
    final_df.to_parquet(out_path)
    
    print(f"📊 Saving summary CSV: {summary_path}")
    summary.to_csv(summary_path, index=False, encoding="utf-8-sig")
    
    # Generate Examples (N=20 per route, seed=42)
    print(f"📝 Saving examples CSV: {examples_path}")
    examples = final_df.groupby("route_id").apply(lambda x: x.sample(min(len(x), 20), random_state=42)).reset_index(drop=True)
    examples.to_csv(examples_path, index=False, encoding="utf-8-sig")
    
    print("✅ Annotation complete!")

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Annotate framework routes for antibody sequences.")
    parser.add_argument("--in_parquet", required=True, help="Input parquet file path")
    parser.add_argument("--out_parquet", required=True, help="Output routed parquet file path")
    parser.add_argument("--out_summary", required=True, help="Output summary CSV path")
    parser.add_argument("--out_examples", required=True, help="Output examples CSV path")
    parser.add_argument("--dry_run", action="store_true", help="Print summary without writing files")
    
    args = parser.parse_args()
    
    annotate_parquet(args.in_parquet, args.out_parquet, args.out_summary, args.out_examples, args.dry_run)
