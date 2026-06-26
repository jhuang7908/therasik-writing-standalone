#!/usr/bin/env python3
"""Export 25 + 2 (HPR true + AbLang2 paired) + TCIA for ADA245 Phage Display n=7.

AbLang2 model is loaded once; HPR uses compute_hpr_index per row.
"""
from __future__ import annotations

import csv
import json
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]
if str(REPO) not in sys.path:
    sys.path.insert(0, str(REPO))

ADA_CSV = REPO / "data" / "ada245" / "database" / "ada_master_245_curated.csv"
NAT384 = REPO / "data" / "natural_380_atlas" / "natural384_cmc_per_antibody.csv"
OUT_JSON = REPO / "projects" / "phage_display_ada7_console_report" / "phage_display_ada7_25plus2_full.json"

from core.cmc.regular_ab_developability import PARAMETER_SET_25

KEYS25 = [p["key"] for p in PARAMETER_SET_25]
PLATFORM = "Phage Display"


def _ablang_batch(pairs: list[tuple[str, str, str]]) -> tuple[dict[str, float | None], str | None]:
    """pairs: (name, vh, vl) — returns (map name -> pll, error or None)."""
    import numpy as np

    out: dict[str, float | None] = {p[0]: None for p in pairs}
    try:
        import ablang2  # type: ignore

        model = ablang2.pretrained("ablang2-paired")
        for name, vh, vl in pairs:
            if not vh or not vl:
                continue
            pll = model([(vh, vl)], mode="pseudo_log_likelihood")
            out[name] = round(float(np.squeeze(pll)), 4)
        return out, None
    except Exception as exc:  # noqa: BLE001
        return out, f"{type(exc).__name__}: {exc}"


def main() -> None:
    nat_by_id: dict[str, dict] = {}
    with NAT384.open(encoding="utf-8", newline="") as f:
        for r in csv.DictReader(f):
            nat_by_id[r["antibody_id"].strip()] = r

    rows_ada: list[dict] = []
    with ADA_CSV.open(encoding="utf-8", newline="") as f:
        for r in csv.DictReader(f):
            if r.get("discovery_platform", "").strip() == PLATFORM:
                rows_ada.append(r)

    from core.humanization.hpr_index import compute_hpr_index
    from core.immunogenicity.mhcii_analyzer import MHCII_Analyzer

    pairs: list[tuple[str, str, str]] = []
    for r in rows_ada:
        name = r["antibody_name"].strip()
        vh = (r.get("vh_seq") or "").strip().upper()
        vl = (r.get("vl_seq") or "").strip().upper()
        pairs.append((name, vh, vl))

    ablang_map, ablang_err = _ablang_batch(pairs)

    out_rows: list[dict] = []
    for r in rows_ada:
        name = r["antibody_name"].strip()
        vh = (r.get("vh_seq") or "").strip().upper()
        vl = (r.get("vl_seq") or "").strip().upper()

        nat = nat_by_id.get(name)
        params25: dict[str, float | None] = {}
        nat384_hit = nat is not None
        for k in KEYS25:
            if nat and k in nat and str(nat[k]).strip() != "":
                try:
                    params25[k] = float(nat[k])
                except ValueError:
                    params25[k] = None
            elif k in r and str(r[k]).strip() != "":
                try:
                    params25[k] = float(r[k])
                except ValueError:
                    params25[k] = None
            else:
                params25[k] = None

        hpr = compute_hpr_index(vh, vl)
        hpr_combined = (hpr.get("combined") or {}).get("score")
        hpr_vh = (hpr.get("vh") or {}).get("score")
        hpr_vl = (hpr.get("vl") or {}).get("score")

        mh = MHCII_Analyzer(vh_seq=vh, vl_seq=vl, use_iedb=False)
        mres = mh.run(is_vhh=False)
        tcia = round(float(mres.tcia_score), 4)

        out_rows.append(
            {
                "antibody_name": name,
                "natural384_row_hit": nat384_hit,
                "ADI_natural384": float(nat["ADI_natural384"]) if nat and nat.get("ADI_natural384") else None,
                "parameters_25": params25,
                "plus2": {
                    "hpr_combined": hpr_combined,
                    "hpr_vh": hpr_vh,
                    "hpr_vl": hpr_vl,
                    "ablang2_paired_pll": ablang_map.get(name),
                    "ablang_batch_error": ablang_err,
                },
                "tcia_score": tcia,
                "tcia_risk": str(mres.risk_level),
                "ada_first_pct": float(r["ada_first_pct"]) if r.get("ada_first_pct") else None,
            }
        )

    OUT_JSON.parent.mkdir(parents=True, exist_ok=True)
    payload = {
        "n": len(out_rows),
        "parameter_keys_25": KEYS25,
        "rows": out_rows,
    }
    OUT_JSON.write_text(json.dumps(payload, indent=2), encoding="utf-8")
    print("Wrote", OUT_JSON.relative_to(REPO))


if __name__ == "__main__":
    main()
