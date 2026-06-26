#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Bootstrap missing canonical envelope entries.

Reads vh_frameworks.yaml and vl_frameworks.yaml, checks canonical_envelopes.yaml,
and adds TODO placeholder entries for any missing framework germlines.

Hard constraints:
- No guessing or inferred numbers
- All missing entries get TODO for all fields
- Notes: "Bootstrapped placeholder; requires curation"
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path
from typing import Any, Dict, List, Set

import yaml

PROJECT_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT_ROOT))


def load_yaml(path: Path) -> Any:
    """Load YAML file."""
    if not path.exists():
        raise FileNotFoundError(f"File not found: {path}")
    with open(path, "r", encoding="utf-8") as f:
        return yaml.safe_load(f) or {}


def write_yaml(path: Path, data: Any) -> None:
    """Write YAML file."""
    path.parent.mkdir(parents=True, exist_ok=True)
    with open(path, "w", encoding="utf-8") as f:
        yaml.safe_dump(data, f, sort_keys=False, allow_unicode=True, default_flow_style=False)


def extract_germlines_from_frameworks(frameworks_data: Dict[str, Any], chain: str) -> Set[str]:
    """
    Extract germline IDs from frameworks YAML.
    
    Args:
        frameworks_data: Loaded YAML data from vh_frameworks.yaml or vl_frameworks.yaml
        chain: "VH" or "VL"
    
    Returns:
        Set of germline IDs (e.g., {"IGHV3-23*01", ...})
    """
    germlines: Set[str] = set()
    
    # Support both "frameworks" and "entries" keys
    entries = frameworks_data.get("frameworks", []) or frameworks_data.get("entries", [])
    
    if not isinstance(entries, list):
        return germlines
    
    for entry in entries:
        # Extract germline from either "germline" field or from "framework_id"
        germline = entry.get("germline", "")
        if not germline:
            # Try to extract from framework_id (e.g., "VH:IGHV3-23*01" -> "IGHV3-23*01")
            fw_id = entry.get("framework_id", "")
            if isinstance(fw_id, str) and fw_id.startswith(f"{chain}:"):
                germline = fw_id.split(":", 1)[1]
            elif isinstance(fw_id, str):
                # If framework_id is just the germline itself
                germline = fw_id
        
        if germline and not germline.upper().startswith("TODO"):
            germlines.add(germline.strip())
    
    return germlines


def create_todo_canonical_entry(chain: str) -> Dict[str, Any]:
    """
    Create a TODO canonical envelope entry.
    
    Args:
        chain: "VH" or "VL"
    
    Returns:
        Canonical entry dict with all fields as TODO
    """
    if chain == "VH":
        return {
            "cdr_h1": {
                "length_mode": "TODO",
                "length_range": "TODO",
                "canonical_class": "TODO",
            },
            "cdr_h2": {
                "length_mode": "TODO",
                "length_range": "TODO",
                "canonical_class": "TODO",
            },
            "notes": "Bootstrapped placeholder; requires curation",
        }
    elif chain == "VL":
        return {
            "cdr_l1": {
                "length_mode": "TODO",
                "length_range": "TODO",
                "canonical_class": "TODO",
            },
            "cdr_l2": {
                "length_mode": "TODO",
                "length_range": "TODO",
                "canonical_class": "TODO",
            },
            "notes": "Bootstrapped placeholder; requires curation",
        }
    else:
        raise ValueError(f"Unknown chain: {chain}")


def bootstrap_canonical_entries(
    vh_frameworks_path: Path,
    vl_frameworks_path: Path,
    canonical_path: Path,
    output_path: Path,
) -> Dict[str, Any]:
    """
    Bootstrap missing canonical entries.
    
    Returns:
        Dict with statistics: {"vh_added": int, "vl_added": int, "vh_missing": List[str], "vl_missing": List[str]}
    """
    # Load frameworks
    vh_frameworks = load_yaml(vh_frameworks_path)
    vl_frameworks = load_yaml(vl_frameworks_path)
    canonical = load_yaml(canonical_path)
    
    # Extract germlines from frameworks
    vh_germlines = extract_germlines_from_frameworks(vh_frameworks, "VH")
    vl_germlines = extract_germlines_from_frameworks(vl_frameworks, "VL")
    
    # Get existing canonical entries
    vh_canonical = canonical.get("vh", {})
    vl_canonical = canonical.get("vl", {})
    
    # Find missing entries
    vh_missing = sorted(vh_germlines - set(vh_canonical.keys()))
    vl_missing = sorted(vl_germlines - set(vl_canonical.keys()))
    
    # Add TODO entries for missing ones
    vh_added = 0
    vl_added = 0
    
    for germline in vh_missing:
        vh_canonical[germline] = create_todo_canonical_entry("VH")
        vh_added += 1
    
    for germline in vl_missing:
        vl_canonical[germline] = create_todo_canonical_entry("VL")
        vl_added += 1
    
    # Update canonical dict
    canonical["vh"] = vh_canonical
    canonical["vl"] = vl_canonical
    
    # Write back
    write_yaml(output_path, canonical)
    
    return {
        "vh_added": vh_added,
        "vl_added": vl_added,
        "vh_missing": vh_missing,
        "vl_missing": vl_missing,
    }


def write_log(log_path: Path, stats: Dict[str, Any], vh_path: Path, vl_path: Path, canonical_path: Path) -> None:
    """Write bootstrap log."""
    lines: List[str] = []
    lines.append("# Canonical Envelope Bootstrap Log")
    lines.append("")
    lines.append(f"- VH frameworks input: `{vh_path}`")
    lines.append(f"- VL frameworks input: `{vl_path}`")
    lines.append(f"- Canonical envelopes input/output: `{canonical_path}`")
    lines.append("")
    
    lines.append("## Summary")
    lines.append("")
    lines.append(f"- VH entries added: {stats['vh_added']}")
    lines.append(f"- VL entries added: {stats['vl_added']}")
    lines.append(f"- Total entries added: {stats['vh_added'] + stats['vl_added']}")
    lines.append("")
    
    if stats["vh_missing"]:
        lines.append("## VH Missing Entries (Added)")
        lines.append("")
        for germline in stats["vh_missing"]:
            lines.append(f"- `{germline}`")
        lines.append("")
    
    if stats["vl_missing"]:
        lines.append("## VL Missing Entries (Added)")
        lines.append("")
        for germline in stats["vl_missing"]:
            lines.append(f"- `{germline}`")
        lines.append("")
    
    lines.append("## Notes")
    lines.append("")
    lines.append("- All added entries have all fields set to TODO")
    lines.append("- Notes field: 'Bootstrapped placeholder; requires curation'")
    lines.append("- No data was inferred or guessed")
    lines.append("")
    
    log_path.parent.mkdir(parents=True, exist_ok=True)
    log_path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Bootstrap missing canonical envelope entries with TODO placeholders"
    )
    parser.add_argument(
        "--vh",
        default="core/data/framework_library/vh_frameworks.yaml",
        help="Path to VH frameworks YAML",
    )
    parser.add_argument(
        "--vl",
        default="core/data/framework_library/vl_frameworks.yaml",
        help="Path to VL frameworks YAML",
    )
    parser.add_argument(
        "--canonical",
        default="core/data/framework_library/canonical_envelopes.yaml",
        help="Path to canonical envelopes YAML (input and output)",
    )
    parser.add_argument(
        "--log",
        default="docs/canonical_bootstrap_log.md",
        help="Path to output log file",
    )
    args = parser.parse_args()
    
    vh_path = PROJECT_ROOT / args.vh
    vl_path = PROJECT_ROOT / args.vl
    canonical_path = PROJECT_ROOT / args.canonical
    log_path = PROJECT_ROOT / args.log
    
    if not vh_path.exists():
        raise FileNotFoundError(f"VH frameworks not found: {vh_path}")
    if not vl_path.exists():
        raise FileNotFoundError(f"VL frameworks not found: {vl_path}")
    if not canonical_path.exists():
        raise FileNotFoundError(f"Canonical envelopes not found: {canonical_path}")
    
    print(f"[INFO] Loading frameworks and canonical envelopes...")
    stats = bootstrap_canonical_entries(vh_path, vl_path, canonical_path, canonical_path)
    
    print(f"[INFO] Writing log...")
    write_log(log_path, stats, vh_path, vl_path, canonical_path)
    
    print(f"[OK] Canonical envelopes updated: {canonical_path}")
    print(f"[OK] Log written: {log_path}")
    print(f"[INFO] VH entries added: {stats['vh_added']}")
    print(f"[INFO] VL entries added: {stats['vl_added']}")
    
    if stats["vh_missing"]:
        print(f"[INFO] VH missing entries: {', '.join(stats['vh_missing'][:5])}")
        if len(stats["vh_missing"]) > 5:
            print(f"[INFO] ... and {len(stats['vh_missing']) - 5} more")
    
    if stats["vl_missing"]:
        print(f"[INFO] VL missing entries: {', '.join(stats['vl_missing'][:5])}")
        if len(stats["vl_missing"]) > 5:
            print(f"[INFO] ... and {len(stats['vl_missing']) - 5} more")
    
    return 0


if __name__ == "__main__":
    sys.exit(main())
