import anarci.anarci as aa_mod, inspect, os
src = inspect.getsource(aa_mod)
outpath = os.path.join(os.path.dirname(__file__), '_anarci_src.txt')
with open(outpath, 'w', encoding='utf-8') as f:
    f.write(src)
print(f"Written {len(src)} chars to {outpath}")
