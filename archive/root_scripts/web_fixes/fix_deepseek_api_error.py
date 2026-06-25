#!/usr/bin/env python3
"""
DeepSeek API：Missing `reasoning_content` field
DeepSeek（thinking mode）
"""

import os
import sys
import json

def explain_error:
    """"""
    print("=" * 80)
    print("DeepSeek API ")
    print("=" * 80)
    
    print("\n❌ :")
    print("  Missing `reasoning_content` field in the assistant message at message index 3")
    
    print("\n📋 :")
    print("  1. DeepSeek（thinking mode）")
    print("  2. 3， `reasoning_content` ")
    print("  3. DeepSeek")
    
    print("\n🔧 :")
    print("  1: Cursor")
    print("    - ， 'deepseek-chat'  'deepseek-reasoner'")
    print("    -  'gpt-4o'")
    
    print("\n  2: ")
    print("    -  'reasoning_content' ")
    print("    - :")
    print("      ```json")
    print("      {")
    print('        "role": "assistant",')
    print('        "content": "",')
    print('        "reasoning_content": "..."')
    print("      }")
    print("      ```")
    
    print("\n  3: CursorAPI")
    print("    - Cursor (Ctrl+,)")
    print("    -  'AI Models'  'Custom API Keys'")
    print("    - DeepSeek API")
    
    print("\n  4: ")
    print("    - : DEEPSEEK_API_KEY=your_key_here")
    print("    - Cursor")

def check_current_config:
    """"""
    print("\n" + "=" * 80)
    print("")
    print("=" * 80)
    
    # 
    deepseek_keys = {
        "DEEPSEEK_API_KEY": os.environ.get("DEEPSEEK_API_KEY"),
        "DEEPSEEK_KEY": os.environ.get("DEEPSEEK_KEY"),
        "DEEPSEEK_TOKEN": os.environ.get("DEEPSEEK_TOKEN"),
    }
    
    print("\n🔑 :")
    found = False
    for key_name, key_value in deepseek_keys.items:
        if key_value:
            print(f"  ✅ {key_name}: {key_value[:10]}...{key_value[-4:]}")
            found = True
        else:
            print(f"  ❌ {key_name}: ")
    
    if not found:
        print("  ⚠️ DeepSeek API")
    
    # Cursor
    print("\n📁 Cursor:")
    cursor_config_paths = [
        os.path.expanduser("~/.cursor/settings.json"),
        os.path.expanduser("~/AppData/Roaming/Cursor/User/settings.json"),
        os.path.expanduser("~/Library/Application Support/Cursor/User/settings.json"),
    ]
    
    for path in cursor_config_paths:
        if os.path.exists(path):
            print(f"  ✅ Cursor: {path}")
            try:
                with open(path, 'r', encoding='utf-8') as f:
                    config = json.load(f)
                    if "aiModels" in config or "customApiKeys" in config:
                        print("  ✅ AI")
            except:
                print("  ⚠️ ")
        else:
            print(f"  ❌ : {path}")

def provide_quick_fix:
    """"""
    print("\n" + "=" * 80)
    print("")
    print("=" * 80)
    
    print("\n🚀 :")
    print("  1. ，")
    print("  2.  'gpt-4o'  'gpt-4o-mini'")
    print("  3. ")
    print("  4. DeepSeek API")
    
    print("\n📝 :")
    print("  1. DeepSeek API:")
    print("     - : https://platform.deepseek.com/")
    print("     - API")
    
    print("\n  2. Cursor:")
    print("     - Cursor (Ctrl+,)")
    print("     -  'AI Models'")
    print("     - :")
    print("       Provider: DeepSeek")
    print("       Model Name: deepseek-chat")
    print("       API Endpoint: https://api.deepseek.com/v1")
    print("       API Key: []")
    
    print("\n  3. :")
    print("     -  'Verify' ")
    print("     - ")

def test_deepseek_connection:
    """DeepSeek"""
    print("\n" + "=" * 80)
    print("DeepSeek")
    print("=" * 80)
    
    try:
        from openai import OpenAI
        
        # 
        api_key = os.environ.get("DEEPSEEK_API_KEY") or os.environ.get("DEEPSEEK_KEY")
        
        if not api_key:
            print("❌ DeepSeek API")
            print("💡 : DEEPSEEK_API_KEY=your_key_here")
            return
        
        print(f"🔑 API: {api_key[:10]}...{api_key[-4:]}")
        
        # 
        client = OpenAI(
            api_key=api_key,
            base_url="https://api.deepseek.com/v1"
        )
        
        print("🔄 ...")
        try:
            # 
            response = client.chat.completions.create(
                model="deepseek-chat",
                messages=[
                    {"role": "user", "content": "Hello, please respond with 'Test successful'."}
                ],
                max_tokens=20
            )
            print(f"✅ !")
            print(f"📝 : {response.choices[0].message.content}")
            
        except Exception as e:
            print(f"❌ : {e}")
            
    except ImportError:
        print("❌ openai")
        print("💡 : pip install openai")
    except Exception as e:
        print(f"❌ : {e}")

if __name__ == "__main__":
    print("🔧 DeepSeek API")
    print("=" * 80)
    
    explain_error
    check_current_config
    provide_quick_fix
    
    # 
    print("\n" + "=" * 80)
    test_option = input("DeepSeek? (y/n): ").strip.lower
    if test_option == 'y':
        test_deepseek_connection
    
    print("\n" + "=" * 80)
    print("✅ ")
    print("=" * 80)


