# Dog framework FR1–FR3 support (v1)

- Built at: `2026-02-22 12:55:28`

## Inputs

- `tier1_anchor_library`: `data\germlines\canis_lupus_familiaris_ig_aa\dog_production_germline_library_v1.json`
- `tier2_population_priors`: `data\germlines\canis_lupus_familiaris_ig_aa\dog_repertoire_and_dla_stats.json`
- `imgt_catalogs`: `{'IGHV': 'data\\germlines\\canis_lupus_familiaris_ig_aa\\IGHV_aa.json', 'IGKV': 'data\\germlines\\canis_lupus_familiaris_ig_aa\\IGKV_aa.json', 'IGLV': 'data\\germlines\\canis_lupus_familiaris_ig_aa\\IGLV_aa.json'}`

## Kabat FR ranges used

- VH: FR1 (1, 25), FR2 (36, 49), FR3 (66, 94)
- VL: FR1 (1, 23), FR2 (35, 49), FR3 (57, 88)

## Tier2 token resolution (VH)

| token | resolved_ids | chosen_id |
|---|---|---|
| `VH1-62` | — | `—` |
| `VH1-44` | — | `—` |

## FR1–FR3 rows (framework-only)

| tier | locus | gene | FR1 | FR2 | FR3 | FR1-3 | source |
|---|---|---|---|---|---|---|---|
| `tier1` | `IGHV` | `IGHV3-35*01` | `EVQLVESGGDLVKPVGSLRLSCVAS` | `WVRQAPGKGLQWVA` | `RFTISRDNAKNTLYLQMRAEDTAMYYCAG` | `EVQLVESGGDLVKPVGSLRLSCVASWVRQAPGKGLQWVARFTISRDNAKNTLYLQMRAEDTAMYYCAG` | clinical_anchor_library |
| `tier1` | `IGHV` | `IGHV3-19*01` | `EVQLVESGGDLVKPAGSLRLSCVAS` | `WVRQAPEKGLQLVA` | `RFTISRDNAKNTVYLQMRAEDTAMYYCAK` | `EVQLVESGGDLVKPAGSLRLSCVASWVRQAPEKGLQLVARFTISRDNAKNTVYLQMRAEDTAMYYCAK` | clinical_anchor_library |
| `tier1` | `IGHV` | `IGHV3-9*01` | `EVQLVESGGDLVKPGGSLRLSCVAS` | `WVRQAPGKGLQWLS` | `RFTISRDNAKNTLYLQMRAEDTAVYYCAR` | `EVQLVESGGDLVKPGGSLRLSCVASWVRQAPGKGLQWLSRFTISRDNAKNTLYLQMRAEDTAVYYCAR` | clinical_anchor_library |
| `tier1` | `IGKV` | `IGKV3-18*02` | `EIVMTQSPASLSLSQEEKVTITC` | `WYQQKPGQAPKLLIY` | `GVPSRFSGSGSGTDFSFTISSLEPEDVAVYYC` | `EIVMTQSPASLSLSQEEKVTITCWYQQKPGQAPKLLIYGVPSRFSGSGSGTDFSFTISSLEPEDVAVYYC` | clinical_anchor_library |
| `tier1` | `IGLV` | `IGLV1-162*01` | `QSVLTQPTSVSGSLGQRVTISC` | `WYQQLPGKAPKLLVY` | `GVPDRFSGSNSGNSDTLTITGLQAEDEADYYC` | `QSVLTQPTSVSGSLGQRVTISCWYQQLPGKAPKLLVYGVPDRFSGSNSGNSDTLTITGLQAEDEADYYC` | clinical_anchor_library |
| `tier1` | `IGKV` | `IGKV2-11*01` | `DIVMTQTPLSLSVSPGETASISC` | `WFRQKPGQSPQRLIY` | `GVPDRFSGSGSGTDFTLRISRVEADDAGVYYC` | `DIVMTQTPLSLSVSPGETASISCWFRQKPGQSPQRLIYGVPDRFSGSGSGTDFTLRISRVEADDAGVYYC` | clinical_anchor_library |

## Consensus (per tier × locus)

> Consensus is a simple per-position majority over Kabat FR-only positions; coverage reports how many scaffolds provide that position.

### `tier1:IGHV`

- n_scaffolds: `3`
- n_positions: `68`

- consensus_FR_only (concatenated): `EVQLVESGGDLVKPAGSLRLSCVASWVRQAPGKGLQWVARFTISRDNAKNTLYLQMRAEDTAMYYCAG`

### `tier1:IGKV`

- n_scaffolds: `2`
- n_positions: `70`

- consensus_FR_only (concatenated): `DIVMTQSPASLSLSPEEKASISCWFQQKPGQAPKLLIYGVPDRFSGSGSGTDFSFRISRLEADDAAVYYC`

### `tier1:IGLV`

- n_scaffolds: `1`
- n_positions: `69`

- consensus_FR_only (concatenated): `QSVLTQPTSVSGSLGQRVTISCWYQQLPGKAPKLLVYGVPDRFSGSNSGNSDTLTITGLQAEDEADYYC`
