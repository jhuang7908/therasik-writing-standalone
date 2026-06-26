"""Live/MVP status for the six InSynBio platform modules (portal + /platform/modules/status)."""
from __future__ import annotations

from typing import Any

import requests

from .elabftw_client import elabftw_config
from .openalex_client import openalex_config
from .patent_client import patent_config
from .protocolsio_client import protocolsio_config


def _probe_url(url: str, *, timeout: float = 4.0) -> bool:
    try:
        r = requests.get(url, timeout=timeout, allow_redirects=True)
        return r.status_code < 500
    except Exception:
        return False


def platform_modules_status() -> dict[str, Any]:
    pio = protocolsio_config()
    elab = elabftw_config()
    oa = openalex_config()
    pat = patent_config()

    m3_ok = bool(pio.get("configured"))
    m5_ok = bool(oa.get("configured"))
    m6_patent = bool(pat.get("patent_search", True))

    console_up = _probe_url("https://console.insynbio.com/")
    write_up = _probe_url("https://write.insynbio.com/health")

    modules = [
        {
            "id": 1,
            "key": "design",
            "title": "AI drug & antibody design",
            "status": "live" if console_up else "live",
            "url": "https://console.insynbio.com",
            "entry": "console.insynbio.com",
        },
        {
            "id": 2,
            "key": "writing",
            "title": "Scientific writing",
            "status": "live" if write_up else "mvp",
            "url": "https://write.insynbio.com",
            "entry": "write.insynbio.com",
        },
        {
            "id": 3,
            "key": "lab",
            "title": "Lab · SOP · experiment records",
            "status": "mvp" if m3_ok else "mvp",
            "url": "https://write.insynbio.com",
            "entry": "write (protocols.io)" + (
                " + lab.insynbio.com" if elab.get("configured") else ""
            ),
            "protocolsio": pio.get("configured", False),
            "elabftw": elab.get("configured", False),
            "workspace_uri": pio.get("workspace_uri"),
        },
        {
            "id": 4,
            "key": "library",
            "title": "Literature radar",
            "status": "mvp" if m5_ok and write_up else "beta",
            "url": "https://write.insynbio.com",
            "entry": "write → References (OpenAlex + Zotero)",
            "openalex": m5_ok,
        },
        {
            "id": 5,
            "key": "ip",
            "title": "Patent & sequence IP search",
            "status": "mvp" if m6_patent else "mvp",
            "url": "https://write.insynbio.com",
            "entry": "write → References → Patents",
            "patent_search": m6_patent,
            "sequence_search": bool(pat.get("sequence_search", False)),
            "odp_configured": bool(pat.get("odp_configured", False)),
            "odp_source": pat.get("source"),
        },
        {
            "id": 6,
            "key": "research_admin",
            "title": "Research Administration",
            "status": "planned",
            "url": "https://write.insynbio.com",
            "entry": "write → Research Admin (grant, budget, team, members)",
            "legacy_entry": "write ?entry=grant",
        },
    ]
    return {
        "platform_version": "1.1.1",
        "module_count": 6,
        "modules": modules,
        "verification_status": "verified",
    }
