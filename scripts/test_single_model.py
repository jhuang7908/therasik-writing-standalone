#!/usr/bin/env python3
import os
import sys
from pathlib import Path

#  anarci shim
sys.path.append(os.getcwd())

from ImmuneBuilder import ABodyBuilder2

def main():
    print("Initializing ABodyBuilder2...")
    predictor = ABodyBuilder2()
    
    # Nivolumab sequences
    vh = "QVQLVESGGGVVQPGRSLRLDCKASGITFSNSGMHWVRQAPGKGLEWVAVIWYDGSKRYYADSVKGRFTISRDNSKNTLFLQMNSLRAEDTAVYYCATNDDYWGQGTLVTVSS"
    vl = "EIVLTQSPATLSLSPGERATLSCRASQSVSSYLAWYQQKPGQAPRLLIYDASNRATGIPARFSGSGSGTDFTLTISSLEPEDFAVYYCQQSSNWPRTFGQGTKVEIK"
    seqs = {"H": vh, "L": vl}
    
    print("Starting prediction...")
    try:
        antibody = predictor.predict(seqs)
        print("Prediction successful.")
        out_path = "test_batch_model.pdb"
        antibody.save_single_unrefined(out_path)
        print(f"Saved to {out_path}")
    except Exception as e:
        import traceback
        traceback.print_exc()
        print(f"Error during prediction: {e}")

if __name__ == "__main__":
    main()
