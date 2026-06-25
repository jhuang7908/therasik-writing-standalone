import anarci, os
pkg = os.path.dirname(anarci.__file__)
dat = os.path.join(pkg, 'dat')
print('pkg:', pkg, flush=True)
print('dat exists:', os.path.exists(dat), flush=True)
if os.path.exists(dat):
    contents = os.listdir(dat)
    print('dat contents:', contents, flush=True)

# Check the actual HMM_path variable used by anarci
import anarci.anarci as aa
# Find HMM_path in the module
if hasattr(aa, 'HMM_path'):
    print('HMM_path attr:', aa.HMM_path, flush=True)
else:
    # Find it in globals
    for k, v in vars(aa).items():
        if 'hmm' in k.lower() or 'dat' in k.lower() or 'path' in k.lower():
            print(f'  {k} = {v}', flush=True)
