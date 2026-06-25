"""
CAR
UniProt API，CAR。

:
    python fetch_verified_sequences.py

 https://rest.uniprot.org
"""

import json
import time
import sys
from urllib import request, error

UNIPROT_REST = "https://rest.uniprot.org/uniprotkb/{acc}.fasta"

# CARUniProt (accession, start, end, description)
# 1-indexed residues，UniProt
ELEMENT_DEFINITIONS = [
    # ───  ───────────────────────────────────────────────
    {
        "id": "CD8a_SP",
        "name": "CD8α",
        "category": "Signal Peptide",
        "uniprot": "P01732",
        "res_start": 2,
        "res_end": 21,
        "note": "CD8A_HUMAN ，CAR-T",
    },
    {
        "id": "GM-CSF_SP",
        "name": "GM-CSF",
        "category": "Signal Peptide",
        "uniprot": "P04141",
        "res_start": 1,
        "res_end": 17,
        "note": "CSF2_HUMAN ",
    },
    # ───  (Hinge) ──────────────────────────────────────
    {
        "id": "CD8a_Short",
        "name": "CD8α Short Hinge (45 aa)",
        "category": "Hinge",
        "uniprot": "P01732",
        "res_start": 138,
        "res_end": 182,
        "note": "CD8A_HUMAN stalk-only ",
    },
    {
        "id": "CD8a_Long",
        "name": "CD8α Long Hinge (119 aa)",
        "category": "Hinge",
        "uniprot": "P01732",
        "res_start": 90,
        "res_end": 210,
        "note": "CD8A_HUMAN （stalk）",
    },
    {
        "id": "CD28_Medium",
        "name": "CD28 Medium Hinge (39 aa)",
        "category": "Hinge",
        "uniprot": "P10747",
        "res_start": 114,
        "res_end": 152,
        "note": "CD28_HUMAN stalk",
    },
    # ───  (Transmembrane Domain) ──────────────────────
    {
        "id": "CD8a_TM",
        "name": "CD8α (24 aa)",
        "category": "Transmembrane Domain",
        "uniprot": "P01732",
        "res_start": 183,
        "res_end": 206,
        "note": "CD8A_HUMAN TM，",
    },
    {
        "id": "CD28_TM",
        "name": "CD28 (27 aa)",
        "category": "Transmembrane Domain",
        "uniprot": "P10747",
        "res_start": 153,
        "res_end": 179,
        "note": "CD28_HUMAN TM，，",
    },
    {
        "id": "CD4_TM",
        "name": "CD4 (22 aa)",
        "category": "Transmembrane Domain",
        "uniprot": "P01730",
        "res_start": 397,
        "res_end": 418,
        "note": "CD4_HUMAN TM，CAR-NK",
    },
    {
        "id": "CD3z_TM",
        "name": "CD3ζ",
        "category": "Transmembrane Domain",
        "uniprot": "P20963",
        "res_start": 22,
        "res_end": 51,
        "note": "CD247_HUMAN TM（CAR，CD8a/CD28 TM）",
    },
    # ───  (Intracellular Signaling) ───────────────
    {
        "id": "CD3z_cyto",
        "name": "CD3ζ — 3×ITAM  (113 aa)",
        "category": "Signaling Domain",
        "uniprot": "P20963",
        "res_start": 52,
        "res_end": 164,
        "note": "CD247_HUMAN ，3ITAM，CAR",
    },
    {
        "id": "4-1BB_cyto",
        "name": "4-1BB (42 aa)",
        "category": "Costimulatory Domain",
        "uniprot": "Q07011",
        "res_start": 214,
        "res_end": 255,
        "note": "TNFR9_HUMAN (CD137/4-1BB) ，TRAF，T",
    },
    {
        "id": "CD28_cyto",
        "name": "CD28 (41 aa)",
        "category": "Costimulatory Domain",
        "uniprot": "P10747",
        "res_start": 180,
        "res_end": 220,
        "note": "CD28_HUMAN ，PI3K/Akt，",
    },
    {
        "id": "OX40_cyto",
        "name": "OX40 (40 aa)",
        "category": "Costimulatory Domain",
        "uniprot": "P43489",
        "res_start": 238,
        "res_end": 277,
        "note": "TNR4_HUMAN (CD134/OX40) ，TRAF，",
    },
    {
        "id": "ICOS_cyto",
        "name": "ICOS (37 aa)",
        "category": "Costimulatory Domain",
        "uniprot": "Q9Y6W8",
        "res_start": 163,
        "res_end": 199,
        "note": "ICOS_HUMAN ，YMFM motif，Th17/Tfh",
    },
    {
        "id": "CAR-NK_2B4_cyto",
        "name": "2B4 (135 aa，CAR-NK)",
        "category": "Costimulatory Domain",
        "uniprot": "Q9BZW8",
        "res_start": 246,
        "res_end": 380,
        "note": "CD244_HUMAN (2B4) ，NK",
    },
    # ─── tEGFR ─────────────────────────
    {
        "id": "tEGFR_SP_DomIII_DomIV_TM",
        "name": "tEGFR (EGFR, ~335 aa)",
        "category": "Safety Switch",
        "uniprot": "P00533",
        "res_start": 1,
        "res_end": 668,
        "note": "EGFR_HUMAN：(1-24)+DomIII(334-504)+DomIV(505-645)+TM(646-668)，DomI/II(25-333)(669-1210). 1-668，.",
        "special_assembly": {
            "segments": [
                {"desc": "", "start": 1, "end": 24},
                {"desc": "Domain III", "start": 334, "end": 504},
                {"desc": "Domain IV", "start": 505, "end": 645},
                {"desc": "Transmembrane", "start": 646, "end": 668},
            ],
            "reference": "Wang X et al. Blood 2011;118(5):1255-63",
        },
    },
]

# （UniProt）
SYNTHETIC_SEQUENCES = [
    {
        "id": "G4S3",
        "name": "(G₄S)₃ Linker",
        "category": "Linker",
        "sequence": "GGGGSGGGGSGGGGS",
        "length": 15,
        "source": "，Huston JS et al. PNAS 1988;85:5879",
    },
    {
        "id": "G4S4",
        "name": "(G₄S)₄ Linker",
        "category": "Linker",
        "sequence": "GGGGSGGGGSGGGGSGGGGS",
        "length": 20,
        "source": "",
    },
    {
        "id": "G4S5",
        "name": "(G₄S)₅ Linker",
        "category": "Linker",
        "sequence": "GGGGSGGGGSGGGGSGGGGSGGGGS",
        "length": 25,
        "source": "",
    },
    {
        "id": "P2A",
        "name": "P2A (Thosea asigna)",
        "category": "Linker",
        "sequence": "GSGATNFSLLKQCGDVEENPGP",
        "length": 22,
        "source": "Kim JH et al. PLoS ONE 2011;6(4):e18556",
        "note": "，>99%",
    },
    {
        "id": "T2A",
        "name": "T2A (B)",
        "category": "Linker",
        "sequence": "EGRGSLLTCGDVEENPGP",
        "length": 18,
        "source": "Kim JH et al. PLoS ONE 2011",
    },
    {
        "id": "E2A",
        "name": "E2A (A)",
        "category": "Linker",
        "sequence": "QCTNYALLKLAGDVESNPGP",
        "length": 20,
        "source": "Kim JH et al. PLoS ONE 2011",
    },
    {
        "id": "F2A",
        "name": "F2A ",
        "category": "Linker",
        "sequence": "VKQTLNFDLLKLAGDVESNPGP",
        "length": 22,
        "source": "Kim JH et al. PLoS ONE 2011",
    },
    {
        "id": "FMC63_scFv",
        "name": "FMC63 scFv (CD19, 243 aa)",
        "category": "Binder",
        "target": "CD19",
        "sequence": "EVQLVESGGGLVQPGGSLRLSCAASGYTFTSYWMHWVRQAPGKGLEWIGEINPGSGGTNYNEKFKSKATLTVDKSSSTAYMQLSSLTSEDSAVYYCARSTYYGGDWYFNVWGAGTTVTVSSGGGGSGGGGSGGGGSDIQMTQSPSSLSASVGDRVTITCRASQDVSTAVAWYQQKPGKAPKLLIYSASFLYSGVPSRFSGSGSGTDFTLTISSLQPEDFATYYCQQHYTTPPTFGQGTKVEIK",
        "length": 243,
        "source": "Nicholson IC et al. Mol Immunol 1997;34:1157-65; Kymriah BLA",
        "cdrs": {
            "VH_CDR1": "GYTFTSYWMH",
            "VH_CDR2": "EINPGSGGTNYNEKFKS",
            "VH_CDR3": "STYYGGDWYFNV",
            "VL_CDR1": "RASQDVSTAVA",
            "VL_CDR2": "SASFLYS",
            "VL_CDR3": "QQHYTTPPT",
        },
        "note": "（Addgene #119010）",
    },
    {
        "id": "GM-CSF_SP",
        "name": "GM-CSF (17 aa)",
        "category": "Signal Peptide",
        "sequence": "MWLQSLLLLGTVACSIS",
        "length": 17,
        "source": "UniProt P04141 (CSF2_HUMAN) ",
    },
    {
        "id": "IgK_SP",
        "name": "IgKappa (21 aa)",
        "category": "Signal Peptide",
        "sequence": "METDTLLLWVLLLWVPGSTGD",
        "length": 21,
        "source": "UniProt P01834 (IGKC_HUMAN) ",
    },
]


def fetch_uniprot_fasta(accession: str) -> str | None:
    """UniProt REST APIFASTA"""
    url = UNIPROT_REST.format(acc=accession)
    try:
        with request.urlopen(url, timeout=15) as resp:
            fasta = resp.read.decode("utf-8")
        return fasta
    except error.URLError as e:
        print(f"  [ERROR]  {accession} : {e}")
        return None


def parse_fasta_seq(fasta: str) -> str:
    """FASTA"""
    lines = fasta.strip.splitlines
    return "".join(ln.strip for ln in lines if not ln.startswith(">"))


def extract_segment(full_seq: str, start: int, end: int) -> str:
    """1-indexed [start, end] """
    return full_seq[start - 1 : end]


def build_tegfr(full_egfr: str) -> str:
    """
    EGFRtEGFR:
    SP(1-24) + DomainIII(334-504) + DomainIV(505-645) + TM(646-668)
    Wang X et al. Blood 2011
    """
    sp = extract_segment(full_egfr, 1, 24)
    dom3 = extract_segment(full_egfr, 334, 504)
    dom4 = extract_segment(full_egfr, 505, 645)
    tm = extract_segment(full_egfr, 646, 668)
    return sp + dom3 + dom4 + tm


def run:
    results = {
        "metadata": {
            "script": "fetch_verified_sequences.py",
            "generated": "2026-04-01",
            "policy": "UniProt REST API，",
        },
        "uniprot_fetched": [],
        "synthetic": SYNTHETIC_SEQUENCES,
        "errors": [],
    }

    # UniProt
    cache: dict[str, str] = {}

    for elem in ELEMENT_DEFINITIONS:
        acc = elem["uniprot"]
        print(f": {elem['id']} ({acc})")

        if acc not in cache:
            print(f"  →  UniProt {acc}...")
            fasta = fetch_uniprot_fasta(acc)
            if fasta is None:
                results["errors"].append(
                    {"id": elem["id"], "error": f" UniProt {acc}"}
                )
                continue
            full_seq = parse_fasta_seq(fasta)
            cache[acc] = full_seq
            time.sleep(0.3)  # API
        else:
            full_seq = cache[acc]

        #  tEGFR
        if elem["id"] == "tEGFR_SP_DomIII_DomIV_TM":
            segment = build_tegfr(full_seq)
            print(f"  tEGFR: {len(segment)} aa")
        else:
            segment = extract_segment(full_seq, elem["res_start"], elem["res_end"])

        record = {
            "id": elem["id"],
            "name": elem["name"],
            "category": elem["category"],
            "uniprot": acc,
            "residues": f"{elem.get('res_start', 'N/A')}-{elem.get('res_end', 'N/A')}",
            "sequence": segment,
            "length": len(segment),
            "sequence_status": "FETCHED_FROM_UNIPROT",
            "note": elem.get("note", ""),
            "verified": True,
        }
        if "special_assembly" in elem:
            record["assembly"] = elem["special_assembly"]

        results["uniprot_fetched"].append(record)
        print(f"  ✓  {len(segment)} aa")

    # 
    out_path = "CAR_SEQUENCES_FETCHED.json"
    with open(out_path, "w", encoding="utf-8") as f:
        json.dump(results, f, ensure_ascii=False, indent=2)

    print(f"\n===  ===")
    print(f"UniProt: {len(results['uniprot_fetched'])} ")
    print(f": {len(results['synthetic'])} ")
    print(f": {len(results['errors'])} ")
    print(f": {out_path}")
    return results


if __name__ == "__main__":
    run
