import argparse
import json
import os
from codon_optimizer import optimize_sequence
from ncbi_client import fetch_genbank_sequence, fetch_pubmed_summary
from external_apis_client import BiologicalAPIClient

# Load functional domains
DB_PATH = os.path.join(os.path.dirname(__file__), "..", "data", "design_rules", "functional_domains.json")
try:
    with open(DB_PATH, "r") as f:
        DOMAIN_DB = json.load(f)
except Exception as e:
    print(f"Warning: Could not load domain database: {e}")
    DOMAIN_DB = {}

def get_domain(category, key):
    return DOMAIN_DB.get(category, {}).get(key, {})

class CARConstruct:
    def __init__(self, name="car_construct"):
        self.name = name
        self.parts = []  # List of (label, sequence) tuples

    def add_part(self, label, seq):
        if seq:
            self.parts.append((label, seq))

    def get_full_aa(self):
        return "".join([p[1] for p in self.parts])

    def print_summary(self):
        print(f"\n{'='*60}")
        print(f" MODULAR CELL THERAPY DESIGN: {self.name.upper()}")
        print(f"{'='*60}")
        for label, seq in self.parts:
            print(f"[{label:^12}] : {len(seq):>3} AA")
        print(f"{'-'*60}")
        full_aa = self.get_full_aa()
        full_dna = optimize_sequence(full_aa)
        print(f"Total Length : {len(full_aa)} AA / {len(full_dna)} bp")
        print(f"{'='*60}")
        print("\nAMINO ACID SEQUENCE:")
        print(full_aa)
        print("\nOPTIMIZED DNA SEQUENCE (Human/CHO):")
        print(full_dna)
        print(f"{'='*60}\n")

# Common Design Presets
PRESETS = {
    "classic_19": {
        "binder": "FMC63",
        "scaffold": "4-1BB_Base",
        "name": "classic_cd19_car"
    },
    "armored_nk": {
        "binder": "FMC63,c11D5.3",
        "scaffold": "CAR-NK_DAP12",
        "armored_cytokine": "Membrane_IL15",
        "name": "armored_tandem_nk"
    },
    "universal_safe": {
        "binder": "Anti_FITC_h4M53",
        "tags": "CD20_Mimotope",
        "dimerizer": "FKBP12",
        "name": "universal_switch_car"
    },
    "synnotch_logic": {
        "binder": "FMC63",
        "scaffold": "SynNotch_Base",
        "name": "synnotch_prime_vector"
    },
    "invivo_targeting": {
        "binder": "Foralumab_hCD3",
        "name": "invivo_linda_vector"
    },
    "autoimmune_treg": {
        "binder": "Anti_CD19_h4M53",
        "scaffold": "CD28_Base",
        "name": "sle_car_treg"
    }
}

def recommend_strategy(disease_type):
    rules_path = os.path.join(os.path.dirname(__file__), "..", ".agent", "skills", "antibody_designer", "resources", "modality_design_rules.json")
    try:
        with open(rules_path, "r") as f:
            rules = json.load(f)
        strat = rules.get("disease_context_strategies", {}).get(disease_type, {})
        if strat:
            print(f"\n💡 [Strategy Recommendation for {disease_type}]:")
            print(f"   - Focus: {strat.get('focus')}")
            print(f"   - Rule: {strat.get('recommendation')}")
    except:
        pass

def auto_select_hinge(binder_key):
    """
    Logic: Distal Epitopes (CD19/BCMA) -> Short Hinge (CD8a)
           Proximal Epitopes (MSLN/GPC3) -> Short Hinge
           Bulky/Steric Distal (CD22/ROR1) -> Long Hinge (IgG4)
    """
    # 1. Resolve Target name
    target_name = "Unknown"
    for cat in ["clinical_binders", "binders", "universal_adapters"]:
        data = get_domain(cat, binder_key.split(",")[0])
        if data:
            target_name = data.get("target", "Unknown")
            break
    
    # 2. Get Target Metadata
    targets_db = DOMAIN_DB.get("targets", {})
    metadata = targets_db.get(target_name, {})
    distance = metadata.get("distance", "Unknown")
    
    # 3. Decision Logic
    if target_name == "CD22" or distance == "Distal" and target_name != "CD19":
        print(f"📐 Target {target_name} is Distal/Bulky. Optimized for LONG hinge.")
        return "IgG4_Long"
    elif distance == "Proximal":
        print(f"📐 Target {target_name} is Proximal. Optimized for SHORT hinge.")
        return "CD8a_Short"
    else:
        return "CD8a_Short" # Default

def generate_car_report(binder_key, scaffold_key="4-1BB_Base", leader_key="CD8a", name="car_t_construct", verify=False, armored_cytokine=None, tags=None, dimerizer=None, linker_type="Medium", shield=None, hinge_key=None, disease=None, is_treg=False):
    construct = CARConstruct(name)
    
    if disease:
        recommend_strategy(disease)

    # 0. Hinge Selection Logic (Synapse Optimizer)
    if not hinge_key:
        hinge_key = auto_select_hinge(binder_key)
    
    hinge_data = get_domain("hinges", hinge_key)
    
    # 1. Leader
    leader = get_domain("leaders", leader_key)
    construct.add_part("LEADER", leader.get("seq", ""))

    # 2. Shielding (Dominant Negative Receptors)
    if shield:
        shield_data = get_domain("frontier_modalities", shield)
        if shield_data:
            construct.add_part(f"SHIELD:{shield}", shield_data.get("seq", ""))
            construct.add_part("P2A", "GSGATNFSLLKQAGDVEENPGP")
            print(f"🛡️ Added TME Shielding: {shield}")

    # 3. Tags (e.g. CD20 mimotope for clearance)
    if tags:
        for t_key in tags.split(","):
            tag_data = get_domain("depletion_epitopes", t_key.strip())
            if tag_data:
                construct.add_part(f"TAG:{t_key}", tag_data.get("seq", ""))
                construct.add_part("LINKER", "GGGGS")

    # 4. Binder Selection (Lego Binders)
    res_seqs = []
    keys = [k.strip() for k in binder_key.split(",")]
    for k in keys:
        # Check clinical binders, universal, or frontier
        data = get_domain("clinical_binders", k) or get_domain("binders", k) or get_domain("universal_adapters", k)
        if data:
            res_seqs.append(data.get("seq", ""))
            print(f"✅ Resolved Binder: {k}")
        else:
            res_seqs.append(k) # Raw sequence
    
    # Selection of Tandem Linker based on library
    linker_lib = get_domain("linkers", linker_type)
    tandem_linker = "GGGGSGGGGSGGGGS" # Default
    if isinstance(linker_lib, dict):
        tandem_linker = linker_lib.get("G4S3", {}).get("seq", tandem_linker)
    
    binder_seq = tandem_linker.join(res_seqs)
    label = "TANDEM_BINDER" if len(res_seqs) > 1 else "BINDER"
    construct.add_part(label, binder_seq)

    # 5. Inducible Switch (e.g. FRB/FKBP for Rapamycin)
    if dimerizer:
        dimer_data = get_domain("dimerization_domains", dimerizer)
        if dimer_data:
            construct.add_part("DIMERIZER", dimer_data.get("seq", ""))
            construct.add_part("LINKER", "GGGGS")
            print(f"🔌 Integrated Inducible Switch: {dimerizer}")

    # 6. Scaffold Assembly (T/NK/SUPRA/Frontier)
    scaffold = {}
    # Search in all scaffold types
    for cat in DOMAIN_DB.get("scaffolds", {}).values():
        if scaffold_key in cat:
            scaffold = cat[scaffold_key]
            break
    
    # Check Frontier Modalities if not in scaffolds (e.g. SynNotch_Base)
    if not scaffold:
        frontier_data = get_domain("frontier_modalities", scaffold_key)
        if frontier_data:
            construct.add_part(f"FRONTIER:{scaffold_key}", frontier_data.get("seq", ""))
            if "SynNotch" in scaffold_key:
                tf_data = get_domain("frontier_modalities", "TF_Gal4_VP64")
                construct.add_part("TF:Gal4VP64", tf_data.get("seq", ""))
            print(f"🚀 Using Frontier Architecture: {scaffold_key}")
            scaffold = True # Mark as found

    if scaffold and isinstance(scaffold, dict):
        comps = scaffold.get("components", {})
        
        # Use auto-selected hinge if not overridden by scaffold hardcode
        final_hinge_seq = hinge_data.get("seq", "") if hinge_data else comps.get("hinge", {}).get("seq", "")
        construct.add_part("HINGE", final_hinge_seq)
        
        construct.add_part("TM", comps.get("tm", {}).get("seq", ""))
        
        # Split CAR logic
        if "zipper_acidic" in comps: construct.add_part("ZIP_ACID", comps.get("zipper_acidic", {}).get("seq", ""))
        if "zipper_basic" in comps: construct.add_part("ZIP_BASE", comps.get("zipper_basic", {}).get("seq", ""))
        
        # Myeloid Activation
        if "phagocytic" in comps:
            phago_data = get_domain("frontier_modalities", comps["phagocytic"])
            construct.add_part("PHAGO", phago_data.get("seq", ""))

        # Multi-Costim logic (3rd Gen)
        if "costim_1" in comps: construct.add_part("COSTIM_1", comps.get("costim_1", {}).get("seq", ""))
        if "costim_2" in comps: construct.add_part("COSTIM_2", comps.get("costim_2", {}).get("seq", ""))
        
        # Base Signaling
        construct.add_part("COSTIM_BASE", comps.get("costim", {}).get("seq", ""))
        construct.add_part("ACTIVATION", comps.get("activation", {}).get("seq", ""))
    
    elif scaffold is not True:
        print(f"Error: Scaffold {scaffold_key} not found.")

    # 7. Armored Co-expression (P2A)
    if armored_cytokine:
        cytokine_data = get_domain("anchored_cytokines", armored_cytokine)
        if cytokine_data:
            construct.add_part("P2A", "GSGATNFSLLKQAGDVEENPGP")
            construct.add_part(f"ARMOR:{armored_cytokine}", cytokine_data.get("seq", ""))
            print(f"🛡️ Armored with anchored cytokine: {armored_cytokine}")

    # 8. Treg Phenotype Stabilization
    if is_treg:
        foxp3 = get_domain("CAR-Treg", "FoxP3_Induction")
        il2ra = get_domain("CAR-Treg", "Stat5_Enhanced_IL2RA")
        construct.add_part("P2A", "GSGATNFSLLKQAGDVEENPGP")
        construct.add_part("FOXP3", foxp3.get("seq", ""))
        construct.add_part("P2A", "GSGATNFSLLKQAGDVEENPGP")
        construct.add_part("IL2RA_ST5", il2ra.get("seq", ""))
        print("🧘 Optimized for Treg Phenotype (FoxP3 + IL2RA Integration)")

    construct.print_summary()

def main():
    parser = argparse.ArgumentParser(description="Lego-like Advanced Cell Therapy Designer")
    parser.add_argument("--preset", choices=PRESETS.keys(), help="Use a pre-defined design template.")
    parser.add_argument("--binder", help="Binder key(s), support tandem with comma.")
    parser.add_argument("--scaffold", default="4-1BB_Base", help="Registry Key for scaffold.")
    parser.add_argument("--tags", help="Comma-separated depletion/tracking tags.")
    parser.add_argument("--dimerizer", help="Inducible switch domain.")
    parser.add_argument("--armored_cytokine", help="Membrane-anchored cytokine co-expression.")
    parser.add_argument("--linker_type", default="Medium", choices=["Short", "Medium", "Long"], help="Linker library category.")
    parser.add_argument("--shield", help="TME Shielding domain.")
    parser.add_argument("--leader", default="CD8a", help="Signal peptide leader.")
    parser.add_argument("--name", default="modular_car_construct", help="Output name.")
    parser.add_argument("--verify", action="store_true", help="Live database verification.")
    parser.add_argument("--disease", choices=["Hematological", "Solid_Tumors", "Autoimmune"], help="Target disease context.")
    parser.add_argument("--treg", action="store_true", help="Build as a CAR-Treg construct.")

    args = parser.parse_args()
    
    # Handle Preset Overrides
    binder = args.binder
    scaffold = args.scaffold
    armored = args.armored_cytokine
    tags = args.tags
    dimerizer = args.dimerizer
    shield = args.shield
    name = args.name

    if args.preset:
        p_data = PRESETS[args.preset]
        print(f"🌟 Loading Preset: {args.preset}...")
        binder = p_data.get("binder", binder)
        scaffold = p_data.get("scaffold", scaffold)
        armored = p_data.get("armored_cytokine", armored)
        tags = p_data.get("tags", tags)
        dimerizer = p_data.get("dimerizer", dimerizer)
        shield = p_data.get("shield", shield)
        name = p_data.get("name", name)

    if not binder and not args.preset:
        parser.error("Either --binder or --preset must be provided.")

    generate_car_report(
        binder, scaffold, args.leader, name, args.verify, 
        armored, tags, dimerizer, args.linker_type, shield, disease=args.disease, is_treg=args.treg
    )

if __name__ == "__main__":
    main()
