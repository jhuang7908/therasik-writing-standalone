#!/usr/bin/env python3
"""
Seed Module 4 literature + patent library demo instances, then verify counts.

Usage:
  python scripts/seed_intelligence_demo_libraries.py --base https://write.insynbio.com
  python scripts/seed_intelligence_demo_libraries.py --base http://localhost:8787 --project-id my_demo
"""
from __future__ import annotations

import argparse
import json
import sys
import textwrap
from datetime import datetime, timezone
from pathlib import Path
from typing import Any
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen

# Curated smoke / demo cohort (antibody engineering themes)
LIT_QUERIES = [
    "trastuzumab HER2 antibody humanization",
    "bispecific antibody T cell engager",
    "nanobody VHH alpaca",
]

PAT_QUERIES = [
    "HER2 antibody trastuzumab",
    "bispecific antibody linker",
    "nanobody single domain",
]

# Fallback when ODP search returns no saveable rows (still valid USPTO apps)
PAT_FALLBACK_QUERIES = ["HER2 antibody", "bispecific antibody"]

DEMO_RIS = textwrap.dedent("""\
    TY  - JOUR
    TI  - Demo reference: antibody developability checklist (imported RIS)
    AU  - InSynBio Demo Team
    JO  - Internal Methods Note
    PY  - 2025/
    DO  - 10.5555/demo.insynbio.m4
    AB  - Seeded entry for Module 4 literature database smoke and UI walkthrough.
    ER  -
""")


def _post(base: str, path: str, body: dict, timeout: int = 120) -> tuple[bool, dict[str, Any] | None, str]:
    url = base.rstrip("/") + path
    data = json.dumps(body).encode("utf-8")
    req = Request(url, data=data, method="POST", headers={"Content-Type": "application/json"})
    try:
        with urlopen(req, timeout=timeout) as resp:
            raw = resp.read().decode("utf-8", errors="replace")
            return True, json.loads(raw) if raw else {}, ""
    except HTTPError as e:
        return False, None, f"HTTP {e.code}: {e.read().decode('utf-8', errors='replace')[:400]}"
    except URLError as e:
        return False, None, str(e.reason)
    except Exception as e:
        return False, None, str(e)


def _get(base: str, path: str, timeout: int = 60) -> tuple[bool, dict[str, Any] | None, str]:
    url = base.rstrip("/") + path
    req = Request(url, method="GET")
    try:
        with urlopen(req, timeout=timeout) as resp:
            raw = resp.read().decode("utf-8", errors="replace")
            return True, json.loads(raw) if raw else {}, ""
    except HTTPError as e:
        return False, None, f"HTTP {e.code}: {e.read().decode('utf-8', errors='replace')[:400]}"
    except URLError as e:
        return False, None, str(e.reason)
    except Exception as e:
        return False, None, str(e)


def seed_literature(base: str, user: str, pid: str, per_query: int) -> dict[str, Any]:
    saved: list[dict[str, Any]] = []
    errors: list[str] = []
    for q in LIT_QUERIES:
        ok, d, err = _post(base, "/library/openalex/search", {
            "username": user, "query": q, "per_page": per_query,
        })
        if not ok:
            errors.append(f"search '{q}': {err}")
            continue
        for w in (d or {}).get("works") or []:
            ok2, res, err2 = _post(base, "/intelligence/library/save", {
                "username": user, "project_id": pid, "source": "openalex", "item": w,
            })
            if ok2:
                saved.append({
                    "id": res.get("id"),
                    "title": (w.get("title") or "")[:80],
                    "doi": w.get("doi"),
                    "inserted": res.get("inserted"),
                    "query": q,
                })
            else:
                errors.append(f"save '{w.get('title','')[:40]}': {err2}")

    ok, d, err = _post(base, "/intelligence/library/import", {
        "username": user, "project_id": pid, "format": "ris", "content": DEMO_RIS,
    })
    ris_ok = ok and (d or {}).get("parsed", 0) >= 1
    if not ris_ok:
        errors.append(f"ris import: {err}")

    return {"saved_openalex": len(saved), "items": saved, "ris_import": ris_ok, "errors": errors}


def _save_patent_hit(
    base: str, user: str, pid: str, p: dict[str, Any], q: str,
    saved: list[dict[str, Any]], errors: list[str], seen: set[str],
) -> None:
    pid_num = str(p.get("patent_id") or "").strip()
    if not pid_num or pid_num in seen:
        return
    if p.get("source") == "portal_link" and not pid_num:
        return
    ok2, res, err2 = _post(base, "/intelligence/library/save", {
        "username": user, "project_id": pid, "source": "patent", "item": p,
    })
    if ok2:
        seen.add(pid_num)
        saved.append({
            "id": (res or {}).get("id"),
            "title": (p.get("title") or "")[:80],
            "patent_id": pid_num,
            "inserted": (res or {}).get("inserted"),
            "query": q,
        })
    else:
        errors.append(f"save patent {pid_num}: {err2}")


def seed_patents(base: str, user: str, pid: str, per_query: int) -> dict[str, Any]:
    saved: list[dict[str, Any]] = []
    errors: list[str] = []
    seen: set[str] = set()
    queries = list(PAT_QUERIES)
    for q in queries:
        ok, d, err = _post(base, "/ip/patent/search", {
            "username": user, "query": q, "limit": per_query,
        })
        if not ok:
            errors.append(f"patent search '{q}': {err}")
            continue
        patents = (d or {}).get("patents") or []
        if not patents:
            errors.append(f"patent search '{q}': empty results")
        for p in patents:
            _save_patent_hit(base, user, pid, p, q, saved, errors, seen)

    if len(saved) < 2:
        for q in PAT_FALLBACK_QUERIES:
            ok, d, err = _post(base, "/ip/patent/search", {
                "username": user, "query": q, "limit": max(per_query, 4),
            })
            if not ok:
                errors.append(f"fallback search '{q}': {err}")
                continue
            for p in (d or {}).get("patents") or []:
                _save_patent_hit(base, user, pid, p, f"fallback:{q}", saved, errors, seen)
            if len(saved) >= 3:
                break

    return {"saved_patents": len(saved), "items": saved, "errors": errors}


def _infer_subproject(item: dict[str, Any], source: str) -> str | None:
    """Map demo rows to 亚项目 labels for UI filter walkthrough."""
    blob = " ".join(
        str(x or "")
        for x in (
            item.get("query"),
            item.get("title"),
            item.get("abstract"),
            item.get("patent_id"),
        )
    ).lower()
    if source == "patent":
        if "her2" in blob or "trastuzumab" in blob:
            return "HER2-FTO"
        if "bispecific" in blob or "t cell" in blob or "engager" in blob:
            return "bispecific-FTO"
        if "nanobody" in blob or "vhh" in blob or "single domain" in blob:
            return "VHH-FTO"
        return "IP-general"
    if "her2" in blob or "trastuzumab" in blob or "humanization" in blob:
        return "HER2-humanization"
    if "bispecific" in blob or "engager" in blob:
        return "bispecific-TCE"
    if "nanobody" in blob or "vhh" in blob or "alpaca" in blob:
        return "VHH-nanobody"
    if "developability" in blob or "demo reference" in blob:
        return "methods-benchmark"
    return None


def apply_demo_subprojects(base: str, user: str, pid: str, lit: dict, pat: dict) -> dict[str, Any]:
    """Tag saved demo rows into subprojects via /intelligence/library/tag."""
    buckets: dict[str, list[int]] = {}
    for block, src in ((lit, "openalex"), (lit, "manual"), (pat, "patent")):
        for it in block.get("items") or []:
            doc_id = it.get("id")
            if not doc_id:
                continue
            sp = _infer_subproject(it, src)
            if not sp:
                continue
            buckets.setdefault(sp, []).append(int(doc_id))

    tagged: dict[str, int] = {}
    errors: list[str] = []
    for sp, ids in buckets.items():
        ok, d, err = _post(base, "/intelligence/library/tag", {
            "username": user,
            "project_id": pid,
            "document_ids": ids,
            "subproject": sp,
        })
        if ok:
            tagged[sp] = int((d or {}).get("updated") or len(ids))
        else:
            errors.append(f"tag {sp}: {err}")

    ok, d, _ = _get(base, f"/intelligence/library/subprojects?project_id={pid}")
    labels = (d or {}).get("subprojects") if ok else []
    return {"tagged": tagged, "subprojects": labels, "errors": errors}


def library_counts(base: str, user: str, pid: str) -> dict[str, Any]:
    out: dict[str, Any] = {}
    for src in ("openalex", "manual", "patent", "sequence", None):
        qs = f"username={user}&project_id={pid}&limit=500"
        if src:
            qs += f"&source={src}"
        ok, d, err = _get(base, f"/intelligence/library/list?{qs}")
        key = src or "all"
        out[key] = {
            "ok": ok,
            "count": len((d or {}).get("documents") or []),
            "total": (d or {}).get("total_in_project"),
            "error": err if not ok else None,
        }
    return out


def main() -> int:
    ap = argparse.ArgumentParser(description="Seed Module 4 literature + patent demo libraries")
    ap.add_argument("--base", default="https://write.insynbio.com")
    ap.add_argument("--project-id", default="demo_m4_lit_pat")
    ap.add_argument("--username", default="demo_ops")
    ap.add_argument("--per-query", type=int, default=3, help="OpenAlex/patent hits saved per query")
    ap.add_argument("--sync-write", action="store_true", help="Run bidirectional Write library sync after seed")
    ap.add_argument("--out", default="", help="Write JSON manifest path")
    args = ap.parse_args()

    manifest: dict[str, Any] = {
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "base": args.base,
        "project_id": args.project_id,
        "username": args.username,
        "ui_url": f"{args.base.rstrip('/')}/intelligence",
        "instructions_en": (
            f"Set Project ID to {args.project_id}, then open Literature Database / Patent Database."
        ),
    }

    print(f"Seeding literature library (project={args.project_id}) …")
    manifest["literature"] = seed_literature(args.base, args.username, args.project_id, args.per_query)

    print(f"Seeding patent library …")
    manifest["patents"] = seed_patents(args.base, args.username, args.project_id, args.per_query)

    print("Applying 亚项目 tags to demo rows …")
    manifest["subprojects"] = apply_demo_subprojects(
        args.base, args.username, args.project_id,
        manifest["literature"], manifest["patents"],
    )

    if args.sync_write:
        print("Syncing with Write reference library …")
        ok, d, err = _post(args.base, "/intelligence/library/sync", {
            "username": args.username,
            "project_id": args.project_id,
            "direction": "both",
        })
        manifest["write_sync"] = {"ok": ok, "result": d, "error": err}

    manifest["counts"] = library_counts(args.base, args.username, args.project_id)

    lit_n = manifest["counts"].get("openalex", {}).get("count", 0) + manifest["counts"].get("manual", {}).get("count", 0)
    pat_n = manifest["counts"].get("patent", {}).get("count", 0)
    manifest["summary"] = {
        "literature_rows": lit_n,
        "patent_rows": pat_n,
        "all_rows": manifest["counts"].get("all", {}).get("count", 0),
        "seed_errors": len(manifest["literature"].get("errors", [])) + len(manifest["patents"].get("errors", [])),
    }

    print("\n--- Demo library instance ---")
    print(f"  Project ID : {args.project_id}")
    print(f"  Literature : {lit_n} rows (openalex + manual)")
    print(f"  Patents    : {pat_n} rows")
    print(f"  Total      : {manifest['summary']['all_rows']}")
    print(f"  IDE        : {manifest['ui_url']}")
    if manifest["summary"]["seed_errors"]:
        print(f"  Warnings   : {manifest['summary']['seed_errors']} seed step error(s) — see manifest")

    repo = Path(__file__).resolve().parents[3]
    docs_manifest = repo / "docs" / "operations" / "module4" / "demo_library_manifest.json"
    docs_manifest.parent.mkdir(parents=True, exist_ok=True)
    docs_manifest.write_text(json.dumps(manifest, indent=2, ensure_ascii=False), encoding="utf-8")
    print(f"\nPublished manifest: {docs_manifest.relative_to(repo)}")

    if args.out:
        Path(args.out).write_text(json.dumps(manifest, indent=2, ensure_ascii=False), encoding="utf-8")
        print(f"Wrote manifest: {args.out}")

    # Minimum bar for demo instance
    ok = lit_n >= 3 and pat_n >= 2
    return 0 if ok else 1


if __name__ == "__main__":
    sys.exit(main())
