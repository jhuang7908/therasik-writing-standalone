import pandas as pd
import numpy as np
import os
import yaml
import sys
import json
from pathlib import Path
from collections import Counter
import math

# Add project root to path for internal imports
PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.append(str(PROJECT_ROOT))

from core.numbering.imgt_anarcii import imgt_number_anarcii

def calculate_shannon_entropy(residues):
    """
    residues: list of amino acids at a position.
    """
    counts = Counter(residues)
    total = sum(counts.values())
    if total == 0: return 0.0
    
    entropy = 0.0
    for count in counts.values():
        p = count / total
        entropy -= p * math.log2(p)
    return entropy

def build_position_sets():
    audit_log = []
    
    # 1. Authoritative Anchor Positions (from query + codebase)
    # Query suggested: {26, 39, 55, 66, 104, 118}
    # codebase functional_sites.yaml mentioned some others.
    authoritative_anchors = {26, 39, 55, 66, 104, 118}
    audit_log.append(f"Base anchors from query: {sorted(list(authoritative_anchors))}")
    
    # 2. VHH Hallmark positions
    vhh_hallmarks = [37, 44, 45, 47]
    audit_log.append(f"VHH Hallmark positions: {vhh_hallmarks}")
    
    # 3. Vernier anchor positions
    vernier_anchors = [28, 29, 94]
    audit_log.append(f"Vernier anchor positions: {vernier_anchors}")
    
    # 4. North-Dunbrack dependent positions (placeholders for now)
    # The structure should support per-canonical-class dependent position lists.
    north_dunbrack = {
        "H1-13-1": [],
        "H2-10-1": [],
        "H2-9-1": [],
        "H1-14-1": []
    }
    audit_log.append("North-Dunbrack dependent positions: Empty placeholders created.")
    
    # 5. Surface Plasticity positions (data-driven)
    germline_jsonl = PROJECT_ROOT / "data" / "germlines" / "vhh_v1" / "vhh_germline_assets_clean.jsonl"
    surface_plasticity = []
    
    if germline_jsonl.exists():
        audit_log.append(f"Loading germline assets for entropy analysis from {germline_jsonl}")
        pos_residues = {} # imgt_pos -> list of residues
        
        count = 0
        with open(germline_jsonl, 'r', encoding='utf-8') as f:
            for line in f:
                l = json.loads(line)
                # Use human germlines for framework distribution (Phase-II+ style)
                if 'Homo' in l['sequence_id']:
                    imgt_map = l.get('imgt_map', {})
                    if not imgt_map: continue
                    count += 1
                    for pos_str, res in imgt_map.items():
                        if res == '-': continue
                        # IMGT map keys are strings, sometimes with insertions (e.g. "1.1")
                        # We want integer positions for entropy whitelist
                        try:
                            # Handle potential insertion codes or non-integer keys
                            if '.' in pos_str:
                                pos_int = int(pos_str.split('.')[0])
                            else:
                                pos_int = int(pos_str)
                            
                            if pos_int not in pos_residues:
                                pos_residues[pos_int] = []
                            pos_residues[pos_int].append(res)
                        except ValueError:
                            continue
        
        audit_log.append(f"Analyzed {count} human germlines for entropy.")
        
        # FR1: 1-26, FR2: 39-55, FR3: 66-104
        fr_ranges = [(1, 26), (39, 55), (66, 104)]
        fr_entropies = {}
        
        for pos, residues in pos_residues.items():
            in_fr = any(start <= pos <= end for start, end in fr_ranges)
            if in_fr:
                fr_entropies[pos] = calculate_shannon_entropy(residues)
        
        if fr_entropies:
            # Candidate surface positions = top 30% entropy
            sorted_positions = sorted(fr_entropies.items(), key=lambda x: x[1], reverse=True)
            # Thresholding
            top_n = int(len(sorted_positions) * 0.3)
            candidates = set([p[0] for p in sorted_positions[:top_n]])
            
            # Exclusions
            flattened_north = set()
            for l in north_dunbrack.values():
                flattened_north.update(l)
            
            exclude_set = authoritative_anchors | set(vhh_hallmarks) | set(vernier_anchors) | flattened_north
            surface_plasticity = sorted(list(candidates - exclude_set))
            
            audit_log.append(f"Computed surface plasticity whitelist v1 (N={len(surface_plasticity)}): {surface_plasticity}")
            if top_n < len(sorted_positions):
                audit_log.append(f"Entropy threshold (top 30%): {sorted_positions[top_n][1]:.4f}")
        else:
            audit_log.append("Warning: No residues found in FR positions. surface_plasticity_positions_v1 will be empty.")
    else:
        audit_log.append(f"Warning: Germline assets not found at {germline_jsonl}. surface_plasticity_positions_v1 will be empty.")

    # Prepare YAML
    yaml_data = {
        "imgt_position_sets": {
            "imgt_anchor_positions": sorted(list(authoritative_anchors)),
            "vhh_hallmark_positions": vhh_hallmarks,
            "vernier_anchor_positions": vernier_anchors,
            "north_dunbrack_dependent_positions": north_dunbrack,
            "surface_plasticity_positions_v1": surface_plasticity
        },
        "meta": {
            "source": "InSynBio-AI Antibody Engineer Suite",
            "generation_script": "scripts/build_imgt_position_sets.py",
            "status": "v1.0-production"
        }
    }

    # Save YAML
    yaml_path = PROJECT_ROOT / "core" / "data" / "position_sets" / "imgt_position_sets.yaml"
    os.makedirs(yaml_path.parent, exist_ok=True)
    with open(yaml_path, 'w', encoding='utf-8') as f:
        yaml.dump(yaml_data, f, sort_keys=False, default_flow_style=False)
    
    # Save Audit Note
    audit_path = PROJECT_ROOT / "output" / "position_sets_generation_audit.md"
    os.makedirs(audit_path.parent, exist_ok=True)
    with open(audit_path, 'w', encoding='utf-8') as f:
        f.write("# IMGT Position Sets Generation Audit\n\n")
        for log in audit_log:
            f.write(f"- {log}\n")
    
    print(f"Saved YAML to {yaml_path}")
    print(f"Saved Audit Note to {audit_path}")

if __name__ == "__main__":
    build_position_sets()
