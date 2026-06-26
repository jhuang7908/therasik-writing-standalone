import pandas as pd
import numpy as np
import json
import yaml
import os
import sys
import math
from pathlib import Path
from collections import Counter

# Add project root to path for internal imports
PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.append(str(PROJECT_ROOT))

# Try to import numbering tool
try:
    from core.numbering.imgt_anarcii import imgt_number_anarcii
    HAS_ANARCII = True
except (ImportError, Exception):
    HAS_ANARCII = False

def calculate_shannon_entropy(residues):
    """
    residues: list of amino acids at a position.
    """
    residues = [r for r in residues if r and r != '-']
    if not residues: return 0.0
    
    counts = Counter(residues)
    total = sum(counts.values())
    
    entropy = 0.0
    for count in counts.values():
        p = count / total
        entropy -= p * math.log2(p)
    return entropy

def main():
    # Paths
    master_csv = PROJECT_ROOT / "data" / "slice3_vhh_paper_grade_master_table_plus_cdr3_features.csv"
    numbering_parquet = PROJECT_ROOT / "data" / "thera_sabdab" / "features" / "anarcii_numbering_slice_3_vhh_design.parquet"
    imgt_yaml_path = PROJECT_ROOT / "core" / "data" / "position_sets" / "imgt_position_sets.yaml"
    
    output_csv = PROJECT_ROOT / "output" / "nd_dependent_slice3_v2_lite_by_class.csv"
    output_summary = PROJECT_ROOT / "output" / "nd_dependent_slice3_v2_lite_summary.md"
    output_audit = PROJECT_ROOT / "output" / "nd_dependent_slice3_v2_lite_audit.md"
    output_yaml_copy = PROJECT_ROOT / "output" / "imgt_position_sets_updated.yaml"

    os.makedirs(PROJECT_ROOT / "output", exist_ok=True)

    # 1. Load data
    df_master = pd.read_csv(master_csv)
    
    # Try to load existing YAML
    if imgt_yaml_path.exists():
        with open(imgt_yaml_path, 'r', encoding='utf-8') as f:
            imgt_yaml = yaml.safe_load(f)
    else:
        imgt_yaml = {"imgt_position_sets": {}}
    
    pos_sets = imgt_yaml.get('imgt_position_sets', {})
    exclusions = set()
    exclusions.update(pos_sets.get('imgt_anchor_positions', []))
    exclusions.update(pos_sets.get('vhh_hallmark_positions', []))
    exclusions.update(pos_sets.get('vernier_anchor_positions', []))

    # 2. Numbering (with fallback)
    residue_data = []
    audit_notes = []
    
    if HAS_ANARCII and numbering_parquet.exists():
        df_numbering = pd.read_parquet(numbering_parquet)
        df = df_master.merge(df_numbering[['antibody_id', 'vh_sequence']], on='antibody_id', how='left')
        
        print(f"Numbering {len(df)} records for Slice-3...")
        fr_ranges = [(1, 26), (39, 55), (66, 104)]
        
        for _, row in df.iterrows():
            ab_id = row['antibody_id']
            seq = row['vh_sequence']
            if not seq or pd.isna(seq): continue
            
            try:
                numbering = imgt_number_anarcii(seq)
                row_residues = {'antibody_id': ab_id}
                for item in numbering:
                    pos = item['pos']
                    aa = item['aa']
                    if any(start <= pos <= end for start, end in fr_ranges):
                        row_residues[pos] = aa
                residue_data.append(row_residues)
            except Exception:
                continue
        
        if not residue_data:
            audit_notes.append("Numbering failed for all sequences even though ANARCII was available.")
        else:
            audit_notes.append(f"Successfully numbered {len(residue_data)} sequences.")
    else:
        if not HAS_ANARCII:
            audit_notes.append("ANARCII package not available in current environment.")
        if not numbering_parquet.exists():
            audit_notes.append(f"Numbering parquet not found at {numbering_parquet}")
        audit_notes.append("Fallback: Proceeding with empty North-Dunbrack dependent sets.")

    # 3. Process results (even if empty)
    results = []
    nd_v2_lite = {
        'method': "slice3_entropy_contrast",
        'thresholds': {
            'entropy_in_class_max': 0.35,
            'entropy_contrast_min': 0.20,
            'min_class_n_core': 5,
            'min_class_n_candidate': 3,
            'min_coverage_core': 0.80
        },
        'exclusions': sorted(list(exclusions)),
        'H1': {},
        'H2': {}
    }

    if residue_data:
        df_residues = pd.DataFrame(residue_data).set_index('antibody_id')
        df_merged = df_master[['antibody_id', 'h1_north', 'h2_north']].merge(df_residues, left_on='antibody_id', right_index=True)
        
        # Inference logic...
        h1_classes = df_merged['h1_north'].unique()
        h2_classes = df_merged['h2_north'].unique()
        
        T_H_IN = 0.35
        T_H_CONTRAST = 0.20
        MIN_N_CORE = 5
        MIN_N_CANDIDATE = 3
        MIN_COV_CORE = 0.80

        for region, classes, col in [('H1', h1_classes, 'h1_north'), ('H2', h2_classes, 'h2_north')]:
            for cls in classes:
                if pd.isna(cls) or cls == 'unknown' or cls == '?': continue
                
                df_cls = df_merged[df_merged[col] == cls]
                df_others = df_merged[df_merged[col] != cls]
                n_seq = len(df_cls)
                
                nd_v2_lite[region][cls] = {'core': [], 'candidate': []}
                if n_seq < MIN_N_CANDIDATE: continue
                
                for pos in [p for p in df_residues.columns if isinstance(p, int)]:
                    if pos in exclusions: continue
                    res_cls = df_cls[pos].dropna().tolist()
                    res_others = df_others[pos].dropna().tolist()
                    if len(res_cls) < MIN_N_CANDIDATE: continue
                    
                    h_cls = calculate_shannon_entropy(res_cls)
                    h_others = calculate_shannon_entropy(res_others)
                    coverage = len(res_cls) / n_seq
                    
                    is_conserved = h_cls <= T_H_IN
                    is_contrasted = (h_others - h_cls) >= T_H_CONTRAST
                    
                    tier = None
                    if is_conserved and is_contrasted and n_seq >= MIN_N_CORE and coverage >= MIN_COV_CORE:
                        tier = 'core'
                        nd_v2_lite[region][cls]['core'].append(int(pos))
                    elif (is_conserved or is_contrasted) and n_seq >= MIN_N_CANDIDATE:
                        tier = 'candidate'
                        nd_v2_lite[region][cls]['candidate'].append(int(pos))
                    
                    if tier:
                        results.append({
                            'region': region, 'class_label': cls, 'n_sequences': n_seq,
                            'position': pos, 'entropy_in_class': round(h_cls, 4),
                            'entropy_outside': round(h_others, 4), 'tier': tier,
                            'coverage': round(coverage, 4), 'notes': f"H_in={h_cls:.2f}, H_out={h_others:.2f}"
                        })
    else:
        # Fallback empty classes from master table
        h1_classes = df_master['h1_north'].dropna().unique()
        h2_classes = df_master['h2_north'].dropna().unique()
        for region, classes in [('H1', h1_classes), ('H2', h2_classes)]:
            for cls in classes:
                if cls == 'unknown' or cls == '?': continue
                nd_v2_lite[region][cls] = {'core': [], 'candidate': []}

    # 4. Save Artifacts
    df_results = pd.DataFrame(results if results else [
        {'region': 'N/A', 'class_label': 'N/A', 'n_sequences': 0, 'position': 0, 
         'entropy_in_class': 0.0, 'entropy_outside': 0.0, 'tier': 'none', 'coverage': 0.0, 'notes': 'fallback empty'}
    ])
    df_results.to_csv(output_csv, index=False)
    
    with open(output_summary, 'w', encoding='utf-8') as f:
        f.write("# North–Dunbrack Dependent Positions (Slice-3 v2-lite) Summary\n\n")
        f.write("## Results\n")
        if not results:
            f.write("⚠️ **WARNING**: No dependent positions were inferred due to missing numbering data or small sample sizes.\n\n")
        else:
            summary_rows = []
            for region in ['H1', 'H2']:
                for cls, sets in nd_v2_lite[region].items():
                    summary_rows.append({'Region': region, 'Class': cls, 'Core': len(sets['core']), 'Candidate': len(sets['candidate'])})
            f.write(pd.DataFrame(summary_rows).to_markdown(index=False) + "\n\n")
        f.write("## Note\nSlice-3 only v2-lite; to be validated with Slice-1 VH in future release.\n")

    with open(output_audit, 'w', encoding='utf-8') as f:
        f.write("# Position Sets Generation Audit (ND-dependent v2-lite)\n\n")
        for note in audit_notes:
            f.write(f"- {note}\n")
        f.write(f"- **Exclusions Applied**: {sorted(list(exclusions))}\n")
        f.write("- **Thresholds**: entropy_in <= 0.35, contrast >= 0.20\n")
        f.write("- **Explicit Note**: Slice-3 only v2-lite; to be validated with Slice-1 VH in future release.\n")

    # 5. Update YAML
    if 'north_dunbrack' not in imgt_yaml:
        imgt_yaml['north_dunbrack'] = {}
    imgt_yaml['north_dunbrack']['dependent_positions_v2_lite'] = nd_v2_lite
    
    with open(imgt_yaml_path, 'w', encoding='utf-8') as f:
        yaml.dump(imgt_yaml, f, sort_keys=False, default_flow_style=False)
    
    with open(output_yaml_copy, 'w', encoding='utf-8') as f:
        yaml.dump(imgt_yaml, f, sort_keys=False, default_flow_style=False)
    
    print(f"Updated YAML saved to {imgt_yaml_path}")

if __name__ == "__main__":
    main()
