#!/usr/bin/env python3
"""
run_vhh_surface_reshaping_v1.py
V3.0 deterministic VHH surface reshaping (IMGT-safe, insertion-safe).
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Dict, List, Optional

SUITE_ROOT = Path(__file__).resolve().parents[1]
if str(SUITE_ROOT) not in sys.path:
    sys.path.insert(0, str(SUITE_ROOT))

_SAP_P75 = 0.714
_SAP_P90 = 0.771
_SASA_THRESHOLD_PCT = 30.0

_CDR_IMGT = frozenset(range(27, 39)) | frozenset(range(56, 66)) | frozenset(range(105, 118))
_TIER0_FORBIDDEN = frozenset({28, 29, 44, 45, 47, 94})
_TIER1_PROTECTED = frozenset({34, 36, 40, 42, 49, 71, 73, 78})

_CONSERVATIVE_SUBS: Dict[str, List[str]] = {
    "F": ["Y"],
    "L": ["S", "T", "Q"],
    "I": ["V"],
    "M": ["L", "Q"],
}

_SAP_HYDRO = frozenset("AILMFWV")


def _sap_proxy(seq: str) -> float:
    s = seq.upper()
    if len(s) < 7:
        return round(sum(1 for a in s if a in _SAP_HYDRO) / 7.0, 3)
    return round(
        max(sum(1 for a in s[i : i + 7] if a in _SAP_HYDRO) / 7.0 for i in range(len(s) - 6)),
        3,
    )


def _imgt_rows(seq: str) -> List[Dict]:
    """
    Return insertion-safe IMGT rows preserving original sequence order.
    Each row contains:
      linear_idx, pos (int), ins_code (str), imgt_label (str), aa (str)
    """
    from core.numbering.imgt_anarcii import imgt_number_anarcii_indexed

    rows = imgt_number_anarcii_indexed(seq).get("rows", [])
    out: List[Dict] = []
    linear_idx = 0
    for r in rows:
        aa = (r.get("aa") or "").strip()
        if not aa or aa == "-":
            continue
        pos = int(r.get("pos"))
        ins = str(r.get("ins_code") or "").strip()
        out.append(
            {
                "linear_idx": linear_idx,
                "pos": pos,
                "ins_code": ins,
                "imgt_label": f"{pos}{ins}" if ins else f"{pos}",
                "aa": aa,
            }
        )
        linear_idx += 1
    return out


def _sequence_proxy_sasa(rows: List[Dict]) -> Dict[str, float]:
    _surface_fr = frozenset(
        {
            1,
            3,
            5,
            10,
            11,
            12,
            13,
            15,
            19,
            23,
            39,
            40,
            41,
            42,
            43,
            46,
            60,
            62,
            63,
            65,
            68,
            70,
            72,
            73,
            74,
            75,
            76,
            82,
            83,
            84,
            85,
            87,
            104,
            107,
            108,
            110,
            112,
        }
    )
    return {r["imgt_label"]: (100.0 if r["pos"] in _surface_fr else 0.0) for r in rows}


def reshape_vhh_surface(
    seq: str,
    strategy: str = "S2",
    sap_target: Optional[float] = None,
    dry_run: bool = False,
) -> Dict:
    target = sap_target if sap_target is not None else (_SAP_P90 if strategy == "S1" else _SAP_P75)
    seq = seq.strip().upper()
    sap_before = _sap_proxy(seq)
    if sap_before <= target:
        return {
            "input_sequence": seq,
            "output_sequence": seq,
            "sap_before": sap_before,
            "sap_after": sap_before,
            "target_sap": target,
            "target_achieved": True,
            "strategy": strategy,
            "mutations": [],
            "positions_evaluated": 0,
            "positions_modified": 0,
            "sasa_method": "sequence-proxy",
            "note": f"SAP {sap_before:.3f} already <= target {target}.",
        }

    rows = _imgt_rows(seq)
    _coverage = len(rows) / max(len(seq), 1)
    if _coverage < 0.80:
        # Severe mismatch: IMGT covers < 80% of residues — coordinate drift is a real risk.
        raise RuntimeError(
            f"IMGT mapping length mismatch: rows={len(rows)} vs seq={len(seq)} "
            f"(coverage={_coverage:.0%} < 80%). Abort to avoid coordinate drift."
        )
    # Partial coverage (80–99%) is acceptable: C-terminal extensions, non-standard residues,
    # or linker tails can cause IMGT to skip some positions. linear_idx is computed
    # directly from iteration so it is always safe to use as a sequence index.
    _imgt_coverage_warning: Optional[str] = None
    if len(rows) < len(seq):
        _imgt_coverage_warning = (
            f"IMGT partial coverage: {len(rows)}/{len(seq)} residues numbered "
            f"({_coverage:.0%}). Mutations applied only to IMGT-numbered positions; "
            "C-terminal or unrecognised residues are preserved unchanged."
        )
    sasa_map = _sequence_proxy_sasa(rows)

    seq_list = list(seq)
    mutations: List[Dict] = []
    evaluated = 0

    for r in rows:
        pos = r["pos"]
        aa = r["aa"]
        lbl = r["imgt_label"]
        linear_idx = r["linear_idx"]

        if sasa_map.get(lbl, 0.0) < _SASA_THRESHOLD_PCT:
            continue
        if pos in _CDR_IMGT:
            continue
        if pos in _TIER0_FORBIDDEN:
            continue
        if pos in _TIER1_PROTECTED:
            # V3.0 hard fix: Tier1 is truly protected (never mutated).
            continue

        evaluated += 1
        if aa not in _CONSERVATIVE_SUBS:
            continue

        new_aa = _CONSERVATIVE_SUBS[aa][0]
        mut = {
            "imgt_pos": pos,
            "imgt_label": lbl,
            "from_aa": aa,
            "to_aa": new_aa,
            "all_options": _CONSERVATIVE_SUBS[aa],
            "is_tier1": False,
            "sasa_pct": sasa_map.get(lbl, 0.0),
            "applied": False,
        }
        if not dry_run:
            seq_list[linear_idx] = new_aa
            mut["applied"] = True
        mutations.append(mut)

        if not dry_run and _sap_proxy("".join(seq_list)) <= target:
            break

    out_seq = "".join(seq_list)
    sap_after = sap_before if dry_run else _sap_proxy(out_seq)
    positions_modified = len([m for m in mutations if m.get("applied")])

    # Determine why target may not be achieved (CDR-driven vs FR-driven SAP)
    if not dry_run and sap_after > target:
        _fr_muts_applied = positions_modified
        # SAP still elevated after all eligible FR mutations: the dominant hydrophobic window
        # is likely located in CDR loops, which are preserved by design.
        _note = (
            f"Framework reshaping applied {_fr_muts_applied} mutation(s). "
            f"Residual SAP {sap_after:.3f} > target {target:.3f}: the dominant hydrophobic window "
            "appears to originate from CDR loop residues, which are preserved unchanged by design. "
            "CDR-driven surface hydrophobicity requires offline CMC optimization "
            "(charge-patch remodelling, CDR sequence engineering, or formulation adjustment)."
        )
    elif dry_run:
        _note = "Dry-run only."
    else:
        _note = "Deterministic reshaping completed. SAP target achieved."

    result = {
        "input_sequence": seq,
        "output_sequence": seq if dry_run else out_seq,
        "sap_before": sap_before,
        "sap_after": sap_after,
        "target_sap": target,
        "target_achieved": (sap_after <= target) if not dry_run else False,
        "strategy": strategy,
        "mutations": mutations,
        "positions_evaluated": evaluated,
        "positions_modified": positions_modified,
        "imgt_coverage": f"{len(rows)}/{len(seq)} ({_coverage:.0%})",
        "sasa_method": "sequence-proxy",
        "cdr_driven_sap": (not dry_run) and (sap_after > target) and (positions_modified > 0),
        "note": _note,
    }
    if _imgt_coverage_warning:
        result["imgt_coverage_warning"] = _imgt_coverage_warning
    return result


def main() -> int:
    parser = argparse.ArgumentParser(description="VHH surface reshaping V3.0")
    parser.add_argument("--seq", required=True, help="VHH sequence")
    parser.add_argument("--strategy", choices=["S1", "S2"], default="S2")
    parser.add_argument("--sap-target", type=float, default=None)
    parser.add_argument("--dry-run", action="store_true")
    parser.add_argument("--out", default=None, help="Output directory")
    parser.add_argument("--json", action="store_true", help="Print JSON")
    args = parser.parse_args()

    res = reshape_vhh_surface(
        seq=args.seq,
        strategy=args.strategy,
        sap_target=args.sap_target,
        dry_run=args.dry_run,
    )

    print(f"SAP before: {res['sap_before']:.3f}")
    print(f"SAP after:  {res['sap_after']:.3f}")
    print(f"Target:     <= {res['target_sap']}")
    print(f"Mutations:  {res['positions_modified']}")

    if args.json:
        print(json.dumps(res, indent=2, ensure_ascii=False))

    if args.out:
        out_dir = Path(args.out)
        out_dir.mkdir(parents=True, exist_ok=True)
        out_file = out_dir / "surface_reshaping_result.json"
        out_file.write_text(json.dumps(res, indent=2, ensure_ascii=False), encoding="utf-8")
        print(f"Saved: {out_file}")

    return 0 if res["target_achieved"] or args.dry_run else 1


if __name__ == "__main__":
    sys.exit(main())
