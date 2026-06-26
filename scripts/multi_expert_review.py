"""
multi_expert_review.py
======================
TheraSIK Multi-Expert Manuscript Review Simulation

Three independent reviewer roles applied to a manuscript:

  Statistician  — statistical methods, sample sizes, p-values, effect sizes,
                  multiple comparison corrections, reproducibility
  Domain Expert — claims vs evidence, novelty framing, logic flow, hedging,
                  overclaiming, limitation disclosure
  Editor        — journal fit, section structure, word/figure/reference counts,
                  mandatory declarations, title and abstract quality

Design principles:
  • Rule-based heuristic — deterministic, no LLM API calls required
  • Source-bounded — only flags what is present (or absent) in the manuscript
  • No editorial decision claims — never says "will be rejected/accepted"
  • Red lines enforced — no invented experiments, no fabricated data suggestions
  • Severity tiers: CRITICAL (must fix) / MAJOR (strongly recommended) / MINOR

Output: {project_dir}/03_QA/multi_expert_review_QA.md

Usage (CLI):
  python scripts/multi_expert_review.py <project_dir>
  python scripts/multi_expert_review.py <project_dir> --reviewer statistician
  python scripts/multi_expert_review.py <project_dir> --reviewer domain
  python scripts/multi_expert_review.py <project_dir> --reviewer editor

Programmatic:
  from multi_expert_review import run_full_review, run_statistician, run_domain_expert, run_editor
"""

from __future__ import annotations

import argparse
import json
import os
import re
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional

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
# ORCHESTRATOR
# ══════════════════════════════════════════════════════════════════════════════

def run_full_review(
    project_dir: str | Path,
    reviewers: list[str] | None = None,
) -> dict:
    """
    Run multi-expert review on a manuscript project.

    Args:
        project_dir: Path to manuscript project directory.
        reviewers:   Subset of ['statistician', 'domain', 'editor']. Default: all three.

    Returns:
        Full review result dict with per-reviewer findings and priority action list.
    """
    proj = Path(project_dir).resolve()
    if reviewers is None:
        reviewers = ["statistician", "domain", "editor"]

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
        "--reviewer", choices=["statistician", "domain", "editor"],
        help="Run only one reviewer (default: all three)"
    )
    parser.add_argument("--json", action="store_true", help="Output raw JSON")
    args = parser.parse_args()

    reviewers = [args.reviewer] if args.reviewer else None
    result    = run_full_review(args.project_dir, reviewers=reviewers)

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
        print(f"  {r['reviewer']:<20} score={r['score']}/10  {r['status']}")
        for f in r.get("findings", []):
            if f["severity"] != INFO:
                icon = sev_icon.get(f["severity"], "·")
                print(f"    {icon} [{f['category']}] {f['issue']}")
        print()

    qa_path = Path(args.project_dir) / "03_QA" / "multi_expert_review_QA.md"
    print(f"Report: {qa_path}")


if __name__ == "__main__":
    main()
