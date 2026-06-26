#!/usr/bin/env python3
"""Citation SSOT — corpus build, DOI verify, RIS/RDF export (nature-citation parity)."""
from __future__ import annotations

import argparse
import importlib.util
import json
import re
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
DOI_RE = re.compile(r"\b(10\.\d{4,9}/[^\s\])>\"']+)", re.I)
DEFAULT_LIBRARY = (
    ROOT / "paper" / "Submission_Package" / "submission_internal" / "Literature_Library"
    / "Review_B_Reference_Library.json"
)
DEFAULT_RDF_OUT = (
    ROOT / "paper" / "Submission_Package" / "ScholarOne_Upload" / "Review_B_DeNovo"
    / "03_Literature" / "Review_B_Reference_Library.rdf"
)


def _load_library_builder():
    path = ROOT / "scripts" / "build_review_b_reference_library.py"
    spec = importlib.util.spec_from_file_location("build_review_b_reference_library", path)
    if spec is None or spec.loader is None:
        raise SystemExit(f"Cannot load {path}")
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def cmd_build_library(args: argparse.Namespace) -> int:
    script = ROOT / "scripts/build_review_b_reference_library.py"
    cmd = [sys.executable, str(script)]
    if args.manuscript:
        cmd.extend(["--manuscript", str(args.manuscript)])
    return subprocess.run(cmd, cwd=str(ROOT)).returncode


def cmd_extract_dois(args: argparse.Namespace) -> int:
    path = Path(args.input).resolve()
    text = path.read_text(encoding="utf-8")
    dois = sorted(set(DOI_RE.findall(text)))
    out = {"source": str(path), "count": len(dois), "dois": dois}
    if args.out:
        Path(args.out).write_text(json.dumps(out, indent=2), encoding="utf-8")
        print(f"DOIs: {args.out} (n={len(dois)})")
    else:
        print(json.dumps(out, indent=2))
    return 0


def cmd_verify(args: argparse.Namespace) -> int:
    verify_script = Path.home() / ".cursor/skills/academic-research-skills/journal-submission-prep/scripts/pubmed_verify.py"
    if not verify_script.exists():
        verify_script = ROOT / "scripts/pubmed_verify.py"
    if not verify_script.exists():
        raise SystemExit("pubmed_verify.py not found — install ARS journal-submission-prep skill")
    cmd = [sys.executable, str(verify_script), "--file", str(args.input)]
    if args.out:
        cmd.extend(["--out", str(args.out)])
    return subprocess.run(cmd, cwd=str(ROOT)).returncode


def cmd_export_zotero_rdf(args: argparse.Namespace) -> int:
    lib_path = Path(args.library or DEFAULT_LIBRARY).resolve()
    if not lib_path.exists():
        raise SystemExit(f"Library JSON not found: {lib_path}\nRun: python scripts/insynbio_citation.py build-library")
    lib = json.loads(lib_path.read_text(encoding="utf-8"))
    out = Path(args.out or DEFAULT_RDF_OUT).resolve()
    builder = _load_library_builder()
    builder.export_zotero_rdf(lib, out)
    print(f"Zotero RDF: {out} (n={len(lib.get('entries', []))})")
    return 0


def main() -> None:
    ap = argparse.ArgumentParser(description="InSynBio citation CLI")
    sub = ap.add_subparsers(dest="cmd", required=True)

    p_build = sub.add_parser("build-library", help="Build project reference library (Review B default)")
    p_build.add_argument("--manuscript", type=Path)
    p_build.set_defaults(func=cmd_build_library)

    p_doi = sub.add_parser("extract-dois", help="Extract DOIs from manuscript MD")
    p_doi.add_argument("--input", type=Path, required=True)
    p_doi.add_argument("--out", type=Path)
    p_doi.set_defaults(func=cmd_extract_dois)

    p_ver = sub.add_parser("verify", help="PubMed verify references in file")
    p_ver.add_argument("--input", type=Path, required=True)
    p_ver.add_argument("--out", type=Path)
    p_ver.set_defaults(func=cmd_verify)

    p_rdf = sub.add_parser("export-zotero-rdf", help="Export Review B library JSON to Zotero RDF")
    p_rdf.add_argument("--library", type=Path, help="Review_B_Reference_Library.json path")
    p_rdf.add_argument("--out", type=Path, help="Output .rdf path")
    p_rdf.set_defaults(func=cmd_export_zotero_rdf)

    args = ap.parse_args()
    raise SystemExit(args.func(args))


if __name__ == "__main__":
    main()
