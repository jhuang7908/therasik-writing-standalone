#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Prepare Thera-SAbDab dataset for canonical comparison.

Performs:
1. QC validation (sequence format, length checks)
2. ANARCII IMGT numbering
3. Germline matching (FR1-FR3 identity)
4. Representative selection by germline

Input:
- data/thera_sabdab/thera_export.xlsx (must have >100 rows)

Output:
- data/thera_sabdab/thera_qc_pass.xlsx
- data/thera_sabdab/thera_germline_mapping.csv
- data/thera_sabdab/thera_representatives_by_germline.yaml
"""

import sys
import re
import hashlib
import pandas as pd
import yaml
from pathlib import Path
from typing import Dict, List, Any, Optional, Tuple
from collections import defaultdict

PROJECT_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT_ROOT))

try:
    from core.numbering.imgt_anarcii import imgt_number_anarcii, IMGTNumberingError
    from core.vhh_humanization import split_regions
    HAS_ANARCII = True
except ImportError as e:
    HAS_ANARCII = False
    print(f"❌ ERROR: ANARCII not available: {e}")
    print("Install with: pip install anarcii")
    sys.exit(1)

# IMGT region boundaries for FR1-FR3 extraction
IMGT_FRAMEWORK_REGIONS = {
    "FR1": {"start": 1, "end": 26},
    "FR2": {"start": 39, "end": 55},
    "FR3": {"start": 66, "end": 104},
}

# Standard 20 amino acids
STANDARD_AA = set("ACDEFGHIKLMNPQRSTVWY")


def validate_sequence(seq: str, chain_type: str) -> Tuple[bool, Optional[str]]:
    """
    Validate sequence format: 20 aa letters + optional gaps.
    
    Returns:
        (is_valid, error_message)
    """
    if not seq or not isinstance(seq, str):
        return False, "Empty or invalid sequence"
    
    # Remove gaps and whitespace for validation
    seq_clean = seq.upper().replace("-", "").replace(" ", "").replace("\n", "").replace("\r", "")
    
    if not seq_clean:
        return False, "Sequence is empty after cleaning"
    
    # Check for non-standard characters
    invalid_chars = set(seq_clean) - STANDARD_AA
    if invalid_chars:
        return False, f"Contains invalid amino acids: {invalid_chars}"
    
    # Length checks (rough bounds to catch constant region contamination)
    min_len = 80 if chain_type == "VH" else 70
    max_len = 150 if chain_type == "VH" else 130
    
    if len(seq_clean) < min_len:
        return False, f"Too short ({len(seq_clean)} aa), likely incomplete variable domain"
    
    if len(seq_clean) > max_len:
        return False, f"Too long ({len(seq_clean)} aa), likely contains constant region"
    
    return True, None


def extract_fr1_fr3_from_numbering(numbering_rows: List[Dict[str, Any]]) -> Optional[str]:
    """Extract FR1-FR3 concatenated sequence from ANARCII numbering results."""
    try:
        regions = split_regions(numbering_rows)
        fr1 = regions.get("FR1", "")
        fr2 = regions.get("FR2", "")
        fr3 = regions.get("FR3", "")
        return fr1 + fr2 + fr3
    except Exception:
        return None


def calculate_sequence_identity(seq1: str, seq2: str) -> float:
    """Calculate sequence identity between two sequences."""
    if not seq1 or not seq2:
        return 0.0
    
    L = min(len(seq1), len(seq2))
    if L == 0:
        return 0.0
    
    same = sum(1 for i in range(L) if seq1[i] == seq2[i])
    return same / L


def match_to_germline(
    therapeutic_fr: str,
    germline_fr_map: Dict[str, str],
) -> Tuple[Optional[str], float]:
    """
    Match therapeutic FR sequence to best-matching IMGT germline.
    
    Returns:
        (best_match_germline_id, identity_score)
    """
    if not therapeutic_fr:
        return None, 0.0
    
    best_match = None
    best_identity = 0.0
    
    for germline_id, germline_fr in germline_fr_map.items():
        if not germline_fr or germline_fr == "TODO":
            continue
        
        identity = calculate_sequence_identity(therapeutic_fr, germline_fr)
        if identity > best_identity:
            best_identity = identity
            best_match = germline_id
    
    return best_match, best_identity


def load_framework_library(yaml_path: Path) -> Dict[str, str]:
    """
    Load framework library YAML and build germline FR map.
    
    Returns:
        {germline_id: fr1_fr3_sequence}
    """
    germline_fr_map = {}
    
    if not yaml_path.exists():
        return germline_fr_map
    
    with open(yaml_path, "r", encoding="utf-8") as f:
        data = yaml.safe_load(f)
        if data and "frameworks" in data:
            for fw in data["frameworks"]:
                germline_id = fw.get("germline")
                fr_seq = fw.get("fr_sequence_fr1_fr3")
                
                if germline_id and fr_seq and fr_seq != "TODO":
                    germline_fr_map[germline_id] = fr_seq
    
    return germline_fr_map


def extract_sequences_from_entry(entry: Dict[str, Any]) -> Tuple[Optional[str], Optional[str], Optional[str]]:
    """
    Extract VH/VL sequences and INN name from Thera-SAbDab entry.
    
    Returns:
        (vh_seq, vl_seq, inn_name)
    """
    # Try multiple column name variations (Thera-SAbDab uses HeavySequence/LightSequence)
    vh_cols = ["HeavySequence", "VH", "Heavy", "Heavy sequence", "VH sequence", "VH_sequence", "Heavy_V_Sequence", "Heavy_Sequence"]
    vl_cols = ["LightSequence", "VL", "Light", "Light sequence", "VL sequence", "VL_sequence", "Light_V_Sequence", "Light_Sequence"]
    name_cols = ["Therapeutic", "Name", "INN", "Antibody_Name", "Therapeutic_Name"]
    
    vh_seq = None
    vl_seq = None
    inn_name = None
    
    for col in vh_cols:
        if col in entry and pd.notna(entry[col]):
            vh_seq = str(entry[col]).strip()
            break
    
    for col in vl_cols:
        if col in entry and pd.notna(entry[col]):
            vl_seq = str(entry[col]).strip()
            break
    
    for col in name_cols:
        if col in entry and pd.notna(entry[col]):
            inn_name = str(entry[col]).strip()
            break
    
    # Clean sequences (remove gaps, keep only standard AA)
    if vh_seq:
        vh_seq = "".join(c for c in vh_seq.upper() if c in STANDARD_AA or c == "-")
        if len(vh_seq.replace("-", "")) < 50:
            vh_seq = None
    
    if vl_seq:
        vl_seq = "".join(c for c in vl_seq.upper() if c in STANDARD_AA or c == "-")
        if len(vl_seq.replace("-", "")) < 40:
            vl_seq = None
    
    return vh_seq, vl_seq, inn_name


def get_sequence_hash(seq: str) -> Optional[str]:
    """Get SHA256 hash of stripped sequence for deduplication."""
    if not seq or not isinstance(seq, str):
        return None
    seq_clean = seq.strip().upper().replace("-", "").replace(" ", "")
    if not seq_clean:
        return None
    return hashlib.sha256(seq_clean.encode('utf-8')).hexdigest()


def infer_modality_from_format(format_raw: str) -> str:
    """
    Infer modality from Format field.
    
    Returns:
        modality ∈ {standard, ADC, fusion, radiolabeled, other}
    """
    if not format_raw or pd.isna(format_raw):
        return "other"
    
    format_upper = str(format_raw).strip().upper()
    
    # Check in order of specificity
    if "ADC" in format_upper or "ANTIBODY-DRUG CONJUGATE" in format_upper:
        return "ADC"
    
    if "FUSION" in format_upper or "IMMUNOFUSION" in format_upper:
        return "fusion"
    
    if "RADIOLABELED" in format_upper or "RADIO" in format_upper:
        return "radiolabeled"
    
    # Standard: Whole mAb, Fab, IgG (and not containing the above keywords)
    if any(keyword in format_upper for keyword in ["WHOLE MAB", "FAB", "IGG"]):
        # Make sure it's not one of the engineered types
        if "ADC" not in format_upper and "FUSION" not in format_upper and "RADIO" not in format_upper:
            return "standard"
    
    # Default to other
    return "other"


def classify_phase(entry: Dict[str, Any]) -> str:
    """
    Classify clinical phase from entry.
    
    Looks for columns: Phase, Status, Clinical stage, Highest_Clin_Trial
    
    Returns:
        - "Phase_II_plus": Phase II, Phase III, Phase I/II, Phase II/III, Approved
        - "Phase_I": Phase I
        - "Preclinical": Preclinical, TBC (To Be Confirmed), or other early stage
        - "Unknown": Missing or unrecognized
    """
    # Try multiple column names (including variations with special characters)
    phase_cols = [
        "Phase",
        "Status",
        "Clinical stage",
        "Highest_Clin_Trial (Feb '25)",
        "Highest_Clin_Trial",
        "Clinical_Stage",
        "ClinicalStage",
    ]
    
    phase_value = None
    # First, try exact match
    for col in phase_cols:
        if col in entry:
            val = entry[col]
            if pd.notna(val) and str(val).strip():
                phase_value = str(val).strip()
                break
    
    # If not found, try fuzzy matching on all entry keys
    if not phase_value:
        for key in entry.keys():
            key_lower = key.lower()
            # Check if key contains "phase", "trial", "clinical", or "status"
            if any(term in key_lower for term in ["phase", "trial", "clinical", "status", "stage"]):
                val = entry[key]
                if pd.notna(val) and str(val).strip():
                    phase_value = str(val).strip()
                    break
    
    if not phase_value:
        return "Unknown"
    
    phase_upper = phase_value.upper()
    
    # Phase ≥ II: Phase II, Phase III, Phase I/II, Phase II/III, Approved
    if any(keyword in phase_upper for keyword in [
        "PHASE-II", "PHASE II", "PHASE_II", "PHASE2",
        "PHASE-III", "PHASE III", "PHASE_III", "PHASE3",
        "PHASE-I/II", "PHASE I/II", "PHASE_I/II", "PHASE1/2",
        "PHASE-II/III", "PHASE II/III", "PHASE_II/III", "PHASE2/3",
        "APPROVED", "MARKETED", "LAUNCHED",
    ]):
        return "Phase_II_plus"
    
    # Phase I (must be standalone, not Phase I/II)
    if "PHASE-I" in phase_upper or phase_upper == "PHASE I" or phase_upper == "PHASE_I" or phase_upper == "PHASE1":
        # Make sure it's not Phase I/II
        if "PHASE-I/II" not in phase_upper and "PHASE I/II" not in phase_upper:
            return "Phase_I"
    
    # Preclinical: Preclinical, TBC, or other early stage indicators
    if any(keyword in phase_upper for keyword in [
        "PRECLINICAL", "PRE-CLINICAL", "PRECLINIC",
        "TBC", "TO BE CONFIRMED",
        "IND", "INVESTIGATIONAL",
        "DISCOVERY", "RESEARCH",
    ]):
        return "Preclinical"
    
    # Unknown for unrecognized values
    return "Unknown"


def detect_format(vh_seq: Optional[str], vl_seq: Optional[str]) -> Tuple[str, str]:
    """
    Detect antibody format based on chain completeness and sequence patterns.
    
    Returns:
        (chain_completeness, format_type)
    
    Chain completeness:
        - "VH_VL": Both VH and VL present
        - "VH_ONLY": Only VH present (VHH/sdAb)
        - "VL_ONLY": Only VL present (abnormal, usually discarded)
    
    Format type:
        - "monospecific_IgG_Fab": 1 VH + 1 VL (standard IgG/Fab)
        - "scFv": VH-linker-VL (single chain, contains linker pattern)
        - "VHH": Single heavy chain only
        - "engineered_multi_domain": Complex engineered format (marked, not analyzed)
        - "VL_ONLY": Only light chain (abnormal)
    """
    # Chain completeness
    if vh_seq and vl_seq:
        chain_completeness = "VH_VL"
    elif vh_seq and not vl_seq:
        chain_completeness = "VH_ONLY"
    elif not vh_seq and vl_seq:
        chain_completeness = "VL_ONLY"
    else:
        chain_completeness = "NONE"
        return chain_completeness, "UNKNOWN"
    
    # Format detection
    if chain_completeness == "VL_ONLY":
        return chain_completeness, "VL_ONLY"
    
    if chain_completeness == "VH_ONLY":
        # Check if it's a VHH or potentially scFv with linker
        vh_clean = vh_seq.strip().upper().replace("-", "").replace(" ", "")
        
        # Check for linker patterns (common scFv linkers: GGGGS, (GGGGS)n, etc.)
        linker_patterns = [
            "GGGGS",  # Common linker
            "GGGGSGGGGS",  # Double linker
            "GGGGSGGGGSGGGGS",  # Triple linker
            "GGGGGS",  # Variant
            "GGGGGSGGGGGS",  # Double variant
        ]
        
        has_linker = any(pattern in vh_clean for pattern in linker_patterns)
        
        # Check length (scFv typically 250-300 aa, VHH typically 110-140 aa)
        if len(vh_clean) > 200 or has_linker:
            return chain_completeness, "engineered_multi_domain"
        else:
            return chain_completeness, "VHH"
    
    if chain_completeness == "VH_VL":
        # Both chains present - check if they're separate or fused
        vh_clean = vh_seq.strip().upper().replace("-", "").replace(" ", "")
        vl_clean = vl_seq.strip().upper().replace("-", "").replace(" ", "")
        
        # Check if either sequence contains linker patterns (suggesting scFv)
        linker_patterns = [
            "GGGGS",
            "GGGGSGGGGS",
            "GGGGSGGGGSGGGGS",
            "GGGGGS",
            "GGGGGSGGGGGS",
        ]
        
        vh_has_linker = any(pattern in vh_clean for pattern in linker_patterns)
        vl_has_linker = any(pattern in vl_clean for pattern in linker_patterns)
        
        # Check for unusually long sequences (suggesting multi-domain)
        vh_len = len(vh_clean)
        vl_len = len(vl_clean)
        
        # Normal VH: 110-140 aa, Normal VL: 100-115 aa
        # If either is >200 aa, likely multi-domain
        if vh_len > 200 or vl_len > 200:
            return chain_completeness, "engineered_multi_domain"
        
        # If linker found in either chain, likely scFv format
        if vh_has_linker or vl_has_linker:
            return chain_completeness, "scFv"
        
        # Default: standard monospecific IgG/Fab
        return chain_completeness, "monospecific_IgG_Fab"


def process_therapeutic_entry_qc_only(entry: Dict[str, Any]) -> Dict[str, Any]:
    """
    Process a single therapeutic antibody entry in QC-only mode.
    
    Only performs:
    - Sequence extraction
    - QC validation (na/illegal chars/length)
    - SHA256 hashing for deduplication
    
    Does NOT call ANARCII or perform germline matching.
    
    Returns:
        Result dict with QC flags, sequences, and hashes
    """
    # Extract sequences and name first
    vh_seq, vl_seq, inn_name = extract_sequences_from_entry(entry)
    
    # Get name from various possible columns
    name = (inn_name or 
            entry.get("Therapeutic", "") or 
            entry.get("Name", "") or 
            entry.get("INN", ""))
    
    result = {
        "Name": name or "",
        "INN": inn_name or name or "",
        "VH": vh_seq,
        "VL": vl_seq,
        "heavy_hash": None,
        "light_hash": None,
        "qc_flags": [],
        "qc_pass": False,
        "fail_reason": None,
    }
    
    # Check for missing sequences
    if not vh_seq and not vl_seq:
        result["qc_flags"].append("MISSING_BOTH_CHAINS")
        result["fail_reason"] = "MISSING_BOTH_CHAINS"
        return result
    
    # Check for NA values
    if vh_seq:
        vh_clean = str(vh_seq).strip().upper()
        if not vh_clean or vh_clean in ['', 'NA', 'N/A', 'NULL', 'NONE', 'NAN']:
            result["qc_flags"].append("VH_NA")
            vh_seq = None
            result["VH"] = None
    
    if vl_seq:
        vl_clean = str(vl_seq).strip().upper()
        if not vl_clean or vl_clean in ['', 'NA', 'N/A', 'NULL', 'NONE', 'NAN']:
            result["qc_flags"].append("VL_NA")
            vl_seq = None
            result["VL"] = None
    
    # QC: Validate VH
    if vh_seq:
        is_valid, error = validate_sequence(vh_seq, "VH")
        if not is_valid:
            result["qc_flags"].append(f"VH_INVALID: {error}")
            vh_seq = None
            result["VH"] = None
        else:
            # Generate hash for valid sequence
            result["heavy_hash"] = get_sequence_hash(vh_seq)
    
    # QC: Validate VL
    if vl_seq:
        is_valid, error = validate_sequence(vl_seq, "VL")
        if not is_valid:
            result["qc_flags"].append(f"VL_INVALID: {error}")
            vl_seq = None
            result["VL"] = None
        else:
            # Generate hash for valid sequence
            result["light_hash"] = get_sequence_hash(vl_seq)
    
    # Determine QC pass/fail
    if not vh_seq and not vl_seq:
        result["qc_flags"].append("BOTH_CHAINS_FAILED_QC")
        result["fail_reason"] = "; ".join(result["qc_flags"])
        return result
    
    # QC pass if at least one chain is valid
    result["qc_pass"] = (result["heavy_hash"] is not None) or (result["light_hash"] is not None)
    
    if not result["qc_pass"]:
        result["fail_reason"] = "; ".join(result["qc_flags"])
        return result
    
    # Structure completeness and format classification
    # Use the validated sequences (after QC)
    validated_vh = result.get("VH") if result.get("heavy_hash") else None
    validated_vl = result.get("VL") if result.get("light_hash") else None
    
    chain_completeness, format_type = detect_format(validated_vh, validated_vl)
    result["chain_completeness"] = chain_completeness
    result["format_type"] = format_type
    
    # Infer modality from Format field
    format_raw = entry.get("Format", "") or ""
    result["modality"] = infer_modality_from_format(format_raw)
    result["format_raw"] = format_raw  # Keep original for reference
    
    return result


def process_therapeutic_entry(
    entry: Dict[str, Any],
    germline_fr_map_vh: Dict[str, str],
    germline_fr_map_vl: Dict[str, str],
) -> Dict[str, Any]:
    """
    Process a single therapeutic antibody entry.
    
    Returns:
        Result dict with QC flags, germline assignments, and metadata
    """
    # Extract sequences and name first
    vh_seq, vl_seq, inn_name = extract_sequences_from_entry(entry)
    
    # Get name from various possible columns
    name = (inn_name or 
            entry.get("Therapeutic", "") or 
            entry.get("Name", "") or 
            entry.get("INN", ""))
    
    result = {
        "Name": name,
        "INN": inn_name or name,
        "VH": None,
        "VL": None,
        "vh_germline": None,
        "vl_germline": None,
        "vh_identity": 0.0,
        "vl_identity": 0.0,
        "qc_flags": [],
        "qc_pass": False,
    }
    result["VH"] = vh_seq
    result["VL"] = vl_seq
    
    if not vh_seq and not vl_seq:
        result["qc_flags"].append("MISSING_BOTH_CHAINS")
        return result
    
    # QC: Validate VH
    if vh_seq:
        is_valid, error = validate_sequence(vh_seq, "VH")
        if not is_valid:
            result["qc_flags"].append(f"VH_INVALID: {error}")
            vh_seq = None
            result["VH"] = None
    
    # QC: Validate VL
    if vl_seq:
        is_valid, error = validate_sequence(vl_seq, "VL")
        if not is_valid:
            result["qc_flags"].append(f"VL_INVALID: {error}")
            vl_seq = None
            result["VL"] = None
    
    if not vh_seq and not vl_seq:
        result["qc_flags"].append("BOTH_CHAINS_FAILED_QC")
        return result
    
    # Process VH with ANARCII
    if vh_seq:
        try:
            numbering_rows = imgt_number_anarcii(vh_seq)
            fr1_fr3 = extract_fr1_fr3_from_numbering(numbering_rows)
            
            if fr1_fr3:
                germline_match, identity = match_to_germline(fr1_fr3, germline_fr_map_vh)
                result["vh_germline"] = germline_match
                result["vh_identity"] = identity
                if not germline_match:
                    result["qc_flags"].append("VH_NO_GERMLINE_MATCH")
            else:
                result["qc_flags"].append("VH_FR_EXTRACTION_FAILED")
        except IMGTNumberingError as e:
            result["qc_flags"].append(f"VH_NUMBERING_FAILED: {str(e)}")
        except Exception as e:
            result["qc_flags"].append(f"VH_PROCESSING_ERROR: {str(e)}")
    
    # Process VL with ANARCII
    if vl_seq:
        try:
            numbering_rows = imgt_number_anarcii(vl_seq)
            fr1_fr3 = extract_fr1_fr3_from_numbering(numbering_rows)
            
            if fr1_fr3:
                germline_match, identity = match_to_germline(fr1_fr3, germline_fr_map_vl)
                result["vl_germline"] = germline_match
                result["vl_identity"] = identity
                if not germline_match:
                    result["qc_flags"].append("VL_NO_GERMLINE_MATCH")
            else:
                result["qc_flags"].append("VL_FR_EXTRACTION_FAILED")
        except IMGTNumberingError as e:
            result["qc_flags"].append(f"VL_NUMBERING_FAILED: {str(e)}")
        except Exception as e:
            result["qc_flags"].append(f"VL_PROCESSING_ERROR: {str(e)}")
    
    # QC pass if at least one chain has valid germline match
    result["qc_pass"] = (result["vh_germline"] is not None) or (result["vl_germline"] is not None)
    
    return result


def select_representatives(
    qc_results: List[Dict[str, Any]],
    vh_germlines: List[str],
    vl_germlines: List[str],
) -> Dict[str, Any]:
    """
    Select 3-5 representative therapeutics per germline.
    
    Priority:
    1. Cover different canonical classes (if available)
    2. Cover different CDR1/2 lengths
    3. High identity scores
    """
    representatives = {
        "vh": {},
        "vl": {},
    }
    
    # Group by germline
    vh_by_germline = defaultdict(list)
    vl_by_germline = defaultdict(list)
    
    for result in qc_results:
        if not result["qc_pass"]:
            continue
        
        if result["vh_germline"]:
            vh_by_germline[result["vh_germline"]].append(result)
        
        if result["vl_germline"]:
            vl_by_germline[result["vl_germline"]].append(result)
    
    # Select representatives for VH
    for germline in vh_germlines:
        candidates = vh_by_germline.get(germline, [])
        if not candidates:
            continue
        
        # Sort by identity (descending)
        candidates_sorted = sorted(candidates, key=lambda x: x["vh_identity"], reverse=True)
        
        # Select top 3-5
        selected = candidates_sorted[:5]
        representatives["vh"][germline] = [
            {
                "INN": r["INN"],
                "Name": r["Name"],
                "identity": r["vh_identity"],
            }
            for r in selected
        ]
    
    # Select representatives for VL
    for germline in vl_germlines:
        candidates = vl_by_germline.get(germline, [])
        if not candidates:
            continue
        
        # Sort by identity (descending)
        candidates_sorted = sorted(candidates, key=lambda x: x["vl_identity"], reverse=True)
        
        # Select top 3-5
        selected = candidates_sorted[:5]
        representatives["vl"][germline] = [
            {
                "INN": r["INN"],
                "Name": r["Name"],
                "identity": r["vl_identity"],
            }
            for r in selected
        ]
    
    return representatives


def main():
    import argparse
    
    parser = argparse.ArgumentParser(description="Prepare Thera-SAbDab dataset: QC + germline mapping")
    parser.add_argument("--in_xlsx", help="Input Thera-SAbDab export XLSX file")
    parser.add_argument("--out_dir", help="Output directory for QC pass and mapping files")
    parser.add_argument("--vh_yaml", help="VH framework library YAML (default: core/data/framework_library/vh_frameworks.with_cdr12.canonical_input.yaml)")
    parser.add_argument("--vl_yaml", help="VL framework library YAML (default: core/data/framework_library/vl_frameworks.with_cdr12.canonical_input.yaml)")
    parser.add_argument("--limit", type=int, help="Limit processing to first N therapeutics (for testing)")
    parser.add_argument("--mode", choices=["full", "qc_only"], default="full",
                        help="Processing mode: 'full' (QC + ANARCII + germline) or 'qc_only' (QC + deduplication only)")
    
    args = parser.parse_args()
    
    # Set paths
    if args.in_xlsx:
        thera_export = Path(args.in_xlsx)
    else:
        thera_export = PROJECT_ROOT / "data" / "thera_sabdab" / "thera_export.xlsx"
    
    if args.vh_yaml:
        vh_yaml = Path(args.vh_yaml)
    else:
        vh_yaml = PROJECT_ROOT / "core" / "data" / "framework_library" / "vh_frameworks.with_cdr12.canonical_input.yaml"
    
    if args.vl_yaml:
        vl_yaml = Path(args.vl_yaml)
    else:
        vl_yaml = PROJECT_ROOT / "core" / "data" / "framework_library" / "vl_frameworks.with_cdr12.canonical_input.yaml"
    
    if args.out_dir:
        out_dir = Path(args.out_dir)
    else:
        out_dir = PROJECT_ROOT / "data" / "thera_sabdab"
    
    out_dir.mkdir(parents=True, exist_ok=True)
    
    # 1. Load and validate input
    if not thera_export.exists():
        raise RuntimeError(f"CRITICAL: Thera-SAbDab export not found: {thera_export}")
    
    print(f"📖 Loading Thera-SAbDab export: {thera_export}")
    df = pd.read_excel(thera_export, engine='openpyxl')
    
    # P0: Fail-fast if still test data
    if len(df) <= 100:
        raise RuntimeError(
            f"CRITICAL: Thera-SAbDab export has only {len(df)} rows. "
            f"This appears to be test data or incomplete export. "
            f"Please download the full spreadsheet from Thera-SAbDab website."
        )
    
    print(f"✅ Loaded {len(df)} therapeutics")
    
    # Apply limit if specified (for testing)
    if args.limit and args.limit > 0:
        df = df.head(args.limit)
        print(f"⚠️  Limited to first {len(df)} therapeutics (--limit={args.limit})")
    
    # Mode-specific processing
    if args.mode == "qc_only":
        # QC-only mode: no ANARCII, no germline matching
        print("\n🔬 Processing therapeutics (QC-only mode, no ANARCII)...")
        qc_results = []
        
        for idx, row in df.iterrows():
            if (idx + 1) % 100 == 0:
                print(f"  Processed {idx + 1}/{len(df)}... (QC pass so far: {sum(1 for r in qc_results if r['qc_pass'])})")
            
            result = process_therapeutic_entry_qc_only(row.to_dict())
            # Add phase classification
            result["phase"] = classify_phase(row.to_dict())
            qc_results.append(result)
        
        # Filter QC pass/fail
        qc_pass = [r for r in qc_results if r["qc_pass"]]
        qc_fail = [r for r in qc_results if not r["qc_pass"]]
        
        n_total = len(qc_results)
        n_pass = len(qc_pass)
        n_fail = len(qc_fail)
        
        # Collect unique hashes
        heavy_hashes = set()
        light_hashes = set()
        for r in qc_pass:
            if r.get("heavy_hash"):
                heavy_hashes.add(r["heavy_hash"])
            if r.get("light_hash"):
                light_hashes.add(r["light_hash"])
        
        unique_heavy = len(heavy_hashes)
        unique_light = len(light_hashes)
        
        # Collect format classification statistics
        chain_completeness_counts = defaultdict(int)
        format_type_counts = defaultdict(int)
        phase_counts = defaultdict(int)
        modality_counts = defaultdict(int)
        
        for r in qc_pass:
            chain_comp = r.get("chain_completeness", "UNKNOWN")
            format_type = r.get("format_type", "UNKNOWN")
            phase = r.get("phase", "Unknown")
            modality = r.get("modality", "other")
            chain_completeness_counts[chain_comp] += 1
            format_type_counts[format_type] += 1
            phase_counts[phase] += 1
            modality_counts[modality] += 1
        
        # Print statistics
        print("\n" + "=" * 60)
        print("📊 QC-Only Mode Statistics")
        print("=" * 60)
        print(f"N_total: {n_total}")
        print(f"N_pass: {n_pass}")
        print(f"N_fail: {n_fail}")
        print(f"unique_heavy: {unique_heavy} ⭐")
        print(f"unique_light: {unique_light} ⭐")
        print("\n📋 Chain Completeness:")
        for chain_type, count in sorted(chain_completeness_counts.items()):
            print(f"   {chain_type}: {count}")
        print("\n📋 Format Type:")
        for format_type, count in sorted(format_type_counts.items()):
            print(f"   {format_type}: {count}")
        print("\n📋 Phase Classification:")
        phase_order = ["Phase_II_plus", "Phase_I", "Preclinical", "Unknown"]
        for phase in phase_order:
            if phase in phase_counts:
                print(f"   {phase}: {phase_counts[phase]}")
        # Also show any unexpected phases
        for phase, count in sorted(phase_counts.items()):
            if phase not in phase_order:
                print(f"   {phase}: {count}")
        print("\n📋 Modality:")
        modality_order = ["standard", "ADC", "fusion", "radiolabeled", "other"]
        for modality in modality_order:
            if modality in modality_counts:
                print(f"   {modality}: {modality_counts[modality]}")
        # Also show any unexpected modalities
        for modality, count in sorted(modality_counts.items()):
            if modality not in modality_order:
                print(f"   {modality}: {count}")
        print("=" * 60)
        
        # Validation gate: unique_heavy + unique_light must be significantly less than 2×N_total
        original_total_sequences = 2 * n_total
        unique_total = unique_heavy + unique_light
        deduplication_ratio = unique_total / original_total_sequences if original_total_sequences > 0 else 0
        
        print(f"\n🔍 Deduplication Analysis:")
        print(f"   Original total sequences (2×N_total): {original_total_sequences}")
        print(f"   Unique sequences (heavy + light): {unique_total}")
        print(f"   Deduplication ratio: {deduplication_ratio:.2%}")
        
        if deduplication_ratio >= 0.95:
            print(f"\n⚠️  WARNING: Deduplication ratio ({deduplication_ratio:.2%}) is very high.")
            print(f"   Expected significant reduction due to duplicate sequences.")
            print(f"   Possible reasons:")
            print(f"   - Data already deduplicated")
            print(f"   - Very diverse dataset")
            print(f"   - QC filtering removed most duplicates")
        else:
            print(f"\n✅ Deduplication validation passed: {deduplication_ratio:.2%} < 95%")
        
        # Output files
        # 1. qc_only_pass.xlsx
        if qc_pass:
            pass_df = pd.DataFrame([
                {
                    "Name": r.get("Name", ""),
                    "INN": r.get("INN", ""),
                    "VH": r.get("VH", ""),
                    "VL": r.get("VL", ""),
                    "heavy_hash": r.get("heavy_hash", ""),
                    "light_hash": r.get("light_hash", ""),
                    "chain_completeness": r.get("chain_completeness", ""),
                    "format_type": r.get("format_type", ""),
                    "modality": r.get("modality", "other"),
                    "format_raw": r.get("format_raw", ""),
                }
                for r in qc_pass
            ])
            pass_path = out_dir / "qc_only_pass.xlsx"
            pass_df.to_excel(pass_path, index=False, engine='openpyxl')
            print(f"\n💾 QC pass saved: {pass_path} ({len(pass_df)} rows)")
        else:
            print(f"\n⚠️  No QC pass entries to save")
        
        # 2. qc_only_fail.csv (always create, even if empty)
        fail_path = out_dir / "qc_only_fail.csv"
        if qc_fail:
            fail_df = pd.DataFrame([
                {
                    "Name": r.get("Name", ""),
                    "INN": r.get("INN", ""),
                    "VH": r.get("VH", ""),
                    "VL": r.get("VL", ""),
                    "fail_reason": r.get("fail_reason", "; ".join(r.get("qc_flags", []))),
                }
                for r in qc_fail
            ])
            fail_df.to_csv(fail_path, index=False, encoding='utf-8')
            print(f"💾 QC fail saved: {fail_path} ({len(fail_df)} rows)")
        else:
            # Create empty CSV with headers
            empty_fail_df = pd.DataFrame(columns=["Name", "INN", "VH", "VL", "fail_reason"])
            empty_fail_df.to_csv(fail_path, index=False, encoding='utf-8')
            print(f"💾 QC fail saved: {fail_path} (0 rows, empty file created)")
        
        # 3. qc_only_hash_index.csv
        hash_index_rows = []
        for r in qc_pass:
            hash_index_rows.append({
                "INN": r.get("INN", ""),
                "Name": r.get("Name", ""),
                "heavy_hash": r.get("heavy_hash", ""),
                "light_hash": r.get("light_hash", ""),
                "chain_completeness": r.get("chain_completeness", ""),
                "format_type": r.get("format_type", ""),
                "modality": r.get("modality", "other"),
            })
        
        if hash_index_rows:
            hash_index_df = pd.DataFrame(hash_index_rows)
            hash_index_path = out_dir / "qc_only_hash_index.csv"
            hash_index_df.to_csv(hash_index_path, index=False, encoding='utf-8')
            print(f"💾 Hash index saved: {hash_index_path} ({len(hash_index_df)} rows)")
        
        print(f"\n✅ QC-only mode completed")
        return
    
    # Full mode: QC + ANARCII + germline matching
    # 2. Load framework library germlines
    print("📖 Loading framework library germlines...")
    germline_fr_map_vh = load_framework_library(vh_yaml)
    germline_fr_map_vl = load_framework_library(vl_yaml)
    print(f"✅ Loaded {len(germline_fr_map_vh)} VH germlines, {len(germline_fr_map_vl)} VL germlines")
    
    # 3. Process each therapeutic
    print("\n🔬 Processing therapeutics (QC + germline matching)...")
    print("   This may take a while (ANARCII numbering for each sequence)...")
    qc_results = []
    
    for idx, row in df.iterrows():
        if (idx + 1) % 50 == 0:
            print(f"  Processed {idx + 1}/{len(df)}... (QC pass so far: {sum(1 for r in qc_results if r['qc_pass'])})")
        
        result = process_therapeutic_entry(row.to_dict(), germline_fr_map_vh, germline_fr_map_vl)
        qc_results.append(result)
    
    # 4. Filter QC pass
    qc_pass = [r for r in qc_results if r["qc_pass"]]
    print(f"\n✅ QC pass: {len(qc_pass)}/{len(qc_results)} therapeutics")
    
    if len(qc_pass) == 0:
        # Diagnostic: analyze failure reasons
        failure_reasons = defaultdict(int)
        vh_seq_count = 0
        vl_seq_count = 0
        vh_numbering_success = 0
        vl_numbering_success = 0
        vh_germline_match = 0
        vl_germline_match = 0
        
        for r in qc_results:
            for flag in r.get("qc_flags", []):
                failure_reasons[flag] += 1
            if r.get("VH"):
                vh_seq_count += 1
            if r.get("VL"):
                vl_seq_count += 1
            if r.get("vh_germline"):
                vh_germline_match += 1
            if r.get("vl_germline"):
                vl_germline_match += 1
            if "VH_NUMBERING_FAILED" not in str(r.get("qc_flags", [])) and r.get("VH"):
                vh_numbering_success += 1
            if "VL_NUMBERING_FAILED" not in str(r.get("qc_flags", [])) and r.get("VL"):
                vl_numbering_success += 1
        
        print("\n" + "="*60)
        print("🔍 Diagnostic Information")
        print("="*60)
        print(f"VH sequences found: {vh_seq_count}/{len(qc_results)}")
        print(f"VL sequences found: {vl_seq_count}/{len(qc_results)}")
        print(f"VH numbering success: {vh_numbering_success}")
        print(f"VL numbering success: {vl_numbering_success}")
        print(f"VH germline matches: {vh_germline_match}")
        print(f"VL germline matches: {vl_germline_match}")
        print(f"\nTop 10 failure reasons:")
        for reason, count in sorted(failure_reasons.items(), key=lambda x: x[1], reverse=True)[:10]:
            print(f"  {reason}: {count}")
        
        # Show sample entries for debugging
        print(f"\nSample entries (first 3 with VH/VL):")
        sample_count = 0
        for r in qc_results[:20]:
            if (r.get("VH") or r.get("VL")) and sample_count < 3:
                print(f"  - {r.get('Name', 'N/A')}: VH={bool(r.get('VH'))}, VL={bool(r.get('VL'))}, "
                      f"VH_germline={r.get('vh_germline')}, VL_germline={r.get('vl_germline')}, "
                      f"flags={r.get('qc_flags', [])[:2]}")
                sample_count += 1
        
        raise RuntimeError(
            f"CRITICAL: No therapeutics passed QC. "
            f"Total: {len(qc_results)}, VH sequences: {vh_seq_count}, VL sequences: {vl_seq_count}, "
            f"VH germline matches: {vh_germline_match}, VL germline matches: {vl_germline_match}. "
            f"Check diagnostic output above for failure reasons."
        )
    
    # 5. Build germline mapping statistics
    vh_mapping = defaultdict(int)
    vl_mapping = defaultdict(int)
    
    for result in qc_pass:
        if result["vh_germline"]:
            vh_mapping[result["vh_germline"]] += 1
        if result["vl_germline"]:
            vl_mapping[result["vl_germline"]] += 1
    
    # 6. Get framework library germlines (for representative selection)
    vh_frameworks = yaml.safe_load(vh_yaml.read_text(encoding='utf-8')).get('frameworks', [])
    vl_frameworks = yaml.safe_load(vl_yaml.read_text(encoding='utf-8')).get('frameworks', [])
    
    vh_germlines = [fw.get('germline') for fw in vh_frameworks if fw.get('germline')]
    vl_germlines = [fw.get('germline') for fw in vl_frameworks if fw.get('germline')]
    
    # 7. Select representatives
    print("\n📊 Selecting representatives by germline...")
    representatives = select_representatives(qc_pass, vh_germlines, vl_germlines)
    
    # 8. Save outputs
    print("\n💾 Saving outputs...")
    
    # 8.1 QC pass XLSX
    qc_df = pd.DataFrame(qc_pass)
    qc_df = qc_df[[
        "Name", "INN", "VH", "VL",
        "vh_germline", "vl_germline",
        "vh_identity", "vl_identity",
        "qc_flags", "qc_pass"
    ]]
    qc_output = out_dir / "thera_qc_pass.xlsx"
    qc_df.to_excel(qc_output, index=False, engine='openpyxl')
    print(f"✅ Saved: {qc_output} ({len(qc_df)} rows)")
    
    # 8.2 Germline mapping CSV
    mapping_data = []
    for germline, count in sorted(vh_mapping.items(), key=lambda x: x[1], reverse=True):
        mapping_data.append({"chain": "VH", "germline": germline, "count": count})
    for germline, count in sorted(vl_mapping.items(), key=lambda x: x[1], reverse=True):
        mapping_data.append({"chain": "VL", "germline": germline, "count": count})
    
    mapping_df = pd.DataFrame(mapping_data)
    mapping_output = out_dir / "thera_germline_mapping.csv"
    mapping_df.to_csv(mapping_output, index=False)
    print(f"✅ Saved: {mapping_output} ({len(mapping_df)} germlines)")
    
    # 8.3 Representatives YAML
    reps_output = out_dir / "thera_representatives_by_germline.yaml"
    with open(reps_output, 'w', encoding='utf-8') as f:
        yaml.safe_dump(representatives, f, sort_keys=False, allow_unicode=True, default_flow_style=False)
    print(f"✅ Saved: {reps_output}")
    
    # 9. Summary
    print("\n" + "="*60)
    print("📊 Summary")
    print("="*60)
    print(f"Total therapeutics: {len(df)}")
    print(f"QC pass: {len(qc_pass)} ({len(qc_pass)/len(df)*100:.1f}%)")
    print(f"VH germlines matched: {len(vh_mapping)}")
    print(f"VL germlines matched: {len(vl_mapping)}")
    print(f"\nTop 5 VH germlines:")
    for germline, count in sorted(vh_mapping.items(), key=lambda x: x[1], reverse=True)[:5]:
        print(f"  {germline}: {count} therapeutics")
    print(f"\nTop 5 VL germlines:")
    for germline, count in sorted(vl_mapping.items(), key=lambda x: x[1], reverse=True)[:5]:
        print(f"  {germline}: {count} therapeutics")
    
    print("\n✅ [SUCCESS] Thera dataset preparation complete!")
    print(f"\n📝 Next steps:")
    print(f"  1. Run canonical tool on: {qc_output}")
    print(f"  2. Generate thera_canonical.tsv (4-column contract)")
    print(f"  3. Run compare_canonical_to_thera_sabdab.py")
    
    return 0


if __name__ == "__main__":
    try:
        sys.exit(main())
    except Exception as e:
        print(f"\n❌ FATAL ERROR: {str(e)}")
        sys.exit(1)
