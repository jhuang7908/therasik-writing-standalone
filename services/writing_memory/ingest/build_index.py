"""
build_index.py — Step 5b: load embeddings/metadata.jsonl + vectors.npy
and build a lightweight cosine-similarity index saved as
    embeddings/index.npz   (vectors + metadata array, L2-normalised)

The index is designed to be loaded into memory once at API startup
(~750 vectors × 1536 dims = ~4 MB; trivial on any server).

Usage
-----
    python services/writing_memory/ingest/build_index.py

Output
------
    embeddings/index.npz
        'vectors'  float32 (N, 1536)   — L2-normalised for dot-product = cosine
        'pmids'    U20     (N,)         — PMID strings
        'journals' U10     (N,)         — journal keys
        'sections' U20     (N,)         — abstract | discussion | conclusion
        'ordinals' int32   (N,)         — chunk index within section
        'texts'    U8000   (N,)         — chunk text (≤ 8k chars each)
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

import numpy as np

_HERE = Path(__file__).resolve().parent
_SERVICE_ROOT = _HERE.parent
EMBEDDINGS_DIR = _SERVICE_ROOT / "embeddings"


def main() -> int:
    meta_path = EMBEDDINGS_DIR / "metadata.jsonl"
    vecs_path = EMBEDDINGS_DIR / "vectors.npy"
    index_path = EMBEDDINGS_DIR / "index.npz"

    if not meta_path.exists():
        print("ERROR: metadata.jsonl not found. Run embed_chunks.py first.", file=sys.stderr)
        return 1
    if not vecs_path.exists():
        print("ERROR: vectors.npy not found. Run embed_chunks.py first.", file=sys.stderr)
        return 1

    # Load metadata
    rows: list[dict] = []
    with meta_path.open(encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if line:
                try:
                    rows.append(json.loads(line))
                except Exception:
                    continue

    # Load raw vectors
    raw = np.load(str(vecs_path))
    print(f"Loaded: {len(rows)} metadata rows, {raw.shape} vectors")

    n = min(len(rows), raw.shape[0])
    if n < len(rows):
        print(f"Warning: {len(rows) - n} metadata rows have no matching vector — truncating")
    rows = rows[:n]
    raw = raw[:n]

    # L2-normalise so dot product == cosine similarity
    norms = np.linalg.norm(raw, axis=1, keepdims=True)
    norms = np.where(norms == 0, 1.0, norms)
    vecs_normed = (raw / norms).astype(np.float32)

    # Pack into numpy string arrays for compact storage
    pmids    = np.array([r.get("pmid",        "") for r in rows], dtype="U24")
    journals = np.array([r.get("journal_key", "") for r in rows], dtype="U12")
    sections = np.array([r.get("section",     "") for r in rows], dtype="U20")
    ordinals = np.array([r.get("ordinal",      0) for r in rows], dtype=np.int32)
    texts    = np.array([r.get("text",        "") for r in rows], dtype="U8000")

    np.savez_compressed(
        str(index_path),
        vectors  = vecs_normed,
        pmids    = pmids,
        journals = journals,
        sections = sections,
        ordinals = ordinals,
        texts    = texts,
    )

    size_kb = index_path.stat().st_size / 1024
    print(f"Index saved: {index_path}  ({size_kb:.0f} KB)  shape={vecs_normed.shape}")

    # Quick sanity: top-1 self-retrieval for the first chunk
    q = vecs_normed[0:1]
    scores = (vecs_normed @ q.T).squeeze()
    top_idx = int(np.argmax(scores))
    assert top_idx == 0, f"Self-retrieval failed: top-1 is {top_idx}"
    print(f"Sanity check: self-retrieval OK (top-1 score={scores[top_idx]:.4f})")
    return 0


if __name__ == "__main__":
    sys.exit(main())
