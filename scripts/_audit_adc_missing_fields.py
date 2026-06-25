import json
from pathlib import Path

MASTER_PATH = Path('data/adc_atlas/adc_master_internal.json')
COMPONENTS_PATH = Path('data/adc_atlas/adc_components.json')
REPORT_PATH = Path('reports/adc_missing_fields_audit.md')

def audit_missing_fields():
    master = json.loads(MASTER_PATH.read_text(encoding='utf-8'))
    components = json.loads(COMPONENTS_PATH.read_text(encoding='utf-8'))
    
    missing_report = [
        "# ADC Internal Database - Missing Fields Audit",
        "This report identifies critical missing data (Sequences, SMILES, PMIDs, DAR) required for a complete knowledge base.",
        ""
    ]
    
    # 1. Audit Programs
    missing_report.append("## 1. ADC Programs Missing Critical Data")
    missing_report.append("| ID | Drug Name | Missing Fields |")
    missing_report.append("|---|---|---|")
    
    for prog in master:
        missing = []
        
        # Check source
        source = prog.get("source_primary", "")
        if not source or source == "unknown":
            missing.append("`source_primary` (PMID/NCT)")
            
        # Check DAR
        dar = prog.get("dar_mean")
        if dar is None or dar == "unknown":
            missing.append("`dar_mean`")
            
        # Check Sequence
        seq_data = prog.get("sequence_data", {})
        if not seq_data:
            missing.append("`sequence_data` (VH/VL/PDB)")
            
        if missing:
            missing_report.append(f"| {prog.get('id')} | **{prog.get('canonical_name')}** | {', '.join(missing)} |")
            
    # 2. Audit Components
    missing_report.append("\n## 2. ADC Components Missing Molecular Structure (SMILES)")
    missing_report.append("| ID | Component Name | Type | Missing Fields |")
    missing_report.append("|---|---|---|---|")
    
    for comp in components:
        missing = []
        mol_struct = comp.get("molecular_structure", {})
        if not mol_struct or "smiles" not in mol_struct:
            missing.append("`SMILES`")
            
        if missing:
            c_type = "Linker" if "ADC-COMP-L" in comp.get("id", "") else "Payload"
            missing_report.append(f"| {comp.get('id')} | **{comp.get('name')}** | {c_type} | {', '.join(missing)} |")
            
    REPORT_PATH.parent.mkdir(parents=True, exist_ok=True)
    REPORT_PATH.write_text("\n".join(missing_report), encoding='utf-8')
    print(f"Audit report generated at {REPORT_PATH}")

if __name__ == "__main__":
    audit_missing_fields()
