"""
Generic CMC scanning logic for antibody sequences.

This module provides sequence-based CMC (Chemistry, Manufacturing, Controls)
liability scanning without requiring structural information or external APIs.
Can be used for VHH, conventional antibodies, and other antibody formats.
"""

from typing import Dict, List, Optional


def scan_cmc_liabilities(seq: str) -> Dict:
    """
    Basic CMC risk scanning for antibody sequences.
    
    Scans for common CMC liabilities:
    - N-glycosylation sites (NXS/T, X != P)
    - Deamidation sites (NG, NS, NN)
    - Isomerization sites (DP, DS, DG, DT)
    - Oxidation sites (M, W residues)
    
    Args:
        seq: Amino acid sequence (uppercase letters expected)
        
    Returns:
        Dictionary containing:
        {
            "length": int,
            "n_glyc_sites": List[Dict],  # N-glycosylation sites
            "deamidation_sites": List[Dict],  # Deamidation sites
            "isomerization_sites": List[Dict],  # Isomerization sites
            "oxidation_sites": List[Dict],  # Oxidation sites
            "summary": {
                "total_flags": int,
                "risk_level": str  # "low" / "medium" / "high"
            }
        }
        
    Raises:
        ValueError: If sequence is empty or contains invalid characters
    """
    # Basic validation
    if not seq:
        raise ValueError("Sequence cannot be empty")
    
    seq = seq.upper().strip()
    
    # Validate sequence contains only valid amino acids
    valid_aas = set('ACDEFGHIKLMNPQRSTVWY')
    if not all(c in valid_aas for c in seq):
        invalid_chars = [c for c in set(seq) if c not in valid_aas]
        raise ValueError(f"Sequence contains invalid characters: {invalid_chars}")
    
    # Scan for different liability types
    n_glyc_sites = _scan_n_glyc(seq)
    deamidation_sites = _scan_deamidation(seq)
    isomerization_sites = _scan_isomerization(seq)
    oxidation_sites = _scan_oxidation(seq)
    
    # Calculate summary
    total_flags = (
        len(n_glyc_sites) +
        len(deamidation_sites) +
        len(isomerization_sites) +
        len(oxidation_sites)
    )
    
    # Determine risk level
    if total_flags == 0:
        risk_level = "low"
    elif 1 <= total_flags <= 4:
        risk_level = "medium"
    else:  # total_flags >= 5
        risk_level = "high"
    
    return {
        "length": len(seq),
        "n_glyc_sites": n_glyc_sites,
        "deamidation_sites": deamidation_sites,
        "isomerization_sites": isomerization_sites,
        "oxidation_sites": oxidation_sites,
        "summary": {
            "total_flags": total_flags,
            "risk_level": risk_level
        }
    }


def _scan_n_glyc(seq: str) -> List[Dict]:
    """
    Scan for N-glycosylation sites (NXS/T motif, where X != P).
    
    N-glycosylation consensus sequence: Asn-X-Ser/Thr (NXS/T)
    where X is any amino acid except Proline.
    
    Args:
        seq: Amino acid sequence
        
    Returns:
        List of risk site dictionaries
    """
    sites = []
    
    # Scan with sliding window of length 3
    for i in range(len(seq) - 2):
        pos1 = i + 1  # 1-based position
        pos2 = i + 2
        pos3 = i + 3
        
        aa1 = seq[i]
        aa2 = seq[i + 1]
        aa3 = seq[i + 2]
        
        # Check for NXS/T pattern (X != P)
        if aa1 == 'N' and aa2 != 'P' and aa3 in ['S', 'T']:
            motif = f"{aa1}{aa2}{aa3}"
            sites.append({
                "position": pos1,  # Position of N
                "aa": aa1,
                "motif": motif,
                "category": "glycosylation",
                "region_hint": None
            })
    
    return sites


def _scan_deamidation(seq: str) -> List[Dict]:
    """
    Scan for deamidation sites (NG, NS, NN motifs).
    
    Deamidation is a common degradation pathway where Asn (N) residues
    can undergo deamidation, especially in NG, NS, and NN contexts.
    
    Args:
        seq: Amino acid sequence
        
    Returns:
        List of risk site dictionaries
    """
    sites = []
    
    # Scan for NG, NS, NN patterns (2-residue motifs)
    for i in range(len(seq) - 1):
        pos = i + 1  # 1-based position
        aa1 = seq[i]
        aa2 = seq[i + 1]
        
        # Check for deamidation-prone motifs
        if aa1 == 'N' and aa2 in ['G', 'S', 'N']:
            motif = f"{aa1}{aa2}"
            sites.append({
                "position": pos,  # Position of N
                "aa": aa1,
                "motif": motif,
                "category": "deamidation",
                "region_hint": None
            })
    
    return sites


def _scan_isomerization(seq: str) -> List[Dict]:
    """
    Scan for isomerization sites (DP, DS, DG, DT motifs).
    
    Aspartic acid (D) can undergo isomerization to isoaspartic acid,
    particularly in DP, DS, DG, and DT contexts.
    
    Args:
        seq: Amino acid sequence
        
    Returns:
        List of risk site dictionaries
    """
    sites = []
    
    # Scan for DP, DS, DG, DT patterns (2-residue motifs)
    for i in range(len(seq) - 1):
        pos = i + 1  # 1-based position
        aa1 = seq[i]
        aa2 = seq[i + 1]
        
        # Check for isomerization-prone motifs
        if aa1 == 'D' and aa2 in ['P', 'S', 'G', 'T']:
            motif = f"{aa1}{aa2}"
            sites.append({
                "position": pos,  # Position of D
                "aa": aa1,
                "motif": motif,
                "category": "isomerization",
                "region_hint": None
            })
    
    return sites


def _scan_oxidation(seq: str) -> List[Dict]:
    """
    Scan for oxidation sites (Methionine and Tryptophan residues).
    
    Methionine (M) and Tryptophan (W) are susceptible to oxidation,
    which can affect protein stability and function.
    
    Args:
        seq: Amino acid sequence
        
    Returns:
        List of risk site dictionaries
    """
    sites = []
    
    # Scan for M and W residues
    for i, aa in enumerate(seq):
        if aa in ['M', 'W']:
            pos = i + 1  # 1-based position
            motif = aa
            category = "oxidation"
            
            sites.append({
                "position": pos,
                "aa": aa,
                "motif": motif,
                "category": category,
                "region_hint": None
            })
    
    return sites


# Legacy class for backward compatibility (optional)
class GenericCMCScanner:
    """
    Generic CMC scanner for antibody sequences.
    
    This class provides a wrapper around the functional API.
    """
    
    @staticmethod
    def scan(seq: str) -> Dict:
        """
        Scan sequence for CMC liabilities.
        
        Args:
            seq: Amino acid sequence
            
        Returns:
            Dictionary with CMC scan results
        """
        return scan_cmc_liabilities(seq)


if __name__ == "__main__":
    # Self-test code
    test_seq = "QVQLVESGGGLVQPGGSLRLSCAASGFPYNHMGWFRQAPGKEREGVAVITADSGSTTYADSVKGRFTISRDDARNTVYLQMNSLKPEDTAVYYCAAGGVGWPYFDYWGQGTQVTVSS"
    
    print("=" * 80)
    print("CMC Liability Scanner - Self Test")
    print("=" * 80)
    print(f"\nTest sequence: {test_seq}")
    print(f"Sequence length: {len(test_seq)}")
    print()
    
    try:
        result = scan_cmc_liabilities(test_seq)
        
        print("Scan Results:")
        print(f"  Length: {result['length']}")
        print(f"  Total flags: {result['summary']['total_flags']}")
        print(f"  Risk level: {result['summary']['risk_level']}")
        print()
        
        print("Detailed Results:")
        print(f"  N-glycosylation sites: {len(result['n_glyc_sites'])}")
        if result['n_glyc_sites']:
            for site in result['n_glyc_sites']:
                print(f"    Position {site['position']}: {site['motif']} ({site['category']})")
        
        print(f"  Deamidation sites: {len(result['deamidation_sites'])}")
        if result['deamidation_sites']:
            for site in result['deamidation_sites']:
                print(f"    Position {site['position']}: {site['motif']} ({site['category']})")
        
        print(f"  Isomerization sites: {len(result['isomerization_sites'])}")
        if result['isomerization_sites']:
            for site in result['isomerization_sites']:
                print(f"    Position {site['position']}: {site['motif']} ({site['category']})")
        
        print(f"  Oxidation sites: {len(result['oxidation_sites'])}")
        if result['oxidation_sites']:
            for site in result['oxidation_sites']:
                print(f"    Position {site['position']}: {site['aa']} ({site['category']})")
        
        print()
        print("=" * 80)
        
    except Exception as e:
        print(f"Error during scanning: {e}")
        import traceback
        traceback.print_exc()

