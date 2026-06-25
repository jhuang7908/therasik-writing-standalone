# Canine BCR Repertoire & DLA Allele Statistics

**Version:** 1.0  
**Date:** 2026-02-21  
**Purpose:** Provide data-driven guidance for canine antibody humanization (caninization) and immunogenicity assessment, based on natural population frequencies.

---

## 1. VH Gene Usage (Scaffold Selection)

Unlike humans, the canine VH repertoire is heavily skewed towards a single family. Selecting a germline scaffold from this high-frequency pool increases the likelihood of in vivo stability and tolerance.

### Key Findings
*   **Dominant Family**: **VH1** (Contains ~76 genes, dominates cDNA clones).
*   **Minor Families**: VH2 (3 genes), VH3 (1 gene).
*   **Diversity Mechanism**: Primarily Junctional Diversity (CDR3) and Somatic Hypermutation (SHM), rather than V-gene combinatorial diversity.

### Recommended "High-Frequency" Scaffolds
If clinical antibody anchors (Bedinvetmab, etc.) are not suitable, prioritize these naturally abundant frameworks:

| Gene (IMGT/Common) | Mapped IMGT ID | Human Homolog | Note |
| :--- | :--- | :--- | :--- |
| **VH1-62** | `IGHV3-38*01` | VH3-21 | Highly frequent in multiple breeds. Mapped to functional surrogate. |
| **VH1-44** | `IGHV3-23*01` | VH3-23 | Highly frequent in multiple breeds. Mapped to functional homologue. |

> **Engineering Implication**: When "humanizing" a mouse antibody for dogs, if the mouse sequence is homologous to Human VH3, it is likely compatible with Canine VH1-62 or VH1-44.

---

## 2. DLA Core Panel (Immunogenicity Assessment)

Canine MHC Class II (DLA) alleles vary significantly by breed. To assess "population-wide" immunogenicity risk without testing every breed, use this **Core Panel** of alleles that are shared across a wide range of breeds (based on 25 AKC breed survey).

### Core DLA Alleles (The "Common Denominators")

| Locus | Allele | Frequency / Coverage |
| :--- | :--- | :--- |
| **DLA-DRB1** | `DLA-DRB1*00101` | Shared by **16/25** breeds |
| **DLA-DRB1** | `DLA-DRB1*01501` | Shared by **19/25** breeds |
| **DLA-DQA1** | `DLA-DQA1*00101` | Major allele (monoallelic in some breeds) |
| **DLA-DQA1** | `DLA-DQA1*00601` | Widely shared |
| **DLA-DQB1** | `DLA-DQB1*00201` | Shared by **17/25** breeds |
| **DLA-DQB1** | `DLA-DQB1*02301` | Shared by **18/25** breeds |

> **Engineering Implication**: In silico immunogenicity prediction (e.g., NetMHCIIpan) should prioritize these alleles. Peptides that bind strongly to these DLA variants represent a higher risk of broad-spectrum immunogenicity in the dog population.

---

## Sources
1.  *Molecular characterization of the VH repertoire in Canis familiaris* (VH usage statistics)
2.  *Frequency and distribution of alleles of canine MHC-II DLA-DQB1, DLA-DQA1 and DLA-DRB1 in 25 representative American Kennel Club breeds* (DLA frequencies)
3.  IMGT Repertoire (IG and TR)
