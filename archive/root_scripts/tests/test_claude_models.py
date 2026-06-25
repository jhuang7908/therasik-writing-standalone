#!/usr/bin/env python3
"""
Claude API
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

from anthropic import Anthropic
client = Anthropic(api_key=API_KEY)

# 
models_to_test = [
    # Sonnet 4.5 
    "claude-sonnet-4-5-20250929",
    "claude-sonnet-4.5-20250929",
    "claude-4-5-sonnet",
    "claude-sonnet-4-5",
    
    # Sonnet 4 
    "claude-sonnet-4-20250514",
    "claude-sonnet-4",
    
    # Opus 4 
    "claude-opus-4-20250514",
    "claude-opus-4",
    
    # 3.5 
    "claude-3-5-sonnet-20241022",
    "claude-3-5-sonnet-20240620",
    "claude-3-5-sonnet",
    
    # 3 
    "claude-3-opus-20240229",
    "claude-3-sonnet-20240229",
    "claude-3-haiku-20240307",
    
    # 
    "claude-sonnet-latest",
    "claude-opus-latest",
]

print("\n...\n")
available_models = []

for model_id in models_to_test:
    try:
        response = client.messages.create(
            model=model_id,
            max_tokens=5,
            messages=[{"role": "user", "content": "hi"}]
        )
        print(f"✅ {model_id:40s} - ")
        available_models.append(model_id)
    except Exception as e:
        error_msg = str(e)
        if "not_found" in error_msg or "404" in error_msg:
            print(f"❌ {model_id:40s} - ")
        elif "401" in error_msg or "authentication" in error_msg:
            print(f"⚠️  {model_id:40s} - ")
            break
        else:
            print(f"⚠️  {model_id:40s} - : {str(e)[:50]}")

print("\n" + "=" * 60)
print("")
print("=" * 60)

if available_models:
    print(f"\n✅  {len(available_models)} :\n")
    for model in available_models:
        marker = " ⭐ Sonnet 4.5" if "4-5" in model or "4.5" in model else ""
        marker = " ⭐ Sonnet 4" if "sonnet-4" in model and not marker else marker
        print(f"  - {model}{marker}")
    
    # 
    sonnet45 = [m for m in available_models if "4-5" in m or "4.5" in m]
    sonnet4 = [m for m in available_models if "sonnet-4" in m and "4-5" not in m and "4.5" not in m]
    
    print("\n:")
    if sonnet45:
        print(f"  ⭐ Sonnet 4.5: {sonnet45[0]}")
    elif sonnet4:
        print(f"  ⭐ Sonnet 4: {sonnet4[0]}")
    elif available_models:
        print(f"  ⭐ : {available_models[0]}")
else:
    print("\n❌ ")
    print("   :")
    print("   - API")
    print("   - ")
    print("   - ")

print("\n" + "=" * 60)







