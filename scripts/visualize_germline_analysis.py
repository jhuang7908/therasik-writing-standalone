import pandas as pd
import matplotlib.pyplot as plt
import seaborn as sns
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent

def classify_target(target_name):
    if not isinstance(target_name, str): return "Other"
    t = target_name.upper()
    if any(k in t for k in ["PD1", "PD-1", "PDCD1", "CTLA4", "CTLA-4", "LAG3", "TIGIT", "TIM3", "OX40", "CD40", "GITR", "CD137", "4-1BB", "ICOS"]):
        return "Immune Checkpoint"
    elif any(k in t for k in ["IL-", "IL1", "IL2", "IL4", "IL5", "IL6", "IL12", "IL13", "IL17", "IL23", "TNF", "IFN", "CXCL", "CCL", "FLT3LG", "SF15", "RANKL", "BLYS", "BAFF"]):
        return "Cytokine/GF"
    elif any(k in t for k in ["HER2", "ERBB2", "EGFR", "EPCAM", "CD20", "CD19", "CD38", "CD33", "CD22", "CD52", "CEA", "MUC1", "PSMA", "BCMA", "GD2", "MSLN"]):
        return "Tumor Marker"
    elif any(k in t for k in ["SARS", "SPIKE", "COVID", "HIV", "RSV", "INFLUENZA", "EBOLA", "CMV", "GP120", "HA"]):
        return "Viral Protein"
    elif any(k in t for k in ["VEGF", "KDR", "MET", "FGFR", "IGF1R", "CD310", "TRAIL", "DLL4", "NOTCH"]):
        return "Receptor/Signalling"
    return "Other"

def run_visualization():
    data_path = PROJECT_ROOT / "data" / "humanization_assay" / "thera_human_igG_germline_analysis.xlsx"
    df = pd.read_excel(data_path)
    df['Target_Category'] = df['targets_meta'].apply(classify_target)
    
    plot_dir = PROJECT_ROOT / "data" / "humanization_assay" / "plots"
    plot_dir.mkdir(parents=True, exist_ok=True)
    
    sns.set_theme(style="whitegrid")
    
    # 1. Comparison of VH/VL Top 10 frequencies (Natural vs Engineered)
    for chain in ['VH', 'VL']:
        plt.figure(figsize=(12, 6))
        col = f'Best_{chain}_Germline'
        
        # Get top 15 overall to have a good set to compare
        top_germs = df[col].value_counts().head(15).index
        plot_df = df[df[col].isin(top_germs)]
        
        # Calculate percentages within each group
        counts = plot_df.groupby(['human_origin_mode', col]).size().reset_index(name='count')
        totals = df.groupby('human_origin_mode').size()
        counts['percentage'] = counts.apply(lambda x: (x['count'] / totals[x['human_origin_mode']]) * 100, axis=1)
        
        sns.barplot(data=counts, x=col, y='percentage', hue='human_origin_mode')
        plt.title(f'Top {chain} Germline Frequency Comparison')
        plt.xticks(rotation=45, ha='right')
        plt.ylabel('Percentage (%)')
        plt.tight_layout()
        plt.savefig(plot_dir / f"comparative_{chain.lower()}_distribution.png")
        plt.close()

    # 2. Target Profile Heatmap (Top VH Germlines vs Target Categories)
    plt.figure(figsize=(14, 8))
    top_vh = df['Best_VH_Germline'].value_counts().head(20).index
    profile_df = df[df['Best_VH_Germline'].isin(top_vh)]
    
    # Create pivot table
    pivot = pd.crosstab(profile_df['Target_Category'], profile_df['Best_VH_Germline'], normalize='index') * 100
    
    sns.heatmap(pivot, annot=True, fmt=".1f", cmap="YlGnBu")
    plt.title('VH Germline Profile (%) across Target Categories')
    plt.tight_layout()
    plt.savefig(plot_dir / "target_category_vh_heatmap.png")
    plt.close()

    # 3. VL Heatmap
    plt.figure(figsize=(14, 8))
    top_vl = df['Best_VL_Germline'].value_counts().head(20).index
    profile_vl = df[df['Best_VL_Germline'].isin(top_vl)]
    pivot_vl = pd.crosstab(profile_vl['Target_Category'], profile_vl['Best_VL_Germline'], normalize='index') * 100
    
    sns.heatmap(pivot_vl, annot=True, fmt=".1f", cmap="OrRd")
    plt.title('VL Germline Profile (%) across Target Categories')
    plt.tight_layout()
    plt.savefig(plot_dir / "target_category_vl_heatmap.png")
    plt.close()

    print(f"Plots saved to {plot_dir}")

if __name__ == "__main__":
    run_visualization()
