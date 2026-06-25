# Antibody Structure & Case Studies

This page covers the structural principles used in AbEngineCore and the logic derived from key case studies.

## 1. Structural Principles

### VH/VL Interface (The θ Angle)
*   The relative orientation of VH and VL domains is measured by the θ angle.
*   **Deviation Rule**: Δθ > 3° suggests a significant structural shift that may impact the antigen-binding pocket.
*   **Control**: Back-mutations at interface residues (e.g., VH37, VH44, VL38, VL44) are used to restore the parental angle.

### Packing & SASA
*   **Packing Score**: Measures the density of atomic contacts. Low packing in the core suggests instability.
*   **SASA (Solvent Accessible Surface Area)**: Used to identify "buried" residues (SASA < 20) which should not be humanized to avoid core destabilization.

## 2. AbEngineCore Case Study Rules

### Case: muMAb4D5 (Humanization Benchmark)
*   **Rule**: 100% CDR retention is mandatory.
*   **Logic**: Even single mutations in CDRs can lead to 10-100x affinity loss.
*   **Outcome**: Achieved 4.3/5 quality score with 4 back-mutations.

### Case: PD-L1 (Epitope Analysis)
*   **Rule**: Blocking vs. Non-blocking classification must be structurally resolved.
*   **Logic**: Use AF2-Multimer to map the interface. If overlap with PD-1 binding site > 30%, classify as "Blocking".

### Case: Fentanyl (Hapten VAM)
*   **Rule**: Scenario D (Small Molecule) requires GAFF2 forcefield for MM/GBSA.
*   **Logic**: Protein-only forcefields fail to accurately score small molecule interactions.

## 3. Decision Logic for Complex Scenarios

| Scenario | Decision Rule |
|---|---|
| **Low pI (< 6.0)** | Perform pI Engineering (e.g., VH/VL surface charge tuning). |
| **High Immunogenicity** | Identify MHC-II hotspots via IEDB and apply "Stealth" mutations. |
| **Aggregation Risk** | Check for hydrophobic patches (> 0.70) and apply hydrophilic substitutions. |

---
**Reference Data:** [`docs/ABENGINECORE_GOVERNANCE.md`](../docs/ABENGINECORE_GOVERNANCE.md)
