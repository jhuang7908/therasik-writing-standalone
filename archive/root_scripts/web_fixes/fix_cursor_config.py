#!/usr/bin/env python3
"""
 Cursor API 

"""

import os
import sys

print("=" * 60)
print("Cursor API ")
print("=" * 60)

# 
print("\n1.  API ...")

api_keys = {
    "OpenAI": os.environ.get("OPENAI_API_KEY"),
    "Anthropic (Claude)": os.environ.get("ANTHROPIC_API_KEY"),
    "DeepSeek": os.environ.get("DEEPSEEK_API_KEY"),
    "Google Gemini": os.environ.get("GEMINI_API_KEY") or os.environ.get("GOOGLE_API_KEY"),
}

valid_keys = []
for name, key in api_keys.items:
    if key:
        print(f"   ✅ {name}: ")
        valid_keys.append(name)
    else:
        print(f"   ❌ {name}: ")

print(f"\n    {len(valid_keys)}  API ")

# 
print("\n2. ")
print("=" * 60)

print("\n💡  Cursor :")
print("""
 1:  Cursor  (Ctrl + ,)
 2:  "API"  "Models"
 3: :
""")

# OpenAI 
print("""
📌 OpenAI :
----------------------------------------
Provider: OpenAI
Model Name: gpt-4o  ( gpt-4o-mini)
API Endpoint: https://api.openai.com/v1
API Key: []
----------------------------------------
""")

# 
print("\n💡 PowerShell :")
print("""
#  OpenAI API 
$env:OPENAI_API_KEY="sk-proj-Yz...7l0A"

#  Anthropic API  
# $env:ANTHROPIC_API_KEY="sk-ant-your-new-key-here"

#  DeepSeek API  
# $env:DEEPSEEK_API_KEY="sk-your-deepseek-key-here"

#  
# [System.Environment]::SetEnvironmentVariable('OPENAI_API_KEY', 'sk-proj-Yz...7l0A', 'User')
""")

# 
print("\n💡 :")
print("""
#  OpenAI
python -c "from openai import OpenAI; import os; client = OpenAI(api_key=os.environ.get('OPENAI_API_KEY')); print('OpenAI ')"

#  API
python check_all_models.py
""")

# 
print("\n3. :")
print("=" * 60)

print("""
🔍 :
1. OpenAI ，
   - : GPT-5.2, GPT-5.2 Fast, GPT-4.1
   - : gpt-4o, gpt-4o-mini, gpt-4-turbo

2. Claude API 
   - : https://console.anthropic.com/

3. DeepSeek Chat 
   - 

4. Gemini 2.5 
   - : https://console.cloud.google.com/
""")

# 
print("\n4. :")
print("=" * 60)

print("""
✅  1:  Cursor  OpenAI 
   - Model Name: gpt-4o
   - 

✅  2:  Claude API 
   - : https://console.anthropic.com/
   - 
   -  Cursor 

✅  3:  Gemini 
   - : https://console.cloud.google.com/
   - 

✅  4:  DeepSeek Chat
   - 
   - ，

✅  5:  Cursor
   - 
""")

print("\n" + "=" * 60)
print("！:")
print("1.  Cursor  gpt-4o")
print("2.  deepseek-chat")
print("3.  API ")
print("=" * 60)


