"""
evidence_gate.py — InSynBio Evidence-Gating Layer
===================================================
Shared pre-flight evidence check consumed by every project CLI / orchestration
entry point.  Returns a structured EvidenceContext that downstream modules
(report generators, decision advisors, CLI summaries) can query without
re-fetching.

Integration contract
--------------------
  from core.resources.evidence_gate import EvidenceGate, EvidenceContext

  gate = EvidenceGate()
  ctx  = gate.check(antibody_name="Trastuzumab", target="HER2")

  ctx.ada_tier          # "TIER1" | "TIER2" | "TIER3" | "NOT_FOUND"
  ctx.ada_value         # "5.1%" or None
  ctx.ada_evidence      # PMID / FDA reference string
  ctx.pubmed_hits       # list[dict]  (max 3 recent)
  ctx.warnings          # list[str]   (human-readable Therasik Warnings)
  ctx.is_trusted        # True only for TIER1

Design choices
--------------
  - Pure Python, no LLM dependency.
  - Network calls are optional: if offline, returns degraded context with
    ``ada_tier = "OFFLINE"`` instead of raising.
  - Does NOT modify any file; read-only against tiered_db.
"""
from __future__ import annotations

import json
import os
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Dict, List, Optional

_SUITE_ROOT = Path(__file__).resolve().parents[2]
_TIERED_DB  = _SUITE_ROOT / "data" / "ADA_reliable_package" / "tiered_db"


@dataclass
class EvidenceContext:
    """Immutable evidence snapshot attached to a single analysis run."""
    antibody_name: str = ""
    target: str = ""

    ada_tier: str = "NOT_FOUND"
    ada_value: Optional[str] = None
    ada_evidence: Optional[str] = None
    ada_entry: Optional[Dict[str, Any]] = None

    pubmed_hits: List[Dict[str, str]] = field(default_factory=list)
    uniprot_info: Optional[Dict[str, Any]] = None
    pdb_hits: List[Dict[str, Any]] = field(default_factory=list)

    warnings: List[str] = field(default_factory=list)

    @property
    def is_trusted(self) -> bool:
        return self.ada_tier == "TIER1"

    @property
    def needs_disclaimer(self) -> bool:
        return self.ada_tier in ("TIER2", "NOT_FOUND", "OFFLINE")

    def summary_lines(self) -> List[str]:
        """Human-readable summary for CLI output."""
        lines = [
            f"[EvidenceGate] Antibody: {self.antibody_name or '(unnamed)'}",
            f"  Target: {self.target or '(unspecified)'}",
            f"  ADA Tier: {self.ada_tier}",
        ]
        if self.ada_value:
            lines.append(f"  ADA Value: {self.ada_value}")
        if self.ada_evidence:
            lines.append(f"  Evidence: {self.ada_evidence}")
        if self.pubmed_hits:
            lines.append(f"  PubMed hits: {len(self.pubmed_hits)} recent articles")
        for w in self.warnings:
            lines.append(f"  WARNING: {w}")
        return lines

    def to_dict(self) -> Dict[str, Any]:
        return {
            "antibody_name": self.antibody_name,
            "target": self.target,
            "ada_tier": self.ada_tier,
            "ada_value": self.ada_value,
            "ada_evidence": self.ada_evidence,
            "pubmed_hit_count": len(self.pubmed_hits),
            "warnings": self.warnings,
            "is_trusted": self.is_trusted,
            "needs_disclaimer": self.needs_disclaimer,
        }


class EvidenceGate:
    """Stateless evidence checker.  Instantiate once per session."""

    def __init__(self, tiered_db_dir: Optional[str] = None, enable_network: bool = True):
        self._db_dir = Path(tiered_db_dir) if tiered_db_dir else _TIERED_DB
        self._net = enable_network
        self._tier1: List[Dict] = []
        self._tier2: List[Dict] = []
        self._tier3: List[Dict] = []
        self._load_tiers()

    def _load_tiers(self) -> None:
        for attr, fname in [("_tier1", "Tier1_Verified.json"),
                            ("_tier2", "Tier2_Proprietary.json"),
                            ("_tier3", "Tier3_Untraceable.json")]:
            path = self._db_dir / fname
            if path.exists():
                with open(path, "r", encoding="utf-8") as f:
                    data = json.load(f)
                    setattr(self, attr, data.get("entries", []))

    def _find_in_tier(self, name: str, tier: List[Dict], tier_label: str):
        name_lower = name.strip().lower()
        for entry in tier:
            entry_name = entry.get("antibody_name", "").strip().lower()
            if entry_name == name_lower:
                return tier_label, entry
        return None, None

    def _lookup_ada(self, name: str):
        for tier_data, label in [(self._tier1, "TIER1"),
                                  (self._tier2, "TIER2"),
                                  (self._tier3, "TIER3")]:
            label_found, entry = self._find_in_tier(name, tier_data, label)
            if label_found:
                return label_found, entry
        return "NOT_FOUND", None

    def check(
        self,
        antibody_name: str = "",
        target: str = "",
        uniprot_id: str = "",
        skip_network: bool = False,
    ) -> EvidenceContext:
        """Run evidence pre-flight and return a frozen context."""
        ctx = EvidenceContext(antibody_name=antibody_name, target=target)

        # 1. ADA tier lookup (always local, fast)
        if antibody_name:
            tier, entry = self._lookup_ada(antibody_name)
            ctx.ada_tier = tier
            ctx.ada_entry = entry
            if entry:
                ctx.ada_value = (
                    entry.get("ada_value_verified")
                    or entry.get("ada_value_ai")
                    or entry.get("ada_value")
                )
                ctx.ada_evidence = (
                    entry.get("pmid")
                    or entry.get("reference")
                    or entry.get("evidence_summary", "")[:200]
                )

            if tier == "TIER3":
                ctx.warnings.append(
                    f"{antibody_name}: Tier 3 (Untraceable). "
                    "No public ADA data found in previous audits. Do not re-search."
                )
            elif tier == "TIER2":
                ctx.warnings.append(
                    f"{antibody_name}: Tier 2 (Proprietary/Unverified). "
                    "ADA value is AI-generated from restricted sources. "
                    "Requires paid database verification before clinical use."
                )

        # 2. Optional network enrichment (PubMed / UniProt / PDB)
        if self._net and not skip_network and (target or uniprot_id):
            try:
                from core.resources.knowledge_bridge import InSynBioKnowledgeBridge
                bridge = InSynBioKnowledgeBridge()

                if uniprot_id:
                    ctx.uniprot_info = bridge.fetch_uniprot_info(uniprot_id)

                if target:
                    query = f"{target} antibody immunogenicity"
                    ctx.pubmed_hits = bridge.search_pubmed(query, max_results=3)
                    ctx.pdb_hits = bridge.find_pdb_structures(target, limit=3)
            except Exception:
                ctx.ada_tier = ctx.ada_tier if ctx.ada_tier != "NOT_FOUND" else "OFFLINE"

        return ctx


def print_evidence_banner(ctx: EvidenceContext) -> None:
    """Print a standardized evidence banner to stdout for CLI entry points."""
    print("\n" + "=" * 60)
    print("INSYNBIO EVIDENCE GATE — Pre-Flight Check")
    print("=" * 60)
    for line in ctx.summary_lines():
        print(line)
    if ctx.needs_disclaimer:
        print("  ** Disclaimer will be added to report output **")
    print("=" * 60 + "\n")
