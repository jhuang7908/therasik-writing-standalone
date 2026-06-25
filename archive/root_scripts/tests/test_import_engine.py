import sys
import os
sys.path.insert(0, os.getcwd())
try:
    print("Importing core.humanization.engine...")
    from core.humanization.engine import HumanizationEngine
    print("Success!")
except Exception as e:
    print(f"Error: {e}")
