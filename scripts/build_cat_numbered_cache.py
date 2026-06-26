"""
Build cat IGHV / IGKV / IGLV numbered cache (Kabat) from germline sequences.
Run in conda env anarcii:
    conda run --no-capture-output -n anarcii python scripts/build_cat_numbered_cache.py

Cat IGHV comes from cat_scaffold_cmc_optimization_tier1_tier2_v1.json (rows list).
Cat IGKV / IGLV come from IGKV_aa.json / IGLV_aa.json in felis_catus_ig_aa.

Output: data/germlines/felis_catus_ig_aa/_cache/
  - cat_ighv_kabat_numbered_cache.json
  - cat_igkv_kabat_numbered_cache.json
  - cat_iglv_kabat_numbered_cache.json
"""
from __future__ import annotations
import contextlib, io, json, sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

REPO = Path(__file__).resolve().parents[1]
CAT_DIR = REPO / "data/germlines/felis_catus_ig_aa"
OUT_DIR = CAT_DIR / "_cache"
OUT_DIR.mkdir(parents=True, exist_ok=True)

AA_ORDER = set("ACDEFGHIKLMNPQRSTVWY")


def number_seq(runner: Any, seq: str, gid: str = "") -> dict[str, str] | None:
    seq = "".join(seq.upper().split())
    if not seq:
        return None
    try:
        with contextlib.redirect_stdout(io.StringIO()):
            runner.number(seq)
            kabat = runner.to_scheme("kabat")
    except Exception as e:
        print(f"    anarcii error ({gid}): {e}", file=sys.stderr)
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


def _seq_from_row(row: dict) -> str:
    for k in ("sequence_aa_kabat_norm", "sequence_aa_imgt", "sequence_aa", "seq"):
        v = row.get(k)
        if isinstance(v, str) and v.strip():
            return v.strip()
    segs = row.get("fr_segments")
    if isinstance(segs, dict):
        return "".join(str(segs.get(k, "")) for k in ("FR1", "FR2", "FR3"))
    return ""


def build_ighv_from_scaffold(runner: Any) -> dict[str, Any]:
    scaffold_path = CAT_DIR / "cat_scaffold_cmc_optimization_tier1_tier2_v1.json"
    data = json.loads(scaffold_path.read_text())
    rows = [r for r in data.get("rows", []) if r.get("locus") == "IGHV" or r.get("chain") == "H"]
    print(f"  Cat IGHV: {len(rows)} sequences from scaffold")

    cache: dict[str, dict[str, str]] = {}
    failures: list[str] = []

    for i, row in enumerate(rows):
        gid = row.get("gene") or row.get("id") or f"row_{i}"
        seq = _seq_from_row(row)
        if not seq:
            failures.append(f"{gid}:no_seq")
            continue
        print(f"  [{i+1}/{len(rows)}] {gid} ({len(seq)} aa) ...", end=" ", flush=True)
        result = number_seq(runner, seq, gid)
        if result:
            cache[gid] = result
            print(f"OK ({len(result)} positions)")
        else:
            failures.append(gid)
            print("FAILED")

    return {
        "_meta": {
            "species": "Felis catus",
            "locus": "IGHV",
            "numbering_scheme": "Kabat via anarcii",
            "source": str(scaffold_path.relative_to(REPO)),
            "n_input": len(rows),
            "n_cached": len(cache),
            "n_failed": len(failures),
            "failed_genes": failures,
            "generated_at": datetime.now(timezone.utc).isoformat(),
        },
        "genes": cache,
    }


def build_from_aa_json(runner: Any, locus_json: Path, locus: str) -> dict[str, Any]:
    data = json.loads(locus_json.read_text())
    entries = data.get("entries", [])
    cache: dict[str, dict[str, str]] = {}
    failures: list[str] = []

    for i, ent in enumerate(entries):
        gid = ent.get("id", f"unknown_{i}")
        seq = ent.get("sequence_aa", "")
        if not seq:
            continue
        print(f"  [{i+1}/{len(entries)}] {gid} ({len(seq)} aa) ...", end=" ", flush=True)
        result = number_seq(runner, seq, gid)
        if result:
            cache[gid] = result
            print(f"OK ({len(result)} positions)")
        else:
            failures.append(gid)
            print("FAILED")

    return {
        "_meta": {
            "species": "Felis catus",
            "locus": locus,
            "numbering_scheme": "Kabat via anarcii",
            "source": str(locus_json.relative_to(REPO)),
            "n_input": len(entries),
            "n_cached": len(cache),
            "n_failed": len(failures),
            "failed_genes": failures,
            "generated_at": datetime.now(timezone.utc).isoformat(),
        },
        "genes": cache,
    }


def main():
    from anarcii import Anarcii
    runner = Anarcii()
    print("anarcii runner initialized.\n")

    # IGHV
    print("Building IGHV cache from scaffold ...")
    ighv_cache = build_ighv_from_scaffold(runner)
    out = OUT_DIR / "cat_ighv_kabat_numbered_cache.json"
    out.write_text(json.dumps(ighv_cache, indent=2, ensure_ascii=False))
    print(f"  -> {out.name}: {ighv_cache['_meta']['n_cached']} cached, {ighv_cache['_meta']['n_failed']} failed\n")

    # IGKV
    igkv_src = CAT_DIR / "IGKV_aa.json"
    if igkv_src.exists():
        print("Building IGKV cache ...")
        igkv_cache = build_from_aa_json(runner, igkv_src, "IGKV")
        out = OUT_DIR / "cat_igkv_kabat_numbered_cache.json"
        out.write_text(json.dumps(igkv_cache, indent=2, ensure_ascii=False))
        print(f"  -> {out.name}: {igkv_cache['_meta']['n_cached']} cached\n")

    # IGLV
    iglv_src = CAT_DIR / "IGLV_aa.json"
    if iglv_src.exists():
        print("Building IGLV cache ...")
        iglv_cache = build_from_aa_json(runner, iglv_src, "IGLV")
        out = OUT_DIR / "cat_iglv_kabat_numbered_cache.json"
        out.write_text(json.dumps(iglv_cache, indent=2, ensure_ascii=False))
        print(f"  -> {out.name}: {iglv_cache['_meta']['n_cached']} cached\n")

    print("Done.")


if __name__ == "__main__":
    main()
