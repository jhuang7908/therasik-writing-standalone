#!/usr/bin/env python3
"""Local polish gate + writing_memory bridge (nature-polishing parity)."""
from __future__ import annotations

import argparse
import json
import os
import re
import sys
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def _load_forbidden() -> tuple[str, ...]:
    try:
        sys.path.insert(0, str(ROOT))
        from services.writing_memory.style_safety import AI_MARKER_PHRASES

        return AI_MARKER_PHRASES
    except Exception:
        return (
            "leverages", "underscores", "pivotal", "intricate", "paramount",
            "key insights", "it is worth noting", "in summary,",
        )


def _load_journal_context(journal: str, section: str | None) -> str:
    try:
        sys.path.insert(0, str(ROOT))
        from services.writing_memory.journal_context import build_journal_context_block

        return build_journal_context_block(journal, section_key=section)
    except Exception:
        return ""


def scan_ai_markers(text: str, forbidden: tuple[str, ...]) -> list[dict]:
    lower = text.lower()
    hits: list[dict] = []
    for phrase in forbidden:
        if phrase.lower() in lower:
            hits.append({"phrase": phrase, "count": lower.count(phrase.lower())})
    return hits


def cmd_scan(args: argparse.Namespace) -> int:
    text = Path(args.input).read_text(encoding="utf-8")
    forbidden = _load_forbidden()
    hits = scan_ai_markers(text, forbidden)
    jctx = _load_journal_context(args.journal, args.section) if args.journal else ""
    report = {
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "journal": args.journal,
        "section": args.section,
        "ai_marker_hits": hits,
        "ai_marker_count": sum(h["count"] for h in hits),
        "status": "FAIL" if sum(h["count"] for h in hits) >= args.fail_threshold else "PASS",
        "journal_context_available": bool(jctx),
    }
    out = Path(args.out).resolve() if args.out else None
    if out:
        out.write_text(json.dumps(report, indent=2), encoding="utf-8")
        print(f"Scan: {out} ({report['status']}, markers={report['ai_marker_count']})")
    else:
        print(json.dumps(report, indent=2))
    return 1 if report["status"] == "FAIL" else 0


def cmd_platform_hint(args: argparse.Namespace) -> None:
    base = os.environ.get("WRITING_MEMORY_URL", "https://write.insynbio.com")
    print(f"Platform polish: {base}")
    print(f"  POST /rewrite  journal={args.journal}")
    print(f"  POST /reduce_ai_tone")
    print(f"  POST /draft_section  section={args.section or 'discussion'}")
    if args.journal:
        block = _load_journal_context(args.journal, args.section)
        if block:
            print("\n--- journal_context preview ---")
            print(block[:1200])


def _lt_check_chunk(text: str, language: str = "en-US", timeout: int = 30) -> list[dict]:
    """Call LanguageTool public API on one chunk of text."""
    import urllib.parse
    import urllib.request

    url = "https://api.languagetool.org/v2/check"
    data = urllib.parse.urlencode({
        "text": text,
        "language": language,
        "disabledRules": "WHITESPACE_RULE,EN_QUOTES,WORD_CONTAINS_UNDERSCORE",
    }).encode("utf-8")
    req = urllib.request.Request(url, data=data,
                                  headers={"Content-Type": "application/x-www-form-urlencoded"})
    try:
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            result = json.loads(resp.read().decode("utf-8"))
            return result.get("matches", [])
    except Exception as e:
        print(f"  [LanguageTool] API error: {e}", file=sys.stderr)
        return []


def cmd_grammar(args: argparse.Namespace) -> int:
    """
    Check grammar/style using the LanguageTool public API (free, no key required).
    Chunks long manuscripts to stay within 20,000-char API limit.
    Filters to relevant categories: GRAMMAR, TYPOS, PUNCTUATION, STYLE.
    """
    text = Path(args.input).read_text(encoding="utf-8")
    # Strip markdown formatting for cleaner LT input
    clean = re.sub(r"#{1,6}\s+", "", text)           # headers
    clean = re.sub(r"\*{1,2}([^*]+)\*{1,2}", r"\1", clean)  # bold/italic
    clean = re.sub(r"`[^`]+`", "", clean)             # inline code
    clean = re.sub(r"```[\s\S]*?```", "", clean)      # code blocks
    clean = re.sub(r"\[([^\]]+)\]\([^)]+\)", r"\1", clean)   # links
    clean = re.sub(r"\s+", " ", clean).strip()

    CHUNK_SIZE = 18_000
    chunks = [clean[i:i+CHUNK_SIZE] for i in range(0, len(clean), CHUNK_SIZE)]

    KEEP_CATS = {"GRAMMAR", "TYPOS", "PUNCTUATION", "STYLE", "CONFUSED_WORDS", "COLLOCATIONS"}
    SKIP_RULES = {"EN_UNPAIRED_BRACKETS", "COMMA_PARENTHESIS_WHITESPACE",
                  "DOUBLE_PUNCTUATION", "UNIT_SPACE"}

    all_matches: list[dict] = []
    print(f"[grammar] Checking {len(clean):,} chars in {len(chunks)} chunk(s) via LanguageTool API…")

    for i, chunk in enumerate(chunks, 1):
        matches = _lt_check_chunk(chunk, language=args.language)
        for m in matches:
            cat = m.get("rule", {}).get("category", {}).get("id", "")
            rule_id = m.get("rule", {}).get("id", "")
            if cat in KEEP_CATS and rule_id not in SKIP_RULES:
                all_matches.append({
                    "chunk": i,
                    "offset": m.get("offset"),
                    "length": m.get("length"),
                    "message": m.get("message"),
                    "category": cat,
                    "rule": rule_id,
                    "context": m.get("context", {}).get("text", ""),
                    "replacements": [r["value"] for r in (m.get("replacements") or [])[:3]],
                    "sentence": m.get("sentence", "")[:200],
                })
        print(f"  Chunk {i}/{len(chunks)}: {len(matches)} issues found")

    # Group by category
    by_cat: dict[str, list] = {}
    for m in all_matches:
        by_cat.setdefault(m["category"], []).append(m)

    overall = "PASS" if len(all_matches) == 0 else ("WARN" if len(all_matches) <= args.fail_threshold else "FAIL")

    report = {
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "input": str(args.input),
        "language": args.language,
        "chars_checked": len(clean),
        "total_issues": len(all_matches),
        "by_category": {cat: len(ms) for cat, ms in by_cat.items()},
        "overall": overall,
        "matches": all_matches[:200],   # cap for file size
    }

    if args.out:
        out = Path(args.out)
        out.parent.mkdir(parents=True, exist_ok=True)
        out.write_text(json.dumps(report, indent=2, ensure_ascii=False), encoding="utf-8")
        # Also write readable MD summary
        md = out.with_suffix(".md")
        md_lines = [
            "# LanguageTool Grammar Report",
            f"Input: `{args.input}`  ",
            f"Language: {args.language}  ",
            f"Issues: {len(all_matches)}  ",
            f"Overall: **{overall}**",
            "",
            "## Issues by Category",
            "",
        ]
        for cat, ms in sorted(by_cat.items(), key=lambda x: -len(x[1])):
            md_lines.append(f"### {cat} ({len(ms)})")
            for m in ms[:10]:
                repl = f" → `{m['replacements'][0]}`" if m["replacements"] else ""
                ctx = m["context"][:80] if m["context"] else m["sentence"][:80]
                md_lines.append(f"- **{m['rule']}**: {m['message']}{repl}  ")
                md_lines.append(f"  *Context:* `…{ctx}…`")
            if len(ms) > 10:
                md_lines.append(f"  *…{len(ms)-10} more (see JSON)*")
            md_lines.append("")
        md.write_text("\n".join(md_lines), encoding="utf-8")
        print(f"[grammar] {overall} — {len(all_matches)} issues → {out}")
        print(f"[grammar] Summary → {md}")
    else:
        for cat, ms in by_cat.items():
            print(f"\n  {cat} ({len(ms)}):")
            for m in ms[:5]:
                print(f"    [{m['rule']}] {m['message'][:80]}")

    return 1 if overall == "FAIL" else 0


def main() -> None:
    ap = argparse.ArgumentParser(description="InSynBio polishing CLI")
    sub = ap.add_subparsers(dest="cmd", required=True)

    p_scan = sub.add_parser("scan", help="Scan for AI marker phrases (local gate)")
    p_scan.add_argument("--input", type=Path, required=True)
    p_scan.add_argument("--journal", default="antibody_therapeutics")
    p_scan.add_argument("--section", default=None)
    p_scan.add_argument("--fail-threshold", type=int, default=3)
    p_scan.add_argument("--out", type=Path)
    p_scan.set_defaults(func=cmd_scan)

    p_hint = sub.add_parser("platform", help="Show write.insynbio.com endpoints")
    p_hint.add_argument("--journal", default="nature")
    p_hint.add_argument("--section", default="discussion")
    p_hint.set_defaults(func=lambda a: (cmd_platform_hint(a), 0)[1])

    p_gram = sub.add_parser("grammar", help="Grammar/style check via LanguageTool public API (free, no key)")
    p_gram.add_argument("--input", type=Path, required=True, help="Manuscript .md or .txt")
    p_gram.add_argument("--language", default="en-US", help="LanguageTool language code")
    p_gram.add_argument("--fail-threshold", type=int, default=50,
                        help="FAIL if issues > threshold (default 50)")
    p_gram.add_argument("--out", type=Path, default=None, help="Write report to JSON (+ .md summary)")
    p_gram.set_defaults(func=cmd_grammar)

    args = ap.parse_args()
    raise SystemExit(args.func(args))


if __name__ == "__main__":
    main()
