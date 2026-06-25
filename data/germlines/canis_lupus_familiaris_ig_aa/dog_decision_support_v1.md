# Dog Humanization Decision Support (v1.1)

**Date**: 2026-02-22
**Policy**: **Tier 1/2 Grafting First** → **Surface Reshaping Fallback**

## 1. Decision Logic 

The caninization process follows a strict 2-step priority queue:

### Priority 1: CDR Grafting (CDR )
**Goal**: Transfer murine CDRs onto a stable Canine Tier 1 or Tier 2 scaffold.
**Prerequisite**: A "Qualified"  scaffold must exist.

**Quantifiable Metrics for "Qualified" **:
1.  **CDR Length Match (Hard Gate)**:
    *   The scaffold's CDR lengths (Kabat definition) must **exactly match** the murine antibody's CDR lengths (excluding CDR3 which is variable, but H1/H2/L1/L2 must match).
    *   *Rationale*: Mismatched lengths imply different canonical structures; grafting forces a loop into an incompatible socket.
2.  **Framework Homology (Soft Gate)**:
    *   Framework Region (FR) Identity > **65%**.
    *   *Rationale*: Below 65%, the core packing is likely too different, risking destabilization.

### Priority 2: Surface Reshaping / Veneering ( - )
**Goal**: Keep the murine 3D structure (Framework + CDRs) intact but "paint" the solvent-exposed surface to look like a dog antibody.
**Trigger**:
    *   IF **No** Tier 1/2 scaffold meets the "CDR Length Match" criteria.
    *   OR IF the best scaffold has FR Identity < 65%.
**Method**:
    *   Identify exposed residues (Solvent Accessibility > 30%).
    *   Mutate *only* exposed non-CDR residues to the sequence of the **highest-homology** dog scaffold (regardless of CDR length).
    *   *Advantage*: Works for **any** antibody structure because it preserves the core.

---

## 2. Scaffold Selection 

### Tier 1: Clinical Anchors (Proven)
*   **VH**: `IGHV3-35*01` (Bedinvetmab-like), `IGHV3-19*01` (Lokivetmab), `IGHV3-9*01` (Landogrozumab).
*   **VL**: `IGKV3-18*02`, `IGKV2-11*01`, `IGLV1-162*01`.

### Tier 2: Population Priors (High Frequency)
*   **VH**: `IGHV3-23*01` (VH1-44), `IGHV3-38*01` (VH1-62).

---

## 3. Execution Pipeline

1.  **Input**: Murine Sequence.
2.  **Scan**: Compare input vs. all Tier 1/2 Scaffolds.
3.  **Check**:
    *   `Max_Identity` scaffold has matching CDR lengths?
    *   `Max_Identity` > 65%?
4.  **Branch**:
    *   **Pass**: Run **CDR Grafting** on best scaffold.
    *   **Fail**: Run **Surface Reshaping** using best scaffold as surface donor.
