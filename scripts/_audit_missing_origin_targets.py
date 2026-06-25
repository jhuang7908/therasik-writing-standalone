import os

import pandas as pd

ROOT = os.path.join(os.path.dirname(__file__), "..")
CSV = os.path.join(ROOT, "data/immunogenicity_knowledge_base/master/ada_master_136_curated.csv")


def is_blank_series(s: pd.Series) -> pd.Series:
    out = s.isna()
    t = s.astype(str).str.strip().str.lower()
    out = out | t.isin(("", "nan", "none", "unknown", "n/a"))
    return out


def main():
    df = pd.read_csv(CSV)
    mt = df[is_blank_series(df["targets"])]
    mo = df[is_blank_series(df["origin"])]
    print("Missing targets:", len(mt))
    for _, r in mt.iterrows():
        print(" ", r["antibody_name"])
    print("Missing origin:", len(mo))
    for _, r in mo.iterrows():
        print(" ", r["antibody_name"], "| genetics:", r.get("genetics_normalized"), "| thera:", r.get("thera_genetics_class"))


if __name__ == "__main__":
    main()
