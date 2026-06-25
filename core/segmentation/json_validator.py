"""
JSON - segmentation_provenance

：
1.  segmentation_provenance.method
2.  segmentation_provenance.scheme == "imgt"
3.  implementation.package  implementation.version
4.  evidence.boundaries
5.  method  anarcii， implementation.package  anarcii

：，""。
"""

from __future__ import annotations

from typing import Dict, Any, List, Tuple


class SegmentationProvenanceValidationError(Exception):
    """Segmentation provenance"""
    pass


def validate_segmentation_provenance(json_data: Dict[str, Any]) -> Tuple[bool, List[str]]:
    """
    JSONsegmentation_provenance
    
    Args:
        json_data: JSON
    
    Returns:
        (is_valid, errors)
        is_valid: True
        errors: 
    
    Raises:
        SegmentationProvenanceValidationError: 
    """
    errors: List[str] = []
    
    # segmentation_provenance
    provenance = json_data.get("segmentation_provenance")
    if not provenance:
        errors.append(" segmentation_provenance ")
        return False, errors
    
    if not isinstance(provenance, dict):
        errors.append("segmentation_provenance ")
        return False, errors
    
    # 1:  method
    method = provenance.get("method")
    if not method:
        errors.append("segmentation_provenance.method ")
    elif not isinstance(method, str):
        errors.append("segmentation_provenance.method ")
    
    # 2:  scheme == "imgt"
    scheme = provenance.get("scheme")
    if not scheme:
        errors.append("segmentation_provenance.scheme ")
    elif scheme != "imgt":
        errors.append(f'segmentation_provenance.scheme  "imgt"， "{scheme}"')
    
    # 3:  implementation.package  implementation.version
    implementation = provenance.get("implementation")
    if not implementation:
        errors.append("segmentation_provenance.implementation ")
    else:
        if not isinstance(implementation, dict):
            errors.append("segmentation_provenance.implementation ")
        else:
            package = implementation.get("package")
            version = implementation.get("version")
            
            if not package:
                errors.append("segmentation_provenance.implementation.package ")
            if not version:
                errors.append("segmentation_provenance.implementation.version ")
            
            # 5:  method  anarcii， implementation.package  anarcii
            if method == "anarcii" and package != "anarcii":
                errors.append(
                    f' method="anarcii" ，implementation.package  "anarcii"，'
                    f' "{package}"'
                )
    
    # 4:  evidence.boundaries
    evidence = provenance.get("evidence")
    if not evidence:
        errors.append("segmentation_provenance.evidence ")
    else:
        if not isinstance(evidence, dict):
            errors.append("segmentation_provenance.evidence ")
        else:
            boundaries = evidence.get("boundaries")
            if not boundaries:
                errors.append("segmentation_provenance.evidence.boundaries ")
            elif not isinstance(boundaries, dict):
                errors.append("segmentation_provenance.evidence.boundaries ")
            else:
                # 
                required_regions = ["FR1", "CDR1", "FR2", "CDR2", "FR3", "CDR3", "FR4"]
                for region in required_regions:
                    if region not in boundaries:
                        errors.append(f"segmentation_provenance.evidence.boundaries : {region}")
                    else:
                        region_boundary = boundaries[region]
                        if not isinstance(region_boundary, list) or len(region_boundary) != 2:
                            errors.append(
                                f"segmentation_provenance.evidence.boundaries.{region} 2"
                            )
    
    is_valid = len(errors) == 0
    return is_valid, errors


def validate_germline_selection_consistency(json_data: Dict[str, Any]) -> Tuple[bool, List[str]]:
    """
    germline_selection_proofgermline
    
    Args:
        json_data: JSON
    
    Returns:
        (is_valid, errors)
    """
    errors: List[str] = []
    
    germline = json_data.get("germline", {})
    germline_selection_proof = json_data.get("germline_selection_proof", {})
    
    if not germline or not germline_selection_proof:
        # ，（）
        return True, errors
    
    selected = germline.get("selected", {})
    selected_scores = selected.get("scores", {})
    selected_overall = selected_scores.get("overall", 0.0)
    
    # germline.selected.scores.overall > 0
    if selected_overall > 0:
        proof_selected = germline_selection_proof.get("selected", {})
        proof_template_id = proof_selected.get("template_id", "")
        proof_combined_score = proof_selected.get("combined_score", 0.0)
        
        selected_id = selected.get("id", "")
        
        # 1: template_id
        if proof_template_id != selected_id:
            errors.append(
                f"germline_selection_proof.selected.template_id ({proof_template_id}) "
                f" germline.selected.id ({selected_id}) "
            )
        
        # 2: score
        if abs(proof_combined_score - selected_overall) >= 0.001:
            errors.append(
                f"germline_selection_proof.selected.combined_score ({proof_combined_score}) "
                f" germline.selected.scores.overall ({selected_overall}) "
            )
        
        # 3: Top1overall0
        germline_candidates = germline.get("candidates", [])
        if germline_candidates:
            top1_overall = germline_candidates[0].get("scores", {}).get("overall", 0.0)
            if top1_overall == 0.0:
                errors.append(
                    "germline.candidates[0].scores.overall  0，Top1  overall  0"
                )
    
    is_valid = len(errors) == 0
    return is_valid, errors


def validate_germline_library_proof(json_data: Dict[str, Any]) -> Tuple[bool, List[str]]:
    """
    4 - Rule A: germlineprovenance
    
    ：
    - assert "germline_library_provenance" in json_data
    - assert json_data["germline_library_provenance"]["sha256"]
    
    Args:
        json_data: JSON
    
    Returns:
        (is_valid, errors)
    """
    errors: List[str] = []
    
    # Rule A: germline library proof
    # 1：
    if "germline_library_provenance" not in json_data:
        errors.append(" germline_library_provenance （Rule A：）")
        return False, errors
    
    provenance = json_data["germline_library_provenance"]
    
    # error（）
    if "error" in provenance:
        errors.append(f"germline_library_provenance : {provenance.get('error')}（Rule A）")
        return False, errors
    
    # 2：sha256
    sha256 = provenance.get("sha256")
    if not sha256:
        errors.append("germline_library_provenance.sha256 （Rule A：sha256）")
        return False, errors
    
    # sha256（）
    library_path = provenance.get("absolute_path") or provenance.get("path")
    if library_path and library_path != "NOT_FOUND":
        try:
            from pathlib import Path
            from core.germline_library_provenance import calculate_file_sha256
            
            file_path = Path(library_path)
            if file_path.exists():
                actual_sha256 = calculate_file_sha256(file_path)
                if actual_sha256 != sha256:
                    errors.append(
                        f"germline_library_provenance.sha256 ({sha256[:16]}...) "
                        f"sha256 ({actual_sha256[:16]}...) （Rule A）"
                    )
                    return False, errors
        except Exception as e:
            # ，
            errors.append(f"sha256: {e}")
    
    return True, errors


def validate_germline_numbering_proof(json_data: Dict[str, Any]) -> Tuple[bool, List[str]]:
    """
    4 - Rule BC: germline IMGTANARCII
    
    ：
    - assert "germline_numbering" in json_data
    - assert json_data["germline_numbering"]["numbering_provenance"]["method"] == "anarcii"
    - assert json_data["germline_numbering"]["scheme"] == "imgt"
    
    Args:
        json_data: JSON
    
    Returns:
        (is_valid, errors)
    """
    errors: List[str] = []
    
    # Rule B: germline IMGT numbering proof
    # 1：
    if "germline_numbering" not in json_data:
        errors.append(" germline_numbering （Rule B：）")
        return False, errors
    
    germline_numbering = json_data["germline_numbering"]
    
    # 
    if "error" in germline_numbering:
        errors.append(f"germline_numbering : {germline_numbering['error']}（Rule B：）")
        return False, errors
    
    # numberings
    numberings = germline_numbering.get("numberings", {})
    if not numberings:
        errors.append("germline_numbering.numberings （Rule B）")
        return False, errors
    
    # scheme
    scheme_valid = False
    for template_id, numbering in numberings.items():
        if "error" in numbering:
            continue
        scheme = numbering.get("scheme")
        if scheme == "imgt":
            scheme_valid = True
            break
    
    if not scheme_valid:
        errors.append("germline_numbering  scheme == 'imgt'（Rule B）")
        return False, errors
    
    # Rule C: ANARCII proof
    numbering_provenance = germline_numbering.get("numbering_provenance")
    if not numbering_provenance:
        errors.append(" germline_numbering.numbering_provenance （Rule C）")
        return False, errors
    
    method = numbering_provenance.get("method")
    if method != "anarcii":
        if method and method.startswith("fallback:"):
            # fallback，
            errors.append(
                f"germline_numbering.numbering_provenance.method = '{method}' "
                f"（fallback，Rule C）"
            )
            # fallback，
        else:
            errors.append(
                f"germline_numbering.numbering_provenance.method = '{method}' != 'anarcii'（Rule C）"
            )
            return False, errors
    
    # packageversion
    package = numbering_provenance.get("package")
    package_version = numbering_provenance.get("package_version")
    
    if not package or package != "anarcii":
        errors.append(
            f"germline_numbering.numbering_provenance.package = '{package}' != 'anarcii'（Rule C）"
        )
        return False, errors
    
    if not package_version or package_version == "not_installed":
        errors.append(
            f"germline_numbering.numbering_provenance.package_version = '{package_version}' "
            f"（ANARCII，Rule C）"
        )
        return False, errors
    
    # segmentation_provenance.method
    segmentation_provenance = json_data.get("segmentation_provenance", {})
    seg_method = segmentation_provenance.get("method")
    
    if seg_method and seg_method != method and not (method.startswith("fallback:") and seg_method.startswith("fallback:")):
        errors.append(
            f"germline numbering method ({method})  "
            f"segmentation method ({seg_method}) （Rule C）"
        )
        # ，
    
    return True, errors


def validate_json_for_delivery(json_data: Dict[str, Any], strict: bool = True) -> Tuple[bool, List[str]]:
    """
    JSON
    
    Args:
        json_data: JSON
        strict: （True，False）
    
    Returns:
        (is_valid, errors)
        is_valid: True
        errors: 
    
    Raises:
        SegmentationProvenanceValidationError: strict=True
    """
    errors: List[str] = []
    
    # segmentation_provenance
    is_valid, provenance_errors = validate_segmentation_provenance(json_data)
    errors.extend(provenance_errors)
    
    # germline_selection_consistency
    is_consistent, consistency_errors = validate_germline_selection_consistency(json_data)
    errors.extend(consistency_errors)
    
    # 4 - Rule A: germlineprovenance
    lib_valid, lib_errors = validate_germline_library_proof(json_data)
    errors.extend(lib_errors)
    if not lib_valid:
        is_valid = False
    
    # 4 - Rule BC: germline IMGTANARCII
    numbering_valid, numbering_errors = validate_germline_numbering_proof(json_data)
    errors.extend(numbering_errors)
    if not numbering_valid:
        is_valid = False
    
    if not is_valid and strict:
        error_msg = "JSON，。\n" + "\n".join(f"  - {e}" for e in errors)
        raise SegmentationProvenanceValidationError(error_msg)
    
    return is_valid, errors


if __name__ == "__main__":
    # 
    import json
    
    # 1: provenance
    test_data_1 = {
        "segmentation_provenance": {
            "method": "anarcii",
            "scheme": "imgt",
            "implementation": {
                "package": "anarcii",
                "version": "1.0.0",
                "python": "3.11.6",
                "platform": "Windows-10",
                "commit": "abc12345"
            },
            "parameters": {
                "species": "camelid",
                "chain": "H",
                "allow_partial": True,
                "max_mismatches": 0
            },
            "evidence": {
                "numbering_first_10": [
                    {"pos": "1", "aa": "E"},
                    {"pos": "2", "aa": "V"}
                ],
                "boundaries": {
                    "FR1": [1, 26],
                    "CDR1": [27, 38],
                    "FR2": [39, 55],
                    "CDR2": [56, 65],
                    "FR3": [66, 104],
                    "CDR3": [105, 117],
                    "FR4": [118, 128]
                }
            }
        }
    }
    
    is_valid, errors = validate_segmentation_provenance(test_data_1)
    print(f"1 (provenance): {'' if is_valid else ''}")
    if errors:
        for e in errors:
            print(f"  - {e}")
    
    # 2: method
    test_data_2 = {
        "segmentation_provenance": {
            "scheme": "imgt"
        }
    }
    
    is_valid, errors = validate_segmentation_provenance(test_data_2)
    print(f"\n2 (method): {'' if is_valid else ''}")
    if errors:
        for e in errors:
            print(f"  - {e}")
    
    # 3: methodpackage
    test_data_3 = {
        "segmentation_provenance": {
            "method": "anarcii",
            "scheme": "imgt",
            "implementation": {
                "package": "anarci",  # ：anarcii
                "version": "1.0.0"
            },
            "evidence": {
                "boundaries": {
                    "FR1": [1, 26],
                    "CDR1": [27, 38],
                    "FR2": [39, 55],
                    "CDR2": [56, 65],
                    "FR3": [66, 104],
                    "CDR3": [105, 117],
                    "FR4": [118, 128]
                }
            }
        }
    }
    
    is_valid, errors = validate_segmentation_provenance(test_data_3)
    print(f"\n3 (methodpackage): {'' if is_valid else ''}")
    if errors:
        for e in errors:
            print(f"  - {e}")

