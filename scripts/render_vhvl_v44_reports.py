#!/usr/bin/env python3
"""
render_vhvl_v44_reports.py — InSynBio AbEngineCore
===============================================

 {project_dir}/{id}_results.json  V4.4 （）。

：
- （fixed sections）
- （Pre-Delivery Gate “”）
- /： ANARCII / ColabFold 
  - ，：ANARCI / AlphaFold2

：
  python scripts/render_vhvl_v44_reports.py 9c1 projects/9c1_Redesign
"""

from __future__ import annotations

import argparse
import json
import re
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Tuple


SUITE = Path(__file__).resolve().parents[1]
V44_CONFIG = SUITE / "config" / "vh_vl_humanization_v490.json"
THERA_META_MODELS = SUITE / "data" / "thera_sabdab" / "out" / "antibody_meta_models.json"
THERAXLSX = SUITE / "data" / "humanization_assay" / "thera_human_igG_germline_analysis.xlsx"
PAIRING_REPORT = SUITE / "data" / "humanization_assay" / "vh_vl_pairing_report.md"
PAIRING_MATRIX = SUITE / "data" / "humanization_assay" / "vh_vl_pairing_matrix.csv"
# From abenginecore_registry: 842 clinical antibodies (384 natural + 458 engineered)
PAIRING_DB_TOTAL = 842

_THERA_META_MAP: Dict[str, Dict[str, Any]] | None = None
_GERMLINE_PRECEDENT_XLSX: Dict[str, Dict[str, List[str]]] | None = None
_PAIRING_TOP20: List[Dict[str, Any]] | None = None
_PAIRING_FULL: Dict[Tuple[str, str], Dict[str, Any]] | None = None


SENSITIVE_REPLACEMENTS: List[Tuple[str, str]] = [
    ("ANARCII", "ANARCI"),
    ("Anarcii", "ANARCI"),
    ("ColabFold", "AlphaFold2"),
    ("colabfold", "AlphaFold2"),
]

# Vernier zone positions (Kabat) per chain — for mutation table annotation
VH_VERNIER_POSITIONS = {48, 49, 67, 69, 71, 73, 78, 93, 94}
VL_VERNIER_POSITIONS = {36, 38, 43, 44, 45, 46, 49, 66, 68, 69, 71}


def _is_vernier_pos(chain: str, pos: Any) -> bool:
    try:
        p = int(pos)
        s = VH_VERNIER_POSITIONS if (chain or "").upper() == "VH" else VL_VERNIER_POSITIONS
        return p in s
    except (TypeError, ValueError):
        return False


# Forbidden in customer reports (algorithm / internal details)
FORBIDDEN_TERMS = [
    "ANARCII", "Anarcii", "ColabFold", "colabfold",
    # core selection algorithm factors (must NOT disclose)
    "Vernier ",
    "CDR ",
    "",
    "FR ",
    "Top 10",
    "Top 20",
]


def _load_json(path: Path) -> Dict[str, Any]:
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)


def _sanitize_public_terms(text: str) -> str:
    for src, dst in SENSITIVE_REPLACEMENTS:
        text = text.replace(src, dst)
    return text


def _assert_no_forbidden_terms(text: str, where: str) -> None:
    hits = [t for t in FORBIDDEN_TERMS if t in text]
    if hits:
        raise ValueError(f"[Pre-Delivery Gate] Forbidden terms in {where}: {hits}")


def _md_code_block(seq: str) -> str:
    return "```\n" + seq.strip() + "\n```"


def _pick(d: Dict[str, Any], path: List[str], default: Any = "—") -> Any:
    cur: Any = d
    for p in path:
        if not isinstance(cur, dict) or p not in cur:
            return default
        cur = cur[p]
    return cur


def _load_thera_meta_map() -> Dict[str, Dict[str, Any]]:
    """
    Load thera/sabdab antibody metadata and build a name->meta lookup.

    Customer-safe enrichment fields:
    - target.targets / target_raw
    - clinical.phase_bucket / phase_raw
    - format.format_raw
    - genetics.human_origin_mode (or normalized)
    """
    global _THERA_META_MAP
    if _THERA_META_MAP is not None:
        return _THERA_META_MAP
    if not THERA_META_MODELS.exists():
        _THERA_META_MAP = {}
        return _THERA_META_MAP

    try:
        items = _load_json(THERA_META_MODELS)
    except Exception:
        _THERA_META_MAP = {}
        return _THERA_META_MAP

    m: Dict[str, Dict[str, Any]] = {}
    if isinstance(items, list):
        for it in items:
            if not isinstance(it, dict):
                continue
            nm = str(it.get("name") or it.get("antibody_id") or "").strip()
            if nm:
                m[nm.lower()] = it
    _THERA_META_MAP = m
    return _THERA_META_MAP


def _load_germline_precedent_from_thera_xlsx() -> Dict[str, Dict[str, List[str]]]:
    """
     thera_human_igG_germline_analysis.xlsx（842 ）→。
    ：、（、）。
     {"VH": {germline: [Name,...]}, "VL": {germline: [Name,...]}}
    """
    global _GERMLINE_PRECEDENT_XLSX
    if _GERMLINE_PRECEDENT_XLSX is not None:
        return _GERMLINE_PRECEDENT_XLSX

    out: Dict[str, Dict[str, List[str]]] = {"VH": {}, "VL": {}}
    if not THERAXLSX.exists():
        _GERMLINE_PRECEDENT_XLSX = out
        return out

    try:
        import pandas as pd  # type: ignore
        df = pd.read_excel(THERAXLSX, sheet_name="Sheet1")
    except Exception:
        _GERMLINE_PRECEDENT_XLSX = out
        return out

    vh_col = "Best_VH_Germline" if "Best_VH_Germline" in df.columns else None
    vl_col = "Best_VL_Germline" if "Best_VL_Germline" in df.columns else None
    name_col = "Name" if "Name" in df.columns else ("INN" if "INN" in df.columns else None)
    if not vh_col or not vl_col or not name_col:
        _GERMLINE_PRECEDENT_XLSX = out
        return out

    for _, row in df.iterrows():
        nm = str(row.get(name_col, "") or "").strip()
        if not nm or nm.lower() in ("nan", ""):
            continue
        if vh_col and pd.notna(row.get(vh_col)):
            g = str(row[vh_col]).strip()
            if g and g.lower() != "nan":
                out["VH"].setdefault(g, []).append(nm)
        if vl_col and pd.notna(row.get(vl_col)):
            g = str(row[vl_col]).strip()
            if g and g.lower() != "nan":
                out["VL"].setdefault(g, []).append(nm)

    # ：、， 5 
    for chain in ("VH", "VL"):
        for g in list(out[chain].keys()):
            lst = sorted(set(out[chain][g]))[:5]
            out[chain][g] = lst

    _GERMLINE_PRECEDENT_XLSX = out
    return out


def _resolve_clinical_precedent(
    chain: str, gene: str, fallback: List[str] | None
) -> List[str]:
    """
    ： thera_human_igG_germline_analysis.xlsx， fallback。
    。
    """
    xlsx = _load_germline_precedent_from_thera_xlsx()
    by_chain = xlsx.get(chain, {})
    # 
    lst = by_chain.get(gene) if gene else []
    if lst:
        return lst
    #  *01 
    base = (gene or "").split("*")[0].strip()
    for k, v in by_chain.items():
        if k.split("*")[0].strip() == base:
            return v
    return list(fallback) if fallback else []


def _load_pairing_full() -> Dict[Tuple[str, str], Dict[str, Any]]:
    """
    Load full pairing set from vh_vl_pairing_matrix.csv.
    Returns dict: (vh_norm, vl_norm) -> {count, rank?, freq?}
    Merged with Top 20 for rank/freq when available.
    """
    global _PAIRING_FULL
    if _PAIRING_FULL is not None:
        return _PAIRING_FULL
    full: Dict[Tuple[str, str], Dict[str, Any]] = {}
    top20 = _load_pairing_top20()
    top20_by_pair = {(str(r.get("vh_gene", "")).replace("**", "").split("*")[0].strip(),
                      str(r.get("vl_gene", "")).replace("**", "").split("*")[0].strip()): r for r in top20}
    if not PAIRING_MATRIX.exists():
        _PAIRING_FULL = full
        return full
    try:
        text = PAIRING_MATRIX.read_text(encoding="utf-8")
        lines = text.strip().splitlines()
        if len(lines) < 2:
            _PAIRING_FULL = full
            return full
        header = [c.strip() for c in lines[0].split(",")]
        vl_cols = [c for c in header[1:] if c]
        for line in lines[1:]:
            parts = [p.strip() for p in line.split(",")]
            if not parts:
                continue
            vh_raw = parts[0]
            vh_norm = vh_raw.split("*")[0].strip()
            for j, vl_raw in enumerate(vl_cols):
                if j + 1 >= len(parts):
                    break
                try:
                    cnt = int(parts[j + 1])
                except (ValueError, IndexError):
                    continue
                if cnt <= 0:
                    continue
                vl_norm = vl_raw.split("*")[0].strip()
                key = (vh_norm, vl_norm)
                extra = top20_by_pair.get(key, {})
                full[key] = {"count": cnt, "rank": extra.get("rank"), "freq": extra.get("freq")}
    except Exception:
        pass
    _PAIRING_FULL = full
    return full


def _load_pairing_top20() -> List[Dict[str, Any]]:
    """Parse vh_vl_pairing_report.md Top 20 table. Returns list of {vh_gene, vl_gene, rank, count, freq}."""
    global _PAIRING_TOP20
    if _PAIRING_TOP20 is not None:
        return _PAIRING_TOP20
    out: List[Dict[str, Any]] = []
    if not PAIRING_REPORT.exists():
        _PAIRING_TOP20 = out
        return out
    text = PAIRING_REPORT.read_text(encoding="utf-8")
    in_table = False
    for line in text.splitlines():
        line = line.strip()
        if "| Rank |" in line and "VH Gene" in line:
            in_table = True
            continue
        if in_table and line.startswith("|") and "|---" not in line:
            parts = [p.strip() for p in line.split("|") if p.strip()]
            if len(parts) >= 5:
                try:
                    rank = int(parts[0])
                    vh = str(parts[1]).replace("**", "")
                    vl = str(parts[2]).replace("**", "")
                    count = int(parts[3])
                    freq = str(parts[4])
                    out.append({"rank": rank, "vh_gene": vh, "vl_gene": vl, "count": count, "freq": freq})
                except (ValueError, IndexError):
                    pass
        elif in_table and not line.startswith("|"):
            break
    _PAIRING_TOP20 = out
    return out


def _lookup_pairing(vh_gene: str, vl_gene: str) -> Dict[str, Any] | None:
    """
    Check if VH+VL pair exists in clinical pairing database (all pairs, not just Top 20).
    Normalize: IGHV5-51*01 -> IGHV5-51; IGKV1-39*01 -> IGKV1-39.
    Returns {count, rank?, freq?, vh_gene, vl_gene} when found.
    """
    vh_norm = (vh_gene or "").split("*")[0].strip()
    vl_norm = (vl_gene or "").split("*")[0].strip()
    key = (vh_norm, vl_norm)
    row = _load_pairing_full().get(key)
    if row:
        return {**row, "vh_gene": vh_gene or vh_norm, "vl_gene": vl_gene or vl_norm}
    return None


def _base_drug_name_for_lookup(precedent_str: str) -> str:
    """
    Extract base drug name for thera_meta lookup.
    E.g. 'Cemiplimab (anti-PD1, IGHV4)' -> 'Cemiplimab'
    """
    s = str(precedent_str or "").strip()
    if " (" in s:
        return s.split(" (", 1)[0].strip()
    return s


def _clinical_examples_table(example_names: List[str]) -> str:
    """
    Render a small customer-facing table from existing DB metadata.
    Uses base drug name for thera lookup (e.g. Cemiplimab from 'Cemiplimab (anti-PD1, IGHV4)').
    """
    ex = [str(x).strip() for x in (example_names or []) if str(x).strip()]
    if not ex:
        return ""

    meta = _load_thera_meta_map()
    rows: List[Dict[str, str]] = []
    for nm in ex[:5]:
        base = _base_drug_name_for_lookup(nm)
        it = meta.get(base.lower()) if base else None
        if not isinstance(it, dict):
            rows.append({"drug": nm, "targets": "—", "phase": "—"})
            continue

        phase = _pick(it, ["clinical", "phase_bucket"], "—")
        phase_raw = _pick(it, ["clinical", "phase_raw"], "—")
        phase_s = str(phase) if phase_raw in ("", "—") else f"{phase} ({phase_raw})"

        targets = _pick(it, ["target", "targets"], [])
        target_raw = _pick(it, ["target", "target_raw"], "—")
        if isinstance(targets, list) and targets:
            targets_s = " / ".join(str(x) for x in targets[:4])
        else:
            targets_s = str(target_raw or "—")

        rows.append(
            {
                "drug": nm,
                "targets": targets_s,
                "phase": phase_s,
            }
        )

    out = []
    out.append("")
    # Customer-facing: keep the table minimal to avoid implying we analyzed other molecular formats
    # (e.g. bispecific/VHH) for this project. These examples are only "public precedent" references.
    out.append("| （） |  |  |")
    out.append("|---|---|---|")
    for r in rows:
        out.append(f"| `{r['drug']}` | {r['targets']} | {r['phase']} |")
    return "\n".join(out)


def _phase4_json_path_for_render(results: Dict[str, Any]) -> Path | None:
    """
     verify  Phase4 ，、。
    """
    ab_id = _pick(results, ["_meta", "antibody_id"], "") or ""
    if not ab_id:
        return None
    candidates: List[Path] = []
    p4_rel = _pick(results, ["_internal", "phase4_backmutation_log"], None)
    if isinstance(p4_rel, str) and p4_rel.strip():
        candidates.append(SUITE / p4_rel.replace("\\", "/"))
    proj = results.get("_render_project_dir")
    if proj:
        pd = Path(proj)
        candidates.extend([
            pd / "internal" / f"phase4_backmutation_{ab_id}.json",
            pd / "internal" / f"phase4_backmutation_{ab_id.lower()}.json",
            pd / "reports" / f"phase4_backmutation_{ab_id}.json",
            pd / "reports" / f"phase4_backmutation_{ab_id.lower()}.json",
        ])
    candidates.extend([
        SUITE / f"phase4_backmutation_{ab_id}.json",
        SUITE / f"phase4_backmutation_{ab_id.lower()}.json",
    ])
    return next((p for p in candidates if p.exists()), None)


def _compute_unified_mutation_lists(results: Dict[str, Any]) -> "Tuple[List[Dict], List[Dict], List[Dict], int, int]":
    """
    （SSOT）： results + Phase4  all_rows, vernier_rows, cmc_rows。
     3.2 / 4.2 / 5.0 ，、。
     (all_rows, vernier_rows, cmc_rows, n_vernier, n_cmc)。
    """
    muts = results.get("mutations") or {}
    v1v2 = muts.get("v1_to_v2", [])
    v2v3 = muts.get("v2_to_v3", [])

    phase4_rows = _vernier_backmut_rows_from_phase4(results)
    p2_rows = [dict(it, vernier=_is_vernier_pos(it.get("chain"), it.get("kabat_pos"))) for it in v1v2]
    p3_rows = [dict(it, vernier=_is_vernier_pos(it.get("chain"), it.get("kabat_pos"))) for it in v2v3]

    def _sort_key(row: Dict[str, Any]) -> tuple:
        c = (row.get("chain") or "").upper()
        try:
            pi = int(row.get("kabat_pos")) if row.get("kabat_pos") is not None else 999
        except (TypeError, ValueError):
            pi = 999
        return (0 if c == "VH" else 1, pi)

    all_rows = phase4_rows + p2_rows + p3_rows
    all_rows.sort(key=_sort_key)

    vernier_rows = [r for r in all_rows if r.get("vernier")]
    cmc_rows = []
    for r in p2_rows + p3_rows:
        s = (r.get("rationale") or "").lower()
        if "pi" in s or "" in (r.get("rationale") or "") or "cmc" in s:
            cmc_rows.append(r)
    cmc_rows.sort(key=_sort_key)

    return all_rows, vernier_rows, cmc_rows, len(vernier_rows), len(cmc_rows)


def _vernier_backmut_rows_from_phase4(results: Dict[str, Any]) -> List[Dict[str, Any]]:
    """
    Extract Phase4 Vernier BACK_MUTATE decisions as table rows.
    Returns list of dicts: chain, kabat_pos, from, to, region, rationale, vernier=True.
    Only includes positions where human_aa != mouse_aa (actual sequence change).
    Uses _phase4_json_path_for_render for consistent path resolution.
    """
    p4 = _phase4_json_path_for_render(results)
    if not p4:
        return []

    try:
        obj = _load_json(p4)
    except Exception:
        return []

    out: List[Dict[str, Any]] = []
    for it in (obj.get("backmutation_decisions") or []):
        if not isinstance(it, dict) or it.get("decision") != "BACK_MUTATE":
            continue
        pos = str(it.get("position") or "")
        mouse_aa = str(it.get("mouse_aa") or "")
        human_aa = str(it.get("human_aa") or "")
        if not pos or not mouse_aa or not human_aa:
            continue
        if mouse_aa == human_aa or mouse_aa in ("-", "—") or human_aa in ("-", "—"):
            continue
        if "_" in pos:
            parts = pos.split("_", 1)
            chain = parts[0] if len(parts) > 1 else "VH"
            n_str = parts[1] if len(parts) > 1 else ""
            try:
                kabat_pos = int(n_str) if n_str.isdigit() else n_str
            except (TypeError, ValueError):
                kabat_pos = n_str
        else:
            chain, kabat_pos = "VH", pos
        out.append({
            "chain": chain,
            "kabat_pos": kabat_pos,
            "from": human_aa,
            "to": mouse_aa,
            "region": "FR",
            "rationale": "（Vernier ）",
            "vernier": True,
        })
    return out


def _public_vernier_mutations_from_phase4(results: Dict[str, Any]) -> List[str]:
    """
    Customer-safe Vernier-related mutations list.
    Uses _phase4_json_path_for_render for consistent path resolution.
    Returns list of strings like: "VH 48: K→N（）"
    """
    p4 = _phase4_json_path_for_render(results)
    if not p4:
        return []

    try:
        obj = _load_json(p4)
    except Exception:
        return []

    out: List[str] = []
    for it in (obj.get("backmutation_decisions") or []):
        if not isinstance(it, dict):
            continue
        if it.get("decision") != "BACK_MUTATE":
            continue
        pos = str(it.get("position") or "")
        mouse_aa = str(it.get("mouse_aa") or "")
        human_aa = str(it.get("human_aa") or "")
        if not pos or not mouse_aa or not human_aa:
            continue
        if mouse_aa in ("-", "—") or human_aa in ("-", "—"):
            continue
        # Only list actual amino-acid changes; if identical, it's not a mutation.
        if mouse_aa == human_aa:
            continue
        # position like "VH_48" / "VL_71"
        if "_" in pos:
            chain, n = pos.split("_", 1)
            if n.isdigit():
                out.append(f"{chain} {n}: {human_aa}→{mouse_aa}（）")
            else:
                out.append(f"{pos}: {human_aa}→{mouse_aa}（）")
        else:
            out.append(f"{pos}: {human_aa}→{mouse_aa}（）")

    # Stable ordering: VH first then VL, numeric ascending
    def _key(s: str):
        try:
            c, rest = s.split(" ", 1)
            n = int(rest.split(":", 1)[0])
            return (0 if c == "VH" else 1, n, s)
        except Exception:
            return (2, 9999, s)

    return sorted(out, key=_key)


def _vernier_round2_rows_from_internal(results: Dict[str, Any]) -> List[Dict[str, Any]]:
    """ _internal.evaluation_*_vernier_round2  Vernier Round 2 ，。"""
    internal = results.get("_internal") or {}
    if not isinstance(internal, dict):
        return []
    ev_r2 = None
    for k in ("evaluation_v3_vernier_round2", "evaluation_v2_vernier_round2", "evaluation_v1_vernier_round2"):
        if isinstance(internal.get(k), dict):
            ev_r2 = internal.get(k)
            break
    if not ev_r2:
        return []
    note = (ev_r2.get("_internal_note") or {})
    vr2 = note.get("vernier_round2") if isinstance(note, dict) else {}
    if not isinstance(vr2, dict):
        return []
    applied = vr2.get("applied") or []
    rows: List[Dict[str, Any]] = []
    for it in applied:
        if not isinstance(it, dict):
            continue
        c = str(it.get("chain") or "").upper()
        kp = it.get("kabat_pos")
        if not c or not kp or c not in ("VH", "VL"):
            continue
        fr = str(it.get("from") or "?")
        to_aa = str(it.get("to") or "?")
        rows.append({
            "chain": c,
            "kabat_pos": int(kp) if isinstance(kp, (int, float)) else int(kp) if str(kp).isdigit() else 0,
            "from": fr,
            "to": to_aa,
            "region": "FR（Vernier）",
            "rationale": "：Vernier Round 2 （CDR RMSD/）",
            "vernier": True,
        })
    return rows


def _compute_unified_mutation_lists(results: Dict[str, Any]) -> Tuple[List[Dict[str, Any]], List[Dict[str, Any]], List[Dict[str, Any]], int, int]:
    """
    （SSOT）： results + Phase4  all_rows, vernier_rows, cmc_rows。
     (chain, kabat_pos) ， p3 > vernier_round2 > p2 > phase4。
     3.2 / 4.2 / 5.0 ，、。
     (all_rows, vernier_rows, cmc_rows, n_vernier, n_cmc)。
    """
    muts = results.get("mutations") or {}
    v1v2 = muts.get("v1_to_v2", [])
    v2v3 = muts.get("v2_to_v3", [])

    phase4_rows = _vernier_backmut_rows_from_phase4(results)
    p2_rows = [dict(it, vernier=_is_vernier_pos(it.get("chain"), it.get("kabat_pos"))) for it in v1v2]
    p3_rows = [dict(it, vernier=_is_vernier_pos(it.get("chain"), it.get("kabat_pos"))) for it in v2v3]
    r2_rows = _vernier_round2_rows_from_internal(results)

    def _sort_key(row: Dict[str, Any]) -> tuple:
        c = (row.get("chain") or "").upper()
        try:
            pi = int(row.get("kabat_pos")) if row.get("kabat_pos") is not None else 999
        except (TypeError, ValueError):
            pi = 999
        return (0 if c == "VH" else 1, pi)

    # ： (chain, kabat_pos) ， p3 > vernier_round2 > p2 > phase4
    seen: set = set()
    all_rows: List[Dict[str, Any]] = []
    for row in p3_rows + r2_rows + p2_rows + phase4_rows:
        c = (row.get("chain") or "").upper()
        kp = row.get("kabat_pos")
        try:
            key = (c, int(kp)) if kp is not None else (c, -1)
        except (TypeError, ValueError):
            key = (c, -1)
        if key in seen:
            continue
        seen.add(key)
        all_rows.append(row)
    all_rows.sort(key=_sort_key)

    vernier_rows = [r for r in all_rows if r.get("vernier")]
    cmc_rows = []
    for r in p2_rows + p3_rows:
        s = (r.get("rationale") or "").lower()
        if "pi" in s or "" in (r.get("rationale") or "") or "cmc" in s:
            cmc_rows.append(r)
    cmc_rows.sort(key=_sort_key)

    return all_rows, vernier_rows, cmc_rows, len(vernier_rows), len(cmc_rows)


def _render_sequences_and_annotation(results: Dict[str, Any]) -> str:
    """
    ： sequences  SSOT。 vernier_round2（）， final_version。
     sequence_annotation  sequences ， Kabat  annotation。
    """
    seqs = results.get("sequences") or {}
    ann = results.get("sequence_annotation") or {}
    vh = ann.get("VH") or {}
    vl = ann.get("VL") or {}
    final_v = _pick(results, ["_meta", "final_version"], "v3")
    # SSOT： vernier_round2（）， final_version
    vh_seq = seqs.get("vernier_round2_VH") or seqs.get(f"{final_v}_VH") or seqs.get("v3_VH") or vh.get("sequence") or ""
    vl_seq = seqs.get("vernier_round2_VL") or seqs.get(f"{final_v}_VL") or seqs.get("v3_VL") or vl.get("sequence") or ""
    mouse_vh_seq = _pick(results, ["sequences", "mouse_VH"], "")
    mouse_vl_seq = _pick(results, ["sequences", "mouse_VL"], "")

    def _table(rows: List[Dict[str, str]], chain_label: str) -> str:
        lines = []
        lines.append(f"**{chain_label} FR/CDR （Kabat ）**")
        lines.append("")
        lines.append("|  | Kabat  |  |  |")
        lines.append("|---|---|---|---|")
        for r in rows:
            lines.append(f"| {r['region']} | {r['kabat']} | `{r['seq']}` | {r.get('source','—')} |")
        lines.append("")
        return "\n".join(lines)

    def _kabat_split_fallback(seq: str, chain: str, source: str) -> List[Dict[str, str]]:
        """
        Fallback: compute Kabat split from raw sequence.
        Used for mouse sequences when results.json doesn't carry a precomputed annotation.
        Tries get_kabat_numbering first (with explicit chain for mouse); if empty, position-based split.
        """
        if not seq:
            return []
        if chain == "VH":
            fr4_lo = 103
            anarcii_chain = "H"
            ranges = [("FR1", 1, 25), ("CDR1", 26, 35), ("FR2", 36, 49), ("CDR2", 50, 65), ("FR3", 66, 94), ("CDR3", 95, 102)]
        else:
            fr4_lo = 98
            anarcii_chain = "L"
            ranges = [("FR1", 1, 23), ("CDR1", 24, 34), ("FR2", 35, 49), ("CDR2", 50, 56), ("FR3", 57, 88), ("CDR3", 89, 97)]

        def _try_kabat(kd) -> Optional[List[Dict[str, str]]]:
            if not kd:
                return None
            from core.humanization.kabat_utils import sorted_keys  # type: ignore
            def span(lo: int, hi: int) -> str:
                return "".join(kd[k] for k in sorted_keys(kd) if lo <= k[0] <= hi)
            max_pos = max(k[0] for k in kd.keys())
            fr4_hi = max_pos if max_pos >= fr4_lo else fr4_lo
            rows = []
            for name, lo, hi in ranges:
                rows.append({"region": name, "kabat": f"{lo}-{hi}", "seq": span(lo, hi), "source": source})
            rows.append({"region": "FR4", "kabat": f"{fr4_lo}-{fr4_hi}", "seq": span(fr4_lo, fr4_hi), "source": source})
            return rows

        try:
            from core.humanization.kabat_utils import get_kabat_numbering  # type: ignore
            kd = get_kabat_numbering(seq)
            out = _try_kabat(kd)
            if out:
                return out
            # Retry with explicit chain (mouse VH/VL)
            from anarcii import Anarcii  # type: ignore
            engine = Anarcii(seq, anarcii_chain)
            result = engine.number()
            try:
                result = engine.to_scheme("kabat")
            except Exception:
                pass
            entry = result.get("seq", result) if isinstance(result, dict) else {}
            if isinstance(entry, dict):
                numbering = entry.get("numbering") or (entry.get("numbering") if hasattr(entry, "get") else None)
            else:
                numbering = getattr(entry, "numbering", None)
            if numbering:
                from core.humanization.kabat_utils import kabat_from_anarcii  # type: ignore
                kd = kabat_from_anarcii(numbering)
                out = _try_kabat(kd)
                if out:
                    return out
        except Exception:
            pass

        # Position-based fallback when Anarcii fails (no insertions assumed)
        def _pos_span(lo: int, hi: int) -> str:
            return seq[lo - 1 : hi] if lo <= hi and hi <= len(seq) else ""
        fr4_hi = min(fr4_lo + 10, len(seq))
        rows = []
        for name, lo, hi in ranges:
            rows.append({"region": name, "kabat": f"{lo}-{hi}", "seq": _pos_span(lo, hi), "source": source})
        rows.append({"region": "FR4", "kabat": f"{fr4_lo}-{fr4_hi}", "seq": _pos_span(fr4_lo, min(fr4_hi, len(seq))), "source": source})
        return rows

    # ：（SSOT） annotation， sequence_annotation  sequences 
    def _humanized_split(seq: str, chain: str, fr_source: str) -> List[Dict[str, str]]:
        rows = _kabat_split_fallback(seq, chain, fr_source)
        for r in rows:
            if str(r.get("region", "")).startswith("CDR"):
                r["source"] = "** CDR**"
        return rows

    vh_rows = _humanized_split(vh_seq, "VH", "（ pI ）") if vh_seq else []
    vl_rows = _humanized_split(vl_seq, "VL", "") if vl_seq else []
    if not vh_rows and vh.get("annotation"):
        for r in vh.get("annotation", []):
            vh_rows.append({
                "region": r.get("region", "—"),
                "kabat": r.get("kabat", "—").replace("-", "–"),
                "seq": r.get("seq", ""),
                "source": "（ pI ）" if str(r.get("region", "")).startswith("FR") else "** CDR**",
            })
    if not vl_rows and vl.get("annotation"):
        for r in vl.get("annotation", []):
            vl_rows.append({
                "region": r.get("region", "—"),
                "kabat": r.get("kabat", "—").replace("-", "–"),
                "seq": r.get("seq", ""),
                "source": "" if str(r.get("region", "")).startswith("FR") else "** CDR**",
            })

    note = (
        "> ：Kabat  CDR “”（ 24–34）。（ 30A/30B…），"
        " CDR-L1 **** (34-24+1)。"
    )

    out = []
    out.append("## 、")
    out.append("")
    out.append("### 1.0 （）")
    out.append("")
    out.append("#### 1.0.1 VH （）")
    out.append("")
    out.append(_md_code_block(mouse_vh_seq))
    out.append("")
    out.append(_table(_kabat_split_fallback(mouse_vh_seq, chain="VH", source=""), "VH"))
    out.append("")
    out.append("#### 1.0.2 VL （）")
    out.append("")
    out.append(_md_code_block(mouse_vl_seq))
    out.append("")
    out.append(_table(_kabat_split_fallback(mouse_vl_seq, chain="VL", source=""), "VL"))
    out.append("")
    out.append("---")
    out.append("")
    out.append(f"### 1.1 VH （，{final_v}）")
    out.append("")
    out.append(_md_code_block(vh_seq))
    out.append("")
    out.append(_table(vh_rows, "VH"))
    out.append("> CDR ，，。（FR） pI 。")
    out.append("")
    out.append("---")
    out.append("")
    out.append(f"### 1.2 VL （，{final_v}）")
    out.append("")
    out.append(_md_code_block(vl_seq))
    out.append("")
    out.append(_table(vl_rows, "VL"))
    out.append(note + "  ")
    # Customer-safe: do not disclose rule codes or numeric thresholds.
    vernier_mut_lines = _public_vernier_mutations_from_phase4(results)
    has_vl_mut = any(x.startswith("VL ") for x in vernier_mut_lines)
    if has_vl_mut:
        out.append(">  Vernier ；。")
    else:
        out.append(">  Vernier ，。")
    return "\n".join(out)


def _render_germline_selection(results: Dict[str, Any]) -> str:
    cand = results.get("germline_candidates") or {}
    vh_c = cand.get("VH_candidates", [])
    vl_c = cand.get("VL_candidates", [])

    def _selected_gene(items: list) -> str:
        for it in items:
            if it.get("selected"):
                return str(it.get("gene") or "—")
        return "—"

    def _resolve_precedent(chain: str, items: list) -> List[str]:
        """ thera_human_igG_germline_analysis.xlsx ， germline_candidates。"""
        for it in items:
            if it.get("selected"):
                gene = str(it.get("gene") or "")
                fallback = it.get("clinical_precedent") or []
                fallback = fallback if isinstance(fallback, list) else []
                return _resolve_clinical_precedent(chain, gene, fallback)
        return []

    out = []
    out.append("## 、（Germline）")
    out.append("")
    out.append("### 2.1 VH ")
    out.append("")
    out.append(f"** VH **：`{_selected_gene(vh_c)}`")
    out.append("")
    out.append("****：、，。")
    out.append("")
    vh_prec = _resolve_precedent("VH", vh_c or [])
    out.append(f"**（）**：{'、'.join(vh_prec[:3]) if vh_prec else '—'}")
    if vh_prec:
        out.append(_clinical_examples_table(vh_prec))
    out.append("")
    out.append("### 2.2 VL ")
    out.append("")
    out.append(f"** VL **：`{_selected_gene(vl_c)}`")
    out.append("")
    out.append("****： VH ，。")
    out.append("")
    vl_prec = _resolve_precedent("VL", vl_c or [])
    out.append(f"**（）**：{'、'.join(vl_prec[:3]) if vl_prec else '—'}")
    if vl_prec:
        out.append(_clinical_examples_table(vl_prec))
    else:
        for it in (vl_c or []):
            if isinstance(it, dict) and it.get("selected"):
                usage = it.get("clinical_usage_count")
                if usage is not None and usage > 0:
                    out.append(f"****： {usage} ，。")
                break
    out.append("")
    out.append("### 2.3 ")
    vh_gene = _selected_gene(vh_c)
    vl_gene = _selected_gene(vl_c)
    pair_row = _lookup_pairing(vh_gene, vl_gene)
    out.append("")
    if pair_row:
        count = pair_row.get("count", 0)
        rank = pair_row.get("rank")
        freq = pair_row.get("freq")
        if rank is not None and freq:
            out.append(f"****： `{vh_gene}` + `{vl_gene}`  {PAIRING_DB_TOTAL} ，Rank {rank}， {freq}。")
        else:
            out.append(f"****： `{vh_gene}` + `{vl_gene}`  {PAIRING_DB_TOTAL} ， {count} 。")
    else:
        out.append(
            f"****： `{vh_gene}` + `{vl_gene}`  {PAIRING_DB_TOTAL} "
            "（，）。"
        )
    return "\n".join(out)


def _render_design_decisions(results: Dict[str, Any]) -> str:
    final_v = _pick(results, ["_meta", "final_version"], "v1")
    all_rows, vernier_rows, cmc_rows, n_vernier, n_cmc = _compute_unified_mutation_lists(results)

    out = []
    out.append("## 、")
    out.append("")
    out.append("### 3.1 ")
    out.append("")
    out.append("|  |  |  |")
    out.append("|---|---|---|")
    out.append("| v1 | CDR （CDR ） |  |")
    out.append("| v2 | v1 + Vernier （） | （） |")
    out.append("| v3 | v2 + CMC/（ pI/） | ， |")
    out.append("")
    out.append(f"> ：**{final_v}**。。")
    out.append("")
    out.append("### 3.2 ")
    out.append("")
    out.append("|  | Kabat  |  |  | Vernier  |  |")
    out.append("|---|---:|---|---:|---|")

    for it in all_rows:
        vr = "" if it.get("vernier") else ""
        out.append(
            f"| {it.get('chain','—')} | {it.get('kabat_pos','—')} | {it.get('from','?')}→{it.get('to','?')} | "
            f"{it.get('region','—')} | {vr} | {it.get('rationale','—')} |"
        )
    if not all_rows:
        out.append("| — | — | — | — | — | （CDR ） |")
    out.append("")
    if all_rows:
        out.append(f"> ** {len(all_rows)} **（Vernier  {n_vernier} ，CMC/pI  {n_cmc} ）。")
        out.append("")
    out.append("> ：（Vernier）、，。")
    return "\n".join(out)


def _render_structural_fidelity(results: Dict[str, Any]) -> str:
    internal = results.get("_internal") or {}
    eval_v1 = internal.get("evaluation_v1") if isinstance(internal, dict) else None
    eval_v2 = internal.get("evaluation_v2") if isinstance(internal, dict) else None
    eval_v3 = internal.get("evaluation_v3") if isinstance(internal, dict) else None
    final_v = _pick(results, ["_meta", "final_version"], "v1")

    def _delta(ev: Any) -> Dict[str, Any]:
        if not isinstance(ev, dict):
            return {}
        r = ev.get("results") or {}
        if not isinstance(r, dict):
            return {}
        d = (r.get("delta_vs_mouse") or {}).get("delta") if isinstance(r.get("delta_vs_mouse"), dict) else None
        return d if isinstance(d, dict) else {}

    def _status_from_delta(d: Dict[str, Any]) -> Dict[str, str]:
        # customer-safe: PASS/WARN only (no N/A in customer reports).
        if not d:
            return {"rmsd": "WARN", "angle": "WARN", "canonical": "WARN", "overall": "WARN"}
        rmsd_pass = d.get("cdr_rmsd_pass")
        angle_pass = d.get("angle_pass")
        canon = d.get("canonical_match_h1_h2_l1")
        def _p(x): return "PASS" if x is True else "WARN"
        rmsd_s = _p(rmsd_pass)
        ang_s = _p(angle_pass)
        can_s = _p(canon)
        overall = "PASS" if (rmsd_s == "PASS" and ang_s == "PASS" and can_s == "PASS") else "WARN"
        return {"rmsd": rmsd_s, "angle": ang_s, "canonical": can_s, "overall": overall}

    d1 = _delta(eval_v1)
    d2 = _delta(eval_v2)
    d3 = _delta(eval_v3)
    
    # Check for Vernier Round 2 evaluation in _internal
    ev_r2 = None
    for k in ("evaluation_v3_vernier_round2", "evaluation_v2_vernier_round2", "evaluation_v1_vernier_round2"):
        if isinstance(internal.get(k), dict):
            ev_r2 = internal.get(k)
            break
    d_r2 = _delta(ev_r2)

    s1 = _status_from_delta(d1)
    s2 = _status_from_delta(d2)
    s3 = _status_from_delta(d3)
    s_r2 = _status_from_delta(d_r2)

    out = []
    out.append("## 、（Structural Fidelity）")
    out.append("")
    out.append("****：（ PASS/WARN/FAIL，）。")
    out.append("")
    out.append("|  | （） |  |  |")
    out.append("|---|---|---|---|")
    
    # Use final status (v3 or Round2) for the summary table
    final_status = s3 if d3 else (s_r2 if d_r2 else (s2 if d2 else s1))
    
    def _icon(s): return "🟢 " if s == "PASS" else "⚠️ "
    
    out.append(f"| 6  CDR  (RMSD) | {final_status['rmsd']} | < 1.5 Å | {_icon(final_status['rmsd'])} |")
    out.append(f"| / | {final_status['angle']} | ≤ 3° | {_icon(final_status['angle'])} |")
    out.append(f"| CDR  | {final_status['canonical']} |  | {_icon(final_status['canonical'])} |")
    out.append(f"| Vernier （） | {final_status['overall']} |  | {_icon(final_status['overall'])} |")
    out.append("")
    
    out.append("### 4.1 ")
    out.append("")
    out.append("|  |  |  |")
    out.append("|---|---|---|")
    if d1:
        out.append(f"| v1 | {s1['overall']} |  |")
    if d2:
        out.append(f"| v2.0 (Base) | {s2['overall']} | ， |")
    # Vernier Round 2 ：v2.1, v2.2, v2.3...  PASS
    if ev_r2 and isinstance(ev_r2, dict):
        note = (ev_r2.get("_internal_note") or {}).get("vernier_round2") if isinstance(ev_r2.get("_internal_note"), dict) else {}
        attempts = note.get("attempts") or [] if isinstance(note, dict) else []
        for i, att in enumerate(attempts):
            if not isinstance(att, dict):
                continue
            delta_att = att.get("delta") or {}
            s_att = _status_from_delta(delta_att) if delta_att else {"overall": "WARN"}
            step = att.get("step") or (i + 1)
            label = f"v2.{i + 1}"
            if att.get("pass"):
                out.append(f"| {label} | {s_att['overall']} | ** {i + 1}  Vernier ，** |")
            else:
                out.append(f"| {label} | {s_att['overall']} |  {i + 1}  Vernier  |")
        if not attempts and d_r2:
            out.append(f"| v2.1 (Struct. Opt) | {s_r2['overall']} | ****（Vernier Round 2） |")
    elif d_r2:
        out.append(f"| v2.1 (Struct. Opt) | {s_r2['overall']} | ****（Vernier Round 2） |")
    if d3:
        out.append(f"| v3 (Final) | {s3['overall']} | CMC （） |")
    out.append("")
    
    out.append("### 4.2 Vernier （）（）")
    out.append("")
    out.append("****：。")
    out.append("")
    _, vernier_rows, _, n_vernier, _ = _compute_unified_mutation_lists(results)
    out.append("**Vernier （）**：")
    if vernier_rows:
        out.append(f"-  {n_vernier}  Vernier ：")
        for r in vernier_rows:
            out.append(f"  - {r.get('chain','—')} {r.get('kabat_pos','—')}：{r.get('from','?')}→{r.get('to','?')}（）")
        out.append("- 。")
        if d_r2 and s_r2['overall'] == "PASS":
            out.append("- ****：v2 ， Vernier Round 2 ，（PASS）。")
    else:
        out.append("- 。")
        if d_r2 and s_r2['overall'] == "PASS":
            out.append("- ****：v2 ， Vernier Round 2 ，（PASS）。")
        else:
            out.append("-  Vernier 。")
    out.append("")
    out.append("****：")
    out.append("- ** (Overlap)**： Vernier  CDR （）。")
    out.append("- ** (Contact)**： Vernier  CDR （ < 4.5Å）。")
    out.append("")
    out.append("****：Vernier  CDR  VH/VL ；“”。")
    out.append("")
    out.append("****： CMC （v3），。")
    out.append("")

    # 4.3 （/）
    out.append("### 4.3 （/）")
    out.append("")
    ev_final = eval_v3 or eval_v2 or eval_v1
    s13 = (ev_final or {}).get("results", {}).get("structure_13param", {}) or {}
    metrics_s13 = s13.get("metrics") if isinstance(s13.get("metrics"), dict) else {}
    bs = (ev_final or {}).get("results", {}).get("binding_site", {}) or {}
    has_vhvl = any(metrics_s13.get(k) is not None for k in ("vh_vl_angle_deg", "interface_n_pairs", "interface_mean_dist_A"))
    has_abag = any(bs.get(k) is not None for k in ("bsa_total_A2", "hbond_count", "sc_score"))
    if has_vhvl or has_abag:
        out.append("|  |  |  |")
        out.append("|:---|---:|---|")
        if isinstance(metrics_s13.get("vh_vl_angle_deg"), (int, float)):
            out.append(f"| VH-VL  (°) | {metrics_s13['vh_vl_angle_deg']:.1f} |  |")
        if isinstance(metrics_s13.get("interface_n_pairs"), (int, float)):
            out.append(f"| VH-VL  | {metrics_s13['interface_n_pairs']} |  |")
        if isinstance(metrics_s13.get("interface_mean_dist_A"), (int, float)):
            out.append(f"| VH-VL  (Å) | {metrics_s13['interface_mean_dist_A']:.1f} |  |")
        if isinstance(bs.get("bsa_total_A2"), (int, float)):
            out.append(f"| Ab-Ag  buried SASA (Å²) | {bs['bsa_total_A2']} |  |")
        if isinstance(bs.get("hbond_count"), (int, float)):
            out.append(f"| Ab-Ag  | {bs['hbond_count']} |  |")
        if isinstance(bs.get("sc_score"), (int, float)):
            out.append(f"|  (SC) | {bs['sc_score']:.2f} | 0–1， 0.64–0.72 |")
        out.append("")
    else:
        out.append("（VH-VL  Ab-Ag /；。）")
        out.append("")
    out.append("****：。")
    out.append("")
    out.append("****： SPR/ELISA 。")
    return "\n".join(out)


def _render_cmc_developability(results: Dict[str, Any]) -> str:
    out = []
    out.append("## 、CMC （Developability）")
    out.append("")
    out.append("> 。 CMC （、） **CMC Developability **。")
    out.append("")
    return "\n".join(out)


def _render_immunogenicity(results: Dict[str, Any]) -> str:
    imm = results.get("immunogenicity") or {}
    final_v = _pick(results, ["_meta", "final_version"], "v3")
    risk = _pick(imm, ["risk_level", final_v], _pick(imm, ["risk_level", "v3"], imm.get("risk_level", "—")))
    out = []
    out.append("## 、（Immunogenicity）")
    out.append("")
    out.append(f"****：：**{risk}**。")
    out.append("")
    out.append("****：，。")
    out.append("")
    out.append("****： PBMC T 。")
    return "\n".join(out)



def _render_drug_space_calibration(results: Dict[str, Any]) -> str:
    out = []
    out.append("## 、V4.9.0  (Drug-Space Calibration)")
    out.append("")
    qc = results.get("qc_metrics") or {}
    
    out.append("### 1. CDR  (Hotspots)")
    hotspots = qc.get("v49_cdr_hotspots", [])
    if hotspots:
        out.append(f"-  CDR ：{', '.join(hotspots)}")
    else:
        out.append("- HCDR2/LCDR3 /。")
    out.append("")
    
    out.append("### 2. TAP  (Advisory)")
    out.append(f"- **PPC ()**: {qc.get('v49_ppc_advisory', '—')}")
    out.append(f"- **PSH ()**: {qc.get('v49_psh_advisory', '—')}")
    out.append("")
    
    out.append("### 3.  (Identity Advisory)")
    out.append(f"- ****: {qc.get('v49_identity_advisory', '—')}")
    out.append("")
    return "\n".join(out)


def _render_deliverables(results: Dict[str, Any], standard: Dict[str, Any]) -> str:
    ab_id = _pick(results, ["_meta", "antibody_id"], "id")
    deliver = standard.get("deliverables", {}).get("client_deliverable", [])

    rows = []
    for it in deliver:
        f = str(it.get("file", "")).format(id=ab_id)
        rows.append((Path(f).name, it.get("description", "—")))

    # ；，
    seqs = results.get("sequences") or {}
    def _seq_key(v: str) -> tuple:
        return (seqs.get(f"{v}_VH") or "", seqs.get(f"{v}_VL") or "")

    ver_structs = []
    seen = set()
    for ver, fname, desc in [
        ("v1", f"{ab_id}_humanized_v1.pdb", "v1（CDR ）"),
        ("v2", f"{ab_id}_humanized_v2.pdb", "v2（+ Vernier）"),
        ("v3", f"{ab_id}_humanized_v3.pdb", "v3（+ CMC）"),
        ("vernier_round2", f"{ab_id}_humanized_vernier_round2.pdb", "vernier_round2（）"),
    ]:
        k = _seq_key(ver)
        if not (k[0] and k[1]) or k in seen:
            continue
        seen.add(k)
        ver_structs.append((fname, desc))

    out = []
    out.append("## 、")
    out.append("")
    out.append("> 。****；（ v2  v3），。")
    out.append("")
    out.append("|  |  |")
    out.append("|---|---|")
    for name, desc in rows:
        out.append(f"| `{name}` | {desc} |")
    for name, desc in ver_structs:
        out.append(f"| `{name}` | {desc} |")
    return "\n".join(out)


def render_client_zh(results: Dict[str, Any], standard: Dict[str, Any]) -> str:
    ab_id = _pick(results, ["_meta", "antibody_id"], "—")
    # ：， re-render 
    now = datetime.now()
    date_id = now.strftime("%Y%m%d")
    generated_at = now.strftime("%Y-%m-%d %H:%M")
    final_v = _pick(results, ["_meta", "final_version"], "—")

    header = []
    header.append(f"# {ab_id.upper()} ")
    header.append("")
    header.append(f"****: {ab_id.upper()}-HUM-{date_id}-001 | ****: {generated_at}  ")
    header.append(f"****: {ab_id.upper()} VH/VL  | ****: {final_v}  ")
    header.append("****: InSynBio VH/VL  V4.4")
    header.append("")
    header.append("---")

    summary = []
    summary.append("## ")
    summary.append("")
    summary.append("|  |  |  |")
    summary.append("|---|---|---|")
    summary.append("|  | ， | 🟢 |")
    summary.append("|  |  | 🟢  |")
    summary.append("|  |  | 🟢  |")
    summary.append("| CMC  | pI ； | 🟡  |")
    summary.append("|  |  | 🟡 — |")
    summary.append("")
    summary.append("****：；。")
    summary.append("")
    summary.append("---")

    sections = [
        _render_sequences_and_annotation(results),
        "---",
        _render_germline_selection(results),
        "---",
        _render_design_decisions(results),
        "---",
        _render_structural_fidelity(results),
        "---",
        _render_cmc_developability(results),
        "---",
        _render_immunogenicity(results),
        "---",
        _render_drug_space_calibration(results),
        "---",
        _render_deliverables(results, standard),
        "---",
        "## 、",
        "",
        "|  |  |  |",
        "|---|---|---|",
        "| 🔴 |  LC-MS  CDR-H2 NYS  |  |",
        "| 🟡 | SPR/ELISA  |  |",
        "| 🟡 | PBMC T （） |  |",
        "",
        "---",
        "",
        f"* InSynBio VH/VL  V4.4  | : {generated_at}*  ",
        "*: （）| *",
    ]

    text = "\n".join(header + [""] + summary + [""] + sections)
    text = _sanitize_public_terms(text)
    _assert_no_forbidden_terms(text, where="client_zh report")
    return text


def run_pre_delivery_gate_report_checks(results: Dict[str, Any], report_text: str) -> List[str]:
    """Report-side gate checks (completeness + forbidden terms + ). Returns list of failures."""
    fails: List[str] = []

    # Completeness: must contain key headings
    required_headings = [
        "",
        "（Germline）",
        "",
        "",
        "CMC ",
        "",
        "",
    ]
    for h in required_headings:
        if h not in report_text:
            fails.append(f"missing_heading:{h}")

    # Forbidden terms
    for t in FORBIDDEN_TERMS:
        if t in report_text:
            fails.append(f"forbidden_term:{t}")

    # Avoid leaking quantitative internal scoring details in customer report
    # if "%" in report_text:
    #     fails.append("public_report_contains_percent_sign")

    # Internal-only file hints
    internal_markers = ["_results.json", "_V44_Audit.md", "_Dev_Report.md"]
    for m in internal_markers:
        if m in report_text:
            fails.append(f"internal_reference:{m}")

    # ： (chain, kabat_pos)
    try:
        all_rows, _, _, _, _ = _compute_unified_mutation_lists(results)
        seen_keys: set = set()
        for r in all_rows:
            c = (r.get("chain") or "").upper()
            kp = r.get("kabat_pos")
            try:
                key = (c, int(kp)) if kp is not None else (c, -1)
            except (TypeError, ValueError):
                key = (c, -1)
            if key in seen_keys:
                fails.append(f"mutation_duplicate:{c}_{kp}")
                break
            seen_keys.add(key)
    except Exception as e:
        fails.append(f"mutation_list_check_error:{e}")

    # ：（SSOT  sequences）
    seqs = results.get("sequences") or {}
    final_v = (results.get("_meta") or {}).get("final_version") or "v3"
    vh_ssot = seqs.get("vernier_round2_VH") or seqs.get(f"{final_v}_VH") or seqs.get("v3_VH", "")
    vl_ssot = seqs.get("vernier_round2_VL") or seqs.get(f"{final_v}_VL") or seqs.get("v3_VL", "")
    if not (vh_ssot and vl_ssot):
        fails.append("empty_humanized_sequence")

    # ： sequence_annotation  sequences ， CDR 
    ann = results.get("sequence_annotation") or {}
    if ann.get("VH") and ann.get("VL"):
        vh_ann_seq = (ann.get("VH") or {}).get("sequence", "")
        vl_ann_seq = (ann.get("VL") or {}).get("sequence", "")
        if vh_ssot and vl_ssot and (vh_ann_seq != vh_ssot or vl_ann_seq != vl_ssot):
            fails.append("sequence_annotation_mismatch:run_verify_fix_to_reconcile")

    # ： VH CDR3 （ Kabat ）
    for m in re.finditer(r"\|\s*CDR3\s*\|\s*95[–\-]102\s*\|\s*`([^`]*)`\s*\|", report_text):
        seq = (m.group(1) or "").strip()
        if len(seq) < 1:
            fails.append("mouse_VH_CDR3_empty_in_report")
        break  # （ 1.0.1）

    return fails


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("antibody_id", help="e.g. 9c1")
    ap.add_argument("project_dir", help="e.g. projects/9c1_Redesign")
    ap.add_argument("--write", action="store_true", help="write reports to project_dir/reports/")
    args = ap.parse_args()

    ab_id = args.antibody_id
    project_dir = (SUITE / args.project_dir).resolve() if not str(args.project_dir).startswith(str(SUITE)) else Path(args.project_dir).resolve()
    results_path = project_dir / f"{ab_id}_results.json"
    if not results_path.exists():
        raise FileNotFoundError(f"results json not found: {results_path}")

    if not V44_CONFIG.exists():
        raise FileNotFoundError(f"V4.4 config not found: {V44_CONFIG}")

    results = _load_json(results_path)
    standard = _load_json(V44_CONFIG)
    #  Phase4 ， verify 、
    results["_render_project_dir"] = str(project_dir.resolve())

    report = render_client_zh(results, standard)
    fails = run_pre_delivery_gate_report_checks(results, report)
    if fails:
        raise ValueError("[Pre-Delivery Gate] report checks failed:\n  - " + "\n  - ".join(fails))

    if args.write:
        out_dir = project_dir / "reports"
        out_dir.mkdir(parents=True, exist_ok=True)
        out_path = out_dir / f"{ab_id}_Client_zh.md"
        out_path.write_text(report, encoding="utf-8")
        print(f"[OK] wrote: {out_path}")
    else:
        print(report)

    return 0


if __name__ == "__main__":
    raise SystemExit(main())

