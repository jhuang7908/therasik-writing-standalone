"""
Reporting Guidelines Checker for writing_memory service.

Covers all major biomedical reporting standards mandated by journals and
meta-journals (EQUATOR Network). Each guideline is implemented as a
rule-based checklist that operates on manuscript text — no LLM required.

Supported guidelines:
  CONSORT 2010  — Randomised Controlled Trials (25 items)
  PRISMA 2020   — Systematic Reviews & Meta-Analyses (27 items)
  STROBE 2007   — Observational Studies (22 items)
  CARE 2016     — Case Reports (13 items)
  ARRIVE 2.0    — Animal Research (21 items)
  TRIPOD 2015   — Prediction Model Studies (22 items)
  CHEERS 2022   — Economic Evaluations (28 items)
  SPIRIT 2013   — Clinical Trial Protocols (33 items)
  SRQR          — Qualitative Research (21 items)

Public API:
  article_type_to_guideline(article_type) -> str | None
  check_guidelines(text, guideline_key, sections=None) -> GuidelineReport
  list_guidelines() -> list[dict]
  get_biomedical_article_types() -> list[dict]
"""
from __future__ import annotations

import re
from dataclasses import dataclass, field
from typing import Any


# ─── Guideline item ───────────────────────────────────────────────────────────

@dataclass
class GuidelineItem:
    item_id: str
    section: str            # where it typically belongs
    description: str        # what it requires
    keywords: list[str]     # regex patterns to look for (ANY match = present)
    required: bool = True   # False = recommended but not mandatory

    def check(self, text: str) -> bool:
        if not self.keywords:
            return False
        for kw in self.keywords:
            try:
                if re.search(kw, text, re.IGNORECASE):
                    return True
            except re.error:
                if kw.lower() in text.lower():
                    return True
        return False


# ─── Guideline definitions ────────────────────────────────────────────────────

_GUIDELINES: dict[str, list[GuidelineItem]] = {

    # ── CONSORT 2010 (RCT) ──────────────────────────────────────────────────
    "consort": [
        GuidelineItem("1a", "Title/Abstract", "Trial design identified in title or abstract",
            [r"\bRCT\b", r"randomis", r"randomiz", r"randomised controlled", r"randomized controlled"]),
        GuidelineItem("2a", "Introduction", "Scientific background and rationale",
            [r"background", r"rationale", r"prior (study|trial|evidence)", r"previous (study|trial)"]),
        GuidelineItem("2b", "Introduction", "Specific objectives or hypotheses",
            [r"objective", r"hypothesis", r"aim", r"purpose", r"we hypothes"]),
        GuidelineItem("3a", "Methods", "Description of trial design (allocation ratio)",
            [r"parallel.group", r"crossover", r"factorial", r"allocation ratio", r"1:1", r"2:1"]),
        GuidelineItem("3b", "Methods", "Important changes to methods after commencement",
            [r"amendment", r"protocol change", r"modified after", r"deviation"], required=False),
        GuidelineItem("4a", "Methods", "Eligibility criteria for participants",
            [r"inclusion criter", r"exclusion criter", r"eligible", r"eligibility"]),
        GuidelineItem("5",  "Methods", "Interventions in sufficient detail to allow replication",
            [r"intervention", r"treatment", r"dose", r"administration", r"regimen"]),
        GuidelineItem("6a", "Methods", "Completely defined pre-specified primary and secondary outcomes",
            [r"primary (endpoint|outcome|measure)", r"secondary (endpoint|outcome|measure)"]),
        GuidelineItem("7a", "Methods", "How sample size was determined",
            [r"sample size", r"power calculation", r"statistical power", r"power\s+\d"]),
        GuidelineItem("8a", "Methods", "Method of generating random allocation sequence",
            [r"random(is|iz)ation sequence", r"random number", r"computer.generated", r"block randomis"]),
        GuidelineItem("9",  "Methods", "Mechanism used to implement the random allocation sequence (concealment)",
            [r"allocation concealment", r"sealed envelope", r"central randomi", r"sequentially numbered"]),
        GuidelineItem("10", "Methods", "Who generated the allocation sequence and who enrolled participants (blinding)",
            [r"blind(ed|ing)", r"double.blind", r"single.blind", r"open.label", r"masking"]),
        GuidelineItem("11a","Methods", "Statistical methods used to compare groups",
            [r"statistical method", r"t.test", r"chi.square", r"ANCOVA", r"mixed model", r"regression"]),
        GuidelineItem("13a","Results", "Flow of participants (CONSORT diagram or equivalent)",
            [r"consort", r"flow diagram", r"screened", r"enrolled", r"randomis", r"completed the study"]),
        GuidelineItem("14a","Results", "Dates defining periods of recruitment and follow-up",
            [r"recruit", r"enrol", r"follow.up period", r"study period", r"\d{4}[\s–-]+\d{4}"]),
        GuidelineItem("15", "Results", "Baseline demographic and clinical characteristics",
            [r"baseline characteristic", r"Table \d", r"age", r"sex|gender", r"BMI|body mass"]),
        GuidelineItem("16", "Results", "Number of participants analysed in each group",
            [r"intent.to.treat", r"per.protocol", r"n\s*=\s*\d", r"analysed"]),
        GuidelineItem("17a","Results", "For each primary and secondary outcome, results for each group",
            [r"primary (outcome|endpoint)", r"between.group", r"difference", r"95%\s*(CI|confidence)"]),
        GuidelineItem("18", "Results", "All important harms or unintended effects",
            [r"adverse (event|effect|reaction)", r"harm", r"side effect", r"AE\b", r"SAE\b"]),
        GuidelineItem("19", "Discussion", "Trial limitations",
            [r"limitation", r"weakness", r"caveat", r"constrain"]),
        GuidelineItem("20", "Discussion", "Generalisability (external validity, applicability)",
            [r"generali", r"external validity", r"applicability", r"extrapolat"]),
        GuidelineItem("21", "Discussion", "Interpretation consistent with results",
            [r"in conclusion", r"these findings", r"suggest that", r"indicate that"]),
        GuidelineItem("22", "Other", "Registration number and name of trial registry",
            [r"ClinicalTrials\.gov", r"ISRCTN", r"NCT\d{8}", r"registered", r"trial registration"]),
        GuidelineItem("23", "Other", "Where the full trial protocol can be accessed",
            [r"protocol", r"supplement", r"appendix", r"online"], required=False),
        GuidelineItem("24", "Other", "Funding sources",
            [r"fund(ed|ing)", r"grant", r"support(ed)? by", r"sponsor"]),
    ],

    # ── PRISMA 2020 (Systematic Review / Meta-Analysis) ──────────────────────
    "prisma": [
        GuidelineItem("1",  "Title",       "Identify the report as a systematic review",
            [r"systematic review", r"meta.analysis", r"scoping review"]),
        GuidelineItem("2",  "Abstract",    "Structured abstract (Background/Methods/Results/Conclusions)",
            [r"background", r"method", r"result", r"conclusion"]),
        GuidelineItem("3",  "Introduction","Describe the rationale for the review",
            [r"rationale", r"background", r"importance of"]),
        GuidelineItem("4",  "Introduction","Provide an explicit statement of objectives",
            [r"objective", r"aim", r"research question", r"PICO", r"PICOS"]),
        GuidelineItem("5",  "Methods",     "Protocol and registration",
            [r"PROSPERO", r"registered", r"protocol", r"CRD\d+"]),
        GuidelineItem("6",  "Methods",     "Eligibility criteria (PICO)",
            [r"inclusion criter", r"exclusion criter", r"eligible", r"PICO"]),
        GuidelineItem("7",  "Methods",     "Information sources (databases searched)",
            [r"PubMed", r"MEDLINE", r"Embase", r"Cochrane", r"Web of Science", r"database"]),
        GuidelineItem("8",  "Methods",     "Search strategy for at least one database",
            [r"search strateg", r"search term", r"MeSH", r"keyword"]),
        GuidelineItem("9",  "Methods",     "Selection process",
            [r"screen", r"title and abstract", r"full.text", r"two (reviewer|author|independent)"]),
        GuidelineItem("10", "Methods",     "Data collection process",
            [r"data extract", r"data collection", r"pilot.test", r"two reviewer"]),
        GuidelineItem("11", "Methods",     "List and define outcomes and other variables",
            [r"outcome", r"variable", r"endpoint"]),
        GuidelineItem("12", "Methods",     "Risk of bias assessment",
            [r"risk of bias", r"quality assessment", r"Cochrane risk", r"Newcastle.Ottawa", r"GRADE", r"ROB"]),
        GuidelineItem("13", "Methods",     "Effect measures",
            [r"odds ratio", r"risk ratio", r"relative risk", r"mean difference", r"hazard ratio",
             r"OR\b", r"RR\b", r"HR\b", r"SMD\b"]),
        GuidelineItem("14", "Methods",     "Synthesis methods (meta-analysis)",
            [r"meta.analys", r"pooled", r"random.effects", r"fixed.effects", r"heterogeneity", r"I.squared"]),
        GuidelineItem("15", "Methods",     "Heterogeneity assessment",
            [r"I.2", r"I\u00b2", r"Q.test", r"heterogeneity", r"Cochran.Q"]),
        GuidelineItem("16", "Methods",     "Publication bias",
            [r"publication bias", r"funnel plot", r"Egger", r"Begg"]),
        GuidelineItem("17", "Results",     "Study selection (PRISMA flow diagram)",
            [r"PRISMA", r"flow diagram", r"screened", r"included", r"excluded"]),
        GuidelineItem("18", "Results",     "Characteristics of included studies",
            [r"characteristic", r"Table \d", r"included stud"]),
        GuidelineItem("19", "Results",     "Risk of bias in studies",
            [r"risk of bias", r"quality of evidence", r"study quality"]),
        GuidelineItem("20", "Results",     "Results of individual studies",
            [r"forest plot", r"Figure \d", r"individual stud"]),
        GuidelineItem("21", "Results",     "Results of syntheses",
            [r"pooled (estimate|result|OR|RR|HR)", r"overall effect", r"combined effect"]),
        GuidelineItem("22", "Results",     "Publication bias results",
            [r"funnel plot", r"Egger test", r"publication bias"], required=False),
        GuidelineItem("24", "Discussion",  "Limitations (including risk of bias, heterogeneity)",
            [r"limitation", r"heterogeneity", r"risk of bias"]),
        GuidelineItem("25", "Discussion",  "Conclusions",
            [r"conclusion", r"in summary", r"in conclusion"]),
        GuidelineItem("26", "Other",       "Registration",
            [r"PROSPERO", r"registered", r"CRD\d+"]),
        GuidelineItem("27", "Other",       "Funding",
            [r"fund", r"grant", r"support"]),
    ],

    # ── STROBE 2007 (Observational: Cohort, Case-Control, Cross-Sectional) ──
    "strobe": [
        GuidelineItem("1a", "Title",       "Indicate the study's design in title or abstract",
            [r"cohort", r"case.control", r"cross.sectional", r"prospective", r"retrospective"]),
        GuidelineItem("2",  "Introduction","Scientific background and rationale",
            [r"background", r"rationale", r"previous stud"]),
        GuidelineItem("3",  "Introduction","Objectives",
            [r"objective", r"aim", r"hypothesis"]),
        GuidelineItem("4",  "Methods",     "Study design",
            [r"cohort stud", r"case.control", r"cross.sectional", r"prospective", r"retrospective"]),
        GuidelineItem("5",  "Methods",     "Setting, locations, and relevant dates",
            [r"setting", r"location", r"hospital", r"clinic", r"study period", r"\d{4}[\s–-]+\d{4}"]),
        GuidelineItem("6",  "Methods",     "Eligibility criteria and sources of selection",
            [r"inclusion criter", r"exclusion criter", r"eligible"]),
        GuidelineItem("7",  "Methods",     "Variables (exposures, outcomes, confounders)",
            [r"exposure", r"outcome", r"confounder", r"covariate", r"variable"]),
        GuidelineItem("8",  "Methods",     "Measurement of variables",
            [r"measur", r"assess", r"diagnos", r"defin"]),
        GuidelineItem("9",  "Methods",     "Bias addressed",
            [r"bias", r"confound", r"selection bias", r"information bias"], required=False),
        GuidelineItem("10", "Methods",     "Study size (power/sample size)",
            [r"sample size", r"power", r"required sample"]),
        GuidelineItem("11", "Methods",     "Statistical methods",
            [r"logistic regression", r"Cox regression", r"hazard ratio", r"odds ratio",
             r"statistical method", r"SPSS", r"R software", r"SAS\b", r"Stata\b"]),
        GuidelineItem("13a","Results",     "Participant flow (numbers at each stage)",
            [r"screened", r"eligible", r"enrolled", r"lost to follow.up", r"Figure \d"]),
        GuidelineItem("14a","Results",     "Dates of recruitment and follow-up",
            [r"recruit", r"follow.up", r"\d{4}"]),
        GuidelineItem("15", "Results",     "Baseline characteristics",
            [r"baseline", r"Table \d", r"age", r"sex|gender"]),
        GuidelineItem("16", "Results",     "Number of outcome events",
            [r"n\s*=\s*\d", r"event", r"case", r"death", r"incidence"]),
        GuidelineItem("17a","Results",     "Unadjusted and adjusted estimates",
            [r"adjust", r"unadjust", r"crude", r"OR\b", r"RR\b", r"HR\b", r"95%\s*CI"]),
        GuidelineItem("20", "Discussion",  "Key results and interpretation",
            [r"key finding", r"our finding", r"result suggest"]),
        GuidelineItem("21", "Discussion",  "Limitations (bias, imprecision)",
            [r"limitation", r"bias", r"weakness"]),
        GuidelineItem("22", "Discussion",  "Generalisability",
            [r"generali", r"external validity"]),
        GuidelineItem("22b","Other",       "Funding",
            [r"fund", r"grant", r"support"]),
    ],

    # ── CARE 2016 (Case Report) ──────────────────────────────────────────────
    "care": [
        GuidelineItem("1",  "Title",       "Case report in title",
            [r"case report", r"case study", r"case presentation"]),
        GuidelineItem("2",  "Abstract",    "Abstract: introduction, case, conclusion",
            [r"abstract", r"introduction|background", r"case|patient", r"conclusion"]),
        GuidelineItem("3",  "Introduction","Why this case is unique/important",
            [r"unique", r"novel", r"rare", r"unusual", r"first report", r"previously unreported"]),
        GuidelineItem("4",  "Patient",     "Patient demographics (de-identified)",
            [r"patient", r"year.old", r"male|female|man|woman", r"presented"]),
        GuidelineItem("5a", "Patient",     "Chief complaint",
            [r"chief complaint", r"present(ed|ing) with", r"complaint", r"symptom"]),
        GuidelineItem("5b", "Patient",     "Medical, family, and psychosocial history",
            [r"history", r"past medical", r"family history", r"previous"]),
        GuidelineItem("5c", "Patient",     "Physical examination",
            [r"physical examination", r"vital sign", r"on examination", r"examination reveal"]),
        GuidelineItem("5d", "Patient",     "Diagnostic testing",
            [r"laboratory", r"imaging", r"CT\b", r"MRI\b", r"biopsy", r"patholog", r"result"]),
        GuidelineItem("5e", "Patient",     "Differential diagnosis",
            [r"differential diagnosis", r"differential", r"rule out"]),
        GuidelineItem("5f", "Patient",     "Treatment",
            [r"treatment", r"management", r"therap", r"prescribed", r"administered"]),
        GuidelineItem("5g", "Patient",     "Follow-up and outcomes",
            [r"follow.up", r"outcome", r"discharg", r"remission", r"recovery"]),
        GuidelineItem("6",  "Discussion",  "Discussion of conclusions including limitations",
            [r"discussion", r"limitation", r"we report", r"to our knowledge"]),
        GuidelineItem("7",  "Patient",     "Patient perspective (if appropriate)",
            [r"patient consent", r"informed consent", r"patient perspective"], required=False),
    ],

    # ── ARRIVE 2.0 (Animal Research) ────────────────────────────────────────
    "arrive": [
        GuidelineItem("1",  "Abstract",    "Structured summary",
            [r"objective", r"method", r"result", r"conclusion"]),
        GuidelineItem("2",  "Introduction","Background and objectives",
            [r"background", r"rationale", r"objective", r"aim"]),
        GuidelineItem("3",  "Methods",     "Ethical statement (IACUC/ethics approval)",
            [r"IACUC", r"Institutional Animal Care", r"ethics committee", r"animal use protocol",
             r"approved by", r"ethical approval"]),
        GuidelineItem("4",  "Methods",     "Study design",
            [r"study design", r"experimental design", r"randomis", r"control group"]),
        GuidelineItem("5",  "Methods",     "Inclusion/exclusion criteria",
            [r"inclusion criter", r"exclusion criter", r"eligible"]),
        GuidelineItem("6",  "Methods",     "Animal species, strain, sex, age",
            [r"mouse|mice|rat|rabbit|monkey|pig|dog", r"strain", r"male|female", r"age|week|month"]),
        GuidelineItem("7",  "Methods",     "Housing and husbandry",
            [r"hous", r"husbandry", r"animal facil", r"barrier", r"SPF"]),
        GuidelineItem("8",  "Methods",     "Sample size and power",
            [r"sample size", r"power", r"n\s*=\s*\d", r"per group"]),
        GuidelineItem("9",  "Methods",     "Allocation to groups",
            [r"random", r"allocat", r"blind"]),
        GuidelineItem("10", "Methods",     "Experimental procedures",
            [r"procedure", r"protocol", r"method", r"inject", r"administr"]),
        GuidelineItem("11", "Methods",     "Statistical analysis",
            [r"statistical", r"ANOVA", r"t.test", r"Mann.Whitney", r"Prism\b", r"SPSS"]),
        GuidelineItem("12", "Results",     "Baseline data",
            [r"baseline", r"before treatment", r"prior to"]),
        GuidelineItem("13", "Results",     "Numbers analysed",
            [r"n\s*=\s*\d", r"animals", r"mice", r"per group"]),
        GuidelineItem("14", "Results",     "Outcomes and estimation",
            [r"mean", r"SEM|SD|standard deviation", r"95%\s*CI", r"p\s*[<>=]\s*0\.\d"]),
        GuidelineItem("15", "Discussion",  "Summary and interpretation",
            [r"in summary", r"these results", r"suggest", r"indicate"]),
        GuidelineItem("16", "Discussion",  "Generalisability",
            [r"generali", r"translat", r"clinical relevance"]),
        GuidelineItem("17", "Discussion",  "Limitations",
            [r"limitation", r"weakness", r"caveat"]),
        GuidelineItem("21", "Other",       "Funding",
            [r"fund", r"grant", r"support"]),
    ],

    # ── TRIPOD 2015 (Prediction Model) ───────────────────────────────────────
    "tripod": [
        GuidelineItem("1",  "Title",       "Identify as prediction model study",
            [r"predict(ion|ive) model", r"risk score", r"nomogram", r"diagnostic model",
             r"prognostic model"]),
        GuidelineItem("2",  "Abstract",    "Structured abstract",
            [r"objective", r"method", r"result", r"conclusion"]),
        GuidelineItem("3a", "Introduction","Medical context and rationale",
            [r"background", r"rationale"]),
        GuidelineItem("4a", "Methods",     "Design (development vs. validation)",
            [r"develop", r"validat", r"internal validation", r"external validation"]),
        GuidelineItem("5a", "Methods",     "Source of data",
            [r"data source", r"cohort", r"registry", r"database", r"electronic health record"]),
        GuidelineItem("7",  "Methods",     "Outcome(s) defined",
            [r"outcome", r"endpoint", r"event", r"diagnos"]),
        GuidelineItem("9",  "Methods",     "Candidate predictors",
            [r"predictor", r"variable", r"feature", r"covariate"]),
        GuidelineItem("10", "Methods",     "Sample size",
            [r"sample size", r"events per variable", r"EPV"]),
        GuidelineItem("12", "Methods",     "Statistical analysis methods",
            [r"logistic regression", r"Cox", r"random forest", r"neural network", r"LASSO"]),
        GuidelineItem("13", "Methods",     "Model performance measures (C-statistic, calibration)",
            [r"C.statistic", r"AUC", r"calibration", r"Hosmer.Lemeshow", r"discrimination",
             r"Brier score"]),
        GuidelineItem("16", "Results",     "Model performance",
            [r"AUC", r"C.statistic", r"sensitivity", r"specificity", r"calibration"]),
        GuidelineItem("20", "Discussion",  "Limitations",
            [r"limitation"]),
        GuidelineItem("22", "Other",       "Funding",
            [r"fund", r"grant"]),
    ],
}


# ─── Article type → guideline mapping ────────────────────────────────────────

_TYPE_TO_GUIDELINE: dict[str, str] = {
    "randomized_controlled_trial": "consort",
    "rct":                         "consort",
    "clinical_trial":              "consort",
    "systematic_review":           "prisma",
    "meta_analysis":               "prisma",
    "scoping_review":              "prisma",
    "cohort_study":                "strobe",
    "case_control_study":          "strobe",
    "cross_sectional_study":       "strobe",
    "observational_study":         "strobe",
    "case_report":                 "care",
    "case_series":                 "care",
    "animal_study":                "arrive",
    "preclinical_study":           "arrive",
    "prediction_model":            "tripod",
    "diagnostic_model":            "tripod",
    "prognostic_model":            "tripod",
}


# ─── Full biomedical article type registry ────────────────────────────────────

_BIOMEDICAL_ARTICLE_TYPES: list[dict[str, Any]] = [
    # ── Basic/translational research ──────────────────────────────────────────
    {"key": "original_research",    "label": "Original Research",          "guideline": None,     "word_range": [3000, 7000], "abstract": "unstructured"},
    {"key": "brief_communication",  "label": "Brief Communication / Short Report", "guideline": None, "word_range": [1500, 3000], "abstract": "unstructured"},
    {"key": "technical_note",       "label": "Technical Note",             "guideline": None,     "word_range": [1500, 2500], "abstract": "unstructured"},
    {"key": "methods_paper",        "label": "Methods / Protocol Paper",   "guideline": None,     "word_range": [3000, 8000], "abstract": "unstructured"},
    {"key": "animal_study",         "label": "Animal Research",            "guideline": "arrive", "word_range": [3000, 6000], "abstract": "structured"},
    {"key": "in_vitro_study",       "label": "In Vitro Study",             "guideline": None,     "word_range": [2500, 5000], "abstract": "unstructured"},
    # ── Clinical research ──────────────────────────────────────────────────────
    {"key": "randomized_controlled_trial", "label": "Randomised Controlled Trial (RCT)", "guideline": "consort", "word_range": [3000, 6000], "abstract": "structured"},
    {"key": "clinical_trial",       "label": "Clinical Trial (non-RCT)",   "guideline": "consort","word_range": [3000, 6000], "abstract": "structured"},
    {"key": "cohort_study",         "label": "Cohort Study",               "guideline": "strobe", "word_range": [3000, 6000], "abstract": "structured"},
    {"key": "case_control_study",   "label": "Case-Control Study",         "guideline": "strobe", "word_range": [2500, 5000], "abstract": "structured"},
    {"key": "cross_sectional_study","label": "Cross-Sectional Study",      "guideline": "strobe", "word_range": [2500, 5000], "abstract": "structured"},
    {"key": "diagnostic_accuracy",  "label": "Diagnostic Accuracy Study",  "guideline": None,     "word_range": [2500, 5000], "abstract": "structured"},
    {"key": "prediction_model",     "label": "Prediction / Prognostic Model", "guideline": "tripod", "word_range": [3000, 6000], "abstract": "structured"},
    # ── Synthesis research ────────────────────────────────────────────────────
    {"key": "systematic_review",    "label": "Systematic Review",          "guideline": "prisma", "word_range": [4000, 10000], "abstract": "structured"},
    {"key": "meta_analysis",        "label": "Meta-Analysis",              "guideline": "prisma", "word_range": [4000, 8000],  "abstract": "structured"},
    {"key": "scoping_review",       "label": "Scoping Review",             "guideline": "prisma", "word_range": [4000, 9000],  "abstract": "structured"},
    {"key": "narrative_review",     "label": "Narrative / Literature Review", "guideline": None, "word_range": [4000, 10000], "abstract": "unstructured"},
    # ── Case-based ────────────────────────────────────────────────────────────
    {"key": "case_report",          "label": "Case Report",                "guideline": "care",   "word_range": [1000, 3000],  "abstract": "unstructured"},
    {"key": "case_series",          "label": "Case Series",                "guideline": "care",   "word_range": [1500, 4000],  "abstract": "unstructured"},
    # ── Commentary / Opinion ─────────────────────────────────────────────────
    {"key": "commentary",           "label": "Commentary / Perspective",   "guideline": None,     "word_range": [800, 2000],   "abstract": "none"},
    {"key": "editorial",            "label": "Editorial",                  "guideline": None,     "word_range": [500, 1500],   "abstract": "none"},
    {"key": "letter",               "label": "Letter to the Editor",       "guideline": None,     "word_range": [300, 800],    "abstract": "none"},
    # ── Specialty ────────────────────────────────────────────────────────────
    {"key": "protocol",             "label": "Study Protocol",             "guideline": None,     "word_range": [3000, 8000],  "abstract": "structured"},
    {"key": "economic_evaluation",  "label": "Economic Evaluation",        "guideline": "cheers", "word_range": [3000, 7000],  "abstract": "structured"},
    {"key": "qualitative_study",    "label": "Qualitative Study",          "guideline": "srqr",   "word_range": [3000, 8000],  "abstract": "structured"},
]


# ─── Result dataclass ─────────────────────────────────────────────────────────

@dataclass
class GuidelineItemResult:
    item_id: str
    section: str
    description: str
    required: bool
    present: bool

    @property
    def status(self) -> str:
        if self.present:
            return "present"
        return "missing" if self.required else "recommended_missing"


@dataclass
class GuidelineReport:
    guideline_key: str
    guideline_name: str
    article_type: str
    total_items: int
    required_items: int
    present_required: int
    present_optional: int
    items: list[GuidelineItemResult] = field(default_factory=list)

    @property
    def compliance_pct(self) -> float:
        if self.required_items == 0:
            return 100.0
        return round(self.present_required / self.required_items * 100, 1)

    @property
    def status(self) -> str:
        if self.compliance_pct >= 90:
            return "PASS"
        if self.compliance_pct >= 70:
            return "WARN"
        return "FAIL"

    def as_dict(self) -> dict[str, Any]:
        missing_required = [i for i in self.items if not i.present and i.required]
        missing_optional = [i for i in self.items if not i.present and not i.required]
        return {
            "guideline": self.guideline_key.upper(),
            "guideline_name": self.guideline_name,
            "article_type": self.article_type,
            "status": self.status,
            "compliance_pct": self.compliance_pct,
            "required_items": self.required_items,
            "present_required": self.present_required,
            "missing_required": [{"id": i.item_id, "section": i.section, "description": i.description}
                                   for i in missing_required],
            "missing_recommended": [{"id": i.item_id, "section": i.section, "description": i.description}
                                     for i in missing_optional],
            "summary": (
                f"{self.compliance_pct}% compliance ({self.present_required}/{self.required_items} "
                f"required items present). Status: {self.status}."
            ),
        }


_GUIDELINE_NAMES: dict[str, str] = {
    "consort": "CONSORT 2010 (Randomised Controlled Trials)",
    "prisma":  "PRISMA 2020 (Systematic Reviews & Meta-Analyses)",
    "strobe":  "STROBE 2007 (Observational Studies)",
    "care":    "CARE 2016 (Case Reports)",
    "arrive":  "ARRIVE 2.0 (Animal Research)",
    "tripod":  "TRIPOD 2015 (Prediction Models)",
    "cheers":  "CHEERS 2022 (Economic Evaluations)",
    "srqr":    "SRQR (Qualitative Research)",
    "spirit":  "SPIRIT 2013 (Clinical Trial Protocols)",
}


# ─── Public API ───────────────────────────────────────────────────────────────

def article_type_to_guideline(article_type: str) -> str | None:
    key = article_type.lower().replace(" ", "_").replace("-", "_")
    direct = _TYPE_TO_GUIDELINE.get(key)
    if direct:
        return direct
    for at in _BIOMEDICAL_ARTICLE_TYPES:
        if at["key"] == key:
            return at.get("guideline")
    return None


def check_guidelines(
    text: str,
    guideline_key: str,
    article_type: str = "",
) -> GuidelineReport:
    key = guideline_key.lower()
    items_def = _GUIDELINES.get(key)
    if not items_def:
        return GuidelineReport(
            guideline_key=key,
            guideline_name=_GUIDELINE_NAMES.get(key, key.upper()),
            article_type=article_type,
            total_items=0, required_items=0,
            present_required=0, present_optional=0,
        )

    results: list[GuidelineItemResult] = []
    for item in items_def:
        present = item.check(text)
        results.append(GuidelineItemResult(
            item_id=item.item_id,
            section=item.section,
            description=item.description,
            required=item.required,
            present=present,
        ))

    req = [r for r in results if r.required]
    opt = [r for r in results if not r.required]
    return GuidelineReport(
        guideline_key=key,
        guideline_name=_GUIDELINE_NAMES.get(key, key.upper()),
        article_type=article_type,
        total_items=len(results),
        required_items=len(req),
        present_required=sum(1 for r in req if r.present),
        present_optional=sum(1 for r in opt if r.present),
        items=results,
    )


def get_biomedical_article_types() -> list[dict[str, Any]]:
    return _BIOMEDICAL_ARTICLE_TYPES


def list_guidelines() -> list[dict[str, Any]]:
    return [
        {
            "key": k,
            "name": v,
            "items": len(_GUIDELINES.get(k, [])),
        }
        for k, v in _GUIDELINE_NAMES.items()
        if k in _GUIDELINES
    ]


__all__ = [
    "article_type_to_guideline",
    "check_guidelines",
    "get_biomedical_article_types",
    "list_guidelines",
    "GuidelineReport",
]
