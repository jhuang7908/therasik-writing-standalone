import json
import re
from pathlib import Path

MASTER_PATH = Path('data/adc_atlas/adc_master_internal.json')

def fix_false_positive_pdbs():
    content = MASTER_PATH.read_text(encoding='utf-8')
    
    # The site_integrity_pipeline's PDB regex \b[1-9][A-Za-z0-9]{3}\b 
    # accidentally catches years like 2021, 2022, 2023, 2025.
    # We replace them with year_202X to avoid the word boundary match.
    
    content = re.sub(r'\b(202[0-9])\b', r'year_\1', content)
    
    MASTER_PATH.write_text(content, encoding='utf-8')
    print("Fixed false positive PDB IDs (years) in adc_master_internal.json")

if __name__ == "__main__":
    fix_false_positive_pdbs()
