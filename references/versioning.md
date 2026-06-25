# Version Management

## Skill Lifecycle States

A skill moves through the following states. Only skills in **Verified** or **Released** state should be used in production manuscript workflows.

| State | Code | Meaning |
|---|---|---|
| Raw | S0 | Imported or created; not yet reviewed |
| Candidate | S1 | Under active evaluation; may have gaps |
| Draft | S2 | Structure is stable; QA not yet complete |
| Verified | S3 | All QA gates pass; peer-reviewed by at least one reviewer |
| Released | S4 | Approved for production use |
| Degraded | S5 | Recurring failures detected; active investigation required |
| Deprecated | S6 | Superseded by a newer version; no new projects |
| Archived | S7 | Frozen; no further updates |

Rules:
- Do not release a skill directly from Draft. It must pass Verified first.
- A skill becomes Degraded automatically when two or more QA regressions occur in the same gate within one version cycle.
- The `lifecycle_state` field in `skill_version_manifest.json` must match this table.
- Record every lifecycle transition in `version_ledger.jsonl` with `change_type: lifecycle_transition`.

## Version Objects

Track four independent versions:

- manuscript version: `draft_v1`, `draft_v2`, `submission_draft_v1`
- workflow version: `workflow_YYYY-MM-DD`
- QA rules version: `qa_rules_YYYY-MM-DD`
- skill version: `skill_semver`

## Required Version Ledger Fields

Use `version_ledger.jsonl` with one JSON object per change:

```json
{
  "timestamp": "2026-06-25T00:00:00Z",
  "object_type": "manuscript|skill|workflow|qa_rule|figure|database",
  "object_id": "string",
  "old_version": "string|null",
  "new_version": "string",
  "change_type": "create|revise|fix|qa_gate_added|qa_gate_failed|qa_gate_passed",
  "reason": "string",
  "source": "user_feedback|expert_review|qa_failure|new_article|system_refactor",
  "files_changed": ["path"],
  "qa_status_after_change": "PASS|FAIL|HUMAN_PENDING|NOT_RUN"
}
```

## Rules

- Never overwrite a major manuscript without saving a new version.
- Record every QA failure that caused a rule change.
- Record every user criticism as a learning event when it changes workflow behavior.
- Do not mark a skill improved unless a real workflow or validation run uses the improvement.
- Keep project-specific lessons separate from generalizable skill rules.

## Naming

- Manuscript source: `{topic}_{journal}_draft_vN.md`
- Submission DOCX: `{topic}_{journal}_SUBMISSION_DRAFT_vN.docx`
- QA report: `{gate_name}_QA.md`
- Workflow audit: `workflow_execution_audit_vN.json`
- Skill ledger: `version_ledger.jsonl`

