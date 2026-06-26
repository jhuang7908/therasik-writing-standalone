#!/usr/bin/env python3
"""
Pipeline for 50 scFv-like bispecific antibodies:
  1. Load sequences (from CSV with antibody_id + heavy_sequence / full_sequence)
  2. Linker detection (G4S, EAAAK, etc.) and split into VH / VL (or scFv1 / scFv2)
  3. ANARCII numbering on each segment (anarcii package)
  4. Export FASTA for ESMFold

Input CSV columns: antibody_id, and one of:
  - full_sequence (single chain, e.g. VH-linker-VL)
  - heavy_sequence, light_sequence (two chains; will concatenate with default linker for ESMFold)

Usage:
  python scripts/scfv_like_50_linker_anarci_esmfold.py --seq-csv data/design_rules/scfv_like_50_sequences.csv --out-dir data/design_rules/scfv_like_50_pipeline
"""
import argparse
import csv
import json
import re
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

# Linker patterns (from functional_domains.json): G4S, EAAAK
LINKER_PATTERNS = [
    ("G4S", re.compile(r"(?:GGGGS)+", re.I)),   # (G4S)n
    ("EAAAK", re.compile(r"EAAAK(?:A)?", re.I)),
    ("G4S_short", re.compile(r"GGGGS", re.I)),  # single G4S
]
# Minimum VH/VL length (Kabat VH ~118, VL ~107)
MIN_VH_LEN = 90
MIN_VL_LEN = 85


def load_scfv_like_ids(id_json_path=None):
    """Load antibody ID set. Default: 50 scFv-like; or from id_json_path (e.g. multispecific_linker_from_export.json)."""
    if id_json_path:
        path = Path(id_json_path)
        if not path.is_absolute():
            path = PROJECT_ROOT / path
        with open(path, encoding="utf-8") as f:
            data = json.load(f)
        return set(data.get("antibody_ids", []))
    path = PROJECT_ROOT / "data" / "design_rules" / "bispecific_125_scfv_like.json"
    with open(path, encoding="utf-8") as f:
        data = json.load(f)
    return set(data.get("antibody_ids", []))


def _normalize_row_to_seqs(row):
    """From a dict row (CSV or Excel), return (aid, { full_sequence? | heavy_sequence?, light_sequence? })."""
    aid = (str(row.get("antibody_id") or row.get("Therapeutic") or "")).strip()
    if not aid:
        return None, None
    full = (str(row.get("full_sequence") or row.get("FullSequence") or "")).strip()
    heavy = (str(row.get("heavy_sequence") or row.get("HeavySequence") or "")).strip()
    light = (str(row.get("light_sequence") or row.get("LightSequence") or "")).strip()
    if full:
        return aid, {"full_sequence": full}
    if heavy and light:
        return aid, {"heavy_sequence": heavy, "light_sequence": light}
    if heavy:
        return aid, {"full_sequence": heavy}
    if light:
        return aid, {"full_sequence": light}
    return aid, None


def load_sequences_from_csv(csv_path: Path):
    """Returns dict: antibody_id -> { full_sequence? | heavy_sequence?, light_sequence? }"""
    rows = {}
    with open(csv_path, encoding="utf-8", newline="") as f:
        reader = csv.DictReader(f)
        for row in reader:
            aid, seqs = _normalize_row_to_seqs(row)
            if aid and seqs:
                rows[aid] = seqs
    return rows


def load_sequences_from_xlsx(xlsx_path: Path, id_set: set):
    """Read Excel; keep only rows whose Therapeutic/antibody_id is in id_set. Returns same dict as CSV loader."""
    try:
        import pandas as pd
    except ImportError:
        raise ImportError("Reading .xlsx requires pandas: pip install pandas openpyxl")
    df = pd.read_excel(xlsx_path, engine="openpyxl")
    cols = list(df.columns)
    # Resolve column by possible names (Thera-SAbDab: Therapeutic, HeavySequence, LightSequence; bispec: HeavySequence(ifbispec), LightSequence(ifbispec))
    def find_col(*candidates):
        for c in candidates:
            for col in cols:
                if col.strip().lower() == c.strip().lower():
                    return col
            if c in cols:
                return c
        return None
    aid_col = find_col("antibody_id", "Therapeutic", "Name") or cols[0]
    full_col = find_col("full_sequence", "FullSequence")
    heavy_col = find_col("HeavySequence", "heavy_sequence") or find_col("HeavySequence(ifbispec)")
    light_col = find_col("LightSequence", "light_sequence") or find_col("LightSequence(ifbispec)")
    def _val(col):
        if col is None or col not in row.index:
            return ""
        v = row[col]
        return str(v).strip() if pd.notna(v) and str(v).strip().lower() != "nan" else ""

    rows = {}
    for _, row in df.iterrows():
        aid = _val(aid_col)
        if aid not in id_set:
            continue
        full, heavy, light = _val(full_col), _val(heavy_col), _val(light_col)
        d = {}
        if full:
            d = {"full_sequence": full}
        elif heavy and light:
            d = {"heavy_sequence": heavy, "light_sequence": light}
        elif heavy:
            d = {"full_sequence": heavy}
        elif light:
            d = {"full_sequence": light}
        if d:
            rows[aid] = d
    return rows


def find_linker(seq: str):
    """Find first occurrence of a known linker; return (name, start, end) or None."""
    best = None
    for name, pat in LINKER_PATTERNS:
        m = pat.search(seq)
        if m and (best is None or m.start() < best[1]):
            best = (name, m.start(), m.end())
    return best


def split_single_chain(seq: str):
    """
    Split VH-linker-VL or scFv1-linker-scFv2 by linker.
    Returns (segment_before, linker_name, linker_seq, segment_after) or (None, None, None, None).
    """
    link = find_linker(seq)
    if not link:
        return None, None, None, None
    name, start, end = link
    before = seq[:start]
    linker_seq = seq[start:end]
    after = seq[end:]
    if len(before) >= MIN_VH_LEN and len(after) >= MIN_VL_LEN:
        return before, name, linker_seq, after
    return None, None, None, None


def run_anarcii_on_segments(segments: list, scheme: str = "imgt"):
    """Run ANARCII (anarcii package) on list of (id, sequence). Returns list of (id, numbering_result or None)."""
    try:
        from anarcii import Anarcii
    except ImportError:
        return [(sid, None) for sid, _ in segments]
    engine = Anarcii()
    ids = [s[0] for s in segments]
    seqs = [s[1] for s in segments]
    try:
        result = engine.number(list(zip(ids, seqs)), scheme=scheme)
    except Exception:
        return [(sid, None) for sid, _ in segments]
    out = []
    for sid, seq in segments:
        out.append((sid, result.get(sid) if result else None))
    return out


def main():
    parser = argparse.ArgumentParser(description="scFv-like 50: linker detection, ANARCII, ESMFold FASTA")
    parser.add_argument("--seq-csv", type=str, required=True, help="CSV or .xlsx with antibody_id/Therapeutic and full_sequence or heavy_sequence/light_sequence (e.g. data/thera_sabdab/thera_export.xlsx)")
    parser.add_argument("--out-dir", type=str, default="data/design_rules/scfv_like_50_pipeline")
    parser.add_argument("--id-json", type=str, default=None, help="Optional: JSON with antibody_ids (e.g. data/design_rules/multispecific_linker_from_export.json for all multispecific+linker)")
    parser.add_argument("--skip-anarcii", action="store_true", help="Skip ANARCII (only linker split + FASTA)")
    args = parser.parse_args()

    out_dir = Path(args.out_dir)
    out_dir.mkdir(parents=True, exist_ok=True)

    seq_path = Path(args.seq_csv)
    ids_50 = load_scfv_like_ids(args.id_json)
    if seq_path.suffix.lower() in (".xlsx", ".xls"):
        seqs = load_sequences_from_xlsx(seq_path, ids_50)
    else:
        seqs = load_sequences_from_csv(seq_path)

    results = []
    fasta_lines = []
    anarci_segments = []

    for aid in sorted(ids_50):
        row = seqs.get(aid)
        if not row:
            results.append({"antibody_id": aid, "status": "no_sequence", "error": "missing in CSV"})
            continue
        full = row.get("full_sequence")
        if not full and (row.get("heavy_sequence") or row.get("light_sequence")):
            # Concatenate with G4S3 for ESMFold
            h, l = row.get("heavy_sequence", ""), row.get("light_sequence", "")
            linker = "GGGGSGGGGSGGGGS"
            full = f"{h}{linker}{l}" if h and l else (h or l)
        if not full or len(full) < 100:
            results.append({"antibody_id": aid, "status": "skip", "error": "sequence too short or missing"})
            continue

        before, linker_name, linker_seq, after = split_single_chain(full)
        if before is not None:
            results.append({
                "antibody_id": aid,
                "status": "split_ok",
                "linker_name": linker_name,
                "linker_seq": linker_seq,
                "len_before": len(before),
                "len_after": len(after),
                "full_len": len(full),
            })
            fasta_lines.append(f">{aid}\n{full}\n")
            anarci_segments.append((f"{aid}_VH", before))
            anarci_segments.append((f"{aid}_VL", after))
        else:
            # Distinguish: no linker at all vs linker found but segment after too short (e.g. "na")
            link = find_linker(full)
            if link:
                name, start, end = link
                before_short = full[:start]
                after_short = full[end:]
                results.append({
                    "antibody_id": aid,
                    "status": "linker_found_short_tail",
                    "linker_name": name,
                    "linker_seq": full[start:end],
                    "len_before": len(before_short),
                    "len_after": len(after_short),
                    "full_len": len(full),
                    "note": "linker present but segment after linker too short (e.g. VH-only/placeholder)",
                })
            else:
                results.append({
                    "antibody_id": aid,
                    "status": "no_linker_found",
                    "full_len": len(full),
                    "note": "no known linker pattern or segments too short",
                })
            fasta_lines.append(f">{aid}\n{full}\n")

    # ANARCII
    anarcii_results = []
    if not args.skip_anarcii and anarci_segments:
        anarcii_out = run_anarcii_on_segments(anarci_segments)
        for (sid, num), (_, seq) in zip(anarcii_out, anarci_segments):
            anarcii_results.append({"segment_id": sid, "has_numbering": num is not None, "len": len(seq)})

    # Write outputs
    with open(out_dir / "linker_split_results.json", "w", encoding="utf-8") as f:
        json.dump({"results": results, "anarcii_summary": anarcii_results}, f, ensure_ascii=False, indent=2)

    with open(out_dir / "esmfold_input.fasta", "w") as f:
        f.writelines(fasta_lines)

    n_ok = sum(1 for r in results if r.get("status") == "split_ok")
    n_no_seq = sum(1 for r in results if r.get("status") == "no_sequence")
    n_short_tail = sum(1 for r in results if r.get("status") == "linker_found_short_tail")
    n_no_linker = sum(1 for r in results if r.get("status") == "no_linker_found")
    print(f"Done. Out dir: {out_dir}")
    print(f"  With sequence: {len(results) - n_no_seq}, split_ok: {n_ok}, linker_found_short_tail: {n_short_tail}, no_linker_found: {n_no_linker}, no_sequence: {n_no_seq}")
    print(f"  FASTA for ESMFold: {out_dir / 'esmfold_input.fasta'} ({len(fasta_lines)} sequences)")


if __name__ == "__main__":
    main()
