"""
Step 2 — Build per-journal requirement JSON files.  (v2.0 — 3-layer detection)

Detection order:
  Layer 1: TITLE_OVERRIDES  — exact title match for 100+ flagship journals
  Layer 2: PUBLISHER_MAP    — 45+ publisher heuristics (substring match)
  Layer 3: CrossRef API     — ISSN lookup → publisher name → re-run heuristic

Input:  scripts/journal_db/medline_journals_raw.json
Output: assets/journal_requirements/<slug>.json  (one file per journal)
        assets/journal_requirements/_index.json

Usage:
    python scripts/journal_db/build_requirements.py
    python scripts/journal_db/build_requirements.py --limit 100   # test
    python scripts/journal_db/build_requirements.py --no-crossref # skip layer 3
"""

import argparse
import json
import re
import sys
import time
import urllib.error
import urllib.request
from pathlib import Path

HERE        = Path(__file__).parent
DEFAULT_IN  = HERE / "medline_journals_raw.json"
DEFAULT_OUT = Path("assets/journal_requirements")

CROSSREF_UA = "InSynBio-JournalDB/2.0 (mailto:jhuang@genomab.com)"
CROSSREF_DELAY = 0.05   # ~20 req/s, well within polite-pool limit
MAX_RETRIES = 3

# ══════════════════════════════════════════════════════════════════════════════
# LAYER 1 — Title-level overrides (exact case-insensitive match)
# 100+ flagship journals whose submission portal is definitively known.
# Key: lowercase journal title (stripped of trailing punctuation).
# ══════════════════════════════════════════════════════════════════════════════
_NPG = {"system": "NPG / Snapp", "url": "https://mts-nature.nature.com/", "source": "title_override"}
_EM  = {"system": "Editorial Manager", "url": "https://www.editorialmanager.com/", "source": "title_override"}
_S1  = {"system": "ScholarOne", "url": "https://mc.manuscriptcentral.com/", "source": "title_override"}
_ACS = {"system": "ACS Paragon Plus", "url": "https://acsparagonplus.acs.org/", "source": "title_override"}
_AAAS= {"system": "AAAS Submit", "url": "https://submit.science.org/", "source": "title_override"}
_BP  = {"system": "Bench>Press", "url": "https://submit.rupress.org/", "source": "title_override"}
_FR  = {"system": "Frontiers", "url": "https://www.frontiersin.org/submission/", "source": "title_override"}
_EL  = {"system": "eLife", "url": "https://submit.elifesciences.org/", "source": "title_override"}
_PNAS= {"system": "PNAS Submit", "url": "https://submit.pnas.org/", "source": "title_override"}
_BMJ = {"system": "ScholarOne", "url": "https://mc.manuscriptcentral.com/bmj", "source": "title_override"}
_JAMA= {"system": "ScholarOne", "url": "https://manuscript.jama.com/", "source": "title_override"}

TITLE_OVERRIDES: dict[str, dict] = {
    # ── Nature flagship + 45 sub-journals ──────────────────────────────────────
    "nature":                                           _NPG,
    "nature medicine":                                  _NPG,
    "nature biotechnology":                             _NPG,
    "nature methods":                                   _NPG,
    "nature communications":                            _NPG,
    "nature cell biology":                              _NPG,
    "nature chemical biology":                          _NPG,
    "nature chemistry":                                 _NPG,
    "nature genetics":                                  _NPG,
    "nature immunology":                                _NPG,
    "nature neuroscience":                              _NPG,
    "nature structural & molecular biology":            _NPG,
    "nature structural and molecular biology":          _NPG,
    "nature aging":                                     _NPG,
    "nature cancer":                                    _NPG,
    "nature cardiovascular research":                   _NPG,
    "nature ecology & evolution":                       _NPG,
    "nature ecology and evolution":                     _NPG,
    "nature metabolism":                                _NPG,
    "nature microbiology":                              _NPG,
    "nature plants":                                    _NPG,
    "nature physics":                                   _NPG,
    "nature materials":                                 _NPG,
    "nature nanotechnology":                            _NPG,
    "nature photonics":                                 _NPG,
    "nature energy":                                    _NPG,
    "nature sustainability":                            _NPG,
    "nature human behaviour":                           _NPG,
    "nature biomedical engineering":                    _NPG,
    "nature computational science":                     _NPG,
    "nature machine intelligence":                      _NPG,
    "nature electronics":                               _NPG,
    "nature reviews cancer":                            _NPG,
    "nature reviews drug discovery":                    _NPG,
    "nature reviews genetics":                          _NPG,
    "nature reviews immunology":                        _NPG,
    "nature reviews molecular cell biology":            _NPG,
    "nature reviews microbiology":                      _NPG,
    "nature reviews neuroscience":                      _NPG,
    "nature reviews cardiology":                        _NPG,
    "nature reviews clinical oncology":                 _NPG,
    "nature reviews disease primers":                   _NPG,
    "nature reviews endocrinology":                     _NPG,
    "nature reviews gastroenterology & hepatology":     _NPG,
    "nature reviews nephrology":                        _NPG,
    "nature reviews rheumatology":                      _NPG,
    "nature reviews urology":                           _NPG,
    "npj precision oncology":                           _NPG,
    "npj genomic medicine":                             _NPG,
    "npj breast cancer":                                _NPG,
    "npj digital medicine":                             _NPG,
    "npj vaccines":                                     _NPG,
    "scientific reports":                               _NPG,
    "communications biology":                           _NPG,
    "communications medicine":                          _NPG,
    # ── Science family (AAAS) ──────────────────────────────────────────────────
    "science":                                          _AAAS,
    "science translational medicine":                   _AAAS,
    "science advances":                                 _AAAS,
    "science signaling":                                _AAAS,
    "science immunology":                               _AAAS,
    "science robotics":                                 _AAAS,
    # ── Cell Press (Editorial Manager) ─────────────────────────────────────────
    "cell":                                             _EM,
    "cancer cell":                                      _EM,
    "cell chemical biology":                            _EM,
    "cell host & microbe":                              _EM,
    "cell host and microbe":                            _EM,
    "cell metabolism":                                  _EM,
    "cell reports":                                     _EM,
    "cell reports medicine":                            _EM,
    "cell stem cell":                                   _EM,
    "cell systems":                                     _EM,
    "current biology":                                  _EM,
    "developmental cell":                               _EM,
    "immunity":                                         _EM,
    "molecular cell":                                   _EM,
    "neuron":                                           _EM,
    "structure":                                        _EM,
    "trends in biochemical sciences":                   _EM,
    "trends in cell biology":                           _EM,
    "trends in immunology":                             _EM,
    "trends in pharmacological sciences":               _EM,
    "trends in molecular medicine":                     _EM,
    "trends in neurosciences":                          _EM,
    "trends in microbiology":                           _EM,
    # ── NEJM / Lancet / BMJ / JAMA ─────────────────────────────────────────────
    "the new england journal of medicine":              _S1,
    "new england journal of medicine":                  _S1,
    "the lancet":                                       _EM,
    "lancet oncology":                                  _EM,
    "lancet neurology":                                 _EM,
    "lancet infectious diseases":                       _EM,
    "lancet psychiatry":                                _EM,
    "lancet digital health":                            _EM,
    "lancet haematology":                               _EM,
    "lancet rheumatology":                              _EM,
    "lancet respiratory medicine":                      _EM,
    "lancet public health":                             _EM,
    "lancet global health":                             _EM,
    "bmj":                                              _BMJ,
    "the bmj":                                          _BMJ,
    "bmj open":                                         _BMJ,
    "jama":                                             _JAMA,
    "jama oncology":                                    _JAMA,
    "jama cardiology":                                  _JAMA,
    "jama neurology":                                   _JAMA,
    "jama psychiatry":                                  _JAMA,
    "jama internal medicine":                           _JAMA,
    "jama surgery":                                     _JAMA,
    "jama pediatrics":                                  _JAMA,
    "jama network open":                                _JAMA,
    # ── PNAS ───────────────────────────────────────────────────────────────────
    "proceedings of the national academy of sciences of the united states of america": _PNAS,
    "pnas nexus":                                       _PNAS,
    # ── eLife ──────────────────────────────────────────────────────────────────
    "elife":                                            _EL,
    # ── JCI ────────────────────────────────────────────────────────────────────
    "the journal of clinical investigation":            _BP,
    "journal of clinical investigation":                _BP,
    "jci insight":                                      _BP,
    # ── Immunity / JEM (Rockefeller) ───────────────────────────────────────────
    "the journal of experimental medicine":             _BP,
    "journal of experimental medicine":                 _BP,
    "journal of cell biology":                          _BP,
    "journal of general physiology":                    _BP,
    # ── Blood / ASH ────────────────────────────────────────────────────────────
    "blood":                                            _S1,
    "blood advances":                                   _S1,
    # ── ACS flagships ──────────────────────────────────────────────────────────
    "journal of the american chemical society":         _ACS,
    "acs nano":                                         _ACS,
    "acs central science":                              _ACS,
    "journal of medicinal chemistry":                   _ACS,
    "journal of proteome research":                     _ACS,
}


# ══════════════════════════════════════════════════════════════════════════════
# LAYER 2 — Publisher heuristics (45+ publishers, substring match, ordered)
# ══════════════════════════════════════════════════════════════════════════════
PUBLISHER_MAP: list[tuple[str, dict]] = [
    # ── Nature Portfolio / Springer Nature ─────────────────────────────────────
    ("nature portfolio",        {"system": "NPG / Snapp",        "url": "https://mts-nature.nature.com/"}),
    ("nature publishing",       {"system": "NPG / Snapp",        "url": "https://mts-nature.nature.com/"}),
    # Springer Nature non-Nature branded journals → ScholarOne or EM
    # (handled separately below after Nature check)
    # ── Wiley ──────────────────────────────────────────────────────────────────
    ("wiley",                   {"system": "ScholarOne",          "url": "https://mc.manuscriptcentral.com/"}),
    ("blackwell",               {"system": "ScholarOne",          "url": "https://mc.manuscriptcentral.com/"}),
    # ── Oxford / OUP ───────────────────────────────────────────────────────────
    ("oxford university press", {"system": "ScholarOne",          "url": "https://mc.manuscriptcentral.com/"}),
    ("oxford",                  {"system": "ScholarOne",          "url": "https://mc.manuscriptcentral.com/"}),
    # ── Taylor & Francis ───────────────────────────────────────────────────────
    ("taylor & francis",        {"system": "ScholarOne",          "url": "https://mc.manuscriptcentral.com/"}),
    ("taylor and francis",      {"system": "ScholarOne",          "url": "https://mc.manuscriptcentral.com/"}),
    ("informa",                 {"system": "ScholarOne",          "url": "https://mc.manuscriptcentral.com/"}),
    # ── Springer / BMC ─────────────────────────────────────────────────────────
    ("springer nature",         {"system": "Editorial Manager",   "url": "https://www.editorialmanager.com/"}),
    ("springer",                {"system": "Editorial Manager",   "url": "https://www.editorialmanager.com/"}),
    ("biomed central",          {"system": "Editorial Manager",   "url": "https://www.editorialmanager.com/"}),
    ("bmc",                     {"system": "Editorial Manager",   "url": "https://www.editorialmanager.com/"}),
    # ── Elsevier / Cell Press / Lancet ─────────────────────────────────────────
    ("elsevier",                {"system": "Editorial Manager",   "url": "https://www.editorialmanager.com/"}),
    ("cell press",              {"system": "Editorial Manager",   "url": "https://www.editorialmanager.com/"}),
    ("lancet",                  {"system": "Editorial Manager",   "url": "https://www.editorialmanager.com/"}),
    # ── PLOS ───────────────────────────────────────────────────────────────────
    ("public library of science", {"system": "Editorial Manager", "url": "https://www.editorialmanager.com/plosone"}),
    ("plos",                    {"system": "Editorial Manager",   "url": "https://www.editorialmanager.com/plosone"}),
    # ── Frontiers ──────────────────────────────────────────────────────────────
    ("frontiers media",         {"system": "Frontiers",           "url": "https://www.frontiersin.org/submission/"}),
    ("frontiers",               {"system": "Frontiers",           "url": "https://www.frontiersin.org/submission/"}),
    # ── American Chemical Society ───────────────────────────────────────────────
    ("american chemical society", {"system": "ACS Paragon Plus",  "url": "https://acsparagonplus.acs.org/"}),
    # ── AAAS / Science ─────────────────────────────────────────────────────────
    ("american association for the advancement of science",
                                {"system": "AAAS Submit",         "url": "https://submit.science.org/"}),
    # ── SAGE ───────────────────────────────────────────────────────────────────
    ("sage publications",       {"system": "ScholarOne",          "url": "https://mc.manuscriptcentral.com/"}),
    ("sage",                    {"system": "ScholarOne",          "url": "https://mc.manuscriptcentral.com/"}),
    # ── Cambridge ──────────────────────────────────────────────────────────────
    ("cambridge university press", {"system": "ScholarOne",       "url": "https://mc.manuscriptcentral.com/"}),
    ("cambridge",               {"system": "ScholarOne",          "url": "https://mc.manuscriptcentral.com/"}),
    # ── American Society for Microbiology ──────────────────────────────────────
    ("american society for microbiology", {"system": "eJournalPress", "url": "https://submit.asm.org/"}),
    # ── American Physiological Society ─────────────────────────────────────────
    ("american physiological society", {"system": "ScholarOne",   "url": "https://mc.manuscriptcentral.com/"}),
    # ── American Heart Association ──────────────────────────────────────────────
    ("american heart association", {"system": "ScholarOne",       "url": "https://mc.manuscriptcentral.com/"}),
    # ── American Society of Hematology ─────────────────────────────────────────
    ("american society of hematology", {"system": "ScholarOne",   "url": "https://mc.manuscriptcentral.com/"}),
    # ── American Diabetes Association ──────────────────────────────────────────
    ("american diabetes association", {"system": "ScholarOne",    "url": "https://mc.manuscriptcentral.com/"}),
    # ── American Society of Clinical Oncology ──────────────────────────────────
    ("american society of clinical oncology", {"system": "ScholarOne", "url": "https://mc.manuscriptcentral.com/"}),
    # ── Society for Neuroscience ────────────────────────────────────────────────
    ("society for neuroscience", {"system": "eNeuro Submit",      "url": "https://submit.eneuro.org/"}),
    # ── Rockefeller University Press ────────────────────────────────────────────
    ("rockefeller university press", {"system": "Bench>Press",    "url": "https://submit.rupress.org/"}),
    ("rockefeller",             {"system": "Bench>Press",         "url": "https://submit.rupress.org/"}),
    # ── MDPI ───────────────────────────────────────────────────────────────────
    ("mdpi",                    {"system": "MDPI Submission",      "url": "https://susy.mdpi.com/"}),
    # ── Karger ─────────────────────────────────────────────────────────────────
    ("karger",                  {"system": "Editorial Manager",   "url": "https://www.editorialmanager.com/"}),
    # ── Lippincott / Wolters Kluwer ────────────────────────────────────────────
    ("lippincott",              {"system": "Editorial Manager",   "url": "https://www.editorialmanager.com/"}),
    ("wolters kluwer",          {"system": "Editorial Manager",   "url": "https://www.editorialmanager.com/"}),
    # ── Thieme ─────────────────────────────────────────────────────────────────
    ("thieme",                  {"system": "Editorial Manager",   "url": "https://www.editorialmanager.com/"}),
    # ── Hindawi ────────────────────────────────────────────────────────────────
    ("hindawi",                 {"system": "Hindawi Online",       "url": "https://www.hindawi.com/journals/"}),
    # ── IOP Publishing ─────────────────────────────────────────────────────────
    ("iop publishing",          {"system": "IOP Publishing",      "url": "https://publishingsupport.iopscience.iop.org/"}),
    ("institute of physics",    {"system": "IOP Publishing",      "url": "https://publishingsupport.iopscience.iop.org/"}),
    # ── Royal Society ──────────────────────────────────────────────────────────
    ("royal society",           {"system": "ScholarOne",          "url": "https://mc.manuscriptcentral.com/"}),
    # ── EMBO ───────────────────────────────────────────────────────────────────
    ("embo press",              {"system": "Editorial Manager",   "url": "https://www.editorialmanager.com/"}),
    ("embo",                    {"system": "Editorial Manager",   "url": "https://www.editorialmanager.com/"}),
    # ── eLife Sciences ─────────────────────────────────────────────────────────
    ("elife sciences",          {"system": "eLife",               "url": "https://submit.elifesciences.org/"}),
    # ── PNAS / NAS ─────────────────────────────────────────────────────────────
    ("national academy of sciences", {"system": "PNAS Submit",   "url": "https://submit.pnas.org/"}),
    # ── BMJ Publishing ─────────────────────────────────────────────────────────
    ("bmj publishing",          {"system": "ScholarOne",          "url": "https://mc.manuscriptcentral.com/bmj"}),
    ("british medical journal", {"system": "ScholarOne",          "url": "https://mc.manuscriptcentral.com/bmj"}),
    # ── American Medical Association ───────────────────────────────────────────
    ("american medical association", {"system": "ScholarOne",     "url": "https://manuscript.jama.com/"}),
    # ── NLM / NIH (usually not directly submittable) ───────────────────────────
    ("national library of medicine", {"system": "unknown",        "url": ""}),
    ("national institutes of health", {"system": "unknown",       "url": ""}),
]

# ── System → default format hints ─────────────────────────────────────────────
SYSTEM_FORMAT_HINTS: dict[str, dict] = {
    "ScholarOne":        {"word_format": "DOCX or PDF", "figures": "TIFF/EPS 300dpi+", "cover_letter": True},
    "Editorial Manager": {"word_format": "DOCX",        "figures": "TIFF/EPS 300dpi+", "cover_letter": True},
    "NPG / Snapp":       {"word_format": "DOCX",        "figures": "PDF/EPS 300dpi",   "cover_letter": True},
    "Frontiers":         {"word_format": "DOCX",        "figures": "TIFF/JPEG 300dpi", "cover_letter": False},
    "MDPI Submission":   {"word_format": "DOCX",        "figures": "PNG/TIFF 300dpi",  "cover_letter": False},
    "ACS Paragon Plus":  {"word_format": "DOCX/LaTeX",  "figures": "TIFF/EPS 600dpi",  "cover_letter": True},
    "eJournalPress":     {"word_format": "DOCX",        "figures": "TIFF 300dpi",      "cover_letter": True},
    "eNeuro Submit":     {"word_format": "DOCX",        "figures": "TIFF/EPS 300dpi",  "cover_letter": True},
    "Bench>Press":       {"word_format": "DOCX",        "figures": "TIFF/EPS 300dpi",  "cover_letter": True},
    "Hindawi Online":    {"word_format": "DOCX",        "figures": "TIFF/PNG 300dpi",  "cover_letter": False},
    "IOP Publishing":    {"word_format": "DOCX/LaTeX",  "figures": "EPS/TIFF 300dpi",  "cover_letter": True},
    "AAAS Submit":       {"word_format": "DOCX",        "figures": "TIFF/EPS 300dpi",  "cover_letter": True},
    "PNAS Submit":       {"word_format": "DOCX/LaTeX",  "figures": "TIFF/EPS 600dpi",  "cover_letter": True},
    "eLife":             {"word_format": "DOCX",        "figures": "TIFF/EPS 300dpi",  "cover_letter": False},
    "unknown":           {"word_format": "check journal","figures": "check journal",   "cover_letter": None},
}


# ══════════════════════════════════════════════════════════════════════════════
# Detection helpers
# ══════════════════════════════════════════════════════════════════════════════

def slugify(title: str) -> str:
    s = title.lower()
    s = re.sub(r"[^a-z0-9]+", "_", s)
    return s.strip("_")[:80]


def _normalize_title(t: str) -> str:
    return t.lower().strip().rstrip(".")


def detect_by_title(title: str) -> dict | None:
    """Layer 1: exact title match against TITLE_OVERRIDES."""
    key = _normalize_title(title)
    return TITLE_OVERRIDES.get(key)


def detect_by_publisher(publisher: str) -> dict | None:
    """Layer 2: substring match against PUBLISHER_MAP."""
    p = publisher.lower()
    for keyword, info in PUBLISHER_MAP:
        if keyword in p:
            return {**info, "source": "publisher_map"}
    return None


# CrossRef cache (ISSN → publisher string from CrossRef)
_crossref_cache: dict[str, str] = {}


def _crossref_get(url: str) -> dict:
    req = urllib.request.Request(url, headers={"User-Agent": CROSSREF_UA})
    for attempt in range(MAX_RETRIES):
        try:
            with urllib.request.urlopen(req, timeout=15) as r:
                return json.loads(r.read())
        except urllib.error.HTTPError as e:
            if e.code == 404:
                return {}
            if attempt < MAX_RETRIES - 1:
                time.sleep(2 ** attempt)
            else:
                return {}
        except Exception:
            if attempt < MAX_RETRIES - 1:
                time.sleep(2 ** attempt)
            else:
                return {}
    return {}


def crossref_publisher(issns: list[str]) -> str:
    """Layer 3: Query CrossRef /journals/{issn} for publisher name."""
    for issn in issns:
        issn = issn.strip()
        if not issn:
            continue
        if issn in _crossref_cache:
            return _crossref_cache[issn]
        data = _crossref_get(f"https://api.crossref.org/journals/{issn}")
        pub = ""
        if data:
            pub = data.get("message", {}).get("publisher", "")
        _crossref_cache[issn] = pub
        time.sleep(CROSSREF_DELAY)
        if pub:
            return pub
    return ""


# ══════════════════════════════════════════════════════════════════════════════
# Main detection: 3 layers in order
# ══════════════════════════════════════════════════════════════════════════════

def detect_system(title: str, publisher: str, issns: list[str],
                  use_crossref: bool = True) -> dict:
    # Layer 1 — title override
    r = detect_by_title(title)
    if r:
        return r

    # Layer 2 — publisher heuristic
    r = detect_by_publisher(publisher)
    if r:
        return r

    # Layer 3 — CrossRef fallback
    if use_crossref and issns:
        cr_pub = crossref_publisher(issns)
        if cr_pub:
            r = detect_by_publisher(cr_pub)
            if r:
                return {**r, "source": "crossref", "crossref_publisher": cr_pub}

    return {"system": "unknown", "url": "", "source": "unknown"}


def build_record(journal: dict, use_crossref: bool = True) -> dict:
    sys_info = detect_system(
        journal.get("title", ""),
        journal.get("publisher", ""),
        journal.get("issn", []),
        use_crossref=use_crossref,
    )
    fmt = SYSTEM_FORMAT_HINTS.get(sys_info["system"], SYSTEM_FORMAT_HINTS["unknown"])
    rec = {
        "nlm_id":            journal["nlm_id"],
        "title":             journal["title"],
        "abbreviation":      journal["abbr"],
        "issn":              journal["issn"],
        "publisher":         journal["publisher"],
        "country":           journal["country"],
        "submission_system": sys_info["system"],
        "submission_url":    sys_info["url"],
        "detection_source":  sys_info["source"],
        "format_hints":      fmt,
        "schema_version":    "2.0",
    }
    if "crossref_publisher" in sys_info:
        rec["crossref_publisher"] = sys_info["crossref_publisher"]
    return rec


def main(in_path: Path, out_dir: Path, limit: int | None, use_crossref: bool):
    if not in_path.exists():
        print(f"ERROR: {in_path} not found.", file=sys.stderr)
        sys.exit(1)

    journals = json.loads(in_path.read_text(encoding="utf-8"))
    if limit:
        journals = journals[:limit]

    out_dir.mkdir(parents=True, exist_ok=True)

    stats = {"total": len(journals), "title_override": 0,
             "publisher_map": 0, "crossref": 0, "unknown": 0, "skipped": 0}
    index: list[dict] = []

    for i, j in enumerate(journals):
        if not j.get("title"):
            stats["skipped"] += 1
            continue
        rec = build_record(j, use_crossref=use_crossref)
        src = rec["detection_source"]
        if src == "title_override":
            stats["title_override"] += 1
        elif src == "publisher_map":
            stats["publisher_map"] += 1
        elif src == "crossref":
            stats["crossref"] += 1
        else:
            stats["unknown"] += 1

        slug = slugify(j["title"]) or f"nlm_{j['nlm_id']}"
        out_file = out_dir / f"{slug}.json"
        if out_file.exists():
            out_file = out_dir / f"{slug}_{j['nlm_id']}.json"
        out_file.write_text(json.dumps(rec, ensure_ascii=False, indent=2), encoding="utf-8")
        index.append({"slug": out_file.stem, "title": rec["title"],
                      "system": rec["submission_system"],
                      "issn": rec["issn"],
                      "detection_source": src})

        if (i + 1) % 500 == 0:
            print(f"  Progress: {i+1}/{len(journals)} ...", flush=True)

    index_path = out_dir / "_index.json"
    index_path.write_text(json.dumps(index, ensure_ascii=False, indent=2), encoding="utf-8")

    total_mapped = stats["title_override"] + stats["publisher_map"] + stats["crossref"]
    print(f"Built {stats['total']} journals → {out_dir}")
    print(f"  Title override : {stats['title_override']}")
    print(f"  Publisher map  : {stats['publisher_map']}")
    print(f"  CrossRef API   : {stats['crossref']}")
    print(f"  Unknown        : {stats['unknown']}")
    print(f"  Skipped        : {stats['skipped']}")
    print(f"  Total mapped   : {total_mapped} / {stats['total']} "
          f"({100*total_mapped//max(stats['total'],1)}%)")
    return stats["total"]


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--in",          dest="in_path",     default=str(DEFAULT_IN))
    ap.add_argument("--out-dir",     dest="out_dir",     default=str(DEFAULT_OUT))
    ap.add_argument("--limit",       type=int,           default=None)
    ap.add_argument("--no-crossref", dest="crossref",    action="store_false",
                    help="Skip CrossRef API fallback (faster, lower coverage)")
    ap.set_defaults(crossref=True)
    args = ap.parse_args()
    n = main(Path(args.in_path), Path(args.out_dir), args.limit, args.crossref)
    sys.exit(0 if n > 0 else 1)
