"""Find ANARCI scheme API."""
from anarcii import Anarcii
a = Anarcii(seq_type='antibody', mode='accuracy')
print('Methods/attrs on Anarcii instance:')
print([m for m in dir(a) if not m.startswith('_')])
print()
# Test default output
seq = 'QVQLVQSGAEVKKPGASVKVSCKASGYTFTRYTMHWVRQAPGQGLEWIGYINPSRGYTNYNQKFKDRVTMTRDTSTSTVYMELSSLRSEDTAVYYCARYYDDHYCLDYWGQGTLVTVSS'
out = a.number([('vh', seq)])
print('Output type:', type(out))
print('First entry keys:', list(out[0].keys()) if isinstance(out, list) else list(out.values())[0].keys() if isinstance(out, dict) else 'unknown')
entry = out[0] if isinstance(out, list) else list(out.values())[0]
print('Numbering[:5]:', entry['numbering'][:5])
print()
# Check if there's a to_scheme method
print('to_scheme method?', hasattr(a, 'to_scheme'))
# Try scheme on number() method?
import inspect
print('number() signature:', inspect.signature(a.number))
