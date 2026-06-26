<!-- version: qa_rules_2026-06-26b | last_updated: 2026-06-26 | changed: Evidence and Reference QA (+4 rules); Citation Abstract Verification (completed + extended); Manuscript QA AI markers (expanded); Multi-Expert Reviewer QA (new section); Citation Insertion Pre-Commit Checklist (new section); Reference Renumbering Integrity (new rule) -->
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
- reference list contains entries with no corresponding in-text citation (floating/uncited references); count must be zero before submission
- reference list contains non-reference content such as editor notes, word counts, or revision markers
- BIB/RIS source file diverges from the DOCX reference list after any manual edits (re-export or manually sync before final render)
- a citation is inserted at a sentence that does not match the paper's subject matter (topically misplaced citation)

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

### AI Writing Style Detection

AI-generated prose has recognizable fingerprints. Flag and block release when three or more of the following are detected in any 500-word window:

**Structural markers:**
- bullet lists embedded in prose where continuous argument is expected
- numbered sub-arguments inside a paragraph (1. ... 2. ... 3. ...)
- section-opening "topic sentence + three supporting bullets" pattern
- self-referential commentary ("In this section, we discuss...", "As described above...")
- Markdown syntax in DOCX body (**, ##, ^, ---, \*, -)

**Lexical markers:**
- overused transitions: "furthermore", "moreover", "notably", "importantly", "it is worth noting", "it is crucial", "it is important to emphasize"
- AI intensifiers: "delves into", "underscores", "highlights the importance of", "paves the way for"
- uniform hedging: every claim ends with "suggesting that" or "indicating that" with no variation
- absence of field-specific jargon where domain experts would naturally use it

**Epistemic markers:**
- claims stated without competing interpretation or acknowledged limitation
- no negative results or null hypotheses discussed where data warrant them
- absence of first-person expert judgment in Perspective/Opinion articles
- every sentence in a paragraph has equal grammatical weight (no topic-sentence hierarchy)

**Sentence rhythm markers (machine-checkable via insynbio_polishing.py):**
- mean sentence length between 18–24 words with SD < 6 (uniform rhythm)
- fewer than 10% of sentences are fewer than 10 words or more than 35 words
- passive voice rate > 60% in Methods; > 40% in Results or Discussion

Run `python scripts/insynbio_polishing.py` on each section. Block release if AI marker count exceeds threshold (default: 3 markers per 500-word window). Record per-section output in the QA report.

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

## Citation Abstract Verification in Network-Constrained Environments

When the sandbox cannot reach PubMed, CrossRef, or Semantic Scholar (network blocked or rate-limited):

- Do NOT mark citation status as FAIL solely because abstracts cannot be fetched. Use status `CANNOT_VERIFY_IN_SANDBOX` instead.
- Do NOT skip the citation step. Record which DOIs were attempted, which succeeded, and which are blocked.
- DO mark the overall Citation Verifier gate as `HUMAN_PENDING` (not PASS) and flag it as a required author action before submission.

**Author local verification instructions:**

For each DOI with status `CANNOT_VERIFY_IN_SANDBOX`:

1. Run locally: `python scripts/literature_db.py add-doi <DOI>` (fetches abstract from PubMed/CrossRef)
2. After all DOIs imported: `python scripts/citation_verifier.py --project <project_dir>`
3. Review citations with overlap score < 0.15 manually — these are high-risk for relevance errors.
4. Resolve any FAIL items before submission.

**Sandbox workaround (partial):**

If Semantic Scholar is accessible (not rate-limited), use:
`GET https://api.semanticscholar.org/graph/v1/paper/DOI:{doi}?fields=abstract,title`

Batch size ≤ 5 requests at a time to avoid rate limiting. Record partial results.

## Multi-Expert Reviewer QA

Block release when:

- any expert reviewer (domain, editor, statistician, or biostatistician) returns one or more MAJOR or CRITICAL findings that have not been addressed or explicitly acknowledged as limitations
- the statistician reviewer returns a score below 7/10 without documented author response to each flagged item
- reviewer simulation output is not included in the QA bundle

When all reviewer findings are resolved or formally acknowledged in the manuscript, mark the gate PASS with a per-reviewer resolution summary.

## Citation Insertion Pre-Commit Checklist

When inserting a reference into the manuscript body (especially when citing previously floating/uncited references), apply this checklist before saving:

1. **Sentence-level match**: Does the cited paper's primary finding or conclusion directly support the specific claim in the sentence? (Topic-level match is insufficient — the paper must be evidential for the sentence.)
2. **Subject match**: Is the paper about the same biological entity, therapeutic modality, or experimental system as the sentence? (e.g., do not cite an EpCAM BiTE paper at a sentence about NKG2D-targeting; do not cite a CAR-macrophage paper at a sentence about expression profiles.)
3. **No double-citation**: Is this ref already cited at another sentence that makes the identical claim?
4. **Relevance tier**: Mark each inserted citation as one of:
   - `EVIDENTIAL` — paper directly proves or measures the claim
   - `TOPICAL` — paper is thematically related but does not directly prove the claim
   - `REVIEW` — paper is a review citing primary literature; secondary evidence only
   Block release if any citation is rated `TOPICAL` or `REVIEW` for a quantitative or mechanistic claim.
5. **No orphan**: After insertion, verify the ref appears in the reference list and all list entries are numbered sequentially.

## Reference Renumbering Integrity

When references are added to or deleted from the reference list mid-workflow:

- Block release when any in-text citation number does not correspond to the correct reference list entry.
- After any deletion or insertion, run a full renumbering check: compare every `(N)` in body text against position N in the reference list.
- If more than three references are renumbered in a single edit, render a new PDF and spot-check 5 randomly selected citation groups.
- Record the renumbering event in `version_ledger.jsonl` with `change_type: fix` and list all affected citation numbers.
- Synchronize BIB/RIS after every renumbering event.