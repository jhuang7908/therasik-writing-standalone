import json
from pathlib import Path
from typing import Dict, List


# ===  ===
#  scripts ，parents[1] 
PROJECT_ROOT = Path(__file__).resolve().parents[1]
CORE_DATA_ROOT = PROJECT_ROOT / "core" / "data"


def load_camelid_vhh_germlines(base_dir: Path = None) -> Dict[str, Dict]:
    """
     core/data/vhh_camelid_reference.json  camelid VHH germline 。
    
    : {id: {"id":..., "sequence":..., "meta":{...}}}
    """
    if base_dir is None:
        base_dir = CORE_DATA_ROOT
    
    json_path = base_dir / "vhh_camelid_reference.json"
    
    if not json_path.exists():
        raise FileNotFoundError(f" camelid germline JSON: {json_path}")
    
    data = json.loads(json_path.read_text(encoding="utf-8"))
    
    lib = {}
    for entry in data.get("entries", []):
        entry_id = entry.get("id")
        if not entry_id:
            continue
        
        lib[entry_id] = {
            "id": entry_id,
            "sequence": entry.get("sequence_aa", ""),
            "meta": entry,
        }
    
    return lib


def load_human_vhh_compatible_germlines(base_dir: Path = None) -> Dict[str, Dict]:
    """
     core/data/human_VH3_germlines.json  human VH3 germline 。
    
    : {id: {"id":..., "sequence":..., "meta":{...}}}
    """
    if base_dir is None:
        base_dir = CORE_DATA_ROOT
    
    json_path = base_dir / "human_VH3_germlines.json"
    
    if not json_path.exists():
        raise FileNotFoundError(f" human germline JSON: {json_path}")
    
    data = json.loads(json_path.read_text(encoding="utf-8"))
    
    lib = {}
    for entry in data.get("entries", []):
        entry_id = entry.get("id")
        if not entry_id:
            continue
        
        lib[entry_id] = {
            "id": entry_id,
            "sequence": entry.get("sequence_aa", ""),
            "meta": entry,
        }
    
    return lib


# === ： entries  ===

def get_human_vh3_entries(base_dir: Path = None) -> List[dict]:
    """
     human VH3 entries 。
    
    :
        entries = get_human_vh3_entries()
        for entry in entries:
            print(entry["id"], entry["sequence_aa"])
    """
    if base_dir is None:
        base_dir = CORE_DATA_ROOT
    
    json_path = base_dir / "human_VH3_germlines.json"
    
    if not json_path.exists():
        return []
    
    data = json.loads(json_path.read_text(encoding="utf-8"))
    return data.get("entries", [])


def get_camelid_vhh_entries(base_dir: Path = None) -> List[dict]:
    """
     camelid VHH entries 。
    
    :
        entries = get_camelid_vhh_entries()
        for entry in entries:
            print(entry["id"], entry["sequence_aa"])
    """
    if base_dir is None:
        base_dir = CORE_DATA_ROOT
    
    json_path = base_dir / "vhh_camelid_reference.json"
    
    if not json_path.exists():
        return []
    
    data = json.loads(json_path.read_text(encoding="utf-8"))
    return data.get("entries", [])


# === ： FASTA （） ===

def _load_fasta(path: Path) -> Dict[str, str]:
    """ FASTA （）"""
    seqs = {}
    header = None
    buf: List[str] = []
    
    with path.open(encoding="utf-8", errors="ignore") as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            if line.startswith(">"):
                if header is not None:
                    seqs[header] = "".join(buf)
                header = line[1:]
                buf = []
            else:
                buf.append(line)
        if header is not None:
            seqs[header] = "".join(buf)
    return seqs




















