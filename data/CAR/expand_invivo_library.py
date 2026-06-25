import json

def expand_invivo_module(file_path):
    with open(file_path, 'r', encoding='utf-8') as f:
        data = json.load(f)

    new_elements = [
        {
            "id": "HBA1_3UTR",
            "name": "Human Alpha-globin 3' UTR (mRNA Stability)",
            "category": "In-Vivo CAR Module",
            "subcategory": "mRNA Stability Element",
            "sequence": "CCCGGCCAGGCAATCCGTCCAGGAGCCCCAGAGCCCTCCCTCCATCTACTTCTCCCTCCAAACCCCAACACCCTTTGGTTCCAATTTCTCTCTTAG",
            "length": 96,
            "type": "DNA/RNA",
            "regulatory_tier": "T1",
            "design_notes": "Canonical 3' UTR from human HBA1 gene. Used in mRNA-CAR constructs (e.g. Rurik 2022) to significantly increase transcript half-life and translation efficiency in T cells."
        },
        {
            "id": "HBB_3UTR",
            "name": "Human Beta-globin 3' UTR (mRNA Stability)",
            "category": "In-Vivo CAR Module",
            "subcategory": "mRNA Stability Element",
            "sequence": "GCTCGCTTTCTTGCTGTCCAATTTCTATTAAAGGTTCCTTTGTTCCCTAAGTCCAACTACTAAACTGGGGGATATTATGAAGGGCCTTGAGCATCTGGATTCTGCCTAATAAAAAACATTTATTTTCATTGC",
            "length": 132,
            "type": "DNA/RNA",
            "regulatory_tier": "T1",
            "design_notes": "Canonical 3' UTR from human HBB gene. Enhances mRNA stability and prevents deadenylation-dependent decay."
        },
        {
            "id": "OKT8_hu_scFv",
            "name": "Humanized Anti-CD8 scFv (Targeting Ligand)",
            "category": "In-Vivo CAR Module",
            "subcategory": "LNP/mRNA Targeting Ligand",
            "sequence": "QVQLQQSGPELVKPGASVKISCKASGYTFTDYNMHWVKQSHGKSLEWIGYIYPYNGGTGYNQKFKSKATLTVDNSSSTAYMELRSLTSEDSAVYYCARSRGYDYYGMDYWGQGTSVTVSSGGGGSGGGGSGGGGSDIQMTQSPSSLSASVGDRVTITCRASQSISRYLNWYQQKPGKAPKLLIYAASTLQSGVPSRFSGSGSGTDFTLTISSLQPEDFATYYCQQSNYPLTFGAGTKLEIK",
            "length": 248,
            "type": "AA",
            "regulatory_tier": "T2",
            "design_notes": "Humanized version of OKT8. Used as a surface targeting ligand on LNPs to selectively deliver mRNA payloads to Cytotoxic T Cells (CD8+)."
        },
        {
            "id": "Anti_CD4_scFv_Targeting",
            "name": "Anti-CD4 scFv (Helper T Cell Targeting)",
            "category": "In-Vivo CAR Module",
            "subcategory": "LNP/mRNA Targeting Ligand",
            "sequence": "QVQLQQSGAELVRPGTSVKVSCKASGYTFTNYWLGWVKQRPGHGLEWIGDIYPGGGYTNYNEKFKGKATLTADTSSSTAYMQLSSLTSEDSAVYFCASGNYDYFDYWGQGTTLTVSSGGGGSGGGGSGGGGSDIQMTQSPSSLSASVGDRVTITCRASQGISSWLAWYQQKPEKAPKSLIYAASSLQSGVPSRFSGSGSGTDFTLTISSLQPEDFATYYCQQYFSYPWTFGGGTKVEIK",
            "length": 242,
            "type": "AA",
            "regulatory_tier": "T2",
            "design_notes": "scFv targeting CD4. Enables selective in-vivo reprogramming of Helper T cells."
        },
        {
            "id": "AES_3UTR_Synthetic",
            "name": "Artificial Element for Stability (AES) 3' UTR",
            "category": "In-Vivo CAR Module",
            "subcategory": "mRNA Stability Element",
            "sequence": "TTTCTATTAAAGGTTCCTTTGTTCCCTAAGTCCAACTACTAAACTGGGGGATATTATGAAGGGCCTTGAGCATCTGGATTCTGCCTAATAAAAAACATTTATTTTCATTGCAAAGAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAA",
            "length": 175,
            "type": "DNA/RNA",
            "regulatory_tier": "T3",
            "design_notes": "Synthetic 3' UTR optimized for maximum translation in hematopoietic lineages. Includes a pre-templated Poly(A) tail of 60nt."
        },
        {
            "id": "SFFV_Promoter_mRNA",
            "name": "SFFV Promoter (mRNA Construct Version)",
            "category": "In-Vivo CAR Module",
            "subcategory": "Expression Control",
            "sequence": "GATGCTGCCGCCTTTTTCCCGAGGGTGGGGGAGAACCGTATATAAGTGCAGTAGTCGCCGTGAACGTTCTTTTTCGCAACGGGTTTGCCGCCAGAACACAGGTAAGTGCCGTGTGTGGTTCCCGCGGGCCTGGCCTCTTTACGGGTTATGGCCCTTGCGTGCCTTGAATTACTTCCACCTGGCTGCAGTACGTGATTCTTGATCCCGAGCTTCGGGTTGGAAGTGGGTGGGAGAGTTCGAGGCCTTGCG",
            "length": 250,
            "type": "DNA",
            "regulatory_tier": "T1",
            "design_notes": "Spleen Focus-Forming Virus (SFFV) U3 region promoter. Highly active in primary human T cells. Preferred for in-vivo DNA-based constructs or used as template for mRNA IVT."
        }
    ]

    added_count = 0
    for elem in new_elements:
        if not any(e['id'] == elem['id'] for e in data['elements']):
            data['elements'].append(elem)
            added_count += 1
    
    data['metadata']['total_elements'] = len(data['elements'])
    data['metadata']['last_updated'] = "2026-04-26"

    with open(file_path, 'w', encoding='utf-8') as f:
        json.dump(data, f, indent=2, ensure_ascii=False)
    
    print(f"Successfully added {added_count} in-vivo specific elements. Total library count: {len(data['elements'])}")

expand_invivo_module('CART_LIBRARY_V3.json')
