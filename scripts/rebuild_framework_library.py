#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
scripts/rebuild_framework_library.py

Rebuilds the framework library by extracting real sequences from IMGT reference FASTA.
Preserves existing canonical classes and cdr3_policy.
Ensures no TODOs remain in fr_sequence_fr1_fr3 for target germlines.
"""

import sys
import os
import yaml
import hashlib
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple
from datetime import datetime

# Add project root to path
PROJECT_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT_ROOT))

from core.numbering.imgt_anarcii import imgt_number_anarcii, IMGTNumberingError
from core.vhh_humanization import split_regions

def sha256_hex(s: str) -> str:
    return hashlib.sha256(s.encode("utf-8")).hexdigest()

def load_yaml(path: Path) -> Any:
    if not path.exists():
        return None
    with open(path, "r", encoding="utf-8") as f:
        return yaml.safe_load(f)

def write_yaml(path: Path, data: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with open(path, "w", encoding="utf-8") as f:
        yaml.safe_dump(data, f, sort_keys=False, allow_unicode=True, default_flow_style=False)

def iter_fasta_records(path: Path):
    header = None
    seq_parts = []
    with open(path, "r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line: continue
            if line.startswith(">"):
                if header:
                    yield header, "".join(seq_parts)
                header = line[1:].strip()
                seq_parts = []
            else:
                seq_parts.append(line)
        if header:
            yield header, "".join(seq_parts)

def scan_fastas(imgt_dir: Path) -> Dict[str, List[Dict[str, str]]]:
    index = {}
    for ext in ["*.fasta", "*.fa"]:
        for fp in imgt_dir.glob(ext):
            rel_path = str(fp.relative_to(PROJECT_ROOT)).replace("\\", "/")
            for header, seq in iter_fasta_records(fp):
                # Simple germline extraction from header
                # Typically IMGT headers look like: >L22657|IGHV3-23*01|Homo sapiens|...
                parts = header.split("|")
                germline = None
                species = "Unknown"
                if len(parts) > 1:
                    germline = parts[1].strip()
                if len(parts) > 2:
                    species = parts[2].strip()
                
                record = {
                    "header": header,
                    "sequence": seq.upper().replace("*", ""),
                    "source_file": rel_path,
                    "species": species
                }

                if germline:
                    index.setdefault(germline.upper(), []).append(record)
                
                # Also index by parts of header just in case
                for p in parts:
                    if "*" in p:
                        index.setdefault(p.strip().upper(), []).append(record)
    return index

def process_rebuild():
    targets_path = PROJECT_ROOT / "core" / "data" / "framework_library" / "targets.yaml"
    vh_path = PROJECT_ROOT / "core" / "data" / "framework_library" / "vh_frameworks.yaml"
    vl_path = PROJECT_ROOT / "core" / "data" / "framework_library" / "vl_frameworks.yaml"
    imgt_dir = PROJECT_ROOT / "core" / "data" / "imgt_ref"

    targets_data = load_yaml(targets_path)
    if not targets_data:
        print("[ERROR] targets.yaml not found.")
        return

    vh_lib = load_yaml(vh_path) or {"frameworks": []}
    vl_lib = load_yaml(vl_path) or {"frameworks": []}

    # Index existing libraries by germline for easy update
    vh_map = {fw["germline"]: fw for fw in vh_lib.get("frameworks", [])}
    vl_map = {fw["germline"]: fw for fw in vl_lib.get("frameworks", [])}

    # Scan FASTA
    fasta_index = scan_fastas(imgt_dir)
    print(f"[INFO] Indexed {len(fasta_index)} germlines from FASTA.")

    # Target germlines
    vh_targets = [t["germline"] for t in targets_data.get("human_vh_targets", [])] + \
                 [t["germline"] for t in targets_data.get("dog_vh_targets", [])]
    vl_targets = [t["germline"] for t in targets_data.get("human_vl_targets", [])] + \
                 [t["germline"] for t in targets_data.get("dog_vl_targets", [])]

    errors = []

    def update_entry(germline: str, chain: str, existing_entry: Optional[Dict[str, Any]], target_species: str) -> Dict[str, Any]:
        if "TODO" in germline.upper():
            return existing_entry # Skip placeholder targets

        records = fasta_index.get(germline.upper(), [])
        if not records:
            # Try relaxed match if exact fails
            base = germline.split("*")[0]
            records = fasta_index.get(base.upper(), [])
            if not records:
                errors.append(f"Missing FASTA record for {germline}")
                return existing_entry

        # Prioritize target species
        selected_rec = records[0]
        for r in records:
            if target_species.lower() in r["species"].lower():
                selected_rec = r
                break
        
        rec = selected_rec
        seq = rec["sequence"]
        
        try:
            # ANARCII numbering
            rows = imgt_number_anarcii(seq)
            regions = split_regions(rows)
            
            fr1 = regions.get("FR1", "")
            fr2 = regions.get("FR2", "")
            fr3 = regions.get("FR3", "")
            
            if not (fr1 and fr2 and fr3):
                errors.append(f"Incomplete FR regions for {germline}: FR1={len(fr1)}, FR2={len(fr2)}, FR3={len(fr3)}")
                return existing_entry

            fr_seq = fr1 + fr2 + fr3
            
            # Create or update entry
            entry = existing_entry or {
                "framework_id": f"{chain}:{germline}",
                "chain": chain,
                "family": germline.split("-")[0],
                "germline": germline,
                "tags": [],
                "use_cases": [],
                "avoid_cases": [],
                "evidence": []
            }
            
            entry["fr_sequence_fr1_fr3"] = fr_seq
            entry["fr_segments"] = {
                "fr1": fr1,
                "fr2": fr2,
                "fr3": fr3
            }
            
            # Traceability
            entry["source_trace"] = {
                "source_file": rec["source_file"],
                "fasta_header": rec["header"],
                "sha256_sequence": sha256_hex(seq),
                "sha256_fr1_fr3": sha256_hex(fr_seq)
            }
            
            # Numbering evidence (minimal positions map)
            pos_map = {row["pos"]: row["aa"] for row in rows if row["aa"] != "-"}
            entry["numbering_evidence"] = {
                "scheme": "IMGT",
                "positions": pos_map
            }
            
            # Ensure canonical and cdr3_policy exist
            if "canonical" not in entry:
                entry["canonical"] = {
                    "cdr1": {"length_mode": "TODO", "length_range": "TODO", "class": "TODO"},
                    "cdr2": {"length_mode": "TODO", "length_range": "TODO", "class": "TODO"}
                }
            if "cdr3_policy" not in entry:
                entry["cdr3_policy"] = {"preferred_max": "TODO", "caution_range": "TODO", "high_risk_min": "TODO"}
                
            return entry

        except Exception as e:
            errors.append(f"Error processing {germline}: {str(e)}")
            return existing_entry

    # Update VH
    new_vh_frameworks = []
    # Human VH
    for t in targets_data.get("human_vh_targets", []):
        g = t["germline"]
        if "TODO" in g.upper(): continue
        entry = update_entry(g, "VH", vh_map.get(g), "Homo sapiens")
        if entry: new_vh_frameworks.append(entry)
    # Dog VH
    for t in targets_data.get("dog_vh_targets", []):
        g = t["germline"]
        if "TODO" in g.upper(): continue
        entry = update_entry(g, "VH", vh_map.get(g), "Canis lupus familiaris")
        if entry: new_vh_frameworks.append(entry)
    
    # Update VL
    new_vl_frameworks = []
    # Human VL
    for t in targets_data.get("human_vl_targets", []):
        g = t["germline"]
        if "TODO" in g.upper(): continue
        entry = update_entry(g, "VL", vl_map.get(g), "Homo sapiens")
        if entry: new_vl_frameworks.append(entry)
    # Dog VL
    for t in targets_data.get("dog_vl_targets", []):
        g = t["germline"]
        if "TODO" in g.upper(): continue
        entry = update_entry(g, "VL", vl_map.get(g), "Canis lupus familiaris")
        if entry: new_vl_frameworks.append(entry)

    # Final check for TODOs in targets
    todo_remains = []
    for fw in new_vh_frameworks:
        if fw.get("fr_sequence_fr1_fr3") == "TODO":
            todo_remains.append(f"VH:{fw['germline']}")
    for fw in new_vl_frameworks:
        if fw.get("fr_sequence_fr1_fr3") == "TODO":
            todo_remains.append(f"VL:{fw['germline']}")

    if todo_remains or errors:
        print("\n[BLOCKERS IDENTIFIED]")
        for err in errors:
            print(f"- ERROR: {err}")
        for t in todo_remains:
            print(f"- TODO REMAINING: {t}")
        
        # Guard: If any target entry remains TODO, raise error
        if todo_remains:
            raise RuntimeError(f"Rebuild failed: {len(todo_remains)} targets still have TODO sequences.")

    # Write back
    write_yaml(vh_path, {"frameworks": new_vh_frameworks})
    write_yaml(vl_path, {"frameworks": new_vl_frameworks})
    print(f"\n[SUCCESS] Rebuild complete. VH: {len(new_vh_frameworks)}, VL: {len(new_vl_frameworks)}")

if __name__ == "__main__":
    try:
        process_rebuild()
    except Exception as e:
        print(f"[FATAL] {str(e)}")
        sys.exit(1)
