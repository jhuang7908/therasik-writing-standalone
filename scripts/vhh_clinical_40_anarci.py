#!/usr/bin/env python3
"""
Run ANARCII numbering on 40 clinical VHH sequences (anarcii package; NOT the older ANARCI program).

Input: FASTA (e.g. from vhh_clinical_data/vhh_sequences_v2.fasta).
Output: out-dir/anarci_results.json (per-sequence numbering summary + raw numbering if available).

Usage:
  python scripts/vhh_clinical_40_anarci.py --from-json --out-dir data/vhh_clinical_40_anarci   # 40 VHH from complete_v2.json
  python scripts/vhh_clinical_40_anarci.py --fasta <path-to-fasta> --out-dir data/vhh_clinical_40_anarci
  python scripts/vhh_clinical_40_anarci.py --out-dir data/vhh_clinical_40_anarci
    (uses FASTA path from data/design_rules/vhh_clinical_40_reference.json)
"""
import argparse
import json
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent
REFERENCE_JSON = PROJECT_ROOT / "data" / "design_rules" / "vhh_clinical_40_reference.json"


def load_40_from_json(json_path: Path):
    """Load 40 VHH from vhh_clinical_antibodies_complete_v2.json. One sequence per therapeutic: heavy or heavy_bispec."""
    with open(json_path, encoding="utf-8") as f:
        data = json.load(f)
    segments = []
    for rec in data:
        name = rec.get("therapeutic_name", "").strip()
        if not name:
            continue
        seqs = rec.get("sequences") or {}
        seq = (seqs.get("heavy") or {}).get("sequence") or (seqs.get("heavy_bispec") or {}).get("sequence")
        if seq and isinstance(seq, str):
            seq = seq.replace(" ", "").strip()
        if seq and len(seq) >= 90:
            segments.append((name, seq))
    return segments


def load_fasta(path: Path):
    """Parse FASTA; return list of (id, sequence). Skip comment lines."""
    records = []
    with open(path, encoding="utf-8") as f:
        current_id, current_seq = None, []
        for line in f:
            line = line.rstrip()
            if not line or line.startswith("#"):
                continue
            if line.startswith(">"):
                if current_id is not None:
                    records.append((current_id, "".join(current_seq)))
                current_id = line[1:].split()[0].strip()
                current_seq = []
            else:
                current_seq.append(line.replace(" ", ""))
        if current_id is not None:
            records.append((current_id, "".join(current_seq)))
    return records


def run_anarci(segments: list, scheme: str = "imgt"):
    """Run ANARCII (anarcii package) on list of (id, sequence). Returns list of (id, numbering_list or None)."""
    try:
        from anarcii import Anarcii
    except ImportError:
        return [(sid, None) for sid, _ in segments]
    engine = Anarcii()
    try:
        result = engine.number([(sid, seq) for sid, seq in segments])
        result = engine.to_scheme(scheme)
    except Exception:
        return [(sid, None) for sid, _ in segments]
    out = []
    for sid, seq in segments:
        entry = (result or {}).get(sid, {}) if isinstance(result, dict) else {}
        numbering = entry.get("numbering") if isinstance(entry, dict) else None
        out.append((sid, numbering))
    return out


def main():
    parser = argparse.ArgumentParser(description="ANARCII numbering for 40 clinical VHH (anarcii package)")
    parser.add_argument("--from-json", action="store_true", help="Load 40 VHH from vhh_clinical_antibodies_complete_v2.json (path from vhh_clinical_40_reference.json)")
    parser.add_argument("--fasta", type=str, default=None, help="Input FASTA (default when not --from-json: from reference)")
    parser.add_argument("--out-dir", type=str, default="data/vhh_clinical_40_anarci")
    parser.add_argument("--scheme", type=str, default="kabat", choices=["imgt", "kabat", "chothia"])
    args = parser.parse_args()

    out_dir = Path(args.out_dir)
    out_dir.mkdir(parents=True, exist_ok=True)

    if args.from_json:
        if not REFERENCE_JSON.exists():
            raise FileNotFoundError(f"Reference not found: {REFERENCE_JSON}")
        with open(REFERENCE_JSON, encoding="utf-8") as f:
            ref = json.load(f)
        base = Path(ref["meta"]["source_path"])
        json_path = base / ref["files"]["json_complete"]
        if not json_path.exists():
            raise FileNotFoundError(f"JSON not found: {json_path}")
        segments = load_40_from_json(json_path)
        print(f"Loaded {len(segments)} VHH sequences from {json_path.name}")
    else:
        fasta_path = None
        if args.fasta:
            fasta_path = Path(args.fasta)
        else:
            if REFERENCE_JSON.exists():
                with open(REFERENCE_JSON, encoding="utf-8") as f:
                    ref = json.load(f)
                base = Path(ref["meta"]["source_path"])
                fasta_path = base / ref["files"]["fasta"]
        if not fasta_path or not fasta_path.exists():
            raise FileNotFoundError(
                f"FASTA not found. Use --fasta or --from-json, or ensure {REFERENCE_JSON} has valid source_path."
            )
        segments = load_fasta(fasta_path)
        print(f"Loaded {len(segments)} VHH sequences from {fasta_path.name}")

    anarci_out = run_anarci(segments, scheme=args.scheme)

    results = []
    for (sid, seq), (_, numbering) in zip(segments, anarci_out):
        has_num = numbering is not None
        # Make numbering JSON-serializable (list of ((pos, ins), aa) or similar)
        num_serial = None
        if numbering is not None:
            if isinstance(numbering, list):
                try:
                    num_serial = [[list(item[0]), item[1]] for item in numbering[:3]] + [f"... {len(numbering)} total"]
                except Exception:
                    num_serial = str(numbering)[:500]
            elif isinstance(numbering, dict):
                try:
                    num_serial = {str(k): v for k, v in list(numbering.items())[:20]}
                except Exception:
                    num_serial = str(type(numbering))
        results.append({
            "id": sid,
            "len": len(seq),
            "has_numbering": has_num,
            "numbering": num_serial,
        })

    out_path = out_dir / "anarci_results.json"
    with open(out_path, "w", encoding="utf-8") as f:
        json.dump({"scheme": args.scheme, "count": len(results), "results": results}, f, ensure_ascii=False, indent=2)
    print(f"Wrote {out_path}")

    n_ok = sum(1 for r in results if r["has_numbering"])
    print(f"ANARCII: {n_ok}/{len(results)} with numbering (scheme={args.scheme})")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
