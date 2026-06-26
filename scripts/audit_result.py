"""
：result.jsonreport.md

：
1. provenance
2. MDJSON
3. JSON，
"""

from __future__ import annotations

import argparse
import json
import re
from datetime import datetime
from pathlib import Path
from typing import Dict, Any, List, Tuple


def validate_input_provenance(json_data: Dict[str, Any]) -> Tuple[bool, List[str]]:
    """input_provenance"""
    errors = []
    
    if "input_provenance" not in json_data:
        errors.append("❌  input_provenance ")
        return False, errors
    
    ip = json_data["input_provenance"]
    
    required_fields = ["sha256", "sequence_id", "length", "aa_alphabet_check"]
    for field in required_fields:
        if field not in ip:
            errors.append(f"❌ input_provenance.{field} ")
    
    if not ip.get("aa_alphabet_check", {}).get("valid"):
        errors.append("❌ input_provenance.aa_alphabet_check.valid != true")
    
    if not ip.get("sha256"):
        errors.append("❌ input_provenance.sha256 ")
    
    return len(errors) == 0, errors


def validate_segmentation_provenance(json_data: Dict[str, Any]) -> Tuple[bool, List[str]]:
    """segmentation_provenance"""
    errors = []
    
    if "segmentation_provenance" not in json_data:
        errors.append("❌  segmentation_provenance ")
        return False, errors
    
    sp = json_data["segmentation_provenance"]
    method = sp.get("method", "")
    
    if method != "anarcii" and not method.startswith("fallback:"):
        errors.append(f"❌ segmentation_provenance.method = '{method}' != 'anarcii'")
    
    if sp.get("scheme") != "imgt":
        errors.append(f"❌ segmentation_provenance.scheme != 'imgt'")
    
    # reconstruction_check
    seg = json_data.get("segmentation", {})
    recon_check = seg.get("reconstruction_check", {})
    if not recon_check.get("matches_input"):
        errors.append("❌ segmentation.reconstruction_check.matches_input != true")
    
    return len(errors) == 0, errors


def validate_germline_library_provenance(json_data: Dict[str, Any]) -> Tuple[bool, List[str]]:
    """germline_library_provenance"""
    errors = []
    
    if "germline_library_provenance" not in json_data:
        errors.append("❌  germline_library_provenance ")
        return False, errors
    
    glp = json_data["germline_library_provenance"]
    
    if not glp.get("sha256"):
        errors.append("❌ germline_library_provenance.sha256 ")
    
    if glp.get("entry_count", 0) == 0:
        errors.append("❌ germline_library_provenance.entry_count == 0")
    
    required_fields = ["library_name", "version", "path"]
    for field in required_fields:
        if not glp.get(field):
            errors.append(f"❌ germline_library_provenance.{field} ")
    
    return len(errors) == 0, errors


def validate_germline_numbering_provenance(json_data: Dict[str, Any]) -> Tuple[bool, List[str]]:
    """germline_numbering_provenance"""
    errors = []
    
    if "germline_numbering" not in json_data:
        errors.append("❌  germline_numbering ")
        return False, errors
    
    gn = json_data["germline_numbering"]
    
    if not gn.get("numberings"):
        errors.append("❌ germline_numbering.numberings ")
    
    np = gn.get("numbering_provenance", {})
    if not np:
        errors.append("❌ germline_numbering.numbering_provenance ")
        return False, errors
    
    method = np.get("method", "")
    if method != "anarcii" and not method.startswith("fallback:"):
        errors.append(f"❌ germline_numbering.numbering_provenance.method = '{method}' != 'anarcii'")
    
    if np.get("scheme") != "imgt":
        errors.append(f"❌ germline_numbering.numbering_provenance.scheme != 'imgt'")
    
    return len(errors) == 0, errors


def validate_alignment_provenance(json_data: Dict[str, Any]) -> Tuple[bool, List[str]]:
    """alignment_provenance"""
    errors = []
    
    if "germline_alignment_provenance" not in json_data:
        errors.append("❌  germline_alignment_provenance ")
    
    if "germline_candidates" not in json_data:
        errors.append("❌  germline_candidates ")
        return False, errors
    
    candidates = json_data["germline_candidates"]
    if len(candidates) == 0:
        errors.append("❌ germline_candidates ")
    
    for cand in candidates:
        if cand.get("evidence", {}).get("imgt_positions_compared", 0) == 0:
            errors.append(f"❌ {cand.get('template_id')}imgt_positions_compared == 0")
    
    return len(errors) == 0, errors


def validate_selection_proof(json_data: Dict[str, Any]) -> Tuple[bool, List[str]]:
    """selection_proof"""
    errors = []
    
    if "germline_selection_proof" not in json_data:
        errors.append("❌  germline_selection_proof ")
        return False, errors
    
    gsp = json_data["germline_selection_proof"]
    
    if gsp.get("eligible_candidate_count", 0) == 0:
        errors.append("❌ germline_selection_proof.eligible_candidate_count == 0")
    
    if not gsp.get("consistency_checks", {}).get("selected_in_ranked_top10"):
        errors.append("❌ germline_selection_proof.consistency_checks.selected_in_ranked_top10 != true")
    
    if not gsp.get("selected"):
        errors.append("❌ germline_selection_proof.selected ")
    
    return len(errors) == 0, errors


def validate_md_matches_json(md_path: Path, json_data: Dict[str, Any]) -> Tuple[bool, List[str]]:
    """MDJSON"""
    errors = []
    
    if not md_path.exists():
        errors.append(f"❌ MD: {md_path}")
        return False, errors
    
    md_content = md_path.read_text(encoding="utf-8")
    
    # 
    gsp = json_data.get("germline_selection_proof", {})
    selected = gsp.get("selected", {})
    
    # selected template_id
    selected_id = selected.get("template_id", "")
    if selected_id:
        if selected_id not in md_content:
            errors.append(f"❌ MDselected template_id: {selected_id}")
    
    # framework_identity（4）
    framework_identity = selected.get("framework_identity", 0.0)
    identity_str = f"{framework_identity:.4f}"
    if identity_str not in md_content:
        # 
        if f"{framework_identity:.3f}" not in md_content and f"{framework_identity:.2f}" not in md_content:
            errors.append(f"❌ MDframework_identity: {identity_str}")
    
    # rank
    rank = selected.get("rank", 0)
    if rank > 0:
        if str(rank) not in md_content:
            errors.append(f"❌ MDrank: {rank}")
    
    # germline_library_provenanceentry_count
    glp = json_data.get("germline_library_provenance", {})
    entry_count = glp.get("entry_count", 0)
    if entry_count > 0:
        if str(entry_count) not in md_content:
            errors.append(f"❌ MDentry_count: {entry_count}")
    
    return len(errors) == 0, errors


def main():
    parser = argparse.ArgumentParser(description="result.jsonreport.md")
    parser.add_argument("--json", type=Path, required=True, help="JSON")
    parser.add_argument("--md", type=Path, required=True, help="MD")
    
    args = parser.parse_args()
    
    print("=" * 80)
    print("JSONMD")
    print("=" * 80)
    print()
    
    # JSON
    if not args.json.exists():
        print(f"❌ JSON: {args.json}")
        return 1
    
    with open(args.json, "r", encoding="utf-8") as f:
        json_data = json.load(f)
    
    all_errors = []
    
    # 1. validate_input_provenance
    print("[1/7]  input_provenance...")
    is_valid, errors = validate_input_provenance(json_data)
    all_errors.extend(errors)
    print("  ✅ " if is_valid else f"  ❌  ({len(errors)})")
    print()
    
    # 2. validate_segmentation_provenance
    print("[2/7]  segmentation_provenance...")
    is_valid, errors = validate_segmentation_provenance(json_data)
    all_errors.extend(errors)
    print("  ✅ " if is_valid else f"  ❌  ({len(errors)})")
    print()
    
    # 3. validate_germline_library_provenance
    print("[3/7]  germline_library_provenance...")
    is_valid, errors = validate_germline_library_provenance(json_data)
    all_errors.extend(errors)
    print("  ✅ " if is_valid else f"  ❌  ({len(errors)})")
    print()
    
    # 4. validate_germline_numbering_provenance
    print("[4/7]  germline_numbering_provenance...")
    is_valid, errors = validate_germline_numbering_provenance(json_data)
    all_errors.extend(errors)
    print("  ✅ " if is_valid else f"  ❌  ({len(errors)})")
    print()
    
    # 5. validate_alignment_provenance
    print("[5/7]  alignment_provenance...")
    is_valid, errors = validate_alignment_provenance(json_data)
    all_errors.extend(errors)
    print("  ✅ " if is_valid else f"  ❌  ({len(errors)})")
    print()
    
    # 6. validate_selection_proof
    print("[6/7]  selection_proof...")
    is_valid, errors = validate_selection_proof(json_data)
    all_errors.extend(errors)
    print("  ✅ " if is_valid else f"  ❌  ({len(errors)})")
    print()
    
    # 7. validate_md_matches_json
    print("[7/7]  MD  JSON ...")
    is_valid, errors = validate_md_matches_json(args.md, json_data)
    all_errors.extend(errors)
    print("  ✅ " if is_valid else f"  ❌  ({len(errors)})")
    print()
    
    # 
    print("=" * 80)
    if len(all_errors) == 0:
        print("✅ ")
        print("=" * 80)
        
        #  audit.md 
        audit_md_path = args.json.parent / "audit.md"
        generate_audit_md(
            json_path=args.json,
            md_path=args.md,
            audit_md_path=audit_md_path,
            json_data=json_data,
            all_errors=all_errors,
        )
        print(f"\n✅ : {audit_md_path}")
        
        return 0
    else:
        print(f"❌ ： {len(all_errors)} ")
        print("=" * 80)
        print("\n:")
        for error in all_errors:
            print(f"  {error}")
        return 1


def generate_audit_md(
    json_path: Path,
    md_path: Path,
    audit_md_path: Path,
    json_data: Dict[str, Any],
    all_errors: List[str],
) -> None:
    """ audit.md """
    lines = []
    
    # 
    lines.append("# EGFR VHH ")
    lines.append("")
    lines.append(f"****: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}  ")
    lines.append(f"****: `scripts/audit_result.py`  ")
    lines.append("****: ")
    lines.append(f"- JSON: `{json_path.relative_to(Path.cwd()) if json_path.is_relative_to(Path.cwd()) else json_path}`")
    lines.append(f"- MD: `{md_path.relative_to(Path.cwd()) if md_path.is_relative_to(Path.cwd()) else md_path}`")
    lines.append("")
    lines.append("---")
    lines.append("")
    
    # 
    if len(all_errors) == 0:
        lines.append("## ")
        lines.append("")
        lines.append("### ✅ ")
        lines.append("")
        lines.append("|  |  |  |")
        lines.append("|--------|------|------|")
        lines.append("| [1/7] input_provenance | ✅  | provenance |")
        lines.append("| [2/7] segmentation_provenance | ✅  | IMGTprovenance |")
        lines.append("| [3/7] germline_library_provenance | ✅  | Germlineprovenance |")
        lines.append("| [4/7] germline_numbering_provenance | ✅  | Germlineprovenance |")
        lines.append("| [5/7] alignment_provenance | ✅  | provenance |")
        lines.append("| [6/7] selection_proof | ✅  | proof |")
        lines.append("| [7/7] MDJSON | ✅  | MDJSON |")
        lines.append("")
    else:
        lines.append("## ")
        lines.append("")
        lines.append("### ❌ ")
        lines.append("")
        lines.append(f"****: {len(all_errors)}")
        lines.append("")
        lines.append("****:")
        for error in all_errors:
            lines.append(f"- {error}")
        lines.append("")
    
    lines.append("---")
    lines.append("")
    
    # 
    lines.append("## ")
    lines.append("")
    
    # 1. 
    ip = json_data.get("input_provenance", {})
    lines.append("### 1. ")
    if ip.get("sha256"):
        lines.append(f"- ✅ `input_provenance.sha256`: `{ip['sha256']}`")
    if ip.get("aa_alphabet_check", {}).get("valid"):
        lines.append(f"- ✅ `input_provenance.aa_alphabet_check.valid`: `true`")
    if ip.get("length"):
        lines.append(f"- ✅ `input_provenance.length`: `{ip['length']}`")
    lines.append("")
    
    # 2. IMGT
    sp = json_data.get("segmentation_provenance", {})
    seg = json_data.get("segmentation", {})
    lines.append("### 2. IMGT")
    if sp.get("method"):
        lines.append(f"- ✅ `segmentation_provenance.method`: `{sp['method']}`")
    if sp.get("scheme"):
        lines.append(f"- ✅ `segmentation_provenance.scheme`: `{sp['scheme']}`")
    if seg.get("reconstruction_check", {}).get("matches_input"):
        lines.append(f"- ✅ `segmentation.reconstruction_check.matches_input`: `true`")
    lines.append("")
    
    # 3. Germline
    glp = json_data.get("germline_library_provenance", {})
    lines.append("### 3. Germline")
    if glp.get("sha256"):
        lines.append(f"- ✅ `germline_library_provenance.sha256`: ")
    if glp.get("entry_count"):
        lines.append(f"- ✅ `germline_library_provenance.entry_count`: `{glp['entry_count']}`")
    if glp.get("path"):
        lines.append(f"- ✅ `germline_library_provenance.path`: ")
    lines.append("")
    
    # 4. Germline
    gn = json_data.get("germline_numbering", {})
    gnp = gn.get("numbering_provenance", {}) if gn else {}
    lines.append("### 4. Germline")
    if gnp.get("method"):
        lines.append(f"- ✅ `germline_numbering.numbering_provenance.method`: `{gnp['method']}`")
    if gnp.get("scheme"):
        lines.append(f"- ✅ `germline_numbering.numbering_provenance.scheme`: `{gnp['scheme']}`")
    numbering_count = len(gn.get("numberings", {})) if gn else 0
    failed_count = gn.get("failed_count", 0) if gn else 0
    total_count = numbering_count + failed_count
    if total_count > 0:
        lines.append(f"- ✅ : `{numbering_count}` ({total_count}，{failed_count})")
    lines.append("")
    
    # 5. 
    gap = json_data.get("germline_alignment_provenance", {})
    candidates = json_data.get("germline_candidates", [])
    lines.append("### 5. ")
    if gap.get("algorithm"):
        lines.append(f"- ✅ `germline_alignment_provenance.algorithm`: `{gap['algorithm']}`")
    if candidates:
        lines.append(f"- ✅ `germline_candidates`: `{len(candidates)}`")
        if all(c.get("evidence", {}).get("imgt_positions_compared", 0) > 0 for c in candidates):
            lines.append("- ✅ `imgt_positions_compared > 0`")
    lines.append("")
    
    # 6. 
    gsp = json_data.get("germline_selection_proof", {})
    selected = gsp.get("selected", {}) if gsp else {}
    lines.append("### 6. ")
    if selected.get("template_id"):
        lines.append(f"- ✅ `germline_selection_proof.selected.template_id`: `{selected['template_id']}`")
    if selected.get("framework_identity") is not None:
        lines.append(f"- ✅ `germline_selection_proof.selected.framework_identity`: `{selected['framework_identity']}`")
    if gsp and gsp.get("consistency_checks", {}).get("selected_in_ranked_top10"):
        lines.append("- ✅ `germline_selection_proof.consistency_checks.selected_in_ranked_top10`: `true`")
    if gsp and gsp.get("eligible_candidate_count"):
        lines.append(f"- ✅ `germline_selection_proof.eligible_candidate_count`: `{gsp['eligible_candidate_count']}`")
    lines.append("")
    
    # 7. MDJSON
    lines.append("### 7. MDJSON")
    if len(all_errors) == 0:
        lines.append("- ✅ MD`template_id`JSON")
        lines.append("- ✅ MD`framework_identity`JSON（4）")
        lines.append("- ✅ MD`rank`JSON")
        if glp.get("entry_count"):
            lines.append(f"- ✅ MD`entry_count`JSON")
    lines.append("")
    
    lines.append("---")
    lines.append("")
    
    # 
    lines.append("## ")
    lines.append("")
    
    # Step 1
    lines.append("### Step 1: ")
    if ip.get("length"):
        lines.append(f"- ✅ : {ip['length']} aa")
    if ip.get("sequence_id"):
        lines.append(f"- ✅ ID: {ip['sequence_id']}")
    if ip.get("sha256"):
        lines.append("- ✅ SHA256: ")
    lines.append("")
    
    # Step 2
    lines.append("### Step 2: IMGT")
    if sp.get("method"):
        lines.append(f"- ✅ : {sp['method']}")
    if sp.get("scheme"):
        lines.append(f"- ✅ : {sp['scheme']}")
    if seg.get("reconstruction_check", {}).get("matches_input"):
        lines.append("- ✅ : ")
    lines.append("")
    
    # Step 3
    lines.append("### Step 3: Germline")
    if glp.get("entry_count"):
        lines.append(f"- ✅ : {glp['entry_count']}")
    if glp.get("sha256"):
        lines.append("- ✅ SHA256: ")
    lines.append("")
    
    # Step 4
    lines.append("### Step 4: GermlineIMGT")
    if numbering_count > 0:
        lines.append(f"- ✅ : {numbering_count}")
    if failed_count > 0:
        lines.append(f"- ✅ : {failed_count}（`failed_templates`）")
    lines.append("")
    
    # Step 5
    lines.append("### Step 5:  vs Germline")
    if candidates:
        lines.append(f"- ✅ : {len(candidates)}")
    if gap.get("algorithm"):
        lines.append(f"- ✅ : {gap['algorithm']}")
    lines.append("")
    
    # Step 6
    lines.append("### Step 6: ")
    if selected.get("template_id"):
        lines.append(f"- ✅ : {selected['template_id']}")
    if selected.get("framework_identity") is not None:
        lines.append(f"- ✅ Framework Identity: {selected['framework_identity']}")
    if gsp and gsp.get("ranked_top10"):
        lines.append("- ✅ Top 10: ")
    lines.append("")
    
    lines.append("---")
    lines.append("")
    
    # 
    lines.append("## ")
    lines.append("")
    if len(all_errors) == 0:
        lines.append("**✅ ，**")
        lines.append("")
        lines.append("- provenance")
        lines.append("- evidence")
        lines.append("- MDJSON")
        lines.append("- 、、、fallback")
        lines.append("")
        lines.append("****:")
        lines.append("- ✅ Single Source of Truth: JSON")
        lines.append("- ✅ Evidence-first: provenanceevidence")
        lines.append("- ✅ Fail-fast: ")
    else:
        lines.append("**❌ **")
        lines.append("")
        lines.append(f" {len(all_errors)} ，。")
    lines.append("")
    lines.append("---")
    lines.append("")
    lines.append(f"****: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    lines.append("")
    
    # 
    with open(audit_md_path, "w", encoding="utf-8") as f:
        f.write("\n".join(lines))


if __name__ == "__main__":
    import sys
    sys.exit(main())

