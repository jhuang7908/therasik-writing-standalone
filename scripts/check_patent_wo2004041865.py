#!/usr/bin/env python3
"""
WO2004041865
"""
import requests
from datetime import datetime

def check_patent_status():
    """"""
    patent_number = "WO2004041865"
    
    print("=" * 60)
    print(f": {patent_number}")
    print("=" * 60)
    
    # 
    print("\n:")
    print(f": {patent_number}")
    print(": Ablynx N.V.")
    print(":  (Single domain antibodies and uses thereof)")
    print(": ")
    
    # 
    print("\n:")
    print(": 2003-11-07 (WO，2004)")
    print(": 2004-05-21")
    print(": 2003-2004")
    
    # 
    print("\n:")
    print("-" * 60)
    
    # PCT20
    filing_year = 2003  # 
    expiration_year = filing_year + 20
    
    print(f": {filing_year}")
    print(f": 20")
    print(f": {expiration_year} ({expiration_year - datetime.now().year})")
    
    current_year = datetime.now().year
    if expiration_year <= current_year:
        print(f"\n✅ :  ({expiration_year})")
    elif expiration_year <= current_year + 2:
        print(f"\n⚠️  :  ({expiration_year})")
    else:
        print(f"\n❌ :  ({expiration_year})")
    
    # 
    print("\n" + "=" * 60)
    print(":")
    print("=" * 60)
    print("1. ⚠️  20")
    print("2. ⚠️  ")
    print("3. ⚠️  、")
    print("4. ⚠️  （、、）")
    print("5. ✅ FTO")
    
    print("\n:")
    print("1. WIPO PATENTSCOPE")
    print("2. ")
    print("3. ")
    
    print(f"\nWIPO: https://patentscope.wipo.int/search/en/{patent_number}")

if __name__ == '__main__':
    check_patent_status()
