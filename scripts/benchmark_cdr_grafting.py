"""
CDR Grafting dog petization + 5-variant benchmark
===================================================
Method: transplant donor VHH CDRs into best-matching dog IGHV germline FR,
        preserve VHH-specific hallmarks (Kabat 37, 44, 45, 47) from donor.

Outputs appended to the existing merged_benchmark folder so all 5 variants
(donor / llamanade / surface / merged / cdr_graft) can be read side-by-side.

Usage
-----
python scripts/benchmark_cdr_grafting.py \
    --qc-json  projects/anti_HSA_VHH_dog_petization/qc/dog_petization_qc.json \
    --merged-json projects/anti_HSA_VHH_dog_petization/merged_benchmark/merged_benchmark.json \
    --donor-pdb-dir projects/anti_HSA_VHH_dog_petization/structures \
    --out-dir projects/anti_HSA_VHH_dog_petization/merged_benchmark \
    [--skip-structure]
"""
from __future__ import annotations
import argparse, json, sys, os, copy, importlib.util
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO))

# ---------------------------------------------------------------------------
# constants
# ---------------------------------------------------------------------------
# Kabat CDR positions for VH / VHH  (both use same scheme)
CDR1_POS = set(str(p) for p in range(26, 36))          # 26-35
CDR2_POS = set(str(p) for p in range(50, 66))          # 50-65 (full VH/VHH CDR2)
CDR2_POS |= {"52A"}                                    # insertion slot
CDR3_POS = set(str(p) for p in range(95, 103))         # 95-102 base
for _ins_letter in "ABCDEFGHIJKLMNOPQRSTUVWXYZ":       # 100A..100Z insertions
    CDR3_POS.add(f"100{_ins_letter}")
ALL_CDR_POS = CDR1_POS | CDR2_POS | CDR3_POS

# VHH hallmark positions - must keep donor residues to preserve sdAb fold
VHH_HALLMARKS = {"37", "44", "45", "47"}

# Dog FR4 (Lokivetmab / Bedinvetmab canonical):  103 W … 113 S
DOG_FR4 = {
    "103": "W", "104": "G", "105": "Q", "106": "G",
    "107": "T", "108": "L", "109": "V", "110": "T",
    "111": "V", "112": "S", "113": "S",
}

# Tier-1 clinical-anchor germlines preferred, then rest
TIER1_GENES = ["IGHV3-35*01", "IGHV3-19*01", "IGHV3-9*01", "IGHV1-30*01", "IGHV3-67*01"]


# ---------------------------------------------------------------------------
# helpers
# ---------------------------------------------------------------------------
def _sort_key(pos_str: str):
    """Sort Kabat position strings: '1','2',...,'82','82A','82B','82C','83',..."""
    if pos_str[-1].isalpha():
        return (int(pos_str[:-1]), pos_str[-1])
    return (int(pos_str), "")


def kabat_to_seq(kd: dict[str, str]) -> str:
    return "".join(kd[k] for k in sorted(kd, key=_sort_key))


def run_anarci(seq: str) -> dict[str, str]:
    """Return Kabat-numbered dict {pos_str: aa} for the sequence."""
    import anarci
    ret = anarci.anarci([("X", seq)], scheme="kabat", output=False)
    results = ret[0]
    numbering = results[0][0][0]  # list of ((pos_int, ins_char), aa)
    out: dict[str, str] = {}
    for (pos, ins), aa in numbering:
        if aa == "-":
            continue
        key = str(pos) if ins.strip() == "" else f"{pos}{ins.strip()}"
        out[key] = aa
    return out


def germline_fr_identity(donor_kd: dict, germ_kd: dict) -> float:
    """Fraction identity over FR positions shared by both."""
    fr_pos = [p for p in donor_kd if p not in ALL_CDR_POS and p not in VHH_HALLMARKS]
    match = total = 0
    for p in fr_pos:
        if p in germ_kd:
            total += 1
            if donor_kd[p] == germ_kd[p]:
                match += 1
    return match / total if total else 0.0


def cdr_graft(donor_kd: dict, acceptor_kd: dict) -> dict[str, str]:
    """
    Build CDR-grafted Kabat dict:
      - FR positions: acceptor (dog germline)
      - CDR positions: donor VHH
      - VHH hallmarks (37,44,45,47): donor VHH (preserve sdAb fold)
      - FR4: dog canonical
    """
    grafted: dict[str, str] = {}

    # FR1 + FR2 + FR3 from acceptor
    for p in acceptor_kd:
        if p not in ALL_CDR_POS:
            grafted[p] = acceptor_kd[p]

    # Override hallmarks with donor values
    for p in VHH_HALLMARKS:
        if p in donor_kd:
            grafted[p] = donor_kd[p]

    # CDRs from donor
    for p in ALL_CDR_POS:
        if p in donor_kd:
            grafted[p] = donor_kd[p]

    # FR4 (dog canonical)
    grafted.update(DOG_FR4)

    return grafted


def load_nanobodybuilder2():
    """Return NanoBodyBuilder2 class from ImmuneBuilder if available."""
    try:
        from ImmuneBuilder import NanoBodyBuilder2 as NBB2
        return NBB2
    except Exception:
        return None


def predict_structure(seq: str, pdb_path: Path, nbb2_cls):
    if nbb2_cls is None:
        return None
    predictor = nbb2_cls()
    nanobody = predictor.predict({"H": seq})
    nanobody.save(str(pdb_path))
    return str(pdb_path)


def calc_rmsd(pdb_a: str, pdb_b: str) -> float | None:
    """Cα RMSD between two PDB files (minimum-length alignment)."""
    try:
        from Bio.PDB import PDBParser, Superimposer
        import numpy as np
        parser = PDBParser(QUIET=True)
        def get_ca(path):
            st = parser.get_structure("x", path)
            return [a for a in st.get_atoms() if a.get_name() == "CA"]
        ca_a = get_ca(pdb_a)
        ca_b = get_ca(pdb_b)
        n = min(len(ca_a), len(ca_b))
        sup = Superimposer()
        sup.set_atoms(ca_a[:n], ca_b[:n])
        sup.apply(ca_b[:n])
        return round(float(np.sqrt(sup.rms)), 3)
    except Exception:
        return None


def run_cmc(seq: str, name: str = "graft") -> dict:
    try:
        from core.cmc.vhh_cmc_engine import evaluate_single_vhh, load_vhh_ref
        ref = load_vhh_ref()
        r = evaluate_single_vhh(name, seq, ref)
        m = r.get("metrics", {})
        return {
            "adi":   round(r.get("adi_score", 0), 1),
            "pi":    round(m.get("pI", 0), 2),
            "sap":   round(m.get("SAP_score", 0), 3),
            "gravy": round(m.get("GRAVY", 0), 3),
            "flags": r.get("risk_flags", []),
        }
    except Exception as e:
        return {"adi": None, "pi": None, "sap": None, "gravy": None, "flags": [str(e)]}


def run_abnativ(seqs: dict[str, str]) -> dict[str, dict]:
    """seqs = {label: sequence}; returns {label: {VHH2_Score: ..., VH2_Score: ...}}"""
    try:
        from Bio.Seq import Seq
        from Bio.SeqRecord import SeqRecord
        from abnativ.model.scoring_functions import abnativ_scoring

        records = [SeqRecord(Seq(s), id=lbl, description="") for lbl, s in seqs.items()]
        out: dict[str, dict] = {k: {} for k in seqs}

        for model in ("VHH2", "VH2"):
            df, _ = abnativ_scoring(
                model_type=model,
                seq_records=records,
                mean_score_only=True,
                do_align=True,
                is_VHH=True,
                verbose=False,
                run_parall_al=False,
            )
            id_col = next((c for c in df.columns if c.lower() in ("seq_id", "id")), None)
            for _, row in df.iterrows():
                sid = str(row[id_col]) if id_col else str(row.iloc[0])
                for col in df.columns:
                    if model in col and "Score" in col and "Percentile" not in col:
                        short = col.replace("AbNatiV ", "").replace(" ", "_")
                        out.setdefault(sid, {})[short] = round(float(row[col]), 4)

        # Normalize to expected keys
        result = {}
        for lbl in seqs:
            row = out.get(lbl, {})
            result[lbl] = {
                "VHH2_Score":    row.get("VHH2_Score"),
                "FR_VHH2_Score": row.get("FR-VHH2_Score"),
                "VH2_Score":     row.get("VH2_Score"),
                "FR_VH2_Score":  row.get("FR-VH2_Score"),
            }
        return result
    except Exception as e:
        return {k: {"VHH2_Score": None, "FR_VHH2_Score": None,
                    "VH2_Score": None, "FR_VH2_Score": None, "_error": str(e)}
                for k in seqs}


def load_nanobert_fn():
    spec = importlib.util.spec_from_file_location(
        "run_dog_qc", REPO / "scripts" / "run_dog_petization_qc.py")
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return getattr(mod, "calc_nanobert_pll", None)


# ---------------------------------------------------------------------------
# main
# ---------------------------------------------------------------------------
def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--qc-json", required=True)
    ap.add_argument("--merged-json", required=True)
    ap.add_argument("--donor-pdb-dir", default=None)
    ap.add_argument("--out-dir", required=True)
    ap.add_argument("--skip-structure", action="store_true")
    args = ap.parse_args()

    qc = json.loads(Path(args.qc_json).read_text())
    merged = json.loads(Path(args.merged_json).read_text())
    out_dir = Path(args.out_dir)
    out_dir.mkdir(parents=True, exist_ok=True)

    # Load dog IGHV Kabat cache
    ighv_cache_path = REPO / "data/germlines/canis_lupus_familiaris_ig_aa/_cache/dog_ighv_kabat_numbered_cache.json"
    ighv_cache = json.loads(ighv_cache_path.read_text())["genes"]

    # NanoBodyBuilder2
    nbb2_cls = None if args.skip_structure else load_nanobodybuilder2()

    # nanoBERT
    print("Loading nanoBERT...")
    nanobert_fn = load_nanobert_fn()

    # -----------------------------------------------------------------------
    # per-antibody CDR grafting
    # -----------------------------------------------------------------------
    graft_results: dict[str, dict] = {}

    for ab in ("A16", "A6"):
        print(f"\n=== CDR grafting {ab} ===")
        donor_seq = qc[ab]["donor_seq"]

        # Step 1: Kabat-annotate donor
        donor_kd = run_anarci(donor_seq)

        # Step 2: find best-match dog IGHV by FR identity
        best_gene, best_id, best_kd = None, -1.0, None
        # Prefer Tier-1 clinical anchors first
        ordered = TIER1_GENES + [g for g in ighv_cache if g not in TIER1_GENES]
        for gene in ordered:
            if gene not in ighv_cache:
                continue
            gkd = ighv_cache[gene]
            frid = germline_fr_identity(donor_kd, gkd)
            if frid > best_id:
                best_id, best_gene, best_kd = frid, gene, gkd

        print(f"  Best acceptor: {best_gene}  FR identity={best_id:.3f}")

        # Step 3: graft
        grafted_kd = cdr_graft(donor_kd, best_kd)
        graft_seq = kabat_to_seq(grafted_kd)

        # identity vs donor
        min_len = min(len(graft_seq), len(donor_seq))
        ident = sum(a == b for a, b in zip(graft_seq, donor_seq)) / max(len(graft_seq), len(donor_seq))

        # Verify CDRs preserved
        def extract_cdr(kd, cdr_pos):
            return "".join(kd[p] for p in sorted(cdr_pos & kd.keys(), key=_sort_key))

        cdr_check = {}
        for name, pos in [("CDR1", CDR1_POS), ("CDR2", CDR2_POS), ("CDR3", CDR3_POS)]:
            donor_cdr = extract_cdr(donor_kd, pos)
            graft_cdr = extract_cdr(grafted_kd, pos)
            cdr_check[name] = {"donor": donor_cdr, "grafted": graft_cdr,
                               "preserved": donor_cdr == graft_cdr}

        # Vernier positions comparison (informational)
        vernier = {}
        for p in ["37", "44", "45", "47", "67", "69", "71", "73", "78", "93", "94"]:
            vernier[p] = {
                "donor": donor_kd.get(p, "-"),
                "dog_germ": best_kd.get(p, "-"),
                "grafted": grafted_kd.get(p, "-"),
            }

        graft_results[ab] = {
            "donor_seq": donor_seq,
            "graft_seq": graft_seq,
            "acceptor_gene": best_gene,
            "acceptor_fr_identity": round(best_id, 4),
            "identity_vs_donor_pct": round(ident * 100, 2),
            "cdr_check": cdr_check,
            "vernier_positions": vernier,
            "n_fr_substitutions": sum(
                1 for p in grafted_kd
                if p not in ALL_CDR_POS and p not in VHH_HALLMARKS
                and p in donor_kd and grafted_kd[p] != donor_kd[p]
            ),
        }
        print(f"  Graft seq: {graft_seq}")
        print(f"  Identity vs donor: {ident*100:.1f}%  |  FR subs: {graft_results[ab]['n_fr_substitutions']}")
        for cname, cv in cdr_check.items():
            status = "OK" if cv["preserved"] else "CHANGED"
            print(f"  {cname}: {cv['donor']} -> {cv['grafted']}  [{status}]")

    # -----------------------------------------------------------------------
    # CMC
    # -----------------------------------------------------------------------
    print("\nRunning CMC for CDR grafts...")
    for ab in ("A16", "A6"):
        cmc = run_cmc(graft_results[ab]["graft_seq"], name=f"{ab}_cdr_graft")
        graft_results[ab]["cmc"] = cmc
        print(f"  {ab} CDR-graft CMC: ADI={cmc['adi']}  pI={cmc['pi']}  SAP={cmc['sap']}")

    # -----------------------------------------------------------------------
    # AbNatiV
    # -----------------------------------------------------------------------
    print("\nRunning AbNatiV (VHH2 + VH2)...")
    all_seqs = {f"{ab}_cdr_graft": graft_results[ab]["graft_seq"] for ab in ("A16", "A6")}
    abnativ_res = run_abnativ(all_seqs)
    for ab in ("A16", "A6"):
        graft_results[ab]["abnativ"] = abnativ_res[f"{ab}_cdr_graft"]
        print(f"  {ab} CDR-graft AbNatiV: VHH2={abnativ_res[f'{ab}_cdr_graft']['VHH2_Score']}  "
              f"VH2={abnativ_res[f'{ab}_cdr_graft']['VH2_Score']}")

    # -----------------------------------------------------------------------
    # nanoBERT
    # -----------------------------------------------------------------------
    print("\nRunning nanoBERT...")
    for ab in ("A16", "A6"):
        if nanobert_fn:
            pll_result = nanobert_fn({f"{ab}_cdr_graft": graft_results[ab]["graft_seq"]})
            # nanobert_fn returns (dict[str, float], error_str_or_None)
            pll_dict, err = pll_result
            pll = pll_dict.get(f"{ab}_cdr_graft") if pll_dict else None
        else:
            pll = None
        graft_results[ab]["nanobert_pll"] = round(pll, 4) if pll is not None else None
        print(f"  {ab} CDR-graft nanoBERT PLL: {pll:.4f}" if pll is not None else f"  {ab} nanoBERT: N/A")

    # -----------------------------------------------------------------------
    # Structure (NanoBodyBuilder2 + RMSD)
    # -----------------------------------------------------------------------
    struct_dir = out_dir / "structures"
    struct_dir.mkdir(exist_ok=True)

    for ab in ("A16", "A6"):
        graft_results[ab]["rmsd_vs_donor"] = None
        graft_results[ab]["pdb_path"] = None

        # Check for already-generated PDB in structures subfolder
        prebuilt = out_dir / "structures" / f"{ab}_cdr_graft_canine.pdb"
        if prebuilt.exists():
            graft_results[ab]["pdb_path"] = str(prebuilt)
            if args.donor_pdb_dir:
                dpdb = Path(args.donor_pdb_dir) / f"{ab}_donor.pdb"
                if dpdb.exists():
                    rmsd = calc_rmsd(str(dpdb), str(prebuilt))
                    graft_results[ab]["rmsd_vs_donor"] = rmsd
                    print(f"  {ab} RMSD vs donor (pre-built): {rmsd}")
            if args.skip_structure:
                print(f"  {ab} structure: using pre-built {prebuilt.name}")
                continue

        if args.skip_structure:
            print(f"  {ab} structure: skipped (--skip-structure)")
            continue

        pdb_out = struct_dir / f"{ab}_cdr_graft_canine.pdb"
        print(f"  Predicting structure {ab} CDR-graft...")
        pdb_path = predict_structure(graft_results[ab]["graft_seq"], pdb_out, nbb2_cls)
        if pdb_path:
            graft_results[ab]["pdb_path"] = str(pdb_path)
            # RMSD vs donor PDB
            if args.donor_pdb_dir:
                dpdb = Path(args.donor_pdb_dir) / f"{ab}_donor.pdb"
                if not dpdb.exists():
                    # try variant names
                    for candidate in Path(args.donor_pdb_dir).glob(f"{ab}*.pdb"):
                        dpdb = candidate; break
                if dpdb.exists():
                    rmsd = calc_rmsd(str(dpdb), pdb_path)
                    graft_results[ab]["rmsd_vs_donor"] = rmsd
                    print(f"  {ab} RMSD vs donor: {rmsd}")

    # -----------------------------------------------------------------------
    # Build extended comparison table (5 variants)
    # merged.comparison_rows format: [{antibody: "A16", cmc: {...}, abnativ: {...}, ...}]
    # -----------------------------------------------------------------------
    def _extract_old_rows(merged_data: dict, ab: str) -> list[dict]:
        """Convert merged_benchmark.json nested format to flat row list."""
        rows = []
        ab_row = next((r for r in merged_data.get("comparison_rows", [])
                       if r.get("antibody") == ab), None)
        if not ab_row:
            return rows
        cmc_d = ab_row.get("cmc", {})
        abn_d = ab_row.get("abnativ", {})
        nb_d  = ab_row.get("nanobert_pll_mean", {})
        rmsd_d = ab_row.get("rmsd_vs_donor_A", {})

        # sequences from QC json (passed via merged arg, rebuild from context)
        seq_d = {}  # no sequence stored in merged benchmark rows

        for v in ("donor", "llamanade", "surface", "merged"):
            c = cmc_d.get(v, {})
            a = abn_d.get(v, {})
            rows.append({
                "Ab": ab, "variant": v, "sequence": seq_d.get(v, ""),
                "ADI":  c.get("adi_score"),
                "pI":   c.get("pI"),
                "SAP":  c.get("SAP_score"),
                "AbNatiV_VHH2":    a.get("VHH2_Score"),
                "AbNatiV_FR_VHH2": a.get("FR-VHH2_Score"),
                "AbNatiV_VH2":     a.get("VH2_Score"),
                "AbNatiV_FR_VH2":  a.get("FR-VH2_Score"),
                "nanoBERT_PLL":    nb_d.get(v),
                "RMSD_vs_donor":   rmsd_d.get(v) if v != "donor" else None,
            })
        return rows

    new_rows = []
    for ab in ("A16", "A6"):
        gr = graft_results[ab]
        cmc = gr.get("cmc", {})
        abn = gr.get("abnativ", {})

        def make_row(variant: str, seq: str, adi, pi, sap,
                     vhh2, fr_vhh2, vh2, fr_vh2, nb_pll, rmsd):
            return {
                "Ab": ab, "variant": variant, "sequence": seq,
                "ADI": adi, "pI": pi, "SAP": sap,
                "AbNatiV_VHH2": vhh2, "AbNatiV_FR_VHH2": fr_vhh2,
                "AbNatiV_VH2": vh2, "AbNatiV_FR_VH2": fr_vh2,
                "nanoBERT_PLL": nb_pll,
                "RMSD_vs_donor": rmsd,
            }

        # Pull previous 4 variants from merged benchmark
        for row in _extract_old_rows(merged, ab):
            new_rows.append(row)

        # add cdr_graft row
        new_rows.append(make_row(
            "cdr_graft", gr["graft_seq"],
            cmc.get("adi"), cmc.get("pi"), cmc.get("sap"),
            abn.get("VHH2_Score"), abn.get("FR_VHH2_Score"),
            abn.get("VH2_Score"), abn.get("FR_VH2_Score"),
            gr.get("nanobert_pll"), gr.get("rmsd_vs_donor"),
        ))
        new_rows.append({})  # spacer

    # -----------------------------------------------------------------------
    # Save JSON
    # -----------------------------------------------------------------------
    output = {
        "cdr_graft_results": graft_results,
        "comparison_rows_5variant": new_rows,
    }
    json_out = out_dir / "cdr_graft_benchmark.json"
    json_out.write_text(json.dumps(output, indent=2, default=str))

    # -----------------------------------------------------------------------
    # Markdown report
    # -----------------------------------------------------------------------
    md_lines = [
        "# 5-Variant dog petization benchmark (donor / llamanade / surface / merged / cdr_graft)",
        "",
        "## CDR-Graft details",
        "",
    ]
    for ab in ("A16", "A6"):
        gr = graft_results[ab]
        md_lines += [
            f"### {ab}",
            f"- **Acceptor germline:** `{gr['acceptor_gene']}`  FR identity = {gr['acceptor_fr_identity']*100:.1f}%",
            f"- **FR substitutions vs donor:** {gr['n_fr_substitutions']}",
            f"- **Identity vs donor:** {gr['identity_vs_donor_pct']:.1f}%",
            "- **CDR preservation:**",
        ]
        for cname, cv in gr["cdr_check"].items():
            st = "✓" if cv["preserved"] else "✗ CHANGED"
            md_lines.append(f"  - {cname}: `{cv['donor']}` {st}")
        md_lines += [
            "- **Grafted sequence:**",
            f"  `{gr['graft_seq']}`",
            "",
            "| Kabat | Donor | Dog Germline | Grafted | Note |",
            "|-------|-------|-------------|---------|------|",
        ]
        for p, v in gr["vernier_positions"].items():
            note = "VHH-hallmark (kept)" if p in VHH_HALLMARKS else "Vernier/FR"
            md_lines.append(f"| {p} | {v['donor']} | {v['dog_germ']} | {v['grafted']} | {note} |")
        md_lines.append("")

    md_lines += [
        "## Full 5-variant comparison",
        "",
        "| Ab | Variant | ADI | pI | SAP | AbNatiV VHH2 | AbNatiV FR-VHH2 | AbNatiV VH2 | AbNatiV FR-VH2 | nanoBERT PLL | Cα RMSD vs donor (Å) |",
        "|----|---------|-----|-----|-----|--------------|-----------------|-------------|----------------|--------------|----------------------|",
    ]
    for row in new_rows:
        if not row:
            md_lines.append("|  |  |  |  |  |  |  |  |  |  |  |")
            continue
        def fmt(v, d=3): return str(round(v, d)) if v is not None else "—"
        md_lines.append(
            f"| {row['Ab']} | {row['variant']} "
            f"| {fmt(row.get('ADI'),1)} | {fmt(row.get('pI'),2)} | {fmt(row.get('SAP'),3)} "
            f"| {fmt(row.get('AbNatiV_VHH2'),4)} | {fmt(row.get('AbNatiV_FR_VHH2'),4)} "
            f"| {fmt(row.get('AbNatiV_VH2'),4)} | {fmt(row.get('AbNatiV_FR_VH2'),4)} "
            f"| {fmt(row.get('nanoBERT_PLL'),4)} | {fmt(row.get('RMSD_vs_donor'),3)} |"
        )

    md_out = out_dir / "5variant_benchmark.md"
    md_out.write_text("\n".join(md_lines), encoding="utf-8")

    print(f"\nWrote {json_out} and {md_out}")


if __name__ == "__main__":
    main()
