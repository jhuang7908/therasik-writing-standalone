#!/usr/bin/env python3
"""
 OpenAI 
"""

import os
from openai import OpenAI

print("=" * 60)
print("OpenAI ")
print("=" * 60)

api_key = os.environ.get("OPENAI_API_KEY")
if not api_key:
    print("❌  OPENAI_API_KEY")
    sys.exit(1)

print(f"✅  API : {api_key[:10]}...{api_key[-4:]}")
client = OpenAI(api_key=api_key)

# 
models_to_test = [
    "gpt-5.2",
    "gpt-5.2-chat-latest",
    "gpt-5.2-2025-12-11",
    "gpt-4o",
    "gpt-4o-mini",
    "gpt-4-turbo",
    "gpt-4",
    "gpt-3.5-turbo",
]

print("\n...")
available_models = []

for model in models_to_test:
    try:
        print(f"\n: {model}")
        response = client.chat.completions.create(
            model=model,
            messages=[{"role": "user", "content": "test"}],
            max_tokens=5
        )
        print(f"   ✅ {model} ")
        available_models.append(model)
    except Exception as e:
        error_msg = str(e)
        if "not found" in error_msg.lower or "does not exist" in error_msg.lower:
            print(f"   ❌ {model} ")
        elif "rate limit" in error_msg.lower:
            print(f"   ⚠️  {model} ")
        else:
            print(f"   ❌ {model} : {str(e)[:50]}")

print("\n" + "=" * 60)
print("")
print("=" * 60)

if available_models:
    print(f"\n✅  {len(available_models)} :")
    for model in available_models:
        print(f"   - {model}")
    
    print("\n💡  Cursor :")
    print(f"   Model Name: {available_models[0]}")
    print(f"   Provider: OpenAI")
    print(f"   API Endpoint: https://api.openai.com/v1")
else:
    print("\n❌ ")
    print("    API ")

print("\n" + "=" * 60)


