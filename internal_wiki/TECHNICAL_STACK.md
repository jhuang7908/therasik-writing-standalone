# Technical Stack & Ops

The InSynBio Antibody Engineering Suite relies on a sophisticated chain of AI tools and custom Python modules.

## 1. Tool Dependencies

| Tool | Version | Purpose |
|---|---|---|
| **AlphaFold2 (Multimer)** | 2.3.x | De novo structure prediction and interface mapping. |
| **ProteinMPNN** | 1.0.1 | Sequence design and CDR redesign. |
| **HADDOCK3** | 3.0.0 | Protein-protein and protein-peptide docking. |
| **ABodyBuilder2** | 1.0 | Fast antibody Fv modeling. |
| **ANARCI** | Latest | Antibody numbering (Chothia, Kabat, IMGT). |
| **EvoEF2** | 1.0 | Fast ΔΔG estimation and clash detection. |
| **OpenMM** | 8.x | Physics-based MM/GBSA refinement. |

## 2. Core Script Registry

| Script | Function |
|---|---|
| `evaluator.py` | The "AbEvaluator" - runs 15-parameter CMC assessment. |
| `affinity_energy_toolkit.py` | Unified API for 6-tool ΔΔG pipeline. |
| `run_mpnn_v2.py` | Orchestrates ProteinMPNN generation with coordinate discipline. |
| `validate_mask_coords.py` | Critical utility to prevent IMGT-Linear mapping errors. |
| `hallucination_guard.py` | Integrity check for all pipeline outputs. |

## 3. Environment Setup

### Conda Environment: `anarcii`
*   **Purpose**: Numbering, CMC, and light-weight analysis.
*   **Key Packages**: `anarci`, `biopython`, `pandas`, `rdkit`.

### Conda Environment: `affmat`
*   **Purpose**: Virtual Affinity Maturation and heavy structural runs.
*   **Key Packages**: `openmm`, `evoef2`, `prodigy`, `thermompnn`.

## 4. Coordinate System Discipline
*   **LINEAR**: 0-indexed, no gaps. Used for sequence operations.
*   **PDB**: Chothia numbering, includes gaps. Used for structural operations.
*   **Rule**: NEVER mix them. Always use `coord_utils.py` for conversion.

---
**Reference Rule:** [`docs/ABENGINECORE_GOVERNANCE.md`](../docs/ABENGINECORE_GOVERNANCE.md)
