#!/usr/bin/env python3
"""
 ImmuneBuilder (ABodyBuilder2) 
 458  Engineered 
"""

import os
import sys
import pandas as pd
from pathlib import Path
import time
import logging

#  anarci shim
sys.path.append(os.getcwd())

try:
    from ImmuneBuilder import ABodyBuilder2
except ImportError:
    print("Error: ImmuneBuilder not found. Please ensure it is installed.")
    sys.exit(1)

# 
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler("modeling_progress.log"),
        logging.StreamHandler()
    ]
)

PROJECT_ROOT = Path(__file__).resolve().parent.parent
OUTPUT_DIR = PROJECT_ROOT / "data/structures/engineered"
OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

def main():
    # 1. 
    data_path = PROJECT_ROOT / "data/humanization_assay/thera_human_igG_germline_analysis.xlsx"
    df = pd.read_excel(data_path)
    
    #  Engineered 
    # ： 'Name', 'VH', 'VL'
    engineered = df[df['human_origin_mode'] == 'engineered_humanisation'].copy()
    engineered = engineered.reset_index(drop=True)
    
    total = len(engineered)
    logging.info(f"， {total} ...")
    
    #  ABodyBuilder2
    predictor = ABodyBuilder2()
    
    success_count = 0
    fail_count = 0
    
    start_time = time.time()
    
    for i, row in engineered.iterrows():
        #  INN， Name
        name = row.get('INN')
        if pd.isna(name) or str(name).strip() == '':
            name = row.get('Name', f"Ab_{i}")
            
        # 
        safe_name = "".join([c if c.isalnum() else "_" for c in str(name)])
        pdb_path = OUTPUT_DIR / f"{safe_name}.pdb"
        
        # ， ()
        if pdb_path.exists():
            success_count += 1
            continue
            
        vh_seq = row.get('VH')
        vl_seq = row.get('VL')
        
        if pd.isna(vh_seq) or pd.isna(vl_seq):
            logging.warning(f"[{i+1}/{total}] : {safe_name}")
            fail_count += 1
            continue
            
        seqs = {"H": vh_seq, "L": vl_seq}
        
        try:
            # 
            antibody = predictor.predict(seqs)
            
            #  save_single_unrefined  OpenMM 
            antibody.save_single_unrefined(str(pdb_path))
            
            success_count += 1
            logging.info(f"[{i+1}/{total}] [] {safe_name} -> {pdb_path.name}")
            
        except Exception as e:
            fail_count += 1
            logging.error(f"[{i+1}/{total}] [] {safe_name}: {str(e)}")
            
        #  10 
        if (i + 1) % 10 == 0:
            elapsed = time.time() - start_time
            avg_time = elapsed / (i + 1)
            remaining = avg_time * (total - (i + 1))
            logging.info(f">>> : {i+1}/{total} | : {success_count} | : {fail_count} | : {remaining/60:.1f} min")

    end_time = time.time()
    logging.info("="*50)
    logging.info(f"! : {(end_time - start_time)/60:.1f} min")
    logging.info(f": {success_count} | : {fail_count}")
    logging.info(f": {OUTPUT_DIR}")
    logging.info("="*50)

if __name__ == "__main__":
    main()
