#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
 ANARCII 
 run_anarcii 
"""

#  ANARCII API
HAS_RUN_ANARCII = False
HAS_ANARCII_CLASS = False

try:
    from anarcii import run_anarcii
    HAS_RUN_ANARCII = True
    print("[INFO] ✓ Found: from anarcii import run_anarcii")
except ImportError:
    print("[INFO] ✗ Not found: from anarcii import run_anarcii")

try:
    from anarcii import Anarcii
    HAS_ANARCII_CLASS = True
    print("[INFO] ✓ Found: from anarcii import Anarcii")
except ImportError:
    print("[INFO] ✗ Not found: from anarcii import Anarcii")

if not HAS_RUN_ANARCII and not HAS_ANARCII_CLASS:
    print("[ERROR] Cannot import anarcii. Please install: pip install anarcii")
    exit(1)

test_seq = "QVQLVESGGGLVQVGGSLRLSRALSGFWYNHMGWFRQAPGKEREGVAVITADSGSTTYADSVKGRFTISRDDARNTVYLQMNSLKPEDTAVYYCAAGGVGWPYFDYWGQGTQVTVSS"

print("\n" + "=" * 80)
print("Testing ANARCII IMGT numbering")
print("=" * 80)
print(f"\nTest sequence length: {len(test_seq)} aa")
print(f"Test sequence (first 50): {test_seq[:50]}...")

#  run_anarcii（）
if HAS_RUN_ANARCII:
    print("\n[INFO] Calling run_anarcii...")
    try:
        res = run_anarcii([("vhh", test_seq)], scheme="imgt")
        print("\nANARCII raw result type:", type(res))
        print("ANARCII raw result length (if iterable):", len(res) if hasattr(res, '__len__') else "N/A")
        print("\nANARCII raw result repr (first 2000 chars):")
        print(str(res)[:2000])
        print("\n" + "=" * 80)
        print("Full structure inspection:")
        print("=" * 80)
        if isinstance(res, tuple):
            print(f"Result is a tuple with {len(res)} elements")
            for i, item in enumerate(res):
                print(f"  Element {i}: type={type(item)}, len={len(item) if hasattr(item, '__len__') else 'N/A'}")
                if i < 2:  # 
                    print(f"    Preview: {str(item)[:500]}")
        elif isinstance(res, dict):
            print(f"Result is a dict with keys: {list(res.keys())}")
            for key in list(res.keys())[:3]:  # 3key
                print(f"  Key '{key}': type={type(res[key])}")
                print(f"    Preview: {str(res[key])[:500]}")
        else:
            print(f"Result type: {type(res)}")
            print(f"Result dir (attributes): {[x for x in dir(res) if not x.startswith('_')][:20]}")
    except Exception as e:
        print(f"[ERROR] run_anarcii failed: {e}")
        import traceback
        traceback.print_exc()
#  Anarcii （）
if HAS_ANARCII_CLASS:
    print("\n" + "=" * 80)
    print("Testing Anarcii class API")
    print("=" * 80)
    try:
        anarcii_obj = Anarcii(
            seq_type="antibody",
            mode="accuracy",
            batch_size=32,
            cpu=True,
            ncpu=-1,
            verbose=False,
        )
        result = anarcii_obj.number(test_seq)
        print("\nANARCII result type:", type(result))
        print("ANARCII result keys (if dict):", list(result.keys()) if isinstance(result, dict) else "N/A")
        print("\nANARCII result repr (first 2000 chars):")
        print(str(result)[:2000])
        print("\n" + "=" * 80)
        print("Full structure inspection:")
        print("=" * 80)
        if isinstance(result, dict):
            for key in list(result.keys())[:3]:
                print(f"\nKey '{key}':")
                val = result[key]
                print(f"  Type: {type(val)}")
                if isinstance(val, dict):
                    print(f"  Dict keys: {list(val.keys())}")
                    for subkey in list(val.keys())[:5]:
                        print(f"    '{subkey}': {type(val[subkey])} = {str(val[subkey])[:200]}")
    except Exception as e:
        print(f"[ERROR] Anarcii.number failed: {e}")
        import traceback
        traceback.print_exc()

if not HAS_RUN_ANARCII and not HAS_ANARCII_CLASS:
    print("\n[ERROR] No ANARCII API available for testing")
    exit(1)

print("\n" + "=" * 80)
print("Test completed")
print("=" * 80)

