"""
Dog antibody framework analysis using IMGT boundaries + germline matching.

anarcii uses IMGT numbering. Confirmed boundaries:
  VH/VL FR1:  1-26   (gap at pos 10 for typical VH)
  VH/VL CDR1: 27-38
  VH/VL FR2:  39-55
  VH/VL CDR2: 56-65
  VH/VL FR3:  66-104
  VH/VL CDR3: 105-117
  VH/VL FR4:  118-128 (VH ends ~128, VK ends ~127, VL ends ~127)
"""
import json
import os
import sys
import pandas as pd
from anarcii import Anarcii

BASE = r"D:\InSynBio-AI-Research\Antibody_Engineer_Suite"
DB_PATH = os.path.join(BASE, "data", "thera_sabdab", "thera_export.xlsx")
GERMLINE_DIR = os.path.join(BASE, "data", "germlines", "canis_lupus_familiaris_ig_aa")

# ---------------------------------------------------------------------------
# Load germline sequences
# ---------------------------------------------------------------------------

def load_fasta(path):
    """Return dict {allele_name: sequence} from a FASTA file."""
    seqs = {}
    name = None
    buf = []
    if not os.path.exists(path):
        return seqs
    with open(path) as fh:
        for line in fh:
            line = line.strip()
            if line.startswith(">"):
                if name:
                    seqs[name] = "".join(buf)
                # parse allele name from second pipe-delimited field
                parts = line[1:].split("|")
                name = parts[1] if len(parts) > 1 else line[1:]
                buf = []
            else:
                buf.append(line)
    if name:
        seqs[name] = "".join(buf)
    return seqs


def load_germlines():
    files = {
        "IGHV": "IGHV_aa.fasta",
        "IGHJ": "IGHJ_aa.fasta",
        "IGKV": "IGKV_aa.fasta",
        "IGKJ": "IGKJ_aa.fasta",
        "IGLV": "IGLV_aa.fasta",
        "IGLJ": "IGLJ_aa.fasta",
    }
    return {k: load_fasta(os.path.join(GERMLINE_DIR, v)) for k, v in files.items()}


def seq_identity(s1, s2):
    """Pairwise identity over aligned overlap (simple, no gaps)."""
    if not s1 or not s2:
        return 0.0
    shorter, longer = (s1, s2) if len(s1) <= len(s2) else (s2, s1)
    matches = sum(a == b for a, b in zip(shorter, longer))
    return matches / len(longer) * 100


def best_match(query, germlines):
    """Return (allele, identity%) for the best SW-style suffix/full match."""
    best_name, best_id = None, 0.0
    for name, ref in germlines.items():
        # Try to find query as a suffix of ref (J-genes: query = end of J)
        # or ref as a suffix of query (V-genes: FR region vs V germline)
        # Use simple overlapping window approach
        best_local = 0.0
        min_overlap = min(len(query), len(ref), 8)
        for start in range(max(0, len(ref) - len(query) - 5),
                           min(len(ref), len(ref) - min_overlap + 1) + 1):
            seg = ref[start: start + len(query)]
            if not seg:
                continue
            id_val = seq_identity(query, seg)
            if id_val > best_local:
                best_local = id_val
        # Also try full alignment (V-genes where query <= ref length)
        id_full = seq_identity(query, ref[:len(query)])
        best_local = max(best_local, id_full)
        if best_local > best_id:
            best_id = best_local
            best_name = name
    return best_name, best_id


# ---------------------------------------------------------------------------
# Numbering & FR extraction
# ---------------------------------------------------------------------------

_engine = Anarcii()

# IMGT boundaries (confirmed with anarcii output):
IMGT_FR = {
    "FR1":  (1,   26),
    "FR2":  (39,  55),
    "FR3":  (66,  104),
    "FR4":  (118, 130),   # 130 catches both VH (128) and VK/VL (127)
    "CDR1": (27,  38),
    "CDR2": (56,  65),
    "CDR3": (105, 117),
}


def extract_regions(seq):
    """Return dict with FR1-FR4 and CDR1-CDR3 strings, plus chain_type."""
    if not isinstance(seq, str) or len(seq) < 50:
        return None
    try:
        res = _engine.number([("seq", seq)])
        if not res or "seq" not in res:
            return None
        info = res["seq"]
        if info.get("error"):
            return None
        numbering = info.get("numbering", [])
        if not numbering:
            return None

        regions = {}
        for label, (lo, hi) in IMGT_FR.items():
            regions[label] = "".join(
                aa for (pos, _), aa in numbering
                if lo <= pos <= hi and aa != "-"
            )
        regions["chain_type"] = info.get("chain_type", "?")
        return regions
    except Exception as e:
        print(f"    Numbering error: {e}")
        return None


# ---------------------------------------------------------------------------
# Main analysis
# ---------------------------------------------------------------------------

print("Loading germlines...")
germlines = load_germlines()
for k, v in germlines.items():
    print(f"  {k}: {len(v)} alleles")

print("\nLoading antibody database...")
df = pd.read_excel(DB_PATH)
targets = ["Lokivetmab", "Bedinvetmab", "Gilvetmab"]
results = df[df["Therapeutic"].isin(targets)].copy()
print(f"Found {len(results)} rows.")

print("\n" + "=" * 70)
print("FRAMEWORK ANALYSIS  (IMGT numbering)")
print("=" * 70)

antibody_data = {}

for _, row in results.iterrows():
    name = row["Therapeutic"]
    vh_seq = row.get("HeavySequence")
    vl_seq = row.get("LightSequence")

    print(f"\n[{name}]")

    # --- VH ---
    vh = extract_regions(vh_seq)
    if vh:
        # germline matching: FR1-FR3 vs IGHV, FR4 vs IGHJ
        vhv_name, vhv_id = best_match(vh["FR1"] + vh["FR2"] + vh["FR3"],
                                      germlines["IGHV"])
        vhj_name, vhj_id = best_match(vh["FR4"], germlines["IGHJ"])

        print(f"  VH chain type : {vh['chain_type']}")
        print(f"  VH germline V : {vhv_name}  ({vhv_id:.1f}% FR1-3 identity)")
        print(f"  VH germline J : {vhj_name}  ({vhj_id:.1f}% FR4 identity)")
        for reg in ("FR1", "CDR1", "FR2", "CDR2", "FR3", "CDR3", "FR4"):
            s = vh[reg]
            print(f"    {reg:5s} ({len(s):2d} aa): {s}")
        antibody_data.setdefault(name, {})["VH"] = vh
    else:
        print("  VH: failed")

    # --- VL ---
    vl = extract_regions(vl_seq)
    if vl:
        ct = vl["chain_type"]
        v_db = "IGKV" if ct == "K" else "IGLV"
        j_db = "IGKJ" if ct == "K" else "IGLJ"
        vlv_name, vlv_id = best_match(vl["FR1"] + vl["FR2"] + vl["FR3"],
                                      germlines[v_db])
        vlj_name, vlj_id = best_match(vl["FR4"], germlines[j_db])

        print(f"  VL chain type : {vl['chain_type']}")
        print(f"  VL germline V : {vlv_name}  ({vlv_id:.1f}% FR1-3 identity)")
        print(f"  VL germline J : {vlj_name}  ({vlj_id:.1f}% FR4 identity)")
        for reg in ("FR1", "CDR1", "FR2", "CDR2", "FR3", "CDR3", "FR4"):
            s = vl[reg]
            print(f"    {reg:5s} ({len(s):2d} aa): {s}")
        antibody_data.setdefault(name, {})["VL"] = vl
    else:
        print("  VL: failed")

# ---------------------------------------------------------------------------
# Cross-antibody FR comparison
# ---------------------------------------------------------------------------
print("\n\n" + "=" * 70)
print("FRAMEWORK IDENTITY COMPARISON")
print("=" * 70)

names = [n for n in targets if n in antibody_data]
for i in range(len(names)):
    for j in range(i + 1, len(names)):
        n1, n2 = names[i], names[j]
        print(f"\n{n1}  vs  {n2}:")
        for chain in ("VH", "VL"):
            d1 = antibody_data.get(n1, {}).get(chain)
            d2 = antibody_data.get(n2, {}).get(chain)
            if not d1 or not d2:
                print(f"  {chain}: data missing")
                continue
            results_line = []
            for fr in ("FR1", "FR2", "FR3", "FR4"):
                tag = ("identical" if d1[fr] == d2[fr]
                       else f"{seq_identity(d1[fr], d2[fr]):.0f}%")
                results_line.append(f"{fr}:{tag}")
            all1 = d1["FR1"] + d1["FR2"] + d1["FR3"] + d1["FR4"]
            all2 = d2["FR1"] + d2["FR2"] + d2["FR3"] + d2["FR4"]
            print(f"  {chain}: {', '.join(results_line)}"
                  f"  → Overall: {seq_identity(all1, all2):.1f}%")

# ---------------------------------------------------------------------------
# Length summary
# ---------------------------------------------------------------------------
print("\n\n" + "=" * 70)
print("FRAMEWORK LENGTH SUMMARY")
print("=" * 70)
print(f"{'Antibody':<14} {'Chain':<6} {'FR1':>4} {'FR2':>4} {'FR3':>4} {'FR4':>4} "
      f"{'CDR1':>5} {'CDR2':>5} {'CDR3':>5} {'FRtot':>6}")
print("-" * 60)
for name in names:
    for chain in ("VH", "VL"):
        d = antibody_data.get(name, {}).get(chain)
        if d:
            fr_tot = sum(len(d[f]) for f in ("FR1","FR2","FR3","FR4"))
            print(f"{name:<14} {chain:<6} "
                  f"{len(d['FR1']):>4} {len(d['FR2']):>4} "
                  f"{len(d['FR3']):>4} {len(d['FR4']):>4} "
                  f"{len(d['CDR1']):>5} {len(d['CDR2']):>5} "
                  f"{len(d['CDR3']):>5} {fr_tot:>6}")
