#!/usr/bin/env python3
"""
Claude API
API
"""

import os
import sys
from getpass import getpass

def check_anthropic_library:
    """anthropic"""
    try:
        import anthropic
        print(f"✅ Anthropic (: {anthropic.__version__})")
        return True
    except ImportError:
        print("❌ anthropic")
        print("\n💡 :")
        print("   pip install anthropic")
        return False

def get_api_key:
    """API"""
    # 
    api_key = os.environ.get("ANTHROPIC_API_KEY") or os.environ.get("CLAUDE_API_KEY")
    
    if api_key:
        print(f"✅ API: {api_key[:10]}...{api_key[-4:]}")
        use_env = input("\n? (Y/n): ").strip.lower
        if use_env != 'n':
            return api_key
    
    # 
    print("\n" + "=" * 60)
    print("API")
    print("=" * 60)
    print("💡 API: https://console.anthropic.com/")
    print("   : sk-ant-...")
    print
    
    api_key = getpass("Anthropic API : ").strip
    
    if not api_key:
        print("❌ API")
        return None
    
    if not api_key.startswith("sk-ant-"):
        print("⚠️  : API ('sk-ant-')")
        confirm = input("? (y/N): ").strip.lower
        if confirm != 'y':
            return None
    
    return api_key

def test_api_connection(api_key):
    """API"""
    print("\n" + "=" * 60)
    print("API...")
    print("=" * 60)
    
    try:
        from anthropic import Anthropic
        client = Anthropic(api_key=api_key)
        
        # 
        print("\n1. ...")
        response = client.messages.create(
            model="claude-3-5-sonnet-20241022",
            max_tokens=20,
            messages=[{"role": "user", "content": "Hello, please respond with 'API test successful'."}]
        )
        
        print("   ✅ !")
        print(f"   : {response.content[0].text}")
        
        return client
        
    except Exception as e:
        print(f"   ❌ : {e}")
        error_str = str(e)
        
        if "401" in error_str or "Unauthorized" in error_str or "authentication" in error_str.lower:
            print("\n💡 : API")
        elif "429" in error_str or "rate limit" in error_str.lower:
            print("\n💡 : API")
        elif "Network" in error_str or "Connection" in error_str or "timeout" in error_str.lower:
            print("\n💡 : ")
            print("   : Claude API")
        else:
            print(f"\n💡 : {error_str[:200]}")
        
        return None

def test_sonnet45(client):
    """Sonnet 4.5"""
    print("\n" + "=" * 60)
    print(" Claude Sonnet 4.5")
    print("=" * 60)
    
    sonnet45_models = [
        "claude-sonnet-4-5-20250929",
        "claude-sonnet-4-5",
        "claude-4-5-sonnet",
    ]
    
    available_models = []
    
    for model_id in sonnet45_models:
        try:
            print(f"\n: {model_id}")
            response = client.messages.create(
                model=model_id,
                max_tokens=30,
                messages=[
                    {"role": "user", "content": "Claude Sonnet 4.5，''。"}
                ]
            )
            print(f"   ✅ {model_id} !")
            print(f"   : {response.content[0].text}")
            available_models.append(model_id)
            
        except Exception as e:
            error_msg = str(e)
            if "not found" in error_msg.lower or "404" in error_msg:
                print(f"   ❌ {model_id}  ")
            elif "model" in error_msg.lower and "invalid" in error_msg.lower:
                print(f"   ❌ {model_id}  ")
            else:
                print(f"   ⚠️  {model_id} : {str(e)[:80]}")
    
    return available_models

def test_other_models(client):
    """Claude"""
    print("\n" + "=" * 60)
    print("Claude")
    print("=" * 60)
    
    models_to_test = [
        ("claude-3-5-sonnet-20241022", "Claude 3.5 Sonnet"),
        ("claude-3-opus-20240229", "Claude 3 Opus"),
        ("claude-3-haiku-20240307", "Claude 3 Haiku"),
        ("claude-sonnet-4-20250514", "Claude Sonnet 4"),
        ("claude-opus-4-20250514", "Claude Opus 4"),
    ]
    
    available = []
    
    for model_id, description in models_to_test:
        try:
            response = client.messages.create(
                model=model_id,
                max_tokens=10,
                messages=[{"role": "user", "content": "test"}]
            )
            print(f"   ✅ {model_id} ({description}) - ")
            available.append((model_id, description))
        except Exception as e:
            if "not found" in str(e).lower or "404" in str(e):
                print(f"   ❌ {model_id} ({description}) - ")
            else:
                print(f"   ⚠️  {model_id} ({description}) - : {str(e)[:60]}")
    
    return available

def generate_summary(client, sonnet45_models, other_models):
    """"""
    print("\n" + "=" * 60)
    print("")
    print("=" * 60)
    
    print("\n✅ Claude API !")
    
    if sonnet45_models:
        print(f"\n🎉 Claude Sonnet 4.5 !")
        print(f"   : {', '.join(sonnet45_models)}")
        print(f"\n   Cursor: {sonnet45_models[0]}")
    else:
        print("\n⚠️  Claude Sonnet 4.5 ")
        print("   :")
        print("   - ")
        print("   - ")
        print("   - ")
    
    if other_models:
        print(f"\n✅  ({len(other_models)} ):")
        for model_id, description in other_models:
            print(f"   - {model_id}: {description}")
    
    print("\n" + "=" * 60)
    print("Cursor")
    print("=" * 60)
    print("\n:")
    if sonnet45_models:
        print(f"   Model Name: {sonnet45_models[0]}")
    elif other_models:
        print(f"   Model Name: {other_models[0][0]}")
    print("   Provider: Anthropic")
    print("   API Endpoint: https://api.anthropic.com/v1")
    print("   API Key: [API]")

if __name__ == "__main__":
    print("\n" + "=" * 60)
    print("Claude API ")
    print("=" * 60)
    
    # 
    if not check_anthropic_library:
        sys.exit(1)
    
    # API
    api_key = get_api_key
    if not api_key:
        print("\n❌ API，")
        sys.exit(1)
    
    # 
    client = test_api_connection(api_key)
    if not client:
        print("\n❌ API，")
        sys.exit(1)
    
    # Sonnet 4.5
    sonnet45_models = test_sonnet45(client)
    
    # 
    other_models = test_other_models(client)
    
    # 
    generate_summary(client, sonnet45_models, other_models)
    
    print("\n" + "=" * 60)
    print("!")
    print("=" * 60)







