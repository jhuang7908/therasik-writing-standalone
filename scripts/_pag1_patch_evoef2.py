"""Patch existing scan results: add EvoEF2 ΔΔG values."""
import sys, json, csv
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))
from core.structure.affinity_energy_toolkit import AffinityEnergyToolkit

PDB = (
    r"D:\InSynBio-AI-Research\Antibody_Engineer_Suite\projects\PAG-1 project"
    r"\7m_humanPAG1\7m_humanPAG1_df5fc"
    r"\7m_humanPAG1_df5fc_relaxed_rank_001_alphafold2_multimer_v3_model_5_seed_000.pdb"
)
JSON_IN = Path(
    r"D:\InSynBio-AI-Research\Antibody_Engineer_Suite\projects\PAG-1 project"
    r"\mutation_scan_results\pag1_mutation_scan.json"
)

tk = AffinityEnergyToolkit(PDB, ab_chains=["A","B"], ag_chains=["C"])

# WT baseline
print("Computing EvoEF2 WT baseline...")
r_wt = tk.run_evoef2([])
if r_wt["error"]:
    print(f"  ERROR: {r_wt['error']}")
    sys.exit(1)
wt_dg = r_wt["dg"]
print(f"  WT dG = {wt_dg}  (error={r_wt['error']})")

# Read existing results
with open(JSON_IN) as f:
    data = json.load(f)

data["wt_baselines"]["evoef2_dg"] = wt_dg

print(f"\nPatching {len(data['mutations'])} mutations...")
print(f"{'Mutation':<14} {'dG':>8} {'ddG':>8} {'err'}")
for m in data["mutations"]:
    mutation = [{"chain": m["chain"], "resi": m["resi"], "wt": m["wt"], "mut": m["mut"]}]
    r = tk.run_evoef2(mutation, wt_dg=wt_dg)
    m["evoef2_ddg"] = r["ddg"]
    m["evoef2_err"] = r["error"]
    m["evoef2_time"] = r["elapsed"]
    dg_str = f"{r['dg']:.3f}" if r["dg"] is not None else "N/A"
    ddg_str = f"{r['ddg']:+.3f}" if r["ddg"] is not None else "N/A"
    print(f"  {m['label']:<14} dG={dg_str:>8}  ddG={ddg_str:>8}  err={r['error']}")

# Save
with open(JSON_IN, "w") as f:
    json.dump(data, f, indent=2)

# Rewrite CSV
CSV_OUT = JSON_IN.with_suffix(".csv")
fieldnames = ["label","region","chain","resi","wt","mut",
              "evoef2_ddg","prodigy_ddg","thermo_ddg","antifold_ddg","esmif1_ddg","mmgbsa_ddg",
              "evoef2_time","prodigy_time","thermo_time","antifold_time","esmif1_time","total_time",
              "evoef2_err","prodigy_err","thermo_err","antifold_err","esmif1_err"]
with open(CSV_OUT, "w", newline="") as f:
    w = csv.DictWriter(f, fieldnames=fieldnames, extrasaction="ignore")
    w.writeheader()
    w.writerows(data["mutations"])

print(f"\nPatched JSON: {JSON_IN}")
print(f"Patched CSV:  {CSV_OUT}")
