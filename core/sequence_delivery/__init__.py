"""
core/sequence_delivery — Sequence retrieval, assembly, translation,
codon optimization, and QA for antibody engineering delivery packages.

Public API:
    from core.sequence_delivery import retrieval, assembler, translator, codon_optimizer, qa

Version history:
    1.0.0  2026-05-01  Initial module (unifies scattered project scripts)
"""

__version__ = "1.0.0"
__module__ = "sequence_delivery"

from . import retrieval, assembler, translator, codon_optimizer, qa

__all__ = ["retrieval", "assembler", "translator", "codon_optimizer", "qa", "__version__"]
