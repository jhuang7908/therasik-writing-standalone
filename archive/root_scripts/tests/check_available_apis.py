#!/usr/bin/env python3
"""
API
、Cursor
"""

import os
import json
from pathlib import Path

def check_env_vars:
    """API"""
    print("=" * 60)
    print("API")
    print("=" * 60)
    
    api_vars = {}
    env_vars = os.environ
    
    # API
    keywords = ['API', 'KEY', 'DEEPSEEK', 'OPENAI', 'ANTHROPIC', 'GEMINI', 'CLAUDE']
    
    for key, value in env_vars.items:
        key_upper = key.upper
        if any(kw in key_upper for kw in keywords):
            # 
            if len(value) > 20:
                display_value = value[:10] + "..." + value[-4:]
            else:
                display_value = "***" if len(value) > 5 else value
            api_vars[key] = display_value
    
    if api_vars:
        print(f" {len(api_vars)} API:")
        for key, value in api_vars.items:
            print(f"  {key}: {value}")
    else:
        print("API")
    
    return api_vars

def check_cursor_config:
    """Cursor"""
    print("\n" + "=" * 60)
    print("Cursor")
    print("=" * 60)
    
    # Cursor
    possible_paths = [
        Path.home / ".cursor" / "settings.json",
        Path.home / ".cursor" / "config.json",
        Path.home / "AppData" / "Roaming" / "Cursor" / "User" / "settings.json",
        Path.home / "Library" / "Application Support" / "Cursor" / "User" / "settings.json",
    ]
    
    found_configs = []
    for path in possible_paths:
        if path.exists:
            found_configs.append(path)
            print(f": {path}")
            try:
                with open(path, 'r', encoding='utf-8') as f:
                    config = json.load(f)
                    # API
                    if isinstance(config, dict):
                        api_keys = {k: "***" if "key" in k.lower or "secret" in k.lower else v 
                                   for k, v in config.items 
                                   if any(kw in k.upper for kw in ['API', 'KEY', 'MODEL', 'DEEPSEEK', 'OPENAI'])}
                        if api_keys:
                            print(f"  API: {list(api_keys.keys)}")
            except Exception as e:
                print(f"  : {e}")
    
    if not found_configs:
        print("Cursor（，Cursor）")
    
    return found_configs

def check_project_config:
    """API"""
    print("\n" + "=" * 60)
    print("")
    print("=" * 60)
    
    project_root = Path(__file__).parent
    config_file = project_root / "config.yaml"
    
    if config_file.exists:
        print(f": {config_file}")
        # config.yamlapi
        try:
            import yaml
            with open(config_file, 'r', encoding='utf-8') as f:
                config = yaml.safe_load(f)
                if 'api' in config:
                    print(f"  API: {config['api']}")
        except Exception as e:
            print(f"  YAML: {e}")
    else:
        print("API")

def generate_api_check_report:
    """API"""
    print("\n" + "=" * 60)
    print("API")
    print("=" * 60)
    
    # API
    apis_to_check = {
        "DeepSeek": {
            "endpoint": "https://api.deepseek.com/v1",
            "test_url": "https://api.deepseek.com/v1/models",
            "docs": "https://platform.deepseek.com/",
        },
        "OpenAI": {
            "endpoint": "https://api.openai.com/v1",
            "test_url": "https://api.openai.com/v1/models",
            "docs": "https://platform.openai.com/",
        },
        "Anthropic (Claude)": {
            "endpoint": "https://api.anthropic.com/v1",
            "test_url": "https://api.anthropic.com/v1/messages",
            "docs": "https://console.anthropic.com/",
        },
        "Google Gemini": {
            "endpoint": "https://generativelanguage.googleapis.com/v1",
            "test_url": "https://generativelanguage.googleapis.com/v1/models",
            "docs": "https://makersuite.google.com/app/apikey",
        },
    }
    
    print("\nAPI:")
    print("-" * 60)
    for name, info in apis_to_check.items:
        print(f"\n{name}:")
        print(f"  API: {info['endpoint']}")
        print(f"  : {info['docs']}")
        print(f"  : API")
    
    print("\n" + "=" * 60)
    print(":")
    print("=" * 60)
    print("1. CursorAPI")
    print("2. DeepSeek API（，）")
    print("3. ")
    print("4. APICursor")

if __name__ == "__main__":
    print("\n" + "=" * 60)
    print("API")
    print("=" * 60)
    
    env_vars = check_env_vars
    cursor_configs = check_cursor_config
    check_project_config
    generate_api_check_report
    
    print("\n" + "=" * 60)
    print("")
    print("=" * 60)







