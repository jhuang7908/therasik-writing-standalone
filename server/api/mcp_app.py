"""
mcp_app.py — fastmcp SSE transport bridge.

Loads the existing MCP tools from therasik-academic-writing-suite
and exposes them via HTTP/SSE so remote agents (Hermes, Cursor) can
connect with just a URL + API key — no local Python install needed.

Tool code is UNCHANGED from the local version.
Auth / rate-limiting / usage logging is handled by main.py middleware
BEFORE the request reaches this ASGI app.
"""
from __future__ import annotations

import os
import sys

# ── Add existing tools to the path ───────────────────────────────────────────
# In Docker: tools are copied into /app/tools/
# In local dev: point TOOLS_PATH to the existing scripts directory
TOOLS_PATH = os.environ.get(
    "TOOLS_PATH",
    os.path.join(
        os.path.dirname(__file__),
        "..", "..", "therasik-academic-writing-suite", "scripts"
    ),
)
if TOOLS_PATH not in sys.path:
    sys.path.insert(0, os.path.abspath(TOOLS_PATH))

# ── Build the MCP server ──────────────────────────────────────────────────────
from fastmcp import FastMCP

mcp = FastMCP("TheraSIK Writing Engine")

# ── Import tools from the existing mcp_server module ─────────────────────────
# Rather than re-implementing, we import the tool functions and register them.
# The existing mcp_server.py uses a local `mcp` instance; we re-register
# each tool onto our cloud `mcp` instance here.

_TOOL_IMPORT_ERRORS: list[str] = []

def _try_register(tool_name: str, fn):
    """Register a callable as an MCP tool, catching any import-time errors."""
    try:
        mcp.tool()(fn)
    except Exception as exc:
        _TOOL_IMPORT_ERRORS.append(f"{tool_name}: {exc}")


try:
    # Import existing tool functions directly
    # Note: the existing mcp_server.py has a local license check (_validate_license).
    # In cloud mode, all requests already passed the auth middleware, so we
    # short-circuit the license gate by setting an env flag.
    os.environ.setdefault("THERASIK_CLOUD_MODE", "1")

    import mcp_server as _ms

    # Collect all tool functions from the existing module
    import inspect
    for _name, _obj in inspect.getmembers(_ms, inspect.isfunction):
        if hasattr(_obj, "_mcp_tool") or _name.startswith("_"):
            continue
        # Only re-export public tool functions (heuristic: no leading underscore,
        # annotated or listed in MCP server's tool registry)
        _KNOWN_TOOLS = {
            "get_journal_requirements", "list_journals", "format_citations",
            "export_references", "verify_citations", "verify_citations_s2",
            "check_grammar", "run_multi_expert_review", "run_qa_gate",
            "search_literature", "generate_stat_figure", "polish_manuscript",
            "get_submission_system_guide", "create_project", "list_projects",
            "get_project_status", "save_manuscript_section", "get_manuscript",
            "run_csl_format", "scrape_journal_requirements",
        }
        if _name in _KNOWN_TOOLS:
            _try_register(_name, _obj)

    # ── Cloud override: journal tools wrapped with sanitise gate ─────────────
    # In cloud mode the raw JSON fields (_file, _source_url, etc.) must be
    # stripped before returning to the client.  We re-register the two journal
    # tools with thin wrappers that call journal_gateway.sanitise().
    try:
        from api.journal_gateway import sanitise, sanitise_list

        _orig_get   = getattr(_ms, "get_journal_requirements", None)
        _orig_list  = getattr(_ms, "list_journals", None)

        if _orig_get:
            def get_journal_requirements(journal_name: str) -> dict:
                """
                Look up submission requirements for a target journal (10,452 journals).
                Returns formatted requirements only — raw database files are not exposed.
                """
                raw = _orig_get(journal_name)
                return sanitise(raw, journal_name)
            _try_register("get_journal_requirements_cloud", get_journal_requirements)

        if _orig_list:
            def list_journals(
                search: str | None = None,
                publisher: str | None = None,
                submission_system: str | None = None,
                limit: int = 50,
            ) -> dict:
                """
                Browse all 10,452 journals. Returns journal names and key fields only.
                """
                raw = _orig_list(search=search, publisher=publisher,
                                 submission_system=submission_system, limit=limit)
                # raw is {"journals": [...], "total": N, ...}
                if "journals" in raw:
                    raw["journals"] = sanitise_list(raw["journals"])
                return raw
            _try_register("list_journals_cloud", list_journals)

        print("[therasik] Journal gateway: cloud sanitise layer active")
    except Exception as _ge:
        print(f"[therasik] WARNING: journal gateway not applied: {_ge}")

    print(f"[therasik] Loaded tools from mcp_server.py. Errors: {_TOOL_IMPORT_ERRORS or 'none'}")

except ImportError as exc:
    print(f"[therasik] WARNING: Could not import mcp_server.py: {exc}")
    print(f"[therasik] TOOLS_PATH={TOOLS_PATH}")

    # Fallback: register a single diagnostic tool so the SSE endpoint is reachable
    @mcp.tool()
    def server_status() -> dict:
        """Returns cloud server status and tool import diagnostics."""
        return {
            "status": "running",
            "tools_loaded": False,
            "tools_path": TOOLS_PATH,
            "import_errors": _TOOL_IMPORT_ERRORS,
            "message": (
                "Core tools not loaded. Check TOOLS_PATH env var or "
                "ensure mcp_server.py is in the container at the expected path."
            ),
        }


# ── Expose as ASGI app (SSE transport) ───────────────────────────────────────
# fastmcp creates a Starlette ASGI app for SSE transport.
mcp_asgi_app = mcp.get_asgi_app()
