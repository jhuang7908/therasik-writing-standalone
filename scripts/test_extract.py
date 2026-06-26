""""""
import sys
sys.path.insert(0, 'scripts')

from extract_multi_species_ig_aa import *
import sys

# 
sys.argv = ['test_extract.py', '--species', '', '']

print("=" * 60)
print("...")
print("=" * 60)

try:
    main()
    print("\n" + "=" * 60)
    print("")
    print("=" * 60)
except Exception as e:
    import traceback
    print("\n" + "=" * 60)
    print("：")
    print("=" * 60)
    traceback.print_exc()




















