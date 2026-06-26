# ================================================================
#  anarci_abnumber_adapter.py — v2.0 Official Release
#  Unified IMGT-based segmentation for VH / VL / VHH
#  Provides: FR/CDR segmentation, VHH hallmark detection,
#            constant-region splitting, ANARCI fallback.
# ================================================================

from dataclasses import dataclass
from typing import List, Dict, Optional, Literal
from abnumber import Chain as AbChain

# Try to import anarci (may fail with newer versions)
try:
    from anarci import anarci
    HAS_ANARCI = True
except ImportError:
    HAS_ANARCI = False
    anarci = None

RegionName = Literal["FR1", "CDR1", "FR2", "CDR2", "FR3", "CDR3", "FR4"]

# -------------------------------
# Data Models
# -------------------------------

@dataclass
class PositionRecord:
    idx: int           # global index
    pos: str           # IMGT position: H27, H27A, L50...
    region: str        # FR1/CDR1/... or CH_const/CL_const
    aa: str            # amino acid


@dataclass
class ChainAnnotation:
    scheme: str
    chain_type: str
    sequence: str
    v_length: int
    regions_seq: Dict[str, str]
    positions: List[PositionRecord]
    constant_seq: str
    constant_positions: List[PositionRecord]
    flags: Dict[str, object]


# -------------------------------
# Internal helpers
# -------------------------------

def _extract_imgt_positions(ab_chain: AbChain):
    """Extract IMGT positions from abnumber Chain."""
    regions = ab_chain.regions  # dict: region -> {Position: aa}
    records = []

    for region_name, pos_dict in regions.items():
        # pos_dict: {PositionObj → "A"}
        for pos_obj, aa in pos_dict.items():
            pos_str = pos_obj.format(chain_type=True)  # H27 / H27A
            records.append((pos_obj.number, pos_obj.letter, pos_str, region_name, aa))

    # IMGT ordering
    records_sorted = sorted(records, key=lambda x: (x[0], x[1]))
    return records_sorted


def _try_anarci(seq: str):
    """Fallback segmentation using ANARCI if abnumber fails."""
    if not HAS_ANARCI:
        raise ImportError("anarci not available")
    res = anarci([("seq", seq)], scheme="imgt")
    numbering = res[0][0][0]  # list of (aa, (pos, ins_code), region)
    chain_type = res[0][1]

    records = []
    for idx, (aa, posinfo, region) in enumerate(numbering, start=1):
        if posinfo is None:
            continue
        num, ins = posinfo
        ins = "" if ins is None else ins
        pos = f"{chain_type}{num}{ins}"
        records.append(
            (num, ins, pos, region, aa)
        )
    return sorted(records, key=lambda x: (x[0], x[1]))


# -------------------------------
# Main function
# -------------------------------

def annotate_chain(seq: str,
                   scheme: str = "imgt",
                   chain_type_hint: Optional[str] = None) -> ChainAnnotation:

    seq = seq.replace("\n", "").strip()

    # 1) Try abnumber (preferred)
    ab_chain = None
    records = None
    ab_chain_type = chain_type_hint

    try:
        ab_chain = AbChain(seq, scheme=scheme, chain_type=ab_chain_type)
        # if chain_type not correct, abnumber auto-detects
        ab_chain_type = ab_chain.chain_type
        records = _extract_imgt_positions(ab_chain)
    except Exception:
        ab_chain = None

    # 2) Fallback to ANARCI
    if ab_chain is None:
        try:
            records = _try_anarci(seq)
            ab_chain_type = records[0][2][0]  # first character: H/K/L
        except Exception:
            # last fallback: crude segmentation (not recommended)
            ab_chain_type = chain_type_hint or "H"
            records = []
            for i, aa in enumerate(seq, start=1):
                pos = f"{ab_chain_type}{i}"
                region = "UNKNOWN"
                records.append((i, "", pos, region, aa))

    # -------------------------------
    # Build structured FR/CDR sequences
    # -------------------------------
    FR1 = FR2 = FR3 = FR4 = ""
    CDR1 = CDR2 = CDR3 = ""

    region_map = {
        "FR1": [],
        "CDR1": [],
        "FR2": [],
        "CDR2": [],
        "FR3": [],
        "CDR3": [],
        "FR4": [],
    }

    for _, _, pos, region, aa in records:
        if region in region_map:
            region_map[region].append(aa)

    regions_seq = {k: "".join(v) for k, v in region_map.items()}

    # -------------------------------
    # Constant region detection
    # -------------------------------
    v_len = len(records)
    constant_seq = seq[v_len:]
    constant_records: List[PositionRecord] = []

    if constant_seq:
        last_num = records[-1][0]
        ct = ab_chain_type
        for i, aa in enumerate(constant_seq):
            pseudo_idx = v_len + 1 + i
            pseudo_pos = f"{ct}{last_num + 1 + i}"
            region = "CH_const" if ct == "H" else "CL_const"
            constant_records.append(
                PositionRecord(
                    idx=pseudo_idx,
                    pos=pseudo_pos,
                    region=region,
                    aa=aa,
                )
            )

    # -------------------------------
    # Convert V-region records to PositionRecord list
    # -------------------------------
    pos_records: List[PositionRecord] = []
    for idx, (num, ins, pos, region, aa) in enumerate(records, start=1):
        pos_records.append(
            PositionRecord(
                idx=idx,
                pos=pos,
                region=region,
                aa=aa,
            )
        )

    # -------------------------------
    # VHH hallmark detection
    # -------------------------------
    hallmark_sites = [37, 44, 45, 47]
    fr2_hallmarks = {}

    # rebuild region dict {region → [(num, ins, pos, region, aa)]}
    region_dict = {}
    for rec in records:
        _, _, pos, region, aa = rec
        region_dict.setdefault(region, []).append(rec)

    fr2_records = region_dict.get("FR2", [])
    for num, ins, pos, region, aa in fr2_records:
        if num in hallmark_sites:
            key = f"H{num}{ins}"
            fr2_hallmarks[key] = aa

    is_vhh_like = (
        ab_chain_type == "H"
        and len(regions_seq["FR4"]) <= 11
        and len(fr2_hallmarks) >= 2
    )

    flags = {
        "fr2_hallmarks": fr2_hallmarks,
        "is_vhh_like": is_vhh_like,
        "chain_type_final": ab_chain_type,
    }

    # -------------------------------
    # Return annotation
    # -------------------------------
    return ChainAnnotation(
        scheme=scheme,
        chain_type=ab_chain_type,
        sequence=seq,
        v_length=v_len,
        regions_seq=regions_seq,
        positions=pos_records,
        constant_seq=constant_seq,
        constant_positions=constant_records,
        flags=flags,
    )





















