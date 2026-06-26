#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
v5_deimmunization_suggestions.py

 V3 + V4 ， parent  v2 
"FR-only "。

：
- v3_immunogenicity/result_v3.json :  HLA （start/end/peptide/rank）
- v4_cluster/result_v4.json        :  cluster + motif 

：
- projects/<project>/v5_deimmunization/result_v5.json
- projects/<project>/v5_deimmunization/result_v5_report.txt

：
    python scripts/v5_deimmunization_suggestions.py --project EGFR_7D12_VHH

：
    --top-positions     （ 10）
    --strong-threshold   binder （ 2.0）
    --weak-threshold     binder （ 10.0）

：
-  FR/CDR ，" CDR"。
   CDR 。
"""

from __future__ import annotations

import argparse
import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple


DEFAULT_BASE_DIR = Path(__file__).resolve().parent.parent


# ---------------------------------------------------------------------------
# 
# ---------------------------------------------------------------------------

@dataclass
class Prediction:
    allele: str
    start: int
    end: int
    peptide: str
    rank: float


@dataclass
class PositionScore:
    position: int
    score: float
    strong_hits: int
    weak_hits: int


# （）
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


def _get_int(row: Dict[str, Any], *keys: str) -> Optional[int]:
    for k in keys:
        if k in row:
            try:
                return int(row[k])
            except Exception:
                continue
    return None


def _get_float(row: Dict[str, Any], *keys: str) -> Optional[float]:
    for k in keys:
        if k in row:
            try:
                return float(row[k])
            except Exception:
                continue
    return None


def _normalize_predictions(pred_block: Dict[str, Any]) -> List[Prediction]:
    """
     V3  hla_binding_predictions ， Prediction 。
    。
    """
    preds_raw = (
        pred_block.get("hla_binding_predictions")
        or pred_block.get("predictions")
        or []
    )
    norm: List[Prediction] = []

    for row in preds_raw:
        peptide = row.get("peptide") or row.get("Peptide") or ""
        allele = row.get("allele") or row.get("Allele") or ""
        start = _get_int(row, "start", "start_position", "Start")
        end = _get_int(row, "end", "end_position", "End")
        rank = _get_float(row, "rank", "percentile_rank", "%Rank", "%Rank_IEDB")

        if not peptide or start is None or end is None or rank is None:
            continue

        norm.append(
            Prediction(
                allele=allele,
                start=start,
                end=end,
                peptide=peptide,
                rank=rank,
            )
        )
    return norm


def _build_position_scores(
    preds: List[Prediction],
    seq_len: int,
    strong_threshold: float,
    weak_threshold: float,
) -> Dict[int, PositionScore]:
    """
    ：
    - rank ，（ 1/rank ）
    - strong / weak 
    """
    scores: Dict[int, PositionScore] = {
        i: PositionScore(position=i, score=0.0, strong_hits=0, weak_hits=0)
        for i in range(1, seq_len + 1)
    }

    for p in preds:
        if p.rank > weak_threshold:
            continue
        weight = 1.0 / max(p.rank, 1e-3)  #  rank=0
        is_strong = p.rank <= strong_threshold

        for pos in range(p.start, p.end + 1):
            if pos not in scores:
                continue
            ps = scores[pos]
            ps.score += weight
            if is_strong:
                ps.strong_hits += 1
            else:
                ps.weak_hits += 1

    # 
    scores = {pos: ps for pos, ps in scores.items() if ps.score > 0.0}
    return scores


def _find_covering_clusters(
    clusters: List[Dict[str, Any]],
    position: int,
) -> List[Dict[str, Any]]:
    """ position  cluster."""
    hits: List[Dict[str, Any]] = []
    for c in clusters:
        start = int(c.get("start", 0))
        end = int(c.get("end", 0))
        if start <= position <= end:
            hits.append(c)
    return hits


def _suggest_substitutions(residue: str) -> List[str]:
    """。"""
    return SUBSTITUTION_MAP.get(residue.upper(), [])


# ---------------------------------------------------------------------------
# ：
# ---------------------------------------------------------------------------

def _build_entry_key(entry: Dict[str, Any]) -> Tuple[str, str]:
    """
     V4 entry  V3  key：
    - parent: (parent_id, "parent")
    - v2:     (parent_id, variant_name)
    """
    parent_id = entry.get("parent_id") or entry.get("name") or "parent"
    if entry.get("variant_type") == "v2_variant":
        vname = entry.get("variant_name") or "v2"
    else:
        vname = "parent"
    return parent_id, vname


def _index_v3_variants(v3_data: Dict[str, Any]) -> Dict[Tuple[str, str], Dict[str, Any]]:
    """
     V3 ： (parent_id, variant_name) → {sequence, analysis_block}
    - parent  variant_name="parent"
    - v2  v2_name
    """
    index: Dict[Tuple[str, str], Dict[str, Any]] = {}
    variants = v3_data.get("variants") or v3_data.get("parents") or []

    for var in variants:
        parent_id = var.get("parent_id") or var.get("name") or "parent"

        # parent
        parent_seq = var.get("parent_sequence") or ""
        parent_analysis = var.get("parent_analysis") or {}
        index[(parent_id, "parent")] = {
            "sequence": parent_seq,
            "analysis": parent_analysis,
        }

        # v2 
        v2_block = var.get("v2_variants_analysis") or var.get("v2_variants") or {}
        for v2_name, v2_info in v2_block.items():
            seq = v2_info.get("sequence") or ""
            analysis = v2_info.get("immunogenicity") or v2_info.get("analysis") or v2_info
            index[(parent_id, v2_name)] = {
                "sequence": seq,
                "analysis": analysis,
            }

    return index


def _build_suggestions_for_entry(
    v4_entry: Dict[str, Any],
    v3_index: Dict[Tuple[str, str], Dict[str, Any]],
    strong_threshold: float,
    weak_threshold: float,
    top_positions: int,
) -> Dict[str, Any]:
    """
     entry（parent  v2 ）。
    """
    key = _build_entry_key(v4_entry)
    v3_entry = v3_index.get(key)
    if v3_entry is None:
        return {
            "name": v4_entry.get("name", ""),
            "parent_id": v4_entry.get("parent_id", ""),
            "variant_type": v4_entry.get("variant_type", ""),
            "variant_name": v4_entry.get("variant_name", ""),
            "sequence": None,
            "sequence_length": v4_entry.get("sequence_length", None),
            "suggestions": [],
            "notes": " V3 ，。",
        }

    sequence: str = v3_entry.get("sequence", "")
    seq_len = len(sequence)
    analysis_block = v3_entry.get("analysis", {})

    preds = _normalize_predictions(analysis_block)
    pos_scores = _build_position_scores(preds, seq_len, strong_threshold, weak_threshold)

    if not pos_scores:
        return {
            "name": v4_entry.get("name", ""),
            "parent_id": v4_entry.get("parent_id", ""),
            "variant_type": v4_entry.get("variant_type", ""),
            "variant_name": v4_entry.get("variant_name", ""),
            "sequence": sequence,
            "sequence_length": seq_len,
            "suggestions": [],
            "notes": " strong/weak 。",
        }

    #  score ， top_positions 
    ranked = sorted(
        pos_scores.values(),
        key=lambda ps: ps.score,
        reverse=True,
    )[:top_positions]

    clusters = v4_entry.get("clusters") or []
    suggestions: List[Dict[str, Any]] = []

    for rank_idx, ps in enumerate(ranked, start=1):
        pos = ps.position
        #  0-based index， 1-based
        aa = sequence[pos - 1] if 1 <= pos <= seq_len else "?"
        subs = _suggest_substitutions(aa)
        covering_clusters = _find_covering_clusters(clusters, pos)

        rationale_parts = [
            f" {pos}（{aa}） MHC-II ",
            f" = {ps.score:.2f}",
        ]
        if ps.strong_hits > 0:
            rationale_parts.append(f" strong binder  {ps.strong_hits} ")
        if covering_clusters:
            # "" cluster 
            worst = min(
                covering_clusters,
                key=lambda c: float(c.get("min_rank", 999.0)),
            )
            rationale_parts.append(
                f" cluster  [{worst.get('start','?')}-{worst.get('end','?')}], "
                f"min_rank = {worst.get('min_rank','?'):.2f}, "
                f"allele_count = {worst.get('allele_count',0)}"
            )

        if not subs:
            rationale_parts.append(
                "，。"
            )
        else:
            rationale_parts.append(
                f"：{', '.join(subs)}（ FR ）。"
            )

        suggestions.append(
            {
                "position": pos,
                "from": aa,
                "to_candidates": subs,
                "score": ps.score,
                "strong_hits": ps.strong_hits,
                "weak_hits": ps.weak_hits,
                "relative_rank": rank_idx,
                "covering_clusters": covering_clusters,
                "rationale": "；".join(rationale_parts),
            }
        )

    return {
        "name": v4_entry.get("name", ""),
        "parent_id": v4_entry.get("parent_id", ""),
        "variant_type": v4_entry.get("variant_type", ""),
        "variant_name": v4_entry.get("variant_name", ""),
        "sequence": sequence,
        "sequence_length": seq_len,
        "strong_threshold": strong_threshold,
        "weak_threshold": weak_threshold,
        "top_positions": top_positions,
        "suggestions": suggestions,
        "notes": "",
    }


def run_v5_for_project(
    project: str,
    base_dir: Path,
    strong_threshold: float,
    weak_threshold: float,
    top_positions: int,
) -> Dict[str, Any]:
    """
    ： project 。
    """
    project_root = base_dir / "projects" / project
    v3_path = project_root / "v3_immunogenicity" / "result_v3.json"
    v4_path = project_root / "v4_cluster" / "result_v4.json"

    if not v3_path.exists():
        raise FileNotFoundError(f"V3 ：{v3_path}")
    if not v4_path.exists():
        raise FileNotFoundError(f"V4 ：{v4_path}")

    v3_data = _load_json(v3_path)
    v4_data = _load_json(v4_path)

    v3_index = _index_v3_variants(v3_data)
    v4_entries = v4_data.get("entries") or []

    out_entries: List[Dict[str, Any]] = []
    for e in v4_entries:
        out_entries.append(
            _build_suggestions_for_entry(
                e,
                v3_index=v3_index,
                strong_threshold=strong_threshold,
                weak_threshold=weak_threshold,
                top_positions=top_positions,
            )
        )

    result_v5 = {
        "project": project,
        "source_v3": str(v3_path),
        "source_v4": str(v4_path),
        "strong_threshold": strong_threshold,
        "weak_threshold": weak_threshold,
        "top_positions": top_positions,
        "entries": out_entries,
    }

    out_json = project_root / "v5_deimmunization" / "result_v5.json"
    _save_json(out_json, result_v5)

    out_txt = project_root / "v5_deimmunization" / "result_v5_report.txt"
    out_txt.parent.mkdir(parents=True, exist_ok=True)
    out_txt.write_text(_build_text_report(result_v5), encoding="utf-8")

    return {
        "json_path": out_json,
        "txt_path": out_txt,
        "entry_count": len(out_entries),
    }


# ---------------------------------------------------------------------------
# 
# ---------------------------------------------------------------------------

def _build_text_report(v5: Dict[str, Any]) -> str:
    lines: List[str] = []
    lines.append("======================================================================")
    lines.append("V5 De-immunization Site Suggestions")
    lines.append("======================================================================")
    lines.append(f"Project: {v5.get('project','')}")
    lines.append(f"Strong binder threshold (rank ≤): {v5.get('strong_threshold')}")
    lines.append(f"Weak binder threshold (rank ≤):   {v5.get('weak_threshold')}")
    lines.append(f"Top positions per entry:           {v5.get('top_positions')}")
    lines.append("")

    entries = v5.get("entries") or []

    for e in entries:
        lines.append("----------------------------------------------------------------------")
        lines.append(f"{e.get('name','')}  ({e.get('variant_type','')})")
        lines.append("----------------------------------------------------------------------")
        lines.append(f"Parent ID:       {e.get('parent_id','')}")
        if e.get("variant_type") == "v2_variant":
            lines.append(f"Variant name:    {e.get('variant_name','')}")
        lines.append(f"Sequence length: {e.get('sequence_length','?')} aa")
        lines.append(f"Strong threshold: rank ≤ {e.get('strong_threshold','?')}")
        lines.append(f"Weak threshold:   rank ≤ {e.get('weak_threshold','?')}")
        if e.get("notes"):
            lines.append(f"Notes: {e['notes']}")
            lines.append("")
            continue

        suggs = e.get("suggestions") or []
        lines.append(f"Suggested positions: {len(suggs)}")
        if not suggs:
            lines.append("  (No high-pressure positions detected under current thresholds.)")
            lines.append("")
            continue

        for s in suggs:
            pos = s.get("position")
            aa_from = s.get("from")
            subs = s.get("to_candidates") or []
            score = s.get("score", 0.0)
            strong_hits = s.get("strong_hits", 0)
            weak_hits = s.get("weak_hits", 0)
            lines.append(
                f"  - Pos {pos} ({aa_from}) | "
                f"score={score:.2f}, strong_hits={strong_hits}, weak_hits={weak_hits}"
            )
            if subs:
                lines.append(f"    → To candidates: {', '.join(subs)}")
            else:
                lines.append("    → No predefined substitution; mark as hotspot for manual review.")
            rationale = s.get("rationale", "")
            if rationale:
                lines.append(f"    Rationale: {rationale}")
        lines.append("")

    lines.append("======================================================================")
    lines.append("End of V5 report.")
    lines.append("")
    return "\n".join(lines)


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------

def main():
    parser = argparse.ArgumentParser(
        description="Run V5 de-immunization site suggestion for a project."
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
    parser.add_argument(
        "--strong-threshold",
        type=float,
        default=2.0,
        help="strong binder  rank （ 2.0）",
    )
    parser.add_argument(
        "--weak-threshold",
        type=float,
        default=10.0,
        help="weak binder  rank （ 10.0）",
    )
    parser.add_argument(
        "--top-positions",
        type=int,
        default=10,
        help="（ 10）",
    )

    args = parser.parse_args()
    base_dir = Path(args.base_dir).resolve()

    info = run_v5_for_project(
        project=args.project,
        base_dir=base_dir,
        strong_threshold=args.strong_threshold,
        weak_threshold=args.weak_threshold,
        top_positions=args.top_positions,
    )

    print("========================================")
    print(" V5 De-immunization Suggestion ")
    print("========================================")
    print(f"Project:   {args.project}")
    print(f"JSON out:  {info['json_path']}")
    print(f"TXT out:   {info['txt_path']}")
    print(f"Entries:   {info['entry_count']}")


if __name__ == "__main__":
    main()






















