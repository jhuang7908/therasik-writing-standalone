#!/usr/bin/env python3
import os
import sys
from pathlib import Path

#  anarci shim
sys.path.append(os.getcwd())

from ImmuneBuilder.sequence_checks import number_sequences

def main():
    vh = "QVQLVESGGGVVQPGRSLRLDCKASGITFSNSGMHWVRQAPGKGLEWVAVIWYDGSKRYYADSVKGRFTISRDNSKNTLFLQMNSLRAEDTAVYYCATNDDYWGQGTLVTVSS"
    
    #  anarci ，
    #  number_sequences  IndexError
    
    print("Testing structural requirements...")
    
    #  anarci 
    #  ImmuneBuilder/sequence_checks.py:23
    # numbered = number_sequences({"H": sequence}, scheme=scheme)
    # output = [x for x in numbered[0][0][0] if x[1] != "-"]
    
    #  number_sequences  [[ [ (pos, aa), ... ] ]]
    
    def mock_anarci(sequences, scheme="imgt", **kwargs):
        # 
        numbering = [((1, ' '), 'Q'), ((2, ' '), 'V')] # 
        #  ImmuneBuilder ：
        # numbered["H"] = results[0] -> results[0] 
        # results[0][0] -> 
        # results[0][0][0] ->  (numbering)
        return [[[numbering]]], [{}], [{}]

    #  anarci () 
    import anarci
    anarci.anarci = mock_anarci
    
    try:
        res = number_sequences({"H": vh})
        print("Success! Number sequences returned:", res)
        #  number_single_sequence 
        # output = [x for x in res[0][0][0] if x[1] != "-"]
        print("Final level access test:", res[0][0][0][0])
    except Exception as e:
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    main()
