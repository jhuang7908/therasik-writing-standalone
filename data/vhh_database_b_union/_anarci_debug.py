import anarci, os, sys

pkg_dir = os.path.dirname(anarci.__file__)
print('pkg dir:', pkg_dir, flush=True)
for f in os.listdir(pkg_dir):
    print(' ', f, flush=True)

# Now import the run_hmmer and find where hmmscan is
import anarci.anarci as aa
import inspect
src = inspect.getsource(aa.run_hmmer)
with open(os.path.join(os.path.dirname(__file__), '_run_hmmer_src.txt'), 'w') as fout:
    fout.write(src)
print('run_hmmer src written', flush=True)
