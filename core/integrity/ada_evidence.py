"""
Strict ADA evidence check: displayed ADA incidence must appear in either
PubMed (title+abstract) for linked PMIDs, or in the fetched citation_url body.

Used for QA — local evidence_excerpt alone does not satisfy this gate.
"""
from __future__ import annotations

import hashlib
import json
import re
import time
import urllib.error
import urllib.request
from pathlib import Path
from typing import Any

from .validators import Finding, Severity, ValidatorRegistry

RE_PUBMED_IN_URL = re.compile(
    r"https?://(?:www\.)?pubmed\.ncbi\.nlm\.nih\.gov/(\d{5,9})/?",
    re.I,
)

# Reasonable limit for label PDFs / HTML (bytes)
_MAX_FETCH_BYTES = 5_000_000
_USER_AGENT = "InSynBio-SiteIntegrity-ADA/1.0"


def _row_pmids(row: dict[str, Any]) -> list[str]:
    out: list[str] = []
    p = row.get("pmids")
    if p is not None and not isinstance(p, list):
        try:
            out.append(str(int(float(p))))
        except (TypeError, ValueError):
            s = str(p).strip()
            if s.isdigit():
                out.append(s)
    elif isinstance(p, list):
        for x in p:
            try:
                out.append(str(int(float(x))))
            except (TypeError, ValueError):
                sx = str(x).strip()
                if sx.isdigit():
                    out.append(sx)
    url = row.get("citation_url") or ""
    if isinstance(url, str):
        for m in RE_PUBMED_IN_URL.finditer(url):
            out.append(m.group(1))
    # de-dupe preserve order
    seen: set[str] = set()
    uniq: list[str] = []
    for x in out:
        if x not in seen:
            seen.add(x)
            uniq.append(x)
    return uniq


def _needles_for_ada(ada_pct: float, ada_display: str | None) -> list[str]:
    """Strings to search (lowercase) in evidence blobs."""
    raw: list[str] = []
    if ada_display and str(ada_display).strip():
        d = str(ada_display).strip()
        raw.append(d)
        raw.append(d.replace(" ", ""))
    try:
        v = float(ada_pct)
    except (TypeError, ValueError):
        v = None
    if v is not None:
        if v == int(v):
            n = int(v)
            raw.extend(
                [
                    f"{n}%",
                    f"{n}.0%",
                    f"({n}%)",
                    f"{n} %",
                    f"{n}.0 %",
                    f"{n}percent",
                    f"{n} percent",
                ]
            )
        else:
            raw.extend(
                [
                    f"{v}%",
                    f"{v:.1f}%",
                    f"{v:.1f} %",
                    f"{v:.2f}%",
                ]
            )
    needles: list[str] = []
    seen: set[str] = set()
    for s in raw:
        low = s.lower().strip()
        if low and low not in seen:
            seen.add(low)
            needles.append(low)
    return needles


def _fetch_citation_body(
    url: str,
    timeout: int,
    cache_dir: Path | None = None,
    cache_ttl_sec: int = 7 * 24 * 3600,
) -> tuple[bytes | None, str | None]:
    if not url or not url.startswith(("http://", "https://")):
        return None, "invalid_or_empty_url"
    if cache_dir is not None:
        cache_dir.mkdir(parents=True, exist_ok=True)
        key = hashlib.sha256(url.encode("utf-8")).hexdigest()
        cpath = cache_dir / key
        if cpath.exists():
            age = time.time() - cpath.stat().st_mtime
            if age < cache_ttl_sec:
                try:
                    return cpath.read_bytes(), None
                except OSError:
                    pass
    try:
        req = urllib.request.Request(
            url,
            headers={"User-Agent": _USER_AGENT, "Accept": "*/*"},
            method="GET",
        )
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            data = resp.read(_MAX_FETCH_BYTES + 1)
        if len(data) > _MAX_FETCH_BYTES:
            data = data[:_MAX_FETCH_BYTES]
        if cache_dir is not None and data:
            try:
                cpath = cache_dir / hashlib.sha256(url.encode("utf-8")).hexdigest()
                cpath.write_bytes(data)
            except OSError:
                pass
        return data, None
    except urllib.error.HTTPError as e:
        return None, f"http_{e.code}"
    except Exception as exc:
        return None, str(exc)[:200]


def _blob_contains_any_needle(blob_lower: str, needles: list[str]) -> bool:
    return any(n in blob_lower for n in needles if n)


def validate_ada_database(
    ada_json_path: Path,
    registry: ValidatorRegistry,
    repo_root: Path,
) -> list[Finding]:
    """
    For each row in ada_db_data.json, require ada_display / ada_pct to appear in
    PubMed title+abstract (for row PMIDs) OR in fetched citation_url bytes/text.
    """
    if not ada_json_path.exists():
        return []

    try:
        rows = json.loads(ada_json_path.read_text(encoding="utf-8", errors="replace"))
    except Exception:
        return []

    if not isinstance(rows, list):
        return []

    all_pmids: list[str] = []
    for row in rows:
        if not isinstance(row, dict):
            continue
        all_pmids.extend(_row_pmids(row))
    registry._prefetch_pmids(list(dict.fromkeys(all_pmids)))

    findings: list[Finding] = []
    try:
        rel_file = str(ada_json_path.resolve().relative_to(repo_root.resolve()))
    except ValueError:
        rel_file = ada_json_path.name

    for idx, row in enumerate(rows):
        if not isinstance(row, dict):
            continue
        name = str(row.get("name", f"row_{idx}"))
        jpath = f"[{idx}]"
        try:
            ada_pct = float(row["ada_pct"])
        except (KeyError, TypeError, ValueError):
            continue
        ada_display = row.get("ada_display")
        needles = _needles_for_ada(ada_pct, ada_display if isinstance(ada_display, str) else None)
        if not needles:
            continue

        pmids = _row_pmids(row)
        citation_url = row.get("citation_url")
        citation_url = citation_url.strip() if isinstance(citation_url, str) else ""

        found_pubmed = False
        for pmid in pmids:
            info = registry._pubmed_cache.get(pmid)
            if not info:
                continue
            blob = (
                (info.get("title") or "")
                + " "
                + (info.get("abstract") or "")
            ).lower()
            if _blob_contains_any_needle(blob, needles):
                found_pubmed = True
                break

        found_url = False
        url_err: str | None = None
        if citation_url:
            cache_dir = repo_root / ".integrity_url_cache"
            raw, err = _fetch_citation_body(
                citation_url, registry.url_timeout, cache_dir=cache_dir
            )
            url_err = err
            if raw is not None:
                try:
                    text = raw.decode("utf-8", errors="ignore").lower()
                except Exception:
                    text = ""
                if _blob_contains_any_needle(text, needles):
                    found_url = True
                if not found_url:
                    low = raw.decode("latin-1", errors="ignore").lower()
                    if _blob_contains_any_needle(low, needles):
                        found_url = True

        if found_pubmed or found_url:
            continue

        detail_parts = [
            f"drug={name}",
            f"needles={needles[:6]}",
            f"pmids={pmids or 'none'}",
        ]
        if citation_url:
            detail_parts.append(f"citation_url={citation_url[:120]}")
        if url_err:
            detail_parts.append(f"fetch_error={url_err}")

        findings.append(
            Finding(
                check_id="ADA_VALUE_IN_EVIDENCE",
                severity=Severity.HIGH,
                entity_type="ada_row",
                value=name,
                file_path=rel_file.replace("\\", "/"),
                json_path=jpath,
                message=(
                    f"ADA value ({ada_display or ada_pct}) not found in PubMed text for linked PMIDs "
                    f"nor in fetched citation_url content."
                ),
                detail=" | ".join(detail_parts),
            )
        )

    return findings
