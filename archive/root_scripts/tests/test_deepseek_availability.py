#!/usr/bin/env python3
"""
 DeepSeek API 

"""

import os
import sys

print("=" * 60)
print("DeepSeek API ")
print("=" * 60)

#  DeepSeek 
deepseek_keys = {
    "DEEPSEEK_API_KEY": os.environ.get("DEEPSEEK_API_KEY"),
    "DEEPSEEK_KEY": os.environ.get("DEEPSEEK_KEY"),
    "DEEPSEEK_TOKEN": os.environ.get("DEEPSEEK_TOKEN"),
    "DEEPSEEK_SECRET": os.environ.get("DEEPSEEK_SECRET"),
}

print("\n1. ...")
found_keys = []
for key_name, key_value in deepseek_keys.items:
    if key_value:
        print(f"   ✅  {key_name}: {key_value[:10]}...{key_value[-4:]}")
        found_keys.append((key_name, key_value))
    else:
        print(f"   ❌  {key_name}")

if not found_keys:
    print("\n   ⚠️   DeepSeek API ")
    print("    Cursor ")

#  OpenAI  DeepSeek
print("\n2.  DeepSeek API ...")

# DeepSeek  OpenAI 
try:
    from openai import OpenAI
    
    # 
    api_key = None
    for key_name, key_value in found_keys:
        api_key = key_value
        break
    
    if not api_key:
        print("   ⚠️   API ")
        print("    Cursor  deepseek-chat ，")
        print("    Cursor ")
        sys.exit(0)
    
    # DeepSeek  OpenAI 
    client = OpenAI(
        api_key=api_key,
        base_url="https://api.deepseek.com/v1"
    )
    
    print("   ...")
    try:
        # 
        models = client.models.list
        print(f"   ✅ API !")
        print(f"    {len(models.data)} ")
        
        #  deepseek-chat
        deepseek_models = [m.id for m in models.data if "deepseek" in m.id.lower]
        if deepseek_models:
            print(f"   ✅  DeepSeek : {', '.join(deepseek_models)}")
        else:
            print("   ⚠️   DeepSeek ")
            
        # 
        print("\n    deepseek-chat ...")
        response = client.chat.completions.create(
            model="deepseek-chat",
            messages=[{"role": "user", "content": "Hello, please respond with 'DeepSeek test successful'."}],
            max_tokens=20
        )
        print(f"   ✅ deepseek-chat !")
        print(f"   : {response.choices[0].message.content}")
        
    except Exception as e:
        print(f"   ❌ API : {e}")
        
except ImportError:
    print("   ❌  openai ")
    print("   💡 : pip install openai")

print("\n" + "=" * 60)
print("")
print("=" * 60)

if found_keys:
    print(f"\n✅  {len(found_keys)}  DeepSeek API ")
    print("    Cursor  deepseek-chat")
else:
    print("\n⚠️   DeepSeek API ")
    print("    Cursor  deepseek-chat ，")
    print("    Cursor ")

print("\n" + "=" * 60)





