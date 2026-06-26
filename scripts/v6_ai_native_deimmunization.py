#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
v6_ai_native_deimmunization.py

 V5 ，：

- VHH hallmark （QVQLV, SGGGLV, GWFR, WGQGT）

- ：hallmark_protected / patch_candidate / hotspot_no_sub

-  patch_candidate  patch

：

- projects/<project>/v5_deimmunization/result_v5.json

：

- projects/<project>/v6_ai_native/result_v6.json

- projects/<project>/v6_ai_native/result_v6_report.txt

：

    python scripts/v6_ai_native_deimmunization.py --project EGFR_7D12_VHH
"""

from __future__ import annotations

import argparse
import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Dict, List, Tuple


DEFAULT_BASE_DIR = Path(__file__).resolve().parent.parent


#  V5 
SUBSTITUTION_MAP: Dict[str, List[str]] = {
    "K": ["Q", "N", "R"],
    "R": ["K", "Q"],
    "E": ["Q", "N"],
    "D": ["N", "Q"],
    "W": ["Y", "F"],
    "Y": ["F", "W"],
    "F": ["Y", "W"],
    "H": ["Y", "N"],
    "P": ["A", "S"],
}


HALLMARK_MOTIFS = [
    "QVQLV",   # N-cap
    "SGGGLV",  # FR1 
    "GWFR",    # VHH FR2 hallmark
    "WGQGT",   # FR4 motif
]


@dataclass
class ClassifiedSuggestion:
    position: int
    aa_from: str
    category: str  # hallmark_protected / patch_candidate / hotspot_no_sub
    score: float
    strong_hits: int
    weak_hits: int
    to_candidates: List[str]
    rationale: str


# ---------------------------------------------------------------------------
# 
# ---------------------------------------------------------------------------

def _load_json(path: Path) -> Any:
    with path.open("r", encoding="utf-8") as f:
        return json.load(f)


def _save_json(path: Path, data: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)


def _find_hallmark_positions(sequence: str) -> Dict[str, List[int]]:
    """
     hallmark motifs， motif → （1-based）。
    """
    motif_pos: Dict[str, List[int]] = {}

    for motif in HALLMARK_MOTIFS:
        start = 0
        while True:
            idx = sequence.find(motif, start)
            if idx == -1:
                break
            start = idx + 1
            # 1-based positions
            positions = list(range(idx + 1, idx + 1 + len(motif)))
            motif_pos.setdefault(motif, []).extend(positions)

    return motif_pos


def _classify_suggestions_for_entry(entry: Dict[str, Any]) -> Tuple[List[ClassifiedSuggestion], Dict[str, List[int]]]:
    """
     entry（parent  v2） V5 suggestion ：

    - hallmark_protected

    - patch_candidate

    - hotspot_no_sub
    """
    seq: str = entry.get("sequence") or ""
    suggs = entry.get("suggestions") or []

    hallmark_pos_by_motif = _find_hallmark_positions(seq)
    hallmark_positions: set[int] = set()
    for plist in hallmark_pos_by_motif.values():
        hallmark_positions.update(plist)

    classified: List[ClassifiedSuggestion] = []

    for s in suggs:
        pos = int(s.get("position"))
        aa = (s.get("from") or "?").upper()
        score = float(s.get("score", 0.0))
        strong_hits = int(s.get("strong_hits", 0))
        weak_hits = int(s.get("weak_hits", 0))
        to_candidates = s.get("to_candidates") or []
        base_rationale = s.get("rationale") or ""

        if pos in hallmark_positions:
            category = "hallmark_protected"
            extra = " VHH hallmark motif （ QVQLV/SGGGLV/GWFR/WGQGT），。"

        elif aa in SUBSTITUTION_MAP and to_candidates:
            category = "patch_candidate"
            extra = " hallmark ，（/）， patch 。"

        else:
            category = "hotspot_no_sub"
            extra = "，，，。"

        rationale = base_rationale
        if rationale:
            rationale += "；" + extra
        else:
            rationale = extra

        classified.append(
            ClassifiedSuggestion(
                position=pos,
                aa_from=aa,
                category=category,
                score=score,
                strong_hits=strong_hits,
                weak_hits=weak_hits,
                to_candidates=to_candidates,
                rationale=rationale,
            )
        )

    # 
    classified.sort(key=lambda x: x.score, reverse=True)
    return classified, hallmark_pos_by_motif


def _build_patches(
    classified: List[ClassifiedSuggestion],
    max_patches: int = 3,
) -> List[Dict[str, Any]]:
    """
     patch_candidate  patch。
    """
    #  patch_candidate
    pcs = [c for c in classified if c.category == "patch_candidate"]
    if not pcs:
        return []

    # 
    pcs.sort(key=lambda x: x.position)

    patches: List[List[ClassifiedSuggestion]] = []
    current_group: List[ClassifiedSuggestion] = [pcs[0]]

    for c in pcs[1:]:
        prev = current_group[-1]
        if c.position - prev.position <= 1:
            current_group.append(c)
        else:
            patches.append(current_group)
            current_group = [c]
    if current_group:
        patches.append(current_group)

    #  patch 
    patches = patches[:max_patches]

    out_patches: List[Dict[str, Any]] = []
    for i, group in enumerate(patches, start=1):
        positions = [c.position for c in group]
        aas = "".join(c.aa_from for c in group)
        patch = {
            "patch_id": f"patch_{i}",
            "positions": positions,
            "from_aas": aas,
            "site_count": len(group),
            "sites": [
                {
                    "position": c.position,
                    "from": c.aa_from,
                    "to_candidates": c.to_candidates,
                    "score": c.score,
                    "strong_hits": c.strong_hits,
                    "weak_hits": c.weak_hits,
                    "rationale": c.rationale,
                }
                for c in group
            ],
            "summary": (
                "，，"
                " patch 。"
            ),
        }
        out_patches.append(patch)

    return out_patches


def run_v6_for_project(
    project: str,
    base_dir: Path,
) -> Dict[str, Any]:
    project_root = base_dir / "projects" / project
    v5_path = project_root / "v5_deimmunization" / "result_v5.json"
    if not v5_path.exists():
        raise FileNotFoundError(f"V5 ：{v5_path}")

    v5_data = _load_json(v5_path)
    entries = v5_data.get("entries") or []

    v6_entries: List[Dict[str, Any]] = []

    for e in entries:
        classified, hallmark_pos_by_motif = _classify_suggestions_for_entry(e)
        patches = _build_patches(classified)

        v6_entries.append(
            {
                "name": e.get("name", ""),
                "parent_id": e.get("parent_id", ""),
                "variant_type": e.get("variant_type", ""),
                "variant_name": e.get("variant_name", ""),
                "sequence_length": e.get("sequence_length", None),
                "hallmark_motifs": hallmark_pos_by_motif,
                "classified_suggestions": [
                    {
                        "position": c.position,
                        "from": c.aa_from,
                        "category": c.category,
                        "score": c.score,
                        "strong_hits": c.strong_hits,
                        "weak_hits": c.weak_hits,
                        "to_candidates": c.to_candidates,
                        "rationale": c.rationale,
                    }
                    for c in classified
                ],
                "patches": patches,
            }
        )

    v6_result = {
        "project": project,
        "source_v5": str(v5_path),
        "entries": v6_entries,
    }

    out_json = project_root / "v6_ai_native" / "result_v6.json"
    _save_json(out_json, v6_result)

    out_txt = project_root / "v6_ai_native" / "result_v6_report.txt"
    out_txt.parent.mkdir(parents=True, exist_ok=True)
    out_txt.write_text(_build_text_report(v6_result), encoding="utf-8")

    return {
        "json_path": out_json,
        "txt_path": out_txt,
        "entry_count": len(v6_entries),
    }


# ---------------------------------------------------------------------------
# 
# ---------------------------------------------------------------------------

def _build_text_report(v6: Dict[str, Any]) -> str:
    lines: List[str] = []
    lines.append("======================================================================")
    lines.append("V6 AI-native De-immunization Patches")
    lines.append("======================================================================")
    lines.append(f"Project: {v6.get('project','')}")
    lines.append("：")
    lines.append("  -  VHH hallmark （QVQLV, SGGGLV, GWFR, WGQGT）， hallmark_protected。")
    lines.append("  -  patch_candidate ， patch。")
    lines.append("  - ，。")
    lines.append("")

    for e in v6.get("entries") or []:
        lines.append("----------------------------------------------------------------------")
        lines.append(f"{e.get('name','')}  ({e.get('variant_type','')})")
        lines.append("----------------------------------------------------------------------")
        lines.append(f"Parent ID:       {e.get('parent_id','')}")
        if e.get("variant_type") == "v2_variant":
            lines.append(f"Variant name:    {e.get('variant_name','')}")
        lines.append(f"Sequence length: {e.get('sequence_length','?')} aa")
        lines.append("")

        # 
        cs = e.get("classified_suggestions") or []
        n_hall = sum(1 for c in cs if c.get("category") == "hallmark_protected")
        n_patch = sum(1 for c in cs if c.get("category") == "patch_candidate")
        n_hot = sum(1 for c in cs if c.get("category") == "hotspot_no_sub")
        lines.append(f"hallmark_protected : {n_hall}")
        lines.append(f"patch_candidate :    {n_patch}")
        lines.append(f"hotspot_no_sub :     {n_hot}")
        lines.append("")

        patches = e.get("patches") or []
        if not patches:
            lines.append(" patch 。")
            lines.append("")
            continue

        lines.append(f" {len(patches)}  patch：")
        for p in patches:
            lines.append(
                f"  - {p.get('patch_id')} | positions={p.get('positions')} | from={p.get('from_aas','')}"
            )
            lines.append(f"    {p.get('summary','')}")
            for s in p.get("sites") or []:
                lines.append(
                    f"    · Pos {s.get('position')} ({s.get('from')}) "
                    f"score={s.get('score',0.0):.2f}, strong_hits={s.get('strong_hits',0)}, "
                    f"weak_hits={s.get('weak_hits',0)}"
                )
                if s.get("to_candidates"):
                    lines.append(f"      → : {', '.join(s['to_candidates'])}")
                if s.get("rationale"):
                    lines.append(f"      : {s['rationale']}")
        lines.append("")

    lines.append("======================================================================")
    lines.append("End of V6 AI-native report.")
    lines.append("")
    return "\n".join(lines)


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------

def main():
    parser = argparse.ArgumentParser(
        description="Run V6 AI-native de-immunization patch design for a project."
    )
    parser.add_argument(
        "--project",
        "-p",
        required=True,
        help="， EGFR_7D12_VHH",
    )
    parser.add_argument(
        "--base-dir",
        "-b",
        default=str(DEFAULT_BASE_DIR),
        help="（：）",
    )
    args = parser.parse_args()
    base_dir = Path(args.base_dir).resolve()

    info = run_v6_for_project(project=args.project, base_dir=base_dir)

    print("========================================")
    print(" V6 AI-native  ")
    print("========================================")
    print(f"Project:   {args.project}")
    print(f"JSON out:  {info['json_path']}")
    print(f"TXT out:   {info['txt_path']}")
    print(f"Entries:   {info['entry_count']}")


if __name__ == "__main__":
    main()






















