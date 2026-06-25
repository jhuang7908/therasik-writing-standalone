"""
core.vhh_scaffolds.scaffold_provenance

：
-  scaffold ""
-  True/False ，：
  - ？(true_native)
  - ？
  -  PDB /  / ？
  -  parent （）？
-  /  / 
"""

from __future__ import annotations

from typing import Any, Dict

from .registry import get_scaffold


def build_scaffold_provenance(scaffold_id: str) -> Dict[str, Any]:
    """
     scaffold_id（ '4W6Y_B', 'NVHH-N1', 'NVHH-H1'）
     flags + 。
    """

    sc = get_scaffold(scaffold_id)

    data = sc.data

    source: Dict[str, Any] = data.get("source", {}) or {}
    design: Dict[str, Any] = data.get("design", {}) or {}
    annotations: Dict[str, Any] = data.get("annotations", {}) or {}
    
    #  parent_scaffold_id（ JSON ）
    parent_scaffold_id = data.get("parent_scaffold_id") or design.get("parent_scaffold_id")

    # ---- True / False  ----
    flags: Dict[str, bool] = {
        # ： /  / 
        "is_true_native": sc.layer == "true_native",
        "is_consensus_native": sc.layer == "consensus_native",
        "is_engineered": sc.layer == "engineered",

        # （PDB /  / ）
        "has_pdb_id": bool(source.get("pdb_id") or data.get("pdb_id")),
        "has_drug_name": bool(source.get("drug_name")),
        "has_publication": bool(source.get("publication_doi") or source.get("publication_ref") or data.get("literature")),

        #  parent （ scaffold ）
        "has_parent_scaffold": bool(parent_scaffold_id),

        #  IMGT （）
        "has_imgt_numbering_info": bool(annotations.get("imgt_numbering_scheme") or annotations.get("imgt_notes")),
    }

    # ----  ----
    provenance: Dict[str, Any] = {
        "id": sc.scaffold_id,
        "layer": sc.layer,
        "source_path": str(sc.source_path),
        "flags": flags,
        "source": {
            # ， .get()
            "pdb_id": source.get("pdb_id"),
            "chain_id": source.get("chain_id"),
            "uniprot_id": source.get("uniprot_id"),
            "drug_name": source.get("drug_name"),
            "indication": source.get("indication"),
            "publication_doi": source.get("publication_doi"),
            "publication_ref": source.get("publication_ref"),
            "notes": source.get("notes"),
        },
        "design": {
            "parent_scaffold_id": parent_scaffold_id,
            "parent_type": design.get("parent_type"),  # true_native / consensus / engineered
            "modification_summary": design.get("modification_summary"),
            "rationale": design.get("rationale"),
        },
        "annotations": {
            "imgt_numbering_scheme": annotations.get("imgt_numbering_scheme"),
            "imgt_notes": annotations.get("imgt_notes"),
        },
    }

    return provenance

