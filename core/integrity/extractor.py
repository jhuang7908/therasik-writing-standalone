"""
EntityExtractor: scans HTML and JSON content roots for PMIDs, sequences,
PDB IDs, and external IDs/URLs, returning a normalized entity list.

Entities extracted:
  pmid        - numeric PubMed ID
  sequence    - amino acid sequence (single-letter, ≥30 chars)
  pdb_id      - 4-char RCSB structure identifier
  url         - external URL (IEDB, UniProt, ClinicalTrials, DOI, DailyMed, FDA)
  uniprot_id  - UniProt accession
  iedb_id     - IEDB structure/assay ID
  doi         - DOI string

Context propagation mirrors audit_site_pmids.py so the same _terms_from_ctx /
_score_relevance helpers work on every extracted entity.
"""
from __future__ import annotations

import json
import re
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

# ── regex patterns ──────────────────────────────────────────────────────────
RE_PUBMED_URL = re.compile(
    r"https?://(?:www\.)?pubmed\.ncbi\.nlm\.nih\.gov/(\d{5,9})/?",
    re.I,
)
RE_PMID_TEXT = re.compile(r"PMID[:\s]+(\d{5,9})", re.I)
RE_PMID_BARE = re.compile(r"\b(\d{7,9})\b")  # fallback in numeric JSON fields

# PDB IDs: 4-char, first char alpha, remaining alphanumeric
RE_PDB_ID = re.compile(r"\b([1-9][A-Z0-9]{3})\b")

# UniProt canonical accession (5 or 6 char)
RE_UNIPROT = re.compile(
    r"\b([OPQ][0-9][A-Z0-9]{3}[0-9]|[A-NR-Z][0-9](?:[A-Z][A-Z0-9]{2}[0-9]){1,2})\b"
)

# IEDB structure/assay IDs in URLs
RE_IEDB_ID = re.compile(r"iedb\.org/[^\"'\s]*[/=](\d{3,7})(?:[/?&\"']|$)", re.I)

# DOI
RE_DOI = re.compile(r"\b(10\.\d{4,9}/[^\s\"'<>]+)")

# External URL patterns worth tracking
RE_EXT_URL = re.compile(
    r"https?://(?:"
    r"(?:www\.)?iedb\.org/[^\s\"'<>]+"
    r"|(?:www\.)?uniprot\.org/[^\s\"'<>]+"
    r"|clinicaltrials\.gov/[^\s\"'<>]+"
    r"|(?:www\.)?dailymed\.nlm\.nih\.gov/[^\s\"'<>]+"
    r"|(?:www\.)?accessdata\.fda\.gov/[^\s\"'<>]+"
    r"|(?:www\.)?rcsb\.org/[^\s\"'<>]+"
    r"|doi\.org/[^\s\"'<>]+"
    r")",
    re.I,
)

# Amino-acid single-letter code sequence (relaxed: standard + X + B/Z/U)
_AA = "ACDEFGHIKLMNPQRSTVWYBZUX"
_AA_PAT = f"[{_AA}]"
RE_SEQUENCE = re.compile(
    rf"\b({_AA_PAT}{{30,}})\b",
    re.I,
)

# JSON keys that commonly hold amino-acid sequences
_SEQ_KEYS = frozenset(
    {
        "sequence",
        "vh_sequence",
        "vl_sequence",
        "vhh_sequence",
        "hc_sequence",
        "lc_sequence",
        "heavy_chain",
        "light_chain",
        "aa_sequence",
        "canonical_sequence",
        "fv_sequence",
    }
)

# Context keys propagated during JSON walk (mirrors audit_site_pmids.py)
_CTX_KEYS = (
    "name",
    "drug",
    "drug_name",
    "alias",
    "aliases",
    "target",
    "targets",
    "indication",
    "gene",
    "antigen",
    "peptide",
    "epitope",
    "disease",
    "disease_context",
    "notes",
    "category",
    "subcategory",
    "mechanism",
    "clone_id",
    "title",
    "description",
)


# ── data model ───────────────────────────────────────────────────────────────
@dataclass
class Entity:
    entity_type: str       # pmid | sequence | pdb_id | url | uniprot_id | iedb_id | doi
    value: str             # canonical value
    file_path: str         # relative to repo root
    json_path: str         # dotted JSON path or "@offset{N}" for HTML
    context: dict = field(default_factory=dict)
    source_format: str = "json"   # "json" or "html"


# ── extractor ────────────────────────────────────────────────────────────────
class EntityExtractor:
    """
    Scan a list of root directories for HTML and JSON files.
    Return a flat list of Entity objects.
    """

    def __init__(
        self,
        roots: list[Path],
        repo_root: Path,
        skip_patterns: list[str] | None = None,
    ):
        self.roots = roots
        self.repo_root = repo_root
        self.skip_patterns = skip_patterns or [
            "node_modules",
            ".git",
            "__pycache__",
            "reports",
        ]

    # ── public ────────────────────────────────────────────────────────────
    def extract(self) -> list[Entity]:
        entities: list[Entity] = []
        for root in self.roots:
            if not root.exists():
                continue
            for path in sorted(root.rglob("*")):
                if any(skip in str(path) for skip in self.skip_patterns):
                    continue
                rel = str(path.relative_to(self.repo_root))
                if path.suffix.lower() == ".json":
                    entities.extend(self._scan_json(path, rel))
                elif path.suffix.lower() in {".html", ".htm"}:
                    entities.extend(self._scan_html(path, rel))
        return entities

    # ── JSON scanning ─────────────────────────────────────────────────────
    def _scan_json(self, path: Path, rel: str) -> list[Entity]:
        try:
            text = path.read_text(encoding="utf-8", errors="replace")
            data = json.loads(text)
        except Exception:
            return []
        entities: list[Entity] = []
        self._walk_json(data, "", {}, rel, entities)
        return entities

    def _walk_json(
        self,
        obj: Any,
        jpath: str,
        ctx: dict,
        rel: str,
        out: list[Entity],
    ) -> None:
        if isinstance(obj, dict):
            new_ctx = dict(ctx)
            for k in _CTX_KEYS:
                if k in obj:
                    new_ctx[k] = obj[k]

            for k, v in obj.items():
                child_path = f"{jpath}.{k}" if jpath else k

                # PMID numeric field
                if k in ("pmid",) and isinstance(v, (int, str)):
                    sv = str(v).strip()
                    if sv.isdigit() and 5 <= len(sv) <= 9:
                        out.append(Entity("pmid", sv, rel, child_path, dict(new_ctx), "json"))

                # PMID list
                elif k in ("pmids", "ada_source_pmids") and isinstance(v, list):
                    for i, p in enumerate(v):
                        sv = str(p).strip()
                        if sv.isdigit() and 5 <= len(sv) <= 9:
                            out.append(Entity("pmid", sv, rel, f"{child_path}[{i}]", dict(new_ctx), "json"))

                # Sequence fields
                elif k in _SEQ_KEYS and isinstance(v, str) and len(v) >= 30:
                    cleaned = re.sub(r"[\s\-_*]", "", v).upper()
                    if self._looks_like_sequence(cleaned):
                        out.append(Entity("sequence", cleaned, rel, child_path, dict(new_ctx), "json"))

                # PDB ID field
                elif k in ("pdb_id", "pdb", "structure_id", "rcsb_id") and isinstance(v, str):
                    pdb = v.strip().upper()
                    if len(pdb) == 4 and RE_PDB_ID.match(pdb):
                        out.append(Entity("pdb_id", pdb, rel, child_path, dict(new_ctx), "json"))

                # String values: scan for embedded PMIDs, URLs, PDB IDs
                elif isinstance(v, str):
                    self._scan_string(v, child_path, new_ctx, rel, out)

                # Recurse
                self._walk_json(v, child_path, new_ctx, rel, out)

        elif isinstance(obj, list):
            for i, item in enumerate(obj):
                self._walk_json(item, f"{jpath}[{i}]", ctx, rel, out)

    # ── HTML scanning ─────────────────────────────────────────────────────
    def _scan_html(self, path: Path, rel: str) -> list[Entity]:
        try:
            text = path.read_text(encoding="utf-8", errors="replace")
        except Exception:
            return []
        entities: list[Entity] = []

        # PubMed URLs
        for m in RE_PUBMED_URL.finditer(text):
            pmid = m.group(1)
            pos = m.start()
            ctx = self._html_context(text, pos)
            entities.append(Entity("pmid", pmid, rel, f"@offset{pos}", ctx, "html"))

        # PMID: XXXXXX text patterns (avoid duplication with URL matches)
        seen_offsets = {int(e.json_path.replace("@offset", "")) for e in entities if e.file_path == rel}
        for m in RE_PMID_TEXT.finditer(text):
            pmid = m.group(1)
            pos = m.start()
            if not any(abs(pos - o) < 100 for o in seen_offsets):
                ctx = self._html_context(text, pos)
                entities.append(Entity("pmid", pmid, rel, f"@offset{pos}", ctx, "html"))
                seen_offsets.add(pos)

        # External URLs
        for m in RE_EXT_URL.finditer(text):
            url = m.group(0).rstrip(".,;)'\"")
            pos = m.start()
            ctx = self._html_context(text, pos)
            # derive sub-type
            etype = self._classify_url(url)
            entities.append(Entity(etype, url, rel, f"@offset{pos}", ctx, "html"))

            # Extract IEDB ID from URL
            mi = RE_IEDB_ID.search(url)
            if mi:
                entities.append(Entity("iedb_id", mi.group(1), rel, f"@offset{pos}", ctx, "html"))

        # DOI patterns in HTML text
        for m in RE_DOI.finditer(text):
            doi = m.group(1).rstrip(".,;)'\"")
            pos = m.start()
            entities.append(Entity("doi", doi, rel, f"@offset{pos}", {}, "html"))

        # PDB IDs in HTML (e.g. in case study pages)
        for m in RE_PDB_ID.finditer(text):
            pdb = m.group(1).upper()
            pos = m.start()
            ctx = self._html_context(text, pos)
            entities.append(Entity("pdb_id", pdb, rel, f"@offset{pos}", ctx, "html"))

        return entities

    # ── helpers ───────────────────────────────────────────────────────────
    def _scan_string(
        self, s: str, jpath: str, ctx: dict, rel: str, out: list[Entity]
    ) -> None:
        for m in RE_PUBMED_URL.finditer(s):
            out.append(Entity("pmid", m.group(1), rel, jpath, dict(ctx), "json"))
        for m in RE_PMID_TEXT.finditer(s):
            out.append(Entity("pmid", m.group(1), rel, jpath, dict(ctx), "json"))
        for m in RE_EXT_URL.finditer(s):
            url = m.group(0).rstrip(".,;)'\"")
            etype = self._classify_url(url)
            out.append(Entity(etype, url, rel, jpath, dict(ctx), "json"))
            mi = RE_IEDB_ID.search(url)
            if mi:
                out.append(Entity("iedb_id", mi.group(1), rel, jpath, dict(ctx), "json"))
        for m in RE_DOI.finditer(s):
            out.append(Entity("doi", m.group(1).rstrip(".,;)"), rel, jpath, dict(ctx), "json"))
        for m in RE_PDB_ID.finditer(s):
            pdb = m.group(1).upper()
            if len(pdb) == 4:
                out.append(Entity("pdb_id", pdb, rel, jpath, dict(ctx), "json"))
        for m in RE_UNIPROT.finditer(s):
            out.append(Entity("uniprot_id", m.group(1), rel, jpath, dict(ctx), "json"))

    def _html_context(self, text: str, pos: int) -> dict:
        """Extract inline JS/data context from HTML text near an offset."""
        chunk = text[max(0, pos - 2500) : pos]
        ctx: dict = {}
        patterns = [
            (r"name\s*:\s*['\"]([^'\"]{1,300})['\"]", "name"),
            (r"drug(?:_name)?\s*:\s*['\"]([^'\"]{1,200})['\"]", "drug"),
            (r"target(?:s)?\s*:\s*['\"]([^'\"]{1,200})['\"]", "target"),
            (r"indication\s*:\s*['\"]([^'\"]{1,200})['\"]", "indication"),
            (r"gene\s*:\s*['\"]([^'\"]{1,100})['\"]", "gene"),
            (r"category\s*:\s*['\"]([^'\"]{1,100})['\"]", "category"),
            (r"mechanism\s*:\s*['\"]([^'\"]{1,500})['\"]", "notes"),
        ]
        for pat, key in patterns:
            last: str | None = None
            for m in re.finditer(pat, chunk, re.I | re.S):
                last = m.group(1).strip()
            if last and key not in ctx:
                ctx[key] = last
        return ctx

    @staticmethod
    def _looks_like_sequence(s: str) -> bool:
        if len(s) < 30:
            return False
        valid = set("ACDEFGHIKLMNPQRSTVWYBZUX")
        ratio = sum(1 for c in s if c in valid) / len(s)
        return ratio >= 0.92

    @staticmethod
    def _classify_url(url: str) -> str:
        low = url.lower()
        if "iedb.org" in low:
            return "url"
        if "uniprot.org" in low:
            return "url"
        if "clinicaltrials.gov" in low:
            return "url"
        if "dailymed" in low or "fda.gov" in low:
            return "url"
        if "rcsb.org" in low:
            return "url"
        if "doi.org" in low:
            return "doi"
        return "url"
