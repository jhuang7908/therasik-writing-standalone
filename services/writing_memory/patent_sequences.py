"""
Patent sequence listing extraction (antibody-focused MVP).

Downloads WIPO ST.26 (or legacy ST.25 text) sequence listings from USPTO ODP
document metadata when available, parses protein/amino-acid rows, and tags
antibody-like chains by length/heuristics.

Does not run BLAST (Phase 2B). ANARCI numbering is Phase 2C (local anarcii env).
"""
from __future__ import annotations

import re
import xml.etree.ElementTree as ET
from typing import Any

import requests

try:
    from patent_client import _normalize_app_no, _odp_headers
except ImportError:
    from .patent_client import _normalize_app_no, _odp_headers  # type: ignore[attr-defined]

_USPTO_ODP_APP = "https://api.uspto.gov/api/v1/patent/applications"
_TIMEOUT = 45
_MAX_XML_BYTES = 6 * 1024 * 1024

_SEQ_DOC_CODES = frozenset({
    "SEQLST", "SEQL", "SEQ.LIST", "SEQ.XML", "WSEQ", "SEQDATA", "SLST",
})
_SEQ_DESC_HINTS = (
    "sequence listing", "sequence data", "st.26", "st.25", "insdseq",
    "amino acid sequence", "nucleotide sequence",
)

_AA_ALPHABET = re.compile(r"^[ACDEFGHIKLMNPQRSTVWY]+$")


def _local_tag(tag: str) -> str:
    return tag.split("}")[-1] if "}" in tag else tag


def _classify_antibody_chain(seq: str) -> dict[str, Any]:
    """Length/heuristic domain guess — [inferred], not ANARCI."""
    n = len(seq)
    kind = "protein"
    notes: list[str] = []
    if n < 20:
        kind = "peptide"
    elif 105 <= n <= 130:
        kind = "vh_like"
        notes.append("length consistent with VH (~110–120 aa)")
    elif 95 <= n <= 115:
        kind = "vl_like"
        notes.append("length consistent with VL (~100–110 aa)")
    elif 110 <= n <= 145 and seq.count("C") >= 2:
        kind = "vhh_like"
        notes.append("length consistent with VHH/nanobody (~120–130 aa)")
    elif n > 400:
        kind = "full_length"
        notes.append("long chain — may include constant region")
    if seq.startswith(("QVQL", "EVQL", "QVKL", "QMQL")):
        notes.append("N-term motif suggests heavy variable")
    if seq.startswith(("DIQMT", "EIVLT", "DIVMT", "QSVLT")):
        notes.append("N-term motif suggests light variable")
    return {"domain_guess": kind, "domain_notes": notes, "classification": "inferred"}


def _parse_sequence_listing_xml(xml_text: str) -> list[dict[str, Any]]:
    """Extract amino-acid sequences from ST.26 / INSDSeq XML (namespace-tolerant)."""
    found: list[dict[str, Any]] = []
    seen: set[str] = set()

    def _add(seq_id: str | None, seq: str) -> None:
        seq = re.sub(r"\s+", "", (seq or "").upper())
        if len(seq) < 8 or not _AA_ALPHABET.match(seq):
            return
        if seq in seen:
            return
        seen.add(seq)
        row: dict[str, Any] = {
            "seq_id": seq_id or f"SEQ{len(found) + 1}",
            "length": len(seq),
            "sequence": seq,
            "mol_type": "AA",
        }
        row.update(_classify_antibody_chain(seq))
        found.append(row)

    for m in re.finditer(
        r"<(?:[\w-]+:)?INSDSeq_sequence[^>]*>([A-Za-z\s]+)</(?:[\w-]+:)?INSDSeq_sequence>",
        xml_text,
        flags=re.I,
    ):
        _add(None, m.group(1))

    try:
        root = ET.fromstring(xml_text)
    except ET.ParseError:
        return found

    current_id: str | None = None
    current_mol = "AA"
    for elem in root.iter():
        tag = _local_tag(elem.tag)
        if tag == "SequenceData":
            current_id = elem.get("sequenceIDNumber") or elem.get("sequenceIdNumber")
        if tag in ("INSDSeq_moltype", "moltype") and elem.text:
            current_mol = elem.text.strip().upper()
        if tag == "INSDSeq_sequence" and elem.text:
            if current_mol in ("AA", "PRT", "PROTEIN", "") or len(elem.text.strip()) >= 8:
                _add(current_id, elem.text)
    return found


def _parse_st25_text(text: str) -> list[dict[str, Any]]:
    """Legacy ST.25 text listing."""
    found: list[dict[str, Any]] = []
    in_seq = False
    buf: list[str] = []
    seq_id = "SEQ1"

    for line in text.splitlines():
        if "<210>" in line:
            if buf:
                seq = "".join(buf).upper()
                if len(seq) >= 8 and _AA_ALPHABET.match(seq):
                    row = {"seq_id": seq_id, "length": len(seq), "sequence": seq, "mol_type": "AA"}
                    row.update(_classify_antibody_chain(seq))
                    found.append(row)
            buf = []
            in_seq = True
            m = re.search(r"<210>\s*(\d+)", line)
            if m:
                seq_id = f"SEQ{m.group(1)}"
            continue
        if in_seq:
            chunk = re.sub(r"[^A-Za-z]", "", line)
            if chunk:
                buf.append(chunk)
            if line.strip().startswith("<400>"):
                in_seq = False
    if buf:
        seq = "".join(buf).upper()
        if len(seq) >= 8 and _AA_ALPHABET.match(seq):
            row = {"seq_id": seq_id, "length": len(seq), "sequence": seq, "mol_type": "AA"}
            row.update(_classify_antibody_chain(seq))
            found.append(row)
    return found


def _fetch_document_bag(app_no: str, headers: dict[str, str]) -> list[dict[str, Any]]:
    r = requests.get(f"{_USPTO_ODP_APP}/{app_no}/documents", headers=headers, timeout=_TIMEOUT)
    r.raise_for_status()
    if "json" not in (r.headers.get("content-type") or "").lower():
        return []
    data = r.json()
    bags = data.get("documentBag") or data.get("documents") or []
    return [b for b in bags if isinstance(b, dict)]


def _sequence_listing_urls(bags: list[dict[str, Any]]) -> list[str]:
    urls: list[str] = []
    fallback: list[str] = []

    def _consider(url: str, mime: str, *, strict: bool) -> None:
        u = url.lower()
        m = mime.upper()
        if "XML" in m or u.endswith(".xml"):
            if strict or any(x in u for x in ("seq", "listing", "st26", "st25", "insd")):
                (urls if strict else fallback).append(url)
        elif m in ("TEXT", "TXT") or u.endswith(".txt"):
            if strict:
                urls.append(url)

    codes_present: set[str] = set()
    for doc in bags:
        code = (doc.get("documentCode") or "").upper()
        if code:
            codes_present.add(code)
        desc = (
            (doc.get("documentCodeDescriptionText") or "")
            + " "
            + (doc.get("documentDescription") or "")
        ).lower()
        strict = code in _SEQ_DOC_CODES or any(h in desc for h in _SEQ_DESC_HINTS)
        for opt in doc.get("downloadOptionBag") or []:
            if not isinstance(opt, dict):
                continue
            url = opt.get("downloadUrl")
            if not url:
                continue
            mime = opt.get("mimeTypeIdentifier") or ""
            _consider(url, mime, strict=strict)

    # Some recent applications list SEQ.XML in metadata but only expose XML on a sibling option.
    if not urls and codes_present.intersection(_SEQ_DOC_CODES):
        for doc in bags:
            for opt in doc.get("downloadOptionBag") or []:
                if not isinstance(opt, dict):
                    continue
                url = opt.get("downloadUrl") or ""
                if not url:
                    continue
                mime = (opt.get("mimeTypeIdentifier") or "").upper()
                u = url.lower()
                if "XML" in mime or u.endswith(".xml") or "sequence" in u:
                    urls.append(url)
    return urls or fallback


def sequence_listing_status_from_bags(bags: list[dict[str, Any]]) -> dict[str, Any]:
    """Whether ST.26 is posted vs downloadable via ODP (for patent detail panel)."""
    codes = sorted({
        str(d.get("documentCode") or "").upper()
        for d in bags
        if isinstance(d, dict) and d.get("documentCode")
    })
    has_code = any(c in _SEQ_DOC_CODES for c in codes)
    urls = _sequence_listing_urls(bags)
    note = ""
    if urls:
        note = "Sequence listing file available from USPTO ODP."
    elif has_code:
        note = (
            "File wrapper lists SEQ.XML/SEQLST but ODP has no downloadable sequence listing yet "
            "(common for very recent applications). Use Google Patents full text or paste ST.26/FASTA "
            "under Sequence / Structure."
        )
    else:
        note = (
            "No SEQLST/SEQ.XML in USPTO file wrapper yet. Wait for USPTO posting or paste "
            "sequences from the specification."
        )
    return {
        "has_sequence_listing_code": has_code,
        "has_sequence_listing": bool(urls),
        "sequence_listing_fetchable": bool(urls),
        "document_codes_seen": codes,
        "sequence_listing_note": note,
    }


def parse_sequence_text(content: str) -> dict[str, Any]:
    """Parse pasted ST.26 XML or FASTA (antibody chains) without USPTO round-trip."""
    text = (content or "").strip()
    if len(text) < 8:
        return {"ok": False, "error": "Paste FASTA or ST.26 XML (≥8 characters).", "sequences": []}
    if "<" in text and ("INSDSeq" in text or "SequenceData" in text or "sequence listing" in text.lower()):
        sequences = _parse_sequence_listing_xml(text)
        src = "st26_xml"
    else:
        sequences = _parse_fasta(text)
        src = "fasta"
    antibody_like = [s for s in sequences if s.get("domain_guess") in ("vh_like", "vl_like", "vhh_like")]
    return {
        "ok": len(sequences) > 0,
        "sequences": sequences,
        "antibody_like": antibody_like,
        "count": len(sequences),
        "antibody_like_count": len(antibody_like),
        "source": src,
        "verification_status": "user-provided",
        "note": (
            f"Parsed {len(sequences)} chain(s) from pasted {src}. "
            "Domain tags are heuristic [inferred]."
        ) if sequences else "No protein sequences recognized in pasted text.",
    }


def _parse_fasta(text: str) -> list[dict[str, Any]]:
    found: list[dict[str, Any]] = []
    seen: set[str] = set()
    hdr = "SEQ1"
    buf: list[str] = []
    for line in text.splitlines():
        line = line.strip()
        if not line:
            continue
        if line.startswith(">"):
            if buf:
                seq = "".join(buf).upper()
                if len(seq) >= 8 and _AA_ALPHABET.match(seq) and seq not in seen:
                    seen.add(seq)
                    row = {"seq_id": hdr, "length": len(seq), "sequence": seq, "mol_type": "AA"}
                    row.update(_classify_antibody_chain(seq))
                    found.append(row)
            hdr = line[1:].split()[0] or f"SEQ{len(found)+1}"
            buf = []
        else:
            buf.append(re.sub(r"[^A-Za-z]", "", line))
    if buf:
        seq = "".join(buf).upper()
        if len(seq) >= 8 and _AA_ALPHABET.match(seq) and seq not in seen:
            row = {"seq_id": hdr, "length": len(seq), "sequence": seq, "mol_type": "AA"}
            row.update(_classify_antibody_chain(seq))
            found.append(row)
    return found


def _download_listing(url: str, headers: dict[str, str]) -> tuple[str, str]:
    r = requests.get(url, headers=headers, timeout=_TIMEOUT, stream=True)
    r.raise_for_status()
    chunks: list[bytes] = []
    size = 0
    for chunk in r.iter_content(65536):
        if not chunk:
            continue
        size += len(chunk)
        if size > _MAX_XML_BYTES:
            raise ValueError("Sequence listing exceeds size limit")
        chunks.append(chunk)
    raw = b"".join(chunks)
    ctype = (r.headers.get("content-type") or "").lower()
    text = raw.decode("utf-8", errors="replace")
    fmt = "xml" if "xml" in ctype or text.lstrip().startswith("<") else "text"
    return text, fmt


def fetch_patent_sequences(patent_id: str) -> dict[str, Any]:
    """
    Return parsed antibody-relevant protein sequences from USPTO sequence listing docs.
    """
    app_no = _normalize_app_no(patent_id)
    if len(app_no) < 4:
        return {"ok": False, "error": "Invalid application number", "sequences": []}

    headers = _odp_headers()
    if not headers:
        return {
            "ok": False,
            "error": "USPTO_ODP_API_KEY not configured",
            "sequences": [],
            "verification_status": "unverified",
        }

    out: dict[str, Any] = {
        "ok": False,
        "application_number": app_no,
        "sequences": [],
        "antibody_like": [],
        "source": "uspto_odp_seqlisting",
        "verification_status": "verified",
    }
    warnings: list[str] = []

    try:
        bags = _fetch_document_bag(app_no, headers)
    except Exception as exc:
        return {"ok": False, "error": str(exc), "sequences": [], "application_number": app_no}

    urls = _sequence_listing_urls(bags)
    if not urls:
        codes = sorted({str(d.get("documentCode") or "") for d in bags if d.get("documentCode")})[:24]
        out["ok"] = True
        out["document_codes_seen"] = codes
        out["note"] = (
            "No sequence listing XML in USPTO file wrapper for this application. "
            "Try a granted antibody patent, paste FASTA/ST.26 under Sequence / Structure, "
            "or wait until SEQLST is posted to ODP."
        )
        out["verification_status"] = "unverified"
        return out

    all_seqs: list[dict[str, Any]] = []
    for url in urls[:3]:
        try:
            text, fmt = _download_listing(url, headers)
            batch = _parse_sequence_listing_xml(text) if fmt == "xml" else _parse_st25_text(text)
            all_seqs.extend(batch)
        except Exception as exc:
            warnings.append(str(exc))

    # Deduplicate by sequence string
    dedup: dict[str, dict[str, Any]] = {}
    for s in all_seqs:
        dedup[s["sequence"]] = s
    sequences = list(dedup.values())
    antibody_like = [
        s for s in sequences
        if s.get("domain_guess") in ("vh_like", "vl_like", "vhh_like")
    ]

    out["sequences"] = sequences
    out["antibody_like"] = antibody_like
    out["count"] = len(sequences)
    out["antibody_like_count"] = len(antibody_like)
    out["ok"] = len(sequences) > 0
    if warnings:
        out["warnings"] = warnings
    if not sequences:
        out["note"] = (
            "Sequence listing file(s) found but no protein sequences parsed. "
            "File may be ST.26 nucleotide-only or use an unsupported layout."
        )
        out["verification_status"] = "inferred"
    else:
        out["note"] = (
            f"Parsed {len(sequences)} protein sequence(s); "
            f"{len(antibody_like)} match antibody chain length heuristics [inferred]. "
            "Confirm with ANARCI/Kabat before engineering use."
        )
    return out
