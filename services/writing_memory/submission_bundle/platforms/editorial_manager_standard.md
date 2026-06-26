# Editorial Manager — Platform-Level Standard Requirements

**Scope:** Technical requirements that apply across all journals using Editorial Manager (Aries Systems / Wolters Kluwer).  
**NOT included:** Journal-specific word counts, figure limits — get those from each journal's author guidelines.  
**Last verified:** 2026-06 (platform-level; journal-level requires separate verification)  
**Source:** https://www.ariessys.com/editorial-manager/ | https://www.editorialmanager.com/

---

## Supported File Formats (upload)

| Role | Accepted formats | Notes |
|---|---|---|
| Manuscript | DOCX, RTF, LaTeX, PDF | DOCX preferred; LaTeX accepted by most EM journals |
| Figures (separate) | TIFF, EPS, PDF, PNG, JPEG | Uploaded as individual files; EM compiles them into proof PDF |
| Supplementary | DOCX, PDF, XLSX, CSV, MP4, MOV, ZIP | Max per-file typically 50 MB; varies by journal |
| Cover letter | Typed in portal text box OR uploaded as DOCX/PDF | |
| Response letter | DOCX, PDF | For revision submissions only |

---

## Technical File Specs

| Parameter | Requirement |
|---|---|
| Max manuscript file size | ~50 MB (check per journal configuration) |
| Figure resolution (halftone/photo) | ≥ 300 dpi at print size |
| Figure resolution (line art) | ≥ 1000 dpi at print size |
| Figure resolution (combination) | ≥ 600 dpi |
| Preferred figure width (1-col) | 85–90 mm |
| Preferred figure width (2-col) | 170–180 mm |
| Font in figures | ≥ 8 pt at final print size |
| Color mode | RGB acceptable for submission; CMYK may be needed for revision |

---

## Manuscript Formatting (platform minimum)

- Line numbers: **enabled** (add via Word → Layout → Line Numbers → Continuous)
- Spacing: **double-spaced** body text (check journal; some allow single-spaced tables)
- Page numbers: **required** (footer recommended)
- Font: 12 pt serif or sans-serif (check journal)
- Margins: ≥ 2.5 cm all sides

---

## Upload Workflow (standard)

1. Go to journal's EM URL (e.g., `https://www.editorialmanager.com/{journal}/`)
2. Register or log in → "Submit New Manuscript"
3. **Article Type** selection (determines subsequent required fields and word-limit checks)
4. **Attributes** — subject categories, funding, data availability
5. **Authors** — add all co-authors in order; ORCID entry available
6. **Reviewer suggestions** — suggest/exclude optional (some journals require ≥3 suggestions)
7. **File upload** — drag-and-drop interface; EM rebuilds into single proof PDF
8. **Additional information** — COI, ethics, cover letter text box
9. **Review PDF** — system-compiled; approve before submit

**Common failure points:**
- "Build PDF" error — usually caused by special characters or non-standard fonts in DOCX; re-save as RTF and retry
- Figure color space issue (CMYK TIFF fails in some EM configurations) — convert to RGB before upload
- LaTeX: ensure all .cls/.sty files are zipped together with the .tex file
- Wrong article type selection (cannot change after submission — contact editorial office)

---

## Required Metadata Fields (all EM journals)

| Field | Source |
|---|---|
| Title | Manuscript §1 |
| Short title / running head | ≤ 50 characters (check journal) |
| Abstract | Plain text (no sub-headings unless structured abstract required) |
| Keywords | 3–6 (check journal; usually semicolon-separated) |
| All author names + affiliations | First name, Last name, Institution, Country, Email |
| Corresponding author | Designated in EM + must match manuscript title page |
| Funding | All funders + grant numbers |
| COI / competing interests | Text field |
| Data availability | Required at many EM journals (especially Elsevier/PLOS) |

---

## Revision Submission (EM-specific)

When responding to reviewers:
1. Log in → "Submissions with Decisions" → "Revise Submission"
2. Upload **revised manuscript** (tracked changes OR clean — per journal instructions)
3. Upload **response to reviewers letter** (DOCX or PDF)
4. Upload **marked-up version** if required (check decision letter)
5. Re-upload updated **figures** if changed
6. Complete COI/ethics attestation if re-prompted

---

## Integration with InSynBio Toolchain

```powershell
# 1. Build submission bundle
python scripts/build_submission_bundle.py --profile <profile_id> --workspace paper/Submission_Package

# 2. Audit before upload
python scripts/build_submission_bundle.py --profile <profile_id> --workspace paper/Submission_Package --audit-only

# 3. Identify journal's system + guidelines
python scripts/insynbio_submission_system.py identify "<Journal Name>"
python scripts/insynbio_submission_system.py checklist "<Journal Name>"

# 4. Scaffold new profile for this journal
python scripts/insynbio_submission_system.py new-profile "<Journal Name>" --type research
```

---

*Word counts, figure limits, and required sections are JOURNAL-level requirements.  
Always verify at the journal's official "Guide for Authors" / "Author Guidelines" page.*
