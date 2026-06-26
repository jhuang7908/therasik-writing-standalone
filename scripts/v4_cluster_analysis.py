#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
v4_cluster_analysis.py

 V3  (v3_immunogenicity/result_v3.json) ：

- / HLA-II binder（ rank ）

-  (cluster)

-  motif（）

：

- projects/<project>/v4_cluster/result_v4.json

- projects/<project>/v4_cluster/result_v4_report.txt

：

    python scripts/v4_cluster_analysis.py --project EGFR_7D12_VHH

：

    --strong-threshold 2.0

    --weak-threshold   10.0

    --cluster-gap      3

"""

from __future__ import annotations

import argparse
import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple


DEFAULT_BASE_DIR = Path(__file__).resolve().parent.parent


@dataclass
class Prediction:
    allele: str
    start: int
    end: int
    peptide: str
    rank: float


@dataclass
class Cluster:
    start: int
    end: int
    min_rank: float
    mean_rank: float
    binder_count: int
    allele_count: int
    peptides: List[str]


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


def _normalize_predictions(entry: Dict[str, Any]) -> List[Prediction]:
    """
     v3  hla_binding_predictions ，
     Prediction 。
    """
    preds_raw = entry.get("hla_binding_predictions") or entry.get("predictions") or []
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


def _split_binders(
    preds: List[Prediction],
    strong_threshold: float,
    weak_threshold: float,
) -> Tuple[List[Prediction], List[Prediction]]:
    strong: List[Prediction] = []
    weak: List[Prediction] = []
    for p in preds:
        if p.rank <= strong_threshold:
            strong.append(p)
        elif p.rank <= weak_threshold:
            weak.append(p)
    return strong, weak


def _cluster_predictions(
    preds: List[Prediction],
    weak_threshold: float,
    cluster_gap: int,
) -> List[Cluster]:
    """
     rank ≤ weak_threshold 。
    -  start/end （gap ≤ cluster_gap） cluster。
    """
    high_risk = [p for p in preds if p.rank <= weak_threshold]
    if not high_risk:
        return []

    high_risk_sorted = sorted(high_risk, key=lambda p: p.start)

    clusters: List[Cluster] = []
    cur_members: List[Prediction] = [high_risk_sorted[0]]
    prev_end = high_risk_sorted[0].end

    for p in high_risk_sorted[1:]:
        gap = p.start - prev_end
        if gap <= cluster_gap:
            cur_members.append(p)
            prev_end = max(prev_end, p.end)
        else:
            clusters.append(_build_cluster(cur_members))
            cur_members = [p]
            prev_end = p.end

    if cur_members:
        clusters.append(_build_cluster(cur_members))

    return clusters


def _build_cluster(members: List[Prediction]) -> Cluster:
    starts = [p.start for p in members]
    ends = [p.end for p in members]
    ranks = [p.rank for p in members]
    peptides = [p.peptide for p in members]
    alleles = {p.allele for p in members}

    return Cluster(
        start=min(starts),
        end=max(ends),
        min_rank=min(ranks),
        mean_rank=sum(ranks) / len(ranks),
        binder_count=len(members),
        allele_count=len(alleles),
        peptides=peptides,
    )


def _count_motifs(preds: List[Prediction], rank_cutoff: float = 5.0) -> Dict[str, Dict[str, Any]]:
    """
     rank ≤ rank_cutoff  Prediction  motif：
     {peptide: {"count": n, "best_rank": r_min}}。
    """
    motif_stats: Dict[str, Dict[str, Any]] = {}
    for p in preds:
        if p.rank > rank_cutoff:
            continue
        m = motif_stats.setdefault(
            p.peptide,
            {"count": 0, "best_rank": p.rank},
        )
        m["count"] += 1
        if p.rank < m["best_rank"]:
            m["best_rank"] = p.rank
    return motif_stats


# ---------------------------------------------------------------------------
# 
# ---------------------------------------------------------------------------

def _analyze_one_block(
    name: str,
    analysis_entry: Dict[str, Any],
    strong_threshold: float,
    weak_threshold: float,
    cluster_gap: int,
) -> Dict[str, Any]:
    """
     parent_analysis  v2_variant_analysis  + motif 。
    """
    preds = _normalize_predictions(analysis_entry)
    strong, weak = _split_binders(preds, strong_threshold, weak_threshold)
    clusters = _cluster_predictions(preds, weak_threshold, cluster_gap)
    motif_stats = _count_motifs(preds, rank_cutoff=5.0)

    #  count 、 best_rank  10  motif
    motif_items = sorted(
        motif_stats.items(),
        key=lambda kv: (-kv[1]["count"], kv[1]["best_rank"]),
    )[:10]

    motifs_list = [
        {
            "motif": pep,
            "count": info["count"],
            "best_rank": info["best_rank"],
        }
        for pep, info in motif_items
    ]

    if strong:
        risk = "high"
    elif weak:
        risk = "medium"
    else:
        risk = "low"

    return {
        "name": name,
        "binder_counts": {
            "total_predictions": len(preds),
            "strong_binders": len(strong),
            "weak_binders": len(weak),
        },
        "risk_level": risk,
        "clusters": [
            {
                "start": c.start,
                "end": c.end,
                "min_rank": c.min_rank,
                "mean_rank": c.mean_rank,
                "binder_count": c.binder_count,
                "allele_count": c.allele_count,
                "peptides": c.peptides,
            }
            for c in clusters
        ],
        "motifs": motifs_list,
    }


def run_v4_for_project(
    project: str,
    base_dir: Path,
    strong_threshold: float,
    weak_threshold: float,
    cluster_gap: int,
) -> Dict[str, Any]:
    """
     v3_immunogenicity/result_v3.json，
     parent  v2  cluster + motif 。
    """
    project_root = base_dir / "projects" / project
    v3_path = project_root / "v3_immunogenicity" / "result_v3.json"
    if not v3_path.exists():
        raise FileNotFoundError(f"v3 ：{v3_path}")

    v3_data = _load_json(v3_path)

    # ：
    # 1) {"variants": [ {...}, ... ]}
    # 2) {"parents": [ {...}, ... ]}
    variants = v3_data.get("variants") or v3_data.get("parents") or []

    all_entries: List[Dict[str, Any]] = []

    for var in variants:
        parent_id = var.get("parent_id") or var.get("name") or "parent"
        parent_seq_len = len(var.get("parent_sequence", ""))

        parent_analysis = var.get("parent_analysis") or {}

        entry_parent = _analyze_one_block(
            name=f"{parent_id}::parent",
            analysis_entry=parent_analysis,
            strong_threshold=strong_threshold,
            weak_threshold=weak_threshold,
            cluster_gap=cluster_gap,
        )
        entry_parent["parent_id"] = parent_id
        entry_parent["variant_type"] = "parent"
        entry_parent["sequence_length"] = parent_seq_len
        all_entries.append(entry_parent)

        #  v2 （）
        v2_block = var.get("v2_variants_analysis") or var.get("v2_variants") or {}
        for v2_name, v2_info in v2_block.items():
            seq = v2_info.get("sequence") or ""
            analysis = v2_info.get("immunogenicity") or v2_info.get("analysis") or v2_info  #  v2_info

            entry_v2 = _analyze_one_block(
                name=f"{parent_id}::{v2_name}",
                analysis_entry=analysis,
                strong_threshold=strong_threshold,
                weak_threshold=weak_threshold,
                cluster_gap=cluster_gap,
            )
            entry_v2["parent_id"] = parent_id
            entry_v2["variant_type"] = "v2_variant"
            entry_v2["variant_name"] = v2_name
            entry_v2["sequence_length"] = len(seq)
            all_entries.append(entry_v2)

    #  motif （ parent / v2 ）
    global_motif_stats: Dict[str, Dict[str, Any]] = {}
    for e in all_entries:
        for m in e.get("motifs", []):
            motif = m["motif"]
            info = global_motif_stats.setdefault(
                motif,
                {"count": 0, "best_rank": m.get("best_rank", 999.0)},
            )
            info["count"] += m["count"]
            if m.get("best_rank", 999.0) < info["best_rank"]:
                info["best_rank"] = m.get("best_rank", 999.0)

    global_motifs = sorted(
        global_motif_stats.items(),
        key=lambda kv: (-kv[1]["count"], kv[1]["best_rank"]),
    )[:20]

    result_v4 = {
        "project": project,
        "source_v3": str(v3_path),
        "strong_threshold": strong_threshold,
        "weak_threshold": weak_threshold,
        "cluster_gap": cluster_gap,
        "entries": all_entries,
        "global_motifs": [
            {
                "motif": motif,
                "count": info["count"],
                "best_rank": info["best_rank"],
            }
            for motif, info in global_motifs
        ],
    }

    out_json = project_root / "v4_cluster" / "result_v4.json"
    _save_json(out_json, result_v4)

    #  txt 
    out_txt = project_root / "v4_cluster" / "result_v4_report.txt"
    out_txt.parent.mkdir(parents=True, exist_ok=True)
    out_txt.write_text(_build_text_report(result_v4), encoding="utf-8")

    return {
        "json_path": out_json,
        "txt_path": out_txt,
        "entry_count": len(all_entries),
    }


def _build_text_report(v4: Dict[str, Any]) -> str:
    lines: List[str] = []
    lines.append("======================================================================")
    lines.append("V4 Immunogenicity Cluster & Motif Analysis")
    lines.append("======================================================================")
    lines.append(f"Project: {v4.get('project','')}")
    lines.append(f"Strong binder threshold (rank ≤): {v4.get('strong_threshold')}")
    lines.append(f"Weak binder threshold (rank ≤):   {v4.get('weak_threshold')}")
    lines.append(f"Cluster gap (aa):                 {v4.get('cluster_gap')}")
    lines.append("")

    entries = v4.get("entries") or []

    for e in entries:
        lines.append("----------------------------------------------------------------------")
        lines.append(f"{e.get('name','')}  ({e.get('variant_type','')})")
        lines.append("----------------------------------------------------------------------")
        lines.append(f"Parent ID:       {e.get('parent_id','')}")
        if e.get("variant_type") == "v2_variant":
            lines.append(f"Variant name:    {e.get('variant_name','')}")
        lines.append(f"Sequence length: {e.get('sequence_length','?')} aa")

        bc = e.get("binder_counts") or {}
        lines.append(
            "Binders: strong={strong}  weak={weak}  total_preds={total}".format(
                strong=bc.get("strong_binders", 0),
                weak=bc.get("weak_binders", 0),
                total=bc.get("total_predictions", 0),
            )
        )
        lines.append(f"Risk level: {e.get('risk_level','unknown')}")
        lines.append("")

        clusters = e.get("clusters") or []
        lines.append(f"Clusters (rank ≤ weak_threshold): {len(clusters)}")
        for c in clusters[:10]:
            lines.append(
                f"  - [{c.get('start','?')}-{c.get('end','?')}] "
                f"binders={c.get('binder_count',0)}, "
                f"alleles={c.get('allele_count',0)}, "
                f"min_rank={c.get('min_rank','?'):.2f}, "
                f"mean_rank={c.get('mean_rank','?'):.2f}"
            )
        lines.append("")

        motifs = e.get("motifs") or []
        if motifs:
            lines.append("Top motifs (rank ≤ 5%, ):")
            for m in motifs[:10]:
                lines.append(
                    f"  - {m.get('motif','')}  "
                    f"(count={m.get('count',0)}, best_rank={m.get('best_rank','?'):.2f})"
                )
        else:
            lines.append("No motifs above rank threshold.")
        lines.append("")

    lines.append("======================================================================")
    lines.append("Global motifs (across all variants)")
    lines.append("======================================================================")
    gm = v4.get("global_motifs") or []
    for m in gm:
        lines.append(
            f"  - {m.get('motif','')}  "
            f"(total_count={m.get('count',0)}, best_rank={m.get('best_rank','?'):.2f})"
        )

    lines.append("")
    lines.append("End of V4 report.")
    return "\n".join(lines)


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------

def main():
    parser = argparse.ArgumentParser(
        description="Run V4 immunogenicity cluster & motif analysis for a project."
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
        "--cluster-gap",
        type=int,
        default=3,
        help="cluster （ aa， 3）",
    )

    args = parser.parse_args()

    base_dir = Path(args.base_dir).resolve()
    info = run_v4_for_project(
        project=args.project,
        base_dir=base_dir,
        strong_threshold=args.strong_threshold,
        weak_threshold=args.weak_threshold,
        cluster_gap=args.cluster_gap,
    )

    print("========================================")
    print(" V4 Cluster & Motif ")
    print("========================================")
    print(f"Project:   {args.project}")
    print(f"JSON out:  {info['json_path']}")
    print(f"TXT out:   {info['txt_path']}")
    print(f"Entries:   {info['entry_count']}")


if __name__ == "__main__":
    main()






















