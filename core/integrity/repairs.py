"""
SafeRepairEngine: deterministic, low-risk automated fixes.

Safe repairs (auto-apply):
  1. Normalize malformed PubMed/DOI/IEDB/UniProt/RCSB URLs (http→https, trailing slash)
  2. Replace known wrong PMIDs from the existing wrong-PMID fix map
  3. Sync canonical JSON files from docs/ to site trees (parity fix)
  4. Normalize sequence formatting (whitespace, separator chars, lowercase→uppercase)

NOT auto-repaired (emitted as findings for human review):
  - Scientific claim values
  - Antibody identities or names
  - Ambiguous sequence or PDB mappings
  - Any change that requires domain judgment

Each Repair carries the original and new value, the file and path affected, and
a human-readable rationale.
"""
from __future__ import annotations

import json
import re
import shutil
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from .extractor import RE_PUBMED_URL
from .validators import Finding, Severity


# ── data model ───────────────────────────────────────────────────────────────
@dataclass
class Repair:
    repair_type: str       # normalize_url | replace_pmid | sync_json | normalize_seq
    file_path: str
    json_path: str
    old_value: str
    new_value: str
    rationale: str
    applied: bool = False


# ── wrong-PMID map (loaded from existing verification artifacts) ──────────────
def _load_wrong_pmid_map(repo_root: Path) -> dict[str, str]:
    """
    Build {old_pmid: corrected_pmid} from existing verification artifacts.
    Reads data/ADA_reliable_package/verification/wrong_pmid_fix_results.json if present.
    """
    candidates: dict[str, str] = {}
    fix_file = repo_root / "data" / "ADA_reliable_package" / "verification" / "wrong_pmid_fix_results.json"
    if fix_file.exists():
        try:
            data = json.loads(fix_file.read_text(encoding="utf-8", errors="replace"))
            entries = data if isinstance(data, list) else data.get("entries", [])
            for entry in entries:
                old = str(entry.get("wrong_pmid", "") or entry.get("original_pmid", "")).strip()
                new = str(entry.get("correct_pmid", "") or entry.get("replacement_pmid", "")).strip()
                if old.isdigit() and new.isdigit() and old != new:
                    candidates[old] = new
        except Exception:
            pass
    return candidates


# ── URL normalisation helpers ─────────────────────────────────────────────────
def _normalize_pubmed_url(url: str) -> str | None:
    """Return canonical https://pubmed.ncbi.nlm.nih.gov/{id}/ or None if unchanged."""
    m = re.search(r"pubmed\.ncbi\.nlm\.nih\.gov/(\d{5,9})", url, re.I)
    if not m:
        return None
    canonical = f"https://pubmed.ncbi.nlm.nih.gov/{m.group(1)}/"
    if url == canonical:
        return None
    return canonical


def _normalize_rcsb_url(url: str) -> str | None:
    m = re.search(r"rcsb\.org/structure/([1-9][A-Z0-9]{3})", url, re.I)
    if not m:
        return None
    canonical = f"https://www.rcsb.org/structure/{m.group(1).upper()}"
    if url == canonical:
        return None
    return canonical


def _normalize_uniprot_url(url: str) -> str | None:
    m = re.search(r"uniprot\.org/(?:uniprot|uniprotkb)/([A-Z0-9]{5,10})", url, re.I)
    if not m:
        return None
    canonical = f"https://www.uniprot.org/uniprotkb/{m.group(1).upper()}"
    if url == canonical:
        return None
    return canonical


def _normalize_doi_url(url: str) -> str | None:
    m = re.search(r"doi\.org/(10\.\d{4,9}/\S+)", url, re.I)
    if not m:
        return None
    doi = m.group(1).rstrip(".,;)'\"")
    canonical = f"https://doi.org/{doi}"
    if url == canonical:
        return None
    return canonical


def _normalize_url(url: str) -> str | None:
    """Try all normalizers; return corrected URL or None if already canonical."""
    for fn in (
        _normalize_pubmed_url,
        _normalize_rcsb_url,
        _normalize_uniprot_url,
        _normalize_doi_url,
    ):
        result = fn(url)
        if result and result != url:
            return result
    return None


def _normalize_sequence(seq: str) -> str | None:
    """Strip whitespace, separators, lowercase → uppercase.  Return None if already clean."""
    cleaned = re.sub(r"[\s\-_.*]", "", seq).upper()
    if cleaned == seq:
        return None
    return cleaned


# ── SafeRepairEngine ─────────────────────────────────────────────────────────
class SafeRepairEngine:
    """
    Apply deterministic repairs to files based on validator findings.
    All writes are gated by apply=True; default is dry-run.
    """

    def __init__(self, repo_root: Path, apply: bool = False):
        self.repo_root = repo_root
        self.apply = apply
        self._wrong_pmid_map = _load_wrong_pmid_map(repo_root)

    # ── entry point ───────────────────────────────────────────────────────
    def compute_repairs(self, findings: list[Finding]) -> list[Repair]:
        """
        Derive a list of Repair objects from findings without touching files.
        Call apply_repairs() afterwards to execute.
        """
        repairs: list[Repair] = []
        for f in findings:
            if f.is_overridden or f.is_auto_repaired:
                continue
            if f.check_id == "EXTERNAL_ID_VALID":
                r = self._repair_url(f)
                if r:
                    repairs.append(r)
            elif f.check_id == "PMID_EXISTS":
                r = self._repair_wrong_pmid(f)
                if r:
                    repairs.append(r)
            elif f.check_id == "SITE_PARITY_OK":
                r = self._repair_parity(f)
                if r:
                    repairs.append(r)
            elif f.check_id == "SEQUENCE_FORMAT_VALID":
                r = self._repair_sequence(f)
                if r:
                    repairs.append(r)
        return repairs

    def apply_repairs(
        self, repairs: list[Repair], findings: list[Finding]
    ) -> list[Repair]:
        """
        Execute repairs that are safe to auto-apply.
        Updates the `applied` flag and marks related findings as repaired.
        Returns the list of applied repairs.
        """
        if not self.apply:
            return []
        applied: list[Repair] = []
        finding_map: dict[tuple, Finding] = {
            (f.file_path, f.json_path, f.value): f for f in findings
        }
        for rep in repairs:
            try:
                ok = self._execute(rep)
                if ok:
                    rep.applied = True
                    applied.append(rep)
                    # Mark the originating finding as repaired
                    key = (rep.file_path, rep.json_path, rep.old_value)
                    if key in finding_map:
                        finding_map[key].is_auto_repaired = True
                        finding_map[key].repaired_value = rep.new_value
            except Exception as exc:
                print(f"[WARN] Repair failed ({rep.repair_type} {rep.file_path}): {exc}")
        return applied

    # ── repair derivation ─────────────────────────────────────────────────
    def _repair_url(self, f: Finding) -> Repair | None:
        normalized = _normalize_url(f.value)
        if normalized is None:
            return None
        return Repair(
            repair_type="normalize_url",
            file_path=f.file_path,
            json_path=f.json_path,
            old_value=f.value,
            new_value=normalized,
            rationale="Normalize URL to canonical https form.",
        )

    def _repair_wrong_pmid(self, f: Finding) -> Repair | None:
        """If the missing PMID has a known replacement in the wrong-PMID map."""
        replacement = self._wrong_pmid_map.get(f.value)
        if not replacement:
            return None
        return Repair(
            repair_type="replace_pmid",
            file_path=f.file_path,
            json_path=f.json_path,
            old_value=f.value,
            new_value=replacement,
            rationale=f"Known wrong PMID {f.value} → verified replacement {replacement}.",
        )

    def _repair_parity(self, f: Finding) -> Repair | None:
        """
        For parity findings the `value` is the JSON filename and `file_path`
        is the out-of-date site-tree copy.  Source is docs/{value}.
        """
        docs_dir = self.repo_root / "docs"
        src = docs_dir / f.value
        if not src.exists():
            return None
        return Repair(
            repair_type="sync_json",
            file_path=f.file_path,
            json_path="(file root)",
            old_value="(stale copy)",
            new_value=str(src),
            rationale=f"Sync canonical docs/{f.value} to {f.file_path}.",
        )

    def _repair_sequence(self, f: Finding) -> Repair | None:
        """Only normalise formatting (whitespace/case); skip alphabet errors."""
        if "invalid AA characters" in f.message:
            return None  # cannot auto-fix unknown characters
        raw = f.value.rstrip("…").rstrip("…")
        cleaned = _normalize_sequence(raw)
        if cleaned is None:
            return None
        return Repair(
            repair_type="normalize_seq",
            file_path=f.file_path,
            json_path=f.json_path,
            old_value=f.value,
            new_value=cleaned,
            rationale="Normalize sequence formatting (whitespace/case).",
        )

    # ── execution ─────────────────────────────────────────────────────────
    def _execute(self, rep: Repair) -> bool:
        abs_path = self.repo_root / rep.file_path
        if rep.repair_type == "sync_json":
            src = Path(rep.new_value)  # new_value is canonical source path
            dst = abs_path
            if not src.exists() or not dst.exists():
                return False
            shutil.copy2(src, dst)
            return True
        elif rep.repair_type in ("normalize_url", "replace_pmid", "normalize_seq"):
            return self._patch_file(abs_path, rep.old_value, rep.new_value)
        return False

    @staticmethod
    def _patch_file(path: Path, old: str, new: str) -> bool:
        """Replace first occurrence of `old` in file with `new` (text files only)."""
        if not path.exists():
            return False
        try:
            text = path.read_text(encoding="utf-8", errors="replace")
            if old not in text:
                return False
            patched = text.replace(old, new, 1)
            path.write_text(patched, encoding="utf-8")
            return True
        except Exception:
            return False
