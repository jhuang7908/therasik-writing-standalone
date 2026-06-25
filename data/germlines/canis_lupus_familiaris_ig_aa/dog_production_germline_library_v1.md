# Dog production germline library (v1)

- Built at: `2026-02-22 12:23:44`
- Species: `Canis_lupus_familiaris`

## Population priors (repertoire / DLA)

- Stats file: `data\germlines\canis_lupus_familiaris_ig_aa\dog_repertoire_and_dla_stats.json`
- Stats meta: `{"description": "Canine BCR Repertoire Stats and DLA Allele Frequencies for Engineering", "version": "1.0", "date": "2026-02-21", "sources": ["Molecular characterization of the VH repertoire in Canis familiaris (VH usage)", "Frequency and distribution of alleles of canine MHC-II ... in 25 AKC breeds (DLA)", "IMGT Repertoire (IG and TR)"]}`

## Clinical canine reference antibodies (repo-internal)

| name | pdb | inferred VH V | id% | inferred VL V | locus | id% |
|---|---|---|---:|---|---|---:|
| Bedinvetmab | `projects\Llama_Humanization_Project\semi_auto_workflow\inputs\Bedinvetmab.pdb` | `IGHV3-19*01` | 0.941 | `IGLV1-162*01` | IGL | 0.913 |
| Lokivetmab | `projects\Llama_Humanization_Project\semi_auto_workflow\inputs\Lokivetmab.pdb` | `IGHV3-35*01` | 0.956 | `IGKV3-18*02` | IGK | 1.000 |
| Landogrozumab | `data\structures\engineered\Landogrozumab.pdb` | `IGHV3-9*01` | 0.926 | `IGKV2-11*01` | IGK | 0.700 |

## Production-capable V-gene scaffolds (derived from above)

### VH V genes

| gene | best_identity | seen_in |
|---|---:|---|
| `IGHV3-35*01` | 0.956 | Lokivetmab |
| `IGHV3-19*01` | 0.941 | Bedinvetmab |
| `IGHV3-9*01` | 0.926 | Landogrozumab |

### VL V genes

| locus | gene | best_identity | seen_in |
|---|---|---:|---|
| IGK | `IGKV3-18*02` | 1.000 | Lokivetmab |
| IGL | `IGLV1-162*01` | 0.913 | Bedinvetmab |
| IGK | `IGKV2-11*01` | 0.700 | Landogrozumab |

## Notes

- This v1 library is anchored on in-repo clinical canine antibodies + IMGT functional annotation, not population frequencies.
- If population-level repertoire / DLA frequency priors are available, they are recorded under sources.population_stats_file and payload.population_support.
- Use-case: choose a small set of production-capable dog V-gene scaffolds for caninization / surface reshaping workflows.
- J-gene mapping is best-effort because IMGT J-REGION translations may not align 1:1 with FR4 definitions in every pipeline.
