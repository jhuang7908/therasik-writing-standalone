#!/usr/bin/env python3
"""
Claude API

"""

import os
import sys
from pathlib import Path

print("=" * 60)
print("Claude API ")
print("=" * 60)

# 1. 
print("\n1. ...")
env_vars = {
    "ANTHROPIC_API_KEY": os.environ.get("ANTHROPIC_API_KEY"),
    "CLAUDE_API_KEY": os.environ.get("CLAUDE_API_KEY"),
}

found_keys = []
for key, value in env_vars.items:
    if value:
        print(f"   ✅  {key}: {value[:10]}...{value[-4:]}")
        found_keys.append((key, value))
    else:
        print(f"   ❌  {key}")

if not found_keys:
    print("\n   ⚠️  API")
    print("\n   💡 :")
    print("      - /")
    print("      - ")
    print("      - IDE")

# 2. Cursor
print("\n2. Cursor...")
cursor_config_paths = [
    Path.home / "AppData" / "Roaming" / "Cursor" / "User" / "settings.json",
    Path.home / ".cursor" / "settings.json",
    Path.home / ".cursor" / "config.json",
]

found_config = False
for config_path in cursor_config_paths:
    if config_path.exists:
        print(f"   ✅ : {config_path}")
        try:
            import json
            with open(config_path, 'r', encoding='utf-8') as f:
                config = json.load(f)
                # API
                api_configs = {k: v for k, v in config.items 
                              if any(keyword in k.lower for keyword in ['api', 'key', 'anthropic', 'claude'])}
                if api_configs:
                    print(f"   ✅ API: {list(api_configs.keys)}")
                    found_config = True
                else:
                    print(f"   ⚠️  API")
        except Exception as e:
            print(f"   ⚠️  : {e}")

if not found_config:
    print("   ⚠️  CursorAPI")

# 3. Anthropic
print("\n3. Anthropic...")
try:
    import anthropic
    print(f"   ✅ Anthropic (: {anthropic.__version__})")
    library_ok = True
except ImportError:
    print("   ❌ Anthropic")
    print("   💡 : pip install anthropic")
    library_ok = False

# 4. ，
if found_keys:
    print("\n4. API...")
    api_key = found_keys[0][1]
    
    if library_ok:
        try:
            from anthropic import Anthropic
            client = Anthropic(api_key=api_key)
            
            # 
            print("   ...")
            response = client.messages.create(
                model="claude-3-5-sonnet-20241022",
                max_tokens=10,
                messages=[{"role": "user", "content": "test"}]
            )
            print("   ✅ API!")
            print(f"   : {response.content[0].text}")
            
        except Exception as e:
            print(f"   ❌ API: {e}")
            error_str = str(e)
            
            if "401" in error_str or "Unauthorized" in error_str or "authentication" in error_str.lower:
                print("\n   💡 : API")
                print("      : https://console.anthropic.com/")
            elif "429" in error_str or "rate limit" in error_str.lower:
                print("\n   💡 : API")
            elif "Network" in error_str or "Connection" in error_str or "timeout" in error_str.lower:
                print("\n   💡 : ")
                print("      : Claude API")
            elif "model" in error_str.lower or "not found" in error_str.lower:
                print("\n   💡 : ")
            else:
                print(f"\n   💡 : {error_str[:200]}")
    else:
        print("   ⚠️  ")

# 5. 
print("\n" + "=" * 60)
print("")
print("=" * 60)

if not found_keys:
    print("\n❌ : API")
    print("\n:")
    print("\n1: PowerShell")
    print("   $env:ANTHROPIC_API_KEY='sk-ant-your-key-here'")
    print("   ")
    
    print("\n2: （Windows）")
    print("   [System.Environment]::SetEnvironmentVariable('ANTHROPIC_API_KEY', 'sk-ant-your-key', 'User')")
    print("   /IDE")
    
    print("\n3: ")
    print("   python test_claude_api_interactive.py")
    
    print("\n4: Cursor")
    print("   1. Cursor (Ctrl+,)")
    print("   2.  'API'  'Anthropic'")
    print("   3. API")
    print("   4. ")

elif found_keys and library_ok:
    print("\n✅ ")
    print("   ，")

print("\n" + "=" * 60)
print("")
print("=" * 60)
print("""
1. ？
   ✅ : sk-ant-xxx...
   ❌ : 

2. /？
   - PowerShell
   - ，

3. Cursor？
   - Cursor

4. API？
   - : https://console.anthropic.com/
   - 
   - 

5. ？
   - Claude API
   - : https://api.anthropic.com/
""")

print("=" * 60)







