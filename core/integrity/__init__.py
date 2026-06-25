"""
InSynBio Site Integrity Package.

Provides pre-deploy validation and safe-repair for website content:
  - PMID authenticity and strict context relevance (QA)
  - ADA rows: displayed ADA %% must appear in PubMed or citation_url (ada_evidence)
  - Sequence format and reference matching
  - PDB/RCSB structure existence and entity relevance
  - External ID and URL validity (IEDB, UniProt, ClinicalTrials, DOI, DailyMed)
  - Site JSON parity across docs/ and deployed site trees

Entry point: scripts/site_integrity_pipeline.py
"""
from .extractor import EntityExtractor, Entity
from .validators import ValidatorRegistry, Finding, Severity
from .repairs import SafeRepairEngine, Repair
from .reporter import IntegrityReporter

__all__ = [
    "EntityExtractor",
    "Entity",
    "ValidatorRegistry",
    "Finding",
    "Severity",
    "SafeRepairEngine",
    "Repair",
    "IntegrityReporter",
]
