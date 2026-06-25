"""
ValidatorRegistry: typed checks returning Finding objects.

Check IDs and default severities:
  PMID_EXISTS              HIGH    - PMID does not resolve in PubMed
  PMID_CONTEXT_RELEVANT    HIGH/MEDIUM - title/abstract not related to page context (strict)
  PMID_SUPPORTS_CLAIM      LOW     - quantitative claim may not appear in PMID text (non-ADA rows)
  ADA_VALUE_IN_EVIDENCE    HIGH    - ADA % must appear in PubMed or citation_url (ada_evidence.py)
  SEQUENCE_FORMAT_VALID    HIGH    - sequence contains illegal characters or unusual length
  SEQUENCE_MATCHES_REF     MEDIUM  - sequence not found in any curated internal source
  PDB_EXISTS               HIGH    - PDB ID not resolvable at RCSB
  PDB_ENTITY_RELEVANT      MEDIUM  - structure title/descriptor does not match page context
  EXTERNAL_ID_VALID        MEDIUM  - external URL returns non-2xx status
  SITE_PARITY_OK           HIGH    - canonical JSON in docs/ differs from deployed site tree

Relies on helpers re-exported from verify_vaccine_kb_pmids.py (efetch_batch,
_score_relevance, _terms_from_ctx) via importlib, exactly as audit_site_pmids.py does.
"""
from __future__ import annotations

import importlib.util
import json
import os
import re
import sys
import time
import urllib.error
import urllib.request
from dataclasses import dataclass, field
from enum import Enum
from pathlib import Path
from typing import Any

from .extractor import Entity

# ── load helpers from verify_vaccine_kb_pmids.py ─────────────────────────────
_SCRIPTS_DIR = Path(__file__).resolve().parents[2] / "scripts"
_VKB_PATH = _SCRIPTS_DIR / "verify_vaccine_kb_pmids.py"

_vkb: Any = None
efetch_batch = None
_score_relevance = None
_terms_from_ctx = None
NCI_META_PMIDS: frozenset = frozenset()

def _load_vkb() -> None:
    global _vkb, efetch_batch, _score_relevance, _terms_from_ctx, NCI_META_PMIDS
    if _vkb is not None:
        return
    if not _VKB_PATH.exists():
        print(f"[WARN] verify_vaccine_kb_pmids.py not found at {_VKB_PATH}; PMID validators disabled.", file=sys.stderr)
        return
    spec = importlib.util.spec_from_file_location("verify_vaccine_kb_pmids", _VKB_PATH)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    _vkb = mod
    efetch_batch = mod.efetch_batch
    _score_relevance = mod._score_relevance
    _terms_from_ctx = mod._terms_from_ctx
    NCI_META_PMIDS = mod.NCI_META_PMIDS


# ── data model ───────────────────────────────────────────────────────────────
class Severity(str, Enum):
    HIGH = "HIGH"
    MEDIUM = "MEDIUM"
    LOW = "LOW"
    INFO = "INFO"


@dataclass
class Finding:
    check_id: str
    severity: Severity
    entity_type: str
    value: str
    file_path: str
    json_path: str
    message: str
    detail: str = ""
    is_auto_repaired: bool = False
    repaired_value: str = ""
    is_overridden: bool = False
    override_reason: str = ""

    def as_dict(self) -> dict:
        return {
            "check_id": self.check_id,
            "severity": self.severity.value,
            "entity_type": self.entity_type,
            "value": self.value,
            "file_path": self.file_path,
            "json_path": self.json_path,
            "message": self.message,
            "detail": self.detail,
            "is_auto_repaired": self.is_auto_repaired,
            "repaired_value": self.repaired_value,
            "is_overridden": self.is_overridden,
            "override_reason": self.override_reason,
        }


# ── standard AA alphabet ─────────────────────────────────────────────────────
_VALID_AA = frozenset("ACDEFGHIKLMNPQRSTVWYBZUX")
_MIN_SEQ_LEN = 30
_MAX_SEQ_LEN = 4000

# ── ValidatorRegistry ─────────────────────────────────────────────────────────
class ValidatorRegistry:
    """
    Run all enabled checks against a list of Entity objects.
    Returns a list of Finding objects.
    """

    def __init__(
        self,
        overrides: dict | None = None,
        ncbi_api_key: str | None = None,
        pmid_relevance_threshold: float = 0.15,
        url_timeout: int = 15,
        curated_sequences: set[str] | None = None,
        repo_root: Path | None = None,
    ):
        _load_vkb()
        self.overrides = overrides or {}
        self.api_key = ncbi_api_key or os.environ.get("NCBI_API_KEY")
        self.relevance_threshold = pmid_relevance_threshold
        self.url_timeout = url_timeout
        self.curated_sequences: set[str] = curated_sequences or set()
        self._repo_root: Path = repo_root or Path(".")
        self._pubmed_cache: dict[str, dict] = {}
        self._http_cache: dict[str, int] = {}
        self._rcsb_cache: dict[str, bool] = {}

    # ── entry point ───────────────────────────────────────────────────────
    def run_all(self, entities: list[Entity]) -> list[Finding]:
        findings: list[Finding] = []

        pmid_entities   = [e for e in entities if e.entity_type == "pmid"]
        seq_entities    = [e for e in entities if e.entity_type == "sequence"]
        pdb_entities    = [e for e in entities if e.entity_type == "pdb_id"]
        url_entities    = [e for e in entities if e.entity_type in ("url", "doi")]

        findings.extend(self._check_pmids(pmid_entities))
        findings.extend(self._check_sequences(seq_entities))
        findings.extend(self._check_pdb_ids(pdb_entities))
        findings.extend(self._check_urls(url_entities))

        self.apply_overrides(findings)
        return findings

    def apply_overrides(self, findings: list[Finding]) -> None:
        for f in findings:
            fp = f.file_path.replace("\\", "/")
            for key in (
                f"{f.check_id}|{f.value}|{fp}",
                f"{f.check_id}|{f.value}|*",
            ):
                if key in self.overrides:
                    f.is_overridden = True
                    f.override_reason = self.overrides[key].get("reason", "")
                    break

    def run_parity(self, docs_dir: Path, site_trees: list[Path]) -> list[Finding]:
        """Check that JSON files in docs/ match their counterparts in every site tree."""
        findings: list[Finding] = []
        if not docs_dir.exists():
            return findings
        for json_file in sorted(docs_dir.glob("*.json")):
            for tree in site_trees:
                counterpart = tree / json_file.name
                if not counterpart.exists():
                    continue
                try:
                    src = json.loads(json_file.read_text(encoding="utf-8", errors="replace"))
                    dst = json.loads(counterpart.read_text(encoding="utf-8", errors="replace"))
                except Exception:
                    continue
                if src != dst:
                    findings.append(Finding(
                        check_id="SITE_PARITY_OK",
                        severity=Severity.HIGH,
                        entity_type="json_file",
                        value=json_file.name,
                        file_path=str(counterpart),
                        json_path="(file root)",
                        message=f"Parity mismatch: docs/{json_file.name} differs from {counterpart}",
                        detail="Run safe-repair to sync canonical copy.",
                    ))
        return findings

    # ── PMID checks ───────────────────────────────────────────────────────
    def _check_pmids(self, entities: list[Entity]) -> list[Finding]:
        if not entities:
            return []

        # Deduplicate and batch-fetch
        unique_pmids = list({e.value for e in entities})
        self._prefetch_pmids(unique_pmids)

        findings: list[Finding] = []
        for e in entities:
            pmid = e.value
            info = self._pubmed_cache.get(pmid)

            # PMID_EXISTS
            if info is None:
                findings.append(Finding(
                    check_id="PMID_EXISTS",
                    severity=Severity.HIGH,
                    entity_type="pmid",
                    value=pmid,
                    file_path=e.file_path,
                    json_path=e.json_path,
                    message=f"PMID {pmid} did not resolve in PubMed (efetch returned no record).",
                ))
                continue

            # NCI meta-PMID: shared reference, skip relevance check
            if pmid in NCI_META_PMIDS:
                continue

            # PMID_CONTEXT_RELEVANT
            if _terms_from_ctx and _score_relevance:
                terms = _terms_from_ctx(e.context)
                if terms:
                    status, score, hits = _score_relevance(
                        terms, info.get("title", ""), info.get("abstract", "")
                    )
                    if status in ("weak_or_unrelated", "no_pubmed_text"):
                        # QA-strict: unrelated PubMed record is always blocking (HIGH).
                        sev = (
                            Severity.HIGH
                            if status == "weak_or_unrelated"
                            else Severity.MEDIUM
                        )
                        findings.append(Finding(
                            check_id="PMID_CONTEXT_RELEVANT",
                            severity=sev,
                            entity_type="pmid",
                            value=pmid,
                            file_path=e.file_path,
                            json_path=e.json_path,
                            message=f"PMID {pmid} context relevance: {status} (score={score})",
                            detail=f"PubMed title: {info.get('title', '(none)')} | Context terms: {terms[:5]}",
                        ))
                    elif status == "review" or score < self.relevance_threshold:
                        findings.append(Finding(
                            check_id="PMID_CONTEXT_RELEVANT",
                            severity=Severity.MEDIUM,
                            entity_type="pmid",
                            value=pmid,
                            file_path=e.file_path,
                            json_path=e.json_path,
                            message=f"PMID {pmid} relevance uncertain (score={score}, status={status}); QA review required.",
                            detail=f"Matched terms: {hits[:5]}",
                        ))

            # PMID_SUPPORTS_CLAIM: heuristic % / incidence check
            ctx_name = e.context.get("name") or e.context.get("drug") or ""
            findings.extend(self._check_pmid_claim(e, info, ctx_name))

        return findings

    def _check_pmid_claim(self, e: Entity, info: dict, ctx_name: str) -> list[Finding]:
        """
        Heuristic check: if a nearby context mentions numeric % (ADA incidence etc.),
        check if that figure appears in the abstract.  Emits LOW severity only.
        """
        notes = str(e.context.get("notes", ""))
        pct_matches = re.findall(r"(\d{1,3}(?:\.\d)?)%", notes)
        if not pct_matches:
            return []
        abstract = info.get("abstract", "").lower()
        title = info.get("title", "").lower()
        blob = title + " " + abstract
        supported = any(pct in blob for pct in pct_matches)
        if not supported and pct_matches:
            return [Finding(
                check_id="PMID_SUPPORTS_CLAIM",
                severity=Severity.LOW,
                entity_type="pmid",
                value=e.value,
                file_path=e.file_path,
                json_path=e.json_path,
                message=f"PMID {e.value}: claimed percentages {pct_matches[:3]} not found verbatim in abstract.",
                detail=f"Context name: {ctx_name[:80]}",
            )]
        return []

    def _prefetch_pmids(self, pmids: list[str]) -> None:
        missing = [p for p in pmids if p not in self._pubmed_cache]
        if not missing or efetch_batch is None:
            return
        batch_size = 200
        for i in range(0, len(missing), batch_size):
            chunk = missing[i : i + batch_size]
            try:
                results = efetch_batch(chunk, self.api_key)
                self._pubmed_cache.update(results)
            except Exception as exc:
                print(f"[WARN] efetch_batch failed: {exc}", file=sys.stderr)
            # Mark unfound PMIDs explicitly as None
            for p in chunk:
                if p not in self._pubmed_cache:
                    self._pubmed_cache[p] = None  # type: ignore[assignment]
            time.sleep(0.35)

    # ── Sequence checks ───────────────────────────────────────────────────
    def _check_sequences(self, entities: list[Entity]) -> list[Finding]:
        findings: list[Finding] = []
        seen: set[str] = set()
        for e in entities:
            seq = e.value.upper()
            if seq in seen:
                continue
            seen.add(seq)

            # SEQUENCE_FORMAT_VALID
            bad_chars = [c for c in seq if c not in _VALID_AA]
            if bad_chars:
                findings.append(Finding(
                    check_id="SEQUENCE_FORMAT_VALID",
                    severity=Severity.HIGH,
                    entity_type="sequence",
                    value=seq[:60] + ("…" if len(seq) > 60 else ""),
                    file_path=e.file_path,
                    json_path=e.json_path,
                    message=f"Sequence contains invalid AA characters: {set(bad_chars)}",
                    detail=f"Length={len(seq)}, first invalid at position {seq.index(bad_chars[0])+1}",
                ))
                continue

            if not (_MIN_SEQ_LEN <= len(seq) <= _MAX_SEQ_LEN):
                findings.append(Finding(
                    check_id="SEQUENCE_FORMAT_VALID",
                    severity=Severity.MEDIUM,
                    entity_type="sequence",
                    value=seq[:60],
                    file_path=e.file_path,
                    json_path=e.json_path,
                    message=f"Sequence length {len(seq)} outside expected range [{_MIN_SEQ_LEN}, {_MAX_SEQ_LEN}].",
                ))

            # SEQUENCE_MATCHES_REF
            if self.curated_sequences and seq not in self.curated_sequences:
                ctx_name = e.context.get("name") or e.context.get("drug") or ""
                findings.append(Finding(
                    check_id="SEQUENCE_MATCHES_REF",
                    severity=Severity.MEDIUM,
                    entity_type="sequence",
                    value=seq[:60] + ("…" if len(seq) > 60 else ""),
                    file_path=e.file_path,
                    json_path=e.json_path,
                    message="Sequence not found in any curated internal reference source.",
                    detail=f"Context: {ctx_name[:80]}",
                ))

        return findings

    # ── PDB checks ────────────────────────────────────────────────────────
    def _check_pdb_ids(self, entities: list[Entity]) -> list[Finding]:
        findings: list[Finding] = []
        seen: set[str] = set()
        for e in entities:
            pdb = e.value.upper()
            if not re.fullmatch(r"[1-9][A-Z0-9]{3}", pdb):
                continue
            if pdb in seen:
                continue
            seen.add(pdb)

            # PDB_EXISTS
            if pdb not in self._rcsb_cache:
                self._rcsb_cache[pdb] = self._rcsb_exists(pdb)

            if not self._rcsb_cache[pdb]:
                findings.append(Finding(
                    check_id="PDB_EXISTS",
                    severity=Severity.HIGH,
                    entity_type="pdb_id",
                    value=pdb,
                    file_path=e.file_path,
                    json_path=e.json_path,
                    message=f"PDB ID {pdb} not found at RCSB REST API.",
                ))
                continue

            # PDB_ENTITY_RELEVANT
            meta = self._rcsb_metadata(pdb)
            if meta and e.context:
                findings.extend(self._check_pdb_relevance(e, pdb, meta))

        return findings

    def _rcsb_exists(self, pdb: str) -> bool:
        url = f"https://data.rcsb.org/rest/v1/core/entry/{pdb.upper()}"
        try:
            req = urllib.request.Request(url)
            req.add_header("User-Agent", "InSynBio-SiteIntegrity/1.0")
            with urllib.request.urlopen(req, timeout=self.url_timeout) as r:
                return r.status == 200
        except Exception:
            return False

    def _rcsb_metadata(self, pdb: str) -> dict | None:
        url = f"https://data.rcsb.org/rest/v1/core/entry/{pdb.upper()}"
        try:
            req = urllib.request.Request(url)
            req.add_header("User-Agent", "InSynBio-SiteIntegrity/1.0")
            with urllib.request.urlopen(req, timeout=self.url_timeout) as r:
                return json.loads(r.read().decode())
        except Exception:
            return None

    def _check_pdb_relevance(
        self, e: Entity, pdb: str, meta: dict
    ) -> list[Finding]:
        findings: list[Finding] = []
        struct = meta.get("struct", {})
        title = (struct.get("title") or struct.get("pdbx_descriptor") or "").lower()
        if not title:
            return []
        ctx_terms = []
        for k in ("name", "drug", "target", "targets", "gene"):
            v = e.context.get(k)
            if isinstance(v, str) and v.strip():
                ctx_terms.append(v.strip().lower()[:80])
            elif isinstance(v, list):
                for x in v:
                    if isinstance(x, str):
                        ctx_terms.append(x.strip().lower()[:80])
        if not ctx_terms:
            return []
        matched = any(t in title or title in t for t in ctx_terms if len(t) >= 3)
        if not matched:
            findings.append(Finding(
                check_id="PDB_ENTITY_RELEVANT",
                severity=Severity.MEDIUM,
                entity_type="pdb_id",
                value=pdb,
                file_path=e.file_path,
                json_path=e.json_path,
                message=f"PDB {pdb} title '{title[:120]}' does not match context terms {ctx_terms[:3]}.",
                detail="Verify the structure corresponds to the displayed antibody/target.",
            ))
        return findings

    # ── URL / external ID checks ──────────────────────────────────────────
    def _check_urls(self, entities: list[Entity]) -> list[Finding]:
        findings: list[Finding] = []
        seen: set[str] = set()
        for e in entities:
            url = e.value
            if url in seen:
                continue
            seen.add(url)
            status = self._http_head(url)
            if status is None or status >= 400:
                display_status = str(status) if status else "error/timeout"
                findings.append(Finding(
                    check_id="EXTERNAL_ID_VALID",
                    severity=Severity.MEDIUM,
                    entity_type=e.entity_type,
                    value=url[:200],
                    file_path=e.file_path,
                    json_path=e.json_path,
                    message=f"External URL returned HTTP {display_status}: {url[:120]}",
                    detail="URL may be broken, moved, or requires authentication.",
                ))
        return findings

    def _http_head(self, url: str) -> int | None:
        if url in self._http_cache:
            return self._http_cache[url]
        try:
            req = urllib.request.Request(url, method="HEAD")
            req.add_header("User-Agent", "InSynBio-SiteIntegrity/1.0")
            req.add_header("Accept", "*/*")
            with urllib.request.urlopen(req, timeout=self.url_timeout) as r:
                self._http_cache[url] = r.status
                return r.status
        except urllib.error.HTTPError as exc:
            self._http_cache[url] = exc.code
            return exc.code
        except Exception:
            self._http_cache[url] = None  # type: ignore[assignment]
            return None
