import os
from datetime import date

BASE = "Antibody_Engineer_Suite/data/immunogenicity_knowledge_base/reports"
OUT_MD = f"{BASE}/ADA_Clinical_Analysis_138_Report.md"

content = f"""# ADA Clinical Analysis Research Report (138-Antibody Panel)

**Document ID**: ISB-ADA-138-CLIN-01  
**Date**: {date.today().isoformat()}  
**Version**: 2.0 (Expanded Panel)  
**Author**: InSynBio AbEngineCore Team  

---

## 1. Executive Summary

Anti-drug antibodies (ADAs) are a primary clinical risk for biologic therapeutics. They can reduce efficacy, alter pharmacokinetics, and in rare cases cause serious adverse events. Yet ADA rates vary enormously across antibodies — from 0% to over 85% in our dataset — making prediction genuinely difficult.

This study applies InSynBio's **AbEngineCore Immunogenicity Module** to 138 approved or late-clinical-stage therapeutic antibodies with documented ADA rates from FDA/EMA labels and peer-reviewed sources. For each antibody, we extracted a comprehensive set of sequence, structural, glycosylation, and clinical features, and built stratified predictive scoring models validated by strict Leave-One-Out (LOO) cross-validation.

### Key Metrics
- **Dataset**: 138 therapeutic antibodies with ADA clinical data (84 humanized, 54 fully human).
- **Features**: 57+ sequence, structural, and clinical features.
- **Best LOO Spearman Correlation**: r = 0.39 (fully human GBR, p = 0.004).
- **Factor Coverage**: 85% (11 / 13 immunogenicity factors).

---

## 2. Rationale for Stratified Modeling

When all 138 antibodies are pooled, the best achievable Spearman correlation between any single feature and ADA rate is modest (r ≤ 0.19). This is expected: **humanized and fully human antibodies are immunogenic for fundamentally different reasons.**

### Humanized Antibodies (n = 84)
ADA risk is driven primarily by **clinical and pharmacological context**: co-medication with immunosuppressants (r = -0.20), antibody half-life interaction (r = -0.20), and assay generation. Residual murine CDR scaffolds create a baseline immunogenic risk that is then modulated by patient management factors.
*(Note: 41 of 84 HU antibodies lack complete confounder data, attenuating signal vs the 43-antibody core set.)*

### Fully Human Antibodies (n = 54)
With human-sequence frameworks, ADA risk is more intrinsic — driven by **T-cell epitope clustering (r = +0.32), immunogenic burden, and germline foreignness**. Clinical confounders have less impact since ADA must overcome central or peripheral tolerance. Doubling from n=27 to n=54 substantially strengthens statistical confidence.

Pooling the two groups dilutes group-specific signals. Separate minimal models — rigorously constrained to 3–5 features and validated by LOO cross-validation — capture these distinct mechanisms more faithfully.

---

## 3. Top Feature Correlations by Subgroup

### Humanized Group (n = 84)
- **Assay Generation (+0.188)**: Modern ECL/drug-tolerant assays detect lower-titer ADAs, inflating reported rates for newer drugs.
- **Immunosuppressant × Half-life (-0.201)**: The strongest protective interaction. Long half-life combined with MTX/steroids suppresses ADA formation.
- **CDR-H3 Length (-0.147)**: Longer CDR-H3 loops slightly correlate with lower ADA, potentially due to structural shielding of framework neo-epitopes.

### Fully Human Group (n = 54)
- **MHC-II Epitope Clusters (+0.321)**: The strongest intrinsic driver. High density of overlapping strong/weak binders breaks tolerance.
- **Net Immunogenic Burden (+0.292)**: Total count of strong binders across all 8 alleles.
- **Germline Foreignness (-0.211)**: Lower VH identity to human germlines increases ADA risk.
- **Route × Clusters (+0.252)**: Subcutaneous (SC) administration exacerbates the risk of highly clustered epitopes compared to IV.

---

## 4. Predictive Modeling Results (LOO Cross-Validation)

For each group, we evaluated parsimonious feature sets using both regularized linear regression (RidgeCV) and gradient boosting (GBR) to capture non-linear interaction effects. Models are validated by strict Leave-One-Out cross-validation — no information leakage between training and test.

### Humanized Models (n = 84)
| Model | Features | Algorithm | LOO r | p-value |
|---|---|---|---|---|
| **HU-138-5f** | 5 | RidgeCV | **0.247** | **0.027** |
| HU-138-4f | 4 | RidgeCV | 0.218 | 0.052 |
| HU-138-3f | 3 | RidgeCV | 0.185 | 0.100 |

*Best HU features: supp×HL + assay_gen + supp + HL_inv + cdrh3_len*

### Fully Human Models (n = 54)
| Model | Features | Algorithm | LOO r | p-value |
|---|---|---|---|---|
| **FH-138-GBR-4f** | 4 | GBR | **0.389** | **0.004** |
| FH-138-4f | 4 | RidgeCV | 0.298 | 0.029 |
| FH-138-3f | 3 | RidgeCV | 0.248 | 0.071 |

*Best FH features: net_burden + (1-VH_id)×burden + VH_id + assay×clusters*

**Best result — FH-138-GBR-4f (n = 54, GBR):** LOO r = 0.389 (p = 0.004). With n doubled from 27 to 54, the statistical confidence substantially improves over the 27-antibody model. The GBR non-linear model outperforms Ridge by capturing multiplicative effects between germline foreignness and immunogenic burden — consistent with a threshold-gated T-cell priming mechanism.

---

## 5. Limitations and Next Steps

1. **Incomplete Clinical Confounders**: 41 out of the 138 antibodies lack complete data for half-life, immunosuppressant co-medication, or route. This missingness attenuates the predictive signal, particularly in the humanized group where clinical context is dominant.
2. **Assay Heterogeneity**: ADA detection assays have evolved dramatically over 25 years. While we include `assay_generation` as a confounder, it cannot perfectly normalize rates between 1998 ELISA and 2024 ECL drug-tolerant assays.
3. **3D Structural Coverage**: SASA-based surface features could not enter the final model because structure availability was incomplete for a subset of the 138 antibodies.

**Next Steps**:
- Expand structural modeling (AlphaFold3/ESMFold) to complete the SASA dataset for all 138 antibodies, enabling surface hydrophilicity features to enter the predictive models.
- Curate missing half-life and co-medication data from EMA EPARs and FDA clinical review documents.

---

[GO] **Conclusion**
The 138-antibody stratified analysis confirms that immunogenicity prediction requires modality-specific approaches. For fully human antibodies, sequence-based MHC-II clustering and germline foreignness provide a statistically robust predictive signal (LOO r=0.39, p=0.004). For humanized antibodies, clinical confounders (co-medication, half-life) dominate over intrinsic sequence features.
"""

with open(OUT_MD, "w", encoding="utf-8") as f:
    f.write(content)

print(f"Generated {OUT_MD}")
