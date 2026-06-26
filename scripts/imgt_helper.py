from vh_vhh_classifier import classify_vh_vhh
from typing import List, Dict
from anarci_client import imgt_number


def get_imgt_numbering(seq: str) -> Dict:
    """
     ANARCI ， JSON 
    """
    return imgt_number(seq)


def rebuild_v_sequence(numbering: List[Dict]) -> str:
    """
     ANARCI  V （“-”）
    """
    aas = []
    for item in numbering:
        aa = item["aa"]
        if aa != "-":
            aas.append(aa)
    return "".join(aas)


def simple_fr_cdr_split(numbering: List[Dict]) -> Dict[str, str]:
    """
     FR/CDR （IMGT ），：
      FR1:  1-26
      CDR1: 27-38
      FR2:  39-55
      CDR2: 56-65
      FR3:  66-104
      CDR3: 105-117
      FR4:  >=118
    。
    """
    buckets = {
        "FR1": [],
        "CDR1": [],
        "FR2": [],
        "CDR2": [],
        "FR3": [],
        "CDR3": [],
        "FR4": [],
    }

    for item in numbering:
        pos = item["position"]
        aa = item["aa"]
        if aa == "-":
            continue

        if 1 <= pos <= 26:
            buckets["FR1"].append(aa)
        elif 27 <= pos <= 38:
            buckets["CDR1"].append(aa)
        elif 39 <= pos <= 55:
            buckets["FR2"].append(aa)
        elif 56 <= pos <= 65:
            buckets["CDR2"].append(aa)
        elif 66 <= pos <= 104:
            buckets["FR3"].append(aa)
        elif 105 <= pos <= 117:
            buckets["CDR3"].append(aa)
        else:
            buckets["FR4"].append(aa)

    return {k: "".join(v) for k, v in buckets.items()}
def analyze_v_region(seq: str) -> Dict:
    """
     V ：

    -  ANARCI /imgt_numbering 
    -  V （ gap）
    -  FR/CDR 
    - VH / VHH 

     dict， pipeline 。
    """
    raw = get_imgt_numbering(seq)
    if not raw.get("success"):
        return {
            "success": False,
            "reason": raw.get("error", "anarci_failed"),
            "length": raw.get("length", len(seq)),
        }

    numbering = raw["numbering"]
    v_seq = rebuild_v_sequence(numbering)
    segments = simple_fr_cdr_split(numbering)
    vh_vhh = classify_vh_vhh(numbering)

    return {
        "success": True,
        "v_sequence": v_seq,
        "v_length": len(v_seq),
        "numbering": numbering,
        "segments": segments,
        "vh_vhh": vh_vhh,
        "meta": {
            "v_start": raw.get("v_start"),
            "v_end": raw.get("v_end"),
            "anarci_length": raw.get("length"),
        },
    }

