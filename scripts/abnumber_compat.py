#!/usr/bin/env python
# -*- coding: utf-8 -*-

# DEPRECATED — replaced by anarci_abnumber_adapter.py
# This module is no longer used in v7.0 and will be removed in a future version.

"""
abnumber_compat.py

 FR/CDR ：

-  abnumber（IMGT/Kabat ）

-  abnumber ，""

 VH / VHH / VL / VK 、、，：

- residue_table:  region（FR1/CDR1/...）

- regions:  start/end

- segments: 

（）:

    from scripts.abnumber_compat import segment_chain

    seg = segment_chain("QVQLVESGGGLV...", chain_type="H", scheme="imgt")

    print(seg["segments"]["FR1"])

    print(seg["residue_table"][0:10])

:

    python scripts/abnumber_compat.py --sequence QVQLVESGGGLV... --chain-type H

:

-  fallback  pipeline ，。

- ， abnumber  VHH / VH 。
"""

from __future__ import annotations

import argparse
from dataclasses import dataclass
from typing import Dict, List, Optional, Any

#  abnumber， fallback
try:
    from abnumber import Chain as AbNumberChain  # type: ignore
    HAS_ABNUMBER = True
except Exception:
    HAS_ABNUMBER = False


@dataclass
class ResidueRecord:
    index: int           # 1-based 
    aa: str              # 
    region: str          # FR1/CDR1/FR2/CDR2/FR3/CDR3/FR4/UNKNOWN
    scheme_pos: str      # （ 1, 2, 27A ），fallback  str(index)


def _build_segmentation_from_abnumber(
    chain: Any,
    chain_type: str,
    scheme: str,
) -> Dict[str, Any]:
    """
     abnumber  Chain  segmentation 。
    """
    residue_table: List[ResidueRecord] = []
    regions: Dict[str, Dict[str, int]] = {
        "FR1": {"start": 0, "end": 0},
        "CDR1": {"start": 0, "end": 0},
        "FR2": {"start": 0, "end": 0},
        "CDR2": {"start": 0, "end": 0},
        "FR3": {"start": 0, "end": 0},
        "CDR3": {"start": 0, "end": 0},
        "FR4": {"start": 0, "end": 0},
    }

    # abnumber  residues :
    # - position ( 1, 2, 3, 27A, 27B...)
    # - region (FR1/CDR1/...)
    # - aa
    seq = ""
    for i, r in enumerate(chain.residues):
        aa = r.aa
        seq += aa
        region = r.region or "UNKNOWN"
        pos = str(r.position)
        idx = i + 1

        residue_table.append(
            ResidueRecord(
                index=idx,
                aa=aa,
                region=region,
                scheme_pos=pos,
            )
        )

        #  region  start/end（ index ）
        if region in regions:
            if regions[region]["start"] == 0:
                regions[region]["start"] = idx
            regions[region]["end"] = idx

    #  regions  segments（）
    segments: Dict[str, str] = {}
    for region, info in regions.items():
        start = info["start"]
        end = info["end"]
        if start > 0 and end >= start:
            # index  1-based
            segments[region] = seq[start - 1 : end]
        else:
            segments[region] = ""

    return {
        "sequence": seq,
        "length": len(seq),
        "chain_type": chain_type,
        "scheme": scheme,
        "regions": regions,
        "segments": segments,
        "residue_table": [
            {
                "index": r.index,
                "aa": r.aa,
                "region": r.region,
                "scheme_pos": r.scheme_pos,
            }
            for r in residue_table
        ],
        "backend": "abnumber",
    }


def _fallback_segmentation(
    sequence: str,
    chain_type: str,
    scheme: str,
) -> Dict[str, Any]:
    """
     fallback： FR/CDR 。
     pipeline ，。

     VH/VHH（chain_type="H"） IMGT （ 110~130 ）:
        FR1  : 1–26
        CDR1 : 27–38
        FR2  : 39–55
        CDR2 : 56–65
        FR3  : 66–104
        CDR3 : 105–117
        FR4  : 118–(len)

    （L/K）（ κ ）。

    ：， fallback  IMGT ， debug。
    """
    n = len(sequence)

    def clip(a: int, b: int) -> tuple[int, int]:
        a = max(1, a)
        b = min(n, b)
        if a > b:
            return 0, 0
        return a, b

    if chain_type.upper() == "H":
        # Heavy / VHH
        r_fr1 = clip(1, 26)
        r_cdr1 = clip(27, 38)
        r_fr2 = clip(39, 55)
        r_cdr2 = clip(56, 65)
        r_fr3 = clip(66, 104)
        r_cdr3 = clip(105, 117)
        r_fr4 = clip(118, n)
    else:
        #  κ 
        r_fr1 = clip(1, 23)
        r_cdr1 = clip(24, 34)
        r_fr2 = clip(35, 49)
        r_cdr2 = clip(50, 56)
        r_fr3 = clip(57, 88)
        r_cdr3 = clip(89, 97)
        r_fr4 = clip(98, n)

    regions = {
        "FR1": {"start": r_fr1[0], "end": r_fr1[1]},
        "CDR1": {"start": r_cdr1[0], "end": r_cdr1[1]},
        "FR2": {"start": r_fr2[0], "end": r_fr2[1]},
        "CDR2": {"start": r_cdr2[0], "end": r_cdr2[1]},
        "FR3": {"start": r_fr3[0], "end": r_fr3[1]},
        "CDR3": {"start": r_cdr3[0], "end": r_cdr3[1]},
        "FR4": {"start": r_fr4[0], "end": r_fr4[1]},
    }

    residue_table: List[ResidueRecord] = []
    for i, aa in enumerate(sequence):
        idx = i + 1
        region = "UNKNOWN"
        for name, info in regions.items():
            if info["start"] > 0 and info["start"] <= idx <= info["end"]:
                region = name
                break
        residue_table.append(
            ResidueRecord(
                index=idx,
                aa=aa,
                region=region,
                scheme_pos=str(idx),
            )
        )

    def seg_seq(r: Dict[str, int]) -> str:
        if r["start"] == 0 or r["end"] == 0:
            return ""
        return sequence[r["start"] - 1 : r["end"]]

    segments = {name: seg_seq(info) for name, info in regions.items()}

    return {
        "sequence": sequence,
        "length": len(sequence),
        "chain_type": chain_type,
        "scheme": scheme,
        "regions": regions,
        "segments": segments,
        "residue_table": [
            {
                "index": r.index,
                "aa": r.aa,
                "region": r.region,
                "scheme_pos": r.scheme_pos,
            }
            for r in residue_table
        ],
        "backend": "fallback_fixed_boundaries",
        "warning": "abnumber ，。。",
    }


def segment_chain(
    sequence: str,
    chain_type: str = "H",
    scheme: str = "imgt",
) -> Dict[str, Any]:
    """
    （//VHH） FR/CDR 。

    :
        sequence   : （）
        chain_type : "H" (heavy/VHH), "L" (light), "K" (kappa), "LAMBDA" 
        scheme     : ， "imgt", "kabat"

    :
        segmentation ，:
        - sequence, length, chain_type, scheme
        - regions:  region  start/end (1-based)
        - segments:  region 
        - residue_table:  index/aa/region/scheme_pos
        - backend: （abnumber  fallback）
    """
    seq = (sequence or "").strip().upper()
    if not seq:
        raise ValueError("sequence ")

    ctype = chain_type.upper()
    if HAS_ABNUMBER:
        try:
            ab_chain = AbNumberChain(seq, scheme=scheme, chain_type="heavy" if ctype == "H" else "light")
            return _build_segmentation_from_abnumber(ab_chain, chain_type=ctype, scheme=scheme)
        except Exception as e:
            #  abnumber ， fallback
            return _fallback_segmentation(seq, chain_type=ctype, scheme=scheme)

    #  abnumber， fallback
    return _fallback_segmentation(seq, chain_type=ctype, scheme=scheme)


# ---------------------------------------------------------------------------
# CLI for quick testing
# ---------------------------------------------------------------------------

def main():
    parser = argparse.ArgumentParser(
        description=" FR/CDR （abnumber ）",
    )
    parser.add_argument(
        "--sequence",
        "-s",
        required=True,
        help="（）",
    )
    parser.add_argument(
        "--chain-type",
        "-c",
        default="H",
        help=": H (/VHH), L/K ()， H",
    )
    parser.add_argument(
        "--scheme",
        default="imgt",
        help="， imgt/kabat， imgt",
    )
    args = parser.parse_args()

    seg = segment_chain(
        sequence=args.sequence,
        chain_type=args.chain_type,
        scheme=args.scheme,
    )

    import json
    print(json.dumps(seg, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()

