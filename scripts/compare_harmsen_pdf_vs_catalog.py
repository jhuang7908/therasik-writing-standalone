#!/usr/bin/env python3
"""
： pypdf  PDF  Supplementary Figure 1 ，
data/reference/.../catalog.json 。

：PDF  token（ TWSW、FWGQG），
      “”， spaced_to_seq
      （）。

:
  python scripts/compare_harmsen_pdf_vs_catalog.py [Data Sheet 1.pdf]
"""
from __future__ import annotations

import json
import re
import sys
from datetime import datetime, timezone
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]
CATALOG = REPO / "data/reference/harmsen_2024_cross_species_sdabs/v1/catalog.json"
REPORT = REPO / "data/reference/harmsen_2024_cross_species_sdabs/v1/validation_pdf_extract_vs_catalog.json"
DEFAULT_PDF = Path.home() / "Downloads" / "Data Sheet 1.pdf"

AA = frozenset("ACDEFGHIKLMNPQRSTVWY")

# C-terminal peptide tails in Supplementary Fig.1 (after VTVSS…); catalog stores VHH only.
_HINGE_SUFFIXES = ("AHHSEDPSS", "EPKIPQPQP", "GTNEV")


def trim_peptide_hinge(full_aa: str) -> tuple[str, str | None]:
    """Remove known hinge/tail after FR4 if present (PDF line includes this column)."""
    for h in sorted(_HINGE_SUFFIXES, key=len, reverse=True):
        if full_aa.endswith(h):
            return full_aa[: -len(h)], h
    return full_aa, None


def spaced_to_seq(parts: str) -> str:
    """Same rule as parse_supplement_spaced_vhh.spaced_row_to_seq."""
    out: list[str] = []
    for p in parts.split():
        if p in ("-", "–"):
            continue
        pu = p.upper().strip()
        if not pu:
            continue
        if pu == "X" or all(c in AA for c in pu):
            out.extend(list(pu))
    return "".join(out)


def load_pdf_text(path: Path) -> str:
    from pypdf import PdfReader

    reader = PdfReader(str(path))
    return "\n".join(page.extract_text() or "" for page in reader.pages)


def extract_clone_lines(text: str) -> dict[str, str]:
    """Map clone_id -> raw spaced segment (PDF text as extracted)."""
    rows: dict[str, str] = {}
    pat = re.compile(
        r"^(?P<id>G\d+|A\d+|sdAb-\d+)\s+[01C]\s+(?P<seq>.+)$",
        re.MULTILINE,
    )
    for m in pat.finditer(text):
        rows[m.group("id")] = m.group("seq").strip()
    return rows


def main() -> int:
    pdf_path = Path(sys.argv[1]) if len(sys.argv) > 1 else DEFAULT_PDF
    if not pdf_path.is_file():
        print(f"PDF not found: {pdf_path}", file=sys.stderr)
        return 2

    catalog = json.loads(CATALOG.read_text(encoding="utf-8"))
    stored = catalog["sequences_supplementary_figure1"]

    raw_text = load_pdf_text(pdf_path)
    spaced_by_clone = extract_clone_lines(raw_text)
    pdf_linear_full = {k: spaced_to_seq(v) for k, v in spaced_by_clone.items()}
    pdf_linear: dict[str, str] = {}
    hinge_stripped: dict[str, str | None] = {}
    for k, seq in pdf_linear_full.items():
        trimmed, hinge = trim_peptide_hinge(seq)
        pdf_linear[k] = trimmed
        if hinge:
            hinge_stripped[k] = hinge

    mismatches: list[dict] = []
    missing: list[str] = []
    ok: list[str] = []

    for clone in sorted(stored.keys()):
        if clone not in pdf_linear:
            missing.append(clone)
            continue
        if stored[clone] == pdf_linear[clone]:
            ok.append(clone)
        else:
            sa, sb = stored[clone], pdf_linear[clone]
            diff_at = None
            for i, (a, b) in enumerate(zip(sa, sb)):
                if a != b:
                    diff_at = {"position": i, "catalog": a, "pdf": b}
                    break
            if diff_at is None and len(sa) != len(sb):
                diff_at = {"position": min(len(sa), len(sb)), "note": "length_mismatch"}
            mismatches.append(
                {
                    "clone": clone,
                    "catalog_len": len(sa),
                    "pdf_len": len(sb),
                    "first_diff": diff_at,
                }
            )

    extra = sorted(set(pdf_linear.keys()) - set(stored.keys()))

    report = {
        "validated_at": datetime.now(timezone.utc).isoformat(),
        "pdf_path": str(pdf_path.resolve()),
        "catalog_path": str(CATALOG.relative_to(REPO)).replace("\\", "/"),
        "method_note": (
            "pypdf text layer → regex clone rows → spaced_to_seq (multi-AA tokens expanded). "
            "Trailing hinge peptides (AHHSEDPSS / EPKIPQPQP / GTNEV) stripped before compare "
            "because catalog stores VHH only."
        ),
        "pdf_regex_rows": len(spaced_by_clone),
        "catalog_clones": len(stored),
        "hinge_removed_from_pdf_extract": hinge_stripped,
        "identical_count": len(ok),
        "mismatch_count": len(mismatches),
        "missing_in_pdf_extract": missing,
        "extra_clone_ids_in_pdf": extra,
        "mismatches": mismatches,
        "summary": (
            "PASS: PDF second extraction matches catalog for all clones."
            if not mismatches and not missing
            else "REVIEW: see missing/mismatches."
        ),
    }

    REPORT.parent.mkdir(parents=True, exist_ok=True)
    REPORT.write_text(json.dumps(report, indent=2, ensure_ascii=False), encoding="utf-8")

    print(json.dumps(report, indent=2, ensure_ascii=False))
    print(f"\nReport written: {REPORT}")

    return 0 if not mismatches and not missing else 1


if __name__ == "__main__":
    raise SystemExit(main())
