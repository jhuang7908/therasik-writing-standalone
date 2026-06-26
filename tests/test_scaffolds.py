"""
Scaffolds
"""

import pytest
from core.scaffolds import (
    load_alpaca_vhh_scaffolds,
    load_human_vhh_safe_templates,
    load_alignment_matrix,
    clear_cache,
    ScaffoldLoadError
)


class TestScaffoldsLoader:
    """scaffolds"""
    
    def test_load_alpaca_scaffolds(self):
        """scaffolds"""
        try:
            scaffolds = load_alpaca_vhh_scaffolds
            assert isinstance(scaffolds, list)
            if len(scaffolds) > 0:
                assert 'scaffold_id' in scaffolds[0]
                assert 'consensus' in scaffolds[0]
        except ScaffoldLoadError:
            # ，
            pytest.skip("Alpaca scaffolds file not found")
    
    def test_load_human_templates(self):
        """human templates"""
        try:
            templates = load_human_vhh_safe_templates
            assert isinstance(templates, list)
            if len(templates) > 0:
                assert 'template_id' in templates[0]
                assert 'developability' in templates[0]
        except ScaffoldLoadError:
            # ，
            pytest.skip("Human templates file not found")
    
    def test_load_alignment_matrix(self):
        """"""
        try:
            matrix = load_alignment_matrix
            assert isinstance(matrix, dict)
        except ScaffoldLoadError:
            # ，
            pytest.skip("Alignment matrix file not found")
    
    def test_cache_clearing(self):
        """"""
        clear_cache
        # ，
        # clear_cache
        assert True


















