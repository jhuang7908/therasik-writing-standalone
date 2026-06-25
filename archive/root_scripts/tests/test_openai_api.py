#!/usr/bin/env python3
"""
OpenAI API
"""

import os
import sys
import json
from typing import Optional

def test_openai_api:
    """OpenAI API"""
    print("=" * 60)
    print("OpenAI API ")
    print("=" * 60)
    
    # API
    api_key = os.environ.get("OPENAI_API_KEY")
    if not api_key:
        print("❌ :  OPENAI_API_KEY ")
        return False
    
    print(f"✅ API: {api_key[:10]}...{api_key[-4:]}")
    
    # openai
    try:
        import openai
        print("✅ OpenAI")
    except ImportError:
        print("❌ : openai")
        print("   : pip install openai")
        return False
    
    # API
    print("\n" + "-" * 60)
    print("API...")
    print("-" * 60)
    
    try:
        client = openai.OpenAI(api_key=api_key)
        
        # 
        print("\n...")
        models_response = client.models.list
        
        available_models = []
        gpt_models = []
        gpt5_models = []
        
        for model in models_response.data:
            model_id = model.id
            available_models.append(model_id)
            
            # GPT
            if "gpt" in model_id.lower:
                gpt_models.append(model_id)
                if "5" in model_id or "gpt-5" in model_id.lower:
                    gpt5_models.append(model_id)
        
        print(f"\n✅ API!")
        print(f"    {len(available_models)} ")
        print(f"    {len(gpt_models)} GPT")
        
        # GPT-5.2
        print("\n" + "-" * 60)
        print("GPT-5.2")
        print("-" * 60)
        
        gpt52_found = False
        gpt52_variants = [
            "gpt-5.2",
            "gpt-5.2-turbo",
            "gpt-5.2-preview",
            "gpt5.2",
            "gpt_5.2"
        ]
        
        for variant in gpt52_variants:
            if variant in available_models:
                print(f"✅ GPT-5.2: {variant}")
                gpt52_found = True
                break
        
        if not gpt52_found:
            print("⚠️  GPT-5.2")
            if gpt5_models:
                print(f"   GPT-5:")
                for model in gpt5_models:
                    print(f"     - {model}")
        
        # GPT
        print("\n" + "-" * 60)
        print("GPT:")
        print("-" * 60)
        if gpt_models:
            for model in sorted(gpt_models):
                marker = " ⭐" if "5.2" in model or "gpt-5.2" in model.lower else ""
                print(f"  - {model}{marker}")
        else:
            print("  GPT")
        
        # API
        print("\n" + "-" * 60)
        print("API...")
        print("-" * 60)
        
        # gpt-4o
        test_model = "gpt-4o" if "gpt-4o" in available_models else (gpt_models[0] if gpt_models else None)
        
        if test_model:
            print(f": {test_model}")
            try:
                response = client.chat.completions.create(
                    model=test_model,
                    messages=[
                        {"role": "user", "content": "Hello, this is a test. Please respond with 'API test successful'."}
                    ],
                    max_tokens=20
                )
                print(f"✅ API!")
                print(f"   : {response.choices[0].message.content}")
                print(f"   tokens: {response.usage.total_tokens}")
            except Exception as e:
                print(f"⚠️  API: {e}")
        else:
            print("⚠️  ")
        
        return {
            "api_available": True,
            "api_key_valid": True,
            "total_models": len(available_models),
            "gpt_models": gpt_models,
            "gpt52_available": gpt52_found,
            "gpt5_models": gpt5_models
        }
        
    except Exception as e:
        print(f"\n❌ API: {e}")
        print(f"   : {type(e).__name__}")
        
        # 
        if "401" in str(e) or "Unauthorized" in str(e):
            print("\n💡 : API")
        elif "429" in str(e) or "Rate limit" in str(e):
            print("\n💡 : API")
        elif "Network" in str(e) or "Connection" in str(e):
            print("\n💡 : ")
        else:
            print("\n💡 : ，API")
        
        return {
            "api_available": False,
            "api_key_valid": False,
            "error": str(e)
        }

def check_openai_version:
    """OpenAI"""
    try:
        import openai
        print(f"OpenAI: {openai.__version__}")
        return openai.__version__
    except ImportError:
        print("OpenAI")
        return None

if __name__ == "__main__":
    print("\n")
    print("=" * 60)
    print("OpenAI API ")
    print("=" * 60)
    
    # 
    print("\n...")
    version = check_openai_version
    
    # 
    result = test_openai_api
    
    # 
    print("\n" + "=" * 60)
    print("")
    print("=" * 60)
    
    if result:
        if result.get("api_available"):
            print("✅ OpenAI API ")
            print(f"   : {result.get('total_models', 0)}")
            print(f"   GPT: {len(result.get('gpt_models', []))}")
            
            if result.get("gpt52_available"):
                print("✅ GPT-5.2 ")
            else:
                print("⚠️  GPT-5.2 ")
                if result.get("gpt5_models"):
                    print(f"    {len(result.get('gpt5_models', []))} GPT-5")
        else:
            print("❌ OpenAI API ")
            if result.get("error"):
                print(f"   : {result.get('error')}")
    else:
        print("❌ ")
    
    print("\n" + "=" * 60)







