#!/usr/bin/env python3
"""
 Cursor "auto" 
"""

import os
import json
from pathlib import Path

print("=" * 70)
print("Cursor Auto ")
print("=" * 70)

#  Cursor 
settings_path = Path(os.environ.get("APPDATA", "")) / "Cursor" / "User" / "settings.json"

print("\n【Cursor 】")
print("-" * 70)
if settings_path.exists:
    print(f"  ✅ : {settings_path}")
    try:
        with open(settings_path, 'r', encoding='utf-8') as f:
            settings = json.load(f)
        
        # 
        model_keys = [k for k in settings.keys if 'model' in k.lower or 'ai' in k.lower]
        if model_keys:
            print("\n  :")
            for key in model_keys:
                print(f"    - {key}: {settings[key]}")
        else:
            print("  ⚠️  ")
        
        # 
        print(f"\n  : {list(settings.keys)}")
    except Exception as e:
        print(f"  ❌ : {e}")
else:
    print(f"  ❌ : {settings_path}")

#  Cursor 
print("\n【】")
print("-" * 70)

config_locations = [
    Path(os.environ.get("APPDATA", "")) / "Cursor" / "User" / "globalStorage",
    Path(os.environ.get("LOCALAPPDATA", "")) / "Cursor",
]

for config_path in config_locations:
    if config_path.exists:
        print(f"  ✅ : {config_path}")
        # 
        try:
            subdirs = [d.name for d in config_path.iterdir if d.is_dir]
            if subdirs:
                print(f"    : {', '.join(subdirs[:5])}...")
        except:
            pass
    else:
        print(f"  ❌ : {config_path}")

print("\n【 Cursor 'Auto' 】")
print("-" * 70)
print("""
Cursor  "Auto" ：

1. ****：
   - OpenAI GPT-4o / GPT-4o-mini（ OpenAI API）
   - Claude 3.5 Sonnet（ Anthropic API）
   - Gemini 2.5（ Google API）
   - DeepSeek Chat（ DeepSeek API）

2. ****：
   - 
   - ，
   - ，

3. ****：
   -  Cursor 
   -  "Auto"，
   -  "AI Models" 

4. ****：
   - 1: 
   - 2:  Cursor  "AI Models" → "Default Model"
   - 3:  Cursor 
""")

print("\n【】")
print("-" * 70)
print("""
 "Auto" ：

1.  Cursor ：
   - 
   -  "Auto"，
   - 

2. ：
   -  Ctrl+, 
   -  "AI Models"
   - 

3.  API ：
   - （ Gemini 2.5）
   - 
""")

print("\n" + "=" * 70)
