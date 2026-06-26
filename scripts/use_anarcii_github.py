#!/usr/bin/env python3
"""
ANARCIIIMGT
GitHub: https://github.com/oxpig/ANARCII
"""
import json
from pathlib import Path
import sys

def check_anarcii_installation():
    """ANARCII"""
    try:
        import anarcii
        print(f"✅ anarcii: {anarcii.__version__ if hasattr(anarcii, '__version__') else ''}")
        return True
    except ImportError:
        print("❌ anarcii")
        print("\n:")
        print("  pip install anarcii")
        return False

def use_anarcii_web_tool():
    """ANARCII"""
    print("\n" + "=" * 60)
    print("ANARCII")
    print("=" * 60)
    print("\n: https://opig.stats.ox.ac.uk/webapps/sabdab-sabpred/sabpred/anarcii/")
    print("\nANARCII，。")
    print("\n:")
    print("1. ")
    print("2. ")
    print("3. IMGT")
    print("4. ")

def try_anarcii_api():
    """ANARCII API"""
    try:
        from anarcii.pipeline import Anarcii
        
        print("\n" + "=" * 60)
        print("ANARCII API")
        print("=" * 60)
        
        # 
        fasta_file = Path("projects/anti_HSA_VHH/input/anti_hsa_vhh_alb8_partial_hallmark.fasta")
        with open(fasta_file, 'r', encoding='utf-8') as f:
            lines = f.readlines()
            sequence = ""
            for line in lines:
                if not line.startswith('>'):
                    sequence += line.strip()
        
        print(f"\n: {len(sequence)} aa")
        print(f": {sequence}\n")
        
        # ANARCII
        anarcii_instance = Anarcii()
        
        # 
        print("ANARCII...")
        
        # GitHub，
        # API
        result = anarcii_instance.number([sequence])
        
        print(f"✅ ")
        print(f": {result}")
        
        return result
        
    except Exception as e:
        print(f"❌ ANARCII API: {e}")
        import traceback
        traceback.print_exc()
        return None

def main():
    """"""
    print("=" * 60)
    print("ANARCII")
    print("GitHub: https://github.com/oxpig/ANARCII")
    print("=" * 60)
    
    # 
    is_installed = check_anarcii_installation()
    
    if is_installed:
        # API
        result = try_anarcii_api()
        if result:
            print("\n✅ ANARCII API")
        else:
            print("\n⚠️  API，")
            use_anarcii_web_tool()
    else:
        print("\n:")
        print("1. ANARCII: pip install anarcii")
        print("2. : https://opig.stats.ox.ac.uk/webapps/sabdab-sabpred/sabpred/anarcii/")
        use_anarcii_web_tool()

if __name__ == '__main__':
    main()
