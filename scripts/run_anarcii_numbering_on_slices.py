#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
scripts/run_anarcii_numbering_on_slices.py

Run ANARCII numbering and germline matching on specific slices from Truth Table.

Target slices:
- Slice 1: Standard humanized ()
- Slice 3: VHH design (VHH)
- Slice 4: Bispecific engineering (bsAb)
- Slice 8: ADC engineering (ADC)

Outputs:
- data/thera_sabdab/features/anarcii_numbering_<slice>.parquet
- data/thera_sabdab/features/germline_match_<slice>.parquet

Features:
- Checkpoint/resume support to avoid re-running on timeout
- Failure rate and error statistics per slice
"""

import sys
import json
import argparse
import pandas as pd
import yaml
import re
import numpy as np
from pathlib import Path
from typing import Dict, List, Any, Optional, Set, Tuple
from collections import defaultdict, Counter
from datetime import datetime

PROJECT_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT_ROOT))

# Try to import ANARCII
try:
    from core.numbering.imgt_anarcii import imgt_number_anarcii, IMGTNumberingError
    from core.vhh_humanization import split_regions
    HAS_ANARCII = True
except ImportError as e:
    HAS_ANARCII = False
    print(f"❌ ERROR: ANARCII not available: {e}")
    print("Install with: pip install anarcii")
    sys.exit(1)


def load_slice_ids(slice_ids_file: Path) -> Set[str]:
    """Load antibody IDs from a slice ID file."""
    if not slice_ids_file.exists():
        return set()
    
    ids = set()
    with open(slice_ids_file, 'r', encoding='utf-8') as f:
        for line in f:
            ab_id = line.strip()
            if ab_id:
                ids.add(ab_id)
    return ids


def get_antibody_id_from_row(row: pd.Series) -> str:
    """Extract antibody_id from a Truth Table row."""
    return row.get("Name", "") or row.get("INN", "") or row.get("Therapeutic", "") or ""


def extract_sequences_from_row(row: pd.Series) -> Tuple[Optional[str], Optional[str]]:
    """
    Extract VH/VL sequences from Truth Table row.
    
    Returns:
        (vh_seq, vl_seq)
    """
    vh_cols = ["HeavySequence", "VH", "Heavy", "Heavy sequence", "VH sequence", "VH_sequence", "Heavy_V_Sequence", "Heavy_Sequence"]
    vl_cols = ["LightSequence", "VL", "Light", "Light sequence", "VL sequence", "VL_sequence", "Light_V_Sequence", "Light_Sequence"]
    
    vh_seq = None
    vl_seq = None
    
    for col in vh_cols:
        if col in row and pd.notna(row[col]):
            vh_seq = str(row[col]).strip()
            if vh_seq:
                break
    
    for col in vl_cols:
        if col in row and pd.notna(row[col]):
            vl_seq = str(row[col]).strip()
            if vl_seq:
                break
    
    return vh_seq, vl_seq


def extract_fr1_fr3_from_numbering(numbering_rows: List[Dict[str, Any]]) -> Optional[str]:
    """Extract FR1-FR3 concatenated sequence from ANARCII numbering results."""
    try:
        # Use split_regions imported from core.vhh_humanization
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


def match_to_germline_dual(
    therapeutic_fr: str,
    global_ref: Dict[str, str],
    library_ref: Dict[str, str],
    match_mode: str,
) -> Dict[str, Any]:
    """
    Match therapeutic FR sequence to best-matching germline using dual reference sets.
    
    Args:
        therapeutic_fr: Therapeutic FR1-FR3 sequence
        global_ref: Global reference (IMGT FASTA) {germline_id: fr1_fr3_sequence}
        library_ref: Library reference (YAML framework library) {germline_id: fr1_fr3_sequence}
        match_mode: One of 'library_only', 'global_only', 'global_and_library'
    
    Returns:
        Dict with match results for both references (if applicable)
    """
    result = {
        "global_match": None,
        "global_identity": 0.0,
        "library_match": None,
        "library_identity": 0.0,
    }
    
    if not therapeutic_fr:
        return result
    
    # Match against library reference
    if match_mode in ("library_only", "global_and_library"):
        library_match, library_identity = match_to_germline(therapeutic_fr, library_ref)
        result["library_match"] = library_match
        result["library_identity"] = library_identity
    
    # Match against global reference
    if match_mode in ("global_only", "global_and_library"):
        global_match, global_identity = match_to_germline(therapeutic_fr, global_ref)
        result["global_match"] = global_match
        result["global_identity"] = global_identity
    
    return result


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


def iter_fasta_records(path: Path):
    """Yield (header_without_gt, sequence) from a FASTA file."""
    header: Optional[str] = None
    seq_parts: List[str] = []
    with open(path, "r", encoding="utf-8") as f:
        for raw in f:
            line = raw.strip()
            if not line:
                continue
            if line.startswith(">"):
                if header is not None:
                    yield header, "".join(seq_parts)
                header = line[1:].strip()
                seq_parts = []
            else:
                seq_parts.append(line)
        if header is not None:
            yield header, "".join(seq_parts)


ALLELE_REGEX = re.compile(r"\b(IGHV|IGKV|IGLV)(\d+)-(\d+)\*(\d+)\b", re.IGNORECASE)


def extract_allele_from_header(header: str) -> Optional[str]:
    """Extract allele ID (e.g., IGHV3-23*01) from FASTA header."""
    matches = list(ALLELE_REGEX.finditer(header))
    if matches:
        m = matches[0]
        prefix = m.group(1).upper()
        fam = m.group(2)
        gene = m.group(3)
        allele = m.group(4)
        return f"{prefix}{fam}-{gene}*{allele}"
    return None


def load_imgt_fasta_global_ref(fasta_path: Path) -> Dict[str, str]:
    """
    Load IMGT FASTA file and extract FR1-FR3 sequences for all germlines.
    
    Returns:
        {germline_id: fr1_fr3_sequence}
    """
    global_ref = {}
    
    if not fasta_path.exists():
        print(f"  ⚠️  Warning: IMGT FASTA file not found: {fasta_path}")
        return global_ref
    
    print(f"  📖 Loading IMGT FASTA: {fasta_path.name}")
    
    count = 0
    failed = 0
    
    for header, sequence in iter_fasta_records(fasta_path):
        allele = extract_allele_from_header(header)
        if not allele:
            continue
        
        # Clean sequence
        seq = sequence.strip().upper().replace(" ", "").replace("\n", "").replace("*", "")
        if not seq:
            continue
        
        # Number and extract FR1-3
        try:
            numbering_rows = imgt_number_anarcii(seq)
            # Use the imported split_regions from core.vhh_humanization
            regions = split_regions(numbering_rows)
            fr1 = regions.get("FR1", "")
            fr2 = regions.get("FR2", "")
            fr3 = regions.get("FR3", "")
            
            if fr1 and fr2 and fr3:
                fr1_fr3 = fr1 + fr2 + fr3
                global_ref[allele] = fr1_fr3
                count += 1
            else:
                failed += 1
                if failed <= 3:  # Print first 3 failures for debugging
                    print(f"      ⚠️  Failed to extract FR regions for {allele}: FR1={len(fr1)}, FR2={len(fr2)}, FR3={len(fr3)}")
        except Exception as e:
            failed += 1
            if failed <= 3:  # Print first 3 failures for debugging
                print(f"      ⚠️  Error processing {allele}: {str(e)}")
            continue
    
    print(f"    ✅ Loaded {count} germlines, {failed} failed")
    return global_ref


def load_checkpoint(checkpoint_file: Path) -> Set[str]:
    """Load processed antibody IDs from checkpoint file."""
    if not checkpoint_file.exists():
        return set()
    
    processed = set()
    try:
        with open(checkpoint_file, 'r', encoding='utf-8') as f:
            for line in f:
                ab_id = line.strip()
                if ab_id:
                    processed.add(ab_id)
    except Exception as e:
        print(f"  ⚠️  Warning: Failed to load checkpoint: {e}")
    
    return processed


def save_checkpoint(checkpoint_file: Path, processed_ids: Set[str]):
    """Save processed antibody IDs to checkpoint file."""
    checkpoint_file.parent.mkdir(parents=True, exist_ok=True)
    with open(checkpoint_file, 'w', encoding='utf-8') as f:
        for ab_id in sorted(processed_ids):
            f.write(f"{ab_id}\n")


def process_antibody(
    antibody_id: str,
    row: pd.Series,
    global_ref_vh: Dict[str, str],
    library_ref_vh: Dict[str, str],
    global_ref_vl: Dict[str, str],
    library_ref_vl: Dict[str, str],
    match_mode: str,
) -> Dict[str, Any]:
    """
    Process a single antibody: ANARCII numbering + germline matching.
    
    Returns:
        Result dict with numbering and germline match info
    """
    result = {
        "antibody_id": antibody_id,
        "vh": {
            "sequence": None,
            "numbering_success": False,
            "numbering_rows": None,
            "fr1_fr3": None,
            "germline_match": None,
            "germline_identity": 0.0,
            "global_match": None,
            "global_identity": 0.0,
            "library_match": None,
            "library_identity": 0.0,
            "delta_identity": None,
            "out_of_library_flag": False,
            "error": None,
        },
        "vl": {
            "sequence": None,
            "numbering_success": False,
            "numbering_rows": None,
            "fr1_fr3": None,
            "germline_match": None,
            "germline_identity": 0.0,
            "global_match": None,
            "global_identity": 0.0,
            "library_match": None,
            "library_identity": 0.0,
            "delta_identity": None,
            "out_of_library_flag": False,
            "error": None,
        },
    }
    
    # Extract sequences
    vh_seq, vl_seq = extract_sequences_from_row(row)
    
    # Process VH
    if vh_seq:
        result["vh"]["sequence"] = vh_seq
        try:
            numbering_rows = imgt_number_anarcii(vh_seq)
            result["vh"]["numbering_success"] = True
            result["vh"]["numbering_rows"] = numbering_rows
            
            fr1_fr3 = extract_fr1_fr3_from_numbering(numbering_rows)
            if fr1_fr3:
                result["vh"]["fr1_fr3"] = fr1_fr3
                # Dual matching
                match_result = match_to_germline_dual(fr1_fr3, global_ref_vh, library_ref_vh, match_mode)
                result["vh"]["global_match"] = match_result["global_match"]
                result["vh"]["global_identity"] = match_result["global_identity"]
                result["vh"]["library_match"] = match_result["library_match"]
                result["vh"]["library_identity"] = match_result["library_identity"]
                
                # Calculate delta_identity and out_of_library_flag
                global_id = result["vh"]["global_identity"]
                library_id = result["vh"]["library_identity"]
                global_match = result["vh"]["global_match"]
                library_match = result["vh"]["library_match"]
                
                # Calculate delta_identity: global_identity - library_identity
                if global_match and library_match:
                    result["vh"]["delta_identity"] = global_id - library_id
                elif global_match:
                    result["vh"]["delta_identity"] = global_id
                elif library_match:
                    result["vh"]["delta_identity"] = -library_id
                else:
                    result["vh"]["delta_identity"] = None
                
                # out_of_library_flag: True if global has match but library doesn't, or library identity is very low
                if global_match and (not library_match or library_id < 0.5):
                    result["vh"]["out_of_library_flag"] = True
                else:
                    result["vh"]["out_of_library_flag"] = False
                
                # For backward compatibility, set germline_match based on match_mode
                if match_mode == "library_only":
                    result["vh"]["germline_match"] = match_result["library_match"]
                    result["vh"]["germline_identity"] = match_result["library_identity"]
                elif match_mode == "global_only":
                    result["vh"]["germline_match"] = match_result["global_match"]
                    result["vh"]["germline_identity"] = match_result["global_identity"]
                else:  # global_and_library
                    # Use the better match
                    if match_result["global_identity"] >= match_result["library_identity"]:
                        result["vh"]["germline_match"] = match_result["global_match"]
                        result["vh"]["germline_identity"] = match_result["global_identity"]
                    else:
                        result["vh"]["germline_match"] = match_result["library_match"]
                        result["vh"]["germline_identity"] = match_result["library_identity"]
        except IMGTNumberingError as e:
            result["vh"]["error"] = f"IMGTNumberingError: {str(e)}"
        except Exception as e:
            result["vh"]["error"] = f"Unexpected error: {str(e)}"
    
    # Process VL
    if vl_seq:
        result["vl"]["sequence"] = vl_seq
        try:
            numbering_rows = imgt_number_anarcii(vl_seq)
            result["vl"]["numbering_success"] = True
            result["vl"]["numbering_rows"] = numbering_rows
            
            fr1_fr3 = extract_fr1_fr3_from_numbering(numbering_rows)
            if fr1_fr3:
                result["vl"]["fr1_fr3"] = fr1_fr3
                # Dual matching
                match_result = match_to_germline_dual(fr1_fr3, global_ref_vl, library_ref_vl, match_mode)
                result["vl"]["global_match"] = match_result["global_match"]
                result["vl"]["global_identity"] = match_result["global_identity"]
                result["vl"]["library_match"] = match_result["library_match"]
                result["vl"]["library_identity"] = match_result["library_identity"]
                
                # Calculate delta_identity and out_of_library_flag
                global_id = result["vl"]["global_identity"]
                library_id = result["vl"]["library_identity"]
                global_match = result["vl"]["global_match"]
                library_match = result["vl"]["library_match"]
                
                # Calculate delta_identity: global_identity - library_identity
                if global_match and library_match:
                    result["vl"]["delta_identity"] = global_id - library_id
                elif global_match:
                    result["vl"]["delta_identity"] = global_id
                elif library_match:
                    result["vl"]["delta_identity"] = -library_id
                else:
                    result["vl"]["delta_identity"] = None
                
                # out_of_library_flag: True if global has match but library doesn't, or library identity is very low
                if global_match and (not library_match or library_id < 0.5):
                    result["vl"]["out_of_library_flag"] = True
                else:
                    result["vl"]["out_of_library_flag"] = False
                
                # For backward compatibility, set germline_match based on match_mode
                if match_mode == "library_only":
                    result["vl"]["germline_match"] = match_result["library_match"]
                    result["vl"]["germline_identity"] = match_result["library_identity"]
                elif match_mode == "global_only":
                    result["vl"]["germline_match"] = match_result["global_match"]
                    result["vl"]["germline_identity"] = match_result["global_identity"]
                else:  # global_and_library
                    # Use the better match
                    if match_result["global_identity"] >= match_result["library_identity"]:
                        result["vl"]["germline_match"] = match_result["global_match"]
                        result["vl"]["germline_identity"] = match_result["global_identity"]
                    else:
                        result["vl"]["germline_match"] = match_result["library_match"]
                        result["vl"]["germline_identity"] = match_result["library_identity"]
        except IMGTNumberingError as e:
            result["vl"]["error"] = f"IMGTNumberingError: {str(e)}"
        except Exception as e:
            result["vl"]["error"] = f"Unexpected error: {str(e)}"
    
    return result


def process_slice(
    slice_id: str,
    slice_name: str,
    df: pd.DataFrame,
    slice_ids: Set[str],
    global_ref_vh: Dict[str, str],
    library_ref_vh: Dict[str, str],
    global_ref_vl: Dict[str, str],
    library_ref_vl: Dict[str, str],
    match_mode: str,
    checkpoint_file: Path,
    output_dir: Path,
) -> Dict[str, Any]:
    """
    Process a single slice: run ANARCII on all antibodies in the slice.
    
    Returns:
        Statistics dictionary
    """
    print(f"\n{'=' * 70}")
    print(f"📦 Processing {slice_id}: {slice_name}")
    print(f"{'=' * 70}")
    
    # Filter DataFrame to slice IDs
    df_slice = df[df.apply(lambda row: get_antibody_id_from_row(row) in slice_ids, axis=1)]
    print(f"  📊 Found {len(df_slice)} records in Truth Table matching slice IDs")
    
    # Load checkpoint
    processed_ids = load_checkpoint(checkpoint_file)
    print(f"  📋 Checkpoint: {len(processed_ids)} already processed")
    
    # Load existing results if parquet files exist
    numbering_path = output_dir / f"anarcii_numbering_{slice_id}.parquet"
    germline_path = output_dir / f"germline_match_{slice_id}.parquet"
    
    existing_numbering = []
    existing_germline = []
    existing_ids = set()
    
    if numbering_path.exists() and germline_path.exists():
        try:
            existing_numbering_df = pd.read_parquet(numbering_path)
            existing_germline_df = pd.read_parquet(germline_path)
            existing_numbering = existing_numbering_df.to_dict('records')
            existing_germline = existing_germline_df.to_dict('records')
            existing_ids = set(existing_numbering_df['antibody_id'].tolist())
            print(f"  📋 Loaded {len(existing_ids)} existing results from parquet files")
        except Exception as e:
            print(f"  ⚠️  Warning: Failed to load existing results: {e}")
    
    # Process each antibody
    numbering_results = existing_numbering.copy()
    germline_results = existing_germline.copy()
    error_stats = {
        "vh_numbering_errors": Counter(),
        "vl_numbering_errors": Counter(),
        "vh_germline_failures": 0,
        "vl_germline_failures": 0,
    }
    
    # Count errors from existing results
    for row in existing_numbering:
        if row.get("vh_error"):
            error_stats["vh_numbering_errors"][row["vh_error"]] += 1
        if row.get("vl_error"):
            error_stats["vl_numbering_errors"][row["vl_error"]] += 1
    
    for row in existing_germline:
        if not row.get("vh_germline_match") and row.get("vh_fr1_fr3"):
            error_stats["vh_germline_failures"] += 1
        if not row.get("vl_germline_match") and row.get("vl_fr1_fr3"):
            error_stats["vl_germline_failures"] += 1
    
    total = len(df_slice)
    processed_count = len(existing_ids)
    new_count = 0
    
    for idx, (_, row) in enumerate(df_slice.iterrows(), 1):
        antibody_id = get_antibody_id_from_row(row)
        
        if not antibody_id:
            continue
        
        # Skip if already processed (in checkpoint or existing results)
        if antibody_id in processed_ids:
            processed_count += 1
            continue
        if antibody_id in existing_ids:
            continue
        
        new_count += 1
        print(f"  [{idx}/{total}] Processing {antibody_id}...", end=" ", flush=True)
        
        # Process antibody
        result = process_antibody(
            antibody_id, row,
            global_ref_vh, library_ref_vh,
            global_ref_vl, library_ref_vl,
            match_mode
        )
        
        # Collect numbering data
        numbering_row = {
            "antibody_id": antibody_id,
            "vh_sequence": result["vh"]["sequence"],
            "vh_numbering_success": result["vh"]["numbering_success"],
            "vh_numbering_rows_count": len(result["vh"]["numbering_rows"]) if result["vh"]["numbering_rows"] else 0,
            "vh_error": result["vh"]["error"],
            "vl_sequence": result["vl"]["sequence"],
            "vl_numbering_success": result["vl"]["numbering_success"],
            "vl_numbering_rows_count": len(result["vl"]["numbering_rows"]) if result["vl"]["numbering_rows"] else 0,
            "vl_error": result["vl"]["error"],
        }
        numbering_results.append(numbering_row)
        
        # Collect germline match data
        germline_row = {
            "antibody_id": antibody_id,
            # Legacy fields (for backward compatibility)
            "vh_germline_match": result["vh"]["germline_match"],
            "vh_germline_identity": result["vh"]["germline_identity"],
            "vl_germline_match": result["vl"]["germline_match"],
            "vl_germline_identity": result["vl"]["germline_identity"],
            # New VH fields
            "vh_best_germline_global": result["vh"]["global_match"],
            "vh_identity_global": result["vh"]["global_identity"],
            "vh_best_framework_lib": result["vh"]["library_match"],
            "vh_identity_lib": result["vh"]["library_identity"],
            "vh_delta_identity": result["vh"]["delta_identity"],
            "vh_out_of_library_flag": result["vh"]["out_of_library_flag"],
            # New VL fields
            "vl_best_germline_global": result["vl"]["global_match"],
            "vl_identity_global": result["vl"]["global_identity"],
            "vl_best_framework_lib": result["vl"]["library_match"],
            "vl_identity_lib": result["vl"]["library_identity"],
            "vl_delta_identity": result["vl"]["delta_identity"],
            "vl_out_of_library_flag": result["vl"]["out_of_library_flag"],
            # Additional fields (for reference)
            "vh_global_match": result["vh"]["global_match"],
            "vh_global_identity": result["vh"]["global_identity"],
            "vh_library_match": result["vh"]["library_match"],
            "vh_library_identity": result["vh"]["library_identity"],
            "vh_fr1_fr3": result["vh"]["fr1_fr3"],
            "vl_global_match": result["vl"]["global_match"],
            "vl_global_identity": result["vl"]["global_identity"],
            "vl_library_match": result["vl"]["library_match"],
            "vl_library_identity": result["vl"]["library_identity"],
            "vl_fr1_fr3": result["vl"]["fr1_fr3"],
        }
        germline_results.append(germline_row)
        
        # Track errors
        if result["vh"]["error"]:
            error_stats["vh_numbering_errors"][result["vh"]["error"]] += 1
        if result["vl"]["error"]:
            error_stats["vl_numbering_errors"][result["vl"]["error"]] += 1
        if not result["vh"]["germline_match"] and result["vh"]["numbering_success"]:
            error_stats["vh_germline_failures"] += 1
        if not result["vl"]["germline_match"] and result["vl"]["numbering_success"]:
            error_stats["vl_germline_failures"] += 1
        
        # Update checkpoint
        processed_ids.add(antibody_id)
        if new_count % 10 == 0:  # Save checkpoint every 10 records
            save_checkpoint(checkpoint_file, processed_ids)
        
        # Print status
        vh_status = "✅" if result["vh"]["numbering_success"] else "❌"
        vl_status = "✅" if result["vl"]["numbering_success"] else "❌"
        print(f"VH:{vh_status} VL:{vl_status}")
    
    # Final checkpoint save
    save_checkpoint(checkpoint_file, processed_ids)
    
    # Save results to parquet
    output_dir.mkdir(parents=True, exist_ok=True)
    
    # Initialize DataFrames
    numbering_df = pd.DataFrame()
    germline_df = pd.DataFrame()
    
    if numbering_results:
        numbering_df = pd.DataFrame(numbering_results)
        numbering_df.to_parquet(numbering_path, index=False)
        print(f"\n  💾 Saved numbering results: {numbering_path} ({len(numbering_df)} records)")
    else:
        print(f"\n  ⚠️  No numbering results to save")
    
    if germline_results:
        germline_df = pd.DataFrame(germline_results)
        germline_df.to_parquet(germline_path, index=False)
        print(f"  💾 Saved germline match results: {germline_path} ({len(germline_df)} records)")
        
        # Generate library coverage report
        generate_library_coverage_report(
            germline_df,
            library_ref_vh,
            library_ref_vl,
            slice_id,
            output_dir,
        )
    else:
        print(f"  ⚠️  No germline results to save")
    
    # Calculate statistics
    total_processed = len(processed_ids)
    vh_success = numbering_df["vh_numbering_success"].sum() if len(numbering_df) > 0 else 0
    vl_success = numbering_df["vl_numbering_success"].sum() if len(numbering_df) > 0 else 0
    vh_total = (numbering_df["vh_sequence"].notna()).sum() if len(numbering_df) > 0 else 0
    vl_total = (numbering_df["vl_sequence"].notna()).sum() if len(numbering_df) > 0 else 0
    
    stats = {
        "slice_id": slice_id,
        "slice_name": slice_name,
        "total_records": total_processed,
        "new_processed": new_count,
        "already_processed": processed_count,
        "vh": {
            "total": int(vh_total),
            "success": int(vh_success),
            "fail_rate": float(1.0 - vh_success / vh_total) if vh_total > 0 else 0.0,
            "germline_match_count": int((germline_df["vh_germline_match"].notna()).sum()) if len(germline_df) > 0 else 0,
            "germline_failures": error_stats["vh_germline_failures"],
        },
        "vl": {
            "total": int(vl_total),
            "success": int(vl_success),
            "fail_rate": float(1.0 - vl_success / vl_total) if vl_total > 0 else 0.0,
            "germline_match_count": int((germline_df["vl_germline_match"].notna()).sum()) if len(germline_df) > 0 else 0,
            "germline_failures": error_stats["vl_germline_failures"],
        },
        "error_breakdown": {
            "vh_numbering_errors": dict(error_stats["vh_numbering_errors"]),
            "vl_numbering_errors": dict(error_stats["vl_numbering_errors"]),
        },
    }
    
    return stats


def generate_library_coverage_report(
    germline_df: pd.DataFrame,
    library_ref_vh: Dict[str, str],
    library_ref_vl: Dict[str, str],
    slice_id: str,
    output_dir: Path,
) -> None:
    """
    Generate library coverage report CSV.
    
    Args:
        germline_df: DataFrame with germline match results
        library_ref_vh: VH library reference (germline_id -> sequence)
        library_ref_vl: VL library reference (germline_id -> sequence)
        slice_id: Slice identifier
        output_dir: Output directory
    """
    if len(germline_df) == 0:
        print(f"  ⚠️  No germline data to generate coverage report")
        return
    
    report_data = []
    
    # Basic counts
    vh_total = germline_df["vh_fr1_fr3"].notna().sum()
    vl_total = germline_df["vl_fr1_fr3"].notna().sum()
    
    report_data.append({"metric": "N_total_heavy", "value": int(vh_total)})
    report_data.append({"metric": "N_total_light", "value": int(vl_total)})
    
    # Out of library rates
    vh_out_of_library = germline_df["vh_out_of_library_flag"].sum() if "vh_out_of_library_flag" in germline_df.columns else 0
    vl_out_of_library = germline_df["vl_out_of_library_flag"].sum() if "vl_out_of_library_flag" in germline_df.columns else 0
    
    vh_out_of_library_rate = vh_out_of_library / vh_total if vh_total > 0 else 0.0
    vl_out_of_library_rate = vl_out_of_library / vl_total if vl_total > 0 else 0.0
    
    report_data.append({"metric": "heavy_out_of_library_rate", "value": f"{vh_out_of_library_rate:.4f}"})
    report_data.append({"metric": "light_out_of_library_rate", "value": f"{vl_out_of_library_rate:.4f}"})
    
    # Top 20 global germlines (heavy)
    vh_global_germlines = germline_df[germline_df["vh_best_germline_global"].notna()]["vh_best_germline_global"]
    if len(vh_global_germlines) > 0:
        vh_global_counts = vh_global_germlines.value_counts().head(20)
        top20_vh_global = "; ".join([f"{germline}({count})" for germline, count in vh_global_counts.items()])
        report_data.append({"metric": "top20_global_germlines_heavy", "value": top20_vh_global})
    else:
        report_data.append({"metric": "top20_global_germlines_heavy", "value": ""})
    
    # Top 20 global germlines (light)
    vl_global_germlines = germline_df[germline_df["vl_best_germline_global"].notna()]["vl_best_germline_global"]
    if len(vl_global_germlines) > 0:
        vl_global_counts = vl_global_germlines.value_counts().head(20)
        top20_vl_global = "; ".join([f"{germline}({count})" for germline, count in vl_global_counts.items()])
        report_data.append({"metric": "top20_global_germlines_light", "value": top20_vl_global})
    else:
        report_data.append({"metric": "top20_global_germlines_light", "value": ""})
    
    # Top 20 library matches (heavy)
    vh_library_matches = germline_df[germline_df["vh_best_framework_lib"].notna()]["vh_best_framework_lib"]
    if len(vh_library_matches) > 0:
        vh_library_counts = vh_library_matches.value_counts().head(20)
        top20_vh_library = "; ".join([f"{framework}({count})" for framework, count in vh_library_counts.items()])
        report_data.append({"metric": "top20_library_matches_heavy", "value": top20_vh_library})
    else:
        report_data.append({"metric": "top20_library_matches_heavy", "value": ""})
    
    # Top 20 library matches (light)
    vl_library_matches = germline_df[germline_df["vl_best_framework_lib"].notna()]["vl_best_framework_lib"]
    if len(vl_library_matches) > 0:
        vl_library_counts = vl_library_matches.value_counts().head(20)
        top20_vl_library = "; ".join([f"{framework}({count})" for framework, count in vl_library_counts.items()])
        report_data.append({"metric": "top20_library_matches_light", "value": top20_vl_library})
    else:
        report_data.append({"metric": "top20_library_matches_light", "value": ""})
    
    # Delta identity distribution (heavy)
    vh_delta_identity = germline_df[germline_df["vh_delta_identity"].notna()]["vh_delta_identity"]
    if len(vh_delta_identity) > 0:
        vh_delta_p50 = float(np.percentile(vh_delta_identity, 50))
        vh_delta_p90 = float(np.percentile(vh_delta_identity, 90))
        vh_delta_p99 = float(np.percentile(vh_delta_identity, 99))
        report_data.append({"metric": "delta_identity_distribution_heavy_p50", "value": f"{vh_delta_p50:.4f}"})
        report_data.append({"metric": "delta_identity_distribution_heavy_p90", "value": f"{vh_delta_p90:.4f}"})
        report_data.append({"metric": "delta_identity_distribution_heavy_p99", "value": f"{vh_delta_p99:.4f}"})
    else:
        report_data.append({"metric": "delta_identity_distribution_heavy_p50", "value": ""})
        report_data.append({"metric": "delta_identity_distribution_heavy_p90", "value": ""})
        report_data.append({"metric": "delta_identity_distribution_heavy_p99", "value": ""})
    
    # Delta identity distribution (light)
    vl_delta_identity = germline_df[germline_df["vl_delta_identity"].notna()]["vl_delta_identity"]
    if len(vl_delta_identity) > 0:
        vl_delta_p50 = float(np.percentile(vl_delta_identity, 50))
        vl_delta_p90 = float(np.percentile(vl_delta_identity, 90))
        vl_delta_p99 = float(np.percentile(vl_delta_identity, 99))
        report_data.append({"metric": "delta_identity_distribution_light_p50", "value": f"{vl_delta_p50:.4f}"})
        report_data.append({"metric": "delta_identity_distribution_light_p90", "value": f"{vl_delta_p90:.4f}"})
        report_data.append({"metric": "delta_identity_distribution_light_p99", "value": f"{vl_delta_p99:.4f}"})
    else:
        report_data.append({"metric": "delta_identity_distribution_light_p50", "value": ""})
        report_data.append({"metric": "delta_identity_distribution_light_p90", "value": ""})
        report_data.append({"metric": "delta_identity_distribution_light_p99", "value": ""})
    
    # Top out-of-library global germlines (heavy)
    # These are germlines that appear in global matches but are NOT in library_ref_vh
    vh_out_of_lib_df = germline_df[
        (germline_df["vh_out_of_library_flag"] == True) & 
        (germline_df["vh_best_germline_global"].notna())
    ]
    if len(vh_out_of_lib_df) > 0:
        vh_out_of_lib_germlines = vh_out_of_lib_df["vh_best_germline_global"]
        vh_out_of_lib_counts = vh_out_of_lib_germlines.value_counts()
        # Filter to only those not in library
        vh_out_of_lib_filtered = {
            germline: count 
            for germline, count in vh_out_of_lib_counts.items() 
            if germline not in library_ref_vh
        }
        if vh_out_of_lib_filtered:
            top_out_of_lib_vh = "; ".join([
                f"{germline}({count})" 
                for germline, count in sorted(vh_out_of_lib_filtered.items(), key=lambda x: x[1], reverse=True)[:20]
            ])
            report_data.append({"metric": "list_top_out_of_library_global_germlines_heavy", "value": top_out_of_lib_vh})
        else:
            report_data.append({"metric": "list_top_out_of_library_global_germlines_heavy", "value": ""})
    else:
        report_data.append({"metric": "list_top_out_of_library_global_germlines_heavy", "value": ""})
    
    # Top out-of-library global germlines (light)
    vl_out_of_lib_df = germline_df[
        (germline_df["vl_out_of_library_flag"] == True) & 
        (germline_df["vl_best_germline_global"].notna())
    ]
    if len(vl_out_of_lib_df) > 0:
        vl_out_of_lib_germlines = vl_out_of_lib_df["vl_best_germline_global"]
        vl_out_of_lib_counts = vl_out_of_lib_germlines.value_counts()
        # Filter to only those not in library
        vl_out_of_lib_filtered = {
            germline: count 
            for germline, count in vl_out_of_lib_counts.items() 
            if germline not in library_ref_vl
        }
        if vl_out_of_lib_filtered:
            top_out_of_lib_vl = "; ".join([
                f"{germline}({count})" 
                for germline, count in sorted(vl_out_of_lib_filtered.items(), key=lambda x: x[1], reverse=True)[:20]
            ])
            report_data.append({"metric": "list_top_out_of_library_global_germlines_light", "value": top_out_of_lib_vl})
        else:
            report_data.append({"metric": "list_top_out_of_library_global_germlines_light", "value": ""})
    else:
        report_data.append({"metric": "list_top_out_of_library_global_germlines_light", "value": ""})
    
    # Save to CSV
    report_df = pd.DataFrame(report_data)
    report_path = output_dir / f"library_coverage_report_{slice_id}.csv"
    report_df.to_csv(report_path, index=False, encoding='utf-8-sig')
    print(f"  💾 Saved library coverage report: {report_path}")


def main():
    parser = argparse.ArgumentParser(description="Run ANARCII numbering on specific slices")
    parser.add_argument("--truth_table_xlsx", default="data/thera_sabdab/out/thera_truth_table.xlsx",
                        help="Input Truth Table XLSX file")
    parser.add_argument("--slice_ids_dir", default="data/thera_sabdab/out/slice_ids",
                        help="Directory containing slice ID files")
    parser.add_argument("--output_dir", default="data/thera_sabdab/features",
                        help="Output directory for parquet files")
    parser.add_argument("--checkpoint_dir", default="data/thera_sabdab/features/checkpoints",
                        help="Directory for checkpoint files")
    parser.add_argument("--vh_framework_yaml", default="core/data/framework_library/vh_frameworks.with_cdr12.canonical_input.yaml",
                        help="VH framework library YAML file")
    parser.add_argument("--vl_framework_yaml", default="core/data/framework_library/vl_frameworks.with_cdr12.canonical_input.yaml",
                        help="VL framework library YAML file")
    parser.add_argument("--imgt_human_vh_fasta", default="core/data/imgt_ref/IGHV_aa.fasta",
                        help="IMGT human VH FASTA file")
    parser.add_argument("--imgt_human_vk_fasta", default="core/data/imgt_ref/IGKV_aa.fasta",
                        help="IMGT human VK FASTA file")
    parser.add_argument("--imgt_human_vl_fasta", default="core/data/imgt_ref/IGLV_aa.fasta",
                        help="IMGT human VL FASTA file")
    parser.add_argument("--match_mode", default="global_and_library",
                        choices=["library_only", "global_only", "global_and_library"],
                        help="Germline matching mode: library_only (current behavior), global_only, or global_and_library (default)")
    parser.add_argument("--slices", nargs="+", default=["slice_1_standard_humanized"],
                        choices=["slice_1_standard_humanized", "slice_3_vhh_design", "slice_4_bispecific_engineering", "slice_8_adc"],
                        help="Slices to process (default: slice_1_standard_humanized). Can specify multiple: --slices slice_1 slice_3")
    
    args = parser.parse_args()
    
    truth_table_xlsx = Path(args.truth_table_xlsx)
    if not truth_table_xlsx.is_absolute():
        truth_table_xlsx = PROJECT_ROOT / truth_table_xlsx
    
    slice_ids_dir = Path(args.slice_ids_dir)
    if not slice_ids_dir.is_absolute():
        slice_ids_dir = PROJECT_ROOT / slice_ids_dir
    
    output_dir = Path(args.output_dir)
    if not output_dir.is_absolute():
        output_dir = PROJECT_ROOT / output_dir
    
    checkpoint_dir = Path(args.checkpoint_dir)
    if not checkpoint_dir.is_absolute():
        checkpoint_dir = PROJECT_ROOT / checkpoint_dir
    
    vh_yaml = Path(args.vh_framework_yaml)
    if not vh_yaml.is_absolute():
        vh_yaml = PROJECT_ROOT / vh_yaml
    
    vl_yaml = Path(args.vl_framework_yaml)
    if not vl_yaml.is_absolute():
        vl_yaml = PROJECT_ROOT / vl_yaml
    
    imgt_vh_fasta = Path(args.imgt_human_vh_fasta)
    if not imgt_vh_fasta.is_absolute():
        imgt_vh_fasta = PROJECT_ROOT / imgt_vh_fasta
    
    imgt_vk_fasta = Path(args.imgt_human_vk_fasta)
    if not imgt_vk_fasta.is_absolute():
        imgt_vk_fasta = PROJECT_ROOT / imgt_vk_fasta
    
    imgt_vl_fasta = Path(args.imgt_human_vl_fasta)
    if not imgt_vl_fasta.is_absolute():
        imgt_vl_fasta = PROJECT_ROOT / imgt_vl_fasta
    
    match_mode = args.match_mode
    
    # Define all available slices
    all_slices = {
        "slice_1_standard_humanized": " IgG ",
        "slice_3_vhh_design": "VHH / ",
        "slice_4_bispecific_engineering": "",
        "slice_8_adc": "ADC Engineering Set",  # Note: Slice 8 is from engineering slices, not slice_ids
    }
    
    # Filter to requested slices
    requested_slices = args.slices
    target_slices = {k: v for k, v in all_slices.items() if k in requested_slices}
    
    if not target_slices:
        raise ValueError(f"No valid slices specified. Available: {list(all_slices.keys())}")
    
    print("=" * 70)
    print("🚀 Running ANARCII Numbering on Slices")
    print("=" * 70)
    print(f"📋 Processing slices: {', '.join(target_slices.keys())}")
    print(f"Truth Table: {truth_table_xlsx}")
    print(f"Slice IDs directory: {slice_ids_dir}")
    print(f"Output directory: {output_dir}")
    print(f"Checkpoint directory: {checkpoint_dir}")
    print("=" * 70)
    
    # Load Truth Table
    print(f"\n📖 Loading Truth Table...")
    if not truth_table_xlsx.exists():
        raise RuntimeError(f"CRITICAL: Truth Table not found: {truth_table_xlsx}")
    
    df = pd.read_excel(truth_table_xlsx, engine='openpyxl')
    print(f"✅ Loaded {len(df)} records")
    
    # Load germline FR maps
    print(f"\n📖 Loading framework libraries...")
    library_ref_vh = load_framework_library(vh_yaml)
    library_ref_vl = load_framework_library(vl_yaml)
    print(f"✅ Loaded {len(library_ref_vh)} VH library germlines, {len(library_ref_vl)} VL library germlines")
    
    # Load IMGT global references
    print(f"\n📖 Loading IMGT global references...")
    global_ref_vh = load_imgt_fasta_global_ref(imgt_vh_fasta)
    
    # For VL, merge IGKV and IGLV
    global_ref_vk = load_imgt_fasta_global_ref(imgt_vk_fasta)
    global_ref_vl_temp = load_imgt_fasta_global_ref(imgt_vl_fasta)
    global_ref_vl = {**global_ref_vk, **global_ref_vl_temp}
    print(f"✅ Loaded {len(global_ref_vh)} VH global germlines, {len(global_ref_vl)} VL global germlines (IGKV+IGLV)")
    
    print(f"\n📋 Match mode: {match_mode}")
    
    # Process each slice
    all_stats = {}
    
    for slice_id, slice_name in target_slices.items():
        # Load slice IDs
        if slice_id == "slice_8_adc":
            # Slice 8 is from engineering slices, filter directly from Truth Table
            slice_ids = set()
            df_slice8 = df[
                (df['modality'] == 'ADC') &
                (df['phase_bucket'].isin(['phase_II_plus', 'phase_I'])) &
                (df['human_origin_mode'] != 'non_human')
            ]
            for _, row in df_slice8.iterrows():
                ab_id = get_antibody_id_from_row(row)
                if ab_id:
                    slice_ids.add(ab_id)
            print(f"\n  📦 Slice 8: Found {len(slice_ids)} ADC records from Truth Table")
        else:
            slice_ids_file = slice_ids_dir / f"{slice_id}_ids.txt"
            slice_ids = load_slice_ids(slice_ids_file)
            if not slice_ids:
                print(f"\n  ⚠️  Warning: No IDs found for {slice_id}: {slice_ids_file}")
                continue
        
        checkpoint_file = checkpoint_dir / f"{slice_id}_checkpoint.txt"
        stats = process_slice(
            slice_id,
            slice_name,
            df,
            slice_ids,
            global_ref_vh,
            library_ref_vh,
            global_ref_vl,
            library_ref_vl,
            match_mode,
            checkpoint_file,
            output_dir,
        )
        all_stats[slice_id] = stats
    
    # Save statistics
    stats_json = output_dir / "anarcii_numbering_stats.json"
    with open(stats_json, 'w', encoding='utf-8') as f:
        json.dump(all_stats, f, indent=2, ensure_ascii=False)
    print(f"\n💾 Saved statistics: {stats_json}")
    
    # Print summary
    print("\n" + "=" * 70)
    print("📊 Summary Statistics")
    print("=" * 70)
    for slice_id, stats in all_stats.items():
        print(f"\n{stats['slice_name']} ({slice_id}):")
        print(f"  Total processed: {stats['total_records']}")
        print(f"  VH: {stats['vh']['success']}/{stats['vh']['total']} success (fail rate: {stats['vh']['fail_rate']:.2%})")
        print(f"  VL: {stats['vl']['success']}/{stats['vl']['total']} success (fail rate: {stats['vl']['fail_rate']:.2%})")
        print(f"  VH germline matches: {stats['vh']['germline_match_count']}")
        print(f"  VL germline matches: {stats['vl']['germline_match_count']}")
    print("=" * 70)
    
    print(f"\n✅ ANARCII numbering completed!")
    print(f"   Output directory: {output_dir}")
    print(f"   Statistics: {stats_json}")


if __name__ == "__main__":
    main()
