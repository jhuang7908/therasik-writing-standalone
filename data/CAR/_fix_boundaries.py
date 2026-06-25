"""
Fix residue boundary documentation for 12 elements with missing range info
Add NCBI Gene ID where possible for protein-coding elements
"""
import json
from pathlib import Path

CAR_DIR = Path(r"D:\InSynBio-AI-Research\Antibody_Engineer_Suite\data\CAR")
V3_PATH  = CAR_DIR / "CART_LIBRARY_V3.json"
with open(V3_PATH, encoding="utf-8") as f:
    lib = json.load(f)
v3 = {e["id"]: e for e in lib["elements"]}

# Format: id -> (UniProt, full_length, start, end, NCBI_Gene_ID, gene_symbol, note)
BOUNDARY_DATA = {
    "IgKappa_SP": (
        "P01834", 214, 1, 22, 3514, "IGKC",
        "IgG kappa constant region N-terminal SP: res 1-22 (22aa signal peptide)"
    ),
    "FKBP12": (
        "P62942", 108, 1, 108, 2280, "FKBP1A",
        "FKBP1A_HUMAN full 108aa; no signal peptide; cytoplasmic protein"
    ),
    "RQR8": (
        None, 146, None, None, None, "RQR8",
        "Synthetic fusion: CD34 epitope (res 1-50) + CD20 epitope (res 51-146); "
        "Designed by Philip 2014 Blood; no natural UniProt/Gene ID — synthetic construct"
    ),
    "HSV-TK": (
        "P03176", 376, 1, 376, None, "UL23",
        "UL23 (TK_HHV11) HSV-1 thymidine kinase full 376aa; "
        "NCBI Gene: 2703454 (HHV-1 strain 17); UniProt P03176"
    ),
    "GPX4_Enhanced": (
        "P36969", 197, 1, 197, 2879, "GPX4",
        "GPX4_HUMAN full 197aa (mitochondrial isoform); U46G mutation for enhanced activity; "
        "Gene: GPX4 (chr 19p13.3); UniProt P36969"
    ),
    "tEGFR_DeplTag": (
        "P00533", 1210, 1, 659, 1956, "EGFR",
        "EGFR_HUMAN res 1-659 (ECD domains I-IV) + TM 645-667; "
        "Truncated: ECD+TM only, no intracellular kinase (res 668-1210 deleted); "
        "Gene: EGFR (chr 7p11.2); UniProt P00533"
    ),
    "FoxP3_TF": (
        "Q9BZS1", 431, 1, 431, 50943, "FOXP3",
        "FOXP3_HUMAN full 431aa transcription factor; "
        "Contains: N-terminal repressor (1-196) + Zinc finger (197-265) + Forkhead domain (338-421); "
        "Gene: FOXP3 (chrXp11.23); UniProt Q9BZS1"
    ),
    "cJun_Overexpression": (
        "P05412", 331, 1, 331, 3725, "JUN",
        "JUN_HUMAN (c-Jun) full 331aa transcription factor; "
        "bZIP domain 254-315; transactivation domain 1-224; "
        "Gene: JUN (chr 1p32.1); UniProt P05412"
    ),
    "FKBP12F36V_dTAG": (
        "P62942", 108, 1, 108, 2280, "FKBP1A",
        "FKBP1A_HUMAN 108aa + F36V point mutation (pos 36: Phe→Val); "
        "Creates FKBP12F36V neomorphic degron for dTAG system; "
        "Gene: FKBP1A (chr 20p13); UniProt P62942"
    ),
    "DHFR_DD_TMPD": (
        "P0ABQ4", 159, 1, 159, 945702, "folA",
        "DYR_ECOLI E.coli DHFR full 159aa + F53L/L83I mutations; "
        "F53L: Phe53→Leu; L83I: Leu83→Ile (destabilizing); "
        "NCBI Gene: 945702 (folA, E.coli K-12); UniProt P0ABQ4"
    ),
    "DAP10_Full": (
        "Q9UBK5", 93, 1, 93, 8847, "HCST",
        "HCST_HUMAN (DAP10) full 93aa; "
        "SP: 1-20; TM: 21-46; cyto: 47-93 (contains YINM YXXM motif at Tyr85); "
        "Gene: HCST (chr 12p13.31); UniProt Q9UBK5"
    ),
    "CD3z_ITAM_2": (
        "P20963", 164, 52, 163, 919, "CD247",
        "CD247_HUMAN (CD3ζ) cyto residues 52-163 (2-ITAM variant, aa 1-111 of cytoplasmic); "
        "Full cytoplasmic: 52-164 contains ITAM1 (Y83/Y94), ITAM2 (Y111/Y123), ITAM3 (Y142/Y153); "
        "Gene: CD247 (chr 1q24.2); UniProt P20963"
    ),
}

print("=== Fixing boundary documentation ===\n")
for eid, (uniprot, full_len, start, end, gene_id, gene_sym, note) in BOUNDARY_DATA.items():
    e = v3.get(eid)
    if not e:
        print(f"  Not found: {eid}"); continue
    
    qa = e.setdefault("qa", {})
    
    # Build boundary string
    if start and end:
        boundary_str = f"Residues {start}-{end} ({end-start+1}aa)"
    else:
        boundary_str = f"Full protein ({full_len}aa)"
    
    # Build gene/protein annotation
    gene_info = ""
    if uniprot:
        gene_info += f"UniProt: {uniprot} ({gene_sym}_HUMAN or _ECOLI)  |  "
    if gene_id:
        gene_info += f"NCBI Gene: {gene_id} ({gene_sym})  |  "
    if start and end:
        gene_info += f"Range: aa {start}-{end}  |  "
    gene_info += f"Full protein: {full_len}aa"
    
    # Update source with boundary info
    old_src = qa.get("source","")
    if boundary_str not in old_src:
        qa["source"] = f"[Boundary: {boundary_str}]  [Gene: {gene_sym}, {gene_id or 'synthetic'}]  " + old_src
    
    # Add structured gene_annotation field
    e["gene_annotation"] = {
        "uniprot_id": uniprot or "synthetic",
        "ncbi_gene_id": gene_id,
        "gene_symbol": gene_sym,
        "full_length_aa": full_len,
        "used_residues_start": start,
        "used_residues_end": end,
        "used_length_aa": (end-start+1) if (start and end) else full_len,
        "boundary_note": note
    }
    
    print(f"  ✓ {eid}:")
    print(f"    Gene: {gene_sym} ({uniprot or 'synthetic'}) | NCBI Gene: {gene_id}")
    if start and end:
        print(f"    Boundary: aa {start}-{end} ({end-start+1}aa) of full {full_len}aa")
    else:
        print(f"    Full protein: {full_len}aa")

# Also add gene_annotation to key elements that already have boundaries but lack structured field
KEY_ELEMENTS = {
    "CD3z_signaling": ("P20963", 164, 52, 164, 919, "CD247", "CD3ζ cyto ITAM domain"),
    "4-1BB_cyto": ("Q07011", 255, 214, 255, 3604, "TNFRSF9", "4-1BB cytoplasmic 214-255"),
    "CD28_cyto": ("P10747", 220, 180, 220, 940, "CD28", "CD28 cytoplasmic 180-220"),
    "OX40_cyto": ("P23510", 277, 238, 277, 7293, "TNFRSF4", "OX40/CD134 cytoplasmic 238-277"),
    "CD28_TM": ("P10747", 220, 153, 179, 940, "CD28", "CD28 transmembrane domain 153-179"),
    "CD8a_TM": ("P01732", 235, 183, 206, 925, "CD8A", "CD8α transmembrane 183-206"),
    "CD8a_Short": ("P01732", 235, 135, 179, 925, "CD8A", "CD8α hinge (short) 135-179"),
    "CD8a_Long": ("P01732", 235, 118, 238, 925, "CD8A", "CD8α hinge extended 118-238"),
    "CD28_Medium": ("P10747", 220, 114, 152, 940, "CD28", "CD28 hinge+stalk 114-152"),
    "CD8a_SP": ("P01732", 235, 1, 21, 925, "CD8A", "CD8α signal peptide 1-21"),
    "GM-CSF_SP": ("P04141", 144, 1, 17, 1437, "CSF2", "GM-CSF signal peptide 1-17"),
    "iCasp9": ("Q14790", 479, 1, 479, 841, "CASP9", "iCasp9: FKBP12-Caspase9 fusion; Casp9 res 1-479"),
    "tEGFR": ("P00533", 1210, 1, 659, 1956, "EGFR", "tEGFR ECD+TM (no kinase)"),
    "NKG2D_ECD_TM": ("P26718", 216, 1, 216, 22914, "KLRK1", "NKG2D full ECD+TM 1-216"),
}

print("\n=== Adding gene_annotation to key elements ===\n")
for eid, (uniprot, full_len, start, end, gene_id, gene_sym, note) in KEY_ELEMENTS.items():
    e = v3.get(eid)
    if not e or "gene_annotation" in e: continue
    e["gene_annotation"] = {
        "uniprot_id": uniprot,
        "ncbi_gene_id": gene_id,
        "gene_symbol": gene_sym,
        "full_length_aa": full_len,
        "used_residues_start": start,
        "used_residues_end": end,
        "used_length_aa": end-start+1,
        "boundary_note": note
    }
    print(f"  + {eid}: {gene_sym} aa{start}-{end}")

# Count total gene annotations
total_with_annotation = sum(1 for e in lib["elements"] if "gene_annotation" in e)
print(f"\n  Total elements with gene_annotation: {total_with_annotation}/{len(lib['elements'])}")

lib["metadata"]["last_updated"] = "2026-04-01"
with open(V3_PATH, "w", encoding="utf-8") as f:
    json.dump(lib, f, ensure_ascii=False, indent=2)
print(f"  Saved. Size: {V3_PATH.stat().st_size//1024} KB")
