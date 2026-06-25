"""Map IMGT positions to canonical residues for known IGHV3-23 sequence."""
from anarcii import Anarcii

# OKT3 IGHV1-humanized (KKPG framework)
seq = 'QVQLVQSGAEVKKPGASVKVSCKASGYTFTRYTMHWVRQAPGQGLEWIGYINPSRGYTNYNQKFKDRVTMTRDTSTSTVYMELSSLRSEDTAVYYCARYYDDHYCLDYWGQGTLVTVSS'
# Foralumab IGHV3 (SGGG framework)  
seq2 = 'QVQLVESGGGVVQPGRSLRLSCAASGFKFSGYGMHWVRQAPGKGLEWVAVIWYDGSKKYYVDSVKGRFTISRDNSKNTLYLQMNSLRAEDTAVYYCARQMGYWHFDLWGRGTLVTVSS'

a = Anarcii(seq_type='antibody', mode='accuracy')

for name, s in [('OKT3 (IGHV1)', seq), ('Foralumab (IGHV3)', seq2)]:
    out = a.number([('vh', s)])
    entry = list(out.values())[0]
    num = entry['numbering']
    print(f'=== {name} ===')
    print(f'  Default scheme = {entry["scheme"]}')
    print(f'  All positions (IMGT/raw):')
    for (pos, ins), aa in num:
        ins_s = ins.strip() if isinstance(ins, str) else ''
        marker = ''
        # Annotate likely key positions
        if pos in (38, 39, 40, 41, 42): marker = '  ← FR2 start (W/V)'
        if pos in (51, 52, 53, 54, 55): marker = '  ← FR2 Hallmark zone'
        if pos in (78, 79, 80, 81, 82, 83): marker = '  ← FR3 middle'
        if pos == 104: marker = '  ← canonical Cys (end FR3)'
        if pos == 105: marker = '  ← CDR3 base IMGT'
        if 105 <= pos <= 117: marker = '  ← CDR3 IMGT'
        if pos == 118: marker = '  ← W start FR4'
        print(f'    {pos:>3}{ins_s:<2} = {aa}{marker}')
    print()
