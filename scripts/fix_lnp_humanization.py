"""
Tag all LNP targeting entries with correct humanization_status.
Assessment based on VH framework analysis and published antibody origins.
"""
import json

HUMANIZATION_MAP = {
    "CD5_scFv_InVivo_Targeting": "MURINE",            # VH starts QVQLQQSGPELV (murine FR1)
    "CD2_Siplizumab_LNP_Targeting": "HUMANIZED",      # Siplizumab (MEDI-507) = humanized IgG1
    "CD56_Lorvotuzumab_LNP_Targeting": "HUMANIZED",   # Lorvotuzumab (huN901) = humanized IgG1
    "CD7_TH69_LNP_Targeting": "MURINE",               # TH-69 = murine IgG2a
    "CD16_3G8_LNP_Targeting": "MURINE",               # 3G8 = murine IgG1
    "CD4_MT310_LNP_Targeting": "MURINE",              # MT310 = murine-derived clone
    "FMC63_CD19_LNP_Targeting": "MURINE",             # FMC63 = murine IgG1 (VH3-like FR but murine origin)
}

NOTES = {
    "CD5_scFv_InVivo_Targeting": "⚠️ MURINE sequence. VH starts QVQLQQSGPELV (murine IGHV1 FR1). For human in vivo use, CDR-graft onto human framework required.",
    "CD7_TH69_LNP_Targeting": "⚠️ MURINE sequence. TH-69 is a murine IgG2a anti-CD7. Not suitable for human in vivo delivery without humanization.",
    "CD16_3G8_LNP_Targeting": "⚠️ MURINE sequence. 3G8 clone is murine IgG1 anti-CD16a/b. Humanization required for clinical LNP applications.",
    "CD4_MT310_LNP_Targeting": "⚠️ MURINE sequence. MT310 clone derived from murine immunization. Requires humanization for in vivo human use.",
    "FMC63_CD19_LNP_Targeting": "⚠️ MURINE sequence. FMC63 is murine IgG1 anti-CD19 (VH3-family FR, but murine origin). Widely used clinically as chimeric scFv in approved CARs (tisagenlecleucel, axicabtagene).",
}

with open("config/cart_components_registry.json") as f:
    data = json.load(f)

elements = data.get("elements", [])
changed = 0
for e in elements:
    if e.get("subcategory") != "LNP/mRNA Targeting Ligand":
        continue
    eid = e.get("id", "")
    if eid in HUMANIZATION_MAP and "humanization_status" not in e:
        e["humanization_status"] = HUMANIZATION_MAP[eid]
        changed += 1
    if eid in NOTES:
        # Prepend warning to existing design_notes if not already there
        current_notes = e.get("design_notes", "")
        if not current_notes.startswith("⚠️"):
            e["design_notes"] = NOTES[eid] + (" " + current_notes if current_notes else "")

print(f"Tagged {changed} entries with humanization_status")

with open("config/cart_components_registry.json", "w") as f:
    json.dump(data, f, indent=2, ensure_ascii=False)

print("Saved.")

# Final summary
lnp = [e for e in data.get("elements", []) if e.get("subcategory") == "LNP/mRNA Targeting Ligand"]
hu = [e["id"] for e in lnp if e.get("humanization_status") == "HUMANIZED"]
mu = [e["id"] for e in lnp if e.get("humanization_status") == "MURINE"]
unk = [e["id"] for e in lnp if e.get("humanization_status") not in ("HUMANIZED", "MURINE")]
print(f"\nHUMANIZED ({len(hu)}): {hu}")
print(f"MURINE    ({len(mu)}): {mu}")
print(f"UNKNOWN   ({len(unk)}): {unk}")
