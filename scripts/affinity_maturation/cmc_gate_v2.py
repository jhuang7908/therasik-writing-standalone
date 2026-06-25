"""CMC gate on AbLang L2b-passing candidates (96 total)."""
import csv
from pathlib import Path
from Bio.SeqUtils.ProtParam import ProteinAnalysis

WT_SEQ = "QVQLVQSGAEVVKPGSSVKLSCKASGFNIKDTYIHWVKQRPEQGREWIGRIYPTNGYTRYDPKFQDRATITADTSTSTAYLEVSRLRSEDTAVYYCSRWGGDGFYAMDYWGQGASVTVSS"
OUTPUT_DIR = Path("projects/mumab4d5_VGRW_SR_R2/affinity_maturation_v2")
PI_SHIFT_MAX = 0.5

skip = {10, 31, 32, 33, 34, 60, 61, 73}
pdb_resi = [i for i in range(1, 129) if i not in skip]
KABAT_MAP = {kabat: idx for idx, kabat in enumerate(pdb_resi)}

CDR_RANGES = [(27, 38), (55, 65), (99, 120)]  # CDR Kabat ranges (approx)

def in_cdr(kabat_site):
    return any(lo <= kabat_site <= hi for lo, hi in CDR_RANGES)

def apply_mut(seq, site, mut_aa):
    return seq[:KABAT_MAP[site]] + mut_aa + seq[KABAT_MAP[site]+1:]

def find_deamid(seq):
    return [f"N{seq[i+1]}@{i+1}" for i in range(len(seq)-1) if seq[i] == "N" and seq[i+1] in "GSTH"]

def find_isom(seq):
    return [f"D{seq[i+1]}@{i+1}" for i in range(len(seq)-1) if seq[i] == "D" and seq[i+1] in "GSP"]

def find_oxid(seq):
    return [f"{aa}@{i+1}" for i, aa in enumerate(seq) if aa in "MW"]

def cmc_metrics(seq):
    pa = ProteinAnalysis(seq)
    return {
        "pI":         round(pa.isoelectric_point(), 2),
        "GRAVY":      round(pa.gravy(), 3),
        "instab":     round(pa.instability_index(), 1),
        "charge_pH7": round(pa.charge_at_pH(7.0), 1),
        "deamid":     find_deamid(seq),
        "isom":       find_isom(seq),
        "oxid":       find_oxid(seq),
    }


def main():
    wt = cmc_metrics(WT_SEQ)
    print("=" * 70)
    print("CMC Gate — 96 ")
    print(f"WT: pI={wt['pI']}  GRAVY={wt['GRAVY']}  charge={wt['charge_pH7']}")
    print(f"    deamid={wt['deamid']}  isom={wt['isom']}  oxid={len(wt['oxid'])} sites")
    print("=" * 70)

    candidates = []
    with open(OUTPUT_DIR / "ablang_l2b_results.csv") as f:
        for row in csv.DictReader(f):
            candidates.append({
                "mutation":     row["mutation"],
                "site":         int(row["site"]),
                "wt_aa":        row["wt_aa"],
                "mut_aa":       row["mut_aa"],
                "evoef2_ddg":   float(row["evoef2_ddg"]),
                "ddg_fold":     row["ddg_fold"],
                "ablang_delta": row["ablang_delta"],
            })

    results = []
    for c in candidates:
        mut_seq    = apply_mut(WT_SEQ, c["site"], c["mut_aa"])
        m          = cmc_metrics(mut_seq)
        pi_shift   = abs(m["pI"] - wt["pI"])
        new_deamid = len(m["deamid"]) - len(wt["deamid"])
        new_isom   = len(m["isom"])   - len(wt["isom"])
        new_oxid   = len(m["oxid"])   - len(wt["oxid"])
        is_cdr     = in_cdr(c["site"])

        warns = []
        hard_fail = False

        if pi_shift > PI_SHIFT_MAX:
            hard_fail = True
            warns.append(f"ΔpI={pi_shift:.2f}")
        if new_deamid > 0 and is_cdr:
            hard_fail = True
            warns.append(f"+deamid_CDR({new_deamid})")
        elif new_deamid > 0:
            warns.append(f"+deamid_FR({new_deamid})")
        if new_isom > 0:
            warns.append(f"+isom({new_isom})")
        if new_oxid > 0:
            warns.append(f"+oxid({new_oxid})")

        results.append({
            **c,
            "pI":         m["pI"],
            "pi_shift":   round(pi_shift, 2),
            "charge":     m["charge_pH7"],
            "GRAVY":      m["GRAVY"],
            "in_cdr":     is_cdr,
            "new_deamid": new_deamid,
            "new_isom":   new_isom,
            "new_oxid":   new_oxid,
            "cmc_warn":   "; ".join(warns),
            "cmc_status": "FAIL" if hard_fail else ("WARN" if warns else "PASS"),
        })

    # 
    out = OUTPUT_DIR / "cmc_gate_results.csv"
    fields = ["mutation","site","wt_aa","mut_aa","evoef2_ddg","ddg_fold","ablang_delta",
              "pI","pi_shift","charge","GRAVY","in_cdr",
              "new_deamid","new_isom","new_oxid","cmc_warn","cmc_status"]
    with open(out, "w", newline="") as f:
        w = csv.DictWriter(f, fieldnames=fields)
        w.writeheader()
        w.writerows(results)

    # 
    n_pass = sum(1 for r in results if r["cmc_status"] == "PASS")
    n_warn = sum(1 for r in results if r["cmc_status"] == "WARN")
    n_fail = sum(1 for r in results if r["cmc_status"] == "FAIL")

    print(f"\nCMC : PASS={n_pass}  WARN={n_warn}  FAIL={n_fail}  ( {len(results)})")

    if n_fail:
        print("\n─── FAIL（）───")
        for r in results:
            if r["cmc_status"] == "FAIL":
                print(f"  {r['mutation']:<12s}  pI={r['pI']}  {r['cmc_warn']}")

    if n_warn:
        print("\n─── WARN（，）───")
        for r in results:
            if r["cmc_status"] == "WARN":
                print(f"  {r['mutation']:<12s}  pI={r['pI']}  charge={r['charge']}  {r['cmc_warn']}")

    # 
    print("\n─── PASS （，EvoEF2）───")
    by_site = {}
    for r in results:
        if r["cmc_status"] in ("PASS","WARN"):
            by_site.setdefault(r["site"], []).append(r)

    for site in sorted(by_site):
        group = sorted(by_site[site], key=lambda x: x["evoef2_ddg"])
        wt_aa = group[0]["wt_aa"]
        cdr_tag = " [CDR]" if group[0]["in_cdr"] else " [FR]"
        print(f"\n  Kabat {site} ({wt_aa}){cdr_tag}")
        print(f"  {'Mut':<6}  {'EvoEF2':>8}  {'ddG_fold':>9}  {'pI':>5}  {'ΔpI':>5}  {'charge':>7}  {'warn'}")
        print(f"  {'-'*65}")
        for r in group:
            warn = r["cmc_warn"] if r["cmc_warn"] else "-"
            status_tag = "⚠" if r["cmc_status"] == "WARN" else " "
            print(f"  {r['mut_aa']:<6}  {r['evoef2_ddg']:>+8.3f}  "
                  f"{str(r['ddg_fold']):>9}  {r['pI']:>5}  "
                  f"{r['pi_shift']:>5.2f}  {r['charge']:>7.1f}  {status_tag}{warn}")

    print(f"\n: {out}")
    return results


if __name__ == "__main__":
    main()
