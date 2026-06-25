import json
from cleaner import clean_sequence
from v_finder import VRegionFinder
from v_classifier import VRegionClassifier
from imgt_segmenter import IMGT_Segmenter
from fc_detector import FcDetector
from linker_tag import LinkerTagDetector


def parse_antibody(raw_seq: str):
    """（RASI v1.0）"""

    result = {
        "meta": {"status": "processing", "warnings": []},
        "v_region": {},
        "classification": {},
        "fr_cdr": {},
        "fc_region": {},
        "linker_tag": []
    }

    # Step 1: 
    seq = clean_sequence(raw_seq)
    if len(seq) < 50:
        result["meta"]["status"] = "failed"
        result["meta"]["warnings"].append("Sequence too short (<50 AA)")
        return result

    # Step 2: V （ + ）
    v_finder = VRegionFinder
    v_region = v_finder.find_v_region(seq)
    result["v_region"] = v_region

    if not v_region["found"]:
        result["meta"]["warnings"].append("V region not detected; degraded mode")
        result["meta"]["status"] = "partial_success"
        return result

    vseq = v_region["sequence"]

    # Step 3: VH / VHH 
    classifier = VRegionClassifier
    vtype = classifier.classify(vseq)
    result["classification"] = vtype

    # Step 4: FR/CDR IMGT 
    segmenter = IMGT_Segmenter
    fr_cdr = segmenter.segment(vseq, vtype["is_vhh"])
    result["fr_cdr"] = fr_cdr

    # Step 5: Fc 
    fc_detector = FcDetector
    fc_info = fc_detector.detect_fc(seq, v_region["end"])
    result["fc_region"] = fc_info

    # Step 6: Linker / Tag 
    lt_detector = LinkerTagDetector
    linkers = lt_detector.detect(seq, v_region, fc_info)
    result["linker_tag"] = linkers

    # Final
    result["meta"]["status"] = "success"
    return result


def parse_sequence(raw_seq: str):
    """
    Simplified API for antibody sequence parsing.
    Returns a simplified structure suitable for JSON serialization.
    """
    result = parse_antibody(raw_seq)
    
    # Transform to match expected test structure
    simplified = {
        "v_region": {
            "found": result.get("v_region", {}).get("found", False),
            "start": result.get("v_region", {}).get("start", -1),
            "end": result.get("v_region", {}).get("end", -1),
            "sequence": result.get("v_region", {}).get("sequence", ""),
            "confidence": result.get("v_region", {}).get("confidence", 0.0),
        },
        "is_vhh_like": result.get("classification", {}).get("is_vhh", False),
        "constant_region": {
            "fc_present": result.get("fc_region", {}).get("present", False),
            "species": result.get("fc_region", {}).get("species", "unknown"),
            "confidence": result.get("fc_region", {}).get("confidence", 0.0),
        },
        "fr_cdr": result.get("fr_cdr", {}),
        "linker_tag": result.get("linker_tag", []),
        "meta": result.get("meta", {})
    }
    
    # Ensure all values are JSON serializable
    def make_json_serializable(obj):
        """Recursively convert objects to JSON-serializable types"""
        if isinstance(obj, dict):
            return {k: make_json_serializable(v) for k, v in obj.items}
        elif isinstance(obj, list):
            return [make_json_serializable(item) for item in obj]
        elif isinstance(obj, (str, int, float, bool)) or obj is None:
            return obj
        else:
            return str(obj)
    
    return make_json_serializable(simplified)


if __name__ == "__main__":
    example = input("Paste antibody sequence:\n")
    out = parse_antibody(example)
    print(json.dumps(out, indent=2, ensure_ascii=False))





















