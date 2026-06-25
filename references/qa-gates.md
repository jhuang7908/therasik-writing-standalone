# QA Gates

## AI Usage Boundary (Traffic Light)

Apply this boundary before any manuscript section is drafted or revised.

**Green — acceptable with author verification:**
- improve grammar, clarity, concision, or tone
- generate outline options or paragraph structures
- produce alternative titles or abstract phrasings
- summarize literature for categorization (not as a substitute for reading)
- translate with terminology and hedging checks

**Yellow — allowed only with strong human control:**
- explain methods or results for wording support
- draft reviewer-response frameworks that are then checked line by line
- help with code or statistics explanations only if outputs are reproduced and validated

**Red — block; do not proceed:**
- ask AI to draft the paper's core scientific argument from scratch
- insert AI-generated references, data, or claims without verification
- upload unpublished manuscripts or peer-review material to public models
- fabricate, manipulate, or conceal substantive image creation

Block release when a Red action is detected in any manuscript section.

## Evidence and Reference QA

Block release when:

- a cited reference lacks DOI, PMID, PMCID, or URL unless manually justified
- a DOI/PMID belongs to a different paper
- duplicate DOI appears for different references
- a claim is not supported by its citation
- references are relevant only topically but not evidentially
- citation order or insertion does not match journal requirements

For each major claim, the QA report must include a claim-evidence entry:

    Claim: <one-sentence statement>
    Evidence: <source identifier and page/figure>
    Status: supported | needs evidence | weak | contradicted

Release is blocked when any claim has Status other than "supported".

## Manuscript QA

Block release when:

- text reads as instructions, checklist, report, or self-commentary instead of review prose
- title is generic, overlong, or mismatched to target journal
- paragraph rhythm is overly fragmented or uniformly AI-like
- no explicit thesis, negative recommendation, or stop-rule exists in sparse-evidence reviews
- retargeted manuscript only changes journal format without conceptual repositioning
- author voice is absent where an expert Perspective/Review requires judgment

Recommended section writing order (revise in this sequence to keep argument coherent):
Results → Introduction → Title → Discussion → Methods → Abstract

## Figure and Table QA

### Figure Contract (required before any figure is generated or accepted)

Each figure must have a declared contract before plotting or acceptance. Block release when any figure lacks:

- **Core conclusion**: the one-sentence claim this figure must defend
- **Evidence chain**: each panel mapped to one piece of evidence; panels that carry no unique evidence are dropped
- **Export contract**: final dimensions, editable text requirement (SVG/PDF with editable text layers), source data traceability, statistics and n values, image-integrity note

Block release when:

- figure does not support the manuscript argument
- figure is decorative rather than explanatory
- figure is visually attractive but scientifically vague
- figure text is unreadable or too dense
- figure/caption contradicts manuscript claims
- table is prose disguised as a table
- table columns are not comparable
- figure/table is not cited in text
- figure contract is missing or incomplete

## Reviewer Simulation Red Lines

When a reviewer simulation is run as part of pre-submission QA, block delivery when:

- reviewer identity, specialty, institution, or biography is invented rather than derived from the manuscript
- experiments, validations, controls, citations, or figure details are invented (not present in input)
- reviewer assessment is silently converted into author rebuttal drafting
- assessment claims editorial certainty ("this belongs in Nature") without a source-bounded basis
- technical failings are omitted when provided evidence does not establish the authors' case

## Format and Render QA

Block release when:

- DOCX lacks required line numbers, spacing, alignment, tables, or figure insertion
- PDF cannot be rendered
- any page is blank or corrupt
- figures are clipped, tiny, blurry, or misplaced
- tables clip or lack readable padding
- front matter required by journal is missing

## Human Gates

These are not machine failures but still block final submission:

- author names and affiliations
- corresponding author details
- funding
- conflict of interest
- author contributions / CRediT
- ethics statements when applicable
- external domain expert sign-off when scientific risk is high
- author confirmation of workflow execution audit
