#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
DeepSeek ：
1)  deepseek_client.py（ pip install openai）
2)  openai ， quick_test.py HTTP
"""

import os
import sys


def run_sdk_test -> int:
    try:
        from deepseek_client import AntibodyDeepSeekClient  # noqa: F401
    except Exception as e:
        print("ℹ️   deepseek_client（ openai Python）")
        print("   ：", repr(e))
        return 3

    api_key = os.environ.get("DEEPSEEK_API_KEY")
    if not api_key:
        print("❌  DEEPSEEK_API_KEY")
        return 2

    client = AntibodyDeepSeekClient(api_key)
    v = client.validate_api_key
    if not v.get("valid"):
        print("❌ API ：", v.get("error"))
        return 1

    print("✅ SDK ：", v.get("message"))
    return 0


def run_http_fallback -> int:
    try:
        import quick_test
        return quick_test.main
    except Exception as e:
        print("❌ HTTP：", repr(e))
        return 1


def main -> int:
    code = run_sdk_test
    if code == 0:
        return 0
    print("\n➡️  HTTP...\n")
    return run_http_fallback


if __name__ == "__main__":
    raise SystemExit(main)

