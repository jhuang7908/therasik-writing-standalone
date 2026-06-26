#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Slice-3 VHH: observed SR/BM classification (from sequences) + association analysis.

Rationale:
- Slice-3 sequences are already humanized therapeutics. We therefore first infer an
  *observed* strategy label from sequence/template signals (SR vs BM; keep Native/Unknown if needed),
  then quantify which factors associate with the SR/BM split.

Inputs (expected in repo):
- data/slice3_vhh_paper_grade_master_table_plus_cdr3_features.csv
- data/thera_sabdab/features/anarcii_numbering_slice_3_vhh_design.parquet
- data/thera_sabdab/features/slice3_vhh_canonical_config.json
- data/thera_sabdab/features/slice3_vhh_north_canonical.json
- data/germlines/vhh_v1/vhh_germline_assets_clean.jsonl  (Homo templates with full CDR1/2)
- data/germlines/vicugna_pacos_ig_aa/vhh_scaffolds/vhh_scaffolds.json (alpaca scaffold consensus)
- core/data/framework_library/vh_frameworks.with_cdr12.canonical_input.yaml

Outputs:
- reports/slice3_vhh_observed_strategy_labels.csv
- reports/slice3_vhh_observed_strategy_association.md
"""

from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

import numpy as np
import pandas as pd
from scipy.stats import fisher_exact, mannwhitneyu

PROJECT_ROOT = Path(__file__).resolve().parent.parent
import sys
sys.path.append(str(PROJECT_ROOT))

MASTER_CSV = PROJECT_ROOT / "data" / "slice3_vhh_paper_grade_master_table_plus_cdr3_features.csv"
NUMBERING_PARQUET = PROJECT_ROOT / "data" / "thera_sabdab" / "features" / "anarcii_numbering_slice_3_vhh_design.parquet"
CDR_JSON = PROJECT_ROOT / "data" / "thera_sabdab" / "features" / "slice3_vhh_canonical_config.json"
NORTH_JSON = PROJECT_ROOT / "data" / "thera_sabdab" / "features" / "slice3_vhh_north_canonical.json"
GERMLINE_ASSETS_JSONL = PROJECT_ROOT / "data" / "germlines" / "vhh_v1" / "vhh_germline_assets_clean.jsonl"
ALPACA_SCAFFOLDS_JSON = PROJECT_ROOT / "data" / "germlines" / "vicugna_pacos_ig_aa" / "vhh_scaffolds" / "vhh_scaffolds.json"
ALPACA_IGHJ_FASTA = PROJECT_ROOT / "data" / "germlines" / "vicugna_pacos_ig_aa" / "IGHJ_aa.fasta"
FW_LIB_YAML = PROJECT_ROOT / "core" / "data" / "framework_library" / "vh_frameworks.with_cdr12.canonical_input.yaml"
FR4_J_YAML = PROJECT_ROOT / "core" / "data" / "framework_library" / "fr4_j_segments.yaml"

OUT_LABELS = PROJECT_ROOT / "reports" / "slice3_vhh_observed_strategy_labels.csv"
OUT_MD = PROJECT_ROOT / "reports" / "slice3_vhh_observed_strategy_association.md"

from core.numbering.imgt_anarcii import imgt_number_anarcii_indexed


FR_POS: set[int] = set(range(1, 27)) | set(range(39, 56)) | set(range(66, 105))
HALLMARK_IMGT: set[int] = {37, 44, 45, 47}
VERNIER_ANCHOR_IMGT: set[int] = {28, 29, 94}
VERNIER_TUNING_IMGT: set[int] = {49, 71, 73, 78}


def _safe_read_json(path: Path) -> Any:
    return json.loads(path.read_text(encoding="utf-8"))


def load_framework_library_positions() -> Dict[str, Dict[int, str]]:
    """
    Load framework library pos->aa maps, keyed by germline name (e.g. IGHV3-23*01).
    """
    import yaml

    if not FW_LIB_YAML.exists():
        raise FileNotFoundError(f"Missing required file: {FW_LIB_YAML}")
    data = yaml.safe_load(FW_LIB_YAML.read_text(encoding="utf-8"))
    lib: Dict[str, Dict[int, str]] = {}
    for fw in data.get("frameworks", []):
        g = fw.get("germline")
        pos = fw.get("numbering_evidence", {}).get("positions", {}) or {}
        if g:
            lib[g] = {int(k): str(v) for k, v in pos.items()}
    return lib


def load_vh_fr4_j_parts() -> List[Dict[str, str]]:
    """
    Load VH FR4/J parts (JH-derived) as the *human FR4 library* for VHH assembly.
    """
    import yaml

    if not FR4_J_YAML.exists():
        raise FileNotFoundError(f"Missing required file: {FR4_J_YAML}")
    data = yaml.safe_load(FR4_J_YAML.read_text(encoding="utf-8")) or {}
    entries = data.get("entries", []) or []
    out: List[Dict[str, str]] = []
    for e in entries:
        if str(e.get("chain")) != "VH":
            continue
        if str(e.get("type")) != "FR4_J":
            continue
        seq = str(e.get("sequence") or "").strip()
        if not seq:
            continue
        out.append({"id": str(e.get("id") or ""), "sequence": seq})
    return out


def load_fasta_records(path: Path) -> List[Dict[str, str]]:
    """
    Minimal FASTA parser (no external deps).
    Returns list of {id, header, sequence}.
    """
    if not path.exists():
        raise FileNotFoundError(f"Missing required file: {path}")
    records: List[Dict[str, str]] = []
    header: Optional[str] = None
    seq_chunks: List[str] = []
    for raw in path.read_text(encoding="utf-8").splitlines():
        line = raw.strip()
        if not line:
            continue
        if line.startswith(">"):
            if header is not None:
                seq = "".join(seq_chunks).replace(" ", "").upper()
                rid = header[1:].split()[0]
                records.append({"id": rid, "header": header[1:], "sequence": seq})
            header = line
            seq_chunks = []
        else:
            seq_chunks.append(line)
    if header is not None:
        seq = "".join(seq_chunks).replace(" ", "").upper()
        rid = header[1:].split()[0]
        records.append({"id": rid, "header": header[1:], "sequence": seq})
    return records


@dataclass(frozen=True)
class TemplateHit:
    fr_id: str
    identity_fr1: float
    identity_fr2: float
    identity_fr3: float
    identity_fr23: float
    identity_fr123: float


def _identity(a: str, b: str) -> float:
    a = (a or "").strip()
    b = (b or "").strip()
    if not a or not b:
        return float("nan")
    matches = sum(1 for x, y in zip(a, b) if x == y)
    denom = max(len(a), len(b))
    return float(matches / denom) if denom else float("nan")


def _extract_fr_parts_from_vh(vh_sequence: str) -> Tuple[str, str, str, str]:
    """
    Extract FR1/FR2/FR3/FR4 using ANARCII numbering.
    - FR1: IMGT 1-26
    - FR2: IMGT 39-55
    - FR3: IMGT 66-104
    - FR4: IMGT 118-128

    Note: FR4 is frequently conserved and some template libraries do not carry FR4;
    we still extract it from therapeutics for completeness.
    """
    numbered = imgt_number_anarcii_indexed(vh_sequence)
    idx_to_pos = {int(r["seq_idx"]): int(r["pos"]) for r in numbered["rows"]}
    pos_to_aa = {idx_to_pos[i]: vh_sequence[i] for i in idx_to_pos.keys() if i < len(vh_sequence)}

    fr1 = "".join(pos_to_aa.get(p, "") for p in range(1, 27))
    fr2 = "".join(pos_to_aa.get(p, "") for p in range(39, 56))
    fr3 = "".join(pos_to_aa.get(p, "") for p in range(66, 105))
    fr4 = "".join(pos_to_aa.get(p, "") for p in range(118, 129))
    return fr1, fr2, fr3, fr4


def best_template_hit_fr1_fr2_fr3(
    query_fr1: str, query_fr2: str, query_fr3: str, templates: List[Dict[str, Any]]
) -> Optional[TemplateHit]:
    best: Optional[TemplateHit] = None
    for t in templates:
        tid = str(t.get("template_id") or t.get("scaffold_id") or t.get("sequence_id") or "")
        fr1 = str(t.get("fr1") or "")
        fr2 = str(t.get("fr2") or "")
        fr3 = str(t.get("fr3") or "")
        i1 = _identity(query_fr1, fr1)
        i2 = _identity(query_fr2, fr2)
        i3 = _identity(query_fr3, fr3)
        # length-weighted identity across FR2+FR3
        denom = (len(query_fr2) + len(query_fr3)) if (query_fr2 or query_fr3) else 0
        if denom:
            w = (len(query_fr2) * (0.0 if np.isnan(i2) else i2) + len(query_fr3) * (0.0 if np.isnan(i3) else i3)) / denom
        else:
            w = float("nan")
        # length-weighted identity across FR1+FR2+FR3
        denom123 = (len(query_fr1) + len(query_fr2) + len(query_fr3)) if (query_fr1 or query_fr2 or query_fr3) else 0
        if denom123:
            w123 = (
                len(query_fr1) * (0.0 if np.isnan(i1) else i1)
                + len(query_fr2) * (0.0 if np.isnan(i2) else i2)
                + len(query_fr3) * (0.0 if np.isnan(i3) else i3)
            ) / denom123
        else:
            w123 = float("nan")

        hit = TemplateHit(
            fr_id=tid,
            identity_fr1=float(i1),
            identity_fr2=float(i2),
            identity_fr3=float(i3),
            identity_fr23=float(w),
            identity_fr123=float(w123),
        )
        if best is None or (hit.identity_fr23 > best.identity_fr23):
            best = hit
    return best


@dataclass(frozen=True)
class FR4Hit:
    part_id: str
    identity: float


def best_fr4_hit(query_fr4: str, parts: List[Dict[str, str]]) -> Optional[FR4Hit]:
    if not query_fr4:
        return None
    best: Optional[FR4Hit] = None
    for p in parts:
        pid = str(p.get("id") or "")
        seq = str(p.get("sequence") or "")
        ident = _identity(query_fr4, seq)
        hit = FR4Hit(part_id=pid, identity=float(ident))
        if best is None or (hit.identity > best.identity):
            best = hit
    return best


@dataclass(frozen=True)
class JHit:
    j_id: str
    identity: float
    window_seq: str
    window_start: int


def _best_substring_identity(query: str, target: str) -> Tuple[float, str, int]:
    """
    Best identity of query against any same-length window in target.
    - If target shorter than query, compares against full target (missing treated as mismatches).
    Returns (best_identity, best_window_seq, best_window_start).
    """
    query = (query or "").strip().upper()
    target = (target or "").strip().upper()
    if not query or not target:
        return float("nan"), "", -1
    qn = len(query)
    if len(target) < qn:
        matches = sum(1 for x, y in zip(query, target) if x == y)
        return float(matches / qn), target, 0
    best_ident = -1.0
    best_win = ""
    best_start = 0
    for s in range(0, len(target) - qn + 1):
        win = target[s : s + qn]
        matches = sum(1 for x, y in zip(query, win) if x == y)
        ident = matches / qn
        if ident > best_ident:
            best_ident = ident
            best_win = win
            best_start = s
    return float(best_ident), best_win, int(best_start)


def best_camelid_ighj_hit(query_fr4: str, j_records: List[Dict[str, str]]) -> Optional[JHit]:
    if not query_fr4:
        return None
    best: Optional[JHit] = None
    for r in j_records:
        jid = str(r.get("id") or "")
        jseq = str(r.get("sequence") or "")
        ident, win, start = _best_substring_identity(query_fr4, jseq)
        hit = JHit(j_id=jid, identity=float(ident), window_seq=win, window_start=int(start))
        if best is None or (hit.identity > best.identity):
            best = hit
    return best


def infer_observed_strategy(
    *,
    best_human: Optional[TemplateHit],
    best_alpaca: Optional[TemplateHit],
    vh_identity_global: float,
    margin: float = 0.01,
) -> str:
    """
    Observed strategy label (post-hoc, based on sequence/template signals).
    """
    if best_human is None and best_alpaca is None:
        return "Unknown"
    if best_human is None:
        # only alpaca available
        return "SR" if (vh_identity_global is not None and float(vh_identity_global) > 0.85) else "Native"
    if best_alpaca is None:
        # only human available
        return "BM"

    # Primary classifier: FR2+FR3 (more diagnostic than FR1 for VHH)
    dh = float(best_human.identity_fr23) - float(best_alpaca.identity_fr23)
    if dh > margin:
        return "BM"
    if dh < -margin:
        return "SR" if (vh_identity_global is not None and float(vh_identity_global) > 0.85) else "Native"
    return "Unknown"


def compute_imgt_mutation_burden_vs_germline(
    *, vh_sequence: str, human_pos_map: Dict[int, str]
) -> Dict[str, Any]:
    """
    Compare query FR positions vs best human germline framework at IMGT positions.
    """
    numbered = imgt_number_anarcii_indexed(vh_sequence)
    idx_to_pos = {int(r["seq_idx"]): int(r["pos"]) for r in numbered["rows"]}
    pos_to_aa = {idx_to_pos[i]: vh_sequence[i] for i in idx_to_pos.keys() if i < len(vh_sequence)}

    mut_positions: List[int] = []
    for pos in sorted(FR_POS):
        q = pos_to_aa.get(pos)
        h = human_pos_map.get(pos)
        if not q or not h or h == "-":
            continue
        if q != h:
            mut_positions.append(pos)

    mut_set = set(mut_positions)
    hallmark = sorted(mut_set & HALLMARK_IMGT)
    vernier_anchor = sorted(mut_set & VERNIER_ANCHOR_IMGT)
    vernier_tuning = sorted(mut_set & VERNIER_TUNING_IMGT)
    other = sorted(mut_set - (set(hallmark) | set(vernier_anchor) | set(vernier_tuning)))

    return {
        "mut_total_fr": int(len(mut_positions)),
        "mut_positions_fr": ";".join(map(str, mut_positions)),
        "mut_hallmark": int(len(hallmark)),
        "mut_hallmark_positions": ";".join(map(str, hallmark)),
        "mut_vernier_anchor": int(len(vernier_anchor)),
        "mut_vernier_tuning": int(len(vernier_tuning)),
        "mut_vernier_positions": ";".join(map(str, sorted(set(vernier_anchor) | set(vernier_tuning)))),
        "mut_other": int(len(other)),
    }


def cliffs_delta(x: np.ndarray, y: np.ndarray) -> float:
    if len(x) == 0 or len(y) == 0:
        return float("nan")
    gt = 0
    lt = 0
    for a in x:
        for b in y:
            if a > b:
                gt += 1
            elif a < b:
                lt += 1
    return (gt - lt) / (len(x) * len(y))


def mw_summary(df: pd.DataFrame, group_col: str, x_col: str, g1: str = "BM", g2: str = "SR") -> Dict[str, Any]:
    x = df.loc[df[group_col] == g1, x_col].dropna().astype(float).to_numpy()
    y = df.loc[df[group_col] == g2, x_col].dropna().astype(float).to_numpy()
    if len(x) == 0 or len(y) == 0:
        return {"p": float("nan"), "delta": float("nan"), "n1": int(len(x)), "n2": int(len(y))}
    stat = mannwhitneyu(x, y, alternative="two-sided")
    return {"p": float(stat.pvalue), "delta": float(cliffs_delta(x, y)), "n1": int(len(x)), "n2": int(len(y))}


def main() -> None:
    # Validate inputs
    missing = [
        p
        for p in [
            MASTER_CSV,
            NUMBERING_PARQUET,
            CDR_JSON,
            NORTH_JSON,
            GERMLINE_ASSETS_JSONL,
            ALPACA_SCAFFOLDS_JSON,
            ALPACA_IGHJ_FASTA,
            FW_LIB_YAML,
            FR4_J_YAML,
        ]
        if not p.exists()
    ]
    if missing:
        msg = "\n".join([f"- {p}" for p in missing])
        raise FileNotFoundError(f"Missing required input(s):\n{msg}")

    OUT_LABELS.parent.mkdir(parents=True, exist_ok=True)
    OUT_MD.parent.mkdir(parents=True, exist_ok=True)

    master = pd.read_csv(MASTER_CSV)
    num = pd.read_parquet(NUMBERING_PARQUET)[["antibody_id", "vh_sequence"]].copy()
    cdr = pd.DataFrame(_safe_read_json(CDR_JSON))
    north = pd.DataFrame(_safe_read_json(NORTH_JSON))

    # --- Human VH template library (no alpaca mutations; includes full CDR1/2 in segments) ---
    templates_human: List[Dict[str, Any]] = []
    with GERMLINE_ASSETS_JSONL.open("r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            rec = json.loads(line)
            sid = str(rec.get("sequence_id") or "")
            if not sid.endswith("|Homo"):
                continue
            seg = rec.get("segments", {}) or {}
            templates_human.append(
                {
                    "template_id": sid,
                    "fr1": seg.get("FR1", ""),
                    "fr2": seg.get("FR2", ""),
                    "fr3": seg.get("FR3", ""),
                }
            )

    # --- Alpaca VHH library (true native Vicugna pacos scaffold consensus) ---
    alpaca_scaffolds = _safe_read_json(ALPACA_SCAFFOLDS_JSON)
    templates_alpaca: List[Dict[str, Any]] = []
    for s in alpaca_scaffolds:
        cons = (s.get("consensus") or {})
        templates_alpaca.append(
            {
                "scaffold_id": s.get("scaffold_id", ""),
                "fr1": cons.get("fr1", ""),
                "fr2": cons.get("fr2", ""),
                "fr3": cons.get("fr3", ""),
            }
        )

    # --- Human FR4/J parts (2 common choices for VHH) ---
    fr4_parts_vh = load_vh_fr4_j_parts()
    # --- Camelid (Vicugna) IGHJ records (for FR4/J comparison) ---
    vicugna_ighj = load_fasta_records(ALPACA_IGHJ_FASTA)

    fw_lib = load_framework_library_positions()

    # Merge base table
    df = (
        master.merge(num, on="antibody_id", how="left")
        .merge(cdr, on="antibody_id", how="left", suffixes=("", "_cdr"))
        .merge(north, on="antibody_id", how="left", suffixes=("", "_north"))
    )

    rows: List[Dict[str, Any]] = []
    for _, r in df.iterrows():
        ab_id = str(r["antibody_id"])
        vh_seq = str(r.get("vh_sequence") or "")
        fr = str(r.get("vh_fr1_fr3") or "")
        gl = str(r.get("vh_best_germline_global") or "")
        hid = float(r.get("vh_identity_global")) if pd.notna(r.get("vh_identity_global")) else float("nan")

        # Use ANARCII to extract FR parts for matching
        fr1_q, fr2_q, fr3_q, fr4_q = _extract_fr_parts_from_vh(vh_seq) if vh_seq else ("", "", "", "")
        best_human = best_template_hit_fr1_fr2_fr3(fr1_q, fr2_q, fr3_q, templates_human)
        best_alpaca = best_template_hit_fr1_fr2_fr3(fr1_q, fr2_q, fr3_q, templates_alpaca)
        best_fr4 = best_fr4_hit(fr4_q, fr4_parts_vh)
        best_vicugna_j = best_camelid_ighj_hit(fr4_q, vicugna_ighj)

        observed = infer_observed_strategy(best_human=best_human, best_alpaca=best_alpaca, vh_identity_global=hid)

        burden = {}
        if vh_seq and gl and gl in fw_lib:
            burden = compute_imgt_mutation_burden_vs_germline(vh_sequence=vh_seq, human_pos_map=fw_lib[gl])
        else:
            burden = {
                "mut_total_fr": np.nan,
                "mut_positions_fr": "",
                "mut_hallmark": np.nan,
                "mut_hallmark_positions": "",
                "mut_vernier_anchor": np.nan,
                "mut_vernier_tuning": np.nan,
                "mut_vernier_positions": "",
                "mut_other": np.nan,
            }

        rows.append(
            {
                "antibody_id": ab_id,
                "observed_strategy": observed,
                "strategy_master": r.get("strategy"),
                "vh_identity_global": hid,
                "vh_best_germline_global": gl,
                "fr1_query": fr1_q,
                "fr2_query": fr2_q,
                "fr3_query": fr3_q,
                "fr4_query": fr4_q,
                "best_human_template_id": best_human.fr_id if best_human else "",
                "best_human_fr1_identity": best_human.identity_fr1 if best_human else np.nan,
                "best_human_fr2_identity": best_human.identity_fr2 if best_human else np.nan,
                "best_human_fr3_identity": best_human.identity_fr3 if best_human else np.nan,
                "best_human_fr23_identity": best_human.identity_fr23 if best_human else np.nan,
                "best_human_fr123_identity": best_human.identity_fr123 if best_human else np.nan,
                "best_alpaca_scaffold_id": best_alpaca.fr_id if best_alpaca else "",
                "best_alpaca_fr1_identity": best_alpaca.identity_fr1 if best_alpaca else np.nan,
                "best_alpaca_fr2_identity": best_alpaca.identity_fr2 if best_alpaca else np.nan,
                "best_alpaca_fr3_identity": best_alpaca.identity_fr3 if best_alpaca else np.nan,
                "best_alpaca_fr23_identity": best_alpaca.identity_fr23 if best_alpaca else np.nan,
                "best_alpaca_fr123_identity": best_alpaca.identity_fr123 if best_alpaca else np.nan,
                "delta_human_minus_alpaca_fr23": (best_human.identity_fr23 - best_alpaca.identity_fr23) if (best_human and best_alpaca) else np.nan,
                "delta_human_minus_alpaca_fr123": (best_human.identity_fr123 - best_alpaca.identity_fr123) if (best_human and best_alpaca) else np.nan,
                "best_human_fr4_j_id": best_fr4.part_id if best_fr4 else "",
                "best_human_fr4_j_identity": best_fr4.identity if best_fr4 else np.nan,
                "best_vicugna_ighj_id": best_vicugna_j.j_id if best_vicugna_j else "",
                "best_vicugna_ighj_identity": best_vicugna_j.identity if best_vicugna_j else np.nan,
                "best_vicugna_ighj_window_seq": best_vicugna_j.window_seq if best_vicugna_j else "",
                "best_vicugna_ighj_window_start": best_vicugna_j.window_start if best_vicugna_j else np.nan,
                "h1_north": r.get("h1_north"),
                "h2_north": r.get("h2_north"),
                "h1_len": r.get("h1_len"),
                "h2_len": r.get("h2_len"),
                "cdr1_len_imgt": r.get("cdr1_len_imgt"),
                "cdr2_len_imgt": r.get("cdr2_len_imgt"),
                "cdr3_len_check": r.get("cdr3_len_check"),
                "cdr1_cluster": r.get("cdr1_cluster"),
                "cdr2_cluster": r.get("cdr2_cluster"),
                "cdr1_score": r.get("cdr1_score"),
                "cdr2_score": r.get("cdr2_score"),
                # include key CDR3 features already computed
                "cdr3_gp_frac": r.get("cdr3_gp_frac"),
                "cdr3_net_charge_est": r.get("cdr3_net_charge_est"),
                "cdr3_hydrophobic_frac": r.get("cdr3_hydrophobic_frac"),
                "cdr3_aromatic_frac": r.get("cdr3_aromatic_frac"),
                **burden,
            }
        )

    out = pd.DataFrame(rows)
    out.to_csv(OUT_LABELS, index=False, encoding="utf-8-sig")

    # Association analysis on SR vs BM only
    df2 = out[out["observed_strategy"].isin(["SR", "BM"])].copy()
    df2["is_BM"] = (df2["observed_strategy"] == "BM").astype(int)

    # Categorical summaries
    ctab_h2 = pd.crosstab(df2["observed_strategy"], df2["h2_north"]).sort_index()
    ctab_cdr1 = pd.crosstab(df2["observed_strategy"], df2["cdr1_cluster"]).sort_index()
    ctab_cdr2 = pd.crosstab(df2["observed_strategy"], df2["cdr2_cluster"]).sort_index()
    def _winner(row) -> str:
        try:
            d = float(row["delta_human_minus_alpaca_fr23"])
        except Exception:
            return "Unknown"
        if d > 0.01:
            return "HumanVH"
        if d < -0.01:
            return "AlpacaVHH"
        return "Unknown"
    df2["fr23_template_winner"] = df2.apply(_winner, axis=1)
    ctab_template_origin = pd.crosstab(df2["observed_strategy"], df2["fr23_template_winner"]).sort_index()

    # Fisher exact on H2 (only if both classes exist)
    fisher_h2 = {"ok": False}
    if set(df2["h2_north"].dropna().unique()) >= {"H2-9-1", "H2-10-1"}:
        a = int(((df2["observed_strategy"] == "BM") & (df2["h2_north"] == "H2-9-1")).sum())
        b = int(((df2["observed_strategy"] == "BM") & (df2["h2_north"] == "H2-10-1")).sum())
        c = int(((df2["observed_strategy"] == "SR") & (df2["h2_north"] == "H2-9-1")).sum())
        d = int(((df2["observed_strategy"] == "SR") & (df2["h2_north"] == "H2-10-1")).sum())
        table = np.array([[a, b], [c, d]])
        orr, p = fisher_exact(table, alternative="two-sided")
        fisher_h2 = {"ok": True, "table": table.tolist(), "odds_ratio": float(orr), "p": float(p)}

    # Numeric tests (BM vs SR)
    numeric_cols = [
        "vh_identity_global",
        "delta_human_minus_alpaca_fr123",
        "best_human_fr23_identity",
        "best_alpaca_fr23_identity",
        "delta_human_minus_alpaca_fr23",
        "best_human_fr4_j_identity",
        "best_vicugna_ighj_identity",
        "mut_total_fr",
        "mut_hallmark",
        "mut_vernier_anchor",
        "mut_vernier_tuning",
        "mut_other",
        "cdr3_len_check",
        "cdr3_gp_frac",
        "cdr3_net_charge_est",
        "cdr3_hydrophobic_frac",
        "cdr3_aromatic_frac",
        "cdr1_score",
        "cdr2_score",
    ]
    mw_rows = []
    for col in numeric_cols:
        s = mw_summary(df2, "observed_strategy", col, g1="BM", g2="SR")
        mw_rows.append({"feature": col, **s})
    mw_df = pd.DataFrame(mw_rows).sort_values(["p", "feature"], ascending=[True, True])

    # Write report
    with OUT_MD.open("w", encoding="utf-8") as f:
        f.write("# Slice-3 VHH: Observed SR/BM classification + association analysis (sequence-based)\n\n")
        f.write("## Outputs\n")
        f.write(f"- Labels: `{OUT_LABELS}`\n")
        f.write(f"- This report: `{OUT_MD}`\n\n")

        f.write("## Observed strategy counts (all 19)\n\n")
        f.write(out["observed_strategy"].value_counts(dropna=False).to_markdown() + "\n\n")

        f.write("## FR4/J comparison (therapeutic FR4 vs human JH4/JH6 vs vicugna IGHJ)\n\n")
        if "best_human_fr4_j_id" in out.columns:
            f.write("### Best human FR4/J part (from `fr4_j_segments.yaml`)\n\n")
            f.write(out["best_human_fr4_j_id"].replace({np.nan: ""}).value_counts(dropna=False).to_markdown() + "\n\n")
        if "best_vicugna_ighj_id" in out.columns:
            f.write("### Best vicugna IGHJ (from `data/germlines/vicugna_pacos_ig_aa/IGHJ_aa.fasta`)\n\n")
            f.write(out["best_vicugna_ighj_id"].replace({np.nan: ""}).value_counts(dropna=False).to_markdown() + "\n\n")
            f.write("Summary of `best_vicugna_ighj_identity` (all 19):\n\n")
            f.write(out["best_vicugna_ighj_identity"].describe().to_frame("value").to_markdown() + "\n\n")

        f.write("## Cross-check vs existing master `strategy`\n\n")
        f.write(pd.crosstab(out["strategy_master"], out["observed_strategy"]).to_markdown() + "\n\n")

        f.write("## Association analysis subset\n")
        f.write("- Included labels: SR/BM only\n")
        f.write(f"- N={len(df2)} (SR={int((df2['observed_strategy']=='SR').sum())}, BM={int((df2['observed_strategy']=='BM').sum())})\n\n")

        f.write("## Template factor (best hit origin)\n\n")
        f.write(ctab_template_origin.to_markdown() + "\n\n")

        f.write("## North proxy factor (H2)\n\n")
        f.write(ctab_h2.to_markdown() + "\n\n")
        if fisher_h2.get("ok"):
            f.write("Fisher exact (2×2; rows=BM/SR, cols=H2-9-1/H2-10-1):\n\n")
            f.write(pd.DataFrame(fisher_h2["table"], index=["BM", "SR"], columns=["H2-9-1", "H2-10-1"]).to_markdown() + "\n\n")
            f.write(f"- odds_ratio={fisher_h2['odds_ratio']:.3g}, p={fisher_h2['p']:.3g}\n\n")

        f.write("## CDR conformation proxies (CDR1/CDR2 cluster IDs)\n\n")
        f.write("### CDR1 clusters\n\n")
        f.write(ctab_cdr1.to_markdown() + "\n\n")
        f.write("### CDR2 clusters\n\n")
        f.write(ctab_cdr2.to_markdown() + "\n\n")

        f.write("## Numeric feature association (BM vs SR)\n\n")
        f.write("Mann–Whitney U p-values + Cliff’s delta (positive delta => BM tends higher):\n\n")
        f.write(mw_df.to_markdown(index=False) + "\n\n")

        f.write("## Notes / limitations\n")
        f.write("- This is **sequence-based** and uses ANARCII IMGT numbering for mutation-burden attribution.\n")
        f.write("- North–Dunbrack labels here are **proxy labels** (rule/length-based in this repo), not structure-derived canonical classes.\n")
        f.write("- N=19 is small; treat p-values as exploratory.\n")

    print(f"Wrote: {OUT_LABELS}")
    print(f"Wrote: {OUT_MD}")


if __name__ == "__main__":
    main()

