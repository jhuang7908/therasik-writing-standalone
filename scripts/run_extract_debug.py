""""""
import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__)))

# 
if sys.platform == 'win32':
    import io
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')
    sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding='utf-8', errors='replace')

from extract_multi_species_ig_aa import *

# 
sys.argv = ['run_extract_debug.py', '--species', '', '']

print("=" * 60, flush=True)
print("...", flush=True)
print("=" * 60, flush=True)
print(f"IMGT_BASE_DIR: {IMGT_BASE_DIR}", flush=True)
print(f"IMGT_BASE_DIR exists: {IMGT_BASE_DIR.exists()}", flush=True)
print(f"OUTPUT_DIR: {OUTPUT_DIR}", flush=True)
print("=" * 60, flush=True)

try:
    main()
    print("\n" + "=" * 60, flush=True)
    print("", flush=True)
    print("=" * 60, flush=True)
    
    # 
    if OUTPUT_DIR.exists():
        json_files = list(OUTPUT_DIR.glob("*.json"))
        print(f"\n {len(json_files)} ：", flush=True)
        for f in json_files:
            print(f"  - {f.name}", flush=True)
    else:
        print("\n", flush=True)
        
except Exception as e:
    import traceback
    print("\n" + "=" * 60, flush=True)
    print("：", flush=True)
    print("=" * 60, flush=True)
    traceback.print_exc(file=sys.stdout)
    sys.stdout.flush()




















