#!/usr/bin/env python3
"""
Validate framework library YAML files against JSON Schema.

Outputs a "missing fields" list per entry (path-like keys).
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any, Dict, List, Tuple

import yaml


PROJECT_ROOT = Path(__file__).resolve().parent.parent
DEFAULT_SCHEMA_PATH = PROJECT_ROOT / "core" / "schemas" / "framework_entry.schema.json"
DEFAULT_YAML_PATHS = [
    PROJECT_ROOT / "core" / "data" / "framework_library" / "vh_frameworks.yaml",
    PROJECT_ROOT / "core" / "data" / "framework_library" / "vl_frameworks.yaml",
]


def _load_yaml_entries(path: Path) -> List[Dict[str, Any]]:
    with open(path, "r", encoding="utf-8") as f:
        data = yaml.safe_load(f) or {}

    if isinstance(data, list):
        entries = data
    elif isinstance(data, dict):
        # preferred shape: {frameworks: [...]}
        if "frameworks" in data:
            entries = data["frameworks"]
        else:
            # fallback: allow a single entry dict
            entries = [data]
    else:
        raise ValueError(f"Unsupported YAML top-level type: {type(data).__name__}")

    if not isinstance(entries, list):
        raise ValueError("frameworks must be a list")

    out: List[Dict[str, Any]] = []
    for i, item in enumerate(entries):
        if not isinstance(item, dict):
            raise ValueError(f"Entry at index {i} is not a mapping/object")
        out.append(item)
    return out


def _load_schema(path: Path) -> Dict[str, Any]:
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)


def _collect_missing_fields(entry: Dict[str, Any], schema: Dict[str, Any]) -> List[str]:
    """
    Collect missing required fields recursively based on schema.required.
    Returns field paths like:
      - canonical.cdr1.length_mode
      - cdr3_policy.preferred_max
    """

    def walk(obj: Any, sch: Dict[str, Any], prefix: str) -> List[str]:
        missing: List[str] = []

        required = sch.get("required", [])
        properties = sch.get("properties", {})

        if required and isinstance(obj, dict):
            for key in required:
                if key not in obj:
                    missing.append(f"{prefix}{key}")

        # recurse only into properties that are present
        if isinstance(obj, dict) and isinstance(properties, dict):
            for key, prop_schema in properties.items():
                if key not in obj:
                    continue
                if not isinstance(prop_schema, dict):
                    continue
                # object recursion
                if prop_schema.get("type") == "object":
                    child = obj.get(key)
                    if isinstance(child, dict):
                        missing.extend(walk(child, prop_schema, f"{prefix}{key}."))

        return missing

    return sorted(set(walk(entry, schema, "")))


def _validate_with_jsonschema(entries: List[Dict[str, Any]], schema: Dict[str, Any]) -> Tuple[bool, List[str]]:
    """
    Validate with jsonschema if available. Returns (ok, error_summaries).
    """
    try:
        from jsonschema import Draft202012Validator  # type: ignore
    except Exception:
        return True, [
            "jsonschema not installed; skipped full schema validation (only missing-field check was performed)."
        ]

    v = Draft202012Validator(schema)
    errors = []
    for idx, entry in enumerate(entries):
        for err in sorted(v.iter_errors(entry), key=lambda e: e.path):
            loc = ".".join(str(p) for p in err.path) if err.path else "<root>"
            errors.append(f"[entry#{idx}] {loc}: {err.message}")
    return len(errors) == 0, errors


def main() -> int:
    parser = argparse.ArgumentParser(description="Validate framework library YAML files.")
    parser.add_argument(
        "--schema",
        type=str,
        default=str(DEFAULT_SCHEMA_PATH),
        help="Path to framework_entry.schema.json",
    )
    parser.add_argument(
        "yaml_paths",
        nargs="*",
        help="YAML files to validate (default: VH+VL framework YAMLs).",
    )
    args = parser.parse_args()

    schema_path = Path(args.schema)
    if not schema_path.exists():
        print(f"ERROR: schema not found: {schema_path}")
        return 2

    yaml_paths = [Path(p) for p in args.yaml_paths] if args.yaml_paths else DEFAULT_YAML_PATHS

    schema = _load_schema(schema_path)

    any_errors = False

    for yaml_path in yaml_paths:
        print("=" * 80)
        print(f"File: {yaml_path}")

        if not yaml_path.exists():
            print(f"ERROR: YAML not found: {yaml_path}")
            any_errors = True
            continue

        try:
            entries = _load_yaml_entries(yaml_path)
        except Exception as e:
            print(f"ERROR: failed to read/parse entries: {e}")
            any_errors = True
            continue

        # Missing-field report (always)
        missing_report = []
        for idx, entry in enumerate(entries):
            entry_id = entry.get("framework_id", f"entry#{idx}")
            missing = _collect_missing_fields(entry, schema)
            if missing:
                missing_report.append((idx, entry_id, missing))

        if missing_report:
            any_errors = True
            print("Missing required fields:")
            for idx, entry_id, missing in missing_report:
                print(f"  - [{idx}] {entry_id}:")
                for m in missing:
                    print(f"      * {m}")
        else:
            print("Missing required fields: none")

        # Full schema validation (optional)
        ok, schema_errors = _validate_with_jsonschema(entries, schema)
        if schema_errors:
            # if jsonschema unavailable, this is informational
            if ok:
                print("\nSchema validation note:")
            else:
                print("\nSchema validation errors:")
                any_errors = True
            for line in schema_errors:
                print(f"  - {line}")
        else:
            print("\nSchema validation: OK")

    print("=" * 80)
    return 1 if any_errors else 0


if __name__ == "__main__":
    raise SystemExit(main())

