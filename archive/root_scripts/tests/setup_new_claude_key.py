#!/usr/bin/env python3
"""
Claude API
"""

import os
import sys

# API（，）
# PowerShell ：$env:NEW_ANTHROPIC_API_KEY = "sk-ant-..."
NEW_CLAUDE_KEY = os.environ.get("NEW_ANTHROPIC_API_KEY")
if not NEW_CLAUDE_KEY:
    print("❌  NEW_ANTHROPIC_API_KEY ")
    print("💡 PowerShell ：$env:NEW_ANTHROPIC_API_KEY = 'sk-ant-...'\n")
    sys.exit(1)

print("=" * 60)
print(" Claude API ")
print("=" * 60)

# 1. 
print("\n1.  Anthropic ...")
try:
    import anthropic
    print("   ✅ Anthropic ")
except ImportError:
    print("   ❌  Anthropic ")
    print("   💡 : pip install anthropic")
    sys.exit(1)

# 2. 
print("\n2.  API ...")
try:
    from anthropic import Anthropic
    client = Anthropic(api_key=NEW_CLAUDE_KEY)
    
    # 
    print("   ...")
    response = client.messages.create(
        model="claude-sonnet-4-5-20250929",
        max_tokens=10,
        messages=[{"role": "user", "content": "test"}]
    )
    print("   ✅  API !")
    print(f"   : {response.content[0].text}")
    
except Exception as e:
    error_msg = str(e)
    print(f"   ❌ API : {e}")
    
    if "401" in error_msg or "authentication" in error_msg.lower:
        print("   💡 : API ")
    elif "not_found" in error_msg.lower:
        print("   💡 : ，...")
        # 
        other_models = [
            "claude-sonnet-4-5",
            "claude-3-5-sonnet-20241022",
            "claude-3-5-sonnet-20240620",
        ]
        
        for model in other_models:
            try:
                response = client.messages.create(
                    model=model,
                    max_tokens=5,
                    messages=[{"role": "user", "content": "test"}]
                )
                print(f"   ✅  {model} !")
                break
            except:
                continue
    else:
        print(f"   💡 : {error_msg[:100]}")
    
    sys.exit(1)

# 3. 
print("\n3. ...")
try:
    os.environ["ANTHROPIC_API_KEY"] = NEW_CLAUDE_KEY
    print("   ✅ ")
except Exception as e:
    print(f"   ❌ : {e}")

# 4. 
print("\n4.  (PowerShell):")
print(f"""
#  :
$env:ANTHROPIC_API_KEY = "sk-ant-..."

#  :
[System.Environment]::SetEnvironmentVariable('ANTHROPIC_API_KEY', 'sk-ant-...', 'User')
""")

print("\n5. ...")
current_key = os.environ.get("ANTHROPIC_API_KEY")
if current_key == NEW_CLAUDE_KEY:
    print("   ✅ ")
else:
    print(f"   ⚠️  ")
    print(f"   : {current_key[:20] if current_key else 'None'}...")

print("\n" + "=" * 60)
print("✅ Claude API ")
print("=" * 60)

# 6. 
print("\n:")
print("1.  Cursor  Claude API ")
print("2.  Cursor ")
print("3.  Claude Sonnet 4.5")
print("4. ， Anthropic ")





