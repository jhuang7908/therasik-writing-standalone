"""Re-render Smart-CMC console-style MD/HTML and audit MD from an existing
smart_cmc_result.json, optionally bumping version metadata (no recompute).

Use this when only `SMART_CMC_PROTOCOL_VERSION`, `SMART_CMC_ANALYSIS_VERSION`,
or `SMART_CMC_REPORT_FORMAT_VERSION` (or report layout) changed but the
underlying baseline / candidate / guard analysis is unchanged.
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

THIS = Path(__file__).resolve()
ROOT = THIS.parent.parent
sys.path.insert(0, str(ROOT))

from scripts.run_smart_cmc_orchestrator import (  # noqa: E402
    SMART_CMC_PROTOCOL_VERSION,
    SMART_CMC_ANALYSIS_VERSION,
    SMART_CMC_REPORT_FORMAT_VERSION,
    _render_md_report,
    _render_console_style_report,
    _render_console_style_html,
)


def rerender_one(drug_dir: Path, aligned_html_name: str | None = None,
                 bump_versions: bool = True) -> None:
    json_path = drug_dir / "smart_cmc_result.json"
    if not json_path.is_file():
        print(f"  [skip] {drug_dir.name}: smart_cmc_result.json not found")
        return

    payload = json.loads(json_path.read_text(encoding="utf-8"))
    payload.setdefault("display_name", drug_dir.name.replace("_", " "))
    versioning = payload.setdefault("versioning", {})

    if bump_versions:
        old = {k: versioning.get(k) for k in (
            "protocol_version", "analysis_version", "report_format_version")}
        versioning["protocol_version"] = SMART_CMC_PROTOCOL_VERSION
        versioning["analysis_version"] = SMART_CMC_ANALYSIS_VERSION
        versioning["report_format_version"] = SMART_CMC_REPORT_FORMAT_VERSION
        print(
            f"  [bump] {drug_dir.name}: "
            f"{old.get('protocol_version')}/{old.get('analysis_version')}/"
            f"{old.get('report_format_version')}"
            f"  ->  {SMART_CMC_PROTOCOL_VERSION}/{SMART_CMC_ANALYSIS_VERSION}/"
            f"{SMART_CMC_REPORT_FORMAT_VERSION}"
        )

    json_path.write_text(json.dumps(payload, indent=2, ensure_ascii=False),
                         encoding="utf-8")

    audit_path = drug_dir / "SMART_CMC_AUDIT.md"
    md_path = drug_dir / "SMART_CMC_WEB_CONSOLE_STYLE.md"
    html_path = drug_dir / "SMART_CMC_WEB_CONSOLE_STYLE.html"

    _render_md_report(audit_path, payload)
    _render_console_style_report(md_path, payload)
    _render_console_style_html(html_path, payload)

    if aligned_html_name:
        aligned = drug_dir / aligned_html_name
        aligned.write_text(html_path.read_text(encoding="utf-8"),
                           encoding="utf-8")
        print(f"  [aligned] {aligned.name}")

    print(f"  [ok] {drug_dir.name}: re-rendered audit + console MD + console HTML")


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--drug-dir", action="append", required=True,
                    help="Per-drug folder containing smart_cmc_result.json (repeatable)")
    ap.add_argument("--aligned-html-name", action="append", default=None,
                    help="Optional aligned-html name per drug-dir, in the same order")
    ap.add_argument("--no-bump", action="store_true",
                    help="Do not overwrite versioning fields; only re-render layout.")
    args = ap.parse_args()

    aligned = args.aligned_html_name or []
    pairs: list[tuple[Path, str | None]] = []
    for i, d in enumerate(args.drug_dir):
        ah = aligned[i] if i < len(aligned) else None
        pairs.append((Path(d), ah))

    print(f"Re-rendering with versions: protocol={SMART_CMC_PROTOCOL_VERSION} "
          f"analysis={SMART_CMC_ANALYSIS_VERSION} "
          f"report_format={SMART_CMC_REPORT_FORMAT_VERSION}")
    for path, ah in pairs:
        if not path.is_dir():
            print(f"  [skip] {path}: not a directory")
            continue
        rerender_one(path, aligned_html_name=ah, bump_versions=not args.no_bump)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
