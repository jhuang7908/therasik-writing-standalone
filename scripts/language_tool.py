"""
language_tool.py — LanguageTool grammar checker with 3-layer biomedical filtering.

Public API: https://api.languagetool.org/v2/check  (free, no key, 20 req/min)
Optional premium: set LT_USERNAME + LT_API_KEY env vars.

Design principle:
  LanguageTool surfaces hundreds of issues for technical manuscripts.
  This module applies three progressive filters plus AI-style confidence
  scoring to reduce noise to a signal-to-noise ratio fit for editorial use.

  The final output is SUGGESTIONS ONLY — every finding is tagged with a
  confidence level (HIGH / MEDIUM / LOW) and a judgment note.
  The AI agent or human author decides whether to adopt each suggestion.

Filter pipeline:
  1. Category whitelist  — keep GRAMMAR + PUNCTUATION, discard TYPOS/STYLE/CASING
  2. Rule ID blacklist   — discard known noisy rule IDs
  3. Technical term skip — auto-extract terms from the manuscript, skip matches
  4. Confidence scoring  — context-aware scoring; only HIGH+MEDIUM returned by default

Rate limiting: 1 req / 3.5s  (conservative for free tier, 20 req/min limit)
"""

from __future__ import annotations

import json
import os
import re
import time
import urllib.error
import urllib.parse
import urllib.request
from typing import Optional

# ── API config ─────────────────────────────────────────────────────────────────
_LT_URL      = os.environ.get("LT_URL", "https://api.languagetool.org/v2/check")
_LT_USERNAME = os.environ.get("LT_USERNAME", "")
_LT_API_KEY  = os.environ.get("LT_API_KEY", "")
_LT_LANGUAGE = "en-US"
_MIN_INTERVAL = 3.5          # conservative: ~17 req/min (leaves headroom)
_MAX_CHARS    = 18_000       # LT limit is 20K; keep buffer
_LAST_CALL    = 0.0

# ── Layer 1: Category whitelist ────────────────────────────────────────────────
# Only grammar and punctuation issues are actionable in technical manuscripts.
_KEEP_CATEGORIES: set[str] = {
    "GRAMMAR",
    "PUNCTUATION",
    "SENTENCE_WHITESPACE",
}
_SKIP_CATEGORIES: set[str] = {
    "TYPOS",          # spelling — main source of biomedical FP
    "STYLE",          # stylistic preference — debatable
    "CASING",         # ALL_CAPS genes/proteins
    "TYPOGRAPHY",     # quote/dash style
    "REDUNDANCY",     # verbose phrasing
    "COLLOCATIONS",   # word pair preference
    "MISC",
}

# ── Layer 2: Rule ID blacklist ─────────────────────────────────────────────────
_SKIP_RULE_IDS: set[str] = {
    "MORFOLOGIK_RULE_EN_US",    # spelling checker — top FP source
    "MORFOLOGIK_RULE_EN_GB",
    "EN_UNPAIRED_BRACKETS",     # equation/formula brackets
    "COMMA_COMPOUND_SENTENCE",  # legitimate long sentences in Methods
    "UPPERCASE_SENTENCE_START", # abbreviation at sentence start
    "EN_COMPOUNDS",             # hyphenation preference
    "ABBREVIATION",             # known abbreviations flagged
    "UNIT_SPACE",               # unit spacing (10μg, 5mL)
    "CURRENCY",                 # dollar signs in statistics
    "EN_SPECIFIC_CASE",         # proper noun casing
    "WHITESPACE_RULE",          # whitespace between special chars
    "DOUBLE_PUNCTUATION",       # ellipsis / multi-dot
}

# ── Layer 3: Technical term patterns ──────────────────────────────────────────
# Auto-extracted from the manuscript; also a hardcoded biomedical seed list.
_BIOMEDICAL_SEEDS: set[str] = {
    # Immunology
    "PD-1","PD-L1","CTLA-4","CD8","CD4","CD3","CD19","CD20","CD25","CD28",
    "CD45","CD56","CD80","CD86","NK","TCR","BCR","MHC","HLA","IFN","TNF",
    "IL-2","IL-6","IL-10","IL-12","IL-17","IL-23","TGF",
    # Antibody formats
    "mAb","IgG","IgM","IgA","IgE","scFv","Fab","Fc","VH","VL","VHH",
    "CDR","FR","ADCC","CDC","FcRn","BiTE","bsAb","ADC",
    # Cell biology
    "PBMC","BMDC","HSPC","iPSC","MSC","HEK","CHO","HeLa","Jurkat","Raji",
    "ATCC","DSMZ","ECACC","STR","IACUC","IRB",
    # Molecular biology
    "PCR","qPCR","RT-PCR","ELISA","FACS","FISH","ChIP","RNA-seq","scRNA-seq",
    "CRISPR","CRISPRa","CRISPRi","sgRNA","crRNA","Cas9","AAV","LNP",
    "siRNA","shRNA","miRNA","lncRNA","circRNA","mRNA",
    # Statistics / metrics
    "CI","HR","OR","RR","AUC","ROC","RMSD","RMSF","SPR","ITC","BLI",
    "IC50","EC50","KD","kon","koff","pI","MW","Da","kDa",
    # Greek / special
    "α","β","γ","δ","ε","μ","λ","Δ","Ω","σ","τ","κ",
    # Units
    "μg","μL","μM","μm","nM","mM","ng","mg","mL","kPa","rpm","g/mol",
}


# ══════════════════════════════════════════════════════════════════════════════
# TECHNICAL TERM AUTO-EXTRACTION
# ══════════════════════════════════════════════════════════════════════════════

def extract_technical_terms(text: str) -> set[str]:
    """
    Auto-extract technical terms from the manuscript itself.

    Patterns:
      - ALL_CAPS abbreviations:  PBMC, TNF, PCR
      - Hyphenated compounds:    anti-PD-1, IL-2, T-cell
      - CamelCase proteins:      PD-L1, HER2, Cas9
      - Greek-letter combos:     α-helical, β-sheet
    """
    terms: set[str] = set(_BIOMEDICAL_SEEDS)
    # ALL_CAPS (2+ letters, optionally with digits/hyphens)
    terms |= set(re.findall(r'\b[A-Z]{2,}(?:[-–][A-Z0-9α-ω]+)*\b', text))
    # Hyphenated: anti-PD-1, IL-6, T-cell
    terms |= set(re.findall(r'\b[A-Za-z]+-[A-Za-z0-9]+(?:-[A-Za-z0-9]+)*\b', text))
    # Gene/protein name-like: CamelCase with digits (HER2, Cas9, scFv, mAb)
    terms |= set(re.findall(r'\b[A-Z][a-z]{0,2}[A-Z0-9][A-Za-z0-9]{0,8}\b', text))
    # Greek-letter combos
    terms |= set(re.findall(r'[αβγδεζηθλμπρστφψωΑΒΓΔΕΖΗΘΛΜΝΞΠΡΣΤΦΨΩ][-\w]*', text))
    # Single-letter + digit gene names: p53, p21, E2F, H3K27
    terms |= set(re.findall(r'\b[A-Z][a-z]?\d+[A-Za-z0-9]*\b', text))
    return terms


# ══════════════════════════════════════════════════════════════════════════════
# CONFIDENCE SCORING (Layer 4 — AI judgment)
# ══════════════════════════════════════════════════════════════════════════════

# Sections where technical language dominates → downgrade confidence
_TECHNICAL_SECTION_RE = re.compile(
    r"#+\s*(?:methods?|materials?(?:\s+and\s+methods?)?|"
    r"experimental\s+(?:procedures?|design)|protocols?|"
    r"statistical\s+analysis|data\s+analysis)\s*$",
    re.IGNORECASE | re.MULTILINE,
)

def _token_is_technical(token: str) -> bool:
    """
    True if the flagged token itself looks like a technical term.
    Only the token is checked — NOT the surrounding prose.
    Surrounding prose in biomedical text is always dense with abbreviations,
    so checking context at 200 chars would always fire.
    """
    t = token.strip(".,;:()")
    # All-caps abbreviation (gene, protein, assay)
    if re.match(r'^[A-Z]{2,}(?:[-–][A-Z0-9]+)*$', t):
        return True
    # Contains Greek letter or unit suffix
    if re.search(r'[αβγδεζηθλμπρστφψωΑ-Ω]|(?:\d+[a-z]{0,2}(?:μ|n|m|p|k)[gLMm])', t):
        return True
    # Gene/protein name with digit (HER2, IL-6, CD8, p53)
    if re.match(r'^[A-Z]{1,4}[-–]?\d+', t):
        return True
    # Hyphenated compound with an uppercase part (anti-PD-1, T-cell is handled by term list)
    if re.search(r'[A-Z]{2,}', t) and '-' in t:
        return True
    return False


def _score_match(m: dict, text: str) -> str:
    """
    Assign confidence: HIGH / MEDIUM / LOW to a filtered LT match.

    HIGH   → confident grammar issue; AI agent should strongly consider fixing.
    MEDIUM → likely issue but context ambiguous; AI agent should review manually.
    LOW    → marginal; style-adjacent; AI agent may ignore.

    Key design: We do NOT penalise based on surrounding technical context
    (which in biomedical prose is always dense). We only penalise if the
    flagged token ITSELF looks technical — which Layers 1-3 should have
    caught but might miss in edge cases.
    """
    category     = m["rule"]["category"]["id"]
    replacements = m.get("replacements", [])
    length       = m["length"]
    offset       = m["offset"]
    token        = text[offset: offset + length]

    # Token itself looks technical → likely FP that slipped through term filter
    if _token_is_technical(token):
        return "LOW"

    # Single-character fixes: apostrophe / hyphen style — often FP
    if length <= 2:
        return "LOW"

    # Strong grammar signal: clear single replacement, meaningful token length
    if (category == "GRAMMAR"
            and len(replacements) == 1
            and length >= 3):
        return "HIGH"

    # Moderate: grammar with multiple replacements, or punctuation
    if category in ("GRAMMAR", "PUNCTUATION") and len(replacements) <= 4:
        return "MEDIUM"

    return "LOW"


# ══════════════════════════════════════════════════════════════════════════════
# HTTP + API CALL
# ══════════════════════════════════════════════════════════════════════════════

def _wait():
    global _LAST_CALL
    elapsed = time.monotonic() - _LAST_CALL
    if elapsed < _MIN_INTERVAL:
        time.sleep(_MIN_INTERVAL - elapsed)
    _LAST_CALL = time.monotonic()


def _lt_call(text: str) -> list[dict]:
    """Send text to LanguageTool API; return raw match list."""
    _wait()
    params: dict[str, str] = {"text": text, "language": _LT_LANGUAGE}
    if _LT_USERNAME and _LT_API_KEY:
        params["username"] = _LT_USERNAME
        params["apiKey"]   = _LT_API_KEY

    data = urllib.parse.urlencode(params).encode("utf-8")
    req  = urllib.request.Request(
        _LT_URL,
        data=data,
        headers={"Content-Type": "application/x-www-form-urlencoded",
                 "Accept": "application/json",
                 "User-Agent": "TheraSIK-GrammarExpert/1.0"},
        method="POST",
    )
    try:
        with urllib.request.urlopen(req, timeout=12) as resp:
            return json.loads(resp.read().decode("utf-8")).get("matches", [])
    except Exception as exc:
        raise RuntimeError(f"LanguageTool API error: {exc}") from exc


# ══════════════════════════════════════════════════════════════════════════════
# THREE-LAYER FILTER
# ══════════════════════════════════════════════════════════════════════════════

def filter_matches(
    matches: list[dict],
    text: str,
    tech_terms: set[str],
    min_confidence: str = "MEDIUM",
) -> list[dict]:
    """
    Apply 3-layer filter + confidence scoring to raw LT matches.

    Returns only matches that pass all layers AND meet the confidence threshold.
    Each returned match gets two extra keys: 'confidence' and 'judgment_note'.
    """
    conf_rank = {"HIGH": 3, "MEDIUM": 2, "LOW": 1}
    threshold = conf_rank.get(min_confidence, 2)

    result = []
    for m in matches:
        cat_id  = m["rule"]["category"]["id"]
        rule_id = m["rule"]["id"]
        token   = text[m["offset"]: m["offset"] + m["length"]]

        # ── Layer 1: category whitelist ────────────────────────────────────
        if cat_id in _SKIP_CATEGORIES or cat_id not in _KEEP_CATEGORIES:
            continue

        # ── Layer 2: rule ID blacklist ─────────────────────────────────────
        if rule_id in _SKIP_RULE_IDS:
            continue

        # ── Layer 3: technical term skip ──────────────────────────────────
        token_clean = token.strip(".,;:()")
        if (token_clean in tech_terms
                or token_clean.upper() in tech_terms
                or token_clean.lower() in tech_terms):
            continue
        # Also skip if any component of a hyphenated token is a tech term
        parts = re.split(r"[-–]", token_clean)
        if any(p in tech_terms or p.upper() in tech_terms for p in parts):
            continue

        # ── Layer 4: confidence scoring ────────────────────────────────────
        confidence = _score_match(m, text)
        if conf_rank.get(confidence, 0) < threshold:
            continue

        # ── Build clean suggestion dict ────────────────────────────────────
        replacements = [r["value"] for r in m.get("replacements", [])[:3]]
        ctx = m.get("context", {})
        snippet = ctx.get("text", "")
        ctx_offset = ctx.get("offset", 0)
        ctx_length = ctx.get("length", 0)
        highlighted = (snippet[:ctx_offset]
                       + "【" + snippet[ctx_offset: ctx_offset + ctx_length] + "】"
                       + snippet[ctx_offset + ctx_length:])

        judgment_note = {
            "HIGH":   "Likely genuine grammar issue — consider fixing.",
            "MEDIUM": "Possible issue — verify in context before accepting.",
            "LOW":    "Marginal suggestion — AI agent may discard.",
        }.get(confidence, "")

        result.append({
            "rule_id":      rule_id,
            "category":     cat_id,
            "message":      m["message"],
            "token":        token,
            "replacements": replacements,
            "context":      highlighted.strip(),
            "offset":       m["offset"],
            "length":       m["length"],
            "confidence":   confidence,
            "judgment_note": judgment_note,
        })

    return result


# ══════════════════════════════════════════════════════════════════════════════
# SECTION-AWARE CHECKING (handles long manuscripts)
# ══════════════════════════════════════════════════════════════════════════════

def _split_sections(text: str, max_chars: int = _MAX_CHARS) -> list[tuple[int, str]]:
    """
    Split text into chunks ≤ max_chars, breaking on paragraph boundaries.
    Returns list of (start_offset, chunk_text).
    """
    if len(text) <= max_chars:
        return [(0, text)]

    chunks: list[tuple[int, str]] = []
    pos = 0
    while pos < len(text):
        end = min(pos + max_chars, len(text))
        if end < len(text):
            # Find last paragraph break before end
            break_pos = text.rfind("\n\n", pos, end)
            if break_pos > pos:
                end = break_pos
        chunks.append((pos, text[pos:end]))
        pos = end
    return chunks


def check_text(
    text: str,
    min_confidence: str = "MEDIUM",
    tech_terms: set[str] | None = None,
) -> list[dict]:
    """
    Check a text block with LanguageTool and return filtered suggestions.

    Args:
        text:           The text to check.
        min_confidence: Minimum confidence to include ("HIGH", "MEDIUM", "LOW").
        tech_terms:     Pre-computed technical term set (optional; extracted if None).

    Returns:
        List of filtered suggestion dicts with confidence + judgment_note.
    """
    if tech_terms is None:
        tech_terms = extract_technical_terms(text)

    chunks = _split_sections(text)
    all_suggestions: list[dict] = []

    for base_offset, chunk in chunks:
        raw = _lt_call(chunk)
        suggestions = filter_matches(raw, chunk, tech_terms, min_confidence)
        # Adjust offsets to global text position
        for s in suggestions:
            s["offset"] += base_offset
        all_suggestions.extend(suggestions)

    return all_suggestions


# ══════════════════════════════════════════════════════════════════════════════
# MANUSCRIPT-LEVEL REPORT
# ══════════════════════════════════════════════════════════════════════════════

def check_manuscript(
    text: str,
    min_confidence: str = "MEDIUM",
    max_suggestions: int = 30,
) -> dict:
    """
    Full manuscript grammar check with AI judgment layer.

    Returns structured report compatible with multi_expert_review format:
    {
      "suggestions":   [...],  # filtered, confidence-tagged
      "high_count":    int,
      "medium_count":  int,
      "total_raw":     int,    # before filtering (shows noise reduction)
      "total_filtered":int,    # after all 4 layers
      "tech_terms_found": int,
      "findings":      [...],  # multi_expert_review finding format
    }
    """
    tech_terms = extract_technical_terms(text)

    # Check each section separately for progress tracking
    chunks = _split_sections(text)
    all_raw: list[dict] = []
    all_filtered: list[dict] = []

    for base_offset, chunk in chunks:
        raw = _lt_call(chunk)
        all_raw.extend(raw)
        filtered = filter_matches(raw, chunk, tech_terms, min_confidence="LOW")
        for s in filtered:
            s["offset"] += base_offset
        all_filtered.extend(filtered)

    # Apply confidence threshold for final output
    conf_rank = {"HIGH": 3, "MEDIUM": 2, "LOW": 1}
    threshold = conf_rank.get(min_confidence, 2)
    final = [s for s in all_filtered
             if conf_rank.get(s["confidence"], 0) >= threshold][:max_suggestions]

    high_count   = sum(1 for s in final if s["confidence"] == "HIGH")
    medium_count = sum(1 for s in final if s["confidence"] == "MEDIUM")

    # Build multi_expert_review compatible findings
    findings: list[dict] = []

    if high_count > 0:
        sev = "MAJOR" if high_count >= 5 else "MINOR"
        findings.append({
            "category": "Grammar (HIGH confidence)",
            "severity":  sev,
            "issue": f"{high_count} confirmed grammar issue(s) detected",
            "evidence": "; ".join(
                f'"{s["token"]}" → "{s["replacements"][0]}"'
                for s in final if s["confidence"] == "HIGH"
            )[:300],
            "recommendation": (
                "Review each HIGH-confidence suggestion. These passed all 4 filters "
                "(category + rule ID + technical term + context) and are likely genuine errors."
            ),
        })

    if medium_count > 0:
        findings.append({
            "category": "Grammar (MEDIUM confidence)",
            "severity":  "MINOR",
            "issue": f"{medium_count} probable grammar suggestion(s) — AI agent should verify",
            "evidence": "; ".join(
                f'"{s["token"]}"'
                for s in final if s["confidence"] == "MEDIUM"
            )[:200],
            "recommendation": (
                "Review in manuscript context. MEDIUM suggestions are plausible but "
                "may still be false positives in specialised technical passages. "
                "AI agent or author has final judgment."
            ),
        })

    noise_ratio = (1 - len(all_filtered) / max(1, len(all_raw))) * 100
    findings.append({
        "category": "Grammar scan metadata",
        "severity":  "INFO",
        "issue": (
            f"LanguageTool raw: {len(all_raw)} matches → "
            f"filtered: {len(all_filtered)} → "
            f"reported: {len(final)}. "
            f"Noise reduction: {noise_ratio:.0f}%."
        ),
        "evidence": f"Technical terms auto-identified: {len(tech_terms)}",
        "recommendation": "",
    })

    return {
        "suggestions":      final,
        "high_count":       high_count,
        "medium_count":     medium_count,
        "total_raw":        len(all_raw),
        "total_filtered":   len(all_filtered),
        "total_reported":   len(final),
        "tech_terms_found": len(tech_terms),
        "findings":         findings,
    }


# ══════════════════════════════════════════════════════════════════════════════
# CONNECTIVITY + AVAILABILITY
# ══════════════════════════════════════════════════════════════════════════════

def is_available(timeout: int = 5) -> bool:
    """Quick connectivity check."""
    try:
        data = urllib.parse.urlencode(
            {"text": "This are a test.", "language": "en-US"}
        ).encode("utf-8")
        req = urllib.request.Request(
            _LT_URL, data=data,
            headers={"Content-Type": "application/x-www-form-urlencoded"},
            method="POST",
        )
        with urllib.request.urlopen(req, timeout=timeout) as r:
            j = json.loads(r.read().decode())
            return "matches" in j
    except Exception:
        return False
