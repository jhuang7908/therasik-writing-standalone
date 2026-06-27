"""
mcp_app.py — TheraSIK cloud MCP endpoint (fastmcp 0.4.1 / mcp 1.10.1).

Architecture:
  - Cloud auth/rate-limit is handled upstream by main.py middleware.
  - This module exposes tools via SSE transport for remote agents.
  - Tools from the local writing suite are imported selectively; functions
    with union-type annotations (str | None) are wrapped with simple defaults
    to avoid mcp-SDK issubclass() bug on Python 3.12.

TOOLS_PATH layout (therasik-writing-standalone at /opt/therasik-mcp):
  /opt/therasik-mcp/
    scripts/          ← writing suite scripts
    server/
      api/
        mcp_app.py    ← this file  (../../scripts → /opt/therasik-mcp/scripts)
"""
from __future__ import annotations

import os
import sys
import logging

logger = logging.getLogger("therasik.mcp_app")

# ── Tool path ─────────────────────────────────────────────────────────────────
TOOLS_PATH = os.environ.get(
    "TOOLS_PATH",
    os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", "scripts")),
)
if os.path.isdir(TOOLS_PATH) and TOOLS_PATH not in sys.path:
    sys.path.insert(0, TOOLS_PATH)

os.environ.setdefault("THERASIK_CLOUD_MODE", "1")

# ── FastMCP server ─────────────────────────────────────────────────────────────
from fastmcp import FastMCP

mcp = FastMCP("TheraSIK Writing Engine")

# ── Minimal always-available tools ────────────────────────────────────────────
@mcp.tool()
def server_status() -> dict:
    """Return cloud server status and tool diagnostics."""
    return {
        "status": "running",
        "tools_path": TOOLS_PATH,
        "tools_path_exists": os.path.isdir(TOOLS_PATH),
        "cloud_mode": os.environ.get("THERASIK_CLOUD_MODE"),
    }


# ── Selective tool import from writing suite ──────────────────────────────────
# Only import tools whose signatures are compatible with mcp 1.10.1's
# Tool.from_function (no union-type annotations in top-level params).
_IMPORT_ERRORS: list[str] = []

def _safe_register(name: str, fn):
    """Register fn as an MCP tool; skip on any error."""
    try:
        mcp.tool()(fn)
        logger.info(f"[therasik] Registered tool: {name}")
    except Exception as exc:
        _IMPORT_ERRORS.append(f"{name}: {exc}")
        logger.warning(f"[therasik] Skipped tool {name}: {exc}")


try:
    import mcp_server as _ms  # noqa: F401 — triggers tool registration on _ms.mcp

    # ── Re-export safe tool functions ─────────────────────────────────────────
    # These functions only use basic type annotations (str, int, bool, dict).
    _SAFE_TOOLS = [
        "get_journal_requirements",
        "list_journals",
        "search_literature",
        "get_submission_system_guide",
        "list_projects",
        "get_project_status",
        "get_manuscript",
    ]
    import inspect as _inspect
    for _name in _SAFE_TOOLS:
        _fn = getattr(_ms, _name, None)
        if _fn and callable(_fn):
            _safe_register(_name, _fn)

    logger.info(f"[therasik] Tool import done. Errors: {_IMPORT_ERRORS or 'none'}")

except Exception as _exc:
    logger.warning(f"[therasik] mcp_server import skipped: {_exc}")
    _IMPORT_ERRORS.append(str(_exc))


# ── Build SSE ASGI app (fastmcp 0.4.1 pattern) ───────────────────────────────
from mcp.server.sse import SseServerTransport
from starlette.applications import Starlette
from starlette.routing import Route


def _build_sse_app() -> Starlette:
    sse = SseServerTransport("/mcp/messages")

    async def handle_sse(request):
        async with sse.connect_sse(
            request.scope, request.receive, request._send
        ) as streams:
            await mcp._mcp_server.run(
                streams[0],
                streams[1],
                mcp._mcp_server.create_initialization_options(),
            )

    async def handle_messages(request):
        await sse.handle_post_message(request.scope, request.receive, request._send)

    return Starlette(
        routes=[
            Route("/mcp/sse",      endpoint=handle_sse),
            Route("/mcp/messages", endpoint=handle_messages, methods=["POST"]),
        ],
    )


mcp_asgi_app = _build_sse_app()
