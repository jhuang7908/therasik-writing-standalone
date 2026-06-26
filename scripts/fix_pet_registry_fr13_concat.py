"""
Patch malformed `fr1_3_concat` field in pet scaffold registries.

Bug (2026-04-29):
    Both cat and dog scaffold registries had `fr1_3_concat` rebuilt without
    FR2, so the field was FR1+FR3 (~54 aa) instead of FR1+FR2+FR3 (~70 aa).
    `select_candidate()` in `run_petization_pipeline.py` uses this field via
    `fast_identity`, which silently dropped reported FR identity for every
    cat scaffold by ~60 percentage points (e.g. real ~91% -> reported ~30%).
    That misrouted Tanezumab Track B to `surface_reshaping` when its
    biological FR identity actually exceeded the 65% graft threshold.

Fix:
    For every row with FR1, FR2 and FR3 strings present in `fr_segments`,
    rewrite `fr1_3_concat = FR1 + FR2 + FR3`. Bump registry version,
    refresh `built_at`, append a `notes` entry, and write a backup.

Owner instruction (2026-04-29): explicit user directive to fix.
"""
from __future__ import annotations

import json
import shutil
from datetime import datetime
from pathlib import Path
from typing import List, Tuple

REGISTRIES: List[Path] = [
    Path("data/germlines/felis_catus_ig_aa/cat_scaffold_cmc_optimization_tier1_tier2_v1.json"),
    Path("data/germlines/canis_lupus_familiaris_ig_aa/dog_scaffold_cmc_optimization_tier1_tier2_v1.json"),
]

PATCH_NOTE = (
    "[2026-04-29] fr1_3_concat patched: rebuilt as FR1+FR2+FR3 from fr_segments. "
    "Pre-patch field omitted FR2 (~14 aa) which deflated Track B FR identity "
    "scoring; petization auto-routing was therefore biased toward "
    "surface_reshaping. See docs/EVOLUTION_LOG.md."
)


def patch_registry(path: Path) -> Tuple[int, int]:
    if not path.exists():
        print(f"[skip] {path} not found")
        return 0, 0

    backup = path.with_suffix(path.suffix + f".bak_{datetime.utcnow().strftime('%Y%m%d_%H%M%S')}")
    shutil.copy2(path, backup)
    print(f"[backup] {backup.name}")

    reg = json.loads(path.read_text(encoding="utf-8"))
    rows = reg["rows"] if isinstance(reg, dict) and "rows" in reg else reg

    fixed = 0
    skipped = 0
    for r in rows:
        if not isinstance(r, dict):
            continue
        seg = r.get("fr_segments") or {}
        fr1, fr2, fr3 = seg.get("FR1", ""), seg.get("FR2", ""), seg.get("FR3", "")
        if not (fr1 and fr2 and fr3):
            skipped += 1
            continue
        expected = fr1 + fr2 + fr3
        if r.get("fr1_3_concat") != expected:
            r["fr1_3_concat"] = expected
            fixed += 1

    if isinstance(reg, dict):
        old_version = reg.get("version", "")
        if old_version and not old_version.endswith("+fr13fix"):
            new_version = old_version
            try:
                # bump patch component if version looks like vMAJOR.MINOR.PATCH
                parts = old_version.lstrip("v").split(".")
                if len(parts) == 3 and all(p.isdigit() for p in parts):
                    parts[-1] = str(int(parts[-1]) + 1)
                    new_version = ("v" if old_version.startswith("v") else "") + ".".join(parts)
            except Exception:
                pass
            reg["version"] = new_version
        reg["built_at"] = datetime.utcnow().isoformat() + "Z"
        notes = reg.get("notes")
        if isinstance(notes, list):
            notes.append(PATCH_NOTE)
        elif isinstance(notes, str):
            reg["notes"] = notes + "\n" + PATCH_NOTE
        else:
            reg["notes"] = PATCH_NOTE

    path.write_text(json.dumps(reg, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    print(f"[patched] {path.name}: fixed={fixed}, skipped(no_fr_segments)={skipped}")
    return fixed, skipped


def main() -> None:
    grand_fixed = 0
    grand_skipped = 0
    for path in REGISTRIES:
        f, s = patch_registry(path)
        grand_fixed += f
        grand_skipped += s
    print(f"\n[done] total rows fixed = {grand_fixed}; skipped (missing fr_segments) = {grand_skipped}")


if __name__ == "__main__":
    main()
