# Anti-Hallucination Policy — Writing Memory MVP

> This document is the **architectural contract** for every LLM call in
> `services/writing_memory/`. Code that violates it must not ship.

The risk in a writing assistant is not "the model writes weird sentences" — it
is **the model invents references, data, mechanisms, or journal preferences
that look authoritative**. We block that at the architecture layer, not at
the prompt layer alone.

---

## 1. Three-layer defence

### Layer A — The LLM is never allowed to generate references

The model output schema does **not** contain a `references[]` field. The only
permitted citation-shaped output is:

```json
{
  "citation_needs": [
    {"topic": "TNF blockade adverse event rate in RA",
     "where_in_text": "sentence 3",
     "status": "CITATION_NEEDED"}
  ]
}
```

Any output containing `pmid`, `doi`, `Journal Year;Vol(Issue):Pages`, or
quoted author names not present in the input must be rejected by the API
layer before reaching the user.

### Layer B — Citations come from the corpus, not the model

If the user requests "find supporting literature for this claim", the
backend:

1. Embeds the claim.
2. Searches the `papers` table via `pgvector` cosine similarity.
3. Returns rows from the database. The model only writes a one-line
   *rationale* per row, not the citation itself.

### Layer C — Server-side re-verification

Before any citation reaches the UI:

- PMID re-verified through `eutils.ncbi.nlm.nih.gov/.../esummary.fcgi`.
- DOI re-verified through `api.crossref.org/works/{doi}`.
- Title-mismatch → flagged `unverified`, hidden from "Insert" button.

Pattern already proven in this repo by `scripts/_fetch_verified_refs.py`.

---

## 2. Numbers, names, mechanisms

Rewrite-style endpoints (`/rewrite`, `/reduce_ai_tone`) operate under the
**no-new-facts** rule:

- The model may not introduce numbers, percentages, p-values, author names,
  drug names, gene symbols, study IDs, or institution names absent from the
  input.
- The system prompt enforces this; the response post-processor re-checks
  by extracting numeric tokens / proper-noun heuristics from input and
  output, and aborting on additions.

Allowed transformations:

- Lexical: replace generic AI vocabulary with discipline-natural verbs.
- Syntactic: split / merge sentences, reorder clauses.
- Rhetorical: align hedge level, claim strength, paragraph pattern to
  target `journal_profile`.

Not allowed:

- Strengthening causal language ("is associated with" → "causes").
- Adding mechanistic claims not present in input.
- "Filling in" missing values from background knowledge.

---

## 3. Journal-profile provenance

Every field inside `journal_profile` JSON must carry:

```json
{
  "value": "...",
  "evidence_paper_count": 27,
  "evidence_paper_ids": [123, 145, ...],
  "verification_status": "verified | inferred | unverified",
  "extracted_at": "ISO8601",
  "profile_version": "0.1.0"
}
```

`verification_status` rules:

| Status | Meaning |
|--------|---------|
| `verified` | Pattern observed in ≥ N papers (N≥10 for MVP) with concrete text evidence. |
| `inferred` | Derived by aggregation but not directly anchored to ≥N texts. |
| `unverified` | Not yet checked; must not appear in user-facing output. |

`reviewer_attack_patterns` are **always** `inferred`. The UI must label them
as **"style-based simulation (inferred)"**, never "prediction".

---

## 4. Forbidden output strings

The API response validator must reject outputs that contain any of:

- Free-form `PMID: <digits>` / `DOI: <string>` not from the corpus.
- Strings matching `(?i)according to .* et al\.`
- Strings matching `(?i)studies have shown that` followed by quantitative
  claim without supporting corpus row.
- Phrases asserting that a specific journal "prefers" or "rejects" content
  without `evidence_paper_count >= 10` in the current profile.

---

## 5. Self-check pass (mandatory)

Every rewrite endpoint runs a **second** LLM call:

```
You are a strict reviewer. Compare INPUT and REWRITE.
Return JSON:
{
  "introduced_numbers": [...],
  "introduced_names":   [...],
  "strengthened_claims":[...],
  "fabricated_citations":[...],
  "verdict": "clean | suspect | reject"
}
```

`verdict == "reject"` → endpoint returns 422 with diagnostic instead of the
rewrite. `suspect` → rewrite shown but flagged in UI.

---

## 6. Audit log

Every LLM call (including self-check) is persisted:

```sql
llm_calls(
  id, endpoint, model, system_prompt_hash, user_input_hash,
  output_hash, latency_ms, prompt_tokens, completion_tokens,
  verdict, created_at
)
```

This is non-negotiable for client-facing deployment.

---

## 7. UI obligations

- A persistent disclaimer: *"This system never generates references. All
  citations come from a verified PMC corpus."*
- Every rewrite shows a small badge with the `journal_profile.version` and
  `evidence_paper_count` it relied on.
- Reviewer simulation panel header text is **fixed**:
  `Style-based reviewer concerns (inferred from corpus, not real peer review)`.

---

## 8. Compliance with existing repo rules

This policy is consistent with, and stricter than:

- `.cursor/rules/response-source-discipline.mdc`
- `.cursor/rules/reliability-adversarial-gate.mdc`
- `.cursor/rules/token-and-external-api-discipline.mdc`

If those rules ever conflict with this document at delivery time, this
document takes precedence **within `services/writing_memory/` only**.
