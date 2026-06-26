"""Extract plain text from uploaded PDF bytes (full-text style learning)."""

from __future__ import annotations

import io


def extract_text_from_pdf_bytes(data: bytes, max_pages: int = 120) -> str:
    """
    Extract text from a PDF. Fails if the result is too short (e.g. scanned image PDF).
    """
    try:
        from pypdf import PdfReader
    except ImportError as exc:
        raise ValueError(
            "PDF support is not installed on the server (missing pypdf). "
            "Use .txt export or contact the administrator."
        ) from exc

    reader = PdfReader(io.BytesIO(data))
    parts: list[str] = []
    for i, page in enumerate(reader.pages):
        if i >= max_pages:
            break
        t = page.extract_text() or ""
        t = t.strip()
        if t:
            parts.append(t)
    text = "\n\n".join(parts).strip()
    if len(text) < 200:
        raise ValueError(
            "PDF text extraction returned too little text (<200 chars). "
            "Scanned/image PDFs need OCR or a text-based PDF export."
        )
    return text


def extract_text_from_upload(filename: str, raw: bytes) -> str:
    """Decode UTF-8 text files or extract text from PDF."""
    lower = (filename or "").lower()
    if lower.endswith(".pdf"):
        return extract_text_from_pdf_bytes(raw)
    try:
        return raw.decode("utf-8")
    except UnicodeDecodeError as exc:
        raise ValueError(
            f"File '{filename}': use PDF or UTF-8 text (.txt / .md)."
        ) from exc
