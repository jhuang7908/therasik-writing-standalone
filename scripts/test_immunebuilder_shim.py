import sys
import os

# 1. Patch anarci BEFORE importing ImmuneBuilder
from anarcii import Anarcii

def legacy_anarci(sequences, scheme="imgt", **kwargs):
    engine = Anarcii()
    results_raw = engine.number(sequences)
    if scheme != "imgt":
        results_raw = engine.to_scheme(scheme)
    formatted_results = []
    alignment_details = []
    hit_tables = []
    for seq_id, seq in sequences:
        res = results_raw.get(seq_id, {})
        if res:
            numbering = res.get('numbering', [])
            formatted_results.append([[numbering]])
        else:
            formatted_results.append(None)
        alignment_details.append({})
        hit_tables.append({})
    return formatted_results, alignment_details, hit_tables

# Create mock module
import types
m = types.ModuleType("anarci")
m.anarci = legacy_anarci
m.validate_sequence = lambda x: True
m.scheme_short_to_long = {
    'imgt': 'imgt', 'kabat': 'kabat', 'chothia': 'chothia', 'aho': 'aho', 'martin': 'martin',
    'i': 'imgt', 'k': 'kabat', 'c': 'chothia', 'a': 'aho', 'm': 'martin'
}
sys.modules["anarci"] = m

# 2. Patch pdbfixer/simtk to avoid heavy dependencies if only doing basic modeling
from unittest.mock import MagicMock
for mod in ["pdbfixer", "simtk", "simtk.openmm", "simtk.openmm.app", "simtk.unit"]:
    sys.modules[mod] = MagicMock()

# 3. Now try to import ImmuneBuilder
try:
    from ImmuneBuilder import ABodyBuilder2
    print("SUCCESS: ABodyBuilder2 imported successfully!")
    
    # Simple test case (Nivolumab sequences)
    vh = "QVQLVESGGGVVQPGRSLRLDCKASGITFSNSGMHWVRQAPGKGLEWVAVIWYDGSKRYYADSVKGRFTISRDNSKNTLFLQMNSLRAEDTAVYYCATNDDYWGQGTLVTVSS"
    vl = "EIVLTQSPATLSLSPGERATLSCRASQSVSSYLAWYQQKPGQAPRLLIYDASNRATGIPARFSGSGSGTDFTLTISSLEPEDFAVYYCQQSSNWPRTFGQGTKVEIK"
    
    predictor = ABodyBuilder2()
    print("Predicting structure...")
    # This might fail if it tries to do refinement (OpenMM needed), but let's see
    # ABodyBuilder2 usually doesn't refine by default unless asked, or it might fail at the end
    antibody = predictor.predict({'H': vh, 'L': vl})
    print("Prediction complete!")
    
    output_pdb = "test_prediction.pdb"
    # Use save_single_unrefined to bypass OpenMM refinement issues in this test
    antibody.save_single_unrefined(output_pdb)
    print(f"Structure saved to {output_pdb}")
    
except Exception as e:
    print(f"FAILED: {str(e)}")
    import traceback
    traceback.print_exc()
