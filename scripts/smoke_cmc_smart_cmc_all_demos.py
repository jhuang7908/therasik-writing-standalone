"""
Smoke test: exercise every CMC demo with Smart-CMC, apply each category bucket and
the Combined variant, recompute, and write a single Markdown report.

Goals
-----
1. Confirm Smart-CMC produces FR mutation suggestions for every demo it can.
2. Confirm mutations apply correctly to the sequence (sequence-level diff).
3. Confirm sequence-level metrics (pI, GRAVY, instability index, SAP score, ADI,
   plus the target metric for each category) move in the expected direction.
4. Confirm the unified strategy holds across origins (humanized, fully-human/phage,
   transgenic-derived, camelid VHH, EngVH/SCAb).
5. Surface any path where a demo has flagged liabilities but Smart-CMC fails to
   produce category mutations / verify buttons would not render.

Outputs
-------
``out/smoke/cmc_smart_cmc_<timestamp>/REPORT.md``
``out/smoke/cmc_smart_cmc_<timestamp>/<demo>_baseline.json``
``out/smoke/cmc_smart_cmc_<timestamp>/<demo>_<category>_variant.json``

Run
---
``conda activate anarcii``
``python scripts/smoke_cmc_smart_cmc_all_demos.py``

Sequence-only mode (run_structure=False) is used for speed and reproducibility.
SASA-dependent metrics (pnc/ppc/psh/SAP_sasa) are not recomputed; their baseline
flags are still surfaced but the variant deltas are reported as "structure-only".
"""
from __future__ import annotations

import json
import re
import sys
import time
import traceback
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

REPO_ROOT = Path(__file__).resolve().parents[1]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

OUT_BASE = REPO_ROOT / "out" / "smoke"
TS = datetime.now().strftime("%Y%m%d_%H%M%S")
OUT_DIR = OUT_BASE / f"cmc_smart_cmc_{TS}"
OUT_DIR.mkdir(parents=True, exist_ok=True)

# ── Demo registry (mirrors api/static/console.html DEMOS) ────────────────────
IGG_DEMOS: List[Dict[str, str]] = [
    {
        "demo_id": "toripalimab-igg",
        "label": "Toripalimab (humanized_transgenic)",
        "antibody_type": "humanized_transgenic",
        "vh": "QGQLVQSGAEVKKPGASVKVSCKASGYTFTDYEMHWVRQAPIHGLEWIGVIESETGGTAYNQKFKGRVTITADKSTSTAYMELSSLRSEDTAVYYCAREGITTVATTYYWYFDVWGQGTTVTVSS",
        "vl": "DVVMTQSPLSLPVTLGQPASISCRSSQSIVHSNGNTYLEWYLQKPGQSPQLLIYKVSNRFSGVPDRFSGSGSGTDFTLKISRVEAEDVGVYYCFQGSHVPLTFGQGTKLEIK",
    },
    {
        "demo_id": "abiprubart-engineered",
        "label": "Abiprubart (humanized engineered)",
        "antibody_type": "humanized",
        "vh": "QVQLVQSGAEVKKPGASVKVSCKASGYTFTNYWMHWVRQAPGQRLEWIGYINPSNDYTKYNQKFKDRATLTADKSANTAYMELSSLRSEDTAVYYCARQGFPYWGQGTLVTVSS",
        "vl": "EIVLTQSPATLSLSPGERATLSCSASSSVSYMHWYQQKPGQAPRRWIYDTSKLASGVPARFSGSGSGTDYTLTISSLEPEDFAVYYCHQLSSDPFTFGGGTKVEIK",
    },
    {
        "demo_id": "briakinumab-phage",
        "label": "Briakinumab (phage_display, fully_human)",
        "antibody_type": "phage_display",
        "vh": "QVQLVESGGGVVQPGRSLRLSCAASGFTFSSYGMHWVRQAPGKGLEWVAFIRYDGSNKYYADSVKGRFTISRDNSKNTLYLQMNSLRAEDTAVYYCKTHGSHDNWGQGTMVTVSS",
        "vl": "QSVLTQPPSVSGAPGQRVTISCSGSRSNIGSNTVKWYQQLPGTAPKLLIYYNDQRPSGVPDRFSGSKSGTSASLAITGLQAEDEADYYCQSYDRYTHPALLFGTGTKVTVL",
    },
]

VHH_DEMOS: List[Dict[str, str]] = [
    {
        "demo_id": "humanized-vhh-eval",
        "label": "7D12 humanized VHH",
        "sdab_origin": "camelid_vhh",
        "seq": "EVQLVESGGGLVQPGGSLRLSCAASGRTSRSYGMGWFRQAPGKEREFVAGISWRGDSTGYADSVKGRFTISRDNAKNTLYLQMNSLRAEDTAVYYCAAAAGSAWYGTLYEYDYWGQGTLVTVSS",
    },
    {
        "demo_id": "nanobody-origin-scab",
        "label": "Porustobart / HBM4003 SCAb (transgenic_sdab)",
        "sdab_origin": "transgenic_sdab",
        "seq": "EVQLVESGGGLIQPGGSLRLSCAVSGFTVSKNYMSWVRQAPGKGLEWVSVVYSGGSKTYADSVKGRFTISRDNSKNTLYLQMNSLRAEDTAVYYCARAVPHSPSSFDIWGQGTMVTVSS",
    },
]

# ── Helpers ──────────────────────────────────────────────────────────────────


def _safe(d: Optional[Dict], path: List[Any], default=None):
    """Walk a nested dict; return default if any step missing."""
    cur = d
    for p in path:
        if cur is None:
            return default
        if isinstance(cur, dict):
            cur = cur.get(p)
        elif isinstance(cur, list) and isinstance(p, int) and 0 <= p < len(cur):
            cur = cur[p]
        else:
            return default
    return cur if cur is not None else default


def _fmt(v, digits: int = 2) -> str:
    if v is None:
        return "—"
    if isinstance(v, (int, float)):
        if abs(v) < 1e-6:
            return "0"
        return f"{v:.{digits}f}"
    return str(v)


def _delta(before, after, digits: int = 2) -> str:
    if before is None or after is None:
        return "—"
    try:
        d = float(after) - float(before)
        sign = "▲ +" if d > 0 else ("▼ " if d < 0 else "→ ")
        return f"{sign}{d:.{digits}f}"
    except (TypeError, ValueError):
        return "—"


def extract_baseline_metrics(payload: Dict[str, Any]) -> Dict[str, Any]:
    """Pull the 4 miniCMC core metrics + ADI + target metrics from an IgG payload."""
    rab = payload.get("regular_ab_developability") or {}
    params = {p.get("key"): p for p in (rab.get("parameters") or []) if isinstance(p, dict)}

    def v(k):
        p = params.get(k)
        return p.get("value") if p else None

    def r(k):
        p = params.get(k)
        return (p or {}).get("risk")

    return {
        # miniCMC core (4)
        "pI": v("pI"),
        "GRAVY": v("GRAVY"),
        "instability_index": v("instability_index"),
        "SAP_score": v("SAP_score"),
        # Category targets
        "net_charge_pH7": v("net_charge_pH7"),
        "ppc": v("ppc"),
        "pnc": v("pnc"),
        "sfvcsp": v("sfvcsp"),
        "hydro_patch_max9": v("hydro_patch_max9"),
        "psh": v("psh"),
        "agg_motifs": v("agg_motifs"),
        "deamidation_sites": v("deamidation_sites"),
        "isomerization_sites": v("isomerization_sites"),
        "oxidation_sites": v("oxidation_sites"),
        "glycosylation_sites": v("glycosylation_sites"),
        "free_cys": v("free_cys"),
        # CDR Fingerprint (V1.9)
        "vh_cdr3_len": v("vh_cdr3_len"),
        "vl_cdr3_len": v("vl_cdr3_len"),
        "vh_cdr3_gravy": v("vh_cdr3_gravy"),
        "vl_cdr3_gravy": v("vl_cdr3_gravy"),
        "vh_cdr3_net_charge": v("vh_cdr3_net_charge"),
        "vl_cdr3_net_charge": v("vl_cdr3_net_charge"),
        "vh_cdr3_arom_density": v("vh_cdr3_arom_density"),
        "vl_cdr3_arom_density": v("vl_cdr3_arom_density"),
        "vh_all_cdr_gravy": v("vh_all_cdr_gravy"),
        "vl_all_cdr_gravy": v("vl_all_cdr_gravy"),
        # Risks (for flagged_keys map)
        "_risks": {k: r(k) for k in params.keys()},
        # Overall ADI / scores
        "ADI": rab.get("developability_index"),
        "abref_percentile": payload.get("abref_percentile") or payload.get("clinical_score"),
        "n_warn": payload.get("cmc_n_warn"),
        "n_fail": payload.get("cmc_n_fail"),
        "overall_status": payload.get("overall_status"),
    }


# Mirror of console.html _cmcCollectMutationsByCategory regex set
CAT_PATTERNS = {
    "charge":      re.compile(r"charge|\bpi\b|net charge|asymm", re.I),
    "hydrophobic": re.compile(r"hydrophob|sap|gravy|patch", re.I),
    "stability":   re.compile(r"stabil|instab|aggreg|motif|cluster", re.I),
    "liability":   re.compile(r"liabil|deamid|isomer|oxidat|glycos|cysteine|\bcys\b", re.I),
}
SITE_FIELD_FALLBACK = {
    "fr_negative_charge_sites": "charge",
    "fr_positive_charge_sites": "charge",
    "fr_instability_sites":     "stability",
}


def categorize_mutations(fr_suggestions: List[Dict[str, Any]]) -> Dict[str, List[Dict[str, Any]]]:
    """Bucket FR mutation candidates by category, mirroring the frontend logic."""
    buckets: Dict[str, List[Dict[str, Any]]] = {"charge": [], "hydrophobic": [], "stability": [], "liability": []}
    seen: Dict[str, set] = {k: set() for k in buckets}

    def push(cat: str, mut: Dict[str, Any]):
        key = (mut.get("chain"), mut.get("pos"), mut.get("from"), mut.get("to"))
        if not mut.get("pos") or key in seen[cat]:
            return
        seen[cat].add(key)
        buckets[cat].append(mut)

    for s in fr_suggestions or []:
        sc = s.get("sequence_candidates") or {}
        target = (s.get("target") or "").lower()
        # Target-string match (preferred)
        cat_from_target = None
        if target.find("charge") >= 0:
            cat_from_target = "charge"
        for k, pat in CAT_PATTERNS.items():
            if pat.search(target) and (k != "hydrophobic" or "charge" not in target):
                cat_from_target = k
                break
        # Site lists
        for f, fallback in SITE_FIELD_FALLBACK.items():
            for p in (sc.get(f) or []):
                fr = p.get("from_aa")
                to = p.get("to_aa_hint")
                if not fr or not to:
                    continue
                cat = cat_from_target or fallback
                push(cat, {
                    "chain": p.get("chain"), "pos": p.get("index_1"),
                    "from": fr, "to": to,
                    "region": p.get("region"), "motif": p.get("motif"),
                    "target": target,
                })
        # Hydrophobic runs always go to hydrophobic
        for run in (sc.get("fr_hydrophobic_runs") or []):
            for p in (run.get("per_residue") or []):
                fr = p.get("from_aa")
                to = p.get("to_aa_hint")
                if not fr or not to:
                    continue
                push("hydrophobic", {
                    "chain": run.get("chain"), "pos": p.get("index_1"),
                    "from": fr, "to": to,
                    "region": p.get("region"), "target": target,
                })
    return buckets


def apply_mutations_vhvl(vh: str, vl: str, muts: List[Dict[str, Any]]) -> Tuple[str, str]:
    """Apply 1-indexed point mutations to VH/VL strings."""
    mvh, mvl = list(vh), list(vl)
    for m in muts:
        idx = (m.get("pos") or 0) - 1
        ch = (m.get("chain") or "").upper()
        if idx < 0:
            continue
        if ch in ("VH", "H") and 0 <= idx < len(mvh):
            mvh[idx] = m["to"]
        elif ch in ("VL", "L") and 0 <= idx < len(mvl):
            mvl[idx] = m["to"]
    return "".join(mvh), "".join(mvl)


def apply_mutations_vhh(seq: str, muts: List[Dict[str, Any]]) -> str:
    s = list(seq)
    for m in muts:
        idx = (m.get("pos") or 0) - 1
        if 0 <= idx < len(s):
            s[idx] = m["to"]
    return "".join(s)


# ── IgG smoke test ───────────────────────────────────────────────────────────


def run_igg_smoke(demo: Dict[str, str]) -> Dict[str, Any]:
    print(f"\n[IGG] {demo['demo_id']} ({demo['antibody_type']}) — running baseline…", flush=True)
    from core.cmc.igg_cmc_pipeline import run_igg_cmc_pipeline

    out_subdir = OUT_DIR / demo["demo_id"]
    out_subdir.mkdir(parents=True, exist_ok=True)

    t0 = time.time()
    baseline = run_igg_cmc_pipeline(
        vh_sequence=demo["vh"],
        vl_sequence=demo["vl"],
        antibody_type=demo["antibody_type"],
        project_name=demo["demo_id"],
        out_dir=out_subdir,
        run_structure=False,
        smart_cmc=True,
    )
    elapsed_base = round(time.time() - t0, 1)
    print(f"  baseline done in {elapsed_base}s", flush=True)

    base_metrics = extract_baseline_metrics(baseline)
    fr_suggs = _safe(baseline, ["regular_ab_developability", "fr_modification_suggestions"], []) or []
    buckets = categorize_mutations(fr_suggs)
    bucket_counts = {k: len(v) for k, v in buckets.items()}

    variants: Dict[str, Dict[str, Any]] = {}
    # Run variant for every non-empty bucket + combined
    cats_with_mutations = [k for k, v in buckets.items() if v]
    cats_to_run = list(cats_with_mutations)
    if len(cats_with_mutations) >= 2:
        cats_to_run.append("combined")

    for cat in cats_to_run:
        if cat == "combined":
            muts = []
            for v in buckets.values():
                muts.extend(v)
            cat_label = "Combined"
        else:
            muts = buckets[cat]
            cat_label = cat.capitalize()

        mvh, mvl = apply_mutations_vhvl(demo["vh"], demo["vl"], muts)
        seq_changed_vh = mvh != demo["vh"]
        seq_changed_vl = mvl != demo["vl"]

        t1 = time.time()
        v_payload = run_igg_cmc_pipeline(
            vh_sequence=mvh,
            vl_sequence=mvl,
            antibody_type=demo["antibody_type"],
            project_name=f"{demo['demo_id']}-{cat}",
            out_dir=out_subdir / f"variant_{cat}",
            run_structure=False,
            smart_cmc=False,
        )
        elapsed_v = round(time.time() - t1, 1)
        var_metrics = extract_baseline_metrics(v_payload)
        variants[cat] = {
            "label": cat_label,
            "n_mutations": len(muts),
            "mutations": [f"{m['chain']} {m['pos']} {m['from']}→{m['to']}" for m in muts],
            "applied_vh_change": seq_changed_vh,
            "applied_vl_change": seq_changed_vl,
            "metrics": var_metrics,
            "elapsed_sec": elapsed_v,
        }
        print(f"  variant [{cat_label}] {len(muts)} muts → ADI {_fmt(base_metrics['ADI'],1)} → {_fmt(var_metrics['ADI'],1)} in {elapsed_v}s", flush=True)

    (out_subdir / "baseline.json").write_text(json.dumps({
        "demo_id": demo["demo_id"],
        "baseline_metrics": base_metrics,
        "bucket_counts": bucket_counts,
        "fr_suggestion_targets": [s.get("target") for s in fr_suggs],
    }, indent=2, default=str), encoding="utf-8")
    (out_subdir / "variants.json").write_text(json.dumps(variants, indent=2, default=str), encoding="utf-8")

    return {
        "demo": demo,
        "elapsed_baseline": elapsed_base,
        "baseline_metrics": base_metrics,
        "bucket_counts": bucket_counts,
        "fr_suggestion_targets": [s.get("target") for s in fr_suggs],
        "variants": variants,
    }


# ── VHH smoke test ───────────────────────────────────────────────────────────


def extract_vhh_metrics(payload: Dict[str, Any]) -> Dict[str, Any]:
    m = payload.get("metrics") or {}
    flags = payload.get("risk_flags") or {}
    return {
        "pI": m.get("pI"),
        "GRAVY": m.get("GRAVY"),
        "instability_index": m.get("instability_index"),
        "SAP_score": m.get("SAP_score"),
        "net_charge_pH7": m.get("net_charge_pH7"),
        "ppc": m.get("ppc"),
        "pnc": m.get("pnc"),
        "hydro_patch_max9": m.get("hydro_patch_max9"),
        "charge_patch_max7": m.get("charge_patch_max7"),
        "agg_motifs": m.get("agg_motifs"),
        "deamidation_sites": m.get("deamidation_sites"),
        "isomerization_sites": m.get("isomerization_sites"),
        "oxidation_sites": m.get("oxidation_sites"),
        "glycosylation_sites": m.get("glycosylation_sites"),
        "free_cys": m.get("free_cys"),
        # CDR Fingerprint (V1.9)
        "vhh_cdr3_len": m.get("vhh_cdr3_len"),
        "vhh_cdr3_gravy": m.get("vhh_cdr3_gravy"),
        "vhh_cdr3_net_charge": m.get("vhh_cdr3_net_charge"),
        "vhh_cdr3_arom_density": m.get("vhh_cdr3_arom_density"),
        "vhh_all_cdr_gravy": m.get("vhh_all_cdr_gravy"),
        "ADI": payload.get("adi_score"),
        "adi_grade": payload.get("adi_grade"),
        "n_warn": payload.get("n_warn"),
        "n_fail": payload.get("n_fail"),
        "overall_status": payload.get("overall_status"),
        "abnativ_delta": payload.get("abnativ_delta"),
        "abnativ_tier": payload.get("abnativ_tier"),
        "hpr_score": payload.get("hpr_score"),
        "_flags": flags,
    }


def run_vhh_smoke(demo: Dict[str, str]) -> Dict[str, Any]:
    print(f"\n[VHH] {demo['demo_id']} (origin={demo['sdab_origin']}) — running baseline…", flush=True)
    from core.cmc.vhh_cmc_engine import evaluate_single_vhh
    from core.cmc.vhh_fr_mutation_sites import get_vhh_fr_suggestions

    out_subdir = OUT_DIR / demo["demo_id"]
    out_subdir.mkdir(parents=True, exist_ok=True)

    t0 = time.time()
    base = evaluate_single_vhh(
        name=demo["demo_id"], seq=demo["seq"],
        origin=demo["sdab_origin"], skip_percentile=True,
    )
    fr_suggs = get_vhh_fr_suggestions(
        seq=demo["seq"], flags=base.get("risk_flags") or {},
        metrics=base.get("metrics") or {}, origin=demo["sdab_origin"],
    ) or []
    elapsed_base = round(time.time() - t0, 1)
    print(f"  baseline done in {elapsed_base}s; {len(fr_suggs)} FR suggestions", flush=True)

    base_metrics = extract_vhh_metrics(base)

    # VHH suggestions schema differs — group by category field
    buckets: Dict[str, List[Dict[str, Any]]] = {"charge": [], "hydrophobic": [], "stability": [], "liability": []}
    for s in fr_suggs:
        cat = (s.get("category") or "").lower()
        if cat not in buckets:
            # Try heuristic match
            cat = "other"
        if cat not in buckets:
            buckets["liability"].append(s)
        else:
            buckets.setdefault(cat, []).append(s)
    bucket_counts = {k: len(v) for k, v in buckets.items() if k in ("charge", "hydrophobic", "stability", "liability")}

    variants: Dict[str, Dict[str, Any]] = {}
    cats_with_muts = [k for k, v in buckets.items() if v and k in ("charge", "hydrophobic", "stability", "liability")]
    for cat in cats_with_muts:
        suggs = buckets[cat]
        # VHH FR suggestion canonical schema (matches console.html): linear_pos / found_aa / suggested_aa
        muts = []
        for s in suggs:
            pos = s.get("linear_pos") or s.get("pos") or s.get("pos_linear") or s.get("position_linear")
            fr = s.get("found_aa") or s.get("from_aa") or s.get("from")
            to = s.get("suggested_aa") or s.get("to_aa") or s.get("to")
            if pos and fr and to:
                muts.append({"chain": "VHH", "pos": int(pos), "from": fr, "to": to,
                             "kabat": s.get("kabat_pos"), "label": s.get("label")})

        if not muts:
            print(f"  variant [{cat}]: 0 applicable mutations (schema mismatch?) — skipped", flush=True)
            continue

        mseq = apply_mutations_vhh(demo["seq"], muts)
        t1 = time.time()
        v = evaluate_single_vhh(name=f"{demo['demo_id']}-{cat}", seq=mseq, origin=demo["sdab_origin"], skip_percentile=True)
        elapsed_v = round(time.time() - t1, 1)
        var_metrics = extract_vhh_metrics(v)
        variants[cat] = {
            "label": cat.capitalize(),
            "n_mutations": len(muts),
            "mutations": [f"VHH {m['pos']} {m['from']}→{m['to']}" for m in muts],
            "metrics": var_metrics,
            "elapsed_sec": elapsed_v,
        }
        print(f"  variant [{cat}] {len(muts)} muts → ADI {_fmt(base_metrics['ADI'],1)} → {_fmt(var_metrics['ADI'],1)} in {elapsed_v}s", flush=True)

    # Combined if >=2 buckets have mutations
    cat_keys_run = [k for k, v in variants.items()]
    if len(cat_keys_run) >= 2:
        all_muts = []
        for k in cat_keys_run:
            # Reconstruct mutations
            for label in variants[k]["mutations"]:
                # parse "VHH <pos> <from>→<to>"
                mm = re.match(r"VHH\s+(\d+)\s+([A-Z])→([A-Z])", label)
                if mm:
                    all_muts.append({"chain": "VHH", "pos": int(mm.group(1)), "from": mm.group(2), "to": mm.group(3)})
        if all_muts:
            mseq = apply_mutations_vhh(demo["seq"], all_muts)
            t1 = time.time()
            v = evaluate_single_vhh(name=f"{demo['demo_id']}-combined", seq=mseq, origin=demo["sdab_origin"], skip_percentile=True)
            elapsed_v = round(time.time() - t1, 1)
            variants["combined"] = {
                "label": "Combined",
                "n_mutations": len(all_muts),
                "mutations": [f"VHH {m['pos']} {m['from']}→{m['to']}" for m in all_muts],
                "metrics": extract_vhh_metrics(v),
                "elapsed_sec": elapsed_v,
            }
            print(f"  variant [combined] {len(all_muts)} muts → ADI {_fmt(base_metrics['ADI'],1)} → {_fmt(variants['combined']['metrics']['ADI'],1)} in {elapsed_v}s", flush=True)

    (out_subdir / "baseline.json").write_text(json.dumps({
        "demo_id": demo["demo_id"],
        "baseline_metrics": base_metrics,
        "bucket_counts": bucket_counts,
        "fr_suggestions": fr_suggs,
    }, indent=2, default=str), encoding="utf-8")
    (out_subdir / "variants.json").write_text(json.dumps(variants, indent=2, default=str), encoding="utf-8")

    return {
        "demo": demo,
        "elapsed_baseline": elapsed_base,
        "baseline_metrics": base_metrics,
        "bucket_counts": bucket_counts,
        "fr_suggestion_count": len(fr_suggs),
        "variants": variants,
    }


# ── Report rendering ─────────────────────────────────────────────────────────


def render_metric_compare_table(base: Dict, var: Dict, target_keys: List[str]) -> str:
    """Render a 3-tier comparison table (miniCMC core + targets) as Markdown."""
    mini = [
        ("pI (Fab)", "pI", 2),
        ("GRAVY", "GRAVY", 3),
        ("Instability index", "instability_index", 2),
        ("SAP score", "SAP_score", 2),
    ]
    rows = ["| Tier | Metric | Before | After | Δ |", "|---|---|---|---|---|"]
    for label, key, dig in mini:
        b, a = base.get(key), var.get(key)
        rows.append(f"| miniCMC | **{label}** | {_fmt(b, dig)} | {_fmt(a, dig)} | {_delta(b, a, dig)} |")
    rows.append(f"| miniCMC | **ADI** | {_fmt(base.get('ADI'), 1)} | {_fmt(var.get('ADI'), 1)} | {_delta(base.get('ADI'), var.get('ADI'), 1)} |")
    for key in target_keys:
        b, a = base.get(key), var.get(key)
        if b is None and a is None:
            continue
        rows.append(f"| Target | {key} | {_fmt(b, 2)} | {_fmt(a, 2)} | {_delta(b, a, 2)} |")
    return "\n".join(rows)


CATEGORY_TARGETS = {
    "charge":      ["net_charge_pH7", "pI", "ppc", "pnc", "sfvcsp"],
    "hydrophobic": ["hydro_patch_max9", "GRAVY", "psh", "agg_motifs"],
    "stability":   ["instability_index", "agg_motifs"],
    "liability":   ["deamidation_sites", "isomerization_sites", "oxidation_sites", "glycosylation_sites", "free_cys"],
    "combined":    ["pI", "net_charge_pH7", "hydro_patch_max9", "agg_motifs", "ppc", "pnc"],
}


def render_report(igg_results: List[Dict], vhh_results: List[Dict], findings: List[str]) -> str:
    parts: List[str] = []
    parts.append(f"# CMC Smart-CMC Smoke Test Report\n")
    parts.append(f"**Run:** `{TS}`  ·  **Mode:** sequence-only (run_structure=False)  ·  **Output:** `out/smoke/cmc_smart_cmc_{TS}/`\n")
    parts.append("## Scope\n")
    parts.append("- 3 IgG demos (Toripalimab, Abiprubart, Briakinumab) — `run_igg_cmc_pipeline`")
    parts.append("- 2 VHH/sdAb demos (7D12 humanized VHH, Porustobart SCAb) — `evaluate_single_vhh` + `get_vhh_fr_suggestions`")
    parts.append("- For each demo: baseline + Smart-CMC bucket-by-bucket variant + Combined variant (if ≥2 categories triggered)")
    parts.append("- Metrics tracked: miniCMC core (pI, GRAVY, instability, SAP) + ADI + category targets\n")

    # ── Overview matrix ─────────────────────────────────────────────────────
    parts.append("## §1 Overview matrix — which demos triggered which categories\n")
    parts.append("| Demo | Origin | ADI | Status | Charge | Hydrophobic | Stability | Liability |")
    parts.append("|---|---|---|---|---|---|---|---|")
    for r in igg_results:
        bc = r["bucket_counts"]
        m = r["baseline_metrics"]
        parts.append(f"| {r['demo']['demo_id']} | {r['demo']['antibody_type']} | {_fmt(m.get('ADI'),1)} | {m.get('overall_status') or '—'} | {bc.get('charge',0)} | {bc.get('hydrophobic',0)} | {bc.get('stability',0)} | {bc.get('liability',0)} |")
    for r in vhh_results:
        bc = r["bucket_counts"]
        m = r["baseline_metrics"]
        parts.append(f"| {r['demo']['demo_id']} | {r['demo']['sdab_origin']} | {_fmt(m.get('ADI'),1)} | {m.get('overall_status') or '—'} | {bc.get('charge',0)} | {bc.get('hydrophobic',0)} | {bc.get('stability',0)} | {bc.get('liability',0)} |")
    parts.append("")

    # ── Per-demo detail ─────────────────────────────────────────────────────
    parts.append("## §2 Per-demo detail\n")
    for r in (igg_results + vhh_results):
        demo_id = r["demo"]["demo_id"]
        is_vhh = "sdab_origin" in r["demo"]
        parts.append(f"### {demo_id} — {r['demo'].get('label','')}\n")
        parts.append(f"**Type:** {'VHH/sdAb' if is_vhh else 'IgG VH+VL'} · **Baseline elapsed:** {r['elapsed_baseline']}s")
        if not is_vhh:
            tgts = r.get("fr_suggestion_targets") or []
            if tgts:
                parts.append(f"**FR-suggestion targets (raw):** {tgts}\n")
        else:
            parts.append(f"**FR suggestions total:** {r.get('fr_suggestion_count',0)}\n")

        base_m = r["baseline_metrics"]
        parts.append("**Baseline miniCMC + ADI:**")
        parts.append(f"- pI={_fmt(base_m.get('pI'),2)} · GRAVY={_fmt(base_m.get('GRAVY'),3)} · Instability={_fmt(base_m.get('instability_index'),2)} · SAP={_fmt(base_m.get('SAP_score'),2)}")
        parts.append(f"- ADI={_fmt(base_m.get('ADI'),1)} · n_warn={base_m.get('n_warn')} · n_fail={base_m.get('n_fail')}\n")

        variants = r.get("variants") or {}
        if not variants:
            parts.append("> ⚠ **No variants produced** — Smart-CMC returned zero categorised mutations.")
            parts.append("")
            continue

        for cat, v in variants.items():
            parts.append(f"#### Variant: {v['label']} ({v['n_mutations']} mutations)")
            if v.get("mutations"):
                parts.append("`" + " · ".join(v["mutations"][:8]) + ("`" + (" ...(+more)" if len(v["mutations"])>8 else "")))
            else:
                parts.append("(no mutation list returned)")
            if "applied_vh_change" in v:
                seq_note = []
                if v.get("applied_vh_change"): seq_note.append("VH changed")
                if v.get("applied_vl_change"): seq_note.append("VL changed")
                parts.append(f"_Sequence mutation applied:_ {', '.join(seq_note) if seq_note else '⚠ NO sequence change detected'}")
            parts.append("")
            tgt_keys = CATEGORY_TARGETS.get(cat, [])
            parts.append(render_metric_compare_table(base_m, v["metrics"], tgt_keys))
            parts.append("")

    # ── Findings ────────────────────────────────────────────────────────────
    parts.append("## §3 Auto-detected findings\n")
    if findings:
        for f in findings:
            parts.append(f"- {f}")
    else:
        parts.append("✓ No issues auto-detected — all demos passed smoke checks.")
    parts.append("")
    return "\n".join(parts)


# ── Finding detectors ────────────────────────────────────────────────────────


def detect_findings(igg_results: List[Dict], vhh_results: List[Dict]) -> List[str]:
    findings: List[str] = []
    for r in (igg_results + vhh_results):
        demo_id = r["demo"]["demo_id"]
        bm = r["baseline_metrics"]
        risks = bm.get("_risks") or bm.get("_flags") or {}

        # Check: baseline has WARN/FAIL but Smart-CMC produced zero buckets
        has_warn_fail = bool((bm.get("n_warn") or 0) + (bm.get("n_fail") or 0))
        bucket_total = sum((r.get("bucket_counts") or {}).values())
        if has_warn_fail and bucket_total == 0:
            findings.append(f"❌ **{demo_id}** has {bm.get('n_warn')} WARN + {bm.get('n_fail')} FAIL but Smart-CMC produced 0 mutation suggestions. (Verify buttons would not render.)")

        # Check: variant applied but sequence didn't change (mutation index out of range)
        for cat, v in (r.get("variants") or {}).items():
            if "applied_vh_change" in v and v["n_mutations"] > 0:
                if not (v["applied_vh_change"] or v["applied_vl_change"]):
                    findings.append(f"❌ **{demo_id}/{cat}** reported {v['n_mutations']} mutations but no sequence change applied — coordinate or chain mismatch.")

        # Check: ADI regressed
        base_adi = bm.get("ADI")
        for cat, v in (r.get("variants") or {}).items():
            vm = v.get("metrics") or {}
            va = vm.get("ADI")
            if base_adi is not None and va is not None:
                if (va - base_adi) < -1.0:
                    findings.append(f"⚠ **{demo_id}/{cat}** ADI regressed {_fmt(base_adi,1)} → {_fmt(va,1)} (Δ {_delta(base_adi, va, 1)}). Smart-CMC suggestion may need refinement.")
                elif (va - base_adi) > 1.0:
                    findings.append(f"✓ **{demo_id}/{cat}** ADI improved {_fmt(base_adi,1)} → {_fmt(va,1)} (Δ {_delta(base_adi, va, 1)}).")

        # Check: agg_motifs introduced
        for cat, v in (r.get("variants") or {}).items():
            vm = v.get("metrics") or {}
            ba, va = bm.get("agg_motifs"), vm.get("agg_motifs")
            if ba is not None and va is not None and va > ba:
                findings.append(f"⚠ **{demo_id}/{cat}** mutations INTRODUCED new aggregation motifs ({ba} → {va}).")

        # Check: charge overshoot (net charge moves from positive to strongly negative or vice versa)
        for cat, v in (r.get("variants") or {}).items():
            if cat not in ("charge", "combined"):
                continue
            vm = v.get("metrics") or {}
            b, a = bm.get("net_charge_pH7"), vm.get("net_charge_pH7")
            if b is not None and a is not None:
                if b > 0 and a < -0.5:
                    findings.append(f"⚠ **{demo_id}/{cat}** charge overshoot: net_charge {_fmt(b,2)} → {_fmt(a,2)} crossed zero into negative territory.")
                elif b < 0 and a > 0.5:
                    findings.append(f"⚠ **{demo_id}/{cat}** charge overshoot: net_charge {_fmt(b,2)} → {_fmt(a,2)} crossed zero into positive territory.")

        # Check: target metric did not move toward goal
        for cat, v in (r.get("variants") or {}).items():
            vm = v.get("metrics") or {}
            if cat == "stability":
                b, a = bm.get("instability_index"), vm.get("instability_index")
                if b is not None and a is not None and a >= b:
                    findings.append(f"⚠ **{demo_id}/{cat}** instability_index did not improve ({_fmt(b,2)} → {_fmt(a,2)}).")
            if cat == "charge":
                bcp, acp = bm.get("net_charge_pH7"), vm.get("net_charge_pH7")
                if bcp is not None and acp is not None and abs(acp) > abs(bcp) + 0.3:
                    findings.append(f"⚠ **{demo_id}/{cat}** |net charge| increased ({_fmt(bcp,2)} → {_fmt(acp,2)}) — worsening.")
            if cat == "liability":
                liab_total_b = sum((bm.get(k) or 0) for k in ("deamidation_sites","isomerization_sites","oxidation_sites","glycosylation_sites","free_cys"))
                liab_total_a = sum((vm.get(k) or 0) for k in ("deamidation_sites","isomerization_sites","oxidation_sites","glycosylation_sites","free_cys"))
                if liab_total_a > liab_total_b:
                    findings.append(f"⚠ **{demo_id}/{cat}** liability sites total increased ({liab_total_b} → {liab_total_a}).")

    return findings


# ── Main ─────────────────────────────────────────────────────────────────────


def main():
    print(f"Smoke test output: {OUT_DIR}", flush=True)
    igg_results: List[Dict] = []
    vhh_results: List[Dict] = []

    for demo in IGG_DEMOS:
        try:
            igg_results.append(run_igg_smoke(demo))
        except Exception as e:
            print(f"  ❌ IgG {demo['demo_id']} FAILED: {e}", flush=True)
            traceback.print_exc()
            igg_results.append({
                "demo": demo, "elapsed_baseline": 0,
                "baseline_metrics": {}, "bucket_counts": {},
                "fr_suggestion_targets": [], "variants": {},
                "error": f"{type(e).__name__}: {e}",
            })

    for demo in VHH_DEMOS:
        try:
            vhh_results.append(run_vhh_smoke(demo))
        except Exception as e:
            print(f"  ❌ VHH {demo['demo_id']} FAILED: {e}", flush=True)
            traceback.print_exc()
            vhh_results.append({
                "demo": demo, "elapsed_baseline": 0,
                "baseline_metrics": {}, "bucket_counts": {},
                "fr_suggestion_count": 0, "variants": {},
                "error": f"{type(e).__name__}: {e}",
            })

    findings = detect_findings(igg_results, vhh_results)
    report_md = render_report(igg_results, vhh_results, findings)
    report_path = OUT_DIR / "REPORT.md"
    report_path.write_text(report_md, encoding="utf-8")
    print(f"\n✓ Report written: {report_path}", flush=True)
    if findings:
        print(f"⚠ {len(findings)} finding(s) auto-detected:", flush=True)
        for f in findings:
            print(f"  {f}", flush=True)


if __name__ == "__main__":
    main()
