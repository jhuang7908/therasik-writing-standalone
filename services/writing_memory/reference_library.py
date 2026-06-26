"""
Per-account reference library store.

Each logged-in account gets its own isolated library at:
  data/reference_libraries/<username>/library.jsonl

Entries follow a standard schema for metadata, full-text status, and project binding.
"""

from __future__ import annotations

import json
import re
import os
import xml.etree.ElementTree as ET
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Optional
from pydantic import BaseModel, Field
import anthropic
import requests

_HERE = Path(__file__).resolve().parent
_ROOT = Path(__import__("os").environ.get("WM_REF_LIBRARY_DIR", 
                                           str(_HERE / "data" / "reference_libraries")))

# Default model for metadata extraction
DEFAULT_MODEL = os.environ.get("ANTHROPIC_MODEL", "claude-3-5-sonnet-20240620")

class ReferenceEntry(BaseModel):
    id: str = Field(..., description="Unique ID (typically PMID, DOI slug, or UUID)")
    title: str
    authors: str
    year: Optional[int] = None
    journal: Optional[str] = None
    volume: Optional[str] = None
    issue: Optional[str] = None
    pages: Optional[str] = None
    doi: Optional[str] = None
    pmid: Optional[str] = None
    pmcid: Optional[str] = None
    abstract: Optional[str] = None
    full_text_status: str = Field("metadata", description="metadata | abstract | fulltext")
    full_text_path: Optional[str] = None
    source: str = Field("manual", description="manual | pubmed | upload | zotero")
    project_ids: list[str] = Field(default_factory=list)
    tags: list[str] = Field(default_factory=list)
    notes: Optional[str] = None
    evidence_chunks: list[dict[str, Any]] = Field(default_factory=list)
    added_at: str = Field(default_factory=lambda: datetime.now(timezone.utc).isoformat())
    updated_at: str = Field(default_factory=lambda: datetime.now(timezone.utc).isoformat())

def _now() -> str:
    return datetime.now(timezone.utc).isoformat()

def _user_dir(username: str) -> Path:
    safe = re.sub(r"[^\w\-]", "_", username)[:64]
    d = _ROOT / safe
    d.mkdir(parents=True, exist_ok=True)
    return d

def _pdfs_dir(username: str) -> Path:
    d = _user_dir(username) / "pdfs"
    d.mkdir(parents=True, exist_ok=True)
    return d

def _settings_path(username: str) -> Path:
    return _user_dir(username) / "settings.json"

def load_settings(username: str) -> dict[str, Any]:
    path = _settings_path(username)
    if path.exists():
        try:
            return json.loads(path.read_text(encoding="utf-8"))
        except Exception:
            pass
    return {
        "oa_download_consent": "none", # none | project | account
        "auto_verify_pmid": True,
        "zotero_user_id": "",
        "zotero_api_key": "",
        "zotero_collection_key": "",
        "zotero_oauth_token": "",
        "zotero_oauth_token_secret": "",
        "zotero_oauth_pending_token": "",
        "zotero_oauth_pending_secret": "",
        "zotero_sync_log": [],
    }

def save_settings(username: str, settings: dict[str, Any]):
    merged = load_settings(username)
    merged.update(settings or {})
    path = _settings_path(username)
    path.write_text(json.dumps(merged, indent=2), encoding="utf-8")


def append_zotero_sync_log(username: str, record: dict[str, Any], max_keep: int = 20) -> None:
    s = load_settings(username)
    logs = list(s.get("zotero_sync_log") or [])
    logs.insert(0, {"at": _now(), **(record or {})})
    s["zotero_sync_log"] = logs[:max_keep]
    save_settings(username, s)

def _library_path(username: str) -> Path:
    return _user_dir(username) / "library.jsonl"


def _doi_from_extra(extra: str | None) -> str | None:
    if not extra:
        return None
    m = re.search(r"\b10\.\d{4,9}/[-._;()/:A-Za-z0-9]+\b", extra)
    return m.group(0) if m else None


def _pmid_from_extra(extra: str | None) -> str | None:
    if not extra:
        return None
    m = re.search(r"PMID:\s*(\d+)", extra, re.IGNORECASE)
    return m.group(1) if m else None

def load_library(username: str) -> list[ReferenceEntry]:
    path = _library_path(username)
    if not path.exists():
        return []
    
    entries = []
    with path.open("r", encoding="utf-8") as f:
        for line in f:
            if not line.strip():
                continue
            try:
                entries.append(ReferenceEntry.parse_raw(line))
            except Exception:
                continue
    return entries

def save_library(username: str, entries: list[ReferenceEntry]):
    path = _library_path(username)
    with path.open("w", encoding="utf-8") as f:
        for entry in entries:
            f.write(entry.json() + "\n")

def add_or_update_reference(username: str, entry_data: dict[str, Any]) -> ReferenceEntry:
    library = load_library(username)
    
    # Identify by ID, PMID, or DOI
    eid = entry_data.get("id") or entry_data.get("pmid") or entry_data.get("doi")
    if not eid:
        import uuid
        eid = str(uuid.uuid4())
    
    existing = next((e for e in library if e.id == eid or (e.pmid and e.pmid == entry_data.get("pmid")) or (e.doi and e.doi == entry_data.get("doi"))), None)
    
    if existing:
        # Update existing
        update_dict = existing.dict()
        for k, v in entry_data.items():
            if k == "project_ids":
                # Merge project IDs
                new_projects = set(update_dict.get("project_ids") or [])
                new_projects.update(v or [])
                update_dict["project_ids"] = list(new_projects)
            elif k == "tags":
                new_tags = set(update_dict.get("tags") or [])
                new_tags.update(v or [])
                update_dict["tags"] = list(new_tags)
            else:
                update_dict[k] = v
        
        update_dict["updated_at"] = _now()
        new_entry = ReferenceEntry(**update_dict)
        # Replace in list
        library = [new_entry if e.id == existing.id else e for e in library]
    else:
        # Create new
        if "id" not in entry_data:
            entry_data["id"] = eid
        new_entry = ReferenceEntry(**entry_data)
        library.append(new_entry)
    
    save_library(username, library)
    return new_entry

def delete_reference(username: str, entry_id: str) -> bool:
    library = load_library(username)
    new_library = [e for e in library if e.id != entry_id]
    if len(new_library) == len(library):
        return False
    save_library(username, new_library)
    return True

def search_library(username: str, query: str, project_id: Optional[str] = None) -> list[ReferenceEntry]:
    library = load_library(username)
    query = query.lower().strip()
    
    results = []
    for e in library:
        if project_id and project_id not in e.project_ids:
            continue
            
        if not query:
            results.append(e)
            continue
            
        # Simple text search across title, authors, abstract, journal
        match = (
            query in e.title.lower() or
            query in e.authors.lower() or
            (e.abstract and query in e.abstract.lower()) or
            (e.journal and query in e.journal.lower()) or
            (e.pmid and query == e.pmid) or
            (e.doi and query in e.doi.lower())
        )
        if match:
            results.append(e)
            
    # Sort by updated_at desc
    results.sort(key=lambda x: x.updated_at, reverse=True)
    return results

# ── Phase 2: PDF Upload & Metadata Extraction ──────────────────

def extract_metadata_from_pdf(content: bytes) -> dict[str, Any]:
    """
    Extract text from PDF and use Claude to identify Title, Authors, DOI, etc.
    """
    from .pdf_text import extract_text_from_pdf_bytes

    # Prefer Grobid if configured.
    grobid_url = (os.environ.get("WM_GROBID_URL", "") or "").strip().rstrip("/")
    if grobid_url:
        try:
            files = {"input": ("paper.pdf", content, "application/pdf")}
            resp = requests.post(
                f"{grobid_url}/api/processHeaderDocument",
                data={"consolidateHeader": "1", "includeRawCitations": "0"},
                files=files,
                timeout=45,
            )
            if resp.ok and resp.text.strip():
                root = ET.fromstring(resp.text)
                ns = {"tei": "http://www.tei-c.org/ns/1.0"}
                title = root.findtext(".//tei:titleStmt/tei:title", default="", namespaces=ns).strip()
                doi = root.findtext(
                    ".//tei:idno[@type='DOI']",
                    default="",
                    namespaces=ns,
                ).strip() or None
                year_txt = root.findtext(
                    ".//tei:publicationStmt/tei:date[@type='published']",
                    default="",
                    namespaces=ns,
                ).strip()
                year = int(year_txt[:4]) if re.match(r"^\d{4}", year_txt) else None
                journal = root.findtext(
                    ".//tei:monogr/tei:title[@level='j']",
                    default="",
                    namespaces=ns,
                ).strip() or None
                author_names: list[str] = []
                for au in root.findall(".//tei:author", ns):
                    s = (au.findtext(".//tei:surname", default="", namespaces=ns) or "").strip()
                    f = (au.findtext(".//tei:forename", default="", namespaces=ns) or "").strip()
                    full = " ".join(x for x in [s, f] if x).strip()
                    if full:
                        author_names.append(full)
                if title:
                    return {
                        "title": title,
                        "authors": ", ".join(author_names) if author_names else None,
                        "year": year,
                        "journal": journal,
                        "doi": doi,
                        "pmid": None,
                        "pmcid": None,
                        "abstract": None,
                    }
        except Exception:
            # Fallback to local extraction + LLM parser
            pass

    try:
        # First 3 pages are usually enough for metadata
        text = extract_text_from_pdf_bytes(content, max_pages=3)
    except Exception as exc:
        raise ValueError(f"Could not extract text from PDF: {exc}")

    system_prompt = """You are a scientific metadata extractor.
Given the first few pages of a research paper, extract the core metadata.
Return ONLY a JSON object with these fields:
{
  "title": "<full title>",
  "authors": "<LastName A, LastName B, ...>",
  "year": <int or null>,
  "journal": "<journal name or null>",
  "doi": "<DOI string or null>",
  "pmid": "<PMID string or null>",
  "pmcid": "<PMCID string or null>",
  "abstract": "<abstract or null>"
}
Rules:
- If a field is not found, set it to null.
- Output raw JSON only — no markdown fences, no explanatory text."""

    api_key = os.environ.get("ANTHROPIC_API_KEY", "")
    if not api_key:
        raise RuntimeError("ANTHROPIC_API_KEY not configured")
    
    client = anthropic.Anthropic(api_key=api_key)
    try:
        resp = client.messages.create(
            model=DEFAULT_MODEL,
            max_tokens=1024,
            temperature=0.0,
            system=system_prompt,
            messages=[{"role": "user", "content": f"Extract metadata from this text:\n\n{text[:8000]}"}],
        )
        raw_json = getattr(resp.content[0] if resp.content else None, "text", "").strip()
    except Exception as exc:
        raise RuntimeError(f"Claude error: {exc}")

    # Strip markdown fences if present
    raw_json = re.sub(r"^```(?:json)?\s*", "", raw_json)
    raw_json = re.sub(r"\s*```$", "", raw_json)

    try:
        return json.loads(raw_json)
    except Exception:
        # Fallback: try to find JSON block
        m = re.search(r"\{.*\}", raw_json, re.DOTALL)
        if m:
            return json.loads(m.group())
        return {}

def process_pdf_upload(username: str, filename: str, content: bytes, project_id: Optional[str] = None) -> ReferenceEntry:
    """
    1. Extract metadata.
    2. Save PDF to account storage.
    3. Add/Update reference library entry.
    """
    meta = extract_metadata_from_pdf(content)
    
    # Save the file
    pdir = _pdfs_dir(username)
    import hashlib
    h = hashlib.sha256(content).hexdigest()[:16]
    safe_name = re.sub(r"[^\w\.]", "_", filename)
    storage_name = f"{h}_{safe_name}"
    path = pdir / storage_name
    path.write_bytes(content)
    
    # Prepare entry data
    entry_data = {
        **meta,
        "full_text_status": "fulltext",
        "full_text_path": str(path),
        "source": "upload",
        "project_ids": [project_id] if project_id else []
    }
    
    # If title is missing, use filename
    if not entry_data.get("title"):
        entry_data["title"] = filename
    
    # If authors missing, use "Unknown"
    if not entry_data.get("authors"):
        entry_data["authors"] = "Unknown"

    return add_or_update_reference(username, entry_data)

def download_oa_fulltext(username: str, entry_id: str) -> bool:
    """
    Try to find and download OA full-text for a reference.
    Returns True if successful.
    """
    library = load_library(username)
    entry = next((e for e in library if e.id == entry_id), None)
    if not entry or entry.full_text_status == "fulltext":
        return False
    
    pdf_url = None
    if entry.pmcid:
        # PMC direct PDF link pattern
        pdf_url = f"https://www.ncbi.nlm.nih.gov/pmc/articles/{entry.pmcid}/pdf/"
    elif entry.doi:
        try:
            from .unpaywall_client import lookup_doi, oa_fields_from_payload

            data = lookup_doi(entry.doi)
            if data and data.get("is_oa"):
                fields = oa_fields_from_payload(data)
                pdf_url = fields.get("oa_pdf_url") or fields.get("oa_url")
        except Exception:
            pass
            
    if not pdf_url:
        return False
        
    try:
        import requests
        r = requests.get(pdf_url, timeout=30, stream=True)
        if r.status_code == 200:
            pdir = _pdfs_dir(username)
            import hashlib
            h = hashlib.sha256(pdf_url.encode()).hexdigest()[:16]
            storage_name = f"oa_{h}_{entry_id}.pdf"
            path = pdir / storage_name
            with path.open("wb") as f:
                for chunk in r.iter_content(chunk_size=8192):
                    f.write(chunk)
            
            # Update entry in library
            # Need to reload to ensure we have latest and update correctly
            library = load_library(username)
            for e in library:
                if e.id == entry_id:
                    e.full_text_status = "fulltext"
                    e.full_text_path = str(path)
                    e.updated_at = _now()
                    break
            save_library(username, library)
            return True
    except Exception:
        pass
        
    return False


def import_zotero_items(
    username: str,
    zotero_user_id: str,
    zotero_api_key: str = "",
    zotero_oauth_token: str = "",
    zotero_oauth_token_secret: str = "",
    collection_key: str | None = None,
    project_id: str | None = None,
    limit: int = 50,
) -> dict[str, Any]:
    """
    Import items from Zotero user library.
    Uses Zotero Web API directly.
    """
    base = f"https://api.zotero.org/users/{zotero_user_id}/items"
    params: dict[str, Any] = {
        "limit": max(1, min(limit, 100)),
        "format": "json",
        "include": "data",
        "itemType": "-attachment || -note",
    }
    if collection_key:
        params["collection"] = collection_key
    headers = {"Zotero-API-Version": "3"}
    if zotero_api_key:
        headers["Authorization"] = f"Bearer {zotero_api_key}"
        r = requests.get(base, params=params, headers=headers, timeout=30)
    else:
        try:
            from requests_oauthlib import OAuth1Session
        except Exception as exc:
            raise RuntimeError("requests-oauthlib is required for Zotero OAuth mode") from exc
        ck = (os.environ.get("ZOTERO_CONSUMER_KEY") or "").strip()
        cs = (os.environ.get("ZOTERO_CONSUMER_SECRET") or "").strip()
        if not (ck and cs and zotero_oauth_token and zotero_oauth_token_secret):
            raise RuntimeError("Missing Zotero OAuth credentials (consumer key/secret or oauth token pair).")
        oauth = OAuth1Session(
            client_key=ck,
            client_secret=cs,
            resource_owner_key=zotero_oauth_token,
            resource_owner_secret=zotero_oauth_token_secret,
        )
        r = oauth.get(base, params=params, headers=headers, timeout=30)
    if not r.ok:
        raise RuntimeError(f"Zotero API failed: {r.status_code} {r.text[:200]}")
    rows = r.json()

    imported = 0
    for item in rows:
        data = (item or {}).get("data") or {}
        title = (data.get("title") or "").strip()
        if not title:
            continue
        creators = data.get("creators") or []
        names: list[str] = []
        for c in creators:
            family = (c.get("lastName") or "").strip()
            given = (c.get("firstName") or "").strip()
            nm = " ".join(x for x in [family, given] if x).strip() or (c.get("name") or "").strip()
            if nm:
                names.append(nm)
        date_raw = (data.get("date") or "").strip()
        year = int(date_raw[:4]) if re.match(r"^\d{4}", date_raw) else None
        doi = (data.get("DOI") or "").strip() or _doi_from_extra(data.get("extra"))
        pmid = _pmid_from_extra(data.get("extra"))

        entry_data = {
            "id": (item.get("key") or None),
            "title": title,
            "authors": ", ".join(names) if names else "Unknown",
            "year": year,
            "journal": (data.get("publicationTitle") or None),
            "volume": (data.get("volume") or None),
            "issue": (data.get("issue") or None),
            "pages": (data.get("pages") or None),
            "doi": doi,
            "pmid": pmid,
            "abstract": (data.get("abstractNote") or None),
            "source": "zotero",
            "project_ids": [project_id] if project_id else [],
            "tags": [t.get("tag", "") for t in (data.get("tags") or []) if t.get("tag")],
        }
        add_or_update_reference(username, entry_data)
        imported += 1
    return {"imported": imported, "fetched": len(rows)}


def sync_zotero_from_settings(
    username: str,
    project_id: str | None = None,
    limit: int = 50,
) -> dict[str, Any]:
    """
    Sync Zotero items using credentials stored in account settings.
    """
    s = load_settings(username)
    uid = (s.get("zotero_user_id") or "").strip()
    key = (s.get("zotero_api_key") or "").strip()
    oauth_token = (s.get("zotero_oauth_token") or "").strip()
    oauth_secret = (s.get("zotero_oauth_token_secret") or "").strip()
    col = (s.get("zotero_collection_key") or "").strip() or None
    if not uid:
        raise RuntimeError("Zotero not connected. Set Zotero user id first.")
    if not key and not (oauth_token and oauth_secret):
        raise RuntimeError("Zotero not connected. Set API key or complete OAuth connection.")
    return import_zotero_items(
        username=username,
        zotero_user_id=uid,
        zotero_api_key=key,
        zotero_oauth_token=oauth_token,
        zotero_oauth_token_secret=oauth_secret,
        collection_key=col,
        project_id=project_id,
        limit=limit,
    )


def zotero_connection_status(username: str) -> dict[str, Any]:
    s = load_settings(username)
    has_api = bool((s.get("zotero_api_key") or "").strip())
    has_oauth = bool(
        (s.get("zotero_oauth_token") or "").strip()
        and (s.get("zotero_oauth_token_secret") or "").strip()
    )
    has_uid = bool((s.get("zotero_user_id") or "").strip())
    ck = (os.environ.get("ZOTERO_CONSUMER_KEY") or "").strip()
    cs = (os.environ.get("ZOTERO_CONSUMER_SECRET") or "").strip()
    env_ok = bool(ck and cs)
    missing_env: list[str] = []
    if not ck:
        missing_env.append("ZOTERO_CONSUMER_KEY")
    if not cs:
        missing_env.append("ZOTERO_CONSUMER_SECRET")
    mode = "oauth" if has_oauth else ("api_key" if has_api else "none")
    connected = has_uid and (has_api or has_oauth)
    warnings: list[str] = []
    if has_oauth and not env_ok:
        warnings.append("OAuth tokens saved but server consumer key/secret missing.")
    if not has_uid and (has_api or has_oauth):
        warnings.append("Credentials set but Zotero user_id missing.")
    return {
        "connected": connected,
        "mode": mode,
        "zotero_user_id": (s.get("zotero_user_id") or ""),
        "zotero_username": (s.get("zotero_username") or ""),
        "has_api_key": has_api,
        "has_oauth_token": has_oauth,
        "oauth_env_configured": env_ok,
        "missing_oauth_env": missing_env,
        "warnings": warnings,
        "recent_sync": list((s.get("zotero_sync_log") or []))[:5],
    }


def test_zotero_connection(username: str) -> dict[str, Any]:
    st = zotero_connection_status(username)
    if not st["connected"]:
        raise RuntimeError("Zotero is not connected.")
    out = sync_zotero_from_settings(username=username, project_id=None, limit=1)
    return {"ok": True, "mode": st["mode"], **out}


def zotero_remediation_guide(username: str) -> dict[str, Any]:
    st = zotero_connection_status(username)
    missing = st.get("missing_oauth_env") or []
    needs_env = bool(missing)
    commands: list[dict[str, str]] = []
    if needs_env:
        commands.append(
            {
                "title": "Set systemd environment",
                "command": "\n".join(
                    [
                        "sudo systemctl edit writing-memory",
                        "# Add:",
                        "[Service]",
                        "Environment=\"ZOTERO_CONSUMER_KEY=your_consumer_key\"",
                        "Environment=\"ZOTERO_CONSUMER_SECRET=your_consumer_secret\"",
                    ]
                ),
            }
        )
        commands.append(
            {
                "title": "Reload and restart service",
                "command": "sudo systemctl daemon-reload && sudo systemctl restart writing-memory && sudo systemctl is-active writing-memory",
            }
        )
        commands.append(
            {
                "title": "Verify environment loaded",
                "command": "sudo systemctl show writing-memory --property=Environment | sed 's/Environment=//'",
            }
        )
    else:
        commands.append(
            {
                "title": "Environment check passed",
                "command": "# ZOTERO_CONSUMER_KEY and ZOTERO_CONSUMER_SECRET already configured",
            }
        )
    return {
        "needs_env_fix": needs_env,
        "missing_env": missing,
        "commands": commands,
    }


def begin_zotero_oauth(username: str, callback_url: str) -> str:
    """
    Start Zotero OAuth1 flow and return authorization URL.
    """
    ck = (os.environ.get("ZOTERO_CONSUMER_KEY") or "").strip()
    cs = (os.environ.get("ZOTERO_CONSUMER_SECRET") or "").strip()
    if not (ck and cs):
        raise RuntimeError("ZOTERO_CONSUMER_KEY / ZOTERO_CONSUMER_SECRET not configured.")
    try:
        from requests_oauthlib import OAuth1Session
    except Exception as exc:
        raise RuntimeError("requests-oauthlib is required for Zotero OAuth mode") from exc

    oauth = OAuth1Session(client_key=ck, client_secret=cs, callback_uri=callback_url)
    token = oauth.fetch_request_token("https://www.zotero.org/oauth/request")
    req_token = token.get("oauth_token", "")
    req_secret = token.get("oauth_token_secret", "")
    if not req_token or not req_secret:
        raise RuntimeError("Failed to obtain Zotero request token.")

    save_settings(
        username,
        {
            "zotero_oauth_pending_token": req_token,
            "zotero_oauth_pending_secret": req_secret,
        },
    )
    return oauth.authorization_url("https://www.zotero.org/oauth/authorize")


def complete_zotero_oauth(username: str, oauth_token: str, oauth_verifier: str) -> dict[str, Any]:
    """
    Complete Zotero OAuth1 flow and persist access token/secret.
    """
    s = load_settings(username)
    pending_token = (s.get("zotero_oauth_pending_token") or "").strip()
    pending_secret = (s.get("zotero_oauth_pending_secret") or "").strip()
    if not pending_token or not pending_secret:
        raise RuntimeError("No pending Zotero OAuth request. Start OAuth again.")
    if pending_token != oauth_token:
        raise RuntimeError("OAuth token mismatch. Start OAuth again.")

    ck = (os.environ.get("ZOTERO_CONSUMER_KEY") or "").strip()
    cs = (os.environ.get("ZOTERO_CONSUMER_SECRET") or "").strip()
    if not (ck and cs):
        raise RuntimeError("ZOTERO_CONSUMER_KEY / ZOTERO_CONSUMER_SECRET not configured.")

    try:
        from requests_oauthlib import OAuth1Session
    except Exception as exc:
        raise RuntimeError("requests-oauthlib is required for Zotero OAuth mode") from exc

    oauth = OAuth1Session(
        client_key=ck,
        client_secret=cs,
        resource_owner_key=oauth_token,
        resource_owner_secret=pending_secret,
        verifier=oauth_verifier,
    )
    token = oauth.fetch_access_token("https://www.zotero.org/oauth/access")
    access_token = (token.get("oauth_token") or "").strip()
    access_secret = (token.get("oauth_token_secret") or "").strip()
    user_id = str(token.get("userID") or "").strip()
    user_name = str(token.get("username") or "").strip()
    if not access_token or not access_secret:
        raise RuntimeError("Failed to obtain Zotero access token.")

    save_settings(
        username,
        {
            "zotero_oauth_token": access_token,
            "zotero_oauth_token_secret": access_secret,
            "zotero_oauth_pending_token": "",
            "zotero_oauth_pending_secret": "",
            "zotero_user_id": user_id or s.get("zotero_user_id", ""),
            "zotero_username": user_name,
        },
    )
    return {"zotero_user_id": user_id, "zotero_username": user_name}


def export_csl_json(username: str, project_id: str | None = None) -> list[dict[str, Any]]:
    """
    Export library entries as CSL-JSON for citeproc compatibility.
    """
    entries = search_library(username, query="", project_id=project_id)
    out: list[dict[str, Any]] = []
    for e in entries:
        authors = []
        for p in [x.strip() for x in (e.authors or "").split(",") if x.strip()]:
            tokens = p.split()
            if len(tokens) >= 2:
                authors.append({"family": tokens[0], "given": " ".join(tokens[1:])})
            else:
                authors.append({"literal": p})
        item = {
            "id": e.id,
            "type": "article-journal",
            "title": e.title,
            "author": authors,
            "container-title": e.journal,
            "issued": {"date-parts": [[e.year]]} if e.year else None,
            "volume": e.volume,
            "issue": e.issue,
            "page": e.pages,
            "DOI": e.doi,
            "PMID": e.pmid,
            "abstract": e.abstract,
        }
        out.append({k: v for k, v in item.items() if v is not None})
    return out


def render_references_by_style(
    username: str,
    style_id: str,
    project_id: str | None = None,
) -> list[str]:
    """
    Render deterministic reference strings using curated style profiles.
    """
    from .journal_specs.format_reference import Author, Paper, format_reference, load_style

    style = load_style(style_id)
    entries = search_library(username, query="", project_id=project_id)
    lines: list[str] = []
    for i, e in enumerate(entries, start=1):
        names = [x.strip() for x in (e.authors or "").split(",") if x.strip()]
        authors: list[Author] = []
        for n in names:
            toks = n.split()
            if len(toks) >= 2:
                authors.append(Author(last=toks[0], initials="".join(toks[1:])))
            elif toks:
                authors.append(Author(last=toks[0], initials=""))
        paper = Paper(
            authors=authors,
            title=e.title or "",
            journal=e.journal or "",
            year=e.year,
            volume=e.volume,
            issue=e.issue,
            pages=e.pages,
            doi=e.doi,
            pmid=e.pmid,
            pmcid=e.pmcid,
        )
        lines.append(format_reference(paper, style, index=i))
    return lines
