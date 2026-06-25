"""
core.vhh_scaffolds.registry

：
-  true_native / consensus / engineered  JSON
-  scaffold_id / ref_id 
-  pipeline（CDR 、、）
"""

from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Dict, Optional, Literal

# ：
BASE_DIR = Path(__file__).resolve().parent

TRUE_NATIVE_DIR = BASE_DIR / "01_true_native"
CONSENSUS_DIR = BASE_DIR / "02_consensus_native"
ENGINEERED_DIR = BASE_DIR / "03_engineered"
METADATA_DIR = BASE_DIR / "04_metadata"


def _load_json(path: Path) -> Dict[str, Any]:
    with path.open("r", encoding="utf-8") as f:
        return json.load(f)


# ========= （） =========

@dataclass
class Scaffold:
    scaffold_id: str
    layer: Literal["true_native", "consensus_native", "engineered"]
    data: Dict[str, Any]
    source_path: Path

    def get_fr(self, idx: int) -> Optional[str]:
        """
         FR1/FR2/FR3/FR4，idx=1..4
         consensus / engineered scaffold 。
        """
        fr_key = f"FR{idx}"
        framework = self.data.get("framework_sequences") or {}
        return framework.get(fr_key)

    @property
    def description(self) -> str:
        return self.data.get("description", "")


# ========= true_native  =========

def list_true_native_ids() -> Dict[str, Path]:
    """
     {ref_id: path}， {"PDB_4W6Y_B": Path(...)}。
    """
    mapping: Dict[str, Path] = {}
    if not TRUE_NATIVE_DIR.exists():
        return mapping

    for p in TRUE_NATIVE_DIR.glob("*.json"):
        obj = _load_json(p)
        ref_id = obj.get("id")
        if ref_id:
            mapping[ref_id] = p
    return mapping


def get_true_native(ref_id: str) -> Dict[str, Any]:
    """
     01_true_native  id  JSON。
    ref_id ："PDB_4W6Y_B"、"PDB_6EZW_A"
    """
    mapping = list_true_native_ids()
    path = mapping.get(ref_id)
    if path is None:
        raise KeyError(f"true_native ref_id not found: {ref_id}")
    return _load_json(path)


# ========= scaffold（N1/H1 ） =========

def _find_scaffold_path(scaffold_id: str) -> Path:
    """
     scaffold_id  02 / 03  JSON 。
    ： = scaffold_id  + '.json'
    :
        NVHH-N1 -> 02_consensus_native/nvhh_n1.json
        NVHH-H1 -> 03_engineered/nvhh_h1.json
    """
    fname = scaffold_id.lower().replace("-", "_") + ".json"

    #  layer 
    candidate_paths = [
        CONSENSUS_DIR / fname,
        ENGINEERED_DIR / fname,
    ]

    for p in candidate_paths:
        if p.exists():
            return p

    raise FileNotFoundError(
        f"Scaffold JSON not found for id={scaffold_id!r}. "
        f"Looked for {candidate_paths}"
    )


def get_scaffold(scaffold_id: str) -> Scaffold:
    """
    ： scaffold_id  Scaffold 。
    -  N1/N2/N3 ：layer='consensus_native'
    -  H1/H2/H3 ：layer='engineered'
    """
    path = _find_scaffold_path(scaffold_id)
    data = _load_json(path)

    #  JSON  layer ，，
    layer: Optional[str] = data.get("layer")
    if layer is None:
        if path.is_relative_to(CONSENSUS_DIR):
            layer = "consensus_native"
        elif path.is_relative_to(ENGINEERED_DIR):
            layer = "engineered"
        else:
            layer = "engineered"  # 

    return Scaffold(
        scaffold_id=scaffold_id,
        layer=layer,  # type: ignore[arg-type]
        data=data,
        source_path=path,
    )


# ========= （IMGT / hallmarks） =========

def load_imgt_rules() -> Dict[str, Any]:
    path = METADATA_DIR / "imgt_numbering_rules.json"
    if not path.exists():
        raise FileNotFoundError("imgt_numbering_rules.json not found")
    return _load_json(path)


def load_vhh_hallmarks() -> Dict[str, Any]:
    path = METADATA_DIR / "vhh_hallmarks.json"
    if not path.exists():
        raise FileNotFoundError("vhh_hallmarks.json not found")
    return _load_json(path)


# ========= ： evaluate_fr2_hallmarks / summarize_scaffold  =========
# ：
#
# def summarize_scaffold(scaffold_id: str) -> Dict[str, Any]:
#     scaffold = get_scaffold(scaffold_id)
#     #  hallmarks / IMGT 
#     return {
#         "id": scaffold.scaffold_id,
#         "layer": scaffold.layer,
#         "description": scaffold.description,
#         "has_fr_sequences": "framework_sequences" in scaffold.data,
#     }

