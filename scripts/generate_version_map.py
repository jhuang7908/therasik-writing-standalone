#!/usr/bin/env python3
"""
Generate scripts/version_map.md from live repository metadata.

Usage:
  python scripts/generate_version_map.py
"""

from __future__ import annotations

import re
from dataclasses import dataclass
from datetime import date
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
OUT_PATH = ROOT / "scripts" / "version_map.md"
STANDARDS_INDEX = ROOT / "docs" / "STANDARDS_INDEX.md"


def _read(path: Path) -> str:
    return path.read_text(encoding="utf-8")


def _extract_first(pattern: str, text: str, label: str) -> str:
    m = re.search(pattern, text, flags=re.MULTILINE)
    if not m:
        raise ValueError(f"Cannot extract {label} with pattern: {pattern}")
    return m.group(1)


def _standard_version(header_name: str) -> str:
    text = _read(STANDARDS_INDEX)
    pattern = rf"\*\*{re.escape(header_name)}\*\*.*?— (V[0-9]+\.[0-9]+)"
    return _extract_first(pattern, text, f"standard version for {header_name}")


def _script_semver(path: Path, pattern: str, label: str) -> str:
    text = _read(path)
    return _extract_first(pattern, text, label)


@dataclass
class Entry:
    script_or_module: str
    independent_version: str
    inherited_standard: str
    current_value: str
    source_of_truth: str
    drift_status: str = "OK"

    def to_row(self) -> str:
        return (
            f"| `{self.script_or_module}` | {self.independent_version} | "
            f"{self.inherited_standard} | {self.current_value} | "
            f"{self.source_of_truth} | {self.drift_status} |"
        )


def build_entries() -> list[Entry]:
    vhh_std = _standard_version("VHH Humanization Design Standard")
    vh2vhh_std = _standard_version("VH to VHH Conversion Standard")
    vam_std = _standard_version("Virtual Affinity Maturation Standard")
    report_std = _standard_version("Report Generation Standard")
    bispecific_std = _standard_version("Bispecific VHH CMC Assessment Standard")
    cmc_std = _standard_version("CMC Developability Assessment Standard")
    vaccine_std = _standard_version("Multi-Epitope Vaccine Design Standard")
    neo_std = _standard_version("NeoantigenScanner Standard")

    bispecific_cli_ver = _script_semver(
        ROOT / "scripts" / "run_bispecific_vhh_cmc.py",
        r"run_bispecific_vhh_cmc\.py\s+v([0-9]+\.[0-9]+\.[0-9]+)",
        "run_bispecific_vhh_cmc.py version",
    )
    website_cli_ver = _script_semver(
        ROOT / "scripts" / "validate_website.py",
        r"validate_website\.py\s+v([0-9]+\.[0-9]+)",
        "validate_website.py version",
    )
    vaccine_cli_ver = _script_semver(
        ROOT / "scripts" / "run_vaccine_design.py",
        r'CLI_VERSION\s*=\s*"([0-9]+\.[0-9]+\.[0-9]+)"',
        "run_vaccine_design.py CLI_VERSION",
    )
    abenginecore_pkg_ver = _script_semver(
        ROOT / "core" / "__init__.py",
        r'__version__\s*=\s*"([0-9]+\.[0-9]+\.[0-9]+)"',
        "core.__version__",
    )
    abeval_contract_ver = _script_semver(
        ROOT / "core" / "evaluation" / "evaluator.py",
        r'"abenginecore_version":\s*"([0-9]+\.[0-9]+\.[0-9]+)"',
        "AbEvaluator output contract version",
    )

    return [
        Entry(
            "scripts/run_vhh_engineering.py",
            "No",
            "`docs/VHH_HUMANIZATION_DESIGN_STANDARD.md` + `docs/VH_TO_VHH_CONVERSION_STANDARD_V1.4.md`",
            f"VHH `{vhh_std}`, VH->VHH `{vh2vhh_std}`",
            "`docs/STANDARDS_INDEX.md`",
        ),
        Entry(
            "api/routers/humanization.py",
            "No",
            "`docs/VHH_HUMANIZATION_DESIGN_STANDARD.md`",
            f"`{vhh_std}`",
            "`docs/STANDARDS_INDEX.md` + router payload/report text",
        ),
        Entry(
            "scripts/vhh_conversion_pipeline.py",
            "No",
            "`docs/VH_TO_VHH_CONVERSION_STANDARD_V1.4.md`",
            f"`{vh2vhh_std}`",
            "`docs/STANDARDS_INDEX.md`",
        ),
        Entry(
            "scripts/run_bispecific_vhh_cmc.py",
            "Yes",
            "`docs/BISPECIFIC_VHH_CMC_STANDARD.md`",
            f"CLI `v{bispecific_cli_ver}`, standard `{bispecific_std}`",
            "script header + standard",
        ),
        Entry(
            "scripts/affinity_energy_cli.py",
            "No",
            "`docs/VIRTUAL_AFFINITY_MATURATION_STANDARD.md`",
            f"`{vam_std}`",
            "`docs/STANDARDS_INDEX.md`",
        ),
        Entry(
            "scripts/run_vaccine_design.py",
            "Yes",
            "`docs/VACCINE_DESIGN_STANDARD_V1.0.md` + `docs/NEOANTIGEN_SCANNER_STANDARD_V1.0.md`",
            f"CLI `{vaccine_cli_ver}`, standards `{vaccine_std}` / `{neo_std}`",
            "`CLI_VERSION` + standards",
        ),
        Entry(
            "scripts/report_cli.py",
            "No",
            "`docs/CURSOR_REPORT_ENGINE_V4_1_SPEC.md`",
            f"`{report_std}`",
            "`docs/STANDARDS_INDEX.md`",
        ),
        Entry(
            "scripts/validate_website.py",
            "Yes",
            "`WEBSITE_UPDATE_PROTOCOL.md`",
            f"script `v{website_cli_ver}`, protocol `V1.0`",
            "script header + protocol",
        ),
        Entry(
            "core/evaluation/evaluator.py",
            "Runtime contract field",
            "`docs/CMC_DEVELOPABILITY_STANDARD_V1.1.md`",
            f"`abenginecore_version = {abeval_contract_ver}`",
            "evaluator output schema",
        ),
        Entry(
            "core/__init__.py",
            "Yes",
            "platform package version",
            f"`__version__ = {abenginecore_pkg_ver}`",
            "package constant",
        ),
        Entry(
            "core/vaccine_design/__init__.py",
            "Module-set versions",
            "vaccine standards",
            "`MODULE_VERSIONS` (1.0.x family)",
            "module constants",
        ),
    ]


def render(entries: list[Entry]) -> str:
    today = date.today().isoformat()
    rows = "\n".join(e.to_row() for e in entries)
    return f"""# Script Version Map

Last updated: {today}
Scope: high-impact entry scripts and core runtime version contracts.

## Usage

- Use this file as a pre-release checklist.
- `Independent version` means the script/module declares its own semver.
- `Inherited standard` means the script version is governed by a standard document.
- `Drift status` should be `OK` unless script text and standard/version source disagree.

## Version Map

| Script / Module | Independent version | Inherited standard | Current value | Source of truth | Drift status |
| --- | --- | --- | --- | --- | --- |
{rows}

## Fast Audit Commands

```powershell
# 1) Standard index baseline
python scripts/sync_standards_alignment.py --check

# 2) Runtime policy and module alignment
python scripts/check_runtime_alignment.py
python scripts/validate_pipeline_policy.py

# 3) Spot-check key version strings
python -c "import pathlib,re; p=pathlib.Path('scripts/run_bispecific_vhh_cmc.py'); print(re.findall(r'v\\d+\\.\\d+\\.\\d+', p.read_text(encoding='utf-8'))[:3])"
python -c "import pathlib,re; p=pathlib.Path('scripts/validate_website.py'); print(re.findall(r'v\\d+\\.\\d+', p.read_text(encoding='utf-8'))[:3])"
python -c "import pathlib,re; p=pathlib.Path('scripts/run_vaccine_design.py'); print(re.findall(r'CLI_VERSION\\s*=\\s*\\\"[0-9.]+\\\"', p.read_text(encoding='utf-8')))"
```

## Release Gate (Recommended)

- `PASS` all three checks: `sync_standards_alignment`, `check_runtime_alignment`, `validate_pipeline_policy`.
- Confirm no remaining `V2.4`/legacy text in active VHH runtime paths.
- Confirm VHH hallmark semantics remain: FR2 gate on `44/45/47`; IMGT `37` is display/context only.
"""


def main() -> None:
    entries = build_entries()
    content = render(entries)
    OUT_PATH.write_text(content, encoding="utf-8")
    print(f"Wrote {OUT_PATH.relative_to(ROOT)}")


if __name__ == "__main__":
    main()
