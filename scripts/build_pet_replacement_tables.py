#!/usr/bin/env python3
"""
Build dog/cat/human amino-acid replacement tables.

Outputs position-specific Kabat frequency tables derived from curated dog/cat
germline/scaffold registries and human germline references. These tables are
intended as project-level engineering references for Llamanade-style frequency
substitution and surface-reshaping replacement ranking.

This script does not modify locked config or standards files.
"""

from __future__ import annotations

import argparse
import contextlib
import io
import json
import subprocess
import sys
from collections import defaultdict
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


REPO_ROOT = Path(__file__).resolve().parents[1]

DOG_DIR = REPO_ROOT / "data" / "germlines" / "canis_lupus_familiaris_ig_aa"
CAT_DIR = REPO_ROOT / "data" / "germlines" / "felis_catus_ig_aa"
HUMAN_DIR = REPO_ROOT / "data" / "germlines" / "human_ig_aa"
LLAMANADE_HUMAN_VH_PROFILE = (
    REPO_ROOT / "external" / "llamanade" / "Llamanade_upstream" / "resources" / "resources" / "ANARCI_Hum_H.json"
)

DOG_REGISTRY = DOG_DIR / "dog_scaffold_cmc_optimization_tier1_tier2_v1.json"
DOG_REPERTOIRE = DOG_DIR / "dog_repertoire_and_dla_stats.json"
CAT_REGISTRY = CAT_DIR / "cat_scaffold_cmc_optimization_tier1_tier2_v1.json"

AA_ORDER = "ACDEFGHIKLMNPQRSTVWY"
HYDROPHOBIC = set("FILMVWY")
POLAR_OR_CHARGED = set("STNQDEKRHY")

TIER_WEIGHT = {
    "tier1": 3.0,
    "tier2": 1.5,
    "tier3": 0.5,
}

RISK_WEIGHT = {
    "low": 1.0,
    "medium": 0.6,
    "high": 0.25,
}

_ANARCII_RUNNER = None


def _load_json(path: Path) -> Any:
    return json.loads(path.read_text(encoding="utf-8"))


def _write_json(path: Path, data: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, indent=2, ensure_ascii=False), encoding="utf-8")


def _number_kabat_inprocess(seq: str) -> list[dict[str, Any]]:
    """Return Kabat-numbered non-gap rows: {key, pos, ins, aa}.

    Uses the same `anarcii` Python package already used in local VHH tools.
    """
    global _ANARCII_RUNNER
    if _ANARCII_RUNNER is None:
        try:
            from anarcii import Anarcii
        except ImportError as exc:
            raise RuntimeError(
                "anarcii package is required. Run in the anarcii conda environment."
            ) from exc
        _ANARCII_RUNNER = Anarcii()

    seq = "".join(seq.upper().split())
    if not seq:
        return []
    _ANARCII_RUNNER.number(seq)
    kabat = _ANARCII_RUNNER.to_scheme("kabat")
    seq_data = kabat.get("Sequence", {})
    rows = []
    for (pos, ins), aa in seq_data.get("numbering", []):
        if not aa or aa == "-":
            continue
        ins_clean = str(ins).strip().upper()
        key = f"{int(pos)}{ins_clean}"
        rows.append({"key": key, "pos": int(pos), "ins": ins_clean, "aa": aa})
    return rows


def _number_kabat(seq: str, *, timeout_seconds: int = 180) -> list[dict[str, Any]]:
    """Safely number one sequence in a subprocess.

    ANARCII can hang on malformed/partial V genes. A per-sequence subprocess
    keeps one bad record from blocking the full replacement-table build.
    """
    proc = subprocess.run(
        [sys.executable, str(Path(__file__).resolve()), "--number-one"],
        input=seq,
        text=True,
        capture_output=True,
        timeout=timeout_seconds,
        check=False,
    )
    if proc.returncode != 0:
        raise RuntimeError((proc.stderr or proc.stdout or "numbering failed").strip())
    lines = [ln.strip() for ln in proc.stdout.splitlines() if ln.strip()]
    if not lines:
        raise RuntimeError("numbering subprocess returned no output")
    return json.loads(lines[-1])


def _safe_weight(row: dict[str, Any], *, species: str, locus: str) -> tuple[float, list[str]]:
    """CMC/tier/developability weight for one scaffold row."""
    reasons: list[str] = []

    tier = str(row.get("tier", "")).lower()
    weight = TIER_WEIGHT.get(tier, 1.0)
    reasons.append(f"tier={tier or 'unknown'}:{weight:g}")

    cmc = row.get("cmc_fr13_only") or row.get("cmc_full") or {}
    summary = cmc.get("summary", {}) if isinstance(cmc, dict) else {}
    risk = str(summary.get("risk_level", "unknown")).lower()
    risk_mult = RISK_WEIGHT.get(risk, 0.8)
    weight *= risk_mult
    reasons.append(f"cmc_risk={risk}:{risk_mult:g}")

    total_flags = summary.get("total_flags")
    if isinstance(total_flags, (int, float)):
        # Gentle penalty: avoid over-amplifying a single sequence-only CMC scan.
        flag_mult = 1.0 / (1.0 + 0.20 * float(total_flags))
        weight *= flag_mult
        reasons.append(f"cmc_flags={total_flags}:{flag_mult:.3f}")

    dev = row.get("developability") or {}
    if isinstance(dev, dict):
        instability = dev.get("instability_index")
        if isinstance(instability, (int, float)) and instability > 40:
            weight *= 0.7
            reasons.append("instability>40:0.7")
        gravy = dev.get("gravy")
        if isinstance(gravy, (int, float)) and gravy > 0.2:
            weight *= 0.75
            reasons.append("gravy>0.2:0.75")
        pi = dev.get("pI")
        if isinstance(pi, (int, float)):
            if locus == "IGHV" and not (5.5 <= pi <= 10.5):
                weight *= 0.8
                reasons.append("vh_pI_outside_soft_range:0.8")
            if locus in {"IGKV", "IGLV"} and not (4.0 <= pi <= 9.0):
                weight *= 0.8
                reasons.append("vl_pI_outside_soft_range:0.8")

    if species == "dog" and locus == "IGHV":
        gene = row.get("gene", "")
        # In-repo dog repertoire prior: VH1-62/VH1-44 map to these IMGT ids.
        if gene in {"IGHV3-38*01", "IGHV3-23*01"}:
            weight *= 3.0
            reasons.append("dog_vh_high_frequency_prior:3.0")

    return max(weight, 0.01), reasons


def _row_sequence(row: dict[str, Any]) -> str:
    for key in ("sequence_aa_kabat_norm", "sequence_aa_imgt", "sequence_aa", "seq"):
        val = row.get(key)
        if isinstance(val, str) and val.strip():
            return val.strip()
    segs = row.get("fr_segments")
    if isinstance(segs, dict):
        return "".join(str(segs.get(k, "")) for k in ("FR1", "FR2", "FR3"))
    return ""


def _rows_from_registry(path: Path, species: str) -> list[dict[str, Any]]:
    data = _load_json(path)
    out = []
    for row in data.get("rows", []):
        locus = row.get("locus")
        chain = row.get("chain")
        seq = _row_sequence(row)
        if not locus or not seq:
            continue
        weight, reasons = _safe_weight(row, species=species, locus=str(locus))
        out.append(
            {
                "species": species,
                "locus": locus,
                "chain": chain,
                "gene": row.get("gene") or row.get("id") or row.get("raw_header", ""),
                "sequence": seq,
                "weight": weight,
                "weight_reasons": reasons,
                "source": str(path.relative_to(REPO_ROOT)),
            }
        )
    return out


def _rows_from_raw_germline(path: Path, species: str, locus: str) -> list[dict[str, Any]]:
    data = _load_json(path)
    out = []
    for ent in data.get("entries", []):
        header = ent.get("raw_header", "")
        # Prefer functional genes for raw fallback tables.
        if "|F|" not in header and "|F-ORF|" not in header:
            continue
        seq = ent.get("sequence_aa", "")
        if not seq:
            continue
        out.append(
            {
                "species": species,
                "locus": locus,
                "chain": "VH" if locus == "IGHV" else "VL",
                "gene": ent.get("id", ""),
                "sequence": seq,
                "weight": 1.0,
                "weight_reasons": ["raw_functional_germline:1.0"],
                "source": str(path.relative_to(REPO_ROOT)),
            }
        )
    return out


def _merge_registry_with_raw(
    registry_rows: list[dict[str, Any]],
    raw_rows: list[dict[str, Any]],
    *,
    locus: str,
) -> tuple[list[dict[str, Any]], str]:
    selected = [r for r in registry_rows if r["locus"] == locus]
    if selected:
        return selected, "curated_registry_cmc_weighted"
    return raw_rows, "raw_functional_germline_unweighted"


def _make_frequency_table(
    rows: list[dict[str, Any]],
    *,
    species: str,
    locus: str,
    safe_numbering: bool = True,
    max_workers: int = 1,
) -> dict[str, Any]:
    counts: dict[str, dict[str, float]] = defaultdict(lambda: defaultdict(float))
    support: dict[str, list[dict[str, Any]]] = defaultdict(list)
    failures: list[dict[str, str]] = []

    print(f"[build] {species} {locus}: numbering {len(rows)} sequences", flush=True)

    def number_one(row: dict[str, Any]) -> tuple[dict[str, Any], list[dict[str, Any]]]:
        if safe_numbering:
            return row, _number_kabat(row["sequence"])
        with contextlib.redirect_stdout(io.StringIO()):
            return row, _number_kabat_inprocess(row["sequence"])

    numbered_rows: list[tuple[dict[str, Any], list[dict[str, Any]]]] = []
    if max_workers > 1:
        completed = 0
        with ThreadPoolExecutor(max_workers=max_workers) as executor:
            future_to_row = {executor.submit(number_one, row): row for row in rows}
            for future in as_completed(future_to_row):
                completed += 1
                if completed == 1 or completed % 25 == 0 or completed == len(rows):
                    print(f"  - {species} {locus}: {completed}/{len(rows)}", flush=True)
                row = future_to_row[future]
                try:
                    numbered_rows.append(future.result())
                except Exception as exc:
                    failures.append({"gene": row.get("gene", ""), "error": str(exc)})
    else:
        for idx, row in enumerate(rows, start=1):
            if idx == 1 or idx % 25 == 0 or idx == len(rows):
                print(f"  - {species} {locus}: {idx}/{len(rows)}", flush=True)
            try:
                numbered_rows.append(number_one(row))
            except Exception as exc:
                failures.append({"gene": row.get("gene", ""), "error": str(exc)})
                continue

    for row, numbered in numbered_rows:
        for nr in numbered:
            key = nr["key"]
            aa = nr["aa"]
            counts[key][aa] += float(row["weight"])
            support[key].append(
                {
                    "gene": row.get("gene", ""),
                    "aa": aa,
                    "weight": round(float(row["weight"]), 4),
                }
            )

    positions: dict[str, Any] = {}
    for key in sorted(counts, key=_kabat_sort_key):
        total = sum(counts[key].values())
        if total <= 0:
            continue
        freqs = {aa: counts[key].get(aa, 0.0) / total for aa in AA_ORDER if counts[key].get(aa, 0.0) > 0}
        freqs = dict(sorted(freqs.items(), key=lambda kv: (-kv[1], kv[0])))
        preferred = next(iter(freqs)) if freqs else None
        allowed = [aa for aa, f in freqs.items() if f >= 0.10]
        if preferred and preferred not in allowed:
            allowed.insert(0, preferred)
        avoid = [aa for aa in AA_ORDER if aa not in allowed and freqs.get(aa, 0.0) < 0.02]
        top_support = sorted(support[key], key=lambda r: (-r["weight"], r["gene"]))[:10]
        positions[key] = {
            "preferred": preferred,
            "allowed_ge_0_10": allowed,
            "frequencies": {aa: round(f, 5) for aa, f in freqs.items()},
            "avoid_lt_0_02_or_absent": avoid,
            "support_n": len(support[key]),
            "weighted_support": round(total, 5),
            "top_support": top_support,
        }

    return {
        "metadata": {
            "table_schema": "position_specific_aa_frequency_v1",
            "species": species,
            "locus": locus,
            "generated_at": datetime.now(timezone.utc).isoformat(),
            "position_scheme": "Kabat via anarcii.to_scheme('kabat')",
            "sequence_count_input": len(rows),
            "sequence_count_numbering_failed": len(failures),
            "aa_order": AA_ORDER,
            "numbering_mode": "subprocess_timeout" if safe_numbering else "trusted_inprocess",
            "numbering_workers": max_workers,
        },
        "positions": positions,
        "numbering_failures": failures,
    }


def _make_frequency_table_from_profile(
    profile: dict[str, dict[str, float]],
    *,
    species: str,
    locus: str,
    source: str,
) -> dict[str, Any]:
    positions: dict[str, Any] = {}
    for key in sorted(profile, key=_kabat_sort_key):
        raw_freqs = profile[key]
        freqs = {
            aa: float(freq)
            for aa, freq in raw_freqs.items()
            if aa in AA_ORDER and isinstance(freq, (int, float)) and float(freq) > 0
        }
        if not freqs:
            continue
        freqs = dict(sorted(freqs.items(), key=lambda kv: (-kv[1], kv[0])))
        preferred = next(iter(freqs))
        allowed = [aa for aa, f in freqs.items() if f >= 0.10]
        if preferred not in allowed:
            allowed.insert(0, preferred)
        avoid = [aa for aa in AA_ORDER if aa not in allowed and freqs.get(aa, 0.0) < 0.02]
        positions[key] = {
            "preferred": preferred,
            "allowed_ge_0_10": allowed,
            "frequencies": {aa: round(f, 5) for aa, f in freqs.items()},
            "avoid_lt_0_02_or_absent": avoid,
            "support_n": None,
            "weighted_support": None,
            "top_support": [],
        }
    return {
        "metadata": {
            "table_schema": "position_specific_aa_frequency_v1",
            "species": species,
            "locus": locus,
            "generated_at": datetime.now(timezone.utc).isoformat(),
            "position_scheme": "Kabat",
            "sequence_count_input": None,
            "sequence_count_numbering_failed": 0,
            "aa_order": AA_ORDER,
            "weighting": "llamanade_human_vh_ngs_profile",
            "source": source,
            "source_note": "Precomputed human VH position-frequency matrix from Llamanade resources.",
        },
        "positions": positions,
        "numbering_failures": [],
    }


def _kabat_sort_key(key: str) -> tuple[int, str]:
    digits = "".join(ch for ch in key if ch.isdigit())
    letters = "".join(ch for ch in key if ch.isalpha())
    return int(digits or 0), letters


def _make_surface_swaps(freq_table: dict[str, Any]) -> dict[str, Any]:
    swaps: dict[str, Any] = {}
    for pos, item in freq_table["positions"].items():
        freqs = item.get("frequencies", {})
        polar_ranked = [aa for aa, _ in sorted(freqs.items(), key=lambda kv: (-kv[1], kv[0])) if aa in POLAR_OR_CHARGED]
        if not polar_ranked:
            continue
        hydrophobic_present = [aa for aa in HYDROPHOBIC if aa in freqs or aa not in item.get("allowed_ge_0_10", [])]
        if not hydrophobic_present:
            continue
        swaps[pos] = {
            "from_hydrophobic": sorted(HYDROPHOBIC),
            "preferred_surface_replacements": polar_ranked[:3],
            "frequency_context": {aa: freqs.get(aa, 0.0) for aa in polar_ranked[:3]},
            "rule": "apply_only_if_FR_surface_exposed_non_protected_and_donor_aa_is_hydrophobic",
        }
    return {
        "metadata": {
            "table_schema": "pet_surface_swap_preferences_v1",
            "species": freq_table["metadata"]["species"],
            "locus": freq_table["metadata"]["locus"],
            "source_frequency_table": freq_table["metadata"]["table_schema"],
            "generated_at": datetime.now(timezone.utc).isoformat(),
        },
        "positions": swaps,
    }


def _make_vhh_compatible_rules(species: str) -> dict[str, Any]:
    return {
        "metadata": {
            "table_schema": "pet_vhh_compatible_rules_v1",
            "species": species,
            "generated_at": datetime.now(timezone.utc).isoformat(),
            "scope": "Use with VHH/sdAb frameworks where ordinary pet VH frequencies may conflict with single-domain solubility.",
        },
        "hard_protect_kabat": {
            "cdrs": {
                "H1": "26-35",
                "H2": "50-65",
                "H3": "95-102/103 plus insertions",
            },
            "canonical_cys": ["22", "92"],
            "vhh_scaffold_hallmark": ["37", "44", "45", "47"],
            "vernier_support": ["2", "27", "28", "29", "30", "48", "49", "67", "69", "71", "73", "78", "93", "94"],
        },
        "notes": [
            "Do not force ordinary pet VH hydrophobic VL-interface residues into autonomous VHH/sdAb designs.",
            "For A6L-like anti-albumin VHHs, CDR lock and structure/SASA contact review must override frequency substitutions.",
            "Surface swap tables are advisory; only apply to FR, non-protected, solvent-exposed residues.",
        ],
    }


def _summary_md(outputs: list[tuple[str, dict[str, Any], str]]) -> str:
    lines = [
        "# Dog/Cat/Human Replacement Tables v1",
        "",
        f"Generated: {datetime.now(timezone.utc).isoformat()}",
        "",
        "## Scope",
        "",
        "Position-specific amino-acid frequencies for dog/cat petization and humanization reference lookup. Dog VH includes available in-repo repertoire priors where mapped; cat uses CMC/tier-weighted curated scaffold rows because no feline in-vivo abundance table was found in-repo; human germline tables use functional IMGT germlines, with an additional Llamanade human VH NGS profile where available.",
        "",
        "## Tables",
        "",
        "| File | Species | Locus | Weighting | Positions | Input rows | Numbering failures |",
        "|---|---|---|---|---:|---:|---:|",
    ]
    for filename, table, weighting in outputs:
        meta = table["metadata"]
        lines.append(
            f"| `{filename}` | {meta['species']} | {meta['locus']} | {weighting} | "
            f"{len(table['positions'])} | {meta['sequence_count_input']} | {meta['sequence_count_numbering_failed']} |"
        )
    lines.extend(
        [
            "",
            "## Weighting Rules",
            "",
            "- Tier: tier1=3.0, tier2=1.5, tier3=0.5.",
            "- CMC risk: low=1.0, medium=0.6, high=0.25.",
            "- CMC flag penalty: `1 / (1 + 0.20 * total_flags)`.",
            "- Developability penalties: instability index >40, GRAVY >0.2, or extreme pI.",
            "- Dog VH prior: `IGHV3-38*01` and `IGHV3-23*01` get ×3.0, based on the in-repo VH1-62/VH1-44 high-frequency mapping.",
            "- Human IGHV/IGKV/IGLV germline tables are unweighted functional-germline frequency references.",
            "- `human_ighv_llamanade_ngs_replacement_frequency_v1.json` is a precomputed human VH NGS profile from Llamanade resources.",
            "",
            "## Limitations",
            "",
            "- Dog heavy-chain abundance is semi-weighted from literature/population priors, not a complete gene-by-gene BCR-seq abundance matrix.",
            "- Dog light-chain and cat heavy/light-chain tables are CMC/tier weighted, not in-vivo abundance weighted.",
            "- Human germline tables are not clinical-anchor rankings; clinical-anchor framework selection remains governed by the humanization pipeline registry.",
            "- Tables are engineering references. CDR preservation and structure QC remain mandatory for petization/humanization deliverables.",
        ]
    )
    return "\n".join(lines) + "\n"


def _collect_existing_outputs(out_dir: Path) -> list[tuple[str, dict[str, Any], str]]:
    outputs: list[tuple[str, dict[str, Any], str]] = []
    for path in sorted(out_dir.glob("*_replacement_frequency_v1.json")):
        table = _load_json(path)
        meta = table.get("metadata", {})
        outputs.append((path.name, table, str(meta.get("weighting", "unknown"))))
    return outputs


def build(out_dir: Path, *, species_filter: set[str] | None = None) -> None:
    out_dir.mkdir(parents=True, exist_ok=True)

    dog_registry_rows = _rows_from_registry(DOG_REGISTRY, "dog")
    cat_registry_rows = _rows_from_registry(CAT_REGISTRY, "cat")

    outputs: list[tuple[str, dict[str, Any], str]] = []

    specs = [
        ("dog", "IGHV", DOG_DIR / "IGHV_aa.json", dog_registry_rows),
        ("dog", "IGKV", DOG_DIR / "IGKV_aa.json", dog_registry_rows),
        ("dog", "IGLV", DOG_DIR / "IGLV_aa.json", dog_registry_rows),
        ("cat", "IGHV", None, cat_registry_rows),
        ("cat", "IGKV", CAT_DIR / "IGKV_aa.json", cat_registry_rows),
        ("cat", "IGLV", CAT_DIR / "IGLV_aa.json", cat_registry_rows),
        ("human", "IGHV", HUMAN_DIR / "IGHV_aa.json", []),
        ("human", "IGKV", HUMAN_DIR / "IGKV_aa.json", []),
        ("human", "IGLV", HUMAN_DIR / "IGLV_aa.json", []),
    ]

    for species, locus, raw_path, registry_rows in specs:
        if species_filter and species not in species_filter:
            continue
        raw_rows: list[dict[str, Any]] = []
        if raw_path and raw_path.exists():
            raw_rows = _rows_from_raw_germline(raw_path, species, locus)
        rows, weighting = _merge_registry_with_raw(registry_rows, raw_rows, locus=locus)
        table = _make_frequency_table(
            rows,
            species=species,
            locus=locus,
            safe_numbering=True,
            max_workers=8,
        )
        table["metadata"]["weighting"] = weighting
        if species == "dog" and locus == "IGHV":
            table["metadata"]["repertoire_prior_file"] = str(DOG_REPERTOIRE.relative_to(REPO_ROOT))
        filename = f"{species}_{locus.lower()}_replacement_frequency_v1.json"
        _write_json(out_dir / filename, table)
        outputs.append((filename, table, weighting))

        swap_filename = f"{species}_{locus.lower()}_surface_swaps_v1.json"
        _write_json(out_dir / swap_filename, _make_surface_swaps(table))

    for species in ("dog", "cat"):
        _write_json(out_dir / f"{species}_vhh_compatible_rules_v1.json", _make_vhh_compatible_rules(species))

    if (species_filter is None or "human" in species_filter) and LLAMANADE_HUMAN_VH_PROFILE.exists():
        rel_source = str(LLAMANADE_HUMAN_VH_PROFILE.relative_to(REPO_ROOT))
        table = _make_frequency_table_from_profile(
            _load_json(LLAMANADE_HUMAN_VH_PROFILE),
            species="human",
            locus="IGHV",
            source=rel_source,
        )
        filename = "human_ighv_llamanade_ngs_replacement_frequency_v1.json"
        _write_json(out_dir / filename, table)
        outputs.append((filename, table, table["metadata"]["weighting"]))
        _write_json(out_dir / "human_ighv_llamanade_ngs_surface_swaps_v1.json", _make_surface_swaps(table))

    (out_dir / "README_pet_replacement_tables_v1.md").write_text(
        _summary_md(_collect_existing_outputs(out_dir)),
        encoding="utf-8",
    )


def main() -> None:
    ap = argparse.ArgumentParser(description="Build dog/cat/human replacement tables")
    ap.add_argument("--number-one", action="store_true", help=argparse.SUPPRESS)
    ap.add_argument(
        "--out-dir",
        default=str(REPO_ROOT / "projects" / "pet_replacement_tables" / "v1"),
        help="Output directory",
    )
    ap.add_argument(
        "--species",
        choices=["dog", "cat", "human"],
        action="append",
        help="Limit generation to one or more species; repeat flag for multiple species.",
    )
    args = ap.parse_args()
    if args.number_one:
        seq = sys.stdin.read().strip()
        # Suppress ANARCII progress text; emit machine-readable JSON only.
        with contextlib.redirect_stdout(io.StringIO()):
            rows = _number_kabat_inprocess(seq)
        print(json.dumps(rows, ensure_ascii=False))
        return
    build(Path(args.out_dir), species_filter=set(args.species) if args.species else None)
    print(f"Wrote replacement tables to {Path(args.out_dir).resolve()}")


if __name__ == "__main__":
    main()
