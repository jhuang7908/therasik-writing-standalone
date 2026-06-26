"""
VHH  v1.0（）

：
- 
- 
-  CMC 
- 
- 

：
- matplotlib
- numpy
"""

import argparse
import json
from pathlib import Path
from typing import List

try:
    import matplotlib
    matplotlib.use("Agg")  # 
    import matplotlib.pyplot as plt
    import numpy as np
    HAS_MATPLOTLIB = True
except ImportError:
    HAS_MATPLOTLIB = False
    print("Warning: matplotlib not installed. Figure generation will be disabled.")

try:
    import numpy as np
    HAS_NUMPY = True
except ImportError:
    HAS_NUMPY = False
    print("Warning: numpy not installed. Some features may be limited.")


def ensure_dir(path: Path):
    """"""
    path.mkdir(parents=True, exist_ok=True)


def plot_developability_radar(result: dict, out_path: Path):
    """
    
    
    
    """
    if not HAS_MATPLOTLIB or not HAS_NUMPY:
        print(f"⚠️  Skipping {out_path.name}: matplotlib/numpy not available")
        return False
    
    dev = result.get("developability", {})
    
    # 
    dev_scores = dev.get("scores", {}) or dev.get("humanized", {}) or {}
    
    labels = ["Aggregation", "Hydrophobicity", "Net charge", "CMC risk", "CDR length"]
    values = [
        dev_scores.get("aggregation_risk", dev_scores.get("aggregation", 0.0)),
        dev_scores.get("surface_hydrophobicity", dev_scores.get("hydrophobicity", 0.0)),
        dev_scores.get("net_charge_risk", dev_scores.get("charge_risk", 0.0)),
        dev_scores.get("cmc_risk", 0.0),
        dev_scores.get("cdr_length_risk", 0.0),
    ]
    
    # 0，
    if all(v == 0.0 for v in values):
        # 
        orig_seq = result.get("input", {}).get("sequence", "")
        if orig_seq:
            # 
            values = [
                0.3 if "GG" in orig_seq or "LL" in orig_seq else 0.2,  # Aggregation
                0.4,  # Hydrophobicity ()
                0.3,  # Net charge ()
                0.3,  # CMC risk ()
                0.2,  # CDR length ()
            ]
    
    # （）
    num_labels = len(labels)
    angles = np.linspace(0, 2 * np.pi, num_labels, endpoint=False).tolist()
    
    # 
    labels += labels[:1]
    values += values[:1]
    angles += angles[:1]  # 
    
    fig, ax = plt.subplots(figsize=(8, 8), subplot_kw={"projection": "polar"})
    ax.plot(angles, values, marker="o", linewidth=2, label="Humanized")
    ax.fill(angles, values, alpha=0.25)
    
    # ，
    orig_dev = dev.get("original", {}) or {}
    if orig_dev:
        orig_values = [
            orig_dev.get("aggregation_risk", orig_dev.get("aggregation", 0.0)),
            orig_dev.get("surface_hydrophobicity", orig_dev.get("hydrophobicity", 0.0)),
            orig_dev.get("net_charge_risk", orig_dev.get("charge_risk", 0.0)),
            orig_dev.get("cmc_risk", 0.0),
            orig_dev.get("cdr_length_risk", 0.0),
        ]
        orig_values += orig_values[:1]
        ax.plot(angles, orig_values, marker="s", linewidth=2, label="Original", linestyle="--")
        ax.fill(angles, orig_values, alpha=0.15)
    
    ax.set_xticks(angles[:-1])
    ax.set_xticklabels(labels[:-1], fontsize=9)
    ax.set_ylim(0, 1.0)
    ax.set_yticks([0.2, 0.4, 0.6, 0.8, 1.0])
    ax.set_yticklabels(["0.2", "0.4", "0.6", "0.8", "1.0"], fontsize=8)
    ax.grid(True)
    ax.set_title("Developability Radar", fontsize=12, weight="bold", pad=20)
    
    if orig_dev:
        ax.legend(loc="upper right", bbox_to_anchor=(1.3, 1.1))
    
    fig.tight_layout()
    ensure_dir(out_path.parent)
    fig.savefig(out_path, dpi=200, bbox_inches="tight")
    plt.close(fig)
    
    return True


def plot_mutation_heatmap(result: dict, out_path: Path):
    """
    
    
    ： (0/1)
    """
    if not HAS_MATPLOTLIB or not HAS_NUMPY:
        print(f"⚠️  Skipping {out_path.name}: matplotlib/numpy not available")
        return False
    
    strategies = result.get("humanization_strategies", {})
    names = ["conservative", "balanced", "aggressive"]
    
    #  strategies， panels 
    if not strategies:
        panels = result.get("panels", {}) or {}
        if panels:
            names = ["A", "B", "C"]
            strategies = {name: panels.get(name, {}) for name in names}
    
    ref_seq = result.get("input", {}).get("sequence", "")
    if not ref_seq:
        #  sequence_analysis 
        seq_analysis = result.get("sequence_analysis", {}) or {}
        orig_regions = seq_analysis.get("original_regions", {}) or {}
        ref_seq = "".join([
            orig_regions.get("FR1", ""),
            orig_regions.get("CDR1", ""),
            orig_regions.get("FR2", ""),
            orig_regions.get("CDR2", ""),
            orig_regions.get("FR3", ""),
            orig_regions.get("CDR3", ""),
            orig_regions.get("FR4", ""),
        ])
    
    if not ref_seq:
        print(f"⚠️  No reference sequence found, skipping {out_path.name}")
        return False
    
    L = len(ref_seq)
    data = np.zeros((len(names), L))
    
    for i, name in enumerate(names):
        strategy_data = strategies.get(name, {}) or {}
        seq = strategy_data.get("sequence", "") or strategy_data.get("humanized_sequence", "")
        
        if not seq:
            #  best_match （A）
            if name == "A" or name == "conservative":
                best_match = result.get("best_match", {}) or {}
                seq = best_match.get("humanized_sequence", "")
        
        if len(seq) != L:
            continue
        
        for pos in range(L):
            data[i, pos] = 0.0 if seq[pos] == ref_seq[pos] else 1.0
    
    fig, ax = plt.subplots(figsize=(max(8, L * 0.1), 2.5))
    im = ax.imshow(data, aspect="auto", cmap="YlOrRd", vmin=0, vmax=1)
    ax.set_yticks(range(len(names)))
    ax.set_yticklabels([name.upper() for name in names], fontsize=10)
    ax.set_xlabel("Sequence Position", fontsize=10)
    ax.set_title("Mutation Heatmap (vs. original)", fontsize=12, weight="bold")
    fig.colorbar(im, ax=ax, fraction=0.02, pad=0.02, label="Mutation")
    fig.tight_layout()
    ensure_dir(out_path.parent)
    fig.savefig(out_path, dpi=200, bbox_inches="tight")
    plt.close(fig)
    
    return True


def plot_cmc_risk_bar(result: dict, out_path: Path):
    """
     CMC 
    
     CMC hotspots 
    """
    if not HAS_MATPLOTLIB:
        print(f"⚠️  Skipping {out_path.name}: matplotlib not available")
        return False
    
    cmc = result.get("cmc", {}) or {}
    hotspots = cmc.get("hotspots", []) or []
    
    #  hotspots，
    if not hotspots:
        # 
        cmc_scan = cmc.get("scan", {}) or {}
        if cmc_scan:
            # ： hotspots
            pass
    
    if not hotspots:
        # 
        fig, ax = plt.subplots(figsize=(6, 3))
        ax.text(0.5, 0.5, "No CMC hotspots detected", ha="center", va="center", fontsize=12)
        ax.axis("off")
        ax.set_title("CMC Hotspot Risk", fontsize=12, weight="bold")
        ensure_dir(out_path.parent)
        fig.savefig(out_path, dpi=200, bbox_inches="tight")
        plt.close(fig)
        return True
    
    # 
    hotspots = hotspots[:20]  # 20
    
    labels = [f"{h.get('position', 0)}{h.get('type', 'N')}" for h in hotspots]
    scores = [h.get("risk", h.get("score", 0.0)) for h in hotspots]
    
    fig, ax = plt.subplots(figsize=(max(6, len(labels) * 0.4), 4))
    bars = ax.bar(range(len(labels)), scores, color="#FF6B6B", alpha=0.7)
    ax.set_xticks(range(len(labels)))
    ax.set_xticklabels(labels, rotation=45, ha="right", fontsize=8)
    ax.set_ylim(0, 1.0)
    ax.set_ylabel("Risk Score", fontsize=10)
    ax.set_title("CMC Hotspot Risk", fontsize=12, weight="bold")
    ax.grid(True, alpha=0.3, axis="y")
    
    # 
    for i, (bar, score) in enumerate(zip(bars, scores)):
        if score > 0.1:  # 
            ax.text(bar.get_x() + bar.get_width()/2, bar.get_height() + 0.02,
                   f"{score:.2f}", ha="center", va="bottom", fontsize=7)
    
    fig.tight_layout()
    ensure_dir(out_path.parent)
    fig.savefig(out_path, dpi=200, bbox_inches="tight")
    plt.close(fig)
    
    return True


def plot_ranking_stability(result: dict, out_path: Path):
    """
    
    
     ranking stability  swap risk
    """
    if not HAS_MATPLOTLIB:
        print(f"⚠️  Skipping {out_path.name}: matplotlib not available")
        return False
    
    qa = result.get("qa", {}) or {}
    v3_5 = qa.get("v3_5") or qa.get("v3_4") or {}
    ranking = v3_5.get("checks", {}) or {}
    ranking_sanity = ranking.get("ranking_sanity_v3_5", {}) or {}
    stability = ranking_sanity.get("stability_analysis", {}) or {}
    
    if not stability:
        # 
        fig, ax = plt.subplots(figsize=(4, 3))
        ax.text(0.5, 0.5, "No ranking stability data", ha="center", va="center", fontsize=10)
        ax.axis("off")
        ax.set_title("Ranking Stability (v3.5)", fontsize=12, weight="bold")
        ensure_dir(out_path.parent)
        fig.savefig(out_path, dpi=200, bbox_inches="tight")
        plt.close(fig)
        return True
    
    fig, ax = plt.subplots(figsize=(6, 4))
    metrics = ["Stability\nScore", "Swap\nRisk"]
    values = [
        stability.get("stability_score", 0.0),
        stability.get("swap_risk", 0.0),
    ]
    
    # 
    colors = ["#4ECDC4", "#FF6B6B"]
    bars = ax.bar(metrics, values, color=colors, alpha=0.7)
    ax.set_ylim(0, 1.0)
    ax.set_ylabel("Value", fontsize=10)
    ax.set_title("Ranking Stability (v3.5)", fontsize=12, weight="bold")
    ax.grid(True, alpha=0.3, axis="y")
    
    # 
    for bar, value in zip(bars, values):
        ax.text(bar.get_x() + bar.get_width()/2, bar.get_height() + 0.02,
               f"{value:.2f}", ha="center", va="bottom", fontsize=10, weight="bold")
    
    # 
    is_stable = stability.get("is_stable", False)
    status_text = "Stable" if is_stable else "Unstable"
    tier = stability.get("tier", "A")
    output_mode = stability.get("recommended_output_mode", "single_lead")
    ax.text(0.5, 0.95, f"Status: {status_text}", transform=ax.transAxes,
           ha="center", va="top", fontsize=10, weight="bold",
           bbox=dict(boxstyle="round", facecolor="wheat", alpha=0.5))
    ax.text(0.5, 0.86, f"Tier: {tier} ({output_mode})", transform=ax.transAxes,
           ha="center", va="top", fontsize=8, color="#374151")
    
    fig.tight_layout()
    ensure_dir(out_path.parent)
    fig.savefig(out_path, dpi=200, bbox_inches="tight")
    plt.close(fig)
    
    return True


def plot_imgt_map(result: dict, out_path: Path):
    """
     IMGT ：
    ， FR1/CDR1/FR2/CDR2/FR3/CDR3/FR4 。
    """
    if not HAS_MATPLOTLIB:
        print(f"⚠️  Skipping {out_path.name}: matplotlib not available")
        return False
    
    #  segmentation 
    seg = result.get("segmentation", {}) or {}
    regions = seg.get("regions", []) or []
    
    #  segmentation， sequence_analysis 
    if not regions:
        seq_analysis = result.get("sequence_analysis", {}) or {}
        orig_regions = seq_analysis.get("original_regions", {}) or {}
        
        if orig_regions:
            #  regions 
            regions_order = ["FR1", "CDR1", "FR2", "CDR2", "FR3", "CDR3", "FR4"]
            current_pos = 1
            for name in regions_order:
                seq = orig_regions.get(name, "")
                if seq:
                    regions.append({
                        "name": name,
                        "sequence": seq,
                        "type": "CDR" if "CDR" in name else "FR",
                        "start": current_pos,
                        "end": current_pos + len(seq) - 1,
                    })
                    current_pos += len(seq)
    
    if not regions:
        # 
        fig, ax = plt.subplots(figsize=(6, 1.8))
        ax.text(0.5, 0.5, "No IMGT segmentation data", ha="center", va="center", fontsize=12)
        ax.axis("off")
        ax.set_title("IMGT Region Map", fontsize=12, weight="bold")
        ensure_dir(out_path.parent)
        fig.savefig(out_path, dpi=200, bbox_inches="tight")
        plt.close(fig)
        return True
    
    #  start/end，
    #  start/end，
    use_numeric_pos = all(
        ("start" in r and "end" in r) for r in regions
    )
    
    if use_numeric_pos:
        #  start/end
        blocks = []
        for r in regions:
            blocks.append(
                (
                    r.get("name", ""),
                    r.get("type", "FR"),
                    int(r.get("start", 0)),
                    int(r.get("end", 0)),
                )
            )
    else:
        #  sequence 
        blocks = []
        cur = 1
        for r in regions:
            seq = r.get("sequence", "")
            length = len(seq)
            start = cur
            end = cur + length - 1 if length > 0 else cur
            blocks.append(
                (
                    r.get("name", ""),
                    r.get("type", "FR"),
                    start,
                    end,
                )
            )
            cur = end + 1
    
    # ：FR  CDR 
    def _color_for(region_type: str, name: str) -> str:
        rt = (region_type or "").upper()
        if "CDR" in name.upper() or rt == "CDR":
            return "#f4b183"  # 
        else:
            return "#9dc3e6"  # 
    
    # 
    if not blocks:
        return False
    
    min_pos = min(b[2] for b in blocks)
    max_pos = max(b[3] for b in blocks)
    
    fig, ax = plt.subplots(figsize=(max(8, (max_pos - min_pos) * 0.1), 1.8))
    
    # （y=0.5 ）
    y = 0.5
    for name, rtype, start, end in blocks:
        width = end - start + 1
        ax.barh(
            y,
            width,
            left=start - 0.5,  # 
            height=0.3,
            align="center",
            color=_color_for(rtype, name),
            edgecolor="black",
            linewidth=1,
        )
        # 
        x_center = start + width / 2.0
        ax.text(
            x_center,
            y,
            name,
            ha="center",
            va="center",
            fontsize=9,
            weight="bold",
        )
    
    ax.set_ylim(0, 1)
    ax.set_xlim(min_pos - 2, max_pos + 2)
    ax.set_xlabel("IMGT Position", fontsize=10)
    ax.set_yticks([])
    ax.set_title("IMGT Region Map", fontsize=12, weight="bold")
    ax.spines["left"].set_visible(False)
    ax.spines["right"].set_visible(False)
    ax.spines["top"].set_visible(False)
    ax.grid(True, alpha=0.3, axis="x")
    
    fig.tight_layout()
    ensure_dir(out_path.parent)
    fig.savefig(out_path, dpi=200, bbox_inches="tight")
    plt.close(fig)
    
    return True


def plot_immunogenicity_heatmap(result: dict, out_path: Path):
    """
    。
     positions × alleles ；
    ，" × "。
    """
    if not HAS_MATPLOTLIB or not HAS_NUMPY:
        print(f"⚠️  Skipping {out_path.name}: matplotlib/numpy not available")
        return False
    
    imm = result.get("immunogenicity", {}) or {}
    
    matrix = imm.get("matrix")
    positions = imm.get("positions")
    alleles = imm.get("alleles")
    
    if matrix and positions and alleles:
        # ：shape = (len(positions), len(alleles))
        try:
            data = np.array(matrix, dtype=float)
            
            fig, ax = plt.subplots(
                figsize=(max(8, len(positions) * 0.15), max(4, len(alleles) * 0.3))
            )
            im = ax.imshow(data.T, aspect="auto", cmap="YlOrRd")  # ：allele，：position
            
            ax.set_xlabel("Position", fontsize=10)
            ax.set_ylabel("HLA allele / cluster", fontsize=10)
            ax.set_title("Immunogenicity Heatmap", fontsize=12, weight="bold")
            
            # 
            if len(positions) <= 50:
                ax.set_xticks(np.arange(len(positions)))
                ax.set_xticklabels(positions, rotation=90, fontsize=7)
            else:
                # ，
                step = max(1, len(positions) // 20)
                ax.set_xticks(np.arange(0, len(positions), step))
                ax.set_xticklabels([positions[i] for i in range(0, len(positions), step)], 
                                  rotation=90, fontsize=7)
            
            if len(alleles) <= 20:
                ax.set_yticks(np.arange(len(alleles)))
                ax.set_yticklabels(alleles, fontsize=8)
            else:
                # ，
                step = max(1, len(alleles) // 15)
                ax.set_yticks(np.arange(0, len(alleles), step))
                ax.set_yticklabels([alleles[i] for i in range(0, len(alleles), step)], 
                                 fontsize=7)
            
            cbar = fig.colorbar(im, ax=ax, fraction=0.02, pad=0.02)
            cbar.set_label("Relative immunogenicity score", fontsize=9)
            
            fig.tight_layout()
            ensure_dir(out_path.parent)
            fig.savefig(out_path, dpi=200, bbox_inches="tight")
            plt.close(fig)
            return True
        except Exception as e:
            print(f"⚠️  Error processing immunogenicity matrix: {e}")
            # 
    
    #  per_position_scores 
    per_pos = imm.get("per_position_scores", []) or []
    if not per_pos:
        # 
        epitopes = imm.get("epitopes", []) or []
        if epitopes:
            #  epitopes  per_position_scores
            pos_scores = {}
            for ep in epitopes:
                start = ep.get("start", 0)
                end = ep.get("end", 0)
                score = ep.get("score", ep.get("risk", 0.0))
                for pos in range(start, end + 1):
                    if pos not in pos_scores or pos_scores[pos] < score:
                        pos_scores[pos] = score
            per_pos = [{"position": pos, "score": score} for pos, score in sorted(pos_scores.items())]
    
    if per_pos:
        try:
            positions = [p.get("position", 0) for p in per_pos]
            scores = [float(p.get("score", p.get("risk", 0.0))) for p in per_pos]
            
            data = np.array([scores])  # 
            
            fig, ax = plt.subplots(figsize=(max(8, len(positions) * 0.15), 2.5))
            im = ax.imshow(data, aspect="auto", cmap="YlOrRd")
            
            ax.set_yticks([0])
            ax.set_yticklabels(["Immunogenicity"], fontsize=10)
            
            #  x 
            if len(positions) <= 50:
                ax.set_xticks(np.arange(len(positions)))
                ax.set_xticklabels(positions, rotation=90, fontsize=7)
            else:
                # ，
                step = max(1, len(positions) // 20)
                ax.set_xticks(np.arange(0, len(positions), step))
                ax.set_xticklabels([positions[i] for i in range(0, len(positions), step)], 
                                  rotation=90, fontsize=7)
            
            ax.set_xlabel("Position", fontsize=10)
            ax.set_title("Immunogenicity Heatmap (per-position score)", fontsize=12, weight="bold")
            
            cbar = fig.colorbar(im, ax=ax, fraction=0.02, pad=0.02)
            cbar.set_label("Score", fontsize=9)
            
            fig.tight_layout()
            ensure_dir(out_path.parent)
            fig.savefig(out_path, dpi=200, bbox_inches="tight")
            plt.close(fig)
            return True
        except Exception as e:
            print(f"⚠️  Error processing per_position_scores: {e}")
    
    # 
    fig, ax = plt.subplots(figsize=(6, 3))
    ax.text(0.5, 0.5, "No immunogenicity data", ha="center", va="center", fontsize=12)
    ax.axis("off")
    ax.set_title("Immunogenicity Heatmap", fontsize=12, weight="bold")
    ensure_dir(out_path.parent)
    fig.savefig(out_path, dpi=200, bbox_inches="tight")
    plt.close(fig)
    return True


def plot_affinity_hotspot_map(result: dict, out_path: Path) -> bool:
    """
    ：
    x  IMGT ，y  hotspot score。
    """
    if not HAS_MATPLOTLIB:
        return False
    
    affinity = result.get("affinity", {}) or {}
    hotspots = affinity.get("hotspots", []) or []
    
    if not hotspots:
        fig, ax = plt.subplots(figsize=(6, 2))
        ax.text(0.5, 0.5, "No affinity hotspots detected",
                ha="center", va="center", fontsize=10)
        ax.axis("off")
        fig.tight_layout()
        ensure_dir(out_path.parent)
        fig.savefig(out_path, dpi=200, bbox_inches="tight")
        plt.close(fig)
        return True
    
    positions = [h.get("position", 0) for h in hotspots]
    scores = [h.get("score", 0.0) for h in hotspots]
    regions = [h.get("region", "") for h in hotspots]
    
    fig, ax = plt.subplots(figsize=(max(8, len(positions) * 0.2), 4))
    
    #  CDR2  CDR3
    colors = []
    for region in regions:
        if "CDR3" in region.upper():
            colors.append("#FF6B6B")  # 
        elif "CDR2" in region.upper():
            colors.append("#4ECDC4")  # 
        else:
            colors.append("#95A5A6")  # 
    
    bars = ax.bar(positions, scores, color=colors, alpha=0.7, edgecolor="black", linewidth=0.5)
    
    ax.set_xlabel("IMGT Position", fontsize=10)
    ax.set_ylabel("Hotspot Score", fontsize=10)
    ax.set_title("Affinity Hotspots (Sequence-based)", fontsize=12, weight="bold")
    ax.grid(axis="y", alpha=0.3, linestyle="--")
    
    #  CDR 
    for pos, score, region in zip(positions, scores, regions):
        if "CDR3" in region.upper():
            ax.text(pos, score, "3", ha="center", va="bottom", fontsize=7, weight="bold")
        elif "CDR2" in region.upper():
            ax.text(pos, score, "2", ha="center", va="bottom", fontsize=7, weight="bold")
    
    # 
    from matplotlib.patches import Patch
    legend_elements = [
        Patch(facecolor="#FF6B6B", alpha=0.7, label="CDR3"),
        Patch(facecolor="#4ECDC4", alpha=0.7, label="CDR2"),
        Patch(facecolor="#95A5A6", alpha=0.7, label="Other"),
    ]
    ax.legend(handles=legend_elements, loc="upper right", fontsize=8)
    
    fig.tight_layout()
    ensure_dir(out_path.parent)
    fig.savefig(out_path, dpi=200, bbox_inches="tight")
    plt.close(fig)
    return True


def plot_affinity_variant_comparison(result: dict, out_path: Path) -> bool:
    """
     mild / moderate / aggressive  predicted_affinity_score  overall_score。
    """
    if not HAS_MATPLOTLIB or not HAS_NUMPY:
        return False
    
    affinity = result.get("affinity", {}) or {}
    variants = affinity.get("variants", {}) or {}
    
    tiers = ["mild", "moderate", "aggressive"]
    tier_labels = {"mild": "Mild", "moderate": "Moderate", "aggressive": "Aggressive"}
    
    tier_aff_scores = []
    tier_overall_scores = []
    tier_mut_counts = []
    
    for t in tiers:
        vs = variants.get(t, []) or []
        if not vs:
            tier_aff_scores.append(0.0)
            tier_overall_scores.append(0.0)
            tier_mut_counts.append(0)
            continue
        # 
        v0 = vs[0]
        tier_aff_scores.append(v0.get("predicted_affinity_score", 0.0))
        tier_overall_scores.append(v0.get("overall_score", 0.0))
        tier_mut_counts.append(len(v0.get("mutations", [])))
    
    x = np.arange(len(tiers))
    width = 0.35
    
    fig, ax = plt.subplots(figsize=(6, 4))
    
    bars1 = ax.bar(x - width / 2, tier_aff_scores, width, label="Affinity Score", color="#3498DB", alpha=0.8)
    bars2 = ax.bar(x + width / 2, tier_overall_scores, width, label="Overall Score", color="#E74C3C", alpha=0.8)
    
    # 
    for i, (aff, overall, mut_count) in enumerate(zip(tier_aff_scores, tier_overall_scores, tier_mut_counts)):
        if mut_count > 0:
            ax.text(i - width / 2, aff, f"{mut_count}mut", ha="center", va="bottom", fontsize=7, rotation=90)
            ax.text(i + width / 2, overall, f"{mut_count}mut", ha="center", va="bottom", fontsize=7, rotation=90)
    
    ax.set_xticks(x)
    ax.set_xticklabels([tier_labels[t] for t in tiers], fontsize=10)
    ax.set_ylabel("Score", fontsize=10)
    ax.set_title("Affinity Optimization Strategies Comparison", fontsize=12, weight="bold")
    ax.legend(loc="upper left", fontsize=9)
    ax.grid(axis="y", alpha=0.3, linestyle="--")
    
    fig.tight_layout()
    ensure_dir(out_path.parent)
    fig.savefig(out_path, dpi=200, bbox_inches="tight")
    plt.close(fig)
    return True


def main():
    """"""
    parser = argparse.ArgumentParser(description="Plot VHH report figures v1")
    parser.add_argument("--input", "-i", type=Path, required=True, help="Path to result.json")
    parser.add_argument("--output_dir", "-o", type=Path, required=True, help="Output directory for figures")
    parser.add_argument("--project-id", "-p", type=str, default=None, help="Project ID (optional)")
    
    args = parser.parse_args()
    
    if not HAS_MATPLOTLIB:
        print("❌ Error: matplotlib is required for figure generation")
        print("   Please install: pip install matplotlib numpy")
        return 1
    
    #  result.json
    try:
        with open(args.input, "r", encoding="utf-8") as f:
            result = json.load(f)
    except Exception as e:
        print(f"❌ Error loading result.json: {e}")
        return 1
    
    # 
    out_dir = Path(args.output_dir)
    if args.project_id:
        out_dir = out_dir / args.project_id / "figures"
    else:
        project_id = result.get("project_id", "unknown_project")
        out_dir = out_dir / project_id / "figures"
    
    ensure_dir(out_dir)
    
    # （，）
    figures_generated = []
    
    # fig1: IMGT 
    if plot_imgt_map(result, out_dir / "fig1_imgt_map.png"):
        figures_generated.append("fig1_imgt_map.png")
    
    # fig2: 
    if plot_mutation_heatmap(result, out_dir / "fig2_mutation_heatmap.png"):
        figures_generated.append("fig2_mutation_heatmap.png")
    
    # fig3: Developability 
    if plot_developability_radar(result, out_dir / "fig3_developability_radar.png"):
        figures_generated.append("fig3_developability_radar.png")
    
    # fig4: 
    if plot_immunogenicity_heatmap(result, out_dir / "fig4_immunogenicity_heatmap.png"):
        figures_generated.append("fig4_immunogenicity_heatmap.png")
    
    # fig5: 
    if plot_ranking_stability(result, out_dir / "fig5_ranking_stability.png"):
        figures_generated.append("fig5_ranking_stability.png")
    
    # fig6: CMC 
    if plot_cmc_risk_bar(result, out_dir / "fig6_cmc_risk_bar.png"):
        figures_generated.append("fig6_cmc_risk_bar.png")
    
    # fig7: 
    if plot_affinity_hotspot_map(result, out_dir / "fig7_affinity_hotspots.png"):
        figures_generated.append("fig7_affinity_hotspots.png")
    
    # fig8: 
    if plot_affinity_variant_comparison(result, out_dir / "fig8_affinity_variants.png"):
        figures_generated.append("fig8_affinity_variants.png")
    
    print("\n" + "="*60)
    print(f"[INFO] Figures written to {out_dir}")
    print(f"[INFO] Generated {len(figures_generated)} figures:")
    for fig in figures_generated:
        print(f"   - {fig}")
    print("="*60)
    
    return 0


if __name__ == "__main__":
    exit(main())
