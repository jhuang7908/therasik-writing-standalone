"""
VHH Engineering Pipeline - Main Entry Point

This module provides the core VHHEngineeringPipeline class that orchestrates
the complete VHH engineering workflow, including:
- Sequence numbering and segmentation
- Germline selection
- Variant generation
- CMC analysis
- Immunogenicity analysis
- Scoring and ranking
- Wet lab suggestions generation
"""

from .vhh_fr2_engineering import apply_fr2_engineering
from core.cmc.generic_cmc_scanner import scan_cmc_liabilities
from scripts.anarci_abnumber_adapter import annotate_chain


class VHHEngineeringPipeline:
    """
    Main pipeline for VHH engineering.
    
    Orchestrates the complete workflow from input sequence to engineered variants
    with comprehensive analysis and recommendations.
    """
    
    def __init__(self, sequence: str, source: str, target: str = 'human', 
                 strategy: str = 'balanced'):
        """
        Initialize the VHH engineering pipeline.
        
        Args:
            sequence: Input VHH amino acid sequence
            source: Source of VHH ('llama', 'alpaca', 'synthetic', 'transgenic', etc.)
            target: Target species for engineering (default: 'human')
            strategy: Engineering strategy ('conservative', 'balanced', 'aggressive')
        """
        self.sequence = sequence.upper()
        self.source = source.lower()
        self.target = target.lower()
        self.strategy = strategy.lower()
        
        # Internal state dictionary to store intermediate results
        self._state = {
            'original_sequence': self.sequence,
            'numbering': None,
            'segmentation': None,
            'selected_germline': None,
            'variants': [],
            'cmc_results': {},
            'immunogenicity_results': {},
            'scores': {},
            'recommendation': None
        }
    
    def run(self):
        """
        Run the complete VHH engineering pipeline.
        
        Returns:
            dict: Pipeline results containing:
                - variants: List of engineered variant dictionaries
                - scores: Dictionary of scoring metrics
                - recommendation: Recommended variant information
        """
        # Step 1: Numbering and segmentation
        self._step_numbering_and_segmentation()
        
        # Step 2: Germline selection
        self._step_germline_selection()
        
        # Step 3: Generate variants
        self._step_generate_variants()
        
        # Step 4: CMC analysis
        self._step_cmc_analysis()
        
        # Step 5: Immunogenicity analysis
        self._step_immunogenicity_analysis()
        
        # Step 6: Scoring and ranking
        self._step_scoring_and_ranking()
        
        # Step 7: Build wet lab suggestions
        self._build_wetlab_suggestions()
        
        # Compile final result
        result = {
            "variants": self._state['variants'],
            "scores": self._state['scores'],
            "recommendation": self._state['recommendation']
        }
        
        return result
    
    def _step_numbering_and_segmentation(self):
        """
        Step 1: Perform sequence numbering and segment identification.
        
        Uses annotate_chain from anarci_abnumber_adapter to number the sequence
        and identify FR1, CDR1, FR2, CDR2, FR3, CDR3, FR4 regions.
        """
        # Use annotate_chain for numbering and segmentation
        annotation = annotate_chain(
            seq=self.sequence,
            chain_type_hint="H",  # VHH is a heavy chain variant
            scheme="imgt"
        )
        
        # Store numbering information
        self._state['numbering'] = {
            'scheme': annotation.scheme,
            'length': len(annotation.sequence),
            'backend': annotation.flags.get('chain_type_final', 'unknown')
        }
        
        # Store segmentation using regions_seq
        self._state['segmentation'] = {
            'fr1': annotation.regions_seq["FR1"],
            'cdr1': annotation.regions_seq["CDR1"],
            'fr2': annotation.regions_seq["FR2"],
            'cdr2': annotation.regions_seq["CDR2"],
            'fr3': annotation.regions_seq["FR3"],
            'cdr3': annotation.regions_seq["CDR3"],
            'fr4': annotation.regions_seq["FR4"]
        }
        
        # Store the full annotation object for later use
        self._state['annotation'] = annotation
    
    def _step_germline_selection(self):
        """
        Step 2: Select appropriate germline sequence for engineering.
        
        Future implementation:
        - Load germline data based on source and target
        - Perform sequence alignment and similarity analysis
        - Select best matching germline(s)
        - Store selected germline information in self._state
        """
        # TODO: Implement germline selection logic
        # TODO: Use vhh_germline_selection module
        
        # Placeholder: Store mock germline info
        self._state['selected_germline'] = {
            'name': f'{self.source}_germline_001',
            'sequence': None,
            'similarity': 0.85
        }
    
    def _step_generate_variants(self):
        """
        Step 3: Generate engineered variants based on strategy.
        
        Implementation:
        - Call apply_fr2_engineering to generate three variants (conservative/balanced/aggressive)
        - Store variant sequences and metadata in self._state['variants']
        
        Returns:
            list: List of variant dictionaries
        """
        try:
            # Call apply_fr2_engineering to generate all three strategy variants
            fr2_variants = apply_fr2_engineering(self.sequence, strategy=self.strategy)
            
            # Organize the three variants into a list
            variants = [
                {
                    "id": "variant_conservative",
                    "strategy": "conservative",
                    "sequence": fr2_variants["conservative"],
                },
                {
                    "id": "variant_balanced",
                    "strategy": "balanced",
                    "sequence": fr2_variants["balanced"],
                },
                {
                    "id": "variant_aggressive",
                    "strategy": "aggressive",
                    "sequence": fr2_variants["aggressive"],
                },
            ]
            
            # Store variants in state
            self._state['variants'] = variants
            
            return variants
            
        except Exception as e:
            # If FR2 engineering fails, fall back to original sequence
            print(f"Warning: FR2 engineering failed: {e}")
            print("Falling back to original sequence variant.")
            
            # Create fallback variant with original sequence
            variants = [
                {
                    "id": "variant_original",
                    "strategy": "none",
                    "sequence": self.sequence,
                }
            ]
            
            # Store fallback variant in state
            self._state['variants'] = variants
            
            return variants
    
    def _step_cmc_analysis(self):
        """
        Step 4: Perform CMC (Chemistry, Manufacturing, Controls) analysis.
        
        Scans each variant using the generic CMC scanner and attaches results
        to each variant. Also creates a summary of risk levels.
        
        Returns:
            list: Updated variants list with CMC results attached
        """
        # Check if variants exist
        if 'variants' not in self._state or not self._state['variants']:
            print("Warning: No variants found for CMC analysis. Skipping step.")
            return []
        
        variants = self._state['variants']
        cmc_summary = {}
        
        # Scan each variant for CMC liabilities
        for variant in variants:
            try:
                # Get sequence from variant
                sequence = variant.get('sequence')
                if not sequence:
                    print(f"Warning: Variant {variant.get('id', 'unknown')} has no sequence. Skipping CMC scan.")
                    variant['cmc'] = None
                    continue
                
                # Run CMC scan
                cmc_result = scan_cmc_liabilities(sequence)
                
                # Attach CMC results to variant
                variant['cmc'] = cmc_result
                
                # Store risk level in summary
                variant_id = variant.get('id', 'unknown')
                risk_level = cmc_result['summary']['risk_level']
                cmc_summary[variant_id] = risk_level
                
            except Exception as e:
                print(f"Warning: CMC scan failed for variant {variant.get('id', 'unknown')}: {e}")
                variant['cmc'] = None
                cmc_summary[variant.get('id', 'unknown')] = 'unknown'
        
        # Store summary in state
        self._state['cmc_summary'] = cmc_summary
        
        # Also keep backward compatibility with old cmc_results format
        cmc_results = {}
        for variant in variants:
            variant_id = variant.get('id', 'unknown')
            if variant.get('cmc'):
                # Extract key metrics for backward compatibility
                cmc_data = variant['cmc']
                cmc_results[variant_id] = {
                    'risk_level': cmc_data['summary']['risk_level'],
                    'total_flags': cmc_data['summary']['total_flags'],
                    'n_glyc_sites': len(cmc_data['n_glyc_sites']),
                    'deamidation_sites': len(cmc_data['deamidation_sites']),
                    'isomerization_sites': len(cmc_data['isomerization_sites']),
                    'oxidation_sites': len(cmc_data['oxidation_sites']),
                    'overall_score': 0.75  # Placeholder, can be calculated from flags
                }
            else:
                cmc_results[variant_id] = {
                    'risk_level': 'unknown',
                    'total_flags': 0,
                    'overall_score': 0.0
                }
        
        self._state['cmc_results'] = cmc_results
        
        return variants
    
    def _step_immunogenicity_analysis(self):
        """
        Step 5: Perform immunogenicity analysis.
        
        Future implementation:
        - Predict T-cell epitopes using IEDB API
        - Analyze HLA binding affinity
        - Calculate immunogenicity scores
        - Store results in self._state['immunogenicity_results']
        """
        # TODO: Implement immunogenicity analysis
        # TODO: Use iedb_client and vhh_immunogenicity modules
        
        # Placeholder: Store mock immunogenicity results
        immunogenicity_results = {}
        for variant in self._state['variants']:
            immunogenicity_results[variant['id']] = {
                'tcell_epitopes': [],
                'hla_binding_score': 0.65,
                'immunogenicity_risk': 'medium'
            }
        
        self._state['immunogenicity_results'] = immunogenicity_results
    
    def _step_scoring_and_ranking(self):
        """
        Step 6: Score and rank all variants.
        
        Future implementation:
        - Combine CMC, immunogenicity, and other scores
        - Apply composite scoring algorithm
        - Rank variants by overall score
        - Select top recommendation
        - Store scores and recommendation in self._state
        """
        # TODO: Implement composite scoring
        # TODO: Use composite_scoring and vhh_scoring modules
        
        # Placeholder: Calculate mock scores and select recommendation
        scores = {}
        for variant in self._state['variants']:
            variant_id = variant['id']
            # Mock composite score
            composite_score = (
                self._state['cmc_results'][variant_id]['overall_score'] * 0.4 +
                (1 - self._state['immunogenicity_results'][variant_id]['hla_binding_score']) * 0.4 +
                0.2  # Other factors placeholder
            )
            scores[variant_id] = {
                'composite_score': round(composite_score, 3),
                'cmc_score': self._state['cmc_results'][variant_id]['overall_score'],
                'immunogenicity_score': 1 - self._state['immunogenicity_results'][variant_id]['hla_binding_score']
            }
        
        self._state['scores'] = scores
        
        # Select top variant as recommendation
        best_variant_id = max(scores.keys(), key=lambda k: scores[k]['composite_score'])
        best_variant = next(v for v in self._state['variants'] if v['id'] == best_variant_id)
        
        self._state['recommendation'] = {
            'variant_id': best_variant_id,
            'sequence': best_variant['sequence'],
            'score': scores[best_variant_id]['composite_score'],
            'rationale': f'Top scoring variant with composite score {scores[best_variant_id]["composite_score"]}'
        }
    
    def _build_wetlab_suggestions(self):
        """
        Step 7: Generate wet lab experimental suggestions.
        
        Future implementation:
        - Based on variant properties and scores
        - Suggest expression systems, purification methods
        - Recommend validation assays
        - Store suggestions (can be added to result or separate output)
        """
        # TODO: Implement wet lab suggestions generation
        # TODO: Use report utilities to format suggestions
        
        # Placeholder: Store suggestions in state (can be accessed later)
        self._state['wetlab_suggestions'] = {
            'expression_system': 'E. coli or mammalian',
            'purification': 'Affinity chromatography recommended',
            'assays': ['Binding assay', 'Stability test', 'Aggregation check']
        }


def main():
    """Main entry point for VHH pipeline (for testing)."""
    # Example usage
    test_sequence = "QVQLVESGGGLVQPGGSLRLSCAASGFTFSSYAMSWVRQAPGKGLEWVSAISGSGGSTYYADSVKGRFTISRDNSKNTLYLQMNSLRAEDTAVYYCAA"
    pipeline = VHHEngineeringPipeline(
        sequence=test_sequence,
        source='llama',
        target='human',
        strategy='balanced'
    )
    result = pipeline.run()
    print("Pipeline result:", result)


if __name__ == "__main__":
    main()

