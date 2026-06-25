w#!/usr/bin/env python3
"""Claude API"""

import os
import sys

print("=" * 60)
print("Claude API ")
print("=" * 60)

# 
print("\n1. Anthropic...")
try:
    import anthropic
    print(f"   ✅ Anthropic (: {anthropic.__version__})")
    library_ok = True
except ImportError:
    print("   ❌ Anthropic")
    print("   💡 : pip install anthropic")
    library_ok = False

# API
print("\n2. API...")
api_key = os.environ.get("ANTHROPIC_API_KEY") or os.environ.get("CLAUDE_API_KEY")
if api_key:
    print(f"   ✅ API: {api_key[:10]}...{api_key[-4:]}")
    key_ok = True
else:
    print("   ⚠️  API")
    print("   💡 :")
    print("      Windows PowerShell: $env:ANTHROPIC_API_KEY='your-key'")
    print("      Windows CMD: set ANTHROPIC_API_KEY=your-key")
    print("      Linux/Mac: export ANTHROPIC_API_KEY='your-key'")
    key_ok = False

# 
print("\n" + "=" * 60)
print("")
print("=" * 60)

if library_ok and key_ok:
    print("\n✅ ，API")
    print("\n:")
    print("   python test_claude_api_interactive.py")
elif library_ok:
    print("\n⚠️  ，API")
    print("\n:")
    print("   1. API: https://console.anthropic.com/")
    print("   2. ")
    print("   3. : python test_claude_api_interactive.py")
elif key_ok:
    print("\n⚠️  API，")
    print("\n:")
    print("   pip install anthropic")
    print("   : python test_claude_api_interactive.py")
else:
    print("\n❌ API")
    print("\n:")
    print("   1. pip install anthropic")
    print("   2. API: https://console.anthropic.com/")
    print("   3. ")
    print("   4. : python test_claude_api_interactive.py")

print("\n" + "=" * 60)







