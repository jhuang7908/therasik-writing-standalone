import pandas as pd
from pathlib import Path
import re

PROJECT_ROOT = Path(__file__).resolve().parent.parent

def classify_target(target_name):
    if not isinstance(target_name, str): return "Other", "Unknown"
    
    t = target_name.upper()
    
    # 1. Origin/Nature
    if any(k in t for k in ["SARS", "SPIKE", "COVID", "HIV", "RSV", "INFLUENZA", "EBOLA", "CMV", "GP120", "HA"]):
        nature = "Viral"
    elif any(k in t for k in ["TOXIN", "CLOSTRIDIUM", "ANTHRAX", "PSEUDOMONAS"]):
        nature = "Bacterial"
    else:
        nature = "Human"
        
    # 2. Functional Category
    # Checkpoint / Immune Modulation
    if any(k in t for k in ["PD1", "PD-1", "PDCD1", "CTLA4", "CTLA-4", "LAG3", "TIGIT", "TIM3", "OX40", "CD40", "GITR", "CD137", "4-1BB", "ICOS"]):
        category = "Immune Checkpoint/Modulator"
    # Cytokine / Secreted
    elif any(k in t for k in ["IL-", "IL1", "IL2", "IL4", "IL5", "IL6", "IL12", "IL13", "IL17", "IL23", "TNF", "IFN", "CXCL", "CCL", "FLT3LG", "SF15", "RANKL", "BLYS", "BAFF"]):
        category = "Cytokine/Growth Factor"
    # Tumor Antigen / B-cell Marker
    elif any(k in t for k in ["HER2", "ERBB2", "EGFR", "EPCAM", "CD20", "CD19", "CD38", "CD33", "CD22", "CD52", "CEA", "MUC1", "PSMA", "BCMA", "GD2", "MSLN"]):
        category = "Tumor/Surface Marker"
    # Receptor / Signalling (Non-Checkpoint)
    elif any(k in t for k in ["VEGF", "KDR", "MET", "FGFR", "IGF1R", "CD310", "TRAIL", "DLL4", "NOTCH"]):
        nature = "Human" # Ensure human if not already viral/bacterial
        category = "Receptor/Signalling"
    elif nature == "Viral":
        category = "Viral Protein"
    elif nature == "Bacterial":
        category = "Bacterial Toxin"
    else:
        category = "Other/Unclassified"
        
    return nature, category

def run_analysis():
    data_path = PROJECT_ROOT / "data" / "humanization_assay" / "thera_human_igG_germline_analysis.xlsx"
    df = pd.read_excel(data_path)
    
    # Apply classification
    df[['Target_Nature', 'Target_Category']] = df['targets_meta'].apply(lambda x: pd.Series(classify_target(x)))
    
    report_path = PROJECT_ROOT / "data" / "humanization_assay" / "categorized_germline_analysis.txt"
    
    with open(report_path, 'w', encoding='utf-8') as f:
        f.write("=" * 80 + "\n")
        f.write("CATEGORIZED TARGET & FRAMEWORK CORRELATION REPORT\n")
        f.write("=" * 80 + "\n\n")
        
        # General distribution of categories
        f.write("1. TARGET CATEGORY DISTRIBUTION\n")
        f.write("-" * 30 + "\n")
        cat_counts = df['Target_Category'].value_counts()
        for cat, count in cat_counts.items():
            f.write(f"{cat}: {count} ({count/len(df)*100:.1f}%)\n")
        f.write("\n")
        
        # Framework Correlation per Category
        f.write("2. FRAMEWORK (GERMLINE) PREFERENCE BY CATEGORY\n")
        f.write("-" * 50 + "\n")
        
        for cat in cat_counts.index:
            sub = df[df['Target_Category'] == cat]
            f.write(f"\n[Category: {cat}]\n")
            f.write(f"Total entries: {len(sub)}\n")
            
            # VH Preference
            f.write("  Top VH Germlines:\n")
            vh_pref = sub['Best_VH_Germline'].value_counts().head(5)
            for gid, count in vh_pref.items():
                f.write(f"    - {gid}: {count} ({count/len(sub)*100:.1f}%)\n")
                
            # VL Preference
            f.write("  Top VL Germlines:\n")
            vl_pref = sub['Best_VL_Germline'].value_counts().head(5)
            for gid, count in vl_pref.items():
                f.write(f"    - {gid}: {count} ({count/len(sub)*100:.1f}%)\n")
        
        f.write("\n" + "=" * 80 + "\n")
        f.write("3. DETAILED TARGETS IN EACH CATEGORY (EXCERPT)\n")
        f.write("=" * 80 + "\n")
        for cat in cat_counts.index:
            unique_targets = df[df['Target_Category'] == cat]['targets_meta'].dropna().unique()[:10]
            f.write(f"\n{cat} Examples: " + ", ".join(unique_targets) + "\n")

    print(f"Report saved to {report_path}")

if __name__ == "__main__":
    run_analysis()
