# Sequence DB — design_info 

**QA 、**： **[SEQUENCE_QA_AND_APPLICATION.md](SEQUENCE_QA_AND_APPLICATION.md)**（： QA、、）。

## 1. 

- ****：UniProt/。
- ****： `design_info`，、、。

## 2. design_info 

 `sequence_db.json` /DNA  `design_info`，：

|  |  |  |
|------|------|------|
| **uniprot_id** | string | UniProt （ P01861）； |
| **residue_range** | [int, int] |  UniProt  [start, end]（1-based） |
| **mutations** | array | ， |
| **domain_boundaries** | object | （ hinge/CH2/CH3）， |
| **references** | array | /， PMID  citation |
| **verification** | string | （ "UniProt P01861 73-216 " / "+SPLE "） |
| **use_case** | string | （ "CAR ，CD22/ROR1"） |

### mutations 

```json
{
  "eu_numbering": 228,
  "wild_type": "S",
  "mutant": "P",
  "rationale": "Hinge stability; prevent Fab-arm exchange"
}
```

（ `position` + `wild_type`/`mutant`， EU  eu_numbering。）

### references 

```json
{ "pmid": "31092904", "citation": "Labrijn et al. Nat Rev Drug Discov 2019" }
```

## 3. （UniProt ） BLAST 

****： `python verify_sequences.py` `design_info.uniprot_id`  `residue_range`  **UniProt **； `verify_report.json`  `verify_report.md`。： `ACTES_RUN_BLAST=1`  blastp vs swissprot（ BLAST+）。

| entry_id | UniProt |  |  |
|----------|---------|------|----------|
| CD8a_TM, CD28_TM, CD3z_TM | P01732, P10747, P20963 |  design_info |  UniProt  ✅ |
| CD8a_Long, CD8a_SP, CD28_Medium | P01732, P10747 |  design_info |  UniProt  ✅ |
| CD28_cyto, 4-1BB_cyto | P10747, Q07011 |  design_info |  UniProt  ✅ |
| CAR-NK_2B4_cyto | Q9BZW8 | 246-380 |  UniProt  ✅ |
| NKG2D_ectodomain | P26718 (KLRK1) | 73-216 |  verify_report（isoform/）|
| DAP10_cyto | Q9UBK5 (HCST) | 44-93 |  verify_report（TM/）|
| 4-1BBL_ectodomain | P41273 (TNFSF9) | 50-255 |  verify_report |
| IgG4_SPLE_Long | P01861 (IGHG4) |  EU 216-447 | **** S228P/L235E/P331S； MISMATCH， |
| CD8a_Short | P01732 | 138-185 |  VectorBuilder 48 aa（ 135-137 AKP ）； 138-185  MISMATCH， 135-182 |

****： `REFERENCES.md`（PMID ）。

## 4.  design_info （ AI ）

 CAR  design_info（uniprot_id / residue_range / domain_boundaries / references / verification / use_case）：

|  | entry_id |  |
|------|----------|------|
| SP/Leader | CD8a_SP | CD8α signal peptide |
| Hinge | CD8a_Short, CD28_Medium, CD8a_Long, IgG4_SPLE_Long | //、Fc  |
| TM | CD8a_TM, CD28_TM |  |
| / | CD28_cyto, 4-1BB_cyto, CD3z_cyto, OX40_cyto, ICOS_cyto, OX40_ICOS_3G_cyto | 2G/3G  |
| CAR-NK | CAR-NK_2B4_cyto | 2B4  |
| 5G  | IL2Rb_cyto | IL-2Rβ P14784 237-350 |
| 5G  | 4-1BB_IL2Rb_5G_cyto | 4-1BB + IL-2Rβ + CD3ζ |
| Linker | G4S3 | (G4S)3  |

 design_info：NKG2D_ectodomain, DAP10_*, 4-1BBL_*, UCOE_A2UCOE, NFAT_Response  sequence_db.json 。

## 5. 

1. ****：`python verify_sequences.py`； `verify_report.json`、`verify_report.md`。
2. ****： `verify_report.md`，「UniProt 」「」。
3. ** BLAST**： `ACTES_RUN_BLAST=1` （ BLAST+）。
4.  **SEQUENCE_QA_AND_APPLICATION.md §2**。

## 6. /

- [ ]  `sources[].name/id`  `sequence`/`length`
- [ ]  UniProt， `design_info.uniprot_id`  `residue_range`，
- [ ] ， `design_info.mutations`（ rationale）
- [ ]  `design_info.references` 
- [ ]  `design_info.verification`  `design_info.use_case`
- [ ]  `ACTES_sequences_canonical.fasta`  `ACTES_promoters.fasta`  `ACTES_sequences_index.md`
- [ ]  `verify_sequences.py`  report 
