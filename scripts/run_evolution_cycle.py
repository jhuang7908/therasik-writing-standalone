#!/usr/bin/env python3
"""
run_evolution_cycle.py — InSynBio Self-Evolution V1 CLI
========================================================
Analyze accumulated RunEvents, detect recurring signals, and
generate governed OBSERVATION / PROPOSAL entries.

Usage:
    python scripts/run_evolution_cycle.py                   # full cycle
    python scripts/run_evolution_cycle.py --dry-run         # preview only
    python scripts/run_evolution_cycle.py --stats           # show event store stats

Output:
    docs/EVOLUTION_LOG.md      — append-only entries (unless --dry-run)
    output/evolution/
        suggestions.json       — machine-readable signal list
        summary.md             — human-readable summary
"""
from __future__ import annotations

import argparse
import sys
from pathlib import Path

SUITE = Path(__file__).resolve().parents[1]
if str(SUITE) not in sys.path:
    sys.path.insert(0, str(SUITE))


def main() -> int:
    ap = argparse.ArgumentParser(
        description="InSynBio Self-Evolution V1 — analyze signals and generate proposals",
    )
    ap.add_argument("--dry-run", action="store_true",
                    help="Preview signals without writing to EVOLUTION_LOG")
    ap.add_argument("--stats", action="store_true",
                    help="Print event store statistics and exit")
    args = ap.parse_args()

    from core.evolution.run_event import RunEventStore
    from core.evolution.signal_analyzer import SignalAnalyzer
    from core.evolution.proposal_engine import ProposalEngine

    store = RunEventStore()

    if args.stats:
        events = store.load_all()
        print(f"Event store: {store.path}")
        print(f"Total events: {len(events)}")
        if events:
            from collections import Counter
            families = Counter(e.family for e in events)
            tiers = Counter(e.ada_tier for e in events)
            tags = Counter(t for e in events for t in e.tags)
            print(f"\nBy family:  {dict(families)}")
            print(f"By ADA tier: {dict(tiers)}")
            print(f"Top tags:    {dict(tags.most_common(10))}")
        return 0

    print("=" * 60)
    print("INSYNBIO SELF-EVOLUTION V1 — Signal Analysis")
    print("=" * 60)

    n_events = store.count()
    print(f"Events in store: {n_events}")

    if n_events == 0:
        print("\nNo events collected yet. Run project pipelines first.")
        print("Events are collected automatically when CLIs with EvidenceGate run.")
        return 0

    analyzer = SignalAnalyzer(store)
    signals = analyzer.analyze()
    print(f"Signals detected: {len(signals)}")

    if not signals:
        print("\nNo recurring patterns detected. System is healthy.")
        return 0

    for sig in signals:
        print(f"\n  [{sig.severity.upper()}] {sig.title}")
        print(f"    Count: {sig.occurrence_count}  |  Category: {sig.category}")
        if sig.suggested_action:
            print(f"    Action: {sig.suggested_action}")

    engine = ProposalEngine()
    result = engine.process(signals, dry_run=args.dry_run)

    print(f"\n{'=' * 60}")
    print(f"Results: {result['observations']} observation(s), {result['proposals']} proposal(s)")
    if args.dry_run:
        print("(dry-run mode — nothing written)")
    else:
        print(f"Suggestions: {result['suggestions_path']}")
        print(f"EVOLUTION_LOG.md updated with {result['observations'] + result['proposals']} entry(ies)")
    print("=" * 60)
    return 0


if __name__ == "__main__":
    sys.exit(main())
