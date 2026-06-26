"""Validate every curated JSON file in journal_specs/ against its schema.

Also flags any field whose verification_status is 'unverified' or
'out_of_date' (informational, not a hard fail).

Usage:
    python -m services.writing_memory.journal_specs.validate
    # or
    python services/writing_memory/journal_specs/validate.py
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

import jsonschema


HERE = Path(__file__).resolve().parent
SPEC_SCHEMA = HERE / "submission_spec.schema.json"
STYLE_SCHEMA = HERE / "reference_style.schema.json"
SPECS_DIR = HERE / "specs"
STYLES_DIR = HERE / "reference_styles"


def _load_json(path: Path) -> dict:
    with path.open(encoding="utf-8") as fh:
        return json.load(fh)


def _walk_unverified(node, path: list[str]) -> list[str]:
    out: list[str] = []
    if isinstance(node, dict):
        # Field envelope?
        if "verification_status" in node and "value" in node:
            status = node.get("verification_status")
            if status in {"unverified", "out_of_date"}:
                out.append(".".join(path) + f" [{status}]")
            return out
        for k, v in node.items():
            out.extend(_walk_unverified(v, path + [k]))
    elif isinstance(node, list):
        for i, v in enumerate(node):
            out.extend(_walk_unverified(v, path + [f"[{i}]"]))
    return out


def main() -> int:
    rc = 0

    spec_schema = _load_json(SPEC_SCHEMA)
    style_schema = _load_json(STYLE_SCHEMA)
    jsonschema.Draft202012Validator.check_schema(spec_schema)
    jsonschema.Draft202012Validator.check_schema(style_schema)
    spec_validator = jsonschema.Draft202012Validator(spec_schema)
    style_validator = jsonschema.Draft202012Validator(style_schema)

    for spec_path in sorted(SPECS_DIR.glob("*.json")):
        spec = _load_json(spec_path)
        errors = list(spec_validator.iter_errors(spec))
        if errors:
            rc = 1
            print(f"[FAIL] {spec_path.relative_to(HERE)}")
            for e in errors[:5]:
                print("       ", "/".join(map(str, e.path)) or "<root>", "->", e.message)
        else:
            unv = _walk_unverified(spec, [])
            print(f"[ OK ] {spec_path.relative_to(HERE)}  (unverified={len(unv)})")
            for u in unv[:5]:
                print("        ", u)
            if len(unv) > 5:
                print(f"         ... +{len(unv) - 5} more")

    for style_path in sorted(STYLES_DIR.glob("*.json")):
        style = _load_json(style_path)
        errors = list(style_validator.iter_errors(style))
        if errors:
            rc = 1
            print(f"[FAIL] {style_path.relative_to(HERE)}")
            for e in errors[:5]:
                print("       ", "/".join(map(str, e.path)) or "<root>", "->", e.message)
        else:
            unv_blocks = [
                k for k in ("in_text_citation", "list_order", "list_entry")
                if style.get(k, {}).get("verification_status") != "verified"
            ]
            badge = "verified" if not unv_blocks else f"unverified: {','.join(unv_blocks)}"
            print(f"[ OK ] {style_path.relative_to(HERE)}  ({badge})")

    return rc


if __name__ == "__main__":
    sys.exit(main())
