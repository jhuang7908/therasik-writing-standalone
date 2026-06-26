#!/usr/bin/env python3
"""
InSynBio Submission Writer — submission-critical text generators.

Subcommands:
  abstract        Structured abstract builder (5-section, word-counted)
  highlights      Journal highlights / key-points generator (5-9 bullets)
  cover-letter    Cover letter template per journal type
  response        Response-to-reviewers letter scaffold
  data-statement  FAIR data availability statement generator

Usage:
  python scripts/insynbio_submission_writer.py abstract --spec specs/abstract_spec.json --journal at --out paper/abstract.md
  python scripts/insynbio_submission_writer.py highlights --manuscript paper/manuscript.md --journal at --out paper/highlights.md
  python scripts/insynbio_submission_writer.py cover-letter --spec specs/cover_spec.json --journal at --out paper/cover_letter.md
  python scripts/insynbio_submission_writer.py response --spec specs/response_spec.json --out paper/response_letter.md
  python scripts/insynbio_submission_writer.py data-statement --spec specs/data_spec.json --journal at --out paper/data_statement.md

Anti-hallucination contract:
  - Abstract content must be provided in spec; this tool structures and word-counts, never invents results.
  - Highlights must be extracted from user-provided manuscript text; not generated from nothing.
  - Cover letter uses a template; all factual fields must be provided by the user.
  - Data statement uses provided accession numbers and repository URLs; never generates fake identifiers.
"""
from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path


# ── Journal presets ───────────────────────────────────────────────────────────

JOURNAL_PRESETS: dict[str, dict] = {
    "at": {
        "name": "Antibody Therapeutics",
        "publisher": "Oxford University Press",
        "issn": "2516-4236",
        "submission_url": "https://mc.manuscriptcentral.com/antibodytherapeutics",
        "abstract_type": "structured",
        "abstract_sections": ["Background", "Objective", "Methods", "Results", "Conclusion"],
        "abstract_word_limit": 250,
        "highlights_count": (5, 9),
        "highlights_char_limit": 85,
        "cover_letter_tone": "formal_invited",
        "editor_title": "Editor-in-Chief",
        "types": ["Review", "Research Article", "Letter", "Commentary"],
        "notes": "AT is fully OA (APC £1,750). Invited reviews do not require article type selection.",
    },
    "nature_methods": {
        "name": "Nature Methods",
        "publisher": "Nature Portfolio / Springer Nature",
        "issn": "1548-7091",
        "submission_url": "https://mts-nmeth.nature.com/",
        "abstract_type": "unstructured",
        "abstract_sections": ["Single paragraph"],
        "abstract_word_limit": 150,
        "highlights_count": (3, 5),
        "highlights_char_limit": 85,
        "cover_letter_tone": "formal",
        "editor_title": "Editor",
        "types": ["Article", "Brief Communication", "Correspondence"],
        "notes": "Nature Methods does not use Highlights; Key Points used instead.",
    },
    "cell": {
        "name": "Cell",
        "publisher": "Cell Press / Elsevier",
        "issn": "0092-8674",
        "submission_url": "https://www.editorialmanager.com/cell/",
        "abstract_type": "structured",
        "abstract_sections": ["Background", "Findings", "Conclusions and Significance"],
        "abstract_word_limit": 150,
        "highlights_count": (4, 4),
        "highlights_char_limit": 85,
        "cover_letter_tone": "formal",
        "editor_title": "Senior Editor",
        "types": ["Article", "Short Article", "Resource"],
        "notes": "Cell Highlights must be exactly 4 bullets.",
    },
    "plos_biol": {
        "name": "PLOS Biology",
        "publisher": "Public Library of Science",
        "issn": "1544-9173",
        "submission_url": "https://www.editorialmanager.com/pbiology/",
        "abstract_type": "structured",
        "abstract_sections": ["Background", "Methodology and Principal Findings", "Conclusions and Significance"],
        "abstract_word_limit": 300,
        "highlights_count": (3, 5),
        "highlights_char_limit": 120,
        "cover_letter_tone": "semi_formal",
        "editor_title": "Editor",
        "types": ["Research Article", "Methods and Resources", "Essay", "Short Report"],
        "notes": "PLOS Biology uses a community-led author summary (~150 words) in addition.",
    },
    "generic": {
        "name": "Journal (generic)",
        "publisher": "Unknown",
        "issn": "",
        "submission_url": "",
        "abstract_type": "structured",
        "abstract_sections": ["Background", "Objective", "Methods", "Results", "Conclusion"],
        "abstract_word_limit": 250,
        "highlights_count": (3, 6),
        "highlights_char_limit": 85,
        "cover_letter_tone": "formal",
        "editor_title": "Editor",
        "types": ["Article", "Review"],
        "notes": "",
    },
}


def _count_words(text: str) -> int:
    return len(re.sub(r"\s+", " ", text.strip()).split())


def _get_preset(journal: str) -> dict:
    return JOURNAL_PRESETS.get(journal.lower().replace("-", "_").replace(" ", "_"),
                               JOURNAL_PRESETS["generic"])


# ── Abstract ─────────────────────────────────────────────────────────────────

ABSTRACT_SPEC_TEMPLATE = {
    "_warning": "Fill all FILL_ME fields. Do NOT invent content — every sentence must reflect actual manuscript data.",
    "title": "FILL_ME: Full manuscript title",
    "article_type": "FILL_ME: review | original_article | letter | methods",
    "journal": "at",
    "sections": {
        "Background": "FILL_ME: 2-3 sentences on the clinical/scientific problem and why it matters",
        "Objective": "FILL_ME: 1-2 sentences on the specific aim of this paper",
        "Methods": "FILL_ME: key methods used (datasets, algorithms, experimental approaches)",
        "Results": "FILL_ME: key quantitative findings with numbers — do NOT summarize qualitatively only",
        "Conclusion": "FILL_ME: 1-2 sentences on the main conclusion and implication",
    },
}


def cmd_abstract(args: argparse.Namespace) -> int:
    preset = _get_preset(args.journal)

    if args.template:
        tmpl = dict(ABSTRACT_SPEC_TEMPLATE)
        tmpl["journal"] = args.journal
        tmpl["sections"] = {s: f"FILL_ME: content for {s} section"
                            for s in preset["abstract_sections"]}
        out = Path(args.out)
        out.parent.mkdir(parents=True, exist_ok=True)
        out.write_text(json.dumps(tmpl, indent=2, ensure_ascii=False), encoding="utf-8")
        print(f"[abstract] Template → {out}")
        return 0

    spec_path = Path(args.spec)
    if not spec_path.exists():
        sys.exit(f"ERROR: spec file not found: {spec_path}")
    spec = json.loads(spec_path.read_text(encoding="utf-8"))

    sections = spec.get("sections", {})
    word_limit = preset["abstract_word_limit"]
    warnings: list[str] = []
    qa: list[dict] = []

    lines = []
    if preset["abstract_type"] == "structured":
        for sec in preset["abstract_sections"]:
            content = sections.get(sec, "").strip()
            if not content or "FILL_ME" in content:
                warnings.append(f"WARN: section '{sec}' is empty or not filled")
                qa.append({"section": sec, "status": "FAIL"})
            else:
                qa.append({"section": sec, "status": "PASS"})
            lines.append(f"**{sec}:** {content}")
    else:
        # unstructured: merge all sections
        merged = " ".join(v.strip() for v in sections.values() if v.strip())
        lines.append(merged)

    full_text = "\n\n".join(lines)
    wc = _count_words(full_text.replace("**", ""))

    if wc > word_limit:
        warnings.append(f"WARN: {wc} words exceeds {word_limit}-word limit for {preset['name']}")
        qa.append({"field": "word_count", "status": "WARN", "value": wc, "limit": word_limit})
    else:
        qa.append({"field": "word_count", "status": "PASS", "value": wc, "limit": word_limit})

    title = spec.get("title", "")
    header = f"# Abstract — {title}\n\n*Journal: {preset['name']} · {wc}/{word_limit} words*\n\n"
    output_md = header + full_text + "\n"

    out = Path(args.out)
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(output_md, encoding="utf-8")

    qa_path = out.with_suffix(".qa.json")
    qa_path.write_text(json.dumps({"overall": "PASS" if not any(w.startswith("WARN") for w in warnings) else "WARN",
                                    "word_count": wc, "word_limit": word_limit,
                                    "warnings": warnings, "qa": qa}, indent=2), encoding="utf-8")

    overall = "PASS" if wc <= word_limit and not warnings else "WARN"
    print(f"[abstract] {overall} — {wc}/{word_limit} words → {out}")
    for w in warnings:
        print(f"  {w}")
    return 0


# ── Highlights ────────────────────────────────────────────────────────────────

def _extract_highlights_from_text(text: str, n: int, char_limit: int) -> list[str]:
    """
    Extract candidate sentences for highlights from manuscript text.
    Looks for:
    - Sentences with numbers/percentages (quantitative findings)
    - Sentences starting with 'We ', 'Our ', 'This ', 'Here '
    - Sentences containing 'demonstrate', 'show', 'find', 'reveal', 'identify'
    - Last sentence of abstract / conclusion sections
    """
    sentences = re.split(r'(?<=[.!?])\s+', text)
    scored: list[tuple[int, str]] = []

    for s in sentences:
        s = s.strip()
        if len(s) < 30 or len(s) > char_limit * 2:
            continue
        score = 0
        if re.search(r'\d+\.?\d*\s*%', s): score += 3
        if re.search(r'\d+\s*(fold|x|patients|cases|samples)', s, re.I): score += 2
        if re.match(r'(We|Our|This|Here)\s', s): score += 2
        if re.search(r'\b(demonstrate|show|find|reveal|identify|report|achieve|develop|establish)\b', s, re.I): score += 2
        if re.search(r'\b(significant|superior|novel|first|new|improved|enhanced|reduced|increased)\b', s, re.I): score += 1
        # Penalize long sentences
        wc = _count_words(s)
        if wc > char_limit // 5:
            score -= 1
        if score > 0:
            scored.append((score, s))

    scored.sort(key=lambda x: -x[0])
    candidates = []
    for _, s in scored:
        truncated = s[:char_limit].rsplit(' ', 1)[0] if len(s) > char_limit else s
        if truncated not in candidates:
            candidates.append(truncated)
        if len(candidates) >= n:
            break
    return candidates


def cmd_highlights(args: argparse.Namespace) -> int:
    preset = _get_preset(args.journal)
    n_min, n_max = preset["highlights_count"]
    char_limit = preset["highlights_char_limit"]
    n_target = args.count or n_max

    if args.manuscript:
        src = Path(args.manuscript)
        if not src.exists():
            sys.exit(f"ERROR: manuscript not found: {src}")
        text = src.read_text(encoding="utf-8")
        candidates = _extract_highlights_from_text(text, n_target, char_limit)
    elif args.bullets:
        candidates = [b.strip().lstrip("•-* ") for b in args.bullets if b.strip()]
    else:
        sys.exit("ERROR: provide --manuscript or --bullets")

    warnings: list[str] = []
    if len(candidates) < n_min:
        warnings.append(f"WARN: only {len(candidates)} highlights extracted (min {n_min} required for {preset['name']})")
    if len(candidates) > n_max:
        warnings.append(f"WARN: {len(candidates)} highlights generated (max {n_max} for {preset['name']})")
        candidates = candidates[:n_max]

    for i, h in enumerate(candidates, 1):
        if len(h) > char_limit:
            warnings.append(f"WARN: highlight {i} is {len(h)} chars (limit {char_limit}): {h[:40]}...")

    out = Path(args.out)
    out.parent.mkdir(parents=True, exist_ok=True)
    lines = [
        f"# Highlights — {preset['name']}",
        f"*{len(candidates)} bullet(s) · limit {char_limit} chars each · range {n_min}–{n_max}*",
        "",
    ]
    for h in candidates:
        lines.append(f"• {h}")

    if warnings:
        lines += ["", "---", "*Warnings:*"]
        for w in warnings:
            lines.append(f"- {w}")
    lines.append("\n---\n*Review and edit each bullet before submission. "
                 "All quantitative claims must be verifiable in the manuscript.*")

    out.write_text("\n".join(lines), encoding="utf-8")
    overall = "PASS" if not warnings else "WARN"
    print(f"[highlights] {overall} — {len(candidates)} highlights → {out}")
    for w in warnings:
        print(f"  {w}")
    return 0


# ── Cover Letter ──────────────────────────────────────────────────────────────

COVER_TEMPLATE: dict[str, str] = {
    "formal_invited": """\
{date}

Dear {editor_salutation},

I write to submit our manuscript entitled "{title}" for consideration as {article_type} in *{journal_name}*.

{opening_paragraph}

{key_contribution_paragraph}

{conflicts_and_coi}

All authors have read and approved the final manuscript. This work has not been published previously and is not under consideration for publication elsewhere{dual_submission_note}.

Reviewer suggestions (optional): {reviewer_suggestions}

We look forward to your consideration.

Yours sincerely,

{corresponding_author}
{corresponding_affiliation}
{corresponding_email}
""",
    "formal": """\
{date}

Dear {editor_salutation},

We submit our manuscript, "{title}", for consideration in *{journal_name}* as {article_type}.

{opening_paragraph}

{key_contribution_paragraph}

{conflicts_and_coi}

This manuscript is original work not under consideration elsewhere{dual_submission_note}.

Suggested reviewers: {reviewer_suggestions}

Thank you for your consideration.

Sincerely,

{corresponding_author}
{corresponding_affiliation}
{corresponding_email}
""",
    "semi_formal": """\
{date}

Dear {editor_salutation},

Please find enclosed our manuscript "{title}" submitted for consideration in *{journal_name}*.

{opening_paragraph}

{key_contribution_paragraph}

The authors declare {conflicts_and_coi}.

{dual_submission_note}

Sincerely,

{corresponding_author}
{corresponding_affiliation}
{corresponding_email}
""",
}

COVER_SPEC_TEMPLATE = {
    "_warning": "Fill all FILL_ME fields before generating the letter.",
    "journal": "at",
    "article_type": "FILL_ME: Invited Review | Research Article | Letter",
    "title": "FILL_ME: Full manuscript title",
    "date": "FILL_ME: e.g. 22 June 2026",
    "editor_salutation": "FILL_ME: e.g. 'Dr. Smith' or 'the Editors'",
    "corresponding_author": "FILL_ME: Full name (corresponding author)",
    "corresponding_affiliation": "FILL_ME: Institution, City, Country",
    "corresponding_email": "FILL_ME: email@domain.com",
    "opening_paragraph": "FILL_ME: 2-3 sentences on why this manuscript is relevant to this journal",
    "key_contribution_paragraph": "FILL_ME: 2-3 sentences on the main novel findings/contributions",
    "conflicts_and_coi": "FILL_ME: e.g. 'No conflicts of interest to declare.' OR describe COI",
    "dual_submission_note": "FILL_ME: leave blank if no companion paper; otherwise: '. A companion paper [describe] is being submitted simultaneously to [journal]'",
    "reviewer_suggestions": "FILL_ME: 2-3 suggested reviewers with email OR 'None suggested'",
}


def cmd_cover_letter(args: argparse.Namespace) -> int:
    preset = _get_preset(args.journal)

    if args.template:
        tmpl = dict(COVER_SPEC_TEMPLATE)
        tmpl["journal"] = args.journal
        out = Path(args.out)
        out.parent.mkdir(parents=True, exist_ok=True)
        out.write_text(json.dumps(tmpl, indent=2, ensure_ascii=False), encoding="utf-8")
        print(f"[cover-letter] Template → {out}")
        return 0

    spec_path = Path(args.spec)
    if not spec_path.exists():
        sys.exit(f"ERROR: spec not found: {spec_path}")
    spec = json.loads(spec_path.read_text(encoding="utf-8"))

    tone = preset.get("cover_letter_tone", "formal")
    template = COVER_TEMPLATE.get(tone, COVER_TEMPLATE["formal"])

    warnings: list[str] = []
    for key, val in spec.items():
        if key.startswith("_"):
            continue
        if "FILL_ME" in str(val):
            warnings.append(f"WARN: field '{key}' not filled")

    letter = template.format(
        date=spec.get("date", "[DATE]"),
        editor_salutation=spec.get("editor_salutation", "the Editorial Team"),
        title=spec.get("title", "[TITLE]"),
        journal_name=preset["name"],
        article_type=spec.get("article_type", "manuscript"),
        opening_paragraph=spec.get("opening_paragraph", "[OPENING]"),
        key_contribution_paragraph=spec.get("key_contribution_paragraph", "[CONTRIBUTIONS]"),
        conflicts_and_coi=spec.get("conflicts_and_coi", "no competing interests"),
        dual_submission_note=spec.get("dual_submission_note", ""),
        reviewer_suggestions=spec.get("reviewer_suggestions", "None suggested"),
        corresponding_author=spec.get("corresponding_author", "[AUTHOR]"),
        corresponding_affiliation=spec.get("corresponding_affiliation", "[AFFILIATION]"),
        corresponding_email=spec.get("corresponding_email", "[EMAIL]"),
    )

    out = Path(args.out)
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(letter, encoding="utf-8")

    overall = "WARN" if warnings else "PASS"
    print(f"[cover-letter] {overall} → {out}")
    for w in warnings:
        print(f"  {w}")
    return 0


# ── Response to reviewers ─────────────────────────────────────────────────────

RESPONSE_TEMPLATE = """\
# Response to Reviewers

**Manuscript:** {title}  
**Manuscript ID:** {manuscript_id}  
**Journal:** {journal}  
**Date:** {date}

We thank the Editors and Reviewers for their thorough evaluation. Below we provide a point-by-point response to each comment. All changes are highlighted in the revised manuscript using track changes.

---

{reviewer_responses}

---

## Summary of Changes

{summary_of_changes}

We believe the revised manuscript fully addresses all reviewers' concerns and is now suitable for publication.

Sincerely,

{corresponding_author}
{corresponding_affiliation}
"""

REVIEWER_BLOCK_TEMPLATE = """\
## Reviewer {n}

### Comment {n}.{i}
> {comment}

**Response:**
{response}

**Change in manuscript:**
{change}

---
"""


def cmd_response(args: argparse.Namespace) -> int:
    if args.template:
        tmpl = {
            "_warning": "Fill all FILL_ME fields. Every 'Response' must quote the specific change made.",
            "journal": args.journal or "at",
            "title": "FILL_ME: manuscript title",
            "manuscript_id": "FILL_ME: e.g. AT-2026-000123",
            "date": "FILL_ME: date of revision",
            "corresponding_author": "FILL_ME",
            "corresponding_affiliation": "FILL_ME",
            "summary_of_changes": "FILL_ME: 5-10 bullet points summarizing all changes",
            "reviewers": [
                {
                    "reviewer_number": 1,
                    "comments": [
                        {
                            "id": "1.1",
                            "comment": "FILL_ME: paste reviewer comment verbatim",
                            "response": "FILL_ME: your response (thank + explain + point to change)",
                            "change": "FILL_ME: e.g. 'Lines 123-145: Added one paragraph clarifying...'",
                        }
                    ],
                }
            ],
        }
        out = Path(args.out)
        out.parent.mkdir(parents=True, exist_ok=True)
        out.write_text(json.dumps(tmpl, indent=2, ensure_ascii=False), encoding="utf-8")
        print(f"[response] Template → {out}")
        return 0

    spec_path = Path(args.spec)
    spec = json.loads(spec_path.read_text(encoding="utf-8"))
    preset = _get_preset(spec.get("journal", args.journal or "generic"))

    reviewer_blocks = []
    for rv in spec.get("reviewers", []):
        n = rv.get("reviewer_number", "?")
        for i, c in enumerate(rv.get("comments", []), 1):
            reviewer_blocks.append(
                REVIEWER_BLOCK_TEMPLATE.format(
                    n=n, i=i,
                    comment=c.get("comment", ""),
                    response=c.get("response", ""),
                    change=c.get("change", ""),
                )
            )

    letter = RESPONSE_TEMPLATE.format(
        title=spec.get("title", "[TITLE]"),
        manuscript_id=spec.get("manuscript_id", "[ID]"),
        journal=preset["name"],
        date=spec.get("date", "[DATE]"),
        reviewer_responses="\n".join(reviewer_blocks),
        summary_of_changes=spec.get("summary_of_changes", "[SUMMARY]"),
        corresponding_author=spec.get("corresponding_author", "[AUTHOR]"),
        corresponding_affiliation=spec.get("corresponding_affiliation", "[AFFILIATION]"),
    )

    out = Path(args.out)
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(letter, encoding="utf-8")
    print(f"[response] → {out}")
    return 0


# ── FAIR Data Availability Statement ─────────────────────────────────────────

# Repository catalogue (name → FAIR-compliant description + base URL)
FAIR_REPOSITORIES: dict[str, dict] = {
    "zenodo": {
        "name": "Zenodo",
        "url": "https://zenodo.org",
        "policy": "Open access under Creative Commons licence",
        "fair_level": "FAIR-compliant (findable, accessible, interoperable, reusable)",
    },
    "figshare": {
        "name": "Figshare",
        "url": "https://figshare.com",
        "policy": "Open access under CC BY 4.0",
        "fair_level": "FAIR-compliant",
    },
    "github": {
        "name": "GitHub",
        "url": "https://github.com",
        "policy": "Open source repository; long-term availability requires archival to Zenodo",
        "fair_level": "Partially FAIR (recommend DOI archival via Zenodo for full compliance)",
    },
    "ncbi_geo": {
        "name": "NCBI Gene Expression Omnibus (GEO)",
        "url": "https://www.ncbi.nlm.nih.gov/geo/",
        "policy": "Public access after embargo; NCBI-managed",
        "fair_level": "FAIR-compliant",
    },
    "pdb": {
        "name": "RCSB Protein Data Bank (PDB)",
        "url": "https://www.rcsb.org",
        "policy": "Open access; mandatory deposition for structural biology publications",
        "fair_level": "FAIR-compliant",
    },
    "uniprot": {
        "name": "UniProtKB",
        "url": "https://www.uniprot.org",
        "policy": "Open access; reviewed entries peer-curated",
        "fair_level": "FAIR-compliant",
    },
    "dryad": {
        "name": "Dryad",
        "url": "https://datadryad.org",
        "policy": "Open access under CC0 (public domain)",
        "fair_level": "FAIR-compliant",
    },
    "sra": {
        "name": "NCBI Sequence Read Archive (SRA)",
        "url": "https://www.ncbi.nlm.nih.gov/sra/",
        "policy": "Public access; primary sequencing data",
        "fair_level": "FAIR-compliant",
    },
    "sabdab": {
        "name": "Structural Antibody Database (SAbDab)",
        "url": "https://opig.stats.ox.ac.uk/webapps/newsabdab/sabdab/",
        "policy": "Open access; antibody structure repository",
        "fair_level": "FAIR-compliant",
    },
    "custom": {
        "name": "Custom Repository",
        "url": "",
        "policy": "As specified by the author",
        "fair_level": "Verify FAIR compliance with journal data policy",
    },
}

# Journal-specific data policy context
JOURNAL_DATA_POLICIES: dict[str, str] = {
    "at": (
        "Antibody Therapeutics (OUP) requires a data availability statement for all research "
        "articles. Data that are central to the manuscript conclusions must be deposited in a "
        "public repository prior to submission. The statement must include a specific "
        "accession number or DOI."
    ),
    "nature": (
        "Nature journals require that all data needed to evaluate the conclusions of the paper "
        "are present in the paper or supplementary materials, or deposited in public databases "
        "with accession codes. Source data for all main figures must be provided."
    ),
    "cell": (
        "Cell Press journals require data supporting the findings to be available and a Data "
        "Availability section listing all databases and accession numbers."
    ),
    "plos": (
        "PLOS journals require all data supporting the findings to be deposited in appropriate "
        "repositories and listed with accession numbers. All data must be available at time of "
        "initial submission for peer review."
    ),
    "generic": (
        "Data supporting the findings of this study are available from the corresponding author "
        "upon reasonable request."
    ),
}

DATA_STATEMENT_TEMPLATE = {
    "datasets": [
        {
            "label": "Humanized antibody sequences",
            "type": "sequences",
            "repository": "zenodo",
            "accession": "10.5281/zenodo.XXXXXXX",
            "description": "Final humanized VH/VL sequences (Seq1–Seq3) in FASTA format",
            "available_at": "upon_publication",
            "license": "CC BY 4.0",
        },
        {
            "label": "Structure prediction models",
            "type": "structural",
            "repository": "pdb",
            "accession": "XXXX",
            "description": "Crystal / predicted structure deposited to PDB",
            "available_at": "upon_publication",
            "license": "CC0",
        },
    ],
    "code": {
        "repository": "github",
        "url": "https://github.com/ORGANIZATION/REPO",
        "zenodo_doi": "10.5281/zenodo.XXXXXXX",
        "description": "Analysis scripts and pipeline code",
        "license": "MIT",
    },
    "restricted": [],
    "upon_request": [],
    "notes": "",
}


def cmd_data_statement(args: argparse.Namespace) -> int:
    """
    Generate a FAIR-compliant data availability statement for journal submission.
    Never invents accession numbers; requires user-provided spec.
    """
    preset = _get_preset(args.journal)
    out = Path(args.out)
    out.parent.mkdir(parents=True, exist_ok=True)

    if args.template or not args.spec:
        tmpl_path = out.with_suffix(".spec.json")
        tmpl_path.write_text(
            json.dumps(DATA_STATEMENT_TEMPLATE, indent=2, ensure_ascii=False), encoding="utf-8"
        )
        print(f"[data-statement] Template spec written → {tmpl_path}")
        print("  Fill in accession numbers and re-run without --template.")
        return 0

    spec = json.loads(Path(args.spec).read_text(encoding="utf-8"))
    datasets = spec.get("datasets", [])
    code = spec.get("code")
    restricted = spec.get("restricted", [])
    upon_request = spec.get("upon_request", [])
    notes = spec.get("notes", "")

    policy_text = JOURNAL_DATA_POLICIES.get(args.journal, JOURNAL_DATA_POLICIES["generic"])

    lines: list[str] = [
        "## Data Availability Statement",
        "",
        f"*Journal policy ({preset['name']}):* {policy_text}",
        "",
    ]

    if datasets:
        lines.append("### Primary Datasets")
        lines.append("")
        for ds in datasets:
            repo_key = ds.get("repository", "custom")
            repo = FAIR_REPOSITORIES.get(repo_key, FAIR_REPOSITORIES["custom"])
            acc = ds.get("accession", "[ACCESSION REQUIRED]")
            desc = ds.get("description", "")
            avail = ds.get("available_at", "upon_publication")
            lic = ds.get("license", "")
            label = ds.get("label", repo_key)

            avail_str = {
                "upon_publication": "available upon publication",
                "immediately": "immediately available",
                "upon_request": "available upon reasonable request",
                "embargo": "available after embargo period",
            }.get(avail, avail)

            # Flag unfilled placeholder accessions
            if "XXXXX" in acc or acc == "[ACCESSION REQUIRED]":
                lines.append(f"- **{label}** ⚠️ *Accession number required before submission*  ")
                lines.append(f"  Repository: {repo['name']} ({repo['url']})  ")
                lines.append(f"  Description: {desc}  ")
                lines.append(f"  Status: {avail_str}")
            else:
                lines.append(f"- **{label}**: {desc}  ")
                lines.append(f"  Deposited at {repo['name']}: {acc}  ")
                lines.append(f"  {repo['policy']}. License: {lic}. {avail_str.capitalize()}.")
            lines.append("")

    if code:
        repo_key = code.get("repository", "github")
        repo = FAIR_REPOSITORIES.get(repo_key, FAIR_REPOSITORIES["custom"])
        url = code.get("url", "")
        zdoi = code.get("zenodo_doi", "")
        desc = code.get("description", "Analysis code")
        lic = code.get("license", "")
        lines.append("### Code Availability")
        lines.append("")
        if "XXXXX" in zdoi:
            lines.append(f"- {desc}  ")
            lines.append(f"  Repository: {url} ⚠️ *Archive to Zenodo for a citable DOI*  ")
        else:
            ref = f"DOI: {zdoi}" if zdoi else url
            lines.append(f"- {desc}  ")
            lines.append(f"  Available at: {url} ({ref})  ")
            lines.append(f"  License: {lic}")
        lines.append("")

    if restricted:
        lines.append("### Restricted Data")
        lines.append("")
        for r in restricted:
            lines.append(f"- {r.get('label','')}: {r.get('reason','')}  ")
            lines.append(f"  Contact: {r.get('contact','corresponding author')}")
        lines.append("")

    if upon_request:
        lines.append("### Data Available Upon Request")
        lines.append("")
        for r in upon_request:
            lines.append(f"- {r.get('label','')}: {r.get('description','')}  ")
        lines.append("")

    if notes:
        lines.append("### Notes")
        lines.append("")
        lines.append(notes)
        lines.append("")

    # Compliance summary
    missing = [ds for ds in datasets if "XXXXX" in ds.get("accession", "XXXXX")]
    if missing or (code and "XXXXX" in code.get("zenodo_doi", "XXXXX")):
        lines.append("> **⚠️ SUBMISSION HOLD:** One or more accession numbers are placeholders. "
                     "Deposit data and replace before submitting.")
        status = "HOLD"
    else:
        lines.append("> **✅ FAIR compliance:** All datasets have accession numbers/DOIs. "
                     "Statement is submission-ready.")
        status = "READY"

    out.write_text("\n".join(lines), encoding="utf-8")

    # JSON audit record
    audit = {
        "journal": args.journal,
        "journal_name": preset["name"],
        "status": status,
        "datasets_declared": len(datasets),
        "accessions_missing": len(missing),
        "code_declared": bool(code),
    }
    audit_path = out.with_suffix(".audit.json")
    audit_path.write_text(json.dumps(audit, indent=2), encoding="utf-8")

    print(f"[data-statement] {status} → {out}")
    print(f"[data-statement] Audit  → {audit_path}")
    if missing:
        print(f"  ⚠️  {len(missing)} accession(s) still need depositing:")
        for ds in missing:
            print(f"     • {ds.get('label','')}")
    return 0 if status == "READY" else 1


# ── CLI ───────────────────────────────────────────────────────────────────────

def _add_journal_arg(p: argparse.ArgumentParser) -> None:
    p.add_argument("--journal", default="at",
                   choices=list(JOURNAL_PRESETS),
                   help="Journal preset (default: at = Antibody Therapeutics)")


def main() -> None:
    ap = argparse.ArgumentParser(
        prog="insynbio_submission_writer",
        description="Submission-critical text generators: abstract · highlights · cover letter · response",
    )
    sub = ap.add_subparsers(dest="cmd", required=True)

    # abstract
    p_abs = sub.add_parser("abstract", help="Structured abstract builder (5-section, word-limited)")
    _add_journal_arg(p_abs)
    p_abs.add_argument("--spec", default=None, help="Spec JSON (see --template to generate)")
    p_abs.add_argument("--template", action="store_true", help="Generate blank spec JSON")
    p_abs.add_argument("--out", required=True)
    p_abs.set_defaults(func=cmd_abstract)

    # highlights
    p_hl = sub.add_parser("highlights", help="Journal highlights / key-points generator")
    _add_journal_arg(p_hl)
    p_hl.add_argument("--manuscript", default=None, help="Manuscript .md or .txt to extract from")
    p_hl.add_argument("--bullets", nargs="+", default=None, help="Provide bullet text directly")
    p_hl.add_argument("--count", type=int, default=None, help="Target number of highlights")
    p_hl.add_argument("--out", required=True)
    p_hl.set_defaults(func=cmd_highlights)

    # cover letter
    p_cl = sub.add_parser("cover-letter", help="Cover letter template per journal type")
    _add_journal_arg(p_cl)
    p_cl.add_argument("--spec", default=None)
    p_cl.add_argument("--template", action="store_true")
    p_cl.add_argument("--out", required=True)
    p_cl.set_defaults(func=cmd_cover_letter)

    # response to reviewers
    p_rv = sub.add_parser("response", help="Response-to-reviewers letter scaffold")
    p_rv.add_argument("--journal", default="at", choices=list(JOURNAL_PRESETS))
    p_rv.add_argument("--spec", default=None)
    p_rv.add_argument("--template", action="store_true")
    p_rv.add_argument("--out", required=True)
    p_rv.set_defaults(func=cmd_response)

    # data availability statement (FAIR)
    p_ds = sub.add_parser("data-statement",
                           help="FAIR data availability statement (required by OUP, Elsevier, PLOS)")
    _add_journal_arg(p_ds)
    p_ds.add_argument("--spec", default=None, help="Spec JSON (see --template to generate)")
    p_ds.add_argument("--template", action="store_true", help="Generate blank spec JSON")
    p_ds.add_argument("--out", required=True)
    p_ds.set_defaults(func=cmd_data_statement)

    # list presets
    p_ls = sub.add_parser("list-journals", help="List available journal presets")
    p_ls.set_defaults(func=lambda a: _list_journals())

    args = ap.parse_args()
    sys.exit(args.func(args))


def _list_journals() -> int:
    print(f"\n{'Key':<20} {'Journal':<35} {'Abstract':<15} {'Highlights'}")
    print("-" * 75)
    for k, v in JOURNAL_PRESETS.items():
        n_min, n_max = v["highlights_count"]
        print(f"  {k:<18} {v['name']:<35} {v['abstract_type']:<15} {n_min}–{n_max} bullets @{v['highlights_char_limit']}chars")
    return 0


if __name__ == "__main__":
    main()
