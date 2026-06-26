from pathlib import Path
from typing import Dict, List
import json
import re


# ===  ===
#  antibody_engineering/scripts ，parents[1]  antibody_engineering

PROJECT_ROOT = Path(__file__).resolve().parents[1]

# core/data （ IMGT ）
CORE_DATA_ROOT = PROJECT_ROOT / "core" / "data"

#  JSON
HUMAN_JSON = CORE_DATA_ROOT / "human_VH3_germlines.json"
CAMELID_JSON = CORE_DATA_ROOT / "vhh_camelid_reference.json"


def load_fasta(path: Path) -> Dict[str, str]:
    seqs: Dict[str, str] = {}
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
    if any(k in h for k in ["lama", "alpaca", "camelus", "dromedary", "camel"]):
        return "camelid"
    return "other"


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


def scan_core_data_fasta() -> List[Path]:
    fasta_files: List[Path] = []
    for ext in ("*.fasta", "*.fa", "*.faa", "*.fas"):
        fasta_files.extend(CORE_DATA_ROOT.rglob(ext))

    print(f"[SCAN]  {CORE_DATA_ROOT}  {len(fasta_files)}  FASTA ")
    if not fasta_files:
        print("[WARN]  FASTA， core/data  IMGT ")
    return fasta_files


def build_human_vh3_entries(fasta_files: List[Path]) -> List[dict]:
    """
     human FASTA  IGHV3-*  germline， human_VH3_germlines.json
    """
    entries: List[dict] = []
    seen_ids = set()

    print("\n[HUMAN]  human_VH3_germlines entries ...")

    for f in fasta_files:
        seqs = load_fasta(f)
        for header, seq in seqs.items():
            sp = guess_species(header)
            if sp != "human":
                continue

            gene_full = extract_ighv_name(header)
            if not gene_full:
                continue

            #  IGHV3-* family
            if not gene_full.startswith("IGHV3-"):
                continue

            gid = f"HUMAN_{gene_full}"
            if gid in seen_ids:
                continue
            seen_ids.add(gid)

            if "*" in gene_full:
                gene, allele = gene_full.split("*", 1)
                allele = "*" + allele
            else:
                gene = gene_full
                allele = ""

            entry = {
                "id": gid,
                "species": "human",
                "locus": "IGHV",
                "gene": gene,
                "allele": allele,
                "sequence_aa": seq,
                "source": "core/data IMGT FASTA",
                "raw_header": header,
                "notes": "VH3 family germline (auto-collected)",
            }
            entries.append(entry)

    print(f"[HUMAN]  {len(entries)}  IGHV3-* germline")
    return entries


def build_camelid_vhh_entries(fasta_files: List[Path]) -> List[dict]:
    """
     camelid FASTA  IGHV germline， vhh_camelid_reference.json

    ： camelid + IGHV* ，
     gene  VHH 。
    """
    entries: List[dict] = []
    seen_ids = set()

    print("\n[CAMELID]  vhh_camelid_reference entries ...")

    for f in fasta_files:
        seqs = load_fasta(f)
        for header, seq in seqs.items():
            sp = guess_species(header)
            if sp != "camelid":
                continue

            gene_full = extract_ighv_name(header)
            if not gene_full:
                #  VHH ，
                if "vhh" in header.lower():
                    print(f"[CAMELID][INFO]  VHH header  IGHV ：{header}")
                continue

            gid = f"CAMELID_{gene_full}"
            if gid in seen_ids:
                continue
            seen_ids.add(gid)

            if "*" in gene_full:
                gene, allele = gene_full.split("*", 1)
                allele = "*" + allele
            else:
                gene = gene_full
                allele = ""

            entry = {
                "id": gid,
                "species": "camelid",
                "locus": "IGHV",
                "gene": gene,
                "allele": allele,
                "sequence_aa": seq,
                "source": "core/data IMGT FASTA",
                "raw_header": header,
                "notes": "camelid IGHV germline (candidate VHH scaffolds)",
            }
            entries.append(entry)

    print(f"[CAMELID]  {len(entries)}  camelid IGHV germline")
    return entries


def upgrade_human_vh3_json(entries: List[dict]) -> None:
    if not entries:
        print("[HUMAN]  human IGHV3-*，human_VH3_germlines.json ")
        return

    data = {
        "library_name": "human_VH3_germlines",
        "version": "from-core-data-mvp1",
        "entries": entries,
    }
    HUMAN_JSON.write_text(json.dumps(data, indent=2, ensure_ascii=False), encoding="utf-8")
    print(f"[HUMAN]  {HUMAN_JSON}")


def upgrade_camelid_json(entries: List[dict]) -> None:
    if not entries:
        print("[CAMELID]  camelid IGHV，vhh_camelid_reference.json ")
        return

    data = {
        "library_name": "vhh_camelid_reference",
        "version": "from-core-data-mvp1",
        "entries": entries,
    }
    CAMELID_JSON.write_text(json.dumps(data, indent=2, ensure_ascii=False), encoding="utf-8")
    print(f"[CAMELID]  {CAMELID_JSON}")


if __name__ == "__main__":
    print(f"[INFO] : {PROJECT_ROOT}")
    print(f"[INFO] core/data : {CORE_DATA_ROOT}")

    fasta_files = scan_core_data_fasta()
    if not fasta_files:
        raise SystemExit(1)

    human_entries = build_human_vh3_entries(fasta_files)
    camelid_entries = build_camelid_vhh_entries(fasta_files)

    OUT_DIR = CORE_DATA_ROOT
    OUT_DIR.mkdir(parents=True, exist_ok=True)

    upgrade_human_vh3_json(human_entries)
    upgrade_camelid_json(camelid_entries)

    print("\n[DONE] human_VH3_germlines.json & vhh_camelid_reference.json （）。")




















