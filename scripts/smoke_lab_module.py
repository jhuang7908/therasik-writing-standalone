#!/usr/bin/env python3
"""Lab module functional smoke test.

Covers:
1) protocols.io search/import
2) SOP generation path (agent_chat + save_sop)
3) experiment design records
4) AI analysis + HTML report archive
5) reagent classification/records
6) resources list + booking capability probe

This script runs against live write API and performs best-effort cleanup.
"""
from __future__ import annotations

import json
import os
import sys
import time
from dataclasses import dataclass, field
from datetime import datetime, timedelta, timezone
from typing import Any

import requests


BASE = os.environ.get("LAB_SMOKE_BASE", "https://write.insynbio.com").rstrip("/")
TIMEOUT = float(os.environ.get("LAB_SMOKE_TIMEOUT", "45"))
PREFIX = f"SMOKE_{datetime.now(timezone.utc).strftime('%Y%m%d_%H%M%S')}"
PROJECT_ID = os.environ.get("LAB_SMOKE_PROJECT_ID", "smoke_lab_project")


@dataclass
class SmokeResult:
    name: str
    status: str
    details: str
    evidence: dict[str, Any] = field(default_factory=dict)


def _request(
    method: str,
    path: str,
    *,
    payload: dict[str, Any] | None = None,
    params: dict[str, Any] | None = None,
) -> tuple[int, Any]:
    url = f"{BASE}{path}"
    resp = requests.request(
        method=method,
        url=url,
        json=payload,
        params=params,
        timeout=TIMEOUT,
    )
    try:
        data = resp.json()
    except Exception:
        data = resp.text
    return resp.status_code, data


def _ok(status: int) -> bool:
    return 200 <= status < 300


def main() -> int:
    results: list[SmokeResult] = []
    created_experiments: list[str] = []
    created_items: list[str] = []
    created_resources: list[str] = []
    created_data_entries: list[str] = []
    created_sops: list[str] = []
    created_report_ids: list[str] = []
    created_bookings: list[str] = []

    # 0) Sanity
    code, cfg = _request("GET", "/lab/config")
    if not _ok(code):
        print(json.dumps({"fatal": f"/lab/config failed HTTP {code}", "body": cfg}, ensure_ascii=False, indent=2))
        return 2
    if not isinstance(cfg, dict) or not cfg.get("configured"):
        print(json.dumps({"fatal": "Lab backend not configured", "config": cfg}, ensure_ascii=False, indent=2))
        return 2
    results.append(SmokeResult("lab_config", "PASS", "Lab backend configured", {"tenant": cfg.get("tenant_id")}))

    # 1) protocols.io search/import (3 queries)
    proto_queries = [
        "western blot antibody",
        "ELISA binding assay",
        "qPCR sample preparation",
    ]
    proto_hits: dict[str, int] = {}
    proto_import_ok = 0
    for q in proto_queries:
        code, out = _request("POST", "/protocolsio/search", payload={"query": q, "limit": 5})
        if not _ok(code):
            results.append(SmokeResult("protocol_search", "FAIL", f"search failed for '{q}' HTTP {code}", {"body": out}))
            continue
        items = []
        if isinstance(out, dict):
            items = out.get("items") or out.get("results") or out.get("protocols") or out.get("curated") or []
        proto_hits[q] = len(items)
        code2, out2 = _request(
            "POST",
            "/protocolsio/import_to_facts",
            payload={"query": q, "limit": 3, "fetch_steps_for_top": 1, "project_id": PROJECT_ID},
        )
        if _ok(code2) and isinstance(out2, dict) and (out2.get("facts_block") or out2.get("steps_markdown")):
            proto_import_ok += 1
    min_hits = sum(1 for _, n in proto_hits.items() if n > 0)
    if min_hits >= 2 and proto_import_ok >= 2:
        results.append(
            SmokeResult(
                "protocol_search_import",
                "PASS",
                "protocols.io search/import works for >=2/3 queries",
                {"hits": proto_hits, "imports_ok": proto_import_ok},
            )
        )
    else:
        results.append(
            SmokeResult(
                "protocol_search_import",
                "WARN",
                "protocols.io partially available",
                {"hits": proto_hits, "imports_ok": proto_import_ok},
            )
        )

    # 2) SOP generation path (agent_chat + save_sop) with 3 instances
    sop_templates = [
        "VHH purification",
        "ELISA binding",
        "qPCR prep",
    ]
    sop_saved = 0
    for t in sop_templates:
        title = f"{PREFIX}_SOP_{t.replace(' ', '_')}"
        prompt = (
            "Draft SOP sections in plain text with headers: "
            "Purpose & Scope, Materials & Equipment, Procedure, QC & Acceptance, Safety & Waste, Revision Log. "
            f"Topic: {t}"
        )
        code_ai, ai = _request("POST", "/agent_chat", payload={"message": prompt, "project_id": PROJECT_ID})
        ai_text = ""
        if _ok(code_ai) and isinstance(ai, dict):
            ai_text = (ai.get("reply") or ai.get("content") or "").strip()
        sections = {
            "purpose": f"{t} purpose",
            "materials": "Antibody, buffer, tubes",
            "procedure": ai_text[:1500] if ai_text else f"Procedure for {t}",
            "qc": "Check controls pass.",
            "safety": "Use PPE.",
            "revision": "v1.0",
        }
        code_s, out_s = _request(
            "POST",
            "/lab/save_sop",
            payload={"title": title, "sections": sections, "entity": "experiments", "project_id": PROJECT_ID},
        )
        if _ok(code_s) and isinstance(out_s, dict) and out_s.get("id"):
            sop_saved += 1
            created_sops.append(str(out_s["id"]))
    results.append(
        SmokeResult(
            "sop_generation_save",
            "PASS" if sop_saved >= 2 else "WARN",
            f"SOP save success {sop_saved}/3",
            {"saved": sop_saved},
        )
    )

    # 3) Experiment design records (3 instances)
    exp_saved = 0
    for idx in range(1, 4):
        title = f"{PREFIX}_EXP_{idx}"
        body_html = (
            "<h3>Study Information</h3>"
            f"<p>Record ID: SMOKE-EXP-{idx}<br>Category: DesignPlan<br>"
            "Project / program: Smoke Lab Validation<br>Study phase: Discovery<br>"
            "Run status: Planned<br>Lead scientist: Smoke Tester<br>"
            "Assay type: Analytical QC<br>Model system: In vitro (biochemical)</p>"
            "<h3>Protocol followed</h3><p>Smoke test SOP reference; replace with saved SOP in production.</p>"
            "<h3>Objective / Hypothesis</h3><p>Objective: test condition and outcome. "
            "Hypothesis: pH condition affects yield relative to control.</p>"
            "<h3>Experimental Design</h3><p>Experimental groups / arms: control; pH 6.5; pH 7.5<br>"
            "Independent variables: pH<br>Dependent variables / readouts: yield mg/L<br>"
            "Controls: process control<br>Sample size (n per group): n=3<br>"
            "Replicates: 3 technical replicates<br>Randomization / blinding: not required for smoke test<br>"
            "Design notes: smoke test record.</p>"
            "<h3>Design Data & Attachments</h3><p><strong>Manual entry</strong></p>"
            "<pre style=\"white-space:pre-wrap;font-family:inherit;font-size:12px;background:#f7f7f7;padding:10px;border-radius:6px\">"
            "Group\tYield mg/L\nControl\tTBD\npH 6.5\tTBD\npH 7.5\tTBD</pre>"
            "<h3>Resources Used</h3><p>Reagents:<br>Smoke buffer lot TBD<br>Instrument/Booking:<br>Smoke instrument TBD</p>"
            "<h3>Execution Notes</h3><p>SOP deviations: none<br>Environmental conditions: record at run time<br>"
            "Execution window: record after run</p>"
            "<h3>Success Criteria / Readout</h3><p>Yield > 5 mg/L; controls pass.</p>"
            "<h3>Raw Data Reference</h3><p>Upload CSV/XLSX after run.</p>"
        )
        code_c, out_c = _request(
            "POST",
            "/lab/create_entry",
            payload={
                "entity": "experiments",
                "title": title,
                "body": body_html,
                "category": "DesignPlan",
                "tags": ["Smoke", "DesignPlan", "category:DesignPlan", "StructuredELN"],
                "project_id": PROJECT_ID,
            },
        )
        if _ok(code_c) and isinstance(out_c, dict) and out_c.get("id"):
            exp_saved += 1
            created_experiments.append(str(out_c["id"]))
    results.append(
        SmokeResult(
            "experiment_design_record",
            "PASS" if exp_saved == 3 else "WARN",
            f"Experiment create success {exp_saved}/3",
            {"created": created_experiments},
        )
    )

    # 4) Reagents classification records (3 instances)
    reagent_cases = [("Antibody", "Anti-His HRP"), ("Chemical", "NaCl"), ("Kit", "qPCR kit")]
    reg_saved = 0
    for cat, name in reagent_cases:
        title = f"{PREFIX}_REAG_{name.replace(' ', '_')}"
        code_r, out_r = _request(
            "POST",
            "/lab/create_entry",
            payload={
                "entity": "items",
                "title": title,
                "body": "Supplier: demo; Lot: 001",
                "category": cat,
                "tags": ["Reagent", cat, "Smoke"],
                "project_id": PROJECT_ID,
            },
        )
        if _ok(code_r) and isinstance(out_r, dict) and out_r.get("id"):
            reg_saved += 1
            created_items.append(str(out_r["id"]))
    code_b, browse = _request(
        "POST",
        "/lab/entries",
        payload={"entity": "items", "limit": 50, "search": PREFIX, "tag_filter": "reagent", "project_id": PROJECT_ID},
    )
    categories_seen = []
    if _ok(code_b) and isinstance(browse, dict):
        categories_seen = [str(e.get("category") or "") for e in (browse.get("entries") or [])]
    results.append(
        SmokeResult(
            "reagent_classification_records",
            "PASS" if reg_saved >= 2 and len(categories_seen) >= 2 else "WARN",
            f"Reagent create {reg_saved}/3; browse returned {len(categories_seen)} records",
            {"categories_seen": categories_seen[:10]},
        )
    )

    # 5) Resources list + booking flow (2-3 instances)
    # Create 2 resource entries
    res_saved = 0
    for inst in ("AKTA_Pure_25", "Plate_Reader"):
        title = f"{PREFIX}_RES_{inst}"
        code_rr, out_rr = _request(
            "POST",
            "/lab/create_entry",
            payload={
                "entity": "resources",
                "title": title,
                "body": "Instrument demo",
                "category": "Instrument",
                "tags": ["Resource", "Instrument", "Smoke"],
                "project_id": PROJECT_ID,
            },
        )
        if _ok(code_rr) and isinstance(out_rr, dict) and out_rr.get("id"):
            res_saved += 1
            created_resources.append(str(out_rr["id"]))
    code_res, res_rows = _request(
        "POST",
        "/lab/entries",
        payload={"entity": "resources", "limit": 50, "search": PREFIX, "tag_filter": "resource", "project_id": PROJECT_ID},
    )
    has_resources = _ok(code_res) and isinstance(res_rows, dict) and bool(res_rows.get("entries"))

    booking_status = "WARN"
    booking_detail = "booking flow not executed"
    booking_http = None
    booking_body: Any = None
    if created_resources:
        target_item = created_resources[0]
        _request(
            "POST",
            "/lab/set_bookable",
            payload={
                "item_id": target_item,
                "is_bookable": True,
                "allow_overlap": False,
                "project_id": PROJECT_ID,
            },
        )
        start = (datetime.now(timezone.utc) + timedelta(days=1)).replace(microsecond=0).strftime("%Y-%m-%dT%H:%M:%SZ")
        end = (datetime.now(timezone.utc) + timedelta(days=1, hours=1)).replace(microsecond=0).strftime("%Y-%m-%dT%H:%M:%SZ")
        code_cb, out_cb = _request(
            "POST",
            "/lab/create_booking",
            payload={
                "item_id": target_item,
                "title": f"{PREFIX} Booking",
                "start": start,
                "end": end,
                "project_id": PROJECT_ID,
            },
        )
        booking_http = code_cb
        booking_body = out_cb
        if _ok(code_cb) and isinstance(out_cb, dict) and out_cb.get("booking_id"):
            created_bookings.append(str(out_cb["booking_id"]))
            code_lb, out_lb = _request(
                "POST",
                "/lab/bookings",
                payload={"project_id": PROJECT_ID, "item_id": target_item, "limit": 10},
            )
            if _ok(code_lb) and isinstance(out_lb, dict) and (out_lb.get("count", 0) >= 1):
                booking_status = "PASS"
                booking_detail = "booking create/list flow works"
            else:
                booking_status = "WARN"
                booking_detail = f"booking create ok but list weak HTTP {code_lb}"
        else:
            booking_status = "WARN"
            booking_detail = f"create_booking failed HTTP {code_cb}"
    results.append(
        SmokeResult(
            "resources_and_booking",
            "PASS" if has_resources and booking_status == "PASS" else "WARN",
            f"resources_ok={has_resources}; {booking_detail}",
            {"resources_created": res_saved, "booking_http": booking_http, "booking_body": booking_body},
        )
    )

    # 6) AI analysis + report generation (2 instances)
    rep_ok = 0
    for idx in range(1, 3):
        title = f"{PREFIX}_DATAREP_{idx}"
        result_blocks = [
            {
                "label": "Result A",
                "notes": "OD450: 0.12, 0.45, 0.88; control 0.10",
                "files": [{"name": "elisa_curve.png", "type": "image/png", "data_url": "data:image/png;base64,"}],
            },
            {
                "label": "Result B",
                "notes": "Yield mg/L: 3.1 vs 6.2",
                "files": [{"name": "yield_table.csv", "type": "text/csv", "data_url": "data:text/csv;base64,"}],
            },
        ]
        code_st, out_st = _request(
            "POST",
            "/lab/analyze_data",
            payload={
                "mode": "statistics",
                "title": title,
                "observations": "Smoke test observations",
                "experiment_ref": "",
                "result_blocks": result_blocks,
                "project_id": PROJECT_ID,
            },
        )
        code_ra, out_ra = _request(
            "POST",
            "/lab/analyze_data",
            payload={
                "mode": "rationality",
                "title": title,
                "observations": "Smoke test observations",
                "conclusion": "candidate improves yield",
                "experiment_ref": "",
                "result_blocks": result_blocks,
                "project_id": PROJECT_ID,
            },
        )
        if not (_ok(code_st) and _ok(code_ra)):
            continue
        stats = out_st.get("analysis", "") if isinstance(out_st, dict) else ""
        rat = out_ra.get("analysis", "") if isinstance(out_ra, dict) else ""
        code_gr, out_gr = _request(
            "POST",
            "/lab/generate_report",
            payload={
                "title": title,
                "experiment_ref": "",
                "sop_id": created_sops[0] if created_sops else None,
                "observations": "Smoke test observations",
                "result_blocks": result_blocks,
                "conclusion": "candidate improves yield",
                "qc_status": "PASS",
                "statistics_analysis": stats[:3000],
                "rationality_analysis": rat[:3000],
                "include_pubmed": True,
                "save_to_eln": True,
                "project_id": PROJECT_ID,
                "author": "Smoke Bot",
            },
        )
        if _ok(code_gr) and isinstance(out_gr, dict) and out_gr.get("report_id"):
            rep_ok += 1
            created_report_ids.append(str(out_gr["report_id"]))
            if out_gr.get("eln_id"):
                created_data_entries.append(str(out_gr["eln_id"]))
    code_pr, out_pr = _request("POST", "/lab/progress_reports", payload={"project_id": PROJECT_ID, "limit": 20})
    report_count = 0
    if _ok(code_pr) and isinstance(out_pr, dict):
        report_count = len(out_pr.get("reports") or [])
    results.append(
        SmokeResult(
            "ai_analysis_and_html_report",
            "PASS" if rep_ok >= 1 and report_count >= 1 else "WARN",
            f"generated reports={rep_ok}, archived visible={report_count}",
            {"report_ids": created_report_ids, "progress_count": report_count},
        )
    )

    # Cleanup created test entries
    for bid in created_bookings:
        _request("POST", "/lab/delete_booking", payload={"booking_id": bid, "project_id": PROJECT_ID})

    for entity, ids in (
        ("experiments", created_experiments + created_sops + created_data_entries),
        ("items", created_items + created_resources),
    ):
        for rid in ids:
            _request("POST", "/lab/delete_entry", payload={"entity": entity, "id": rid, "project_id": PROJECT_ID})

    # Summarize
    summary = {
        "base": BASE,
        "project_id": PROJECT_ID,
        "prefix": PREFIX,
        "results": [r.__dict__ for r in results],
        "totals": {
            "PASS": sum(1 for r in results if r.status == "PASS"),
            "WARN": sum(1 for r in results if r.status == "WARN"),
            "FAIL": sum(1 for r in results if r.status == "FAIL"),
        },
        "generated_at": datetime.now(timezone.utc).isoformat(),
    }
    print(json.dumps(summary, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
