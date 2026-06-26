"""
PAG1 Multi-Mutation Scan
========================
Comprehensive affinity scanning across CDR hotspot positions of the 7m antibody
complexed with human PAG1.

CDR positions (sequential PDB numbering, chain A = VH, chain B = VL):
  VH CDR1 (Chothia 26-32): seq 26-35  GYTFTSYVMH
  VH CDR2 (Chothia 52-56): seq 50-57  YIYPYNDK
  VH CDR3 (Chothia 95-102): seq 97-107 ARYKYGQGFAY

Scan strategy:
  - 30 single-point mutations across 12 CDR positions
  - Fast tools (EvoEF2, PRODIGY, ThermoMPNN, AntiFold, ESM-IF1): all 30 variants
  - MM/GBSA: 10-variant subset (representative range)
  - Output: CSV + JSON for downstream correlation analysis
"""

import sys, os, time, json, csv, tempfile
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))
from core.structure.affinity_energy_toolkit import AffinityEnergyToolkit

# ── Configuration ────────────────────────────────────────────────────────────

PDB = (
    r"D:\InSynBio-AI-Research\Antibody_Engineer_Suite\projects\PAG-1 project"
    r"\7m_humanPAG1\7m_humanPAG1_df5fc"
    r"\7m_humanPAG1_df5fc_relaxed_rank_001_alphafold2_multimer_v3_model_5_seed_000.pdb"
)
AB_CHAINS  = ["A", "B"]   # VH, VL
AG_CHAINS  = ["C"]         # PAG1

OUT_DIR = Path(r"D:\InSynBio-AI-Research\Antibody_Engineer_Suite\projects\PAG-1 project\mutation_scan_results")
OUT_DIR.mkdir(parents=True, exist_ok=True)

# ── Mutation list ─────────────────────────────────────────────────────────────
# Format: (chain, resi, wt, [mut_list], region_label)
# Selected CDR hotspot positions × representative substitutions

SCAN_MUTATIONS = [
    # VH CDR1 (Chothia 26-32) — key contact residues
    ("A", 27, "Y", ["A", "F", "W"],    "VH_CDR1"),   # Y27: aromatic contact
    ("A", 29, "F", ["A", "Y", "L"],    "VH_CDR1"),   # F29: hydrophobic core
    ("A", 31, "S", ["T", "G", "R"],    "VH_CDR1"),   # S31: polar contact

    # VH CDR2 (Chothia 52-56) — binding loop
    ("A", 50, "Y", ["A", "F", "H"],    "VH_CDR2"),   # Y50: aromatic stack
    ("A", 52, "Y", ["A", "F", "W"],    "VH_CDR2"),   # Y52: potential H-bond donor
    ("A", 54, "Y", ["A", "F", "S"],    "VH_CDR2"),   # Y54: interface contact

    # VH CDR3 (Chothia 95-102) — primary specificity determinant
    ("A", 99, "Y", ["A", "F", "W"],    "VH_CDR3"),   # Y99: aromatic interface
    ("A", 100,"K", ["R", "A", "E"],    "VH_CDR3"),   # K100: charge interaction
    ("A", 101,"Y", ["A", "F", "H"],    "VH_CDR3"),   # Y101: key contact
    ("A", 103,"Q", ["N", "K", "A"],    "VH_CDR3"),   # Q103: H-bond
    ("A", 105,"F", ["Y", "A", "L"],    "VH_CDR3"),   # F105: hydrophobic
    ("A", 107,"Y", ["A", "F", "W"],    "VH_CDR3"),   # Y107: terminal aromatic
]

# Flatten to list of dicts
all_muts = []
for chain, resi, wt, muts, region in SCAN_MUTATIONS:
    for mut in muts:
        all_muts.append({
            "chain": chain, "resi": resi, "wt": wt, "mut": mut,
            "label": f"{chain}{resi}{wt}>{mut}",
            "region": region,
        })

print(f"Total mutations to scan: {len(all_muts)}")
print(f"Regions: {set(m['region'] for m in all_muts)}")

# MM/GBSA subset — 10 representative variants covering beneficial/neutral/detrimental
MMGBSA_SUBSET_LABELS = {
    "A27Y>A", "A27Y>W",        # CDR1 Y27: alanine (likely detrimental), tryptophan
    "A99Y>A", "A99Y>W",        # CDR3 Y99: alanine vs tryptophan
    "A100K>R", "A100K>E",      # CDR3 K100: charge reversal
    "A101Y>A", "A101Y>F",      # CDR3 Y101: key position
    "A103Q>K", "A105F>Y",      # CDR3 additional positions
}

# ── Initialize toolkit ────────────────────────────────────────────────────────

print(f"\nInitializing toolkit on: {Path(PDB).name}")
tk = AffinityEnergyToolkit(PDB, ab_chains=AB_CHAINS, ag_chains=AG_CHAINS)

# ── Fast tools scan ───────────────────────────────────────────────────────────

FAST_TOOLS = ["evoef2", "prodigy", "thermompnn", "antifold", "esm_if1"]

results = []
tool_cache = {}  # Cache WT results where applicable

print(f"\n{'='*70}")
print("FAST TOOLS SCAN (EvoEF2 / PRODIGY / ThermoMPNN / AntiFold / ESM-IF1)")
print(f"{'='*70}")

# Pre-compute WT baselines for tools that support it
print("\n[WT baseline]")
wt_prodigy_dg  = None
wt_esmif1_logp = None

r_wt_prodigy = tk.run_prodigy([])
if r_wt_prodigy["error"] is None:
    wt_prodigy_dg = r_wt_prodigy["dg"]
    print(f"  PRODIGY WT dG: {wt_prodigy_dg:.3f} kcal/mol")

r_wt_esmif1 = tk.run_esm_if1([], wt_logp=None)
if r_wt_esmif1.get("wt_logp") is not None:
    wt_esmif1_logp = r_wt_esmif1.get("wt_logp")
    print(f"  ESM-IF1 WT logP: {wt_esmif1_logp:.4f}")

print(f"\nScanning {len(all_muts)} mutations across fast tools...")
print(f"{'Mutation':<14} {'Region':<10} {'EvoEF2':>8} {'PRODIGY':>8} {'ThermoMPN':>10} {'AntiFold':>9} {'ESM-IF1':>8} {'Time':>6}")
print("-" * 75)

for i, m in enumerate(all_muts):
    mutation = [{"chain": m["chain"], "resi": m["resi"], "wt": m["wt"], "mut": m["mut"]}]
    row = {
        "label": m["label"],
        "region": m["region"],
        "chain": m["chain"],
        "resi": m["resi"],
        "wt": m["wt"],
        "mut": m["mut"],
    }
    t_start = time.time()

    # EvoEF2
    r = tk.run_evoef2(mutation)
    row["evoef2_ddg"]   = r["ddg"]
    row["evoef2_err"]   = r["error"]
    row["evoef2_time"]  = r["elapsed"]

    # PRODIGY
    r = tk.run_prodigy(mutation, wt_dg=wt_prodigy_dg)
    row["prodigy_ddg"]  = r["ddg"]
    row["prodigy_err"]  = r["error"]
    row["prodigy_time"] = r["elapsed"]

    # ThermoMPNN
    r = tk.run_thermompnn(mutation)
    row["thermo_ddg"]   = r["ddg"]
    row["thermo_err"]   = r["error"]
    row["thermo_time"]  = r["elapsed"]

    # AntiFold
    r = tk.run_antifold(mutation)
    row["antifold_ddg"] = r["ddg"]
    row["antifold_err"] = r["error"]
    row["antifold_time"]= r["elapsed"]

    # ESM-IF1
    r = tk.run_esm_if1(mutation, wt_logp=wt_esmif1_logp)
    row["esmif1_ddg"]   = r["ddg"]
    row["esmif1_err"]   = r["error"]
    row["esmif1_time"]  = r["elapsed"]

    elapsed = time.time() - t_start
    row["total_time"] = round(elapsed, 1)
    results.append(row)

    def fmt(v, e):
        if e: return f"{'ERR':>8}"
        if v is None: return f"{'N/A':>8}"
        return f"{v:>8.3f}"

    print(f"{m['label']:<14} {m['region']:<10} "
          f"{fmt(row['evoef2_ddg'], row['evoef2_err'])}"
          f"{fmt(row['prodigy_ddg'], row['prodigy_err'])}"
          f"{fmt(row['thermo_ddg'], row['thermo_err']):>10}"
          f"{fmt(row['antifold_ddg'], row['antifold_err']):>9}"
          f"{fmt(row['esmif1_ddg'], row['esmif1_err'])}"
          f"{elapsed:>6.1f}s")

# ── MM/GBSA subset ────────────────────────────────────────────────────────────

print(f"\n{'='*70}")
print("MM/GBSA SUBSET (10 representative mutations, 200 minimization steps)")
print(f"{'='*70}")

mmgbsa_results = {}
wt_mmgbsa = None

# WT baseline
print("\n[WT MM/GBSA]")
r_wt_mm = tk.run_mmgbsa([], minimization_steps=200)
if r_wt_mm["error"] is None:
    wt_mmgbsa = r_wt_mm["dg"]
    print(f"  MM/GBSA WT dG: {wt_mmgbsa:.3f} kcal/mol  ({r_wt_mm['elapsed']:.1f}s)")

for row in results:
    if row["label"] not in MMGBSA_SUBSET_LABELS:
        continue
    mutation = [{"chain": row["chain"], "resi": row["resi"], "wt": row["wt"], "mut": row["mut"]}]
    r = tk.run_mmgbsa(mutation, wt_dg=wt_mmgbsa, minimization_steps=200)
    mmgbsa_results[row["label"]] = r["ddg"]
    err_str = f"  ERR: {r['error']}" if r["error"] else ""
    print(f"  {row['label']:<14}: ddG = {str(r['ddg']):<10} ({r['elapsed']:.1f}s){err_str}")

# Attach MM/GBSA results to main table
for row in results:
    row["mmgbsa_ddg"] = mmgbsa_results.get(row["label"])

# ── Save results ──────────────────────────────────────────────────────────────

csv_path  = OUT_DIR / "pag1_mutation_scan.csv"
json_path = OUT_DIR / "pag1_mutation_scan.json"

# CSV
fieldnames = ["label","region","chain","resi","wt","mut",
              "evoef2_ddg","prodigy_ddg","thermo_ddg","antifold_ddg","esmif1_ddg","mmgbsa_ddg",
              "evoef2_time","prodigy_time","thermo_time","antifold_time","esmif1_time","total_time",
              "evoef2_err","prodigy_err","thermo_err","antifold_err","esmif1_err"]
with open(csv_path, "w", newline="") as f:
    w = csv.DictWriter(f, fieldnames=fieldnames, extrasaction="ignore")
    w.writeheader()
    w.writerows(results)

# JSON
with open(json_path, "w") as f:
    json.dump({
        "pdb": PDB, "ab_chains": AB_CHAINS, "ag_chains": AG_CHAINS,
        "wt_baselines": {
            "prodigy_dg": wt_prodigy_dg,
            "esmif1_logp": wt_esmif1_logp,
            "mmgbsa_dg": wt_mmgbsa,
        },
        "mutations": results
    }, f, indent=2)

print(f"\n\nResults saved:")
print(f"  CSV : {csv_path}")
print(f"  JSON: {json_path}")
print(f"\nTotal mutations scanned: {len(results)}")
print(f"MM/GBSA variants:        {sum(1 for r in results if r['mmgbsa_ddg'] is not None)}")
