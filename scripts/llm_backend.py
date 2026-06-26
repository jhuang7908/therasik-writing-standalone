"""
llm_backend.py — Gemini-backed LLM expert layer for multi_expert_review.

Architecture:
  • GeminiBackend: thin wrapper around google-generativeai SDK.
  • Three expert prompts: AI Diagnostician, Citation Auditor, Reproducibility Reviewer.
  • get_backend(): module-level singleton; honours GEMINI_API_KEY env var.
  • call_expert(): top-level helper used by multi_expert_review.py.

Fallback contract:
  Any exception from Gemini (network, quota, parse error) is caught by the
  *caller* (multi_expert_review.py).  This module only raises on misconfiguration
  so the caller can decide whether to fall back to rule-based mode.
"""

from __future__ import annotations

import json
import logging
import os
import re
import time

logger = logging.getLogger(__name__)

# ── SDK availability probe ────────────────────────────────────────────────────
# Prefer the new google-genai SDK (google.genai); fall back to legacy google-generativeai.
_SDK_NEW     = False
_SDK_LEGACY  = False
_SDK_AVAILABLE = False
_genai_new   = None
_genai_legacy = None

try:
    from google import genai as _genai_new   # pip install google-genai (current)
    _SDK_NEW = True
    _SDK_AVAILABLE = True
except ImportError:
    pass

if not _SDK_NEW:
    try:
        import google.generativeai as _genai_legacy  # pip install google-generativeai (deprecated)
        _SDK_LEGACY = True
        _SDK_AVAILABLE = True
    except ImportError:
        pass


# ══════════════════════════════════════════════════════════════════════════════
# SYSTEM PROMPTS — one per expert role
# ══════════════════════════════════════════════════════════════════════════════

PROMPT_AI_DIAGNOSTICIAN = """You are a senior academic writing quality reviewer whose sole focus is detecting AI-generated prose. You are rigorous, evidence-based, and cite specific passages.

Analyze the manuscript below across these 6 dimensions:

1. **AI phrase markers** — canonical LLM vocabulary that signals AI authorship:
   "delve into / delves into", "pivotal role / crucial role / paramount importance",
   "it is worth noting", "sheds light on", "paves the way", "holds great promise",
   "tapestry", "landscape of", "nuanced", "leverages", "underscores",
   "a growing body of evidence", "taken together", "collectively", "robust(ly)",
   "multifaceted", "intricate", "highlights the importance", "offers valuable insights".
   Flag every occurrence with a quote.

2. **Transition-opener density** — sentences starting with:
   "Furthermore,", "Moreover,", "Additionally,", "However,", "Nevertheless,",
   "Therefore,", "Thus,", "Hence,", "Indeed,", "Certainly,", "Clearly,".
   Flag if >18% of sentences open with these words.

3. **AI self-talk / meta-description** — the text describing itself:
   "In this review / paper / study, we aim to…", "This work provides a comprehensive…",
   "The purpose of this review is to…". Flag every occurrence.

4. **Unanchored factual claims** — assertions of established fact with no citation:
   "Studies have shown that…", "It is well established that…",
   "Research consistently demonstrates that…", "It is widely accepted that…"
   Flag each one if not immediately followed by [n] or (Author Year).

5. **Empty evaluative language** — strong adjectives with no numerical support:
   "excellent/outstanding/remarkable/extraordinary performance/efficacy/results".

6. **Sentence-length rhythm** — compute mean and std of word counts per sentence.
   Flag if mean > 18 and std < 6 (suspiciously uniform cadence).

Return ONLY valid JSON (no markdown wrapper, no prose outside the JSON):
{
  "score": <integer 0-10; 10 = no AI markers found>,
  "findings": [
    {
      "category": "<one of: AI phrase markers | Transition-opener density | AI self-talk | Unanchored claims | Empty evaluative language | Sentence rhythm>",
      "severity": "<CRITICAL | MAJOR | MINOR | INFO>",
      "issue": "<one-sentence problem description>",
      "quote": "<exact excerpt from manuscript, ≤120 chars, or empty string>",
      "recommendation": "<specific, actionable fix>"
    }
  ],
  "ai_phrase_count": <total count of flagged AI phrases>,
  "unanchored_count": <total count of unanchored claims>,
  "opener_rate": <fraction of sentences with transition openers, e.g. 0.21>,
  "summary": "Score X/10. N AI phrase(s), N unanchored claim(s), N self-talk. N critical."
}

Severity guide:
- CRITICAL: AI self-identification text, or ≥8 AI phrases, or ≥3 unanchored claims.
- MAJOR: 4–7 AI phrases, or ≥2 unanchored claims, or transition rate >28%.
- MINOR: 1–3 AI phrases, or 1 unanchored claim, or evaluative language.
- INFO: rhythm note only.

Be exhaustive. Quote the actual text. A clean human-written paper should score 8–10."""


PROMPT_CITATION_AUDITOR = """You are a rigorous citation integrity auditor for peer-reviewed biomedical manuscripts. Your job is to identify hallucination-risk zones and citation hygiene problems.

Analyze the manuscript below across these 6 dimensions:

1. **Citation density** — count all in-text citations ([1], [2,3], (Smith 2023), etc.).
   Divide by total word count × 100 to get citations per 100 words.
   Flag if < 0.5/100 words (hallucination risk) or > 4.0/100 words (padding).

2. **Strong uncited claims** — quantitative or absolute assertions with no immediate citation:
   "significantly increased/decreased/reduced/improved/inhibited [without [n]]",
   "markedly/substantially/dramatically [effect] [without citation]".
   Quote every instance.

3. **Topical citation patterns** — citations used as topic links, not evidence:
   "related to [n]", "as reviewed in [n]", "as reported by [n]",
   "according to [n]", "for review see [n]".
   Flag if > 3 instances (weak evidential support).

4. **Citation-free paragraph clusters** — count consecutive paragraphs (>40 words) with no citation.
   Flag if ≥ 4 consecutive paragraphs lack any citation.

5. **Abstract citation policy** — most journals require citation-free abstracts.
   Flag if abstract contains > 5 citations.

6. **Methods citation density** — novel or modified methods without citations.
   Flag if Methods describes "novel/new/modified/adapted/custom [method/assay/algorithm]"
   but has zero citations in that sentence/paragraph.

Return ONLY valid JSON:
{
  "score": <integer 0-10; 10 = excellent citation hygiene>,
  "findings": [
    {
      "category": "<Citation density | Strong uncited claims | Topical citation pattern | Citation-free paragraphs | Abstract citations | Methods citation>",
      "severity": "<CRITICAL | MAJOR | MINOR | INFO>",
      "issue": "<one-sentence problem description>",
      "quote": "<exact excerpt ≤120 chars, or empty string>",
      "recommendation": "<specific actionable fix>"
    }
  ],
  "total_citations": <integer>,
  "cite_density": <float, citations per 100 words>,
  "uncited_strong": <integer count of strong uncited claims>,
  "summary": "Score X/10. N citation(s), density X.XX/100 words. N uncited strong claim(s). N critical."
}

Severity:
- CRITICAL: density < 0.2/100 words in a >800-word document, or ≥3 strong uncited claims.
- MAJOR: density 0.2–0.5, or ≥4 citation-free paragraphs, or ≥2 uncited strong claims.
- MINOR: topical patterns, methods density issues, abstract over-citation.
- INFO: borderline density, observations."""


PROMPT_REPRODUCIBILITY_REVIEWER = """You are a scientific reproducibility expert reviewing manuscripts against ARRIVE 2.0, CONSORT, and standard journal requirements. You check whether an independent laboratory could replicate the experiments from the information provided.

Analyze the manuscript below across these 7 dimensions:

1. **Methods section completeness** — Is there a Methods section of ≥100 words? Flag if absent or too short.

2. **Sample size / n** — Is n= stated for every experimental group?
   Flag if no explicit "n=" found anywhere in the manuscript.

3. **Statistical software + version** — Is the software and version specified?
   e.g., "R version 4.3.1", "GraphPad Prism 10", "SPSS v29", "Python 3.11 / SciPy 1.11".
   Flag if statistical analysis is performed but software/version is not mentioned.

4. **Cell line provenance** — If cell lines (HEK, CHO, Jurkat, HeLa, Vero, etc.) are used,
   is the source repository (ATCC, DSMZ, ECACC, JCRB) and catalog/accession number stated?
   Is mycoplasma testing or STR authentication mentioned?

5. **Antibody specification** — If antibodies/mAbs are used,
   is the clone name AND catalog number provided for each?
   e.g., "anti-CD3 (clone OKT3; BioLegend cat. 317302)".

6. **Randomisation and blinding** — For in vivo or clinical studies:
   Is the randomisation procedure described? Is blinding mentioned?
   Required by ARRIVE 2.0 and CONSORT.

7. **Data / code availability** — Is there a Data Availability statement?
   Is an actual repository link or accession number provided
   (GEO GSExxxx, SRA PRJNAxxxx, Zenodo DOI, GitHub URL, Figshare)?
   Flag if only "available upon request" with no repository.

Return ONLY valid JSON:
{
  "score": <integer 0-10; 10 = fully reproducible>,
  "findings": [
    {
      "category": "<Methods section | Sample size | Statistical software | Cell line provenance | Antibody specification | Randomisation | Data availability>",
      "severity": "<CRITICAL | MAJOR | MINOR | INFO>",
      "issue": "<one-sentence problem description>",
      "quote": "<exact excerpt ≤120 chars, or empty string>",
      "recommendation": "<specific actionable fix>"
    }
  ],
  "summary": "Score X/10. N critical, N major, N minor."
}

Severity:
- CRITICAL: Methods section absent, no n= anywhere in manuscript.
- MAJOR: software/version missing, cell line source missing, no data availability.
- MINOR: authentication not mentioned, antibody catalog missing, 'available upon request' only.
- INFO: general observations."""


# ══════════════════════════════════════════════════════════════════════════════
# GEMINI BACKEND
# ══════════════════════════════════════════════════════════════════════════════

class GeminiBackend:
    """
    Thin wrapper that supports both google-genai (new) and google-generativeai (legacy).

    SDK preference: google-genai → google-generativeai (legacy, deprecated).
    Rate-limiting: self-enforced to ≤15 RPM (Gemini free tier).
    Model: gemini-1.5-flash by default (free tier, 1M tokens/day).
    """

    DEFAULT_MODEL = "gemini-2.5-flash"
    MIN_INTERVAL  = 4.1     # seconds between calls (15 RPM)
    MAX_CHARS     = 32_000  # ~8K tokens; protects free-tier quota

    def __init__(
        self,
        model:   str | None = None,
        api_key: str | None = None,
    ):
        self.model_name = model   or os.environ.get("GEMINI_MODEL", self.DEFAULT_MODEL)
        self.api_key    = api_key or os.environ.get("GEMINI_API_KEY", "")
        self._client    = None   # new SDK client
        self._legacy_model = None  # legacy SDK model object
        self._last_call = 0.0

    # ── Lazy init ─────────────────────────────────────────────────────────────
    def _ensure_ready(self):
        if not _SDK_AVAILABLE:
            raise RuntimeError(
                "Neither google-genai nor google-generativeai is installed. "
                "Run: pip install google-genai"
            )
        if not self.api_key:
            raise RuntimeError("GEMINI_API_KEY environment variable not set.")

        if _SDK_NEW and self._client is None:
            self._client = _genai_new.Client(api_key=self.api_key)

        if _SDK_LEGACY and not _SDK_NEW and self._legacy_model is None:
            import warnings
            with warnings.catch_warnings():
                warnings.simplefilter("ignore")
                _genai_legacy.configure(api_key=self.api_key)
                self._legacy_model = _genai_legacy.GenerativeModel(self.model_name)

    # ── Rate limiter ──────────────────────────────────────────────────────────
    def _wait_rate_limit(self):
        elapsed = time.monotonic() - self._last_call
        if elapsed < self.MIN_INTERVAL:
            time.sleep(self.MIN_INTERVAL - elapsed)

    # ── Core call ─────────────────────────────────────────────────────────────
    def call(self, system_prompt: str, manuscript: str) -> str:
        """Send expert review request; return raw response text."""
        self._ensure_ready()
        self._wait_rate_limit()

        if len(manuscript) > self.MAX_CHARS:
            half = self.MAX_CHARS // 2
            manuscript = (
                manuscript[:half]
                + "\n\n[... middle truncated for token budget ...]\n\n"
                + manuscript[-half:]
            )

        full_prompt = (
            f"{system_prompt}\n\n"
            f"=== MANUSCRIPT START ===\n{manuscript}\n=== MANUSCRIPT END ==="
        )

        if _SDK_NEW and self._client is not None:
            response = self._client.models.generate_content(
                model=self.model_name,
                contents=full_prompt,
            )
            text = response.text
        else:
            response = self._legacy_model.generate_content(full_prompt)
            text = response.text

        self._last_call = time.monotonic()
        return text

    # ── JSON call ─────────────────────────────────────────────────────────────
    def call_json(self, system_prompt: str, manuscript: str) -> dict:
        """Call Gemini and parse JSON response; raises on parse/network failure."""
        raw = self.call(system_prompt, manuscript)

        stripped = raw.strip()
        m = re.search(r"```(?:json)?\s*([\s\S]+?)\s*```", stripped)
        if m:
            stripped = m.group(1).strip()

        try:
            return json.loads(stripped)
        except json.JSONDecodeError:
            m2 = re.search(r"\{[\s\S]+\}", stripped)
            if m2:
                return json.loads(m2.group())
            raise ValueError(f"Gemini response is not valid JSON:\n{raw[:300]}")


# ══════════════════════════════════════════════════════════════════════════════
# MODULE-LEVEL SINGLETON
# ══════════════════════════════════════════════════════════════════════════════

_BACKEND: GeminiBackend | None = None


def get_backend() -> GeminiBackend:
    global _BACKEND
    if _BACKEND is None:
        _BACKEND = GeminiBackend()
    return _BACKEND


def is_available() -> bool:
    """Return True if Gemini SDK is installed AND API key is present."""
    return _SDK_AVAILABLE and bool(os.environ.get("GEMINI_API_KEY", ""))


# ══════════════════════════════════════════════════════════════════════════════
# TOP-LEVEL EXPERT DISPATCH
# ══════════════════════════════════════════════════════════════════════════════

_EXPERT_PROMPTS = {
    "ai_diagnostician":    PROMPT_AI_DIAGNOSTICIAN,
    "citation_auditor":    PROMPT_CITATION_AUDITOR,
    "reproducibility":     PROMPT_REPRODUCIBILITY_REVIEWER,
}

# Fields expected in each expert's output (for normalisation)
_EXPERT_DEFAULTS = {
    "ai_diagnostician": {
        "reviewer":        "AI Diagnostician",
        "ai_phrase_count": 0,
        "unanchored_count": 0,
        "opener_rate":     0.0,
    },
    "citation_auditor": {
        "reviewer":        "Citation Auditor",
        "total_citations": 0,
        "cite_density":    0.0,
        "uncited_strong":  0,
    },
    "reproducibility": {
        "reviewer": "Reproducibility Reviewer",
    },
}


def call_expert(role: str, text: str) -> dict:
    """
    Call Gemini for the given expert role.

    Args:
        role:  One of 'ai_diagnostician', 'citation_auditor', 'reproducibility'.
        text:  Full manuscript text.

    Returns:
        Normalised result dict compatible with multi_expert_review output format.

    Raises:
        RuntimeError: if SDK not available or API key missing.
        ValueError:   if Gemini response cannot be parsed.
        Any network / quota error from the SDK.
    """
    if role not in _EXPERT_PROMPTS:
        raise ValueError(f"Unknown expert role: {role!r}. "
                         f"Valid: {list(_EXPERT_PROMPTS)}")

    backend  = get_backend()
    raw_data = backend.call_json(_EXPERT_PROMPTS[role], text)

    # Normalise findings to match rule-based format
    findings = []
    for f in raw_data.get("findings", []):
        findings.append({
            "category":       f.get("category", ""),
            "severity":       f.get("severity", "INFO"),
            "issue":          f.get("issue", ""),
            "quote":          f.get("quote", ""),
            "recommendation": f.get("recommendation", ""),
        })

    # Build normalised result
    result = {
        **_EXPERT_DEFAULTS.get(role, {}),
        "score":    int(raw_data.get("score", 5)),
        "status":   _derive_status(findings, int(raw_data.get("score", 5))),
        "findings": findings,
        "summary":  raw_data.get("summary", f"LLM review complete. {len(findings)} finding(s)."),
        "_source":  "gemini",
    }

    # Merge role-specific numeric fields
    for key in ("ai_phrase_count", "unanchored_count", "opener_rate",
                "total_citations", "cite_density", "uncited_strong"):
        if key in raw_data:
            result[key] = raw_data[key]

    return result


def _derive_status(findings: list[dict], score: int) -> str:
    severities = {f["severity"] for f in findings}
    if "CRITICAL" in severities:
        return "CRITICAL"
    if "MAJOR" in severities or score < 7:
        return "MAJOR"
    return "PASS"
