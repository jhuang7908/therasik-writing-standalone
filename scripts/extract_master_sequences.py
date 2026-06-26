import json
import pandas as pd
from pathlib import Path
import sys

# Add root to sys.path
ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

def extract_sequences():
    # 1. VHH68 + Porustobart
    vhh68_index_path = ROOT / "data/vhh_structural_union/vhh_structural_union_index.json"
    vhh68_data = json.loads(vhh68_index_path.read_text(encoding="utf-8"))
    
    sequences = []
    # Clinical VHH
    for entry in vhh68_data.get("clinical_vhh", []):
        sequences.append({
            "id": entry["id"],
            "sequence": entry["sequence"],
            "pdb_path": str(ROOT / entry["pdb_model"]) if entry.get("pdb_model") else None,
            "category": "Clinical_VHH",
            "source": "VHH68"
        })
        if entry["id"] == "Porustobart":
            sequences[-1]["category"] = "Transgenic_sdAb"

    # Database B
    for entry in vhh68_data.get("database_b", []):
        sequences.append({
            "id": entry["id"],
            "sequence": entry["sequence"],
            "pdb_path": str(ROOT / entry["pdb_model"]) if entry.get("pdb_model") else None,
            "category": "Database_B",
            "source": "VHH68"
        })

    # 2. Atlas-24
    atlas_path = ROOT / "data/vhh_design_atlas_v3.json"
    atlas_data = json.loads(atlas_path.read_text(encoding="utf-8"))
    
    eng_vh_count = 0
    for entry in atlas_data:
        if entry.get("category") == "Engineered_Human_VH":
            name = entry["name"].split(" / ")[0]
            pdb_id = entry.get("pdb_id")
            pdb_path = None
            if pdb_id:
                potential_paths = [
                    ROOT / f"data/vhh_clinical_39_union/immunebuilder_models/{name}/rank0_unrefined.pdb",
                    ROOT / f"data/vhh_clinical_39_union/immunebuilder_models/{pdb_id}/rank0_unrefined.pdb"
                ]
                for p in potential_paths:
                    if p.exists():
                        pdb_path = str(p)
                        break
            
            sequences.append({
                "id": name,
                "sequence": entry["sequence"],
                "pdb_path": pdb_path,
                "category": "Engineered_Human_VH",
                "source": "Atlas-24"
            })
            eng_vh_count += 1
            if eng_vh_count >= 24:
                break

    # 3. Negative Control VH (Regular IgG VH)
    # Adding clinical IgG VH sequences from console demos + well knowns
    neg_controls = [
        {"id": "Adalimumab_VH", "sequence": "EVQLVESGGGLVQPGRSLRLSCAASGFTFDDYAMHWVRQAPGKGLEWVSAITWNSGHIDYADSVEGRFTISRDNAKNSLYLQMNSLRAEDTAVYYCAKVSYLSTASSLDYWGQGTLVTVSS"},
        {"id": "Trastuzumab_VH", "sequence": "EVQLVESGGGLVQPGGSLRLSCAASGFNIKDTYIHWVRQAPGKGLEWVARIYPTNGYTRYADSVKGRFTISADTSKNTAYLQMNSLRAEDTAVYYCSRWGGDGFYAMDYWGQGTLVTVSS"},
        {"id": "Pembrolizumab_VH", "sequence": "QVQLVQSGVEVKKPGASVKVSCKASGYTFTNYYMYWVRQAPGQGLEWMGGINPSNGGTNFNEKFKNRVTLTTDSSTTTAYMELKSLQFDDTAVYYCARRDYRFDMGFDYWGQGTTVTVSS"},
        {"id": "Nivolumab_VH", "sequence": "QVQLVESGGGVVQPGRSLRLDCKASGITFSNSGMHWVRQAPGKGLEWVAVIWYDGSKRYYADSVKGRFTISRDNSKNTLFLQMNSLRAEDTAVYYCATNDDYWGQGTLVTVSS"},
        {"id": "Rituximab_VH", "sequence": "QVQLQQPGAELVKPGASVKMSCKASGYTFTSYNMHWVKQTPGRGLEWIGAIYPGNGDTSYNQKFKGKATLTADKSSSTAYMQLSSLTSEDSAVYYCARSTYYGGDWYFNVWGAGTTVTVSA"},
        {"id": "Tislelizumab_VH", "sequence": "QVQLQESGPGLVKPSETLSLTCTVSGFSLTSYGVHWIRQPPGKGLEWIGVIYADGSTNYNPSLKSRVTISKDTSKNQVSLKLSSVTAADTAVYYCARAYGNYWYIDVWGQGTTVTVSS"},
        {"id": "Toripalimab_VH", "sequence": "QGQLVQSGAEVKKPGASVKVSCKASGYTFTDYEMHWVRQAPIHGLEWIGVIESETGGTAYNQKFKGRVTITADKSTSTAYMELSSLRSEDTAVYYCAREGITTVATTYYWYFDVWGQGTTVTVSS"},
        {"id": "Camrelizumab_VH", "sequence": "EVQLVESGGGLVQPGGSLRLSCAASGFTFSSYMMSWVRQAPGKGLEWVASISSSGGSTYYADSVKGRFTISRDNSKNTLYLQMNSLRAEDTAVYYCARVEGYGNSNGMDVWGQGTMVTVSS"},
        {"id": "Mumab4d5_VH", "sequence": "EVQLVQSGAEVKKPGASVKVSCKASGYTFTSYNMHWVRQAPGQGLEWMGIINPSGGSTSYAQKFQGRVTMTRDTSTSTVYMELSSLRSEDTAVYYCARDQGSIRGFDYWGQGTLVTVSS"},
        {"id": "IGHV3-23_Germline", "sequence": "EVQLVESGGGLVQPGGSLRLSCAASGFTFSSYAMSWVRQAPGKGLEWVSAISGSGGSTYYADSVKGRFTISRDNAKNSLYLQMNSLRAEDTAVYYCAK"},
    ]
    for nc in neg_controls:
        sequences.append({
            "id": nc["id"],
            "sequence": nc["sequence"],
            "pdb_path": None,
            "category": "Negative_Control_VH",
            "source": "Clinical_IgG_or_Germline"
        })
                
    return sequences

if __name__ == "__main__":
    seqs = extract_sequences()
    print(f"Extracted {len(seqs)} sequences.")
    df = pd.DataFrame(seqs)
    df.to_csv(ROOT / "data/vhh_master_seq_list.csv", index=False)
    print("Saved to data/vhh_master_seq_list.csv")
