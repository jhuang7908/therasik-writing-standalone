import pandas as pd
import numpy as np
from pathlib import Path
import json
import re
import sys

# Add project root to path
PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.append(str(PROJECT_ROOT))

# =============================================================================
# 1. CLINICAL METADATA DICTIONARY (Curation)
# =============================================================================
CLINICAL_DATA = {
    "Caplacizumab": {"Target": "vWF", "Status": "Approved (EU/US)", "Company": "Sanofi/Ablynx", "Indication": "aTTP", "Format": "Bivalent VHH", "Notes": "First approved Nanobody"},
    "Ozoralizumab": {"Target": "TNFα x TNFα x HSA", "Status": "Approved (JP)", "Company": "Taisho/Ablynx", "Indication": "RA", "Format": "Trivalent VHH", "Notes": "Nanozora; Full Resurfacing"},
    "Envafolimab": {"Target": "PD-L1", "Status": "Approved (CN) / Disc (US)", "Company": "3D Med/Tracon", "Indication": "Solid Tumors", "Format": "VHH-Fc", "Notes": "Subcutaneous; US trial missed endpoint"},
    "Vobarilizumab": {"Target": "IL-6R x HSA", "Status": "Discontinued", "Company": "Ablynx/AbbVie", "Indication": "RA/SLE", "Format": "Bivalent VHH", "Notes": "Failed efficacy in SLE; AbbVie returned rights"},
    "Sonelokimab1": {"Target": "IL-17A/F x HSA", "Status": "Phase 3", "Company": "MoonLake", "Indication": "Psoriasis/HS", "Format": "Trivalent VHH", "Notes": "Nanobody (Domain 1)"},
    "Sonelokimab2": {"Target": "IL-17A/F x HSA", "Status": "Phase 3", "Company": "MoonLake", "Indication": "Psoriasis/HS", "Format": "Trivalent VHH", "Notes": "Nanobody (Domain 2)"},
    "Brivekimig1": {"Target": "TNF x OX40L", "Status": "Phase 2", "Company": "Sanofi", "Indication": "HS", "Format": "Bispecific VHH", "Notes": "HS-OBTAIN positive results"},
    "Brivekimig2": {"Target": "TNF x OX40L", "Status": "Phase 2", "Company": "Sanofi", "Indication": "HS", "Format": "Bispecific VHH", "Notes": "Domain 2"},
    "Gefurulimab": {"Target": "C5 x HSA", "Status": "Phase 3", "Company": "Alexion", "Indication": "MG/PNH", "Format": "Trivalent VHH", "Notes": "Ultomiris successor; Grafting strategy"},
    "Enristomig": {"Target": "PD-L1 x 4-1BB", "Status": "Phase 1/2", "Company": "Numab?", "Indication": "Solid Tumors", "Format": "Multispecific", "Notes": "Deep humanization"},
    "Erfonrilimab": {"Target": "PD-L1 x CTLA-4", "Status": "Phase 2", "Company": "Alphamab", "Indication": "Tumors", "Format": "Bispecific VHH", "Notes": "KN046"},
    "Porustobart": {"Target": "CTLA-4", "Status": "Phase 1", "Company": "Harbour BioMed", "Indication": "Tumors", "Format": "HCAb (H2L2)", "Notes": "Harbour Mice platform (Transgenic)"},
    "Letolizumab": {"Target": "CD40L", "Status": "Discontinued/Stalled", "Company": "BMS/Biogen", "Indication": "Autoimmune", "Format": "VHH-Fc?", "Notes": "Target safety risks (thrombo)"},
    "Rimteravimab": {"Target": "SARS-CoV-2 RBD", "Status": "Stalled", "Company": "Multiple", "Indication": "COVID-19", "Format": "VHH-Fc", "Notes": "Lost relevance due to variants"},
    "Ozekibart": {"Target": "DR5 (TNFRSF10B)", "Status": "Phase 1", "Company": "InhibRx/Sanofi?", "Indication": "Tumors", "Format": "Tetravalent VHH", "Notes": "Agonist"},
    "Tarperprumig": {"Target": "Properdin", "Status": "Phase 1", "Company": "Alexion", "Indication": "Complement diseases", "Format": "Bispecific VHH", "Notes": "Alternative pathway inhibitor"},
    "Podentamig": {"Target": "BCMA x CD3 x HSA", "Status": "Phase 1", "Company": "Harpoon/Merck", "Indication": "Myeloma", "Format": "TriTAC (VHH is HSA binder)", "Notes": "VHH likely anti-HSA only"},
    "Isecarosmab": {"Target": "CD123 x CD33", "Status": "Preclinical/Early", "Company": "Sanofi/Ablynx", "Indication": "AML", "Format": "Bispecific VHH", "Notes": "Dual myeloid targeting"},
    "Gocatamig2": {"Target": "DLL3/CD3?", "Status": "Phase 1", "Company": "Daiichi?", "Indication": "SCLC", "Format": "BiTE-like", "Notes": "Neuroendocrine tumors"},
    "Gocatamig": {"Target": "DLL3/CD3?", "Status": "Phase 1", "Company": "Daiichi?", "Indication": "SCLC", "Format": "BiTE-like", "Notes": "Neuroendocrine tumors"} 
}

# Fix ID mapping for table (some IDs in CSV might differ slightly or need mapping)
ID_MAP = {
    "Gocatamig2": "Gocatamig2", 
    "Podentamig1": "Podentamig",
}

# =============================================================================
# 2. SETUP & DATA LOADING
# =============================================================================
PROJECT_ROOT = Path('.').resolve()
MASTER_CSV = PROJECT_ROOT / "reports" / "slice3_vhh_observed_strategy_labels.csv"
HUMAN_LIB = PROJECT_ROOT / "data" / "germlines" / "vhh_v1" / "vhh_germline_assets_clean.jsonl"
OUT_CSV = PROJECT_ROOT / "reports" / "slice3_vhh_comprehensive_functional_library.csv"
OUT_MD = PROJECT_ROOT / "reports" / "slice3_vhh_comprehensive_functional_library.md"

# Load Human Germline Sequences (for mutation checking)
human_germlines = {}
if HUMAN_LIB.exists():
    with open(HUMAN_LIB, 'r', encoding='utf-8') as f:
        for line in f:
            try:
                rec = json.loads(line)
                # Key: "IGHV3-23*01" (strip species tag if needed)
                full_id = rec.get('sequence_id', '')
                short_id = full_id.split('|')[1] if '|' in full_id else full_id
                
                seg = rec.get('segments', {})
                # We need the full FR sequence to map positions
                # For simplicity in this specific "Functional Mutation" check, 
                # we will rely on the Master CSV's 'fr_query' and 'best_human_template_id' 
                # but we need the REFERENCE residues at specific IMGT positions.
                # The JSONL has 'imgt_map'.
                imgt_map = rec.get('imgt_map', {})
                human_germlines[short_id] = imgt_map
            except: pass

# Load Master Data
df = pd.read_csv(MASTER_CSV)

# =============================================================================
# 3. HELPER FUNCTIONS
# =============================================================================

from core.numbering.imgt_anarcii import imgt_number_anarcii_indexed

def get_functional_mutations(row):
    """
    Compare VHH sequence against its Best Human Template.
    Report residues at Hallmark (37,44,45,47) and Vernier (28,29,94)
    IF they differ from human (i.e., retained Alpaca or mutated).
    """
    # 1. Get Query Sequence
    vh_seq = (str(row.get('fr1_query','')) + str(row.get('fr2_query','')) + str(row.get('fr3_query',''))).replace('nan','')
    # We need the full sequence to number it correctly? 
    # Actually, the 'fr_query' columns are just strings. 
    # Better to re-number the full sequence if available, or just map the FR strings.
    # The dataframe doesn't have the full sequence readily available in one col except maybe we can reconstruct.
    # Let's assume we can re-number the concatenated FR parts (approximation) or better, 
    # if 'vh_sequence' was in input. It's not in the labels CSV.
    # We will try to rely on 'mut_hallmark_positions' etc from the CSV if reliable, 
    # BUT the user wants "Specific AA changes" (e.g. L45R). The CSV only gives counts/positions.
    
    # Let's reconstruct approximate seq (CDRs are missing in labels CSV? No, cols are there?)
    # Labels CSV lacks CDR sequences.
    # We MUST load the master table for sequences.
    
    return "Pending Master Merge"

# Load TRUE Master Table for Sequences
TRUE_MASTER = PROJECT_ROOT / "data" / "slice3_vhh_paper_grade_master_table_plus_cdr3_features.csv"
df_seq = pd.read_csv(TRUE_MASTER)
# Merge sequences into df
df = pd.merge(df, df_seq[['antibody_id', 'vh_fr1_fr3', 'cdr1', 'cdr2', 'cdr3']], on='antibody_id', how='left')

# Define Position Sets (IMGT)
HALLMARK_POS = [37, 44, 45, 47]
VERNIER_POS = [28, 29, 94]

def get_full_sequence(row):
    # Reconstruct full sequence from parts to ensure correct numbering
    # Master labels csv has fr1_query... but might not have cdrs.
    # We merged 'cdr1', 'cdr2' from true master.
    f1 = str(row.get('fr1_query', '')).replace('nan', '')
    c1 = str(row.get('cdr1', '')).replace('nan', '')
    f2 = str(row.get('fr2_query', '')).replace('nan', '')
    c2 = str(row.get('cdr2', '')).replace('nan', '')
    f3 = str(row.get('fr3_query', '')).replace('nan', '')
    
    # If any part is missing significantly, fallback?
    # Actually, fr1_query in CSV comes from ANARCII split, so it should be reliable.
    return f1 + c1 + f2 + c2 + f3

def analyze_residues(row):
    """
    Detailed residue analysis.
    """
    seq = get_full_sequence(row)
    
    if len(seq) < 50: return "Seq Error", "Seq Error"
    
    # Number the sequence
    try:
        numbered = imgt_number_anarcii_indexed(seq)
    except:
        return "Numbering Fail", "Numbering Fail"
        
    # Create Map: IMGT_Pos -> AA
    # Note: imgt_number_anarcii_indexed returns rows with 'pos' (str) and 'seq_idx'.
    # We need to handle '42' vs '42A'. Hallmark/Vernier are integers.
    query_map = {}
    for r in numbered['rows']:
        p_str = str(r['pos'])
        if p_str.isdigit():
            query_map[int(p_str)] = r['aa']
            
    # Get Human Germline Map
    h_id_full = row['best_human_template_id'] # e.g. M99660|IGHV3-23*01|Homo
    if pd.isna(h_id_full): return "No Template", "No Template"
    
    h_id = h_id_full.split('|')[1] if '|' in h_id_full else h_id_full
    h_map = human_germlines.get(h_id, {})
    
    if not h_map:
        # Fallback: IGHV3-23*01 map (Universal) if specific missing
        h_map = human_germlines.get('IGHV3-23*01', {})
        
    # Analyze Hallmark
    hallmark_res = []
    for p in HALLMARK_POS:
        q_aa = query_map.get(p, '-')
        h_aa = h_map.get(str(p), '?')
        if q_aa != '-' and q_aa != h_aa:
            hallmark_res.append(f"{q_aa}{p} (Hu:{h_aa})")
    
    # Analyze Vernier
    vernier_res = []
    for p in VERNIER_POS:
        q_aa = query_map.get(p, '-')
        h_aa = h_map.get(str(p), '?')
        if q_aa != '-' and q_aa != h_aa:
            vernier_res.append(f"{q_aa}{p} (Hu:{h_aa})")
            
    h_str = ", ".join(hallmark_res) if hallmark_res else "Fully Human"
    v_str = ", ".join(vernier_res) if vernier_res else "Fully Human"
    
    return h_str, v_str

# =============================================================================
# 4. EXECUTION & LOGIC APPLICATION
# =============================================================================

# Apply Strategy Logic (Refined)
def refine_strategy(row):
    # My Class Logic from previous turn
    if row['delta_human_minus_alpaca_fr23'] > 0:
        return 'BM (Grafting)'
    elif row['vh_identity_global'] > 0.85:
        # Check Hallmark count to distinguish SR types
        # We can use the column 'mut_hallmark' from labels csv (it counts mismatches from human)
        # If mut_hallmark >= 2, it's SR (Hallmark Retained)
        if row['mut_hallmark'] >= 2:
            return 'SR (Hallmark Retained)'
        else:
            return 'SR (Surface Only)'
    else:
        return 'Native'

df['Inferred_Strategy'] = df.apply(refine_strategy, axis=1)

# Apply Residue Analysis
df[['Functional_Hallmarks', 'Functional_Vernier']] = df.apply(lambda r: pd.Series(analyze_residues(r)), axis=1)

# Map Clinical Data
def get_clinical(id_val, field):
    # Try direct match
    if id_val in CLINICAL_DATA:
        return CLINICAL_DATA[id_val].get(field, '-')
    # Try mapped match
    mapped = ID_MAP.get(id_val)
    if mapped and mapped in CLINICAL_DATA:
        return CLINICAL_DATA[mapped].get(field, '-')
    # Try fuzzy
    for k in CLINICAL_DATA:
        if k in id_val:
            return CLINICAL_DATA[k].get(field, '-')
    return "Unknown"

df['Target'] = df['antibody_id'].apply(lambda x: get_clinical(x, 'Target'))
df['Status'] = df['antibody_id'].apply(lambda x: get_clinical(x, 'Status'))
df['Company'] = df['antibody_id'].apply(lambda x: get_clinical(x, 'Company'))
df['Indication'] = df['antibody_id'].apply(lambda x: get_clinical(x, 'Indication'))

# Final Columns Selection
final_cols = [
    'antibody_id', 
    'Target', 'Status', 'Indication', 'Company',
    'Inferred_Strategy',
    'Functional_Hallmarks', 'Functional_Vernier',
    'vh_identity_global',
    'best_human_template_id',
    'h2_north', 'h2_len', 
    'best_human_fr4_j_id',
    'delta_human_minus_alpaca_fr23'
]

out_df = df[final_cols].copy()

# Rename for readability
out_df.columns = [
    'Drug Name', 'Target', 'Clinical Status', 'Indication', 'Company',
    'Humanization Strategy',
    'Hallmark Mutations (vs Human)', 'Vernier Mutations (vs Human)',
    'Global Human Identity', 'Best Human Germline', 
    'H2 Class', 'H2 Length', 'FR4 Source', 'FR2/3 Delta (Hu-Alp)'
]

# Write CSV
out_df.to_csv(OUT_CSV, index=False)
print(f"Wrote CSV: {OUT_CSV}")

# Write Markdown Report
with open(OUT_MD, 'w', encoding='utf-8') as f:
    f.write("# Slice-3 VHH Comprehensive Functional Library\n\n")
    f.write("## 1. Clinical & Strategy Overview\n\n")
    f.write(out_df[['Drug Name', 'Humanization Strategy', 'Target', 'Clinical Status', 'Global Human Identity']].to_markdown(index=False))
    
    f.write("\n\n## 2. Functional Mutation Analysis (Back-Mutations)\n")
    f.write("These residues indicate retention of Alpaca features against the human germline baseline.\n\n")
    f.write(out_df[['Drug Name', 'Humanization Strategy', 'Hallmark Mutations (vs Human)', 'Vernier Mutations (vs Human)']].to_markdown(index=False))

print(f"Wrote MD: {OUT_MD}")
