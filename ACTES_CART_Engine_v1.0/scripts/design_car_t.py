import argparse
import json
import os
import sys

# Try to load optimizer and NCBI optionally, so failure doesn't break logic core
try:
    from codon_optimizer import optimize_sequence
except ImportError:
    optimize_sequence = lambda seq: f"[Codon Optimizer Unavailable: {len(seq)*3} bp pending]"

try:
    from ncbi_client import fetch_genbank_sequence, fetch_pubmed_summary
    from external_apis_client import BiologicalAPIClient
except ImportError:
    pass

# Load functional domains
MOD_DIR = os.path.dirname(os.path.abspath(__file__))
DB_SEARCH_PATHS = [
    os.path.join(MOD_DIR, "..", "..", "..", "..", "data", "design_rules", "functional_domains.json"),
    os.path.join(MOD_DIR, "..", "resources", "functional_domains.json")
]

DOMAIN_DB = {}
for path in DB_SEARCH_PATHS:
    if os.path.exists(path):
        try:
            with open(path, "r") as f:
                DOMAIN_DB = json.load(f)
            break
        except Exception as e:
            print(f"Warning: Could not load domain database at {path}: {e}")

def get_domain(category, key):
    return DOMAIN_DB.get(category, {}).get(key, {})

def smart_clinical_architecture(binder_seq, target_name, is_solid_tumor=False, tme_factors=None, dual_target=None, in_vivo=False, cns_target=False):
    """
    Intelligent Assembly Reasoning for Clinical Cellular Therapy.
    Iterates over 10 categories (161 elements) to build a robust architecture.
    """
    print(f"\n[CLINICAL ARCHITECTURE ENGINE] Diagnosing Design Blueprint for: {target_name}")
    blueprint = {
        "chassis": "CAR-T",
        "binder": {"seq": binder_seq, "name": "Custom_Binder"},
        "leader": {"name": "CD8a", "seq": get_domain("leaders", "CD8a").get("seq", "MALPVTALLLPLALLLHAARP")},
        "hinge": {}, "tm": {}, "costim": {}, "activation": {},
        "linker": None, "safety_switches": [], "tme_armor": [], "cleavage": None,
        "metrics": {"kd": "Unknown", "koff": "Unknown"}
    }
    
    tme_factors = [f.upper() for f in (tme_factors or [])]
    target_rules = DOMAIN_DB.get("targets", {}).get(target_name, {})
    distance = target_rules.get("distance", "Unknown")
    affinity_rule = target_rules.get("affinity_rule", "")

    # 0. IN-VIVO DELIVERY LOGIC & CNS (Brain) LOGIC
    if in_vivo:
        print("  > IN-VIVO DELIVERY: Vector packaging constraints apply (AAV/LNP). Prioritizing compact components.")
        # Override to ensure compact size
        distance = "Proximal" 
        blueprint["chassis"] = "In-Vivo CAR-T Vector"
        
    if cns_target:
        print("  > CNS/BRAIN DISPATCH: Target located behind Blood-Brain Barrier (BBB) or is Glioblastoma.")
        if in_vivo:
            print("    - ⚠️ IN-VIVO CNS: Mandatory AAV9 or target-specific BBB-crossing lipid formulation required.")
        else:
            print("    - 🧠 REGIONAL DELIVERY: Recommend Intracavitary/Intraventricular (ICV) administration instead of systemic IV.")
        # CNS armory: standard macrophages don't cross well; T-cells or CAR-NK preferred.
        if "macrophage" in tme_factors:
            print("    - OVERRIDE: Reverting CAR-M to CAR-T/NK due to poor macrophage BBB penetrance.")
            tme_factors.remove("MACROPHAGE")

    # 1. & 2. Chassis, Hinge & Scaffold (Distance & Steric rules)
    if "macrophage" in tme_factors or "fibrotic" in tme_factors:
        print("  > CHASSIS: Solid tumor with severe stroma -> Switching to CAR-M (FcRg) for phagocytic infiltration.")
        blueprint["chassis"] = "CAR-M"
        scaffold_key = "CAR-M_FcRg"
        scaffold = DOMAIN_DB["scaffolds"]["CAR-M"][scaffold_key]
    else:
        if distance == "Proximal" or in_vivo:
            print("  > HINGE/SCAFFOLD: Membrane-proximal target or In-Vivo limit -> Enforcing Short Hinge (4-1BB_Base / CD8a).")
            scaffold_key = "4-1BB_Base"
        elif distance == "Distal" and ("High steric hindrance" in target_rules.get("note", "") or "Long" in target_rules.get("note", "")):
            print("  > HINGE/SCAFFOLD: High steric hindrance distal target -> CD28_Base & Long Hinge required.")
            scaffold_key = "CD28_Base"
            blueprint["hinge"] = {"name": "IgG4_Long", "seq": DOMAIN_DB.get("hinges", {}).get("IgG4_Long", {}).get("seq", "VEPKSCDKTHTCPPCPAPELLGGPSVFLFPPKPKDTLMISRTPEVTCVVVDVSHEDPEVKFNWYVDGVEVHNAKTKPREEQYNSTYRVVSVLTVLHQDWLNGKEYKCKVSNKALPAPIEKTISKAKGQPREPQVYTLPPSRDELTKNQVSLTCLVKGFYPSDIAVEWESNGQPENNYKTTPPVLDSDGSFFLYSKLTVDKSRWQQGNVFSCSVMHEALHNHYTQKSLSLSPGK")}
        else:
            print("  > HINGE/SCAFFOLD: Defaulting to standard 2nd Gen 4-1BB.")
            scaffold_key = "4-1BB_Base"
        scaffold = DOMAIN_DB["scaffolds"]["CAR-T"][scaffold_key]

    blueprint["scaffold_name"] = scaffold_key
    components = scaffold.get("components", {})
    if not blueprint["hinge"]: blueprint["hinge"] = components.get("hinge", {})
    blueprint["tm"] = components.get("tm", {})
    blueprint["costim"] = components.get("costim", {})
    blueprint["activation"] = components.get("activation", {})
    
    # 3. Kinetics & Affinity Rules
    if "exhaustion" in affinity_rule.lower() or "koff" in affinity_rule.lower():
        blueprint["metrics"]["koff"] = "≥ 1e-2 s^-1 (Fast off-rate for serial killing)"
        blueprint["metrics"]["kd"] = "10 nM - 100 nM"
    elif "density" in affinity_rule.lower() and "low" in affinity_rule.lower():
        blueprint["metrics"]["koff"] = "≤ 1e-4 s^-1 (Slow dissociation)"
        blueprint["metrics"]["kd"] = "< 0.1 nM (Ultra-high affinity)"
    elif "toxicity" in affinity_rule.lower():
        blueprint["metrics"]["kd"] = "50 nM - 500 nM (Low affinity for density discrimination)"
        blueprint["metrics"]["koff"] = "~ 1e-1 to 1e-2 s^-1"
    else:
        blueprint["metrics"]["kd"] = "1 nM - 50 nM (Moderate to High)"
        blueprint["metrics"]["koff"] = "~ 1e-3 s^-1"
        
    # 4. Universal Adapters & Bispecific/Dual-Targeting Linkers
    if dual_target:
        print(f"  > BISPECIFIC LOGIC: Dual-targeting ({target_name} + {dual_target}).")
        if target_name == dual_target:
            print("    - HOMOTYPIC TANDEM: Targeting two epitopes on the same protein. Medium Linker recommended.")
            blueprint["linker"] = {"name": "G4S3", "seq": DOMAIN_DB.get("linkers", {}).get("Medium", {}).get("G4S3", {}).get("seq", "GGGGSGGGGSGGGGS")}
        else:
            print("    - HETEROTYPIC TANDEM: Two different targets (OR gate). Long flexibility needed to span cell surface.")
            blueprint["linker"] = {"name": "G4S5/G4S6", "seq": DOMAIN_DB.get("linkers", {}).get("Medium", {}).get("G4S5", {}).get("seq", "GGGGSGGGGSGGGGSGGGGSGGGGS")}
            # If combining strong+weak targets, recommend logic gating
            if in_vivo == False and is_solid_tumor:
                print("  > 💡 RECOMMENDATION: For solid tumors, consider converting this Tandem-CAR into a SynNotch (AND gate) to prevent severe off-tumor toxicity.")

    # 5. & 6. Switch Receptors & TME Armor
    if is_solid_tumor:
        print("  > SOLID TUMOR DETECTED: Evaluating TME countermeasures...")
        if in_vivo:
            print("    - ⚠️ IN-VIVO LIMIT: Skipping large TME Armour (CSR/DNR) to respect viral vector packaging limits (~4.7kb).")
        else:
            if "PD-L1" in tme_factors or "PDL1" in tme_factors:
                print("    - TME: High PD-L1 -> Equipping PD1_CD28_CSR (Chimeric Switch Receptor).")
                csr = get_domain("switch_receptors", "PD1_CD28_CSR")
                blueprint["tme_armor"].append({"name": "PD1_CD28_CSR", "seq": csr.get("full_CSR_seq", ""), "desc": "Converts PD-L1 inhibition to CD28 costimulation."})
            
            if "TGFB" in tme_factors:
                print("    - TME: High TGF-beta -> Equipping TGFB_DNR (Dominant Negative Receptor).")
                dnr = get_domain("frontier_modalities", "TGFB_DNR")
                blueprint["tme_armor"].append({"name": "TGFB_DNR", "seq": dnr.get("seq", ""), "desc": "Blocks immunosuppressive TGF-beta signaling."})
                
            if "STROMAL" in tme_factors or "COLD" in tme_factors:
                print("    - TME: Cold/Stromal tumor -> Equipping Membrane_IL15 to promote NK/T infiltration.")
                il15 = get_domain("anchored_cytokines", "Membrane_IL15")
                blueprint["tme_armor"].append({"name": "Membrane_IL15", "seq": il15.get("seq", ""), "desc": "Anchored cytokine for persistence."})

    # 7. Safety Switches & Cleavage (2A)
    # If we add powerful TME armor or cytokines, we MUST add a safety switch.
    if (blueprint["tme_armor"] or target_name in ["HER2", "GD2", "EGFR"]) and not in_vivo:
        print("  > SAFETY PROTOCOL: High-risk profile. Compulsory Safety Switch active.")
        icasp9 = get_domain("safety_switches", "iCasp9")
        blueprint["safety_switches"].append({"name": "iCasp9", "seq": icasp9.get("seq", "")})
        p2a = get_domain("two_A_peptides", "P2A")
        blueprint["cleavage"] = {"name": "P2A", "seq": p2a.get("seq", "GSGATNFSLLKQAGDVEENPGP")}
    elif in_vivo:
        print("  > SAFETY PROTOCOL: In-Vivo vector packaging limits prohibit heavy Safety Switches. Proceed with caution.")

    print("  > ASSEMBLY COMPLETE.")
    return blueprint

def export_markdown_report(name, bp, full_vector_seq):
    primary_reports_dir = os.path.join(MOD_DIR, "..", "..", "..", "..", "reports", "generated_plans")
    fallback_reports_dir = os.path.join(MOD_DIR, "..", "reports", "generated_plans")
    
    # Try using the project root if it exists, otherwise use localized workspace
    if os.path.exists(os.path.join(MOD_DIR, "..", "..", "..", "..", "data")):
        reports_dir = primary_reports_dir
    else:
        reports_dir = fallback_reports_dir
        
    os.makedirs(reports_dir, exist_ok=True)
    
    file_path = os.path.join(reports_dir, f"{name}_Clinical_Blueprint.md")
    
    with open(file_path, "w", encoding="utf-8") as f:
        f.write(f"# 🧬 Clinical Experimental Plan: `{name.upper()}`\n\n")
        f.write("## 1. Construct Architecture Summary\n")
        f.write(f"- **Primary Chassis:** {bp['chassis']}\n")
        f.write(f"- **Scaffold Backbone:** {bp['scaffold_name']}\n")
        f.write(f"- **Target Affinity Strategy:** {bp['metrics']['kd']}\n")
        f.write(f"- **Binding Kinetics (Off-rate):** {bp['metrics']['koff']}\n\n")
        
        f.write("## 2. Component Logic & Assembly Stack\n")
        f.write("| Module | Assigned Element | Biological Rationale/Notes |\n")
        f.write("|---|---|---|\n")
        f.write(f"| **Leader** | {bp['leader']['name']} | High-efficiency membrane targeting |\n")
        
        if bp['linker']:
             f.write(f"| **Linker (Dual)** | {bp['linker']['name']} | Accommodates tandem binding geometry |\n")
             
        f.write(f"| **Hinge** | {bp['hinge'].get('name', bp['hinge'].get('source', 'Standard'))} | Matched to target epitope distance |\n")
        f.write(f"| **Co-stimulation** | {bp.get('costim', {}).get('source', '4-1BB')} | Determines metabolic persistence |\n")
        f.write(f"| **Activation** | {bp.get('activation', {}).get('source', 'CD3z')} | ITAM signaling core |\n\n")
        
        if bp['tme_armor'] or bp['safety_switches']:
            f.write("## 3. Auxiliary Payloads (TME & Safety)\n")
            if bp['cleavage']:
                f.write(f"**Cleavage Mechanism:** {bp['cleavage']['name']} Ribosomal Skip Sequence\n\n")
            for armor in bp['tme_armor']:
                f.write(f"**⚔️ TME Armor: {armor['name']}**\n- *Function:* {armor['desc']}\n\n")
            for safety in bp['safety_switches']:
                f.write(f"**🛑 Safety Switch: {safety['name']}**\n- *Function:* Inducible Apoptosis for severe CRS mitigation\n\n")
        
        f.write("## 4. Sequence Outputs\n")
        f.write(f"**Total Vector Polyprotein AA Length:** {len(full_vector_seq)} AAs\n\n")
        f.write("```amino_acid\n")
        # Format FASTA like wrapping
        for i in range(0, len(full_vector_seq), 80):
            f.write(full_vector_seq[i:i+80] + "\n")
        f.write("```\n\n")
        
        f.write("---\n*Generated by ACTES Antibody Engineer Suite Phase 3 Clinical Architecture Engine*\n")
        
    print(f"\n✅ [PHASE 3: EXPORT SUCCESS] Experimental plan saved to: {file_path}")

def print_clinical_report(name, bp):
    print(f"\n{'='*75}")
    print(f" 🧬 CLINICAL CELLULAR THERAPY ARCHITECTURE: {name.upper()} 🧬")
    print(f"{'='*75}")
    print(f"CHASSIS:  {bp['chassis']} (Scaffold: {bp['scaffold_name']})")
    print(f"AFFINITY: Target {bp['metrics']['kd']}")
    print(f"KINETICS: {bp['metrics']['koff']}")
    print(f"{'-'*75}")
    print(f"🛠️  CORE ARCHITECTURE MODULES:")
    print(f"  [1] LEADER:    {bp['leader']['name']}")
    if bp['linker']:
        print(f"  [*] LINKER:    {bp['linker']['name']} (Tandem configuration)")
    print(f"  [2] HINGE:     {bp['hinge'].get('source', bp['hinge'].get('name', 'Standard'))}")
    if bp.get("tm", {}).get("source"):
        print(f"  [3] TM/COSTIM: {bp['tm'].get('source', 'N/A')} / {bp.get('costim', {}).get('source', 'N/A')}")
    if isinstance(bp.get("activation"), dict) and bp.get("activation", {}).get("source"):
        print(f"  [4] SIGNALING: {bp['activation'].get('source', 'N/A')}")
        
    if bp['tme_armor'] or bp['safety_switches']:
        print(f"{'-'*75}")
        print(f"🛡️  AUXILIARY PAYLOADS (Polycistronic Vector):")
        if bp['cleavage']:
            print(f"  [✂️] CLEAVAGE:  {bp['cleavage']['name']} Ribosomal Skip Sequence")
        for armor in bp['tme_armor']:
            print(f"  [⚔️] TME ARMOR: {armor['name']} - {armor['desc']}")
        for safety in bp['safety_switches']:
            print(f"  [🛑] SAFETY:    {safety['name']} Inducible Apoptosis Switch")

    # Final string concatenation
    parts = [bp['leader'].get('seq', ''), bp['binder'].get('seq', '')]
    if bp['linker']: parts.append(bp['linker'].get('seq', ''))
    
    parts.extend([
        bp['hinge'].get('seq', ''),
        bp['tm'].get('seq', ''),
        bp.get('costim', {}).get('seq', ''),
        bp.get('activation', {}).get('seq', '')
    ])
    
    primary_car_seq = "".join(parts)
    full_vector_seq = primary_car_seq
    
    if bp['cleavage']:
        cleavage_seq = bp['cleavage'].get('seq', '')
        full_vector_seq += cleavage_seq
        for armor in bp['tme_armor']:
            full_vector_seq += armor.get('seq', '') + cleavage_seq
        for safety in bp['safety_switches']:
            full_vector_seq += safety.get('seq', '')
            
    print(f"{'-'*75}")
    print(f"Total AA Length (CAR only): {len(primary_car_seq)}")
    print(f"Total Vector Polyprotein AA Length: {len(full_vector_seq)}")
    print(f"\nFULL AMINO ACID SEQUENCE:")
    # Print in blocks of 80 characters for readability
    for i in range(0, len(full_vector_seq), 80):
        print(full_vector_seq[i:i+80])
    print(f"{'='*75}\n")
    
    # Export Phase 3 Markdown Report
    export_markdown_report(name, bp, full_vector_seq)

def main():
    parser = argparse.ArgumentParser(description="Clinical Cellular Therapy Architecture Generator")
    parser.add_argument("--binder", required=True, help="Binding domain sequence (VHH or scFv)")
    parser.add_argument("--target", required=True, help="Primary Target Name (e.g., MSLN, CD19, HER2)")
    parser.add_argument("--dual", help="Secondary target for Tandem/Bispecific CAR (e.g., CD22)")
    parser.add_argument("--solid", action="store_true", help="Flag: This is a solid tumor target")
    parser.add_argument("--invivo", action="store_true", help="Flag: Design for in-vivo viral vector delivery (LNP/AAV limits)")
    parser.add_argument("--cns", action="store_true", help="Flag: CNS/Brain localized target (e.g. Glioblastoma)")
    parser.add_argument("--tme", nargs='+', default=[], help="TME Factors: PDL1, TGFB, STROMAL, COLD, MACROPHAGE")
    parser.add_argument("--name", default="clinical_construct", help="Name for the output report")

    args = parser.parse_args()
    
    blueprint = smart_clinical_architecture(args.binder, args.target, args.solid, args.tme, args.dual, args.invivo, args.cns)
    print_clinical_report(args.name, blueprint)

if __name__ == "__main__":
    main()
