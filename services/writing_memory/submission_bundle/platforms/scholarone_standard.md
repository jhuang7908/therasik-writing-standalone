# ScholarOne Manuscripts — Platform-Level Standard Requirements

**Scope:** Technical requirements that apply across all journals using ScholarOne (Clarivate).  
**NOT included:** Journal-specific word counts, figure limits — get those from each journal's author guidelines.  
**Last verified:** 2026-06 (platform-level; journal-level requires separate verification)  
**Source:** https://clarivate.com/products/scientific-and-academic-research/research-publishing-solutions/scholarone/

---

## Supported File Formats (upload)

| Role | Accepted formats | Notes |
|---|---|---|
| Manuscript | DOCX, RTF, LaTeX (.tex + .bbl), PDF | DOCX strongly preferred; PDF often accepted for initial submission only |
| Figures (separate) | TIFF, EPS, PDF, PNG, JPEG | TIFF/EPS required for production; JPEG acceptable for review only |
| Supplementary | DOCX, PDF, XLSX, MP4, MOV | Max per-file: 50 MB (varies); ZIP allowed for multiple files |
| Cover letter | DOCX, PDF, or typed in portal text box | |
| Blinded manuscript | Same formats; author info removed | Required for double-blind review journals |

---

## Technical File Specs

| Parameter | Requirement |
|---|---|
| Max manuscript file size | ~50 MB (check per journal) |
| Figure resolution (halftone/photo) | ≥ 300 dpi at print size |
| Figure resolution (line art) | ≥ 1000 dpi at print size |
| Figure resolution (combination) | ≥ 600 dpi |
| Preferred figure width (1-col) | 85–90 mm |
| Preferred figure width (2-col) | 170–180 mm |
| Font in figures | Arial or Helvetica recommended; ≥ 8 pt at final size |
| Color mode | RGB for online; CMYK for print (check journal) |

---

## Manuscript Formatting (platform minimum)

These are the **minimum** formatting requirements ScholarOne accepts. Most journals specify stricter requirements in their author guidelines.

- Line numbers: **enabled** (most journals require; add via Word → Layout → Line Numbers)
- Spacing: **double-spaced** (unless journal specifies otherwise)
- Page numbers: **required**
- Font: 12 pt Times New Roman or Arial (check journal)
- Margins: ≥ 2.5 cm all sides

---

## Upload Workflow (standard)

1. Log in → "Author Center" → "Submit New Manuscript"
2. Select **Article Type** (must match what you'll describe in cover letter)
3. **Step 1** — Title, Abstract, Keywords (type directly into portal — do NOT paste from DOCX with formatting)
4. **Step 2** — Attributes (subject area, specialty, funding info)
5. **Step 3** — Authors (all co-authors must be added; ORCID recommended)
6. **Step 4** — Reviewers (suggest ≥3; exclude if needed)
7. **Step 5** — Details & Comments (cover letter text or upload)
8. **Step 6** — File upload (manuscript + figures + supplementary in required order)
9. **Step 7** — Review & Submit → check compiled PDF proof → submit

**Common failure points:**
- Special characters in title/abstract (paste as plain text then reformat)
- Figure file too large (compress TIFF: LZW lossless)
- Missing author ORCID (add before submission if journal requires)
- Wrong article type (changes available sections and word limit checks)

---

## Required Metadata Fields (all ScholarOne journals)

| Field | Source |
|---|---|
| Title | Manuscript §1 |
| Running title (short) | ≤ 50 characters — check journal limit |
| Abstract | Manuscript §Abstract; plain text only |
| Keywords | 3–8 keywords, semicolon-separated (check journal) |
| All author names | First, last, institutional affiliation, email |
| Corresponding author email | Clearly designated |
| Funding sources | All funders + grant numbers |
| COI statement | Text field — paste from manuscript |

---

## After Submission

- Download **PDF proof** (system-compiled) — verify figures are legible
- Note **manuscript ID** (e.g., AT-2025-XXXX) — required for all follow-up
- Expect automated acknowledgment email within minutes
- Editorial decision timeline: varies (2 weeks – 6 months)

---

## Integration with InSynBio Toolchain

```powershell
# 1. Build submission bundle
python scripts/build_submission_bundle.py --profile <profile_id> --workspace paper/Submission_Package

# 2. Audit before upload
python scripts/build_submission_bundle.py --profile <profile_id> --workspace paper/Submission_Package --audit-only

# 3. Check journal's specific requirements
python scripts/insynbio_submission_system.py checklist "<Journal Name>"

# 4. OA policy
python scripts/insynbio_journal_format.py oa-policy "<Journal Name>"
```

---

*Word counts, figure limits, and specific required sections are JOURNAL-level requirements.  
Always verify at the journal's official author guidelines page before submitting.*
