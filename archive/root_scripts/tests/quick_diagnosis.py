#!/usr/bin/env python3
"""
 - 
"""

import os
import sys

print("=" * 60)
print(" - ")
print("=" * 60)

print("\n：")
print("1. OpenAI GPT （ Cursor ）")
print("2. Claude API")
print("3. DeepSeek Chat（，？）")
print("4. Gemini 2.5")
print("5. ")

print("\n" + "=" * 60)
print("")
print("=" * 60)

# 
print("\n1. :")
openai_key = os.environ.get("OPENAI_API_KEY")
anthropic_key = os.environ.get("ANTHROPIC_API_KEY")

if openai_key:
    print(f"   ✅ OPENAI_API_KEY:  ({openai_key[:10]}...{openai_key[-4:]})")
else:
    print("   ❌ OPENAI_API_KEY: ")

if anthropic_key:
    print(f"   ✅ ANTHROPIC_API_KEY:  ({anthropic_key[:10]}...{anthropic_key[-4:]})")
else:
    print("   ❌ ANTHROPIC_API_KEY: ")

#  OpenAI
print("\n2. OpenAI API :")
if openai_key:
    try:
        from openai import OpenAI
        client = OpenAI(api_key=openai_key)
        response = client.chat.completions.create(
            model="gpt-4o",
            messages=[{"role": "user", "content": "test"}],
            max_tokens=5
        )
        print("   ✅ OpenAI API ")
        print("   💡  Cursor ")
        print("   💡  Cursor  Model Name : gpt-4o")
    except Exception as e:
        print(f"   ❌ OpenAI API : {e}")
else:
    print("   ⚠️  ")

#  Anthropic
print("\n3. Anthropic (Claude) API :")
if anthropic_key:
    try:
        from anthropic import Anthropic
        client = Anthropic(api_key=anthropic_key)
        response = client.messages.create(
            model="claude-sonnet-4-5-20250929",
            max_tokens=5,
            messages=[{"role": "user", "content": "test"}]
        )
        print("   ✅ Anthropic API ")
    except Exception as e:
        error_msg = str(e)
        if "401" in error_msg or "authentication" in error_msg.lower:
            print("   ❌ Anthropic API ")
            print("   💡 : https://console.anthropic.com/")
        elif "404" in error_msg or "not found" in error_msg:
            print("   ⚠️  ，...")
            try:
                response = client.messages.create(
                    model="claude-sonnet-4-5",
                    max_tokens=5,
                    messages=[{"role": "user", "content": "test"}]
                )
                print("   ✅  claude-sonnet-4-5 ")
            except:
                print("   ❌  Claude ")
        else:
            print(f"   ❌ Anthropic API : {e}")
else:
    print("   ⚠️  ")

print("\n" + "=" * 60)
print("")
print("=" * 60)

print("""
，：

1.  Cursor ？
2. ？
3.  OpenAI  Model Name  gpt-4o？

，：
- 
-  Cursor 
- 
""")

print("\n" + "=" * 60)
