# Cat (*Felis catus*) constant regions — SSOT directory

**Authoritative status report:** [`CAT_CONSTANT_STATUS.md`](./CAT_CONSTANT_STATUS.md)

## Files

| File | Content | Status |
|------|---------|--------|
| `IGHC_cat.fasta` | Heavy chain: **IgG1a**, **IgG1b**, **IgG2** (335 aa each; NCBI accessions in headers) | Verified |
| `IGKC_cat.fasta` | κ light chain constant (107 aa) | Verified |
| `IGLC_cat.fasta` | λ constant **IGLC1\*01** (106 aa, IMGT000038) | Verified |
| `cat_constant_regions_verified.fasta` | Legacy bundle (IgG2 + IGKC snapshots) | See CAT_CONSTANT_STATUS |

## Effector-oriented selection (qualitative)

There is **no in-repo ADCC titre database** — only sequences plus operational notes in `CAT_CONSTANT_STATUS.md`.

- **Effector-silent / default therapeutic Fc:** prefer **wild-type IgG2** (`cat_IgG2` in `IGHC_cat.fasta`).
- **Higher classical effector potential:** IgG1a / IgG1b wild-types (project-specific; assay-backed decisions outside this repo).

## Dual-track felinization (engineering)

See **`docs/PETIZATION_CAT_DUAL_TRACK_V1.md`**: Track A (canine VH + feline VL) vs Track B (full-feline Fv from cat scaffold registry).

## Deprecated sections

Older text in this README claiming “IGLC missing” or “IGHC incomplete” is **obsolete** — use `CAT_CONSTANT_STATUS.md` as single source of truth.
