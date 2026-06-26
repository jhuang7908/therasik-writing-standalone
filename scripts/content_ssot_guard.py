#!/usr/bin/env python3
"""DeepSeek write + Kimi review + DeepSeek fix gate for media/PPT SSOT."""
from __future__ import annotations

import json
import os
import re
import sys
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parent.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

CG = ROOT / "content_generation_tools"
REVIEWER_PROMPT = CG / "academic_ppt_prompts" / "06_reviewer_system.md"
FIXER_PROMPT = CG / "academic_ppt_prompts" / "07_fix_system.md"

_PMID_RE = re.compile(r"PMID[:\s]*(\d{6,8})", re.I)
_DOI_RE = re.compile(r"(?:DOI[:\s]*|doi[:\s]*)(10\.\d{4,}/[^\s\",\\]]+)", re.I)
_EN_TOKEN_RE = re.compile(r"[A-Za-z0-9][A-Za-z0-9+\-/]{1,24}")
_TOPIC_PREFIX_RE = re.compile(r"^[①②③④⑤⑥⑦⑧⑨⑩\d\.\s\-\*]+")


def load_env() -> None:
    env_paths = [Path("/etc/insynbio/finance-xhs.env"), CG / ".env"]
    for env_path in env_paths:
        if not env_path.exists():
            continue
        for line in env_path.read_text(encoding="utf-8").splitlines():
            line = line.strip()
            if not line or line.startswith("#") or "=" not in line:
                continue
            k, _, v = line.partition("=")
            key = k.strip()
            val = v.strip()
            if not key or not val:
                continue
            # Keep existing unless empty
            if not (os.environ.get(key) or "").strip():
                os.environ[key] = val


def _strip_json(text: str) -> str:
    t = text.strip()
    # Robustly extract JSON block bounded by outer curly braces
    first_brace = t.find("{")
    last_brace = t.rfind("}")
    if first_brace != -1 and last_brace != -1 and last_brace > first_brace:
        return t[first_brace:last_brace+1]
    
    if t.startswith("```"):
        t = re.sub(r"^```\w*\n?", "", t)
        t = re.sub(r"\n?```$", "", t)
    return t.strip()


def _openai_compat_chat(
    *,
    api_key: str,
    base_url: str,
    model: str,
    system: str,
    user: str,
    temperature: float = 0.2,
    max_tokens: int = 8000,
) -> str:
    from openai import OpenAI  # type: ignore

    client = OpenAI(api_key=api_key, base_url=base_url, timeout=300.0)
    rsp = client.chat.completions.create(
        model=model,
        temperature=temperature,
        max_tokens=max_tokens,
        messages=[
            {"role": "system", "content": system},
            {"role": "user", "content": user},
        ],
    )
    return rsp.choices[0].message.content or ""


def deepseek_chat(system: str, user: str, *, model: str = "deepseek-chat") -> str:
    api_key = os.environ.get("DEEPSEEK_API_KEY")
    if not api_key:
        raise RuntimeError("Missing DEEPSEEK_API_KEY")
    base = os.environ.get("DEEPSEEK_API_BASE", "https://api.deepseek.com/v1")
    return _openai_compat_chat(
        api_key=api_key, base_url=base, model=model, system=system, user=user
    )


def kimi_chat(system: str, user: str, *, model: str = "kimi-k2.6") -> str:
    api_key = os.environ.get("MOONSHOT_API_KEY") or os.environ.get("KIMI_API_KEY")
    if not api_key:
        raise RuntimeError("Missing KIMI_API_KEY")
    base = os.environ.get("KIMI_BASE_URL", "https://api.moonshot.cn/v1")
    return _openai_compat_chat(
        api_key=api_key,
        base_url=base,
        model=model,
        system=system,
        user=user,
        temperature=1.0,
    )


def openai_chat(system: str, user: str, *, model: str = "gpt-4o") -> str:
    api_key = os.environ.get("OPENAI_API_KEY")
    if not api_key:
        raise RuntimeError("Missing OPENAI_API_KEY")
    base = os.environ.get("OPENAI_API_BASE", "https://api.openai.com/v1")
    return _openai_compat_chat(
        api_key=api_key,
        base_url=base,
        model=model,
        system=system,
        user=user,
        temperature=0.2,
    )


def gemini_chat_llm(system: str, user: str, *, model: str = "gemini-2.5-pro") -> str:
    key = os.environ.get("GEMINI_API_KEY")
    if not key:
        raise RuntimeError("Missing GEMINI_API_KEY")
    base = os.environ.get("GEMINI_BASE_URL", "https://generativelanguage.googleapis.com/v1beta/openai")
    return _openai_compat_chat(
        api_key=key,
        base_url=base,
        model=model,
        system=system,
        user=user,
        temperature=0.2,
    )


def anthropic_chat_llm(system: str, user: str, *, model: str = "claude-3-5-sonnet-20241022") -> str:
    import anthropic
    api_key = os.environ.get("ANTHROPIC_API_KEY")
    if not api_key:
        raise RuntimeError("Missing ANTHROPIC_API_KEY")
    client = anthropic.Anthropic(api_key=api_key)
    message = client.messages.create(
        model=model,
        max_tokens=8000,
        temperature=0.2,
        system=system,
        messages=[
            {"role": "user", "content": user}
        ]
    )
    return message.content[0].text


def qwen_chat(system: str, user: str, *, model: str | None = None) -> str:
    api_key = os.environ.get("DASHSCOPE_API_KEY") or os.environ.get("QWEN_API_KEY")
    if not api_key:
        raise RuntimeError("Missing DASHSCOPE_API_KEY")
    base = os.environ.get(
        "DASHSCOPE_BASE_URL",
        "https://dashscope.aliyuncs.com/compatible-mode/v1",
    )
    model = model or os.environ.get("QWEN_MODEL", "qwen-plus")
    return _openai_compat_chat(
        api_key=api_key,
        base_url=base,
        model=model,
        system=system,
        user=user,
    )


def _is_retryable_llm_error(exc: BaseException) -> bool:
    msg = str(exc).lower()
    if any(
        k in msg
        for k in (
            "insufficient",
            "quota",
            "balance",
            "rate limit",
            "timeout",
            "connection",
            "missing",
            "unavailable",
            "overloaded",
        )
    ):
        return True
    code = getattr(exc, "status_code", None)
    return code in (402, 429, 500, 502, 503, 529)


def resilient_chat(
    system: str,
    user: str,
    *,
    role: str = "writer",
) -> tuple[str, str]:
    """Try LLM chain without stopping. Returns (text, provider_used)."""
    load_env()
    if role == "reviewer":
        chain: list[tuple[str, Any]] = [
            ("gemini", lambda s, u: gemini_chat_llm(s, u)),
            ("kimi", lambda s, u: kimi_chat(s, u)),
            ("deepseek", lambda s, u: deepseek_chat(s, u)),
            ("openai", lambda s, u: openai_chat(s, u)),
        ]
    else:
        chain = [
            ("gemini", lambda s, u: gemini_chat_llm(s, u)),
            ("kimi", lambda s, u: kimi_chat(s, u)),
            ("deepseek", lambda s, u: deepseek_chat(s, u)),
            ("openai", lambda s, u: openai_chat(s, u)),
        ]

    errors: list[dict[str, str]] = []
    for name, fn in chain:
        try:
            print(f"  [LLM] Attempting {name} for {role}...")
            res = fn(system, user)
            print(f"  [LLM] {name} succeeded!")
            return res, name
        except Exception as exc:
            print(f"  [LLM] {name} failed: {str(exc)[:150]}")
            errors.append({name: str(exc)[:240]})
            if not _is_retryable_llm_error(exc) and name != chain[-1][0]:
                continue
            continue
    raise RuntimeError(f"All LLM providers failed ({role}): {errors}")


def writer_chat(system: str, user: str) -> tuple[str, str]:
    return resilient_chat(system, user, role="writer")


def fixer_chat(system: str, user: str) -> tuple[str, str]:
    return resilient_chat(system, user, role="fixer")


def reviewer_chat(system: str, user: str) -> tuple[str, str]:
    return resilient_chat(system, user, role="reviewer")


def _topic_for_verify(topic: str, line: str) -> str:
    """English entity tokens for cross-lingual title matching (no embedding API)."""
    noise = {"PMID", "DOI", "HTTP", "HTTPS", "WWW", "ET", "AL"}
    tokens = _EN_TOKEN_RE.findall(f"{topic} {line}")
    kept = [t for t in tokens if t.upper() not in noise and not t.isdigit()]
    return " ".join(kept) if kept else topic.strip()


def _extract_doi_from_line(line: str) -> str:
    m = _DOI_RE.search(line)
    if m:
        return m.group(1).rstrip(".,;\"'\\")
    m2 = re.search(r"(10\.\d{4,}/[^\s\"'\\>,]+)", line)
    return m2.group(1).rstrip(".,;\"'\\") if m2 else ""


def extract_citation_claims(text: str) -> list[dict[str, str]]:
    """Find PMID/DOI lines in SSOT JSON or markdown; never trust LLM IDs without audit."""
    claims: list[dict[str, str]] = []
    seen: set[tuple[str, str]] = set()
    for line in text.splitlines():
        pmid_m = _PMID_RE.search(line)
        if not pmid_m:
            continue
        pmid = pmid_m.group(1)
        doi = _extract_doi_from_line(line)
        before = line[: pmid_m.start()]
        topic = _TOPIC_PREFIX_RE.sub("", before.strip())
        topic = re.sub(r"[：:]\s*$", "", topic).strip().strip("\"'")
        key = (pmid, doi)
        if key in seen:
            continue
        seen.add(key)
        claims.append(
            {
                "topic": topic or f"PMID {pmid}",
                "pmid": pmid,
                "doi": doi,
                "line": line.strip()[:240],
            }
        )
    return claims


def _normalize_doi(doi: str) -> str:
    return doi.strip().lower().rstrip(".")


def _record_match_text(record: Any) -> str:
    abstract = getattr(record, "abstract", "") or ""
    return f"{record.title}\n{abstract}"[:2000]


def _keyword_match_score(topic: str, line: str, record: Any) -> float:
    """Token hit rate in PubMed title+abstract (works without OpenAI, cross-lingual labels)."""
    noise = {"PMID", "DOI", "HTTP", "HTTPS", "WWW", "ET", "AL", "CR", "HU", "PBMC"}
    text = _record_match_text(record).lower()
    tokens = [
        t.lower()
        for t in _EN_TOKEN_RE.findall(f"{topic} {line}")
        if len(t) >= 3 and t.upper() not in noise
    ]
    if not tokens:
        return 0.0
    hits = sum(1 for t in tokens if t in text)
    return hits / len(tokens)


def _score_topic_match(topic: str, line: str, record: Any) -> tuple[float, str, str]:
    """
    Returns (score, verdict, method).
    Prefer embedding when OpenAI is available; else keyword + Jaccard on title.
    """
    from services.writing_memory.references.verify import (
        PARTIAL_THRESHOLD,
        VERIFY_THRESHOLD,
        title_jaccard,
        topic_record_similarity,
    )

    verify_topic = _topic_for_verify(topic, line)
    method = "keyword"
    score = _keyword_match_score(verify_topic, line, record)
    if score >= 0.34:
        return score, "verified", method

    try:
        emb = topic_record_similarity(verify_topic, record)
        method = "embedding"
        score = max(score, emb)
    except Exception:
        jaccard = title_jaccard(verify_topic, record.title)
        score = max(score, jaccard)
        method = "jaccard"

    if score >= VERIFY_THRESHOLD:
        verdict = "verified"
    elif score >= max(PARTIAL_THRESHOLD, 0.20):
        verdict = "partial"
    elif score >= 0.12:
        verdict = "partial"
    else:
        verdict = "unverified"
    return score, verdict, method


def audit_citations(content_ssot: str) -> dict[str, Any]:
    """
    Hard gate: every PMID must exist in PubMed AND match the claimed topic.
    Reuses writing_memory verify.py (embedding + CrossRef) when available.
    """
    from services.writing_memory.references.pubmed_client import fetch_by_pmid

    claims = extract_citation_claims(content_ssot)
    if not claims:
        return {"status": "PASS", "citations": [], "fact_errors": []}

    rows: list[dict[str, Any]] = []
    fact_errors: list[dict[str, str]] = []

    for claim in claims:
        pmid = claim["pmid"]
        record = fetch_by_pmid(pmid)
        if record is None:
            fact_errors.append(
                {
                    "location": claim["line"][:80],
                    "claim": f"PMID {pmid}",
                    "issue": "PMID not found in PubMed",
                    "severity": "high",
                }
            )
            rows.append({**claim, "verdict": "missing", "pubmed_title": ""})
            continue

        score, verdict, method = (0.0, "unverified", "none")
        claimed_doi = claim.get("doi") or ""
        doi_verified = bool(
            claimed_doi and record.doi
            and _normalize_doi(claimed_doi) == _normalize_doi(record.doi)
        )
        if doi_verified:
            score, verdict, method = 1.0, "verified", "doi_match"
        else:
            if claimed_doi and record.doi:
                verdict = "conflict"
                fact_errors.append(
                    {
                        "location": claim["line"][:80],
                        "claim": f"DOI {claimed_doi}",
                        "issue": (
                            f"DOI mismatch: PubMed record has {record.doi}; "
                            f"title={record.title[:100]}"
                        ),
                        "severity": "high",
                    }
                )
            else:
                score, verdict, method = _score_topic_match(
                    claim["topic"], claim["line"], record
                )

        if verdict in ("unverified", "conflict", "missing"):
            fact_errors.append(
                {
                    "location": claim["line"][:80],
                    "claim": claim["topic"][:120],
                    "issue": (
                        f"PMID {pmid} topic mismatch ({verdict}, "
                        f"score={score:.2f}, method={method}): {record.title[:120]}"
                    ),
                    "severity": "high",
                }
            )
        elif verdict == "partial":
            fact_errors.append(
                {
                    "location": claim["line"][:80],
                    "claim": claim["topic"][:120],
                    "issue": (
                        f"PMID {pmid} weak topic match (partial, "
                        f"score={score:.2f}, method={method}): "
                        f"{record.title[:100]}"
                    ),
                    "severity": "medium",
                }
            )

        rows.append(
            {
                **claim,
                "verdict": verdict,
                "similarity": round(float(score), 4),
                "match_method": method,
                "pubmed_title": record.title,
                "pubmed_doi": record.doi,
                "pubmed_journal": record.journal,
            }
        )

    hard_fail = any(e["severity"] == "high" for e in fact_errors)
    return {
        "status": "FAIL" if hard_fail else "PASS",
        "citations": rows,
        "fact_errors": fact_errors,
    }


def _merge_citation_audit(review: dict[str, Any], citation_audit: dict[str, Any]) -> dict[str, Any]:
    """Fold PubMed audit into Kimi review JSON."""
    merged = dict(review)
    cite_errors = citation_audit.get("fact_errors") or []
    if not cite_errors:
        merged["citation_audit"] = citation_audit
        return merged
    merged.setdefault("fact_errors", [])
    merged["fact_errors"] = list(merged["fact_errors"]) + cite_errors
    merged["citation_audit"] = citation_audit
    if citation_audit.get("status") == "FAIL":
        merged["status"] = "FAIL"
    return merged


def review_ssot(
    source_excerpt: str,
    content_ssot: str,
    *,
    content_type: str = "ppt",
    lang: str = "zh",
) -> dict[str, Any]:
    system = REVIEWER_PROMPT.read_text(encoding="utf-8")
    user = (
        f"content_type: {content_type}\nlang: {lang}\n\n"
        f"## 原文摘录\n{source_excerpt[:45000]}\n\n"
        f"## 待审查 SSOT\n{content_ssot[:50000]}\n"
    )
    raw, review_provider = reviewer_chat(system, user)
    text = _strip_json(raw)
    try:
        report = json.loads(text)
        report["_provider"] = review_provider
        return report
    except json.JSONDecodeError:
        return {
            "status": "FAIL",
            "fact_errors": [],
            "parse_error": raw[:500],
            "fix_instructions": ["审查输出非 JSON，请人工检查"],
            "_provider": review_provider,
        }


def fix_ssot(
    source_excerpt: str,
    content_ssot: str,
    review_report: dict[str, Any],
    *,
    content_type: str = "ppt",
) -> str:
    system = FIXER_PROMPT.read_text(encoding="utf-8")
    user = (
        f"content_type: {content_type}\n\n"
        f"## 原文摘录\n{source_excerpt[:45000]}\n\n"
        f"## 当前 SSOT\n{content_ssot[:50000]}\n\n"
        f"## 审查报告\n{json.dumps(review_report, ensure_ascii=False, indent=2)}\n"
    )
    raw, fix_provider = fixer_chat(system, user)
    fixed = _strip_json(raw)
    return fixed


def guarded_pipeline(
    source_excerpt: str,
    draft_ssot: str,
    *,
    content_type: str = "ppt",
    max_rounds: int = 2,
    skip_citation_audit: bool = False,
) -> dict[str, Any]:
    """Review → fix loop. Returns final SSOT and audit trail."""
    load_env()
    current = draft_ssot
    trail: list[dict[str, Any]] = []
    providers: list[str] = []

    if not skip_citation_audit:
        initial_cite = audit_citations(current)
        trail.append({"round": 0, "citation_audit": initial_cite})
        if initial_cite.get("status") == "FAIL":
            return {
                "content_ssot": current,
                "final_review": {"status": "FAIL", "citation_audit": initial_cite},
                "trail": trail,
                "providers": providers,
                "passed": False,
                "citation_gate_failed": True,
            }

    for i in range(max_rounds):
        try:
            report = review_ssot(source_excerpt, current, content_type=content_type)
        except Exception as exc:
            report = {
                "status": "WARN",
                "fact_errors": [],
                "fix_instructions": [],
                "review_skipped": str(exc)[:300],
            }
        if not skip_citation_audit:
            cite_audit = audit_citations(current)
            report = _merge_citation_audit(report, cite_audit)
            trail.append({"round": i + 1, "citation_audit": cite_audit})
        if report.get("_provider"):
            providers.append(f"review:{report['_provider']}")
        trail.append({"round": i + 1, "review": report})
        cite_ok = (
            skip_citation_audit
            or all(e.get("severity") != "high" for e in (report.get("fact_errors") or []))
        )
        if report.get("status") == "PASS" and not report.get("fact_errors") and cite_ok:
            break
        try:
            current = fix_ssot(source_excerpt, current, report, content_type=content_type)
        except Exception as exc:
            trail.append({"round": i + 1, "fix_error": str(exc)[:300]})
            break

    final_cite = (
        {"status": "SKIPPED"}
        if skip_citation_audit
        else audit_citations(current)
    )
    if not skip_citation_audit:
        trail.append({"round": "final", "citation_audit": final_cite})

    final_review: dict[str, Any] = {}
    for entry in reversed(trail):
        if "review" in entry:
            final_review = entry["review"]
            break

    cite_pass = skip_citation_audit or final_cite.get("status") == "PASS"
    review_pass = final_review.get("status") == "PASS" and not any(
        e.get("severity") == "high" for e in (final_review.get("fact_errors") or [])
    )
    return {
        "content_ssot": current,
        "final_review": final_review,
        "final_citation_audit": final_cite,
        "trail": trail,
        "providers": providers,
        "passed": review_pass and cite_pass,
        "citation_gate_failed": not cite_pass,
    }


def main() -> None:
    import argparse

    parser = argparse.ArgumentParser(description="Content SSOT guard + citation audit")
    parser.add_argument(
        "--audit-citations",
        metavar="FILE",
        help="Audit PMID/DOI topic match in a JSON or markdown SSOT file (exit 1 on FAIL)",
    )
    args = parser.parse_args()
    if args.audit_citations:
        path = Path(args.audit_citations)
        text = path.read_text(encoding="utf-8")
        report = audit_citations(text)
        print(json.dumps(report, ensure_ascii=False, indent=2))
        raise SystemExit(0 if report.get("status") == "PASS" else 1)
    parser.print_help()


if __name__ == "__main__":
    main()
