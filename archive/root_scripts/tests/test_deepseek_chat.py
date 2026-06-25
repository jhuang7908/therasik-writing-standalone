#!/usr/bin/env python3
"""
DeepSeek Chat API
deepseek-chat，reasoning_content
"""

import os
import sys
from openai import OpenAI

def test_deepseek_chat:
    """deepseek-chat"""
    print("=" * 60)
    print(" DeepSeek Chat API ")
    print("=" * 60)
    
    # 
    api_key = os.environ.get("DEEPSEEK_API_KEY")
    if not api_key:
        print("❌  DEEPSEEK_API_KEY ")
        print("\n💡 :")
        print("   PowerShell:")
        print('   $env:DEEPSEEK_API_KEY = "your_api_key_here"')
        print("\n   :")
        print("   DEEPSEEK_API_KEY=your_api_key_here")
        return False
    
    print(f"✅ API: {api_key[:10]}...{api_key[-4:]}")
    
    try:
        # 
        client = OpenAI(
            api_key=api_key,
            base_url="https://api.deepseek.com/v1"
        )
        
        print("\n🔄  deepseek-chat ...")
        
        # 
        response = client.chat.completions.create(
            model="deepseek-chat",
            messages=[
                {"role": "user", "content": " 'DeepSeek Chat '"}
            ],
            max_tokens=20,
            temperature=0.7
        )
        
        print(f"✅ !")
        print(f"📝 : {response.choices[0].message.content}")
        
        # 
        print(f"\n📊 : deepseek-chat")
        print(f"📊 : {response.usage.total_tokens} tokens")
        
        return True
        
    except Exception as e:
        print(f"❌ : {e}")
        
        # 
        if "401" in str(e):
            print("\n💡 API，")
        elif "404" in str(e):
            print("\n💡 ， 'deepseek-chat'")
        elif "reasoning_content" in str(e):
            print("\n💡 ， deepseek-chat")
            print("   Cursor")
        else:
            print("\n💡 API")
        
        return False

def check_cursor_config:
    """Cursor"""
    print("\n" + "=" * 60)
    print("Cursor")
    print("=" * 60)
    
    print("\n📝 CursorDeepSeek Chat:")
    print("1.  Ctrl+, ")
    print("2.  'AI Models'")
    print("3.  'Add Model'")
    print("4. :")
    print("   - Provider: DeepSeek")
    print("   - Model Name: deepseek-chat")
    print("   - API Endpoint: https://api.deepseek.com/v1")
    print("   - API Key: []")
    print("5.  'Verify' ")
    print("6. ")
    
    print("\n⚠️ :")
    print("-  'deepseek-chat'  'deepseek-reasoner'")
    print("- 'deepseek-chat'  reasoning_content ")
    print("- ，")

def quick_fix_for_current_session:
    """"""
    print("\n" + "=" * 60)
    print("")
    print("=" * 60)
    
    print("\n🚀 :")
    print("1. ，")
    print("2.  'gpt-4o'  'gpt-4o-mini'")
    print("3. ，")
    print("4. DeepSeek Chat")
    
    print("\n📊 :")
    print("- gpt-4o: ，")
    print("- gpt-4o-mini: ，")
    print("- deepseek-chat: API")

if __name__ == "__main__":
    # 
    success = test_deepseek_chat
    
    if not success:
        check_cursor_config
        quick_fix_for_current_session
    
    print("\n" + "=" * 60)
    print("")
    print("=" * 60)
    
    if success:
        print("✅ DeepSeek Chat ，Cursor")
    else:
        print("⚠️  DeepSeek Chat ，:")
        print("   1.  gpt-4o ")
        print("   2.  DeepSeek Chat API")
        print("   3. API: https://platform.deepseek.com/")


