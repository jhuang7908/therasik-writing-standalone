"""
PD-1 Antibody Drug VH→VHH Algorithm Validation Script
=======================================================
Purpose: Extract VH sequences from 6 published PD-1 antibody PDB files,
         run them through the full VH→VHH evaluation pipeline (Stage 1, Stage 2b,
         V1.5 risk assessment), and produce a comparative analysis report.

This is an ALGORITHM VALIDATION exercise — the goal is to:
  1. Verify algorithm correctness on known clinical sequences
  2. Identify edge cases / weaknesses in the scoring logic
  3. Produce observations for potential V1.6 improvements

Run:
    conda run -n anarcii python scripts/validate_vh2vhh_pd1_panel.py
"""
from __future__ import annotations

import json
import sys
from pathlib import Path
from typing import Any, Dict, List, Optional

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

# ─────────────────────────────────────────────────────────────────────────────
# PD-1 antibody drug panel
# ─────────────────────────────────────────────────────────────────────────────
PROJ = ROOT / "projects" / "Reference_Antibodies"

PANEL: List[Dict[str, Any]] = [
    {
        "drug":    "Pembrolizumab",
        "alias":   "Keytruda",
        "company": "Merck (MSD)",
        "pdb_id":  "5B8C",
        "pdb_path": str(PROJ / "Pembrolizumab_Human_Experimental" / "5B8C.pdb"),
        "chain":   "B",   # heavy chain verified
        "source_class": "human_mab",
        "expected_vh_len": (113, 120),
    },
    {
        "drug":    "Nivolumab",
        "alias":   "Opdivo",
        "company": "BMS",
        "pdb_id":  "5WT9",
        "pdb_path": str(PROJ / "Nivolumab_Human_Experimental" / "5WT9.pdb"),
        "chain":   "H",
        "source_class": "human_mab",
        "expected_vh_len": (113, 120),
    },
    {
        "drug":    "Toripalimab",
        "alias":   "Tuoyi / Loqtorzi",
        "company": "Junshi Biosciences",
        "pdb_id":  "6JBT",
        "pdb_path": str(PROJ / "Toripalimab_Human_Experimental" / "6JBT.pdb"),
        "chain":   "H",
        "source_class": "human_mab",
        "expected_vh_len": (113, 125),
    },
    {
        "drug":    "Tislelizumab",
        "alias":   "Tevimbra",
        "company": "BeiGene",
        "pdb_id":  "7CGW",
        "pdb_path": str(ROOT.parent / "7CGW.pdb"),
        "chain":   "H",
        "source_class": "human_mab",
        "expected_vh_len": (113, 125),
    },
    {
        "drug":    "Pembrolizumab-alt",
        "alias":   "Keytruda (5JXE complex)",
        "company": "Merck (MSD)",
        "pdb_id":  "5JXE",
        "pdb_path": str(PROJ / "Pembrolizumab_Alt_Human_Experimental" / "5JXE.pdb"),
        "chain":   "D",
        "source_class": "human_mab",
        "expected_vh_len": (113, 120),
    },
    {
        "drug":    "Camrelizumab",
        "alias":   "AiRuiKa (SHR-1210)",
        "company": "Hengrui Medicine",
        "pdb_id":  "COMP-CAM",
        "pdb_path": str(PROJ / "COMPARATIVE_EVALUATION" / "Camrelizumab_DogPD1_Best.pdb"),
        "chain":   "A",
        "source_class": "human_mab",
        "expected_vh_len": (110, 125),
    },
]

AA3TO1 = {
    "ALA":"A","ARG":"R","ASN":"N","ASP":"D","CYS":"C","GLN":"Q","GLU":"E",
    "GLY":"G","HIS":"H","ILE":"I","LEU":"L","LYS":"K","MET":"M","PHE":"F",
    "PRO":"P","SER":"S","THR":"T","TRP":"W","TYR":"Y","VAL":"V",
}


# ─────────────────────────────────────────────────────────────────────────────
# Step 1: Extract VH sequence from PDB via ANARCI
# ─────────────────────────────────────────────────────────────────────────────

def _extract_seqs_from_atom(pdb_path: str) -> Dict[str, List[str]]:
    """
    Fallback: parse Cα ATOM records to build per-chain residue lists
    (used when SEQRES records are absent, e.g. AlphaFold / docking models).
    """
    atom_chains: Dict[str, Dict[int, str]] = {}  # chain → {resseq: resname}
    with open(pdb_path, "r", encoding="utf-8", errors="ignore") as fh:
        for line in fh:
            rec = line[:6].strip()
            if rec not in ("ATOM", "HETATM"):
                continue
            atom_name = line[12:16].strip()
            if atom_name != "CA":
                continue
            ch = line[21:22].strip()
            try:
                resseq = int(line[22:26].strip())
            except ValueError:
                continue
            resname = line[17:20].strip()
            if ch not in atom_chains:
                atom_chains[ch] = {}
            atom_chains[ch][resseq] = resname
    # Convert to ordered residue lists
    result: Dict[str, List[str]] = {}
    for ch, rmap in atom_chains.items():
        result[ch] = [rmap[k] for k in sorted(rmap)]
    return result


def extract_vh_from_pdb(pdb_path: str, preferred_chain: Optional[str],
                        expected_len_range: tuple) -> Dict[str, Any]:
    """
    Parse PDB SEQRES records (or fall back to ATOM Cα) to get candidate
    sequences, then run ANARCI to confirm which is the VH (H chain).
    """
    from anarcii import Anarcii

    p = Path(pdb_path)
    if not p.exists():
        return {"error": f"PDB not found: {pdb_path}"}

    # ── Try SEQRES first ──────────────────────────────────────────────────
    seqres: Dict[str, List[str]] = {}
    with p.open("r", encoding="utf-8", errors="ignore") as fh:
        for line in fh:
            if not line.startswith("SEQRES"):
                continue
            ch = line[11:12].strip()
            residues = line[19:].split()
            if ch not in seqres:
                seqres[ch] = []
            seqres[ch].extend(residues)

    # ── Fall back to ATOM Cα if no SEQRES found (e.g. docking models) ────
    if not seqres:
        seqres = _extract_seqs_from_atom(pdb_path)

    chains_to_try = (
        [preferred_chain] if preferred_chain and preferred_chain in seqres
        else list(seqres.keys())
    )

    a = Anarcii(seq_type="antibody", mode="accuracy", verbose=False)

    best: Dict[str, Any] = {}
    for ch in chains_to_try:
        raw_seq = "".join(AA3TO1.get(r, "X") for r in seqres.get(ch, []))
        if len(raw_seq) < 80:
            continue

        a.number([raw_seq])
        entry = a.to_scheme("kabat").get("Sequence 1", {})
        if entry.get("error") or entry.get("chain_type") not in ("H",):
            continue

        numbering = entry.get("numbering", [])
        vh_residues = [(pos, icode, aa) for (pos, icode), aa in numbering if aa != "-"]
        if not vh_residues:
            continue

        # VH variable region only
        vh_seq = "".join(aa for _, _, aa in vh_residues)
        vl = expected_len_range
        if not (vl[0] <= len(vh_seq) <= vl[1] + 30):
            # allow some tolerance — full-chain PDBs include constant regions
            # extract just variable region (Kabat 1-113 approx)
            vh_var = "".join(aa for (pos, _, aa) in vh_residues if pos <= 113)
            if not vh_var:
                vh_var = vh_seq[:125]
        else:
            vh_var = vh_seq

        # trim to variable region if needed
        if len(vh_var) > 130:
            vh_var = vh_var[:125]

        best = {
            "chain": ch,
            "vh_seq": vh_var,
            "full_chain_len": len(raw_seq),
            "vh_var_len": len(vh_var),
            "germline_chain": entry.get("chain_type"),
        }
        if preferred_chain and ch == preferred_chain:
            break

    if not best:
        return {"error": f"No VH chain identified in {p.name} (chains tried: {chains_to_try})"}
    return best


# ─────────────────────────────────────────────────────────────────────────────
# Step 2: Run Stage 1 + Stage 2b + V1.5 risk assessment
# ─────────────────────────────────────────────────────────────────────────────

def run_full_pipeline(drug_meta: Dict[str, Any], vh_seq: str) -> Dict[str, Any]:
    """Run Stage1 → candidate generation → Stage2b (AbEvaluator) → V1.5 risk."""
    from scripts.vhh_conversion_pipeline import run_stage1, run_stage2
    from core.humanization.engine import _vhh_mini_cmc  # noqa: PLC0415
    from api.routers.vh_to_vhh import _generate_conversion_candidates, _compute_v15_risk_assessment  # noqa: PLC0415

    source_class = drug_meta.get("source_class", "human_mab")

    # ── Stage 1 ──────────────────────────────────────────────────────────────
    s1 = run_stage1(vh_seq, source_type=source_class)
    fe = s1.get("feasibility") or {}
    cdr3_len: int = s1.get("cdr3_length") or 13
    cdr2_len: int = s1.get("cdr2_length") or 10

    # ── Candidate generation ──────────────────────────────────────────────────
    candidates = _generate_conversion_candidates(
        vh_seq=vh_seq,
        source_class=source_class,
        cdr3_len=cdr3_len,
        cdr2_len=cdr2_len,
        top_n=3,
    )

    # ── Stage 2b: AbEvaluator rank ────────────────────────────────────────────
    entries = [{"sequence_id": c["candidate_id"], "sequence": c["sequence"]} for c in candidates]
    s2_results = run_stage2(entries)
    s2_map = {r.get("sequence_id"): r for r in s2_results if isinstance(r, dict)}

    status_rank = {"PASS": 0, "WARN": 1, "FAIL": 2, "ERROR": 3}
    for cand in candidates:
        s2 = s2_map.get(cand["candidate_id"], {})
        cand["clinical_status"] = s2.get("status")
        cand["clinical_score"] = s2.get("clinical_score")
        es = s2.get("executive_summary") or {}
        cand["overall_flags"] = es.get("overall_flags") or []

    candidates.sort(key=lambda c: (
        status_rank.get(str(c.get("clinical_status") or "ERROR").upper(), 9),
        -(c.get("clinical_score") if isinstance(c.get("clinical_score"), (int, float)) else -999),
        -(c.get("template_score") if isinstance(c.get("template_score"), (int, float)) else -999),
    ))
    best = candidates[0]

    # ── mini-CMC on best ──────────────────────────────────────────────────────
    try:
        mini_cmc = _vhh_mini_cmc(best.get("sequence") or vh_seq)
    except Exception as e:
        mini_cmc = {"error": str(e)}

    # ── V1.5 risk assessment ──────────────────────────────────────────────────
    payload: Dict[str, Any] = {
        "mini_cmc": mini_cmc,
        "cmc_flags": best.get("overall_flags") or [],
        "cdr3_length": cdr3_len,
        "cdr2_length": cdr2_len,
        "converted_sequence": best.get("sequence") or vh_seq,
        "source_class": source_class,
    }
    try:
        v15 = _compute_v15_risk_assessment(payload)
    except Exception as e:
        v15 = {"error": str(e)}

    return {
        "stage1": {
            "feasibility_verdict": fe.get("verdict"),
            "feasibility_risk": fe.get("risk_level"),
            "cdr3_len": cdr3_len,
            "cdr2_len": cdr2_len,
            "notes": fe.get("notes", []),
        },
        "best_candidate": {
            "candidate_id": best.get("candidate_id"),
            "strategy": best.get("strategy"),
            "template_id": best.get("template_id"),
            "germline": best.get("germline"),
            "sequence": best.get("sequence"),
            "template_score": best.get("template_score"),
            "framework_identity": best.get("framework_identity"),
            "fr2_identity": best.get("fr2_identity"),
            "mutations_applied": best.get("mutations_applied") or [],
            "clinical_status": best.get("clinical_status"),
            "clinical_score": best.get("clinical_score"),
            "overall_flags": best.get("overall_flags") or [],
        },
        "mini_cmc": mini_cmc,
        "v15_risk": v15,
        "all_candidates": [
            {
                "candidate_id": c.get("candidate_id"),
                "strategy": c.get("strategy"),
                "template_score": c.get("template_score"),
                "clinical_status": c.get("clinical_status"),
                "clinical_score": c.get("clinical_score"),
                "mutations_applied": c.get("mutations_applied") or [],
            }
            for c in candidates
        ],
    }


# ─────────────────────────────────────────────────────────────────────────────
# Step 3: Markdown comparison table
# ─────────────────────────────────────────────────────────────────────────────

def _fmt_blockers(risk: Dict[str, Any]) -> str:
    rows = risk.get("risk_attribution") or []
    blockers = [r["risk_dimension"] for r in rows if r.get("severity") == "BLOCKER"]
    warns = [r["risk_dimension"] for r in rows if r.get("severity") == "WARN"]
    parts = []
    if blockers:
        parts.append("🚫 " + ", ".join(blockers))
    if warns:
        parts.append("⚠ " + ", ".join(warns))
    return "; ".join(parts) if parts else "✅ clean"


def generate_md_report(results: List[Dict[str, Any]]) -> str:
    lines: List[str] = []
    lines.append("# PD-1 Antibody Drug Panel — VH→VHH Algorithm Validation")
    lines.append("")
    lines.append("> **Purpose:** Validate V1.5 pipeline logic on 6 published anti-PD-1 drugs.")
    lines.append("> Each drug's VH sequence is extracted from experimental PDB structure,")
    lines.append("> run through full Stage 1 → Stage 2b (AbEvaluator) → V1.5 risk assessment.")
    lines.append("")

    # Summary table
    lines.append("## Summary Comparison Table")
    lines.append("")
    lines.append("| Drug | PDB | CDR-H3 | CDR-H2 | Stage1 Verdict | Best Strategy | Clin.Status | Clin.Score | pI | Success% | Primary Blockers/Warns |")
    lines.append("|------|-----|--------|--------|----------------|---------------|-------------|------------|----|----------|------------------------|")

    for r in results:
        meta = r["meta"]
        ex = r.get("extract") or {}
        pipe = r.get("pipeline") or {}
        s1 = pipe.get("stage1") or {}
        best = pipe.get("best_candidate") or {}
        mc = pipe.get("mini_cmc") or {}
        v15 = pipe.get("v15_risk") or {}
        err = r.get("error")

        drug = f"{meta['drug']}"
        pdb = meta["pdb_id"]
        cdr3 = s1.get("cdr3_len", "—")
        cdr2 = s1.get("cdr2_len", "—")
        verdict = s1.get("feasibility_verdict") or err or "error"
        strategy = (best.get("strategy") or "—")[:30]
        cs = best.get("clinical_status") or "—"
        score = f"{best.get('clinical_score'):.3f}" if isinstance(best.get("clinical_score"), (int, float)) else "—"
        pi = f"{mc.get('pI'):.2f}" if isinstance(mc.get("pI"), (int, float)) else "—"
        sp = f"{v15.get('success_probability', 0)*100:.0f}%" if isinstance(v15.get("success_probability"), float) else "—"
        blockers = _fmt_blockers(v15) if not err else f"ERROR: {err[:60]}"

        lines.append(f"| {drug} | {pdb} | {cdr3} | {cdr2} | {verdict} | `{strategy}` | **{cs}** | {score} | {pi} | **{sp}** | {blockers} |")

    lines.append("")

    # Per-drug detailed section
    lines.append("## Per-Drug Detailed Analysis")
    lines.append("")
    for r in results:
        meta = r["meta"]
        pipe = r.get("pipeline") or {}
        s1 = pipe.get("stage1") or {}
        best = pipe.get("best_candidate") or {}
        mc = pipe.get("mini_cmc") or {}
        v15 = pipe.get("v15_risk") or {}
        all_cands = pipe.get("all_candidates") or []

        lines.append(f"### {meta['drug']} ({meta['alias']}) — {meta['pdb_id']}")
        lines.append("")
        if r.get("error"):
            lines.append(f"> **ERROR:** {r['error']}")
            lines.append("")
            continue

        vh = (r.get("extract") or {}).get("vh_seq") or ""
        lines.append(f"- **VH length:** {len(vh)} aa")
        lines.append(f"- **CDR-H3 / CDR-H2:** {s1.get('cdr3_len')} aa / {s1.get('cdr2_len')} aa")
        lines.append(f"- **Stage 1 verdict:** `{s1.get('feasibility_verdict')}` (risk: {s1.get('feasibility_risk')})")
        for n in (s1.get("notes") or [])[:4]:
            lines.append(f"  - {n}")
        lines.append("")

        lines.append("**Best VHH candidate:**")
        lines.append(f"- Strategy: `{best.get('strategy')}`")
        lines.append(f"- Template: `{best.get('template_id') or '—'}` | Germline: `{best.get('germline') or '—'}`")
        lines.append(f"- FR identity: {best.get('framework_identity', 0)*100:.1f}% | FR2: {best.get('fr2_identity', 0)*100:.1f}%")
        lines.append(f"- Mutations applied: {len(best.get('mutations_applied',[]))} ({', '.join(best.get('mutations_applied',[])[:8])})")
        lines.append(f"- Clinical status: **{best.get('clinical_status')}** | Score: {best.get('clinical_score')}")
        if best.get("overall_flags"):
            lines.append(f"- CMC flags: {'; '.join(str(f) for f in best['overall_flags'][:6])}")
        lines.append("")

        lines.append("**mini-CMC (converted VHH):**")
        for k in ("pI", "net_charge_pH7", "GRAVY", "instability_index", "length"):
            v = mc.get(k)
            if v is not None:
                lines.append(f"- {k}: {round(v, 2) if isinstance(v, float) else v}")
        lines.append("")

        lines.append("**V1.5 Risk Assessment:**")
        sp = v15.get("success_probability")
        lines.append(f"- Success probability: **{sp*100:.0f}%** ({v15.get('confidence_band','—')})" if isinstance(sp, float) else "- Success probability: —")
        lines.append(f"- Verdict: `{v15.get('verdict_severity','—')}`")
        lines.append(f"- Primary blocker: {v15.get('primary_blocker') or 'None'}")
        lines.append(f"- Primary recommendation: Option {v15.get('primary_recommendation','—')}")
        risk_rows = v15.get("risk_attribution") or []
        if risk_rows:
            lines.append("- Risk attribution:")
            for rr in risk_rows:
                lines.append(f"  - [{rr.get('severity','?')}] **{rr.get('risk_dimension')}**: {rr.get('current_value')} (threshold: {rr.get('safety_threshold')}) ← {rr.get('attribution_source')}")
        lines.append("")

        if len(all_cands) > 1:
            lines.append("**All candidates ranked:**")
            lines.append("| Rank | ID | Strategy | Clin.Status | Clin.Score | Template Score | Mutations |")
            lines.append("|------|----|----------|-------------|------------|----------------|-----------|")
            for i, c in enumerate(all_cands, 1):
                lines.append(f"| {i} | `{(c.get('candidate_id') or '')[:30]}` | `{(c.get('strategy') or '')[:25]}` | {c.get('clinical_status')} | {c.get('clinical_score')} | {c.get('template_score')} | {len(c.get('mutations_applied',[]))} |")
            lines.append("")

        lines.append("---")
        lines.append("")

    # Algorithm observations section
    lines.append("## Algorithm Validation Observations")
    lines.append("")
    lines.append("*Auto-generated by validate_vh2vhh_pd1_panel.py — review and promote to EVOLUTION_LOG.md*")
    lines.append("")
    lines.append("| # | Observation | Severity | Affected Drug(s) |")
    lines.append("|---|-------------|----------|------------------|")
    lines.append("| 1 | *(Filled manually after reviewing results above)* | — | — |")
    lines.append("")

    return "\n".join(lines)


# ─────────────────────────────────────────────────────────────────────────────
# Main
# ─────────────────────────────────────────────────────────────────────────────

def main() -> int:
    print("=" * 70)
    print("PD-1 Antibody VH→VHH Algorithm Validation Panel")
    print("=" * 70)
    print()

    all_results: List[Dict[str, Any]] = []

    for meta in PANEL:
        drug = meta["drug"]
        print(f"[{drug}] Extracting VH from {meta['pdb_id']}...", end=" ", flush=True)

        extract = extract_vh_from_pdb(
            meta["pdb_path"],
            meta.get("chain"),
            meta.get("expected_vh_len", (113, 125)),
        )

        if extract.get("error"):
            print(f"SKIP — {extract['error']}")
            all_results.append({"meta": meta, "extract": extract, "error": extract["error"]})
            continue

        vh_seq = extract["vh_seq"]
        print(f"OK ({extract['vh_var_len']} aa, chain={extract['chain']})")

        print(f"[{drug}] Running pipeline (Stage1→Stage2b→V1.5)...", end=" ", flush=True)
        try:
            pipe = run_full_pipeline(meta, vh_seq)
            best_status = (pipe.get("best_candidate") or {}).get("clinical_status") or "?"
            sp = (pipe.get("v15_risk") or {}).get("success_probability")
            sp_str = f"{sp*100:.0f}%" if isinstance(sp, float) else "?"
            print(f"OK → {best_status}, success={sp_str}")
        except Exception as e:
            import traceback
            msg = traceback.format_exc()
            print(f"ERROR — {e}")
            pipe = None
            all_results.append({"meta": meta, "extract": extract, "pipeline": None, "error": str(e), "traceback": msg})
            continue

        all_results.append({"meta": meta, "extract": extract, "pipeline": pipe})

    # Save JSON
    out_json = ROOT / ".tmp_pd1_vh2vhh_validation.json"
    out_json.write_text(json.dumps(all_results, indent=2, ensure_ascii=False, default=str), encoding="utf-8")
    print(f"\nFull JSON saved: {out_json}")

    # Save Markdown report
    md = generate_md_report(all_results)
    out_md = ROOT / ".tmp_pd1_vh2vhh_validation.md"
    out_md.write_text(md, encoding="utf-8")
    print(f"Markdown report: {out_md}")

    # Print quick summary
    print()
    print("=" * 70)
    print("QUICK SUMMARY")
    print("=" * 70)
    print(f"{'Drug':<22} {'CDR3':>5} {'Verdict':<12} {'ClinStatus':<12} {'ClinScore':>9} {'Success%':>8} {'Blockers'}")
    print("-" * 100)
    for r in all_results:
        if r.get("error") and not r.get("pipeline"):
            print(f"{r['meta']['drug']:<22} {'—':>5} {'ERROR':<12} {'—':<12} {'—':>9} {'—':>8} {str(r.get('error',''))[:40]}")
            continue
        pipe = r.get("pipeline") or {}
        s1 = pipe.get("stage1") or {}
        best = pipe.get("best_candidate") or {}
        v15 = pipe.get("v15_risk") or {}
        sp = v15.get("success_probability")
        sp_str = f"{sp*100:.0f}%" if isinstance(sp, float) else "?"
        score = best.get("clinical_score")
        score_str = f"{score:.3f}" if isinstance(score, (int, float)) else "?"
        blockers = "; ".join(
            rr.get("risk_dimension","?")
            for rr in (v15.get("risk_attribution") or [])
            if rr.get("severity") == "BLOCKER"
        ) or "none"
        warns = "; ".join(
            rr.get("risk_dimension","?")
            for rr in (v15.get("risk_attribution") or [])
            if rr.get("severity") == "WARN"
        ) or ""
        risk_str = (f"🚫{blockers}" if blockers != "none" else "") + (f" ⚠{warns}" if warns else "")
        print(f"{r['meta']['drug']:<22} {s1.get('cdr3_len','—'):>5} {s1.get('feasibility_verdict','—'):<12} "
              f"{best.get('clinical_status','—'):<12} {score_str:>9} {sp_str:>8}  {risk_str or '✅ clean'}")

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
