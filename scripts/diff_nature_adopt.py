#!/usr/bin/env python3
"""Diff vendor/nature-skills vs local insynbio-* skills for adopt tracking.

Usage:
  python scripts/diff_nature_adopt.py --update-vendor
  python scripts/diff_nature_adopt.py --report vendor/nature_skills_diff_report.json
  python scripts/diff_nature_adopt.py --markdown vendor/NATURE_ADOPT_DIFF.md
"""
from __future__ import annotations

import argparse
import json
import re
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
VENDOR = ROOT / "vendor" / "nature-skills"
VENDOR_SKILLS = VENDOR / "skills"
LOCAL_SKILLS = ROOT / ".cursor" / "skills"
ADOPTED_ROOT = ROOT / "vendor" / "adopted"
LOCK = ROOT / "vendor" / "nature_skills.lock.json"

# nature module → local skill dir(s)
NATURE_MAP: dict[str, list[str]] = {
    "nature-academic-search": ["insynbio-literature-search", "insynbio-citation"],
    "nature-writing": ["insynbio-polishing"],  # + ARS external
    "nature-polishing": ["insynbio-polishing"],
    "nature-reviewer": [],  # ARS academic-paper-reviewer (external)
    "nature-response": [],
    "nature-citation": ["insynbio-citation"],
    "nature-data": ["journal-submission-bundle"],
    "nature-figure": ["insynbio-figure"],
    "nature-reader": ["insynbio-paper-reader"],
    "nature-paper2ppt": ["insynbio-paper2ppt"],
    "nature-paper-to-patent": ["insynbio-paper-to-patent"],
}

EXTERNAL_NOTES = {
    "nature-writing": "~/.cursor/skills/academic-research-skills/academic-paper/",
    "nature-reviewer": "~/.cursor/skills/academic-research-skills/academic-paper-reviewer/",
    "nature-response": "~/.cursor/skills/academic-research-skills/journal-submission-prep/",
}


def _run(cmd: list[str], cwd: Path | None = None) -> subprocess.CompletedProcess:
    return subprocess.run(cmd, cwd=str(cwd or ROOT), capture_output=True, text=True)


def update_vendor() -> dict[str, str]:
    if not (VENDOR / ".git").exists():
        VENDOR.parent.mkdir(parents=True, exist_ok=True)
        r = _run(["git", "clone", "--depth", "1", "https://github.com/Yuan1z0825/nature-skills.git", str(VENDOR)])
        if r.returncode != 0:
            raise SystemExit(f"Clone failed: {r.stderr}")
    else:
        _run(["git", "fetch", "--depth", "1", "origin", "main"], cwd=VENDOR)
        _run(["git", "reset", "--hard", "origin/main"], cwd=VENDOR)
    rev = _run(["git", "rev-parse", "HEAD"], cwd=VENDOR)
    date = _run(["git", "log", "-1", "--format=%ci"], cwd=VENDOR)
    subj = _run(["git", "log", "-1", "--format=%s"], cwd=VENDOR)
    info = {
        "commit": rev.stdout.strip(),
        "committed_at": date.stdout.strip(),
        "subject": subj.stdout.strip(),
        "updated_at": datetime.now(timezone.utc).isoformat(),
        "url": "https://github.com/Yuan1z0825/nature-skills",
    }
    LOCK.write_text(json.dumps(info, indent=2), encoding="utf-8")
    print(f"Vendor updated: {info['commit'][:12]} — {info['subject']}")
    return info


def _parse_frontmatter(path: Path) -> dict[str, str]:
    if not path.exists():
        return {}
    text = path.read_text(encoding="utf-8", errors="replace")
    m = re.match(r"^---\s*\n(.*?)\n---", text, re.DOTALL)
    if not m:
        return {}
    out: dict[str, str] = {}
    for line in m.group(1).splitlines():
        if ":" in line:
            k, _, v = line.partition(":")
            out[k.strip()] = v.strip().strip('"')
    return out


def _read_yaml_version(manifest: Path) -> str | None:
    if not manifest.exists():
        return None
    for line in manifest.read_text(encoding="utf-8", errors="replace").splitlines():
        if line.strip().startswith("version:"):
            return line.split(":", 1)[1].strip().strip('"')
    return None


def _list_static_relpaths(skill_dir: Path) -> list[str]:
    static = skill_dir / "static"
    if not static.exists():
        return []
    return sorted(p.relative_to(static).as_posix() for p in static.rglob("*") if p.is_file())


def _parse_readme_index() -> dict[str, str]:
    readme = VENDOR / "README.md"
    statuses: dict[str, str] = {}
    if not readme.exists():
        return statuses
    for line in readme.read_text(encoding="utf-8", errors="replace").splitlines():
        m = re.match(r"\|\s*\[`(nature-[^`]+)`\].*\|\s*(\w+)\s*\|", line)
        if m:
            statuses[m.group(1)] = m.group(2)
    return statuses


def _vendor_commit() -> str:
    if LOCK.exists():
        return json.loads(LOCK.read_text(encoding="utf-8")).get("commit", "")[:12]
    if (VENDOR / ".git").exists():
        return _run(["git", "rev-parse", "HEAD"], cwd=VENDOR).stdout.strip()[:12]
    return "unknown"


def _adopt_banner(nature_module: str, relpath: str, commit: str) -> str:
    return (
        f"<!-- adopted from upstream {nature_module}/static/{relpath} @ {commit} -->\n"
        f"<!-- tracked mirror: vendor/adopted/ — local overlay in insynbio SKILL if needed -->\n\n"
    )


def mirror_module(nature_module: str, *, force: bool = False) -> dict[str, Any]:
    """Copy nature static/ into vendor/adopted/ and .cursor/skills/ targets."""
    if not VENDOR_SKILLS.exists():
        raise SystemExit(f"Missing vendor clone: {VENDOR}\nRun: python scripts/diff_nature_adopt.py --update-vendor")

    src_static = VENDOR_SKILLS / nature_module / "static"
    if not src_static.exists():
        raise SystemExit(f"No static/ in vendor module: {nature_module}")

    targets = NATURE_MAP.get(nature_module, [])
    if not targets:
        raise SystemExit(f"No NATURE_MAP entry for {nature_module}")

    commit = _vendor_commit()
    copied: list[str] = []
    skipped: list[str] = []

    for local_skill in targets:
        for skill_root in (ADOPTED_ROOT / local_skill, LOCAL_SKILLS / local_skill):
            dest_static = skill_root / "static"
            for src in sorted(src_static.rglob("*")):
                if not src.is_file():
                    continue
                rel = src.relative_to(src_static)
                dest = dest_static / rel
                if dest.exists() and not force:
                    skipped.append(f"{local_skill}:{rel.as_posix()}")
                    continue
                body = src.read_text(encoding="utf-8", errors="replace")
                banner = _adopt_banner(nature_module, rel.as_posix(), commit)
                if not body.startswith("<!-- adopted from upstream"):
                    body = banner + body
                dest.parent.mkdir(parents=True, exist_ok=True)
                dest.write_text(body, encoding="utf-8")
                copied.append(f"{skill_root.relative_to(ROOT)}/{rel.as_posix()}")

    summary = {
        "nature_module": nature_module,
        "vendor_commit": commit,
        "copied_count": len(copied),
        "skipped_count": len(skipped),
        "copied": copied,
        "skipped": skipped[:20],
    }
    print(f"Mirrored {nature_module}: {len(copied)} files written, {len(skipped)} skipped (use --force to overwrite)")
    return summary


def _local_skill_info(name: str) -> dict[str, Any]:
    d = LOCAL_SKILLS / name
    if not d.exists():
        return {"exists": False}
    return {
        "exists": True,
        "path": str(d.relative_to(ROOT)),
        "skill_version": _parse_frontmatter(d / "SKILL.md").get("version"),
        "manifest_version": _read_yaml_version(d / "manifest.yaml"),
        "static_files": _list_static_relpaths(d),
        "static_count": len(_list_static_relpaths(d)),
    }


def build_report() -> dict[str, Any]:
    if not VENDOR_SKILLS.exists():
        raise SystemExit(f"Missing vendor clone: {VENDOR}\nRun: python scripts/diff_nature_adopt.py --update-vendor")

    lock = json.loads(LOCK.read_text(encoding="utf-8")) if LOCK.exists() else {}
    readme_status = _parse_readme_index()

    nature_dirs = sorted(
        p.name for p in VENDOR_SKILLS.iterdir()
        if p.is_dir() and p.name.startswith("nature-")
    )
    extra_vendor = sorted(
        p.name for p in VENDOR_SKILLS.iterdir()
        if p.is_dir() and not p.name.startswith("nature-") and p.name != "_shared"
    )

    modules: list[dict[str, Any]] = []
    for name in nature_dirs:
        nd = VENDOR_SKILLS / name
        nature_static = _list_static_relpaths(nd)
        local_names = NATURE_MAP.get(name, [])
        local_infos = [_local_skill_info(n) for n in local_names]

        local_static: set[str] = set()
        for li in local_infos:
            if li.get("exists"):
                local_static.update(li.get("static_files", []))

        # Heuristic: nature static paths we don't have under any mapped local skill
        missing_local = [p for p in nature_static if p not in local_static]

        modules.append({
            "nature_module": name,
            "readme_status": readme_status.get(name),
            "nature_version": _read_yaml_version(nd / "manifest.yaml"),
            "nature_skill_version": _parse_frontmatter(nd / "SKILL.md").get("version"),
            "nature_static_count": len(nature_static),
            "local_skills": local_names,
            "local": local_infos,
            "external_note": EXTERNAL_NOTES.get(name),
            "static_gaps_vs_nature": missing_local[:40],
            "static_gap_count": len(missing_local),
        })

    local_only = sorted(
        p.name for p in LOCAL_SKILLS.iterdir()
        if p.is_dir() and p.name.startswith("insynbio-") and p.name not in {
            x for names in NATURE_MAP.values() for x in names
        }
    )

    return {
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "vendor_lock": lock,
        "vendor_commit": lock.get("commit") or _run(["git", "rev-parse", "HEAD"], cwd=VENDOR).stdout.strip(),
        "nature_module_count": len(nature_dirs),
        "extra_vendor_skills": extra_vendor,
        "insynbio_superset_skills": local_only + ["insynbio-rigor", "insynbio-therasik-suite", "insynbio-research-suite"],
        "modules": modules,
        "adopt_matrix": str(
            (ROOT / ".cursor/skills/insynbio-therasik-suite/static/core/nature-skills-adopt-matrix.md").relative_to(ROOT)
        ),
        "learn_protocol": str(
            (ROOT / ".cursor/skills/_shared/core/nature-skills-learn-protocol.md").relative_to(ROOT)
        ),
    }


def to_markdown(report: dict[str, Any]) -> str:
    lines = [
        "# nature-skills adopt diff",
        "",
        f"- Generated: {report['generated_at']}",
        f"- Vendor commit: `{report.get('vendor_commit', '')[:12]}`",
        f"- Lock: `vendor/nature_skills.lock.json`",
        "",
    ]
    if report.get("extra_vendor_skills"):
        lines.append(f"- **New vendor skills (not in our map):** {', '.join(report['extra_vendor_skills'])}")
        lines.append("")

    lines.extend(["## Modules", ""])
    for m in report["modules"]:
        lines.append(f"### `{m['nature_module']}` ({m.get('readme_status', '?')})")
        lines.append(f"- nature manifest: `{m.get('nature_version')}` · SKILL `{m.get('nature_skill_version')}`")
        lines.append(f"- nature static files: {m['nature_static_count']}")
        if m.get("local_skills"):
            for loc in m["local"]:
                if loc.get("exists"):
                    lines.append(
                        f"- local `{loc['path']}`: manifest `{loc.get('manifest_version')}` · "
                        f"static {loc.get('static_count')}"
                    )
                else:
                    lines.append(f"- local **MISSING** `{loc}`")
        if m.get("external_note"):
            lines.append(f"- external: `{m['external_note']}`")
        if m.get("static_gap_count", 0) > 0:
            lines.append(f"- **static gaps to review ({m['static_gap_count']}):**")
            for g in m.get("static_gaps_vs_nature", [])[:15]:
                lines.append(f"  - `{g}`")
            if m["static_gap_count"] > 15:
                lines.append(f"  - … +{m['static_gap_count'] - 15} more")
        lines.append("")

    lines.extend(["## InSynBio-only (no nature counterpart)", ""])
    for s in report.get("insynbio_superset_skills", []):
        lines.append(f"- `{s}`")
    lines.append("")
    return "\n".join(lines)


def main() -> None:
    ap = argparse.ArgumentParser(description="Diff nature-skills vendor vs insynbio skills")
    ap.add_argument("--update-vendor", action="store_true", help="git pull nature-skills into vendor/")
    ap.add_argument("--mirror", nargs="+", metavar="MODULE", help="Mirror static/ for nature module(s)")
    ap.add_argument("--force", action="store_true", help="Overwrite existing mirrored static files")
    ap.add_argument("--report", type=Path, help="Write JSON report")
    ap.add_argument("--markdown", type=Path, help="Write Markdown summary")
    args = ap.parse_args()

    if args.update_vendor:
        update_vendor()

    if args.mirror:
        for mod in args.mirror:
            name = mod if mod.startswith("nature-") else f"nature-{mod}"
            mirror_module(name, force=args.force)

    if not args.report and not args.markdown and not args.update_vendor and not args.mirror:
        ap.print_help()
        raise SystemExit(0)

    if args.report or args.markdown:
        report = build_report()
        if args.report:
            args.report.parent.mkdir(parents=True, exist_ok=True)
            args.report.write_text(json.dumps(report, indent=2, ensure_ascii=False), encoding="utf-8")
            print(f"JSON: {args.report}")
        if args.markdown:
            args.markdown.parent.mkdir(parents=True, exist_ok=True)
            args.markdown.write_text(to_markdown(report), encoding="utf-8")
            print(f"MD: {args.markdown}")


if __name__ == "__main__":
    main()
