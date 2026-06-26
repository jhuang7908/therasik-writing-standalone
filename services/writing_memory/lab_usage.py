import json
import os
import math
from pathlib import Path

USAGE_FILE = Path("data/lab_usage.json")

def record_usage(model: str, input_tokens: int, output_tokens: int):
    # Prices per 1M tokens in USD
    prices = {
        "deepseek-chat": (0.14, 0.28),
        "deepseek-reasoner": (0.55, 2.19),
        "claude-3-5-sonnet-20241022": (3.00, 15.00),
        "claude-3-5-haiku-20241022": (1.00, 5.00),
        "gpt-4o": (5.00, 15.00),
        "gpt-4o-mini": (0.15, 0.60),
    }
    inp_p, out_p = prices.get(model, (1.00, 5.00))
    cost_usd = (input_tokens * inp_p / 1e6) + (output_tokens * out_p / 1e6)
    
    # Determine multiplier based on provider
    if "deepseek" in model.lower():
        multiplier = 4
    elif "claude" in model.lower():
        multiplier = 3
    elif "gpt" in model.lower() or "o1-" in model.lower() or "o3-" in model.lower():
        multiplier = 3
    else:
        multiplier = 3
        
    # Calculate credits. Let's say 1 USD = 10000 base credits.
    credits_used = int(math.ceil(cost_usd * multiplier * 10000))
    
    USAGE_FILE.parent.mkdir(parents=True, exist_ok=True)
    
    data = {"available": 100000, "usage": 0}
    if USAGE_FILE.exists():
        try:
            data = json.loads(USAGE_FILE.read_text(encoding="utf-8"))
        except Exception:
            pass
            
    data["usage"] = data.get("usage", 0) + credits_used
    data["available"] = max(0, data.get("available", 100000) - credits_used)
    
    USAGE_FILE.write_text(json.dumps(data, indent=2), encoding="utf-8")

def get_usage_stats():
    if USAGE_FILE.exists():
        try:
            return json.loads(USAGE_FILE.read_text(encoding="utf-8"))
        except Exception:
            pass
    return {"available": 100000, "usage": 0}
