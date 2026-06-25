import sys
import os
sys.path.insert(0, os.getcwd())
try:
    print("Importing core.immunogenicity...")
    import core.immunogenicity
    print("Success!")
except Exception as e:
    print(f"Error: {e}")
