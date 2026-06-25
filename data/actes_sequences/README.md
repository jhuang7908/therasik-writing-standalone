# ACTES  A 

 ACTES  A ****， **≥2 **（UniProt + NCBI RefSeq）。

## 

| / |  |
| :--- | :--- |
| **config.json** | （UniProt ID、、） |
| **sequence_db.json** | ： `sources`、`alignment`、`status`、`canonical_sequence`、`sequence_sha256_16` |
| **ACTES_sequences_canonical.fasta** | ****； A  |
| **ACTES_promoters.fasta** | ** DNA/**（EF1a、NFAT_Response、WPRE ）； sequence_db  `type: "dna"`  |
| **ACTES_sequences_index.md** |  ↔ entry_id  |
| **ACTES_INTEGRATION_AND_SUBMISSION.md** | （、、） |
| **sources/** |  FASTA（`{entry_id}_UniProt.fasta`、`{entry_id}_RefSeq.fasta`） |
| **alignments/** | （`{entry_id}_alignment.txt`）， |

## 

- **ACTES_sequences_canonical.fasta** ****； DNA， DNA 。
- **DNA/**（EF1a、SFFV、NFAT_Response、WPRE ） `sequence_db.json`  `"type": "dna"`， **ACTES_promoters.fasta**。
- ****： NFAT_Response  4× NFAT （ 116 bp），****，；SynNotch_RAM  Pro 。（ CAR-T_NK ）（/），。

## 

- **verified**：UniProt  RefSeq  ≥ 99%
- **mismatch_review**：，（/）
- **single_source**： UniProt（ RefSeq  NCBI ）
- **static_single_source**：（ FLAG_Tag、GGSG3），

## 

```bash
# 
python scripts/actes_fetch_sequences.py --out data/actes_sequences

#  UniProt（ NCBI，）
python scripts/actes_fetch_sequences.py --no-ncbi
```

：`requests`； `biopython` 。

## （/）

、WPRE  DNA ，**、**。：

```bash
# URL ，
python scripts/actes_fetch_double_verify.py --url "https://..." --out data/actes_sequences/promoters/EF1A.txt

#  FASTA 
python scripts/actes_fetch_double_verify.py --file path/to/EF1A.fasta --out data/actes_sequences/promoters/EF1A_verified.fasta

# 
python scripts/actes_fetch_double_verify.py --url "https://..." --dry-run
```

 `scripts/actes_fetch_double_verify.py`。VectorBuilder [Promoters](https://en.vectorbuilder.com/resources/vector-component/promoter.html)  **Details  “View”  DNA **； Addgene/GenBank 。（ URL ，）。

## 

-  `entry_id`  ** A.15 **  ** A** 。
- “” UniProt ， `config.json`；/scFv、，。
