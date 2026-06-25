"""Diagnose EvoEF2 + AffinityEnergyToolkit on server."""
import json, subprocess, pathlib, sys

ROOT = pathlib.Path(__file__).resolve().parents[1]

# 1. Check tools registry
reg = json.loads((ROOT / "config/tools_registry.json").read_text())
e2 = reg["tools"].get("EvoEF2", {})
print("=== EvoEF2 registry entry ===")
print(json.dumps(e2, indent=2))
print()

# 2. Check if binary exists
entrypoint = e2.get("entrypoint", "")
if entrypoint:
    ep = pathlib.Path(entrypoint) if pathlib.Path(entrypoint).is_absolute() else ROOT / entrypoint
    print(f"Binary exists: {ep.is_file()}  ({ep})")
    print()

# 3. Try toolkit directly
sys.path.insert(0, str(ROOT))
from core.structure.affinity_energy_toolkit import AffinityEnergyToolkit

pdb = ROOT / "projects/fgf 23/vam_boltz_scan/FGF23/FGF23_relaxed.pdb"
print(f"PDB exists: {pdb.is_file()}")

tk = AffinityEnergyToolkit(
    complex_pdb=str(pdb),
    ab_chains=["H", "L"],
    ag_chains=["A"],
)

print("Running EvoEF2 WT baseline...")
r = tk.run_evoef2([])
print("Result:", r)
