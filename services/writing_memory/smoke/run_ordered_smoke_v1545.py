"""
Ordered smoke test v15.45 — run on VPS localhost with Admin auth.

  Step 1: Same paragraph → /rewrite for elife, pnas, nejm (citation divergence)
  Step 2: huNSG-QUAD abstract → plan → draft key sections → QC score (before autofix)
  Step 3: QC autofix one round → rescore

Citations: set WM_SMOKE_CITATIONS=1 (default) so draft_section uses auto_insert_citations
(PubMed via /insert_citations). Set WM_SMOKE_CITATIONS=0 for fast draft-only smoke.

Usage (VPS):
  cd /srv/services/writing_memory
  .venv/bin/python smoke/run_ordered_smoke_v1545.py

Or local against production:
  WM_BASE=https://write.insynbio.com WM_AUTH=Admin:Rocky123 python smoke/run_ordered_smoke_v1545.py
"""

from __future__ import annotations

import base64
import json
import os
import re
import sys
import time
import urllib.error
import urllib.request
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

BASE = os.getenv("WM_BASE", "http://127.0.0.1:8100").rstrip("/")
AUTH_RAW = os.getenv("WM_AUTH", "Admin:Rocky123")
OUT_DIR = Path(__file__).resolve().parent
# Default ON: smoke must exercise PubMed citation path, not only [CITE:] placeholders.
SMOKE_INSERT_CITATIONS = os.getenv("WM_SMOKE_CITATIONS", "1").lower() not in (
    "0",
    "false",
    "no",
)

TEST_PARAGRAPH = (
    "HuNSG-QUAD mice reconstituted with human HSPCs mount NF-κB-dependent, "
    "type I interferon, and NLRP3 inflammasome responses after lipopolysaccharide "
    "challenge; MCC950 selectively blocks IL-1β and IL-18 without increasing "
    "monocyte death, indicating cytokine release can proceed independently of "
    "pyroptotic cell death."
)

HU_ABSTRACT = """Background: Dysregulated innate immune responses underlie multiple inflammatory diseases, but clinical translation of preclinical innate immunity research in mice is hampered by the difficulty of studying human inflammatory reactions in an in vivo context. We therefore sought to establish in vivo human inflammatory responses in NSG-QUAD mice that express four human myelopoiesis transgenes to improve engraftment of a human innate immune system.

Methods: We reconstituted NSG-QUAD mice with human hematopoietic stem and progenitor cells (HSPCs), after which we evaluated human myeloid cell development and subsequent human responses to systemic and local lipopolysaccharide (LPS) challenges.

Results: NSG-QUAD mice already displayed engraftment of human monocytes, dendritic cells and granulocytes in peripheral blood, spleen and liver at 6 weeks after HSPC injection. HuNSG-QUAD mice responded to intraperitoneal and intranasal LPS with NF-κB-dependent cytokines, type I interferon, and NLRP3 inflammasome-mediated IL-1β and IL-18. MCC950 specifically abrogated IL-1β and IL-18 without affecting monocyte death.

Conclusions: HuNSG-QUAD mice are competent for studying NF-κB, type I interferon and inflammasome effectors of human innate immunity in vivo."""


def _headers() -> dict[str, str]:
    token = base64.b64encode(AUTH_RAW.encode()).decode()
    return {"Content-Type": "application/json", "Authorization": f"Basic {token}"}


def post(path: str, body: dict, timeout: int = 300) -> tuple[int, dict]:
    data = json.dumps(body).encode()
    req = urllib.request.Request(
        f"{BASE}{path}",
        data=data,
        headers=_headers(),
        method="POST",
    )
    try:
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            return resp.status, json.loads(resp.read())
    except urllib.error.HTTPError as exc:
        raw = exc.read()
        try:
            return exc.code, json.loads(raw)
        except Exception:
            return exc.code, {"error": raw.decode(errors="replace")[:800]}


def get(path: str, timeout: int = 30) -> tuple[int, dict]:
    req = urllib.request.Request(f"{BASE}{path}", headers=_headers())
    try:
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            return resp.status, json.loads(resp.read())
    except urllib.error.HTTPError as exc:
        raw = exc.read()
        try:
            return exc.code, json.loads(raw)
        except Exception:
            return exc.code, {"error": raw.decode(errors="replace")[:800]}


def merge_reference_lists(*lists: list[list[Any]]) -> list[str]:
    """Merge per-section reference_list entries (strings; tolerate nested lists)."""
    seen: set[str] = set()
    out: list[str] = []

    def _add(item: Any) -> None:
        if isinstance(item, list):
            for sub in item:
                _add(sub)
        elif isinstance(item, dict):
            text = (item.get("formatted") or item.get("text") or "").strip()
            if text:
                _add(text)
        elif isinstance(item, str):
            text = item.strip()
            if text and text not in seen:
                seen.add(text)
                out.append(text)

    for refs in lists:
        for r in refs or []:
            _add(r)
    return out


def prose_from_draft(dr: dict) -> tuple[str, list[str], dict]:
    """Prefer cited prose when auto_insert_citations ran."""
    prose = dr.get("rendered_prose_cited") or dr.get("rendered_prose") or ""
    refs = list(dr.get("reference_list") or [])
    meta = {
        "citations_inserted": (dr.get("_meta") or {}).get("citations_inserted"),
        "n_citation_audit": len(dr.get("citation_audit") or []),
        "cite_placeholders_left": len(re.findall(r"\[CITE:\s*[^\]]+\]", prose, re.I)),
    }
    return prose, refs, meta


def citation_signals(text: str) -> dict[str, int]:
    return {
        "author_year_paren": len(re.findall(
            r"\([A-Z][A-Za-z\-']+(?:\s+et\s+al\.)?,?\s+\d{4}[a-z]?\)", text
        )),
        "numbered_bracket": len(re.findall(r"\[\d+(?:[\s,;\-]\d+)*\]", text)),
        "cite_placeholder": len(re.findall(r"\[CITE:\s*[^\]]+\]", text, re.I)),
        "ai_markers": sum(
            1 for m in (
                "leverages", "underscores", "pivotal", "intricate", "delve",
                "tapestry", "transformative", "comprehensive understanding",
            )
            if m in text.lower()
        ),
    }


def step1_rewrite_divergence() -> dict:
    print("\n=== STEP 1: Three-journal /rewrite divergence ===")
    out: dict = {"paragraph": TEST_PARAGRAPH, "journals": {}}
    for journal in ("elife", "pnas", "nejm"):
        print(f"  rewrite → {journal} …")
        t0 = time.time()
        code, data = post("/rewrite", {
            "paragraph": TEST_PARAGRAPH,
            "target_journal": journal,
            "section": "discussion",
            "article_type": "research",
        }, timeout=180)
        elapsed = round(time.time() - t0, 1)
        text = data.get("rewritten_paragraph") or data.get("error") or str(data)[:400]
        sig = citation_signals(text) if isinstance(text, str) else {}
        out["journals"][journal] = {
            "http": code,
            "elapsed_s": elapsed,
            "signals": sig,
            "text_preview": (text[:500] if isinstance(text, str) else text),
            "style_adjustments": (data.get("style_adjustments") or [])[:5],
        }
        print(f"    HTTP {code} {elapsed}s  signals={sig}")
    return out


def step2_hungs_plan_and_draft() -> dict:
    print("\n=== STEP 2: huNSG-QUAD plan + section drafts ===")
    out: dict = {}

    print("  recommend_journal …")
    code, rec = post("/recommend_journal", {
        "abstract_text": HU_ABSTRACT,
        "article_type": "research",
    }, timeout=120)
    out["recommend_journal"] = {"http": code, "top": (rec.get("recommendations") or rec)[:3] if code == 200 else rec}

    print("  plan_paper …")
    t0 = time.time()
    code, plan = post("/plan_paper", {
        "user_intent": HU_ABSTRACT,
        "article_type": "research",
        "data_summary": "6-week engraftment; IP and intranasal LPS; MCC950 blocks IL-1b/IL-18 without monocyte death.",
        "experimental_design": "NSG-QUAD + human HSPC; flow cytometry; Luminex cytokines; LPS challenge.",
    }, timeout=300)
    out["plan_paper"] = {
        "http": code,
        "elapsed_s": round(time.time() - t0, 1),
        "suggested_title": plan.get("suggested_title") if code == 200 else None,
        "outline_keys": list((plan.get("outline") or {}).keys()) if code == 200 else [],
    }
    if code != 200:
        print(f"    plan FAILED: {plan}")
        return out

    target_journal = "plos_med"  # strong fit for humanized mouse innate immunity
    sections_drafted: list[dict] = []
    per_section_refs: list[list[str]] = []
    print(f"  auto_insert_citations={SMOKE_INSERT_CITATIONS}")
    for sec in ("abstract", "introduction", "results", "discussion", "methods"):
        print(f"  draft_section → {sec} …")
        t0 = time.time()
        code, dr = post("/draft_section", {
            "plan": plan,
            "section_key": sec,
            "target_journal": target_journal,
            "article_type": "research",
            "auto_insert_citations": SMOKE_INSERT_CITATIONS,
            "force_author_year": True,
        }, timeout=300)
        prose, refs, cite_meta = prose_from_draft(dr)
        per_section_refs.append(refs)
        fills = dr.get("fill_markers_used") or []
        sections_drafted.append({
            "key": sec,
            "title": sec.title(),
            "text": prose,
            "http": code,
            "elapsed_s": round(time.time() - t0, 1),
            "words": dr.get("approximate_words"),
            "fill_count": len(fills),
            "fill_markers": fills[:8],
            "citation_meta": cite_meta,
            "reference_count": len(refs),
        })
        print(f"    HTTP {code} {sections_drafted[-1]['elapsed_s']}s  "
              f"words={sections_drafted[-1]['words']} fills={sections_drafted[-1]['fill_count']} "
              f"refs={len(refs)} cite_left={cite_meta.get('cite_placeholders_left')}")

    out["sections"] = sections_drafted
    out["merged_reference_list"] = merge_reference_lists(per_section_refs)
    out["auto_insert_citations"] = SMOKE_INSERT_CITATIONS
    out["target_journal"] = target_journal
    out["plan"] = plan
    return out


def step3_qc(
    sections: list[dict],
    plan: dict | None,
    journal: str,
    label: str,
    reference_list: list[str] | None = None,
) -> dict:
    print(f"\n=== STEP 3: manuscript_qc_score ({label}) ===")
    abstract = next((s["text"] for s in sections if s["key"] == "abstract"), HU_ABSTRACT)
    refs = reference_list or []
    body = {
        "sections": [{"key": s["key"], "title": s["title"], "text": s["text"]} for s in sections],
        "target_journal": journal,
        "article_type": "research",
        "abstract_text": abstract,
        "reference_list": refs,
        "verify_references": bool(refs),
        "plan": plan,
        "check_grammar": False,
    }
    t0 = time.time()
    code, qc = post("/manuscript_qc_score", body, timeout=180)
    elapsed = round(time.time() - t0, 1)
    summary = {
        "label": label,
        "http": code,
        "elapsed_s": elapsed,
        "overall_score": qc.get("overall_score"),
        "overall_verdict": qc.get("overall_verdict"),
        "hard_gate": qc.get("hard_gate_triggered"),
        "dimensions_failed": qc.get("dimensions_failed"),
        "dimensions_warned": qc.get("dimensions_warned"),
        "dimensions": {
            k: {"score": v.get("score"), "verdict": v.get("verdict"), "summary": v.get("summary")}
            for k, v in (qc.get("dimensions") or {}).items()
        },
    }
    print(f"  overall={summary['overall_score']} {summary['overall_verdict']} "
          f"fail={summary['dimensions_failed']} warn={summary['dimensions_warned']}")
    return summary


def step4_autofix(sections: list[dict], journal: str) -> tuple[list[dict], dict]:
    print("\n=== STEP 4: manuscript_qc_autofix (1 round) ===")
    abstract = next((s["text"] for s in sections if s["key"] == "abstract"), HU_ABSTRACT)
    code, result = post("/manuscript_qc_autofix", {
        "sections": [{"key": s["key"], "title": s["title"], "text": s["text"]} for s in sections],
        "target_journal": journal,
        "article_type": "research",
        "abstract_text": abstract,
        "reference_list": [],
        "fix_dimensions": [],
        "max_rounds": 1,
    }, timeout=600)
    updated = result.get("sections") or []
    final_qc = result.get("final_score") or {}
    print(f"  HTTP {code} final_score={final_qc.get('overall_score')} "
          f"verdict={final_qc.get('overall_verdict')}")
    # merge updated text back
    by_key = {u.get("key"): u.get("text", "") for u in updated if isinstance(u, dict)}
    new_sections = []
    for s in sections:
        ns = dict(s)
        if s["key"] in by_key and by_key[s["key"]]:
            ns["text"] = by_key[s["key"]]
        new_sections.append(ns)
    return new_sections, {"http": code, "final_score": final_qc, "rounds": result.get("rounds")}


def main() -> int:
    report: dict = {
        "protocol_version": "v15.45_ordered_smoke",
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "base_url": BASE,
    }

    # health
    code, health = get("/health")
    report["health"] = {"http": code, "status": health.get("status")}

    report["step1_rewrite"] = step1_rewrite_divergence()

    hung = step2_hungs_plan_and_draft()
    report["step2_hungs"] = hung

    sections = hung.get("sections") or []
    journal = hung.get("target_journal") or "plos_med"
    plan = hung.get("plan")

    merged_refs = hung.get("merged_reference_list") or []
    report["citations_smoke"] = {
        "auto_insert_citations": hung.get("auto_insert_citations", SMOKE_INSERT_CITATIONS),
        "merged_reference_count": len(merged_refs),
    }

    if sections:
        report["step3_qc_before"] = step3_qc(
            sections, plan, journal, "before_autofix", reference_list=merged_refs
        )
        fixed_sections, autofix_meta = step4_autofix(sections, journal)
        report["step4_autofix"] = autofix_meta
        report["step3_qc_after"] = step3_qc(
            fixed_sections, plan, journal, "after_autofix", reference_list=merged_refs
        )

    ts = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    out_path = OUT_DIR / f"huNSG_QUAD_ordered_smoke_{ts}.json"
    out_path.write_text(json.dumps(report, indent=2, ensure_ascii=False), encoding="utf-8")
    print(f"\nWrote {out_path}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
