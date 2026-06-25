# Thera-SAbDab Therapeutic Antibody Database

This directory should contain the Thera-SAbDab therapeutic antibody database file.

## Required File

Download the Thera-SAbDab database in CSV or XLSX format and place it in this directory.

## Download Instructions

1. Visit: https://opig.stats.ox.ac.uk/webapps/thera-sabdab/
2. Navigate to the "Downloads" tab
3. Download the database in your preferred format:
   - **CSV format** (recommended for easier parsing)
   - **XLSX format** (requires openpyxl: `pip install openpyxl`)
4. Place the downloaded file in this directory

## File Format

The script `build_thera_evidence_layer.py` will automatically detect:
- CSV files (`.csv`)
- Excel files (`.xlsx`)

The script looks for common column names:
- **VH sequence**: `VH_sequence`, `Heavy_V_Sequence`, `VH`, `Heavy_Chain`, etc.
- **VL sequence**: `VL_sequence`, `Light_V_Sequence`, `VL`, `VK`, `VL_chain`, etc.
- **INN name**: `INN`, `Name`, `Antibody_Name`, `Therapeutic_Name`, etc.

## Usage

After placing the file, run:

```bash
python scripts/build_thera_evidence_layer.py
```

The script will:
1. Parse therapeutic antibody sequences
2. Number and segment using ANARCII
3. Match to IMGT germlines (best FR1-FR3 identity)
4. Compute framework usage statistics
5. Generate evidence report and JSON statistics

## Outputs

- **Report**: `docs/framework_library_thera_evidence.md`
- **Statistics**: `core/data/framework_library/thera_stats.json`

## Notes

- The script only processes entries with valid VH or VL sequences
- Germline matching requires FR1-FR3 sequences in framework library YAML files
- Only Tier1/Tier2 frameworks are included in evidence section
- All statistics are based solely on Thera-SAbDab dataset (no invention)
