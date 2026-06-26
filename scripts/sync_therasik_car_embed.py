"""Replace var DATA=... in Therasik_Component_Browser.html from component_library_public.json."""
import json
from pathlib import Path
from json import JSONDecoder

ROOT = Path(__file__).resolve().parents[1]
PUB = ROOT / "docs" / "car_kb_data_public.json"
HTML = ROOT / "docs" / "Therasik_Component_Browser.html"


def main():
    data = json.loads(PUB.read_text(encoding="utf-8"))
    js = json.dumps(data, ensure_ascii=False, separators=(",", ":"))
    text = HTML.read_text(encoding="utf-8")
    key = "var DATA="
    i = text.find(key)
    if i < 0:
        raise SystemExit("var DATA= not found")
    blob_start = i + len(key)
    obj, consumed = JSONDecoder().raw_decode(text[blob_start:])
    suffix = text[blob_start + consumed :]
    new_text = text[:blob_start] + js + suffix
    HTML.write_text(new_text, encoding="utf-8")
    print("Updated", HTML.name, "embedded DATA from", PUB.name, f"({len(data['elements'])} elements)")


if __name__ == "__main__":
    main()
