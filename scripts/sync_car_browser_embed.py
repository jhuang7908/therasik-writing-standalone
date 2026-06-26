"""
Replace inline `var DATA=...` in CAR component browser HTML from component_library_public.json.
"""
from __future__ import annotations

import json
from json import JSONDecoder
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
PUB = ROOT / "docs" / "car_kb_data_public.json"


def inject(html_path: Path, data: dict) -> None:
    t = html_path.read_text(encoding="utf-8")
    key = "var DATA="
    i = t.find(key)
    if i < 0:
        raise SystemExit(f"{html_path}: missing {key!r}")
    i += len(key)
    _, end = JSONDecoder().raw_decode(t[i:])
    data_js = json.dumps(data, ensure_ascii=False, separators=(",", ":"))
    new_t = t[:i] + data_js + t[i + end :]
    html_path.write_text(new_t, encoding="utf-8")
    print(f"Updated {html_path.name} ({len(new_t) // 1024} KB)")


def main() -> None:
    data = json.loads(PUB.read_text(encoding="utf-8"))
    # insynbio: run insynbio-web-source/_gen_browser.py first (full template regen)
    inject(ROOT / "therasik-web-source" / "Therasik_Component_Browser.html", data)
    docs = ROOT / "docs" / "component-browser.html"
    if docs.exists():
        inject(docs, data)
    docs_t = ROOT / "docs" / "Therasik_Component_Browser.html"
    if docs_t.exists():
        inject(docs_t, data)


if __name__ == "__main__":
    main()
