"""
run_anarcii_numbering_70.py
============================
ABARCII IMGT numbering of the 70 confirmed human/humanized therapeutic antibodies
from the ADA database project.

Pipeline
--------
1. Build sequence input from TheraSAbDab (HeavySequence, LightSequence, bispec arms).
   Ozoralizumab: add arm3 **VH3** = full ALB8 (117 aa, PDB 8Z8V chain B, no His6); see OZORALIZUMAB_ALB8_VHH_AA.
2. Load ABARCII once; batch-number all chains in one pass (avoids repeated model loads).
3. Extract per-chain IMGT annotation:
     - chain_type, ABARCII score
     - CDR1/2/3 sequences and lengths  (IMGT CDR definition)
     - FR1/2/3/4 sequences             (IMGT FR definition)
     - raw IMGT position map           (compact string for audit)
4. Germline assignment (human only)
     - Compare FR1+FR2+FR3 to **OGRDB** published human IG V alleles (AIRR JSON → DNA→AA),
       cached under data/germlines/ogrdb_human_*.json.
     - OGRDB mainly covers human / primate / mouse IG & TR; it is **not** a substitute for
       multi-species IMGT. AbEngineCore species scans use IMGT_V-QUEST_reference_directory +
       aa_translated (see core/resources/germline_resources.py).
     - Cross-check vs. 842_antibody_germline_assignment.csv (where available).
5. Output
     - data/thera_sabdab/out/anarcii_numbering_70.csv   (per-chain rows)
     - data/thera_sabdab/out/anarcii_numbering_70_summary.txt
6. Post-step (germline columns in CSV)
     - python scripts/fill_anarcii_ogrdb_germlines.py
       Refreshes germline_anarcii / germline_anarcii_pct from cached OGRDB JSON (network if cache missing).

IMGT CDR / FR position boundaries (on IMGT 1-indexed positions, no insertions):
  VH  FR1: 1-26   CDR1: 27-38   FR2: 39-55   CDR2: 56-65   FR3: 66-104  CDR3: 105-117  FR4: 118-128
  VL  FR1: 1-26   CDR1: 27-38   FR2: 39-55   CDR2: 56-65   FR3: 66-104  CDR3: 105-117  FR4: 118-127

Performance note (CPU)
------------------------------
  ABARCII speed mode, batch_size=32: ~430s for 3 sequences (auto-regressive decoder).
  For all ~130 chains this run will take approximately 20-40 minutes.
  Run with:  python -u scripts/run_anarcii_numbering_70.py
  Progress is written to data/thera_sabdab/out/anarcii_progress.log in real-time.

Author: InSynBio AI Research Suite
"""
from __future__ import annotations

import json
import re
import sys
import time
import warnings
from pathlib import Path
from typing import Any

import pandas as pd
import requests

warnings.filterwarnings("ignore")

# Force unbuffered output so progress is visible when piped
sys.stdout.reconfigure(line_buffering=True)
sys.stderr.reconfigure(line_buffering=True)

# ── Paths ──────────────────────────────────────────────────────────────────────
SUITE = Path(__file__).resolve().parent.parent
THERA_XLSX     = SUITE / "data" / "thera_sabdab" / "TheraSAbDab_SeqStruc_OnlineDownload.xlsx"
CONFIRMED70    = SUITE / "data" / "thera_sabdab" / "out" / "confirmed70_human_humanized_germline_ada.csv"
GERMLINE_842   = SUITE / "data" / "humanization_assay" / "842_antibody_germline_assignment.csv"
GERMLINE_CACHE = SUITE / "data" / "germlines"
OUT_DIR        = SUITE / "data" / "thera_sabdab" / "out"
OUT_CSV        = OUT_DIR / "anarcii_numbering_70.csv"
OUT_TXT        = OUT_DIR / "anarcii_numbering_70_summary.txt"
LOG_FILE       = OUT_DIR / "anarcii_progress.log"

GERMLINE_CACHE.mkdir(parents=True, exist_ok=True)
OUT_DIR.mkdir(parents=True, exist_ok=True)

# ── IMGT position definitions ──────────────────────────────────────────────────
# IMGT positions as integers (base 1); insertions (letter suffix) excluded here.
IMGT_FR1   = range(1,   27)    # 1-26
IMGT_CDR1  = range(27,  39)    # 27-38
IMGT_FR2   = range(39,  56)    # 39-55
IMGT_CDR2  = range(56,  66)    # 56-65
IMGT_FR3   = range(66,  105)   # 66-104
IMGT_CDR3  = range(105, 118)   # 105-117
IMGT_FR4   = range(118, 129)   # 118-128  (VH) / 127 (VL) – use same range, trim naturally

# Full ALB8 anti-HSA VHH (PDB 8Z8V chain B SEQRES; His6 tag excluded). Sync with
# scripts/build_confirmed70_sequences_full.py OZORALIZUMAB_ALB8_VHH_AA.
OZORALIZUMAB_ALB8_VHH_AA = (
    "EVQLVESGGGLVQPGNSLRLSCAASGFTFSSFGMSWVRQAPGKGLEWVSSISGSGSDTLYADSVKGRFTISRDNAKTT"
    "LYLQMNSLRPEDTAVYYCTIGGSLSRSSQGTLVTVSSTS"
)


def _norm(s: object) -> str:
    if pd.isna(s): return ""
    return re.sub(r"[-\s]", "", str(s).lower().strip())


def _is_real_seq(s: object) -> bool:
    s = str(s).strip()
    return len(s) > 10 and s.lower() not in ("nan", "na", "none", "-", "n/a")


# ── Germline reference download / cache ───────────────────────────────────────
# OGRDB API (swagger: /api/germline/set/{species}/{set_name}/{release_version}/{format})
# Old paths .../Human/IGH/published/ungapped return 404; set names are IGH_VDJ, IGKappa_VJ, IGLambda_VJ.
# `ungapped` returns DNA FASTA; we use `airr` JSON and translate coding_sequence → AA for FR identity.
OGRDB_BASE = "https://ogrdb.airr-community.org/api/germline/set/Human"

CHAIN_OGRDB = {
    "H": f"{OGRDB_BASE}/IGH_VDJ/published/airr",
    "K": f"{OGRDB_BASE}/IGKappa_VJ/published/airr",
    "L": f"{OGRDB_BASE}/IGLambda_VJ/published/airr",
}
CHAIN_LABEL_PREFIX = {"H": "IGHV", "K": "IGKV", "L": "IGLV"}
CHAIN_CACHE_FILE = {
    "H": GERMLINE_CACHE / "ogrdb_human_IGHV_v2.json",
    "K": GERMLINE_CACHE / "ogrdb_human_IGKV_v2.json",
    "L": GERMLINE_CACHE / "ogrdb_human_IGLV_v2.json",
}

# Standard genetic code (uppercase DNA → one-letter AA)
_GENETIC_CODE: dict[str, str] = {}
for triplet, aa in [
    ("TTT", "F"), ("TTC", "F"), ("TTA", "L"), ("TTG", "L"),
    ("TCT", "S"), ("TCC", "S"), ("TCA", "S"), ("TCG", "S"),
    ("TAT", "Y"), ("TAC", "Y"), ("TAA", "*"), ("TAG", "*"),
    ("TGT", "C"), ("TGC", "C"), ("TGA", "*"), ("TGG", "W"),
    ("CTT", "L"), ("CTC", "L"), ("CTA", "L"), ("CTG", "L"),
    ("CCT", "P"), ("CCC", "P"), ("CCA", "P"), ("CCG", "P"),
    ("CAT", "H"), ("CAC", "H"), ("CAA", "Q"), ("CAG", "Q"),
    ("CGT", "R"), ("CGC", "R"), ("CGA", "R"), ("CGG", "R"),
    ("ATT", "I"), ("ATC", "I"), ("ATA", "I"), ("ATG", "M"),
    ("ACT", "T"), ("ACC", "T"), ("ACA", "T"), ("ACG", "T"),
    ("AAT", "N"), ("AAC", "N"), ("AAA", "K"), ("AAG", "K"),
    ("AGT", "S"), ("AGC", "S"), ("AGA", "R"), ("AGG", "R"),
    ("GTT", "V"), ("GTC", "V"), ("GTA", "V"), ("GTG", "V"),
    ("GCT", "A"), ("GCC", "A"), ("GCA", "A"), ("GCG", "A"),
    ("GAT", "D"), ("GAC", "D"), ("GAA", "E"), ("GAG", "E"),
    ("GGT", "G"), ("GGC", "G"), ("GGA", "G"), ("GGG", "G"),
]:
    _GENETIC_CODE[triplet] = aa


def _dna_to_aa(dna: str) -> str:
    dna = "".join(b for b in dna.upper() if b in "ACGT")
    out: list[str] = []
    for i in range(0, len(dna) - 2, 3):
        out.append(_GENETIC_CODE.get(dna[i : i + 3], "X"))
    return "".join(out)


def _fetch_ogrdb(chain: str) -> dict[str, str]:
    """Download OGRDB AIRR JSON; translate V-gene coding_sequence to AA.
    Returns {allele_label: aa_sequence} e.g. IGHV3-23*01.
    """
    cache_path = CHAIN_CACHE_FILE[chain]
    if cache_path.exists():
        return json.loads(cache_path.read_text())

    url = CHAIN_OGRDB[chain]
    prefix = CHAIN_LABEL_PREFIX[chain]
    print(f"  Downloading OGRDB {chain} ({prefix}) from {url} …")
    try:
        r = requests.get(url, timeout=120)
        r.raise_for_status()
        data = r.json()
    except Exception as exc:
        print(f"  OGRDB download failed for {chain}: {exc} — skipping germline assignment")
        return {}

    genes: dict[str, str] = {}
    germline_sets = data.get("GermlineSet") or []
    for gs in germline_sets:
        for ad in gs.get("allele_descriptions") or []:
            if not isinstance(ad, dict):
                continue
            label = str(ad.get("label") or "").strip()
            if not label.startswith(prefix):
                continue
            coding = ad.get("coding_sequence") or ""
            if not coding:
                continue
            aa = _dna_to_aa(str(coding))
            if aa:
                genes[label] = aa

    print(f"  → {len(genes)} {chain} V-alleles cached (from AIRR + DNA→AA).")
    cache_path.write_text(json.dumps(genes, indent=2))
    return genes


def _load_germline_ref() -> dict[str, dict[str, str]]:
    """Returns {"H": {gene: seq}, "K": {gene: seq}, "L": {gene: seq}}"""
    refs: dict[str, dict[str, str]] = {}
    for chain in ("H", "K", "L"):
        refs[chain] = _fetch_ogrdb(chain)
    return refs


# ── ABARCII extraction helpers ─────────────────────────────────────────────────

def _extract_range(numbering: list, pos_range: range) -> str:
    """Extract residues at IMGT integer positions (no insertions) in order."""
    pos_set = set(pos_range)
    return "".join(
        aa for (pos, ins), aa in numbering
        if pos in pos_set and ins == " " and aa != "-"
    )


def _extract_range_with_ins(numbering: list, pos_range: range) -> str:
    """Extract residues including insertion letters (for CDR3 etc.)."""
    lo, hi = pos_range.start, pos_range.stop
    return "".join(
        aa for (pos, ins), aa in numbering
        if lo <= pos < hi and aa != "-"
    )


def _parse_chain(result: dict) -> dict[str, Any]:
    """Pull per-chain metrics from one ABARCII result dict."""
    numbering = result.get("numbering") or []
    chain_type = result.get("chain_type", "?")
    score = result.get("score", 0.0)
    is_heavy = chain_type == "H"

    fr1  = _extract_range(numbering, IMGT_FR1)
    cdr1 = _extract_range_with_ins(numbering, IMGT_CDR1)
    fr2  = _extract_range(numbering, IMGT_FR2)
    cdr2 = _extract_range_with_ins(numbering, IMGT_CDR2)
    fr3  = _extract_range(numbering, IMGT_FR3)
    cdr3 = _extract_range_with_ins(numbering, IMGT_CDR3)
    fr4  = _extract_range(numbering, IMGT_FR4)

    fr_concat = fr1 + fr2 + fr3

    # Compact position map for audit (pos:aa)
    pos_map = ";".join(
        f"{pos}{ins.strip()}:{aa}"
        for (pos, ins), aa in numbering
        if aa != "-"
    )

    return {
        "chain_type": chain_type,
        "anarcii_score": round(score, 3),
        "numbered": bool(numbering),
        "fr1": fr1, "fr1_len": len(fr1),
        "cdr1": cdr1, "cdr1_len": len(cdr1),
        "fr2": fr2, "fr2_len": len(fr2),
        "cdr2": cdr2, "cdr2_len": len(cdr2),
        "fr3": fr3, "fr3_len": len(fr3),
        "cdr3": cdr3, "cdr3_len": len(cdr3),
        "fr4": fr4, "fr4_len": len(fr4),
        "fr_concat": fr_concat,
        "imgt_pos_map": pos_map[:500],   # truncate for CSV readability
    }


# ── Germline assignment ────────────────────────────────────────────────────────

def _best_germline(fr_concat: str, ref_genes: dict[str, str]) -> tuple[str, float]:
    """Find best-matching IMGT V-gene by FR1+FR2+FR3 sequence identity."""
    if not fr_concat or not ref_genes:
        return "unknown", 0.0

    best_gene, best_id = "unknown", 0.0
    for gene, gseq in ref_genes.items():
        # Compare overlapping length
        n = min(len(fr_concat), len(gseq))
        if n == 0:
            continue
        matches = sum(1 for a, b in zip(fr_concat, gseq) if a == b)
        pct = round(100.0 * matches / n, 2)
        if pct > best_id:
            best_id = pct
            best_gene = gene
    return best_gene, best_id


def _gene_family(allele: str) -> str:
    """IGHV3-23*01 → IGHV3-23"""
    return allele.split("*")[0] if "*" in allele else allele


def _materialize_anarcii_row(
    key: str,
    result: dict,
    chain_meta: dict[str, dict],
    germline_ref: dict[str, dict[str, str]],
    map842: dict[str, dict],
) -> dict[str, Any]:
    """Build one CSV row from ABARCII `result` (same schema as main())."""
    meta = chain_meta.get(key, {})
    drug = meta.get("drug", key)
    arm = meta.get("arm", "")
    c_label = meta.get("chain_label", "")

    parsed = _parse_chain(result)
    ct = parsed["chain_type"]

    ref_chain = "H" if ct == "H" else ("K" if ct == "K" else "L")
    ref_genes = germline_ref.get(ref_chain, {})
    anarcii_gl, anarcii_gl_pct = _best_germline(parsed["fr_concat"], ref_genes)

    drug_key = _norm(drug)
    m842 = map842.get(drug_key, {})
    cols842 = list(m842.keys())
    vh_col842 = next((c for c in cols842 if "vh" in c.lower() and "germline" in c.lower()), None)
    vl_col842 = next((c for c in cols842 if "vl" in c.lower() and "germline" in c.lower()), None)
    if vh_col842 is None:
        vh_col842 = next((c for c in cols842 if "heavy" in c.lower() or "ighv" in c.lower()), None)
    if vl_col842 is None:
        vl_col842 = next((c for c in cols842 if "light" in c.lower() or "igkv" in c.lower() or "iglv" in c.lower()), None)

    csv842_germline = ""
    if ct == "H" and vh_col842:
        csv842_germline = str(m842.get(vh_col842, ""))
    elif ct in ("K", "L") and vl_col842:
        csv842_germline = str(m842.get(vl_col842, ""))

    return {
        "drug": drug,
        "arm": arm,
        "chain_label": c_label,
        "anarcii_key": key,
        "chain_type": ct,
        "anarcii_score": parsed["anarcii_score"],
        "numbered_ok": parsed["numbered"],
        "fr1": parsed["fr1"],
        "fr1_len": parsed["fr1_len"],
        "cdr1": parsed["cdr1"],
        "cdr1_len": parsed["cdr1_len"],
        "fr2": parsed["fr2"],
        "fr2_len": parsed["fr2_len"],
        "cdr2": parsed["cdr2"],
        "cdr2_len": parsed["cdr2_len"],
        "fr3": parsed["fr3"],
        "fr3_len": parsed["fr3_len"],
        "cdr3": parsed["cdr3"],
        "cdr3_len": parsed["cdr3_len"],
        "fr4": parsed["fr4"],
        "fr4_len": parsed["fr4_len"],
        "germline_anarcii": anarcii_gl,
        "germline_anarcii_pct": anarcii_gl_pct,
        "germline_family": _gene_family(anarcii_gl),
        "germline_842csv": csv842_germline,
        "germline_agree": (
            anarcii_gl.split("*")[0].upper() == csv842_germline.split("*")[0].upper()
            if csv842_germline and anarcii_gl != "unknown"
            else "N/A"
        ),
        "imgt_pos_map": parsed["imgt_pos_map"],
    }


# ── Load 842 germline CSV for cross-check ─────────────────────────────────────

def _load_842_map() -> dict[str, dict]:
    """Returns {norm_name: {vh_germline, vl_germline, ...}}"""
    if not GERMLINE_842.exists():
        return {}
    df = pd.read_csv(GERMLINE_842, low_memory=False)
    result: dict[str, dict] = {}
    name_col = next((c for c in df.columns if "drug" in c.lower() or "antibody" in c.lower() or "inn" in c.lower()), df.columns[0])
    for _, row in df.iterrows():
        key = _norm(row[name_col])
        if key:
            result[key] = {c: row[c] for c in df.columns}
    return result


# ── Main ───────────────────────────────────────────────────────────────────────

def _log(msg: str, log_fh=None) -> None:
    ts = time.strftime("%H:%M:%S")
    line = f"[{ts}] {msg}"
    print(line)
    if log_fh:
        log_fh.write(line + "\n")
        log_fh.flush()


def main():
    LOG_FILE.parent.mkdir(parents=True, exist_ok=True)
    log_fh = LOG_FILE.open("w", encoding="utf-8")
    t_start = time.time()

    _log("=" * 70, log_fh)
    _log("ABARCII IMGT numbering — 70 confirmed human/humanized antibodies", log_fh)
    _log(f"mode=speed  batch_size=32  cpu=True", log_fh)
    _log("=" * 70, log_fh)

    # ── Load 70-drug list and TheraSAbDab ──────────────────────────────────────
    _log("Loading TheraSAbDab …", log_fh)
    df70   = pd.read_csv(CONFIRMED70)
    names70 = {_norm(n): n for n in df70["antibody_name"]}

    df_thera = pd.read_excel(THERA_XLSX)
    df_thera["_key"] = df_thera["Therapeutic"].apply(_norm)
    df_thera = df_thera[df_thera["_key"].isin(names70)].copy()
    _log(f"  Loaded {len(df_thera)} rows from TheraSAbDab", log_fh)

    # ── Build sequence input dict ──────────────────────────────────────────────
    # Key convention: "<DrugName>|VH", "<DrugName>|VL", "<DrugName>|VH2", "<DrugName>|VL2"
    seq_dict: dict[str, str] = {}
    chain_meta: dict[str, dict] = {}   # key → {drug, arm, chain_label}

    for _, row in df_thera.iterrows():
        drug = str(row["Therapeutic"]).strip()
        pairs = [
            (f"{drug}|VH",  row.get("HeavySequence", ""),   "VH",  "arm1"),
            (f"{drug}|VL",  row.get("LightSequence", ""),   "VL",  "arm1"),
            (f"{drug}|VH2", row.get("HeavySequence(ifbispec)", ""), "VH2", "arm2"),
            (f"{drug}|VL2", row.get("LightSequence(ifbispec)", ""), "VL2", "arm2"),
        ]
        for key, seq, label, arm in pairs:
            if _is_real_seq(seq):
                seq_dict[key] = str(seq).strip()
                chain_meta[key] = {"drug": drug, "arm": arm, "chain_label": label}

    # Ozoralizumab: Thera gives two VHH columns; add full ALB8 (117 aa) from PDB 8Z8V as arm3 / VH3.
    for display_name in df70["antibody_name"].astype(str):
        if _norm(display_name) == "ozoralizumab":
            k = f"{display_name}|VH3"
            seq_dict[k] = OZORALIZUMAB_ALB8_VHH_AA
            chain_meta[k] = {"drug": display_name, "arm": "arm3", "chain_label": "VH3"}
            break

    _log(f"Total chains to number: {len(seq_dict)}", log_fh)
    _log("  Estimated runtime on CPU (mode=speed, batch=32): ~25-40 min", log_fh)

    # ── Load ABARCII and run numbering ─────────────────────────────────────────
    _log("\nLoading ABARCII (mode=speed, batch_size=32) …", log_fh)
    from anarcii import Anarcii
    t_load = time.time()
    model = Anarcii(seq_type="antibody", mode="speed", cpu=True, batch_size=32)
    _log(f"  Model ready in {time.time()-t_load:.1f}s", log_fh)

    _log(f"Running ABARCII.number() on {len(seq_dict)} chains …", log_fh)
    _log("  (autoregressive inference — no per-chain progress until done)", log_fh)
    t_num = time.time()
    numbered = model.number(seq_dict)
    elapsed_num = time.time() - t_num
    _log(f"  Numbering done in {elapsed_num:.1f}s ({elapsed_num/len(seq_dict):.1f}s/chain)."
         f"  {len(numbered)} chains returned.", log_fh)

    # ── Load germline references ───────────────────────────────────────────────
    _log("\nLoading OGRDB (AIRR) human IG V reference …", log_fh)
    germline_ref = _load_germline_ref()
    total_ref = sum(len(v) for v in germline_ref.values())
    _log(f"  VH: {len(germline_ref.get('H', {}))}  VK: {len(germline_ref.get('K', {}))}  VL: {len(germline_ref.get('L', {}))}"
         f"  (total {total_ref} reference genes)", log_fh)

    # ── Load 842 cross-check ───────────────────────────────────────────────────
    map842 = _load_842_map()
    _log(f"  842-assignment map: {len(map842)} entries", log_fh)

    # ── Parse results ──────────────────────────────────────────────────────────
    _log("\nParsing and assigning germlines …", log_fh)
    rows: list[dict] = []

    for key, result in numbered.items():
        rows.append(_materialize_anarcii_row(key, result, chain_meta, germline_ref, map842))

    # ── Save CSV ───────────────────────────────────────────────────────────────
    df_out = pd.DataFrame(rows)
    df_out.to_csv(OUT_CSV, index=False)
    _log(f"\nSaved {len(df_out)} chain rows → {OUT_CSV.relative_to(SUITE)}", log_fh)

    # ── Summary report ────────────────────────────────────────────────────────
    _write_summary(df_out, germline_ref)

    total_elapsed = time.time() - t_start
    _log(f"\nSummary report → {OUT_TXT.relative_to(SUITE)}", log_fh)
    _log(f"Total wall time: {total_elapsed/60:.1f} minutes", log_fh)
    _log("Done.", log_fh)
    log_fh.close()


def _write_summary(df: pd.DataFrame, germline_ref: dict) -> None:
    lines: list[str] = []
    lines.append("=" * 72)
    lines.append("ABARCII IMGT Numbering — 70 Human/Humanized Therapeutic Antibodies")
    lines.append("=" * 72)

    total_chains = len(df)
    ok_chains    = df["numbered_ok"].sum()
    lines.append(f"\nTotal chains numbered : {total_chains}")
    lines.append(f"Successfully numbered : {ok_chains}")
    lines.append(f"Failed (no numbering) : {total_chains - ok_chains}")

    lines.append("\n── Chain type distribution ──────────────────────────────────────────")
    ct_counts = df["chain_type"].value_counts()
    for ct, n in ct_counts.items():
        lines.append(f"  {ct:4s}: {n}")

    lines.append("\n── Germline reference coverage ──────────────────────────────────────")
    for c, d in germline_ref.items():
        lines.append(f"  Chain {c}: {len(d)} IMGT V-genes loaded")

    lines.append("\n── Per-drug IMGT annotation summary ─────────────────────────────────")
    header = f"{'Drug':30s}  {'Arm':5s}  {'Ch':3s}  {'Score':7s}  {'FR1':4s} {'CDR1':5s} {'FR2':4s} {'CDR2':5s} {'FR3':4s} {'CDR3':5s}  {'Germline (ABARCII)':22s}  {'ID%':6s}  {'842-CSV germline':22s}  {'Agree'}"
    lines.append(header)
    lines.append("-" * len(header))
    for _, row in df.iterrows():
        agree_str = str(row["germline_agree"])
        lines.append(
            f"{row['drug']:30s}  {row['arm']:5s}  {row['chain_type']:3s}  "
            f"{row['anarcii_score']:7.3f}  "
            f"{row['fr1_len']:4d} {row['cdr1_len']:5d} {row['fr2_len']:4d} "
            f"{row['cdr2_len']:5d} {row['fr3_len']:4d} {row['cdr3_len']:5d}  "
            f"{row['germline_anarcii']:22s}  {row['germline_anarcii_pct']:6.2f}  "
            f"{row['germline_842csv']:22s}  {agree_str}"
        )

    # Agreement stats
    agree_rows = df[df["germline_agree"] != "N/A"]
    if len(agree_rows):
        n_agree = (agree_rows["germline_agree"] == True).sum()  # noqa: E712
        lines.append(f"\n── 842-CSV vs ABARCII germline agreement ───────────────────────────")
        lines.append(f"  Chains with 842-CSV reference : {len(agree_rows)}")
        lines.append(f"  Agree (family level)          : {n_agree} / {len(agree_rows)} ({100*n_agree/len(agree_rows):.1f}%)")
        disagree = agree_rows[agree_rows["germline_agree"] == False]  # noqa: E712
        if len(disagree):
            lines.append(f"  Discrepancies:")
            for _, row in disagree.iterrows():
                lines.append(f"    {row['drug']:30s} {row['chain_label']:4s}  ABARCII={row['germline_anarcii']:22s}  842-CSV={row['germline_842csv']}")

    # CDR3 length distribution
    h_df  = df[df["chain_type"] == "H"]
    lk_df = df[df["chain_type"].isin(["K", "L"])]
    lines.append("\n── CDR3 length distribution ─────────────────────────────────────────")
    if len(h_df):
        h_cdr3 = h_df["cdr3_len"]
        lines.append(f"  VH CDR3:  min={h_cdr3.min()}  max={h_cdr3.max()}  median={h_cdr3.median():.1f}  mean={h_cdr3.mean():.1f}")
    if len(lk_df):
        lk_cdr3 = lk_df["cdr3_len"]
        lines.append(f"  VL CDR3:  min={lk_cdr3.min()}  max={lk_cdr3.max()}  median={lk_cdr3.median():.1f}  mean={lk_cdr3.mean():.1f}")

    # Bispecifics note
    bispec_drugs = df[df["arm"] == "arm2"]["drug"].unique()
    if len(bispec_drugs):
        lines.append("\n── Bispecific antibodies (arm2 sequences numbered) ──────────────────")
        for d in bispec_drugs:
            arm2_rows = df[(df["drug"] == d) & (df["arm"] == "arm2")]
            chains = ", ".join(arm2_rows["chain_label"].tolist())
            lines.append(f"  {d}:  arms = {chains}")

    arm3_drugs = df[df["arm"] == "arm3"]["drug"].unique()
    if len(arm3_drugs):
        lines.append("\n── Third heavy-domain rows (arm3, e.g. Ozoralizumab ALB8 / PDB 8Z8V) ─")
        for d in arm3_drugs:
            arm3_rows = df[(df["drug"] == d) & (df["arm"] == "arm3")]
            chains = ", ".join(arm3_rows["chain_label"].tolist())
            lines.append(f"  {d}:  chains = {chains}")

    lines.append("\n" + "=" * 72)
    lines.append("Germline assignment method: FR1+FR2+FR3 identity vs OGRDB published human V alleles (AIRR)")
    lines.append("Cross-check: 842_antibody_germline_assignment.csv (by INN match)")
    lines.append("=" * 72)

    OUT_TXT.write_text("\n".join(lines), encoding="utf-8")


if __name__ == "__main__":
    main()
