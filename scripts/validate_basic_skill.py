from __future__ import annotations

import json
import re
import sys
from pathlib import Path

MIN_DESC_LEN = 40
MIN_REF_BYTES = 200


def main() -> int:
    if len(sys.argv) != 2:
        print("usage: validate_basic_skill.py <skill_dir>", file=sys.stderr)
        return 2

    skill_dir = Path(sys.argv[1]).resolve()
    errors: list[str] = []

    # SKILL.md structure
    skill_md = skill_dir / "SKILL.md"
    if not skill_md.exists():
        print("FAIL: missing SKILL.md")
        return 1

    text = skill_md.read_text(encoding="utf-8")
    if not text.startswith("---\n"):
        errors.append("SKILL.md missing YAML frontmatter start")
    else:
        parts = text.split("---", 2)
        if len(parts) < 3:
            errors.append("SKILL.md missing YAML frontmatter end")
        else:
            fm = parts[1]
            name_match = re.search(r"^name:\s*([a-z0-9-]+)\s*$", fm, re.M)
            desc_match = re.search(r"^description:\s*(.+?)\s*$", fm, re.M)
            if not name_match:
                errors.append("SKILL.md missing or invalid 'name' field")
            if not desc_match or len(desc_match.group(1).strip()) < MIN_DESC_LEN:
                errors.append("SKILL.md description too short (< 40 chars)")

    if "traffic light" not in text.lower() and "ai usage boundary" not in text.lower():
        errors.append("SKILL.md does not reference AI usage boundary (traffic light)")

    if "figure contract" not in text.lower():
        errors.append("SKILL.md does not mention figure contract")

    # Required references/ files with minimum content
    for ref in [
        "references/workflow.md",
        "references/qa-gates.md",
        "references/versioning.md",
        "references/case-learning.md",
        "references/mcp-roadmap.md",
    ]:
        path = skill_dir / ref
        if not path.exists():
            errors.append(f"Missing {ref}")
        elif len(path.read_bytes()) < MIN_REF_BYTES:
            errors.append(f"{ref} is a near-empty stub (< {MIN_REF_BYTES} bytes)")

    qa_gates = skill_dir / "references" / "qa-gates.md"
    if qa_gates.exists():
        qg = qa_gates.read_text(encoding="utf-8", errors="replace").lower()
        if "traffic light" not in qg and "green" not in qg:
            errors.append("references/qa-gates.md does not mention AI traffic light")
        if "figure contract" not in qg:
            errors.append("references/qa-gates.md does not mention figure contract")

    workflow_ref = skill_dir / "references" / "workflow.md"
    if workflow_ref.exists():
        wf = workflow_ref.read_text(encoding="utf-8", errors="replace").lower()
        if "figure contract" not in wf:
            errors.append("references/workflow.md does not mention figure contract")

    versioning_ref = skill_dir / "references" / "versioning.md"
    if versioning_ref.exists():
        vs = versioning_ref.read_text(encoding="utf-8", errors="replace").lower()
        if "lifecycle" not in vs:
            errors.append("references/versioning.md does not mention lifecycle states")

    # skill_version_manifest.json
    manifest_path = skill_dir / "skill_version_manifest.json"
    if not manifest_path.exists():
        errors.append("Missing skill_version_manifest.json")
    else:
        try:
            manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
            if "version" not in manifest:
                errors.append("skill_version_manifest.json missing 'version' field")
            if "lifecycle_state" not in manifest:
                errors.append("skill_version_manifest.json missing 'lifecycle_state' field")
        except json.JSONDecodeError as exc:
            errors.append(f"skill_version_manifest.json parse error: {exc}")

    # Required QA scripts
    for script in [
        "scripts/qa/run_reference_claim_qa.py",
        "scripts/qa/run_paragraph_structure_qa.py",
        "scripts/qa/run_ai_style_qa.py",
        "scripts/qa/run_figure_contract_qa.py",
    ]:
        if not (skill_dir / script).exists():
            errors.append(f"Missing QA script: {script}")

    # Orchestration scripts
    for script in ["scripts/run_full_workflow.py", "scripts/run_regression_tests.py"]:
        if not (skill_dir / script).exists():
            errors.append(f"Missing script: {script}")

    # project_config.json template
    config_path = skill_dir / "assets" / "project-template" / "project_config.json"
    if not config_path.exists():
        errors.append("Missing assets/project-template/project_config.json")
    else:
        try:
            cfg = json.loads(config_path.read_text(encoding="utf-8"))
            step_names = [s.get("name", "") for s in cfg.get("workflow_steps", [])]
            if "figure_contract_qa" not in step_names:
                errors.append("project_config.json workflow_steps missing 'figure_contract_qa'")
            gates = cfg.get("strict_release_artifacts", {})
            if "figure_contract_QA" not in gates:
                errors.append("project_config.json strict_release_artifacts missing 'figure_contract_QA'")
        except json.JSONDecodeError as exc:
            errors.append(f"project_config.json parse error: {exc}")

    if errors:
        for e in errors:
            print(f"FAIL: {e}")
        return 1

    print("PASS")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
