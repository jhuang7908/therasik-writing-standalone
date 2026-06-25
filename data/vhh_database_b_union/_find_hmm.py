import anarci, os
pkg = os.path.dirname(anarci.__file__)
hmm_dir = os.path.join(pkg, 'dat', 'HMMs')
print('HMMs dir:', hmm_dir, flush=True)
print('exists:', os.path.exists(hmm_dir), flush=True)
if os.path.exists(hmm_dir):
    for f in os.listdir(hmm_dir):
        fpath = os.path.join(hmm_dir, f)
        sz = os.path.getsize(fpath) if os.path.isfile(fpath) else 'dir'
        print(f'  {f}: {sz}', flush=True)

# Find HMM_path in the anarci module
import anarci.anarci as aa
src_file = aa.__file__
print('anarci src:', src_file, flush=True)

# Search for HMM_path
import re
with open(src_file) as f:
    txt = f.read()
for m in re.finditer(r'HMM_path\s*=.*', txt):
    print('HMM_path line:', m.group(), flush=True)
