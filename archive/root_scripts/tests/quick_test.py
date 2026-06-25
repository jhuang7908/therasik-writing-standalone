#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
DeepSeek API （， openai ）

（PowerShell）：
  $env:DEEPSEEK_API_KEY="sk-xxxxx"
  python .\quick_test.py
"""

import json
import os
import sys
import urllib.request
import urllib.error


def main -> int:
    api_key = os.environ.get("DEEPSEEK_API_KEY")
    if not api_key:
        print("❌  DEEPSEEK_API_KEY")
        return 2

    url = "https://api.deepseek.com/v1/chat/completions"
    payload = {
        "model": "deepseek-chat",
        "messages": [{"role": "user", "content": "， OK"}],
        "max_tokens": 20,
    }
    headers = {
        "Authorization": f"Bearer {api_key}",
        "Content-Type": "application/json",
    }

    req = urllib.request.Request(
        url=url,
        data=json.dumps(payload).encode("utf-8"),
        headers=headers,
        method="POST",
    )

    try:
        with urllib.request.urlopen(req, timeout=30) as resp:
            body = resp.read.decode("utf-8")
        data = json.loads(body)
        msg = data["choices"][0]["message"]["content"]
        print("✅ DeepSeek API ")
        print("：", msg)
        return 0
    except urllib.error.HTTPError as e:
        detail = e.read.decode("utf-8", errors="replace") if e.fp else ""
        print(f"❌ HTTP {e.code}: {e.reason}")
        if detail:
            print(detail)
        return 1
    except Exception as e:
        print("❌ ：", repr(e))
        return 1


if __name__ == "__main__":
    raise SystemExit(main)

