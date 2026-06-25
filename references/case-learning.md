# Case Learning Protocol

## Trigger

Use this protocol whenever the user, an expert, or a reviewer identifies a problem that was not prevented by the workflow.

## Steps

1. Classify the failure.
2. Decide whether it is project-specific or generalizable.
3. If generalizable, add or revise a QA gate.
4. Add a regression check so the same error cannot silently pass again.
5. Record the change in `version_ledger.jsonl`.
6. Rerun the affected workflow.

## Failure Classes

- hallucinated reference
- irrelevant reference
- weak claim support
- AI-style prose
- fragmented paragraph rhythm
- generic title
- retargeting without conceptual change
- lack of expert voice
- missing figure argument
- visually attractive but scientifically weak figure
- poor table structure
- missing render QA
- skipped workflow step
- author ownership missing
- external expert needed

## Promotion Rule

Do not promote one article-specific fix into a global rule unless it is likely to recur across manuscripts.

## Regression Examples

- If a manuscript passes while paragraph rhythm is AI-like, add paragraph statistics QA.
- If a manuscript passes while retargeted from another journal, add retargeting originality QA.
- If a sparse-evidence review lacks hard judgments, add expert detectability QA.
- If a workflow step was skipped, add workflow execution audit QA.

