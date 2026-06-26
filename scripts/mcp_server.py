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
        Full paper record dict, or error if not found.
    """
    if litdb is None:
        return {"error": "literature_db not available"}
    _lic = _validate_license()
    if not _lic.get("valid"):
        return {"error": "License validation failed", "detail": _lic}
    try:
        conn = _get_db(db_path)
        paper = litdb.get_paper(conn, identifier)
        if paper is None:
            return {"error": f"Paper not found: {identifier}"}
        return paper
    except Exception as exc:
        return {"error": str(exc)}


@mcp.tool()
def import_pdf_full_text(pdf_path: str, paper_id: str, db_path: str | None = None) -> dict:
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


@mcp.tool()
def export_references_csv(
    query: str | None = None,
    paper_ids: list[str] | None = None,
    output_path: str | None = None,
    db_path: str | None = None,
) -> dict:
    """
    Export paper references to a CSV file for use in manuscript preparation.

    Args:
        query:       Optional search query to filter papers.
        paper_ids:   Optional explicit list of paper_ids to export.
        output_path: Path to write CSV.
        db_path:     Override default database path.

    Returns:
        dict with output_path, count, or error.
    """
    if litdb is None:
        return {"error": "literature_db not available"}
    _lic = _validate_license()
    if not _lic.get("valid"):
        return {"error": "License validation failed", "detail": _lic}
    try:
        conn   = _get_db(db_path)
        result = litdb.export_csv(conn, query=query, paper_ids=paper_ids, output_path=output_path)
        return result
    except Exception as exc:
        return {"error": str(exc)}


@mcp.tool()
def get_journal_requirements(journal_name: str) -> dict:
    """
    Look up submission requirements for a target journal.

    Returns word limits, abstract limits, section requirements, reference limits,
    figure limits, submission system, and open access options from the local
    journal database (5,000+ journals).

    Args:
        journal_name: Full or partial journal name.

    Returns:
        Full journal requirements dict, or suggestions if not found exactly.
    """
    _lic = _validate_license()
    if not _lic.get("valid"):
        return {"error": "License validation failed", "detail": _lic}

    import json as _json
    journal_dir = SKILL_DIR / "assets" / "journal_requirements"
    index_path  = journal_dir / "_index.json"

    if index_path.exists():
        index = _json.loads(index_path.read_text(encoding="utf-8"))
        name_lower = journal_name.lower()
        for entry in index:
            if entry.get("name", "").lower() == name_lower:
                jpath = journal_dir / entry["file"]
                if jpath.exists():
                    return _json.loads(jpath.read_text(encoding="utf-8"))
        matches = [e for e in index if name_lower in e.get("name", "").lower()][:5]
        if matches:
            return {
                "error": f"Journal not found exactly: {journal_name}",
                "suggestions": [m["name"] for m in matches],
            }

    data = _journal_from_cloud(journal_name)
    if data:
        return data
    return {"error": f"Journal not found: {journal_name}. Try list_journals to browse."}


@mcp.tool()
def list_journals(
    publisher: str | None = None,
    submission_system: str | None = None,
    limit: int = 50,
) -> dict:
    """
    List journals in the local database, optionally filtered by publisher or
    submission system.

    Args:
        publisher:         Filter by publisher name (partial, case-insensitive).
        submission_system: Filter by system (e.g. ScholarOne, Editorial Manager).
        limit:             Max results (default 50, max 200).

    Returns:
        dict with count and journals list.
    """
    _lic = _validate_license()
    if not _lic.get("valid"):
        return {"error": "License validation failed", "detail": _lic}

    import json as _json
    journal_dir = SKILL_DIR / "assets" / "journal_requirements"
    index_path  = journal_dir / "_index.json"
    if not index_path.exists():
        return {"error": "Journal index not found. Run build_journal_db.py first."}

    index   = _json.loads(index_path.read_text(encoding="utf-8"))
    results = index

    if publisher:
        pub_lower = publisher.lower()
        results = [e for e in results if pub_lower in e.get("publisher", "").lower()]
    if submission_system:
        sys_lower = submission_system.lower()
        results = [e for e in results if sys_lower in e.get("submission_system", "").lower()]

    limit = min(int(limit), 200)
    paged = results[:limit]
    return {
        "count":    len(results),
        "showing":  len(paged),
        "journals": [
            {
                "name":              e.get("name"),
                "publisher":         e.get("publisher"),
                "submission_system": e.get("submission_system"),
                "impact_factor":     e.get("impact_factor"),
            }
            for e in paged
        ],
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

    Verifies word count, abstract length, required sections, reference count,
    figure count, data availability statement, and TheraSIK QA gate status.

    Args:
        project_dir:  Path to the manuscript project directory.
        article_type: Override article type (Article, Letter, Review, etc.).

    Returns:
        dict with status (PASS/FAIL/WARN), checks list, submission_system, word_count.
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
        return subprep.generate_cover_letter(project_dir, corresponding_author=corresponding_author)
    except Exception as exc:
        return {"error": str(exc)}


@mcp.tool()
def get_submission_system_guide(system_name: str) -> dict:
    """
    Return step-by-step submission instructions for a specific platform.

    Covers: ScholarOne, Editorial Manager, eJournalPress, Frontiers, Snapp,
    Bench>Press, EVISE, ScienceSubmit, PeerJ, F1000Research.

    Args:
        system_name: Platform name (case-insensitive partial match).

    Returns:
        Full platform guide with checklist, file order, figure format, notes.
    """
    if subprep is None:
        return {"error": "submission_prep module not available"}
    _lic = _validate_license()
    if not _lic.get("valid"):
        return {"error": "License validation failed", "detail": _lic}
    try:
        return subprep.get_system_guide(system_name)
    except Exception as exc:
        return {"error": str(exc)}


@mcp.tool()
def run_multi_expert_review(
    project_dir: str,
    reviewers: list[str] | None = None,
) -> dict:
    """
    Run multi-expert manuscript review from three independent reviewer roles.

    Rule-based heuristics (no LLM API calls):
      - Statistician: statistical tests, p-values, effect sizes, corrections,
                      sample size/power analysis, reproducibility
      - Domain Expert: overclaiming, causal language, hypothesis framing,
                       limitations, alternative explanations, novelty
      - Editor:        word count, sections, references, figures, declarations
                       (COI, Data Availability, Ethics, Funding)

    Source-bounded — findings reference only manuscript content.
    No accept/reject predictions.

    Output: {project_dir}/03_QA/multi_expert_review_QA.md

    Args:
        project_dir: Path to manuscript project directory.
        reviewers:   Subset to run, e.g. ["statistician", "editor"].
                     Default: all three.

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
        result = mer.run_full_review(project_dir, reviewers=reviewers)
        result["report_path"] = str(
            Path(project_dir) / "03_QA" / "multi_expert_review_QA.md"
        )
        return result
    except Exception as exc:
        return {"error": str(exc)}


@mcp.tool()
def validate_skill_installation(skill_dir: str | None = None) -> dict:
    """
    Validate that the TheraSIK skill is correctly installed.

    Args:
        skill_dir: Override skill root path (default: auto-detected).

    Returns:
        dict with valid (bool), status (PASS/FAIL), and errors list.
    """
    import subprocess as sp
    target = str(skill_dir or SKILL_DIR)
    cmd    = [sys.executable, str(SCRIPTS_DIR / "validate_basic_skill.py"), target]
    r      = sp.run(cmd, capture_output=True, text=True, cwd=str(SKILL_DIR))
    errors = [ln for ln in r.stdout.splitlines() if ln.startswith("FAIL:")]
    return {
        "valid":  r.returncode == 0,
        "status": "PASS" if r.returncode == 0 else "FAIL",
        "errors": errors,
        "stdout": r.stdout.strip(),
    }


# ── Manuscript planning + search + stat figures ───────────────────────────────

try:
    import manuscript_planner as msplan
except ImportError:
    msplan = None  # type: ignore

try:
    import similar_search as simsearch
except ImportError:
    simsearch = None  # type: ignore

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
def find_similar_papers(
    query: str,
    db_path: str | None = None,
    top_k: int = 10,
    year_from: int | None = None,
    year_to: int | None = None,
    journal_filter: str | None = None,
) -> dict:
    """
    Find papers in the local literature database similar to a query text.

    Uses TF-IDF cosine similarity (60%) + BM25 (40%) ranking.
    Works offline — no API calls required.

    Args:
        query:         Query text: abstract, paragraph, keyword list, or topic.
        db_path:       Override database path.
        top_k:         Number of results (default 10, max 50).
        year_from:     Filter papers published from this year.
        year_to:       Filter papers published up to this year.
        journal_filter: Case-insensitive substring filter on journal name.

    Returns:
        dict with count and papers list (each with similarity_score, match_terms).
    """
    if simsearch is None:
        return {"error": "similar_search module not available"}
    _lic = _validate_license()
    if not _lic.get("valid"):
        return {"error": "License validation failed", "detail": _lic}
    try:
        results = simsearch.find_similar_papers(
            query, db_path=db_path, top_k=min(int(top_k), 50),
            year_from=year_from, year_to=year_to, journal_filter=journal_filter,
        )
        return {"count": len(results), "papers": results}
    except FileNotFoundError as exc:
        return {"error": str(exc)}
    except Exception as exc:
        return {"error": str(exc)}


@mcp.tool()
def generate_stat_figure(
    plot_type: str,
    data: dict,
    output_path: str,
) -> dict:
    """
    Generate a publication-quality statistical figure.

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
    PNG output is at 300 DPI (journal-ready).

    Args:
        plot_type:   Plot type string (see above).
        data:        Data specification dict. Structure varies by type;
                     see stat_plots.py docstrings for each format.
        output_path: Absolute path for the output figure file.

    Returns:
        dict with output_path (str) and success (bool), or error.
    """
    if statplots is None:
        return {"error": "stat_plots module not available. Install matplotlib: pip install matplotlib"}
    _lic = _validate_license()
    if not _lic.get("valid"):
        return {"error": "License validation failed", "detail": _lic}
    try:
        return statplots.generate_figure(plot_type, data, output_path)
    except Exception as exc:
        return {"error": str(exc)}


# ── Entry point ───────────────────────────────────────────────────────────────

if __name__ == "__main__":
    mcp.run(transport="stdio")
