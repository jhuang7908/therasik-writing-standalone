"""
GermlineProvenance

1：「germline 」
- germline
- sha256
- entry_count
- germline_library_provenance
"""

from __future__ import annotations

import hashlib
import json
from datetime import datetime
from pathlib import Path
from typing import Dict, Any, Optional


def calculate_file_sha256(file_path: Path) -> str:
    """
    SHA256
    
    Args:
        file_path: 
    
    Returns:
        SHA256（）
    """
    sha256_hash = hashlib.sha256()
    with open(file_path, "rb") as f:
        for byte_block in iter(lambda: f.read(4096), b""):
            sha256_hash.update(byte_block)
    return sha256_hash.hexdigest()


def load_germline_library_with_provenance(
    library_path: Optional[Path] = None,
    library_name: str = "human_VH3_germline_library",
    source: str = "internal_consensus_scaffold",
    version: str = "v1.0",
) -> tuple[Dict[str, Any], Dict[str, Any]]:
    """
    germlineprovenance
    
    Args:
        library_path: （None，）
        library_name: 
        source: 
        version: 
    
    Returns:
        (library_data, provenance_dict)
        - library_data: （JSON）
        - provenance_dict: provenance
    """
    # ，
    if library_path is None:
        from core.utils.config_loader import get_config_lazy as get_config
        cfg = get_config()
        # 
        possible_paths = [
            cfg.paths.human_templates,  # human_vh3_vhh_safe_templates.json
            Path(cfg.paths.project_root) / "data" / "germlines" / "human_VH3_germlines.json",
            Path(cfg.paths.project_root) / "core" / "data" / "human_VH3_germlines.json",
        ]
        
        library_path = None
        for path in possible_paths:
            if path and path.exists():
                library_path = path
                break
        
        if library_path is None:
            raise FileNotFoundError(
                f"germline。: {possible_paths}"
            )
    
    library_path = Path(library_path)
    
    if not library_path.exists():
        raise FileNotFoundError(f"Germline: {library_path}")
    
    # 
    with open(library_path, "r", encoding="utf-8") as f:
        library_data = json.load(f)
    
    # SHA256
    sha256 = calculate_file_sha256(library_path)
    
    # entry_count
    # JSON
    entry_count = 0
    if isinstance(library_data, list):
        entry_count = len(library_data)
    elif isinstance(library_data, dict):
        if "entries" in library_data:
            entry_count = len(library_data["entries"])
        elif "templates" in library_data:
            entry_count = len(library_data["templates"])
        else:
            # 
            entry_count = len([k for k in library_data.keys() if not k.startswith("_")])
    
    # 
    file_format = "json"
    if library_path.suffix.lower() == ".fasta":
        file_format = "fasta"
    
    # provenance
    provenance = {
        "library_name": library_name,
        "source": source,
        "format": file_format,
        "path": str(library_path.relative_to(Path.cwd())) if library_path.is_relative_to(Path.cwd()) else str(library_path),
        "absolute_path": str(library_path.resolve()),
        "version": version,
        "entry_count": entry_count,
        "sha256": sha256,
        "loaded_at": datetime.utcnow().strftime("%Y-%m-%dT%H:%M:%SZ"),
    }
    
    return library_data, provenance


def build_germline_library_provenance(
    json_data: Dict[str, Any],
    library_path: Optional[Path] = None,
) -> Dict[str, Any]:
    """
    JSONgermline_library_provenance
    
    Args:
        json_data: JSON
        library_path: （，）
    
    Returns:
        germline_library_provenance
    """
    # best_match
    best_match = json_data.get("best_match", {})
    template = best_match.get("template", {}) or {}
    template_id = template.get("template_id") or best_match.get("template_id", "")
    
    # template_id
    if "VH3" in template_id or "HUMAN_VH3" in template_id:
        library_name = "human_VH3_germline_library"
        source = "internal_consensus_scaffold"
        version = "v1.0"
    else:
        library_name = "germline_library"
        source = "internal_consensus_scaffold"
        version = "v1.0"
    
    try:
        library_data, provenance = load_germline_library_with_provenance(
            library_path=library_path,
            library_name=library_name,
            source=source,
            version=version,
        )
        return provenance
    except FileNotFoundError as e:
        # ，provenance
        return {
            "library_name": library_name,
            "source": source,
            "format": "unknown",
            "path": "NOT_FOUND",
            "version": version,
            "entry_count": 0,
            "sha256": "",
            "loaded_at": datetime.utcnow().strftime("%Y-%m-%dT%H:%M:%SZ"),
            "error": str(e),
        }













