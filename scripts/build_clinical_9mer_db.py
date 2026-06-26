#!/usr/bin/env python3
"""
scripts/build_clinical_9mer_db.py

Builds a 9-mer peptide frequency database from the 842 clinical antibodies.

Schema v1.3 — adds IGK (VL kappa) sub-libraries alongside VH:
  {
    "_meta": {...},

    # VH (heavy chain)
    "9mers":              { <9mer>: count, ... },   # VH global pool
    "family_9mers":       { "IGHV1": {...}, ... },  # VH family sub-libs
    "family_n_antibodies":{ "IGHV1": 282, ... },

    # VK (kappa light chain)
    "vl_9mers":              { <9mer>: count, ... },
    "vl_family_9mers":       { "IGKV1": {...}, ... },
    "vl_family_n_antibodies":{ "IGKV1": 404, ... },
  }

Layer 2 voting strategy:
  chain="VH" -> uses 9mers / family_9mers keyed on IGHV family
  chain="VK" -> uses vl_9mers / vl_family_9mers keyed on IGKV family
  Sparse family data -> automatic fallback to the chain-specific global pool.
"""

import json
import csv
import re
from collections import Counter, defaultdict
from pathlib import Path

SUITE_ROOT = Path(__file__).resolve().parents[1]
_ATLAS_PATHS = [
    SUITE_ROOT / "data" / "engineered_459_atlas" / "master_table.csv",
    SUITE_ROOT / "data" / "natural_380_atlas" / "master_table.csv",
]
OUT_DB = SUITE_ROOT / "config" / "clinical_842_9mer_db.json"

VALID_AA = frozenset("ACDEFGHIKLMNPQRSTVWY")
_VH_FAM_RE = re.compile(r"(IGHV\d+)", re.IGNORECASE)
_VK_FAM_RE = re.compile(r"(IGKV\d+)", re.IGNORECASE)


def _is_valid_9mer(s: str) -> bool:
    """Strict 20AA whitelist; rejects X, B, Z, U, O, gaps and any junk char."""
    return len(s) == 9 and all(c in VALID_AA for c in s)


def _parse_vh_family(germline: str) -> str:
    m = _VH_FAM_RE.search((germline or "").upper())
    return m.group(1) if m else "UNKNOWN"


def _parse_vk_family(germline: str) -> str:
    m = _VK_FAM_RE.search((germline or "").upper())
    return m.group(1) if m else "UNKNOWN"


def _count_9mers(full_seq: str,
                 global_ctr: Counter,
                 family_ctr: Counter,
                 rejected: list) -> None:
    """Slide a 9-mer window over full_seq and update counters in-place."""
    for i in range(len(full_seq) - 8):
        nm = full_seq[i:i + 9]
        if _is_valid_9mer(nm):
            global_ctr[nm] += 1
            family_ctr[nm] += 1
        else:
            rejected.append(nm)


def _print_family_stats(label: str, family_n: Counter,
                        family_counts: dict, total: int) -> None:
    print(f"\n{label} family breakdown:")
    for fam, n in sorted(family_n.items(), key=lambda x: -x[1]):
        pct = n / total * 100
        u9m = len(family_counts[fam])
        print(f"  {fam:12s}  n={n:3d} ({pct:4.1f}%)  unique_9mers={u9m:,}")


def build_9mer_db() -> None:
    print("Loading 842 clinical antibodies to build 9-mer database (VH + VK)...")

    # VH counters
    vh_global: Counter = Counter()
    vh_family_counts: dict = defaultdict(Counter)
    vh_family_n: Counter = Counter()

    # VK counters
    vk_global: Counter = Counter()
    vk_family_counts: dict = defaultdict(Counter)
    vk_family_n: Counter = Counter()

    total_antibodies = 0
    rejected: list = []

    for path in _ATLAS_PATHS:
        if not path.exists():
            print(f"  [WARN] Not found: {path}")
            continue
        with open(path, encoding="utf-8") as f:
            for row in csv.DictReader(f):
                # ── VH ───────────────────────────────────────────────────────
                vh_fr1  = (row.get("vh_fr1")  or "").upper().strip()
                vh_cdr1 = (row.get("vh_cdr1") or "").upper().strip()
                vh_fr2  = (row.get("vh_fr2")  or "").upper().strip()
                vh_cdr2 = (row.get("vh_cdr2") or "").upper().strip()
                vh_fr3  = (row.get("vh_fr3")  or "").upper().strip()

                # ── VL (IGK) ─────────────────────────────────────────────────
                vl_fr1  = (row.get("vl_fr1")  or "").upper().strip()
                vl_cdr1 = (row.get("vl_cdr1") or "").upper().strip()
                vl_fr2  = (row.get("vl_fr2")  or "").upper().strip()
                vl_cdr2 = (row.get("vl_cdr2") or "").upper().strip()
                vl_fr3  = (row.get("vl_fr3")  or "").upper().strip()

                if not (vh_fr1 and vh_fr2 and vh_fr3):
                    continue

                total_antibodies += 1

                # VH
                vh_fam = _parse_vh_family(row.get("vh_germline") or "")
                vh_family_n[vh_fam] += 1
                vh_seq = vh_fr1 + vh_cdr1 + vh_fr2 + vh_cdr2 + vh_fr3
                _count_9mers(vh_seq, vh_global, vh_family_counts[vh_fam], rejected)

                # VK (skip if VL data absent)
                if vl_fr1 and vl_fr2 and vl_fr3:
                    vk_fam = _parse_vk_family(row.get("vl_germline") or "")
                    vk_family_n[vk_fam] += 1
                    vk_seq = vl_fr1 + vl_cdr1 + vl_fr2 + vl_cdr2 + vl_fr3
                    _count_9mers(vk_seq, vk_global, vk_family_counts[vk_fam], rejected)

    # ── Summary ───────────────────────────────────────────────────────────────
    print(f"\nProcessed {total_antibodies} antibodies.")
    print(f"VH global unique 9-mers : {len(vh_global)}")
    print(f"VK global unique 9-mers : {len(vk_global)}")
    print(f"Rejected 9-mers (total) : {len(rejected)}")
    _print_family_stats("VH (IGHV)", vh_family_n, vh_family_counts, total_antibodies)
    _print_family_stats("VK (IGKV)", vk_family_n, vk_family_counts, total_antibodies)

    # ── Serialise ─────────────────────────────────────────────────────────────
    payload = {
        "_meta": {
            "description": (
                "9-mer frequencies from 842 clinical antibodies. "
                "VH and IGK (kappa VL) sub-libraries both present. "
                "Family-conditioned voting with automatic global fallback. "
                "Used with OAS supplement (oas_human_9mer_v1.json.gz) for "
                "dual-database weighted voting in ContextualSubstitutionEngine."
            ),
            "n_antibodies": total_antibodies,
            "vh_unique_9mers_global": len(vh_global),
            "vk_unique_9mers_global": len(vk_global),
            "rejected_9mers": len(rejected),
            "filter": "strict_20AA_whitelist (ACDEFGHIKLMNPQRSTVWY)",
            "schema_version": "2.0",
            "oas_supplement": "oas_human_9mer_v1.json.gz",
            "voting_weights": {
                "W_CLINICAL_VOTE": 10,
                "W_OAS_VOTE": 1,
                "note": (
                    "Each clinical-842 window hit = W_CLINICAL_VOTE votes. "
                    "Each OAS-present window hit = W_OAS_VOTE votes. "
                    "Combined score used for Layer-2 threshold and ratio check."
                )
            },
        },
        # VH
        "family_n_antibodies": dict(vh_family_n),
        "9mers": dict(vh_global.most_common()),
        "family_9mers": {
            fam: dict(ctr.most_common())
            for fam, ctr in sorted(vh_family_counts.items())
        },
        # VK
        "vl_family_n_antibodies": dict(vk_family_n),
        "vl_9mers": dict(vk_global.most_common()),
        "vl_family_9mers": {
            fam: dict(ctr.most_common())
            for fam, ctr in sorted(vk_family_counts.items())
        },
    }

    OUT_DB.write_text(json.dumps(payload, indent=2), encoding="utf-8")
    sz_mb = OUT_DB.stat().st_size / 1024 / 1024
    print(f"\nSaved 9-mer database to {OUT_DB.name}  ({sz_mb:.1f} MB)")


if __name__ == "__main__":
    build_9mer_db()
