"""
germline_filter.py — InSynBio AbEngineCore
==========================================
Filters peptides against human germline V/J sequences to identify
"self" peptides (immune tolerance).

Usage:
    from core.immunogenicity.germline_filter import GermlineFilter
    gf = GermlineFilter()
    is_self = gf.is_germline("QVQLVQSGAEVKKPG")
"""

import json
import os
from pathlib import Path
from typing import Set, List, Dict

# Path to germline data relative to this file
# core/immunogenicity/germline_filter.py -> ... -> data/germlines/human_ig_aa
_SUITE_ROOT = Path(__file__).resolve().parents[2]
_GERMLINE_DIR = _SUITE_ROOT / "data" / "germlines" / "human_ig_aa"

class GermlineFilter:
    _instance = None
    _peptides: Set[str] = set()
    _peptide_weights: Dict[str, float] = {}  # peptide -> tolerance score (0.0-1.0)
    _loaded: bool = False

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super(GermlineFilter, cls).__new__(cls)
        return cls._instance

    def __init__(self):
        if not self._loaded:
            self.load_germlines()

    def load_germlines(self):
        """Load human V and J sequences and build k-mer index with frequency weighting."""
        if self._loaded:
            return

        files = [
            "IGHV_aa.json", "IGKV_aa.json", "IGLV_aa.json",
            "IGHJ_aa.json", "IGKJ_aa.json", "IGLJ_aa.json"
        ]

        # Count total sequences per chain type to normalize frequency
        # We simplify by just counting total V and total J sequences
        total_v = 0
        total_j = 0
        
        # Store sequences with their source file type (VH, VK, VL, JH, JK, JL)
        sequences_by_type = {}

        for fname in files:
            path = _GERMLINE_DIR / fname
            if not path.exists():
                print(f"[GermlineFilter] Warning: {path} not found.")
                continue
            
            chain_type = fname.split("_")[0] # IGHV, IGKV, etc.
            sequences_by_type[chain_type] = []
            
            try:
                with open(path, "r", encoding="utf-8") as f:
                    data = json.load(f)
                    entries = data.get("entries", [])
                    
                    # Update totals
                    if "V" in chain_type:
                        total_v += len(entries)
                    elif "J" in chain_type:
                        total_j += len(entries)
                        
                    for entry in entries:
                        seq = entry.get("sequence_aa", "").strip().upper()
                        if self._is_valid_protein(seq):
                            sequences_by_type[chain_type].append(seq)
            except Exception as e:
                print(f"[GermlineFilter] Error loading {fname}: {e}")

        # Build k-mer index with frequency
        # Tolerance score = (frequency in germline)
        # If a peptide appears in 100% of germlines, score = 1.0 (fully tolerated)
        # If it appears in 1% of germlines, score = 0.01 (low tolerance)
        # However, we need to be careful. V-genes are many.
        # A peptide in IGHV1-69 is tolerated even if it's not in IGHV3-23.
        # "Tolerance" means "is present in the human population".
        # If it exists in ANY germline, it is "self".
        # But the user asked for: "germline" (higher frequency -> more tolerated).
        # This implies we should weight the tolerance.
        
        # Strategy:
        # 1. Count occurrence of each 15-mer across all germlines.
        # 2. But simply counting is misleading because gene usage varies.
        #    IGHV3-23 is used 100x more than IGHV1-2.
        #    Ideally we weight by clinical usage frequency.
        #    We don't have clinical usage tables loaded here easily.
        #    Fallback: Assume uniform probability of gene existence in genome (which is true).
        #    If a peptide is in a rare allele, it's still "self" for that person.
        #    But for a population drug, a peptide present in a common allele is "more tolerated" across population.
        #    Let's count raw occurrence in the germline DB as a proxy for "commonness".
        
        self._peptides = set()
        self._peptide_weights = {}
        k = 15
        
        # Flatten all V sequences
        all_v = []
        for t in ["IGHV", "IGKV", "IGLV"]:
            all_v.extend(sequences_by_type.get(t, []))
            
        # Count k-mers in V genes
        v_counts = {}
        for seq in all_v:
            if len(seq) < k: continue
            # Use set to count each seq only once per peptide (binary presence per gene)
            seen_in_seq = set()
            for i in range(len(seq) - k + 1):
                pep = seq[i : i + k]
                seen_in_seq.add(pep)
            for pep in seen_in_seq:
                v_counts[pep] = v_counts.get(pep, 0) + 1
                
        # Normalize V counts
        # Max score 1.0 if present in all V genes (impossible), but let's scale it.
        # Actually, "is_germline" is binary in the current Analyzer.
        # We will store the raw count or frequency.
        # Let's store frequency relative to total V genes of that chain type?
        # No, just store binary set for now to keep "is_germline" working,
        # AND store a "tolerance_score" in a separate dict.
        
        for pep, count in v_counts.items():
            self._peptides.add(pep)
            # Simple frequency: count / total_v
            # This is low for specific CDRs, high for FRs.
            self._peptide_weights[pep] = count / max(1, total_v)

        self._full_sequences = all_v # Keep V sequences for fallback
        self._loaded = True
        print(f"[GermlineFilter] Loaded {len(all_v)} V-gene sequences. Index contains {len(self._peptides)} unique {k}-mers.")

    def get_tolerance_score(self, peptide: str) -> float:
        """
        Return tolerance score (0.0 - 1.0).
        Based on frequency of peptide in human germline database.
        """
        if not self._loaded:
            self.load_germlines()
        return self._peptide_weights.get(peptide, 0.0)


    def _is_valid_protein(self, seq: str) -> bool:
        """Heuristic to check if sequence is protein (not DNA)."""
        if not seq: return False
        if len(seq) < 5: return False
        # If it contains chars other than ACGTN, it's likely protein
        # But protein can be "ACGT..." too (Ala, Cys, Gly, Thr).
        # Check for common protein-only chars: L, F, P, Q, E, I, Y, W, R, K, M, D, H, V, S
        protein_chars = set("LFPQEIYWRKMDHVS")
        if any(c in protein_chars for c in seq):
            return True
        # If it's only ACGTN, assume DNA
        dna_chars = set("ACGTN")
        if all(c in dna_chars for c in seq):
            return False
        return True

    def is_germline(self, peptide: str) -> bool:
        """Check if peptide exists in human germline."""
        if not self._loaded:
            self.load_germlines()
        
        # Exact match in 15-mer index
        if len(peptide) == 15:
            return peptide in self._peptides
        
        # Fallback for other lengths: substring search
        # This is slower but safe
        for seq in self._full_sequences:
            if peptide in seq:
                return True
        return False

    def filter_epitopes(self, epitopes: List[Dict]) -> List[Dict]:
        """
        Mark epitopes as tolerated if they match germline.
        Expects list of dicts with 'peptide' key.
        Adds 'is_germline': True/False to each dict.
        """
        for ep in epitopes:
            pep = ep.get("peptide", "")
            ep["is_germline"] = self.is_germline(pep)
        return epitopes
