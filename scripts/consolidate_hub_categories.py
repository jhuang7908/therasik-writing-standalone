#!/usr/bin/env python3

"""Apply 8-channel balance + junk filter to us-chinese-life-hub.html."""

from __future__ import annotations



import argparse

import json

import re

from collections import Counter

from pathlib import Path



from hub_modules_ssot import HUB_MODULES, LEGACY_MODULE_MAP, enrich_hub_item_dates, normalize_hub_items



ROOT = Path(__file__).resolve().parents[1]

HUB = ROOT / "insynbio-web-source" / "us-chinese-life-hub.html"

N_CHANNELS = len(HUB_MODULES)





def _load_items_from_html(html: str) -> list[dict]:

    return json.loads(re.search(r"const ITEMS = (\[.*?\]);", html, re.S).group(1))





def _replace_modules(html: str) -> str:

    payload = json.dumps(HUB_MODULES, ensure_ascii=False, separators=(",", ":"))

    return re.sub(r"const MODULES = \[.*?\];", f"const MODULES = {payload};", html, count=1, flags=re.S)





def _replace_items(html: str, items: list[dict]) -> str:

    payload = json.dumps(items, ensure_ascii=False, separators=(",", ":"))

    return re.sub(

        r"const ITEMS = \[.*?\];\n\nconst UI_STRINGS",

        f"const ITEMS = {payload};\n\nconst UI_STRINGS",

        html,

        count=1,

        flags=re.S,

    )





def _patch_ui_strings(html: str) -> str:

    for old in ("11", "5", "4"):

        html = html.replace(f"{old}大民生频道", f"{N_CHANNELS}大民生频道")

        html = html.replace(f"{old}大民生頻道", f"{N_CHANNELS}大民生頻道")

    html = html.replace("11 Public Channels", f"{N_CHANNELS} Public Channels")

    html = html.replace("5 Public Channels", f"{N_CHANNELS} Public Channels")

    html = html.replace("4 Public Channels", f"{N_CHANNELS} Public Channels")

    html = re.sub(

        r"📂 \d+大民生频道 · 按类别浏览",

        f"📂 {N_CHANNELS}大民生频道 · 按类别浏览",

        html,

    )

    html = re.sub(

        r'"channels_title": "1️⃣ \d+大民生频道"',

        f'"channels_title": "1️⃣ {N_CHANNELS}大民生频道"',

        html,

    )

    html = re.sub(

        r'"channels_title": "1️⃣ \d+大民生頻道"',

        f'"channels_title": "1️⃣ {N_CHANNELS}大民生頻道"',

        html,

    )

    html = re.sub(

        r'"channels_title": "1️⃣ \d+ Public Channels"',

        f'"channels_title": "1️⃣ {N_CHANNELS} Public Channels"',

        html,

    )

    return html





def _patch_legacy_map(html: str) -> str:

    pairs = ",\n  ".join(f'"{k}":"{v}"' for k, v in LEGACY_MODULE_MAP.items())

    block = f"const LEGACY_MODULE_MAP = {{\n  {pairs}\n}};"

    return re.sub(r"const LEGACY_MODULE_MAP = \{.*?\};", block, html, count=1, flags=re.S)





def _patch_interest_chips(html: str) -> str:

    chips = """const INTEREST_CHIPS = [

  { id: "亲子·公园", label: "👶 亲子/公园" },

  { id: "健身·户外", label: "🏃 健身/户外" },

  { id: "文化·节庆", label: "🎭 文化/节庆" },

  { id: "语言·教育", label: "📚 语言/教育" },

  { id: "就业·培训", label: "💼 就业/培训" },

  { id: "福利·政务", label: "🏥 福利/政务" },

  { id: "交通·安全", label: "🚇 交通/安全" },

  { id: "公益·义工", label: "🤝 义工机会" },

];"""

    return re.sub(r"const INTEREST_CHIPS = \[.*?\];", chips, html, count=1, flags=re.S)





def main() -> int:

    ap = argparse.ArgumentParser()

    ap.add_argument("--hub", type=Path, default=HUB)

    ap.add_argument("--merge-live", type=Path, help="Optional live_update JSON to merge items from")

    args = ap.parse_args()



    html = args.hub.read_text(encoding="utf-8")

    items = _load_items_from_html(html)



    if args.merge_live and args.merge_live.is_file():

        live = json.loads(args.merge_live.read_text(encoding="utf-8"))

        live_items = live.get("items") or []

        seen = {(i.get("url") or "").rstrip("/") for i in items}

        for it in live_items:

            u = (it.get("url") or "").rstrip("/")

            if u and u not in seen:

                items.append(it)

                seen.add(u)



    before = len(items)

    items = normalize_hub_items(items)
    items = [enrich_hub_item_dates(it) for it in items]

    for idx, it in enumerate(items, 1):

        it["id"] = f"live_{idx:03d}"



    html = _replace_modules(html)

    html = _replace_items(html, items)

    html = _patch_ui_strings(html)

    html = _patch_legacy_map(html)

    html = _patch_interest_chips(html)

    args.hub.write_text(html, encoding="utf-8")



    c = Counter(i["module"] for i in items)

    print(f"Items: {before} -> {len(items)} after junk filter + remap")

    for mod in HUB_MODULES:

        print(f"  {mod['zh']:8} {c.get(mod['zh'], 0)}")

    return 0





if __name__ == "__main__":

    raise SystemExit(main())

