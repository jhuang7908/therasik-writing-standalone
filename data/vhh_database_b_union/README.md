# Database B — / VHH（NanoBodyBuilder2）

## 

```bash
set KMP_DUPLICATE_LIB_OK=TRUE
python scripts/build_database_b_nanobuilder.py --python "%CONDA_PREFIX%\python.exe"
```

-  `data/sabdab_nano/sabdab_nano_summary_all.tsv`  **29**  `(pdb, Hchain)`。
-  RCSB  PDB， **PPBuilder** 。
-  **`scripts/predict_one_immunebuilder.py`**，`model_type: nanobody`（**NanoBodyBuilder2**），** AlphaFold2**。

## 

|  |  |
|------|------|
| `database_b_manifest_29.json` | 29  |
| `database_b_sequences.json` |  +  |
| `immunebuilder_models/<pdb_chain>/rank0_unrefined.pdb` |  |
| `run_log.txt` |  |

## （ ImmuneBuilder）

```bash
python scripts/build_vhh_structural_union_index.py
```

：`data/vhh_structural_union/vhh_structural_union_index.json`。
