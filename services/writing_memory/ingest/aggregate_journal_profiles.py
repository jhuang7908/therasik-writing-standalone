"""
aggregate_journal_profiles.py — Step 3: collapse per-paper ArticleProfiles
into one JournalProfile per journal using Claude Sonnet as the aggregator.

The aggregation prompt feeds Claude all N article profiles for a journal at
once and asks it to produce a single JournalProfile v0.1.0 JSON object.

Because the full article-profile JSON for 48-50 papers can be large (~200-400 k
tokens), this script uses a two-stage strategy:

  Stage A (code-driven): compute hard statistics from the profiles in Python
    — mode values for enum fields, phrase frequency counts, reviewer-attack
    frequency counts.  These are cheap to compute and provably correct.

  Stage B (Claude-driven): feed Claude a *compact summary* (statistics +
    representative phrases + top attack patterns) rather than all raw JSON.
    Claude writes the JournalProfile's free-text narrative fields and ranks
    the final phrase_bank.  This keeps input to ~8–12 k tokens per journal.

This hybrid approach:
  - Avoids hallucinated evidence_paper_counts (computed, not generated)
  - Stays within Sonnet context limits
  - Keeps costs low (≈ 3 Sonnet calls total)

Usage
-----
    python services/writing_memory/ingest/aggregate_journal_profiles.py
    python services/writing_memory/ingest/aggregate_journal_profiles.py --journals pnas
    python services/writing_memory/ingest/aggregate_journal_profiles.py --dry-run

Output
------
    services/writing_memory/journal_profiles/
        pnas.json
        elife.json
        plos_med.json
"""

from __future__ import annotations

import argparse
import json
import os
import re
import sys
import time
from collections import Counter, defaultdict
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import anthropic
import jsonschema

_HERE = Path(__file__).resolve().parent
_SERVICE_ROOT = _HERE.parent

PROFILES_DIR  = _SERVICE_ROOT / "article_profiles"
OUT_DIR       = _SERVICE_ROOT / "journal_profiles"
SCHEMA_PATH   = _SERVICE_ROOT / "schemas" / "journal_profile.schema.json"
PROMPT_PATH   = _SERVICE_ROOT / "prompts" / "journal_aggregate.system.md"

DEFAULT_MODEL = os.environ.get("ANTHROPIC_MODEL", "claude-sonnet-4-5")
MAX_TOKENS    = 8192
TEMPERATURE   = 0.1

JOURNAL_META = {
    "pnas":     {"display": "Proceedings of the National Academy of Sciences", "issn": "1091-6490"},
    "elife":    {"display": "eLife",          "issn": "2050-084X"},
    "plos_med": {"display": "PLOS Medicine",  "issn": "1549-1676"},
}


# ---------------------------------------------------------------------------
# Stage A: Code-driven statistics
# ---------------------------------------------------------------------------

def _load_profiles(journal_key: str) -> list[dict[str, Any]]:
    jdir = PROFILES_DIR / journal_key
    profiles = []
    for p in sorted(jdir.glob("*.json")):
        if p.stem.startswith("_"):
            continue
        try:
            d = json.loads(p.read_text(encoding="utf-8"))
            # Skip any profile that has a _schema_error (shouldn't exist after cleaning)
            if "_schema_error" not in d:
                profiles.append(d)
        except Exception:
            continue
    return profiles


def _mode(values: list[str]) -> str:
    if not values:
        return "other"
    return Counter(values).most_common(1)[0][0]


def _compute_statistics(profiles: list[dict[str, Any]]) -> dict[str, Any]:
    """
    Compute frequency tables over all enum fields and phrase/attack collections.
    Returns a structured stats dict that is fed to Claude in Stage B.
    """
    stats: dict[str, Any] = {
        "paper_count": len(profiles),
        "pmids": [p.get("source", {}).get("pmid", "") for p in profiles],
    }

    # --- Enum fields ---
    opening_styles: list[str] = []
    dominant_frames: list[str] = []
    tones: list[str] = []
    logic_patterns: list[str] = []
    hedge_levels: list[str] = []
    claim_strengths: list[str] = []
    avg_lengths: list[str] = []
    claim_overall: list[str] = []

    for prof in profiles:
        rp = prof.get("rhetoric_profile", {})
        opening_styles.append(rp.get("opening_style", "other"))
        dominant_frames.append(rp.get("dominant_frame", "other"))
        tones.append(rp.get("tone", "other"))

        lp = prof.get("logic_profile", {})
        logic_patterns.append(lp.get("main_pattern", "other"))

        sp = prof.get("sentence_style_profile", {})
        hedge_levels.append(sp.get("hedge_level", "medium"))
        claim_strengths.append(sp.get("claim_strength", "moderate"))
        avg_lengths.append(sp.get("avg_sentence_length", "medium"))

        csp = prof.get("claim_strength_profile", {})
        claim_overall.append(csp.get("overall", "balanced"))

    stats["rhetoric"] = {
        "opening_style_mode":    _mode(opening_styles),
        "opening_style_dist":    dict(Counter(opening_styles).most_common()),
        "dominant_frame_mode":   _mode(dominant_frames),
        "dominant_frame_dist":   dict(Counter(dominant_frames).most_common()),
        "tone_mode":             _mode(tones),
        "tone_dist":             dict(Counter(tones).most_common()),
    }
    stats["logic"] = {
        "main_pattern_mode":     _mode(logic_patterns),
        "main_pattern_dist":     dict(Counter(logic_patterns).most_common()),
    }
    stats["sentence_style"] = {
        "hedge_level_mode":      _mode(hedge_levels),
        "claim_strength_mode":   _mode(claim_strengths),
        "avg_length_mode":       _mode(avg_lengths),
    }
    stats["claim_strength"] = {
        "overall_mode":          _mode(claim_overall),
        "overall_dist":          dict(Counter(claim_overall).most_common()),
    }

    # --- Verb frequencies ---
    verb_counter: Counter[str] = Counter()
    for prof in profiles:
        sp = prof.get("sentence_style_profile", {})
        for v in (sp.get("preferred_verbs") or []):
            verb_counter[v.lower()] += 1
    stats["top_verbs"] = [v for v, _ in verb_counter.most_common(20)]

    # --- Claim chain items (recurring) ---
    chain_counter: Counter[str] = Counter()
    for prof in profiles:
        lp = prof.get("logic_profile", {})
        for item in (lp.get("claim_chain") or []):
            chain_counter[item.strip()] += 1
    stats["top_claim_chain_items"] = [
        {"item": item, "count": cnt}
        for item, cnt in chain_counter.most_common(10)
    ]

    # --- Typical paragraph pattern items ---
    para_counter: Counter[str] = Counter()
    for prof in profiles:
        pp = prof.get("paragraph_structure_profile", {})
        for item in (pp.get("typical_pattern") or []):
            para_counter[item.strip()] += 1
    stats["top_para_pattern_items"] = [
        {"item": item, "count": cnt}
        for item, cnt in para_counter.most_common(8)
    ]

    # --- Phrase bank: collect ALL phrases, rank by frequency across papers ---
    # Even frequency=1 is valid — these represent the journal's characteristic
    # style phrases that authors reuse. Exact repetition across papers is rare;
    # Claude will cluster near-duplicates and select the 30 most representative.
    phrase_to_pmids: dict[str, list[str]] = defaultdict(list)
    phrase_category: dict[str, str] = {}
    for prof in profiles:
        pmid = prof.get("source", {}).get("pmid", "")
        for pe in (prof.get("phrase_evidence") or []):
            phrase = (pe.get("phrase") or "").strip()
            cat = pe.get("category", "other")
            if phrase:
                phrase_to_pmids[phrase].append(pmid)
                if phrase not in phrase_category:
                    phrase_category[phrase] = cat

    all_phrases = [
        {
            "phrase": phrase,
            "category": phrase_category[phrase],
            "frequency": len(set(pmids)),
            "evidence_paper_ids": sorted(set(pmids)),
        }
        for phrase, pmids in phrase_to_pmids.items()
    ]
    # Sort: first by frequency desc, then by phrase length (shorter = more reusable)
    all_phrases.sort(key=lambda x: (-x["frequency"], len(x["phrase"])))
    # Sample: top 30 by freq + 30 spread across categories (give Claude variety)
    top_freq = all_phrases[:30]
    by_category: dict[str, list] = defaultdict(list)
    for p in all_phrases[30:]:
        by_category[p["category"]].append(p)
    variety = []
    for cat_phrases in by_category.values():
        variety.extend(cat_phrases[:5])
    variety.sort(key=lambda x: -x["frequency"])
    stats["phrase_candidates"] = (top_freq + variety[:30])[:80]

    # --- Reviewer attack patterns (all unique, ≥1 paper) ---
    attack_to_pmids: dict[str, list[str]] = defaultdict(list)
    for prof in profiles:
        pmid = prof.get("source", {}).get("pmid", "")
        rpp = prof.get("reviewer_preference_profile", {})
        for attack in (rpp.get("likely_attacks") or []):
            attack = attack.strip()
            if attack:
                attack_to_pmids[attack].append(pmid)

    all_attacks = [
        {
            "pattern": pattern,
            "frequency": len(set(pmids)),
            "evidence_paper_ids": sorted(set(pmids)),
            "verification_status": "inferred",
        }
        for pattern, pmids in attack_to_pmids.items()
    ]
    all_attacks.sort(key=lambda x: -x["frequency"])
    stats["attack_candidates"] = all_attacks[:40]

    return stats


# ---------------------------------------------------------------------------
# Stage B: Claude aggregation prompt
# ---------------------------------------------------------------------------

def _build_aggregation_message(
    journal_key: str,
    stats: dict[str, Any],
    schema: dict[str, Any],
    now_utc: str,
) -> str:
    meta = JOURNAL_META[journal_key]
    parts: list[str] = []

    parts.append(f"## Journal: {meta['display']} (key={journal_key})")
    parts.append(f"## Source paper count: {stats['paper_count']}")
    parts.append(f"## UTC timestamp for generated_at: {now_utc}")
    parts.append("")

    parts.append("## Pre-computed statistics (use these directly — do not re-derive)")
    parts.append("```json")
    # Send stats without the full phrase/attack lists (those come separately)
    compact_stats = {k: v for k, v in stats.items()
                     if k not in ("phrase_candidates", "attack_candidates", "pmids")}
    parts.append(json.dumps(compact_stats, indent=2))
    parts.append("```")
    parts.append("")

    parts.append("## Phrase candidates (pre-computed, frequency ≥ 2 papers)")
    parts.append("Pick up to 30 for phrase_bank. Each phrase MUST appear verbatim in")
    parts.append("evidence_paper_ids as supplied below. Do not add or remove PMIDs.")
    parts.append("```json")
    parts.append(json.dumps(stats["phrase_candidates"][:60], indent=2))
    parts.append("```")
    parts.append("")

    parts.append("## Reviewer attack candidates (pre-computed, frequency ≥ 3 papers)")
    parts.append("Pick up to 15 for reviewer_attack_patterns. Every item has")
    parts.append("verification_status='inferred'. Do not change PMIDs.")
    parts.append("```json")
    parts.append(json.dumps(stats["attack_candidates"], indent=2))
    parts.append("```")
    parts.append("")

    parts.append("## Source PMIDs (for source_paper_ids field)")
    parts.append(json.dumps(stats["pmids"]))
    parts.append("")

    parts.append("## Required JSON Schema (JournalProfile v0.1.0)")
    parts.append("```json")
    parts.append(json.dumps(schema, indent=2))
    parts.append("```")
    parts.append("")
    parts.append(
        "Produce ONE JSON object matching the schema.\n"
        "Use the pre-computed statistics above for all enum/count fields.\n"
        "Write concise natural-language summaries for the `value` fields of "
        "rhetoric_profile, logic_profile, sentence_style_profile, "
        "paragraph_structure_profile, and claim_strength_profile.\n"
        "No markdown fences. No prose outside the JSON."
    )

    return "\n".join(parts)


# ---------------------------------------------------------------------------
# Main aggregation function for one journal
# ---------------------------------------------------------------------------

def aggregate_journal(
    journal_key: str,
    client: anthropic.Anthropic,
    system_prompt: str,
    schema: dict[str, Any],
    out_dir: Path,
    dry_run: bool = False,
) -> dict[str, Any]:
    print(f"\n[{journal_key}] loading profiles ...")
    profiles = _load_profiles(journal_key)
    if not profiles:
        return {"status": "fail", "error": "no profiles found"}

    print(f"[{journal_key}] {len(profiles)} profiles — computing statistics ...")
    stats = _compute_statistics(profiles)

    now_utc = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
    user_msg = _build_aggregation_message(journal_key, stats, schema, now_utc)

    token_estimate = len(user_msg) // 4
    print(f"[{journal_key}] user message ~{token_estimate} tokens")

    if dry_run:
        print(f"[{journal_key}] DRY RUN — skipping Claude call")
        print(f"  phrase_candidates: {len(stats['phrase_candidates'])}")
        print(f"  attack_candidates: {len(stats['attack_candidates'])}")
        return {"status": "dry_run"}

    print(f"[{journal_key}] calling Claude {DEFAULT_MODEL} ...")
    raw_text = None
    for attempt in range(3):
        try:
            response = client.messages.create(
                model=DEFAULT_MODEL,
                max_tokens=MAX_TOKENS,
                temperature=TEMPERATURE,
                system=system_prompt,
                messages=[{"role": "user", "content": user_msg}],
            )
            if response.content:
                raw_text = response.content[0].text.strip()
                if raw_text:
                    break
            time.sleep(5.0 * (attempt + 1))
        except Exception as exc:
            if attempt < 2:
                time.sleep(8.0)
                continue
            return {"status": "fail", "error": f"Claude API error: {exc}"}

    if not raw_text:
        return {"status": "fail", "error": "Claude returned empty response"}

    # Strip accidental markdown fences
    raw_text = re.sub(r"^```(?:json)?\s*", "", raw_text)
    raw_text = re.sub(r"\s*```$", "", raw_text)

    try:
        profile = json.loads(raw_text)
    except json.JSONDecodeError as exc:
        return {"status": "fail", "error": f"JSON parse error: {exc}"}

    # Inject fields that Claude might not know to fill correctly
    profile["schema_version"]    = "0.1.0"
    profile["profile_version"]   = "0.1.0"
    profile["generated_at"]      = now_utc
    profile["source_paper_count"] = len(profiles)
    profile["source_paper_ids"]  = stats["pmids"]
    profile["journal"] = {
        "key":     journal_key,
        "display": JOURNAL_META[journal_key]["display"],
        "issn":    JOURNAL_META[journal_key]["issn"],
    }

    # Schema validation
    try:
        jsonschema.validate(instance=profile, schema=schema)
        schema_valid = True
    except jsonschema.ValidationError as exc:
        schema_valid = False
        profile["_schema_error"] = exc.message

    # Save
    out_dir.mkdir(parents=True, exist_ok=True)
    out_path = out_dir / f"{journal_key}.json"
    out_path.write_text(json.dumps(profile, ensure_ascii=False, indent=2), encoding="utf-8")

    print(f"[{journal_key}] saved → {out_path}  schema_valid={schema_valid}")
    return {
        "status": "ok" if schema_valid else "warn",
        "schema_valid": schema_valid,
        "phrase_bank_size": len(profile.get("phrase_bank") or []),
        "attack_patterns":  len(profile.get("reviewer_attack_patterns") or []),
        "error": profile.get("_schema_error"),
    }


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def main(argv: list[str]) -> int:
    ap = argparse.ArgumentParser(
        description="Aggregate per-paper ArticleProfiles into JournalProfiles."
    )
    ap.add_argument("--journals", nargs="*",
                    default=["pnas", "elife", "plos_med"])
    ap.add_argument("--out-dir", type=Path, default=OUT_DIR)
    ap.add_argument("--dry-run", action="store_true")
    args = ap.parse_args(argv)

    api_key = os.environ.get("ANTHROPIC_API_KEY", "")
    if not api_key and not args.dry_run:
        print("ERROR: ANTHROPIC_API_KEY not set.", file=sys.stderr)
        return 1

    system_prompt = PROMPT_PATH.read_text(encoding="utf-8")
    schema = json.loads(SCHEMA_PATH.read_text(encoding="utf-8"))

    client = anthropic.Anthropic(api_key=api_key) if not args.dry_run else None

    report: dict[str, Any] = {
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "journals": {},
    }

    overall_ok = True
    for jkey in args.journals:
        result = aggregate_journal(
            jkey, client, system_prompt, schema, args.out_dir,
            dry_run=args.dry_run,
        )
        report["journals"][jkey] = result
        if result.get("status") == "fail":
            overall_ok = False

    report_path = args.out_dir / "_aggregation_report.json"
    args.out_dir.mkdir(parents=True, exist_ok=True)
    report_path.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")

    print(f"\nAggregation report: {report_path}")
    for jkey, res in report["journals"].items():
        status = res.get("status", "?")
        extra = (
            f"  phrases={res.get('phrase_bank_size',0)}"
            f"  attacks={res.get('attack_patterns',0)}"
        ) if status != "fail" else f"  err={res.get('error','')[:80]}"
        print(f"  {jkey}: {status}{extra}")

    return 0 if overall_ok else 1


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
