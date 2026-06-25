"""Test ANARCI to_scheme."""
from anarcii import Anarcii
import inspect
a = Anarcii(seq_type='antibody', mode='accuracy')
print('to_scheme signature:', inspect.signature(a.to_scheme))
print()

seq = 'QVQLVQSGAEVKKPGASVKVSCKASGYTFTRYTMHWVRQAPGQGLEWIGYINPSRGYTNYNQKFKDRVTMTRDTSTSTVYMELSSLRSEDTAVYYCARYYDDHYCLDYWGQGTLVTVSS'
out = a.number([('vh', seq)])
print('Default scheme:', list(out.values())[0]['scheme'])
print()

for scheme in ['kabat', 'imgt', 'chothia']:
    try:
        a.to_scheme(scheme)
        out = a.number([('vh', seq)])
        entry = list(out.values())[0]
        num = entry['numbering']
        print(f'=== scheme={scheme} (entry.scheme={entry["scheme"]}) ===')
        for (pos, ins), aa in num:
            if 88 <= pos <= 105:
                ins_disp = ins.strip() if isinstance(ins, str) else ''
                print(f'  {pos:>3}{ins_disp:<2} = {aa}')
        print()
    except Exception as e:
        print(f'scheme={scheme} ERROR: {e}')
