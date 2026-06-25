"""
VHH Classic Germline FR Panel - Hardcoded Scaffolds

4classic human germline scaffold（FR1/FR2/FR3）+ FR4（IGHJ4/IGHJ6）
SHA256，。
"""

from __future__ import annotations

import hashlib
from typing import Dict, Any, List
from dataclasses import dataclass


@dataclass
class ClassicScaffold:
    """Classic scaffold"""
    scaffold_id: str
    fr1: str
    fr2: str
    fr3: str
    cdr1: str  # CDR1（canonical profile）
    cdr2: str  # CDR2（canonical profile）
    source_authority: str
    version: str
    sequence_sha256: str


@dataclass
class ClassicJRegion:
    """Classic J region (FR4)"""
    j_region_id: str
    fr4: str
    source_authority: str
    version: str
    sequence_sha256: str


# ============================================================================
# Classic Scaffolds (FR1/FR2/FR3)
# ============================================================================

CLASSIC_SCAFFOLDS: Dict[str, ClassicScaffold] = {
    "IGHV3-23*01": ClassicScaffold(
        scaffold_id="IGHV3-23*01",
        fr1="EVQLLESGGGLVQPGGSLRLSCAAS",
        fr2="MSWVRQAPGKGLEWVSA",
        fr3="YYADSVKGRFTISRDNSKNTLYLQMNSLRAEDTAVYYC",
        cdr1="GFTFSSYA",  # 8，IMGT 27-38
        cdr2="ISGSGGST",  # 8，IMGT 56-65
        source_authority="IMGT/DomainGapAlign curated",
        version="v1.0",
        sequence_sha256="",  # 
    ),
    "IGHV3-66*01": ClassicScaffold(
        scaffold_id="IGHV3-66*01",
        fr1="EVQLVESGGGLVQPGGSLRLSCAAS",
        fr2="MSWVRQAPGKGLEWVSV",
        fr3="YYADSVKGRFTISRDNSKNTLYLQMNSLRAEDTAVYYC",
        cdr1="GFTVSSNY",  # 8，IMGT 27-38
        cdr2="IYSGGST",   # 7，IMGT 56-65（62）
        source_authority="IMGT/DomainGapAlign curated",
        version="v1.0",
        sequence_sha256="",  # 
    ),
    "IGHV3-30*01": ClassicScaffold(
        scaffold_id="IGHV3-30*01",
        fr1="QVQLVESGGGVVQPGRSLRLSCAAS",
        fr2="MHWVRQAPGKGLEWVAV",
        fr3="YYADSVKGRFTISRDNSKNTLYLQMNSLRAEDTAVYYC",
        cdr1="GFTFSSYA",  # 8，IMGT 27-38
        cdr2="ISYDGSNK",  # 8，IMGT 56-65
        source_authority="IMGT/DomainGapAlign curated",
        version="v1.0",
        sequence_sha256="",  # 
    ),
    "IGHV3-7*01": ClassicScaffold(
        scaffold_id="IGHV3-7*01",
        fr1="EVQLVESGGGLVQPGGSLRLSCAAS",
        fr2="MSWVRQAPGKGLEWVAN",
        fr3="YYVDSVKGRFTISRDNAKNSLYLQMNSLRAEDTAVYYC",
        cdr1="GFTFSSYW",  # 8，IMGT 27-38
        cdr2="IKQDGSEK",  # 8，IMGT 56-65
        source_authority="IMGT/DomainGapAlign curated",
        version="v1.0",
        sequence_sha256="",  # 
    ),
}

# ============================================================================
# Classic J Regions (FR4)
# ============================================================================

CLASSIC_J_REGIONS: Dict[str, ClassicJRegion] = {
    "IGHJ4": ClassicJRegion(
        j_region_id="IGHJ4",
        fr4="WGQGTLVTVSS",
        source_authority="IMGT/DomainGapAlign curated",
        version="v1.0",
        sequence_sha256="",  # 
    ),
    "IGHJ6": ClassicJRegion(
        j_region_id="IGHJ6",
        fr4="WGQGTTVTVSS",
        source_authority="IMGT/DomainGapAlign curated",
        version="v1.0",
        sequence_sha256="",  # 
    ),
}


def _compute_sha256(sequence: str) -> str:
    """SHA256"""
    return hashlib.sha256(sequence.encode('utf-8')).hexdigest()


def _initialize_sha256():
    """scaffoldJ regionSHA256"""
    for scaffold in CLASSIC_SCAFFOLDS.values():
        framework_full = scaffold.fr1 + scaffold.fr2 + scaffold.fr3
        scaffold.sequence_sha256 = _compute_sha256(framework_full)
    
    for j_region in CLASSIC_J_REGIONS.values():
        j_region.sequence_sha256 = _compute_sha256(j_region.fr4)


# SHA256
_initialize_sha256()


def get_classic_scaffold(scaffold_id: str) -> ClassicScaffold:
    """
    classic scaffold
    
    Args:
        scaffold_id: scaffold ID ( "IGHV3-23*01")
    
    Returns:
        ClassicScaffold
    
    Raises:
        KeyError: scaffold_id
    """
    if scaffold_id not in CLASSIC_SCAFFOLDS:
        raise KeyError(f"Unknown scaffold_id: {scaffold_id}")
    return CLASSIC_SCAFFOLDS[scaffold_id]


def get_classic_j_region(j_region_id: str) -> ClassicJRegion:
    """
    classic J region
    
    Args:
        j_region_id: J region ID ( "IGHJ4")
    
    Returns:
        ClassicJRegion
    
    Raises:
        KeyError: j_region_id
    """
    if j_region_id not in CLASSIC_J_REGIONS:
        raise KeyError(f"Unknown j_region_id: {j_region_id}")
    return CLASSIC_J_REGIONS[j_region_id]


def get_all_scaffold_ids() -> List[str]:
    """scaffold ID"""
    return list(CLASSIC_SCAFFOLDS.keys())


def get_all_j_region_ids() -> List[str]:
    """J region ID"""
    return list(CLASSIC_J_REGIONS.keys())


def validate_scaffold_integrity(scaffold_id: str) -> bool:
    """
    scaffold（SHA256）
    
    Args:
        scaffold_id: scaffold ID
    
    Returns:
        True if integrity check passes, False otherwise
    """
    try:
        scaffold = get_classic_scaffold(scaffold_id)
        framework_full = scaffold.fr1 + scaffold.fr2 + scaffold.fr3
        computed_hash = _compute_sha256(framework_full)
        return computed_hash == scaffold.sequence_sha256
    except KeyError:
        return False


def validate_j_region_integrity(j_region_id: str) -> bool:
    """
    J region（SHA256）
    
    Args:
        j_region_id: J region ID
    
    Returns:
        True if integrity check passes, False otherwise
    """
    try:
        j_region = get_classic_j_region(j_region_id)
        computed_hash = _compute_sha256(j_region.fr4)
        return computed_hash == j_region.sequence_sha256
    except KeyError:
        return False


def get_scaffold_framework_full(scaffold_id: str) -> str:
    """
    scaffoldframework（FR1+FR2+FR3）
    
    Args:
        scaffold_id: scaffold ID
    
    Returns:
        framework
    """
    scaffold = get_classic_scaffold(scaffold_id)
    return scaffold.fr1 + scaffold.fr2 + scaffold.fr3

