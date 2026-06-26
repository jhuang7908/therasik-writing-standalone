"""
Article-type Gold Standard Library (v1.1).
Manages curated benchmark papers and their statistical profiles.
Includes textstat readability metrics (Flesch-Kincaid, Gunning-Fog, Dale-Chall).

PLATFORM_BENCHMARKS: 6 real published papers (antibody/humanized-mouse field),
one per article type.  Used as blind QA targets — excluded from citation search
during writing, then compared against the AI draft after completion.
"""
from __future__ import annotations

import json
import re
import statistics
from datetime import datetime
from pathlib import Path
from typing import Any
from pydantic import BaseModel, Field

import numpy as np

# textstat: pip install textstat — pure Python, zero compiled deps
try:
    import textstat as _textstat
    _TEXTSTAT_AVAILABLE = True
except ImportError:
    _textstat = None  # type: ignore[assignment]
    _TEXTSTAT_AVAILABLE = False

_HERE = Path(__file__).resolve().parent
BENCHMARKS_ROOT = _HERE / "data" / "article_type_benchmarks"
BENCHMARKS_ROOT.mkdir(parents=True, exist_ok=True)

# ---------------------------------------------------------------------------
# PLATFORM BENCHMARKS — 6 real published papers, one per article type.
# All in the antibody / humanized-mouse therapeutic field.
#
# These are used as BLIND QA targets:
#   1. Their PMIDs are excluded from citation search during draft writing.
#   2. After the full draft is complete the user can run a "Compare with
#      Original" step to measure how closely the AI draft matches the expert.
# ---------------------------------------------------------------------------
PLATFORM_BENCHMARKS: dict[str, dict] = {
    "research": {
        "pmid": "37550425",
        "title": (
            "Computational optimization of antibody humanness and stability "
            "by systematic energy-based ranking"
        ),
        "short_title": "CUMAb: structure-guided antibody humanization",
        "authors": "Tennenhouse A, Khmelnitsky L, Khalaila R, et al.",
        "journal": "Communications Biology",
        "year": 2023,
        "doi": "10.1038/s42003-023-05141-1",
        "topic_summary": (
            "Structure-guided pipeline (CUMAb) for humanizing animal antibodies "
            "by systematically grafting CDRs onto thousands of human frameworks "
            "and ranking designs by Rosetta atomistic energy. Demonstrated "
            "superior stability and humanness over homology-based selection alone."
        ),
        "plan_fields": {
            "intent": (
                "We present CUMAb, a web-accessible tool that starts from an "
                "experimental or model antibody structure, grafts animal CDRs onto "
                "thousands of human frameworks, and uses Rosetta energy simulations "
                "to rank designs by stability and structural integrity. The goal is "
                "to show that energy-based ranking outperforms sequence-homology "
                "selection and can identify unexpectedly beneficial non-homologous "
                "human frameworks."
            ),
            "data": (
                "Five independent antibodies humanized with CUMAb; affinities "
                "similar to parental or improved; some designs show marked stability "
                "gains; non-homologous frameworks frequently preferred over highest-"
                "homology templates; multiple CUMAb designs with different frameworks "
                "differing by dozens of mutations proved functionally equivalent."
            ),
            "design": (
                "Input: experimental or modeled antibody structure; CDR grafting "
                "onto a curated set of ~8,000 human framework templates; Rosetta "
                "relax + ΔΔG scoring for each design; top-ranked candidates "
                "expressed in mammalian cells; SPR/BLI binding validation; "
                "SEC/DSF stability assessment."
            ),
            "discussion": (
                "Energy-based framework selection is essential when high-homology "
                "templates fail to maintain stability. CUMAb is publicly available "
                "at http://CUMAb.weizmann.ac.il. Limitations: depends on structure "
                "quality; not validated for antibody–antigen co-crystal inputs."
            ),
        },
    },
    "review": {
        "pmid": "38812514",
        "title": (
            "Prospects for the computational humanization of antibodies and nanobodies"
        ),
        "short_title": "Computational antibody/nanobody humanization review",
        "authors": "Gordon GL, Raybould MIJ, Wong A, Deane CM",
        "journal": "Frontiers in Immunology",
        "year": 2024,
        "doi": "10.3389/fimmu.2024.1399438",
        "topic_summary": (
            "Comprehensive review of computational methods for antibody and "
            "nanobody humanization: CDR grafting, resurfacing, SDR grafting, "
            "machine-learning-based tools (Sapiens, Hu-mAb, CUMAb), multi-"
            "parameter optimization, and the special challenges of humanizing VHHs."
        ),
        "plan_fields": {
            "intent": (
                "Narrative review covering computational strategies for antibody "
                "and nanobody (VHH) humanization: from classic CDR-grafting to "
                "deep-learning methods trained on the Observed Antibody Space (OAS). "
                "Emphasis on multi-parameter optimization balancing humanness, "
                "binding affinity retention, and developability, plus the unique "
                "structural challenges of VHH humanization."
            ),
            "data": (
                "Themes: (1) limitations of homology-only framework selection; "
                "(2) ML tools — Sapiens, Hu-mAb, OASis, CUMAb — benchmark "
                "comparisons on ≥150 clinical humanized antibodies; "
                "(3) VHH-specific hallmarks (FR2 hydrophobic core, long CDR3) "
                "that invalidate antibody-focused tools; "
                "(4) evidence on affinity retention rates."
            ),
            "design": (
                "PubMed + SAbDab + OAS literature 2000–2024; English; focus on "
                "published computational tools with validation data; excluded "
                "purely experimental or clinical-outcome studies."
            ),
            "discussion": (
                "Convergence on structure-aware ML approaches; critical gap is "
                "validated VHH-specific datasets; future directions include "
                "structure-conditioned generative models and unified multi-"
                "parameter design pipelines."
            ),
        },
    },
    "case_report": {
        "pmid": "35514985",
        "title": (
            "Case Report: Use of Obinutuzumab as an Alternative Monoclonal "
            "Anti-CD20 Antibody in a Patient With Refractory Immune "
            "Thrombocytopenia Complicated by Rituximab-Induced Serum Sickness "
            "and Anti-Rituximab Antibodies"
        ),
        "short_title": "Obinutuzumab rescue after rituximab serum sickness in ITP",
        "authors": "Blase JR, Frame D, Michniacki TF, Walkovich K",
        "journal": "Frontiers in Immunology",
        "year": 2022,
        "doi": "10.3389/fimmu.2022.863177",
        "topic_summary": (
            "Case of a 25-year-old woman with Evans syndrome who developed "
            "rituximab-induced serum sickness (fever, ARDS, platelet refractoriness) "
            "from neutralizing anti-rituximab antibodies. Successfully rescued by "
            "switching to humanized anti-CD20 obinutuzumab. Mini-review of 10 "
            "prior serum sickness cases from rituximab for ITP."
        ),
        "plan_fields": {
            "intent": (
                "Report a rare and severe case of rituximab-induced serum sickness "
                "complicated by ARDS and presumed neutralizing anti-rituximab "
                "antibodies in a patient with Evans syndrome, highlighting the "
                "therapeutic success of switching to the humanized anti-CD20 "
                "antibody obinutuzumab."
            ),
            "data": (
                "25-year-old female; Evans syndrome; rituximab 375 mg/m² day 0; "
                "serum sickness onset day 7 — fever 39°C, diffuse urticaria, "
                "arthralgias; ARDS requiring high-flow oxygen; platelet "
                "refractoriness; positive anti-rituximab antibody assay; "
                "tocilizumab + high-dose steroids partial response; obinutuzumab "
                "1000 mg IV → complete resolution day 14."
            ),
            "design": (
                "Single-centre case report; infectious work-up negative; "
                "haematophagocytic lymphohistiocytosis panel negative; anti-drug "
                "antibody assay confirmed neutralizing anti-rituximab IgG; "
                "PubMed review of 10 previously published rituximab serum sickness "
                "cases in ITP."
            ),
            "discussion": (
                "First reported ARDS complication in rituximab serum sickness for "
                "ITP. Chimeric vs humanized anti-CD20 antibody immunogenicity "
                "profiles. Key lesson: early recognition of atypical infusion-"
                "related symptoms and availability of humanized anti-CD20 "
                "alternative are critical for patient safety."
            ),
        },
    },
    "letter": {
        "pmid": "34110413",
        "title": (
            "Humanization of antibodies using a machine learning approach "
            "on large-scale repertoire data"
        ),
        "short_title": "Hu-mAb: ML antibody humanization (Application Note)",
        "authors": "Marks C, Hummer AM, Chin M, Deane CM",
        "journal": "Bioinformatics",
        "year": 2021,
        "doi": "10.1093/bioinformatics/btab434",
        "topic_summary": (
            "Application Note introducing Hu-mAb, a random-forest classifier "
            "trained on 2 billion antibody sequences from the Observed Antibody "
            "Space to discriminate human from murine sequences and suggest "
            "humanizing mutations. Outperforms prior best-in-class; mutations "
            "substantially overlap with those deduced experimentally for known "
            "therapeutic antibodies."
        ),
        "plan_fields": {
            "intent": (
                "Brief report: we built Hu-mAb, a machine-learning tool using "
                "random-forest classifiers trained on the Observed Antibody Space "
                "(OAS, 2 billion sequences) to distinguish human from murine "
                "antibody sequences and suggest humanizing mutations. Hu-mAb "
                "outperforms current best-in-class models and its mutation "
                "suggestions substantially match those found experimentally for "
                "known therapeutic antibodies."
            ),
            "data": (
                "Classifier AUC >0.97 on held-out test set; negative correlation "
                "of Hu-mAb score with experimental immunogenicity of known "
                "therapeutics; for 12 antibodies with known parental sequences, "
                "Hu-mAb mutation lists overlap ≥60% with experimental "
                "humanization decisions."
            ),
            "design": (
                "V-gene-specific random forest models; features: per-position "
                "amino acid one-hot + germline identity; training: OAS 2B sequences "
                "balanced murine/human; validation: benchmark vs Sapiens + BioPhi "
                "OASis; Hu-mAb available as open-source tool."
            ),
            "discussion": (
                "Hu-mAb replaces trial-and-error humanization experiments "
                "computationally; limitation is OAS sampling bias toward IgG "
                "isotypes; does not model CDR-framework packing interactions."
            ),
        },
    },
    "protocol": {
        "pmid": "39076979",
        "title": (
            "Comparison of 'framework shuffling' and 'CDR grafting' in "
            "humanization of a PD-1 murine antibody"
        ),
        "short_title": "Framework shuffling vs CDR grafting for PD-1 antibody humanization",
        "authors": "Wang Y, Chen Y, Xu H, et al.",
        "journal": "Frontiers in Immunology",
        "year": 2024,
        "doi": "10.3389/fimmu.2024.1395854",
        "topic_summary": (
            "Head-to-head comparison of CDR-grafting and framework-shuffling "
            "humanization workflows applied to murine anti-PD-1 antibody XM-PD1. "
            "Evaluates purity, thermal stability (DSF), binding (SPR), predicted "
            "humanness (OASis), and T-cell epitope immunogenicity for all "
            "candidate variants, providing a practical step-by-step guide."
        ),
        "plan_fields": {
            "intent": (
                "Protocol-style comparison of two humanization strategies — CDR "
                "grafting and framework shuffling — applied to the murine anti-PD-1 "
                "antibody XM-PD1. Primary goal: determine which workflow better "
                "preserves affinity and stability while minimising immunogenic risk."
            ),
            "data": (
                "9 CDR-grafting candidates (H1–H9) and 9 FR-shuffling candidates "
                "(T1–T9) expressed in ExpiCHO; binding affinity KD by SPR; Tm by "
                "DSF; OASis humanness score; T-cell epitope burden by in silico "
                "MHCII prediction; SEC purity >95% for all leads."
            ),
            "design": (
                "Step 1: CDR-grafting — select human IGHV/IGLV with highest "
                "homology + key back-mutations; "
                "Step 2: FR-shuffling — phage-display library >4×10⁶ diversity "
                "of human germline FRs with fixed CDRs; "
                "Step 3: Parallel head-to-head characterisation of top candidates."
            ),
            "discussion": (
                "FR-shuffling produced variants with higher OASis scores and lower "
                "predicted T-cell epitope burden than CDR-grafting; CDR-grafting "
                "faster to execute. Recommendation: use FR-shuffling when "
                "immunogenicity risk is the primary concern; CDR-grafting for "
                "rapid lead identification."
            ),
        },
    },
    "systematic_review": {
        "pmid": "34797516",
        "title": (
            "Anti-Drug Antibody Formation Against Biologic Agents in "
            "Inflammatory Bowel Disease: A Systematic Review and Meta-analysis"
        ),
        "short_title": "ADA rates to biologics in IBD: systematic review & meta-analysis",
        "authors": "Sazonovs A, Kennedy NA, Ahmad T, et al.",
        "journal": "Inflammatory Bowel Diseases",
        "year": 2022,
        "doi": "10.1093/ibd/izab220",
        "topic_summary": (
            "PRISMA-compliant meta-analysis of 68 studies (33 in meta-analysis, "
            "5,850 patients) quantifying anti-drug antibody (ADA) rates for six "
            "biologics used in IBD. Pooled ADA monotherapy rates: infliximab 28%, "
            "adalimumab 7.5%, golimumab 3.8%, certolizumab 10.9%, ustekinumab "
            "6.2%, natalizumab 16%. Combination immunomodulator therapy "
            "significantly reduced ADA formation."
        ),
        "plan_fields": {
            "intent": (
                "Systematic review and meta-analysis assessing the rate of "
                "anti-drug antibody (ADA) formation against all major biologic "
                "agents used in inflammatory bowel disease (IBD), the impact of "
                "combination immunomodulator therapy on ADA rates, and the "
                "association of ADAs with clinical efficacy and safety outcomes."
            ),
            "data": (
                "68 studies identified; 33 studies (n=5,850 patients) in meta-"
                "analysis; pooled ADA monotherapy rates per biologic (infliximab "
                "28%, adalimumab 7.5%, golimumab 3.8%, certolizumab 10.9%, "
                "ustekinumab 6.2%, natalizumab 16%); combination therapy reduced "
                "ADA rates for all assessed agents (RR 0.20–0.52); ADA to "
                "infliximab associated with lower clinical response (RR 0.75)."
            ),
            "design": (
                "PICO: IBD patients treated with biologics; outcome: ADA incidence, "
                "drug levels, clinical response, safety. "
                "Databases: MEDLINE, Embase, CENTRAL through April 2020. "
                "Inclusion: RCTs and observational studies reporting immunogenicity. "
                "GRADE evidence quality assessment. PRISMA 2020 reporting."
            ),
            "discussion": (
                "High heterogeneity partly explained by drug-sensitive assay use "
                "underestimating ADAs. Combination immunomodulator therapy "
                "consistently protective. Limitation: short follow-up in most RCTs; "
                "assay non-standardisation across studies. Future: real-world "
                "long-term ADA monitoring needed for newer biologics."
            ),
        },
    },
}


def get_platform_benchmark(article_type: str) -> dict | None:
    """Return the platform benchmark record for a given article type, or None."""
    return PLATFORM_BENCHMARKS.get(article_type)

def _embed_texts(texts: list[str], openai_client: Any) -> np.ndarray:
    resp = openai_client.embeddings.create(model="text-embedding-3-small", input=texts)
    vecs = np.array([d.embedding for d in resp.data], dtype=np.float32)
    norms = np.linalg.norm(vecs, axis=1, keepdims=True)
    norms[norms == 0] = 1.0
    return vecs / norms

class ReadabilityStats(BaseModel):
    """textstat-derived readability metrics (all optional — graceful if textstat missing)."""
    flesch_reading_ease: float | None = None      # 0–100; higher = easier; target 30–50 for academic
    flesch_kincaid_grade: float | None = None     # US grade level; target 14–18 for research papers
    gunning_fog: float | None = None              # fog index; < 18 for readable academic prose
    dale_chall: float | None = None               # comprehension score; 9–10 = college level
    smog_index: float | None = None               # SMOG grade
    automated_readability: float | None = None    # ARI
    avg_syllables_per_word: float | None = None


class SectionStats(BaseModel):
    word_count: int = 0
    sentence_count: int = 0
    paragraph_count: int = 0
    avg_sentence_length: float = 0.0
    sentence_length_std: float = 0.0
    citation_count: int = 0
    citations_per_100_words: float = 0.0
    readability: ReadabilityStats = Field(default_factory=ReadabilityStats)


class PaperProfile(BaseModel):
    pmid: str
    title: str
    article_type: str
    total_word_count: int = 0
    sections: dict[str, SectionStats] = Field(default_factory=dict)
    vocabulary_richness: float = 0.0    # unique words / total words
    readability: ReadabilityStats = Field(default_factory=ReadabilityStats)


class TypeStandardProfile(BaseModel):
    article_type: str
    n_papers: int = 0
    avg_total_words: float = 0.0
    section_baselines: dict[str, SectionStats] = Field(default_factory=dict)
    avg_readability: ReadabilityStats = Field(default_factory=ReadabilityStats)
    textstat_available: bool = _TEXTSTAT_AVAILABLE
    updated_at: str = ""

def compute_readability(text: str) -> ReadabilityStats:
    """Return textstat metrics. All fields None if textstat not installed."""
    if not _TEXTSTAT_AVAILABLE or not text.strip():
        return ReadabilityStats()
    try:
        syllables = _textstat.syllable_count(text)
        words = _textstat.lexicon_count(text, removepunct=True)
        return ReadabilityStats(
            flesch_reading_ease=round(_textstat.flesch_reading_ease(text), 1),
            flesch_kincaid_grade=round(_textstat.flesch_kincaid_grade(text), 1),
            gunning_fog=round(_textstat.gunning_fog(text), 1),
            dale_chall=round(_textstat.dale_chall_readability_score(text), 2),
            smog_index=round(_textstat.smog_index(text), 1),
            automated_readability=round(_textstat.automated_readability_index(text), 1),
            avg_syllables_per_word=round(syllables / max(1, words), 2),
        )
    except Exception:
        return ReadabilityStats()


def readability_verdict(stats: ReadabilityStats) -> str:
    """
    'pass'  = metrics consistent with peer-reviewed biomedical prose
    'warn'  = borderline (too easy or too hard)
    'fail'  = clearly outside expected range
    Target for biomedical research: FK-grade 14–20, Gunning-Fog 14–22
    """
    if stats.flesch_kincaid_grade is None:
        return "unavailable"
    fk = stats.flesch_kincaid_grade
    fog = stats.gunning_fog or 0
    if 13 <= fk <= 22 and (fog == 0 or 12 <= fog <= 24):
        return "pass"
    if 10 <= fk <= 25:
        return "warn"
    return "fail"


def _split_sentences(text: str) -> list[str]:
    return re.split(r"(?<=[.!?])\s+(?=[A-Z(])", text.strip())

def _split_paragraphs(text: str) -> list[str]:
    return [p.strip() for p in re.split(r"\n\s*\n+", text.strip()) if p.strip()]

def _count_citations(text: str) -> int:
    # Match [1], [1, 2], (Author, 2024), (Author et al., 2024)
    numbered = len(re.findall(r"\[\d+(?:,\s*\d+)*\]", text))
    parenthetical = len(re.findall(r"\([A-Z][a-z]+(?:\s+et\s+al\.)?,\s*\d{4}\)", text))
    return numbered + parenthetical

def _heuristic_sections(text: str) -> dict[str, str]:
    """
    Split text into named sections based on common academic headings.
    Falls back to a single 'body' section if no headings found.
    """
    heading_re = re.compile(
        r"^\s*(?:#+\s*)?("
        r"abstract|introduction|background|methods?|materials?\s+and\s+methods?"
        r"|results?|discussion|conclusion|references?|figure\s+legends?"
        r")\s*$",
        re.IGNORECASE | re.MULTILINE,
    )
    parts: dict[str, list[str]] = {}
    current = "body"
    for line in text.splitlines():
        m = heading_re.match(line)
        if m:
            current = m.group(1).lower().replace(" ", "_")
            parts.setdefault(current, [])
        else:
            parts.setdefault(current, []).append(line)
    if not parts or list(parts.keys()) == ["body"]:
        return {"body": text}
    return {k: "\n".join(v) for k, v in parts.items() if "\n".join(v).strip()}


def analyze_paper_text(
    text: str,
    article_type: str,
    pmid: str = "unknown",
    title: str = "unknown",
) -> PaperProfile:
    total_words = len(text.split())
    words_lower = re.findall(r"\w+", text.lower())
    richness = len(set(words_lower)) / max(1, len(words_lower))

    profile = PaperProfile(
        pmid=pmid,
        title=title,
        article_type=article_type,
        total_word_count=total_words,
        vocabulary_richness=round(richness, 4),
        readability=compute_readability(text),
    )

    section_map = _heuristic_sections(text)
    for key, content in section_map.items():
        sents = _split_sentences(content)
        paras = _split_paragraphs(content)
        sent_lens = [len(s.split()) for s in sents if s.strip()]
        cites = _count_citations(content)
        profile.sections[key] = SectionStats(
            word_count=len(content.split()),
            sentence_count=len(sents),
            paragraph_count=len(paras),
            avg_sentence_length=round(statistics.mean(sent_lens), 2) if sent_lens else 0,
            sentence_length_std=round(statistics.stdev(sent_lens), 2) if len(sent_lens) > 1 else 0,
            citation_count=cites,
            citations_per_100_words=round((cites / max(1, len(content.split()))) * 100, 2),
            readability=compute_readability(content),
        )
    return profile

def save_benchmark_paper(username: str, profile: PaperProfile, full_text: str):
    user_dir = BENCHMARKS_ROOT / username
    user_dir.mkdir(parents=True, exist_ok=True)
    
    type_dir = user_dir / profile.article_type
    type_dir.mkdir(parents=True, exist_ok=True)
    
    # Save JSON profile
    (type_dir / f"{profile.pmid}.json").write_text(profile.json(indent=2), encoding="utf-8")
    # Save text
    (type_dir / f"{profile.pmid}.txt").write_text(full_text, encoding="utf-8")

def get_type_standard(username: str, article_type: str) -> TypeStandardProfile | None:
    type_dir = BENCHMARKS_ROOT / username / article_type
    if not type_dir.exists():
        return None
    
    profiles = []
    for p in type_dir.glob("*.json"):
        try:
            profiles.append(PaperProfile.parse_raw(p.read_text(encoding="utf-8")))
        except Exception:
            continue
            
    if not profiles:
        return None
        
    std = TypeStandardProfile(
        article_type=article_type,
        n_papers=len(profiles),
        avg_total_words=round(statistics.mean([p.total_word_count for p in profiles]), 1),
        updated_at=datetime.utcnow().isoformat(),
        textstat_available=_TEXTSTAT_AVAILABLE,
    )

    # Aggregate body-level section stats
    all_body = [p.sections.get("body") for p in profiles if p.sections.get("body")]
    if all_body:
        std.section_baselines["body"] = SectionStats(
            word_count=int(statistics.mean([s.word_count for s in all_body])),
            sentence_count=int(statistics.mean([s.sentence_count for s in all_body])),
            paragraph_count=int(statistics.mean([s.paragraph_count for s in all_body])),
            avg_sentence_length=round(statistics.mean([s.avg_sentence_length for s in all_body]), 2),
            sentence_length_std=round(statistics.mean([s.sentence_length_std for s in all_body]), 2),
            citation_count=int(statistics.mean([s.citation_count for s in all_body])),
            citations_per_100_words=round(statistics.mean([s.citations_per_100_words for s in all_body]), 2),
        )

    # Aggregate readability across all papers
    fk_vals = [p.readability.flesch_kincaid_grade for p in profiles if p.readability.flesch_kincaid_grade is not None]
    fog_vals = [p.readability.gunning_fog for p in profiles if p.readability.gunning_fog is not None]
    fre_vals = [p.readability.flesch_reading_ease for p in profiles if p.readability.flesch_reading_ease is not None]
    std.avg_readability = ReadabilityStats(
        flesch_reading_ease=round(statistics.mean(fre_vals), 1) if fre_vals else None,
        flesch_kincaid_grade=round(statistics.mean(fk_vals), 1) if fk_vals else None,
        gunning_fog=round(statistics.mean(fog_vals), 1) if fog_vals else None,
    )
    return std

def index_standard_library(username: str, article_type: str, openai_client: Any):
    """
    Embed all benchmark papers for this type and save to a local .npz index.
    """
    type_dir = BENCHMARKS_ROOT / username / article_type
    if not type_dir.exists():
        return
        
    texts = []
    for p in type_dir.glob("*.txt"):
        texts.append(p.read_text(encoding="utf-8")[:8000]) # chunk for embedding
        
    if not texts:
        return
        
    vecs = _embed_texts(texts, openai_client)
    idx_path = type_dir / "index.npz"
    np.savez_compressed(str(idx_path), vectors=vecs, texts=np.array(texts, dtype=object))
