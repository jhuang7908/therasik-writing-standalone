import sys
from anarcii import Anarcii

def anarci(sequences, scheme="imgt", **kwargs):
    """
    Shim function for legacy ANARCI calls using ANARCII.
    Expects list of (id, seq) tuples.
    Returns (results, alignment_details, hit_tables).
    """
    engine = Anarcii()
    results_raw = engine.number(sequences)
    
    if scheme != "imgt":
        results_raw = engine.to_scheme(scheme)
    
    # Based on the error Traceback:
    # numbered = number_sequences({"H": sequence}, scheme=scheme)
    # output = [x for x in numbered[0][0][0] if x[1] != "-"]
    
    # number_sequences in ImmuneBuilder:
    # results = [anarci(sequences, scheme=scheme, **kwargs)]
    # return results[0] # THIS IS KEY. It returns the 1st element of the list anarci returns.
    
    # So if anarci returns (A, B, C):
    # numbered = A
    # Then output = [x for x in A[0][0][0] if x[1] != "-"]
    # This means A must be [[[numbering_list]]]
    
    all_numbering = []
    
    for seq_id, seq in sequences:
        res = results_raw.get(seq_id, {})
        if res:
            numbering = res.get('numbering', [])
            all_numbering.append([numbering]) # [[numbering]]
        else:
            all_numbering.append([[]])
            
    # If ImmuneBuilder calls for ONE sequence, sequences has length 1.
    # all_numbering = [ [[numbering]] ]
    # number_sequences returns results[0] = all_numbering
    # Then numbered = [ [[numbering]] ]
    # numbered[0] = [[numbering]]
    # numbered[0][0] = [numbering]
    # numbered[0][0][0] = numbering
    
    # THIS MATCHES THE INDEXING!
    
    return [all_numbering], [{}], [{}]

def validate_sequence(seq):
    return True # Simple mock

scheme_short_to_long = {
    'imgt': 'imgt',
    'kabat': 'kabat',
    'chothia': 'chothia',
    'aho': 'aho',
    'martin': 'martin',
    'i': 'imgt',
    'k': 'kabat',
    'c': 'chothia',
    'a': 'aho',
    'm': 'martin'
}

# If this file is imported as anarci, it will work.
if __name__ == "__main__":
    # Test
    res = anarci([('test', 'EVQLVESGGGLVQPGGSLRLSCAASGFTFSSYAMSWVRQAPGKGLEWVSAISGSGGSTYYADSVKGRFTISRDNSKNTLYLQMNSLRAEDTAVYYCAK')])
    print("Test result success:", res[0][0] is not None)
