#!/usr/bin/env python3
"""
 Claude 3.5 Sonnet、Gemini 2.5、DeepSeek Chat 
"""

import os
import sys

print("=" * 70)
print("")
print("=" * 70)

# 1. Claude 3.5 Sonnet
print("\n【1. Claude 3.5 Sonnet】")
print("-" * 70)
anthropic_key = os.environ.get("ANTHROPIC_API_KEY")
if anthropic_key:
    print(f"  ✅  API : {anthropic_key[:10]}...{anthropic_key[-4:]}")
    try:
        from anthropic import Anthropic
        client = Anthropic(api_key=anthropic_key)
        
        # 
        models_to_test = [
            "claude-3-5-sonnet-20241022",
            "claude-3-5-sonnet-20240620",
            "claude-3-5-sonnet",
            "claude-3-5-haiku-20241022",  # Haiku 
            "claude-3-5-opus-20241022",   # Opus 
        ]
        
        print("  ...")
        working_model = None
        for model in models_to_test:
            try:
                response = client.messages.create(
                    model=model,
                    max_tokens=1,
                    messages=[{"role": "user", "content": "hi"}]
                )
                print(f"  ✅ {model} - ")
                working_model = model
                break
            except Exception as e:
                error_msg = str(e)
                if "not_found" in error_msg.lower or "404" in error_msg:
                    print(f"  ❌ {model} - ")
                else:
                    print(f"  ⚠️  {model} - : {error_msg[:50]}")
        
        if working_model:
            print(f"\n  ✅ Claude ！: {working_model}")
        else:
            print("\n  ❌ ")
            print("  💡 ： Anthropic ")
    except ImportError:
        print("  ❌  anthropic ")
        print("  💡 : pip install anthropic")
    except Exception as e:
        print(f"  ❌ : {e}")
else:
    print("  ❌  ANTHROPIC_API_KEY")
    print("  💡 : https://console.anthropic.com/")

# 2. Gemini 2.5
print("\n【2. Gemini 2.5】")
print("-" * 70)
gemini_key = os.environ.get("GEMINI_API_KEY") or os.environ.get("GOOGLE_API_KEY")
if gemini_key:
    print(f"  ✅  API : {gemini_key[:10]}...{gemini_key[-4:]}")
    try:
        import google.generativeai as genai
        genai.configure(api_key=gemini_key)
        
        #  Gemini 
        models_to_test = [
            "gemini-2.0-flash-exp",
            "gemini-1.5-pro",
            "gemini-1.5-flash",
            "gemini-pro",
        ]
        
        print("  ...")
        working_model = None
        for model_name in models_to_test:
            try:
                model = genai.GenerativeModel(model_name)
                response = model.generate_content("hi")
                print(f"  ✅ {model_name} - ")
                working_model = model_name
                break
            except Exception as e:
                error_msg = str(e)
                if "not found" in error_msg.lower or "404" in error_msg:
                    print(f"  ❌ {model_name} - ")
                else:
                    print(f"  ⚠️  {model_name} - : {error_msg[:50]}")
        
        if working_model:
            print(f"\n  ✅ Gemini ！: {working_model}")
        else:
            print("\n  ❌ ")
    except ImportError:
        print("  ❌  google-generativeai ")
        print("  💡 : pip install google-generativeai")
    except Exception as e:
        print(f"  ❌ : {e}")
else:
    print("  ❌  GEMINI_API_KEY  GOOGLE_API_KEY")
    print("  💡 : https://makersuite.google.com/app/apikey")

# 3. DeepSeek Chat
print("\n【3. DeepSeek Chat】")
print("-" * 70)
deepseek_key = os.environ.get("DEEPSEEK_API_KEY")
if deepseek_key:
    print(f"  ✅  API : {deepseek_key[:10]}...{deepseek_key[-4:]}")
    try:
        from openai import OpenAI
        client = OpenAI(
            api_key=deepseek_key,
            base_url="https://api.deepseek.com/v1"
        )
        
        #  DeepSeek 
        response = client.chat.completions.create(
            model="deepseek-chat",
            messages=[{"role": "user", "content": "hi"}],
            max_tokens=5
        )
        print("  ✅ deepseek-chat - ")
        print("\n  ✅ DeepSeek Chat ！")
    except ImportError:
        print("  ❌  openai ")
        print("  💡 : pip install openai")
    except Exception as e:
        print(f"  ❌ : {e}")
        print("  💡  API ")
else:
    print("  ❌  DEEPSEEK_API_KEY")
    print("  💡 : https://platform.deepseek.com/")

# 
print("\n" + "=" * 70)
print("")
print("=" * 70)

available_models = []
if anthropic_key:
    available_models.append("Claude ")
if gemini_key:
    available_models.append("Gemini ")
if deepseek_key:
    available_models.append("DeepSeek Chat ")

if available_models:
    print(f"\n✅  API: {', '.join(available_models)}")
    print("\n💡 ：")
    print("  1.  Cursor  API")
    print("  2. ")
    print("  3. ")
else:
    print("\n❌ ")
    print("\n💡 ：")
    print("  1.  API ")
    print("  2.  Cursor ")
    print("  3. ")

print("\n" + "=" * 70)
