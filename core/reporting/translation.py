"""
translation.py — InSynBio Client Report Translation Engine
===========================================================
Provides:
  - CONTENT_TRANSLATION_RULES  : internal term → client-facing term
  - METHODOLOGY_RELIABILITY_ZH : standard reliability statement (Chinese)
  - sanitize_for_client()      : strip internal blocks + apply translations + polish
  - client_reliability_block() : generate standard methodology statement

Design rationale
----------------
Client reports must convey scientific rigour without disclosing proprietary
tool names, database identifiers, or algorithmic parameters.  This module
centralises every translation decision so that project scripts never need
to hand-craft redactions.

Tagging convention in source Markdown
--------------------------------------
Wrap content that must ONLY appear in the internal report with:

    <!-- INTERNAL_ONLY_START -->
    ...raw algorithm details, tool parameters, file paths...
    <!-- INTERNAL_ONLY_END -->

The sanitize_for_client() function removes these blocks completely.

Version history
---------------
  v1.0  2026-04-02  Initial implementation
  v1.1  2026-04-02  Added post-processing polish pass (_polish_chinese),
                    Scenario/BioChatter/Batch/file-path rules
"""
from __future__ import annotations

import re
from typing import Callable


# ---------------------------------------------------------------------------
# Translation rules
# ---------------------------------------------------------------------------

# Order matters: longer / more-specific phrases first to avoid partial replacement.
CONTENT_TRANSLATION_RULES: list[tuple[str, str]] = [

    # ── Compound phrases with underscores (highest priority) ────────────
    ("HADDOCK3_refined",        ""),
    ("HADDOCK3_refinement",     ""),
    ("PDB_exp",                 ""),
    ("AF2_high",                ""),
    ("AF2_mid",                 ""),
    ("AF2_low",                 ""),
    ("structure_source_tier",   ""),
    ("antibody_type",           ""),

    # ── Compound phrases (must precede single-word matches) ──────────────
    ("AF2-Multimer",            ""),
    ("AlphaFold 3",             ""),
    ("AlphaFold3",              ""),
    ("AlphaFold-Multimer",      ""),
    ("AlphaFold",               ""),
    ("ColabFold",               ""),
    ("ESM-IF1",                 ""),
    ("ESM-2",                   ""),
    ("ESM2",                    ""),
    ("MM/GBSA",                 ""),
    ("HADDOCK3",                ""),
    ("HADDOCK",                 ""),
    ("ThermoMPNN",              ""),
    ("ImmuneBuilder",           ""),
    ("EvoEF2",                  ""),
    ("PRODIGY",                 ""),
    ("AntiFold",                ""),
    ("AbLang",                  ""),
    ("OpenMM",                  ""),
    ("ANARCII",                 ""),
    ("anarcii",                 ""),

    # ── Database names ───────────────────────────────────────────────────
    ("SKEMPI2",                 ""),
    ("BindingDB",               ""),
    ("IEDB",                    ""),
    ("SAbDab",                  ""),

    # ── Metric names that reveal pipeline ───────────────────────────────
    ("pLDDT_interface",         ""),
    ("pLDDT",                   ""),
    ("ipTM",                    ""),
    ("DockQ",                   ""),
    ("irmsd",                   ""),
    ("fnat",                    ""),
    ("ΔΔG_fold",                ""),
    ("ΔΔG_bind",                ""),
    ("ΔΔG",                     ""),
    ("Δlog-lik",                ""),
    ("ΔlogP",                   ""),
    ("BSA",                     ""),
    ("Pearson r",               "-"),
    ("minimization_steps",      ""),
    ("BuildMutant",             ""),
    ("Cluster-1",               ""),
    ("cluster concentration",   ""),
    ("Sampling",                ""),

    # ── Pipeline phase labels (anonymise internal numbering) ────────────
    ("Phase -1",                ""),
    ("Phase 0",                 ""),
    ("Phase 1",                 ""),
    ("Phase 2.5",               ""),
    ("Phase 2",                 ""),
    ("Phase 3",                 ""),
    ("Phase 4.5",               ""),
    ("Phase 4",                 ""),
    ("Phase 5",                 ""),
    ("Phase 6",                 ""),

    # ── Scenario labels ──────────────────────────────────────────────────
    ("Scenario A-VHH",          "-VHH "),
    ("Scenario A-VHL",          "-"),
    ("Scenario A",              ""),
    ("Scenario B",              "-"),
    ("Scenario C",              "-VHH "),

    # ── Internal platform names (external = InSynBio / Therasik) ─────────
    ("BioChatter",              "InSynBio "),
    ("Therasik",                "InSynBio "),

    # ── Batch labels (simplify for client) ───────────────────────────────
    ("Batch A",                 ""),
    ("Batch B",                 ""),

    # ── Runtime / infrastructure references ──────────────────────────────
    ("conda affmat",            ""),
    ("conda anarcii",           ""),
    ("conda",                   ""),
    ("affmat",                  ""),
    ("pip install",             ""),

    # ── Internal file paths / version refs ───────────────────────────────
    ("EVOLUTION_LOG.md",        ""),
    ("VIRTUAL_AFFINITY_MATURATION_STANDARD.md", ""),
]


# ---------------------------------------------------------------------------
# Standard methodology reliability statement (client-facing)
# ---------------------------------------------------------------------------

METHODOLOGY_RELIABILITY_ZH = """\
## 

，、\
，。

****（）：

|  | - |  |
|---------|-------------------|--------|
| （） | r ≈ 0.45–0.58 | ， |
|  | r ≈ 0.55–0.70 |  |
|  | （） |  |
|  | （） |  |

****：

- ，（ SPR、BLI）
- ""，
-  ±2 kcal/mol ，

>  InSynBio ACTES ，。\
，。
"""

METHODOLOGY_RELIABILITY_EN = """\
## Methodology Reliability Statement

All computational predictions in this report are based on a multi-dimensional
cross-validation framework combining binding energy prediction, thermal
stability assessment, and sequence developability evaluation.  A candidate is
classified as high-confidence only when all three dimensions converge.

**Prediction accuracy reference** (based on published benchmark studies):

| Analysis Dimension | Typical Prediction–Experiment Correlation | Use |
|---|---|---|
| Binding energy prediction (fast screen) | r ≈ 0.45–0.58 | Directional triage |
| High-precision physical calculation | r ≈ 0.55–0.70 | Final candidate ranking |
| Thermal stability assessment | Qualitative (veto) | Exclude unstable mutations |
| Sequence developability | Qualitative (veto) | Exclude low-expressibility sequences |

**Interpretation guidance**:

- Computational predictions are directional tools; final candidates require
  wet-lab confirmation (e.g. SPR, BLI).
- "High-confidence" denotes consistent outcomes across multiple independent
  computational analyses.
- Candidates differing by < ±2 kcal/mol should not be considered significantly
  distinct without experimental data.

> This report was generated by the InSynBio ACTES Computational Platform.
> For methodological details, please contact the technical team.
"""


# ---------------------------------------------------------------------------
# Sanitisation functions
# ---------------------------------------------------------------------------

# Compiled pattern for INTERNAL_ONLY blocks
_INTERNAL_BLOCK_PATTERN = re.compile(
    r"<!--\s*INTERNAL_ONLY_START\s*-->.*?<!--\s*INTERNAL_ONLY_END\s*-->",
    flags=re.DOTALL | re.IGNORECASE,
)

# Pattern for lines tagged with [INTERNAL]
_INTERNAL_LINE_PATTERN = re.compile(
    r"^.*\[INTERNAL\].*$\n?",
    flags=re.MULTILINE,
)


def _polish_chinese(text: str) -> str:
    """Post-process translated Chinese text to remove mechanical artifacts.

    Fixes common problems created by word-level term substitution:
      - Double/triple repeated Chinese noun phrases
      - Translated Phase labels creating redundant section titles
      - Stray spaces between Chinese characters/phrases
      - Empty parentheses or dangling punctuation
      - Internal file paths (docs/..., projects/..., config/...)
      - Residual "V1.x" standard version references
    """
    # ── Remove internal file paths ───────────────────────────────────────
    text = re.sub(r"`?(?:docs|projects|config|core|scripts)/[\w/\-\.]+`?", "", text)

    # ── Remove "VAM  Vx.y" references ────────────────────────────────
    text = re.sub(r"VAM\s*\s*V\d+\.\d+", "InSynBio ", text)

    # ── Collapse repeated Chinese phrases ON SAME LINE (2-12 chars) ────
    # e.g. " " → ""
    text = re.sub(r'([\u4e00-\u9fff]{2,12}) +\1', r'\1', text)

    # ── Fix "XX — XX" pattern where title repeats phase translation ──
    # e.g. "## 、 — " → "## 、"
    text = re.sub(
        r'(#{1,4}\s*[\u4e00-\u9fff\d、]+)\s*—\s*([\u4e00-\u9fff]+)',
        _dedupe_heading,
        text,
    )

    # ── Fix spaces between adjacent Chinese phrases (SINGLE LINE ONLY) ──
    # " " → ""
    # CRITICAL: Only collapse spaces within a line, never across newlines.
    text = re.sub(
        r'([\u4e00-\u9fff\uff0c\uff1b\u3001]) +([\u4e00-\u9fff])',
        r'\1\2',
        text,
    )

    # ── Fix " " → "" (remove stray "") ──
    text = re.sub(r'\s*', '', text)

    # ── Fix empty parentheses left after path removal ────────────────────
    text = re.sub(r'\(\s*\)', '', text)
    text = re.sub(r'\s*。', '。', text)
    text = re.sub(r'\s*$', '', text, flags=re.MULTILINE)

    # ── Fix double punctuation ───────────────────────────────────────────
    text = re.sub(r'。。', '。', text)
    text = re.sub(r'，，', '，', text)

    # ── Collapse multiple spaces to single (within lines only) ──────────
    text = re.sub(r' {2,}', ' ', text)

    # ── Remove lines that became empty after cleaning ────────────────────
    text = re.sub(r'\n{3,}', '\n\n', text)

    return text


def _dedupe_heading(m: re.Match) -> str:
    """Remove redundant portion in a '## Num、PhraseLong — PhraseShort' heading."""
    prefix = m.group(1)   # e.g. "## 、"
    suffix = m.group(2)   # e.g. ""

    # If prefix already contains the suffix (or vice versa), drop the " — suffix"
    # Also strip trailing "" from prefix if it's a Phase translation artifact
    clean_prefix = re.sub(r'$', '', prefix)
    if suffix in clean_prefix or clean_prefix.endswith(suffix):
        return clean_prefix
    return f"{clean_prefix} — {suffix}"


def sanitize_for_client(
    markdown_text: str,
    extra_rules: list[tuple[str, str]] | None = None,
    lang: str = "zh",
) -> str:
    """Return a client-safe version of the Markdown source.

    Steps performed (in order):
      1. Remove ``<!-- INTERNAL_ONLY_START --> ... <!-- INTERNAL_ONLY_END -->`` blocks.
      2. Remove lines tagged with ``[INTERNAL]``.
      3. Apply all ``CONTENT_TRANSLATION_RULES`` term substitutions.
      4. Apply any caller-supplied ``extra_rules``.
      5. Polish pass: deduplicate, fix spacing, remove file paths.

    Parameters
    ----------
    markdown_text : str
        Raw Markdown source (internal version).
    extra_rules : list of (pattern, replacement) tuples, optional
        Project-specific additional translation rules.
    lang : str
        Language hint for future multi-language support ("zh" | "en").
        Currently unused but reserved.

    Returns
    -------
    str
        Sanitised Markdown safe for client delivery.
    """
    text = _INTERNAL_BLOCK_PATTERN.sub("", markdown_text)
    text = _INTERNAL_LINE_PATTERN.sub("", text)

    rules = CONTENT_TRANSLATION_RULES + (extra_rules or [])
    for internal_term, client_term in rules:
        if not internal_term:
            continue
        pattern = r"(?<![A-Za-z0-9\-])" + re.escape(internal_term) + r"(?![A-Za-z0-9\-])"
        text = re.sub(pattern, client_term, text)

    if lang == "zh":
        text = _polish_chinese(text)

    text = re.sub(r"\n{3,}", "\n\n", text)
    return text


def client_reliability_block(lang: str = "zh") -> str:
    """Return the standard methodology reliability section for client reports.

    This should be injected at the end of the main analysis, before the
    Risks & Limitations chapter.

    Parameters
    ----------
    lang : str
        ``"zh"`` for Chinese (default), ``"en"`` for English.
    """
    return METHODOLOGY_RELIABILITY_ZH if lang == "zh" else METHODOLOGY_RELIABILITY_EN


def strip_internal_tags(text: str) -> str:
    """Remove only the INTERNAL_ONLY tag markers, preserving content.

    Useful for generating a 'clean internal' view where the content
    inside INTERNAL_ONLY blocks is kept but the HTML comment tags are
    stripped (e.g. for Markdown preview).
    """
    text = re.sub(r"<!--\s*INTERNAL_ONLY_START\s*-->", "", text, flags=re.IGNORECASE)
    text = re.sub(r"<!--\s*INTERNAL_ONLY_END\s*-->", "", text, flags=re.IGNORECASE)
    return text
