# Lofacimig — Reconciliation Status

**Status:** Full 493 aa heavy-chain sequence collected from NCATS/GSRS API; excluded from single-domain VHH cohorts.
**Generated:** 2026-04-30
**Scope:** Resolves the `master_table_only_no_seq` finding from `data/_reconciliation/VHH_ID_RECONCILIATION.csv`.

This file captures externally verified metadata and sequence provenance for **Lofacimig (INN)** without introducing it into single-domain VHH production cohorts. The `vhh_clinical_39_union/vhh_39_sequences_clinical_validated.csv` and `VHH42_reference_stats_v1.json` cohorts are intentionally **not** modified by this note.

---

## 1. Verified Metadata

| Field | Value | Source |
| --- | --- | --- |
| INN | Lofacimig (proposed 2024) | NCATS, Thera-SAbDab |
| Code name | KN060 | Synapse / PatSnap, Alphamab |
| Originator | Suzhou Alphamab Co., Ltd. | Synapse / PatSnap |
| Target | Human coagulation factor XI (F11 / FXI / PTA), Apple-2 and Apple-3 domains | NCATS UNII record |
| Modality | Bispecific only-heavy-chain (VH-VH-G1(h-CH2-CH3)) homodimer | NCATS |
| Origin | Camelid (Lama glama / Camelus dromedarius), humanized | NCATS |
| VH framework | Camelid IGHV3S45*01 (~86.6%) / human IGHV3-66*01 (~83.5%) | NCATS |
| J-region | IGHJ5*02 (100%) | NCATS |
| CDR-IMGT lengths | 9 / 7 / 23 (positions 26–34, 52–58, 97–119) | NCATS |
| Per-chain length | 493 aa (homodimer) | NCATS |
| C-terminal modification | K removal (lysine clipping) | NCATS |
| N-terminal modification | Q → pyroglutamate (pidolic acid) | NCATS |
| Linker | 3-mer Gly-Ala-Pro (GAP) between VH1 and VH2 | NCATS |
| Highest reported clinical phase | Phase 2 (venous thromboembolism); Phase 1 (essential hypertension) | Synapse / PatSnap |
| UNII | L55HB62LXD | NCATS |
| External ID (Synapse) | KN060 | Synapse / PatSnap |

---

## 2. Sources Consulted

| Source | URL | Status |
| --- | --- | --- |
| NCATS Drugs Substance Record | <https://drugs.ncats.io/substance/L55HB62LXD> | Reachable; confirms substance class, modality, framework, CDR lengths, modifications |
| NCATS/GSRS API | <https://drugs.ncats.io/api/v1/substances(L55HB62LXD)> | Reachable; provides two identical 493 aa protein subunits |
| Synapse / PatSnap drug page | <https://synapse.patsnap.com/drug/a55a512588d246e595955eef3d8e66f9> | Reachable; confirms KN060, Alphamab originator, indications |
| Thera-SAbDab therapeutic record | <https://opig.stats.ox.ac.uk/webapps/sabdab-sabpred/therasabdab/search/?therapeutic=Lofacimig> | Service Unavailable at retrieval time |
| TargetMol product page | <https://www.targetmol.com/compound/lofacimig> | Reachable; confirms VH-VH-G1 dimer modality |
| WHO INN Proposed/Recommended List PDFs (~132, 2024) | <https://www.who.int/teams/health-product-policy-and-standards/inn/inn-publications> | **Not yet retrieved**; primary authoritative source for full amino acid sequence |
| Alphamab KN060 patents (CN/WO/US) | The Lens / Patentscope | **Not yet retrieved**; secondary authoritative source for full amino acid sequence |

---

## 3. Sequence Status

The complete amino acid sequence for the per-chain 493 aa Lofacimig protein **is available through the NCATS/GSRS API**. The API returns two identical 493 aa subunits, consistent with a homodimer.

Cleaned outputs:

- `data/sequence_provenance/lofacimig/lofacimig_ncats_gsrs_full_chain_v1.json`
- `data/sequence_provenance/lofacimig/lofacimig_ncats_gsrs_full_chain_v1.fasta`
- Generator: `scripts/collect_clean_lofacimig_sequence.py`

Cleaned boundaries:

| Segment | Coordinates | Length |
| --- | ---: | ---: |
| VH1 | 1-130 | 130 aa |
| GAP linker | 131-133 | 3 aa |
| VH2 | 134-259 | 126 aa |
| G1(h-CH2-CH3) | 260-493 | 234 aa |

IMGT CDR lengths:

| Domain | CDR1 | CDR2 | CDR3 |
| --- | ---: | ---: | ---: |
| VH1 | 9 | 7 | 23 |
| VH2 | 8 | 7 | 20 |

Therefore, **Lofacimig is no longer sequence-unknown**, but **it remains excluded from the validated 39 clinical single-domain VHH cohort and the VHH42 CMC benchmark** because it is a tandem VH-Fc clinical molecule rather than a single-domain VHH cohort row. Adding it silently to VHH42 would:

- Pollute the canonical clinical VHH cohort.
- Risk incorrect Hallmark / Vernier / CMC statistics.
- Violate the source-discipline rule for sequence claims.

---

## 4. Recommended Cross-Check Path

If independent primary-document confirmation is needed beyond NCATS/GSRS, use this priority:

1. **WHO INN Proposed List 132 (2024)** PDF — usually contains the full amino acid sequence, signal peptide notes, glycosylation, and disulfide map.
2. **Alphamab / Suzhou Alphamab patent family for KN060** on The Lens or Patentscope. The originator typically discloses VH1 and VH2 sequences and the GAP linker.
3. **Thera-SAbDab Lofacimig record** once OPIG service is back up.

After independent cross-check:

1. Save the source PDF or patent record to `data/sequence_provenance/lofacimig_source/` (new folder, not LOCKED).
2. Cross-check against `data/sequence_provenance/lofacimig/lofacimig_ncats_gsrs_full_chain_v1.json`; do not create a clinical39 row unless an explicit governance decision changes the cohort definition.
3. Decide explicitly whether Lofacimig should be promoted into:
   - The validated 39 clinical cohort (it is bispecific and full-Fc, so this is **not** automatic).
   - A separate `vhh_bispecific_with_fc_supplement` cohort.
4. **Do not** silently include Lofacimig in VHH42 CMC stats. The frozen `VHH42_reference_stats_v1.json` is composed of single-domain VHH only; a 493 aa VH-VH-G1 dimer does not belong there without an explicit standard-level decision.

---

## 5. Reconciliation Impact

Current reconciliation status:

- The `master_table_only_no_seq` origin tag for Lofacimig in `VHH_ID_RECONCILIATION.csv` is **expected and accepted**, not an error.
- `cohort_platform_tag` is now `humanized_camelid_tandem_vh_fc`.
- `data/vhh_database/VHH_DATABASE_EXCLUDED_NON_SDVHH_v1.csv` carries Lofacimig as an excluded non-single-domain molecule.
- No VHH42 / clinical39 / camelid68 single-domain calibration counts change.

The entry is **sequence-collected but excluded** from single-domain VHH sequence statistics.

Legacy partial artifact:

- `data/sequence_provenance/lofacimig/lofacimig_vh1_imgt_regions_v1.json` contains the earlier 130 aa VH1-only extraction from in-repo report files.
- The authoritative cleaned artifact is now `lofacimig_ncats_gsrs_full_chain_v1.json`.
