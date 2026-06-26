"""
Benchmark Deep Frequency-Guided petization against Donor and Surface Reshaping.
"""
from __future__ import annotations
import json, sys, importlib.util
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO))

def load_nanobodybuilder2():
    try:
        from ImmuneBuilder import NanoBodyBuilder2 as NBB2
        return NBB2
    except Exception:
        return None

def predict_structure(seq: str, pdb_path: Path, nbb2_cls):
    if pdb_path.is_file():
        return str(pdb_path)
    if nbb2_cls is None:
        return None
    predictor = nbb2_cls()
    nanobody = predictor.predict({"H": seq})
    nanobody.save(str(pdb_path))
    return str(pdb_path)

def calc_rmsd(pdb_a: str, pdb_b: str) -> float | None:
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

def run_cmc(seq: str, name: str = "variant") -> dict:
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
            "hydro9": round(m.get("hydro_patch_max9", 0), 3),
            "n_warn": r.get("n_warn", 0),
            "n_fail": r.get("n_fail", 0),
        }
    except Exception as e:
        return {
            "adi": None, "pi": None, "sap": None, "gravy": None,
            "hydro9": None, "n_warn": None, "n_fail": None,
        }

def run_abnativ(seqs: dict[str, str]) -> dict[str, dict]:
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
                    "VH2_Score": None, "FR_VH2_Score": None} for k in seqs}

def load_nanobert_fn():
    spec = importlib.util.spec_from_file_location(
        "run_dog_qc", REPO / "scripts" / "run_dog_petization_qc.py")
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return getattr(mod, "calc_nanobert_pll", None)

def main():
    out_dir = REPO / "projects/anti_HSA_VHH_dog_petization/deep_freq"
    out_dir.mkdir(parents=True, exist_ok=True)

    bench_path = REPO / "projects/anti_HSA_VHH_dog_petization/merged_benchmark/cdr_graft_benchmark.json"
    bench_data = json.loads(bench_path.read_text())

    old_rows = bench_data.get("comparison_rows_5variant", [])
    surface_path = REPO / "projects/anti_HSA_VHH_dog_petization/surface_reshaping/surface_reshaping_result.json"
    surface_data = json.loads(surface_path.read_text())

    df_path = out_dir / "deep_freq_result.json"
    df_data = json.loads(df_path.read_text())
    
    nbb2_cls = load_nanobodybuilder2()
    nanobert_fn = load_nanobert_fn()

    def find_bench_row(ab: str, variant: str) -> dict | None:
        for row in old_rows:
            if row and row.get("Ab") == ab and row.get("variant") == variant:
                return row
        return None

    def fmt(v, d=3):
        return str(round(v, d)) if v is not None else "—"

    # Build markdown: CMC from sequences; AbNatiV + nanoBERT batched per antibody (same scoring run)
    md_lines = [
        "# Deep Frequency-Guided vs donor / surface / standard CDR graft",
        "",
        "Variants: **donor**, **surface** (SASA ≥ 20 Å² FR reshaping; `surface_reshaping_result.json`), **cdr_graft** (dog IGHV acceptor + donor CDRs + Kabat 37/44/45/47 from donor; `benchmark_cdr_grafting.py`), **deep_freq_protected** (`run_deep_freq_petization.py`).",
        "",
        "## Sequence scores (AbNatiV + nanoBERT)",
        "",
        "- **AbNatiV_VHH2** / **AbNatiV_VH2**: AbNatiV models `VHH2` and `VH2` (plus FR-VHH2 / FR-VH2).",
        "- **nanoBERT_PLL**: pseudo-log-likelihood from Hugging Face `NaturalAntibody/nanoBERT` (see `scripts/run_dog_petization_qc.py`). There is no separate “nanoherb2”; if that was meant, use this column.",
        "",
        "## Why ADI / SAP can match across designs",
        "",
        "- **SAP** (`SAP_score`) is a **7-mer hydrophobic fraction** proxy (`_sap_proxy` in `core/cmc/vhh_cmc_engine.py`), rounded to 0.001. Many FR-only edits **do not change the worst 7-mer**, so SAP is unchanged.",
        "- **ADI** aggregates **PASS/WARN/FAIL** flags into four buckets; if no metric crosses a gate, the weighted score **plateaus** (often the same 1-decimal ADI as donor).",
        "- **GRAVY**, **Hydro9** (`hydro_patch_max9`), and **n_warn** separate designs when ADI/SAP look tied.",
        "",
        "| Ab | Variant | ADI | pI | SAP | GRAVY | Hydro9 | n_warn | "
        "AbNatiV_VHH2 | AbNatiV_FR-VHH2 | AbNatiV_VH2 | AbNatiV_FR-VH2 | nanoBERT_PLL | Cα RMSD vs donor (Å) |",
        "|----|---------|-----|-----|-----|-------|--------|--------|"
        "--------------|----------------|-------------|----------------|--------------|----------------------|",
    ]

    json_rows: list[dict] = []

    for ab in ("A16", "A6"):
        if ab not in df_data:
            continue
        graft = bench_data["cdr_graft_results"][ab]
        donor_seq = graft["donor_seq"]
        graft_seq = graft["graft_seq"]
        surface_seq = surface_data[ab]["reshaped_seq"]
        deep_seq = df_data[ab]["reshaped_seq"]

        print(f"\n=== {ab}: structure + AbNatiV + nanoBERT (4 variants) ===")

        struct_dir = out_dir / "structures"
        struct_dir.mkdir(exist_ok=True)
        pdb_out = struct_dir / f"{ab}_deep_freq.pdb"
        predict_structure(deep_seq, pdb_out, nbb2_cls)
        donor_pdb = REPO / f"projects/anti_HSA_VHH_dog_petization/structures/{ab}_donor.pdb"
        rmsd_deep = None
        if donor_pdb.exists():
            rmsd_deep = calc_rmsd(str(donor_pdb), str(pdb_out))

        score_ids = {
            "donor": f"{ab}_donor",
            "surface": f"{ab}_surface",
            "cdr_graft": f"{ab}_cdr_graft",
            "deep_freq_protected": f"{ab}_deep_freq",
        }
        seq_batch = {
            score_ids["donor"]: donor_seq,
            score_ids["surface"]: surface_seq,
            score_ids["cdr_graft"]: graft_seq,
            score_ids["deep_freq_protected"]: deep_seq,
        }
        abnativ_all = run_abnativ(seq_batch)
        pll_all: dict[str, float] = {}
        if nanobert_fn:
            pll_dict, err = nanobert_fn(seq_batch)
            if pll_dict:
                pll_all = pll_dict

        def row_from_scores(vkey: str, cmc: dict, rmsd_val):
            sid = score_ids[vkey]
            an = abnativ_all.get(sid, {})
            pll = pll_all.get(sid)
            return {
                "Ab": ab,
                "variant": vkey,
                "ADI": cmc["adi"],
                "pI": cmc["pi"],
                "SAP": cmc["sap"],
                "GRAVY": cmc["gravy"],
                "Hydro9": cmc["hydro9"],
                "n_warn": cmc["n_warn"],
                "AbNatiV_VHH2": an.get("VHH2_Score"),
                "AbNatiV_FR_VHH2": an.get("FR_VHH2_Score"),
                "AbNatiV_VH2": an.get("VH2_Score"),
                "AbNatiV_FR_VH2": an.get("FR_VH2_Score"),
                "nanoBERT_PLL": round(pll, 4) if pll is not None else None,
                "RMSD_vs_donor": rmsd_val,
            }

        variant_defs = [
            ("donor", donor_seq, lambda: None),
            ("surface", surface_seq, lambda: find_bench_row(ab, "surface")),
            ("cdr_graft", graft_seq, lambda: find_bench_row(ab, "cdr_graft")),
            ("deep_freq_protected", deep_seq, lambda: None),
        ]

        for vkey, seq, bench_fn in variant_defs:
            c = run_cmc(seq, f"{ab}_{vkey}")
            br = bench_fn() or {}
            rmsd_val = None
            if vkey == "deep_freq_protected":
                rmsd_val = rmsd_deep
            else:
                rmsd_val = br.get("RMSD_vs_donor")

            rec = row_from_scores(vkey, c, rmsd_val)
            json_rows.append(rec)
            bold = vkey == "deep_freq_protected"
            pfx, sfx = ("**", "**") if bold else ("", "")
            md_lines.append(
                f"| {pfx}{ab}{sfx} | {pfx}{vkey}{sfx} "
                f"| {pfx}{fmt(c['adi'],1)}{sfx} | {pfx}{fmt(c['pi'],2)}{sfx} | {pfx}{fmt(c['sap'],3)}{sfx} "
                f"| {pfx}{fmt(c['gravy'],3)}{sfx} | {pfx}{fmt(c['hydro9'],3)}{sfx} | {pfx}{c['n_warn']}{sfx} "
                f"| {pfx}{fmt(rec['AbNatiV_VHH2'],4)}{sfx} | {pfx}{fmt(rec['AbNatiV_FR_VHH2'],4)}{sfx} "
                f"| {pfx}{fmt(rec['AbNatiV_VH2'],4)}{sfx} | {pfx}{fmt(rec['AbNatiV_FR_VH2'],4)}{sfx} "
                f"| {pfx}{fmt(rec['nanoBERT_PLL'],4)}{sfx} | {pfx}{fmt(rmsd_val,3)}{sfx} |"
            )
        md_lines.append("|  |  |  |  |  |  |  |  |  |  |  |  |  |  |")

    md_out = out_dir / "deep_freq_benchmark.md"
    md_out.write_text("\n".join(md_lines), encoding="utf-8")
    json_out = out_dir / "deep_freq_benchmark.json"
    json_out.write_text(json.dumps({"rows": json_rows}, indent=2), encoding="utf-8")
    print(f"\nWrote {md_out} and {json_out}")

if __name__ == "__main__":
    main()
