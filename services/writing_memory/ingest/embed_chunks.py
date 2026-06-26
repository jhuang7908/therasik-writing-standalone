"""
embed_chunks.py — Step 5a: split paper text into ~150-word chunks and embed
each chunk with OpenAI text-embedding-3-small.

Each chunk is saved as one row in
    embeddings/metadata.jsonl     — one JSON record per chunk
    embeddings/vectors.npy        — float32 numpy array, shape (N, 1536)

Both files grow incrementally — the script checks which papers are already
embedded and skips them (``--resume`` default behaviour).

Usage
-----
    # Smoke: 3 papers (1 per journal)
    python services/writing_memory/ingest/embed_chunks.py --smoke

    # Full 146 papers
    python services/writing_memory/ingest/embed_chunks.py

    # Resume after interruption
    python services/writing_memory/ingest/embed_chunks.py --resume

Environment
-----------
    OPENAI_API_KEY          required
    WRITING_MEMORY_PAPERS_DIR   override papers_raw location
"""

from __future__ import annotations

import argparse
import json
import os
import re
import sys
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import numpy as np

_HERE = Path(__file__).resolve().parent
_SERVICE_ROOT = _HERE.parent

PAPERS_DIR    = Path(os.environ.get("WRITING_MEMORY_PAPERS_DIR",
                                     str(_SERVICE_ROOT / "papers_raw")))
EMBEDDINGS_DIR = _SERVICE_ROOT / "embeddings"

EMBED_MODEL   = "text-embedding-3-small"
EMBED_DIM     = 1536
CHUNK_WORDS   = 150          # target words per chunk
CHUNK_OVERLAP = 20           # word overlap between adjacent chunks
SECTIONS      = ["abstract", "discussion", "conclusion"]
BATCH_SIZE    = 100          # OpenAI embedding batch size (max 2048)
RATE_DELAY    = 0.05         # seconds between API calls (3000 RPM limit)

JOURNAL_KEYS = ["pnas", "elife", "plos_med"]


# ---------------------------------------------------------------------------
# Text splitting
# ---------------------------------------------------------------------------

def _split_into_chunks(text: str, target_words: int = CHUNK_WORDS,
                       overlap: int = CHUNK_OVERLAP) -> list[str]:
    if not text:
        return []
    # Sentence-aware split: break on ". " or ".\n" then assemble chunks
    sentences = re.split(r"(?<=[.!?])\s+", text.strip())
    chunks: list[str] = []
    buf: list[str] = []
    buf_words = 0

    for sent in sentences:
        sent = sent.strip()
        if not sent:
            continue
        w = len(sent.split())
        buf.append(sent)
        buf_words += w
        if buf_words >= target_words:
            chunks.append(" ".join(buf))
            # overlap: keep last `overlap` words as seed for next chunk
            tail = " ".join(buf).split()[-overlap:]
            buf = [" ".join(tail)] if tail else []
            buf_words = len(tail)

    if buf:
        chunks.append(" ".join(buf))
    return [c for c in chunks if len(c.split()) >= 20]  # drop tiny fragments


# ---------------------------------------------------------------------------
# Collect chunks from all papers
# ---------------------------------------------------------------------------

def _collect_chunks(
    journals: list[str],
    smoke: bool,
    already_embedded: set[str],
) -> list[dict[str, Any]]:
    """Return list of chunk dicts (no embeddings yet)."""
    rows: list[dict[str, Any]] = []

    for jkey in journals:
        jdir = PAPERS_DIR / jkey
        if not jdir.exists():
            continue
        papers = sorted(jdir.glob("*.json"))
        if smoke:
            papers = papers[:1]

        for ppath in papers:
            pmid = ppath.stem
            if pmid in already_embedded:
                continue
            try:
                paper = json.loads(ppath.read_text(encoding="utf-8"))
            except Exception:
                continue

            for section in SECTIONS:
                text = (paper.get(section) or "").strip()
                if not text:
                    continue
                chunks = _split_into_chunks(text)
                for idx, chunk in enumerate(chunks):
                    rows.append({
                        "pmid":       pmid,
                        "journal_key": jkey,
                        "section":    section,
                        "ordinal":    idx,
                        "text":       chunk,
                        "word_count": len(chunk.split()),
                        "embed_model": EMBED_MODEL,
                        "embed_dim":  EMBED_DIM,
                        "created_at": datetime.now(timezone.utc).isoformat(),
                    })

    return rows


# ---------------------------------------------------------------------------
# Embed via OpenAI
# ---------------------------------------------------------------------------

def _embed_batch(texts: list[str], client: Any) -> list[list[float]]:
    response = client.embeddings.create(
        model=EMBED_MODEL,
        input=texts,
    )
    time.sleep(RATE_DELAY)
    return [item.embedding for item in response.data]


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def main(argv: list[str]) -> int:
    ap = argparse.ArgumentParser(
        description="Embed paper chunks with OpenAI text-embedding-3-small."
    )
    ap.add_argument("--journals", nargs="*", default=JOURNAL_KEYS)
    ap.add_argument("--smoke", action="store_true",
                    help="Process 1 paper per journal only")
    ap.add_argument("--resume", action="store_true", default=True,
                    help="Skip already-embedded PMIDs (default: on)")
    ap.add_argument("--no-resume", dest="resume", action="store_false")
    args = ap.parse_args(argv)

    api_key = os.environ.get("OPENAI_API_KEY", "")
    if not api_key:
        print("ERROR: OPENAI_API_KEY not set.", file=sys.stderr)
        return 1

    from openai import OpenAI
    client = OpenAI(api_key=api_key)

    EMBEDDINGS_DIR.mkdir(parents=True, exist_ok=True)
    meta_path  = EMBEDDINGS_DIR / "metadata.jsonl"
    vecs_path  = EMBEDDINGS_DIR / "vectors.npy"

    # Load already-embedded PMIDs from existing metadata
    already_embedded: set[str] = set()
    if args.resume and meta_path.exists():
        with meta_path.open(encoding="utf-8") as f:
            for line in f:
                try:
                    row = json.loads(line)
                    already_embedded.add(row["pmid"])
                except Exception:
                    continue
        print(f"Resume: {len(already_embedded)} PMIDs already embedded, skipping.")

    # Collect chunks
    print("Collecting chunks ...")
    chunks = _collect_chunks(args.journals, args.smoke, already_embedded)
    if not chunks:
        print("Nothing to embed.")
        return 0
    print(f"Chunks to embed: {len(chunks)}")

    # Load existing vectors (for appending)
    existing_vecs: list[np.ndarray] = []
    if args.resume and vecs_path.exists():
        existing_vecs_arr = np.load(str(vecs_path))
        existing_vecs = [existing_vecs_arr]
        print(f"Existing vectors: {existing_vecs_arr.shape[0]}")

    # Embed in batches
    texts = [c["text"] for c in chunks]
    all_vecs: list[list[float]] = []
    total_batches = (len(texts) + BATCH_SIZE - 1) // BATCH_SIZE

    for b_idx in range(0, len(texts), BATCH_SIZE):
        batch_texts = texts[b_idx : b_idx + BATCH_SIZE]
        batch_num = b_idx // BATCH_SIZE + 1
        print(f"  Embedding batch {batch_num}/{total_batches} "
              f"({len(batch_texts)} chunks) ...", end=" ", flush=True)
        try:
            vecs = _embed_batch(batch_texts, client)
            all_vecs.extend(vecs)
            print("ok")
        except Exception as exc:
            print(f"FAIL — {exc}")
            # On error, save what we have and exit gracefully
            break

    if not all_vecs:
        print("No vectors produced.")
        return 1

    # Build new matrix (only new vectors)
    new_mat = np.array(all_vecs, dtype=np.float32)

    # Append to existing vectors
    if existing_vecs:
        combined = np.vstack(existing_vecs + [new_mat])
    else:
        combined = new_mat

    # Save vectors
    np.save(str(vecs_path), combined)
    print(f"Saved vectors: shape={combined.shape}")

    # Append metadata
    with meta_path.open("a", encoding="utf-8") as f:
        for row in chunks[:len(all_vecs)]:
            f.write(json.dumps(row, ensure_ascii=False) + "\n")

    print(f"Metadata: {meta_path}")
    print(f"Vectors:  {vecs_path}")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
