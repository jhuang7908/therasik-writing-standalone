#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Join canonical envelopes into framework library entries.

Inputs:
- core/data/framework_library/vh_frameworks.yaml
- core/data/framework_library/vl_frameworks.yaml
- core/data/framework_library/canonical_envelopes.yaml

Outputs (in-place update by default):
- vh_frameworks.yaml
- vl_frameworks.yaml
- docs/framework_library_join_log.md

Hard constraints:
- Do NOT modify fr_sequence_fr1_fr3 or fr_segments.
- Only populate/overwrite `canonical` and optionally `cdr3_policy`.
- If canonical mapping missing, keep TODO and log.
"""

from __future__ import annotations

import argparse
from pathlib import Path
from typing import Any, Dict, List, Tuple

try:
    import yaml
except ImportError as e:
    raise SystemExit("Missing dependency: PyYAML. Please install pyyaml.") from e


def load_yaml(path: Path) -> Any:
    return yaml.safe_load(path.read_text(encoding="utf-8"))


def write_yaml(path: Path, data: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8") as f:
        yaml.safe_dump(data, f, sort_keys=False, allow_unicode=True)


def write_log(path: Path, lines: List[str]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def default_cdr3_policy_for_chain(chain: str) -> Dict[str, Any]:
    """
    Conservative, generic policy only. You can later specialize per framework.
    This is *not* a guarantee of developability; it's a risk window for sorting.
    """
    if chain.upper() == "VH":
        return {
            "preferred_max": 18,
            "caution_range": [19, 22],
            "high_risk_min": 23,
            "notes": "Generic VH CDR-H3 length risk window; refine per program."
        }
    # VL (L3)
    return {
        "preferred_max": 11,
        "caution_range": [12, 13],
        "high_risk_min": 14,
        "notes": "Generic VL CDR-L3 length risk window; refine per program."
    }


def join_into_entries(
    entries: List[Dict[str, Any]],
    canonical_map: Dict[str, Any],
    chain: str,
    set_default_cdr3_policy: bool,
    log_lines: List[str],
) -> Tuple[int, int]:
    updated = 0
    missing = 0

    for e in entries:
        fw_id = str(e.get("framework_id") or e.get("germline") or "")
        if not fw_id:
            missing += 1
            log_lines.append(f"- WARN: entry missing framework_id/germline; skip")
            continue

        # Extract germline from framework_id (e.g., "VH:IGHV3-23*01" -> "IGHV3-23*01")
        # or use germline field directly
        germline = e.get("germline", "")
        if not germline and fw_id.startswith(f"{chain}:"):
            germline = fw_id.split(":", 1)[1]
        elif not germline:
            germline = fw_id

        # Match against canonical map (keys are germline IDs like "IGHV3-23*01")
        if germline in canonical_map:
            # Convert canonical envelope format to framework format
            envelope = canonical_map[germline]
            canonical = convert_canonical_envelope_to_framework_format(envelope, chain)
            e["canonical"] = canonical
            updated += 1
            log_lines.append(f"- OK: {fw_id} (germline: {germline}) canonical joined")
        else:
            # keep existing TODO or whatever; do not invent
            if e.get("canonical") in (None, "", "TODO"):
                e["canonical"] = {
                    "cdr1": {"length_mode": "TODO", "length_range": "TODO", "class": "TODO"},
                    "cdr2": {"length_mode": "TODO", "length_range": "TODO", "class": "TODO"},
                }
            missing += 1
            log_lines.append(f"- MISS: {fw_id} (germline: {germline}) canonical not found (kept TODO)")

        if set_default_cdr3_policy:
            # only set if empty/TODO to avoid clobbering future specialization
            cdr3_policy = e.get("cdr3_policy")
            if cdr3_policy in (None, "", "TODO"):
                e["cdr3_policy"] = default_cdr3_policy_for_chain(chain)
            elif isinstance(cdr3_policy, dict):
                # Check if all values are TODO
                all_todo = all(
                    v in (None, "", "TODO") 
                    for v in [cdr3_policy.get("preferred_max"), cdr3_policy.get("caution_range"), cdr3_policy.get("high_risk_min")]
                )
                if all_todo:
                    e["cdr3_policy"] = default_cdr3_policy_for_chain(chain)

    return updated, missing


def convert_canonical_envelope_to_framework_format(
    envelope: Dict[str, Any],
    chain: str
) -> Dict[str, Any]:
    """
    Convert canonical envelope format to framework library format.
    
    Input format (canonical_envelopes.yaml):
      cdr_h1: {length_mode: 5, length_range: [4, 6], canonical_class: "H1-1"}
      cdr_h2: {length_mode: 17, length_range: [16, 18], canonical_class: "H2-3-2"}
    
    Output format (frameworks.yaml):
      canonical:
        cdr1: {length_mode: 5, length_range: [4, 6], class: "H1-1"}
        cdr2: {length_mode: 17, length_range: [16, 18], class: "H2-3-2"}
    """
    if chain == "VH":
        cdr1_key = "cdr_h1"
        cdr2_key = "cdr_h2"
    elif chain == "VL":
        cdr1_key = "cdr_l1"
        cdr2_key = "cdr_l2"
    else:
        raise ValueError(f"Unknown chain: {chain}")
    
    cdr1_data = envelope.get(cdr1_key, {})
    cdr2_data = envelope.get(cdr2_key, {})
    
    canonical = {
        "cdr1": {
            "length_mode": cdr1_data.get("length_mode", "TODO"),
            "length_range": cdr1_data.get("length_range", "TODO"),
            "class": cdr1_data.get("canonical_class", "TODO"),
        },
        "cdr2": {
            "length_mode": cdr2_data.get("length_mode", "TODO"),
            "length_range": cdr2_data.get("length_range", "TODO"),
            "class": cdr2_data.get("canonical_class", "TODO"),
        },
    }
    
    return canonical


def main() -> int:
    parser = argparse.ArgumentParser(description="Join canonical envelopes into framework YAMLs.")
    parser.add_argument("--vh", default="core/data/framework_library/vh_frameworks.yaml")
    parser.add_argument("--vl", default="core/data/framework_library/vl_frameworks.yaml")
    parser.add_argument("--canonical", default="core/data/framework_library/canonical_envelopes.yaml")
    parser.add_argument("--inplace", action="store_true", help="Write back to same YAML files")
    parser.add_argument("--out_dir", default="", help="If not inplace, write to this directory")
    parser.add_argument("--set_default_cdr3_policy", action="store_true", help="Set generic cdr3_policy if TODO/empty")
    args = parser.parse_args()

    vh_path = Path(args.vh)
    vl_path = Path(args.vl)
    canon_path = Path(args.canonical)

    if not vh_path.exists():
        raise SystemExit(f"VH frameworks not found: {vh_path}")
    if not vl_path.exists():
        raise SystemExit(f"VL frameworks not found: {vl_path}")
    if not canon_path.exists():
        raise SystemExit(f"Canonical envelopes not found: {canon_path}")

    vh = load_yaml(vh_path)
    vl = load_yaml(vl_path)
    canon = load_yaml(canon_path)

    # Build mapping: framework_id -> canonical dict
    # canonical_envelopes.yaml structure: vh: {fw_id: {...}}, vl: {fw_id: {...}}
    vh_canon_raw = (canon.get("vh") or {})
    vl_canon_raw = (canon.get("vl") or {})
    # We store only the canonical fields (drop notes optionally but keep it if present)
    vh_canon_map: Dict[str, Any] = {k: v for k, v in vh_canon_raw.items()}
    vl_canon_map: Dict[str, Any] = {k: v for k, v in vl_canon_raw.items()}

    log_lines: List[str] = []
    log_lines.append("# Framework Library Canonical Join Log")
    log_lines.append("")
    log_lines.append(f"- VH input: `{vh_path}`")
    log_lines.append(f"- VL input: `{vl_path}`")
    log_lines.append(f"- canonical source: `{canon_path}`")
    log_lines.append(f"- set_default_cdr3_policy: {bool(args.set_default_cdr3_policy)}")
    log_lines.append("")

    # Support both "frameworks" and "entries" keys for compatibility
    vh_entries = (vh.get("frameworks") or vh.get("entries") or [])
    vl_entries = (vl.get("frameworks") or vl.get("entries") or [])

    if not isinstance(vh_entries, list) or not isinstance(vl_entries, list):
        raise SystemExit("Framework YAML format unexpected: expected top-level {frameworks:[...]} or {entries:[...]}")

    log_lines.append("## VH join results")
    vh_updated, vh_missing = join_into_entries(
        vh_entries, vh_canon_map, "VH", args.set_default_cdr3_policy, log_lines
    )
    log_lines.append("")
    log_lines.append(f"Summary: updated={vh_updated}, missing={vh_missing}")
    log_lines.append("")

    log_lines.append("## VL join results")
    vl_updated, vl_missing = join_into_entries(
        vl_entries, vl_canon_map, "VL", args.set_default_cdr3_policy, log_lines
    )
    log_lines.append("")
    log_lines.append(f"Summary: updated={vl_updated}, missing={vl_missing}")
    log_lines.append("")

    # Write outputs
    if args.inplace:
        write_yaml(vh_path, vh)
        write_yaml(vl_path, vl)
        out_vh = vh_path
        out_vl = vl_path
    else:
        if not args.out_dir:
            raise SystemExit("Provide --out_dir when not using --inplace")
        out_dir = Path(args.out_dir)
        out_vh = out_dir / vh_path.name
        out_vl = out_dir / vl_path.name
        write_yaml(out_vh, vh)
        write_yaml(out_vl, vl)

    log_out = Path("docs") / "framework_library_join_log.md"
    write_log(log_out, log_lines)

    print(f"[OK] VH written: {out_vh}")
    print(f"[OK] VL written: {out_vl}")
    print(f"[OK] Log written: {log_out}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
