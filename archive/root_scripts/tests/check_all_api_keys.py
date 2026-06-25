#!/usr/bin/env python3
"""
APIAPI
"""

import os
import sys
from anthropic import Anthropic
from openai import OpenAI
# from deepseek import Deepseek (DeepSeekPython)
# from google.generativeai import GenerativeModel (GeminiPython)

print("=" * 60)
print("API ")
print("=" * 60)

def check_openai_key:
    """OpenAI API"""
    print("\n---  OpenAI API --- ")
    key = os.environ.get("OPENAI_API_KEY")
    if not key:
        print("❌  OPENAI_API_KEY")
        return False
    
    print(f"✅  OPENAI_API_KEY: {key[:10]}...{key[-4:]}")
    try:
        client = OpenAI(api_key=key)
        client.models.list # 
        print("✅ OpenAI API ")
        return True
    except Exception as e:
        print(f"❌ OpenAI API : {e}")
        return False

def check_anthropic_key:
    """Anthropic API"""
    print("\n---  Anthropic API (Claude) --- ")
    key = os.environ.get("ANTHROPIC_API_KEY")
    if not key:
        print("❌  ANTHROPIC_API_KEY")
        return False
    
    print(f"✅  ANTHROPIC_API_KEY: {key[:10]}...{key[-4:]}")
    try:
        client = Anthropic(api_key=key)
        client.messages.create(
            model="claude-3-5-sonnet-20241022", # 
            max_tokens=1,
            messages=[{"role": "user", "content": "hi"}]
        )
        print("✅ Anthropic API ")
        return True
    except Exception as e:
        print(f"❌ Anthropic API : {e}")
        return False

def check_deepseek_key:
    """DeepSeek API"""
    print("\n---  DeepSeek API --- ")
    key = os.environ.get("DEEPSEEK_API_KEY")
    if not key:
        print("❌  DEEPSEEK_API_KEY")
        return False
    
    print(f"✅  DEEPSEEK_API_KEY: {key[:10]}...{key[-4:]}")
    # DeepSeek APIPython，OpenAI
    # 
    if key.startswith("sk-") and len(key) > 30:
        print("✅ DeepSeek API  (API)")
        # deepseek-pyrequestsAPI
        return True
    else:
        print("❌ DeepSeek API ")
        return False

def check_gemini_key:
    """Google Gemini API"""
    print("\n---  Google Gemini API --- ")
    key = os.environ.get("GEMINI_API_KEY") or os.environ.get("GOOGLE_API_KEY")
    if not key:
        print("❌  GEMINI_API_KEY  GOOGLE_API_KEY")
        return False
    
    print(f"✅  Gemini API : {key[:10]}...{key[-4:]}")
    # Gemini APIgoogle-generativeairequests
    # 
    if len(key) > 30:
        print("✅ Gemini API  (API)")
        return True
    else:
        print("❌ Gemini API ")
        return False

if __name__ == "__main__":
    valid_keys_count = 0
    
    if check_openai_key:
        valid_keys_count += 1
        
    if check_anthropic_key:
        valid_keys_count += 1
        
    if check_deepseek_key:
        valid_keys_count += 1
        
    if check_gemini_key:
        valid_keys_count += 1
    
    print("\n" + "=" * 60)
    print(f" {valid_keys_count} API")
    print("============================================================")





