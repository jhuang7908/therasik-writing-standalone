"""

"""

import pytest
import tempfile
import yaml
from pathlib import Path
from core.config import Config, get_config
from core.utils.config_loader import clear_config_cache


class TestConfigLoading:
    """"""
    
    def test_config_loads_successfully(self):
        """"""
        cfg = get_config
        assert cfg is not None
        assert cfg.paths.project_root.exists
    
    def test_config_validation(self):
        """"""
        cfg = get_config
        errors = Config.validate(cfg)
        # ：，，
        # 
    
    def test_scoring_profile_default(self):
        """scoring profile"""
        cfg = get_config
        weights = cfg.parameters.get_scoring_weights
        assert 'framework_identity' in weights
        assert 'cdr_compatibility' in weights
        assert 'developability' in weights
    
    def test_scoring_profile_custom(self):
        """scoring profile"""
        # 
        with tempfile.NamedTemporaryFile(mode='w', suffix='.yaml', delete=False) as f:
            config_data = {
                'parameters': {
                    'scoring': {
                        'active_profile': 'developability_strict',
                        'profiles': {
                            'developability_strict': {
                                'framework_identity': 0.4,
                                'cdr_compatibility': 0.2,
                                'developability': 0.4
                            }
                        }
                    }
                }
            }
            yaml.dump(config_data, f)
            temp_path = Path(f.name)
        
        try:
            clear_config_cache
            cfg = Config.load(config_path=temp_path, validate=False)
            if cfg.parameters.scoring:
                weights = cfg.parameters.get_scoring_weights
                assert weights['developability'] == 0.4
                assert weights['framework_identity'] == 0.4
        finally:
            temp_path.unlink
            clear_config_cache


class TestConfigValidation:
    """"""
    
    def test_validation_parameter_ranges(self):
        """"""
        cfg = get_config
        
        # clustering_threshold
        original = cfg.parameters.clustering_threshold
        cfg.parameters.clustering_threshold = 1.5  # 
        errors = Config.validate(cfg)
        assert any('clustering_threshold' in e for e in errors)
        cfg.parameters.clustering_threshold = original  # 
    
    def test_validation_cdr_score_consistency(self):
        """CDR score"""
        cfg = get_config
        
        # hard_min > soft_min
        original_hard = cfg.parameters.hard_min_cdr_score
        original_soft = cfg.parameters.soft_min_cdr_score
        cfg.parameters.hard_min_cdr_score = 0.6
        cfg.parameters.soft_min_cdr_score = 0.3
        errors = Config.validate(cfg)
        assert any('hard_min_cdr_score' in e for e in errors)
        cfg.parameters.hard_min_cdr_score = original_hard
        cfg.parameters.soft_min_cdr_score = original_soft  # 


















