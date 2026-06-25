"""
FR2 Engineering Logic and Decision Tables for VHH.

This module implements FR2 (Framework Region 2) engineering strategies for VHH
humanization. FR2 is a critical region for solubility and immunogenicity reduction.

Key FR2 positions (IMGT numbering):
- Positions 37-49 are typically in FR2
- Critical positions: 37, 39, 40, 44, 45, 46, 47, 48
"""

from typing import Dict, List, Tuple, Optional
import re
from scripts.anarci_abnumber_adapter import annotate_chain


class VHHFR2Engineer:
    """
    FR2 engineering module for VHH humanization.
    
    Implements decision tables for three strategies:
    - Conservative: Minimal mutations, preserve original structure
    - Balanced: Moderate mutations, balance humanization and function
    - Aggressive: Maximum humanization, prioritize human-like sequence
    """
    
    # FR2 key positions in IMGT numbering (approximate, may vary)
    FR2_POSITIONS = [37, 39, 40, 41, 42, 43, 44, 45, 46, 47, 48, 49]
    
    # Decision table: {position: {original_aa: {strategy: target_aa}}}
    # None means no mutation for that strategy
    FR2_DECISION_TABLE = {
        # Position 37: V -> F (human VH3 common)
        37: {
            'V': {'conservative': None, 'balanced': 'F', 'aggressive': 'F'},
            'F': {'conservative': None, 'balanced': None, 'aggressive': None},
            'L': {'conservative': None, 'balanced': 'F', 'aggressive': 'F'},
            # Other AAs: no change in conservative, F in balanced/aggressive
        },
        # Position 39: Q -> E (human VH3)
        39: {
            'Q': {'conservative': None, 'balanced': 'E', 'aggressive': 'E'},
            'E': {'conservative': None, 'balanced': None, 'aggressive': None},
            'K': {'conservative': None, 'balanced': 'E', 'aggressive': 'E'},
        },
        # Position 40: V -> V (usually no change, but can be L in some cases)
        40: {
            'V': {'conservative': None, 'balanced': None, 'aggressive': None},
            'L': {'conservative': None, 'balanced': 'V', 'aggressive': 'V'},
            'I': {'conservative': None, 'balanced': 'V', 'aggressive': 'V'},
        },
        # Position 44: G -> K (human VH3, critical for solubility)
        44: {
            'G': {'conservative': None, 'balanced': 'K', 'aggressive': 'K'},
            'K': {'conservative': None, 'balanced': None, 'aggressive': None},
            'R': {'conservative': None, 'balanced': 'K', 'aggressive': 'K'},
            'A': {'conservative': None, 'balanced': 'K', 'aggressive': 'K'},
        },
        # Position 45: R -> L (human VH3, critical for solubility)
        45: {
            'R': {'conservative': None, 'balanced': 'L', 'aggressive': 'L'},
            'L': {'conservative': None, 'balanced': None, 'aggressive': None},
            'K': {'conservative': None, 'balanced': 'L', 'aggressive': 'L'},
            'Q': {'conservative': None, 'balanced': 'L', 'aggressive': 'L'},
        },
        # Position 46: L -> W (human VH3)
        46: {
            'L': {'conservative': None, 'balanced': 'W', 'aggressive': 'W'},
            'W': {'conservative': None, 'balanced': None, 'aggressive': None},
            'F': {'conservative': None, 'balanced': 'W', 'aggressive': 'W'},
            'V': {'conservative': None, 'balanced': 'W', 'aggressive': 'W'},
        },
        # Position 47: W -> G (human VH3, critical for solubility)
        47: {
            'W': {'conservative': None, 'balanced': 'G', 'aggressive': 'G'},
            'G': {'conservative': None, 'balanced': None, 'aggressive': None},
            'Y': {'conservative': None, 'balanced': 'G', 'aggressive': 'G'},
            'F': {'conservative': None, 'balanced': 'G', 'aggressive': 'G'},
        },
        # Position 48: G -> G (usually no change)
        48: {
            'G': {'conservative': None, 'balanced': None, 'aggressive': None},
            'A': {'conservative': None, 'balanced': 'G', 'aggressive': 'G'},
        },
    }
    
    # Human VH3 consensus FR2 sequence (positions 37-49, IMGT)
    HUMAN_VH3_FR2_CONSENSUS = {
        37: 'F',
        39: 'E',
        40: 'V',
        44: 'K',
        45: 'L',
        46: 'W',
        47: 'G',
        48: 'G',
    }
    
    def __init__(self, strategy: str = 'balanced'):
        """
        Initialize FR2 engineer.
        
        Args:
            strategy: Engineering strategy ('conservative', 'balanced', 'aggressive')
        """
        self.strategy = strategy.lower()
        if self.strategy not in ['conservative', 'balanced', 'aggressive']:
            raise ValueError(f"Invalid strategy: {strategy}. Must be 'conservative', 'balanced', or 'aggressive'")
    
    def apply_fr2_mutations(self, sequence: str, fr2_start: int, fr2_end: int, 
                           position_mapping: Optional[Dict[int, int]] = None) -> Tuple[str, List[Dict]]:
        """
        Apply FR2 mutations based on strategy and decision table.
        
        Args:
            sequence: Full VHH sequence
            fr2_start: Start position of FR2 in sequence (0-indexed)
            fr2_end: End position of FR2 in sequence (0-indexed, exclusive)
            position_mapping: Optional mapping from IMGT position to sequence index
                            If None, assumes sequence positions align with IMGT
            
        Returns:
            Tuple of (mutated_sequence, mutations_list)
            mutations_list: List of dicts with keys: position, original, mutated, strategy
        """
        if position_mapping is None:
            # Simple mapping: assume IMGT position 1 = sequence index 0
            # This is a placeholder - real implementation needs proper IMGT numbering
            position_mapping = {imgt_pos: imgt_pos - 1 for imgt_pos in self.FR2_POSITIONS}
        
        mutations = []
        sequence_list = list(sequence)
        
        # Apply mutations based on decision table
        for imgt_pos, seq_idx in position_mapping.items():
            if imgt_pos not in self.FR2_DECISION_TABLE:
                continue
            
            if seq_idx < 0 or seq_idx >= len(sequence):
                continue
            
            original_aa = sequence_list[seq_idx]
            decision_table = self.FR2_DECISION_TABLE[imgt_pos]
            
            # Check if we have a decision for this amino acid
            if original_aa in decision_table:
                target_aa = decision_table[original_aa].get(self.strategy)
            else:
                # For unknown AAs, check if we should mutate to consensus
                target_aa = self._get_consensus_mutation(imgt_pos, original_aa)
            
            if target_aa and target_aa != original_aa:
                sequence_list[seq_idx] = target_aa
                mutations.append({
                    'position': imgt_pos,
                    'sequence_index': seq_idx,
                    'original': original_aa,
                    'mutated': target_aa,
                    'strategy': self.strategy,
                    'region': 'FR2'
                })
        
        mutated_sequence = ''.join(sequence_list)
        return mutated_sequence, mutations
    
    def _get_consensus_mutation(self, imgt_pos: int, original_aa: str) -> Optional[str]:
        """
        Get consensus mutation for a position based on strategy.
        
        Args:
            imgt_pos: IMGT position number
            original_aa: Original amino acid
            
        Returns:
            Target amino acid or None if no mutation
        """
        if imgt_pos not in self.HUMAN_VH3_FR2_CONSENSUS:
            return None
        
        consensus_aa = self.HUMAN_VH3_FR2_CONSENSUS[imgt_pos]
        
        if original_aa == consensus_aa:
            return None
        
        # Strategy-based decision
        if self.strategy == 'conservative':
            # Conservative: only mutate if it's a critical position and very different
            critical_positions = [44, 45, 47]  # Most critical for solubility
            if imgt_pos in critical_positions:
                return consensus_aa
            return None
        elif self.strategy == 'balanced':
            # Balanced: mutate to consensus for most positions
            return consensus_aa
        else:  # aggressive
            # Aggressive: always mutate to consensus
            return consensus_aa
    
    def get_mutation_summary(self, mutations: List[Dict]) -> Dict:
        """
        Generate a summary of mutations.
        
        Args:
            mutations: List of mutation dictionaries
            
        Returns:
            Summary dictionary with counts and details
        """
        return {
            'total_mutations': len(mutations),
            'strategy': self.strategy,
            'mutations_by_position': {m['position']: m for m in mutations},
            'critical_mutations': [m for m in mutations if m['position'] in [44, 45, 47]],
            'description': self._get_strategy_description()
        }
    
    def _get_strategy_description(self) -> str:
        """Get description of current strategy."""
        descriptions = {
            'conservative': 'Minimal mutations, preserves original structure and function',
            'balanced': 'Moderate mutations, balances humanization and function preservation',
            'aggressive': 'Maximum humanization, prioritizes human-like sequence'
        }
        return descriptions.get(self.strategy, 'Unknown strategy')
    
    @staticmethod
    def get_strategy_differences() -> Dict:
        """
        Get detailed comparison of strategy differences.
        
        Returns:
            Dictionary comparing the three strategies
        """
        return {
            'conservative': {
                'description': 'Minimal mutations, preserves original structure',
                'typical_mutations': 0-2,
                'key_positions_mutated': [44, 45],  # Only most critical
                'risk_level': 'Low - minimal functional impact',
                'use_case': 'When preserving binding affinity is critical'
            },
            'balanced': {
                'description': 'Moderate mutations, balances humanization and function',
                'typical_mutations': 3-5,
                'key_positions_mutated': [37, 39, 44, 45, 46, 47],
                'risk_level': 'Medium - moderate functional impact',
                'use_case': 'General purpose humanization (recommended)'
            },
            'aggressive': {
                'description': 'Maximum humanization, prioritizes human-like sequence',
                'typical_mutations': 6-8,
                'key_positions_mutated': [37, 39, 40, 44, 45, 46, 47, 48],
                'risk_level': 'Higher - may affect binding, requires validation',
                'use_case': 'When maximum humanization is required'
            }
        }


# FR2 Strategy Table for direct sequence engineering
FR2_STRATEGY_TABLE = {
    "human_residue": {
        37: 'V',
        44: 'G',
        45: 'L',
        47: 'W'
    },
    "recommendation": {
        37: 'F',  # Optional for balanced
        44: 'E',
        45: 'R',
        47: 'W'  # Keep W unless input is not W
    },
    "camelid_typical": {
        37: 'F',
        44: 'R',  # or Q, K
        45: 'L',  # or Q, K
        47: 'W'
    }
}


def apply_fr2_engineering(seq: str, strategy: str = 'balanced') -> Dict[str, str]:
    """
    Apply FR2 engineering to generate variants using three strategies.
    
    Input: VHH amino acid sequence (unnumbered)
    Output: Dictionary with three variant sequences:
        {
            "conservative": <seq1>,
            "balanced": <seq2>,
            "aggressive": <seq3>
        }
    
    Rules:
        conservative:
            - Only modify position 37 (F→V optional)
            - Don't force changes at 44/45/47 unless clearly non-camelid
        
        balanced (default):
            - Use FR2_STRATEGY_TABLE["recommendation"]
            - 44->E, 45->R, 47 keep W (unless input is not W)
            - Output variant_B
        
        aggressive:
            - Force apply human_residue (37->V, 44->G, 45->L, 47->W)
            - Output variant_A
    
    Args:
        seq: Input VHH amino acid sequence
        strategy: Strategy to use (not used, always generates all three)
    
    Returns:
        Dictionary with keys: "conservative", "balanced", "aggressive"
    """
    seq = seq.upper()
    results = {}
    mutations_log = {}
    annotation = None  # Initialize annotation variable
    
    seq_len = len(seq)
    if seq_len < 30:
        # Very short sequence, return original for all
        return {
            "conservative": seq,
            "balanced": seq,
            "aggressive": seq
        }
    
    # Use annotate_chain to get proper IMGT numbering and FR2 region
    try:
        annotation = annotate_chain(
            sequence=seq,
            chain_type="H",  # VHH is a heavy chain variant
            scheme="imgt"
        )
        
        # Get FR2 region boundaries from annotation
        if "FR2" in annotation.regions:
            fr2_start, fr2_end = annotation.regions["FR2"]
        else:
            # Fallback if FR2 not found
            fr2_start = 13
            fr2_end = min(27, seq_len - 10)
        
        # Create position mapping from IMGT positions to sequence indices
        # Key IMGT positions: 37, 39, 40, 44, 45, 46, 47, 48
        position_mapping = {}
        key_imgt_positions = [37, 39, 40, 44, 45, 46, 47, 48]
        
        for imgt_pos in key_imgt_positions:
            pos_record = annotation.get_position_by_scheme_number(str(imgt_pos))
            if pos_record:
                position_mapping[imgt_pos] = pos_record.sequence_index
            else:
                # Fallback: estimate position if not found
                # This should rarely happen with proper annotation
                relative_pos = imgt_pos - 37  # Relative to position 37
                estimated_idx = fr2_start + relative_pos
                if 0 <= estimated_idx < seq_len:
                    position_mapping[imgt_pos] = estimated_idx
        
    except Exception as e:
        # Fallback to old estimation method if annotation fails
        print(f"Warning: Failed to annotate sequence with annotate_chain: {e}")
        print("Falling back to estimated FR2 positions.")
        
        fr2_start = 13
        fr2_end = min(27, seq_len - 10)
        
        position_mapping = {
            37: fr2_start,
            39: fr2_start + 2,
            40: fr2_start + 4,
            44: fr2_start + 8,
            45: fr2_start + 10,
            46: fr2_start + 12,
            47: fr2_start + 14,
            48: fr2_start + 16,
        }
        
        # Adjust positions to be within sequence bounds
        for pos, idx in list(position_mapping.items()):
            if idx >= seq_len:
                position_mapping[pos] = seq_len - 1
            if idx < 0:
                position_mapping[pos] = 0
    
    # ===== CONSERVATIVE STRATEGY =====
    conservative_seq = list(seq)
    conservative_mutations = []
    
    # Only modify position 37 (F→V optional)
    pos37_idx = position_mapping.get(37)
    if pos37_idx and pos37_idx < len(conservative_seq):
        if conservative_seq[pos37_idx] == 'F':
            # Optional: F→V (but conservative says optional, so we'll skip)
            # Only change if clearly needed
            pass
        elif conservative_seq[pos37_idx] not in ['V', 'F']:
            # If clearly non-camelid, change to V
            conservative_seq[pos37_idx] = 'V'
            conservative_mutations.append(f"Pos37: {seq[pos37_idx]}→V")
    
    # Don't force changes at 44/45/47 unless clearly non-camelid
    # Check if 44/45/47 are clearly non-camelid
    camelid_typical_44 = ['R', 'Q', 'K', 'E']
    camelid_typical_45 = ['L', 'Q', 'K']
    camelid_typical_47 = ['W']
    
    pos44_idx = position_mapping.get(44)
    pos45_idx = position_mapping.get(45)
    pos47_idx = position_mapping.get(47)
    
    if pos44_idx and pos44_idx < len(conservative_seq):
        if conservative_seq[pos44_idx] not in camelid_typical_44:
            # Clearly non-camelid, change to typical camelid (R)
            conservative_seq[pos44_idx] = 'R'
            conservative_mutations.append(f"Pos44: {seq[pos44_idx]}→R")
    
    if pos45_idx and pos45_idx < len(conservative_seq):
        if conservative_seq[pos45_idx] not in camelid_typical_45:
            # Clearly non-camelid, change to typical camelid (L)
            conservative_seq[pos45_idx] = 'L'
            conservative_mutations.append(f"Pos45: {seq[pos45_idx]}→L")
    
    if pos47_idx and pos47_idx < len(conservative_seq):
        if conservative_seq[pos47_idx] not in camelid_typical_47:
            # Clearly non-camelid, change to W
            conservative_seq[pos47_idx] = 'W'
            conservative_mutations.append(f"Pos47: {seq[pos47_idx]}→W")
    
    results["conservative"] = ''.join(conservative_seq)
    mutations_log["conservative"] = conservative_mutations
    
    # ===== BALANCED STRATEGY =====
    balanced_seq = list(seq)
    balanced_mutations = []
    
    # Use FR2_STRATEGY_TABLE["recommendation"]
    # 44->E, 45->R, 47 keep W (unless input is not W)
    
    # Position 44 -> E
    if pos44_idx and pos44_idx < len(balanced_seq):
        if balanced_seq[pos44_idx] != 'E':
            balanced_seq[pos44_idx] = 'E'
            balanced_mutations.append(f"Pos44: {seq[pos44_idx]}→E")
    
    # Position 45 -> R
    if pos45_idx and pos45_idx < len(balanced_seq):
        if balanced_seq[pos45_idx] != 'R':
            balanced_seq[pos45_idx] = 'R'
            balanced_mutations.append(f"Pos45: {seq[pos45_idx]}→R")
    
    # Position 47: keep W (unless input is not W)
    if pos47_idx and pos47_idx < len(balanced_seq):
        if balanced_seq[pos47_idx] != 'W':
            balanced_seq[pos47_idx] = 'W'
            balanced_mutations.append(f"Pos47: {seq[pos47_idx]}→W")
    
    # Optional: Position 37 -> F (from recommendation)
    if pos37_idx and pos37_idx < len(balanced_seq):
        if balanced_seq[pos37_idx] != 'F':
            balanced_seq[pos37_idx] = 'F'
            balanced_mutations.append(f"Pos37: {seq[pos37_idx]}→F")
    
    results["balanced"] = ''.join(balanced_seq)
    mutations_log["balanced"] = balanced_mutations
    
    # ===== AGGRESSIVE STRATEGY =====
    aggressive_seq = list(seq)
    aggressive_mutations = []
    
    # Force apply human_residue (37->V, 44->G, 45->L, 47->W)
    human_residues = FR2_STRATEGY_TABLE["human_residue"]
    
    # Position 37 -> V
    if pos37_idx and pos37_idx < len(aggressive_seq):
        if aggressive_seq[pos37_idx] != 'V':
            aggressive_seq[pos37_idx] = 'V'
            aggressive_mutations.append(f"Pos37: {seq[pos37_idx]}→V")
    
    # Position 44 -> G
    if pos44_idx and pos44_idx < len(aggressive_seq):
        if aggressive_seq[pos44_idx] != 'G':
            aggressive_seq[pos44_idx] = 'G'
            aggressive_mutations.append(f"Pos44: {seq[pos44_idx]}→G")
    
    # Position 45 -> L
    if pos45_idx and pos45_idx < len(aggressive_seq):
        if aggressive_seq[pos45_idx] != 'L':
            aggressive_seq[pos45_idx] = 'L'
            aggressive_mutations.append(f"Pos45: {seq[pos45_idx]}→L")
    
    # Position 47 -> W
    if pos47_idx and pos47_idx < len(aggressive_seq):
        if aggressive_seq[pos47_idx] != 'W':
            aggressive_seq[pos47_idx] = 'W'
            aggressive_mutations.append(f"Pos47: {seq[pos47_idx]}→W")
    
    results["aggressive"] = ''.join(aggressive_seq)
    mutations_log["aggressive"] = aggressive_mutations
    
    # Print log of mutations
    print("\n" + "=" * 80)
    print("FR2 Engineering Results")
    print("=" * 80)
    print(f"Original sequence: {seq}")
    print(f"Sequence length: {len(seq)}")
    if annotation:
        fr2_seq = annotation.get_region_sequence("FR2")
        print(f"FR2 region (from annotation): {fr2_seq}")
        if "FR2" in annotation.regions:
            fr2_start, fr2_end = annotation.regions["FR2"]
            print(f"FR2 positions: {fr2_start}-{fr2_end} (0-based)")
    else:
        # Use fr2_start and fr2_end from fallback
        if 'fr2_start' in locals() and 'fr2_end' in locals():
            print(f"Estimated FR2 region: positions {fr2_start}-{fr2_end}")
    print()
    
    for strategy_name in ["conservative", "balanced", "aggressive"]:
        print(f"--- {strategy_name.upper()} Strategy ---")
        if mutations_log[strategy_name]:
            print(f"  Mutations applied:")
            for mut in mutations_log[strategy_name]:
                print(f"    {mut}")
        else:
            print(f"  No mutations applied")
        print(f"  Result: {results[strategy_name]}")
        print()
    
    print("=" * 80)
    
    return results

