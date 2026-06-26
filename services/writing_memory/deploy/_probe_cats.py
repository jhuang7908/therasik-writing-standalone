"""Probe eLabFTW classification: resource categories (items_types) and whether
this token can create them. Creates a temp category then deletes it. Token never printed.
"""
import json
import urllib.request
import urllib.error

ENV_PATH = "/srv/services/writing_memory/.env"


def load_env():
    cfg = {}
    with open(ENV_PATH, encoding="utf-8") as fh:
        for line in fh:
            line = line.strip()
            if not line or line.startswith("#") or "=" not in line:
                continue
            k, _, v = line.partition("=")
            cfg[k.strip()] = v.strip()
    return cfg


def call(base, token, path, method="GET", payload=None):
    url = base.rstrip("/") + path
    data = json.dumps(payload).encode() if payload is not None else None
    req = urllib.request.Request(url, data=data, method=method,
                                 headers={"Authorization": token, "Accept": "application/json",
                                          "Content-Type": "application/json"})
    try:
        with urllib.request.urlopen(req, timeout=25) as r:
            return r.status, r.headers.get("Location", ""), r.read().decode("utf-8", "replace")
    except urllib.error.HTTPError as e:
        return e.code, "", e.read().decode("utf-8", "replace")
    except Exception as e:  # noqa: BLE001
        return -1, "", str(e)


def main():
    cfg = load_env()
    base = cfg.get("ELABFTW_BASE_URL", "")
    token = cfg.get("ELABFTW_API_TOKEN", "")

    st, _, body = call(base, token, "/api/v2/items_types")
    print(f"GET items_types -> HTTP {st}")
    try:
        data = json.loads(body)
        print("count:", len(data) if isinstance(data, list) else "n/a")
        if isinstance(data, list):
            for t in data:
                print("  id=", t.get("id"), "title=", t.get("title"), "color=", t.get("color"))
    except Exception:
        print(body[:400])

    # Try to create a temp category to test write permission
    st, loc, body = call(base, token, "/api/v2/items_types", method="POST",
                         payload={"title": "__probe_tmp__"})
    print(f"\nPOST items_types -> HTTP {st} Location={loc}")
    if st not in (200, 201):
        print("create not permitted / body:", body[:300])
        return
    new_id = loc.rstrip("/").split("/")[-1] if loc else ""
    print("created temp category id:", new_id)
    if new_id:
        st2, _, _ = call(base, token, f"/api/v2/items_types/{new_id}", method="DELETE")
        print(f"DELETE temp category -> HTTP {st2}")


if __name__ == "__main__":
    main()
