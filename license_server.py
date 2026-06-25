"""
license_server.py  v1.1.0
=================
TheraSIK Cloud License, Journal API & Proxy Server

Endpoints:
  POST /validate            -- validate MCP Key + Agent Key pair
  POST /consume             -- consume Agent Key quota units
  GET  /journal/{name}      -- get journal requirements
  GET  /journals            -- list all journals
  POST /proxy/pubmed        -- rate-limited + cached PubMed E-utilities proxy
  POST /proxy/crossref      -- rate-limited + cached CrossRef REST proxy
  GET  /queue/status        -- current global queue depth
  POST /admin/create-pair   -- create new MCP+Agent key pair (admin only)
  POST /admin/revoke        -- revoke a key pair (admin only)
  GET  /admin/pairs         -- list all key pairs (admin only)
  POST /admin/topup         -- add quota to Agent Key (admin only)
  GET  /health              -- health check

Rate limiting (v1.1.0):
  - Per-user token bucket: RATE_LIMIT_RPM requests/minute (default 30)
  - Global PubMed semaphore: PUBMED_CONCURRENCY concurrent calls (default 8)
  - Global CrossRef semaphore: CROSSREF_CONCURRENCY concurrent calls (default 4)
  - SQLite result cache: CACHE_TTL_DAYS day TTL (default 30)

Environment variables:
  ADMIN_SECRET          -- secret token for admin endpoints
  DATABASE_URL          -- SQLite path (default: ./licenses.db)
  JOURNAL_DIR           -- path to journal JSON files
  NCBI_API_KEY          -- free NCBI key → 10 req/s (vs 3 without key)
                           get free key: https://www.ncbi.nlm.nih.gov/account/
  RATE_LIMIT_RPM        -- per-user rate limit, requests/minute (default: 30)
  PUBMED_CONCURRENCY    -- max concurrent PubMed calls (default: 8)
  CROSSREF_CONCURRENCY  -- max concurrent CrossRef calls (default: 4)
  CACHE_TTL_DAYS        -- cache TTL in days (default: 30)

Deploy to Railway:
  railway init && railway up
"""

from __future__ import annotations

import asyncio
import hashlib
import json
import os
import secrets
import sqlite3
import string
import time
from contextlib import asynccontextmanager
from datetime import datetime, timezone, timedelta
from pathlib import Path
from typing import Optional

try:
    from fastapi import FastAPI, HTTPException, Header, Depends, Request, Response
    from fastapi.middleware.cors import CORSMiddleware
    from pydantic import BaseModel
    import uvicorn
except ImportError:
    print("Install: pip install fastapi uvicorn pydantic httpx")
    raise

try:
    import httpx
except ImportError:
    print("Install: pip install httpx")
    raise

# ── Config ────────────────────────────────────────────────────────────────────
ADMIN_SECRET       = os.environ.get("ADMIN_SECRET", "change-this-secret")
DB_PATH            = os.environ.get("DATABASE_URL", "./licenses.db")
JOURNAL_DIR        = Path(os.environ.get("JOURNAL_DIR", "./assets/journal_requirements"))
NCBI_API_KEY       = os.environ.get("NCBI_API_KEY", "")
RATE_LIMIT_RPM     = int(os.environ.get("RATE_LIMIT_RPM", "30"))
PUBMED_CONCURRENCY = int(os.environ.get("PUBMED_CONCURRENCY", "8"))
CROSSREF_CONCURRENCY = int(os.environ.get("CROSSREF_CONCURRENCY", "4"))
CACHE_TTL_DAYS     = int(os.environ.get("CACHE_TTL_DAYS", "30"))

# ── Global async state ────────────────────────────────────────────────────────
# Initialized in lifespan to ensure we're inside the event loop.
_pubmed_sem: asyncio.Semaphore | None = None
_crossref_sem: asyncio.Semaphore | None = None
_bucket_lock: asyncio.Lock | None = None
_http_client: httpx.AsyncClient | None = None

# Token bucket store: {agent_key: {"tokens": float, "last_refill": float}}
_buckets: dict[str, dict] = {}

# Queue depth counters (informational only)
_pubmed_waiting = 0
_crossref_waiting = 0


@asynccontextmanager
async def lifespan(app: FastAPI):
    global _pubmed_sem, _crossref_sem, _bucket_lock, _http_client
    _pubmed_sem    = asyncio.Semaphore(PUBMED_CONCURRENCY)
    _crossref_sem  = asyncio.Semaphore(CROSSREF_CONCURRENCY)
    _bucket_lock   = asyncio.Lock()
    _http_client   = httpx.AsyncClient(timeout=30.0, follow_redirects=True)
    yield
    await _http_client.aclose()


# ── App ────────────────────────────────────────────────────────────────────────
app = FastAPI(title="TheraSIK License Server", version="1.1.0", lifespan=lifespan)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"], allow_methods=["*"], allow_headers=["*"]
)


# ── Database ──────────────────────────────────────────────────────────────────

def get_conn() -> sqlite3.Connection:
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    conn.executescript("""
        CREATE TABLE IF NOT EXISTS key_pairs (
            pair_id         TEXT PRIMARY KEY,
            mcp_key         TEXT UNIQUE NOT NULL,
            agent_key       TEXT UNIQUE NOT NULL,
            customer_email  TEXT,
            customer_name   TEXT,
            plan            TEXT DEFAULT 'standard',
            mcp_expires_at  TEXT NOT NULL,
            agent_quota     INTEGER NOT NULL DEFAULT 100,
            agent_used      INTEGER NOT NULL DEFAULT 0,
            status          TEXT DEFAULT 'active',
            created_at      TEXT NOT NULL,
            notes           TEXT
        );
        CREATE INDEX IF NOT EXISTS idx_mcp_key   ON key_pairs(mcp_key);
        CREATE INDEX IF NOT EXISTS idx_agent_key ON key_pairs(agent_key);

        -- API result cache (avoids hitting PubMed/CrossRef repeatedly)
        CREATE TABLE IF NOT EXISTS api_cache (
            cache_key   TEXT PRIMARY KEY,   -- e.g. "pubmed:12345678"
            payload     TEXT NOT NULL,      -- JSON response
            fetched_at  TEXT NOT NULL,      -- ISO timestamp
            ttl_days    INTEGER DEFAULT 30
        );
        CREATE INDEX IF NOT EXISTS idx_cache_key ON api_cache(cache_key);
    """)
    conn.commit()
    return conn


def _cache_get(conn: sqlite3.Connection, key: str) -> dict | None:
    row = conn.execute(
        "SELECT payload, fetched_at, ttl_days FROM api_cache WHERE cache_key=?", (key,)
    ).fetchone()
    if not row:
        return None
    fetched = datetime.fromisoformat(row["fetched_at"])
    ttl = timedelta(days=row["ttl_days"])
    if datetime.now(timezone.utc) - fetched.replace(tzinfo=timezone.utc) > ttl:
        conn.execute("DELETE FROM api_cache WHERE cache_key=?", (key,))
        conn.commit()
        return None
    return json.loads(row["payload"])


def _cache_set(conn: sqlite3.Connection, key: str, data: dict, ttl_days: int = CACHE_TTL_DAYS):
    now = datetime.now(timezone.utc).isoformat()
    conn.execute(
        """INSERT INTO api_cache (cache_key, payload, fetched_at, ttl_days)
           VALUES (?,?,?,?)
           ON CONFLICT(cache_key) DO UPDATE SET payload=excluded.payload,
           fetched_at=excluded.fetched_at, ttl_days=excluded.ttl_days""",
        (key, json.dumps(data), now, ttl_days)
    )
    conn.commit()


# ── Key generation ────────────────────────────────────────────────────────────

def _gen_key(prefix: str) -> str:
    chars = string.ascii_uppercase + string.digits
    body = "".join(secrets.choice(chars) for _ in range(20))
    return f"{prefix}-{body[:5]}-{body[5:10]}-{body[10:15]}-{body[15:20]}"


# ── Admin auth ────────────────────────────────────────────────────────────────

def require_admin(x_admin_secret: str = Header(...)):
    if x_admin_secret != ADMIN_SECRET:
        raise HTTPException(status_code=403, detail="Invalid admin secret")


# ── Rate limiter (token bucket per agent_key) ─────────────────────────────────

async def _check_rate_limit(agent_key: str) -> dict:
    """
    Token bucket: capacity = RATE_LIMIT_RPM tokens, refill rate = RPM/60 per second.
    Returns {"allowed": bool, "tokens_remaining": float, "retry_after": float}
    """
    capacity   = float(RATE_LIMIT_RPM)
    refill_per_sec = capacity / 60.0

    async with _bucket_lock:
        now = time.monotonic()
        if agent_key not in _buckets:
            _buckets[agent_key] = {"tokens": capacity, "last_refill": now}

        bucket = _buckets[agent_key]
        elapsed = now - bucket["last_refill"]
        bucket["tokens"] = min(capacity, bucket["tokens"] + elapsed * refill_per_sec)
        bucket["last_refill"] = now

        if bucket["tokens"] >= 1.0:
            bucket["tokens"] -= 1.0
            return {"allowed": True, "tokens_remaining": bucket["tokens"], "retry_after": 0}
        else:
            deficit = 1.0 - bucket["tokens"]
            retry_after = deficit / refill_per_sec
            return {"allowed": False, "tokens_remaining": 0.0, "retry_after": retry_after}


async def _require_rate_ok(agent_key: str, response: Response):
    """FastAPI dependency: check rate limit, set headers, raise 429 if exceeded."""
    result = await _check_rate_limit(agent_key)
    response.headers["X-RateLimit-Limit"]     = str(RATE_LIMIT_RPM)
    response.headers["X-RateLimit-Remaining"] = str(int(result["tokens_remaining"]))
    if not result["allowed"]:
        response.headers["Retry-After"] = f"{result['retry_after']:.1f}"
        raise HTTPException(
            status_code=429,
            detail={
                "error": "rate_limit_exceeded",
                "message": f"Too many requests. Max {RATE_LIMIT_RPM} per minute per key.",
                "retry_after_seconds": round(result["retry_after"], 1)
            }
        )


# ── Key pair auth (reusable dependency) ──────────────────────────────────────

def _get_active_pair(mcp_key: str, agent_key: str) -> sqlite3.Row:
    conn = get_conn()
    row = conn.execute(
        "SELECT * FROM key_pairs WHERE mcp_key=? AND agent_key=? AND status='active'",
        (mcp_key, agent_key)
    ).fetchone()
    if not row:
        raise HTTPException(status_code=401, detail="Invalid or revoked key pair")
    return row


# ── Models ────────────────────────────────────────────────────────────────────

class ValidateRequest(BaseModel):
    mcp_key: str
    agent_key: str
    machine_id: Optional[str] = None

class ConsumeRequest(BaseModel):
    mcp_key: str
    agent_key: str
    units: int = 1
    operation: str = "api_call"

class ProxyPubMedRequest(BaseModel):
    mcp_key: str
    agent_key: str
    pmid: str

class ProxyCrossRefRequest(BaseModel):
    mcp_key: str
    agent_key: str
    doi: str

class CreatePairRequest(BaseModel):
    customer_email: str
    customer_name: str = ""
    plan: str = "standard"
    mcp_days: int = 365
    agent_quota: int = 500
    notes: str = ""

class TopupRequest(BaseModel):
    agent_key: str
    units: int

class RevokeRequest(BaseModel):
    mcp_key: Optional[str] = None
    agent_key: Optional[str] = None


# ── Validate endpoint ─────────────────────────────────────────────────────────

@app.post("/validate")
def validate(req: ValidateRequest):
    conn = get_conn()
    row = conn.execute(
        "SELECT * FROM key_pairs WHERE mcp_key=? AND agent_key=?",
        (req.mcp_key, req.agent_key)
    ).fetchone()

    if not row:
        raise HTTPException(status_code=401, detail={
            "valid": False, "reason": "key_pair_not_found",
            "message": "MCP Key and Agent Key do not match or do not exist"
        })
    if row["status"] != "active":
        raise HTTPException(status_code=403, detail={
            "valid": False, "reason": "revoked",
            "message": "This license has been revoked. Contact support."
        })

    now     = datetime.now(timezone.utc)
    expires = datetime.fromisoformat(row["mcp_expires_at"])
    if now > expires:
        raise HTTPException(status_code=402, detail={
            "valid": False, "reason": "mcp_expired",
            "message": f"MCP subscription expired on {row['mcp_expires_at'][:10]}. Please renew.",
            "expired_at": row["mcp_expires_at"]
        })

    quota_remaining = row["agent_quota"] - row["agent_used"]
    if quota_remaining <= 0:
        raise HTTPException(status_code=402, detail={
            "valid": False, "reason": "agent_quota_exhausted",
            "message": "Agent Key quota exhausted. Please top up.",
            "quota_total": row["agent_quota"],
            "quota_used": row["agent_used"]
        })

    return {
        "valid": True,
        "customer_email":       row["customer_email"],
        "customer_name":        row["customer_name"],
        "plan":                 row["plan"],
        "mcp_expires_at":       row["mcp_expires_at"],
        "agent_quota_total":    row["agent_quota"],
        "agent_quota_used":     row["agent_used"],
        "agent_quota_remaining": quota_remaining,
        "days_remaining":       (expires - now).days,
        "rate_limit_rpm":       RATE_LIMIT_RPM,
    }


# ── Consume endpoint ──────────────────────────────────────────────────────────

@app.post("/consume")
def consume(req: ConsumeRequest):
    conn = get_conn()
    row  = _get_active_pair(req.mcp_key, req.agent_key)

    quota_remaining = row["agent_quota"] - row["agent_used"]
    if quota_remaining < req.units:
        raise HTTPException(status_code=402, detail={
            "error": "insufficient_quota",
            "remaining": quota_remaining,
            "requested": req.units
        })

    conn.execute(
        "UPDATE key_pairs SET agent_used = agent_used + ? WHERE mcp_key=?",
        (req.units, req.mcp_key)
    )
    conn.commit()

    return {
        "consumed":        req.units,
        "quota_remaining": quota_remaining - req.units,
        "operation":       req.operation,
    }


# ── Proxy: PubMed ─────────────────────────────────────────────────────────────

@app.post("/proxy/pubmed")
async def proxy_pubmed(req: ProxyPubMedRequest, response: Response):
    """
    Rate-limited, cached PubMed E-utilities proxy.

    Flow:
      1. Validate key pair
      2. Check per-user rate limit (token bucket)
      3. Check SQLite cache (30-day TTL)
      4. If cache miss: acquire global semaphore → fetch from NCBI → store cache
      5. Return JSON + rate-limit headers
    """
    global _pubmed_waiting

    # 1. Auth
    _get_active_pair(req.mcp_key, req.agent_key)

    # 2. Rate limit
    await _require_rate_ok(req.agent_key, response)

    pmid      = req.pmid.strip()
    cache_key = f"pubmed:{pmid}"

    # 3. Cache check
    conn   = get_conn()
    cached = _cache_get(conn, cache_key)
    if cached:
        response.headers["X-Cache"] = "HIT"
        return cached

    # 4. Queue + fetch
    response.headers["X-Cache"] = "MISS"
    _pubmed_waiting += 1
    response.headers["X-Queue-Depth"] = str(_pubmed_waiting)

    try:
        async with _pubmed_sem:
            _pubmed_waiting -= 1

            params: dict[str, str] = {
                "db":      "pubmed",
                "id":      pmid,
                "retmode": "xml",
                "rettype": "abstract",
            }
            if NCBI_API_KEY:
                params["api_key"] = NCBI_API_KEY

            r = await _http_client.get(
                "https://eutils.ncbi.nlm.nih.gov/entrez/eutils/efetch.fcgi",
                params=params,
            )
    except Exception as e:
        _pubmed_waiting = max(0, _pubmed_waiting - 1)
        raise HTTPException(status_code=502, detail=f"PubMed fetch failed: {e}")

    if r.status_code != 200:
        raise HTTPException(status_code=502, detail=f"PubMed returned {r.status_code}")

    # Parse XML to a structured dict (lightweight, no lxml required)
    import xml.etree.ElementTree as ET
    try:
        root = ET.fromstring(r.text)
        article = root.find(".//PubmedArticle")
        if article is None:
            raise HTTPException(status_code=404, detail=f"PMID {pmid} not found in PubMed")

        def _text(el, path, default=""):
            node = el.find(path)
            return "".join(node.itertext()).strip() if node is not None else default

        authors = []
        for auth in article.findall(".//Author"):
            ln = _text(auth, "LastName")
            fn = _text(auth, "ForeName") or _text(auth, "Initials")
            if ln:
                authors.append(f"{ln} {fn}".strip())

        data = {
            "pmid":     pmid,
            "title":    _text(article, ".//ArticleTitle"),
            "abstract": _text(article, ".//AbstractText"),
            "journal":  _text(article, ".//Journal/Title"),
            "year":     _text(article, ".//PubDate/Year") or _text(article, ".//PubDate/MedlineDate")[:4],
            "volume":   _text(article, ".//Volume"),
            "issue":    _text(article, ".//Issue"),
            "pages":    _text(article, ".//MedlinePgn"),
            "doi":      next(
                (id_el.text for id_el in article.findall(".//ArticleId")
                 if id_el.get("IdType") == "doi"), ""
            ),
            "authors":  authors,
            "source":   "pubmed",
        }
    except ET.ParseError as e:
        raise HTTPException(status_code=502, detail=f"PubMed XML parse error: {e}")

    # 5. Cache + return
    _cache_set(conn, cache_key, data)
    return data


# ── Proxy: CrossRef ────────────────────────────────────────────────────────────

@app.post("/proxy/crossref")
async def proxy_crossref(req: ProxyCrossRefRequest, response: Response):
    """
    Rate-limited, cached CrossRef REST API proxy.

    Flow:
      1. Validate key pair
      2. Check per-user rate limit
      3. Check SQLite cache (30-day TTL)
      4. If cache miss: acquire global semaphore → fetch CrossRef → store cache
      5. Return JSON + rate-limit headers
    """
    global _crossref_waiting

    # 1. Auth
    _get_active_pair(req.mcp_key, req.agent_key)

    # 2. Rate limit
    await _require_rate_ok(req.agent_key, response)

    doi       = req.doi.strip().lstrip("https://doi.org/").lstrip("doi:")
    cache_key = f"crossref:{hashlib.md5(doi.encode()).hexdigest()}"

    # 3. Cache check
    conn   = get_conn()
    cached = _cache_get(conn, cache_key)
    if cached:
        response.headers["X-Cache"] = "HIT"
        return cached

    # 4. Queue + fetch
    response.headers["X-Cache"] = "MISS"
    _crossref_waiting += 1
    response.headers["X-Queue-Depth"] = str(_crossref_waiting)

    try:
        async with _crossref_sem:
            _crossref_waiting -= 1
            r = await _http_client.get(
                f"https://api.crossref.org/works/{doi}",
                headers={"User-Agent": "TheraSIK/1.1 (mailto:support@therasik.io)"},
            )
    except Exception as e:
        _crossref_waiting = max(0, _crossref_waiting - 1)
        raise HTTPException(status_code=502, detail=f"CrossRef fetch failed: {e}")

    if r.status_code == 404:
        raise HTTPException(status_code=404, detail=f"DOI '{doi}' not found in CrossRef")
    if r.status_code != 200:
        raise HTTPException(status_code=502, detail=f"CrossRef returned {r.status_code}")

    raw  = r.json().get("message", {})
    def _cr_str(val) -> str:
        if isinstance(val, list):
            return " ".join(str(v) for v in val)
        return str(val) if val else ""

    authors = []
    for a in raw.get("author", []):
        name = f"{a.get('family', '')} {a.get('given', '')}".strip()
        if name:
            authors.append(name)

    date_parts = raw.get("published-print", raw.get("published-online", {})).get("date-parts", [[]])
    year = str(date_parts[0][0]) if date_parts and date_parts[0] else ""

    data = {
        "doi":      doi,
        "title":    _cr_str(raw.get("title")),
        "abstract": raw.get("abstract", ""),
        "journal":  _cr_str(raw.get("container-title")),
        "year":     year,
        "volume":   raw.get("volume", ""),
        "issue":    raw.get("issue", ""),
        "pages":    raw.get("page", ""),
        "authors":  authors,
        "type":     raw.get("type", ""),
        "publisher": raw.get("publisher", ""),
        "source":   "crossref",
    }

    # 5. Cache + return
    _cache_set(conn, cache_key, data)
    return data


# ── Queue status ──────────────────────────────────────────────────────────────

@app.get("/queue/status")
def queue_status():
    """Current queue depth and concurrency limits."""
    pubmed_active = PUBMED_CONCURRENCY - (_pubmed_sem._value if _pubmed_sem else 0)
    crossref_active = CROSSREF_CONCURRENCY - (_crossref_sem._value if _crossref_sem else 0)
    return {
        "pubmed": {
            "concurrency_limit": PUBMED_CONCURRENCY,
            "active":            pubmed_active,
            "waiting":           _pubmed_waiting,
        },
        "crossref": {
            "concurrency_limit": CROSSREF_CONCURRENCY,
            "active":            crossref_active,
            "waiting":           _crossref_waiting,
        },
        "rate_limit_rpm":  RATE_LIMIT_RPM,
        "ncbi_key_active": bool(NCBI_API_KEY),
    }


# ── Journal endpoints ─────────────────────────────────────────────────────────

def _load_index() -> dict:
    idx = JOURNAL_DIR / "_index.json"
    if not idx.exists():
        return {}
    return json.loads(idx.read_text(encoding="utf-8"))


@app.get("/journals")
def list_journals():
    index = _load_index()
    return {"journals": list(index.values()), "count": len(index)}


@app.get("/journal/{name}")
def get_journal(name: str):
    index = _load_index()
    query = name.lower().strip()

    if query in index:
        f = JOURNAL_DIR / f"{query}.json"
        if f.exists():
            return json.loads(f.read_text(encoding="utf-8"))

    matches = [k for k, v in index.items()
               if query in k or query in v.get("display_name", "").lower()]

    if len(matches) == 1:
        f = JOURNAL_DIR / f"{matches[0]}.json"
        if f.exists():
            return json.loads(f.read_text(encoding="utf-8"))

    if matches:
        return {"matches": {k: index[k].get("display_name") for k in matches[:10]}}

    raise HTTPException(status_code=404, detail=f"Journal '{name}' not found")


# ── Admin endpoints ───────────────────────────────────────────────────────────

@app.post("/admin/create-pair", dependencies=[Depends(require_admin)])
def create_pair(req: CreatePairRequest):
    import uuid
    conn      = get_conn()
    mcp_key   = _gen_key("THERASIK-MCP")
    agent_key = _gen_key("THERASIK-AGT")
    pair_id   = str(uuid.uuid4())
    now       = datetime.now(timezone.utc)
    expires   = now + timedelta(days=req.mcp_days)

    conn.execute("""
        INSERT INTO key_pairs
        (pair_id, mcp_key, agent_key, customer_email, customer_name,
         plan, mcp_expires_at, agent_quota, agent_used, status, created_at, notes)
        VALUES (?,?,?,?,?,?,?,?,0,'active',?,?)
    """, (pair_id, mcp_key, agent_key, req.customer_email, req.customer_name,
          req.plan, expires.isoformat(), req.agent_quota, now.isoformat(), req.notes))
    conn.commit()

    return {
        "pair_id":        pair_id,
        "mcp_key":        mcp_key,
        "agent_key":      agent_key,
        "customer_email": req.customer_email,
        "mcp_expires_at": expires.isoformat()[:10],
        "agent_quota":    req.agent_quota,
        "instructions": (
            f"Set in .env:\n"
            f"THERASIK_MCP_KEY={mcp_key}\n"
            f"THERASIK_AGENT_KEY={agent_key}"
        )
    }


@app.post("/admin/revoke", dependencies=[Depends(require_admin)])
def revoke(req: RevokeRequest):
    conn = get_conn()
    if req.mcp_key:
        conn.execute("UPDATE key_pairs SET status='revoked' WHERE mcp_key=?", (req.mcp_key,))
    elif req.agent_key:
        conn.execute("UPDATE key_pairs SET status='revoked' WHERE agent_key=?", (req.agent_key,))
    else:
        raise HTTPException(status_code=400, detail="Provide mcp_key or agent_key")
    conn.commit()
    return {"status": "revoked"}


@app.post("/admin/topup", dependencies=[Depends(require_admin)])
def topup(req: TopupRequest):
    conn = get_conn()
    conn.execute(
        "UPDATE key_pairs SET agent_quota = agent_quota + ? WHERE agent_key=?",
        (req.units, req.agent_key)
    )
    conn.commit()
    row = conn.execute("SELECT * FROM key_pairs WHERE agent_key=?", (req.agent_key,)).fetchone()
    return {
        "agent_key":      req.agent_key,
        "new_quota":      row["agent_quota"],
        "quota_used":     row["agent_used"],
        "quota_remaining": row["agent_quota"] - row["agent_used"],
    }


@app.get("/admin/pairs", dependencies=[Depends(require_admin)])
def list_pairs(status: str = "active"):
    conn = get_conn()
    rows = conn.execute(
        "SELECT * FROM key_pairs WHERE status=? ORDER BY created_at DESC", (status,)
    ).fetchall()
    return {"pairs": [dict(r) for r in rows], "count": len(rows)}


# ── Cache management (admin) ──────────────────────────────────────────────────

@app.get("/admin/cache/stats", dependencies=[Depends(require_admin)])
def cache_stats():
    conn = get_conn()
    total = conn.execute("SELECT COUNT(*) as n FROM api_cache").fetchone()["n"]
    pubmed = conn.execute(
        "SELECT COUNT(*) as n FROM api_cache WHERE cache_key LIKE 'pubmed:%'"
    ).fetchone()["n"]
    crossref = conn.execute(
        "SELECT COUNT(*) as n FROM api_cache WHERE cache_key LIKE 'crossref:%'"
    ).fetchone()["n"]
    return {"total": total, "pubmed": pubmed, "crossref": crossref, "ttl_days": CACHE_TTL_DAYS}


@app.delete("/admin/cache/purge", dependencies=[Depends(require_admin)])
def cache_purge():
    conn = get_conn()
    now = datetime.now(timezone.utc).isoformat()
    result = conn.execute(
        """DELETE FROM api_cache
           WHERE datetime(fetched_at, '+' || ttl_days || ' days') < datetime(?)""",
        (now,)
    )
    conn.commit()
    return {"purged": result.rowcount}


# ── Health ────────────────────────────────────────────────────────────────────

@app.get("/health")
def health():
    return {
        "status":          "ok",
        "service":         "therasik-license-server",
        "version":         "1.1.0",
        "ncbi_key_active": bool(NCBI_API_KEY),
        "rate_limit_rpm":  RATE_LIMIT_RPM,
    }


# ── Entry point ───────────────────────────────────────────────────────────────

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 8000))
    uvicorn.run(app, host="0.0.0.0", port=port)
