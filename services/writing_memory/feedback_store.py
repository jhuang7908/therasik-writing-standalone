"""
Per-account feedback store and writing analytics for writing_memory service.

Storage: SQLite, one DB file per username in data/writing_feedback/
Schema is forward-compatible — new columns added with ALTER TABLE when needed.

Learning model:
  When a user accepts/downloads a version, we extract style features and
  incrementally update that account's style profile. Over time this teaches
  the system to generate closer to that user's preferences without ever
  sharing data between accounts.

Public API:
    record_acceptance(username, article_type, qa_score, text, session_id) -> None
    get_quality_trend(username, limit=20) -> list[dict]
    get_style_profile(username) -> dict
    update_style_from_text(username, text, article_type) -> dict
    get_learning_summary(username) -> dict
"""
from __future__ import annotations

import hashlib
import json
import re
import sqlite3
import statistics
from contextlib import contextmanager
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

_DATA_ROOT = Path(__file__).resolve().parent / "data" / "writing_feedback"
_DATA_ROOT.mkdir(parents=True, exist_ok=True)


# ─── DB setup ─────────────────────────────────────────────────────────────────

def _db_path(username: str) -> Path:
    safe = re.sub(r"[^\w\-]", "_", username)
    return _DATA_ROOT / f"{safe}.db"


@contextmanager
def _conn(username: str):
    path = _db_path(username)
    con = sqlite3.connect(str(path), timeout=10)
    con.row_factory = sqlite3.Row
    con.execute("PRAGMA journal_mode=WAL")
    try:
        _ensure_schema(con)
        yield con
        con.commit()
    finally:
        con.close()


def _ensure_schema(con: sqlite3.Connection) -> None:
    con.executescript("""
    CREATE TABLE IF NOT EXISTS accepted_versions (
        id             INTEGER PRIMARY KEY AUTOINCREMENT,
        session_id     TEXT,
        article_type   TEXT,
        qa_score       REAL,
        word_count     INTEGER,
        avg_sent_len   REAL,
        vocab_richness REAL,
        citation_density REAL,
        fk_grade       REAL,
        text_hash      TEXT,
        full_text      TEXT,
        accepted_at    TEXT
    );
    """)
    # Migration: add full_text if missing
    try:
        con.execute("ALTER TABLE accepted_versions ADD COLUMN full_text TEXT")
    except sqlite3.OperationalError:
        pass # already exists

    con.executescript("""
    CREATE TABLE IF NOT EXISTS style_profile (
        key   TEXT PRIMARY KEY,
        value TEXT,
        updated_at TEXT
    );

    CREATE TABLE IF NOT EXISTS quality_log (
        id           INTEGER PRIMARY KEY AUTOINCREMENT,
        session_id   TEXT,
        article_type TEXT,
        stage        TEXT,
        qa_score     REAL,
        word_count   INTEGER,
        logged_at    TEXT
    );
    """)


# ─── Feature extraction ───────────────────────────────────────────────────────

def _extract_text_features(text: str) -> dict[str, Any]:
    words = re.findall(r"\w+", text)
    sentences = re.split(r"(?<=[.!?])\s+(?=[A-Z])", text.strip())
    sentences = [s for s in sentences if s.strip()]
    sent_lens = [len(re.findall(r"\w+", s)) for s in sentences]
    cites_num = len(re.findall(r"\[\d+(?:[,;]\s*\d+)*\]", text))
    cites_aut = len(re.findall(r"\([A-Z][a-z]+(?:\s+et\s+al\.)?,\s*\d{4}\)", text))
    word_count = len(words)
    return {
        "word_count": word_count,
        "avg_sent_len": round(statistics.mean(sent_lens), 2) if sent_lens else 0,
        "sent_len_std": round(statistics.stdev(sent_lens), 2) if len(sent_lens) > 1 else 0,
        "vocab_richness": round(len(set(w.lower() for w in words)) / max(1, word_count), 4),
        "citation_density": round((cites_num + cites_aut) / max(1, word_count) * 100, 3),
        "text_hash": hashlib.sha256(text[:5000].encode()).hexdigest()[:16],
    }


# ─── Write operations ─────────────────────────────────────────────────────────

def record_acceptance(
    username: str,
    article_type: str,
    qa_score: float,
    text: str,
    session_id: str = "",
) -> dict[str, Any]:
    """
    Record that the user accepted/downloaded a draft version.
    Extracts style features and persists them, then updates style profile.
    """
    feats = _extract_text_features(text)
    now = datetime.now(timezone.utc).isoformat()
    with _conn(username) as con:
        con.execute(
            """INSERT INTO accepted_versions
               (session_id, article_type, qa_score, word_count, avg_sent_len,
                vocab_richness, citation_density, text_hash, full_text, accepted_at)
               VALUES (?,?,?,?,?,?,?,?,?,?)""",
            (session_id, article_type, qa_score,
             feats["word_count"], feats["avg_sent_len"],
             feats["vocab_richness"], feats["citation_density"],
             feats["text_hash"], text, now),
        )
    # Incrementally update style profile from this acceptance
    return update_style_from_text(username, text, article_type)


def log_quality(
    username: str,
    session_id: str,
    article_type: str,
    stage: str,           # "draft_1", "draft_2", "final"
    qa_score: float,
    word_count: int = 0,
) -> None:
    now = datetime.now(timezone.utc).isoformat()
    with _conn(username) as con:
        con.execute(
            """INSERT INTO quality_log
               (session_id, article_type, stage, qa_score, word_count, logged_at)
               VALUES (?,?,?,?,?,?)""",
            (session_id, article_type, stage, qa_score, word_count, now),
        )


def update_style_from_text(
    username: str,
    text: str,
    article_type: str = "",
) -> dict[str, Any]:
    """
    Incrementally update this account's style profile from accepted text.
    Uses exponential moving average (alpha=0.3) so recent work weighs more.
    """
    feats = _extract_text_features(text)
    alpha = 0.3  # weight of new sample vs historical

    with _conn(username) as con:
        existing_json = con.execute(
            "SELECT value FROM style_profile WHERE key='features'"
        ).fetchone()
        if existing_json:
            old = json.loads(existing_json["value"])
            merged = {
                "avg_sent_len":     round(alpha * feats["avg_sent_len"]     + (1 - alpha) * old.get("avg_sent_len", feats["avg_sent_len"]), 2),
                "vocab_richness":   round(alpha * feats["vocab_richness"]   + (1 - alpha) * old.get("vocab_richness", feats["vocab_richness"]), 4),
                "citation_density": round(alpha * feats["citation_density"] + (1 - alpha) * old.get("citation_density", feats["citation_density"]), 3),
                "sample_count":     old.get("sample_count", 0) + 1,
                "article_types":    list(set(old.get("article_types", []) + [article_type])),
                "last_updated":     datetime.now(timezone.utc).isoformat(),
            }
        else:
            merged = {
                **feats,
                "sample_count": 1,
                "article_types": [article_type] if article_type else [],
                "last_updated": datetime.now(timezone.utc).isoformat(),
            }

        now = datetime.now(timezone.utc).isoformat()
        con.execute(
            """INSERT INTO style_profile (key, value, updated_at)
               VALUES ('features', ?, ?)
               ON CONFLICT(key) DO UPDATE SET value=excluded.value, updated_at=excluded.updated_at""",
            (json.dumps(merged), now),
        )
    return merged


# ─── Read operations ──────────────────────────────────────────────────────────

def get_quality_trend(
    username: str,
    limit: int = 30,
) -> list[dict[str, Any]]:
    """
    Return per-session quality trend for the account.
    Combines accepted_versions and quality_log tables.
    """
    with _conn(username) as con:
        rows = con.execute(
            """SELECT article_type, qa_score, word_count, accepted_at as logged_at, 'accepted' as stage
               FROM accepted_versions
               UNION ALL
               SELECT article_type, qa_score, word_count, logged_at, stage
               FROM quality_log
               ORDER BY logged_at DESC LIMIT ?""",
            (limit,),
        ).fetchall()
    return [dict(r) for r in rows]


def get_style_profile(username: str) -> dict[str, Any]:
    with _conn(username) as con:
        row = con.execute(
            "SELECT value FROM style_profile WHERE key='features'"
        ).fetchone()
        count = con.execute("SELECT COUNT(*) as n FROM accepted_versions").fetchone()
        types_rows = con.execute(
            "SELECT DISTINCT article_type FROM accepted_versions WHERE article_type != ''"
        ).fetchall()
    profile = json.loads(row["value"]) if row else {}
    profile["total_accepted_versions"] = count["n"] if count else 0
    profile["article_types_written"] = [r["article_type"] for r in types_rows]
    return profile


def get_learning_summary(username: str) -> dict[str, Any]:
    """
    High-level summary of this account's learning state and quality evolution.
    """
    trend = get_quality_trend(username, limit=50)
    profile = get_style_profile(username)

    if not trend:
        return {
            "total_sessions": 0,
            "avg_qa_score": None,
            "qa_trend_direction": "no data",
            "recent_5": [],
            "style_profile": profile,
            "learning_active": False,
            "personalization_level": "none",
            "message": "No accepted versions yet. Accept a draft to begin personalisation.",
        }

    scores = [t["qa_score"] for t in trend if t.get("qa_score") is not None]
    avg = round(statistics.mean(scores), 3) if scores else None

    # Trend direction: compare first half vs second half scores
    trend_dir = "stable"
    if len(scores) >= 4:
        mid = len(scores) // 2
        first_half_avg = statistics.mean(scores[mid:])   # older (reversed order)
        second_half_avg = statistics.mean(scores[:mid])  # more recent
        delta = second_half_avg - first_half_avg
        if delta > 0.03:
            trend_dir = "improving"
        elif delta < -0.03:
            trend_dir = "declining"

    return {
        "total_sessions": len(scores),
        "avg_qa_score": avg,
        "qa_trend_direction": trend_dir,
        "recent_5": [round(s, 2) for s in scores[:5]],
        "style_profile": profile,
        "learning_active": profile.get("sample_count", 0) > 0,
        "personalization_level": _personalization_level(profile.get("sample_count", 0)),
    }


def _personalization_level(n: int) -> str:
    if n == 0:
        return "none"
    if n < 3:
        return "initializing"
    if n < 10:
        return "developing"
    if n < 30:
        return "established"
    return "mature"


def get_writing_history(username: str, limit: int = 200) -> list[dict[str, Any]]:
    """Return the full list of accepted draft records for a user, newest first."""
    with _conn(username) as con:
        rows = con.execute(
            """SELECT id, session_id, article_type, qa_score, word_count,
                      avg_sent_len, vocab_richness, citation_density, accepted_at
               FROM accepted_versions
               ORDER BY accepted_at DESC
               LIMIT ?""",
            (limit,),
        ).fetchall()
    return [dict(r) for r in rows]


def get_version_text(username: str, version_id: int) -> str | None:
    """Return the full text of a specific accepted version."""
    with _conn(username) as con:
        row = con.execute(
            "SELECT full_text FROM accepted_versions WHERE id = ?",
            (version_id,),
        ).fetchone()
    return row["full_text"] if row else None


__all__ = [
    "record_acceptance",
    "log_quality",
    "update_style_from_text",
    "get_quality_trend",
    "get_style_profile",
    "get_learning_summary",
    "get_writing_history",
    "get_version_text",
]
