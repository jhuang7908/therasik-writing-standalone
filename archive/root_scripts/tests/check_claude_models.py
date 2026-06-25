#!/usr/bin/env python3
"""
 Claude 
"""

import os
import sys

print("=" * 70)
print("Claude ")
print("=" * 70)

anthropic_key = os.environ.get("ANTHROPIC_API_KEY")
if not anthropic_key:
    print("\n❌  ANTHROPIC_API_KEY")
    print("💡 : https://console.anthropic.com/")
    sys.exit(1)

print(f"\n✅  API : {anthropic_key[:10]}...{anthropic_key[-4:]}")

try:
    from anthropic import Anthropic
    client = Anthropic(api_key=anthropic_key)
    
    #  Claude 
    models_to_test = [
        # Claude 3.5 
        "claude-3-5-sonnet-20241022",
        "claude-3-5-sonnet-20240620",
        "claude-3-5-sonnet",
        "claude-3-5-opus-20241022",
        "claude-3-5-opus",
        "claude-3-5-haiku-20241022",
        "claude-3-5-haiku",
        
        # Claude 3 
        "claude-3-opus-20240229",
        "claude-3-opus",
        "claude-3-sonnet-20240229",
        "claude-3-sonnet",
        "claude-3-haiku-20240307",
        "claude-3-haiku",
        
        # Claude 4 
        "claude-4-sonnet",
        "claude-4-opus",
        "claude-sonnet-4",
        "claude-opus-4",
        
        # 
        "claude-3-opus-20240508",
        "claude-3-sonnet-20240508",
    ]
    
    print("\n【】")
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
            elif "401" in error_msg or "authentication" in error_msg.lower:
                print(f"  ⚠️  {model} - ")
                break
            else:
                print(f"  ⚠️  {model} - : {error_msg[:60]}")
    
    print("\n" + "=" * 70)
    print("")
    print("=" * 70)
    
    if working_models:
        print(f"\n✅  {len(working_models)} ：")
        for model in working_models:
            print(f"  - {model}")
        
        # 
        recommended = None
        if "claude-3-5-sonnet-20241022" in working_models:
            recommended = "claude-3-5-sonnet-20241022"
        elif "claude-3-5-sonnet" in working_models:
            recommended = "claude-3-5-sonnet"
        elif "claude-3-5-opus" in working_models:
            recommended = "claude-3-5-opus"
        elif working_models:
            recommended = working_models[0]
        
        if recommended:
            print(f"\n💡 : {recommended}")
            print("\n Cursor ：")
            print(f"  Provider: Anthropic")
            print(f"  Model Name: {recommended}")
            print(f"  API Endpoint: https://api.anthropic.com/v1")
            print(f"  API Key: []")
    else:
        print("\n❌  Claude ")
        print("\n：")
        print("  1. API ")
        print("  2. ")
        print("  3. ")
        print("\n💡 ：")
        print("  1.  Anthropic : https://console.anthropic.com/")
        print("  2.  API ")
        print("  3.  Anthropic ")
    
except ImportError:
    print("\n❌  anthropic ")
    print("💡 : pip install anthropic")
except Exception as e:
    print(f"\n❌ : {e}")
    print("\n💡 ：")
    print("  1. ")
    print("  2. API ")
    print("  3. Anthropic API ")

print("\n" + "=" * 70)
