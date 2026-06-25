"""
core/vaccine_design/iedb_search.py
────────────────────────────────────
IEDB (Immune Epitope Database) online search interface.

Provides:
  1. Epitope search by antigen / pathogen / HLA allele
  2. T cell assay results retrieval
  3. B cell assay results retrieval
  4. Antigen detail lookup

WHY AN ONLINE INTERFACE?
  The IEDB contains >1 million curated epitopes from primary literature.
  We do NOT replicate this database locally (copyright + update burden).
  Instead, we provide a thin query wrapper so clients can search online
  on demand. Our local knowledge bases (taa_database, infectious_antigens)
  contain only the most representative, QA-verified entries.

IEDB REST API reference:
  https://www.iedb.org/api_legacy/
  https://query.iedb.org/ (newer GraphQL endpoint)

Usage
-----
    searcher = IEDBSearcher()

    # Search epitopes for a given antigen
    results = searcher.search_epitopes(antigen="KRAS", organism="Homo sapiens")
    for r in results:
        print(r["epitope_id"], r["linear_sequence"], r["hla_restriction"])

    # Search MHC-I epitopes for a specific pathogen
    flu_epitopes = searcher.search_infectious_epitopes(
        pathogen="Influenza",
        mhc_class="I",
        hla="HLA-A*02:01",
    )

    # Get IEDB web URL for manual browsing (for client portal links)
    url = IEDBSearcher.web_url_epitope_search(antigen="KRAS G12D")

Environment: conda activate vaccine (requires internet connection)
"""
from __future__ import annotations

import json
import logging
import time
import urllib.parse
import urllib.request
import urllib.error
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional

__version__ = "1.0.0"

logger = logging.getLogger(__name__)

# ── IEDB REST API endpoints ──────────────────────────────────────────────────
IEDB_LEGACY_BASE = "https://www.iedb.org/api_legacy/json/v2"
IEDB_WEB_BASE    = "https://www.iedb.org"

# Documented resource endpoints
ENDPOINT_EPITOPE       = f"{IEDB_LEGACY_BASE}/epitope"
ENDPOINT_TCELL         = f"{IEDB_LEGACY_BASE}/tcell"
ENDPOINT_BCELL         = f"{IEDB_LEGACY_BASE}/bcell"
ENDPOINT_MHC_BIND      = f"{IEDB_LEGACY_BASE}/mhc_bind"
ENDPOINT_RECEPTOR      = f"{IEDB_LEGACY_BASE}/receptor"

# Conservative rate limiting — IEDB requests max 3 req/sec from single IP
REQUEST_DELAY_SEC = 0.4


@dataclass
class IEDBEpitope:
    """Simplified epitope record from IEDB API."""
    epitope_id: str
    linear_sequence: str
    hla_restriction: str
    mhc_class: str
    antigen_name: str
    antigen_accession: str
    organism: str
    assay_type: str          # T cell / B cell / MHC binding
    measurement: str         # Positive / Negative
    pmid: str
    reference: str
    iedb_url: str


class IEDBSearcher:
    """IEDB online epitope search client.

    All methods require internet access. Results are returned as dicts/
    dataclasses and can be integrated into the vaccine design pipeline.

    For large-scale programmatic access, consider downloading the full
    IEDB export at https://www.iedb.org/database_export_v3.php (CC-BY 4.0).
    """

    def __init__(self, timeout_sec: int = 30, retry: int = 2):
        self.timeout = timeout_sec
        self.retry = retry

    # ── epitope search ────────────────────────────────────────────────────

    def search_epitopes(
        self,
        antigen: Optional[str] = None,
        organism: Optional[str] = None,
        hla: Optional[str] = None,
        mhc_class: Optional[str] = None,
        assay_type: Optional[str] = None,   # "T cell" / "B cell" / "MHC binding"
        positive_only: bool = True,
        max_results: int = 100,
    ) -> List[Dict[str, Any]]:
        """Search IEDB epitopes. Returns list of raw result dicts.

        Args:
            antigen: Antigen name keyword (e.g., "KRAS", "Spike", "MART-1")
            organism: Host organism ("Homo sapiens" / "Mus musculus")
            hla: HLA restriction (e.g., "HLA-A*02:01", "DRB1*04:01")
            mhc_class: "I" or "II"
            assay_type: Filter by assay type
            positive_only: Only return positive assay results
            max_results: Maximum results to return
        """
        params: Dict[str, Any] = {
            "format": "json",
            "limit": min(max_results, 1000),
            "offset": 0,
        }
        if antigen:
            params["antigen_name"] = antigen
        if organism:
            params["h_organism_name"] = organism
        if hla:
            params["mhc_allele_name"] = hla
        if positive_only:
            params["qualitative_measure"] = "Positive"

        results = self._get(ENDPOINT_EPITOPE, params)
        if not results:
            return []

        # Flatten/normalize the nested IEDB response
        flat = []
        for item in (results if isinstance(results, list) else results.get("objects", [])):
            flat.append(self._flatten_epitope(item))
        return flat[:max_results]

    # ── T cell assay search ───────────────────────────────────────────────

    def search_tcell(
        self,
        epitope_seq: Optional[str] = None,
        hla: Optional[str] = None,
        antigen: Optional[str] = None,
        positive_only: bool = True,
        max_results: int = 100,
    ) -> List[Dict[str, Any]]:
        """Search T cell assay results from IEDB."""
        params: Dict[str, Any] = {
            "format": "json",
            "limit": min(max_results, 1000),
        }
        if epitope_seq:
            params["linear_sequence"] = epitope_seq
        if hla:
            params["mhc_allele_name"] = hla
        if antigen:
            params["antigen_name"] = antigen
        if positive_only:
            params["qualitative_measure"] = "Positive"

        results = self._get(ENDPOINT_TCELL, params)
        if not results:
            return []
        items = results if isinstance(results, list) else results.get("objects", [])
        return items[:max_results]

    # ── infectious disease epitope convenience search ─────────────────────

    def search_infectious_epitopes(
        self,
        pathogen: str,
        mhc_class: Optional[str] = None,
        hla: Optional[str] = None,
        max_results: int = 50,
    ) -> List[Dict[str, Any]]:
        """Search T cell epitopes for an infectious disease pathogen.

        Convenience wrapper for common vaccine design queries.
        """
        params: Dict[str, Any] = {
            "format": "json",
            "limit": max_results,
            "qualitative_measure": "Positive",
            "r_object_type": "Linear peptide",
        }
        if pathogen:
            params["source_organism_name"] = pathogen
        if hla:
            params["mhc_allele_name"] = hla

        results = self._get(ENDPOINT_TCELL, params)
        if not results:
            return []
        items = results if isinstance(results, list) else results.get("objects", [])

        if mhc_class:
            items = [
                i for i in items
                if f"class {mhc_class.upper()}" in str(i).lower()
                or (mhc_class == "I" and "HLA-A" in str(i.get("mhc_allele_name", ""))
                    or "HLA-B" in str(i.get("mhc_allele_name", "")))
                or (mhc_class == "II" and "DRB" in str(i.get("mhc_allele_name", ""))
                    or "DQ" in str(i.get("mhc_allele_name", "")))
            ]
        return items[:max_results]

    # ── tumor antigen epitope search ──────────────────────────────────────

    def search_tumor_epitopes(
        self,
        antigen: str,
        hla: Optional[str] = None,
        max_results: int = 50,
    ) -> List[Dict[str, Any]]:
        """Search T cell epitopes for a tumor antigen."""
        return self.search_tcell(
            antigen=antigen,
            hla=hla,
            positive_only=True,
            max_results=max_results,
        )

    # ── MHC binding data search ───────────────────────────────────────────

    def search_mhc_binding(
        self,
        peptide: Optional[str] = None,
        allele: Optional[str] = None,
        max_results: int = 50,
    ) -> List[Dict[str, Any]]:
        """Search experimentally measured MHC binding affinities."""
        params: Dict[str, Any] = {
            "format": "json",
            "limit": max_results,
        }
        if peptide:
            params["linear_sequence"] = peptide
        if allele:
            params["mhc_allele_name"] = allele

        results = self._get(ENDPOINT_MHC_BIND, params)
        if not results:
            return []
        return (results if isinstance(results, list) else results.get("objects", []))[:max_results]

    # ── static web URL helpers (for client portal links) ──────────────────

    @staticmethod
    def web_url_epitope_search(
        antigen: Optional[str] = None,
        hla: Optional[str] = None,
        pathogen: Optional[str] = None,
    ) -> str:
        """Build an IEDB web URL that can be opened in a browser.

        Use in client reports to let users do deeper exploration.
        """
        base = "https://www.iedb.org/result_v3.php"
        params = {
            "cookie_id": "",
            "object_type": "Linear peptide",
            "epitope_type": "Linear",
        }
        if antigen:
            params["antigen_name"] = antigen
        if hla:
            params["mhc_allele_name"] = hla
        if pathogen:
            params["source_organism_name"] = pathogen
        return base + "?" + urllib.parse.urlencode(params)

    @staticmethod
    def web_url_structure(pdb_id: str) -> str:
        """Direct RCSB PDB URL for a TCR-pMHC structure."""
        return f"https://www.rcsb.org/structure/{pdb_id.upper()}"

    @staticmethod
    def web_url_antigen(antigen_name: str) -> str:
        """IEDB antigen detail page URL."""
        q = urllib.parse.quote(antigen_name)
        return f"https://www.iedb.org/antigen/{q}/"

    # ── internal HTTP ─────────────────────────────────────────────────────

    def _get(self, endpoint: str, params: Dict[str, Any]) -> Any:
        """GET request to IEDB API with retry. Returns parsed JSON or None."""
        url = endpoint + "?" + urllib.parse.urlencode(
            {k: v for k, v in params.items() if v is not None}
        )
        logger.debug(f"IEDB GET: {url}")
        for attempt in range(self.retry + 1):
            try:
                req = urllib.request.Request(
                    url,
                    headers={
                        "Accept": "application/json",
                        "User-Agent": "InSynBio-VaccineDesign/1.0",
                    },
                )
                with urllib.request.urlopen(req, timeout=self.timeout) as resp:
                    time.sleep(REQUEST_DELAY_SEC)
                    return json.loads(resp.read().decode("utf-8"))
            except urllib.error.HTTPError as e:
                logger.warning(f"IEDB HTTP {e.code}: {url}")
                if e.code == 429:  # rate limited
                    time.sleep(5 * (attempt + 1))
                elif attempt < self.retry:
                    time.sleep(1.5 ** attempt)
                else:
                    return None
            except urllib.error.URLError as e:
                logger.warning(f"IEDB network error: {e.reason}")
                if attempt < self.retry:
                    time.sleep(2)
                else:
                    return None
            except Exception as e:
                logger.error(f"IEDB unexpected error: {e}")
                return None
        return None

    @staticmethod
    def _flatten_epitope(item: Dict) -> Dict:
        """Flatten IEDB nested response to simple dict."""
        return {
            "epitope_id": item.get("epitope_id", ""),
            "linear_sequence": item.get("linear_sequence", ""),
            "hla_restriction": item.get("mhc_allele_name", ""),
            "antigen_name": item.get("antigen_name", ""),
            "antigen_accession": item.get("antigen_accession", ""),
            "organism": item.get("source_organism_name", ""),
            "assay_type": item.get("assay_type", ""),
            "measurement": item.get("qualitative_measure", ""),
            "pmid": item.get("pubmed_id", ""),
            "iedb_url": f"https://www.iedb.org/epitope/{item.get('epitope_id', '')}",
        }


# ── convenience functions ────────────────────────────────────────────────────

def iedb_search(
    antigen: str,
    hla: Optional[str] = None,
    max_results: int = 30,
) -> List[Dict[str, Any]]:
    """One-line IEDB T cell epitope search. Convenience wrapper."""
    searcher = IEDBSearcher()
    return searcher.search_tcell(antigen=antigen, hla=hla, max_results=max_results)


def iedb_url(antigen: str, hla: Optional[str] = None) -> str:
    """Generate IEDB browser URL for a given antigen query."""
    return IEDBSearcher.web_url_epitope_search(antigen=antigen, hla=hla)
