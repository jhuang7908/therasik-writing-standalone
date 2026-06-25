#!/usr/bin/env python3
"""
APIClaude API
"""

import os
import sys

# 
API_KEY = os.environ.get("ANTHROPIC_API_KEY")
if not API_KEY:
    print("❌  ANTHROPIC_API_KEY ")
    print("💡 PowerShell ：$env:ANTHROPIC_API_KEY = 'sk-ant-...'\n")
    sys.exit(1)

print("=" * 60)
print("Claude API ")
print("=" * 60)

# 
print("\n1. Anthropic...")
try:
    import anthropic
    from anthropic import Anthropic
    version = getattr(anthropic, '__version__', '')
    print(f"   ✅ Anthropic (: {version})")
except ImportError:
    print("   ❌ Anthropic")
    print("   💡 : pip install anthropic")
    sys.exit(1)

# API
print("\n2. API...")
try:
    client = Anthropic(api_key=API_KEY)
    
    # 
    print("   ...")
    response = client.messages.create(
        model="claude-3-5-sonnet-20241022",
        max_tokens=30,
        messages=[{"role": "user", "content": "Hello, please respond with 'API test successful'."}]
    )
    
    print("   ✅ API!")
    print(f"   : {response.content[0].text}")
    
except Exception as e:
    print(f"   ❌ API: {e}")
    error_str = str(e)
    
    if "401" in error_str or "Unauthorized" in error_str or "authentication" in error_str.lower:
        print("\n   💡 : API")
        print("      : https://console.anthropic.com/")
    elif "429" in error_str or "rate limit" in error_str.lower:
        print("\n   💡 : API")
    elif "Network" in error_str or "Connection" in error_str or "timeout" in error_str.lower:
        print("\n   💡 : ")
        print("      : Claude API")
    else:
        print(f"\n   💡 : {error_str[:200]}")
    sys.exit(1)

# Sonnet 4.5
print("\n3.  Claude Sonnet 4.5...")
sonnet45_models = [
    "claude-sonnet-4-5-20250929",
    "claude-sonnet-4-5",
    "claude-4-5-sonnet",
]

available_sonnet45 = []
for model_id in sonnet45_models:
    try:
        print(f"   : {model_id}")
        response = client.messages.create(
            model=model_id,
            max_tokens=30,
            messages=[
                {"role": "user", "content": "Claude Sonnet 4.5，''。"}
            ]
        )
        print(f"   ✅ {model_id} !")
        print(f"   : {response.content[0].text}")
        available_sonnet45.append(model_id)
        break  # 
    except Exception as e:
        error_msg = str(e)
        if "not found" in error_msg.lower or "404" in error_msg:
            print(f"   ❌ {model_id}  ")
        elif "model" in error_msg.lower and "invalid" in error_msg.lower:
            print(f"   ❌ {model_id}  ")
        else:
            print(f"   ⚠️  {model_id} : {str(e)[:80]}")

# 
print("\n4. Claude...")
other_models = [
    ("claude-3-5-sonnet-20241022", "Claude 3.5 Sonnet"),
    ("claude-3-opus-20240229", "Claude 3 Opus"),
    ("claude-sonnet-4-20250514", "Claude Sonnet 4"),
    ("claude-opus-4-20250514", "Claude Opus 4"),
]

available_others = []
for model_id, description in other_models:
    try:
        response = client.messages.create(
            model=model_id,
            max_tokens=10,
            messages=[{"role": "user", "content": "test"}]
        )
        print(f"   ✅ {model_id} ({description}) - ")
        available_others.append((model_id, description))
    except Exception as e:
        if "not found" in str(e).lower or "404" in str(e):
            print(f"   ❌ {model_id} ({description}) - ")
        else:
            print(f"   ⚠️  {model_id} ({description}) - : {str(e)[:60]}")

# 
print("\n" + "=" * 60)
print("")
print("=" * 60)

print("\n✅ Claude API !")

if available_sonnet45:
    print(f"\n🎉 Claude Sonnet 4.5 !")
    print(f"   : {available_sonnet45[0]}")
    print(f"\n   Cursor:")
    print(f"   Model Name: {available_sonnet45[0]}")
    print(f"   Provider: Anthropic")
    print(f"   API Endpoint: https://api.anthropic.com/v1")
    print(f"   API Key: {API_KEY[:20]}...")
else:
    print("\n⚠️  Claude Sonnet 4.5 ")
    if available_others:
        print(f"   : {available_others[0][0]} ({available_others[0][1]})")

if available_others:
    print(f"\n✅  ({len(available_others)} ):")
    for model_id, description in available_others[:3]:  # 3
        print(f"   - {model_id}: {description}")

print("\n" + "=" * 60)
print("✅ !")
print("=" * 60)

