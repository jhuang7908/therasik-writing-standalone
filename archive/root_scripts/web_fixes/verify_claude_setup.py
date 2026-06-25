#!/usr/bin/env python3
"""
Claude API
"""

import os
import sys

print("=" * 60)
print(" Claude API ")
print("=" * 60)

# 
api_key = os.environ.get("ANTHROPIC_API_KEY")

if api_key:
    print(f"\n✅ ")
    print(f"   API: {api_key[:20]}...{api_key[-4:]}")
    
    # API
    print("\nAPI...")
    try:
        from anthropic import Anthropic
        client = Anthropic(api_key=api_key)
        
        response = client.messages.create(
            model="claude-sonnet-4-5-20250929",
            max_tokens=20,
            messages=[{"role": "user", "content": "Hello, respond with 'Setup verified successfully'."}]
        )
        
        print("✅ API!")
        print(f"   : {response.content[0].text}")
        print("\n🎉 ！。")
        
    except Exception as e:
        print(f"⚠️  API: {e}")
        print("   ，。")
else:
    print("\n⚠️  ")
    print("\n:")
    print("  1. PowerShell/Cursor")
    print("  2. ")
    print("\n:")
    print("  1. PowerShell")
    print("  2. Cursor")
    print("  3. ")

print("\n" + "=" * 60)







