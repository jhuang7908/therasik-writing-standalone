"""
Deployment locale for **customer-facing** VH/VL reports (distinct from pipeline i18n).

**Site IDs (recommended)**

- ``INSYNBIO_PUBLIC_SITE=insynbio`` — English public site (English customers; API forces
  ``report_language=en``).

- ``INSYNBIO_PUBLIC_SITE=therasik`` — Chinese public site ( honors ``VHVLRequest.report_language``
  ``en`` | ``zh``, default ``zh``).

If ``INSYNBIO_PUBLIC_SITE`` is unset, ``INSYNBIO_PUBLIC_LOCALE`` is used: ``en`` (default) or ``zh``.

**Workflow:** Iterate on the English console and API with defaults (``en`` / insynbio). After QA,
set ``INSYNBIO_PUBLIC_SITE=therasik`` (or ``INSYNBIO_PUBLIC_LOCALE=zh``) for TheraSIK-facing Chinese delivery.
"""
from __future__ import annotations

import os
from typing import Optional

__all__ = ["public_locale", "public_site_name", "resolve_vhvl_report_language"]


def public_locale() -> str:
    """``en`` = InSynBio-style English delivery; ``zh`` = TheraSIK-style Chinese-capable delivery."""
    site = (os.environ.get("INSYNBIO_PUBLIC_SITE") or "").strip().lower()
    if site in ("insynbio", "in-synbio"):
        return "en"
    if site in ("therasik", "thera-sik", "thera_sik"):
        return "zh"
    v = (os.environ.get("INSYNBIO_PUBLIC_LOCALE") or "en").strip().lower()
    if v in ("zh", "zh-cn", "cn", "chinese", "china"):
        return "zh"
    return "en"


def public_site_name() -> str:
    """Marketing site id for UI: ``insynbio`` (English) or ``therasik`` (Chinese)."""
    site = (os.environ.get("INSYNBIO_PUBLIC_SITE") or "").strip().lower()
    if site in ("insynbio", "in-synbio"):
        return "insynbio"
    if site in ("therasik", "thera-sik", "thera_sik"):
        return "therasik"
    return "therasik" if public_locale() == "zh" else "insynbio"


def resolve_vhvl_report_language(req_value: Optional[str]) -> str:
    """Effective client report language for a VH/VL job."""
    if public_locale() == "en":
        return "en"
    rl = (req_value or "zh").strip().lower()
    if rl in ("zh", "zh-cn", "cn"):
        return "zh"
    if rl in ("en", "english"):
        return "en"
    return "zh"
