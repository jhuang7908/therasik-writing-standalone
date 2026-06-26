#!/usr/bin/env python3
"""
Batch ESMFold structure prediction from a FASTA file.

Each record: header = ID, sequence = single chain (e.g. VH-linker-VL).
Calls ESMFold API (default) or local fair-esm, saves one PDB per record.

Usage:
  python scripts/run_esmfold_batch_from_fasta.py --fasta data/design_rules/multispecific_linker_pipeline/esmfold_input_two_sided_84.fasta --out-dir data/design_rules/multispecific_linker_pipeline/esmfold_predictions
  python scripts/run_esmfold_batch_from_fasta.py --fasta path/to.fasta --out-dir out --method local

Similar scripts in repo:
  - projects/pembrolizumab/design_rounds/round1_H2_H3edge/.../run_esmfold.py (API, VH:VL FASTA)
  - projects/pembrolizumab/design_rounds/round1_H2_H3edge/run_esmfold_gate1.py (local, quality metrics)
  - docs/ESMFOLD_SCRIPTS_INDEX.md
"""
import argparse
import re
import time
from pathlib import Path

try:
    import requests
except ImportError:
    requests = None

ESMFOLD_API_URL = "https://api.esmatlas.com/foldSequence/v1/pdb/"
MAX_RETRIES = 3
SLEEP_SEC = 1.5


def _sanitize_id(seq_id: str) -> str:
    """Safe filename from sequence ID."""
    return re.sub(r'[\\/*?:"<>|]', "_", str(seq_id).strip())[:80]


def predict_api(sequence: str, output_pdb: Path) -> bool:
    if requests is None:
        raise ImportError("requests required for API: pip install requests")
    for attempt in range(MAX_RETRIES):
        try:
            r = requests.post(ESMFOLD_API_URL, data=sequence, timeout=90)
            if r.status_code == 200 and (r.text.strip().startswith("ATOM") or r.text.strip().startswith("HEADER")):
                output_pdb.write_text(r.text, encoding="utf-8")
                return True
            if r.status_code == 429:
                time.sleep(10)
                continue
        except Exception as e:
            print(f"    Attempt {attempt+1} error: {e}")
        time.sleep(SLEEP_SEC)
    return False


def predict_local(sequence: str, output_pdb: Path) -> bool:
    try:
        import esm
        import torch
    except ImportError:
        raise ImportError("Local ESMFold requires: pip install fair-esm torch")
    model = esm.pretrained.esmfold_v1()
    model = model.eval()
    if torch.cuda.is_available():
        model = model.cuda()
    with torch.no_grad():
        pdb_str = model.infer_pdb(sequence)
    output_pdb.write_text(pdb_str, encoding="utf-8")
    return True


def main():
    parser = argparse.ArgumentParser(description="Batch ESMFold from FASTA")
    parser.add_argument("--fasta", type=str, required=True, help="Input FASTA (one sequence per record)")
    parser.add_argument("--out-dir", type=str, required=True, help="Output directory for PDB files")
    parser.add_argument("--method", choices=["api", "local"], default="api", help="api (default) or local")
    parser.add_argument("--skip-existing", action="store_true", default=True, help="Skip if PDB already exists (default: True)")
    parser.add_argument("--limit", type=int, default=None, help="Max number of sequences to run (for testing)")
    args = parser.parse_args()

    fasta_path = Path(args.fasta)
    if not fasta_path.is_file():
        raise FileNotFoundError(f"FASTA not found: {fasta_path}")

    out_dir = Path(args.out_dir)
    out_dir.mkdir(parents=True, exist_ok=True)

    # Parse FASTA
    records = []
    with open(fasta_path, encoding="utf-8") as f:
        current_id, current_seq = None, []
        for line in f:
            line = line.rstrip()
            if line.startswith(">"):
                if current_id is not None:
                    records.append((current_id, "".join(current_seq)))
                current_id = line[1:].split()[0].strip()
                current_seq = []
            else:
                current_seq.append(line)
        if current_id is not None:
            records.append((current_id, "".join(current_seq)))

    if args.limit is not None:
        records = records[: args.limit]
        print(f"Limited to first {len(records)} sequences")
    print(f"Loaded {len(records)} sequences from {fasta_path.name}")
    print(f"Method: {args.method}, Out: {out_dir}")

    ok, fail = 0, 0
    for i, (seq_id, seq) in enumerate(records, start=1):
        seq = seq.replace(" ", "").replace("\n", "")
        if not seq or len(seq) < 50:
            print(f"[{i}/{len(records)}] Skip {seq_id}: sequence too short")
            fail += 1
            continue
        safe_id = _sanitize_id(seq_id)
        out_pdb = out_dir / f"{safe_id}.pdb"
        if args.skip_existing and out_pdb.exists():
            print(f"[{i}/{len(records)}] Skip {seq_id} (exists)")
            ok += 1
            continue
        print(f"[{i}/{len(records)}] Predicting {seq_id} (len={len(seq)})...")
        try:
            if args.method == "api":
                success = predict_api(seq, out_pdb)
            else:
                success = predict_local(seq, out_pdb)
            if success:
                print(f"  Saved {out_pdb.name}")
                ok += 1
            else:
                print(f"  Failed")
                fail += 1
        except Exception as e:
            print(f"  Error: {e}")
            fail += 1
        if args.method == "api":
            time.sleep(SLEEP_SEC)

    print(f"\nDone. OK: {ok}, Failed: {fail}")


if __name__ == "__main__":
    main()
