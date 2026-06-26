#!/usr/bin/env python3
"""
Validate 39 VHH sequences and merge curated clinical supplement.
- Sequence: valid amino acids only, length in [90, 150].
- Optional: ABARCII numbering check (VH domain).
- Merge clinical_supplement_curated.json into rows where Target/Phase empty.
Output: validated CSV/JSON + validation report.
"""
import csv
import json
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent
UNION_DIR = PROJECT_ROOT / "data" / "vhh_clinical_39_union"
INPUT_JSON = UNION_DIR / "vhh_39_sequences_clinical.json"
SUPPLEMENT_JSON = UNION_DIR / "clinical_supplement_curated.json"
OZEKIBART_SEQ_JSON = UNION_DIR / "ozekibart_sequence.json"
ABARCII_RESULTS = PROJECT_ROOT / "data" / "vhh_clinical_40_anarci" / "anarci_results.json"

VALID_AA = set("ACDEFGHIKLMNPQRSTVWY")
MIN_LEN, MAX_LEN = 90, 150


def validate_sequence(seq: str):
    """Return (ok, message)."""
    if not seq or not seq.strip():
        return False, "empty"
    s = seq.strip().upper()
    bad = set(c for c in s if c not in VALID_AA)
    if bad:
        return False, f"invalid_aa:{','.join(sorted(bad))}"
    if len(s) < MIN_LEN:
        return False, f"too_short:{len(s)}"
    if len(s) > MAX_LEN:
        return False, f"too_long:{len(s)}"
    return True, "ok"


def load_anarci_ids():
    """Set of IDs that have ABARCII numbering (VH)."""
    if not ABARCII_RESULTS.exists():
        return set()
    with open(ABARCII_RESULTS, encoding="utf-8") as f:
        data = json.load(f)
    return {r["id"] for r in data["results"] if r.get("has_numbering")}


def load_supplement():
    if not SUPPLEMENT_JSON.exists():
        return {}
    with open(SUPPLEMENT_JSON, encoding="utf-8") as f:
        data = json.load(f)
    return data.get("entries", {})


def main():
    with open(INPUT_JSON, encoding="utf-8") as f:
        data = json.load(f)
    rows = list(data["vhh"])
    supplement = load_supplement()
    anarci_ok = load_anarci_ids()

    # Ozekibart: fill sequence from Thera-SAbDab supplement if missing
    if OZEKIBART_SEQ_JSON.exists():
        with open(OZEKIBART_SEQ_JSON, encoding="utf-8") as f:
            ozek = json.load(f)
        for r in rows:
            if (r.get("Name") == "Ozekibart") and not (r.get("Sequence") or "").strip():
                r["Sequence"] = (ozek.get("Sequence") or "").strip()
                break

    # Merge supplement (only fill if current Target/Phase empty)
    for r in rows:
        name = r.get("Name", "")
        if name in supplement:
            s = supplement[name]
            if not (r.get("Target") or "").strip():
                r["Target"] = s.get("Target", "").strip() or r.get("Target", "")
            if not (r.get("Clinical_Phase") or "").strip():
                r["Clinical_Phase"] = s.get("Clinical_Phase", "").strip() or r.get("Clinical_Phase", "")

    # Validate sequences
    report = {"valid": [], "invalid": [], "no_sequence": [], "anarci_ok": [], "anarci_missing": []}
    for r in rows:
        name = r.get("Name", "")
        seq = (r.get("Sequence") or "").strip()
        if not seq:
            report["no_sequence"].append(name)
            continue
        ok, msg = validate_sequence(seq)
        if ok:
            report["valid"].append({"name": name, "len": len(seq)})
            if name in anarci_ok:
                report["anarci_ok"].append(name)
            else:
                report["anarci_missing"].append(name)
        else:
            report["invalid"].append({"name": name, "reason": msg})

    # Write updated JSON/CSV
    out_json = UNION_DIR / "vhh_39_sequences_clinical_validated.json"
    with open(out_json, "w", encoding="utf-8") as f:
        json.dump({"count": len(rows), "vhh": rows, "_validation": report}, f, ensure_ascii=False, indent=2)
    print(f"Wrote {out_json}")

    fieldnames = ["Name", "Sequence", "Target", "Clinical_Phase", "CDR3_Length_aa", "CDR2_Fold", "Classification", "Human_Identity_pct", "In_Paper_Table1"]
    out_csv = UNION_DIR / "vhh_39_sequences_clinical_validated.csv"
    with open(out_csv, "w", encoding="utf-8", newline="") as f:
        w = csv.DictWriter(f, fieldnames=fieldnames)
        w.writeheader()
        w.writerows(rows)
    print(f"Wrote {out_csv}")

    # Validation report
    report_path = UNION_DIR / "validation_report.txt"
    with open(report_path, "w", encoding="utf-8") as f:
        f.write("39 VHH sequence validation report\n")
        f.write("================================\n")
        f.write(f"Valid sequences (AA set OK, length {MIN_LEN}-{MAX_LEN}): {len(report['valid'])}\n")
        f.write(f"Invalid: {len(report['invalid'])}\n")
        f.write(f"No sequence: {len(report['no_sequence'])}\n")
        f.write(f"ABARCII numbering OK (VH): {len(report['anarci_ok'])}\n")
        f.write(f"ABARCII missing (not in 38): {len(report['anarci_missing'])}\n")
        if report["invalid"]:
            f.write("\nInvalid:\n")
            for x in report["invalid"]:
                f.write(f"  {x['name']}: {x['reason']}\n")
        if report["no_sequence"]:
            f.write("\nNo sequence:\n")
            for n in report["no_sequence"]:
                f.write(f"  {n}\n")
        if report["anarci_missing"]:
            f.write("\nNot in ABARCII 38 (expected for Ozekibart + any ID mismatch):\n")
            for n in report["anarci_missing"]:
                f.write(f"  {n}\n")
    print(f"Wrote {report_path}")

    n_target = sum(1 for r in rows if (r.get("Target") or "").strip())
    print(f"Validation: {len(report['valid'])} valid, {len(report['invalid'])} invalid, {len(report['no_sequence'])} no seq; {len(report['anarci_ok'])} ABARCII OK. With Target: {n_target}/39.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
