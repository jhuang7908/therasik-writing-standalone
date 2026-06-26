#!/usr/bin/env python3
"""
scripts/build_oas_9mer_supplement.py
=====================================
Extract the pre-built OAS human antibody 9-mer database from the `promb`
package (Merck MSDLLCpapers, MIT license) and save it as a compact
gzip-compressed JSON file for use by ContextualSubstitutionEngine.

The promb `human-oas` database contains 9-mer peptides found in >=10% of
healthy human subjects across OAS (Observed Antibody Space) NGS studies.
This represents ~5.7M unique high-confidence human antibody 9-mers.

No external downloads required — the database is bundled inside `promb`.

Output: config/oas_human_9mer_v1.json.gz
Schema:
  {
    "_meta": {
        "source": "promb human-oas",
        "promb_version": "...",
        "prevalence_threshold": ">=10% of OAS subjects",
        "n_9mers": 5725303,
        "chain_scope": "VH+VK combined (no chain separation in OAS)",
        "note": "Binary presence/absence; no frequency counts available.",
        "schema_version": "1.0"
    },
    "9mers": ["QVQLVQSGV", "GRGLELVAT", ...]   # sorted list
  }

Usage:
    conda run -n anarcii python scripts/build_oas_9mer_supplement.py
"""

import gzip
import json
import time
from pathlib import Path

SUITE_ROOT = Path(__file__).resolve().parents[1]
OUT_PATH = SUITE_ROOT / "config" / "oas_human_9mer_v1.json.gz"

VALID_AA = frozenset("ACDEFGHIKLMNPQRSTVWY")


def _is_valid_9mer(s: str) -> bool:
    return len(s) == 9 and all(c in VALID_AA for c in s)


def build_oas_supplement() -> None:
    print("Loading promb human-oas database...")
    t0 = time.time()

    try:
        from promb import init_db
        import promb
        promb_version = getattr(promb, "__version__", "unknown")
    except ImportError:
        raise ImportError(
            "promb not installed. Run: conda run -n anarcii pip install promb"
        )

    db = init_db("human-oas")
    elapsed = time.time() - t0
    print(f"  Loaded in {elapsed:.1f}s")

    # Extract frozenset of 9-mer strings
    peptides: frozenset = db.peptides
    print(f"  Raw 9-mer count: {len(peptides):,}")

    # Filter to strict 20AA standard residues only (remove any with X, B, Z, U)
    print("  Filtering to strict 20AA whitelist...")
    clean = sorted(p for p in peptides if _is_valid_9mer(p))
    n_rejected = len(peptides) - len(clean)
    print(f"  Valid: {len(clean):,}  Rejected (non-standard AA): {n_rejected:,}")

    payload = {
        "_meta": {
            "source": "promb human-oas",
            "promb_version": promb_version,
            "prevalence_threshold": ">=10% of OAS (Observed Antibody Space) subjects",
            "oas_reference": (
                "Kovaltsuk et al. (2018) J. Immunol. 201:2502-2509. "
                "doi:10.4049/jimmunol.1800708"
            ),
            "biophi_reference": (
                "Prihoda et al. (2022) mAbs 14:1. "
                "doi:10.1080/19420862.2021.2020203"
            ),
            "n_9mers_raw": len(peptides),
            "n_9mers_valid": len(clean),
            "n_9mers_rejected": n_rejected,
            "chain_scope": (
                "VH+VK combined — OAS does not separate by chain in this DB. "
                "Use as chain-agnostic presence/absence signal."
            ),
            "storage": "binary presence/absence (no per-9mer frequency counts)",
            "voting_role": (
                "OAS supplement for Layer-2 voting. "
                "Each OAS-present window contributes W_OAS votes; "
                "clinical-842 windows contribute W_CLINICAL votes. "
                "See contextual_substitution_engine.py for weights."
            ),
            "schema_version": "1.0",
        },
        "9mers": clean,
    }

    print(f"  Writing to {OUT_PATH.name}...")
    t1 = time.time()
    with gzip.open(OUT_PATH, "wt", encoding="utf-8") as f:
        json.dump(payload, f, separators=(",", ":"))

    sz_mb = OUT_PATH.stat().st_size / 1024 / 1024
    print(f"  Done in {time.time()-t1:.1f}s  ({sz_mb:.1f} MB compressed)")
    print(f"\n✓ OAS supplement saved: {OUT_PATH}")
    print(f"  Valid 9-mers : {len(clean):,}")
    print(f"  File size    : {sz_mb:.1f} MB")


if __name__ == "__main__":
    build_oas_supplement()
