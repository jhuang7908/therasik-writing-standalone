"""Fill missing origin, genetics_normalized, targets, fc_isotype, format_type, modality, moa_class."""
import os

import pandas as pd

ROOT = os.path.join(os.path.dirname(__file__), "..")
CSV = os.path.join(ROOT, "data/immunogenicity_knowledge_base/master/ada_master_136_curated.csv")

# Curated from indication_text + public drug class (humanized engineered mAbs / VHH)
PATCH = {
    "Emicizumab": {
        "origin": "engineered",
        "genetics_normalized": "humanised",
        "targets": "F9|F10",
        "fc_isotype": "G4",
        "format_type": "bispecific_IgG4",
        "modality": "bispecific",
        "moa_class": "anti-coagulation",
    },
    "Faricimab": {
        "origin": "engineered",
        "genetics_normalized": "humanised",
        "targets": "VEGFA|ANGPT2",
        "fc_isotype": "G1",
        "format_type": "bispecific_IgG1",
        "modality": "bispecific",
        "moa_class": "anti-VEGF",
    },
    "Ozoralizumab": {
        "origin": "engineered",
        "genetics_normalized": "humanised",
        "targets": "TNF|TNFA",
        "format_type": "trivalent_VHH_anti-TNF",
        "modality": "VHH",
        "moa_class": "anti-TNF",
    },
    "Tarlatamab": {
        "origin": "engineered",
        "genetics_normalized": "humanised",
        "targets": "DLL3|CD3E|CD3",
        "fc_isotype": "G1",
        "format_type": "bispecific_TCE",
        "modality": "bispecific",
        "moa_class": "T-cell engager (other)",
    },
    "Zenocutuzumab": {
        "origin": "engineered",
        "genetics_normalized": "humanised",
        "targets": "ERBB2|ERBB3",
        "fc_isotype": "G1",
        "format_type": "bispecific_IgG1",
        "modality": "bispecific",
        "moa_class": "other",
    },
}


def main():
    df = pd.read_csv(CSV)
    for name, fields in PATCH.items():
        idx = df.index[df["antibody_name"] == name]
        if len(idx) != 1:
            raise SystemExit(f"Expected one row for {name}, got {len(idx)}")
        i = idx[0]
        for col, val in fields.items():
            if col not in df.columns:
                raise SystemExit(f"Missing column {col}")
            df.at[i, col] = val
        print(f"Patched {name} (row {i})")
    df.to_csv(CSV, index=False)
    print("Saved", CSV)


if __name__ == "__main__":
    main()
