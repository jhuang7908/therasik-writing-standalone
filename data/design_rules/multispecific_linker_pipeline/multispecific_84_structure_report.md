# Structural analysis: 84 multispecific clinical antibodies (VH–linker–VL)

## 1. Structural stability

- **Mean pLDDT (global)** — mean: 84.9, min: 76.7, max: 87.6
- **Linker pLDDT** — mean: 37.8, min: 32.0
- **Fraction of residues with pLDDT ≥ 70** — median: 0.91

## 2. Linker impact

- **Linker end-to-end distance (Å)** — mean: 32.4
- **VH C-term ↔ VL N-term (junction, Å)** — mean: 29.9
- **Clashes involving linker (VH–linker + linker–VL)** — total across structures: 0
- **VH–linker contacts (CA < 8 Å)** — median per structure: 22
- **Linker–VL contacts** — median per structure: 5

## 3. VH–VL interface

- **VH–VL contacts (CA < 8 Å)** — mean: 41, median: 40
- **VH–VL clashes (CA < 3.5 Å)** — total: 0

## 4. Radius of gyration (Å)

- **Full chain** — mean: 17.8
- **VH** — mean: 13.6
- **Linker** — mean: 10.9
- **VL** — mean: 13.0

## 5. Outliers (low stability or high clash)

- **Lowest mean pLDDT (top 5):** Obertamig, Ramantamig1, Pasritamig, Xirestomig, Vixtimotamab
- **Clash:** All 84 structures have 0 CA–CA clashes (VH–linker, linker–VL, VH–VL).

---

Metrics computed by `scripts/analyze_multispecific_84_esmfold.py`.  
Full per-antibody metrics: `multispecific_84_structure_metrics.csv`, `multispecific_84_structure_summary.json`.