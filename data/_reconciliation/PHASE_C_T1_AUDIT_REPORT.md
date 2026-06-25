# Phase C — T1 Deep Audit Report

**Scope:** VH/VL IgG cohort + ADA Immunogenicity family  
**Date:** 2026-04-30  
**Status:** AUDIT COMPLETE — action items identified, no data modified

---

## 1. VH/VL IgG Family Findings

### 1.1 Elipovimab and Zinlirvimab — Missing from 842_combined

**Root cause:** Processing omission, not data absence.

| Antibody | VH seq | VL seq | PDB file | In 842_combined |
|---|---|---|---|---|
| Elipovimab | 132 aa | 105 aa | `data/structures/natural/Elipovimab.pdb` | **NO** |
| Zinlirvimab | 132 aa | 108 aa | `data/structures/natural/Zinlirvimab.pdb` | **NO** |

Both antibodies have sequences in `natural_380_atlas/master_table.csv` and PDB files on disk. They were simply not included in the structure metrics run that generated `842_combined_assessment.csv`. The natural cohort in 842_combined is therefore **382 of 384** (98.4% complete).

**Root cause (verified by PDB inspection 2026-04-30):**

| Antibody | Chain H residues (PDB) | Chain L residues (PDB) | Sequence (master_table) | Root Cause |
|---|---|---|---|---|
| Elipovimab | 133 (Fv, with insertion codes 100A/100B) | 108 | VH 132 aa | ANARCI 1-residue count mismatch (PDB 133 vs seq 132); insertion code parsing issue |
| Zinlirvimab | **230** (VH + CH1 — full Fab) | **211** (VL + CL — full Fab) | VH 132 aa | PDB is a full Fab structure, not Fv; structure metrics script requires Fv only |

The structure metrics run that generated 842_combined encountered these same failures and silently skipped both entries. This was not a random omission.

**Required action:**
- **Zinlirvimab:** Extract Fv fragment (residues 1–~128 of chain H, 1–~108 of chain L) from the Fab PDB before re-running structure metrics. Use `pdbfixer` or BioPython with residue-range selection.
- **Elipovimab:** Investigate the ANARCI count mismatch (sequence 132 aa, PDB 133 residues). Likely a non-standard or extra terminal residue. Re-number or trim before re-running.
- After both are resolved, append the 2 new rows to `842_combined_assessment.csv` (bringing the natural cohort to the expected 384) and log in `docs/EVOLUTION_LOG.md` as `[OBSERVATION]`.

### 1.2 Naming Drift (directory vs actual count)

| Directory / file name | Implied count | Actual rows | Delta |
|---|---|---|---|
| `natural_380_atlas/` | 380 | 384 | +4 |
| `engineered_459_atlas/` | 459 | 458 | −1 |

**Required action:** Do not rename directories (breaking change risk). Document the naming drift in `data/_ATLAS_INDEX.md` with a note: "Directory name reflects historical cohort tag; authoritative population count is from master_table.csv row count."

---

## 2. ADA Immunogenicity Family Findings

### 2.1 ADA% Value Mismatches (7 entries)

Seven antibodies show divergent ADA% values between `immunogenicity_panel_136_master.csv` (primary, frozen T1) and `InSynBio_Combined_ADA_Database.csv` (secondary T2).

| Antibody | panel_136 ADA% | combined_db ADA% | Delta | Severity |
|---|---|---|---|---|
| Atoltivimab | 80.0 | 0.0 | 80.0 pp | **CRITICAL** — likely data entry error in combined_db |
| Depemokimab | 95.0 | 10.0 | 85.0 pp | **CRITICAL** — severe discrepancy |
| Rozanolixizumab | 15.0 | 37.0 | 22.0 pp | HIGH |
| Mogamulizumab | 3.9 | 14.1 | 10.2 pp | HIGH |
| Donanemab | 90.0 | 87.0 | 3.0 pp | LOW — likely rounding |
| Relatlimab | 2.0 | 5.6 | 3.6 pp | LOW — different study populations likely |
| Olokizumab | 15.0 | 3.2 | 11.8 pp | HIGH |

**Ruling:** `panel_136` is the frozen T1 source. Its values take precedence. The combined_db values for Atoltivimab and Depemokimab must be traced to their original source and corrected.

**Required action (priority HIGH):**
1. Trace Atoltivimab and Depemokimab combined_db values to original literature or package insert.
2. Update `InSynBio_Combined_ADA_Database.csv` with corrected values, tagging the source.
3. Log the correction in `immunogenicity_knowledge_base/ada_expansion_research_log.md`.

### 2.2 Root ↔ Master Copy Sync Gaps (25 entries)

**9 entries in root-level `ada_master_136_curated.csv` but NOT in IKB master copy:**

| Antibody |
|---|
| Abrezekimab |
| Lemalesomab |
| Lumiliximab |
| Ontamalimab |
| Ozanezumab |
| Sifalimumab |
| Tabalumab |
| Tanezumab |
| Tibulizumab |

**16 entries in IKB master copy but NOT in root-level file:**

| Antibody | | |
|---|---|---|
| Bebtelovimab | Briakinumab | Bermekimab |
| Batoclimab | Narsoplimab | Maftivimab |
| Lenzilumab | Felzartamab | Camidanlumab |
| Oportuzumab | Iparomlimab | Geptanolimab |
| Margetuximab | Monalizumab | Tiragolumab |
| Farletuzumab | | |

**Root cause:** The root-level file (`data/ada_master_136_curated.csv`) and the IKB master copy (`immunogenicity_knowledge_base/master/ada_master_136_curated.csv`) have diverged. They are being maintained independently.

**Required action:**
1. Designate `immunogenicity_knowledge_base/master/ada_master_136_curated.csv` as the **single authoritative master** (it has more entries: 154 vs 147).
2. The root-level `data/ada_master_136_curated.csv` should either be deprecated (replaced by a symlink/redirect note) or regenerated from the master copy.
3. Add 9 root-only entries to the IKB master copy after verifying their metadata is complete.

### 2.3 Panel 136 vs Combined DB Coverage Gaps

| Direction | Count | Entries (sample) |
|---|---|---|
| In panel_136, not in combined_db | 2 | (see ADA_ID_RECONCILIATION.csv) |
| In combined_db, not in panel_136 | 12 | Nipocalimab, Epcoritamab, Elranatamab, Abrezekimab, Lemalesomab ... |

The 12 entries in combined_db but not in panel_136 are likely candidates from batch2/batch3 expansions that have not yet been reviewed for inclusion in the frozen panel.

**Required action:** Schedule a quarterly panel review. Candidates with complete metadata and verified ADA% should be promoted to panel_136 after owner approval.

### 2.4 Curation Gaps (66 entries)

All 66 entries are already documented in `ada_curation_gap_list.csv`. This is a known T3 backlog, not a T1 data quality issue. No immediate action required.

### 2.5 Positive/Negative Separation — PASS

`in_both_positive_and_negative = 0`  
No antibody appears in both the immunogenicity panel (positive cohort) and the negative library. Separation is clean.

---

## 3. Priority Action Matrix

| Priority | Action | Owner | Dataset | Deadline |
|---|---|---|---|---|
| **P1** | Trace and correct Atoltivimab ADA% in combined_db (0.0 → correct value) | Curation | ADA | Next curation sprint |
| **P1** | Trace and correct Depemokimab ADA% in combined_db (10.0 → correct value) | Curation | ADA | Next curation sprint |
| **P2** | Run structure metrics for Elipovimab + Zinlirvimab → append to 842_combined | Engineering | VH/VL | Before next fingerprint extraction |
| **P2** | Designate IKB master as authoritative; sync/deprecate root-level ADA CSV | Curation | ADA | Next curation sprint |
| **P2** | Correct Rozanolixizumab, Mogamulizumab, Olokizumab ADA% in combined_db | Curation | ADA | Next curation sprint |
| **P3** | Add 9 root-only entries to IKB master copy | Curation | ADA | Quarterly review |
| **P3** | Document naming drift in `data/_ATLAS_INDEX.md` | Governance | VH/VL | Next doc pass |
| **P4** | Quarterly panel_136 expansion review (12 combined_db candidates) | Owner | ADA | Quarterly |

---

## 4. Verification Status

- Root cause of 842_combined gap: `[verified]` — PDB files confirmed on disk
- ADA% values in panel_136: `[user-provided]` — curated from literature by team
- ADA% discrepancies in combined_db for Atoltivimab/Depemokimab: `[unverified]` — requires source tracing
- Root vs master copy divergence: `[verified]` — confirmed by row-level cross-walk

## 5. Adversarial Checks

- **Alternative explanation for 842_combined gap:** Elipovimab and Zinlirvimab PDB files may not parse correctly with the structure metrics script. — `PASS (resolved)`: PDB inspection confirmed specific root causes (Zinlirvimab = Fab, Elipovimab = ANARCI count mismatch). Chain IDs H/L are correct in both.
- **Failure mode for ADA% correction:** Updating combined_db without tracing the exact source could introduce a different error. — `PASS`: correction requires source citation.
- **Boundary assumption:** panel_136 is treated as ground truth; if panel values are themselves from a single study with small N, the delta vs. combined_db may reflect legitimate population differences rather than data errors. — `WARN`: Atoltivimab (0.0 in combined_db) is still implausible and warrants review regardless.

## 6. Sources

- `data/_reconciliation/ADA_ID_RECONCILIATION.csv` — cross-walk artifact `[verified]`
- `data/_reconciliation/VHVL_IGG_ID_RECONCILIATION.csv` — cross-walk artifact `[verified]`
- `data/natural_380_atlas/master_table.csv` — sequence and PDB path source `[verified]`
