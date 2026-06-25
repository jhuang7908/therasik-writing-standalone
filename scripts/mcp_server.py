"""
mcp_server.py
=============
TheraSIK Academic Writing Suite -- MCP Server

Exposes the writing suite as an MCP (Model Context Protocol) server so any
MCP-compatible LLM platform (Claude Code, Cursor, Codex, Antigravity, Cowork,
etc.) can call the suite's tools directly.

Transport: stdio (default) -- works with every MCP client via:
  python mcp_server.py

Tools exposed
-------------
  Manuscript workflow
    create_manuscript_project   -- scaffold a new project directory
    run_manuscript_workflow     -- run the full QA + render pipeline
    get_manuscript_status       -- read current gate statuses
    run_qa_gate                 -- run a single QA gate

  Literature database (RAG knowledge base)
    search_literature           -- FTS5 + TF-IDF search over stored papers
    add_paper_by_doi            -- fetch + store paper metadata via CrossRef
    add_paper_by_pmid           -- fetch + store paper metadata via PubMed
    get_paper                   -- retrieve a stored paper by ID/DOI/PMID
    import_pdf_full_text        -- extract and store PDF full text
    export_references_csv       -- export selected papers to references.csv

  Journal requirements
    get_journal_requirements    -- look up submission rules for a journal
    list_journals               -- list all journals in the database

  System
    validate_skill_installation -- check that the skill is correctly installed

Dependencies (install once):
  pip install mcp pdfplumber
  # numpy is usually pre-installed; if not: pip install numpy

Usage
-----
  # stdio (works everywhere)
  python scripts/mcp_server.py

  # With explicit skill dir (if running from a different directory)
  THERASIK_DIR=/path/to/therasik-academic-writing-suite python scripts/mcp_server.py
"""

from __future__ import annotations

import json
import os
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
    import literature_db as litdb
except ImportError:
    litdb = None  # type: ignore

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
_LICENSE_CACHE_TTL = 3600 * 6   # re-validate every 6 hours
_LICENSE_GRACE_SECS = 3600 * 24 * 7  # 7-day offline grace period


def _validate_license() -> dict:
    """Validate MCP Key + Agent Key against the license server. Caches result."""
    now = time.time()
    cached = _LICENSE_CACHE.get("result")
    cached_at = _LICENSE_CACHE.get("at", 0)

    # Return cached result if fresh
    if cached and (now - cached_at) < _LICENSE_CACHE_TTL:
        return cached

    # Skip validation in dev mode
    if MCP_KEY == "DEV" and AGENT_KEY == "DEV":
        result = {"valid": True, "plan": "dev", "agent_quota_remaining": 999999}
        _LICENSE_CACHE.update({"result": result, "at": now})
        return result

    if not MCP_KEY or not AGENT_KEY:
        print(
            "\nERROR: License keys not set.\n"
            "Add to your environment or .env file:\n"
            "  THERASIK_MCP_KEY=THERASIK-MCP-XXXXX\n"
            "  THERASIK_AGENT_KEY=THERASIK-AGT-XXXXX\n"
            "Contact support@therasik.io to obtain your keys.\n",
            file=sys.stderr,
        )
        sys.exit(1)

    try:
        body = json.dumps({"mcp_key": MCP_KEY, "agent_key": AGENT_KEY}).encode()
        req = urllib.request.Request(
            f"{LICENSE_API}/validate",
            data=body,
            method="POST",
            headers={"Content-Type": "application/json", "User-Agent": "therasik-mcp/1.0"},
        )
        with urllib.request.urlopen(req, timeout=8) as resp:
            result = json.loads(resp.read())
            _LICENSE_CACHE.update({"result": result, "at": now, "offline_since": None})
            return result

    except urllib.error.HTTPError as e:
        error = json.loads(e.read())
        reason = error.get("detail", {})
        if isinstance(reason, dict):
            msg = reason.get("message", "License validation failed")
        else:
            msg = str(reason)
        print(f"\nERROR: {msg}\n", file=sys.stderr)
        sys.exit(1)

    except Exception:
        # Network error -- check offline grace period
        offline_since = _LICENSE_CACHE.get("offline_since") or now
        _LICENSE_CACHE["offline_since"] = offline_since
        if cached and (now - offline_since) < _LICENSE_GRACE_SECS:
            print(
                f"[TheraSIK] License server unreachable. "
                f"Offline grace period: {int(((_LICENSE_GRACE_SECS - (now - offline_since)) / 3600))}h remaining.",
                file=sys.stderr,
            )
            return cached
        print(
            "\nERROR: Cannot reach license server and offline grace period expired.\n"
            "Please connect to the internet to revalidate your license.\n",
            file=sys.stderr,
        )
        sys.exit(1)


def _consume(operation: str = "api_call", units: int = 1) -> None:
    """Consume Agent Key quota units on the license server (best-effort)."""
    try:
        body = json.dumps({
            "mcp_key": MCP_KEY, "agent_key": AGENT_KEY,
            "units": units, "operation": operation
        }).encode()
        req = urllib.request.Request(
            f"{LICENSE_API}/consume", data=body, method="POST",
            headers={"Content-Type": "application/json"},
        )
        urllib.request.urlopen(req, timeout=5)
    except Exception:
        pass  # Non-blocking -- don't fail the tool call over quota tracking


def _journal_from_cloud(name: str) -> dict | None:
    """Query journal requirements from cloud API (falls back to local)."""
    try:
        url = f"{LICENSE_API}/journal/{urllib.request.quote(name)}"
        req = urllib.request.Request(url, headers={"User-Agent": "therasik-mcp/1.0"})
        with urllib.request.urlopen(req, timeout=8) as resp:
            return json.loads(resp.read())
    except Exception:
        return None


# ── Validate license on startup ───────────────────────────────────────────────
_license_info = _validate_license()

# ── Server init ───────────────────────────────────────────────────────────────
mcp = FastMCP("therasik-academic-writing-suite")

DEFAULT_DB = SKILL_DIR / "assets" / "literature_db" / "literature.db"
JOURNAL_DIR = SKILL_DIR / "assets" / "journal_requirements"
JOURNAL_INDEX = JOURNAL_DIR / "_index.json"
SCRIPTS_DIR = SKILL_DIR / "scripts"
TEMPLATE_DIR = SKILL_DIR / "assets" / "project-template"


# ── Helper ────────────────────────────────────────────────────────────────────

def _run_py(script: str, args: list[str], cwd: Path | None = None) -> dict:
    cmd = [sys.executable, str(SCRIPTS_DIR / script)] + args
    result = subprocess.run(
        cmd,
        capture_output=True, text=True,
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
        project_dir: Absolute or relative path where the project will be created.
        project_name: Human-readable project name (goes into project_config.json).
        authors: Comma-separated author list (optional).
        journal_target: Target journal name, e.g. 'Nature', 'NEJM' (optional).

    Returns:
        dict with 'success', 'project_dir', and any 'error' messages.
    """
    import shutil

    proj = Path(project_dir).resolve()
    if proj.exists() and any(proj.iterdir()):
        return {"success": False, "error": f"Directory {proj} already exists and is not empty"}

    try:
        shutil.copytree(str(TEMPLATE_DIR), str(proj), dirs_exist_ok=True)
    except Exception as exc:
        return {"success": False, "error": str(exc)}

    # Patch project_config.json with provided values
    config_path = proj / "project_config.json"
    if config_path.exists():
        try:
            cfg = json.loads(config_path.read_text(encoding="utf-8"))
            cfg["project_name"] = project_name
            if authors:
                cfg["authors"] = [a.strip() for a in authors.split(",")]
            if journal_target:
                cfg["journal_target"] = journal_target
            config_path.write_text(json.dumps(cfg, indent=2, ensure_ascii=False), encoding="utf-8")
        except Exception as exc:
            pass  # Non-fatal; project is created, config patch failed

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
    Writes a workflow_execution_audit_vN.json in the project directory.

    Args:
        project_dir: Path to the manuscript project directory.
        skip_qa_scripts: If True, skips QA script execution (framework test mode).
        render_outputs: If False, skips document rendering steps.

    Returns:
        dict with 'success', 'gate_summary', 'audit_file', 'stdout', 'stderr'.
    """
    proj = Path(project_dir).resolve()
    config_path = proj if proj.name == "project_config.json" else proj / "project_config.json"
    if not config_path.exists():
        return {
            "success": False,
            "error": f"project_config.json not found: {config_path}",
        }

    args = [str(config_path)]
    if skip_qa_scripts:
        args.append("--skip-qa-scripts")

    result = _run_py("run_full_workflow.py", args)

    # Try to extract gate summary from stdout
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
        "note": "render_outputs is controlled by project_config workflow_steps in this Phase 2 stdio server.",
    }


@mcp.tool()
def get_manuscript_status(project_dir: str) -> dict:
    """
    Read the current QA gate statuses for a manuscript project.

    Scans the 03_QA directory for QA markdown files and returns the
    Status line from each.

    Args:
        project_dir: Path to the manuscript project directory.

    Returns:
        dict with 'gates' (mapping of gate name -> status) and 'summary'.
    """
    proj = Path(project_dir).resolve()
    qa_dir = proj / "03_QA"

    if not qa_dir.exists():
        return {"gates": {}, "summary": "No 03_QA directory found"}

    gates: dict[str, str] = {}
    for md_file in sorted(qa_dir.glob("*.md")):
        status = "UNKNOWN"
        try:
            for line in md_file.read_text(encoding="utf-8", errors="ignore").splitlines()[:40]:
                stripped = line.strip()
                if stripped.lower().startswith("status:"):
                    raw = stripped.split(":", 1)[1].strip()
                    token = raw.split()[0].upper() if raw.split() else "UNKNOWN"
                    status = token
                    break
        except Exception:
            status = "READ_ERROR"
        gates[md_file.stem] = status

    total = len(gates)
    passing = sum(1 for s in gates.values() if s == "PASS")
    failing = sum(1 for s in gates.values() if s == "FAIL")
    pending = sum(1 for s in gates.values() if s == "PENDING")

    return {
        "gates": gates,
        "summary": f"{passing}/{total} PASS, {failing} FAIL, {pending} PENDING",
        "all_pass": failing == 0 and total > 0,
    }


@mcp.tool()
def run_qa_gate(
    project_dir: str,
    gate: str,
    verify_doi: bool = False,
) -> dict:
    """
    Run a single QA gate script for a manuscript project.

    Available gates:
      reference_claim  -- reference completeness and claim support
      ai_style         -- AI-style / human voice detection
      paragraph        -- paragraph structure and coherence
      figure_contract  -- figure contract completeness

    Args:
        project_dir: Path to the manuscript project directory.
        gate: One of 'reference_claim', 'ai_style', 'paragraph', 'figure_contract'.
        verify_doi: For reference_claim gate only -- hit CrossRef to verify DOIs.

    Returns:
        dict with 'success', 'status' (PASS/FAIL), 'output_file', 'stdout'.
    """
    gate_map = {
        "reference_claim": ("run_reference_claim_qa.py", "reference_claim_support_QA.md"),
        "ai_style": ("run_ai_style_qa.py", "ai_style_human_voice_QA.md"),
        "paragraph": ("run_paragraph_structure_qa.py", "paragraph_structure_QA.md"),
        "figure_contract": ("run_figure_contract_qa.py", "figure_contract_QA.md"),
    }

    if gate not in gate_map:
        return {
            "success": False,
            "error": f"Unknown gate '{gate}'. Valid: {list(gate_map.keys())}",
        }

    script, output_name = gate_map[gate]
    args = ["--project-root", project_dir]
    if gate == "reference_claim" and verify_doi:
        args.append("--verify-doi")

    result = _run_py(f"qa/{script}", args)

    output_path = Path(project_dir) / "03_QA" / output_name
    status = "UNKNOWN"
    if output_path.exists():
        for line in output_path.read_text(encoding="utf-8", errors="ignore").splitlines()[:10]:
            if line.strip().lower().startswith("status:"):
                raw = line.strip().split(":", 1)[1].strip()
                status = raw.split()[0].upper() if raw.split() else "UNKNOWN"
                break

    return {
        "success": result["returncode"] == 0,
        "status": status,
        "output_file": str(output_path),
        "stdout": result["stdout"],
        "stderr": result["stderr"],
    }


# ── Literature database tools ─────────────────────────────────────────────────

@mcp.tool()
def search_literature(
    query: str,
    limit: int = 10,
    year_from: int | None = None,
    year_to: int | None = None,
    journal: str | None = None,
    db_path: str | None = None,
) -> dict:
    """
    Search the local literature database using full-text and TF-IDF search.

    Searches across title, abstract, keywords, and full text (if imported).
    Combines SQLite FTS5 keyword search with TF-IDF cosine similarity ranking.

    Args:
        query: Search query string (supports FTS5 syntax: "antibody AND complement").
        limit: Maximum number of results to return (default 10).
        year_from: Filter to papers published >= this year.
        year_to: Filter to papers published <= this year.
        journal: Filter by journal name substring (case-insensitive).
        db_path: Override default database path.

    Returns:
        dict with 'results' list and 'total' count.
    """
    if litdb is None:
        return {"error": "literature_db not available", "results": []}
    try:
        conn = _get_db(db_path)
        results = litdb.search(conn, query, limit=limit,
                               year_from=year_from, year_to=year_to, journal=journal)
        # Sanitize authors field
        for r in results:
            if isinstance(r.get("authors"), str):
                try:
                    r["authors"] = json.loads(r["authors"])
                except Exception:
                    pass
        return {"results": results, "total": len(results)}
    except Exception as exc:
        return {"error": str(exc), "results": []}


def _proxy_fetch(endpoint: str, payload: dict) -> dict | None:
    """
    Call the TheraSIK cloud proxy (rate-limited, cached).
    Returns parsed JSON on success, None on any failure (caller falls back to direct).
    Skipped in DEV mode.
    """
    if MCP_KEY == "DEV" and AGENT_KEY == "DEV":
        return None  # dev mode: always call APIs directly
    if not MCP_KEY or not AGENT_KEY:
        return None
    try:
        body = json.dumps(payload).encode()
        req = urllib.request.Request(
            f"{LICENSE_API}/{endpoint}",
            data=body, method="POST",
            headers={"Content-Type": "application/json", "User-Agent": "therasik-mcp/1.1"},
        )
        with urllib.request.urlopen(req, timeout=30) as resp:
            return json.loads(resp.read())
    except urllib.error.HTTPError as e:
        if e.code == 429:
            # Rate limited -- surface to caller
            try:
                detail = json.loads(e.read()).get("detail", {})
                retry = detail.get("retry_after_seconds", 2)
            except Exception:
                retry = 2
            raise RuntimeError(
                f"Rate limit exceeded. Retry in {retry}s. "
                f"(Server limit: {os.environ.get('RATE_LIMIT_RPM', 30)} req/min)"
            )
        return None  # other HTTP errors → fall back to direct
    except Exception:
        return None  # network error → fall back to direct


@mcp.tool()
def add_paper_by_doi(doi: str, db_path: str | None = None) -> dict:
    """
    Fetch paper metadata from CrossRef by DOI and store in the local database.

    Routing: tries the TheraSIK cloud proxy first (rate-limited, shared cache).
    Falls back to direct CrossRef API if proxy unavailable (e.g. DEV mode).

    Args:
        doi: DOI string, with or without 'https://doi.org/' prefix.
        db_path: Override default database path.

    Returns:
        dict with 'paper_id', 'is_new', 'title', or 'error'.
    """
    if litdb is None:
        return {"error": "literature_db not available"}
    try:
        # Try cloud proxy first (handles rate limiting + caching for all users)
        meta = _proxy_fetch("proxy/crossref", {"mcp_key": MCP_KEY, "agent_key": AGENT_KEY, "doi": doi})
        if meta is None:
            # Fall back to direct API
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
        return {"error": str(exc)}  # rate limit message
    except Exception as exc:
        return {"error": str(exc)}


@mcp.tool()
def add_paper_by_pmid(pmid: str, db_path: str | None = None) -> dict:
    """
    Fetch paper metadata from PubMed by PMID and store in the local database.

    Routing: tries the TheraSIK cloud proxy first (rate-limited, shared cache).
    Falls back to direct PubMed E-utilities if proxy unavailable (e.g. DEV mode).

    Args:
        pmid: PubMed ID as a string (e.g. "34912118").
        db_path: Override default database path.

    Returns:
        dict with 'paper_id', 'is_new', 'title', or 'error'.
    """
    if litdb is None:
        return {"error": "literature_db not available"}
    try:
        # Try cloud proxy first
        meta = _proxy_fetch("proxy/pubmed", {"mcp_key": MCP_KEY, "agent_key": AGENT_KEY, "pmid": pmid})
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
        db_path: Override default database path.

    Returns:
        Full paper record dict, or 'error' if not found.
    """
    if litdb is None:
        return {"error": "literature_db not available"}
    try:
        conn = _get_db(db_path)
        paper = litdb.get_paper_by_id(conn, identifier)
        if paper is None:
            return {"error": f"Paper not found: {identifier}"}
        return paper
    except Exception as exc:
        return {"error": str(exc)}


@mcp.tool()
def import_pdf_full_text(
    pdf_path: str,
    doi: str | None = None,
    paper_id: str | None = None,
    db_path: str | None = None,
) -> dict:
    """
    Extract full text from a PDF and store it in the literature database.

    The paper must already exist in the database (add it first via add_paper_by_doi
    or add_paper_by_pmid). Provide either doi or paper_id to link the PDF.

    Requires pdfplumber: pip install pdfplumber

    Args:
        pdf_path: Absolute path to the PDF file.
        doi: DOI of the paper (to link PDF to existing record).
        paper_id: paper_id of the paper (alternative to doi).
        db_path: Override default database path.

    Returns:
        dict with 'paper_id' and 'success', or 'error'.
    """
    if litdb is None:
        return {"error": "literature_db not available"}
    try:
        conn = _get_db(db_path)
        pid = litdb.import_full_text_pdf(conn, Path(pdf_path),
                                          paper_id=paper_id, doi=doi)
        return {"paper_id": pid, "success": True}
    except Exception as exc:
        return {"error": str(exc), "success": False}


@mcp.tool()
def export_references_csv(
    paper_ids: list[str],
    output_path: str,
    db_path: str | None = None,
) -> dict:
    """
    Export selected papers from the literature database to references.csv format.

    The output file is compatible with run_reference_claim_qa.py.
    Copy it to {project}/00_project_database/references.csv.

    Args:
        paper_ids: List of paper_id, DOI, or PMID strings to export.
        output_path: Where to write the CSV file.
        db_path: Override default database path.

    Returns:
        dict with 'exported_count', 'output_path', or 'error'.
    """
    if litdb is None:
        return {"error": "literature_db not available"}
    try:
        conn = _get_db(db_path)
        n = litdb.export_to_references_csv(conn, paper_ids, Path(output_path))
        return {"exported_count": n, "output_path": output_path}
    except Exception as exc:
        return {"error": str(exc)}


# ── Journal requirements tools ────────────────────────────────────────────────

def _load_journal_index() -> dict:
    if not JOURNAL_INDEX.exists():
        return {}
    return json.loads(JOURNAL_INDEX.read_text(encoding="utf-8"))


def _load_journal_file(key: str) -> dict | None:
    path = JOURNAL_DIR / f"{key}.json"
    if not path.exists():
        return None
    return json.loads(path.read_text(encoding="utf-8"))


@mcp.tool()
def get_journal_requirements(journal_name: str) -> dict:
    """
    Look up submission requirements and formatting rules for a journal.

    Returns word limits, abstract limits, figure/table limits, reference style,
    required sections, data availability policy, preprint policy, and submission URL.

    Args:
        journal_name: Journal name (case-insensitive). Partial matches supported.
                      Examples: 'nature', 'nejm', 'cell', 'plos one', 'lancet',
                                'nature medicine', 'jbc', 'science', 'immunity',
                                'frontiers pharmacology'

    Returns:
        Full journal requirements dict, or list of close matches if ambiguous.
    """
    # Try cloud API first (5,600+ journals), fall back to local (10 journals)
    cloud = _journal_from_cloud(journal_name)
    if cloud and "error" not in cloud and "matches" not in cloud:
        _consume("journal_lookup")
        return cloud

    # Local fallback
    index = _load_journal_index()
    query = journal_name.lower().strip()

    if query in index:
        data = _load_journal_file(query)
        return data or {"error": f"Data file missing for '{query}'"}

    matches = []
    for key, info in index.items():
        display = info.get("display_name", "").lower()
        if query in key or query in display:
            matches.append(key)

    if len(matches) == 1:
        data = _load_journal_file(matches[0])
        return data or {"error": f"Data file missing for '{matches[0]}'"}

    if matches:
        return {
            "message": f"Multiple matches for '{journal_name}'. Narrow your query.",
            "matches": {k: index[k].get("display_name") for k in matches},
        }

    # Return cloud partial matches if available
    if cloud and "matches" in cloud:
        return cloud

    return {
        "error": f"Journal '{journal_name}' not found.",
        "available": list(index.keys()),
    }


@mcp.tool()
def list_journals() -> dict:
    """
    List all journals available in the local journal requirements database.

    Returns:
        dict with 'journals' list (each entry has key, display_name, issn, publisher).
    """
    index = _load_journal_index()
    journals = [
        {
            "key": k,
            "display_name": v.get("display_name", k),
            "issn": v.get("issn", ""),
            "publisher": v.get("publisher", ""),
        }
        for k, v in index.items()
    ]
    return {"journals": journals, "count": len(journals)}


# ── Submission preparation tools ──────────────────────────────────────────────

try:
    import submission_prep as subprep
except ImportError:
    subprep = None  # type: ignore


@mcp.tool()
def check_submission_compliance(
    project_dir: str,
    article_type: str | None = None,
) -> dict:
    """
    Check manuscript compliance against the target journal's requirements.

    Verifies word count, abstract length, required sections, reference count,
    figure count, data availability statement, and TheraSIK QA gate status.

    The target journal is read from project_config.json (target_journal field).

    Args:
        project_dir: Path to the manuscript project directory.
        article_type: Override article type (e.g. 'Article', 'Letter', 'Review').
                      Defaults to the value in project_config.json.

    Returns:
        dict with 'status' (PASS/FAIL/WARN), 'checks' list, 'submission_url',
        'submission_system', and 'word_count'.
    """
    if subprep is None:
        return {"error": "submission_prep module not available"}
    try:
        result = subprep.check_compliance(project_dir, article_type)
        _consume("submission_check")
        return result
    except Exception as exc:
        return {"error": str(exc)}


@mcp.tool()
def prepare_submission_package(
    project_dir: str,
    article_type: str | None = None,
    corresponding_author: str = "",
) -> dict:
    """
    Build a complete submission package for the target journal.

    Actions performed:
      1. Compliance check (word counts, sections, figures, references, QA gates)
      2. Cover letter template → 04_submission/cover_letter.md
      3. Submission checklist → 04_submission/submission_checklist.md
      4. Copy DOCX + PDF + figures + QA reports → 04_submission/
      5. Write submission_manifest.json with all metadata

    Review all [bracketed placeholders] in the cover letter before submitting.

    Args:
        project_dir: Path to the manuscript project directory.
        article_type: Override article type (e.g. 'Article', 'Letter', 'Review').
        corresponding_author: Name and email of corresponding author for cover letter,
                              e.g. "Dr. Jane Smith <j.smith@univ.edu>".

    Returns:
        dict with 'status', 'submission_dir', 'cover_letter', 'checklist',
        'submission_url', 'submission_system', and 'checks' list.
    """
    if subprep is None:
        return {"error": "submission_prep module not available"}
    try:
        result = subprep.prepare_submission(project_dir, article_type, corresponding_author)
        _consume("submission_prep", units=2)
        return result
    except Exception as exc:
        return {"error": str(exc)}


@mcp.tool()
def get_submission_system_guide(system_name: str) -> dict:
    """
    Return the built-in submission checklist and file requirements for a
    major manuscript submission system.

    Provides: checklist of required steps, file upload order, accepted figure
    formats, and system-specific notes — even when journal-specific word limits
    are unknown.

    Available systems:
      ScholarOne, Editorial Manager, eJournalPress, Frontiers, Snapp,
      Bench>Press, EVISE, ScienceSubmit, PeerJ, F1000Research

    Args:
        system_name: Submission system name (case-insensitive, partial match OK).
                     Examples: 'ScholarOne', 'Editorial Manager', 'Frontiers',
                               'EM', 'Snapp', 'EJP', 'BenchPress'

    Returns:
        dict with 'checklist', 'file_order', 'figure_format', 'max_file_size_mb',
        'notes', and 'aka' (alternative names).
    """
    if subprep is None:
        return {"error": "submission_prep module not available"}
    try:
        result = subprep.get_system_guide(system_name)
        return result
    except Exception as exc:
        return {"error": str(exc)}


@mcp.tool()
def generate_cover_letter(
    project_dir: str,
    corresponding_author: str = "",
) -> dict:
    """
    Generate a journal-specific cover letter template.

    Fills in journal name, date, title (from manuscript), and article type.
    Review and complete all [bracketed placeholders] before submitting.

    Writes to: {project_dir}/04_submission/cover_letter.md

    Args:
        project_dir: Path to the manuscript project directory.
        corresponding_author: Name and contact details for the cover letter signature.

    Returns:
        dict with 'cover_letter_path' and 'text' (full markdown content).
    """
    if subprep is None:
        return {"error": "submission_prep module not available"}
    try:
        text = subprep.generate_cover_letter(project_dir, corresponding_author)
        cover_path = str(Path(project_dir) / "04_submission" / "cover_letter.md")
        _consume("cover_letter")
        return {"cover_letter_path": cover_path, "text": text}
    except Exception as exc:
        return {"error": str(exc)}


# ── System tool ───────────────────────────────────────────────────────────────

@mcp.tool()
def validate_skill_installation(skill_dir: str | None = None) -> dict:
    """
    Validate that the TheraSIK academic writing suite is correctly installed.

    Checks SKILL.md, required reference files, QA scripts, orchestration scripts,
    project template, and skill_version_manifest.json.

    Args:
        skill_dir: Path to the skill directory. Defaults to the server's own directory.

    Returns:
        dict with 'valid' (bool), 'status' (PASS/FAIL), and any 'errors'.
    """
    target = str(skill_dir or SKILL_DIR)
    result = _run_py(
        "../scripts/validate_basic_skill.py",
        [target],
        cwd=SKILL_DIR,
    )
    # validate_basic_skill.py is at scripts/validate_basic_skill.py
    # use direct path
    cmd = [sys.executable, str(SCRIPTS_DIR / "validate_basic_skill.py"), target]
    import subprocess as sp
    r = sp.run(cmd, capture_output=True, text=True, cwd=str(SKILL_DIR))
    errors = [ln for ln in r.stdout.splitlines() if ln.startswith("FAIL:")]
    return {
        "valid": r.returncode == 0,
        "status": "PASS" if r.returncode == 0 else "FAIL",
        "errors": errors,
        "stdout": r.stdout.strip(),
    }


# ── Entry point ───────────────────────────────────────────────────────────────

if __name__ == "__main__":
    mcp.run(transport="stdio")
