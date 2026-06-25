# Dog scaffold CMC optimization (Tier1/Tier2) — v1

- Built at: `2026-02-22 13:23:33`
- Shortlist: `data\germlines\canis_lupus_familiaris_ig_aa\dog_scaffold_shortlist_tier1_tier2_v1.json`

## Tier2 status

- VH tokens: `VH1-62`, `VH1-44`
- Mapping: {
  "VH1-44": "IGHV3-23*01",
  "VH1-62": "IGHV3-38*01"
}
- Note: Tier2 tokens mapped to IMGT IDs via resolution_status; processed as Tier2 scaffolds.

**Version**: 1.1 (2026-04-14)  
**Changelog**: Added Tier1 IGHV1-30*01 (Cirevetmab) / IGHV3-67*01 (Izenivetmab); Tier2 IGHV3-72*01 (Ranevetmab) / IGHV3-54*01 (Gilvetmab). V1.1 entries manually curated — rerun `optimize_dog_scaffolds_cmc_tier1_tier2_v1.py` for full auto-computed detail.

## Results (Tier1 & Tier2 scaffolds)

| tier | locus | gene | chain | FR1 | FR2 | FR3 | CMC(full flags) | CMC(FR13 before→after) | mutations |
|---|---|---|---|---|---|---|---:|---|---:|
| `tier1` | `IGHV` | `IGHV3-35*01` | `VH` | `EVQLVESGGDLVKPVGSLRLSCVAS` | `WVRQAPGKGLQWVA` | `RFTISRDNAKNTLYLQMRAEDTAMYYCAG` | 7 | 4→0 | 4 |
| `tier1` | `IGHV` | `IGHV3-19*01` | `VH` | `EVQLVESGGDLVKPAGSLRLSCVAS` | `WVRQAPEKGLQLVA` | `RFTISRDNAKNTVYLQMRAEDTAMYYCAK` | 7 | 4→0 | 4 |
| `tier1` | `IGHV` | `IGHV3-9*01` | `VH` | `EVQLVESGGDLVKPGGSLRLSCVAS` | `WVRQAPGKGLQWLS` | `RFTISRDNAKNTLYLQMRAEDTAVYYCAR` | 6 | 3→0 | 3 |
| `tier1` | `IGHV` | `IGHV1-30*01` ⭐V1.1 | `VH` | `EVQLVQSGAEVKKPGASVKVSCKTSGYTFI` | `WVRQAPGAGLDWMG` | `RVTLTADTSTSTAYMELSSLRAGDIAVYYCAR` | — | 3→0 | 3 (M48→L, M82→L, D83→E) |
| `tier1` | `IGHV` | `IGHV3-67*01` ⭐V1.1 | `VH` | `EVQLVESGGDLVKPGGSLRLSCVASGFTFS` | `WVRQAPGKGLQWVA` | `RFTISRDNAKNTLYLQMNSLRAEDTAMYYCAK` | — | 4→0 | 4 (N82A→Q, D86→E, M82→L, M89→L) |
| `tier1` | `IGKV` | `IGKV3-18*02` | `VL` | `EIVMTQSPASLSLSQEEKVTITC` | `WYQQKPGQAPKLLIY` | `GVPSRFSGSGSGTDFSFTISSLEPEDVAVYYC` | 3 | 1→0 | 1 |
| `tier1` | `IGKV` | `IGKV2-11*01` | `VL` | `DIVMTQTPLSLSVSPGETASISC` | `WFRQKPGQSPQRLIY` | `GVPDRFSGSGSGTDFTLRISRVEADDAGVYYC` | 3 | 1→0 | 1 |
| `tier1` | `IGLV` | `IGLV1-162*01` | `VL` | `QSVLTQPTSVSGSLGQRVTISC` | `WYQQLPGKAPKLLVY` | `GVPDRFSGSNSGNSDTLTITGLQAEDEADYYC` | 7 | 3→0 | 3 |
| `tier2` | `IGHV` | `IGHV3-38*01` | `VH` | `EVQLVESGGDLVKPGGTLRLSCVAS` | `WVRQSPGKGLQWVA` | `RFTISRDNAKNTLYLQMRAEDTAVYYCAK` | 8 | 3→0 | 3 |
| `tier2` | `IGHV` | `IGHV3-23*01` | `VH` | `EVQLVESGGDLEKPGGSLRLSCVAS` | `WVRQAPGKGLQGVS` | `RFTISRDNAKNTLYLQMRAEDTAVYSCAK` | 6 | 3→0 | 3 |
| `tier2` | `IGHV` | `IGHV3-72*01` ⭐V1.1 | `VH` | `EVQLVESGGDLVKPGDSLRLSCVASGFTFS` | `WVRQAPRKGLQWVG` | `RFTISRDNAKNTLYLQMNSLRAEDTALYNCAR` | — | 3→0 | 3 (N82A→Q, D86→E, M82→L) |
| `tier2` | `IGHV` | `IGHV3-54*01` ⭐V1.1 | `VH` | `EVQLVESGGDLMKPGGSLRLSCVASGFTIS` | `WVRQAPGKGLQWVG` | `RFTISRDNAKNTLYLQMNSLRAEDTAVYYCVKG` | — | 4→0 | 4 (M12→L, N82A→Q, D86→E, M82→L) |

## Mutation details

### `IGHV:IGHV3-35*01`

| Kabat | from | to | reason |
|---|---|---|---|
| `82A` | `N` | `Q` | `deamidation:NS` |
| `86` | `D` | `E` | `isomerization:DT` |
| `82` | `M` | `L` | `oxidation:M` |
| `89` | `M` | `L` | `oxidation:M` |

### `IGHV:IGHV3-19*01`

| Kabat | from | to | reason |
|---|---|---|---|
| `82A` | `N` | `Q` | `deamidation:NS` |
| `86` | `D` | `E` | `isomerization:DT` |
| `82` | `M` | `L` | `oxidation:M` |
| `89` | `M` | `L` | `oxidation:M` |

### `IGHV:IGHV3-9*01`

| Kabat | from | to | reason |
|---|---|---|---|
| `82A` | `N` | `Q` | `deamidation:NS` |
| `86` | `D` | `E` | `isomerization:DT` |
| `82` | `M` | `L` | `oxidation:M` |

### `IGKV:IGKV3-18*02`

| Kabat | from | to | reason |
|---|---|---|---|
| `4` | `M` | `L` | `oxidation:M` |

### `IGKV:IGKV2-11*01`

| Kabat | from | to | reason |
|---|---|---|---|
| `4` | `M` | `L` | `oxidation:M` |

### `IGLV:IGLV1-162*01`

| Kabat | from | to | reason |
|---|---|---|---|
| `66` | `N` | `Q` | `deamidation:NS` |
| `69` | `N` | `Q` | `deamidation:NS` |
| `71` | `D` | `E` | `isomerization:DT` |

### `IGHV:IGHV3-38*01`

| Kabat | from | to | reason |
|---|---|---|---|
| `82A` | `N` | `Q` | `deamidation:NS` |
| `86` | `D` | `E` | `isomerization:DT` |
| `82` | `M` | `L` | `oxidation:M` |

### `IGHV:IGHV3-23*01`

| Kabat | from | to | reason |
|---|---|---|---|
| `82A` | `N` | `Q` | `deamidation:NS` |
| `86` | `D` | `E` | `isomerization:DT` |
| `82` | `M` | `L` | `oxidation:M` |
