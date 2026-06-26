from typing import Dict, List


def _get_region_seq(numbering: List[Dict], start: int, end: int) -> str:
    """
     IMGT position （ '-'）
    """
    aas = []
    for item in numbering:
        pos = item["position"]
        aa = item["aa"]
        if aa == "-":
            continue
        if start <= pos <= end:
            aas.append(aa)
    return "".join(aas)


def classify_vh_vhh(numbering: List[Dict]) -> Dict:
    """
     VH/VHH ：

    ：
      - FR2 （E/Q/R/G）
      - CDR3 
      - FR4  WGQ 

    ：
      {
        "is_vhh_like": bool,
        "score": float,
        "features": {...}
      }
    """
    # FR2: IMGT 39-55
    fr2 = _get_region_seq(numbering, 39, 55)
    # CDR3: 105-117
    cdr3 = _get_region_seq(numbering, 105, 117)
    # FR4: 118+
    fr4 = _get_region_seq(numbering, 118, 1000)

    score = 0.0
    features = {}

    #  1：FR2 
    if fr2:
        hydros = sum(fr2.count(x) for x in ["E", "Q", "R", "G"])
        ratio = hydros / len(fr2)
        features["fr2_hydrophilic_ratio"] = ratio
        if ratio >= 0.4:  # ，
            score += 1.5
    else:
        features["fr2_hydrophilic_ratio"] = None

    #  2：CDR3 
    cdr3_len = len(cdr3)
    features["cdr3_length"] = cdr3_len
    if cdr3_len >= 15:
        score += 1.0

    #  3：FR4 motif
    if fr4.startswith("WGQ"):
        features["fr4_motif"] = "WGQ*"
        score += 1.0
    elif fr4:
        features["fr4_motif"] = fr4[:4]
    else:
        features["fr4_motif"] = None

    # ：score > 2.0  VHH-like
    is_vhh_like = score >= 2.0

    return {
        "is_vhh_like": is_vhh_like,
        "score": score,
        "features": features,
    }
