"""
IMGT - provenance

IMGT，provenance。
"""

from __future__ import annotations

import sys
import platform
from typing import Dict, Any, Optional, Tuple, List
from pathlib import Path

try:
    from anarcii import Anarcii
    HAS_ANARCII = True
except ImportError:
    HAS_ANARCII = False
    Anarcii = None

try:
    from anarci import anarci
    HAS_ANARCI = True
except ImportError:
    HAS_ANARCI = False

from core.numbering.imgt_anarcii import imgt_number_anarcii, IMGTNumberingError
from core.vhh_humanization import split_regions, IMGT_REGIONS


def _get_package_version(package_name: str) -> str:
    """"""
    try:
        import importlib.metadata
        return importlib.metadata.version(package_name)
    except Exception:
        try:
            import pkg_resources
            return pkg_resources.get_distribution(package_name).version
        except Exception:
            return "unknown"


def _get_python_version() -> str:
    """Python"""
    return f"{sys.version_info.major}.{sys.version_info.minor}.{sys.version_info.micro}"


def _get_platform_info() -> str:
    """"""
    return f"{platform.system()}-{platform.release()}"


def _get_git_commit() -> Optional[str]:
    """git commit SHA"""
    try:
        import subprocess
        result = subprocess.run(
            ["git", "rev-parse", "HEAD"],
            capture_output=True,
            text=True,
            timeout=2,
            cwd=Path(__file__).parent.parent.parent
        )
        if result.returncode == 0:
            return result.stdout.strip()[:8]  # 8
    except Exception:
        pass
    return None


def _calculate_boundaries(rows: List[Dict[str, Any]]) -> Dict[str, List[int]]:
    """
    
    
    Returns:
        {
            "FR1": [start, end],
            "CDR1": [start, end],
            ...
        }
    """
    boundaries = {}
    
    for region_name, region_info in IMGT_REGIONS.items():
        start_pos = region_info["start"]
        end_pos = region_info["end"]
        
        # 
        actual_start = None
        actual_end = None
        
        for row in rows:
            pos = row.get("pos")
            if pos is None:
                continue
            
            if start_pos <= pos <= end_pos:
                if actual_start is None:
                    actual_start = pos
                actual_end = pos
        
        if actual_start is not None and actual_end is not None:
            boundaries[region_name] = [actual_start, actual_end]
        else:
            # 
            boundaries[region_name] = [start_pos, end_pos]
    
    return boundaries


def _get_numbering_first_10(rows: List[Dict[str, Any]]) -> List[Dict[str, str]]:
    """10"""
    result = []
    for row in rows[:10]:
        pos = row.get("pos")
        aa = row.get("aa")
        if pos is not None and aa is not None:
            result.append({"pos": str(pos), "aa": str(aa)})
    return result


def run_anarcii_imgt(
    seq: str,
    species: str = "camelid",
    chain: str = "H",
    allow_partial: bool = True,
    max_mismatches: int = 0,
) -> Tuple[Dict[str, str], List[Dict[str, Any]], Dict[str, Any]]:
    """
    ANARCIIIMGT，、provenance。
    
    Args:
        seq: VHH
        species: （"camelid"）
        chain: （"H"）
        allow_partial: 
        max_mismatches: 
    
    Returns:
        (segmentation, numbering, provenance)
        
        segmentation: {
            "FR1": str,
            "CDR1": str,
            "FR2": str,
            "CDR2": str,
            "FR3": str,
            "CDR3": str,
            "FR4": str
        }
        
        numbering: List[Dict] - IMGT
        
        provenance: {
            "method": str,  # "anarcii"  "fallback:anarci"  "fallback:regex_minimal"
            "scheme": str,  # "imgt"
            "implementation": {...},
            "parameters": {...},
            "evidence": {...}
        }
    """
    method = "anarcii"
    fallback_used = None
    numbering = None
    segmentation = None
    
    # ANARCII
    if HAS_ANARCII:
        try:
            numbering = imgt_number_anarcii(seq)
            segmentation = split_regions(numbering)
            method = "anarcii"
        except (IMGTNumberingError, Exception) as e:
            # ANARCII，fallback
            fallback_used = "anarcii"
            method = None
    
    # Fallback 1: ANARCI
    if method is None and HAS_ANARCI:
        try:
            numbered, alignment_details, hit_tables = anarci([("seq", seq)], scheme="imgt")
            if numbered and numbered[0] and numbered[0][0]:
                # ANARCI
                numbering = []
                for item in numbered[0][0]:
                    if len(item) >= 2:
                        pos_info, aa = item[0], item[1]
                        if isinstance(pos_info, tuple) and len(pos_info) >= 1:
                            pos = pos_info[0]
                            ins_code = pos_info[1] if len(pos_info) > 1 else " "
                            if aa != "-" and pos is not None:
                                numbering.append({
                                    "pos": int(pos),
                                    "ins_code": str(ins_code),
                                    "aa": str(aa),
                                    "chain_type": chain,
                                    "scheme": "imgt"
                                })
                
                if numbering:
                    segmentation = split_regions(numbering)
                    method = "fallback:anarci"
        except Exception:
            pass
    
    # Fallback 2: regex_minimal（）
    if method is None:
        try:
            from core.vhh_scaffolds.cdr_parser import _heuristic_segment
            segmentation = _heuristic_segment(seq)
            # regexnumbering（IMGT）
            # provenance，
            numbering = []
            # （IMGT）
            pos = 1
            for region_name in ["FR1", "CDR1", "FR2", "CDR2", "FR3", "CDR3", "FR4"]:
                region_seq = segmentation.get(region_name, "")
                for aa in region_seq:
                    numbering.append({
                        "pos": pos,
                        "ins_code": " ",
                        "aa": aa,
                        "chain_type": chain,
                        "scheme": "imgt"
                    })
                    pos += 1
            method = "fallback:regex_minimal"
        except Exception:
            # fallback
            raise RuntimeError("All segmentation methods failed")
    
    # provenance
    if method == "anarcii":
        package_name = "anarcii"
        package_version = _get_package_version("anarcii")
    elif method == "fallback:anarci":
        package_name = "anarci"
        package_version = _get_package_version("anarci")
    else:
        package_name = "regex_minimal"
        package_version = "internal"
    
    # 
    if numbering:
        boundaries = _calculate_boundaries(numbering)
        numbering_first_10 = _get_numbering_first_10(numbering)
    else:
        # numbering，IMGT
        boundaries = {
            "FR1": [IMGT_REGIONS["FR1"]["start"], IMGT_REGIONS["FR1"]["end"]],
            "CDR1": [IMGT_REGIONS["CDR1"]["start"], IMGT_REGIONS["CDR1"]["end"]],
            "FR2": [IMGT_REGIONS["FR2"]["start"], IMGT_REGIONS["FR2"]["end"]],
            "CDR2": [IMGT_REGIONS["CDR2"]["start"], IMGT_REGIONS["CDR2"]["end"]],
            "FR3": [IMGT_REGIONS["FR3"]["start"], IMGT_REGIONS["FR3"]["end"]],
            "CDR3": [IMGT_REGIONS["CDR3"]["start"], IMGT_REGIONS["CDR3"]["end"]],
            "FR4": [IMGT_REGIONS["FR4"]["start"], IMGT_REGIONS["FR4"]["end"]],
        }
        numbering_first_10 = []
    
    provenance = {
        "method": method,
        "scheme": "imgt",
        "implementation": {
            "package": package_name,
            "version": package_version,
            "python": _get_python_version(),
            "platform": _get_platform_info(),
            "commit": _get_git_commit()
        },
        "parameters": {
            "species": species,
            "chain": chain,
            "allow_partial": allow_partial,
            "max_mismatches": max_mismatches,
            "fallbacks": ["anarci", "regex_minimal"]
        },
        "evidence": {
            "numbering_first_10": numbering_first_10,
            "boundaries": boundaries
        }
    }
    
    # fallback，parameters
    if fallback_used:
        provenance["parameters"]["fallbacks_used"] = [method]
    
    return segmentation, numbering or [], provenance

