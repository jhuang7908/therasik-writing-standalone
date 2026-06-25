"""
Knowledge Enricher for the ACTES CAR-T Decision Engine.

Bridges the InSynBio Knowledge Bridge (UniProt, PubMed, PDB APIs) and
the Three-Tier ADA database into the DecisionAdvisor pipeline.

Integration points:
  D2 (Antigen Properties) — enriched with UniProt protein data
  D8 (Clinical Evidence)  — enriched with latest PubMed literature
  Binder risk             — ADA incidence from tiered_db
  Structure availability  — PDB hit list for the target
"""
from __future__ import annotations

import json
import logging
from pathlib import Path
from typing import Any

logger = logging.getLogger(__name__)

_DATA_ROOT = Path(__file__).resolve().parent.parent.parent / "data"
_ADA_DB_DIR = _DATA_ROOT / "ADA_reliable_package" / "tiered_db"

_TARGET_UNIPROT_MAP: dict[str, str] = {
    "CD19": "P15391",
    "CD20": "P11836",
    "CD22": "P20273",
    "CD33": "P20138",
    "CD123": "P26951",
    "BCMA": "Q02223",
    "GPC3": "P51654",
    "HER2": "P04626",
    "EGFR": "P00533",
    "MSLN": "Q13421",
    "MUC1": "P15941",
    "PSMA": "Q04609",
    "CEA": "P06731",
    "EpCAM": "P16422",
    "GD2": None,
    "B7-H3": "Q5ZPR3",
    "DLL3": "Q9NYJ7",
    "CLDN18.2": "P56856",
    "PD-L1": "Q9NZQ7",
    "CD70": "P32970",
    "CD38": "P28907",
    "GPRC5D": "Q9NZD1",
    "FLT3": "P36888",
    "CD7": "P09564",
    "CS1": "Q9NQ25",
    "NKG2D": "P26718",
    "PfCSP": None,
    "PfEMP1_CIDRa1": None,
}


class KnowledgeEnricher:
    """Auto-enriches ACTES decision layers with live knowledge data.

    Gracefully degrades to empty enrichments when offline or APIs fail.
    """

    def __init__(self, enable_api: bool = True, cache_dir: Path | None = None):
        self._enable_api = enable_api
        self._bridge = None
        self._ada_tiers: dict[str, list[dict]] = {}
        self._cache_dir = cache_dir or (_DATA_ROOT / "sequence_cache")
        self._cache_dir.mkdir(parents=True, exist_ok=True)

        if enable_api:
            try:
                from core.resources.knowledge_bridge import InSynBioKnowledgeBridge
                self._bridge = InSynBioKnowledgeBridge()
            except ImportError:
                logger.warning("Knowledge Bridge not available; running in offline mode.")
                self._enable_api = False

        self._load_ada_db()

    def _load_ada_db(self):
        for tier_name in ("Tier1_Verified", "Tier2_Proprietary", "Tier3_Untraceable"):
            path = _ADA_DB_DIR / f"{tier_name}.json"
            if path.exists():
                try:
                    data = json.loads(path.read_text(encoding="utf-8"))
                    self._ada_tiers[tier_name] = data.get("entries", [])
                except Exception as e:
                    logger.warning("Failed to load ADA tier %s: %s", tier_name, e)

    def enrich(self, target: str, indication: str) -> dict:
        """Run all enrichment queries and return a structured enrichment bundle.

        Returns dict with keys:
          uniprot, pubmed_clinical, pubmed_cart, pdb_structures,
          ada_risk, enrichment_status
        """
        uniprot_id = self._resolve_uniprot(target)

        uniprot_data = self._fetch_uniprot(uniprot_id) if uniprot_id else {}
        pubmed_clinical = self._search_pubmed_clinical(target, indication)
        pubmed_cart = self._search_pubmed_cart(target)
        pdb_hits = self._search_pdb(target)
        ada_risk = self._check_ada_risk(target)

        sources_queried = []
        if uniprot_data and "error" not in uniprot_data:
            sources_queried.append("UniProt")
        if pubmed_clinical:
            sources_queried.append("PubMed_clinical")
        if pubmed_cart:
            sources_queried.append("PubMed_CART")
        if pdb_hits:
            sources_queried.append("PDB")
        if ada_risk.get("entries"):
            sources_queried.append("ADA_tiered_db")

        return {
            "uniprot": uniprot_data,
            "pubmed_clinical": pubmed_clinical,
            "pubmed_cart": pubmed_cart,
            "pdb_structures": pdb_hits,
            "ada_risk": ada_risk,
            "enrichment_status": {
                "api_enabled": self._enable_api,
                "sources_queried": sources_queried,
                "target_uniprot": uniprot_id,
            },
        }

    def enrich_d2(self, d2: dict, enrichment: dict) -> dict:
        """Merge UniProt enrichment into D2 antigen properties."""
        up = enrichment.get("uniprot", {})
        if not up or "error" in up:
            return d2

        extra: dict[str, Any] = {}

        if up.get("name") and not d2.get("known"):
            extra["uniprot_name"] = up["name"]

        ptms = up.get("ptms", [])
        if ptms:
            glyco_sites = [
                f for f in ptms if f.get("type") == "Glycosylation"
            ]
            disulfide = [
                f for f in ptms if f.get("type") == "Disulfide bond"
            ]
            extra["uniprot_glycosylation_sites"] = len(glyco_sites)
            extra["uniprot_disulfide_bonds"] = len(disulfide)
            if glyco_sites:
                extra["glycosylation_warning"] = (
                    f"Target has {len(glyco_sites)} glycosylation site(s) — "
                    "epitope accessibility may vary with glycoform. Consider "
                    "binder validation on both glycosylated and deglycosylated antigen."
                )

        if up.get("function"):
            extra["uniprot_function"] = up["function"]

        pdb = enrichment.get("pdb_structures", [])
        if pdb and not any("error" in str(p) for p in pdb):
            extra["available_pdb_structures"] = [
                {"pdb_id": p.get("pdb_id"), "resolution": p.get("resolution"), "method": p.get("method")}
                for p in pdb[:5]
            ]
            extra["structure_availability"] = f"{len(pdb)} PDB structure(s) found for target"

        if extra:
            d2 = dict(d2)
            d2["knowledge_enrichment"] = extra
            old_rationale = d2.get("rationale", "")
            additions = []
            if "glycosylation_warning" in extra:
                additions.append(extra["glycosylation_warning"])
            if "structure_availability" in extra:
                additions.append(extra["structure_availability"])
            if additions:
                d2["rationale"] = old_rationale + " [KnowledgeEngine] " + "; ".join(additions)

        return d2

    def enrich_d8(self, d8: dict, enrichment: dict) -> dict:
        """Merge PubMed enrichment into D8 clinical evidence."""
        clinical = enrichment.get("pubmed_clinical", [])
        cart = enrichment.get("pubmed_cart", [])

        if not clinical and not cart:
            return d8

        d8 = dict(d8)
        if clinical and not any("error" in str(c) for c in clinical):
            d8["live_pubmed_clinical"] = [
                {"title": c.get("title", ""), "date": c.get("pubdate", ""), "url": c.get("url", "")}
                for c in clinical[:5]
            ]

        if cart and not any("error" in str(c) for c in cart):
            d8["live_pubmed_cart"] = [
                {"title": c.get("title", ""), "date": c.get("pubdate", ""), "url": c.get("url", "")}
                for c in cart[:5]
            ]

        total = len(d8.get("live_pubmed_clinical", [])) + len(d8.get("live_pubmed_cart", []))
        if total:
            old_rationale = d8.get("rationale", "")
            d8["rationale"] = old_rationale + f" [KnowledgeEngine] {total} recent PubMed article(s) retrieved for real-time evidence grounding."

        return d8

    def get_ada_assessment(self, target: str) -> dict:
        """Check ADA tiered_db for immunogenicity risk of binders against this target."""
        return self._check_ada_risk(target)

    # ── Private helpers ──────────────────────────────────────────────

    @staticmethod
    def _normalize_target(name: str) -> str:
        """Normalize target name for fuzzy matching: strip Greek, dashes, whitespace."""
        import re
        name = name.lower().strip()
        name = name.replace("α", "a").replace("β", "b").replace("γ", "g")
        name = name.replace("delta", "d").replace("epsilon", "e")
        name = re.sub(r"[\s\-_/()]+", "", name)
        return name

    @staticmethod
    def _target_matches_ada(query: str, entry_target: str) -> bool:
        """Check if a query target name matches an ADA database entry target."""
        import re
        norm = KnowledgeEnricher._normalize_target

        q = norm(query)
        tokens = re.split(r"[/,;()\s]+", entry_target)
        tokens = [norm(t) for t in tokens if t.strip()]
        e_full = norm(entry_target)

        if q == e_full:
            return True
        if q in tokens:
            return True
        if e_full.startswith(q) and len(q) >= 3:
            return True
        if len(q) >= 4 and q in e_full:
            return True
        return False

    @staticmethod
    def _resolve_uniprot(target: str) -> str | None:
        direct = _TARGET_UNIPROT_MAP.get(target)
        if direct:
            return direct
        for key, uid in _TARGET_UNIPROT_MAP.items():
            if key.lower() == target.lower():
                return uid
        return None

    def _fetch_uniprot(self, accession: str) -> dict:
        if not self._bridge:
            return {}
        cache_file = self._cache_dir / f"uniprot_{accession}.json"
        if cache_file.exists():
            try:
                return json.loads(cache_file.read_text(encoding="utf-8"))
            except Exception:
                pass
        try:
            data = self._bridge.fetch_uniprot_info(accession)
            if data and "error" not in data:
                cache_file.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")
            return data
        except Exception as e:
            logger.warning("UniProt fetch for %s failed: %s", accession, e)
            return {"error": str(e)}

    def _search_pubmed_clinical(self, target: str, indication: str) -> list[dict]:
        if not self._bridge:
            return []
        query = f"{target} CAR-T {indication} clinical trial"
        try:
            return self._bridge.search_pubmed(query, max_results=5)
        except Exception as e:
            logger.warning("PubMed clinical search failed: %s", e)
            return [{"error": str(e)}]

    def _search_pubmed_cart(self, target: str) -> list[dict]:
        if not self._bridge:
            return []
        query = f"{target} CAR-T therapy 2024 2025 2026"
        try:
            return self._bridge.search_pubmed(query, max_results=5)
        except Exception as e:
            logger.warning("PubMed CAR-T search failed: %s", e)
            return [{"error": str(e)}]

    def _search_pdb(self, target: str) -> list[dict]:
        if not self._bridge:
            return []
        try:
            return self._bridge.find_pdb_structures(target, limit=5)
        except Exception as e:
            logger.warning("PDB search for %s failed: %s", target, e)
            return [{"error": str(e)}]

    def _check_ada_risk(self, target: str) -> dict:
        """Search the Three-Tier ADA database for binders against this target."""
        matches: list[dict] = []
        tier_found = None

        for tier_name in ("Tier1_Verified", "Tier2_Proprietary", "Tier3_Untraceable"):
            entries = self._ada_tiers.get(tier_name, [])
            for entry in entries:
                entry_target = entry.get("target", "")
                if not self._target_matches_ada(target, entry_target):
                    continue
                matches.append({
                    "antibody_name": entry.get("antibody_name"),
                    "target": entry_target,
                    "ada_value": entry.get("ada_value_verified", entry.get("ada_value_original", "N/A")),
                    "tier": tier_name,
                    "status": entry.get("status"),
                    "pmid": entry.get("pmid"),
                })
                if tier_found is None:
                    tier_found = tier_name

        if not matches:
            return {
                "target": target,
                "entries": [],
                "risk_summary": f"No ADA data found for target '{target}' in tiered database.",
                "recommendation": "Novel target — immunogenicity assessment should be planned experimentally.",
            }

        ada_values = []
        for m in matches:
            val = m.get("ada_value", "")
            if isinstance(val, str) and "%" in val:
                try:
                    pct = float(val.split("%")[0].strip().split()[-1])
                    ada_values.append(pct)
                except (ValueError, IndexError):
                    pass

        mean_ada = sum(ada_values) / len(ada_values) if ada_values else None
        if mean_ada is not None:
            if mean_ada > 30:
                risk_level = "HIGH"
                rec = "High ADA incidence for existing binders — consider fully human/humanized scFv, llama-derived VHH, or humanization optimization."
            elif mean_ada > 10:
                risk_level = "MODERATE"
                rec = "Moderate ADA incidence — humanized binder recommended; monitor ADA in early clinical."
            else:
                risk_level = "LOW"
                rec = "Low ADA incidence — standard binder formats acceptable."
        else:
            risk_level = "UNKNOWN"
            rec = "ADA values not parseable — manual review recommended."

        return {
            "target": target,
            "entries": matches[:5],
            "n_total_matches": len(matches),
            "mean_ada_pct": round(mean_ada, 1) if mean_ada is not None else None,
            "risk_level": risk_level,
            "risk_summary": f"{len(matches)} existing antibody(s) targeting {target} found. Risk: {risk_level}.",
            "recommendation": rec,
            "highest_tier": tier_found,
        }
