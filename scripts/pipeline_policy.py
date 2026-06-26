#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
pipeline_policy.py — runtime policy loader from standards SSOT
"""
from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Dict

_SUITE_ROOT = Path(__file__).resolve().parents[1]
_SSOT_PATH = _SUITE_ROOT / "config" / "standards_ssot.json"


def load_standards_ssot() -> Dict[str, Any]:
    return json.loads(_SSOT_PATH.read_text(encoding="utf-8"))


def get_runtime_policy(source_type: str) -> Dict[str, Any]:
    ssot = load_standards_ssot()
    policies = ssot.get("runtime_policies") or {}
    if source_type not in policies:
        raise KeyError(f"runtime policy not found for source_type={source_type!r}")
    return policies[source_type]


def get_standard_entry(standard_id: str) -> Dict[str, Any]:
    ssot = load_standards_ssot()
    for item in ssot.get("standards") or []:
        if item.get("id") == standard_id:
            return item
    raise KeyError(f"standard_id not found in SSOT: {standard_id!r}")


def get_policy_with_standard(source_type: str) -> Dict[str, Any]:
    policy = dict(get_runtime_policy(source_type))
    policy["standard"] = get_standard_entry(str(policy.get("standard_id") or ""))
    return policy

