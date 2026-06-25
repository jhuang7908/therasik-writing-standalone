## Fig1. Pipeline schematic (Mermaid)

```mermaid
flowchart TD
  A[Input sequences: 19 clinical VHH + 7D12] --> B[ANARCI IMGT numbering + FR/CDR segmentation]
  B --> C[SSOT position sets: anchors/vernier/hallmark/ND-dependent/surface-strict]
  C --> D[Observed strategy inference: SR vs BM vs Native (human vs alpaca template matching)]
  C --> E[Variant generation: Native / SR / BM (IMGT constrained)]
  E --> F[IEDB MHC-II 15-mer scan (rank≤1,≤2) + audit/cache]
  E --> G[CMC/developability proxy: liabilities + hp_max9/cp_max7 + dev_score]
  A --> H[Structure: PDB or AlphaFold2]
  H --> I[Surface hydrophilicity: relSASA + KD; patch analysis]
  F --> J[Paper tables/figures]
  G --> J
  I --> J
```
