#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
scripts/build_framework_library_from_imgt.py

 IMGT reference FASTA  framework library（FR1–FR3 only）。

（fail-fast / no invention）：
1)  core/data/framework_library/targets.yaml
2)  core/data/imgt_ref/  FASTA（）
3)  target allele:
   -  fasta record（header  allele；）
   -  ANARCII  IMGT/Kabat 
   -  IMGT  FR1, FR2, FR3（ FR4）
   - ：
     - fr_sequence_fr1_fr3 = FR1+FR2+FR3（FR4）
     - fr_segments: {fr1, fr2, fr3}
     - numbering_maps: {imgt_to_kabat, kabat_to_imgt}（）
     - source_trace: {source_file, fasta_header, sha256(sequence)}
4) ：
   - core/data/framework_library/vh_frameworks.yaml
   - core/data/framework_library/vl_frameworks.yaml
5) ：
   - （fail-fast）
   - 
   - 
6)  build log: docs/framework_library_build_log.md
   - /
   - 
   - 
"""

from __future__ import annotations

import argparse
import hashlib
import re
import sys
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, Iterable, List, Optional, Tuple

import yaml

PROJECT_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT_ROOT))

from core.numbering.imgt_anarcii import imgt_number_anarcii, IMGTNumberingError
from core.numbering.dual_map import build_dual_map, DualMapError
from core.vhh_humanization import split_regions

FASTA_EXTS = {".fa", ".fasta", ".faa", ".fsa", ".fas", ".txt"}


@dataclass(frozen=True)
class FastaRecord:
    source_file: str  # relative to core/data/imgt_ref
    header: str       # full header text (without '>')
    sequence: str     # AA sequence (uppercase, no spaces)


def sha256_hex(s: str) -> str:
    return hashlib.sha256(s.encode("utf-8")).hexdigest()


def clean_aa_sequence(seq: str) -> str:
    seq = seq.strip().upper().replace(" ", "").replace("\n", "").replace("\r", "").replace("*", "")
    # keep only standard AA letters; if anything else exists, treat as error (no silent cleanup)
    if not seq:
        raise ValueError("Empty sequence after cleaning")
    non_std = sorted(set([c for c in seq if c not in set("ACDEFGHIKLMNPQRSTVWY")]))
    if non_std:
        raise ValueError(f"Non-standard AA characters found: {non_std}")
    return seq


def iter_fasta_records(path: Path) -> Iterable[Tuple[str, str]]:
    """Yield (header_without_gt, sequence) from a FASTA file."""
    header: Optional[str] = None
    seq_parts: List[str] = []
    with open(path, "r", encoding="utf-8") as f:
        for raw in f:
            line = raw.strip()
            if not line:
                continue
            if line.startswith(">"):
                if header is not None:
                    yield header, "".join(seq_parts)
                header = line[1:].strip()
                seq_parts = []
            else:
                seq_parts.append(line)
        if header is not None:
            yield header, "".join(seq_parts)


ALLELE_REGEX = re.compile(r"\b(IGHV|IGKV|IGLV)(\d+)-(\d+)\*(\d+)\b", re.IGNORECASE)


def extract_human_alleles_from_header(header: str) -> List[str]:
    """Extract human-like allele IDs (IGHV/IGKV/IGLV...) from header."""
    alleles: List[str] = []
    for m in ALLELE_REGEX.finditer(header):
        prefix = m.group(1).upper()
        fam = m.group(2)
        gene = m.group(3)
        allele = m.group(4)
        alleles.append(f"{prefix}{fam}-{gene}*{allele}")
    return sorted(set(alleles))


def gene_key(allele: str) -> str:
    """
    Return gene key without allele (e.g. IGHV3-23 from IGHV3-23*01).
    If not parseable, returns uppercased input.
    """
    a = allele.strip().upper()
    if "*" in a:
        return a.split("*", 1)[0]
    return a


def family_from_allele(allele: str) -> str:
    """
    Compute family field used in YAML (e.g. IGHV3, IGKV1, IGLV2).
    """
    a = allele.strip().upper()
    m = re.match(r"^(IGHV|IGKV|IGLV)(\d+)-", a)
    if not m:
        return "TODO"
    return f"{m.group(1)}{m.group(2)}"


def load_targets(targets_path: Path) -> Dict[str, List[str]]:
    """
    Load targets from YAML. Supports both formats:
    - Old: list of strings ["IGHV3-23*01", ...]
    - New: list of objects [{"germline": "IGHV3-23*01", "tier": "...", ...}, ...]
    """
    if not targets_path.exists():
        raise FileNotFoundError(f"targets.yaml not found: {targets_path}")
    with open(targets_path, "r", encoding="utf-8") as f:
        data = yaml.safe_load(f) or {}
    
    # Support both old format (with "targets:" wrapper) and new format (direct keys)
    if "targets" in data and isinstance(data["targets"], dict):
        t = data["targets"]
    else:
        # New format: direct keys at top level
        t = data
    
    required = ["human_vh_targets", "human_vl_targets", "dog_vh_targets", "dog_vl_targets"]
    for k in required:
        if k not in t or not isinstance(t[k], list):
            raise ValueError(f"targets.yaml missing list: {k}")
    
    # Extract germline IDs from either format
    result: Dict[str, List[str]] = {}
    for k in required:
        alleles: List[str] = []
        for item in t[k]:
            if isinstance(item, str):
                # Old format: direct string
                alleles.append(item.strip())
            elif isinstance(item, dict):
                # New format: object with "germline" field
                germline = item.get("germline", "")
                if germline:
                    alleles.append(str(germline).strip())
            else:
                raise ValueError(f"Invalid target entry in {k}: expected string or dict with 'germline' field")
        result[k] = alleles
    
    return result


def scan_imgt_ref_fastas(imgt_ref_dir: Path) -> Tuple[Dict[str, List[FastaRecord]], List[str]]:
    """
    Scan all FASTA-like files in imgt_ref_dir recursively.

    Returns:
      - allele_index: allele -> list of records where header contains that allele
      - scanned_files: list of relative file paths scanned
    """
    if not imgt_ref_dir.exists():
        raise FileNotFoundError(f"imgt_ref directory not found: {imgt_ref_dir}")

    # Collect FASTA files with glob pattern before reading records
    fasta_files: List[Path] = []
    for pattern in ["*.fa", "*.fasta", "*.faa", "*.fsa", "*.fas"]:
        fasta_files.extend(imgt_ref_dir.rglob(pattern))
    
    # Remove duplicates and filter to only files
    fasta_files = sorted(set([fp for fp in fasta_files if fp.is_file()]))
    
    # Print matched files before reading
    print("=" * 80)
    print("IMGT FASTA File Scan")
    print("=" * 80)
    if not fasta_files:
        raise SystemExit(
            f"No FASTA files found in {imgt_ref_dir}. "
            f"Expected IMGT reference FASTA (.fa/.fasta)."
        )
    
    print(f"Found {len(fasta_files)} FASTA file(s):")
    for fp in fasta_files:
        rel = str(fp.relative_to(imgt_ref_dir)).replace("\\", "/")
        print(f"  {rel}")
    print("=" * 80)

    allele_index: Dict[str, List[FastaRecord]] = {}
    scanned: List[str] = []
    total_records_loaded = 0

    for fp in fasta_files:
        # Additional check: must contain '>' lines (skip README or other non-fasta text)
        try:
            content_head = fp.read_text(encoding="utf-8", errors="ignore")[:2048]
        except Exception:
            continue
        if ">" not in content_head:
            continue

        rel = str(fp.relative_to(imgt_ref_dir)).replace("\\", "/")
        scanned.append(rel)

        for header, seq in iter_fasta_records(fp):
            alleles = extract_human_alleles_from_header(header)
            if not alleles:
                continue
            seq_clean = clean_aa_sequence(seq)
            rec = FastaRecord(source_file=rel, header=header, sequence=seq_clean)
            total_records_loaded += 1
            for a in alleles:
                allele_index.setdefault(a, []).append(rec)

    print(f"[INFO] FASTA records loaded: {total_records_loaded}")
    print()

    return allele_index, scanned


def find_record_or_raise(
    allele: str,
    allele_index: Dict[str, List[FastaRecord]],
) -> FastaRecord:
    allele_u = allele.strip().upper()
    recs = allele_index.get(allele_u, [])

    if len(recs) == 1:
        return recs[0]

    if len(recs) > 1:
        sources = [f"{r.source_file} :: {r.header}" for r in recs[:10]]
        raise RuntimeError(
            "Allele matched multiple FASTA records (ambiguous). "
            f"allele={allele_u}. Examples:\n- " + "\n- ".join(sources)
        )

    # Exact match failed. Try relaxed matching: base gene + allele token in header
    base_gene = gene_key(allele_u)  # e.g., "IGHV3-23" from "IGHV3-23*01"
    allele_token = "*" + allele_u.split("*", 1)[1] if "*" in allele_u else ""  # e.g., "*01"
    
    # Collect all unique records from allele_index (dedupe by object identity)
    all_records: List[FastaRecord] = []
    seen_records = set()
    for records_list in allele_index.values():
        for rec in records_list:
            # Use (source_file, header) as unique key since FastaRecord is frozen
            rec_key = (rec.source_file, rec.header)
            if rec_key not in seen_records:
                seen_records.add(rec_key)
                all_records.append(rec)
    
    # Find records with headers containing base gene
    candidate_records: List[FastaRecord] = []
    candidate_headers: List[str] = []
    base_gene_upper = base_gene.upper()
    
    for rec in all_records:
        header_upper = rec.header.upper()
        if base_gene_upper in header_upper:
            candidate_records.append(rec)
            candidate_headers.append(rec.header)
    
    # Try relaxed matching: base gene AND allele token both in header
    if allele_token:
        allele_token_upper = allele_token.upper()
        relaxed_matches = []
        for rec in candidate_records:
            header_upper = rec.header.upper()
            if base_gene_upper in header_upper and allele_token_upper in header_upper:
                relaxed_matches.append(rec)
        
        if len(relaxed_matches) == 1:
            return relaxed_matches[0]
        
        if len(relaxed_matches) > 1:
            sources = [f"{r.source_file} :: {r.header}" for r in relaxed_matches[:10]]
            raise RuntimeError(
                f"Allele {allele_u} matched multiple FASTA records after relaxed matching "
                f"(base gene '{base_gene}' + allele token '{allele_token}'). "
                f"Ambiguous result. Examples:\n- " + "\n- ".join(sources)
            )
    
    # Still not found: raise error with candidate headers (top 30)
    candidate_headers_sorted = sorted(set(candidate_headers))[:30]
    error_msg = (
        f"No FASTA record found for germline: {allele_u}\n"
        f"Base gene searched: {base_gene}\n"
        f"Allele token searched: {allele_token if allele_token else 'N/A'}\n"
        f"\nTop {len(candidate_headers_sorted)} FASTA headers containing '{base_gene}':\n"
    )
    for i, header in enumerate(candidate_headers_sorted, 1):
        error_msg += f"  {i}. {header}\n"
    
    raise RuntimeError(error_msg)


def build_numbering_maps(seq: str) -> Dict[str, Dict[str, str]]:
    """
    Build IMGT<->Kabat maps using residue-level dual_map.

    Returns:
      { \"imgt_to_kabat\": {...}, \"kabat_to_imgt\": {...} }

    Strict behavior:
    - If dual map build fails or status is not 'full', raise.
    """
    dual, status, _chain_type = build_dual_map(seq)
    if status != "full":
        raise RuntimeError(f"Dual numbering status is not full: {status}")

    imgt_to_kabat: Dict[str, str] = {}
    kabat_to_imgt: Dict[str, str] = {}

    for entry in dual:
        imgt_pos = entry.get("imgt_pos")
        kabat_pos = entry.get("kabat_pos")
        if not imgt_pos or not kabat_pos:
            continue
        # Ensure one-to-one consistency
        if imgt_pos in imgt_to_kabat and imgt_to_kabat[imgt_pos] != kabat_pos:
            raise RuntimeError(f"Conflicting map for IMGT {imgt_pos}: {imgt_to_kabat[imgt_pos]} vs {kabat_pos}")
        if kabat_pos in kabat_to_imgt and kabat_to_imgt[kabat_pos] != imgt_pos:
            raise RuntimeError(f"Conflicting map for Kabat {kabat_pos}: {kabat_to_imgt[kabat_pos]} vs {imgt_pos}")
        imgt_to_kabat[imgt_pos] = kabat_pos
        kabat_to_imgt[kabat_pos] = imgt_pos

    if not imgt_to_kabat or not kabat_to_imgt:
        raise RuntimeError("Empty IMGT<->Kabat mapping produced")

    return {"imgt_to_kabat": imgt_to_kabat, "kabat_to_imgt": kabat_to_imgt}


def extract_fr_segments_from_imgt_numbering(seq: str) -> Tuple[str, Dict[str, str]]:
    """
    Run ANARCII IMGT numbering and extract FR1/FR2/FR3 via IMGT boundaries.
    Returns:
      (fr_sequence_fr1_fr3, {fr1, fr2, fr3})
    """
    rows = imgt_number_anarcii(seq)  # raises IMGTNumberingError on fail
    regions = split_regions(rows)
    fr1 = regions.get("FR1", "")
    fr2 = regions.get("FR2", "")
    fr3 = regions.get("FR3", "")

    # Strict boundary presence (no silent truncation accepted here)
    if not fr1 or not fr2 or not fr3:
        raise RuntimeError(f"Missing FR regions after IMGT segmentation: FR1={len(fr1)}, FR2={len(fr2)}, FR3={len(fr3)}")

    fr = fr1 + fr2 + fr3
    if not fr:
        raise RuntimeError("Empty FR1+FR2+FR3 sequence extracted")

    return fr, {"fr1": fr1, "fr2": fr2, "fr3": fr3}


def make_framework_entry(chain: str, allele: str, rec: FastaRecord) -> Dict[str, Any]:
    """
    Create one framework YAML entry for the given allele.
    """
    fr_sequence, fr_segments = extract_fr_segments_from_imgt_numbering(rec.sequence)
    numbering_maps = build_numbering_maps(rec.sequence)

    return {
        "framework_id": f"{chain}:{allele}",
        "chain": chain,
        "family": family_from_allele(allele),
        "germline": allele,
        "fr_sequence_fr1_fr3": fr_sequence,
        "fr_segments": fr_segments,
        "numbering_maps": numbering_maps,
        "source_trace": {
            "source_file": rec.source_file,
            "fasta_header": rec.header,
            "sha256": sha256_hex(rec.sequence),
        },
        # Do NOT fabricate canonical; keep TODO unless internal mapping exists.
        "canonical": {
            "cdr1": {"length_mode": "TODO", "length_range": "TODO", "class": "TODO"},
            "cdr2": {"length_mode": "TODO", "length_range": "TODO", "class": "TODO"},
        },
        "cdr3_policy": {"preferred_max": "TODO", "caution_range": "TODO", "high_risk_min": "TODO"},
        "tags": ["tier1"],
        "use_cases": [],
        "avoid_cases": [],
        "evidence": [
            {
                "type": "internal",
                "note": "Extracted from IMGT reference FASTA; see source_trace for file/header/sha256. No biological claims implied.",
            }
        ],
    }


def write_yaml(path: Path, frameworks: List[Dict[str, Any]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with open(path, "w", encoding="utf-8") as f:
        yaml.safe_dump({"frameworks": frameworks}, f, sort_keys=False, allow_unicode=True)


def render_build_log(
    *,
    started_at: str,
    targets_path: Path,
    imgt_ref_dir: Path,
    scanned_files: List[str],
    successes: List[Dict[str, Any]],
    failures: List[Dict[str, Any]],
    skips: List[Dict[str, Any]],
) -> str:
    lines: List[str] = []
    lines.append("# Framework Library Build Log")
    lines.append("")
    lines.append(f"**Started:** {started_at}")
    lines.append(f"**Targets:** `{targets_path.as_posix()}`")
    lines.append(f"**IMGT FASTA dir:** `{imgt_ref_dir.as_posix()}`")
    lines.append("")

    lines.append("## FASTA Scan")
    lines.append("")
    lines.append(f"- **Scanned files:** {len(scanned_files)}")
    for fp in scanned_files[:50]:
        lines.append(f"  - `{fp}`")
    if len(scanned_files) > 50:
        lines.append(f"  - ... and {len(scanned_files) - 50} more")
    lines.append("")

    lines.append("## Summary")
    lines.append("")
    lines.append(f"- **Success:** {len(successes)}")
    lines.append(f"- **Failed:** {len(failures)}")
    lines.append(f"- **Skipped (TODO targets):** {len(skips)}")
    lines.append("")

    if skips:
        lines.append("## Skipped Targets (non-actionable)")
        lines.append("")
        lines.append("| target | reason |")
        lines.append("|---|---|")
        for s in skips:
            lines.append(f"| {s.get('target')} | {s.get('reason')} |")
        lines.append("")

    if successes:
        lines.append("## Success Entries")
        lines.append("")
        lines.append("| chain | allele | source_file | sha256 | fr_len | header |")
        lines.append("|---|---|---|---|---:|---|")
        for e in successes:
            st = e["source_trace"]
            fr_len = len(e.get("fr_sequence_fr1_fr3", ""))
            header = st.get("fasta_header", "")
            header_short = header if len(header) <= 80 else header[:77] + "..."
            lines.append(
                f"| {e.get('chain')} | {e.get('germline')} | `{st.get('source_file')}` | `{st.get('sha256')}` | {fr_len} | {header_short} |"
            )
        lines.append("")

    if failures:
        lines.append("## Failure Entries (build aborted)")
        lines.append("")
        lines.append("| chain | allele | reason | details |")
        lines.append("|---|---|---|---|")
        for f in failures:
            details = f.get("details", "")
            details_short = details if len(details) <= 120 else details[:117] + "..."
            lines.append(f"| {f.get('chain')} | {f.get('allele')} | {f.get('reason')} | {details_short} |")
        lines.append("")

    lines.append("## Notes")
    lines.append("")
    lines.append("- Fail-fast: any numbering/segmentation failure aborts the build.")
    lines.append("- No sequences are inferred; all sequences are extracted directly from FASTA records.")
    lines.append("- FR definition: FR1–FR3 only (FR4 excluded by definition).")
    lines.append("")

    return "\n".join(lines)


def main() -> int:
    parser = argparse.ArgumentParser(description="Build framework library from IMGT FASTA (strict, targets-driven)")
    parser.add_argument(
        "--targets",
        type=Path,
        default=PROJECT_ROOT / "core" / "data" / "framework_library" / "targets.yaml",
        help="Path to targets.yaml",
    )
    parser.add_argument(
        "--imgt_ref_dir",
        type=Path,
        default=None,
        help="Directory containing IMGT FASTA files (can include multiple files)",
    )
    parser.add_argument(
        "--imgt_dir",
        type=Path,
        default=None,
        help="Alias for --imgt_ref_dir",
    )
    parser.add_argument(
        "--out_vh",
        type=Path,
        default=None,
        help="Output VH frameworks YAML",
    )
    parser.add_argument(
        "--out_vl",
        type=Path,
        default=None,
        help="Output VL frameworks YAML",
    )
    parser.add_argument(
        "--out_dir",
        type=Path,
        default=None,
        help="Output directory (sets --out_vh and --out_vl relative to this)",
    )
    parser.add_argument(
        "--scheme",
        type=str,
        default="imgt",
        help="Numbering scheme (default: imgt, currently only IMGT is supported)",
    )
    parser.add_argument(
        "--build_log",
        type=Path,
        default=PROJECT_ROOT / "docs" / "framework_library_build_log.md",
        help="Build log path",
    )
    args = parser.parse_args()
    
    # Resolve imgt_ref_dir (support both --imgt_ref_dir and --imgt_dir)
    if args.imgt_dir is not None:
        imgt_ref_dir = args.imgt_dir
    elif args.imgt_ref_dir is not None:
        imgt_ref_dir = args.imgt_ref_dir
    else:
        imgt_ref_dir = PROJECT_ROOT / "core" / "data" / "imgt_ref"
    
    # Resolve output paths (support --out_dir or individual --out_vh/--out_vl)
    if args.out_dir is not None:
        out_vh = args.out_dir / "vh_frameworks.yaml"
        out_vl = args.out_dir / "vl_frameworks.yaml"
    else:
        out_vh = args.out_vh or (PROJECT_ROOT / "core" / "data" / "framework_library" / "vh_frameworks.yaml")
        out_vl = args.out_vl or (PROJECT_ROOT / "core" / "data" / "framework_library" / "vl_frameworks.yaml")
    
    # Validate scheme (currently only IMGT is supported)
    if args.scheme.lower() != "imgt":
        raise ValueError(f"Unsupported numbering scheme: {args.scheme}. Only 'imgt' is currently supported.")

    started_at = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    successes: List[Dict[str, Any]] = []
    failures: List[Dict[str, Any]] = []
    skips: List[Dict[str, Any]] = []

    try:
        targets = load_targets(args.targets)
        allele_index, scanned_files = scan_imgt_ref_fastas(imgt_ref_dir)

        # Build ordered target lists
        vh_targets = []
        vl_targets = []

        for a in targets["human_vh_targets"] + targets["dog_vh_targets"]:
            vh_targets.append(str(a).strip())
        for a in targets["human_vl_targets"] + targets["dog_vl_targets"]:
            vl_targets.append(str(a).strip())

        vh_entries: List[Dict[str, Any]] = []
        vl_entries: List[Dict[str, Any]] = []

        # Process VH targets (fail-fast with per-allele reporting)
        for allele in vh_targets:
            allele = str(allele).strip()
            if not allele or allele.upper().startswith("TODO"):
                skips.append({"target": allele, "reason": "TODO target ( IMGT )"})
                continue
            chain = "VH"
            try:
                rec = find_record_or_raise(allele, allele_index)
                entry = make_framework_entry(chain, allele.strip().upper(), rec)
            except Exception as e:
                failures.append(
                    {
                        "chain": chain,
                        "allele": allele,
                        "reason": type(e).__name__,
                        "details": str(e),
                    }
                )
                raise
            vh_entries.append(entry)
            successes.append(entry)

        # Process VL targets (fail-fast with per-allele reporting)
        for allele in vl_targets:
            allele = str(allele).strip()
            if not allele or allele.upper().startswith("TODO"):
                skips.append({"target": allele, "reason": "TODO target ( IMGT )"})
                continue
            chain = "VL"
            try:
                rec = find_record_or_raise(allele, allele_index)
                entry = make_framework_entry(chain, allele.strip().upper(), rec)
            except Exception as e:
                failures.append(
                    {
                        "chain": chain,
                        "allele": allele,
                        "reason": type(e).__name__,
                        "details": str(e),
                    }
                )
                raise
            vl_entries.append(entry)
            successes.append(entry)

        # Write outputs only if everything succeeded
        write_yaml(args.out_vh, vh_entries)
        write_yaml(args.out_vl, vl_entries)

        log_text = render_build_log(
            started_at=started_at,
            targets_path=args.targets,
            imgt_ref_dir=args.imgt_ref_dir,
            scanned_files=scanned_files,
            successes=successes,
            failures=failures,
            skips=skips,
        )
        args.build_log.parent.mkdir(parents=True, exist_ok=True)
        args.build_log.write_text(log_text, encoding="utf-8")
        return 0

    except (IMGTNumberingError, DualMapError, Exception) as e:
        # Fail-fast: log the failure and abort. Do NOT write YAML outputs on failure.
        # (Per-allele failures are already appended above; this is a safety net.)
        if not failures:
            failures.append(
                {
                    "chain": "unknown",
                    "allele": "unknown",
                    "reason": type(e).__name__,
                    "details": str(e),
                }
            )
        # Best-effort build log
        try:
            # Re-scan list for log if possible
            scanned_files: List[str] = []
            if imgt_ref_dir.exists():
                _allele_index, scanned_files = scan_imgt_ref_fastas(imgt_ref_dir)
            log_text = render_build_log(
                started_at=started_at,
                targets_path=args.targets,
                imgt_ref_dir=imgt_ref_dir,
                scanned_files=scanned_files,
                successes=successes,
                failures=failures,
                skips=skips,
            )
            args.build_log.parent.mkdir(parents=True, exist_ok=True)
            args.build_log.write_text(log_text, encoding="utf-8")
        except Exception:
            pass
        raise


if __name__ == "__main__":
    sys.exit(main())
