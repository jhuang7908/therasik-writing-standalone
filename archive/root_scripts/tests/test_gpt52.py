#!/usr/bin/env python3
"""
GPT-5.2
"""

import os
from openai import OpenAI

def test_gpt52:
    """GPT-5.2"""
    print("=" * 60)
    print("GPT-5.2 ")
    print("=" * 60)
    
    api_key = os.environ.get("OPENAI_API_KEY")
    if not api_key:
        print("❌ API")
        return
    
    client = OpenAI(api_key=api_key)
    
    # GPT-5.2
    gpt52_models = [
        "gpt-5.2",
        "gpt-5.2-2025-12-11",
        "gpt-5.2-chat-latest",
        "gpt-5.2-pro",
        "gpt-5.2-pro-2025-12-11"
    ]
    
    print("\nGPT-5.2...")
    print("-" * 60)
    
    # 
    test_model = "gpt-5.2"
    print(f"\n: {test_model}")
    
    try:
        response = client.chat.completions.create(
            model=test_model,
            messages=[
                {
                    "role": "user", 
                    "content": "GPT-5.2，''。"
                }
            ],
            max_completion_tokens=50,
            temperature=0.7
        )
        
        print(f"✅ {test_model} !")
        print(f"   : {response.choices[0].message.content}")
        print(f"   tokens: {response.usage.total_tokens}")
        print(f"   tokens: {response.usage.prompt_tokens}")
        print(f"   tokens: {response.usage.completion_tokens}")
        
        return True
        
    except Exception as e:
        print(f"❌ {test_model} : {e}")
        
        # 
        print("\nGPT-5.2...")
        for model in gpt52_models[1:]:
            try:
                print(f"\n: {model}")
                response = client.chat.completions.create(
                    model=model,
                    messages=[
                        {"role": "user", "content": "Hello, test."}
                    ],
                    max_completion_tokens=20
                )
                print(f"✅ {model} !")
                print(f"   : {response.choices[0].message.content}")
                return True
            except Exception as e2:
                print(f"   ❌ {model} : {str(e2)[:100]}")
        
        return False

if __name__ == "__main__":
    result = test_gpt52
    
    print("\n" + "=" * 60)
    if result:
        print("✅ GPT-5.2  - Cursor!")
    else:
        print("⚠️  GPT-5.2 ")
    print("=" * 60)

