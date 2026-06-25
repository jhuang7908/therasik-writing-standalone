# De Novo CDR Design SOP — V1.0
## InSynBio Antibody Engineer Suite

> Established: 2026-04 | Based on: VGRW-SR-R2 HER2 VHH CDR2+CDR3 design campaign

---

## 1. Overview

This SOP covers the **de novo CDR redesign pipeline** for VHH and VH/VL antibody sequences with the following objectives:
- Patent escape (maximize CDR sequence diversity from WT)
- Affinity rescue (recover binding after CDR modification)
- CDR2+CDR3 co-design (standard default mode)

The pipeline is fully automated from MPNN sampling through final VAM report. All parameters below represent the distilled defaults from two rounds of the VGRW-SR-R2 design campaign.

---

## 2. Design Strategy Decision Tree

```
Project goal?
├── Patent escape only         → Mode: CDR2-only, patent_escape clustering
├── Affinity rescue            → Mode: CDR2+CDR3 co-design, affinity_rescue clustering
└── Both (default recommended) → Mode: CDR2+CDR3 co-design, patent_escape clustering
                                  + VAM layer2 for affinity recovery
```

**Default recommendation: CDR2+CDR3 co-design.** Do NOT use serial single-CDR redesign as it breaks CDR cooperativity and leads to cumulative affinity loss.

---

## 3. CDR Root Constraint Rules

Root residues define the loop's structural take-off and landing geometry. Never design them freely.

### 3.1 Three-tier residue classification

| Tier | Definition | MPNN treatment | Post-filter |
|------|-----------|----------------|-------------|
| **Root-fixed** | N-root (first CDR residue), C-root / J-anchor (last 1-2 CDR residues) | Added to MPNN fixed list | Must match WT exactly |
| **Semiopen** | 1 AA immediately adjacent to each root, inside the CDR | Allowed by MPNN | Must pass BLOSUM62 ≥ 1 conservative substitution check |
| **Loop body** | All remaining CDR residues | Fully open | No substitution restriction |

### 3.2 CDR2 defaults (17 aa, VGRW-SR-R2 numbering)

| Tier | 0-indexed positions | Notes |
|------|-------------------|-------|
| Root-fixed | 46, 62 | N-root (pos 47 1-indexed), C-root (pos 63 1-indexed) |
| Semiopen | 47, 61 | Adjacent to roots |
| Loop body | 48–60 | 13 fully designed positions |

### 3.3 CDR3 defaults (13 aa, VGRW-SR-R2 numbering)

| Tier | 0-indexed positions | Notes |
|------|-------------------|-------|
| Root-fixed | 96, 106, 107 | N-root (S), J-anchor D, J-anchor Y |
| Semiopen | 97, 104, 105 | Adjacent to roots |
| Loop body | 98–103 | 6 fully designed positions (core loop) |

> **Rationale**: CDR3 positions 106 (D) and 107 (Y) are highly conserved J-gene residues. In our campaign, MPNN autonomously avoided mutating them, confirming their structural importance.

---

## 4. MPNN Sampling Parameters

### 4.1 Standard settings

| Parameter | Value | Notes |
|-----------|-------|-------|
| `num_seq_per_target` | 300 (quick) / 500–1000 (formal) | Per temperature |
| `sampling_temps` | `0.2, 0.3, 0.35` | Three temperatures standard |
| `seed` | 42 | Reproducibility |
| Optional temp | `0.4` | Adds diversity; increases PTM rate |
| Max temp | `0.5` | Never exceed; too many unnatural sequences |

### 4.2 Temperature guidance

- `0.2`: Most conservative; close to MPNN's most probable sequence
- `0.3`: Best balance of naturalness and diversity (primary temperature)
- `0.35–0.4`: Extended diversity search; use when 0.2/0.3 not giving enough variety
- `>0.45`: Avoid for CDR loop design; probability of nonsensical sidechains increases

---

## 5. Pre-filter Chain (T0.0 → T0 → T1 → T0.5)

| Filter | Tool | Threshold | Purpose |
|--------|------|-----------|---------|
| **T0.0** PTM | regex | Any deamidation/isomerization/N-glyc in CDR → fail | Block liability sequences before any compute |
| **T0** OASis | promb | Coverage ≥ WT × 0.80 | Human naturalness check |
| **T1** AbLang | ablang | score ≥ WT × 1.50 | Pseudo-perplexity naturalness |
| **T0.5** Cluster | cluster_and_filter_v2 | See Section 6 | Diversity filter before structure prediction |

> **Note**: T0.0 PTM check catches the single most impactful filter at near-zero cost. Always run it first.

---

## 6. T0.5 Diversity Clustering

### 6.1 Mode presets

| Mode | CDR identity max | Min CDR mutations | Hamming frac | Max survivors |
|------|-----------------|-------------------|--------------|---------------|
| `patent_escape` | 0.65 | 5 | 0.30 | 50 |
| `affinity_rescue` | 0.95 | 1 | 0.15 | 50 |
| `broad_diversity` | 0.55 | 7 | 0.25 | 50 |

### 6.2 Multi-CDR identity calculation

When CDR2+CDR3 are co-designed, CDR identity is computed over the **combined concatenated CDR string** (CDR2 + CDR3), not per-CDR. This is more meaningful for diversity assessment.

### 6.3 Hamming clustering

Cluster radius = `combined_cdr_length × hamming_frac`. Representative = highest AbLang score within each cluster. This ensures structural variety while avoiding near-identical candidates from small temperature differences.

---

## 7. T3 Complex Clash Filter — Three-Tier Funnel

### 7.1 Clash tiers

| Tier | Clash count | Action | Rationale |
|------|------------|--------|-----------|
| **Green** | 0–5 | Direct pass | Clean interface |
| **Gray** | 6–15 | EvoEF2 RepairStructure → recheck | Sidechain rotamer adjustment may resolve |
| **Red** | >15 | Direct reject | Backbone-level conflict; cannot repair without main-chain movement |

### 7.2 Gray-zone repair procedure

1. Run `EvoEF2 --command=RepairStructure` on the candidate PDB
2. Re-superimpose repaired structure on framework Cα
3. Re-count CDR-antigen clashes
4. If repaired clash ≤ 5: rescue and pass
5. If repaired clash still > 5: reject

> **Why this matters**: The original `>5` hard cutoff penalizes large-sidechain AAs (Trp, Tyr, Arg) that form the tightest VHH-antigen interfaces. Gray-zone rescue recovers ~10–20% of candidates that would otherwise be incorrectly rejected.

### 7.3 Overlap check

Minimum CDR contact fraction with antigen: **0.60**. Applied jointly with clash check. A molecule with 0 clashes but 0.38 overlap (CDR pointing away from antigen) is still rejected.

---

## 8. Phase 4: HADDOCK3 + MM/GBSA

### 8.1 Input selection

Only send to HADDOCK3 candidates that pass ALL of:
- T3 clash: green or gray-rescued
- T3 overlap ≥ 0.60
- AbLang score ≥ WT × 1.50
- No PTM flags in CDR regions
- CMC: no hard-fail on aggregation/hydrophobic patch

### 8.2 Reference baseline

Always include WT (or parent if iterative design) in every HADDOCK3 batch. This ensures MM/GBSA comparisons are self-consistent within the same run.

### 8.3 Decision logic

| MM/GBSA result | Action |
|---------------|--------|
| Any candidate ΔG ≤ WT ΔG | Accept best; no VAM needed |
| All candidates ΔG > WT ΔG | Trigger VAM on best candidate |
| All HADDOCK3 failed | Re-run with relaxed tolerance; or report no survivors |

---

## 9. Complete VAM — Two-Layer Protocol

### 9.1 Layer 1: single-point scan

1. Enumerate all single-point substitutions at **designed CDR positions** (exclude root-fixed positions)
2. EvoEF2 ΔΔG scan
3. Filter: ΔΔG < 0 (beneficial)
4. ThermoMPNN stability veto (ΔΔG_stability ≤ 0.5)
5. MM/GBSA on top 8 stable hits

If Layer 1 finds 0 beneficial hits → recovery pass: take lowest-ΔΔG candidates regardless of sign → ThermoMPNN + MM/GBSA.

### 9.2 Layer 2: pairwise combinatorial

**Only runs if Layer 1 finds ≥ 2 beneficial seeds.**

1. Take top-10 Layer-1 seed mutations
2. Enumerate all pairwise combinations (skip if same position)
3. Up to 45 pairs (configurable)
4. EvoEF2 scan
5. ThermoMPNN veto
6. MM/GBSA on top 5

> **Rationale**: Epistatic (cooperative) mutations are common in CDR maturation. Layer 1 alone misses synergistic pairs. In the VGRW-SR-R2 campaign, Layer 1 found 0 seeds — Layer 2 was not triggered. This is scientifically correct: it confirms the parent is at a local energy minimum and combinatorial VAM alone is insufficient without backbone movement.

### 9.3 When to stop VAM

| Scenario | Decision |
|---------|---------|
| Layer 1 + Layer 2 both 0 improvements | Stop; switch to CDR co-design or backbone flexible method |
| Layer 1 improvement found | Report best single mutant; optionally run Layer 2 |
| Layer 2 improvement found | Report best combo mutant as final recommendation |
| Single-CDR design consistently worse than WT | Abandon serial strategy; switch to CDR2+CDR3 co-design |

---

## 10. Script Reference

| Script | Purpose | conda env |
|--------|---------|-----------|
| `pipeline/run_mpnn_v2.py` | Generalized MPNN sampling, multi-CDR, root constraints | `affmat` |
| `pipeline/cluster_and_filter_v2.py` | T0.5 clustering, multi-CDR identity, mode presets | `affmat` |
| `pipeline/run_t3_v2.py` | T3 complex clash gate, three-tier funnel, gray-zone repair | `affmat` |
| `pipeline/vam_complete.py` | Complete two-layer VAM (single-point + pairwise combo) | `affmat` |
| `pipeline/mask_strategy_template_CDR23_codesign.json` | Config template for CDR2+CDR3 co-design | — |

---

## 11. Compute Budget Guidance

| Stage | Per-candidate cost | When to invest |
|-------|------------------|----------------|
| MPNN sampling | ~5–30 min total | Always; cheap |
| T0.0 PTM filter | ~0 ms | Always |
| T1 AbLang | ~10 sec/seq | Always |
| T0.5 clustering | ~5 min | Always; saves all downstream cost |
| ImmuneBuilder | ~40 sec/seq | Yes for CDR3 changes; optional for CDR2-only |
| T3 clash check | ~30–90 sec/seq | Always; cheap gateway to HADDOCK3 |
| EvoEF2 gray repair | ~60 sec/seq | Only gray-zone (clash 6–15) |
| HADDOCK3 | ~20–40 min/complex | Only T3-passed + CMC-OK candidates |
| MM/GBSA | ~5–10 min/complex | Only post-HADDOCK3 |
| VAM Layer 1 | ~2–5 min (EvoEF2) + ~5 min (MMGBSA) | When affinity drops vs WT |
| VAM Layer 2 | ~5–15 min (EvoEF2) + ~10 min (MMGBSA) | When L1 finds ≥2 seeds |

---

## 12. Known Limitations

1. **Fixed backbone**: All current MPNN/EvoEF2 operations assume the CDR main chain is fixed. Affinity improvements requiring backbone movement (> ~1 Å CDR main-chain RMSD) are invisible to this pipeline.

2. **EvoEF2 force field**: Accurate for buried core mutations; less reliable for highly flexible solvent-exposed CDR loops. Use MM/GBSA as the final arbiter, not EvoEF2 alone.

3. **Serial CDR redesign**: As shown in the VGRW-SR-R2 campaign, redesigning CDR2 first then CDR3 breaks inter-CDR cooperativity and leads to cumulative energy loss. Always prefer co-design.

4. **OASis for highly modified VHH**: When the parent sequence already has >7 CDR mutations vs any human sequence, OASis coverage may drop to near 0. In affinity rescue mode, bypassing the OASis filter (`affinity_rescue` mode) is acceptable.

---

## 13. Appendix: Conservative Substitution Table (BLOSUM62 ≥ 1)

| WT | Allowed conservative substitutions |
|----|-----------------------------------|
| A  | G, S, T, V |
| C  | S |
| D  | E, N |
| E  | D, K, Q |
| F  | Y, W, L |
| G  | A, S |
| H  | N, Q, Y |
| I  | L, M, V |
| K  | E, Q, R |
| L  | I, F, M, V |
| M  | I, L, V |
| N  | D, H, S |
| P  | (none — proline is structurally unique) |
| Q  | E, K, R |
| R  | K, Q |
| S  | A, G, N, T |
| T  | A, S, V |
| V  | A, I, L, M, T |
| W  | F, Y |
| Y  | F, H, W |
