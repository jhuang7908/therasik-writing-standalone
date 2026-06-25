#!/usr/bin/env python3
"""
ACTES sequence verification: UniProt segment match and optional BLAST.
- For entries with design_info.uniprot_id and residue_range: fetch UniProt,
  extract segment, compare to canonical_sequence.
- Writes verify_report.json and verify_report.md; optionally runs BLAST (if
  BLAST_BIN or Biopython NCBIWWW available) for key entries.
"""
from __future__ import annotations

import json
import os
import re
import sys
from pathlib import Path

try:
    import requests
    _has_requests = True
except ImportError:
    requests = None
    _has_requests = False
try:
    from urllib.request import urlopen
    _has_urlopen = True
except ImportError:
    urlopen = None
    _has_urlopen = False

SCRIPT_DIR = Path(__file__).resolve.parent
DB_PATH = SCRIPT_DIR / "sequence_db.json"
REPORT_JSON = SCRIPT_DIR / "verify_report.json"
REPORT_MD = SCRIPT_DIR / "verify_report.md"
ALIGNMENTS_DIR = SCRIPT_DIR / "alignments"


def fetch_uniprot_sequence(accession: str) -> str | None:
    """Fetch canonical protein sequence from UniProt REST (FASTA)."""
    url = f"https://rest.uniprot.org/uniprotkb/{accession}.fasta"
    try:
        if _has_requests and requests:
            r = requests.get(url, timeout=15)
            r.raise_for_status
            text = r.text
        elif _has_urlopen and urlopen:
            with urlopen(url, timeout=15) as resp:
                text = resp.read.decode
        else:
            return None
    except Exception:
        return None
    lines = text.strip.splitlines
    if lines and lines[0].startswith(">"):
        raw = "".join(lines[1:])
    else:
        raw = "".join(lines)
    seq = raw.replace(" ", "").replace("\r", "").replace("\n", "")
    return seq if seq and seq.isalpha else None


def verify_entry(entry: dict) -> dict:
    """Verify one entry: UniProt segment match if applicable."""
    out = {
        "entry_id": entry.get("entry_id"),
        "type": entry.get("type", "protein"),
        "uniprot_verified": None,
        "uniprot_match": None,
        "uniprot_note": None,
        "canonical_len": None,
    }
    canonical = entry.get("canonical_sequence")
    if not canonical or not isinstance(canonical, str):
        out["uniprot_note"] = "no canonical_sequence"
        return out
    canonical = canonical.strip.replace(" ", "").replace("\r", "").replace("\n", "")
    out["canonical_len"] = len(canonical)

    design = entry.get("design_info") or {}
    uniprot_id = design.get("uniprot_id")
    residue_range = design.get("residue_range")
    if not uniprot_id or not residue_range or not isinstance(residue_range, (list, tuple)) or len(residue_range) != 2:
        out["uniprot_note"] = "no uniprot_id or residue_range in design_info"
        return out

    start, end = int(residue_range[0]), int(residue_range[1])
    full = fetch_uniprot_sequence(str(uniprot_id))
    if not full:
        out["uniprot_verified"] = False
        out["uniprot_note"] = f"UniProt {uniprot_id} fetch failed"
        return out
    # 1-based inclusive [start, end]
    segment = full[start - 1 : end]
    match = segment == canonical
    out["uniprot_verified"] = True
    out["uniprot_match"] = match
    out["uniprot_note"] = f"UniProt {uniprot_id} [{start}-{end}]: {'MATCH' if match else 'MISMATCH'}"
    if not match:
        out["expected_len"] = len(segment)
        out["segment_preview"] = (segment[:30] + "..." if len(segment) > 30 else segment)
        out["canonical_preview"] = (canonical[:30] + "..." if len(canonical) > 30 else canonical)
    return out


def run_blast_local(seq: str, entry_id: str) -> dict | None:
    """If BLAST+ is installed, run blastp -db swissprot -query -; return parsed summary."""
    import subprocess
    import tempfile
    with tempfile.NamedTemporaryFile(mode="w", suffix=".fasta", delete=False) as f:
        f.write(f"> {entry_id}\n{seq}\n")
        path = f.name
    try:
        cmd = [
            "blastp", "-db", "swissprot", "-query", path,
            "-outfmt", "6 qacc sacc pident length mismatch gapopen qstart qend sstart send evalue bitscore",
            "-max_target_seqs", "5", "-evalue", "1e-5"
        ]
        r = subprocess.run(cmd, capture_output=True, text=True, timeout=60, cwd=SCRIPT_DIR)
    except (FileNotFoundError, subprocess.TimeoutExpired):
        return None
    finally:
        try:
            os.unlink(path)
        except Exception:
            pass
    if r.returncode != 0 or not r.stdout.strip:
        return None
    lines = r.stdout.strip.splitlines
    hits = []
    for line in lines[:5]:
        parts = line.split("\t")
        if len(parts) >= 12:
            hits.append({
                "subject": parts[1],
                "pident": float(parts[2]),
                "length": int(parts[3]),
                "evalue": parts[10],
                "bitscore": parts[11],
            })
    return {"hits": hits, "note": "blastp vs swissprot"} if hits else None


def main:
    if not (SCRIPT_DIR / "sequence_db.json").exists:
        print("sequence_db.json not found", file=sys.stderr)
        sys.exit(1)
    with open(DB_PATH, "r", encoding="utf-8") as f:
        data = json.load(f)
    entries = data.get("entries", [])

    results = []
    for ent in entries:
        r = verify_entry(ent)
        if r.get("uniprot_verified") is True and r.get("canonical_len"):
            # Optional: run BLAST for first few key entries (slow)
            if os.environ.get("ACTES_RUN_BLAST") == "1" and ent.get("type") == "protein":
                blast = run_blast_local(ent.get("canonical_sequence", ""), ent.get("entry_id", ""))
                if blast:
                    r["blast"] = blast
        results.append(r)

    report = {
        "version": "1.0",
        "db_path": str(DB_PATH),
        "total_entries": len(entries),
        "uniprot_checked": sum(1 for r in results if r.get("uniprot_verified") is True),
        "uniprot_match": sum(1 for r in results if r.get("uniprot_match") is True),
        "uniprot_mismatch": sum(1 for r in results if r.get("uniprot_verified") is True and r.get("uniprot_match") is False),
        "results": results,
    }

    with open(REPORT_JSON, "w", encoding="utf-8") as f:
        json.dump(report, f, indent=2, ensure_ascii=False)

    # Markdown report
    lines = [
        "# ACTES ",
        "",
        f"- : {report['total_entries']}",
        f"-  UniProt : {report['uniprot_checked']}",
        f"- : {report['uniprot_match']}",
        f"- : {report['uniprot_mismatch']}",
        "",
        "## UniProt ",
        "",
        "| entry_id |  | UniProt  |  |  |",
        "| --- | --- | --- | --- | --- |",
    ]
    for r in results:
        eid = r.get("entry_id") or ""
        typ = r.get("type") or ""
        checked = "" if r.get("uniprot_verified") is True else ""
        if r.get("uniprot_match") is True:
            res = "✅ "
        elif r.get("uniprot_match") is False:
            res = "❌ "
        else:
            res = "—"
        note = (r.get("uniprot_note") or "").replace("|", "\\|")
        lines.append(f"| {eid} | {typ} | {checked} | {res} | {note} |")
    lines.extend(["", "---", ""])
    with open(REPORT_MD, "w", encoding="utf-8") as f:
        f.write("\n".join(lines))

    print(f"UniProt checked: {report['uniprot_checked']}, match: {report['uniprot_match']}, mismatch: {report['uniprot_mismatch']}")
    if report["uniprot_mismatch"]:
        for r in results:
            if r.get("uniprot_match") is False:
                print(f"  MISMATCH: {r.get('entry_id')} - {r.get('uniprot_note')}")
    return 0 if report["uniprot_mismatch"] == 0 else 1


if __name__ == "__main__":
    sys.exit(main)
