"""
Platform-wide journal style learning from uploaded exemplar full texts (PDF or text).

Uploads merge into a shared pack per journal name (accumulative, all users reuse).
Immediate path: paragraph chunks + embeddings (RAG) + optional Claude profile.

Not a substitute for curated journal_specs (submission rules).
"""

from __future__ import annotations

import hashlib
import json
import re
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import numpy as np

_HERE = Path(__file__).resolve().parent
COMMUNITY_STYLES_ROOT = Path(
    __import__("os").environ.get(
        "WM_COMMUNITY_STYLES_DIR",
        str(_HERE / "data" / "community_journal_styles"),
    )
)
# Legacy per-user storage (read-only fallback for old select keys user:...)
USER_STYLES_ROOT = Path(
    __import__("os").environ.get("WM_USER_STYLES_DIR", str(_HERE / "data" / "user_styles"))
)
PROMPTS_DIR = _HERE / "prompts"

# Product thresholds (MVP — hybrid upload + corpus AI supplement)
MIN_TARGET_JOURNAL_PAPERS_PER_UPLOAD = 1
RECOMMENDED_TARGET_JOURNAL_PAPERS = 5
RECOMMENDED_SIMILAR_PAPERS = 5
STRONG_TARGET_JOURNAL_PAPERS = 5
STRONG_SIMILAR_PAPERS = 5
MIN_PAPERS_FOR_PROFILE = 2
MAX_PAPERS_PER_UPLOAD = 12
MAX_ACCUMULATED_PAPERS = 80
TARGET_KINDS = frozenset({"target_journal", "corpus_target"})
SIMILAR_KINDS = frozenset({"similar", "corpus_similar"})
ARCHIVE_KINDS = frozenset({"archive_misfit"})
_MAX_CHARS_PER_PAPER = 120_000
_MIN_CHARS_PER_PAPER = 200
_MIN_CHARS_TOTAL = 800
_CHUNK_MIN_LEN = 120
_CHUNK_MAX = 400

# Full-text reading limits per article type
# (customer uploads + corpus; abstract-only pool is handled by citation_pool.py)
FULLTEXT_LIMITS: dict[str, dict[str, int]] = {
    "research":    {"recommended": 3, "review": 1, "max": 5},
    "review":      {"recommended": 5, "review": 2, "max": 8},
    "case_report": {"recommended": 2, "review": 1, "max": 3},
    "letter":      {"recommended": 1, "review": 1, "max": 2},
    "protocol":    {"recommended": 3, "review": 1, "max": 5},
    "systematic_review": {"recommended": 5, "review": 2, "max": 8},
}

LEARNING_GUIDANCE = {
    "min_target_journal_per_upload": MIN_TARGET_JOURNAL_PAPERS_PER_UPLOAD,
    "recommended_target_journal": RECOMMENDED_TARGET_JOURNAL_PAPERS,
    "recommended_similar": RECOMMENDED_SIMILAR_PAPERS,
    "strong_target_journal": STRONG_TARGET_JOURNAL_PAPERS,
    "strong_similar": STRONG_SIMILAR_PAPERS,
    "min_for_profile": MIN_PAPERS_FOR_PROFILE,
    "hybrid_corpus_augment": True,
    "min_customer_target_pdf_always": 2,
    "recommended_customer_target_pdf": 4,
    "fulltext_limits_by_type": FULLTEXT_LIMITS,
    "priority": "customer_uploads_first",
    "note_zh": (
        "全文精读优先使用客户上传文献；不足时才从语料库补充。"
        "每种文章类型建议全文数量：研究论文 3篇研究+1篇综述（上限5篇），"
        "综述 5篇研究+2篇综述（上限8篇），其余类型按比例。"
        "引用检索只需摘要，不消耗全文配额。"
    ),
    "note_en": (
        "Priority: customer-uploaded full texts first; OA corpus fills only the gap. "
        "Full-text reading limits by article type — research: 3 research+1 review (max 5); "
        "review: 5 research+2 review (max 8); case report: max 3; letter: max 2. "
        "Citation pool uses abstract-only reading — does not count against fulltext quota."
    ),
}


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


def _slugify(name: str) -> str:
    s = re.sub(r"[^a-zA-Z0-9]+", "_", (name or "").strip().lower()).strip("_")
    return (s[:64] or "journal")


def journal_slug(display_name: str) -> str:
    return _slugify(display_name)


def pack_id_for_journal(display_name: str) -> str:
    return f"learned_{journal_slug(display_name)}"


def journal_select_key(pack_id: str) -> str:
    return f"learned:{pack_id}"


def learning_guidance() -> dict[str, Any]:
    return dict(LEARNING_GUIDANCE)


def _coverage_tier(target_count: int, similar_count: int = 0) -> str:
    if target_count >= STRONG_TARGET_JOURNAL_PAPERS and similar_count >= STRONG_SIMILAR_PAPERS:
        return "strong"
    if target_count >= 3 and similar_count >= 2:
        return "adequate"
    return "bootstrap"


def _count_by_kind(papers: list[dict[str, Any]]) -> tuple[int, int, int, int]:
    target = similar = corpus_t = corpus_s = 0
    for p in papers:
        k = p.get("kind") or "target_journal"
        if k in ARCHIVE_KINDS:
            continue
        if k in TARGET_KINDS:
            target += 1
            if k == "corpus_target":
                corpus_t += 1
        elif k in SIMILAR_KINDS:
            similar += 1
            if k == "corpus_similar":
                corpus_s += 1
    return target, similar, corpus_t, corpus_s


def _community_dir() -> Path:
    d = COMMUNITY_STYLES_ROOT
    d.mkdir(parents=True, exist_ok=True)
    return d


def _pack_path(pack_id: str) -> Path:
    return _community_dir() / f"{pack_id}.json"


def _index_path(pack_id: str) -> Path:
    return _community_dir() / f"{pack_id}_index.npz"


def _text_store_path(pack_id: str, sha256: str) -> Path:
    d = _community_dir() / "texts" / pack_id
    d.mkdir(parents=True, exist_ok=True)
    return d / f"{sha256}.txt"


def _paper_hash(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8", errors="ignore")).hexdigest()[:16]


def list_community_packs() -> list[dict[str, Any]]:
    out: list[dict[str, Any]] = []
    for p in sorted(_community_dir().glob("learned_*.json")):
        try:
            data = json.loads(p.read_text(encoding="utf-8"))
            pid = data.get("pack_id", p.stem)
            tgt = int(data.get("target_journal_paper_count", 0))
            sim = int(data.get("similar_paper_count", 0))
            out.append({
                "pack_id": pid,
                "journal_slug": data.get("journal_slug"),
                "journal_select_key": journal_select_key(pid),
                "journal_display_name": data.get("journal_display_name"),
                "linked_journal_key": data.get("linked_journal_key"),
                "article_type": data.get("article_type"),
                "chunk_count": data.get("chunk_count", 0),
                "target_journal_paper_count": tgt,
                "similar_paper_count": sim,
                "corpus_target_count": data.get("corpus_target_count", 0),
                "corpus_similar_count": data.get("corpus_similar_count", 0),
                "coverage_tier": data.get("coverage_tier") or _coverage_tier(tgt, sim),
                "has_profile": bool(data.get("profile")),
                "contributor_count": len(data.get("contributors") or []),
                "created_at": data.get("created_at"),
                "updated_at": data.get("updated_at"),
            })
        except Exception:
            continue
    return out


# Backward-compatible alias
def list_user_packs(_username: str | None = None) -> list[dict[str, Any]]:
    return list_community_packs()


def load_community_pack(pack_id: str) -> dict[str, Any] | None:
    path = _pack_path(pack_id)
    if not path.exists():
        return None
    return json.loads(path.read_text(encoding="utf-8"))


def load_pack_by_select_key(select_key: str) -> dict[str, Any] | None:
    if select_key.startswith("learned:"):
        return load_community_pack(select_key[8:])
    if select_key.startswith("user:"):
        return _load_legacy_user_pack(select_key[5:])
    return None


def load_user_pack_by_select_key(username: str, select_key: str) -> dict[str, Any] | None:
    """Legacy API — community packs ignore username."""
    return load_pack_by_select_key(select_key)


def _load_legacy_user_pack(pack_id: str) -> dict[str, Any] | None:
    for d in USER_STYLES_ROOT.iterdir() if USER_STYLES_ROOT.exists() else []:
        path = d / f"{pack_id}.json"
        if path.exists():
            return json.loads(path.read_text(encoding="utf-8"))
    return None


def _split_paragraphs(text: str) -> list[str]:
    parts = re.split(r"\n\s*\n+", text.strip())
    chunks: list[str] = []
    for p in parts:
        p = re.sub(r"\s+", " ", p).strip()
        if len(p) >= _CHUNK_MIN_LEN:
            chunks.append(p[:4000])
    if not chunks and len(text.strip()) >= _CHUNK_MIN_LEN:
        chunks.append(text.strip()[:4000])
    return chunks


def _embed_texts(texts: list[str], openai_client: Any) -> np.ndarray:
    resp = openai_client.embeddings.create(model="text-embedding-3-small", input=texts)
    vecs = np.array([d.embedding for d in resp.data], dtype=np.float32)
    norms = np.linalg.norm(vecs, axis=1, keepdims=True)
    norms[norms == 0] = 1.0
    return vecs / norms


def find_similar_chunks(
    pack_id: str,
    query: str,
    top_k: int = 3,
    openai_client: Any | None = None,
) -> list[dict[str, Any]]:
    idx_path = _index_path(pack_id)
    if not idx_path.exists() or not openai_client:
        return []
    data = np.load(str(idx_path), allow_pickle=False)
    vecs: np.ndarray = data["vectors"]
    texts = data["texts"]
    q = _embed_texts([query], openai_client)[0]
    scores = vecs @ q
    top_idx = np.argsort(scores)[::-1][:top_k]
    out = []
    for i in top_idx:
        sim = float(scores[i])
        if sim < 0.2:
            break
        out.append({
            "text": str(texts[i]),
            "similarity": round(sim, 4),
            "source": "community_upload",
        })
    return out


def find_similar_user_chunks(
    _username: str,
    pack_id: str,
    query: str,
    top_k: int = 3,
    openai_client: Any | None = None,
) -> list[dict[str, Any]]:
    return find_similar_chunks(pack_id, query, top_k=top_k, openai_client=openai_client)


def _load_all_chunks_for_pack(pack_id: str, papers: list[dict[str, Any]]) -> list[str]:
    chunks: list[str] = []
    for p in papers:
        h = p.get("sha256")
        if not h:
            continue
        path = _text_store_path(pack_id, h)
        if not path.exists():
            continue
        text = path.read_text(encoding="utf-8", errors="ignore")
        chunks.extend(_split_paragraphs(text))
    return chunks[:_CHUNK_MAX]


def learn_from_uploads(
    *,
    contributor: str,
    journal_display_name: str,
    article_type: str,
    papers: list[dict[str, str]],
    linked_journal_key: str | None = None,
    corpus_supplement: list[dict[str, str]] | None = None,
    call_claude: Any | None = None,
    openai_client: Any | None = None,
) -> dict[str, Any]:
    """
    Merge papers into a platform-wide pack for this journal.

    papers: [{title, text, kind}] kind = target_journal | similar
    """
    if not contributor:
        raise ValueError("Login required to contribute exemplar papers.")
    if not journal_display_name.strip():
        raise ValueError("journal_display_name is required.")
    if corpus_supplement:
        papers = list(papers) + list(corpus_supplement)
    if not papers:
        raise ValueError("At least one paper is required.")
    if len(papers) > MAX_PAPERS_PER_UPLOAD + 10:
        raise ValueError(f"Too many papers in one request (max {MAX_PAPERS_PER_UPLOAD + 10}).")

    target_in_batch = sum(
        1 for p in papers if (p.get("kind") or "target_journal") in TARGET_KINDS
    )
    if target_in_batch < MIN_TARGET_JOURNAL_PAPERS_PER_UPLOAD:
        raise ValueError(
            f"At least {MIN_TARGET_JOURNAL_PAPERS_PER_UPLOAD} target-journal paper required per upload "
            f"(got {target_in_batch}). Similar-style papers alone are not enough."
        )

    new_texts: list[str] = []
    new_meta: list[dict[str, str]] = []
    total_chars = 0

    for i, p in enumerate(papers):
        text = (p.get("text") or "").strip()
        if len(text) < _MIN_CHARS_PER_PAPER:
            raise ValueError(f"Paper {i + 1} is too short (min {_MIN_CHARS_PER_PAPER} characters).")
        if len(text) > _MAX_CHARS_PER_PAPER:
            text = text[:_MAX_CHARS_PER_PAPER]
        total_chars += len(text)
        title = (p.get("title") or f"Paper {i + 1}").strip()
        kind = (p.get("kind") or "target_journal").strip()
        h = _paper_hash(text)
        new_meta.append({
            "title": title,
            "kind": kind,
            "chars": str(len(text)),
            "sha256": h,
            "uploaded_by": contributor if kind not in ("corpus_target", "corpus_similar") else "corpus_ai",
            "uploaded_at": _now(),
            "source": p.get("source") or ("corpus_ai" if kind.startswith("corpus_") else "customer_upload"),
            "pmid": p.get("pmid"),
        })
        new_texts.append(text)

    if total_chars < _MIN_CHARS_TOTAL:
        raise ValueError(f"Total text too short (min {_MIN_CHARS_TOTAL} characters).")

    pack_id = pack_id_for_journal(journal_display_name)
    slug = journal_slug(journal_display_name)
    existing = load_community_pack(pack_id) or {}

    old_papers: list[dict[str, Any]] = list(existing.get("papers") or [])
    seen_hashes = {p.get("sha256") for p in old_papers if p.get("sha256")}

    merged_papers = list(old_papers)
    added = 0
    for meta, text in zip(new_meta, new_texts):
        if meta["sha256"] in seen_hashes:
            continue
        seen_hashes.add(meta["sha256"])
        _text_store_path(pack_id, meta["sha256"]).write_text(text, encoding="utf-8")
        merged_papers.append(meta)
        added += 1

    if len(merged_papers) > MAX_ACCUMULATED_PAPERS:
        merged_papers = merged_papers[-MAX_ACCUMULATED_PAPERS:]

    all_chunks = _load_all_chunks_for_pack(pack_id, merged_papers)

    target_count, similar_count, corpus_t, corpus_s = _count_by_kind(merged_papers)
    tier = _coverage_tier(target_count, similar_count)

    contributors = list(existing.get("contributors") or [])
    if contributor not in contributors:
        contributors.append(contributor)

    profile: dict[str, Any] | None = existing.get("profile")
    profile_error: str | None = None

    should_profile = call_claude and target_count >= MIN_PAPERS_FOR_PROFILE and len(all_chunks) >= 2
    if should_profile:
        prompt_path = PROMPTS_DIR / "learn_user_style.system.md"
        system = prompt_path.read_text(encoding="utf-8") if prompt_path.exists() else ""
        sample = "\n\n---\n\n".join(all_chunks[:16])[:28_000]
        user_content = (
            f"## journal_display_name\n{journal_display_name}\n\n"
            f"## article_type\n{article_type}\n\n"
            f"## target_journal_paper_count\n{target_count}\n\n"
            f"## similar_paper_count\n{similar_count}\n\n"
            f"## coverage_tier\n{tier}\n\n"
            f"## exemplar_paragraphs\n{sample}\n\n"
            "Output ONE JSON object only."
        )
        try:
            raw = call_claude(system, user_content)
            profile = json.loads(raw)
            profile["source_paper_count"] = len(merged_papers)
            profile["target_journal_paper_count"] = target_count
            profile["verification_status"] = "community_upload"
            profile["generated_at"] = _now()
        except Exception as exc:
            profile_error = str(exc)

    if openai_client and all_chunks:
        vecs = _embed_texts(all_chunks, openai_client)
        np.savez_compressed(
            str(_index_path(pack_id)),
            vectors=vecs,
            texts=np.array(all_chunks, dtype=object),
        )

    record = {
        "pack_id": pack_id,
        "journal_slug": slug,
        "journal_display_name": journal_display_name,
        "linked_journal_key": linked_journal_key or existing.get("linked_journal_key"),
        "article_type": article_type,
        "papers": merged_papers,
        "target_journal_paper_count": target_count,
        "similar_paper_count": similar_count,
        "corpus_target_count": corpus_t,
        "corpus_similar_count": corpus_s,
        "coverage_tier": tier,
        "chunk_count": len(all_chunks),
        "profile": profile,
        "profile_error": profile_error,
        "contributors": contributors,
        "created_at": existing.get("created_at") or _now(),
        "updated_at": _now(),
        "disclaimer": (
            "Style learned from customer uploads and/or OA corpus retrieval (cadence only — do not copy). "
            "Not official journal instructions. Use curated journal specs for submission format rules."
        ),
        "guidance": LEARNING_GUIDANCE,
    }

    _pack_path(pack_id).write_text(
        json.dumps(record, indent=2, ensure_ascii=False),
        encoding="utf-8",
    )

    msg_parts = [
        f"Platform style pack updated (+{added} new paper{'s' if added != 1 else ''}, "
        f"{record['chunk_count']} paragraphs indexed).",
        f"Target-journal papers accumulated: {target_count} ({tier}).",
    ]
    if tier != "strong":
        msg_parts.append(
            f"Hybrid target: ≥{RECOMMENDED_TARGET_JOURNAL_PAPERS} target-journal + "
            f"≥{RECOMMENDED_SIMILAR_PAPERS} similar exemplars "
            f"(now {target_count}+{similar_count}; corpus AI can help fill gaps)."
        )
    elif profile:
        msg_parts.append("Profile summary refreshed.")
    elif target_count < MIN_PAPERS_FOR_PROFILE:
        msg_parts.append(
            f"Profile summary unlocks at {MIN_PAPERS_FOR_PROFILE}+ target-journal papers "
            f"(currently {target_count})."
        )

    return {
        "pack_id": pack_id,
        "journal_select_key": journal_select_key(pack_id),
        "journal_display_name": journal_display_name,
        "chunk_count": record["chunk_count"],
        "papers_added": added,
        "target_journal_paper_count": target_count,
        "similar_paper_count": similar_count,
        "coverage_tier": tier,
        "corpus_target_count": corpus_t,
        "corpus_similar_count": corpus_s,
        "profile_ready": profile is not None,
        "profile_error": profile_error,
        "message": " ".join(msg_parts),
        "guidance": LEARNING_GUIDANCE,
    }


def exemplar_texts_for_pack(
    pack: dict[str, Any],
    article_type: str = "research",
    max_fulltexts: int | None = None,
) -> list[str]:
    """
    Load stored exemplar bodies for style QA / plagiarism checks.

    Priority: customer-uploaded papers first (kind='target_journal' or 'similar'),
    corpus-augmented papers second (kind='corpus_target' or 'corpus_similar').
    Within each tier, reviews come before research papers (broader context first).

    Respects FULLTEXT_LIMITS per article_type when max_fulltexts is None.
    """
    pack_id = pack.get("pack_id", "")
    limit = max_fulltexts or (
        FULLTEXT_LIMITS.get(article_type, FULLTEXT_LIMITS["research"])["max"]
    )

    # Sort: customer uploads (no corpus prefix) first, corpus second; reviews first within each tier
    def _sort_key(p: dict[str, Any]) -> tuple[int, int]:
        kind = p.get("kind") or "target_journal"
        is_corpus = 1 if "corpus" in kind else 0
        is_review = 0 if "review" in (p.get("paper_type") or "") else 1
        return (is_corpus, is_review)

    papers = sorted(pack.get("papers") or [], key=_sort_key)

    texts: list[str] = []
    for p in papers:
        if len(texts) >= limit:
            break
        h = p.get("sha256")
        if not h or not pack_id:
            continue
        path = _text_store_path(pack_id, h)
        if path.exists():
            texts.append(path.read_text(encoding="utf-8", errors="ignore")[:8000])
    return texts
