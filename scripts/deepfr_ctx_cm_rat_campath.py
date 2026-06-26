#!/usr/bin/env python3
"""
Generate a conservative DeepFR-CTX-CMC candidate for the rat Campath benchmark.

Canonical SSOT display name: DeepFR-CTX-CMC (internal id deepfr_ctx_cmc).
This script filename remains deepfr_ctx_cm_rat_campath.py for registry path stability.

DeepFR-CTX-CMC is a project-level CMC polish experiment, not a new standard:
- FR-only substitutions
- Candidate residues borrowed only from existing evaluated variants
- No CDR, Cys, Pro/Gly backbone, or new N-glyc changes
- Optimizes mini-CMC, primarily Instability Index, while preserving HPR
"""
from __future__ import annotations

import itertools
import json
import re
import sys
from pathlib import Path
from typing import Dict, Iterable, List, Tuple

SUITE = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(SUITE))

from core.cmc.adi_score import compute_adi
from core.cmc.cmc_metrics import CMCMetricEngine
from core.humanization.hpr_index import compute_hpr_index
from core.humanization.kabat_utils import get_kabat_numbering, sorted_keys

PROJ = SUITE / "projects" / "rat_campath_console_humanization"
NGLYC_RE = re.compile(r"N[^P][ST]")


def _chain_fr_indices(seq: str, chain: str) -> List[int]:
    kd = get_kabat_numbering(seq)
    keys = sorted_keys(kd)
    fr_indices: List[int] = []
    for i, key in enumerate(keys):
        pos = key[0]
        if chain == "VH":
            in_cdr = (26 <= pos <= 35) or (50 <= pos <= 65) or (95 <= pos <= 102)
        else:
            in_cdr = (24 <= pos <= 34) or (50 <= pos <= 56) or (89 <= pos <= 97)
        if not in_cdr:
            fr_indices.append(i)
    return fr_indices


def _metrics(vh: str, vl: str) -> Dict:
    m = CMCMetricEngine.compute_metrics(vh, vl)
    rm = {
        "pI": m.get("pI"),
        "GRAVY": m.get("GRAVY"),
        "instability_index": m.get("instability_index"),
        "net_charge_pH7": m.get("net_charge_pH7"),
        "hydro_patch_max9": m.get("hydro_patch_max9"),
        "charge_patch_max7": m.get("charge_patch_max7"),
        "SAP_score": m.get("SAP_score"),
        "Fv_charge_asymmetry": m.get("Fv_charge_asymmetry"),
        "agg_motifs": m.get("agg_motifs"),
        "hydro_cluster_count": m.get("hydro_cluster_count"),
        "n_deamidation": len(m.get("deamidation_sites") or []),
        "n_isomerization": len(m.get("isomerization_sites") or []),
        "n_glyc": len(m.get("glycosylation_sites") or []),
        "n_oxidation": len(m.get("oxidation_sites") or []),
        "n_free_cys": len(m.get("free_cys") or []),
    }
    try:
        rm["ADI"] = round(float(compute_adi(rm)), 2)
    except Exception:
        rm["ADI"] = None
    return rm


def _apply(base_vh: str, base_vl: str, muts: Iterable[Tuple[str, int, str, str]]) -> Tuple[str, str]:
    vh = list(base_vh)
    vl = list(base_vl)
    for chain, idx, old, new in muts:
        arr = vh if chain == "VH" else vl
        if arr[idx] != old:
            raise ValueError(f"{chain}{idx}: expected {old}, observed {arr[idx]}")
        arr[idx] = new
    return "".join(vh), "".join(vl)


def _safe_candidate(base_seq: str, idx: int, old: str, new: str) -> bool:
    if old == new:
        return False
    if old in {"C", "P", "G"} or new in {"C", "P", "G"}:
        return False
    mutated = base_seq[:idx] + new + base_seq[idx + 1:]
    return set(m.start() for m in NGLYC_RE.finditer(mutated)) <= set(
        m.start() for m in NGLYC_RE.finditer(base_seq)
    )


def main() -> None:
    data = json.loads((PROJ / "humanized_sequences.json").read_text(encoding="utf-8"))
    base_vh = data["DeepFR_CTX"]["vh"]
    base_vl = data["DeepFR_CTX"]["vl"]

    source_names = ["Surface_reshape", "CDR_graft_Vernier_BM", "9AA_CTX", "rat_parent"]
    sources = {
        name: (data[name]["vh"], data[name]["vl"])
        for name in source_names
    }

    fr_vh = set(_chain_fr_indices(base_vh, "VH"))
    fr_vl = set(_chain_fr_indices(base_vl, "VK"))

    candidates: List[Tuple[str, int, str, str, str]] = []
    seen = set()
    for source_name, (src_vh, src_vl) in sources.items():
        for chain, base_seq, src_seq, fr_idxs in [
            ("VH", base_vh, src_vh, fr_vh),
            ("VL", base_vl, src_vl, fr_vl),
        ]:
            if len(base_seq) != len(src_seq):
                continue
            for idx, (old, new) in enumerate(zip(base_seq, src_seq)):
                key = (chain, idx, old, new)
                if idx in fr_idxs and key not in seen and _safe_candidate(base_seq, idx, old, new):
                    candidates.append((chain, idx, old, new, source_name))
                    seen.add(key)

    base_m = _metrics(base_vh, base_vl)
    base_hpr = compute_hpr_index(base_vh, base_vl)["combined"]["score"]

    scored_singles = []
    for cand in candidates:
        chain, idx, old, new, src = cand
        vh, vl = _apply(base_vh, base_vl, [(chain, idx, old, new)])
        m = _metrics(vh, vl)
        instab_delta = float(base_m["instability_index"]) - float(m["instability_index"])
        if instab_delta <= 0:
            continue
        scored_singles.append({
            "mutation": cand,
            "metrics": m,
            "instab_delta": round(instab_delta, 3),
            "score": round(instab_delta + 0.25 * (float(m.get("ADI") or 0) - float(base_m.get("ADI") or 0)), 3),
        })

    scored_singles.sort(key=lambda x: (-x["score"], -x["instab_delta"]))
    top = scored_singles[:14]

    # Search combinations up to 3 from top CMC-improving singles.
    combo_rows = []
    for r in range(1, min(3, len(top)) + 1):
        for combo in itertools.combinations([x["mutation"] for x in top], r):
            # Do not use two substitutions at the same position.
            positions = {(c[0], c[1]) for c in combo}
            if len(positions) != len(combo):
                continue
            vh, vl = _apply(base_vh, base_vl, [(c[0], c[1], c[2], c[3]) for c in combo])
            m = _metrics(vh, vl)
            if (m.get("n_glyc") or 0) > (base_m.get("n_glyc") or 0):
                continue
            hpr = compute_hpr_index(vh, vl)["combined"]["score"]
            if hpr < 0.80:
                continue
            instab_delta = float(base_m["instability_index"]) - float(m["instability_index"])
            if instab_delta <= 0:
                continue
            # Prefer Instab improvement, preserve ADI and HPR.
            score = (
                instab_delta
                + 0.4 * (float(m.get("ADI") or 0) - float(base_m.get("ADI") or 0))
                + 5.0 * (float(hpr) - float(base_hpr))
                - 0.25 * len(combo)
            )
            combo_rows.append({
                "combo": combo,
                "vh": vh,
                "vl": vl,
                "metrics": m,
                "hpr_combined": round(float(hpr), 4),
                "instab_delta": round(instab_delta, 3),
                "score": round(score, 3),
            })

    combo_rows.sort(key=lambda x: (-x["score"], -x["instab_delta"], -x["hpr_combined"]))
    best = combo_rows[0]

    payload = {
        "algorithm": "DeepFR-CTX-CMC",
        "scope": "project-level FR-only mini-CMC polish candidate",
        "base_variant": "DeepFR-CTX",
        "base_metrics": {**base_m, "HPR_combined": round(float(base_hpr), 4)},
        "candidate_count": len(candidates),
        "top_single_mutations": scored_singles[:20],
        "selected_combo": {
            "mutations": [
                {
                    "chain": c[0],
                    "linear_index_0based": c[1],
                    "from": c[2],
                    "to": c[3],
                    "source_variant": c[4],
                }
                for c in best["combo"]
            ],
            "metrics": best["metrics"],
            "HPR_combined": best["hpr_combined"],
            "instab_delta": best["instab_delta"],
            "score": best["score"],
        },
    }

    data["DeepFR_CTX_CMC"] = {
        "vh": best["vh"],
        "vl": best["vl"],
        "algorithm": "DeepFR-CTX-CMC",
        "cm_polish": payload["selected_combo"],
    }
    (PROJ / "humanized_sequences.json").write_text(json.dumps(data, indent=2), encoding="utf-8")

    out_json = PROJ / "deepfr_ctx_cmc_scan.json"
    out_json.write_text(json.dumps(payload, indent=2), encoding="utf-8")

    lines = [
        "# DeepFR-CTX-CMC scan",
        "",
        f"Base Instab: {base_m['instability_index']} | Base ADI: {base_m['ADI']} | Base HPR: {round(float(base_hpr), 4)}",
        "",
        "## Selected CM Candidate",
        "",
        "| Mutation | Source |",
        "|---|---|",
    ]
    for c in payload["selected_combo"]["mutations"]:
        lines.append(
            f"| {c['chain']}[{c['linear_index_0based']}] {c['from']}->{c['to']} | {c['source_variant']} |"
        )
    sm = payload["selected_combo"]["metrics"]
    lines += [
        "",
        "## miniCMC",
        "",
        "| Variant | Instab | ADI | HPR comb | pI | Agg | ChgPatch7 | FvAsym | Deamid | Isomer |",
        "|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|",
        f"| DeepFR-CTX | {base_m['instability_index']} | {base_m['ADI']} | {round(float(base_hpr), 4)} | {base_m['pI']} | {base_m['agg_motifs']} | {base_m['charge_patch_max7']} | {base_m['Fv_charge_asymmetry']} | {base_m['n_deamidation']} | {base_m['n_isomerization']} |",
        f"| DeepFR-CTX-CMC | {sm['instability_index']} | {sm['ADI']} | {payload['selected_combo']['HPR_combined']} | {sm['pI']} | {sm['agg_motifs']} | {sm['charge_patch_max7']} | {sm['Fv_charge_asymmetry']} | {sm['n_deamidation']} | {sm['n_isomerization']} |",
    ]
    out_md = PROJ / "DEEPFR_CTX_CMC_SCAN.md"
    out_md.write_text("\n".join(lines) + "\n", encoding="utf-8")

    print("\n".join(lines))
    print(f"\nWrote {out_json}")
    print(f"Wrote {out_md}")
    print("Updated humanized_sequences.json with DeepFR_CTX_CMC")


if __name__ == "__main__":
    main()
