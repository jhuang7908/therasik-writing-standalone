"""
Customer upload intake: quality gate, relevance review, archive routing.

Policy
------
- Learn tone/cadence only — never treat uploads as text to copy.
- Target pack: only relevance-passed papers for the requested journal.
- Misfit but readable papers → auto-classified archive packs (not wasted).
- Spam / hostile low-quality feeds → rejected (logged, not indexed).
- Always require >= 2 customer target-journal PDFs per batch (even if vector corpus covers the journal).
"""

from __future__ import annotations

import json
import re
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from .user_style import (
    MIN_TARGET_JOURNAL_PAPERS_PER_UPLOAD,
    TARGET_KINDS,
    _paper_hash,
    _slugify,
    journal_select_key,
    pack_id_for_journal,
)

_HERE = Path(__file__).resolve().parent
AUDIT_LOG = Path(
    __import__("os").environ.get(
        "WM_UPLOAD_AUDIT_LOG",
        str(_HERE / "data" / "upload_intake_audit.jsonl"),
    )
)

MIN_CUSTOMER_TARGET_PDF_ALWAYS = 2
MIN_CUSTOMER_PDF_IF_NO_CORPUS = 2  # alias; kept for messages when corpus is thin
RECOMMENDED_CUSTOMER_TARGET_PDF = 5
RECOMMENDED_CUSTOMER_FOR_NO_CORPUS = 3
RELEVANCE_PASS = 0.32
RELEVANCE_ARCHIVE = 0.18
CORPUS_COVER_MIN_HITS = 2
CORPUS_COVER_MIN_SIM = 0.26
MIN_QUALITY_WORDS = 80
MIN_QUALITY_UNIQUE_RATIO = 0.12
MAX_REPEAT_CHAR_RUN = 40


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


def _word_stats(text: str) -> dict[str, Any]:
    words = re.findall(r"[a-zA-Z]{2,}", text.lower())
    if not words:
        return {"word_count": 0, "unique_ratio": 0.0}
    return {
        "word_count": len(words),
        "unique_ratio": len(set(words)) / len(words),
    }


def quality_gate(text: str, title: str = "") -> dict[str, Any]:
    """Block obvious spam / non-article garbage before relevance scoring."""
    t = (text or "").strip()
    issues: list[str] = []
    if len(t) < 400:
        issues.append("too_short")
    stats = _word_stats(t[:12_000])
    if stats["word_count"] < MIN_QUALITY_WORDS:
        issues.append("too_few_words")
    if stats["unique_ratio"] < MIN_QUALITY_UNIQUE_RATIO:
        issues.append("low_lexical_diversity")
    if re.search(r"(.)\1{" + str(MAX_REPEAT_CHAR_RUN) + r",}", t):
        issues.append("repeated_char_runs")
    alpha = sum(1 for c in t if c.isalpha())
    if len(t) > 200 and alpha / len(t) < 0.45:
        issues.append("low_alpha_ratio")
    spam_markers = ("lorem ipsum", "as an ai language model", "click here", "buy now")
    lower = t.lower()
    for m in spam_markers:
        if m in lower:
            issues.append(f"spam_marker:{m}")
    verdict = "pass" if not issues else "fail"
    return {
        "verdict": verdict,
        "issues": issues,
        "word_count": stats["word_count"],
        "unique_ratio": round(stats["unique_ratio"], 4),
        "title": title,
    }


def _journal_name_overlap(requested: str, text: str) -> float:
    """Cheap signal: fraction of requested journal tokens found in text."""
    req_tokens = [w for w in re.findall(r"[a-zA-Z0-9]+", requested.lower()) if len(w) > 2]
    if not req_tokens:
        return 0.0
    lower = text.lower()[:20_000]
    hits = sum(1 for w in req_tokens if w in lower)
    return hits / len(req_tokens)


def _embedding_relevance(
    text: str,
    journal_display_name: str,
    article_type: str,
    openai_client: Any,
) -> float:
    from .user_style import _embed_texts

    sample = text[:4000]
    query = (
        f"{journal_display_name} peer-reviewed {article_type} scientific article "
        "discussion introduction methods"
    )
    try:
        vecs = _embed_texts([sample, query], openai_client)
        return float(vecs[0] @ vecs[1])
    except Exception:
        return 0.0


def corpus_covers_journal(
    journal_display_name: str,
    linked_journal_key: str | None,
) -> dict[str, Any]:
    from .vector_store import search_chunks, vector_backend_status

    if vector_backend_status().get("active_backend") == "none":
        return {
            "covers": False,
            "reason": "no_vector_backend",
            "hit_count": 0,
            "top_similarity": 0.0,
        }

    hits = search_chunks(
        f"{journal_display_name} research article discussion",
        journal=linked_journal_key if linked_journal_key in ("pnas", "elife", "plos_med") else None,
        section="discussion",
        top_k=8,
    )
    if not hits:
        hits = search_chunks(f"{journal_display_name} biomedical research", top_k=8)
    good = [h for h in hits if float(h.get("similarity") or 0) >= CORPUS_COVER_MIN_SIM]
    top_sim = max((float(h.get("similarity") or 0) for h in hits), default=0.0)
    covers = len(good) >= CORPUS_COVER_MIN_HITS
    return {
        "covers": covers,
        "reason": "ok" if covers else "insufficient_corpus_hits",
        "hit_count": len(good),
        "top_similarity": round(top_sim, 4),
    }


def _detect_archive_journal(text: str, title: str) -> str:
    """Infer a coarse archive label from title/first lines (no waste bucket)."""
    head = f"{title}\n{text[:2500]}".lower()
    if "nature" in head:
        return "Nature-family (auto-classified)"
    if "lancet" in head:
        return "The Lancet (auto-classified)"
    if "cell " in head or "molecular cell" in head:
        return "Cell Press (auto-classified)"
    if "plos" in head:
        return "PLOS (auto-classified)"
    if "bmj" in head:
        return "BMJ (auto-classified)"
    if re.search(r"\breview\b", head):
        return "Review article style (auto-classified)"
    if re.search(r"\bcase report\b", head):
        return "Case report style (auto-classified)"
    return "General biomedical archive (auto-classified)"


def review_single_paper(
    paper: dict[str, str],
    *,
    journal_display_name: str,
    article_type: str,
    openai_client: Any | None,
) -> dict[str, Any]:
    title = paper.get("title") or "Upload"
    text = (paper.get("text") or "").strip()
    kind = paper.get("kind") or "target_journal"

    q = quality_gate(text, title)
    if q["verdict"] == "fail":
        return {
            "decision": "rejected",
            "reason": "quality_gate_fail",
            "quality": q,
            "relevance_score": None,
            "archive_journal": None,
        }

    embed_sim = 0.0
    if openai_client:
        embed_sim = _embedding_relevance(text, journal_display_name, article_type, openai_client)
    name_overlap = _journal_name_overlap(journal_display_name, text)
    relevance = 0.65 * embed_sim + 0.35 * name_overlap

    if kind in ("similar",):
        pass_threshold = RELEVANCE_ARCHIVE
    else:
        pass_threshold = RELEVANCE_PASS

    if relevance >= pass_threshold:
        decision = "accepted"
        reason = "relevance_pass"
        archive_journal = None
    elif relevance >= RELEVANCE_ARCHIVE:
        decision = "archived"
        reason = "misfit_archived"
        archive_journal = _detect_archive_journal(text, title)
    else:
        decision = "rejected"
        reason = "low_relevance"
        archive_journal = None

    return {
        "decision": decision,
        "reason": reason,
        "quality": q,
        "relevance_score": round(relevance, 4),
        "embed_similarity": round(embed_sim, 4),
        "name_overlap": round(name_overlap, 4),
        "archive_journal": archive_journal,
        "sha256": _paper_hash(text),
    }


def _append_audit(record: dict[str, Any]) -> None:
    try:
        AUDIT_LOG.parent.mkdir(parents=True, exist_ok=True)
        with AUDIT_LOG.open("a", encoding="utf-8") as f:
            f.write(json.dumps(record, ensure_ascii=False) + "\n")
    except Exception:
        pass


def process_upload_intake(
    customer_papers: list[dict[str, str]],
    *,
    journal_display_name: str,
    article_type: str,
    linked_journal_key: str | None,
    contributor: str,
    openai_client: Any | None,
    call_claude: Any | None = None,
    run_term_extraction: bool = True,
) -> dict[str, Any]:
    """
    Review customer uploads; split into accepted / archived / rejected.
    Enforces >= MIN_CUSTOMER_TARGET_PDF_ALWAYS customer target-journal PDFs per batch.
    """
    corpus = corpus_covers_journal(journal_display_name, linked_journal_key)
    customer_target = [
        p for p in customer_papers
        if (p.get("kind") or "target_journal") in TARGET_KINDS
        and not str(p.get("kind", "")).startswith("corpus_")
    ]

    if len(customer_target) < MIN_CUSTOMER_TARGET_PDF_ALWAYS:
        return {
            "can_proceed": False,
            "block_reason": (
                f"Each learn batch requires at least {MIN_CUSTOMER_TARGET_PDF_ALWAYS} "
                f"customer target-journal PDFs (got {len(customer_target)}). "
                "Vector corpus supplement cannot replace customer PDFs. "
                "Tone/cadence learning only — not copying."
            ),
            "corpus_coverage": corpus,
            "accepted": [],
            "archived": [],
            "rejected": [],
            "report": [],
        }

    if not customer_papers and not corpus["covers"]:
        return {
            "can_proceed": False,
            "block_reason": "No customer papers and no corpus coverage.",
            "corpus_coverage": corpus,
            "accepted": [],
            "archived": [],
            "rejected": [],
            "report": [],
        }

    accepted: list[dict[str, str]] = []
    archived: list[dict[str, Any]] = []
    rejected: list[dict[str, Any]] = []
    report: list[dict[str, Any]] = []

    for i, paper in enumerate(customer_papers):
        rev = review_single_paper(
            paper,
            journal_display_name=journal_display_name,
            article_type=article_type,
            openai_client=openai_client,
        )
        row = {
            "index": i + 1,
            "title": paper.get("title"),
            "kind": paper.get("kind"),
            **rev,
        }
        report.append(row)

        enriched = dict(paper)
        enriched["intake_relevance"] = str(rev.get("relevance_score") or "")
        enriched["intake_quality"] = rev.get("quality", {}).get("verdict", "")

        if rev["decision"] == "accepted":
            enriched["kind"] = paper.get("kind") or "target_journal"
            accepted.append(enriched)
        elif rev["decision"] == "archived":
            enriched["kind"] = "archive_misfit"
            enriched["original_kind"] = paper.get("kind")
            archived.append({
                "paper": enriched,
                "archive_journal": rev["archive_journal"] or "General archive",
            })
        else:
            rejected.append(row)

        _append_audit({
            "at": _now(),
            "contributor": contributor,
            "requested_journal": journal_display_name,
            "title": paper.get("title"),
            "sha256": rev.get("sha256"),
            "decision": rev["decision"],
            "reason": rev["reason"],
            "relevance": rev.get("relevance_score"),
        })

    if not accepted and not archived:
        return {
            "can_proceed": False,
            "block_reason": (
                "No uploads passed intake. Add higher-quality PDFs from the target journal "
                "or clearly related same-field papers. Suspicious/low-relevance files were rejected."
            ),
            "corpus_coverage": corpus,
            "accepted": [],
            "archived": [],
            "rejected": rejected,
            "report": report,
        }

    accepted_target = [p for p in accepted if (p.get("kind") or "") in TARGET_KINDS]
    if len(accepted_target) < MIN_TARGET_JOURNAL_PAPERS_PER_UPLOAD:
        return {
            "can_proceed": False,
            "block_reason": (
                "No target-journal PDF passed relevance review for this journal. "
                "Upload more on-journal full texts (tone/cadence learning — not copying)."
            ),
            "corpus_coverage": corpus,
            "accepted": accepted,
            "archived": archived,
            "rejected": rejected,
            "report": report,
        }

    # Terminology extraction — run on accepted papers, non-blocking
    term_extraction_results: list[dict[str, Any]] = []
    if run_term_extraction and call_claude and accepted:
        try:
            from .term_registry import extract_and_merge as _term_extract
            from .user_style import journal_slug
            field_key = journal_slug(journal_display_name)
            for p in accepted[:6]:  # cap: max 6 papers per batch
                text = (p.get("text") or "").strip()
                if not text:
                    continue
                result = _term_extract(
                    field_key=field_key,
                    text=text,
                    source_id=p.get("sha256") or _paper_hash(text),
                    call_claude=call_claude,
                )
                term_extraction_results.append(result)
        except Exception as exc:
            term_extraction_results.append({"error": str(exc)})

    return {
        "can_proceed": True,
        "block_reason": None,
        "corpus_coverage": corpus,
        "accepted": accepted,
        "archived": archived,
        "rejected": rejected,
        "report": report,
        "requires_more_customer_pdfs": len(accepted_target) < RECOMMENDED_CUSTOMER_TARGET_PDF,
        "accepted_target_count": len(accepted_target),
        "min_customer_target_required": MIN_CUSTOMER_TARGET_PDF_ALWAYS,
        "term_extraction": term_extraction_results,
    }
