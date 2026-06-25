#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
vhh_scaffold_match_and_craft.py

：
1） human VHH FR index（human_vhh_fr_index.json）
2）/ VHH  IMGT （ imgt_number_anarcii）
3） FR1/FR2/FR3  human scaffold ， identity + hallmark 
4） scaffold（best_match）（candidates）
5） best scaffold  craft：FR  human，CDR  VHH， humanized VHH 
"""

import json
import sys
from pathlib import Path
from typing import Dict, List, Tuple, Any, Optional

# 
PROJECT_ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(PROJECT_ROOT))

# =====  ANARCII  =====
from core.numbering.imgt_anarcii import imgt_number_anarcii, IMGTNumberingError
from core.vhh_humanization import split_regions, IMGT_REGIONS


def load_human_vhh_fr_panel(
    path: str = "core/scaffolds/human_vhh_fr_index.json"
) -> List[Dict[str, Any]]:
    """VHH FR"""
    full_path = PROJECT_ROOT / path
    with open(full_path, "r", encoding="utf-8") as f:
        data = json.load(f)
    return data["scaffolds"]


def _get_region_from_pos(pos: int) -> str:
    """IMGT。
    [V1.8.9]  CDR2  Kabat CDR2  (IMGT 66-74)，
     VH→VHH  unique CDR2 ，。
    """
    if IMGT_REGIONS["FR1"]["start"] <= pos <= IMGT_REGIONS["FR1"]["end"]:
        return "FR1"
    elif IMGT_REGIONS["CDR1"]["start"] <= pos <= IMGT_REGIONS["CDR1"]["end"]:
        return "CDR1"
    # [V1.8.9] Kabat anchor protection: IMGT 39-40 (Kabat H34-35) are critical for 
    # CD3 binding interface. Protect them from scaffold replacement.
    elif 39 <= pos <= 40:
        return "CDR1"
    elif IMGT_REGIONS["FR2"]["start"] <= pos <= IMGT_REGIONS["FR2"]["end"]:
        return "FR2"
    # CDR2 ：IMGT 56-65 ， 66-74  Kabat CDR2 
    elif 56 <= pos <= 74:
        return "CDR2"
    elif 75 <= pos <= 104:
        return "FR3"
    elif IMGT_REGIONS["CDR3"]["start"] <= pos <= IMGT_REGIONS["CDR3"]["end"]:
        return "CDR3"
    elif IMGT_REGIONS["FR4"]["start"] <= pos <= IMGT_REGIONS["FR4"]["end"]:
        return "FR4"
    else:
        return "UNKNOWN"


def _build_vhh_residue_map_and_regions(seq: str) -> Tuple[Dict[int, str], Dict[str, Tuple[int, int]]]:
    """
     imgt_number_anarcii(seq)  VHH/VH  IMGT 。
     residue_map (base-position only, used for FR identity)  regions。

    NOTE: ins_code are preserved in _ordered_rows (attached to the returned map as
    residue_map._ordered_rows) so that craft_humanized_vhh can reconstruct CDR3
    faithfully even when it contains IMGT insertion codes (e.g. 111A, 111B…).
    This prevents the insertion-code overwrite bug that silently truncated long CDR3s.
    """
    try:
        rows = imgt_number_anarcii(seq)
    except IMGTNumberingError as e:
        raise RuntimeError(f"IMGT numbering failed: {e}") from e

    # Ordered list of (pos, ins_code, aa) for every non-gap residue — used by
    # craft_humanized_vhh for exact CDR sequence reconstruction.
    ordered_rows = [
        (r["pos"], (r.get("ins_code") or " ").strip(), r["aa"])
        for r in rows
        if isinstance(r.get("pos"), int) and isinstance(r.get("aa"), str) and r["aa"] not in ("-", "")
    ]

    # Base-position map (last ins wins, but only used for FR identity comparisons
    # where insertions never occur — so this is safe for FR use).
    residue_map: Dict[int, str] = {}
    for pos, _ins, aa in ordered_rows:
        residue_map[pos] = aa

    # Attach ordered rows as a non-dict attribute so callers can retrieve full CDR3.
    # We use a simple wrapper class to keep the existing Dict[int,str] interface.
    class _ResMap(dict):  # noqa: N801
        pass

    rmap = _ResMap(residue_map)
    rmap._ordered_rows = ordered_rows  # type: ignore[attr-defined]

    # Build region bounds from base positions
    region_bounds: Dict[str, List[int]] = {}
    for pos in residue_map:
        region = _get_region_from_pos(pos)
        if region not in region_bounds:
            region_bounds[region] = [pos, pos]
        else:
            region_bounds[region][0] = min(region_bounds[region][0], pos)
            region_bounds[region][1] = max(region_bounds[region][1], pos)

    regions: Dict[str, Tuple[int, int]] = {}
    for name, (start, end) in region_bounds.items():
        regions[name] = (int(start), int(end))

    return rmap, regions


def _calc_fr_identity(
    vhh_map: Dict[int, str],
    vhh_regions: Dict[str, Tuple[int, int]],
    sc_map: Dict[int, str],
    sc_regions: Dict[str, List[int]],
    use_fr4: bool = True,
) -> Dict[str, float]:
    """ FR1/FR2/FR3(+FR4) identity， dict。"""
    fr_names = ["FR1", "FR2", "FR3"]
    if use_fr4:
        fr_names.append("FR4")

    idents: Dict[str, float] = {}
    for fr in fr_names:
        v_range = vhh_regions.get(fr)
        s_range = sc_regions.get(fr)
        if not v_range or not s_range:
            idents[fr] = 0.0
            continue
        v_start, v_end = v_range
        s_start, s_end = s_range[0], s_range[1]
        same = 0
        total = 0
        #  identity
        start = max(v_start, s_start)
        end = min(v_end, s_end)
        for pos in range(start, end + 1):
            v_aa = vhh_map.get(pos)
            s_aa = sc_map.get(pos)
            if v_aa and s_aa:
                total += 1
                if v_aa == s_aa:
                    same += 1
        idents[fr] = same / total if total > 0 else 0.0
    return idents


def _calc_hallmark_score(
    vhh_map: Dict[int, str],
    sc_hallmarks: Dict[str, str],
    positions: List[int] = [44, 45, 47],  # FR2 hallmarks only; pos37 is CDR1
) -> float:
    """ VHH hallmark ：（IMGT 44/45/47）。"""
    same = 0
    total = 0
    for pos in positions:
        v_aa = vhh_map.get(pos)
        # keykey
        s_aa = sc_hallmarks.get(str(pos)) or sc_hallmarks.get(pos)
        if v_aa and s_aa:
            total += 1
            if v_aa == s_aa:
                same += 1
    return same / total if total > 0 else 0.0


def match_vhh_to_human_fr(
    seq: str,
    index_path: str = "core/scaffolds/human_vhh_fr_index.json",
    fr_identity_min: float = 0.70,
    hallmark_min: float = 0.50,
) -> Dict[str, Any]:
    """
     VHH ， human VHH FR panel  scaffold。

    ：
    {
      "success": True/False,
      "best_match": { ... } or None,
      "candidates": [ ... ],   #  score 
      "vhh_residue_map": {...},
      "vhh_regions": {...},
      "error": str or None
    }
    """
    try:
        vhh_map, vhh_regions = _build_vhh_residue_map_and_regions(seq)
    except Exception as e:
        return {
            "success": False,
            "best_match": None,
            "candidates": [],
            "vhh_residue_map": {},
            "vhh_regions": {},
            "error": f"Failed to build VHH residue map: {e}"
        }
    
    scaffolds = load_human_vhh_fr_panel(index_path)
    candidates: List[Dict[str, Any]] = []

    for sc in scaffolds:
        sc_map = {int(k): v for k, v in sc["imgt_positions"].items()}
        sc_regions = sc.get("regions", {})
        sc_hallmarks = sc.get("hallmark_positions", {})
        dev_score = sc.get("developability_score", 0.5)

        fr_idents = _calc_fr_identity(vhh_map, vhh_regions, sc_map, sc_regions)
        hallmark_score = _calc_hallmark_score(vhh_map, sc_hallmarks)

        # ：FR2 
        total_score = (
            0.2 * fr_idents.get("FR1", 0.0)
            + 0.4 * fr_idents.get("FR2", 0.0)
            + 0.3 * fr_idents.get("FR3", 0.0)
            + 0.1 * hallmark_score
        )

        candidates.append({
            "id": sc["id"],
            "scaffold_entry": sc,  #  craft
            "fr_identity_FR1": fr_idents.get("FR1", 0.0),
            "fr_identity_FR2": fr_idents.get("FR2", 0.0),
            "fr_identity_FR3": fr_idents.get("FR3", 0.0),
            "hallmark_score": hallmark_score,
            "developability_score": dev_score,
            "total_score": total_score,
        })

    if not candidates:
        return {
            "success": False,
            "best_match": None,
            "candidates": [],
            "vhh_residue_map": vhh_map,
            "vhh_regions": vhh_regions,
            "error": "no scaffold candidates (panel empty?)"
        }

    candidates.sort(key=lambda c: c["total_score"], reverse=True)
    best = candidates[0]

    # 
    if best["fr_identity_FR2"] < fr_identity_min or best["hallmark_score"] < hallmark_min:
        return {
            "success": False,
            "best_match": None,
            "candidates": candidates[:5],
            "vhh_residue_map": vhh_map,
            "vhh_regions": vhh_regions,
            "error": "no scaffold meets FR2/hallmark thresholds; please review top candidates."
        }

    return {
        "success": True,
        "best_match": best,
        "candidates": candidates[:5],
        "vhh_residue_map": vhh_map,
        "vhh_regions": vhh_regions,
        "error": None,
    }


def craft_humanized_vhh(
    vhh_map: Dict[int, str],
    vhh_regions: Dict[str, Tuple[int, int]],
    scaffold_entry: Dict[str, Any],
) -> str:
    """
    CDR-graft: FR positions from the human VHH42 scaffold; CDR1/CDR2/CDR3 from
    the donor VH/VHH, preserving ALL IMGT insertion residues (111A, 111B…).

    Algorithm:
      - Scaffold base positions (integer IMGT) drive the backbone.
      - When a scaffold position falls inside a CDR IMGT range (from vhh_regions),
        that scaffold residue is skipped and the FULL donor CDR (including
        insertions from _ordered_rows) is injected exactly once.
      - FR scaffold residues are kept as-is, with donor fallback for missing positions.

    This prevents the insertion-code truncation bug: long CDR3s (e.g. Toripalimab
    IGHV1 16aa CDR3 with IMGT insertions at 111/112) are grafted in full.
    """
    sc_map = {int(k): v for k, v in scaffold_entry["imgt_positions"].items()}

    # [V1.8.9] Use the provided vhh_regions for CDR detection to preserve unique CDR tails.
    # Fallback to standard IMGT if vhh_regions is empty or invalid.
    CDR_RANGES = vhh_regions or {
        "CDR1": (27, 38),
        "CDR2": (56, 65),
        "CDR3": (105, 117),
    }

    def _is_cdr(pos: int) -> Optional[str]:
        for cdr, r_range in CDR_RANGES.items():
            if not cdr.startswith("CDR"):
                continue
            lo, hi = r_range
            if lo <= pos <= hi:
                return cdr
        return None

    # Build donor CDR sequences with full insertion codes from _ordered_rows
    donor_cdr_seqs: Dict[str, str] = {}
    ordered_rows = getattr(vhh_map, "_ordered_rows", None)
    for cdr_name, (cdr_lo, cdr_hi) in CDR_RANGES.items():
        if ordered_rows is not None:
            cdr_residues = [aa for (pos, _ins, aa) in ordered_rows if cdr_lo <= pos <= cdr_hi]
        else:
            # Fallback: base positions only (old behaviour, no insertion codes)
            cdr_residues = [vhh_map[p] for p in range(cdr_lo, cdr_hi + 1) if p in vhh_map]
        donor_cdr_seqs[cdr_name] = "".join(cdr_residues)

    all_sc_positions = sorted(sc_map.keys())
    if not all_sc_positions:
        return ""

    seq_parts: List[str] = []
    injected_cdrs: set = set()  # track which CDRs have already been injected

    for sc_pos in all_sc_positions:
        cdr = _is_cdr(sc_pos)
        if cdr is not None:
            # First time we enter this CDR range: inject full donor CDR
            if cdr not in injected_cdrs:
                donor_cdr = donor_cdr_seqs.get(cdr, "")
                if donor_cdr:
                    seq_parts.append(donor_cdr)
                injected_cdrs.add(cdr)
            # Skip scaffold residues inside CDR range (donor CDR already injected)
        else:
            # FR position: use scaffold residue, fallback to donor
            aa = sc_map.get(sc_pos) or vhh_map.get(sc_pos)
            if aa:
                seq_parts.append(aa)

    return "".join(seq_parts)


def build_vhh_variants(
    seq: str,
    match_result: Dict[str, Any],
    index_path: str = "core/scaffolds/human_vhh_fr_index.json",
) -> List[Dict[str, Any]]:
    """
     variants ：
      - variant_id:  ID（ parent / SAFE_A / SAFE_B）
      - kind: parent / humanized
      - label: 
      - sequence: 
      - scaffold_id:  parent  None， scaffold  ID
      - matching_scores:  candidate  FR identity / hallmark / total_score
    """
    variants: List[Dict[str, Any]] = []

    # 1)  VHH  parent
    variants.append({
        "variant_id": "parent",
        "kind": "parent",
        "label": "Original llama VHH",
        "sequence": seq,
        "scaffold_id": None,
        "matching_scores": None,
    })

    # ， parent
    if not match_result.get("success"):
        return variants

    # 2)  scaffold panel
    scaffolds = load_human_vhh_fr_panel(index_path)
    #  scaffold ， ID  key
    scaffold_map = {sc["id"]: sc for sc in scaffolds}

    vhh_map = match_result["vhh_residue_map"]
    vhh_regions = match_result["vhh_regions"]

    for cand in match_result.get("candidates", []):
        full_id = cand["id"]
        sc_entry = scaffold_map.get(full_id)
        if sc_entry is None:
            # ID，
            key_prefix = full_id.split(" | ")[0]
            for sc in scaffolds:
                if sc["id"].startswith(key_prefix):
                    sc_entry = sc
                    break
            if sc_entry is None:
                continue

        humanized_seq = craft_humanized_vhh(
            vhh_map=vhh_map,
            vhh_regions=vhh_regions,
            scaffold_entry=sc_entry,
        )

        #  ID  plan=A/B/C
        plan = "unknown"
        if "| plan=" in full_id:
            for part in full_id.split(" | "):
                if part.startswith("plan="):
                    plan = part.split("=", 1)[1]
                    break

        variant_id = f"humanized_{plan}"

        #  scaffold  ID（ plan ）
        scaffold_base_id = full_id.split(" | ")[0]

        variants.append({
            "variant_id": variant_id,
            "kind": "humanized",
            "label": f"Humanized on {scaffold_base_id} (plan {plan})",
            "sequence": humanized_seq,
            "scaffold_id": scaffold_base_id,
            "matching_scores": {
                "fr_identity_FR1": cand.get("fr_identity_FR1"),
                "fr_identity_FR2": cand.get("fr_identity_FR2"),
                "fr_identity_FR3": cand.get("fr_identity_FR3"),
                "hallmark_score": cand.get("hallmark_score"),
                "developability_score": cand.get("developability_score"),
                "total_score": cand.get("total_score"),
            },
        })

    return variants


def generate_markdown_report(
    original_seq: str,
    result: Dict[str, Any],
    humanized_seq: str,
    output_path: Optional[str] = None
) -> str:
    """Markdown"""
    from datetime import datetime
    
    md_content = f"""# VHH Scaffold Matching and Crafting Report

**：** {datetime.now().strftime("%Y-%m-%d %H:%M:%S")}

---

## 1. 

**VHH：**
```
{original_seq}
```

**：** {len(original_seq)} aa

---

## 2. 

"""
    
    if not result["success"]:
        md_content += f"""
### ⚠️ 

**：** {result.get("error", "Unknown error")}

### Scaffold（Top 5）

"""
        for i, c in enumerate(result.get("candidates", [])[:5], 1):
            md_content += f"""
#### Candidate {i}

- **ID**: `{c['id']}`
- **FR1 Identity**: {c['fr_identity_FR1']:.3f} ({c['fr_identity_FR1']*100:.1f}%)
- **FR2 Identity**: {c['fr_identity_FR2']:.3f} ({c['fr_identity_FR2']*100:.1f}%)
- **FR3 Identity**: {c['fr_identity_FR3']:.3f} ({c['fr_identity_FR3']*100:.1f}%)
- **Hallmark Score**: {c['hallmark_score']:.3f} ({c['hallmark_score']*100:.1f}%)
- **Total Score**: {c['total_score']:.3f} ({c['total_score']*100:.1f}%)

"""
    else:
        best = result["best_match"]
        md_content += f"""
### ✅ Scaffold

- **ID**: `{best['id']}`
- **FR1 Identity**: {best['fr_identity_FR1']:.3f} ({best['fr_identity_FR1']*100:.1f}%)
- **FR2 Identity**: {best['fr_identity_FR2']:.3f} ({best['fr_identity_FR2']*100:.1f}%)
- **FR3 Identity**: {best['fr_identity_FR3']:.3f} ({best['fr_identity_FR3']*100:.1f}%)
- **Hallmark Score**: {best['hallmark_score']:.3f} ({best['hallmark_score']*100:.1f}%)
- **Developability Score**: {best.get('developability_score', 0.5):.3f}
- **Total Score**: {best['total_score']:.3f} ({best['total_score']*100:.1f}%)

### （Top 5）

"""
        for i, c in enumerate(result.get("candidates", [])[1:6], 2):
            md_content += f"""
#### Candidate {i}

- **ID**: `{c['id']}`
- **FR1 Identity**: {c['fr_identity_FR1']:.3f}
- **FR2 Identity**: {c['fr_identity_FR2']:.3f}
- **FR3 Identity**: {c['fr_identity_FR3']:.3f}
- **Hallmark Score**: {c['hallmark_score']:.3f}
- **Total Score**: {c['total_score']:.3f}

"""
    
    md_content += f"""
---

## 3. Craft

"""
    
    if result["success"]:
        md_content += f"""
### VHH

```
{humanized_seq}
```

**：** {len(humanized_seq)} aa

### 

|  |  |  |  |  |
|------|---------|-----------|------|------|
"""
        # 
        vhh_map = result["vhh_residue_map"]
        scaffold_entry = result["best_match"].get("scaffold_entry")
        if not scaffold_entry:
            # scaffold_entry，best_match
            md_content += "⚠️ （scaffold_entry）\n\n"
        else:
            sc_map = {int(k): v for k, v in scaffold_entry["imgt_positions"].items()}
        
            mutations = []
            for pos in sorted(vhh_map.keys()):
                orig_aa = vhh_map.get(pos, "-")
                region = ""
                for rname, (start, end) in result["vhh_regions"].items():
                    if start <= pos <= end:
                        region = rname
                        break
                
                if region.startswith("CDR"):
                    hum_aa = orig_aa  # CDR
                else:
                    hum_aa = sc_map.get(pos, orig_aa)
                
                if orig_aa != hum_aa:
                    mutations.append((pos, orig_aa, hum_aa, region))
            
            # 20
            for pos, orig_aa, hum_aa, region in mutations[:20]:
                md_content += f"| {pos} | {orig_aa} | {hum_aa} | {region} | {orig_aa}→{hum_aa} |\n"
            
            if len(mutations) > 20:
                md_content += f"| ... | ... | ... | ... | ( {len(mutations)} ) |\n"
            
            md_content += f"""
**：** {len(mutations)} （FR）

"""
    else:
        md_content += """
⚠️ ，。

"""
    
    md_content += """
---

## 4. 

### VHH

"""
    for region_name in ["FR1", "CDR1", "FR2", "CDR2", "FR3", "CDR3", "FR4"]:
        region_range = result["vhh_regions"].get(region_name)
        if region_range:
            start, end = region_range
            md_content += f"- **{region_name}**:  {start}-{end}\n"
    
    md_content += """
---

****
"""
    
    if output_path:
        Path(output_path).write_text(md_content, encoding="utf-8")
        print(f"[INFO] Markdown report saved to: {output_path}")
    
    return md_content


def main():
    import argparse
    parser = argparse.ArgumentParser(description="Match VHH to human FR scaffold and craft humanized VHH.")
    parser.add_argument("--seq", required=True, help="Input VHH amino acid sequence")
    parser.add_argument(
        "--index",
        default="core/scaffolds/human_vhh_fr_index.json",
        help="Human VHH FR index JSON path"
    )
    parser.add_argument(
        "--fr-identity-min",
        type=float,
        default=0.70,
        help="Minimum FR2 identity threshold (default: 0.70)"
    )
    parser.add_argument(
        "--hallmark-min",
        type=float,
        default=0.50,
        help="Minimum hallmark score threshold (default: 0.50)"
    )
    parser.add_argument(
        "--output",
        default="result_vhh_scaffold_match.json",
        help="Output JSON path for downstream pipeline (default: result_vhh_scaffold_match.json)"
    )
    parser.add_argument(
        "--output-json",
        help="Output JSON result file path (deprecated, use --output instead)"
    )
    parser.add_argument(
        "--output-md",
        help="Output Markdown report file path"
    )
    args = parser.parse_args()

    #  --output  --output-json（）
    output_json_path = args.output if args.output != "result_vhh_scaffold_match.json" or not args.output_json else args.output_json

    match_res = match_vhh_to_human_fr(
        args.seq,
        index_path=args.index,
        fr_identity_min=args.fr_identity_min,
        hallmark_min=args.hallmark_min
    )

    # （）
    humanized_seq = ""
    scaffold_entry_for_md = None
    if match_res["success"]:
        scaffold_entry = match_res["best_match"]["scaffold_entry"]
        scaffold_entry_for_md = scaffold_entry  # MD
        humanized_seq = craft_humanized_vhh(
            vhh_map=match_res["vhh_residue_map"],
            vhh_regions=match_res["vhh_regions"],
            scaffold_entry=scaffold_entry,
        )
        match_res["humanized_sequence"] = humanized_seq
        match_res["original_sequence"] = args.seq
    else:
        match_res["humanized_sequence"] = None
        match_res["original_sequence"] = args.seq

    #  variants （scaffold_entry，build_vhh_variantsscaffold_entry）
    variants = build_vhh_variants(args.seq, match_res, index_path=args.index)

    # scaffold_entry（，JSON）
    for c in match_res.get("candidates", []):
        if "scaffold_entry" in c:
            c.pop("scaffold_entry")
    if match_res.get("best_match") and "scaffold_entry" in match_res["best_match"]:
        match_res["best_match"].pop("scaffold_entry")

    # JSON（variants）
    out = {
        "input_sequence": args.seq,
        "input_length": len(args.seq),
        "matching_result": match_res,
        "variants": variants,
    }
    
    Path(output_json_path).write_text(
        json.dumps(out, indent=2, ensure_ascii=False),
        encoding="utf-8"
    )
    print(f"[INFO] Wrote scaffold matching + variants to {output_json_path}")

    # Markdown（scaffold_entry）
    if args.output_md:
        # scaffold_entryMD
        if match_res["success"] and scaffold_entry_for_md:
            match_res["best_match"]["scaffold_entry"] = scaffold_entry_for_md
        generate_markdown_report(args.seq, match_res, humanized_seq, args.output_md)
        # 
        if match_res["success"] and "scaffold_entry" in match_res["best_match"]:
            match_res["best_match"].pop("scaffold_entry")

    # 
    if not match_res["success"]:
        print("[WARN] Matching did not pass thresholds.")
        print("Error:", match_res["error"])
        print("\nTop candidates:")
        for i, c in enumerate(match_res["candidates"], 1):
            print(f"\nCandidate {i}:")
            print(f"  ID: {c['id']}")
            print(f"  FR1 Identity: {c['fr_identity_FR1']:.3f}")
            print(f"  FR2 Identity: {c['fr_identity_FR2']:.3f}")
            print(f"  FR3 Identity: {c['fr_identity_FR3']:.3f}")
            print(f"  Hallmark Score: {c['hallmark_score']:.3f}")
            print(f"  Total Score: {c['total_score']:.3f}")
        print(f"\n[INFO] Generated {len(variants)} variant(s) (parent only)")
        return

    print("[INFO] Best scaffold:")
    best = match_res["best_match"]
    print(f"  ID: {best['id']}")
    print(f"  FR1 Identity: {best['fr_identity_FR1']:.3f}")
    print(f"  FR2 Identity: {best['fr_identity_FR2']:.3f}")
    print(f"  FR3 Identity: {best['fr_identity_FR3']:.3f}")
    print(f"  Hallmark Score: {best['hallmark_score']:.3f}")
    print(f"  Total Score: {best['total_score']:.3f}")

    print("\n[INFO] Humanized VHH sequence:")
    print(humanized_seq)
    print(f"\n[INFO] Sequence length: {len(humanized_seq)} aa")
    print(f"\n[INFO] Generated {len(variants)} variant(s):")
    for v in variants:
        print(f"  - {v['variant_id']}: {v['label']}")


if __name__ == "__main__":
    main()

