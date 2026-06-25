# Humanization Core (VH/VL)

This page details the rules and procedures for conventional VH/VL antibody humanization (V4.5.1).

## 1. Vernier Zone Residues (Kabat Numbering)

The Vernier Zone consists of framework residues that directly support the CDR loops. Maintaining mouse residues at these positions is critical for affinity retention.

| Position | Region | Importance | Rationale |
|---|---|---|---|
| **27** | FR1 | High | CDR1 anchor support |
| **28** | FR1 | High | CDR1 anchor support |
| **29** | FR1 | High | CDR1 anchor support |
| **30** | FR1 | High | CDR1 anchor support |
| **47** | FR2 | High | CDR2 support |
| **49** | FR2 | High | CDR2 support |
| **71** | FR3 | Critical | CDR2-CDR3 geometry (H2 sensitivity) |
| **73** | FR3 | High | Adjacent to CDR3 |
| **78** | FR3 | High | CDR3 electrostatic support |
| **93** | FR3 | Critical | CDR3 anchor |
| **94** | FR3 | Critical | CDR3 anchor |

## 2. Humanization Rules (SOP V4.5.1)

### Phase 1: CDR Identification
*   Use **Chothia Union** definition for boundaries.
*   Union ranges: 26–38 (H1/L1), 55–65 (H2/L2), 105–117 (H3/L3).

### Phase 2: Framework Selection
*   **CDR Length Gate**: H1/H2/L1 lengths must match exactly.
*   **L2 Exclusion**: Kappa CDR2 is invariant (7 aa), excluded from filtering.
*   **Golden Pairs**: Prioritize VH/VL pairs frequently co-occurring in the 458-engineered database.
*   **Vernier Score**: T1×3 + T2×2 + T3×1 weighted scoring.

### Phase 3: Structural Modeling
*   Mandatory mouse modeling via **ABodyBuilder2**.
*   Calculate θ_mouse (VH/VL angle), SASA, and packing density.

### Phase 4: Back-mutation (BM) Decisions
*   **HC1**: Mouse G/P/C → ALWAYS retain mouse.
*   **HC4 (SASA)**: If SASA < 20 (buried) → retain mouse.
*   **HC5 (CDR Dist)**: If distance to CDR < 4.5 Å → retain mouse.
*   **SC1 (Angle)**: If Δθ > 3° → force retention of VH71.

### Phase 5: Quality Control
*   **CDR RMSD**: H1/H2/L2/L3 < 1.5 Å (HARD GATE); H3/L1 (WARN only).
*   **VH/VL Angle**: |Δθ| ≤ 10° (PASS), > 20° (HARD ABORT).
*   **Canonical Class**: Humanized structure must match mouse canonical class.

## 3. Option A (Fallback Strategy)
If automated selection fails pI (>8.5) or immunogenicity targets, use **IGHV3-23** (Gold Standard) provided RMSD < 1.5 Å.

---
**Reference Standard:** [`docs/VH_VL_HUMANIZATION_STANDARD_V4.4.md`](../docs/VH_VL_HUMANIZATION_STANDARD_V4.4.md)
