"""
multi_expert_review.py
======================
TheraSIK Multi-Expert Manuscript Review Simulation

Six independent reviewer roles:

  Statistician          — statistical methods, sample sizes, p-values, effect sizes,
                          multiple comparison corrections, reproducibility
  Domain Expert         — claims vs evidence, novelty framing, logic flow, hedging,
                          overclaiming, limitation disclosure
  Editor                — journal fit, section structure, word/figure/reference counts,
                          mandatory declarations, title and abstract quality
  AI Diagnostician      — AI phrase markers, self-talk, unanchored claims,
                          sentence rhythm; Gemini-backed with rule fallback
  Citation Auditor      — citation density, hallucination-risk gaps, topical vs
                          evidential citations; Gemini-backed with rule fallback
  Reproducibility       — methods completeness, software + version, cell line
                          provenance, data deposition; Gemini-backed with rule fallback

Design principles:
  • Original three roles: rule-based heuristic, deterministic, no LLM required
  • New three roles: Gemini-1.5-flash backed (free tier) with automatic rule fallback
  • Source-bounded — only flags what is present (or absent) in the manuscript
  • No editorial decision claims — never says "will be rejected/accepted"
  • Severity tiers: CRITICAL (must fix) / MAJOR (strongly recommended) / MINOR

Output: {project_dir}/03_QA/multi_expert_review_QA.md

Usage (CLI):
  python scripts/multi_expert_review.py <project_dir>
  python scripts/multi_expert_review.py <project_dir> --reviewer statistician
  python scripts/multi_expert_review.py <project_dir> --reviewer ai_diagnostician
  python scripts/multi_expert_review.py <project_dir> --use-llm

Programmatic:
  from multi_expert_review import run_full_review, run_statistician, run_domain_expert, run_editor
"""

from __future__ import annotations

import argparse
import json
import logging
import os
import re
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional

logger = logging.getLogger(__name__)

SKILL_DIR   = Path(os.environ.get("THERASIK_DIR", Path(__file__).resolve().parents[1]))
JOURNAL_DIR = SKILL_DIR / "assets" / "journal_requirements"

sys.path.insert(0, str(SKILL_DIR / "scripts"))
try:
    from submission_prep import count_words, count_abstract_words, count_references, \
        count_figures, detect_sections, load_journal
except ImportError:
    def count_words(t): return len(re.findall(r"\b\w+\b", t))
    def count_abstract_words(t): return 0
    def count_references(t): return 0
    def count_figures(t, d=None): return 0
    def detect_sections(t): return []
    def load_journal(n): return None


# ── Severity constants ─────────────────────────────────────────────────────────
CRITICAL = "CRITICAL"
MAJOR    = "MAJOR"
MINOR    = "MINOR"
INFO     = "INFO"


# ── Finding dataclass ─────────────────────────────────────────────────────────

def finding(category: str, severity: str, issue: str,
            evidence: str = "", recommendation: str = "") -> dict:
    return {
        "category":       category,
        "severity":       severity,
        "issue":          issue,
        "evidence":       evidence[:200] if evidence else "",
        "recommendation": recommendation,
    }


# ── Text utilities ─────────────────────────────────────────────────────────────

def _section_text(text: str, heading: str) -> str:
    """Extract text of a section by heading."""
    m = re.search(
        rf"^#{1,3}\s*{re.escape(heading)}\s*\n(.*?)(?=^#{1,3}\s|\Z)",
        text, re.IGNORECASE | re.MULTILINE | re.DOTALL
    )
    return m.group(1) if m else ""


def _sentences(text: str) -> list[str]:
    return [s.strip() for s in re.split(r"(?<=[.!?])\s+", text) if len(s.strip()) > 10]


def _quote(text: str, pattern: str, window: int = 60) -> str:
    """Return a short quote showing where a pattern was found."""
    m = re.search(pattern, text, re.IGNORECASE)
    if not m:
        return ""
    start = max(0, m.start() - 20)
    end   = min(len(text), m.end() + window)
    return "…" + text[start:end].replace("\n", " ").strip() + "…"


# ══════════════════════════════════════════════════════════════════════════════
# REVIEWER 1 — STATISTICIAN
# ══════════════════════════════════════════════════════════════════════════════

STAT_TESTS = [
    "t-test", "t test", "student.*t", "anova", "ancova", "manova",
    "chi.square", "chi-square", "fisher.*exact", "mann.whitney", "wilcoxon",
    "kruskal.wallis", "log.rank", "kaplan.meier", "cox.*regression",
    "linear regression", "logistic regression", "mixed.*model", "lme",
    "pearson", "spearman", "correlation", "bootstrap", "permutation.*test",
    "bayesian", "mcmc", "random.*forest", "lasso", "ridge",
]

EFFECT_SIZE_TERMS = [
    r"cohen.?s\s+d", r"hedges.?\s*g", r"odds\s+ratio", r"\bor\b",
    r"hazard\s+ratio", r"\bhr\b", r"risk\s+ratio", r"\brr\b",
    r"relative\s+risk", r"effect\s+size", r"standardized\s+mean\s+difference",
    r"eta.squared", r"omega.squared", r"r.squared", r"\br²",
    r"auc\b", r"area\s+under.*curve", r"accuracy", r"sensitivity", r"specificity",
]

CORRECTION_TERMS = [
    "bonferroni", "benjamini", "hochberg", "fdr", "false discovery",
    "multiple.*comparison", "multiple.*test", "correction", "adjusted.*p",
    "holm", "sidak", "tukey",
]

CI_TERMS = [r"95\s*%\s*ci", r"confidence\s+interval", r"\bci\b\s*[\[\(]", r"\[.*,.*\]"]

POWER_TERMS = ["power analysis", "sample size calculation", "statistical power",
               "underpowered", "post.hoc power"]

OVERCLAIM_STATS = [
    "proves", "definitively", "conclusively proves", "irrefutably",
    "without doubt", "certainly", "unequivocally",
]


def run_statistician(text: str, config: dict = {}) -> dict:
    """
    Statistician review: statistical rigor, reporting standards, reproducibility.
    """
    findings: list[dict] = []
    score = 10

    # ── 1. Statistical tests used ─────────────────────────────────────────────
    tests_found = [t for t in STAT_TESTS if re.search(t, text, re.IGNORECASE)]
    if not tests_found:
        # Check for any numeric data suggesting statistics
        has_numbers = bool(re.search(r"\bp\s*[<>=≤≥]\s*0\.\d+", text, re.IGNORECASE))
        if has_numbers:
            findings.append(finding(
                "Statistical tests", CRITICAL,
                "P-values reported but no statistical test named",
                _quote(text, r"p\s*[<>=]\s*0\.\d+"),
                "Name the specific statistical test used for each comparison (e.g. Mann-Whitney U, two-tailed t-test)."
            ))
            score -= 2
    else:
        # Tests found — check justification
        justified = bool(re.search(
            r"(?:assumed?|verified?|tested?|confirmed?)\s+(?:normal|gaussian|parametric|non.parametric)",
            text, re.IGNORECASE
        ))
        if not justified and any(t in tests_found for t in ["t-test", "anova", "pearson"]):
            findings.append(finding(
                "Statistical tests", MAJOR,
                "Parametric tests used without normality justification",
                f"Tests found: {', '.join(tests_found[:3])}",
                "State explicitly whether data distribution was assessed (e.g. Shapiro-Wilk, Q-Q plot) "
                "and justify choice of parametric vs non-parametric tests."
            ))
            score -= 1

    # ── 2. P-value reporting ──────────────────────────────────────────────────
    p_values = re.findall(r"p\s*[<>=≤≥]\s*0\.\d+", text, re.IGNORECASE)
    if p_values:
        # Check for exact p-values vs threshold only
        threshold_only = [p for p in p_values if re.match(r"p\s*<\s*0\.0[15]$", p.strip(), re.IGNORECASE)]
        if len(threshold_only) > 2 and len(threshold_only) == len(p_values):
            findings.append(finding(
                "P-value reporting", MAJOR,
                "P-values reported only as threshold comparisons (p<0.05), not exact values",
                f"e.g. {threshold_only[0]}",
                "Report exact p-values (e.g. p=0.023) where possible; threshold notation "
                "(p<0.05) is acceptable only when exact value is unavailable."
            ))
            score -= 1

        # Check for multiple comparisons
        multiple = len(p_values) > 3
        correction_mentioned = any(re.search(t, text, re.IGNORECASE) for t in CORRECTION_TERMS)
        if multiple and not correction_mentioned:
            findings.append(finding(
                "Multiple comparisons", CRITICAL if len(p_values) > 6 else MAJOR,
                f"{len(p_values)} p-values reported with no multiple comparison correction",
                f"First p-value: {p_values[0]}",
                "Apply appropriate correction (Bonferroni, Benjamini-Hochberg FDR) when "
                "conducting multiple statistical tests. State the correction method used."
            ))
            score -= 2 if len(p_values) > 6 else 1

    # ── 3. Effect sizes ───────────────────────────────────────────────────────
    effect_found = any(re.search(t, text, re.IGNORECASE) for t in EFFECT_SIZE_TERMS)
    has_stats    = bool(p_values) or bool(tests_found)
    if has_stats and not effect_found:
        findings.append(finding(
            "Effect sizes", MAJOR,
            "Statistical significance reported without effect sizes",
            "",
            "Supplement p-values with effect size measures (Cohen's d, odds ratio, hazard ratio, "
            "AUC, etc.) to convey practical significance alongside statistical significance."
        ))
        score -= 1

    # ── 4. Confidence intervals ───────────────────────────────────────────────
    ci_found = any(re.search(t, text, re.IGNORECASE) for t in CI_TERMS)
    if has_stats and not ci_found:
        findings.append(finding(
            "Confidence intervals", MAJOR,
            "No confidence intervals reported for primary outcomes",
            "",
            "Report 95% confidence intervals for all primary outcome measures. "
            "CIs convey both effect magnitude and precision."
        ))
        score -= 1

    # ── 5. Sample size / power ────────────────────────────────────────────────
    n_mentioned  = bool(re.search(r"\bn\s*=\s*\d+|\bN\s*=\s*\d+|n\s*=\s*\d+", text))
    power_found  = any(re.search(t, text, re.IGNORECASE) for t in POWER_TERMS)
    is_clinical  = bool(re.search(r"patient|participant|subject|cohort|trial|clinical", text, re.IGNORECASE))
    if is_clinical and not power_found:
        findings.append(finding(
            "Sample size", MAJOR,
            "Clinical/human study without power analysis or sample size justification",
            "",
            "Include a priori power analysis stating: assumed effect size, α level, "
            "desired power (≥0.80), and resulting required sample size."
        ))
        score -= 1
    elif not n_mentioned and has_stats:
        findings.append(finding(
            "Sample size", MAJOR,
            "Sample size (n=) not explicitly stated alongside statistical results",
            "",
            "State sample size (n=) for each group being compared."
        ))
        score -= 1

    # ── 6. Variability reporting ──────────────────────────────────────────────
    sd_sem = re.findall(r"±\s*\d|±\s*[A-Z]+|mean\s*±|SD|SEM|standard\s+(?:deviation|error)", text, re.IGNORECASE)
    if sd_sem:
        has_sd  = bool(re.search(r"\bSD\b|standard\s+deviation", text, re.IGNORECASE))
        has_sem = bool(re.search(r"\bSEM\b|standard\s+error", text, re.IGNORECASE))
        if has_sd and has_sem:
            findings.append(finding(
                "Variability", MINOR,
                "Both SD and SEM used — verify consistency",
                "",
                "Use SD to describe spread of data, SEM only for mean estimates. "
                "Mixing SD and SEM in different figures is a common error."
            ))

    # ── 7. Reproducibility ────────────────────────────────────────────────────
    repro_terms = ["independent.*experiment", "replicate", "biological.*replicate",
                   "technical.*replicate", "repeat", "independent.*cohort"]
    repro_found = any(re.search(t, text, re.IGNORECASE) for t in repro_terms)
    if not repro_found and tests_found:
        findings.append(finding(
            "Reproducibility", MAJOR,
            "Replication strategy not described",
            "",
            "State the number of independent biological and technical replicates. "
            "Clarify whether experiments were repeated and report all attempts."
        ))
        score -= 1

    # ── 8. Outlier handling ───────────────────────────────────────────────────
    outlier_mention = bool(re.search(r"outlier|exclusion\s+criter|removed.*data|excluded.*subject",
                                     text, re.IGNORECASE))
    grubbs = bool(re.search(r"grubbs|rout.*test|dixon.*q", text, re.IGNORECASE))
    if not outlier_mention and tests_found:
        findings.append(finding(
            "Outlier handling", MINOR,
            "Outlier detection and exclusion policy not stated",
            "",
            "Describe any outlier detection method used (Grubbs, ROUT, IQR rule) "
            "and state the exclusion criteria pre-specified before data collection."
        ))

    # ── 9. Software reporting ─────────────────────────────────────────────────
    software_found = bool(re.search(
        r"spss|stata|sas|r\s+version|prism|graphpad|python|matlab|jamovi|jasp",
        text, re.IGNORECASE
    ))
    if tests_found and not software_found:
        findings.append(finding(
            "Software", MINOR,
            "Statistical software not specified",
            "",
            "Name the statistical software and version used (e.g. 'R v4.3.0', "
            "'GraphPad Prism 10', 'SPSS v28')."
        ))

    score = max(0, min(10, score))
    critical = [f for f in findings if f["severity"] == CRITICAL]
    status = CRITICAL if critical else (MAJOR if score < 7 else "PASS")

    return {
        "reviewer": "Statistician",
        "score": score,
        "status": status,
        "findings": findings,
        "summary": (
            f"Score {score}/10. "
            f"{len(critical)} critical, "
            f"{len([f for f in findings if f['severity']==MAJOR])} major, "
            f"{len([f for f in findings if f['severity']==MINOR])} minor issues."
        ),
    }


# ══════════════════════════════════════════════════════════════════════════════
# REVIEWER 2 — DOMAIN EXPERT
# ══════════════════════════════════════════════════════════════════════════════

OVERCLAIM_WORDS = [
    r"\bproves?\b", r"\bproven\b", r"\bdemonstratively\b",
    r"\bconclusively\b", r"\birrefutably\b", r"\bundoubtedly\b",
    r"\bcertainly\s+(?:shows?|demonstrates?|proves?)\b",
    r"\bfirst\s+(?:ever|in\s+history|to\s+show)\b",
    r"\bgroundbreaking\b", r"\brevolutionary\b", r"\bparadigm.shifting\b",
    r"\bnovel\b.*\bnovel\b.*\bnovel\b",  # 3+ times
]

HEDGING_WORDS = [
    "suggests?", "indicates?", "implies?", "may ", "might ", "could ",
    "appear?s? to", "is consistent with", "supports? the hypothesis",
    "we propose", "we hypothesize", "we speculate",
]

CAUSAL_WORDS = [
    r"\bcauses?\b", r"\bdrives?\b", r"\binduces?\b", r"\bleads?\s+to\b",
    r"\bresults?\s+in\b", r"\bresponsible\s+for\b", r"\bmediated?\s+by\b",
]


def run_domain_expert(text: str, config: dict = {}) -> dict:
    """
    Domain expert review: scientific accuracy, claims vs evidence, logic flow.
    """
    findings: list[dict] = []
    score = 10

    # ── 1. Overclaiming ───────────────────────────────────────────────────────
    overclaims = []
    for pat in OVERCLAIM_WORDS:
        m = re.search(pat, text, re.IGNORECASE)
        if m:
            overclaims.append(_quote(text, pat, 80))
    if overclaims:
        sev = CRITICAL if len(overclaims) > 2 else MAJOR
        findings.append(finding(
            "Overclaiming", sev,
            f"{len(overclaims)} instance(s) of language that overstates findings",
            overclaims[0],
            "Replace absolute causal/certainty language with appropriately hedged terms: "
            "'suggests', 'is consistent with', 'supports the hypothesis that'. "
            "Reserve 'demonstrates' for mechanistic experiments with direct evidence."
        ))
        score -= min(3, len(overclaims))

    # ── 2. Causal claims without mechanistic evidence ──────────────────────────
    causal_matches = []
    for pat in CAUSAL_WORDS:
        for m in re.finditer(pat, text, re.IGNORECASE):
            start = max(0, m.start() - 50)
            causal_matches.append(text[start: m.end() + 80].replace("\n", " "))

    mechanistic_evidence = bool(re.search(
        r"knockdown|knockout|k[oi]\b|overexpress|rescue.*experiment|mechanistically|pathway|"
        r"gain.of.function|loss.of.function|directly\s+binds|co.immunoprecipitat|chip",
        text, re.IGNORECASE
    ))
    if causal_matches and not mechanistic_evidence:
        findings.append(finding(
            "Causal claims", MAJOR,
            f"{len(causal_matches)} causal statements found without mechanistic experimental evidence",
            causal_matches[0][:150] if causal_matches else "",
            "Causal language ('causes', 'drives', 'induces') requires direct mechanistic evidence "
            "(e.g. knockdown/rescue, genetic manipulation). Use 'associates with' or 'correlates with' "
            "for observational data."
        ))
        score -= 1

    # ── 3. Hypothesis clearly stated ──────────────────────────────────────────
    intro_text = _section_text(text, "Introduction") or _section_text(text, "Background")
    hypothesis = bool(re.search(
        r"we\s+(?:hypothes|propos|aim|sought|test)|hypothesis\s+(?:is|that|:)|"
        r"to\s+(?:test|investigate|determine|assess|examine)\s+whether",
        intro_text, re.IGNORECASE
    ))
    if intro_text and not hypothesis:
        findings.append(finding(
            "Research question", MAJOR,
            "Research hypothesis or question not explicitly stated in Introduction",
            "",
            "Add a clear statement of the hypothesis or specific aim at the end of the "
            "Introduction (e.g. 'We hypothesized that…' or 'The aim of this study was to…')."
        ))
        score -= 1

    # ── 4. Literature gap ─────────────────────────────────────────────────────
    gap_terms = [
        r"(?:remains?|is)\s+unknown", r"has\s+not\s+been\s+(?:studied|investigated|reported|shown)",
        r"gap\s+in\s+(?:the\s+)?(?:knowledge|literature|understanding)",
        r"limited\s+(?:evidence|data|understanding)", r"poorly\s+understood",
        r"no\s+(?:study|studies|evidence|data)\s+(?:has|have)",
    ]
    gap_found = any(re.search(t, intro_text or text, re.IGNORECASE) for t in gap_terms)
    if intro_text and not gap_found:
        findings.append(finding(
            "Literature gap", MAJOR,
            "Knowledge gap motivating the study not clearly identified",
            "",
            "State explicitly what is not known and why that gap matters. "
            "This is typically 1–2 sentences near the end of the Introduction."
        ))
        score -= 1

    # ── 5. Results logic flow ─────────────────────────────────────────────────
    results_text = _section_text(text, "Results")
    if results_text:
        sentences = _sentences(results_text)
        # Check for topic sentences (first sentence of each paragraph setting context)
        paragraphs = [p.strip() for p in results_text.split("\n\n") if len(p.strip()) > 100]
        weak_starts = []
        for para in paragraphs[:8]:
            first_sentence = _sentences(para)[0] if _sentences(para) else ""
            # Weak start: begins with "Figure", "Table", "As shown", "The data"
            if re.match(r"^(?:figure|table|as\s+shown|the\s+data|as\s+seen)", first_sentence, re.IGNORECASE):
                weak_starts.append(first_sentence[:80])
        if len(weak_starts) > 2:
            findings.append(finding(
                "Results structure", MINOR,
                f"{len(weak_starts)} result paragraph(s) start with figure/data reference instead of a finding statement",
                weak_starts[0] if weak_starts else "",
                "Start each results paragraph with the key finding in plain language "
                "(e.g. 'Treatment X reduced tumor volume by 40%…'), then reference the supporting figure."
            ))

    # ── 6. Discussion: limitations ────────────────────────────────────────────
    discussion = _section_text(text, "Discussion")
    limitation_found = bool(re.search(
        r"limitation|caveat|shortcoming|weakness|constraint|should\s+be\s+(?:noted|interpreted)",
        discussion or text, re.IGNORECASE
    ))
    if discussion and not limitation_found:
        findings.append(finding(
            "Limitations", CRITICAL,
            "No limitations section or explicit acknowledgement of study limitations",
            "",
            "Add a dedicated limitations paragraph in the Discussion. Reviewers "
            "and editors expect transparent acknowledgement of methodological constraints, "
            "sample size limitations, and generalisability boundaries."
        ))
        score -= 2

    # ── 7. Alternative explanations ───────────────────────────────────────────
    alt_found = bool(re.search(
        r"alternative(?:ly)?|another\s+(?:possibility|explanation|interpretation)|"
        r"cannot\s+(?:rule\s+out|exclude)|other\s+(?:factor|mechanism|explanation)",
        discussion or text, re.IGNORECASE
    ))
    if discussion and not alt_found and len(discussion) > 300:
        findings.append(finding(
            "Alternative explanations", MAJOR,
            "Discussion does not address alternative explanations for findings",
            "",
            "For each major result, briefly consider and address at least one plausible "
            "alternative explanation and explain why your interpretation is preferred."
        ))
        score -= 1

    # ── 8. Novelty statement ──────────────────────────────────────────────────
    novelty_found = bool(re.search(
        r"novel|first\s+(?:to|study|report|demonstrate|show)|new\s+(?:finding|insight|approach|method)|"
        r"previously\s+(?:unknown|unreported|unrecognized)|advance",
        text, re.IGNORECASE
    ))
    if not novelty_found:
        findings.append(finding(
            "Novelty", MAJOR,
            "Novel contribution of the work not explicitly stated",
            "",
            "Clearly state what is new about this work in both the Abstract and Introduction. "
            "Reviewers need to assess novelty relative to existing literature."
        ))
        score -= 1

    # ── 9. Hedging adequacy ───────────────────────────────────────────────────
    hedge_count = sum(len(re.findall(h, text, re.IGNORECASE)) for h in HEDGING_WORDS)
    total_sentences = max(1, len(_sentences(text)))
    hedge_ratio = hedge_count / total_sentences
    if hedge_ratio < 0.05 and total_sentences > 30:
        findings.append(finding(
            "Scientific hedging", MINOR,
            f"Low hedging density ({hedge_ratio:.1%} of sentences) — language may be overconfident",
            "",
            "Ensure claims are appropriately qualified with hedging language where direct "
            "causal evidence is absent. Scientific claims should reflect the strength of evidence."
        ))

    # ── 10. Self-citation balance ─────────────────────────────────────────────
    # Rough proxy: repeated author names in references
    ref_section = _section_text(text, "References") or _section_text(text, "Bibliography")
    if ref_section:
        total_refs = max(1, count_references(text))
        # Look for repeated author surnames (crude proxy for self-citation clustering)
        author_names = re.findall(r"^[A-Z][a-z]+\s+[A-Z]", ref_section, re.MULTILINE)
        if author_names:
            from collections import Counter
            counts = Counter(author_names)
            dominant = [(name, n) for name, n in counts.most_common(3) if n / total_refs > 0.25]
            if dominant:
                findings.append(finding(
                    "Citation balance", MINOR,
                    f"Potential citation imbalance: '{dominant[0][0]}' appears in "
                    f"{dominant[0][1]}/{total_refs} references ({dominant[0][1]/total_refs:.0%})",
                    "",
                    "Review reference list for potential over-reliance on a single research group. "
                    "Ensure balanced representation of the field."
                ))

    score = max(0, min(10, score))
    critical = [f for f in findings if f["severity"] == CRITICAL]
    status = CRITICAL if critical else (MAJOR if score < 7 else "PASS")

    return {
        "reviewer": "Domain Expert",
        "score": score,
        "status": status,
        "findings": findings,
        "summary": (
            f"Score {score}/10. "
            f"{len(critical)} critical, "
            f"{len([f for f in findings if f['severity']==MAJOR])} major, "
            f"{len([f for f in findings if f['severity']==MINOR])} minor issues."
        ),
    }


# ══════════════════════════════════════════════════════════════════════════════
# REVIEWER 3 — EDITOR
# ══════════════════════════════════════════════════════════════════════════════

MANDATORY_DECLARATIONS = [
    ("conflict of interest",
     r"conflict.*interest|competing.*interest|disclosure|no.*conflict|declare.*no",
     "Conflict of interest / competing interests declaration"),
    ("author contributions",
     r"author\s+contribution|credit\s+(?:statement|taxonomy)|contributed\s+(?:to|equally)",
     "Author contributions statement (CRediT taxonomy)"),
    ("data availability",
     r"data\s+availability|data\s+(?:are|is)\s+available|data\s+(?:can\s+be|upon\s+request)|"
     r"available\s+(?:upon|on)\s+request|deposited\s+(?:in|at)|github\.com|zenodo|figshare|dryad",
     "Data availability statement"),
    ("funding",
     r"funded\s+by|funding|grant\s+(?:number|support|from)|supported\s+by|award\s+number",
     "Funding / acknowledgements"),
]


def run_editor(text: str, config: dict = {}, journal_data: dict | None = None) -> dict:
    """
    Editorial review: structure, compliance, completeness, format.
    """
    findings: list[dict] = []
    score = 10

    journal_name = config.get("target_journal", "")
    art_type     = config.get("article_type", "Article")

    # Use loaded journal data or try to load it
    if journal_data is None and journal_name:
        journal_data = load_journal(journal_name)

    spec: dict = {}
    if journal_data:
        art_specs = journal_data.get("article_types", {})
        for k, v in art_specs.items():
            if k.lower() == art_type.lower():
                spec = v
                break
        if not spec and art_specs:
            spec = next(iter(art_specs.values()))

    # ── 1. Word count ─────────────────────────────────────────────────────────
    total_words  = count_words(text)
    word_limit   = spec.get("max_words_main_text")
    if word_limit:
        pct = total_words / word_limit * 100
        if total_words > word_limit:
            over = total_words - word_limit
            findings.append(finding(
                "Word count", CRITICAL,
                f"Manuscript exceeds word limit by {over:,} words ({total_words:,} / {word_limit:,})",
                "",
                f"Reduce manuscript by at least {over:,} words before submission. "
                "Focus cuts on Discussion, Introduction, and Methods redundancies."
            ))
            score -= 3
        elif pct < 40:
            findings.append(finding(
                "Word count", MINOR,
                f"Manuscript is unusually short ({total_words:,} / {word_limit:,} words, {pct:.0f}%)",
                "",
                "Verify that all required sections are adequately developed."
            ))
    else:
        findings.append(finding(
            "Word count", INFO,
            f"Total word count: {total_words:,} (no journal limit available for '{journal_name}')",
            "", ""
        ))

    # ── 2. Abstract ───────────────────────────────────────────────────────────
    abs_words = count_abstract_words(text)
    abs_limit  = spec.get("max_words_abstract")
    if abs_limit:
        if abs_words == 0:
            findings.append(finding(
                "Abstract", CRITICAL,
                "Abstract section not detected",
                "",
                "Add a clearly labelled Abstract section. Most journals require it as the first section."
            ))
            score -= 2
        elif abs_words > abs_limit:
            findings.append(finding(
                "Abstract", CRITICAL,
                f"Abstract exceeds limit by {abs_words - abs_limit} words ({abs_words} / {abs_limit})",
                "",
                f"Trim abstract to ≤ {abs_limit} words."
            ))
            score -= 1
    elif abs_words == 0:
        findings.append(finding(
            "Abstract", MAJOR,
            "Abstract section not detected",
            "",
            "Add a clearly labelled Abstract section."
        ))
        score -= 1

    # ── 3. Required sections ──────────────────────────────────────────────────
    found_sections = [s.lower() for s in detect_sections(text)]
    required = spec.get("required_sections", ["Abstract", "Introduction", "Methods", "Results", "Discussion"])
    missing  = [s for s in required if s.lower() not in found_sections]
    if missing:
        sev = CRITICAL if len(missing) > 2 else MAJOR
        findings.append(finding(
            "Required sections", sev,
            f"Missing section(s): {', '.join(missing)}",
            "",
            f"Add the following sections required by {journal_name or 'the journal'}: {', '.join(missing)}."
        ))
        score -= len(missing)

    # ── 4. Reference count ────────────────────────────────────────────────────
    ref_count = count_references(text)
    ref_limit  = spec.get("max_references")
    if ref_limit and ref_count > ref_limit:
        findings.append(finding(
            "References", MAJOR,
            f"Reference count exceeds limit ({ref_count} / {ref_limit} allowed)",
            "",
            f"Reduce references by {ref_count - ref_limit}. Prioritise the most recent and directly relevant citations."
        ))
        score -= 1
    elif ref_count == 0:
        findings.append(finding(
            "References", MAJOR,
            "No references detected — verify reference list format",
            "",
            "Ensure references are in a labelled 'References' section at the end of the manuscript."
        ))

    # ── 5. Figure count ───────────────────────────────────────────────────────
    fig_dir   = None
    fig_count = count_figures(text, fig_dir)
    fig_limit  = spec.get("max_figures")
    if fig_limit and fig_count > fig_limit:
        findings.append(finding(
            "Figures", MAJOR,
            f"Figure count exceeds limit ({fig_count} / {fig_limit} allowed)",
            "",
            f"Move {fig_count - fig_limit} figure(s) to supplementary materials."
        ))
        score -= 1

    # ── 6. Mandatory declarations ─────────────────────────────────────────────
    for key, pattern, label in MANDATORY_DECLARATIONS:
        found = bool(re.search(pattern, text, re.IGNORECASE))
        if not found:
            findings.append(finding(
                "Declarations", MAJOR,
                f"Missing: {label}",
                "",
                f"Add a '{label}' statement. This is required by virtually all journals."
            ))
            score -= 1

    # ── 7. Ethics statement ───────────────────────────────────────────────────
    is_human   = bool(re.search(r"\bhuman\b|\bpatient\b|\bparticipant\b|\bsubject\b", text, re.IGNORECASE))
    is_animal  = bool(re.search(r"\banimal\b|\bmouse\b|\brat\b|\bpig\b|\bprimate\b", text, re.IGNORECASE))
    ethics_found = bool(re.search(
        r"ethics\s+(?:committee|board|approval|statement)|irb|iacuc|"
        r"institutional\s+review|approved\s+by|consent\s+(?:was\s+)?obtained|"
        r"helsinki|informed\s+consent",
        text, re.IGNORECASE
    ))
    if (is_human or is_animal) and not ethics_found:
        findings.append(finding(
            "Ethics", CRITICAL,
            "Human or animal study detected but no ethics approval / consent statement found",
            "",
            "Add an ethics statement specifying the approving body (IRB/IACUC), "
            "protocol number, and (for human studies) informed consent procedure."
        ))
        score -= 2

    # ── 8. Title quality ──────────────────────────────────────────────────────
    title_match = re.search(r"^#\s+(.+)$", text, re.MULTILINE)
    if title_match:
        title = title_match.group(1).strip()
        title_words = len(title.split())
        if title_words > 20:
            findings.append(finding(
                "Title", MINOR,
                f"Title is long ({title_words} words) — most journals recommend ≤ 15–20 words",
                title[:80],
                "Consider shortening. A concise title improves discoverability and searchability."
            ))
        if not re.search(r"[A-Z]", title):
            findings.append(finding(
                "Title", MINOR, "Title appears to be all lower-case", title[:60],
                "Capitalise the title per journal style."
            ))
        # Check for colon (informative subtitle structure)
        if title_words > 15 and ":" not in title:
            findings.append(finding(
                "Title", INFO,
                "Long title without a colon — consider a topic: finding structure",
                title[:80],
                "e.g. '[Topic/Method]: [Key Finding]' improves scannability."
            ))
    else:
        findings.append(finding(
            "Title", MAJOR,
            "No level-1 heading (title) detected",
            "",
            "Add the manuscript title as a Markdown level-1 heading (# Title)."
        ))
        score -= 1

    # ── 9. Preprint disclosure ────────────────────────────────────────────────
    preprint = bool(re.search(r"biorxiv|medrxiv|arxiv|preprint|posted\s+on", text, re.IGNORECASE))
    if preprint:
        preprint_policy = journal_data.get("preprint_policy", "") if journal_data else ""
        if preprint_policy and "not accepted" in preprint_policy.lower():
            findings.append(finding(
                "Preprint", CRITICAL,
                f"{journal_name} does not accept manuscripts posted as preprints",
                "",
                f"Policy: {preprint_policy}. Verify before submitting."
            ))
            score -= 2
        else:
            findings.append(finding(
                "Preprint", INFO,
                "Manuscript mentions a preprint — verify journal's preprint policy",
                "",
                f"Policy for {journal_name or 'this journal'}: "
                f"{preprint_policy or 'check journal website'}."
            ))

    # ── 10. Open access ──────────────────────────────────────────────────────
    oa = journal_data.get("open_access_option") if journal_data else None
    if oa is True:
        findings.append(finding(
            "Open access", INFO,
            f"{journal_name} offers open access — select license during submission",
            "",
            "Choose CC-BY (gold OA) or CC-BY-NC-ND as applicable. "
            "Check whether your funder mandates a specific OA license."
        ))

    score = max(0, min(10, score))
    critical = [f for f in findings if f["severity"] == CRITICAL]
    status = CRITICAL if critical else (MAJOR if score < 7 else "PASS")

    return {
        "reviewer": "Editor",
        "score": score,
        "status": status,
        "findings": findings,
        "word_count": total_words,
        "summary": (
            f"Score {score}/10. "
            f"{len(critical)} critical, "
            f"{len([f for f in findings if f['severity']==MAJOR])} major, "
            f"{len([f for f in findings if f['severity']==MINOR])} minor issues."
        ),
    }


# ══════════════════════════════════════════════════════════════════════════════
# REVIEWER 4 — AI DIAGNOSTICIAN
# Detects AI-generated prose signatures at sentence, paragraph, and structure
# level.  Rule-based; no LLM call required.
# ══════════════════════════════════════════════════════════════════════════════

# ── AI phrase markers — English (150+ entries, 8 categories) ─────────────────
_AI_PHRASES_EN: list[str] = [
    # 1. Sycophantic / meta openers
    "it is worth noting", "it is worth mentioning", "it is important to note",
    "it is important to mention", "it should be noted", "it should be mentioned",
    "it is crucial to note", "it is essential to note", "it is interesting to note",
    "importantly,", "notably,", "interestingly,", "remarkably,", "significantly,",
    "crucially,", "critically,",
    # 2. Empty value claims
    "plays a crucial role", "plays a pivotal role", "plays an important role",
    "plays a vital role", "plays a key role", "plays a central role",
    "plays a significant role", "plays a fundamental role",
    "is of paramount importance", "is of utmost importance", "is of great importance",
    "is of critical importance", "is critically important", "is vitally important",
    "highlights the importance", "underscores the importance", "emphasizes the importance",
    "demonstrates the importance", "illustrates the importance",
    "sheds light on", "paves the way", "paves the way for",
    "holds great promise", "holds significant promise", "shows great promise",
    "represents a significant advance", "represents a major advance",
    "represents an important step", "represents a crucial step",
    "offers valuable insights", "provides valuable insights",
    "provides a comprehensive understanding", "offers a comprehensive overview",
    "provides an in-depth analysis", "offers an in-depth understanding",
    "a growing body of evidence", "a growing body of literature",
    "a substantial body of evidence", "a wealth of evidence",
    "has the potential to", "has the potential for",
    "opens up new avenues", "opens new possibilities",
    "is a promising approach", "represents a promising strategy",
    # 3. Hollow transitions / connectors
    "in summary,", "in conclusion,", "to summarize,", "to conclude,",
    "taken together,", "collectively,", "overall,", "in light of",
    "in this context,", "with this in mind,", "against this backdrop,",
    "building on this,", "building upon this,", "in line with this,",
    "consistent with this,", "in accordance with this,",
    # 4. Filler adjectives / overused intensifiers
    "pivotal", "paramount", "intricate", "multifaceted", "nuanced",
    "leverages", "underscores", "groundbreaking", "transformative",
    "revolutionary", "unprecedented", "game-changing", "game-changer",
    "paradigm shift", "paradigm-shifting", "state-of-the-art",
    "cutting-edge", "innovative", "novel approach", "robust framework",
    "holistic approach", "seamless integration", "dynamic landscape",
    "rapidly evolving", "ever-evolving", "rapidly advancing",
    "synergistic", "synergistic effect", "synergistic relationship",
    "comprehensive framework", "comprehensive approach",
    # 5. Self-referential / paper describing itself
    "in this review", "in this study we aim", "this paper aims",
    "this review aims", "the purpose of this review", "the aim of this study",
    "this work aims to provide", "this article aims to",
    "this paper seeks to", "this study seeks to", "this work seeks to",
    "we aim to provide", "we aim to discuss", "we aim to explore",
    "this manuscript provides", "the present study aims",
    "herein, we", "herein we report", "herein we present",
    # 6. Delve / explore cluster
    "delve into", "delves into", "delved into",
    "tapestry", "landscape of", "ecosystem of",
    "in-depth exploration", "thorough exploration",
    "comprehensive exploration",
    # 7. Vague generalisations (hallucination risk)
    "has been extensively studied", "has been widely studied",
    "has been well documented", "is well documented",
    "numerous studies have", "many studies have", "several studies have",
    "previous research has shown", "prior research has demonstrated",
    "it is generally accepted", "it is widely accepted",
    "it is commonly believed", "it is widely believed",
    "it has long been known", "it is well known that",
    "evidence suggests that", "evidence indicates that",
    "research suggests that", "the literature suggests",
    # 8. Padding / filler sentence starters
    "first and foremost,", "last but not least,",
    "needless to say,", "it goes without saying",
    "as mentioned above", "as mentioned earlier", "as previously mentioned",
    "as discussed above", "as noted above", "as stated above",
    "in today's world", "in today's rapidly", "in the modern era",
    "in recent years,", "in recent decades,", "in the past decade,",
]

# ── AI phrase markers — Chinese (50+ entries) ────────────────────────────────
_AI_PHRASES_ZH: list[str] = [
    # 元叙述（纸描述自己）
    "本文旨在", "本研究旨在", "本综述旨在", "本文将",
    "本研究将", "本文从", "本文通过", "本研究通过",
    # 空泛价值声明
    "具有重要意义", "具有重要价值", "具有重要作用",
    "发挥重要作用", "发挥关键作用", "发挥至关重要的作用",
    "不可或缺", "至关重要", "举足轻重",
    "具有广阔的应用前景", "具有良好的应用前景",
    "为……奠定基础", "为……提供新思路", "为……提供理论依据",
    # 无锚定断言
    "研究表明", "大量研究表明", "众多研究表明",
    "已有研究证实", "研究已证明", "已被广泛证明",
    "已知", "众所周知", "广为人知",
    # 空洞过渡
    "值得注意的是", "值得关注的是", "值得指出的是",
    "值得强调的是", "需要指出的是", "需要强调的是",
    "与此同时", "此外，", "另外，", "同时，",
    "综上所述", "总体而言", "总的来说", "总结而言",
    "在此基础上", "在此背景下", "在此背景下，",
    # 填充形容词
    "深入探讨", "系统分析", "全面探讨", "系统综述",
    "深入分析", "全面分析", "全面了解", "全面认识",
    "前所未有", "革命性", "突破性", "创新性",
]

# Combined flat list for fast in-text search
_AI_PHRASES: list[str] = _AI_PHRASES_EN + _AI_PHRASES_ZH

# ── Transition-word sentence openers ─────────────────────────────────────────
_AI_OPENER_RE = re.compile(
    r"^(?:furthermore|moreover|additionally|in addition|"
    r"however|nevertheless|nonetheless|on the other hand|"
    r"therefore|thus|hence|consequently|"
    r"indeed|certainly|clearly|obviously|undoubtedly|"
    r"notably|importantly|interestingly|remarkably|"
    r"specifically|particularly|generally|typically|"
    r"essentially|fundamentally|ultimately|initially|"
    r"subsequently|finally|lastly)[,\s]",
    re.IGNORECASE,
)

# ── Patterns that suggest fabricated / unsourced claims ───────────────────────
_UNANCHORED_CLAIM_RE = [
    r"studies\s+have\s+shown\s+that(?!\s*\[|\s*\()",
    r"(?:it|this)\s+has\s+been\s+(?:well[\s-])?established\s+that(?!\s*\[|\s*\()",
    r"(?:it\s+is\s+|is\s+)(?:widely|generally|broadly)\s+(?:accepted|recognized|known)\s+that(?!\s*\[|\s*\()",
    r"research\s+(?:consistently\s+)?(?:shows?|demonstrates?|suggests?)\s+that(?!\s*\[|\s*\()",
    r"(?:many|numerous|several|previous|prior)\s+studies\s+(?:have|has)\s+(?:shown|demonstrated|reported|found)\s+that(?!\s*\[|\s*\()",
    r"(?:it\s+is\s+|is\s+)(?:well[\s-])?known\s+that(?!\s*\[|\s*\()",
    r"evidence\s+(?:suggests?|indicates?|shows?)\s+that(?!\s*\[|\s*\()",
    r"(?:it\s+has\s+been|has\s+been)\s+(?:well[\s-])?documented\s+that(?!\s*\[|\s*\()",
]

# ── Empty evaluative adjectives ───────────────────────────────────────────────
_EMPTY_EVAL_RE = [
    r"\b(?:excellent|outstanding|remarkable|extraordinary|exceptional|superior|"
    r"impressive|powerful|strong|robust|remarkable|unprecedented)\s+"
    r"(?:performance|efficacy|results?|activity|effect|outcome|improvement|reduction)",
]

# ── Self-talk / first-person AI self-description ──────────────────────────────
_SELF_TALK_RE = re.compile(
    r"\b(?:as an ai|as a language model|i am an ai|i cannot|i don'?t have|"
    r"i was trained|my training data|my knowledge cutoff|"
    r"作为ai|作为语言模型|我是ai|我是人工智能|我的知识截止|我无法|"
    r"i must clarify|i should note that i am|as an artificial intelligence)\b",
    re.IGNORECASE,
)

# ── Passive voice density ─────────────────────────────────────────────────────
# Matches "was/were/is/are/been + past participle" constructions
_PASSIVE_RE = re.compile(
    r"\b(?:was|were|is|are|been|be|being)\s+"
    r"(?:\w+ly\s+)?(?:\w+ed|found|shown|observed|reported|demonstrated|"
    r"performed|conducted|measured|analyzed|evaluated|assessed|used|"
    r"treated|compared|examined|investigated|determined|identified|"
    r"calculated|estimated|obtained|detected|confirmed|validated)\b",
    re.IGNORECASE,
)

# ── Paragraph opener monotony ─────────────────────────────────────────────────
# Openers that AI overuses at the start of paragraphs
_PARA_OPENER_RE = re.compile(
    r"^(?:the\s+\w+|this\s+\w+|these\s+\w+|in\s+this|in\s+the|"
    r"to\s+(?:the|our|this)|as\s+a|as\s+an|it\s+is|there\s+is|there\s+are)\b",
    re.IGNORECASE,
)


def run_ai_diagnostician(text: str, config: dict = {}, use_llm: bool = False) -> dict:
    """
    AI Diagnostician: detects AI-generated prose signatures across 6 dimensions.

    When use_llm=True, delegates to Gemini-1.5-flash for deeper semantic analysis.
    Falls back to rule-based implementation automatically if Gemini is unavailable
    or returns an unparseable response.

    1. AI phrase markers (canonical LLM vocabulary)
    2. Transition-word opener density (AI over-relies on sentence connectors)
    3. Self-talk / meta-description (AI describing itself)
    4. Unanchored factual claims (assertions without citation)
    5. Empty evaluative language (subjective praise without data)
    6. Sentence-length rhythm (AI prose is suspiciously uniform)
    """
    if use_llm:
        try:
            import llm_backend as _llm
            result = _llm.call_expert("ai_diagnostician", text)
            result["_mode"] = "gemini"
            return result
        except Exception as exc:
            logger.warning("AI Diagnostician LLM failed (%s) — falling back to rules.", exc)

    import statistics as _stats

    findings: list[dict] = []
    score = 10

    body = re.sub(r"```[\s\S]*?```", "", text)
    body_lines = [ln for ln in body.splitlines() if not ln.startswith("#")]
    body_clean = " ".join(body_lines)
    sentences = _sentences(body_clean)
    n = max(1, len(sentences))

    # ── 1. AI phrase markers ──────────────────────────────────────────────────
    hits: list[str] = []
    low = body_clean.lower()
    for phrase in _AI_PHRASES:
        phrase_plain = phrase.replace("(ly)", "").replace("(", "").replace(")", "")
        if phrase_plain in low:
            ctx = _quote(body_clean, re.escape(phrase_plain), 60)
            hits.append(f'"{phrase_plain}" — {ctx}')
    if hits:
        sev = CRITICAL if len(hits) >= 8 else (MAJOR if len(hits) >= 4 else MINOR)
        score -= min(4, len(hits) // 2)
        findings.append(finding(
            "AI phrase markers", sev,
            f"{len(hits)} canonical AI phrase(s) detected across manuscript",
            "\n".join(hits[:5]),
            "Replace each flagged phrase with precise, evidence-backed language. "
            "E.g. 'plays a crucial role' → cite the mechanism and quantify it; "
            "'it is worth noting' → delete the opener, state the fact directly; "
            "'delves into' → 'examines' or 'analyses'. "
            "Target: 0 phrase markers before submission.",
        ))

    # ── 2. Transition-opener density ─────────────────────────────────────────
    opener_count = sum(
        1 for s in sentences if _AI_OPENER_RE.match(s.strip()))
    opener_rate = opener_count / n
    if opener_rate > 0.18:
        sev = MAJOR if opener_rate > 0.28 else MINOR
        score -= 1
        findings.append(finding(
            "Transition-opener density", sev,
            f"{opener_count}/{n} sentences ({opener_rate:.0%}) open with a "
            "formulaic transition word (AI signature)",
            "",
            "Vary sentence structure. Not every paragraph needs a connector. "
            "Start sentences with the subject or a specific finding instead.",
        ))

    # ── 3. Self-talk / meta-description ──────────────────────────────────────
    self_talk_hits = _SELF_TALK_RE.findall(text)
    meta_hits = [s for s in sentences if re.search(
        r"in\s+this\s+(?:review|paper|study|article|work)\s+(?:we\s+)?(?:aim|seek|provide|discuss|"
        r"present|demonstrate|explore|overview|examine|highlight)",
        s, re.IGNORECASE)]
    total_self = len(self_talk_hits) + len(meta_hits)
    if self_talk_hits:
        score -= 3
        findings.append(finding(
            "AI self-talk", CRITICAL,
            f"AI self-identification language detected ({len(self_talk_hits)} instance(s))",
            str(self_talk_hits[:3]),
            "Remove all phrases where the AI describes itself as an AI or a language model. "
            "This text must not appear in any manuscript or client-facing document.",
        ))
    if len(meta_hits) > 4:
        score -= 1
        findings.append(finding(
            "Meta-description", MAJOR,
            f"{len(meta_hits)} sentences describe the paper's own purpose/structure (AI meta-narration)",
            meta_hits[0][:120] if meta_hits else "",
            "Keep one clear aim-of-study sentence in the Introduction. "
            "Delete repetitions in Abstract, Discussion, and Conclusion that re-announce the paper.",
        ))

    # ── 4. Unanchored factual claims ─────────────────────────────────────────
    unanchored: list[str] = []
    for pat in _UNANCHORED_CLAIM_RE:
        for m in re.finditer(pat, text, re.IGNORECASE):
            start = max(0, m.start() - 30)
            snippet = text[start: m.end() + 80].replace("\n", " ")
            unanchored.append(snippet[:140])
    if unanchored:
        sev = CRITICAL if len(unanchored) >= 3 else MAJOR
        score -= min(3, len(unanchored))
        findings.append(finding(
            "Unanchored claims", sev,
            f"{len(unanchored)} assertion(s) of established fact with no citation "
            "(hallucination risk zone)",
            unanchored[0] if unanchored else "",
            "Every 'studies have shown that…', 'it is well established that…', and "
            "'research demonstrates that…' must be immediately followed by [citation]. "
            "If no citation exists, reframe as a hypothesis or remove the claim.",
        ))

    # ── 5. Empty evaluative language ─────────────────────────────────────────
    empty_evals: list[str] = []
    for pat in _EMPTY_EVAL_RE:
        for m in re.finditer(pat, text, re.IGNORECASE):
            start = max(0, m.start() - 20)
            empty_evals.append(text[start: m.end() + 60].replace("\n", " ")[:100])
    if empty_evals:
        findings.append(finding(
            "Empty evaluative language", MINOR,
            f"{len(empty_evals)} evaluative phrase(s) with no numeric/mechanistic support",
            empty_evals[0] if empty_evals else "",
            "Replace 'excellent/outstanding/remarkable [performance]' with specific metrics "
            "(e.g. 'achieved 94% sensitivity (95% CI 88–97%) vs 71% for the comparator').",
        ))
        score -= 1

    # ── 6. Sentence-length rhythm ─────────────────────────────────────────────
    wc = [len(s.split()) for s in sentences if len(s.split()) >= 4]
    if len(wc) >= 15:
        stdev = _stats.stdev(wc)
        mean  = _stats.mean(wc)
        if stdev < 6 and mean > 18:
            score -= 1
            findings.append(finding(
                "Sentence rhythm", MINOR,
                f"Sentence length suspiciously uniform (mean {mean:.0f} words, "
                f"σ={stdev:.1f}) — AI prose signature",
                "",
                "Mix short punchy sentences with longer analytical ones. "
                "AI prose tends to a steady 20–28 word cadence throughout.",
            ))

    # ── 7. Passive voice density ──────────────────────────────────────────────
    passive_hits = _PASSIVE_RE.findall(body_clean)
    passive_rate = len(passive_hits) / n
    if passive_rate > 0.30 and n >= 20:
        sev = MAJOR if passive_rate > 0.45 else MINOR
        score -= 1
        findings.append(finding(
            "Passive voice density", sev,
            f"Passive voice rate {passive_rate:.0%} ({len(passive_hits)}/{n} sentences) "
            f"— AI writing overuses passive constructions",
            "",
            "Aim for < 25% passive voice. Rewrite passive results sentences in active "
            "voice: 'We observed X' instead of 'X was observed'. "
            "Passive is acceptable in Methods; avoid it in Results/Discussion.",
        ))

    # ── 8. Paragraph opener monotony ─────────────────────────────────────────
    paragraphs_raw = [p.strip() for p in body_clean.split("\n\n")
                      if p.strip() and len(p.split()) > 20]
    if len(paragraphs_raw) >= 5:
        opener_matches = sum(
            1 for p in paragraphs_raw if _PARA_OPENER_RE.match(p))
        para_opener_rate = opener_matches / len(paragraphs_raw)
        if para_opener_rate > 0.55:
            findings.append(finding(
                "Paragraph opener monotony", MINOR,
                f"{opener_matches}/{len(paragraphs_raw)} paragraphs ({para_opener_rate:.0%}) "
                "open with a generic pattern ('The…', 'This…', 'In this…') — AI signature",
                "",
                "Vary paragraph openers: start with a key finding, a specific observation, "
                "a counterpoint, or a named entity. Generic openers flatten academic prose.",
            ))

    # ── 9. Chinese AI markers ─────────────────────────────────────────────────
    zh_hits = [ph for ph in _AI_PHRASES_ZH if ph in text]
    if zh_hits:
        sev = MAJOR if len(zh_hits) >= 5 else MINOR
        score -= min(2, len(zh_hits) // 3)
        findings.append(finding(
            "Chinese AI phrase markers", sev,
            f"{len(zh_hits)} Chinese AI writing pattern(s) detected",
            "；".join(zh_hits[:5]),
            "Replace generic Chinese AI phrases with precise, evidence-backed expressions. "
            "E.g. '具有重要意义' → 具体说明重要性的机制和数据；'值得注意的是' → 直接陈述事实。",
        ))

    score = max(0, min(10, score))
    critical = [f for f in findings if f["severity"] == CRITICAL]
    status   = CRITICAL if critical else (MAJOR if score < 7 else "PASS")

    return {
        "reviewer":          "AI Diagnostician",
        "score":             score,
        "status":            status,
        "findings":          findings,
        "ai_phrase_count":   len(hits),
        "unanchored_count":  len(unanchored),
        "opener_rate":       round(opener_rate, 3),
        "passive_rate":      round(passive_rate, 3),
        "zh_phrase_count":   len(zh_hits),
        "summary": (
            f"Score {score}/10. "
            f"{len(hits)} AI phrase(s) (EN), {len(zh_hits)} AI phrase(s) (ZH), "
            f"{len(unanchored)} unanchored claim(s), "
            f"{len(self_talk_hits)} self-talk hit(s), "
            f"passive {passive_rate:.0%}. "
            f"{len(critical)} critical."
        ),
    }


# ══════════════════════════════════════════════════════════════════════════════
# REVIEWER 5 — CITATION AUDITOR
# Checks whether citations are used with evidential intent (not just topical),
# detects orphan/dangling patterns, and flags hallucination-risk citation gaps.
# Pure text analysis — no network call.
# ══════════════════════════════════════════════════════════════════════════════

# Sentences that cite with weak/hedged claim language (TOPICAL risk)
_TOPICAL_CITE_RE = re.compile(
    r"(?:related to|associated with|in the context of|regarding|concerning|"
    r"as reported by|as described by|according to|reviewed in|summarized in|"
    r"for (?:a )?review,?\s*see)\s*\[?\d",
    re.IGNORECASE,
)

# Sentences making strong claims without any citation
_STRONG_UNCITED_RE = re.compile(
    r"(?:significantly|markedly|substantially|dramatically|"
    r"completely|fully|absolutely|definitively)\s+"
    r"(?:increased?|decreased?|reduced?|improved?|inhibited?|"
    r"enhanced?|suppressed?|eliminated?|blocked?|prevented?)"
    r"(?!\s*\[|\s*\(\d)",
    re.IGNORECASE,
)


def run_citation_auditor(text: str, config: dict = {}, use_llm: bool = False) -> dict:
    """
    Citation Auditor: semantic-level citation hygiene check.

    When use_llm=True, delegates to Gemini-1.5-flash for deeper semantic analysis.
    Falls back to rule-based implementation automatically on any failure.

    1. Citation density — citations per 100 words (too sparse = hallucination risk)
    2. Claim-citation gap — strong quantitative claims with no citation
    3. Topical citation pattern — cited for topic not evidence
    4. Citation clustering — >4 consecutive paragraphs with no citation
    5. Abstract citation check — abstracts should be self-contained (few/no refs)
    6. Methods citation — novel methods must be cited
    """
    if use_llm:
        try:
            import llm_backend as _llm
            result = _llm.call_expert("citation_auditor", text)
            result["_mode"] = "gemini"
            return result
        except Exception as exc:
            logger.warning("Citation Auditor LLM failed (%s) — falling back to rules.", exc)

    findings: list[dict] = []
    score = 10

    # Strip code/figure captions
    clean = re.sub(r"```[\s\S]*?```", "", text)

    # Count in-text citations [n] or (Author Year)
    bracket_cites = re.findall(r"\[\d+(?:,\s*\d+)*\]", clean)
    author_cites  = re.findall(r"\([A-Z][a-z]+(?:\s+et\s+al\.?)?,?\s*\d{4}\)", clean)
    total_cites   = len(bracket_cites) + len(author_cites)
    word_count    = max(1, len(re.findall(r"\b\w+\b", clean)))
    cite_density  = total_cites / word_count * 100  # per 100 words

    # ── 1. Citation density ───────────────────────────────────────────────────
    if cite_density < 0.5 and word_count > 800:
        sev = CRITICAL if cite_density < 0.2 else MAJOR
        score -= 2
        findings.append(finding(
            "Citation density", sev,
            f"Only {total_cites} citation(s) in {word_count:,} words "
            f"({cite_density:.2f}/100 words) — hallucination risk",
            "",
            "A typical research article cites 0.8–2.0 refs per 100 words. "
            "Review every factual claim and ensure it is supported by a citation. "
            "Missing citations are a primary vector for AI-hallucinated 'facts'.",
        ))
    elif cite_density > 4.0:
        findings.append(finding(
            "Citation density", MINOR,
            f"Very high citation density ({cite_density:.1f}/100 words) — "
            "may indicate citation padding",
            "",
            "Ensure each citation is genuinely evidential. Remove topical/decorative citations.",
        ))

    # ── 2. Strong quantitative claims without citations ───────────────────────
    uncited_strong = []
    for m in _STRONG_UNCITED_RE.finditer(clean):
        start = max(0, m.start() - 40)
        uncited_strong.append(clean[start: m.end() + 80].replace("\n", " ")[:130])
    if uncited_strong:
        sev = CRITICAL if len(uncited_strong) >= 3 else MAJOR
        score -= min(3, len(uncited_strong))
        findings.append(finding(
            "Uncited strong claims", sev,
            f"{len(uncited_strong)} quantitative/absolute claim(s) with no immediately "
            "following citation (hallucination risk zone)",
            uncited_strong[0] if uncited_strong else "",
            "Every claim of a measured effect (significantly increased, markedly reduced, …) "
            "must be followed immediately by [n] or (Author Year). "
            "If no citation exists, remove the quantifier or soften to 'may'.",
        ))

    # ── 3. Topical citation patterns ─────────────────────────────────────────
    topical_hits = _TOPICAL_CITE_RE.findall(clean)
    if len(topical_hits) > 3:
        findings.append(finding(
            "Topical citation pattern", MINOR,
            f"{len(topical_hits)} citation(s) use topic-linking language "
            "('related to [n]', 'as reviewed in [n]') — may be TOPICAL not EVIDENTIAL",
            topical_hits[0] if topical_hits else "",
            "Prefer evidential framing: 'Smith et al. demonstrated X [n]' over "
            "'X has been studied [n]'. Topical citations do not support quantitative claims.",
        ))

    # ── 4. Citation-free paragraph clusters ──────────────────────────────────
    paragraphs = [p.strip() for p in re.split(r"\n{2,}", clean)
                  if p.strip() and not p.strip().startswith("#")
                  and len(p.split()) > 40]
    has_cite = [bool(re.search(r"\[\d|\([A-Z][a-z].*\d{4}\)", p)) for p in paragraphs]
    max_gap = 0
    cur_gap = 0
    for c in has_cite:
        cur_gap = 0 if c else cur_gap + 1
        max_gap = max(max_gap, cur_gap)
    if max_gap >= 4:
        score -= 1
        findings.append(finding(
            "Citation-free paragraphs", MAJOR,
            f"Up to {max_gap} consecutive paragraphs without any citation",
            "",
            "Long stretches of text without citations suggest either original synthesis "
            "(acceptable in Discussion — label as author interpretation) or AI-generated "
            "fill (flag for manual review and citation search).",
        ))

    # ── 5. Abstract citation policy ──────────────────────────────────────────
    abstract = _section_text(text, "Abstract")
    if abstract:
        abs_cites = len(re.findall(r"\[\d+\]|\([A-Z][a-z]+.*?\d{4}\)", abstract))
        if abs_cites > 5:
            findings.append(finding(
                "Abstract citations", MINOR,
                f"Abstract contains {abs_cites} citation(s) — most journals prefer "
                "abstracts to be self-contained",
                "",
                "Check journal policy on abstract citations. Nature, NEJM, Cell, and most "
                "clinical journals require citation-free abstracts.",
            ))

    # ── 6. Methods section citation check ────────────────────────────────────
    methods = _section_text(text, "Methods") or _section_text(text, "Materials and Methods")
    if methods:
        novel_method = bool(re.search(
            r"(?:novel|new|modified|adapted|custom|in-house|developed)\s+"
            r"(?:method|assay|protocol|algorithm|pipeline|approach|tool)",
            methods, re.IGNORECASE,
        ))
        methods_cites = len(re.findall(r"\[\d+\]|\([A-Z][a-z]+.*?\d{4}\)", methods))
        method_words  = len(methods.split())
        method_density = methods_cites / max(1, method_words) * 100
        if novel_method and methods_cites == 0:
            score -= 1
            findings.append(finding(
                "Methods citation", MAJOR,
                "Novel/modified method described in Methods section has no citations",
                "",
                "Cite the original method protocol and any adaptations. "
                "Un-cited novel methods cannot be reproduced.",
            ))
        elif method_density < 0.3 and method_words > 300:
            findings.append(finding(
                "Methods citation density", MINOR,
                f"Methods section has low citation density ({method_density:.2f}/100 words, "
                f"{methods_cites} citation(s) in {method_words} words)",
                "",
                "Standard statistical tests, assay kits, and established protocols "
                "should all be cited to their authoritative source.",
            ))

    # ── 7. DOI / PMID extraction + format validation ──────────────────────────
    try:
        import citation_verifier as _cv
        extracted_dois  = _cv.extract_dois(clean)
        extracted_pmids = _cv.extract_pmids(clean)
        bad_format = [d for d in extracted_dois if not _cv.DOI_FORMAT.match(d)]
        if bad_format:
            score -= 1
            findings.append(finding(
                "DOI format", MAJOR,
                f"{len(bad_format)} DOI(s) with invalid format (not matching 10.xxxx/suffix)",
                "; ".join(bad_format[:4]),
                "Correct malformed DOIs. Valid DOI format: 10.XXXX/suffix. "
                "Malformed DOIs are a hallucination signal.",
            ))
        _cv_available = True
        _n_dois  = len(extracted_dois)
        _n_pmids = len(extracted_pmids)
    except ImportError:
        _cv_available = False
        _n_dois = _n_pmids = 0
        bad_format = []

    # ── 8. Live verification: S2 → CrossRef → PubMed (optional, use_llm flag) ─
    verified_count = not_found_count = 0
    if _cv_available and use_llm:
        try:
            vr = _cv.verify_all(clean, max_dois=20, max_pmids=8)
            verified_count  = vr["dois"]["verified"] + vr["pmids"]["verified"]
            not_found_count = (len(vr["dois"]["not_found"])
                               + len(vr["pmids"]["not_found"])
                               + len(vr["dois"]["invalid"]))
            sev_map = {"CRITICAL": CRITICAL, "MAJOR": MAJOR,
                       "MINOR": MINOR, "INFO": INFO}
            for f in vr["findings"]:
                findings.append({
                    "category":       f.get("category", "Citation verification"),
                    "severity":       sev_map.get(f.get("severity", "INFO"), INFO),
                    "issue":          f.get("issue", ""),
                    "evidence":       f.get("evidence", ""),
                    "recommendation": f.get("recommendation", ""),
                })
                if f.get("severity") in ("CRITICAL", "MAJOR"):
                    score -= 1
        except Exception as exc:
            logger.warning("Citation verification (S2/CrossRef/PubMed) failed: %s", exc)
    elif _cv_available and (_n_dois + _n_pmids) > 0:
        findings.append(finding(
            "Citation verification", INFO,
            f"{_n_dois} DOI(s) + {_n_pmids} PMID(s) found — "
            "run with use_llm=True to verify via S2 / CrossRef / PubMed",
            "", "",
        ))

    score = max(0, min(10, score))
    critical = [f for f in findings if f["severity"] == CRITICAL]
    status   = CRITICAL if critical else (MAJOR if score < 7 else "PASS")

    verify_note = (f", {verified_count} verified / {not_found_count} not_found"
                   if (verified_count or not_found_count) else "")
    return {
        "reviewer":        "Citation Auditor",
        "score":           score,
        "status":          status,
        "findings":        findings,
        "total_citations": total_cites,
        "cite_density":    round(cite_density, 3),
        "uncited_strong":  len(uncited_strong),
        "dois_found":      _n_dois,
        "pmids_found":     _n_pmids,
        "dois_verified":   verified_count,
        "dois_not_found":  not_found_count,
        "summary": (
            f"Score {score}/10. "
            f"{total_cites} citation(s), density {cite_density:.2f}/100 words. "
            f"{len(uncited_strong)} uncited strong claim(s). "
            f"{_n_dois} DOI(s) + {_n_pmids} PMID(s) extracted"
            f"{verify_note}. {len(critical)} critical."
        ),
    }


# ══════════════════════════════════════════════════════════════════════════════
# REVIEWER 6 — REPRODUCIBILITY REVIEWER
# Checks whether experiments, analyses, and data are described with enough
# detail for an independent lab to reproduce them.
# ══════════════════════════════════════════════════════════════════════════════

_REPRODUCIBILITY_REQUIRED = [
    # (label, regex_to_find_claim, regex_to_find_detail)
    ("Sample size / n", r"\bn\s*=\s*\d|n\s*=\s*\d", None),   # presence check only
    ("Statistical software", r"\bstatistic|\banalys",
     r"\bR\b|\bspss\b|\bprism\b|\bsas\b|\bstata\b|\bpython\b|\bscipy\b|\bmatlab\b"),
    ("Software version", r"\bR\b|\bspss\b|\bprism\b|\bpython\b",
     r"v(?:ersion)?\s*\d|\d+\.\d+"),
    ("Cell line source / authentication", r"\bcell\s+line|\bHEK|\bCHO|\bJurkat|\bRaji\b",
     r"ATCC|DSMZ|mycoplasma|STR|authentcat"),
    ("Antibody clone / catalog", r"\bantibod(?:y|ies)|\bmAb\b|\bIgG\b",
     r"clone\s+\w+|catalog\s*(?:no\.?|number|#)|Cat\.?\s*(?:no\.?|#)"),
]


def run_reproducibility_reviewer(text: str, config: dict = {}, use_llm: bool = False) -> dict:
    """
    Reproducibility Reviewer: checks methods for independent replication.

    When use_llm=True, delegates to Gemini-1.5-flash for deeper semantic analysis.
    Falls back to rule-based implementation automatically on any failure.

    1. Materials & Methods section completeness
    2. Sample size / statistical power reported
    3. Software + version specified
    4. Cell line / reagent provenance
    5. Data / code availability statement
    6. Randomisation & blinding (for in vivo / clinical)
    7. Raw data deposition (repository link)
    """
    if use_llm:
        try:
            import llm_backend as _llm
            result = _llm.call_expert("reproducibility", text)
            result["_mode"] = "gemini"
            return result
        except Exception as exc:
            logger.warning("Reproducibility Reviewer LLM failed (%s) — falling back to rules.", exc)

    findings: list[dict] = []
    score = 10

    methods = (_section_text(text, "Methods")
               or _section_text(text, "Materials and Methods")
               or _section_text(text, "Material and Methods"))

    # ── 1. Methods section existence ─────────────────────────────────────────
    if not methods or len(methods.split()) < 100:
        score -= 3
        findings.append(finding(
            "Methods section", CRITICAL,
            "Methods section absent or too short (<100 words)",
            "",
            "A complete Methods section is required for reproducibility. "
            "Include detailed protocols for each experiment.",
        ))
        # Cannot perform further methods checks without section
        methods = text  # fall back to full text for remaining checks

    # ── 2. Sample size ────────────────────────────────────────────────────────
    n_match = re.search(r"\bn\s*=\s*(\d+)", text, re.IGNORECASE)
    if not n_match:
        score -= 1
        findings.append(finding(
            "Sample size", MAJOR,
            "No explicit sample size (n=) found in manuscript",
            "",
            "State the sample size (n) for every experimental group. "
            "If this is a computational study, state the dataset size.",
        ))

    # ── 3. Statistical software + version ────────────────────────────────────
    stat_software = bool(re.search(
        r"\bR\s+(?:version\s+)?\d|\bSPSS\s+(?:v|version\s+)?\d|\bPrism\s+(?:v|version\s+)?\d|"
        r"Python\s+\d|\bGraphPad\b|\bSAS\s+\d|\bSTATA\s+\d|\bSciPy\b|\bscikit-learn\b",
        methods, re.IGNORECASE,
    ))
    if not stat_software and re.search(
        r"\bstatistic|\banalys|\btest\b|\banova|\bregression", methods, re.IGNORECASE
    ):
        score -= 1
        findings.append(finding(
            "Statistical software", MAJOR,
            "Statistical analysis mentioned but software/version not specified",
            "",
            "State the exact software and version used for all statistical analyses, "
            "e.g. 'R version 4.3.1 (R Core Team, 2023)' or 'GraphPad Prism 10 (GraphPad, San Diego)'.",
        ))

    # ── 4. Cell line / reagent provenance ────────────────────────────────────
    has_cell = bool(re.search(
        r"\bcell\s+line|\bHEK\b|\bCHO\b|\bJurkat\b|\bRaji\b|\bHeLa\b|\bvero\b",
        text, re.IGNORECASE,
    ))
    if has_cell:
        has_source = bool(re.search(r"ATCC|DSMZ|ECACC|JCRB", methods, re.IGNORECASE))
        has_auth   = bool(re.search(r"mycoplasma|STR\s+profile|authent", methods, re.IGNORECASE))
        if not has_source:
            score -= 1
            findings.append(finding(
                "Cell line provenance", MAJOR,
                "Cell line(s) used but source repository (ATCC / DSMZ) not cited",
                "",
                "State the source (ATCC, DSMZ, JCRB) and catalog/accession number "
                "for each cell line. Editors and reviewers increasingly require this.",
            ))
        if not has_auth:
            findings.append(finding(
                "Cell authentication", MINOR,
                "Cell line authentication (mycoplasma / STR profiling) not mentioned",
                "",
                "State whether cells were tested for mycoplasma and/or authenticated "
                "by STR profiling. This is standard in Nature, Cell, and most high-impact journals.",
            ))

    # ── 5. Antibody specification ─────────────────────────────────────────────
    has_ab = bool(re.search(r"\bantibod(?:y|ies)\b|\bmAb\b", text, re.IGNORECASE))
    if has_ab:
        has_clone   = bool(re.search(r"\bclone\b|\bCat\.?\s*(?:no\.?|#)", methods, re.IGNORECASE))
        has_catalog = bool(re.search(r"\d{4,}-\d{3,}|catalog\s+(?:no|number|#)", methods, re.IGNORECASE))
        if not (has_clone or has_catalog):
            findings.append(finding(
                "Antibody specification", MAJOR,
                "Antibody/mAb used but clone name or catalog number not provided",
                "",
                "List antibody vendor, clone name, and catalog number for every antibody used. "
                "Example: 'anti-CD3 (clone OKT3; BioLegend cat. 317302)'.",
            ))

    # ── 6. Randomisation and blinding (in vivo / clinical) ───────────────────
    in_vivo = bool(re.search(
        r"\banimals?\b|\bmice\b|\brats?\b|\bmurine\b|\bin\s+vivo\b|\bclinical\s+trial\b",
        text, re.IGNORECASE,
    ))
    if in_vivo:
        has_random = bool(re.search(r"randomis|randomiz|randomly\s+assigned", methods, re.IGNORECASE))
        has_blind  = bool(re.search(r"\bblind(?:ed|ing)?\b|\bmasked?\b", methods, re.IGNORECASE))
        if not has_random:
            score -= 1
            findings.append(finding(
                "Randomisation", MAJOR,
                "In vivo / clinical study does not describe randomisation procedure",
                "",
                "State explicitly how subjects/animals were randomised to groups. "
                "Required by ARRIVE 2.0, CONSORT, and most journal policies.",
            ))
        if not has_blind:
            findings.append(finding(
                "Blinding", MINOR,
                "In vivo / clinical study does not mention blinding",
                "",
                "State whether outcome assessors were blinded to group allocation. "
                "If blinding was not possible, explain why.",
            ))

    # ── 7. Data / code availability ───────────────────────────────────────────
    data_avail = bool(re.search(
        r"data\s+availability|data\s+(?:are\s+)?(?:available|deposited|accessible)|"
        r"raw\s+data|source\s+data|supplementary\s+data|repository|zenodo|figshare|"
        r"github\.com|dryad|arrayexpress|geo\b|sra\b|sequence.*deposited",
        text, re.IGNORECASE,
    ))
    if not data_avail:
        score -= 1
        findings.append(finding(
            "Data availability", MAJOR,
            "No data availability statement or repository link detected",
            "",
            "Add a 'Data Availability' section. Deposit raw data in a public repository "
            "(Zenodo, Figshare, GEO, SRA, GitHub) and provide the accession/DOI. "
            "This is mandatory for Nature, Cell, Science, PLOS, and most BMC journals.",
        ))
    else:
        # Check for actual accession numbers
        has_accession = bool(re.search(
            r"GSE\d{4,}|PRJNA\d{4,}|E-MTAB-\d{4,}|zenodo\.org/\d|10\.\d{4,}/zenodo|"
            r"figshare\.com/\d|github\.com/\S+/\S+",
            text, re.IGNORECASE,
        ))
        if not has_accession:
            findings.append(finding(
                "Repository accession", MINOR,
                "Data availability mentioned but no repository accession number found",
                "",
                "Replace placeholder text ('data will be available upon request') with "
                "a real accession number or DOI. Reviewers increasingly reject "
                "'available upon request' statements.",
            ))

    score = max(0, min(10, score))
    critical = [f for f in findings if f["severity"] == CRITICAL]
    status   = CRITICAL if critical else (MAJOR if score < 7 else "PASS")

    return {
        "reviewer": "Reproducibility Reviewer",
        "score":    score,
        "status":   status,
        "findings": findings,
        "summary": (
            f"Score {score}/10. "
            f"{len(critical)} critical, "
            f"{len([f for f in findings if f['severity']==MAJOR])} major, "
            f"{len([f for f in findings if f['severity']==MINOR])} minor."
        ),
    }


# ══════════════════════════════════════════════════════════════════════════════
# ORCHESTRATOR
# ══════════════════════════════════════════════════════════════════════════════

def run_grammar_expert(
    text: str,
    config: dict = {},
    min_confidence: str = "MEDIUM",
) -> dict:
    """
    Grammar Expert (role 7): LanguageTool-based grammar & punctuation check.

    AI judgment layer: 4-stage filter (category whitelist → rule-ID blacklist →
    technical term skip → context-aware confidence scoring) drastically reduces
    false positives for biomedical prose.

    Output philosophy:
      Every finding is a SUGGESTION, not a hard error. Each suggestion carries
      a confidence level (HIGH / MEDIUM) and a judgment_note. The AI agent or
      author has full discretion over whether to adopt each suggestion.

    LanguageTool availability:
      Uses the free public API (api.languagetool.org). If the API is unreachable
      (network restrictions, rate limiting), returns an INFO-level notice with
      no findings rather than raising an error.
    """
    try:
        import language_tool as _lt
    except ImportError:
        return {
            "reviewer": "Grammar Expert",
            "score": None,
            "status": INFO,
            "findings": [finding(
                "Dependency", INFO,
                "language_tool.py not found in scripts directory",
                "",
                "Ensure language_tool.py is present alongside multi_expert_review.py",
            )],
            "_mode": "unavailable",
        }

    # Connectivity check (fast, < 5s)
    if not _lt.is_available(timeout=5):
        return {
            "reviewer": "Grammar Expert",
            "score": None,
            "status": INFO,
            "findings": [finding(
                "LanguageTool connectivity", INFO,
                "LanguageTool public API unreachable in current environment",
                "api.languagetool.org — no response within 5s",
                "Grammar check skipped. Run in an environment with internet access "
                "or set LT_URL to a self-hosted LanguageTool instance.",
            )],
            "_mode": "offline",
        }

    try:
        report = _lt.check_manuscript(text, min_confidence=min_confidence)
    except RuntimeError as exc:
        return {
            "reviewer": "Grammar Expert",
            "score": None,
            "status": INFO,
            "findings": [finding(
                "LanguageTool error", INFO,
                str(exc), "", "Check internet access and retry.",
            )],
            "_mode": "error",
        }

    high   = report["high_count"]
    medium = report["medium_count"]
    total  = report["total_reported"]
    raw    = report["total_raw"]

    # Score: start at 10, deduct for HIGH (−1 each, max −5) + MEDIUM (−0.5 each, max −2)
    score = round(max(0, 10 - min(high, 5) - min(medium * 0.5, 2)), 1)
    status = CRITICAL if high >= 8 else MAJOR if high >= 3 else MINOR if total > 0 else "PASS"

    # Prepend noise-reduction summary finding
    findings = report["findings"]  # already in multi_expert_review format

    return {
        "reviewer":      "Grammar Expert",
        "score":         score,
        "status":        status,
        "findings":      findings,
        "suggestions":   report["suggestions"],   # full detail for MCP consumers
        "raw_count":     raw,
        "filtered_count": report["total_filtered"],
        "reported_count": total,
        "tech_terms_identified": report["tech_terms_found"],
        "_mode": "languagetool",
    }


def run_full_review(
    project_dir: str | Path,
    reviewers: list[str] | None = None,
    use_llm: bool = False,
    grammar_confidence: str = "MEDIUM",
) -> dict:
    """
    Run multi-expert review on a manuscript project.

    Reviewer roster (7 roles):
      statistician          — statistical methods, effect sizes, corrections
      domain                — overclaiming, causal language, logic flow
      editor                — journal fit, word counts, declarations
      ai_diagnostician      — AI phrase markers, self-talk, unanchored claims
      citation_auditor      — citation density, hallucination gaps, topical cites
      reproducibility       — methods completeness, data deposition, reagent provenance
      grammar               — LanguageTool grammar/punctuation (4-layer filter + AI judgment)

    Args:
        project_dir:        Path to manuscript project directory.
        reviewers:          Subset of the 7 roles. Default: all seven.
        use_llm:            If True, ai_diagnostician, citation_auditor, and
                            reproducibility call Gemini-2.5-flash with rule fallback.
        grammar_confidence: Minimum confidence threshold for Grammar Expert
                            suggestions ("HIGH" | "MEDIUM" | "LOW"). Default "MEDIUM".

    Returns:
        Full review result dict with per-reviewer findings and priority action list.
    """
    proj = Path(project_dir).resolve()
    if reviewers is None:
        reviewers = ["statistician", "domain", "editor",
                     "ai_diagnostician", "citation_auditor", "reproducibility",
                     "grammar"]

    # Load config
    config: dict = {}
    config_path = proj / "project_config.json"
    if config_path.exists():
        config = json.loads(config_path.read_text(encoding="utf-8"))

    # Load journal data
    journal_name = config.get("target_journal", "")
    journal_data = load_journal(journal_name) if journal_name else None

    # Find manuscript
    ms_rel  = config.get("outputs", {}).get("manuscript_md", "01_manuscript/manuscript.md")
    ms_path = proj / ms_rel
    if not ms_path.exists():
        ms_path = next(proj.rglob("*.md"), None)
    if not ms_path or not ms_path.exists():
        return {"error": "Manuscript file not found", "project_dir": str(proj)}

    text = ms_path.read_text(encoding="utf-8")

    # Run selected reviewers
    results: dict[str, dict] = {}
    if "statistician" in reviewers:
        results["statistician"] = run_statistician(text, config)
    if "domain" in reviewers:
        results["domain"] = run_domain_expert(text, config)
    if "editor" in reviewers:
        results["editor"] = run_editor(text, config, journal_data)
    if "ai_diagnostician" in reviewers:
        results["ai_diagnostician"] = run_ai_diagnostician(text, config, use_llm=use_llm)
    if "citation_auditor" in reviewers:
        results["citation_auditor"] = run_citation_auditor(text, config, use_llm=use_llm)
    if "reproducibility" in reviewers:
        results["reproducibility"] = run_reproducibility_reviewer(text, config, use_llm=use_llm)
    if "grammar" in reviewers:
        results["grammar"] = run_grammar_expert(text, config,
                                                min_confidence=grammar_confidence)

    # Build unified priority action list
    all_findings: list[dict] = []
    for role, r in results.items():
        for f in r.get("findings", []):
            if f["severity"] != INFO:
                all_findings.append({**f, "reviewer": role})

    priority_order = {CRITICAL: 0, MAJOR: 1, MINOR: 2}
    all_findings.sort(key=lambda x: priority_order.get(x["severity"], 9))

    # Overall status
    any_critical = any(r.get("status") == CRITICAL for r in results.values())
    any_major    = any(r.get("status") == MAJOR for r in results.values())
    overall      = CRITICAL if any_critical else (MAJOR if any_major else "PASS")
    avg_score    = round(sum(r.get("score", 0) for r in results.values()) / max(1, len(results)), 1)

    review_result = {
        "overall_status":  overall,
        "overall_score":   avg_score,
        "journal":         journal_name,
        "article_type":    config.get("article_type", "Article"),
        "manuscript":      str(ms_path),
        "reviewers":       results,
        "priority_actions": all_findings,
        "reviewed_at":     datetime.now(timezone.utc).isoformat(),
    }

    # Write QA report
    _write_qa_report(review_result, proj)

    return review_result


def _write_qa_report(result: dict, proj: Path):
    """Write multi_expert_review_QA.md to 03_QA/."""
    qa_dir = proj / "03_QA"
    qa_dir.mkdir(exist_ok=True)

    sev_icon = {CRITICAL: "❌", MAJOR: "⚠️", MINOR: "○", INFO: "ℹ️"}
    status_line = {CRITICAL: "Status: FAIL", MAJOR: "Status: WARN", "PASS": "Status: PASS"}

    lines = [
        f"# Multi-Expert Review QA",
        f"",
        f"{status_line.get(result['overall_status'], 'Status: UNKNOWN')}",
        f"Overall score: {result['overall_score']}/10",
        f"Journal: {result.get('journal','(not specified)')}",
        f"Article type: {result.get('article_type','')}",
        f"Reviewed: {result['reviewed_at'][:19].replace('T',' ')} UTC",
        f"",
        f"---",
        f"",
        f"## Priority Action List",
        f"",
    ]

    critical_actions = [f for f in result["priority_actions"] if f["severity"] == CRITICAL]
    major_actions    = [f for f in result["priority_actions"] if f["severity"] == MAJOR]
    minor_actions    = [f for f in result["priority_actions"] if f["severity"] == MINOR]

    if critical_actions:
        lines.append("### Critical (must fix before submission)")
        lines.append("")
        for i, f in enumerate(critical_actions, 1):
            lines.append(f"{i}. **[{f['reviewer'].upper()}]** {f['issue']}")
            if f.get("recommendation"):
                lines.append(f"   → {f['recommendation']}")
            lines.append("")

    if major_actions:
        lines.append("### Major (strongly recommended)")
        lines.append("")
        for i, f in enumerate(major_actions, 1):
            lines.append(f"{i}. **[{f['reviewer'].upper()}]** {f['issue']}")
            if f.get("recommendation"):
                lines.append(f"   → {f['recommendation']}")
            lines.append("")

    if minor_actions:
        lines.append("### Minor (optional improvements)")
        lines.append("")
        for i, f in enumerate(minor_actions, 1):
            lines.append(f"{i}. **[{f['reviewer'].upper()}]** {f['issue']}")
            lines.append("")

    # Per-reviewer sections
    lines += ["---", "", "## Reviewer Reports", ""]

    for role, r in result.get("reviewers", {}).items():
        reviewer_name = r.get("reviewer", role.title())
        role_status   = r.get("status", "")
        role_score    = r.get("score", 0)
        lines += [
            f"### {reviewer_name}",
            f"Score: {role_score}/10 | {role_status}",
            f"{r.get('summary','')}",
            "",
        ]
        for f in r.get("findings", []):
            if f["severity"] == INFO:
                continue
            icon = sev_icon.get(f["severity"], "·")
            lines.append(f"- {icon} **{f['category']}**: {f['issue']}")
            if f.get("evidence"):
                lines.append(f"  > {f['evidence']}")
            if f.get("recommendation"):
                lines.append(f"  → {f['recommendation']}")
        lines.append("")

    lines += [
        "---",
        "",
        "## Red Lines (enforced)",
        "",
        "- Source-bounded: all findings based only on manuscript content",
        "- No invented experiments or data suggested",
        "- No editorial decision claims ('will be accepted/rejected')",
        "- No fabricated reviewer identities",
        "",
        "*Generated by TheraSIK Multi-Expert Review — heuristic analysis only.*",
        "*Human expert review is always required before submission.*",
    ]

    out_path = qa_dir / "multi_expert_review_QA.md"
    out_path.write_text("\n".join(lines), encoding="utf-8")
    return out_path


# ── CLI ───────────────────────────────────────────────────────────────────────

def main():
    parser = argparse.ArgumentParser(description="TheraSIK Multi-Expert Manuscript Review")
    parser.add_argument("project_dir", help="Path to manuscript project directory")
    parser.add_argument(
        "--reviewer",
        choices=["statistician", "domain", "editor",
                 "ai_diagnostician", "citation_auditor", "reproducibility",
                 "grammar"],
        help="Run only one reviewer (default: all seven)"
    )
    parser.add_argument(
        "--grammar-confidence",
        choices=["HIGH", "MEDIUM", "LOW"],
        default="MEDIUM",
        help="Minimum confidence for Grammar Expert suggestions (default: MEDIUM)",
    )
    parser.add_argument("--json", action="store_true", help="Output raw JSON")
    parser.add_argument(
        "--use-llm", action="store_true",
        help="Enable Gemini-1.5-flash for ai_diagnostician, citation_auditor, reproducibility "
             "(requires GEMINI_API_KEY; falls back to rules automatically)"
    )
    args = parser.parse_args()

    reviewers = [args.reviewer] if args.reviewer else None
    result    = run_full_review(
        args.project_dir,
        reviewers=reviewers,
        use_llm=getattr(args, "use_llm", False),
        grammar_confidence=getattr(args, "grammar_confidence", "MEDIUM"),
    )

    if "error" in result:
        print(f"ERROR: {result['error']}", file=sys.stderr)
        sys.exit(1)

    if args.json:
        print(json.dumps(result, indent=2, ensure_ascii=False))
        return

    # Human-readable summary
    sev_icon = {CRITICAL: "❌", MAJOR: "⚠️", MINOR: "○"}
    print(f"\nOverall: {result['overall_status']}  (score {result['overall_score']}/10)")
    print(f"Journal: {result.get('journal','—')}  |  Type: {result.get('article_type','—')}")
    print()

    for role, r in result.get("reviewers", {}).items():
        mode_tag = f" [gemini]" if r.get("_mode") == "gemini" else " [rules]"
        print(f"  {r['reviewer']:<22} score={r['score']}/10  {r['status']}{mode_tag}")
        for f in r.get("findings", []):
            if f["severity"] != INFO:
                icon = sev_icon.get(f["severity"], "·")
                print(f"    {icon} [{f['category']}] {f['issue']}")
        print()

    qa_path = Path(args.project_dir) / "03_QA" / "multi_expert_review_QA.md"
    print(f"Report: {qa_path}")


if __name__ == "__main__":
    main()
