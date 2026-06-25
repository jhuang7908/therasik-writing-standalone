"""Debug ANARCI numbering scheme."""
import sys
from anarcii import Anarcii
import inspect

sig = inspect.signature(Anarcii.__init__)
print('Anarcii init params:', list(sig.parameters.keys()))

seq = 'QVQLVQSGAEVKKPGASVKVSCKASGYTFTRYTMHWVRQAPGQGLEWIGYINPSRGYTNYNQKFKDRVTMTRDTSTSTVYMELSSLRSEDTAVYYCARYYDDHYCLDYWGQGTLVTVSS'

for scheme in ['imgt', 'kabat', 'chothia']:
    try:
        a = Anarcii(seq_type='antibody', mode='accuracy', scheme=scheme)
        out = a.number([('vh', seq)])
        entry = out[0] if isinstance(out, list) else out['vh']
        num = entry['numbering']
        print(f'\n=== scheme={scheme} ===')
        # Show positions 90-105
        for (pos, ins), aa in num:
            if 88 <= pos <= 105:
                ins_disp = ins if isinstance(ins, str) and ins.strip() else ''
                print(f'  {pos:>3}{ins_disp:<2} = {aa}')
    except TypeError as e:
        print(f'scheme={scheme} not supported via constructor: {e}')
    except Exception as e:
        print(f'scheme={scheme} ERROR: {e}')
