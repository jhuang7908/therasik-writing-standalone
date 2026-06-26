"""
build_section_phrases.py — A1 corpus phrase-bank extractor (v15.44+)

Walk article_profiles/{journal_key}/*.json and aggregate phrase_evidence
into journal_profiles/{key}.section_phrases.json.

Pure Python — no LLM. Phrases are taken verbatim from verified profiles.

Usage (from repo root):
    python services/writing_memory/ingest/build_section_phrases.py --journal elife
    python services/writing_memory/ingest/build_section_phrases.py --all
"""

from __future__ import annotations

import argparse
import json
import re
from collections import Counter, defaultdict
from datetime import datetime, timezone
from pathlib import Path

_HERE = Path(__file__).resolve().parent.parent
_PROFILES_ROOT = _HERE / "article_profiles"
_OUT_DIR = _HERE / "journal_profiles"

# phrase_evidence.category → (section, slot)
_CATEGORY_MAP: dict[str, list[tuple[str, str]]] = {
    "opening":       [("introduction", "opening_phrases"), ("discussion", "opening_phrases")],
    "transition":    [("results", "transition_phrases"), ("discussion", "transition_phrases")],
    "hedge":         [("introduction", "gap_phrases")],
    "limitation":    [("discussion", "limitation_phrases")],
    "implication":   [("discussion", "future_work_phrases")],
    "figure_legend": [("results", "figure_intro_phrases")],
    "claim":         [("results", "opening_phrases")],
    "causal":        [("discussion", "transition_phrases"), ("results", "transition_phrases")],
}

_TOP_K = 8
_MIN_PHRASE_LEN = 25
_MAX_PHRASE_LEN = 220


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


def _word_ngrams(text: str, n: int = 5) -> set[str]:
    words = re.findall(r"[a-z0-9']+", text.lower())
    if len(words) < n:
        return set()
    return {" ".join(words[i : i + n]) for i in range(len(words) - n + 1)}


def _ngram_overlap(a: str, b: str, n: int = 5) -> float:
    ga = _word_ngrams(a, n)
    if not ga:
        return 0.0
    gb = _word_ngrams(b, n)
    return len(ga & gb) / len(ga)


def _normalise_phrase(p: str) -> str:
    p = re.sub(r"\s+", " ", (p or "").strip())
    # Trim trailing incomplete clause
    if len(p) > _MAX_PHRASE_LEN:
        p = p[:_MAX_PHRASE_LEN].rsplit(" ", 1)[0] + "…"
    return p


def _is_usable(p: str) -> bool:
    if len(p) < _MIN_PHRASE_LEN:
        return False
    # Skip figure-only labels
    if re.match(r"^fig(ure)?\s*\d", p, re.I):
        return False
    return True


def _dedupe_rank(counter: Counter[str], top_k: int) -> list[str]:
    """Sort by frequency, greedily dedupe near-duplicates."""
    ranked = [p for p, _ in counter.most_common()]
    kept: list[str] = []
    for phrase in ranked:
        if not _is_usable(phrase):
            continue
        if any(_ngram_overlap(phrase, k) > 0.7 for k in kept):
            continue
        kept.append(phrase)
        if len(kept) >= top_k:
            break
    return kept


def _collect_from_profile(data: dict) -> dict[tuple[str, str], Counter[str]]:
    buckets: dict[tuple[str, str], Counter[str]] = defaultdict(Counter)

    for pe in data.get("phrase_evidence") or []:
        if not isinstance(pe, dict):
            continue
        phrase = _normalise_phrase(pe.get("phrase") or "")
        cat = (pe.get("category") or "other").lower().strip()
        if not phrase or cat == "other":
            continue
        for section, slot in _CATEGORY_MAP.get(cat, []):
            buckets[(section, slot)][phrase] += 1

    # Limitation phrases from claim_strength_profile.examples
    for ex in (data.get("claim_strength_profile") or {}).get("examples") or []:
        if not isinstance(ex, dict):
            continue
        if (ex.get("category") or "").lower() != "limitation":
            continue
        phrase = _normalise_phrase(ex.get("quoted_phrase") or "")
        if phrase:
            buckets[("discussion", "limitation_phrases")][phrase] += 1

    # Results-style openers from logic_profile.claim_chain first lines
    for line in (data.get("logic_profile") or {}).get("claim_chain") or []:
        line = _normalise_phrase(str(line))
        if line and _is_usable(line) and re.match(r"^(we|our|these|this)\b", line, re.I):
            buckets[("results", "opening_phrases")][line] += 1

    return buckets


def build_for_journal(journal_key: str, top_k: int = _TOP_K) -> dict:
    prof_dir = _PROFILES_ROOT / journal_key
    if not prof_dir.is_dir():
        raise FileNotFoundError(f"No article_profiles folder: {prof_dir}")

    merged: dict[tuple[str, str], Counter[str]] = defaultdict(Counter)
    paper_count = 0

    for path in sorted(prof_dir.glob("*.json")):
        if path.name.startswith("_"):
            continue
        try:
            data = json.loads(path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError):
            continue
        paper_count += 1
        for key, ctr in _collect_from_profile(data).items():
            merged[key].update(ctr)

    sections_out: dict[str, dict[str, list[str]]] = {}
    for (section, slot), counter in sorted(merged.items()):
        phrases = _dedupe_rank(counter, top_k)
        if not phrases:
            continue
        sections_out.setdefault(section, {})[slot] = phrases

    return {
        "schema_version": "0.1.0",
        "journal_key": journal_key,
        "source_paper_count": paper_count,
        "generated_at": _now(),
        "generation_method": "corpus_extraction_v1 (build_section_phrases.py)",
        "sections": sections_out,
    }


def build_generic(top_k: int = _TOP_K) -> dict:
    """Merge phrase banks from elife, pnas, plos_med (deduped)."""
    merged_slots: dict[tuple[str, str], Counter[str]] = defaultdict(Counter)
    total_papers = 0
    for jk in ("elife", "pnas", "plos_med"):
        doc = build_for_journal(jk, top_k=top_k * 2)
        total_papers += doc["source_paper_count"]
        for section, slots in (doc.get("sections") or {}).items():
            for slot, phrases in slots.items():
                for p in phrases:
                    merged_slots[(section, slot)][p] += 1

    sections_out: dict[str, dict[str, list[str]]] = {}
    for (section, slot), counter in sorted(merged_slots.items()):
        phrases = _dedupe_rank(counter, top_k)
        if phrases:
            sections_out.setdefault(section, {})[slot] = phrases

    return {
        "schema_version": "0.1.0",
        "journal_key": "generic",
        "source_paper_count": total_papers,
        "generated_at": _now(),
        "generation_method": "merged_from_elife_pnas_plos_med",
        "sections": sections_out,
    }


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--journal", help="elife | pnas | plos_med | generic")
    ap.add_argument("--all", action="store_true", help="Build all four banks")
    ap.add_argument("--top-k", type=int, default=_TOP_K)
    ap.add_argument("--out-dir", type=Path, default=_OUT_DIR)
    args = ap.parse_args()

    keys: list[str]
    if args.all:
        keys = ["elife", "pnas", "plos_med", "generic"]
    elif args.journal:
        keys = [args.journal.strip().lower()]
    else:
        ap.error("Specify --journal KEY or --all")

    args.out_dir.mkdir(parents=True, exist_ok=True)

    for key in keys:
        if key == "generic":
            doc = build_generic(top_k=args.top_k)
        else:
            doc = build_for_journal(key, top_k=args.top_k)
        out_path = args.out_dir / f"{key}.section_phrases.json"
        out_path.write_text(json.dumps(doc, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
        n_slots = sum(len(v) for v in (doc.get("sections") or {}).values())
        print(f"Wrote {out_path}  papers={doc['source_paper_count']}  slots={n_slots}")


if __name__ == "__main__":
    main()
