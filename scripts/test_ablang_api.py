import sys
import ablang

m = ablang.pretrained('heavy')
m.freeze()
seq = 'QVQLVQSGAEVVKPGSSVKLSCKASGFNIKDTYIHWVKQRPEQGREWIGRIYPTNGYTRYDPKFQDRATITADTSTSTAYLEVSRLRSEDTAVYYCSRWGGDGFYAMDYWGQGASVTVSS'

for mode in ['likelihood', 'probability', 'pseudo_log_likelihood', 'seqcoding', 'rescoding']:
    try:
        result = m([seq], mode=mode)
        sys.stderr.write(f"mode={mode}: type={type(result)}, shape={getattr(result, 'shape', 'N/A')}\n")
        if hasattr(result, 'shape') and len(result.shape) <= 1:
            sys.stderr.write(f"  value: {result}\n")
        elif hasattr(result, '__len__') and len(result) <= 3:
            sys.stderr.write(f"  value: {result}\n")
    except Exception as e:
        sys.stderr.write(f"mode={mode}: ERROR {e}\n")

try:
    result = m.likelihood([seq])
    sys.stderr.write(f"m.likelihood: type={type(result)}\n")
    sys.stderr.write(f"  value: {result}\n")
except Exception as e:
    sys.stderr.write(f"m.likelihood: ERROR {e}\n")
