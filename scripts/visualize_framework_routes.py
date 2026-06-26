import pandas as pd
import matplotlib.pyplot as plt
import seaborn as sns
import argparse
import os
from pathlib import Path

def generate_visualizations(in_parquet, out_dir):
    print(f"📖 Reading routed parquet: {in_parquet}")
    df = pd.read_parquet(in_parquet)
    
    os.makedirs(out_dir, exist_ok=True)
    
    # 1. Delta Identity Distribution Histogram
    print("📊 Generating Delta Identity Histogram...")
    plt.figure(figsize=(10, 6))
    sns.histplot(df['vh_delta_identity'], label='VH Delta', color='blue', alpha=0.5, kde=True)
    sns.histplot(df['vl_delta_identity'], label='VL Delta', color='orange', alpha=0.5, kde=True)
    plt.axvline(x=0.03, color='green', linestyle='--', label='p75 (0.03)')
    plt.axvline(x=0.06, color='yellow', linestyle='--', label='p90 (0.06)')
    plt.axvline(x=0.29, color='red', linestyle='--', label='p99 (0.29)')
    plt.title('Distribution of Delta Identity (VH vs VL) - Slice 1')
    plt.xlabel('Delta Identity')
    plt.ylabel('Frequency')
    plt.legend()
    plt.grid(axis='y', alpha=0.3)
    plt.savefig(os.path.join(out_dir, 'fig_delta_identity_hist_slice_1.png'), dpi=300, bbox_inches='tight')
    plt.close()

    # 2. Framework Band x CDR Load Band Heatmap
    print("📊 Generating Band Heatmap...")
    # Create contingency table
    heatmap_data = pd.crosstab(df['framework_band'], df['cdr_load_band'])
    
    # Ensure all bands are present for consistent visualization
    all_f_bands = ['F0', 'F1', 'F2', 'F3']
    all_c_bands = ['C0', 'C1', 'C2', 'C3']
    heatmap_data = heatmap_data.reindex(index=all_f_bands, columns=all_c_bands, fill_value=0)
    
    plt.figure(figsize=(8, 6))
    sns.heatmap(heatmap_data, annot=True, fmt='d', cmap='YlGnBu', cbar_kws={'label': 'Count'})
    plt.title('Framework Band vs CDR Load Band - Slice 1')
    plt.xlabel('CDR Load Band')
    plt.ylabel('Framework Band')
    plt.savefig(os.path.join(out_dir, 'fig_band_heatmap_slice_1.png'), dpi=300, bbox_inches='tight')
    plt.close()

    # 3. Top Germlines Rank-Frequency Curve
    print("📊 Generating Rank-Frequency Curves...")
    fig, axes = plt.subplots(1, 2, figsize=(15, 6))
    
    # VH Germline Frequencies
    vh_counts = df['vh_best_germline_global'].value_counts()
    axes[0].plot(range(len(vh_counts)), vh_counts.values, marker='o', markersize=4)
    axes[0].set_title('VH Global Germline Frequency (Long Tail)')
    axes[0].set_xlabel('Rank')
    axes[0].set_ylabel('Frequency')
    axes[0].grid(alpha=0.3)
    
    # VH Library Match Frequencies
    lib_counts = df['vh_best_framework_lib'].value_counts()
    axes[1].plot(range(len(lib_counts)), lib_counts.values, marker='s', markersize=4, color='green')
    axes[1].set_title('VH Library Framework Frequency (Long Tail)')
    axes[1].set_xlabel('Rank')
    axes[1].set_ylabel('Frequency')
    axes[1].grid(alpha=0.3)
    
    plt.tight_layout()
    plt.savefig(os.path.join(out_dir, 'fig_rank_frequency_slice_1.png'), dpi=300, bbox_inches='tight')
    plt.close()
    
    print(f"✅ Visualizations saved to {out_dir}")

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Generate visualization plots for routed framework analysis.")
    parser.add_argument("--in_parquet", required=True, help="Input routed parquet file path")
    parser.add_argument("--out_dir", required=True, help="Output directory for figures")
    
    args = parser.parse_args()
    
    generate_visualizations(args.in_parquet, args.out_dir)
