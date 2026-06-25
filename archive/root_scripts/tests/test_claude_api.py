#!/usr/bin/env python3
"""
Claude API
Sonnet 4.5
"""

import os
import sys
from typing import Optional, Dict

def check_anthropic_api_key:
    """Anthropic API"""
    print("=" * 60)
    print("Claude API ")
    print("=" * 60)
    
    # 
    api_key = os.environ.get("ANTHROPIC_API_KEY") or os.environ.get("CLAUDE_API_KEY")
    
    if not api_key:
        print("⚠️  ANTHROPIC_API_KEYCLAUDE_API_KEY")
        print("\n💡 API:")
        print("   1. : https://console.anthropic.com/")
        print("   2. /")
        print("   3. API")
        print("   4. : export ANTHROPIC_API_KEY='your-key'")
        return None
    
    print(f"✅ API: {api_key[:10]}...{api_key[-4:]}")
    return api_key

def test_anthropic_api(api_key: str):
    """Anthropic API"""
    print("\n" + "-" * 60)
    print("API...")
    print("-" * 60)
    
    # anthropic
    try:
        from anthropic import Anthropic
        print("✅ Anthropic")
    except ImportError:
        print("❌ : anthropic")
        print("   : pip install anthropic")
        return None
    
    try:
        client = Anthropic(api_key=api_key)
        
        # API - messages API
        print("\nAPI...")
        
        # 
        test_response = client.messages.create(
            model="claude-3-5-sonnet-20241022",  # 
            max_tokens=10,
            messages=[
                {"role": "user", "content": "Hello"}
            ]
        )
        
        print("✅ API!")
        print(f"   : {test_response.content[0].text[:50]}")
        
        return client
        
    except Exception as e:
        print(f"❌ API: {e}")
        print(f"   : {type(e).__name__}")
        
        # 
        error_str = str(e)
        if "401" in error_str or "Unauthorized" in error_str or "authentication" in error_str.lower:
            print("\n💡 : API")
            print("   : https://console.anthropic.com/")
        elif "429" in error_str or "rate limit" in error_str.lower:
            print("\n💡 : API")
        elif "Network" in error_str or "Connection" in error_str or "timeout" in error_str.lower:
            print("\n💡 : ")
            print("   : Claude API")
        elif "model" in error_str.lower or "not found" in error_str.lower:
            print("\n💡 : ")
        else:
            print("\n💡 : ，API")
        
        return None

def check_claude_models(client):
    """Claude"""
    print("\n" + "-" * 60)
    print("")
    print("-" * 60)
    
    # Claude（Anthropic）
    known_models = {
        "claude-3-5-sonnet-20241022": "Claude 3.5 Sonnet ",
        "claude-3-5-sonnet-20240620": "Claude 3.5 Sonnet ",
        "claude-3-opus-20240229": "Claude 3 Opus",
        "claude-3-sonnet-20240229": "Claude 3 Sonnet",
        "claude-3-haiku-20240307": "Claude 3 Haiku",
        "claude-opus-4.5": "Claude Opus 4.5 ",
        "claude-sonnet-4.5": "Claude Sonnet 4.5 ",
    }
    
    print("\n...")
    available_models = []
    sonnet45_found = False
    
    for model_id, description in known_models.items:
        try:
            # 
            response = client.messages.create(
                model=model_id,
                max_tokens=5,
                messages=[{"role": "user", "content": "test"}]
            )
            available_models.append({
                "id": model_id,
                "description": description,
                "status": "✅ "
            })
            
            # Sonnet 4.5
            if "4.5" in model_id.lower or "sonnet-4.5" in model_id.lower:
                sonnet45_found = True
                print(f"  ⭐ {model_id}: {description} - ✅ ")
            else:
                print(f"  ✅ {model_id}: {description} - ")
                
        except Exception as e:
            error_msg = str(e)
            if "not found" in error_msg.lower or "404" in error_msg:
                print(f"  ❌ {model_id}: {description} - ")
            elif "401" in error_msg or "authentication" in error_msg.lower:
                print(f"  ⚠️  {model_id}: ")
                break
            else:
                print(f"  ⚠️  {model_id}: {description} - : {str(e)[:50]}")
    
    return available_models, sonnet45_found

def test_sonnet45(client):
    """Sonnet 4.5"""
    print("\n" + "-" * 60)
    print(" Claude Sonnet 4.5")
    print("-" * 60)
    
    # Sonnet 4.5
    sonnet45_variants = [
        "claude-sonnet-4.5",
        "claude-3-5-sonnet-4.5",
        "claude-sonnet-4.5-20241022",
        "claude-opus-4.5",
        "claude-4.5-sonnet",
        "sonnet-4.5",
    ]
    
    found_models = []
    
    for model_id in sonnet45_variants:
        try:
            print(f"\n: {model_id}")
            response = client.messages.create(
                model=model_id,
                max_tokens=20,
                messages=[
                    {"role": "user", "content": "Claude Sonnet 4.5。"}
                ]
            )
            print(f"  ✅ {model_id} !")
            print(f"     : {response.content[0].text[:100]}")
            found_models.append(model_id)
            
        except Exception as e:
            error_msg = str(e)
            if "not found" in error_msg.lower or "404" in error_msg:
                print(f"  ❌ {model_id}  ")
            elif "model" in error_msg.lower and "invalid" in error_msg.lower:
                print(f"  ❌ {model_id}  ")
            else:
                print(f"  ⚠️  {model_id} : {str(e)[:80]}")
    
    return found_models

def generate_recommendation(api_key, available_models, sonnet45_found, sonnet45_models):
    """"""
    print("\n" + "=" * 60)
    print("")
    print("=" * 60)
    
    if not api_key:
        print("\n❌ API")
        print("\n📝 :")
        print("1.  https://console.anthropic.com/")
        print("2. /")
        print("3. API")
        print("4. :")
        print("   Windows PowerShell: $env:ANTHROPIC_API_KEY='your-key'")
        print("   Windows CMD: set ANTHROPIC_API_KEY=your-key")
        print("   Linux/Mac: export ANTHROPIC_API_KEY='your-key'")
        return
    
    if not available_models:
        print("\n⚠️  Claude API")
        print("   :")
        print("   - API")
        print("   - ")
        print("   - ")
        return
    
    print(f"\n✅  {len(available_models)} ")
    
    if sonnet45_found or sonnet45_models:
        print("\n🎉 Claude Sonnet 4.5 !")
        if sonnet45_models:
            print(f"   : {', '.join(sonnet45_models)}")
        print("\n:")
        print("  - : claude-sonnet-4.5  claude-opus-4.5")
        print("  - : 、、")
    else:
        print("\n⚠️  Claude Sonnet 4.5")
        print("   :")
        for model in available_models:
            if "sonnet" in model["id"].lower:
                print(f"  - {model['id']}: {model['description']}")
        
        print("\n💡 :")
        print("  - Claude 3.5 SonnetSonnet 4.5")
        print("  - Sonnet 4.5")

if __name__ == "__main__":
    print("\n")
    print("=" * 60)
    print("Claude API ")
    print("=" * 60)
    
    # API
    api_key = check_anthropic_api_key
    
    if not api_key:
        print("\n" + "=" * 60)
        print("❌ API，")
        print("=" * 60)
        sys.exit(1)
    
    # API
    client = test_anthropic_api(api_key)
    
    if not client:
        print("\n" + "=" * 60)
        print("❌ API")
        print("=" * 60)
        sys.exit(1)
    
    # 
    available_models, sonnet45_found = check_claude_models(client)
    
    # Sonnet 4.5
    sonnet45_models = test_sonnet45(client)
    
    # 
    generate_recommendation(api_key, available_models, sonnet45_found, sonnet45_models)
    
    print("\n" + "=" * 60)
    print("")
    print("=" * 60)







