#!/usr/bin/env python3
"""
Smoke test + Markdown report: three Natural-384 discovery_platform subsets vs frozen gates.

Uses the same core path as POST /cmc/igg (fast modules + build_regular_ab_developability).
Does not run Fv structure prediction (optional offline follow-up).

Usage:
  python scripts/run_natural384_platform_cmc_demo_report.py --out reports/natural384_platform_cmc_demo.md
"""
from __future__ import annotations

import argparse
import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List

ROOT = Path(__file__).resolve().parents[1]

CASES: List[Dict[str, str]] = [
    {
        "id": "natural384_transgenic_animal",
        "label": "Briakinumab (Natural-384 transgenic-animal subset)",
        "antibody_type": "natural384_transgenic_animal",
        "vh": (
            "QVQLVESGGGVVQPGRSLRLSCAASGFTFSSYGMHWVRQAPGKGLEWVAFIRYDGSNKYYADSVKGRFTISRDNSKNTLYLQMNSLRAEDTAVYYCKTHGSHDNWGQGTMVTVSS"
        ),
        "vl": (
            "QSVLTQPPSVSGAPGQRVTISCSGSRSNIGSNTVKWYQQLPGTAPKLLIYYNDQRPSGVPDRFSGSKSGTSASLAITGLQAEDEADYYCQSYDRYTHPALLFGTGTKVTVL"
        ),
    },
    {
        "id": "natural384_phage_display",
        "label": "Adalimumab (Natural-384 phage-display subset)",
        "antibody_type": "natural384_phage_display",
        "vh": (
            "EVQLVESGGGLVQPGRSLRLSCAASGFTFDDYAMHWVRQAPGKGLEWVSAITWNSGHIDYADSVEGRFTISRDNAKNSLYLQMNSLRAEDTAVYYCAKVSYLSTASSLDYWGQGTLVTVSS"
        ),
        "vl": (
            "DIQMTQSPSSLSASVGDRVTITCRASQGIRNYLAWYQQKPGKAPKLLIYAASTLQSGVPSRFSGSGSGTDFTLTISSLQPEDVATYYCQRYNRAPYTFGQGTKVEIK"
        ),
    },
    {
        "id": "natural384_human_b_cell_derived",
        "label": "Actoxumab (Natural-384 human B-cell-derived subset)",
        "antibody_type": "natural384_human_b_cell_derived",
        "vh": (
            "QVQLVESGGGVVQPGRSLRLSCAASGFSFSNYGMHWVRQAPGKGLEWVALIWYDGSNEDYTDSVKGRFTISRDNSKNTLYLQMNSLRAEDTAVYYCARWGMVRGVIDVFDIWGQGTVVTVSS"
        ),
        "vl": (
            "DIQMTQSPSSVSASVGDRVTITCRASQGISSWLAWYQHKPGKAPKLLIYAASSLQSGVPSRFSGSGSGTDFTLTISSLQPEDFATYYCQQANSFPWTFGQGTKVEIK"
        ),
    },
]


def _fmt_params_short(parameters: List[Dict[str, Any]], *, keys: List[str]) -> str:
    lines = []
    by_k = {p.get("key"): p for p in parameters if isinstance(p, dict)}
    for k in keys:
        p = by_k.get(k) or {}
        nr = p.get("normal_range") or "—"
        val = p.get("value")
        risk = p.get("risk") or "—"
        gate = p.get("gate_status") or "—"
        lines.append(f"| {k} | {val} | {nr} | {risk} | {gate} |")
    return "\n".join(lines)


def run_case(case: Dict[str, str]) -> Dict[str, Any]:
    from core.evaluation.evaluator import AbEvaluator, AntibodyType

    ab_type_map = {
        "natural384_transgenic_animal": AntibodyType.FULLY_HUMAN,
        "natural384_phage_display": AntibodyType.FULLY_HUMAN,
        "natural384_human_b_cell_derived": AntibodyType.FULLY_HUMAN,
    }
    at = case["antibody_type"]
    ev = AbEvaluator(
        project_name="natural384_platform_demo",
        ab_type=ab_type_map[at],
        vh_seq=case["vh"].strip().upper(),
        vl_seq=case["vl"].strip().upper(),
        strict_qa=False,
    )
    result = ev.run(modules=["developability", "cdr_scan", "germline", "cmc_advisor"])
    cdr = result.results.get("cdr_scan", {}) or {}
    liab_list = cdr.get("liabilities", []) or []
    cmc_adv = result.results.get("cmc_advisor", {}) or {}
    adv_metrics = cmc_adv.get("metrics", {}) or {}
    raw_metrics = {
        k: (v.get("value") if isinstance(v, dict) else v)
        for k, v in adv_metrics.items()
    }

    def _merge_suggestions_from_gates() -> list:
        base: list = list(cmc_adv.get("mutation_suggestions", []) or [])
        if base:
            return base
        out: list = []
        for mkey, minfo in adv_metrics.items():
            if not isinstance(minfo, dict):
                continue
            g = str(minfo.get("gate", "")).upper()
            if g in ("WARN", "FAIL"):
                out.append({"metric": mkey, "target_metric": mkey, "gate": g})
        return out

    merged = _merge_suggestions_from_gates()
    from core.cmc.regular_ab_developability import build_regular_ab_developability

    germ = result.results.get("germline", {}) or {}
    rab = build_regular_ab_developability(
        vh_seq=case["vh"].strip().upper(),
        vl_seq=case["vl"].strip().upper(),
        origin=at,
        raw_metrics=raw_metrics,
        cdr_liabilities=liab_list,
        germline=germ,
        mutation_suggestions=merged,
        fv_pdb_path=None,
    )
    return {
        "clinical_score": result.clinical_score,
        "overall_status": result.overall_status,
        "regular_ab_developability": rab,
        "mutation_suggestions_source_count": len(merged),
    }


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--out", type=Path, default=ROOT / "reports" / "natural384_platform_cmc_demo.md")
    args = ap.parse_args()
    args.out.parent.mkdir(parents=True, exist_ok=True)

    ts = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
    chunks: List[str] = []
    chunks.append("# Natural-384 platform subset — IgG CMC demo report\n\n")
    chunks.append(f"Generated (UTC): `{ts}`  \n")
    chunks.append(
        "Protocol: same as `POST /cmc/igg` fast modules "
        "(`developability`, `cdr_scan`, `germline`, `cmc_advisor`) + "
        "`build_regular_ab_developability`. **No Fv PDB** in this batch — structural tiles stay NOT_RUN unless modeled separately.\n\n"
    )
    chunks.append(
        "## Verification status\n\n"
        "- `[verified]` Each row uses frozen subset stats from `data/reference/Natural384_subset_*_stats_v1.json` "
        "when present; `reference_context` in JSON names the active file.\n"
        "- `[user-provided]` Demo VH/VL sequences match `api/static/console.html` Natural-384 demos.\n\n"
    )

    json_dump: Dict[str, Any] = {"generated_at": ts, "cases": []}

    for case in CASES:
        payload = run_case(case)
        rab = payload["regular_ab_developability"]
        json_dump["cases"].append({"case_id": case["id"], "payload": payload})
        rc = rab.get("reference_context") or {}
        ob = rc.get("origin_benchmark") or {}
        prim = rc.get("primary_stats_file") or "—"
        params = rab.get("parameters") or []
        sugg = rab.get("fr_modification_suggestions") or []

        chunks.append(f"## {case['label']}\n\n")
        chunks.append(f"- **antibody_type:** `{case['antibody_type']}`\n")
        chunks.append(f"- **benchmark_mode:** `{ob.get('benchmark_mode', '—')}`\n")
        chunks.append(f"- **primary_stats_file (engine):** `{prim}`\n")
        chunks.append(f"- **developability_index / ADI:** `{rab.get('developability_index')}`  \n")
        chunks.append(f"- **risk_level:** `{rab.get('risk_level')}`  \n")
        chunks.append(f"- **overall_gate_status:** `{rab.get('overall_gate_status')}`  \n")
        hard = rab.get("hard_gate_failures") or []
        if hard:
            chunks.append(f"- **hard_gate_failures:** `{', '.join(str(x.get('key')) for x in hard)}`  \n")
        chunks.append(f"- **clinical_score (AbRef-style composite):** `{payload.get('clinical_score')}`  \n")
        chunks.append(f"- **evaluator overall_status:** `{payload.get('overall_status')}`  \n\n")

        chunks.append("### Sample metrics vs normal range (p5–p95)\n\n")
        chunks.append("| Metric | Value | Normal range | Risk | Gate |\n|---|---|---|---|---|\n")
        chunks.append(
            _fmt_params_short(
                params,
                keys=["pI", "GRAVY", "SAP_score", "instability_index", "hydro_patch_max9", "Fv_charge_asymmetry"],
            )
        )
        chunks.append("\n\n")

        chunks.append("### FR-only engineering actions (policy)\n\n")
        chunks.append(
            "Automated suggestions are **framework-only**; CDR findings remain advisory per "
            "`data/rules/cmc_mutation_policy_v1_2.json` and `cmc-mutation-policy` skill.\n\n"
        )
        if not sugg:
            chunks.append("*No FR modification suggestions in this run (gates mostly PASS or no HIGH targets).* \n\n")
        else:
            chunks.append(f"*{len(sugg)} suggestion row(s); excerpt:*\n\n")
            for i, s in enumerate(sugg[:8]):
                chunks.append(
                    f"{i + 1}. **{s.get('target', s.get('metric_key', '?'))}** — "
                    f"{s.get('recommendation', s.get('priority', ''))}\n"
                )
            if len(sugg) > 8:
                chunks.append(f"\n… +{len(sugg) - 8} more.\n")
            chunks.append("\n")

        notes = rab.get("source_specific_notes") or []
        if notes:
            chunks.append("### Source notes\n\n")
            for n in notes:
                chunks.append(f"- ({n.get('level')}) {n.get('text')}\n")
            chunks.append("\n")

    chunks.append("## Adversarial checks\n\n")
    chunks.append(
        "- **Subset n (especially human B-cell ≈39):** outer quantiles are noisy — `[inferred]` wide WARN bands possible; "
        "same numeric gate logic as engine — **PASS** for transparency.\n"
        "- **No structure in this script:** psh/ppc/pnc/Vernier metrics may be NOT_RUN — conclusions are sequence-heavy — **WARN**.\n"
        "- **Clinical_score** remains AbRef-style composite; it does not replace subset gates — **PASS**.\n\n"
    )
    chunks.append("## Sources\n\n")
    chunks.append(
        "- `core/cmc/regular_ab_developability.py` — origin routing and frozen references.\n"
        "- `data/reference/Natural384_subset_*_stats_v1.json` — subset distributions.\n"
        "- `api/static/console.html` — demo VH/VL sequences.\n\n"
    )

    args.out.write_text("".join(chunks), encoding="utf-8")
    sidecar = args.out.with_suffix(".json")
    sidecar.write_text(json.dumps(json_dump, indent=2, ensure_ascii=False), encoding="utf-8")
    print(f"Wrote {args.out}")
    print(f"Wrote {sidecar}")


if __name__ == "__main__":
    main()
