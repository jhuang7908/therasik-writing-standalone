"""
Build dog IGHV / IGKV / IGLV numbered cache (Kabat) from raw germline sequences.
Run in conda env anarcii:
    conda run --no-capture-output -n anarcii python scripts/build_dog_numbered_cache.py

Output: data/germlines/canis_lupus_familiaris_ig_aa/_cache/
  - dog_ighv_kabat_numbered_cache.json
  - dog_igkv_kabat_numbered_cache.json
  - dog_iglv_kabat_numbered_cache.json

Each file: { gene_id: { kabat_pos_str: aa } }
"""
from __future__ import annotations
import contextlib, io, json, sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

REPO = Path(__file__).resolve().parents[1]
DOG_DIR = REPO / "data/germlines/canis_lupus_familiaris_ig_aa"
OUT_DIR = DOG_DIR / "_cache"
OUT_DIR.mkdir(parents=True, exist_ok=True)

AA_ORDER = set("ACDEFGHIKLMNPQRSTVWY")


def number_seq(runner: Any, seq: str) -> dict[str, str] | None:
    seq = "".join(seq.upper().split())
    if not seq:
        return None
    try:
        with contextlib.redirect_stdout(io.StringIO()):
            runner.number(seq)
            kabat = runner.to_scheme("kabat")
    except Exception as e:
        print(f"    anarcii error: {e}", file=sys.stderr)
        return None
    seq_data = list(kabat.values())[0] if kabat else {}
    numbered = seq_data.get("numbering", [])
    result: dict[str, str] = {}
    for (pos, ins), aa in numbered:
        if not aa or aa == "-":
            continue
        ins_clean = str(ins).strip().upper()
        key = f"{int(pos)}{ins_clean}" if ins_clean else str(int(pos))
        if aa in AA_ORDER:
            result[key] = aa
    return result if result else None


def build_cache(locus_json: Path, locus: str) -> dict[str, Any]:
    from anarcii import Anarcii
    runner = Anarcii()

    data = json.loads(locus_json.read_text())
    entries = data.get("entries", [])
    cache: dict[str, dict[str, str]] = {}
    failures: list[str] = []

    for i, ent in enumerate(entries):
        gid = ent.get("id", f"unknown_{i}")
        seq = ent.get("sequence_aa", "")
        header = ent.get("raw_header", "")
        # Accept all entries (functional and ORF), filter by header later if needed
        if not seq:
            continue
        print(f"  [{i+1}/{len(entries)}] {gid} ({len(seq)} aa) ...", end=" ", flush=True)
        result = number_seq(runner, seq)
        if result:
            cache[gid] = result
            print(f"OK ({len(result)} positions)")
        else:
            failures.append(gid)
            print("FAILED")

    return {
        "_meta": {
            "species": "Canis lupus familiaris",
            "locus": locus,
            "numbering_scheme": "Kabat via anarcii",
            "n_input": len(entries),
            "n_cached": len(cache),
            "n_failed": len(failures),
            "failed_genes": failures,
            "generated_at": datetime.now(timezone.utc).isoformat(),
        },
        "genes": cache,
    }


def main():
    for locus in ("IGHV", "IGKV", "IGLV"):
        src = DOG_DIR / f"{locus}_aa.json"
        out = OUT_DIR / f"dog_{locus.lower()}_kabat_numbered_cache.json"
        if not src.exists():
            print(f"SKIP {locus}: {src} not found")
            continue
        print(f"\nBuilding {locus} cache from {src.name} ...")
        cache = build_cache(src, locus)
        out.write_text(json.dumps(cache, indent=2, ensure_ascii=False))
        n = cache["_meta"]["n_cached"]
        nf = cache["_meta"]["n_failed"]
        print(f"  -> {out.name}: {n} cached, {nf} failed")

    print("\nDone.")


if __name__ == "__main__":
    main()
