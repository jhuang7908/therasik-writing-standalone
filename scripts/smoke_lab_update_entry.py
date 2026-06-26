#!/usr/bin/env python3
from __future__ import annotations

import json
import requests

BASE = "https://write.insynbio.com"


def post(path: str, payload: dict):
    r = requests.post(BASE + path, json=payload, timeout=40)
    try:
        d = r.json()
    except Exception:
        d = {"raw": r.text}
    return r.status_code, d


def main() -> int:
    title = "SMOKE EDIT DEMO RECORD"
    create_body = "<h3>Objective / Hypothesis</h3><p>Before edit.</p>"
    c1, d1 = post("/lab/create_entry", {"entity": "experiments", "title": title, "body": create_body, "tags": ["Smoke", "Edit"]})
    if c1 != 200 or "id" not in d1:
        print(json.dumps({"ok": False, "step": "create", "status": c1, "body": d1}, ensure_ascii=False, indent=2))
        return 2
    rid = str(d1["id"])

    c2, d2 = post(
        "/lab/update_entry",
        {
            "entity": "experiments",
            "id": rid,
            "title": title + " UPDATED",
            "body": "<h3>Objective / Hypothesis</h3><p>After edit.</p>",
            "tags": ["Smoke", "Edit", "Updated"],
        },
    )
    if c2 != 200:
        print(json.dumps({"ok": False, "step": "update", "id": rid, "status": c2, "body": d2}, ensure_ascii=False, indent=2))
        post("/lab/delete_entry", {"entity": "experiments", "id": rid})
        return 2

    c3, d3 = post("/lab/get_entry", {"entity": "experiments", "id": rid})
    ok = c3 == 200 and isinstance(d3, dict) and "UPDATED" in str(d3.get("title", "")) and "After edit" in str(d3.get("body", ""))

    post("/lab/delete_entry", {"entity": "experiments", "id": rid})
    print(json.dumps({"ok": bool(ok), "id": rid, "title": d3.get("title"), "status_get": c3}, ensure_ascii=False, indent=2))
    return 0 if ok else 1


if __name__ == "__main__":
    raise SystemExit(main())
