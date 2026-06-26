#!/usr/bin/env python3
"""Publication figure toolkit — DPI audit, TIFF export, project recipes."""
from __future__ import annotations

import argparse
import json
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def _figure_dpi(path: Path) -> tuple[int | None, int | None]:
    try:
        from PIL import Image
    except ImportError:
        return None, None
    try:
        with Image.open(path) as im:
            dpi = im.info.get("dpi") or (None, None)
            if isinstance(dpi, tuple) and len(dpi) >= 2:
                return int(dpi[0]), int(dpi[1])
    except Exception:
        pass
    return None, None


def cmd_audit(args: argparse.Namespace) -> int:
    paths = [Path(p).resolve() for p in args.paths]
    min_dpi = args.min_dpi
    rows: list[dict] = []
    fails = 0
    for p in paths:
        if not p.exists():
            rows.append({"path": str(p), "status": "FAIL", "reason": "missing"})
            fails += 1
            continue
        dx, dy = _figure_dpi(p)
        ok = dx is not None and dy is not None and dx >= min_dpi and dy >= min_dpi
        if p.suffix.lower() in {".svg", ".pdf", ".eps"} and dx is None:
            ok = True
            rows.append({"path": str(p), "status": "WARN", "reason": "vector — DPI not embedded", "dpi": None})
            continue
        status = "PASS" if ok else "FAIL"
        if status == "FAIL":
            fails += 1
        rows.append({"path": str(p), "status": status, "dpi": [dx, dy], "min_dpi": min_dpi})
    report = {
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "min_dpi": min_dpi,
        "overall": "FAIL" if fails else "PASS",
        "figures": rows,
    }
    out = Path(args.out).resolve() if args.out else None
    if out:
        out.parent.mkdir(parents=True, exist_ok=True)
        out.write_text(json.dumps(report, indent=2), encoding="utf-8")
        print(f"Audit: {out} ({report['overall']})")
    else:
        print(json.dumps(report, indent=2))
    return 1 if fails else 0


def cmd_png_to_tiff(args: argparse.Namespace) -> int:
    try:
        from PIL import Image
    except ImportError as e:
        raise SystemExit("Pillow required: pip install Pillow") from e
    src = Path(args.input).resolve()
    dst = Path(args.output).resolve()
    dst.parent.mkdir(parents=True, exist_ok=True)
    im = Image.open(src)
    if im.mode in ("RGBA", "P"):
        im = im.convert("RGB")
    im.save(dst, format="TIFF", compression="tiff_lzw", dpi=(args.dpi, args.dpi))
    print(f"TIFF: {dst} @ {args.dpi} dpi")
    return 0


def cmd_render_recipe(args: argparse.Namespace) -> int:
    recipe = args.recipe
    if recipe == "review_b_graphical_tables":
        script = (
            ROOT
            / "paper/Submission_Package/ScholarOne_Upload/Review_B_DeNovo/deck_ppt/render_graphical_tables.py"
        )
        if not script.exists():
            raise SystemExit(f"Missing recipe script: {script}")
        r = subprocess.run([sys.executable, str(script)], cwd=str(script.parent))
        return r.returncode
    raise SystemExit(f"Unknown recipe: {recipe}")


def cmd_stats(args: argparse.Namespace) -> int:
    """
    Route to chart-atlas stat recipes: forest | volcano | heatmap | stats-demo
    Each recipe delegates to core/figure/templates/*.py.
    """
    import importlib.util

    recipe = args.recipe
    template_dir = ROOT / "core" / "figure" / "templates"

    recipe_map = {
        "forest":    template_dir / "forest_plot.py",
        "volcano":   template_dir / "volcano_plot.py",
        "heatmap":   template_dir / "zscore_heatmap.py",
        "stats-demo": template_dir / "stats_annotator.py",
        "km":        template_dir / "km_plot.py",
        "legend":    template_dir / "figure_legend.py",
    }

    if recipe not in recipe_map:
        raise SystemExit(f"Unknown stats recipe: {recipe}. Available: {list(recipe_map)}")

    script_path = recipe_map[recipe]
    if not script_path.exists():
        raise SystemExit(f"Recipe script not found: {script_path}")

    # Load module and call main() with forwarded sys.argv
    spec = importlib.util.spec_from_file_location("_recipe", script_path)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)

    # Rebuild argv for the sub-script (strip 'stats --recipe X')
    sub_argv = []
    if recipe == "legend":
        # legend uses its own subcommand structure
        legend_spec = None
        for i, a in enumerate(args.extra or []):
            if a == "--legend-spec" and i + 1 < len(args.extra):
                legend_spec = args.extra[i + 1]
        sub_argv = ["generate",
                    "--legend-spec", legend_spec or "spec.json",
                    "--out", args.out or "figures/legend.md"]
        extra_clean = [a for a in (args.extra or []) if a not in ("--", "--legend-spec", legend_spec or "")]
        sub_argv += [a for a in extra_clean if a not in sub_argv]
    elif recipe == "stats-demo":
            sub_argv = ["--demo", "--out", args.out or "figures/stats_annotator_demo.svg"]
    else:
        if args.csv:
            sub_argv += ["--csv", args.csv]
        if args.out:
            sub_argv += ["--out", args.out]
        if args.title:
            sub_argv += ["--title", args.title]
        if args.double_column:
            sub_argv += ["--double-column"]
        if args.dpi:
            sub_argv += ["--dpi", str(args.dpi)]
        # Forward recipe-specific extras (strip leading '--' separator if present)
        for extra in (args.extra or []):
            if extra != "--":
                sub_argv.append(extra)

    import sys as _sys
    old_argv = _sys.argv
    _sys.argv = [str(script_path)] + sub_argv
    try:
        mod.main()
    finally:
        _sys.argv = old_argv
    return 0


def _run_comply(args: argparse.Namespace) -> int:
    script_map = {
        "at": ROOT / "scripts" / "at_figure_comply.py",
    }
    script = Path(args.script) if args.script else script_map.get(args.journal)
    if not script or not script.exists():
        raise SystemExit(f"Comply script not found: {script}")
    r = subprocess.run([sys.executable, str(script)], cwd=str(ROOT))
    return r.returncode


def cmd_concordance(args: argparse.Namespace) -> int:
    """
    Figure-text concordance checker.

    Scans a manuscript (.md or .txt) for figure/table citations and cross-checks against
    the set of actual figure files in the figures directory.

    Reports:
      - Cited in text but file missing (FAIL)
      - File exists but never cited in text (WARN)
      - Correctly cited and present (PASS)
    """
    import re as _re

    mpath = Path(args.manuscript)
    if mpath.suffix.lower() == ".docx":
        # Extract text from DOCX (XML-based ZIP) without python-docx dependency
        import zipfile
        import xml.etree.ElementTree as ET
        ns = "{http://schemas.openxmlformats.org/wordprocessingml/2006/main}"
        manuscript_text = ""
        try:
            with zipfile.ZipFile(mpath) as z:
                xml_content = z.read("word/document.xml")
            root = ET.fromstring(xml_content)
            parts = []
            for t in root.iter(f"{ns}t"):
                parts.append(t.text or "")
            manuscript_text = " ".join(parts)
        except Exception as e:
            print(f"[concordance] Could not parse DOCX: {e}", file=sys.stderr)
            return 1
    else:
        manuscript_text = mpath.read_text(encoding="utf-8", errors="replace")

    # Extract all figure/table references from text
    # Matches: Fig. 1, Figure 1, Fig 1A, Figures 1–3, Table 1, Supplementary Figure 1
    patterns = [
        r"(?:Fig(?:ure|s)?\.?\s*)(\d+[A-F]?)",       # Fig. 1, Figure 1A, Figs 1-3
        r"(?:Table\s*)(\d+)",                           # Table 1
        r"(?:Extended Data Fig(?:ure)?\.?\s*)(\d+)",    # Extended Data Figure 1
        r"(?:Supplementary Fig(?:ure)?\.?\s*)(\d+)",   # Supplementary Figure 1
    ]

    cited_refs: dict[str, set[str]] = {
        "Fig": set(), "Table": set(), "Extended": set(), "Supp": set(),
    }
    for pat, key in zip(patterns, ["Fig", "Table", "Extended", "Supp"]):
        for m in _re.finditer(pat, manuscript_text, _re.IGNORECASE):
            cited_refs[key].add(m.group(1))

    all_cited_labels: set[str] = set()
    for key, nums in cited_refs.items():
        for n in nums:
            all_cited_labels.add(f"{key}_{n}")

    # Discover actual figure files
    fig_dir = Path(args.figures_dir)
    IMG_EXTS = {".png", ".tif", ".tiff", ".jpg", ".jpeg", ".svg", ".pdf", ".eps"}
    found_files: dict[str, Path] = {}
    if fig_dir.exists():
        for f in sorted(fig_dir.rglob("*")):
            if f.suffix.lower() in IMG_EXTS:
                found_files[f.stem.lower()] = f

    # Attempt to match file names to figure labels
    # Convention: fig1.png, figure_1.png, figure1a.png, table_1.png, etc.
    def _infer_label(stem: str) -> str | None:
        stem = stem.lower()
        m = _re.match(r"(?:fig(?:ure)?_?s?)(\d+[a-f]?)", stem)
        if m:
            return f"Fig_{m.group(1).upper()}"
        m = _re.match(r"table_?(\d+)", stem)
        if m:
            return f"Table_{m.group(1)}"
        m = _re.match(r"(?:supp(?:lemental)?_?fig(?:ure)?_?)(\d+)", stem)
        if m:
            return f"Supp_{m.group(1)}"
        m = _re.match(r"(?:extended_?(?:data_?)?fig(?:ure)?_?)(\d+)", stem)
        if m:
            return f"Extended_{m.group(1)}"
        return None

    file_labels: dict[str, Path] = {}
    for stem, path in found_files.items():
        lbl = _infer_label(stem)
        if lbl:
            file_labels[lbl] = path

    # Cross-check
    cited_and_present = all_cited_labels & set(file_labels.keys())
    cited_missing = all_cited_labels - set(file_labels.keys())
    uncited_files = set(file_labels.keys()) - all_cited_labels

    rows: list[dict] = []
    for lbl in sorted(cited_and_present):
        rows.append({"label": lbl, "status": "PASS", "file": str(file_labels[lbl])})
    for lbl in sorted(cited_missing):
        rows.append({"label": lbl, "status": "FAIL", "reason": "Cited in text but no matching file found"})
    for lbl in sorted(uncited_files):
        rows.append({"label": lbl, "status": "WARN", "file": str(file_labels[lbl]),
                     "reason": "File exists but not cited in manuscript"})

    n_fail = sum(1 for r in rows if r["status"] == "FAIL")
    n_warn = sum(1 for r in rows if r["status"] == "WARN")
    overall = "FAIL" if n_fail else ("WARN" if n_warn else "PASS")

    print(f"\n[concordance] Manuscript: {args.manuscript}")
    print(f"[concordance] Figures dir: {args.figures_dir}")
    print(f"[concordance] Overall: {overall}  (PASS={len(cited_and_present)}, WARN={n_warn}, FAIL={n_fail})")

    if cited_missing:
        print("\n  ✗ CITED but file MISSING:")
        for lbl in sorted(cited_missing):
            print(f"    {lbl}")

    if uncited_files:
        print("\n  ⚠ FILE exists but NOT CITED in text:")
        for lbl in sorted(uncited_files):
            print(f"    {lbl}  ({file_labels[lbl].name})")

    if cited_and_present:
        print(f"\n  ✓ {len(cited_and_present)} figure(s)/table(s) correctly cited and present.")

    print()
    print("Tip: Text references matched using patterns: Fig./Figure/Table/Supp/Extended Data")
    print("     File names should follow: fig1.png / figure_2a.png / table_1.svg / supp_fig1.png")

    report = {
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "manuscript": str(args.manuscript),
        "figures_dir": str(args.figures_dir),
        "overall": overall,
        "pass": len(cited_and_present),
        "warn": n_warn,
        "fail": n_fail,
        "details": rows,
        "cited_refs_in_text": {k: sorted(v) for k, v in cited_refs.items() if v},
    }

    if args.out:
        out = Path(args.out)
        out.parent.mkdir(parents=True, exist_ok=True)
        out.write_text(json.dumps(report, indent=2, ensure_ascii=False), encoding="utf-8")
        print(f"[concordance] Report → {out}")

    return 1 if overall == "FAIL" else 0


def main() -> None:
    ap = argparse.ArgumentParser(description="InSynBio publication figure CLI")
    sub = ap.add_subparsers(dest="cmd", required=True)

    p_audit = sub.add_parser("audit", help="DPI audit for submission figures")
    p_audit.add_argument("paths", nargs="+", help="Figure files or directories")
    p_audit.add_argument("--min-dpi", type=int, default=300)
    p_audit.add_argument("--out", help="Write figure_audit.json")
    p_audit.set_defaults(func=cmd_audit)

    p_tiff = sub.add_parser("png-to-tiff", help="Convert PNG to 300 dpi TIFF for upload")
    p_tiff.add_argument("--input", required=True)
    p_tiff.add_argument("--output", required=True)
    p_tiff.add_argument("--dpi", type=int, default=300)
    p_tiff.set_defaults(func=cmd_png_to_tiff)

    p_rec = sub.add_parser("render-recipe", help="Run bundled figure recipe")
    p_rec.add_argument("--recipe", required=True, choices=["review_b_graphical_tables"])
    p_rec.set_defaults(func=cmd_render_recipe)

    # chart-atlas stat recipes (forest | volcano | heatmap | stats-demo)
    p_stats = sub.add_parser("stats", help="Chart-atlas stat recipes (forest/volcano/heatmap/stats-demo/km/legend)")
    p_stats.add_argument("--recipe", required=True,
                         choices=["forest", "volcano", "heatmap", "stats-demo", "km", "legend"],
                         help="forest | volcano | heatmap | stats-demo | km=KM survival | legend=figure legend")
    p_stats.add_argument("--csv", default=None, help="Input CSV file")
    p_stats.add_argument("--out", default=None, help="Output path (.svg/.pdf/.tiff/.png)")
    p_stats.add_argument("--title", default="", help="Figure title")
    p_stats.add_argument("--double-column", action="store_true", help="17.4 cm width (2-column journals)")
    p_stats.add_argument("--dpi", type=int, default=300)
    p_stats.add_argument("extra", nargs=argparse.REMAINDER,
                         help="Recipe-specific extra args (e.g. -- --fc-thresh 1.0 --p-thresh 0.05)")
    p_stats.set_defaults(func=cmd_stats)

    p_comply = sub.add_parser("comply", help="Convert figures to journal format spec (OUP AT default)")
    p_comply.add_argument("--journal", default="at", choices=["at"],
                          help="Journal preset: at=Antibody Therapeutics (OUP)")
    p_comply.add_argument("--script", default=None,
                          help="Override comply script (default: scripts/at_figure_comply.py)")
    p_comply.set_defaults(func=lambda a: _run_comply(a))

    p_conc = sub.add_parser("concordance",
                             help="Cross-check figure citations in text vs. actual figure files")
    p_conc.add_argument("--manuscript", required=True,
                        help="Manuscript file (.md or .txt)")
    p_conc.add_argument("--figures-dir", default="paper/figures",
                        help="Directory containing figure files (default: paper/figures)")
    p_conc.add_argument("--out", default=None, help="Write concordance report JSON")
    p_conc.set_defaults(func=cmd_concordance)

    args = ap.parse_args()
    if args.cmd == "audit":
        expanded: list[str] = []
        for p in args.paths:
            path = Path(p)
            if path.is_dir():
                expanded.extend(str(f) for f in path.rglob("*") if f.suffix.lower() in {".png", ".tif", ".tiff", ".jpg", ".jpeg", ".svg", ".pdf"})
            else:
                expanded.append(str(path))
        args.paths = expanded or args.paths
    raise SystemExit(args.func(args))


if __name__ == "__main__":
    main()
