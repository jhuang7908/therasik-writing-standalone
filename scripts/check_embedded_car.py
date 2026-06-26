"""Compare embedded CAR DATA in component-browser vs CART_LIBRARY_V3.json."""
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]

def load_embedded(html_path: Path):
    t = html_path.read_text(encoding="utf-8")
    key = "var DATA="
    i = t.find(key)
    if i < 0:
        raise SystemExit(f"No var DATA= in {html_path}")
    i += len(key)
    decoder = json.JSONDecoder()
    obj, _ = decoder.raw_decode(t[i:])
    return obj

def main():
    lib = json.loads((ROOT / "data/CAR/CART_LIBRARY_V3.json").read_text(encoding="utf-8"))
    lib_e = next(e for e in lib["elements"] if e["id"] == "EGFRvIII_VHH")
    for name, path in [
        ("insynbio component-browser", ROOT / "insynbio-web-source/component-browser.html"),
        ("therasik Therasik_Component_Browser", ROOT / "therasik-web-source/Therasik_Component_Browser.html"),
    ]:
        d = load_embedded(path)
        w_e = next(e for e in d["elements"] if e["id"] == "EGFRvIII_VHH")
        same = w_e["sequence"] == lib_e["sequence"]
        print(f"{name}:")
        print(f"  embedded len={len(w_e['sequence'])} lib len={len(lib_e['sequence'])} match={same}")
        if not same:
            print(f"  embedded tail: ...{w_e['sequence'][-30:]}")
            print(f"  lib tail:      ...{lib_e['sequence'][-30:]}")

if __name__ == "__main__":
    main()
