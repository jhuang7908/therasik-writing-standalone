"""
Correct ≥30% ADA outliers verified against FDA labels (DailyMed SPL / PI text).

- Depemokimab: 95% was a mis-extraction (95% CI in PK text). True ADA §12.6 = 10% (66/691).
- Donanemab: 90% rounded wrong vs PI §12.6 = 87% (691/792; 176/202).
- Atoltivimab: 80% was viral inhibition in label text, not ADA. PI = not detected (n=24 HV study).
"""
import math
import os

import pandas as pd

ROOT = os.path.join(os.path.dirname(__file__), "..")
CSV_PATH = os.path.join(ROOT, "data/immunogenicity_knowledge_base/master/ada_master_136_curated.csv")

UPDATES = {
    "Depemokimab": {
        "ada_first_pct": 10.0,
        "ada_value_display": "10%",
        "evidence_tier": "A",
        "evidence_source": "FDA PI (EXDENSUR, depemokimab-ulaa); §12.6 Immunogenicity",
        "citation_urls": "https://dailymed.nlm.nih.gov/dailymed/drugInfo.cfm?setid=30332b20-2ac0-42ad-a775-d3ca7f5fe29f",
        "ada_source_url_primary": "https://dailymed.nlm.nih.gov/dailymed/drugInfo.cfm?setid=30332b20-2ac0-42ad-a775-d3ca7f5fe29f",
        "ada_source_type_curated": "FDA_PI",
        "ada_source_pmids": math.nan,
        "ada_has_text_evidence": 1,
        "ada_evidence_chain_excerpt": (
            "ADA to depemokimab in EXDENSUR 100 mg q6mo (SWIFT-1, SWIFT-2 + OLE): 10% (66/691). "
            "Among ADA-positive: 6% (4/66) neutralizing antibodies. "
            "No identified clinically significant effect on PK, PD, safety, or efficacy (FDA PI §12.6, EXDENSUR)."
        ),
    },
    "Donanemab": {
        "ada_first_pct": 87.0,
        "ada_value_display": "87%",
        "evidence_tier": "A",
        "evidence_source": "FDA PI (KISUNLA, donanemab-azbt); §12.6 Immunogenicity",
        "citation_urls": "https://dailymed.nlm.nih.gov/dailymed/drugInfo.cfm?setid=190352d4-ef62-4679-b4fa-e846e2766afa",
        "ada_source_url_primary": "https://dailymed.nlm.nih.gov/dailymed/drugInfo.cfm?setid=190352d4-ef62-4679-b4fa-e846e2766afa",
        "ada_source_type_curated": "FDA_PI",
        "ada_has_text_evidence": 1,
        "ada_evidence_chain_excerpt": (
            "Study 1 (≤18 mo, Dosing Regimen 1): 87% (691/792) developed anti-donanemab-azbt antibodies; "
            "of those, 100% had neutralizing antibodies. "
            "Study 2 (≤12 mo, Dosing Regimen 2): 87% (176/202) developed ADAs; 100% neutralizing among ADA+. "
            "ADA associated with higher infusion-related reaction rates vs patients without ADAs. "
            "(FDA PI §12.6, KISUNLA.)"
        ),
    },
    "Atoltivimab": {
        "ada_first_pct": 0.0,
        "ada_value_display": "0% (not detected)",
        "evidence_tier": "A",
        "evidence_source": "FDA PI (INMAZEB); Immunogenicity",
        "citation_urls": "https://dailymed.nlm.nih.gov/dailymed/drugInfo.cfm?setid=0536b6fe-6fe5-4fd6-8cc6-1b481945c1fa",
        "ada_source_url_primary": "https://dailymed.nlm.nih.gov/dailymed/drugInfo.cfm?setid=0536b6fe-6fe5-4fd6-8cc6-1b481945c1fa",
        "ada_source_type_curated": "FDA_PI",
        "ada_source_pmids": math.nan,
        "ada_has_text_evidence": 1,
        "ada_evidence_chain_excerpt": (
            "INMAZEB label: anti-atoltivimab, anti-maftivimab, and anti-odesivimab antibodies evaluated in "
            "24 healthy adults (single-dose escalation). "
            "Immunogenic responses were not detected at baseline or through 168 days post-dose in any subjects. "
            "Older literature/database entries citing ~80% 'ADA' for atoltivimab conflated 80% viral inhibition "
            "in a plaque-reduction assay with immunogenicity incidence."
        ),
    },
}


def main():
    df = pd.read_csv(CSV_PATH)
    for name, fields in UPDATES.items():
        idx = df.index[df["antibody_name"] == name]
        if len(idx) != 1:
            raise SystemExit(f"Expected one row for {name}, got {len(idx)}")
        i = idx[0]
        for col, val in fields.items():
            if col not in df.columns:
                raise SystemExit(f"Missing column {col}")
            df.at[i, col] = val
        print(f"Updated {name} (row {i})")
    df.to_csv(CSV_PATH, index=False)
    print(f"Saved {CSV_PATH}")


if __name__ == "__main__":
    main()
