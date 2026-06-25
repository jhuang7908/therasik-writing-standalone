# VHH cohort definitions — unified terminology (file-derived)

**Purpose:** One glossary so oral shorthand (“ /  /  / ”) maps to **measurable artifacts**. Numbers below must match the latest `scripts/audit_vhh_cohort_counts.py` run unless files change.

**Machine snapshot:** `data/_reconciliation/vhh_cohort_counts_snapshot.json` (regenerate after cohort edits).

```powershell
python scripts/audit_vhh_cohort_counts.py --json-out data/_reconciliation/vhh_cohort_counts_snapshot.json
```

---

## Canonical counts (current frozen files)

| Label | n | Primary SSOT file(s) |
| --- | ---:| --- |
| **Validated clinical sequences** | **39** | `data/vhh_clinical_39_union/vhh_39_sequences_clinical_validated.json` |
| **Clinical atlas master rows** | **40** | `data/vhh_39_clinical_atlas/master_table.csv` |
| **Atlas-only (not single-domain VHH cohort)** | **1** | Same CSV row **Lofacimig** — full 493 aa chain collected, but excluded from single-domain VHH stats; see `LOFACIMIG_STATUS.md` |
| **VHH42 per-sequence CMC table** | **42** | `data/vhh_clinical_39_union/vhh42_cmc_metrics.csv` |
| **… of which clinical-side rows** | **39** | Same CSV — names aligned with validated cohort (not Lofacimig) |
| **… of which Database-B supplement rows** | **3** | `data/vhh_clinical_39_union/vhh42_sabdab_supplement.json` (`1yzz_A`, `3eak_A`, `6rnk_B`); these are **Database-B rows with a VHH42 role**, not a separate entity class |
| **VHH68 / structural union (models + CMC row union)** | **69** | `data/vhh_structural_union/vhh68_special_cmc_results.json`, `vhh_structural_union_index.json` |
| **… clinical bucket** (`clinical_vhh_immunbuilder`) | **40** | Includes **Porustobart** and **Erfonrilimab-VHH2** in JSON (`source_set` does **not** encode mouse vs camelid) |
| **… Database-B bucket** (`database_b_humanized_camelid_nanobuilder`) | **29** | Includes the **same three** PDB chains used as VHH42 supplement — **no extra identities** |

**Arithmetic check:** 39 (validated clinical sequences) + 1 (Lofacimig metadata row) = **40** atlas rows.  
**VHH68:** 40 + 29 = **69** rows in `vhh68_special_cmc_results.json`.

---

## Terminology — what *not* to conflate

| Phrase | Meaning in this repo |
| --- | --- |
| “ VHH” (sequence pipelines) | Use `entity_class = clinical_single_domain_vhh` for clinical single-domain VHH rows after platform split. This includes **Erfonrilimab-VHH2** even though it is structural-union-only, and excludes separately tagged **Porustobart** (`transgenic_mouse_nanobody_vhh`) and **Lofacimig** (`humanized_camelid_tandem_vh_fc`). |
| “ VHH” | Ambiguous and should **not** be used as a cohort count by itself. The 3 VHH42 supplement rows (`1yzz_A`, `3eak_A`, `6rnk_B`) are **Database-B engineered/humanized camelid VHH** rows with `vhh42_role = vhh42_database_b_supplement`; they are **not clinical VHH** and not a separate entity class. If you mean “any humanized therapeutic”, define an INN-level list externally. |
| “ / Database-B” | **29** identities in the current Database-B manifest used with structural union (`database_b_manifest_29.json` naming). Same **29** rows as the Database-B bucket in VHH68 JSON. |
| “” | **Porustobart** is the usual comparator (transgenic mouse platform). In JSON it sits under **`clinical_vhh_immunbuilder`** — **platform is not a separate `source_set`**. Cite INN / reconciliation notes when claiming platform. |

---

## Drift control

1. After adding/removing sequences, rerun **`audit_vhh_cohort_counts.py`** and commit the new snapshot JSON.
2. **`config/abenginecore_registry.json`** may still describe **28** Database-B entries in prose — treat as **documentation drift** until an owner-approved registry sync; **ground truth is the files listed above**.

---

## Lofacimig — sequence status (authoritative)

- **Full 493 aa heavy-chain sequence has been collected** from NCATS/GSRS API and cleaned under `data/sequence_provenance/lofacimig/`.
- **`vhh_39_sequences_clinical_validated.*`** deliberately **excludes** Lofacimig because it is a tandem VH-Fc molecule, not a single-domain VHH cohort row.

So: **sequence-collected**, but **not part of this suite’s validated clinical single-domain VHH list**.

---

## Nanobody / transgenic-mouse platform — who is marked?

**Frozen SSOT for explicit tags:** `data/vhh_structural_union/vhh_platform_labels_v1.json`

| Display ID | `cohort_platform_tag` | Meaning in suite |
| --- | --- | --- |
| **Porustobart** | `transgenic_mouse_nanobody` | Only id in the **69-row** structural/CMC union **explicitly** tagged as **transgenic mouse** nanobody comparator (matches VHH68 `_meta` platform exclusion policy). |
| **Lofacimig** | `humanized_camelid_tandem_vh_fc` | Humanized camelid-derived tandem VH-Fc clinical molecule; **not** a mouse/VHH platform tag and **not** a validated single-domain VHH cohort row. |
| *(all other rows)* | *(empty)* | Not labeled mouse nanobody here; default assumptions in `vhh_platform_labels_v1.json` `_meta.defaults`. |

**Reconciliation export:** column **`cohort_platform_tag`** in `VHH_ID_RECONCILIATION.csv` (filled from the sidecar).

---

## Related artifacts

- Identity cross-walk: `VHH_ID_RECONCILIATION.csv` / `.json` (generator `scripts/reconciliation/build_vhh_id_reconciliation.py`).
- Platform sidecar: `data/vhh_structural_union/vhh_platform_labels_v1.json`.
- Lofacimig policy: `LOFACIMIG_STATUS.md`.
