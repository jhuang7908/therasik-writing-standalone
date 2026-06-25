#!/usr/bin/env python3
"""
 Cursor API ：tools[0]: missing field `function`
 Cursor  Bug 
"""

import os
import sys
from pathlib import Path

print("=" * 70)
print("Cursor API ")
print(": tools[0]: missing field `function`")
print("=" * 70)

print("\n【】")
print("-" * 70)
print(" Cursor  API ，。")
print("： 'function' 。")
print(" Cursor  Bug，。")

print("\n【】")
print("-" * 70)
print("1. ✅  Cursor")
print("   -  Cursor")
print("   -  Cursor")
print("   - ")
print
print("2. ✅ ")
print("   - ，")
print("   - ：Gemini 2.5")
print
print("3. ✅ ")
print("   -  Cursor")
print("   -  Cursor ")
print("   - ")

print("\n【 API 】")
print("-" * 70)

# 
api_keys = {
    "OpenAI": os.environ.get("OPENAI_API_KEY"),
    "Anthropic (Claude)": os.environ.get("ANTHROPIC_API_KEY"),
    "DeepSeek": os.environ.get("DEEPSEEK_API_KEY"),
    "Google Gemini": os.environ.get("GEMINI_API_KEY") or os.environ.get("GOOGLE_API_KEY"),
}

print("\n API ：")
for name, key in api_keys.items:
    if key:
        masked = f"{key[:10]}...{key[-4:]}" if len(key) > 14 else "***"
        print(f"  ✅ {name}: {masked}")
    else:
        print(f"  ❌ {name}: ")

print("\n【Cursor 】")
print("-" * 70)
cursor_config_paths = [
    Path.home / "AppData" / "Roaming" / "Cursor" / "User" / "settings.json",
    Path.home / ".cursor" / "settings.json",
]

print("\n Cursor ：")
for path in cursor_config_paths:
    if path.exists:
        print(f"  ✅ : {path}")
        print(f"     : {path.stat.st_size} ")
    else:
        print(f"  ❌ : {path}")

print("\n【】")
print("-" * 70)
print("""
 1:  Cursor
  -  Ctrl+Shift+Q 
  - 
  -  Cursor

 2: 
  - 
  - 

 3: 
  - ， Gemini 2.5 
  - 

 4: 
  -  Cursor 
  -  Cursor 
  -  Cursor 
""")

print("\n【】")
print("-" * 70)
print("：")
print("  'Failed to deserialize the JSON body into the target type: ")
print("   tools[0]: missing field `function` at line 1 column 33574'")
print
print("：")
print("  - Cursor  API")
print("  -  'function' ")
print("  -  Cursor  Bug")
print("  - ")

print("\n" + "=" * 70)
print("！")
print("=" * 70)
print("\n💡 ： Cursor ，。")
