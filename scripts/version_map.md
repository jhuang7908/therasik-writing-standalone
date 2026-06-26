# Script Version Map

Last updated: 2026-05-04
Scope: high-impact entry scripts and core runtime version contracts.

## Usage

- Use this file as a pre-release checklist.
- `Independent version` means the script/module declares its own semver.
- `Inherited standard` means the script version is governed by a standard document.
- `Drift status` should be `OK` unless script text and standard/version source disagree.

## Version Map

| Script / Module | Independent version | Inherited standard | Current value | Source of truth | Drift status |
| --- | --- | --- | --- | --- | --- |
| `scripts/run_vhh_engineering.py` | No | `docs/VHH_HUMANIZATION_DESIGN_STANDARD.md` + `docs/VH_TO_VHH_CONVERSION_STANDARD_V1.4.md` | VHH `V3.2`, VH->VHH `V1.7` | `docs/STANDARDS_INDEX.md` | OK |
| `api/routers/humanization.py` | No | `docs/VHH_HUMANIZATION_DESIGN_STANDARD.md` | `V3.2` | `docs/STANDARDS_INDEX.md` + router payload/report text | OK |
| `scripts/vhh_conversion_pipeline.py` | No | `docs/VH_TO_VHH_CONVERSION_STANDARD_V1.4.md` | `V1.7` | `docs/STANDARDS_INDEX.md` | OK |
| `scripts/run_bispecific_vhh_cmc.py` | Yes | `docs/BISPECIFIC_VHH_CMC_STANDARD.md` | CLI `v2.0.0`, standard `V1.0` | script header + standard | OK |
| `scripts/affinity_energy_cli.py` | No | `docs/VIRTUAL_AFFINITY_MATURATION_STANDARD.md` | `V1.5` | `docs/STANDARDS_INDEX.md` | OK |
| `scripts/run_vaccine_design.py` | Yes | `docs/VACCINE_DESIGN_STANDARD_V1.0.md` + `docs/NEOANTIGEN_SCANNER_STANDARD_V1.0.md` | CLI `1.0.0`, standards `V1.0` / `V1.0` | `CLI_VERSION` + standards | OK |
| `scripts/report_cli.py` | No | `docs/CURSOR_REPORT_ENGINE_V4_1_SPEC.md` | `V4.1` | `docs/STANDARDS_INDEX.md` | OK |
| `scripts/validate_website.py` | Yes | `WEBSITE_UPDATE_PROTOCOL.md` | script `v1.1`, protocol `V1.0` | script header + protocol | OK |
| `core/evaluation/evaluator.py` | Runtime contract field | `docs/CMC_DEVELOPABILITY_STANDARD_V1.1.md` | `abenginecore_version = 1.3.0` | evaluator output schema | OK |
| `core/__init__.py` | Yes | platform package version | `__version__ = 1.0.0` | package constant | OK |
| `core/vaccine_design/__init__.py` | Module-set versions | vaccine standards | `MODULE_VERSIONS` (1.0.x family) | module constants | OK |

## Fast Audit Commands

```powershell
# 1) Standard index baseline
python scripts/sync_standards_alignment.py --check

# 2) Runtime policy and module alignment
python scripts/check_runtime_alignment.py
python scripts/validate_pipeline_policy.py

# 3) Spot-check key version strings
python -c "import pathlib,re; p=pathlib.Path('scripts/run_bispecific_vhh_cmc.py'); print(re.findall(r'v\d+\.\d+\.\d+', p.read_text(encoding='utf-8'))[:3])"
python -c "import pathlib,re; p=pathlib.Path('scripts/validate_website.py'); print(re.findall(r'v\d+\.\d+', p.read_text(encoding='utf-8'))[:3])"
python -c "import pathlib,re; p=pathlib.Path('scripts/run_vaccine_design.py'); print(re.findall(r'CLI_VERSION\s*=\s*\"[0-9.]+\"', p.read_text(encoding='utf-8')))"
```

## Release Gate (Recommended)

- `PASS` all three checks: `sync_standards_alignment`, `check_runtime_alignment`, `validate_pipeline_policy`.
- Confirm no remaining `V2.4`/legacy text in active VHH runtime paths.
- Confirm VHH hallmark semantics remain: FR2 gate on `44/45/47`; IMGT `37` is display/context only.
