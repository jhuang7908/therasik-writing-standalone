# VHH (Nanobody) Engineering

VHH engineering requires specific rules due to the lack of a light chain and unique "camelid" structural features.

## 1. VHH Hallmark Residues (Kabat Numbering)

These residues in FR2 are responsible for the solubility and stability of VHH compared to conventional VH.

| Position | Conventional VH | VHH Hallmark | Function |
|---|---|---|---|
| **37** | V | **F/Y** (or Q) | Hydrophilic substitution for solubility |
| **44** | W | **G/E** | Prevents VH/VL pairing |
| **45** | L | **R/C** | Prevents VH/VL pairing |
| **47** | W | **F/L** (or I) | Hydrophilic substitution |

**Rule**: These positions are **Tier 0 (CRITICAL)** and must NEVER be humanized in S1/S2/S3 strategies.

## 2. VHH Vernier Zone

| Position | Type | Rationale |
|---|---|---|
| **28, 29** | Anchor | Critical for CDR1 geometry |
| **94** | Anchor | Critical for CDR3 geometry |
| **49, 71, 73, 78** | Tuning | Fine-tuning of CDR2/3 support |

## 3. Threat Zones (Liability & Immunogenicity)

**Threat Zones** are regions with high risk of chemical liabilities or T-cell epitope hotspots.

*   **Zone 1: CDR3 Junctions**: High risk of neoepitopes after humanization.
*   **Zone 2: FR2 Hallmarks**: While critical for stability, these non-human residues are the primary source of immunogenicity.
*   **Zone 3: C-terminal FR4**: Often truncated or modified in constructs, leading to potential aggregation.

## 4. Humanization Strategies (Tier System)

*   **S1 (Base)**: Tier 0 only (7 mutations, ~94% humanized).
*   **S2 (Safety)**: Tier 0 + Tier 1 (15 mutations, ~87% humanized).
*   **S3 (Affinity)**: Tier 0 + Tier 1 + Tier 2 (29 mutations, ~75% humanized).

---
**Reference Standard:** [`docs/VHH_HUMANIZATION_DESIGN_STANDARD.md`](../docs/VHH_HUMANIZATION_DESIGN_STANDARD.md)
