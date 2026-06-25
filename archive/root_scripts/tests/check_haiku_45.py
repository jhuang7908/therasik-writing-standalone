#!/usr/bin/env python3
"""
 Claude Haiku 4.5 
"""

import os
import sys

print("=" * 70)
print("Claude Haiku 4.5 ")
print("=" * 70)

anthropic_key = os.environ.get("ANTHROPIC_API_KEY")
if not anthropic_key:
    print("\n❌  ANTHROPIC_API_KEY")
    sys.exit(1)

print(f"\n✅  API : {anthropic_key[:10]}...{anthropic_key[-4:]}")

try:
    from anthropic import Anthropic
    client = Anthropic(api_key=anthropic_key)
    
    #  Haiku 4.5 
    models_to_test = [
        # Haiku 4.5 
        "claude-haiku-4-5",
        "claude-4-5-haiku",
        "claude-haiku-4.5",
        "claude-4.5-haiku",
        "claude-haiku-4-5-20250929",
        "claude-4-5-haiku-20250929",
        "claude-haiku-4-5-20250108",
        "claude-4-5-haiku-20250108",
        
        # 
        "claude-3-5-haiku-20241022",  # 
        "claude-3-haiku-20240307",    # 
    ]
    
    print("\n【 Haiku 4.5 】")
    print("-" * 70)
    
    working_models = []
    
    for model in models_to_test:
        try:
            response = client.messages.create(
                model=model,
                max_tokens=1,
                messages=[{"role": "user", "content": "hi"}]
            )
            print(f"  ✅ {model} - ")
            working_models.append(model)
        except Exception as e:
            error_msg = str(e)
            if "not_found" in error_msg.lower or "404" in error_msg or "model:" in error_msg:
                print(f"  ❌ {model} - ")
            else:
                print(f"  ⚠️  {model} - : {error_msg[:60]}")
    
    print("\n" + "=" * 70)
    print("")
    print("=" * 70)
    
    if working_models:
        print(f"\n✅  {len(working_models)} ：")
        for model in working_models:
            print(f"  - {model}")
        
        #  Haiku 4.5
        haiku_45 = None
        for model in working_models:
            if "4" in model and "5" in model and "haiku" in model.lower:
                haiku_45 = model
                break
        
        if haiku_45:
            print(f"\n🎯 Haiku 4.5 : {haiku_45}")
            print("\n Cursor ：")
            print(f"  Provider: Anthropic")
            print(f"  Model Name: {haiku_45}")
            print(f"  API Endpoint: https://api.anthropic.com/v1")
            print(f"  API Key: []")
        else:
            print("\n💡 : " + working_models[0])
            print("\n Cursor ：")
            print(f"  Provider: Anthropic")
            print(f"  Model Name: {working_models[0]}")
            print(f"  API Endpoint: https://api.anthropic.com/v1")
            print(f"  API Key: []")
    else:
        print("\n❌ ")
        print("\n💡 ：")
        print("  1.  Anthropic ")
        print("  2.  Anthropic : https://docs.anthropic.com/")
    
except ImportError:
    print("\n❌  anthropic ")
    print("💡 : pip install anthropic")
except Exception as e:
    print(f"\n❌ : {e}")

print("\n" + "=" * 70)
