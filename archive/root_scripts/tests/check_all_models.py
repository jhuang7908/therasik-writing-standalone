#!/usr/bin/env python3
"""

"""

import os
import sys

print("=" * 60)
print("")
print("=" * 60)

# 
print("\n1. ...")
env_vars = {
    "OPENAI_API_KEY": os.environ.get("OPENAI_API_KEY"),
    "ANTHROPIC_API_KEY": os.environ.get("ANTHROPIC_API_KEY"),
    "DEEPSEEK_API_KEY": os.environ.get("DEEPSEEK_API_KEY"),
    "GEMINI_API_KEY": os.environ.get("GEMINI_API_KEY"),
    "GOOGLE_API_KEY": os.environ.get("GOOGLE_API_KEY"),
}

for key, value in env_vars.items:
    if value:
        print(f"   ✅ {key}: {value[:10]}...{value[-4:]}")
    else:
        print(f"   ❌ {key}: ")

#  DeepSeek 
print("\n2.  DeepSeek API...")
deepseek_key = env_vars["DEEPSEEK_API_KEY"]
if deepseek_key:
    try:
        from openai import OpenAI
        client = OpenAI(
            api_key=deepseek_key,
            base_url="https://api.deepseek.com/v1"
        )
        
        print("    deepseek-chat...")
        response = client.chat.completions.create(
            model="deepseek-chat",
            messages=[{"role": "user", "content": "test"}],
            max_tokens=10
        )
        print(f"   ✅ deepseek-chat !")
        print(f"   : {response.choices[0].message.content}")
    except Exception as e:
        print(f"   ❌ DeepSeek : {e}")
else:
    print("   ⚠️   DeepSeek API ， Cursor ")

#  OpenAI
print("\n3.  OpenAI API...")
openai_key = env_vars["OPENAI_API_KEY"]
if openai_key:
    try:
        from openai import OpenAI
        client = OpenAI(api_key=openai_key)
        
        print("    gpt-4o...")
        response = client.chat.completions.create(
            model="gpt-4o",
            messages=[{"role": "user", "content": "test"}],
            max_tokens=10
        )
        print(f"   ✅ OpenAI API !")
        print(f"   : {response.choices[0].message.content}")
    except Exception as e:
        print(f"   ❌ OpenAI : {e}")
else:
    print("   ⚠️   OpenAI API ")

print("\n" + "=" * 60)
print("")
print("=" * 60)

print("\n:")
print("✅ DeepSeek Chat -  ( Cursor )")
print("❌  - ")

print("\n:")
print("1.  DeepSeek  Cursor ")
print("2.  API ")
print("3. Cursor ")

print("\n:")
print("1.  Cursor ")
print("2.  API  (Claude, OpenAI )")
print("3.  DeepSeek Chat ")


