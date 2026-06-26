"""
mcp_server.py  v2.0
===================
TheraSIK Academic Writing Suite -- MCP Server

Exposes the writing suite as an MCP (Model Context Protocol) server so any
MCP-compatible LLM platform (Claude Code, Cursor, Codex, etc.) can call the
suite's tools directly.

Transport: stdio (default) or SSE (remote / browser clients):
  python scripts/mcp_server.py
  python scripts/mcp_server.py --transport sse --port 8765

License keys load from SKILL_DIR/.env via python-dotenv.
Use THERASIK_MCP_KEY=DEV / THERASIK_AGENT_KEY=DEV for local development.

────────────────────────────────────────────────────────────────────────────
TOOL INVENTORY  (22 tools total)
────────────────────────────────────────────────────────────────────────────
Manuscript workflow (4)
  create_manuscript_project   scaffold new project directory
  run_manuscript_workflow     run full QA + render pipeline
  get_manuscript_status       read current gate statuses
  run_qa_gate                 run single QA gate (incl. multi_expert)

Literature database (5)
  search_literature           FTS5 keyword OR TF-IDF similarity search
  add_paper_by_doi            CrossRef DOI → local DB
  add_paper_by_pmid           PubMed PMID → local DB
  get_paper                   retrieve paper by ID/DOI/PMID
  import_pdf_full_text        extract + store PDF full text

References (3)
  export_references           export in CSV / RIS / BibTeX / Zotero(CSL-JSON)
  verify_citations            check in-text ↔ reference list consistency
  format_citations            format a reference list in a given citation style

Journal requirements (2)
  get_journal_requirements    submission rules for a journal (10 452 journals)
  list_journals               browse journal database with filters

Submission preparation (4)
  check_submission_compliance compliance check vs journal rules
  prepare_submission_package  assemble complete submission package
  generate_cover_letter       generate journal cover letter
  get_submission_system_guide platform-specific submission instructions

Review & polish (2)
  polish_manuscript           AI-marker scan + LanguageTool grammar check
  run_multi_expert_review     three-role simulated peer review

Planning & figures (2)
  plan_manuscript             section scaffold + word budgets
  generate_stat_figure        publication-quality statistical figures

System (1)
  validate_skill_installation check skill installation integrity
────────────────────────────────────────────────────────────────────────────

CHANGELOG vs v1.x
-----------------
FIXED  get_journal_requirements  — index was a dict; now searches all 10 452
                                   journal files by title + slug matching
FIXED  list_journals             — was returning only 10 hardcoded entries;
                                   now streams from all 10 452 files
MERGED find_similar_papers       — merged into search_literature(mode=
                                   "similarity"); standalone tool removed
MERGED export_references_csv     — superseded by export_references(format=...)
ADDED  export_references         — unified export: csv / ris / bibtex / zotero
ADDED  verify_citations          — in-text ↔ reference list consistency check
ADDED  format_citations          — format refs in Vancouver/APA/Harvard/AMA style
ADDED  polish_manuscript         — expose insynbio_polishing scan + grammar
FIXED  run_qa_gate               — added multi_expert as valid gate
FIXED  generate_stat_figure      — graceful dependency error with install hint
FIXED  get_submission_system_guide — now reads from _platform_docs.json asset
"""

from __future__ import annotations

import json
import os
import re
import subprocess
import sys
import time
import urllib.request
import urllib.error
from pathlib import Path
from typing import Any

# ── Resolve skill root ────────────────────────────────────────────────────────
SKILL_DIR = Path(os.environ.get("THERASIK_DIR", Path(__file__).resolve().parents[1]))
sys.path.insert(0, str(SKILL_DIR / "scripts"))

try:
    from dotenv import load_dotenv
    load_dotenv(SKILL_DIR / ".env")
except ImportError:
    pass

try:
    import literature_db as litdb
except ImportError:
    litdb = None  # type: ignore

try:
    import csl_engine  # CSL (Citation Style Language) rendering, 10k+ styles
except ImportError:
    csl_engine = None  # type: ignore

try:
    from mcp.server.fastmcp import FastMCP
except ImportError:
    print(
        "ERROR: 'mcp' package not installed. Run:\n"
        "  pip install mcp\n",
        file=sys.stderr,
    )
    sys.exit(1)

# ── License configuration ─────────────────────────────────────────────────────
MCP_KEY   = os.environ.get("THERASIK_MCP_KEY", "")
AGENT_KEY = os.environ.get("THERASIK_AGENT_KEY", "")
LICENSE_API = os.environ.get("THERASIK_LICENSE_API", "https://api.therasik.io")
_LICENSE_CACHE: dict = {}
_LICENSE_CACHE_TTL  = 3600 * 6
_LICENSE_GRACE_SECS = 3600 * 24 * 7


def _validate_license() -> dict:
    now = time.time()
    cached = _LICENSE_CACHE.get("result")
    cached_at = _LICENSE_CACHE.get("at", 0)
    if cached and (now - cached_at) < _LICENSE_CACHE_TTL:
        return cached
    if MCP_KEY == "DEV" and AGENT_KEY == "DEV":
        result = {"valid": True, "plan": "dev", "agent_quota_remaining": 999999}
        _LICENSE_CACHE.update({"result": result, "at": now})
        return result
    if not MCP_KEY or not AGENT_KEY:
        print(
            "\nERROR: License keys not set.\n"
            "Add to .env: THERASIK_MCP_KEY=THERASIK-MCP-XXXXX\n"
            "             THERASIK_AGENT_KEY=THERASIK-AGT-XXXXX\n",
            file=sys.stderr,
        )
        sys.exit(1)
    try:
        body = json.dumps({"mcp_key": MCP_KEY, "agent_key": AGENT_KEY}).encode()
        req = urllib.request.Request(
            f"{LICENSE_API}/validate", data=body, method="POST",
            headers={"Content-Type": "application/json",
                     "User-Agent": "therasik-mcp/2.0"},
        )
        with urllib.request.urlopen(req, timeout=8) as resp:
            result = json.loads(resp.read())
            _LICENSE_CACHE.update({"result": result, "at": now,
                                   "offline_since": None})
            return result
    except urllib.error.HTTPError as e:
        error = json.loads(e.read())
        reason = error.get("detail", {})
        msg = reason.get("message", "License validation failed") \
            if isinstance(reason, dict) else str(reason)
        print(f"\nERROR: {msg}\n", file=sys.stderr)
        sys.exit(1)
    except Exception:
        offline_since = _LICENSE_CACHE.get("offline_since") or now
        _LICENSE_CACHE["offline_since"] = offline_since
        if cached and (now - offline_since) < _LICENSE_GRACE_SECS:
            hrs = int((_LICENSE_GRACE_SECS - (now - offline_since)) / 3600)
            print(f"[TheraSIK] License offline. Grace: {hrs}h remaining.",
                  file=sys.stderr)
            return cached
        print("\nERROR: License server unreachable and grace period expired.\n",
              file=sys.stderr)
        sys.exit(1)


def _consume(operation: str = "api_call", units: int = 1) -> None:
    try:
        body = json.dumps({
            "mcp_key": MCP_KEY, "agent_key": AGENT_KEY,
            "units": units, "operation": operation,
        }).encode()
        req = urllib.request.Request(
            f"{LICENSE_API}/consume", data=body, method="POST",
            headers={"Content-Type": "application/json"},
        )
        urllib.request.urlopen(req, timeout=5)
    except Exception:
        pass


def _proxy_fetch(endpoint: str, payload: dict) -> dict | None:
    if MCP_KEY == "DEV" and AGENT_KEY == "DEV":
        return None
    if not MCP_KEY or not AGENT_KEY:
        return None
    try:
        body = json.dumps(payload).encode()
        req = urllib.request.Request(
            f"{LICENSE_API}/{endpoint}", data=body, method="POST",
            headers={"Content-Type": "application/json",
                     "User-Agent": "therasik-mcp/2.0"},
        )
        with urllib.request.urlopen(req, timeout=30) as resp:
            return json.loads(resp.read())
    except urllib.error.HTTPError as e:
        if e.code == 429:
            try:
                detail = json.loads(e.read()).get("detail", {})
                retry = detail.get("retry_after_seconds", 2)
            except Exception:
                retry = 2
            raise RuntimeError(
                f"Rate limit exceeded. Retry in {retry}s."
            )
        return None
    except Exception:
        return None


# ── Validate license on startup ───────────────────────────────────────────────
_license_info = _validate_license()


def _parse_server_args():
    import argparse
    parser = argparse.ArgumentParser(add_help=False)
    parser.add_argument("--transport", choices=("stdio", "sse"), default="stdio")
    parser.add_argument("--host", default="127.0.0.1")
    parser.add_argument("--port", type=int, default=8765)
    return parser.parse_known_args()[0]


_SERVER_ARGS = _parse_server_args()

# ── Server init ───────────────────────────────────────────────────────────────
mcp = FastMCP(
    "therasik-academic-writing-suite",
    host=_SERVER_ARGS.host,
    port=_SERVER_ARGS.port,
)

DEFAULT_DB    = SKILL_DIR / "assets" / "literature_db" / "literature.db"
JOURNAL_DIR   = SKILL_DIR / "assets" / "journal_requirements"
SCRIPTS_DIR   = SKILL_DIR / "scripts"
TEMPLATE_DIR  = SKILL_DIR / "assets" / "project-template"
PLATFORM_DOCS = JOURNAL_DIR / "_platform_docs.json"


# ── Helpers ───────────────────────────────────────────────────────────────────

def _run_py(script: str, args: list[str], cwd: Path | None = None) -> dict:
    cmd = [sys.executable, str(SCRIPTS_DIR / script)] + args
    result = subprocess.run(
        cmd, capture_output=True, text=True,
        cwd=str(cwd or SKILL_DIR),
    )
    return {
        "returncode": result.returncode,
        "stdout": result.stdout.strip(),
        "stderr": result.stderr.strip(),
        "success": result.returncode == 0,
    }


def _get_db(db_path: str | None = None) -> Any:
    if litdb is None:
        raise RuntimeError("literature_db module not available")
    path = Path(db_path) if db_path else DEFAULT_DB
    return litdb.get_db(path)


def _slugify(name: str) -> str:
    """Convert journal name to likely filename slug."""
    s = name.lower()
    s = re.sub(r"[^a-z0-9]+", "_", s)
    return s.strip("_")


def _search_journal_files(name_lower: str, limit: int = 5) -> list[dict]:
    """
    Search 10 452 journal files by title/slug.
    Exact match first, then substring, then publisher_map detection.
    """
    if not JOURNAL_DIR.exists():
        return []

    candidates: list[tuple[int, Path]] = []
    slug = _slugify(name_lower)

    for p in JOURNAL_DIR.glob("*.json"):
        stem = p.stem
        if stem.startswith("_"):
            continue
        score = 0
        if stem == slug:
            score = 100
        elif name_lower in stem.replace("_", " "):
            score = 50
        elif slug in stem:
            score = 30
        if score:
            candidates.append((score, p))

    candidates.sort(key=lambda x: -x[0])
    results = []
    for _, p in candidates[:limit]:
        try:
            data = json.loads(p.read_text(encoding="utf-8"))
            data["_file"] = p.name
            results.append(data)
        except Exception:
            pass
    return results


# ── Manuscript workflow tools ─────────────────────────────────────────────────

@mcp.tool()
def create_manuscript_project(
    project_dir: str,
    project_name: str = "New Manuscript",
    authors: str = "",
    journal_target: str = "",
) -> dict:
    """
    Scaffold a new manuscript project directory from the TheraSIK template.

    Args:
        project_dir:   Absolute or relative path where the project will be created.
        project_name:  Human-readable project name.
        authors:       Comma-separated author list (optional).
        journal_target: Target journal name (optional).

    Returns:
        dict with 'success', 'project_dir', 'message', or 'error'.
    """
    import shutil
    proj = Path(project_dir).resolve()
    if proj.exists() and any(proj.iterdir()):
        return {"success": False,
                "error": f"Directory {proj} already exists and is not empty"}
    try:
        shutil.copytree(str(TEMPLATE_DIR), str(proj), dirs_exist_ok=True)
    except Exception as exc:
        return {"success": False, "error": str(exc)}

    config_path = proj / "project_config.json"
    if config_path.exists():
        try:
            cfg = json.loads(config_path.read_text(encoding="utf-8"))
            cfg["project_name"] = project_name
            if authors:
                cfg["authors"] = [a.strip() for a in authors.split(",")]
            if journal_target:
                cfg["journal_target"] = journal_target
            config_path.write_text(
                json.dumps(cfg, indent=2, ensure_ascii=False), encoding="utf-8"
            )
        except Exception:
            pass

    return {
        "success": True,
        "project_dir": str(proj),
        "message": f"Project '{project_name}' created at {proj}",
    }


@mcp.tool()
def run_manuscript_workflow(
    project_dir: str,
    skip_qa_scripts: bool = False,
    render_outputs: bool = True,
) -> dict:
    """
    Run the full manuscript QA and rendering workflow for a project.

    Executes all configured steps: check_path, command, qa_script, render_outputs.
    Writes workflow_execution_audit_vN.json in the project directory.

    Args:
        project_dir:    Path to the manuscript project directory.
        skip_qa_scripts: Skip QA script execution (framework test mode).
        render_outputs: If False, skip document rendering steps.

    Returns:
        dict with 'success', 'gate_summary', 'audit_file', 'stdout', 'stderr'.
    """
    proj = Path(project_dir).resolve()
    config_path = (proj if proj.name == "project_config.json"
                   else proj / "project_config.json")
    if not config_path.exists():
        return {"success": False,
                "error": f"project_config.json not found: {config_path}"}

    args = [str(config_path)]
    if skip_qa_scripts:
        args.append("--skip-qa-scripts")

    result = _run_py("run_full_workflow.py", args)
    gate_summary: dict = {}
    try:
        if result["stdout"]:
            gate_summary = json.loads(result["stdout"])
    except Exception:
        pass

    return {
        "success": result["returncode"] == 0,
        "gate_summary": gate_summary,
        "stdout": result["stdout"],
        "stderr": result["stderr"],
    }


@mcp.tool()
def get_manuscript_status(project_dir: str) -> dict:
    """
    Read the current QA gate statuses for a manuscript project.

    Scans the 03_QA directory for QA markdown files and returns
    the Status line from each.

    Args:
        project_dir: Path to the manuscript project directory.

    Returns:
        dict with 'gates' (gate name → status), 'summary', 'all_pass'.
    """
    proj = Path(project_dir).resolve()
    qa_dir = proj / "03_QA"
    if not qa_dir.exists():
        return {"gates": {}, "summary": "No 03_QA directory found",
                "all_pass": False}

    gates: dict[str, str] = {}
    for md_file in sorted(qa_dir.glob("*.md")):
        status = "UNKNOWN"
        try:
            for line in md_file.read_text(
                    encoding="utf-8", errors="ignore").splitlines()[:40]:
                stripped = line.strip()
                if stripped.lower().startswith("status:"):
                    raw = stripped.split(":", 1)[1].strip()
                    status = raw.split()[0].upper() if raw.split() else "UNKNOWN"
                    break
        except Exception:
            status = "READ_ERROR"
        gates[md_file.stem] = status

    total   = len(gates)
    passing = sum(1 for s in gates.values() if s == "PASS")
    failing = sum(1 for s in gates.values() if s == "FAIL")
    pending = sum(1 for s in gates.values() if s == "PENDING")

    return {
        "gates":   gates,
        "summary": f"{passing}/{total} PASS, {failing} FAIL, {pending} PENDING",
        "all_pass": failing == 0 and total > 0,
    }


@mcp.tool()
def run_qa_gate(
    project_dir: str,
    gate: str,
    verify_doi: bool = False,
    reviewers: list[str] | None = None,
) -> dict:
    """
    Run a single QA gate script for a manuscript project.

    Available gates:
      reference_claim  — reference completeness and claim support
      ai_style         — AI-style / human-voice detection
      paragraph        — paragraph structure and coherence
      figure_contract  — figure contract completeness
      multi_expert     — six-role simulated peer review
                         (statistician, domain, editor,
                          ai_diagnostician, citation_auditor, reproducibility)

    Args:
        project_dir: Path to the manuscript project directory.
        gate:        One of the gates listed above.
        verify_doi:  For reference_claim only — verify DOIs via CrossRef.
        reviewers:   For multi_expert only — subset of roles to run
                     (default: all six).

    Returns:
        dict with 'success', 'status' (PASS/FAIL/WARN), 'output_file', 'stdout'.
    """
    if gate == "multi_expert":
        return run_multi_expert_review(project_dir, reviewers=reviewers)

    gate_map = {
        "reference_claim": ("run_reference_claim_qa.py",
                            "reference_claim_support_QA.md"),
        "ai_style":        ("run_ai_style_qa.py",
                            "ai_style_human_voice_QA.md"),
        "paragraph":       ("run_paragraph_structure_qa.py",
                            "paragraph_structure_QA.md"),
        "figure_contract": ("run_figure_contract_qa.py",
                            "figure_contract_QA.md"),
    }

    if gate not in gate_map:
        return {
            "success": False,
            "error": (f"Unknown gate '{gate}'. "
                      f"Valid: {list(gate_map.keys()) + ['multi_expert']}"),
        }

    script, output_name = gate_map[gate]
    args = ["--project-root", project_dir]
    if gate == "reference_claim" and verify_doi:
        args.append("--verify-doi")

    result = _run_py(f"qa/{script}", args)

    output_path = Path(project_dir) / "03_QA" / output_name
    status = "UNKNOWN"
    if output_path.exists():
        for line in output_path.read_text(
                encoding="utf-8", errors="ignore").splitlines()[:10]:
            if line.strip().lower().startswith("status:"):
                raw = line.strip().split(":", 1)[1].strip()
                status = raw.split()[0].upper() if raw.split() else "UNKNOWN"
                break

    return {
        "success": result["returncode"] == 0,
        "status":  status,
        "output_file": str(output_path),
        "stdout": result["stdout"],
        "stderr": result["stderr"],
    }


# ── Literature database tools ─────────────────────────────────────────────────

@mcp.tool()
def search_literature(
    query: str,
    mode: str = "keyword",
    limit: int = 10,
    year_from: int | None = None,
    year_to: int | None = None,
    journal: str | None = None,
    db_path: str | None = None,
) -> dict:
    """
    Search the local literature database.

    Two search modes:
      keyword    — FTS5 full-text search (fast, supports Boolean operators:
                   "antibody AND complement", "CAR-T OR NK cell")
      similarity — TF-IDF cosine (60%) + BM25 (40%) ranking; best for
                   finding papers similar to a paragraph or abstract fragment

    Args:
        query:     Search query or reference text fragment.
        mode:      'keyword' (default) or 'similarity'.
        limit:     Maximum results to return (default 10).
        year_from: Filter papers published >= this year.
        year_to:   Filter papers published <= this year.
        journal:   Filter by journal name substring (case-insensitive).
        db_path:   Override default database path.

    Returns:
        dict with 'results' list, 'total', 'mode'.
    """
    if litdb is None:
        return {"error": "literature_db not available", "results": []}

    try:
        conn = _get_db(db_path)

        if mode == "similarity":
            try:
                import similar_search as simsearch
                results = simsearch.find_similar_papers(
                    query, db_path=db_path,
                    top_k=min(int(limit), 50),
                    year_from=year_from,
                    year_to=year_to,
                    journal_filter=journal,
                )
                return {"results": results, "total": len(results),
                        "mode": "similarity"}
            except ImportError:
                return {"error": "similar_search module not available",
                        "results": []}
            except Exception as exc:
                return {"error": str(exc), "results": []}

        results = litdb.search(conn, query, limit=limit,
                               year_from=year_from, year_to=year_to,
                               journal=journal)
        for r in results:
            if isinstance(r.get("authors"), str):
                try:
                    r["authors"] = json.loads(r["authors"])
                except Exception:
                    pass
        return {"results": results, "total": len(results), "mode": "keyword"}

    except Exception as exc:
        return {"error": str(exc), "results": []}


@mcp.tool()
def add_paper_by_doi(doi: str, db_path: str | None = None) -> dict:
    """
    Fetch paper metadata from CrossRef by DOI and store in the local database.

    Routes via TheraSIK cloud proxy first (rate-limited, shared cache).
    Falls back to direct CrossRef API in DEV mode or if proxy unavailable.

    Args:
        doi:     DOI string, with or without 'https://doi.org/' prefix.
        db_path: Override default database path.

    Returns:
        dict with 'paper_id', 'is_new', 'title', 'year', 'journal', 'doi',
        or 'error'.
    """
    if litdb is None:
        return {"error": "literature_db not available"}
    try:
        meta = _proxy_fetch("proxy/crossref",
                            {"mcp_key": MCP_KEY, "agent_key": AGENT_KEY,
                             "doi": doi})
        if meta is None:
            meta = litdb.fetch_crossref(doi)
        if "error" in meta:
            return {"error": meta["error"]}
        meta["source"] = "crossref"
        conn = _get_db(db_path)
        paper_id, is_new = litdb.add_paper(conn, meta)
        litdb._rebuild_tfidf(conn)
        _consume("add_paper_doi", units=1)
        return {
            "paper_id": paper_id,
            "is_new":   is_new,
            "title":    meta.get("title"),
            "year":     meta.get("year"),
            "journal":  meta.get("journal"),
            "doi":      meta.get("doi"),
        }
    except RuntimeError as exc:
        return {"error": str(exc)}
    except Exception as exc:
        return {"error": str(exc)}


@mcp.tool()
def add_paper_by_pmid(pmid: str, db_path: str | None = None) -> dict:
    """
    Fetch paper metadata from PubMed by PMID and store in the local database.

    Routes via TheraSIK cloud proxy first.
    Falls back to direct PubMed E-utilities in DEV mode or if proxy unavailable.

    Args:
        pmid:    PubMed ID as a string (e.g. "34912118").
        db_path: Override default database path.

    Returns:
        dict with 'paper_id', 'is_new', 'title', 'year', 'journal', 'pmid',
        'doi', or 'error'.
    """
    if litdb is None:
        return {"error": "literature_db not available"}
    try:
        meta = _proxy_fetch("proxy/pubmed",
                            {"mcp_key": MCP_KEY, "agent_key": AGENT_KEY,
                             "pmid": pmid})
        if meta is None:
            meta = litdb.fetch_pubmed(pmid)
        if "error" in meta:
            return {"error": meta["error"]}
        meta["source"] = "pubmed"
        conn = _get_db(db_path)
        paper_id, is_new = litdb.add_paper(conn, meta)
        litdb._rebuild_tfidf(conn)
        _consume("add_paper_pmid", units=1)
        return {
            "paper_id": paper_id,
            "is_new":   is_new,
            "title":    meta.get("title"),
            "year":     meta.get("year"),
            "journal":  meta.get("journal"),
            "pmid":     meta.get("pmid"),
            "doi":      meta.get("doi"),
        }
    except RuntimeError as exc:
        return {"error": str(exc)}
    except Exception as exc:
        return {"error": str(exc)}


@mcp.tool()
def get_paper(identifier: str, db_path: str | None = None) -> dict:
    """
    Retrieve a paper from the local database by paper_id, DOI, or PMID.

    Args:
        identifier: paper_id (hex string), DOI, or PMID.
        db_path:    Override default database path.

    Returns:
        Full paper record dict, or error if not found.
    """
    if litdb is None:
        return {"error": "literature_db not available"}
    _lic = _validate_license()
    if not _lic.get("valid"):
        return {"error": "License validation failed", "detail": _lic}
    try:
        conn  = _get_db(db_path)
        paper = litdb.get_paper(conn, identifier)
        if paper is None:
            return {"error": f"Paper not found: {identifier}"}
        return paper
    except Exception as exc:
        return {"error": str(exc)}


@mcp.tool()
def import_pdf_full_text(
    pdf_path: str,
    paper_id: str,
    db_path: str | None = None,
) -> dict:
    """
    Extract full text from a PDF and store it in the literature database.

    Attaches the extracted text to an existing paper record so it becomes
    searchable via search_literature.

    Args:
        pdf_path: Absolute path to the PDF file.
        paper_id: Existing paper_id to attach text to.
        db_path:  Override default database path.

    Returns:
        dict with success (bool), word_count, or error.
    """
    if litdb is None:
        return {"error": "literature_db not available"}
    _lic = _validate_license()
    if not _lic.get("valid"):
        return {"error": "License validation failed", "detail": _lic}
    try:
        conn   = _get_db(db_path)
        result = litdb.import_pdf(conn, pdf_path, paper_id)
        litdb._rebuild_tfidf(conn)
        return result
    except Exception as exc:
        return {"error": str(exc)}


# ── References tools ──────────────────────────────────────────────────────────

@mcp.tool()
def export_references(
    format: str = "ris",
    query: str | None = None,
    paper_ids: list[str] | None = None,
    output_path: str | None = None,
    db_path: str | None = None,
) -> dict:
    """
    Export paper references in standard formats for use in reference managers.

    Supported formats:
      ris     — RIS format (Endnote, Mendeley, Zotero, RefWorks, Papers)
      bibtex  — BibTeX format (LaTeX, Overleaf, JabRef)
      zotero  — CSL-JSON format (native Zotero import format)
      csv     — CSV spreadsheet (Excel, Sheets, custom pipelines)

    Zotero import: File → Import → RIS or CSL-JSON.
    Mendeley / Endnote: File → Import → RIS.
    Overleaf / LaTeX: upload .bib file as bibliography resource.

    Args:
        format:      Output format: 'ris' | 'bibtex' | 'zotero' | 'csv'
                     (default: 'ris').
        query:       Optional search query to filter papers.
        paper_ids:   Optional explicit list of paper_ids to export.
        output_path: Path to write output file. If omitted, returns content
                     as a string in the response.
        db_path:     Override default database path.

    Returns:
        dict with 'format', 'count', 'output_path' or 'content', or 'error'.
    """
    if litdb is None:
        return {"error": "literature_db not available"}
    _lic = _validate_license()
    if not _lic.get("valid"):
        return {"error": "License validation failed", "detail": _lic}

    fmt = format.lower().strip()
    if fmt not in ("ris", "bibtex", "zotero", "csv"):
        return {"error": f"Unknown format '{fmt}'. Use: ris, bibtex, zotero, csv"}

    try:
        conn = _get_db(db_path)

        # Gather papers
        if paper_ids:
            papers = [litdb.get_paper(conn, pid) for pid in paper_ids]
            papers = [p for p in papers if p]
        elif query:
            papers = litdb.search(conn, query, limit=500)
        else:
            papers = litdb.search(conn, "", limit=500)

        for p in papers:
            if isinstance(p.get("authors"), str):
                try:
                    p["authors"] = json.loads(p["authors"])
                except Exception:
                    pass

        if fmt == "csv":
            result = litdb.export_csv(conn, query=query,
                                      paper_ids=paper_ids,
                                      output_path=output_path)
            result["format"] = "csv"
            return result

        if fmt == "ris":
            content = _papers_to_ris(papers)
            ext = ".ris"
        elif fmt == "bibtex":
            content = _papers_to_bibtex(papers)
            ext = ".bib"
        else:  # zotero / CSL-JSON
            content = _papers_to_csl_json(papers)
            ext = ".json"

        if output_path:
            out = Path(output_path)
            if not out.suffix:
                out = out.with_suffix(ext)
            out.parent.mkdir(parents=True, exist_ok=True)
            out.write_text(content, encoding="utf-8")
            return {"format": fmt, "count": len(papers),
                    "output_path": str(out)}
        else:
            return {"format": fmt, "count": len(papers),
                    "content": content[:8000],
                    "truncated": len(content) > 8000}

    except Exception as exc:
        return {"error": str(exc)}


def _ris_escape(s: str) -> str:
    return (s or "").replace("\n", " ").replace("\r", "").strip()


def _papers_to_ris(papers: list[dict]) -> str:
    lines: list[str] = []
    for p in papers:
        authors = p.get("authors") or []
        if isinstance(authors, str):
            try:
                authors = json.loads(authors)
            except Exception:
                authors = [authors]
        lines.append("TY  - JOUR")
        lines.append(f"TI  - {_ris_escape(p.get('title', ''))}")
        for a in authors:
            lines.append(f"AU  - {_ris_escape(str(a))}")
        if p.get("year"):
            lines.append(f"PY  - {p['year']}")
        if p.get("journal"):
            lines.append(f"JO  - {_ris_escape(p['journal'])}")
        if p.get("volume"):
            lines.append(f"VL  - {p['volume']}")
        if p.get("issue"):
            lines.append(f"IS  - {p['issue']}")
        if p.get("pages"):
            lines.append(f"SP  - {_ris_escape(str(p['pages']))}")
        if p.get("doi"):
            lines.append(f"DO  - {p['doi']}")
        if p.get("pmid"):
            lines.append(f"AN  - {p['pmid']}")
        if p.get("abstract"):
            lines.append(f"AB  - {_ris_escape(p['abstract'][:1000])}")
        if p.get("keywords"):
            kws = p["keywords"]
            if isinstance(kws, str):
                kws = [kws]
            for kw in kws:
                lines.append(f"KW  - {_ris_escape(str(kw))}")
        lines.append("ER  - ")
        lines.append("")
    return "\n".join(lines)


def _bibtex_key(p: dict, idx: int) -> str:
    authors = p.get("authors") or []
    if isinstance(authors, str):
        try:
            authors = json.loads(authors)
        except Exception:
            authors = [authors]
    last = ""
    if authors:
        first_author = str(authors[0])
        last = first_author.split(",")[0].split()[-1] if first_author else ""
    year = p.get("year", "")
    title_words = (p.get("title") or "").split()
    tw = title_words[0].lower() if title_words else f"ref{idx}"
    tw = re.sub(r"[^a-z]", "", tw)
    key = f"{last.lower()}{year}{tw}" if last else f"ref{idx}{year}"
    return re.sub(r"[^a-z0-9]", "", key) or f"ref{idx}"


def _bibtex_escape(s: str) -> str:
    return (s or "").replace("{", "{{").replace("}", "}}").replace("\n", " ").strip()


def _papers_to_bibtex(papers: list[dict]) -> str:
    lines: list[str] = []
    for i, p in enumerate(papers):
        key = _bibtex_key(p, i)
        authors = p.get("authors") or []
        if isinstance(authors, str):
            try:
                authors = json.loads(authors)
            except Exception:
                authors = [authors]
        author_str = " and ".join(str(a) for a in authors)
        lines.append(f"@article{{{key},")
        if p.get("title"):
            lines.append(f"  title = {{{_bibtex_escape(p['title'])}}},")
        if author_str:
            lines.append(f"  author = {{{_bibtex_escape(author_str)}}},")
        if p.get("journal"):
            lines.append(f"  journal = {{{_bibtex_escape(p['journal'])}}},")
        if p.get("year"):
            lines.append(f"  year = {{{p['year']}}},")
        if p.get("volume"):
            lines.append(f"  volume = {{{p['volume']}}},")
        if p.get("issue"):
            lines.append(f"  number = {{{p['issue']}}},")
        if p.get("pages"):
            lines.append(f"  pages = {{{p['pages']}}},")
        if p.get("doi"):
            lines.append(f"  doi = {{{p['doi']}}},")
        if p.get("pmid"):
            lines.append(f"  note = {{PMID: {p['pmid']}}},")
        lines.append("}")
        lines.append("")
    return "\n".join(lines)


def _papers_to_csl_json(papers: list[dict]) -> str:
    """CSL-JSON: native Zotero import format."""
    items: list[dict] = []
    for p in papers:
        authors = p.get("authors") or []
        if isinstance(authors, str):
            try:
                authors = json.loads(authors)
            except Exception:
                authors = [authors]

        csl_authors: list[dict] = []
        for a in authors:
            name = str(a)
            if "," in name:
                parts = name.split(",", 1)
                csl_authors.append({"family": parts[0].strip(),
                                    "given": parts[1].strip()})
            else:
                csl_authors.append({"literal": name})

        item: dict = {
            "type": "article-journal",
            "id":   p.get("paper_id") or p.get("doi") or p.get("pmid") or "",
        }
        if p.get("title"):
            item["title"] = p["title"]
        if csl_authors:
            item["author"] = csl_authors
        if p.get("journal"):
            item["container-title"] = p["journal"]
        if p.get("year"):
            item["issued"] = {"date-parts": [[int(p["year"])]]}
        if p.get("volume"):
            item["volume"] = str(p["volume"])
        if p.get("issue"):
            item["issue"] = str(p["issue"])
        if p.get("pages"):
            item["page"] = str(p["pages"])
        if p.get("doi"):
            item["DOI"] = p["doi"]
        if p.get("pmid"):
            item["PMID"] = str(p["pmid"])
        if p.get("abstract"):
            item["abstract"] = p["abstract"]
        if p.get("keywords"):
            kws = p["keywords"]
            if isinstance(kws, str):
                try:
                    kws = json.loads(kws)
                except Exception:
                    kws = [kws]
            item["keyword"] = ", ".join(str(k) for k in kws)
        items.append(item)
    return json.dumps(items, indent=2, ensure_ascii=False)


@mcp.tool()
def verify_citations(
    project_dir: str,
    manuscript_file: str = "02_manuscript/manuscript.md",
    references_file: str | None = None,
    db_path: str | None = None,
) -> dict:
    """
    Check in-text citation ↔ reference list consistency for a manuscript.

    Detects:
      - Dangling citations: numbers cited in-text but missing from reference list
      - Orphan references: entries in reference list never cited in text
      - Duplicate reference entries
      - Non-sequential citation numbering gaps

    Optionally cross-checks against the local literature DB to compute
    keyword overlap between in-text context and the paper's abstract.

    Args:
        project_dir:     Path to the manuscript project directory.
        manuscript_file: Relative path to manuscript within project_dir
                         (default: 02_manuscript/manuscript.md).
        references_file: Override path to references section (MD or TXT).
                         If None, references are auto-detected at end of
                         manuscript_file.
        db_path:         Override literature database path.

    Returns:
        dict with 'status' (PASS/WARN/FAIL), 'dangling', 'orphans',
        'duplicates', 'max_cited', 'ref_count', 'issues'.
    """
    _lic = _validate_license()
    if not _lic.get("valid"):
        return {"error": "License validation failed", "detail": _lic}

    proj = Path(project_dir).resolve()
    ms_path = proj / manuscript_file
    if not ms_path.exists():
        return {"error": f"Manuscript file not found: {ms_path}"}

    text = ms_path.read_text(encoding="utf-8", errors="ignore")

    # Split body vs references section
    ref_section_markers = [
        r"^#+\s*[Rr]eferences?\s*$",
        r"^#+\s*[Bb]ibliography\s*$",
        r"^#+\s*[Ww]orks\s+[Cc]ited\s*$",
    ]
    body = text
    ref_block = ""
    for marker in ref_section_markers:
        m = re.search(marker, text, re.MULTILINE)
        if m:
            body     = text[:m.start()]
            ref_block = text[m.start():]
            break

    if references_file:
        rp = Path(references_file)
        if not rp.is_absolute():
            rp = proj / references_file
        if rp.exists():
            ref_block = rp.read_text(encoding="utf-8", errors="ignore")

    # Extract cited numbers from body  [1], [1,2], [1-3], (1), (1,2)
    cited_nums: set[int] = set()
    for m in re.finditer(r"[\[(](\d[\d,;\s\-–]+?)[\])]", body):
        raw = m.group(1)
        for part in re.split(r"[,;\s]+", raw):
            if "–" in part or "-" in part:
                parts = re.split(r"[–\-]", part)
                try:
                    lo, hi = int(parts[0]), int(parts[-1])
                    cited_nums.update(range(lo, hi + 1))
                except ValueError:
                    pass
            else:
                try:
                    cited_nums.add(int(part.strip()))
                except ValueError:
                    pass

    # Extract reference entries from ref_block
    # Patterns: "1. Author..." or "[1] Author..." or "1) Author..."
    ref_entries: dict[int, str] = {}
    for m in re.finditer(
            r"^\s*[\[\(]?(\d+)[\]\).]?\s+(.+)", ref_block, re.MULTILINE):
        try:
            num  = int(m.group(1))
            text_snippet = m.group(2)[:120]
            ref_entries[num] = text_snippet
        except ValueError:
            pass

    # Checks
    ref_nums = set(ref_entries.keys())
    max_cited = max(cited_nums) if cited_nums else 0
    dangling  = sorted(cited_nums - ref_nums)   # cited but no entry
    orphans   = sorted(ref_nums - cited_nums)   # entry but never cited

    # Duplicates in ref block (same number listed twice)
    raw_nums: list[int] = []
    for m in re.finditer(r"^\s*[\[\(]?(\d+)[\]\).]?\s", ref_block, re.MULTILINE):
        try:
            raw_nums.append(int(m.group(1)))
        except ValueError:
            pass
    duplicates = sorted({n for n in raw_nums if raw_nums.count(n) > 1})

    # Numbering gaps
    if ref_nums:
        expected = set(range(1, max(ref_nums) + 1))
        gaps = sorted(expected - ref_nums)
    else:
        gaps = []

    issues: list[str] = []
    if dangling:
        issues.append(f"Dangling citations (cited but missing from list): {dangling}")
    if orphans:
        issues.append(f"Orphan references (in list but never cited): {orphans}")
    if duplicates:
        issues.append(f"Duplicate reference numbers: {duplicates}")
    if gaps:
        issues.append(f"Numbering gaps in reference list: {gaps}")

    if dangling or duplicates:
        status = "FAIL"
    elif orphans or gaps:
        status = "WARN"
    else:
        status = "PASS"

    # Write QA report
    qa_dir = proj / "03_QA"
    qa_dir.mkdir(parents=True, exist_ok=True)
    qa_file = qa_dir / "citation_verification_QA.md"
    qa_content = [
        "# Citation Verification QA",
        f"Status: {status}",
        f"Manuscript: {ms_path}",
        "",
        f"## Summary",
        f"- Total in-text citation numbers found: {len(cited_nums)}",
        f"- Total reference list entries found: {len(ref_nums)}",
        f"- Max cited number: {max_cited}",
        "",
        "## Issues",
    ]
    if issues:
        for iss in issues:
            qa_content.append(f"- {iss}")
    else:
        qa_content.append("- None. All citations consistent.")

    if ref_entries:
        qa_content.append("\n## Reference Entries Detected")
        for num in sorted(ref_entries)[:10]:
            qa_content.append(f"  [{num}] {ref_entries[num]}...")
        if len(ref_entries) > 10:
            qa_content.append(f"  ... ({len(ref_entries) - 10} more)")

    qa_file.write_text("\n".join(qa_content), encoding="utf-8")

    return {
        "status":     status,
        "dangling":   dangling,
        "orphans":    orphans,
        "duplicates": duplicates,
        "gaps":       gaps,
        "max_cited":  max_cited,
        "ref_count":  len(ref_entries),
        "issues":     issues,
        "qa_file":    str(qa_file),
    }


@mcp.tool()
def format_citations(
    paper_ids: list[str],
    style: str = "vancouver",
    db_path: str | None = None,
    output_path: str | None = None,
    allow_download: bool = True,
) -> dict:
    """
    Format a reference list in a journal citation style.

    Two rendering engines, tried in order:

    1. CSL engine (citeproc-py) — supports ANY of the 10,000+ styles from the
       official Citation Style Language repository, addressed by their CSL id,
       e.g.:
         "vancouver", "apa", "nature", "cell", "science", "ieee",
         "the-lancet", "plos-one",
         "frontiers-in-immunology", "journal-of-immunology",
         "the-new-england-journal-of-medicine", ...
       Journal-specific (dependent) styles are resolved to their parent style
       automatically. The .csl file is cached under assets/csl_styles/.

    2. Built-in fallback (no extra dependency) — used when citeproc-py is not
       installed or a style cannot be resolved. Supports:
         vancouver | apa | harvard | ama | nature | mla

    The output can be pasted directly into a Word document, or imported into
    Zotero/Mendeley alongside the exported RIS/BibTeX file.

    Args:
        paper_ids:      List of paper_ids (from local DB) to include.
        style:          Citation style id (default: 'vancouver'). Any CSL style
                        id works when the CSL engine is available.
        db_path:        Override default database path.
        output_path:    If provided, also write formatted list to this file.
        allow_download: Allow fetching an uncached .csl from the CSL repo.

    Returns:
        dict with 'style', 'engine' ('csl' | 'builtin'), 'count',
        'formatted' (list of strings), 'formatted_text' (copy-paste block),
        and (CSL only) 'style_id' / 'resolved_parent'; or 'error'.
    """
    if litdb is None:
        return {"error": "literature_db not available"}
    _lic = _validate_license()
    if not _lic.get("valid"):
        return {"error": "License validation failed", "detail": _lic}

    style = style.lower().strip()
    builtin_styles = ("vancouver", "apa", "harvard", "ama", "nature", "mla")

    try:
        conn = _get_db(db_path)
        papers = []
        for pid in paper_ids:
            p = litdb.get_paper(conn, pid)
            if p:
                if isinstance(p.get("authors"), str):
                    try:
                        p["authors"] = json.loads(p["authors"])
                    except Exception:
                        pass
                papers.append(p)

        if not papers:
            return {"error": "No papers found for given paper_ids"}

        engine = "builtin"
        formatted: list[str] = []
        csl_meta: dict = {}

        # 1. Try the CSL engine (any of 10k+ journal styles)
        if csl_engine is not None and csl_engine.is_available():
            try:
                csl_items = json.loads(_papers_to_csl_json(papers))
                rendered = csl_engine.render_bibliography(
                    csl_items, style, allow_download=allow_download)
            except Exception:
                rendered = None
            if rendered and rendered.get("entries"):
                engine = "csl"
                formatted = rendered["entries"]
                csl_meta = {
                    "style_id":        rendered.get("style_id"),
                    "resolved_parent": rendered.get("resolved_parent"),
                }

        # 2. Fallback to the built-in formatter
        if not formatted:
            if style not in builtin_styles:
                return {
                    "error": (
                        f"Style '{style}' could not be rendered. CSL engine "
                        f"{'unavailable' if (csl_engine is None or not csl_engine.is_available()) else 'could not resolve this style'}. "
                        f"Built-in styles: {builtin_styles}."
                    ),
                    "hint": "pip install citeproc-py  # enables 10k+ CSL styles",
                }
            for i, p in enumerate(papers, 1):
                formatted.append(_format_one_citation(p, i, style))

        block = "\n".join(formatted)

        if output_path:
            out = Path(output_path)
            out.parent.mkdir(parents=True, exist_ok=True)
            out.write_text(block, encoding="utf-8")

        result = {
            "style":          style,
            "engine":         engine,
            "count":          len(papers),
            "formatted":      formatted,
            "formatted_text": block,
            "output_path":    output_path,
        }
        result.update({k: v for k, v in csl_meta.items() if v is not None})
        return result

    except Exception as exc:
        return {"error": str(exc)}


def _format_authors(authors: list, style: str, max_n: int = 6) -> str:
    """Format author list for a given citation style."""
    if not authors:
        return ""

    def _initials(name: str) -> str:
        """Convert 'Smith, John A.' → 'Smith J' or similar."""
        name = name.strip()
        if "," in name:
            parts = name.split(",", 1)
            last = parts[0].strip()
            first = parts[1].strip()
            initials = "".join(
                w[0].upper() for w in first.split() if w
            )
            return f"{last} {initials}"
        return name

    def _apa_name(name: str) -> str:
        name = name.strip()
        if "," in name:
            parts = name.split(",", 1)
            last = parts[0].strip()
            first = parts[1].strip()
            initials = ". ".join(w[0].upper() for w in first.split() if w) + "."
            return f"{last}, {initials}"
        return name

    names = [str(a) for a in authors]
    n = len(names)

    if style in ("vancouver", "ama", "nature"):
        formatted_names = [_initials(a) for a in names]
        if n <= max_n:
            return ", ".join(formatted_names)
        return ", ".join(formatted_names[:max_n]) + ", et al"

    if style == "apa":
        formatted_names = [_apa_name(a) for a in names]
        if n == 1:
            return formatted_names[0]
        if n == 2:
            return f"{formatted_names[0]}, & {formatted_names[1]}"
        if n <= max_n:
            return ", ".join(formatted_names[:-1]) + f", & {formatted_names[-1]}"
        return ", ".join(formatted_names[:max_n]) + ", ... " + _apa_name(names[-1])

    if style == "harvard":
        formatted_names = [_initials(a) for a in names]
        if n == 1:
            return formatted_names[0]
        if n == 2:
            return f"{formatted_names[0]} and {formatted_names[1]}"
        if n <= max_n:
            return ", ".join(formatted_names[:-1]) + f" and {formatted_names[-1]}"
        return ", ".join(formatted_names[:max_n]) + " et al."

    if style == "mla":
        if n == 1:
            return names[0]
        if n == 2:
            return f"{names[0]}, and {names[1]}"
        return f"{names[0]}, et al"

    return ", ".join(str(a) for a in names[:max_n])


def _format_one_citation(p: dict, num: int, style: str) -> str:
    authors  = p.get("authors") or []
    title    = (p.get("title") or "").strip().rstrip(".")
    journal  = (p.get("journal") or "").strip()
    year     = p.get("year") or ""
    volume   = p.get("volume") or ""
    issue    = p.get("issue") or ""
    pages    = p.get("pages") or ""
    doi      = p.get("doi") or ""
    pmid     = p.get("pmid") or ""

    author_str = _format_authors(authors, style)

    if style in ("vancouver", "ama"):
        vol_iss = f"{volume}" + (f"({issue})" if issue else "")
        loc = f"{vol_iss}:{pages}" if pages else vol_iss
        doi_str = f" doi:{doi}" if doi else (f" PMID:{pmid}" if pmid else "")
        return (f"{num}. {author_str}. {title}. "
                f"{journal}. {year};{loc}.{doi_str}")

    if style == "nature":
        vol_iss = f"{volume}" + (f", {issue}" if issue else "")
        doi_str = f" https://doi.org/{doi}" if doi else ""
        return (f"{num}. {author_str} {title}. "
                f"{journal} {vol_iss}, {pages} ({year}).{doi_str}")

    if style == "apa":
        vol_iss = f"{volume}" + (f"({issue})" if issue else "")
        doi_str = f" https://doi.org/{doi}" if doi else ""
        return (f"{author_str} ({year}). {title}. "
                f"{journal}, {vol_iss}, {pages}.{doi_str}")

    if style == "harvard":
        vol_iss = f"{volume}" + (f"({issue})" if issue else "")
        doi_str = f" doi:{doi}" if doi else ""
        return (f"{author_str} ({year}) '{title}', "
                f"{journal}, {vol_iss}, pp. {pages}.{doi_str}")

    if style == "mla":
        return (f'{author_str} "{title}." '
                f"{journal}, vol. {volume}, no. {issue}, "
                f"{year}, pp. {pages}.")

    return f"{num}. {title}"


# ── Journal requirements tools ────────────────────────────────────────────────

@mcp.tool()
def get_journal_requirements(journal_name: str) -> dict:
    """
    Look up submission requirements for a target journal (10 452 journals).

    Covers: word limits, abstract limits, section requirements, reference
    limits, figure limits, submission system, formatting hints, open access
    options, and citation style.

    Difference: 投稿须知 (Author Guidelines) = full submission policy
    including ethics, data sharing, author contributions, etc.
    投稿格式 (Formatting Guide) = layout, word count, figure specs only.
    This tool returns both where available.

    Args:
        journal_name: Full or partial journal name (case-insensitive).
                      Examples: "Frontiers in Immunology",
                                "Nature Medicine", "PLOS ONE".

    Returns:
        Full journal requirements dict, or suggestions if not found.
    """
    _lic = _validate_license()
    if not _lic.get("valid"):
        return {"error": "License validation failed", "detail": _lic}

    name_lower = journal_name.lower().strip()

    # 1. Try local file search (10 452 JSON files)
    matches = _search_journal_files(name_lower)
    if matches:
        best = matches[0]
        result = {**best}
        if len(matches) > 1:
            result["_also_matched"] = [m.get("title") for m in matches[1:]]
        return result

    # 2. Try platform_docs for submission system info
    if PLATFORM_DOCS.exists():
        try:
            pdata = json.loads(PLATFORM_DOCS.read_text(encoding="utf-8"))
            for sys_name, sys_info in pdata.get("platforms", {}).items():
                if name_lower in sys_name.lower():
                    return {"name": sys_name,
                            "type": "submission_platform",
                            **sys_info}
        except Exception:
            pass

    # 3. Cloud fallback
    try:
        url = (f"{LICENSE_API}/journal/"
               f"{urllib.request.pathname2url(journal_name)}")
        req = urllib.request.Request(
            url, headers={"User-Agent": "therasik-mcp/2.0"})
        with urllib.request.urlopen(req, timeout=8) as resp:
            return json.loads(resp.read())
    except Exception:
        pass

    return {
        "error": f"Journal not found: '{journal_name}'",
        "hint":  "Try list_journals to browse. Use partial names e.g. 'immunology'.",
    }


@mcp.tool()
def list_journals(
    search: str | None = None,
    publisher: str | None = None,
    submission_system: str | None = None,
    limit: int = 50,
) -> dict:
    """
    Browse all 10 452 journals in the local database.

    Optionally filter by name/keyword, publisher, or submission system.

    Note on submission terminology:
      - 投稿须知 (Author Guidelines): Complete policy document covering ethics,
        data availability, author contributions, conflict of interest, and
        formatting requirements. Usually 10-30 pages.
      - 投稿格式 (Formatting Guide): Subset of the above covering only
        structural and typographic requirements (word count, figure specs,
        section order). Usually 1-3 pages.
      - This database primarily stores submission_system routing and
        format_hints (投稿格式). Full 须知 content comes from the scraped
        _platform_docs.json for major systems.

    Args:
        search:           Name/keyword filter (partial match, case-insensitive).
        publisher:        Publisher name filter.
        submission_system: Platform filter ('Editorial Manager', 'ScholarOne',
                          'Frontiers', 'MDPI', etc.).
        limit:            Max results (default 50, max 500).

    Returns:
        dict with 'count', 'showing', 'journals' list.
    """
    _lic = _validate_license()
    if not _lic.get("valid"):
        return {"error": "License validation failed", "detail": _lic}

    if not JOURNAL_DIR.exists():
        return {"error": "Journal database not found. Run build_journal_db.py first."}

    limit = min(int(limit), 500)
    results: list[dict] = []
    total_scanned = 0

    search_lower    = search.lower().strip() if search else None
    pub_lower       = publisher.lower().strip() if publisher else None
    sys_lower       = submission_system.lower().strip() if submission_system else None

    for p in JOURNAL_DIR.glob("*.json"):
        if p.stem.startswith("_"):
            continue
        total_scanned += 1
        try:
            data = json.loads(p.read_text(encoding="utf-8"))
        except Exception:
            continue

        title  = (data.get("title") or "").lower()
        pub    = (data.get("publisher") or "").lower()
        sys_   = (data.get("submission_system") or "").lower()

        if search_lower and search_lower not in title and search_lower not in p.stem:
            continue
        if pub_lower and pub_lower not in pub:
            continue
        if sys_lower and sys_lower not in sys_:
            continue

        results.append({
            "title":             data.get("title"),
            "abbreviation":      data.get("abbreviation"),
            "publisher":         data.get("publisher"),
            "submission_system": data.get("submission_system"),
            "issn":              data.get("issn"),
            "nlm_id":            data.get("nlm_id"),
            "submission_url":    data.get("submission_url"),
        })

        if len(results) >= limit:
            break

    return {
        "count":   len(results),
        "showing": len(results),
        "scanned": total_scanned,
        "note":    ("total journals ≈10 452; scan stops at limit. "
                    "Narrow search terms for faster results."),
        "journals": results,
    }


# ── Submission preparation tools ──────────────────────────────────────────────

try:
    import submission_prep as subprep
except ImportError:
    subprep = None  # type: ignore

try:
    import multi_expert_review as mer
except ImportError:
    mer = None  # type: ignore


@mcp.tool()
def check_submission_compliance(
    project_dir: str,
    article_type: str | None = None,
) -> dict:
    """
    Check manuscript compliance against the target journal requirements.

    Verifies: word count, abstract length, required sections, reference count,
    figure count, data availability statement, and TheraSIK QA gate status.

    Args:
        project_dir:  Path to the manuscript project directory.
        article_type: Override article type (Article, Letter, Review, etc.).

    Returns:
        dict with status (PASS/FAIL/WARN), checks list, submission_system,
        word_count.
    """
    if subprep is None:
        return {"error": "submission_prep module not available"}
    _lic = _validate_license()
    if not _lic.get("valid"):
        return {"error": "License validation failed", "detail": _lic}
    try:
        return subprep.check_compliance(project_dir, article_type=article_type)
    except Exception as exc:
        return {"error": str(exc)}


@mcp.tool()
def prepare_submission_package(
    project_dir: str,
    article_type: str | None = None,
    corresponding_author: str | None = None,
) -> dict:
    """
    Assemble a complete submission package: DOCX/PDF, cover letter, checklist,
    manifest. Runs compliance check and flags blocking issues.

    Args:
        project_dir:          Path to manuscript project directory.
        article_type:         Override article type.
        corresponding_author: Name and email, e.g. "Jane Doe <j@uni.edu>".

    Returns:
        dict with status, output_dir, files, compliance_status, blocking_issues.
    """
    if subprep is None:
        return {"error": "submission_prep module not available"}
    _lic = _validate_license()
    if not _lic.get("valid"):
        return {"error": "License validation failed", "detail": _lic}
    try:
        return subprep.prepare_submission(
            project_dir,
            article_type=article_type,
            corresponding_author=corresponding_author,
        )
    except Exception as exc:
        return {"error": str(exc)}


@mcp.tool()
def generate_cover_letter(
    project_dir: str,
    corresponding_author: str | None = None,
) -> dict:
    """
    Generate a journal cover letter for a manuscript.

    Reads project_config.json for journal name, title, and author list.
    Writes to 04_submission/cover_letter.md.

    Args:
        project_dir:          Path to manuscript project directory.
        corresponding_author: Name and affiliation override.

    Returns:
        dict with output_path and preview (first 300 chars).
    """
    if subprep is None:
        return {"error": "submission_prep module not available"}
    _lic = _validate_license()
    if not _lic.get("valid"):
        return {"error": "License validation failed", "detail": _lic}
    try:
        return subprep.generate_cover_letter(
            project_dir, corresponding_author=corresponding_author
        )
    except Exception as exc:
        return {"error": str(exc)}


@mcp.tool()
def get_submission_system_guide(system_name: str) -> dict:
    """
    Return step-by-step submission instructions for a specific platform.

    Reads from the scraped _platform_docs.json asset which contains live
    author guidelines and file format requirements scraped from:
      ScholarOne, Editorial Manager, NPG/Snapp (Nature), Frontiers,
      ACS Paragon Plus, AAAS Submit (Science), MDPI Submission.

    Args:
        system_name: Platform name (case-insensitive partial match).
                     Examples: 'Frontiers', 'ScholarOne', 'MDPI', 'Nature'.

    Returns:
        Platform guide with static_info (file limits, formats, DPI) and
        scraped_pages (live author guidelines text preview).
    """
    _lic = _validate_license()
    if not _lic.get("valid"):
        return {"error": "License validation failed", "detail": _lic}

    # Read from _platform_docs.json asset
    if PLATFORM_DOCS.exists():
        try:
            pdata    = json.loads(PLATFORM_DOCS.read_text(encoding="utf-8"))
            name_low = system_name.lower()
            platforms = pdata.get("platforms", {})

            # Exact match first
            for k, v in platforms.items():
                if k.lower() == name_low:
                    return {"platform": k, **v}

            # Partial match
            matches = {k: v for k, v in platforms.items()
                       if name_low in k.lower()}
            if matches:
                k = next(iter(matches))
                return {"platform": k, **matches[k]}

            return {
                "error": f"Platform '{system_name}' not found.",
                "available": list(platforms.keys()),
            }
        except Exception as exc:
            return {"error": f"Could not read platform docs: {exc}"}

    # Legacy fallback to subprep module
    if subprep is not None:
        try:
            return subprep.get_system_guide(system_name)
        except Exception as exc:
            return {"error": str(exc)}

    return {"error": "_platform_docs.json not found and submission_prep unavailable"}


# ── Review & polish tools ─────────────────────────────────────────────────────

@mcp.tool()
def polish_manuscript(
    input_file: str,
    mode: str = "scan",
    journal: str | None = None,
    section: str | None = None,
    fail_threshold: int = 3,
    language: str = "en-US",
    output_path: str | None = None,
) -> dict:
    """
    Polish and QA-check a manuscript for AI markers and grammar issues.

    Two modes:
      scan    — Detect AI-style marker phrases (e.g. "leverages", "pivotal",
                "intricate", "it is worth noting") that flag AI authorship
                detectors. Returns PASS/FAIL with hit list.
      grammar — LanguageTool public API grammar + style check (free, no key
                required). Categories: GRAMMAR, TYPOS, PUNCTUATION, STYLE,
                CONFUSED_WORDS, COLLOCATIONS.

    Args:
        input_file:      Path to manuscript text file (MD, TXT, or DOCX text).
        mode:            'scan' (AI markers) or 'grammar' (LanguageTool).
        journal:         Target journal name — loads journal style context.
        section:         Section name (e.g. 'discussion', 'abstract').
        fail_threshold:  Number of issues triggering FAIL (default 3).
        language:        Language code for grammar check (default 'en-US').
        output_path:     Write JSON report to this path (optional).

    Returns:
        dict with 'status' (PASS/WARN/FAIL), 'mode', issue details, or 'error'.
    """
    _lic = _validate_license()
    if not _lic.get("valid"):
        return {"error": "License validation failed", "detail": _lic}

    polisher_script = SCRIPTS_DIR / "insynbio_polishing.py"
    if not polisher_script.exists():
        return {"error": "insynbio_polishing.py not found in scripts/"}

    if mode not in ("scan", "grammar"):
        return {"error": f"Unknown mode '{mode}'. Use 'scan' or 'grammar'."}

    # insynbio_polishing.py CLI requires subcommand first:
    #   insynbio_polishing.py scan --input <file>
    args = [mode, "--input", str(input_file)]
    if journal:
        args += ["--journal", journal]
    if section:
        args += ["--section", section]
    if fail_threshold != 3:
        args += ["--fail-threshold", str(fail_threshold)]
    if mode == "grammar":
        args += ["--language", language]
    if output_path:
        args += ["--out", output_path]

    result = _run_py("insynbio_polishing.py", args)

    # Parse JSON output if available
    parsed: dict = {}
    if result["stdout"]:
        try:
            parsed = json.loads(result["stdout"])
        except Exception:
            parsed = {"raw_output": result["stdout"]}

    return {
        "success": result["returncode"] == 0,
        "mode":    mode,
        **parsed,
        "stderr":  result["stderr"] or None,
    }


@mcp.tool()
def verify_citations_s2(
    project_dir: str,
    manuscript_file: str = "02_manuscript/manuscript.md",
    max_verify: int = 25,
) -> dict:
    """
    Verify manuscript DOIs and PMIDs against 3 free public APIs (cascade).

    Verification chain per DOI:
      1. Semantic Scholar  (fastest, broadest coverage)
      2. CrossRef          (authoritative DOI registry)
      3. PubMed E-utils    (DOI → PMID → metadata)

    PMIDs verified directly via PubMed E-utilities.

    Flags:
      - not_found: not found across all 3 APIs — possible hallucinated citation
      - invalid_format: DOI string does not match 10.xxxx/suffix pattern
      - verified: confirmed real paper with title, year, venue + source API

    All APIs are free; no key required. Optionally set:
      S2_API_KEY, NCBI_API_KEY, CROSSREF_MAILTO for higher rate limits.

    Args:
        project_dir:     Path to manuscript project directory.
        manuscript_file: Relative path to manuscript (default: 02_manuscript/manuscript.md).
        max_verify:      Max DOIs to verify per run (default 25, to stay within rate limits).

    Returns:
        dict with total_dois, verified, not_found, invalid, hallucination_risk list,
        and per-DOI details.
    """
    _lic = _validate_license()
    if not _lic.get("valid"):
        return {"error": "License validation failed", "detail": _lic}

    proj = Path(project_dir).resolve()
    ms_path = proj / manuscript_file
    if not ms_path.exists():
        # Try to find any markdown file
        candidates = list(proj.rglob("*.md"))
        if not candidates:
            return {"error": f"Manuscript not found: {ms_path}"}
        ms_path = candidates[0]

    try:
        import citation_verifier as _cv
    except ImportError:
        return {"error": "citation_verifier module not found — ensure scripts/ is in path"}

    text = ms_path.read_text(encoding="utf-8", errors="ignore")
    try:
        report = _cv.verify_all(text, max_dois=max_verify, max_pmids=10)
        report["manuscript"] = str(ms_path)
        report["_source"]    = "semantic_scholar + crossref + pubmed"
        return report
    except Exception as exc:
        return {"error": str(exc)}


@mcp.tool()
def check_grammar(
    project_dir: str,
    manuscript_file: str = "02_manuscript/manuscript.md",
    min_confidence: str = "MEDIUM",
) -> dict:
    """
    Run LanguageTool grammar & punctuation check with AI judgment filtering.

    Uses 4-stage filter to eliminate false positives common in biomedical manuscripts:
      1. Category whitelist     — GRAMMAR + PUNCTUATION only; discards TYPOS/STYLE/CASING
      2. Rule ID blacklist      — removes known noisy rule IDs (spelling, unit spacing, etc.)
      3. Technical term skip    — auto-extracts gene/protein/abbreviation terms from the
                                  manuscript itself and skips any match containing them
      4. Confidence scoring     — context-aware; technical-section matches are downgraded

    Output is SUGGESTIONS ONLY:
      Every finding carries a confidence level (HIGH / MEDIUM) and a judgment_note.
      The AI agent decides whether to accept each suggestion — nothing is auto-applied.

    Args:
        project_dir:     Path to manuscript project directory.
        manuscript_file: Relative path to manuscript (default: 02_manuscript/manuscript.md).
        min_confidence:  "HIGH" | "MEDIUM" | "LOW" — minimum confidence to report.
                         "MEDIUM" is recommended for most manuscripts.

    Returns:
        dict with:
          - suggestions: list of {token, replacements, context, confidence, judgment_note}
          - high_count, medium_count, total_raw, total_reported
          - findings: list in multi_expert_review format
          - tech_terms_identified: int  (shows how many terms were auto-extracted)
          - noise_reduction_pct: int    (shows how noisy raw LT output was)

    Requires:
        Internet access to api.languagetool.org (free, no API key needed).
        Optional: set LT_USERNAME + LT_API_KEY for higher rate limits.
    """
    _lic = _validate_license()
    if not _lic.get("valid"):
        return {"error": "License validation failed", "detail": _lic}

    proj = Path(project_dir).resolve()
    ms_path = proj / manuscript_file
    if not ms_path.exists():
        candidates = list(proj.rglob("*.md"))
        if not candidates:
            return {"error": f"Manuscript not found: {ms_path}"}
        ms_path = candidates[0]

    try:
        import language_tool as _lt
    except ImportError:
        return {"error": "language_tool module not found — ensure scripts/ is in path"}

    text = ms_path.read_text(encoding="utf-8", errors="ignore")

    if not _lt.is_available(timeout=6):
        return {
            "status": "offline",
            "message": "LanguageTool API unreachable. Run in environment with internet access.",
            "suggestions": [],
        }

    try:
        report = _lt.check_manuscript(text, min_confidence=min_confidence)
        raw    = report["total_raw"]
        filt   = report["total_filtered"]
        noise_reduction = round((1 - filt / max(1, raw)) * 100)
        report["noise_reduction_pct"] = noise_reduction
        report["manuscript"]          = str(ms_path)
        report["min_confidence_used"] = min_confidence
        return report
    except Exception as exc:
        return {"error": str(exc)}


@mcp.tool()
def run_multi_expert_review(
    project_dir: str,
    reviewers: list[str] | None = None,
    use_llm: bool = False,
) -> dict:
    """
    Run multi-expert manuscript review from independent reviewer roles.

    Seven-role review. Original three roles are rule-based. Three new roles support
    Gemini-2.5-flash (free tier) with automatic rule fallback. Grammar Expert uses
    LanguageTool with 4-layer AI judgment filter.

      - Statistician:         statistical tests, p-values, effect sizes,
                              corrections, sample size/power analysis     [rules]
      - Domain Expert:        overclaiming, causal language, hypothesis framing,
                              limitations, alternative explanations       [rules]
      - Editor:               word count, sections, references, figures,
                              declarations                                [rules]
      - AI Diagnostician:     AI phrase markers, self-talk, unanchored claims,
                              sentence-rhythm uniformity                  [gemini|rules]
      - Citation Auditor:     citation density, hallucination-risk gaps,
                              strong uncited claims, topical cites        [gemini|rules]
      - Reproducibility:      methods completeness, software + version,
                              cell line provenance, data deposition       [gemini|rules]
      - Grammar Expert:       LanguageTool grammar/punctuation with 4-layer
                              biomedical false-positive filter; AI confidence
                              scoring; output is suggestions only          [languagetool]

    Source-bounded — findings reference only manuscript content.
    No accept/reject predictions. Output: {project_dir}/03_QA/multi_expert_review_QA.md

    Args:
        project_dir: Path to manuscript project directory.
        reviewers:   Subset to run. Default: all seven
                     ("statistician","domain","editor","ai_diagnostician",
                      "citation_auditor","reproducibility","grammar").
        use_llm:     If True, ai_diagnostician / citation_auditor / reproducibility
                     call Gemini-2.5-flash (requires GEMINI_API_KEY env var).
                     Falls back to rules automatically on any failure.

    Returns:
        dict with overall_status, overall_score (0-10), per-reviewer findings,
        priority_actions (CRITICAL > MAJOR > MINOR), and report_path.
    """
    if mer is None:
        return {"error": "multi_expert_review module not available"}
    _lic = _validate_license()
    if not _lic.get("valid"):
        return {"error": "License validation failed", "detail": _lic}
    try:
        result = mer.run_full_review(project_dir, reviewers=reviewers, use_llm=use_llm,
                                     grammar_confidence="MEDIUM")
        result["report_path"] = str(
            Path(project_dir) / "03_QA" / "multi_expert_review_QA.md"
        )
        return result
    except Exception as exc:
        return {"error": str(exc)}


# ── Planning & figures tools ──────────────────────────────────────────────────

try:
    import manuscript_planner as msplan
except ImportError:
    msplan = None  # type: ignore

try:
    import stat_plots as statplots
except ImportError:
    statplots = None  # type: ignore


@mcp.tool()
def plan_manuscript(
    project_dir: str,
    topic: str = "",
    aim: str = "",
    article_type: str = "",
    journal_name: str = "",
    design: str = "",
    keywords: list[str] | None = None,
) -> dict:
    """
    Generate a structured manuscript writing plan.

    Produces section scaffold, word budgets calibrated to journal limits,
    science-first writing order, figure/table slot plan, and key message
    templates for each section.

    Writes to {project_dir}/00_planning/manuscript_plan.md
                           and section_outline.md

    Args:
        project_dir:  Path to manuscript project directory.
        topic:        Research topic or title idea.
        aim:          Primary aim or hypothesis statement.
        article_type: original | review | brief | methods | meta | case
                      (auto-detected from topic if omitted).
        journal_name: Target journal — used to calibrate word budgets.
        design:       Study design (e.g. RCT, retrospective cohort, in vitro).
        keywords:     List of 5–8 keywords.

    Returns:
        Plan dict with sections, word_budget, writing_order, figures, tables.
    """
    if msplan is None:
        return {"error": "manuscript_planner module not available"}
    _lic = _validate_license()
    if not _lic.get("valid"):
        return {"error": "License validation failed", "detail": _lic}
    try:
        return msplan.plan_manuscript(
            project_dir,
            topic=topic, aim=aim, article_type=article_type,
            journal_name=journal_name, design=design, keywords=keywords,
        )
    except Exception as exc:
        return {"error": str(exc)}


@mcp.tool()
def generate_stat_figure(
    plot_type: str,
    data: dict,
    output_path: str,
) -> dict:
    """
    Generate a publication-quality statistical figure (300 DPI, journal-ready).

    Supported types:
      forest   — Forest plot (OR/HR/RR with CI, pooled diamond, I²)
      km       — Kaplan-Meier survival curves (with at-risk table)
      roc      — ROC/AUC curves (single or multiple classifiers)
      heatmap  — Correlation or expression heatmap
      bar      — Grouped bar chart with error bars
      box      — Box + strip plot (individual data points)
      scatter  — Scatter plot with optional regression line
      volcano  — Volcano plot (log2FC vs -log10p)

    Output format is inferred from output_path extension (.png/.svg/.pdf).
    PNG output is at 300 DPI.

    Requires matplotlib: pip install matplotlib scipy

    Args:
        plot_type:   Plot type string (see above).
        data:        Data specification dict (structure varies by type;
                     see stat_plots.py docstrings).
        output_path: Absolute path for the output figure file.

    Returns:
        dict with output_path (str) and success (bool), or error with
        install instructions.
    """
    if statplots is None:
        return {
            "error": "stat_plots module unavailable (matplotlib not installed)",
            "install": "pip install matplotlib scipy",
            "success": False,
        }
    _lic = _validate_license()
    if not _lic.get("valid"):
        return {"error": "License validation failed", "detail": _lic}
    try:
        return statplots.generate_figure(plot_type, data, output_path)
    except ImportError as exc:
        missing = str(exc).split("'")
        pkg = missing[1] if len(missing) > 1 else "dependency"
        return {
            "error": f"Missing dependency: {pkg}",
            "install": f"pip install {pkg}",
            "success": False,
        }
    except Exception as exc:
        return {"error": str(exc), "success": False}


# ── System tools ──────────────────────────────────────────────────────────────

@mcp.tool()
def validate_skill_installation(skill_dir: str | None = None) -> dict:
    """
    Validate that the TheraSIK skill is correctly installed.

    Args:
        skill_dir: Override skill root path (default: auto-detected).

    Returns:
        dict with valid (bool), status (PASS/FAIL), errors list, stdout.
    """
    target = str(skill_dir or SKILL_DIR)
    cmd    = [sys.executable, str(SCRIPTS_DIR / "validate_basic_skill.py"), target]
    r      = subprocess.run(cmd, capture_output=True, text=True,
                            cwd=str(SKILL_DIR))
    errors = [ln for ln in r.stdout.splitlines() if ln.startswith("FAIL:")]
    return {
        "valid":  r.returncode == 0,
        "status": "PASS" if r.returncode == 0 else "FAIL",
        "errors": errors,
        "stdout": r.stdout.strip(),
    }


# ── Entry point ───────────────────────────────────────────────────────────────

if __name__ == "__main__":
    mcp.run(transport=_SERVER_ARGS.transport)
