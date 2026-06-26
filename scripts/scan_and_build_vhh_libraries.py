from pathlib import Path
from typing import Dict, List
import json
import re


# ===  ===
# 
PROJECT_ROOT = Path(__file__).parent.parent
CORE_DATA_ROOT = PROJECT_ROOT / "data"  # 

# ： data/germline 
OUT_BASE = PROJECT_ROOT / "data" / "germline"
CAMELID_OUT_FASTA = OUT_BASE / "vhh_camelid" / "camelid_vhh_germlines.fasta"
CAMELID_OUT_INDEX = OUT_BASE / "vhh_camelid" / "camelid_vhh_index.json"
HUMAN_OUT_FASTA = OUT_BASE / "human_vhh_compatible" / "human_vhh_compatible.fasta"
HUMAN_OUT_INDEX = OUT_BASE / "human_vhh_compatible" / "human_vhh_compatible_index.json"


def load_fasta(path: Path) -> Dict[str, str]:
    seqs = {}
    header = None
    buf: List[str] = []
    with path.open(encoding="utf-8", errors="ignore") as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            if line.startswith(">"):
                if header is not None:
                    seqs[header] = "".join(buf)
                header = line[1:]
                buf = []
            else:
                buf.append(line)
        if header is not None:
            seqs[header] = "".join(buf)
    return seqs


def guess_species(header: str) -> str:
    h = header.lower()
    if "homo sapiens" in h or "human" in h:
        return "human"
    if "lama" in h or "alpaca" in h or "camelus" in h or "dromedary" in h or "camel" in h:
        return "camelid"
    return "unknown"


def extract_ighv_name(header: str) -> str:
    """
     IMGT  header  IGHV ，:
      IGHV3-23*01
      IGHV1-69*02
     ""。
    """
    m = re.search(r"(IGHV[0-9A-Za-z\-]+[*][0-9A-Za-z]+)", header)
    if not m:
        return ""
    return m.group(1)


def scan_core_data():
    """
     data  fasta/fa ：
    - 
    -  IGHV 
    """
    fasta_files: List[Path] = []
    for ext in ("*.fasta", "*.fa", "*.faa", "*.fas"):
        fasta_files.extend(CORE_DATA_ROOT.rglob(ext))

    print(f"[SCAN]  {CORE_DATA_ROOT}  {len(fasta_files)}  FASTA \n")

    species_count = {}
    human_genes = set()
    camelid_genes = set()

    for f in fasta_files:
        seqs = load_fasta(f)
        print(f"[FILE] {f}  (: {len(seqs)})")

        for h in seqs.keys():
            sp = guess_species(h)
            species_count[sp] = species_count.get(sp, 0) + 1

            gene = extract_ighv_name(h)
            if not gene:
                continue

            if sp == "human":
                human_genes.add(gene)
            elif sp == "camelid":
                camelid_genes.add(gene)

    print("\n===  ===")
    for sp, cnt in species_count.items():
        print(f"  {sp:8s}: {cnt} headers")

    print("\n=== Human IGHV （） ===")
    for g in sorted(human_genes):
        print("  ", g)

    print("\n=== Camelid IGHV/VHH （） ===")
    for g in sorted(camelid_genes):
        print("  ", g)

    return fasta_files, human_genes, camelid_genes


def build_camelid_vhh_library(fasta_files: List[Path], camelid_genes: set):
    """
     FASTA ， camelid IGHV  VHH germline 。
     3~5 ， scan 。
    """
    if not camelid_genes:
        print("[CAMELID]  camelid IGHV， VHH germline ")
        return

    #  scan  gene 
    target_fragments = [
        "IGHV3",   #  VHH  IGHV3 family
    ]

    OUT_BASE.mkdir(parents=True, exist_ok=True)
    (OUT_BASE / "vhh_camelid").mkdir(parents=True, exist_ok=True)

    lines: List[str] = []
    entries: List[dict] = []

    used = set()

    print("\n[CAMELID]  VHH germline  ...")
    for f in fasta_files:
        seqs = load_fasta(f)
        for header, seq in seqs.items():
            sp = guess_species(header)
            if sp != "camelid":
                continue
            gene_full = extract_ighv_name(header)
            if not gene_full:
                continue

            # ，
            if not any(fr in gene_full for fr in target_fragments):
                continue

            gid = f"CAMELID_{gene_full}"
            if gid in used:
                continue
            used.add(gid)

            fasta_header = f"{gid}|source=core_data|raw_header={header}"
            lines.append(f">{fasta_header}")
            lines.append(seq)

            entries.append(
                {
                    "id": gid,
                    "species": "camelid",
                    "gene": gene_full.split("*")[0],
                    "allele": "*" + gene_full.split("*")[1] if "*" in gene_full else "",
                    "note": "VHH-related camelid germline (from core/data IMGT)",
                    "fasta_header": fasta_header,
                    "raw_header": header,
                    "source_file": str(f),
                }
            )

    if not entries:
        print("[CAMELID]  camelid IGHV3， gene ")
        return

    CAMELID_OUT_FASTA.write_text("\n".join(lines) + "\n", encoding="utf-8")
    CAMELID_OUT_INDEX.write_text(
        json.dumps(
            {
                "library_name": "camelid_vhh_germlines",
                "version": "from-core-data-mvp1",
                "entries": entries,
            },
            indent=2,
            ensure_ascii=False,
        ),
        encoding="utf-8",
    )
    print(f"[CAMELID]  VHH germline ：\n  {CAMELID_OUT_FASTA}\n  {CAMELID_OUT_INDEX}")


def build_human_vhh_compatible_library(fasta_files: List[Path], human_genes: set):
    """
     human IGHV  germline：
      IGHV3-23*01, IGHV3-66*01, IGHV3-11*01, IGHV1-69*02
     allele （ *02）， gene 。
    """
    if not human_genes:
        print("[HUMAN]  human IGHV， human germline ")
        return

    desired = {
        "IGHV3-23": ["*01", "*02", "*03"],   # 
        "IGHV3-66": ["*01", "*02"],
        "IGHV3-11": ["*01", "*02"],
        "IGHV1-69": ["*02", "*01", "*09"],
    }

    OUT_BASE.mkdir(parents=True, exist_ok=True)
    (OUT_BASE / "human_vhh_compatible").mkdir(parents=True, exist_ok=True)

    #  scan  gene ， gene  allele
    selected_full_names = []

    for gene_prefix, allele_pref in desired.items():
        #  gene_prefix  IGHV ， IGHV3-23*01, IGHV3-23*02
        candidates = [g for g in human_genes if g.startswith(gene_prefix)]
        if not candidates:
            print(f"[HUMAN] ： human_genes  {gene_prefix}，")
            continue

        #  allele 
        chosen = None
        for allele in allele_pref:
            full = f"{gene_prefix}{allele}"
            if full in candidates:
                chosen = full
                break
        if chosen is None:
            #  allele，
            chosen = sorted(candidates)[0]

        selected_full_names.append(chosen)

    print("\n[HUMAN]  VHH-compatible human IGHV：")
    for n in selected_full_names:
        print("  ", n)

    lines: List[str] = []
    entries: List[dict] = []
    used = set()

    for f in fasta_files:
        seqs = load_fasta(f)
        for header, seq in seqs.items():
            sp = guess_species(header)
            if sp != "human":
                continue
            gene_full = extract_ighv_name(header)
            if not gene_full:
                continue
            if gene_full not in selected_full_names:
                continue

            gid = f"HUMAN_{gene_full}"
            if gid in used:
                continue
            used.add(gid)

            fasta_header = f"{gid}|source=core_data|raw_header={header}"
            lines.append(f">{fasta_header}")
            lines.append(seq)

            gene, allele = gene_full.split("*")
            entries.append(
                {
                    "id": gid,
                    "species": "human",
                    "gene": gene,
                    "allele": "*" + allele,
                    "note": "VHH-compatible human germline (from core/data IMGT)",
                    "fasta_header": fasta_header,
                    "raw_header": header,
                    "source_file": str(f),
                }
            )

    if not entries:
        print("[HUMAN]  desired human IGHV， gene ")
        return

    HUMAN_OUT_FASTA.write_text("\n".join(lines) + "\n", encoding="utf-8")
    HUMAN_OUT_INDEX.write_text(
        json.dumps(
            {
                "library_name": "human_vhh_compatible",
                "version": "from-core-data-mvp1",
                "entries": entries,
            },
            indent=2,
            ensure_ascii=False,
        ),
        encoding="utf-8",
    )
    print(f"[HUMAN]  human VHH-compatible germline ：\n  {HUMAN_OUT_FASTA}\n  {HUMAN_OUT_INDEX}")


if __name__ == "__main__":
    print(f"[INFO] : {CORE_DATA_ROOT}")
    fasta_files, human_genes, camelid_genes = scan_core_data()

    OUT_BASE.mkdir(parents=True, exist_ok=True)

    build_camelid_vhh_library(fasta_files, camelid_genes)
    build_human_vhh_compatible_library(fasta_files, human_genes)

    print("\n[DONE]  + 。")




















