#!/usr/bin/env python3
"""
 Vernier Zone  (Packing Density)

"""

import os
import sys
import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
import seaborn as sns
from pathlib import Path
from Bio.PDB import PDBParser, NeighborSearch, Selection
import warnings
from Bio.PDB.PDBExceptions import PDBConstructionWarning

#  PDB 
warnings.simplefilter('ignore', PDBConstructionWarning)

#  anarci shim
sys.path.append(os.getcwd())
try:
    import anarci
except ImportError:
    print("Error: local anarci shim not found.")
    sys.exit(1)

from Bio.PDB.Polypeptide import is_aa

THREE_TO_ONE = {
    'ALA': 'A', 'CYS': 'C', 'ASP': 'D', 'GLU': 'E', 'PHE': 'F',
    'GLY': 'G', 'HIS': 'H', 'ILE': 'I', 'LYS': 'K', 'LEU': 'L',
    'MET': 'M', 'ASN': 'N', 'PRO': 'P', 'GLN': 'Q', 'ARG': 'R',
    'SER': 'S', 'THR': 'T', 'VAL': 'V', 'TRP': 'W', 'TYR': 'Y'
}

PROJECT_ROOT = Path(__file__).resolve().parent.parent
STRUCTURE_DIR = PROJECT_ROOT / "data/structures/engineered"
OUTPUT_EXCEL = PROJECT_ROOT / "data/humanization_assay/vernier_structural_metrics.xlsx"
IMG_OUTPUT = PROJECT_ROOT / "data/humanization_assay/packing_density_vh71.png"

#  Vernier  (Kabat Numbering)
TARGET_RESIDUES = {
    "H": [71, 49, 94],
    # "L": [71] # Optional
}

def get_residue_from_structure(structure, chain_id, res_num, insertion_code=' '):
    """
     PDB 
    : ImmuneBuilder  PDB  1 ，
    。 ANARCI 
    Kabat 71  PDB 。
    """
    model = structure[0]
    if chain_id not in model:
        return None
    
    chain = model[chain_id]
    #  PDB  ANARCI  numbering 
    # :  numbering， Kabat 71  Index (0-based)
    #  Chain  Index  Residue
    return None

def calc_contact_number(target_res, atoms, radius=4.5):
    """
     heavy atoms within radius of target side chain
    """
    if target_res is None:
        return np.nan
        
    target_atoms = [a for a in target_res.get_atoms() if a.element != 'H']
    # :  N, CA, C, O
    backbone = ['N', 'CA', 'C', 'O']
    side_chain_atoms = [a for a in target_atoms if a.name not in backbone]
    
    if not side_chain_atoms:
        # Glycine 
        side_chain_atoms = [a for a in target_atoms if a.name == 'CA']
        
    ns = NeighborSearch(atoms)
    contacts = set()
    
    for atom in side_chain_atoms:
        neighbors = ns.search(atom.get_coord(), radius, level='A')
        for n in neighbors:
            if n.get_parent() != target_res: # 
                contacts.add(n)
                
    return len(contacts)

def analyze_structure(pdb_path, parser):
    try:
        structure = parser.get_structure('ab', str(pdb_path))
        
        # 1. 
        seqs = {}
        for chain in structure[0]:
            seq = []
            for res in chain:
                if is_aa(res, standard=True):
                    resname = res.get_resname()
                    val = THREE_TO_ONE.get(resname, 'X')
                    seq.append(val)
            seqs[chain.id] = "".join(seq)
            
        # 2. Numbering to find Kabat positions
        # anarci shim expects list of (id, seq)
        # map PDB chain to sequence
        # We need H chain
        if 'H' not in seqs:
            return None
            
        h_seq = seqs['H']
        # call anarci
        # returns ([[[numbering]]], [{}], [{}])
        # numbering is list of ((pos, ins), aa)
        try:
            numbered_results, _, _ = anarci.anarci([('H', h_seq)], scheme='kabat')
            if not numbered_results or numbered_results[0] is None:
                return None
            
            # format: (seq_info, domain_list, score_list)
            # domain_list[0] is numbering
            numbering = numbered_results[0][1][0]
        except Exception:
            return None
            
        # 3. Find indices for target Kabat positions
        # numbering is a list. The index in this list corresponds to the residue index in PDB chain
        # e.g. numbering[0] is the 1st residue (Bio.PDB index 0)
        
        metrics = {}
        
        # Build atom list for NeighborSearch once
        all_atoms = [a for a in structure.get_atoms() if a.element != 'H']
        
        chain_h = structure[0]['H']
        res_list = list(chain_h.get_residues())
        
        for target_kabat in TARGET_RESIDUES['H']:
            # Find index in numbering where pos == target_kabat
            found_idx = -1
            found_aa = ''
            
            for idx, ((pos, ins), aa) in enumerate(numbering):
                if pos == target_kabat and ins == ' ': # Assume no insertion for key positions usually
                    found_idx = idx
                    found_aa = aa
                    break
            
            col_prefix = f"VH_{target_kabat}"
            if found_idx != -1 and found_idx < len(res_list):
                res = res_list[found_idx]
                # Double check AA identity
                # three_to_one(res.get_resname()) should == found_aa
                
                cn = calc_contact_number(res, all_atoms)
                metrics[f"{col_prefix}_AA"] = found_aa
                metrics[f"{col_prefix}_CN"] = cn
            else:
                metrics[f"{col_prefix}_AA"] = None
                metrics[f"{col_prefix}_CN"] = np.nan
                
        return metrics

    except Exception as e:
        print(f"Error processing {pdb_path.name}: {e}")
        return None

def main():
    print("="*60)
    print("Vernier Zone Structural Packing Analysis")
    print("="*60)
    
    pdb_files = list(STRUCTURE_DIR.glob("*.pdb"))
    print(f"Found {len(pdb_files)} PDB files.")
    
    parser = PDBParser(QUIET=True)
    results = []
    
    for i, pdb_file in enumerate(pdb_files):
        if (i+1) % 50 == 0:
            print(f"Processing {i+1}/{len(pdb_files)}...")
            
        metrics = analyze_structure(pdb_file, parser)
        if metrics:
            metrics['File'] = pdb_file.stem
            results.append(metrics)
            
    df = pd.DataFrame(results)
    
    # Merge with metadata if possible (to get Germline info)
    # For now, just save raw metrics
    print(f"Saving metrics to {OUTPUT_EXCEL}...")
    df.to_excel(OUTPUT_EXCEL, index=False)
    
    print(f"Metrics columns: {df.columns.tolist()}")
    
    # Visualization: VH 71 Packing
    if 'VH_71_CN' in df.columns and 'VH_71_AA' in df.columns:
        print("Columns found, generating plot...")
        plt.figure(figsize=(8, 6))
        # Filter for top AAs
        top_aa = df['VH_71_AA'].value_counts().head(4).index
        plot_df = df[df['VH_71_AA'].isin(top_aa)]
        
        sns.boxplot(x='VH_71_AA', y='VH_71_CN', data=plot_df, palette="Set2")
        plt.title("Packing Density of VH 71 Residues (Engineered)")
        plt.xlabel("Amino Acid at VH 71 (Kabat)")
        plt.ylabel("Contact Number (Heavy Atoms within 4.5A)")
        plt.grid(True, axis='y', alpha=0.3)
        plt.savefig(IMG_OUTPUT)
        # Copy to artifacts
        artifact_path = PROJECT_ROOT / "../../../brain/328e287e-c9ab-48fa-8799-4534421dcf87/packing_density_vh71.png"
        try:
             # Ensure directory exists but in this env we know where we are
             plt.savefig(artifact_path) 
        except:
            pass # Ignore if path tricky
            
        print(f"Plot saved to {IMG_OUTPUT}")

if __name__ == "__main__":
    main()
