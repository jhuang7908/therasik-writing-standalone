# ADA risk index thresholds (candidate)

- Source: `D:\InSynBio-AI-Research\Antibody_Engineer_Suite\data\ada245\database\ada_master_245_curated.csv`
- Rows in file: **216**
- High ADA definition: **first incidence ≥ 10.0%**

## Global

### `immuno_tcia_score`
- n valid: 129 (high-risk 48, low-risk 81)
- Orientation: **higher_is_risk**
- ROC AUC: **0.492**
- Youden cutoff (raw): **0.5961**
- Sensitivity / specificity @ cutoff: **0.875** / **0.198**
- Medians — high-risk: **0.68645**, low-risk: **0.6816**
- Rule: high ADA risk if immuno_tcia_score >= 0.5961
- Note: AUC near random — do not use this metric alone for gating.

### `hpr_proxy_pct_IMGT_mean`
- n valid: 133 (high-risk 49, low-risk 84)
- Orientation: **lower_is_risk**
- ROC AUC: **0.621**
- Youden cutoff (raw): **92.4**
- Sensitivity / specificity @ cutoff: **0.878** / **0.393**
- Medians — high-risk: **83.94**, low-risk: **86.925**
- Rule: high ADA risk if hpr_proxy_pct_IMGT_mean <= 92.4

---
_Candidate values — not production SSOT until owner-approved registry update._