"""
Feature Annotation Module v1

Tagging-only feature annotation for antibody sequences.
No scoring, no recommendations, only residue-level tags.
"""

from core.features.annotate import annotate_features, export_feature_matrix

__all__ = ['annotate_features', 'export_feature_matrix']








