import json
from pathlib import Path

ssot_path = Path("config/standards_ssot.json")
data = json.loads(ssot_path.read_text(encoding="utf-8"))

target = data["runtime_policies"]["conventional_vh"]
print("Current standard_id:", target.get("standard_id"))
print("Current policy_family:", target.get("policy_family"))

target["standard_id"] = "VH_TO_VHH_CONVERSION_STANDARD_V1.8.17"
target["_v1817_note"] = (
    "V1.8.17 (2026-05-16): "
    "(1) Stealth tier changed from CDR3-length-based to net_basic/pI-conditional "
    "(NONE net_basic<=2 / MINIMAL 3-4 / STANDARD 5-6 / FULL >=7 or pI>=9.0). "
    "Structural audit (n=6 CD3 Fv panel, ABodyBuilder2): all Stealth K positions are "
    "surface-exposed in Fv (SASA ~94 A2) — NOT VL-shielded. Stealth = charge management only. "
    "(2) Y91/F91 and W103 added as monitoring metrics (no mutation). "
    "n=130 VHH cohort: CDR3-drape on Y91 confirmed (r=-0.23, p=0.008) but effect size small. "
    "Hallmark (L45R/W47G/G44E) and VL-safety SASA gate (50 A2 threshold) UNCHANGED from V1.8.16. "
    "Script: scripts/run_cd3_v1817.py"
)

ssot_path.write_text(json.dumps(data, indent=2, ensure_ascii=False), encoding="utf-8")
print("Updated. New standard_id:", data["runtime_policies"]["conventional_vh"]["standard_id"])
