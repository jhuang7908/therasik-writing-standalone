#!/usr/bin/env python3
"""Generate an aggressive 9AA-CTX humanization variant for mouse anti-CD20.

This keeps the original conservative 9AA-CTX result intact and adds a separate
`9aa_ctx_aggressive` entry to `humanized_sequences.json`.
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

sys.path.insert(0, ".")

from core.humanization import contextual_substitution_engine as cse
from core.humanization.contextual_substitution_engine import ContextualSubstitutionEngine


OUT = Path("projects/mouse_cd20_humanization")
ANNOTATION_PATH = OUT / "annotation.json"
SEQUENCES_PATH = OUT / "humanized_sequences.json"

# More humanizing Layer-2 settings.
AGGRESSIVE_MIN_VOTES = 15
AGGRESSIVE_RATIO = 1.5
AGGRESSIVE_FAMILY_BACKOFF = 5

# V4.4/V5 assembly rule: FR4 is appended separately from human FR4.
HUMAN_VH_FR4 = "WGQGTLVTVSS"
HUMAN_VK_FR4 = "FGGGTKLEIK"


def _replacement_decisions(result):
    rows = []
    for decision in result.decisions:
        if decision.decision == "REPLACED":
            rows.append(
                {
                    "segment": decision.fr_segment,
                    "pos": decision.fr_pos,
                    "from": decision.original_aa,
                    "to": decision.proposed_aa,
                    "source": decision.evidence.get("vote_source"),
                    "ratio": decision.evidence.get("vote_ratio"),
                    "top_votes": decision.evidence.get("top_aa_votes"),
                    "original_votes": decision.evidence.get("original_aa_votes"),
                }
            )
    return rows


def main() -> None:
    annotation = json.loads(ANNOTATION_PATH.read_text())
    sequences = json.loads(SEQUENCES_PATH.read_text())

    vh_seg = annotation["VH"]["segments"]
    vl_seg = annotation["VL"]["segments"]

    vh_germline = sequences.get("deepfr", {}).get("vh_germline", "IGHV3-23")
    vl_germline = sequences.get("deepfr", {}).get("vl_germline", "IGKV1-39")

    # Tune module-level thresholds for this isolated aggressive run.
    cse.MIN_VOTES_LAYER2 = AGGRESSIVE_MIN_VOTES
    cse.LAYER2_CONFIDENCE_RATIO = AGGRESSIVE_RATIO
    cse.FAMILY_BACKOFF_THRESHOLD = AGGRESSIVE_FAMILY_BACKOFF

    engine = ContextualSubstitutionEngine()

    ctx_vh = engine.humanize_fr(
        fr1=vh_seg["FR1"],
        cdr1=vh_seg["CDR1"],
        fr2=vh_seg["FR2"],
        cdr2=vh_seg["CDR2"],
        fr3=vh_seg["FR3"],
        vh_germline=vh_germline,
        chain="VH",
    )
    ctx_vl = engine.humanize_fr(
        fr1=vl_seg["FR1"],
        cdr1=vl_seg["CDR1"],
        fr2=vl_seg["FR2"],
        cdr2=vl_seg["CDR2"],
        fr3=vl_seg["FR3"],
        vh_germline=vl_germline,
        chain="VK",
    )

    vh_out = ctx_vh.output_seq + vh_seg["CDR3"] + HUMAN_VH_FR4
    vl_out = ctx_vl.output_seq + vl_seg["CDR3"] + HUMAN_VK_FR4

    sequences["9aa_ctx_aggressive"] = {
        "vh": vh_out,
        "vl": vl_out,
        "vh_germline": vh_germline,
        "vl_germline": vl_germline,
        "vh_fr4_source": "human_universal_clinical",
        "vl_fr4_source": "human_universal_clinical",
        "thresholds": {
            "min_votes_layer2": AGGRESSIVE_MIN_VOTES,
            "layer2_confidence_ratio": AGGRESSIVE_RATIO,
            "family_backoff_threshold": AGGRESSIVE_FAMILY_BACKOFF,
        },
        "vh_replacements": ctx_vh.n_replacements,
        "vl_replacements": ctx_vl.n_replacements,
        "vh_decisions": _replacement_decisions(ctx_vh),
        "vl_decisions": _replacement_decisions(ctx_vl),
        "vh_summary_by_layer": ctx_vh.summary_by_layer,
        "vl_summary_by_layer": ctx_vl.summary_by_layer,
    }

    SEQUENCES_PATH.write_text(json.dumps(sequences, indent=2))

    print("Generated 9aa_ctx_aggressive")
    print(f"  VH replacements: {ctx_vh.n_replacements}")
    print(f"  VL replacements: {ctx_vl.n_replacements}")
    print(f"  VH length: {len(vh_out)}")
    print(f"  VL length: {len(vl_out)}")


if __name__ == "__main__":
    main()
