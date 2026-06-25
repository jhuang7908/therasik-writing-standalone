#!/usr/bin/env python3
"""Generate Tanezumab caninization final report (V3c / V4b) with clinical-dog differentiation."""
from __future__ import annotations

import argparse
import json
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

from anarci import anarci

suite_root = Path(__file__).resolve().parent
sys.path.insert(0, str(suite_root))

from core.humanization.deepfr_ctx_pet import validate_conserved_cys
from core.humanization.kabat_utils import sorted_keys

# ── Reference sequences ─────────────────────────────────────────────────────
TANEZUMAB_VH = (
    "QVQLQESGPGLVRPSQTLSLTCTVSGFSLIGYDLNWVRQPPGRGLEWIGIIWGDGTTDYNSAVKSRVTMLKDTSKNQFSLRLSSVTAADTAVYYCARGGYWYATSYYFDYWGQGTLVTVSS"
)
TANEZUMAB_VL = (
    "DIQMTQSPSSLSASVGDRVTITCRASQSISNNLNWYQQKPGKAPKLLIYYTSRFHSGVPSRFSGSGSGTDFTFTISSLQPEDIATYYCQQEHTLPYTFGQGTKLEIK"
)

# Tier-1 clinical canine references (in-repo verified FASTA)
CLINICAL_DOG = {
    "Bedinvetmab": {
        "vh": "EVQLVESGGDLVKPGGSLRLSCVASGFTFSSHGMHWVRQSPGKGLQWVAVINSGGSSTYYTDAVKGRFTISRDNAKNTVYLQMNSLRAEDTAMYYCAKESVGGWEQLVGPHFDYWGQGTLVIVSS",
        "vl": "QSVLTQPTSVSGSLGQRVTISCSGSTNNIGILGASWYQLFPGKAPKLLVYGNGNRPSGVPDRFSGADSGDSVTLTITGLQAEDEADYYCQSFDTTLGAHVFGGGTHLTVL",
        "lc": "lambda",
        "target": "NGF (canine pain / Librela)",
        "status": "Approved",
    },
    "Lokivetmab": {
        "vh": "EVQLVESGGDLVKPGGSLRLSCVASGFTFSNYGMSWVRQAPGKGLQWVATISYGGSYTYYPDNIKGRFTISRDNAKNTLYLQMNSLRAEDTAMYYCVRGYGYDTMDYWGQGTLVTVSS",
        "vl": "EIVMTQSPASLSLSQEEKVTITCKASQSVSFAGTGLMHWYQQKPGQAPKLLIYRASNLEAGVPSRFSGSGSGTDFSFTISSLEPEDVAVYYCQQSREYPWTFGQGTKLEIK",
        "lc": "kappa",
        "target": "IL-31 (atopic dermatitis / Cytopoint)",
        "status": "Approved",
    },
    "Ranevetmab": {
        "vh": "EVQLVESGGGLVQPGGSLRLSCVASGFSLTNNNVNWVRQAPGKGLEWVGGVWAGGATDYNSALKSRFTISRDNAKNTVFLQMHSLRSEDTAVYYCARDGGYSSSTLYAMDAWGQGTSVTVSS",
        "vl": "DIVMTQSPASLSLSQGETVTITCRASEDIYNALAWYQQKPGQAPKLLIYNTDTLHTGVPSRFSGSGSGTDFSLTISSLEPEDVAVYYCQHYFHYPRTFGQGTKVELK",
        "lc": "kappa",
        "target": "NGF (veterinary NGF antagonist)",
        "status": "Clinical / reference",
    },
}

V3B_VH = "EVQLVESGGDLVKPGGSLRLSCVASGFSLIGYDLNWVRQAPGKGLQWVAIIWGDGTTDYNSAVKSRVTISKDSAKNTFYLQLQSLRAEETAVYYCARGGYWYATSYYFDYWGQGTSVTVSS"
V3B_VL = "EIVLTQSPASLSLSQEEKVTITCRASQSISNNLNWYQQKPGQAPKLLIYYTSRFHSGVPSRFSGSGSGTDFSFTISSLEPEDVAVYYCQQEHTLPYTFGQGTKVELK"
V4_VH = "EVQLVESGGDLVKPAGSLRLSCVASGFSLIGYDLNWVRQAPEKGLQLVAIIWGDGTTDYNSAVKSRFTISKDFAKNTVYLQMRAEDTAMYYCAKGGYWYATSYYFDYWGQGTSVTVSS"
V4_VL = "QSVLTQPTSVSGSLGQRVTISCRASQSISNNLNWYQQLPGKAPKLLVYYTSRFHSGVPDRFSGSNSGNSATLTITGLQAEDEADYYCQQEHTLPYTFGGGTHLTVL"

HC_SIG = "MGWSCIILFLVATATGVHS"
LC_SIG = "METDTLLLWVLLLWVPGSTG"
DOG_IGGB_CONST = (
    "ASTTAPSVFPLAPSCGSTSGSTVALACLVSGYFPEPVTVSWNSGSLTSGVHTFPSVLQSSGLYSLSSMVTVPSSRWPSETFTCNVAHPASKTKVDKPVPKRENGRVPRPPDCPKCPAPEMLGGPSVFIFPPKPKDTLLIARTPEVTCVVVDLDPEDPEVQISWFVDGKQMQTAKTQPREEQFNGTYRVVSVLPIGHQDWLKGKQFTCKVNNKALPSPIERTISKARGQAHQPSVYVLPPSREELSKNTVSLTCLIKDFFPPDIDVEWQSNGQQEPESKYRTTPPQLDEDGSYFLYSKLSVDKSRWQRGDTFICAVMHEALHNHYTQKSLSHSPGK"
)
DOG_KAPPA_CONST = "RNDAQPAVYLFQPSPDQLHTGSASVVCLLNSFYPKDINVKWKVDGVIQDTGIQESVTEQDKDSTYSLSSTLTMSSTEYLSHELYSCEITHKSLPSTLIKSFQRSECQRVD"
DOG_LAMBDA_CONST = "GQPKSSPLVTLFPPSSEELGANKATLVCLISDFYPSGLKVAWKADGSTIIQGVETTKPSKQSNNKYTASSYLSLTPDKWKSHSSFSCLVTHQGSTVEKKVAPAECS"

DOG_OPT = {
    "A": "GCC", "C": "TGC", "D": "GAC", "E": "GAG", "F": "TTC", "G": "GGC", "H": "CAC", "I": "ATC",
    "K": "AAG", "L": "CTG", "M": "ATG", "N": "AAC", "P": "CCC", "Q": "CAG", "R": "CGC", "S": "TCC",
    "T": "ACC", "V": "GTC", "W": "TGG", "Y": "TAC", "*": "TGA",
}


def optimize_cdna(protein: str) -> str:
    return "".join(DOG_OPT.get(aa, "NNN") for aa in protein)


def get_kabat_dict(seq: str) -> Optional[Dict[Tuple[int, str], str]]:
    results = anarci([("seq", seq)], scheme="kabat")
    if not results[0] or not results[0][0]:
        return None
    numbering = results[0][0][0][0]
    return {(pos, ins.strip()): aa for (pos, ins), aa in numbering}


def get_segments(seq: str, chain: str) -> Tuple[Optional[Dict[str, str]], Optional[Dict]]:
    kd = get_kabat_dict(seq)
    if not kd:
        return None, None
    if chain == "VH":
        r_map = {
            "FR1": (1, 25), "CDR1": (26, 35), "FR2": (36, 49), "CDR2": (50, 65),
            "FR3": (66, 94), "CDR3": (95, 102), "FR4": (103, 113),
        }
    else:
        r_map = {
            "FR1": (1, 23), "CDR1": (24, 34), "FR2": (35, 49), "CDR2": (50, 56),
            "FR3": (57, 88), "CDR3": (89, 97), "FR4": (98, 107),
        }
    regions = {name: "".join(kd[k] for k in sorted_keys(kd) if lo <= k[0] <= hi) for name, (lo, hi) in r_map.items()}
    return regions, kd


def is_in_cdr(pos: int, chain: str) -> bool:
    if chain == "VH":
        return (26 <= pos <= 35) or (50 <= pos <= 65) or (95 <= pos <= 102)
    return (24 <= pos <= 34) or (50 <= pos <= 56) or (89 <= pos <= 97)


def region_similarity(kd1: Dict, kd2: Dict, chain: str, region: str) -> float:
    matches = total = 0
    for k in sorted(set(kd1.keys()) | set(kd2.keys())):
        pos = k[0]
        in_cdr = is_in_cdr(pos, chain)
        if region == "CDR" and not in_cdr:
            continue
        if region == "FR" and in_cdr:
            continue
        if chain == "VH" and pos > 94 and region == "FR":
            continue
        if chain == "VL" and pos > 88 and region == "FR":
            continue
        total += 1
        if kd1.get(k) == kd2.get(k):
            matches += 1
    return (matches / total * 100.0) if total else 0.0


def fv_identity(kd_vh1, kd_vh2, kd_vl1, kd_vl2) -> float:
    m = t = 0
    for kd, chain in [(kd_vh1, "VH"), (kd_vl1, "VL")]:
        kd_ref = kd_vh2 if chain == "VH" else kd_vl2
        for k in sorted(set(kd.keys()) | set(kd_ref.keys())):
            t += 1
            if kd.get(k) == kd_ref.get(k):
                m += 1
    return (m / t * 100.0) if t else 0.0


def kabat_diffs(kd1: Dict, kd2: Dict, chain: str, region: str, max_show: int = 24) -> List[Dict[str, str]]:
    out: List[Dict[str, str]] = []
    for k in sorted_keys({**{k: kd1.get(k) for k in kd1}, **{k: kd2.get(k) for k in kd2}}):
        pos, ins = k
        in_cdr = is_in_cdr(pos, chain)
        if region == "CDR" and not in_cdr:
            continue
        if region == "FR" and in_cdr:
            continue
        a1, a2 = kd1.get(k, "-"), kd2.get(k, "-")
        if a1 != a2:
            label = f"{pos}{ins}" if ins else str(pos)
            out.append({"pos": label, "variant": a1, "reference": a2})
        if len(out) >= max_show:
            break
    return out


def load_design(path: Path) -> Dict[str, Any]:
    with open(path, encoding="utf-8") as f:
        return json.load(f)


def pipeline_summary(pipe: Dict[str, Any]) -> str:
    ctx = pipe.get("ctx_voting", {})
    guard = pipe.get("pet_native_guard", {})
    n_ctx = len(ctx.get("changes", []))
    n_rb = guard.get("n_rollbacks", 0)
    rb_detail = ""
    for rb in guard.get("rollbacks", [])[:3]:
        rb_detail += f" {rb.get('pos')}:{rb.get('optimized_aa')}→{rb.get('graft_aa')}({rb.get('reason')});"
    return f"9-mer subs={n_ctx}, Guard rollbacks={n_rb}{(' —' + rb_detail) if rb_detail else ''}"


def build_report(out_path: Path) -> None:
    v3c = load_design(suite_root / "v3c_design_results.json")
    v4b = load_design(suite_root / "v4b_design_results.json")
    v3c_vh, v3c_vl = v3c["vh"], v3c["vl"]
    v4b_vh, v4b_vl = v4b["vh"], v4b["vl"]

    for name, vh, vl in [("V3c", v3c_vh, v3c_vl), ("V4b", v4b_vh, v4b_vl)]:
        for chain, seq in [("VH", vh), ("VL", vl)]:
            errs = validate_conserved_cys(seq, chain)
            if errs:
                raise RuntimeError(f"{name} {chain} Cys gate: {errs}")

    variants = {
        "Tanezumab (human donor)": (TANEZUMAB_VH, TANEZUMAB_VL, "human"),
        "V3b": (V3B_VH, V3B_VL, "kappa"),
        "V3c": (v3c_vh, v3c_vl, "kappa"),
        "V4": (V4_VH, V4_VL, "lambda"),
        "V4b": (v4b_vh, v4b_vl, "lambda"),
    }
    for name, ref in CLINICAL_DOG.items():
        variants[name] = (ref["vh"], ref["vl"], ref["lc"])

    parsed: Dict[str, Any] = {}
    for name, (vh, vl, lc) in variants.items():
        vh_seg, vh_kd = get_segments(vh, "VH")
        vl_seg, vl_kd = get_segments(vl, "VL")
        parsed[name] = {"vh": vh, "vl": vl, "lc": lc, "vh_seg": vh_seg, "vl_seg": vl_seg, "vh_kd": vh_kd, "vl_kd": vl_kd}

    sim_matrix: Dict[str, Dict[str, Dict[str, float]]] = {}
    candidates = ["V3c", "V4b", "V3b", "V4", "Tanezumab (human donor)"]
    clinical_names = list(CLINICAL_DOG.keys())
    for cand in candidates:
        sim_matrix[cand] = {}
        ck_vh, ck_vl = parsed[cand]["vh_kd"], parsed[cand]["vl_kd"]
        for ref in clinical_names:
            rk_vh, rk_vl = parsed[ref]["vh_kd"], parsed[ref]["vl_kd"]
            sim_matrix[cand][ref] = {
                "vh_fr": region_similarity(ck_vh, rk_vh, "VH", "FR"),
                "vh_cdr": region_similarity(ck_vh, rk_vh, "VH", "CDR"),
                "vl_fr": region_similarity(ck_vl, rk_vl, "VL", "FR"),
                "vl_cdr": region_similarity(ck_vl, rk_vl, "VL", "CDR"),
                "fv": fv_identity(ck_vh, rk_vh, ck_vl, rk_vl),
            }

    bedin = parsed["Bedinvetmab"]
    diffs = {
        "V3c": {
            "vh_fr": kabat_diffs(parsed["V3c"]["vh_kd"], bedin["vh_kd"], "VH", "FR"),
            "vh_cdr": kabat_diffs(parsed["V3c"]["vh_kd"], bedin["vh_kd"], "VH", "CDR"),
            "vl_fr": kabat_diffs(parsed["V3c"]["vl_kd"], bedin["vl_kd"], "VL", "FR"),
            "vl_cdr": kabat_diffs(parsed["V3c"]["vl_kd"], bedin["vl_kd"], "VL", "CDR"),
        },
        "V4b": {
            "vh_fr": kabat_diffs(parsed["V4b"]["vh_kd"], bedin["vh_kd"], "VH", "FR"),
            "vh_cdr": kabat_diffs(parsed["V4b"]["vh_kd"], bedin["vh_kd"], "VH", "CDR"),
            "vl_fr": kabat_diffs(parsed["V4b"]["vl_kd"], bedin["vl_kd"], "VL", "FR"),
            "vl_cdr": kabat_diffs(parsed["V4b"]["vl_kd"], bedin["vl_kd"], "VL", "CDR"),
        },
    }

    deliverables = {}
    for name in ["V3c", "V4b"]:
        lc = parsed[name]["lc"]
        cl = DOG_KAPPA_CONST if lc == "kappa" else DOG_LAMBDA_CONST
        hc = HC_SIG + parsed[name]["vh"] + DOG_IGGB_CONST
        lc_full = LC_SIG + parsed[name]["vl"] + cl
        deliverables[name] = {
            "hc_protein": hc,
            "lc_protein": lc_full,
            "hc_cdna": optimize_cdna(hc),
            "lc_cdna": optimize_cdna(lc_full),
        }

    ts = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M UTC")
    proto = v3c.get("protocol_version", "2.8.0")

    def sim_row(cand: str, ref: str) -> str:
        s = sim_matrix[cand][ref]
        fv_cls = "sim-low" if s["fv"] < 55 else ("sim-mid" if s["fv"] < 70 else "sim-high")
        return (
            f"<tr><td><strong>{cand}</strong></td><td>{ref}</td>"
            f"<td>{s['vh_fr']:.1f}%</td><td>{s['vh_cdr']:.1f}%</td>"
            f"<td>{s['vl_fr']:.1f}%</td><td>{s['vl_cdr']:.1f}%</td>"
            f"<td class='{fv_cls}'>{s['fv']:.1f}%</td></tr>"
        )

    def diff_table(title: str, rows: List[Dict]) -> str:
        if not rows:
            return f"<p><em>{title}: no differences in shown window (identical or aligned).</em></p>"
        html = f"<h4>{title}</h4><table><tr><th>Kabat</th><th>Variant</th><th>Bedinvetmab</th></tr>"
        for r in rows:
            html += f"<tr><td>{r['pos']}</td><td class='cdr'>{r['variant']}</td><td>{r['reference']}</td></tr>"
        html += "</table>"
        return html

    html = f"""<!DOCTYPE html>
<html lang="zh-CN">
<head>
<meta charset="UTF-8">
<meta name="robots" content="noindex,nofollow">
<title>Tanezumab Caninization — Sequence Report v{proto} | InSynBio</title>
<style>
body{{font-family:'Segoe UI',Arial,sans-serif;background:#f8fafc;color:#1e293b;font-size:13px;line-height:1.55;padding:20px;}}
.wrap{{max-width:1280px;margin:0 auto;background:#fff;padding:40px;border-radius:12px;box-shadow:0 4px 20px rgba(0,0,0,0.08);}}
.hdr{{background:linear-gradient(135deg,#1e3a5f,#2563eb);color:#fff;padding:28px;border-radius:12px;margin-bottom:28px;}}
h1{{font-size:24px;margin:0;}}
h2{{font-size:17px;color:#1e3a5f;border-left:5px solid #2563eb;padding-left:12px;margin:32px 0 16px;}}
h3{{font-size:14px;color:#334155;margin:18px 0 8px;}}
.meta{{background:#f1f5f9;border-radius:8px;padding:16px;font-size:12px;color:#475569;}}
table{{width:100%;border-collapse:collapse;margin:12px 0 24px;}}
th{{background:#f8fafc;text-align:left;padding:10px;border-bottom:2px solid #e2e8f0;font-size:12px;}}
td{{padding:10px;border-bottom:1px solid #f1f5f9;font-size:12px;}}
.seq-box{{font-family:Consolas,monospace;font-size:10.5px;background:#f8fafc;border:1px solid #cbd5e1;border-radius:6px;padding:12px;word-break:break-all;white-space:pre-wrap;line-height:1.45;}}
.cdr{{color:#2563eb;font-weight:600;}}
.sim-low{{color:#15803d;font-weight:700;}}
.sim-mid{{color:#b45309;font-weight:600;}}
.sim-high{{color:#b91c1c;font-weight:700;}}
.card{{border:1px solid #e2e8f0;border-radius:10px;padding:18px;margin:16px 0;}}
.v3c{{border-left:5px solid #2563eb;background:#eff6ff;}}
.v4b{{border-left:5px solid #16a34a;background:#f0fdf4;}}
.badge{{display:inline-block;padding:2px 8px;border-radius:10px;font-size:10px;font-weight:700;margin-right:6px;}}
.pass{{background:#dcfce7;color:#166534;}}
.warn{{background:#fef3c7;color:#92400e;}}
.fail{{background:#fee2e2;color:#991b1b;}}
.note{{color:#64748b;font-size:12px;}}
</style>
</head>
<body>
<div class="wrap">
<div class="hdr">
  <h1>Tanezumab 犬源化 — 序列与临床差异化报告</h1>
  <p style="opacity:0.92;margin:8px 0 0;">DeepFR-CTX-Pet v{proto} · Pet-native Guard · Structure-guided · Generated {ts}</p>
</div>

<div class="meta">
  <strong>§0 Metadata</strong><br>
  Protocol Version: <strong>{proto}</strong> · Algorithm: DeepFR-CTX-Pet · Species: Canis lupus familiaris<br>
  Structure PDB: Dog NGF complex (Boltz model_0) · P4: Pet-native Guard (dog_9mer_v1, no human OAS)<br>
  Report Format Version: 1.1 · Analysis: AbEngineCore developability + cmc_advisor
</div>

<h2>§1 Executive Summary</h2>
<table>
<tr><th>Candidate</th><th>Scaffold</th><th>CMC</th><th>pI</th><th>vs Bedinvetmab Fv</th><th>Primary FTO read</th></tr>
<tr>
  <td><strong>V3c</strong></td><td>IGHV3-9 / IGKV3-18 (Kappa)</td>
  <td><span class="badge fail">{v3c['cmc']['status']}</span></td><td>{v3c['cmc']['pI']}</td>
  <td class="sim-low">{sim_matrix['V3c']['Bedinvetmab']['fv']:.1f}%</td>
  <td>Maximum differentiation from Librela benchmark; distinct CDR-H3 from Bedinvetmab</td>
</tr>
<tr>
  <td><strong>V4b</strong></td><td>IGHV3-19 / IGLV1-141 (Lambda)</td>
  <td><span class="badge warn">{v4b['cmc']['status']}</span></td><td>{v4b['cmc']['pI']}</td>
  <td class="sim-mid">{sim_matrix['V4b']['Bedinvetmab']['fv']:.1f}%</td>
  <td>Same lambda isotype as Bedinvetmab; higher FR overlap — CDRs carry Tanezumab epitope</td>
</tr>
</table>
<p class="note">Clinical reference panel: Bedinvetmab (NGF, approved), Lokivetmab (IL-31, kappa benchmark), Ranevetmab (NGF). Similarity = Kabat FR/CDR; lower Fv identity vs Bedinvetmab supports FTO differentiation for NGF program.</p>

<h2>§2 Pipeline Audit (v2.8.0)</h2>
<table>
<tr><th>Chain</th><th>V3c</th><th>V4b</th></tr>
<tr><td>VH</td><td>{pipeline_summary(v3c['vh_pipeline'])}</td><td>{pipeline_summary(v4b['vh_pipeline'])}</td></tr>
<tr><td>VL</td><td>{pipeline_summary(v3c['vl_pipeline'])}</td><td>{pipeline_summary(v4b['vl_pipeline'])}</td></tr>
</table>
<p class="note">V3c VL: S60D retained (pet 9-mer + Pet-native Guard, 0 rollbacks). V4b VL: K66G rolled back (pro_gly hard veto).</p>

<h2>§3 Differentiation Matrix — vs Clinical Canine Antibodies</h2>
<p class="note">Green Fv &lt;55% = high differentiation; amber 55–70%; red &gt;70% = high overlap with clinical reference.</p>
<table>
<tr><th>Candidate</th><th>Clinical Reference</th><th>VH FR</th><th>VH CDR</th><th>VL FR</th><th>VL CDR</th><th>Fv Identity</th></tr>
"""
    for cand in ["V3c", "V4b"]:
        for ref in clinical_names:
            html += sim_row(cand, ref)

    html += """
</table>

<h2>§4 Kabat Differences vs Bedinvetmab (NGF competitor)</h2>
<div class="card v3c">
<h3>V3c vs Bedinvetmab</h3>
"""
    html += diff_table("VH FR differences (first 24)", diffs["V3c"]["vh_fr"])
    html += diff_table("VH CDR differences", diffs["V3c"]["vh_cdr"])
    html += diff_table("VL FR differences (first 24)", diffs["V3c"]["vl_fr"])
    html += diff_table("VL CDR differences", diffs["V3c"]["vl_cdr"])
    html += f"""
<p><strong>V3c VH:</strong> <span class="seq-box">{v3c_vh}</span></p>
<p><strong>V3c VL:</strong> <span class="seq-box">{v3c_vl}</span></p>
</div>
<div class="card v4b">
<h3>V4b vs Bedinvetmab</h3>
"""
    html += diff_table("VH FR differences (first 24)", diffs["V4b"]["vh_fr"])
    html += diff_table("VH CDR differences", diffs["V4b"]["vh_cdr"])
    html += diff_table("VL FR differences (first 24)", diffs["V4b"]["vl_fr"])
    html += diff_table("VL CDR differences", diffs["V4b"]["vl_cdr"])
    html += f"""
<p><strong>V4b VH:</strong> <span class="seq-box">{v4b_vh}</span></p>
<p><strong>V4b VL:</strong> <span class="seq-box">{v4b_vl}</span></p>
</div>

<h2>§5 Regional Alignment (Kabat segments)</h2>
<h3>Heavy Chain</h3>
<table>
<tr><th>Molecule</th><th>FR1</th><th>CDR1</th><th>FR2</th><th>CDR2</th><th>FR3</th><th>CDR3</th><th>FR4</th></tr>
"""
    for name in ["Bedinvetmab", "V3c", "V4b", "Lokivetmab", "Ranevetmab"]:
        r = parsed[name]["vh_seg"]
        html += f"<tr><td>{name}</td><td>{r['FR1']}</td><td class='cdr'>{r['CDR1']}</td><td>{r['FR2']}</td><td class='cdr'>{r['CDR2']}</td><td>{r['FR3']}</td><td class='cdr'>{r['CDR3']}</td><td>{r['FR4']}</td></tr>"

    html += """
</table>
<h3>Light Chain</h3>
<table>
<tr><th>Molecule</th><th>FR1</th><th>CDR1</th><th>FR2</th><th>CDR2</th><th>FR3</th><th>CDR3</th><th>FR4</th></tr>
"""
    for name in ["Bedinvetmab", "V3c", "V4b", "Lokivetmab", "Ranevetmab"]:
        r = parsed[name]["vl_seg"]
        html += f"<tr><td>{name}</td><td>{r['FR1']}</td><td class='cdr'>{r['CDR1']}</td><td>{r['FR2']}</td><td class='cdr'>{r['CDR2']}</td><td>{r['FR3']}</td><td class='cdr'>{r['CDR3']}</td><td>{r['FR4']}</td></tr>"

    html += f"""
</table>

<h2>§6 Full Construct Deliverables</h2>
<div class="card v3c">
<h3>V3c — HC / LC (signal + Fv + dog constant)</h3>
<p><strong>HC protein</strong></p><div class="seq-box">{deliverables['V3c']['hc_protein']}</div>
<p><strong>LC protein</strong></p><div class="seq-box">{deliverables['V3c']['lc_protein']}</div>
<p><strong>HC cDNA (canine codon)</strong></p><div class="seq-box">{deliverables['V3c']['hc_cdna']}</div>
<p><strong>LC cDNA</strong></p><div class="seq-box">{deliverables['V3c']['lc_cdna']}</div>
</div>
<div class="card v4b">
<h3>V4b — HC / LC</h3>
<p><strong>HC protein</strong></p><div class="seq-box">{deliverables['V4b']['hc_protein']}</div>
<p><strong>LC protein</strong></p><div class="seq-box">{deliverables['V4b']['lc_protein']}</div>
<p><strong>HC cDNA</strong></p><div class="seq-box">{deliverables['V4b']['hc_cdna']}</div>
<p><strong>LC cDNA</strong></p><div class="seq-box">{deliverables['V4b']['lc_cdna']}</div>
</div>

<h2>§7 Clinical Reference Sequences (source: in-repo Tier-1 canine FASTA)</h2>
<table>
<tr><th>Name</th><th>Target</th><th>Status</th><th>LC type</th><th>VH length</th><th>VL length</th></tr>
"""
    for name, meta in CLINICAL_DOG.items():
        html += (
            f"<tr><td>{name}</td><td>{meta['target']}</td><td>{meta['status']}</td>"
            f"<td>{meta['lc']}</td><td>{len(meta['vh'])}</td><td>{len(meta['vl'])}</td></tr>"
        )

    html += """
</table>

<p style="text-align:center;color:#94a3b8;font-size:11px;margin-top:36px;">
InSynBio Antibody Engineer Suite · Internal Engineering Workspace · Confidential
</p>
</div>
</body>
</html>
"""

    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(html, encoding="utf-8")

    summary = {
        "generated_at": ts,
        "protocol_version": proto,
        "similarity_matrix": sim_matrix,
        "v3c": {"vh": v3c_vh, "vl": v3c_vl, "cmc": v3c["cmc"]},
        "v4b": {"vh": v4b_vh, "vl": v4b_vl, "cmc": v4b["cmc"]},
    }
    json_path = out_path.with_suffix(".json")
    json_path.write_text(json.dumps(summary, indent=2), encoding="utf-8")
    print(f"HTML → {out_path}")
    print(f"JSON → {json_path}")
    print(f"V3c vs Bedinvetmab Fv: {sim_matrix['V3c']['Bedinvetmab']['fv']:.1f}%")
    print(f"V4b vs Bedinvetmab Fv: {sim_matrix['V4b']['Bedinvetmab']['fv']:.1f}%")


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument(
        "--out",
        type=Path,
        default=suite_root / "projects/Tanezumab_Caninization/Tanezumab_Sequence_Report_v2_8.html",
    )
    args = ap.parse_args()
    build_report(args.out)


if __name__ == "__main__":
    main()
