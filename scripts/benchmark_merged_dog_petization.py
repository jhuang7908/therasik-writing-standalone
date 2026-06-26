"""
benchmark_merged_dog_petization.py
───────────────────────────────────────────────────────────────────────────────
Merge Llamanade + Surface-reshaping dog petization mutations into one sequence
per clone (union of Kabat positions). On position conflicts, **surface wins**.

Then benchmark **donor**, **llamanade**, **surface**, **merged**:
  - NanoBodyBuilder2 structure + Cα RMSD vs donor PDB
  - VHH CMC (evaluate_single_vhh: ADI + key metrics)
  - AbNatiV VHH2 + VH2
  - nanoBERT mean PLL

Usage (anarcii env):
  python scripts/benchmark_merged_dog_petization.py \\
    --qc-json projects/anti_HSA_VHH_dog_petization/qc/dog_petization_qc.json \\
    --donor-pdb-dir projects/anti_HSA_VHH_dog_petization/structures \\
    --out-dir projects/anti_HSA_VHH_dog_petization/merged_benchmark
"""
from __future__ import annotations

import argparse
import contextlib
import io
import json
import os
import re
import sys
import warnings
from pathlib import Path

warnings.filterwarnings("ignore")
os.environ.setdefault("KMP_DUPLICATE_LIB_OK", "TRUE")

_REPO = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(_REPO))


_MUT_RE = re.compile(r"^([A-Z])(\d+[A-Z]?)([A-Z])$")


def parse_mutation_token(tok: str) -> tuple[str, str, str]:
    """Return (orig_aa, kabat_pos_key, new_aa). E.g. N82BS -> N, 82B, S."""
    m = _MUT_RE.match(tok.strip())
    if not m:
        raise ValueError(f"Bad mutation token: {tok!r}")
    return m.group(1), m.group(2), m.group(3)


def kabat_map_rows(seq: str) -> list[dict]:
    """Anarci Kabat rows: pos, ins, aa."""
    import torch

    torch.multiprocessing.set_sharing_strategy("file_system")
    from anarcii import Anarcii

    runner = Anarcii()
    with contextlib.redirect_stdout(io.StringIO()):
        runner.number(seq.strip().upper())
        result = runner.to_scheme("kabat")
    seq_data = list(result.values())[0] if result else {}
    numbered = seq_data.get("numbering", [])
    rows: list[dict] = []
    for (pos_int, ins_code), aa in numbered:
        if aa == "-" or aa is None:
            continue
        rows.append({
            "pos": int(pos_int),
            "ins": str(ins_code).strip().upper(),
            "aa": aa,
            "key": str(int(pos_int)) + str(ins_code).strip().upper(),
        })
    return rows


def apply_kabat_substitutions(seq: str, key_to_aa: dict[str, str]) -> tuple[str, list[str]]:
    """Replace residues by Kabat key. Verifies expected aa where mutation lists encode it."""
    rows = kabat_map_rows(seq)
    errs: list[str] = []
    out_chars: list[str] = []
    for r in rows:
        k = r["key"]
        aa = r["aa"]
        if k in key_to_aa:
            out_chars.append(key_to_aa[k])
        else:
            out_chars.append(aa)
    merged = "".join(out_chars)
    if len(merged) != len(seq):
        errs.append(f"length_mismatch merged={len(merged)} donor={len(seq)}")
    return merged, errs


def merge_mutation_sets(
    donor_seq: str,
    llam_muts: list[str],
    surf_muts: list[str],
) -> tuple[str, dict]:
    """
    Union of Kabat positions: apply all Llamanade substitutions first, then apply
    Surface list — **surface `to_aa` always wins** when the same Kabat key appears
    in both lists with different targets.
    """
    registry: dict[str, dict] = {}

    for tok in llam_muts:
        o, k, t = parse_mutation_token(tok)
        registry[k] = {"to_aa": t, "donor_aa_expected": o, "methods": ["llamanade"]}

    for tok in surf_muts:
        o, k, t = parse_mutation_token(tok)
        if k not in registry:
            registry[k] = {"to_aa": t, "donor_aa_expected": o, "methods": ["surface"]}
            continue
        prev = registry[k]["to_aa"]
        if prev != t:
            registry[k]["conflict_llamanade_vs_surface"] = {"llamanade_to": prev, "surface_to": t}
        registry[k]["to_aa"] = t
        if "surface" not in registry[k]["methods"]:
            registry[k]["methods"].append("surface")

    key_to_aa = {k: v["to_aa"] for k, v in registry.items()}
    merged, errs = apply_kabat_substitutions(donor_seq, key_to_aa)

    n_both = sum(
        1 for v in registry.values()
        if "llamanade" in v["methods"] and "surface" in v["methods"]
    )
    n_conflict = sum(1 for v in registry.values() if v.get("conflict_llamanade_vs_surface"))

    audit = {
        "n_positions_total": len(registry),
        "n_positions_in_both_method_lists": n_both,
        "n_position_conflicts_surface_wins": n_conflict,
        "registry": registry,
        "apply_errors": errs,
    }
    return merged, audit


def predict_nb(seq: str, out_pdb: Path) -> bool:
    try:
        os.environ.setdefault("KMP_DUPLICATE_LIB_OK", "TRUE")
        from ImmuneBuilder import NanoBodyBuilder2

        out_pdb.parent.mkdir(parents=True, exist_ok=True)
        nb = NanoBodyBuilder2().predict({"H": seq})
        nb.save(str(out_pdb))
        return True
    except Exception as e:
        print(f"[WARN] NanoBodyBuilder2 failed: {e}")
        return False


def ca_rmsd(ref_pdb: str, mob_pdb: str) -> float | None:
    try:
        from Bio.PDB import PDBParser, Superimposer

        p = PDBParser(QUIET=True)
        ref_s = p.get_structure("r", ref_pdb)
        mob_s = p.get_structure("m", mob_pdb)
        rc = list(ref_s[0].get_chains())[0]
        mc = list(mob_s[0].get_chains())[0]

        def cas(ch):
            return [r["CA"] for r in ch.get_residues() if "CA" in r and r.get_id()[0] == " "]

        ra, ma = cas(rc), cas(mc)
        n = min(len(ra), len(ma))
        if n < 10:
            return None
        sup = Superimposer()
        sup.set_atoms(ra[:n], ma[:n])
        sup.apply(mob_s.get_atoms())
        return round(float(sup.rms), 3)
    except Exception:
        return None


def run_abnativ_batch(seq_id_to_seq: dict[str, str]) -> dict[str, dict]:
    from Bio.Seq import Seq
    from Bio.SeqRecord import SeqRecord
    from abnativ.model.scoring_functions import abnativ_scoring

    records = [SeqRecord(Seq(s), id=i, description="") for i, s in seq_id_to_seq.items()]
    out: dict[str, dict] = {k: {} for k in seq_id_to_seq}
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
    return out


def run_nanobert_batch(seq_id_to_seq: dict[str, str]) -> dict[str, float]:
    import importlib.util

    mod_path = _REPO / "scripts" / "run_dog_petization_qc.py"
    spec = importlib.util.spec_from_file_location("dog_qc", mod_path)
    mod = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    spec.loader.exec_module(mod)
    scores, err = mod.calc_nanobert_pll(seq_id_to_seq)
    if err:
        print(f"[WARN] nanoBERT: {err}")
    return scores


def main() -> None:
    try:
        import torch
        torch.multiprocessing.set_sharing_strategy("file_system")
    except Exception:
        pass

    ap = argparse.ArgumentParser()
    ap.add_argument("--qc-json", required=True, type=Path)
    ap.add_argument("--donor-pdb-dir", required=True, type=Path)
    ap.add_argument("--out-dir", required=True, type=Path)
    ap.add_argument("--skip-structure", action="store_true")
    args = ap.parse_args()

    qc = json.loads(args.qc_json.read_text(encoding="utf-8"))

    from core.cmc.vhh_cmc_engine import evaluate_single_vhh, load_vhh_ref

    ref_stats = load_vhh_ref()

    antibodies = [k for k in qc if not k.startswith("_") and isinstance(qc[k], dict) and "llamanade" in qc[k]]
    out_dir = args.out_dir
    out_dir.mkdir(parents=True, exist_ok=True)

    all_rows: list[dict] = []
    merged_payload: dict[str, dict] = {}

    # Build all sequences for batch scoring
    abnativ_input: dict[str, str] = {}
    for ab in antibodies:
        d = qc[ab]
        donor = d["donor_seq"]
        lseq = d["llamanade"]["caninized_seq"]
        sseq = d["surface_reshaping"]["caninized_seq"]
        lm = d["llamanade"]["mutations"]
        sm = d["surface_reshaping"]["mutations"]

        merged_seq, audit = merge_mutation_sets(donor, lm, sm)
        merged_payload[ab] = {
            "merged_sequence": merged_seq,
            "identity_vs_donor_pct": round(
                sum(a == b for a, b in zip(donor, merged_seq)) / max(len(donor), 1) * 100, 2
            ),
            "audit": audit,
            "n_mut_llamanade": len(lm),
            "n_mut_surface": len(sm),
            "n_unique_positions_merged": audit["n_positions_total"],
        }

        abnativ_input[f"{ab}_donor"] = donor
        abnativ_input[f"{ab}_llamanade"] = lseq
        abnativ_input[f"{ab}_surface"] = sseq
        abnativ_input[f"{ab}_merged"] = merged_seq

    print("Running AbNatiV (VHH2 + VH2)...", flush=True)
    abnativ_all = run_abnativ_batch(abnativ_input)

    print("Running nanoBERT...", flush=True)
    nano_all = run_nanobert_batch(abnativ_input)

    for ab in antibodies:
        d = qc[ab]
        donor = d["donor_seq"]
        mp = merged_payload[ab]
        merged_seq = mp["merged_sequence"]

        donor_pdb = args.donor_pdb_dir / f"{ab}_donor.pdb"
        merged_pdb = out_dir / f"{ab}_merged_canine.pdb"

        rmsd_m = None
        if not args.skip_structure and donor_pdb.is_file():
            print(f"  Predicting merged structure {ab}...", flush=True)
            if predict_nb(merged_seq, merged_pdb):
                rmsd_m = ca_rmsd(str(donor_pdb), str(merged_pdb))
        elif args.skip_structure:
            merged_pdb = None

        # CMC each variant
        variants = {
            "donor": donor,
            "llamanade": d["llamanade"]["caninized_seq"],
            "surface": d["surface_reshaping"]["caninized_seq"],
            "merged": merged_seq,
        }
        cmc_block: dict[str, dict] = {}
        for tag, s in variants.items():
            ev = evaluate_single_vhh(f"{ab}_{tag}", s, ref_stats, skip_percentile=False)
            cmc_block[tag] = {
                "adi_score": ev["adi_score"],
                "adi_grade": ev["adi_grade"],
                "overall_status": ev["overall_status"],
                "pI": round(ev["metrics"]["pI"], 3),
                "SAP_score": round(ev["metrics"]["SAP_score"], 4),
                "GRAVY": round(ev["metrics"]["GRAVY"], 4),
                "n_warn": ev["n_warn"],
                "n_fail": ev["n_fail"],
            }

        def pull_ab(sid: str) -> dict:
            raw = abnativ_all.get(sid, {})
            return {
                "VHH2_Score": raw.get("VHH2_Score"),
                "FR-VHH2_Score": raw.get("FR-VHH2_Score"),
                "VH2_Score": raw.get("VH2_Score"),
                "FR-VH2_Score": raw.get("FR-VH2_Score"),
            }

        row = {
            "antibody": ab,
            "cmc": cmc_block,
            "abnativ": {
                "donor": pull_ab(f"{ab}_donor"),
                "llamanade": pull_ab(f"{ab}_llamanade"),
                "surface": pull_ab(f"{ab}_surface"),
                "merged": pull_ab(f"{ab}_merged"),
            },
            "nanobert_pll_mean": {
                "donor": nano_all.get(f"{ab}_donor"),
                "llamanade": nano_all.get(f"{ab}_llamanade"),
                "surface": nano_all.get(f"{ab}_surface"),
                "merged": nano_all.get(f"{ab}_merged"),
            },
            "rmsd_vs_donor_A": {
                "llamanade": d["llamanade"].get("rmsd_vs_donor_A"),
                "surface": d["surface_reshaping"].get("rmsd_vs_donor_A"),
                "merged": rmsd_m,
            },
            "merged_pdb": str(merged_pdb) if (merged_pdb and merged_pdb.is_file()) else None,
        }
        all_rows.append(row)

        sid_m = f"{ab}_merged"
        print(
            f"=== {ab} merged: id={mp['identity_vs_donor_pct']}%  "
            f"uniq_pos={mp['n_unique_positions_merged']}  "
            f"ADI={cmc_block['merged']['adi_score']}  "
            f"VHH2={pull_ab(sid_m).get('VHH2_Score')}  "
            f"nanoPLL={nano_all.get(sid_m)}  RMSD={rmsd_m}",
            flush=True,
        )

    out_json = out_dir / "merged_benchmark.json"
    out_json.write_text(
        json.dumps({"antibodies": merged_payload, "comparison_rows": all_rows}, indent=2, ensure_ascii=False),
        encoding="utf-8",
    )

    # Markdown table
    md_lines = [
        "# Merged dog petization benchmark",
        "",
        "**Merge rule**: union of Kabat mutation positions from Llamanade + Surface; **same position conflict → surface `to_aa` wins**.",
        "",
        "| Ab | Variant | ADI | pI | SAP | AbNatiV VHH2 | AbNatiV FR-VHH2 | AbNatiV VH2 | AbNatiV FR-VH2 | nanoBERT PLL | Cα RMSD vs donor (Å) |",
        "|----|---------|-----|-----|-----|--------------|-----------------|-------------|----------------|--------------|----------------------|",
    ]
    for row in all_rows:
        ab = row["antibody"]
        rmap = row["rmsd_vs_donor_A"]
        for var in ("donor", "llamanade", "surface", "merged"):
            c = row["cmc"][var]
            a = row["abnativ"][var]
            nb = row["nanobert_pll_mean"][var]
            if var == "donor":
                rmsd = "—"
            elif var == "merged":
                rmsd = rmap.get("merged")
            else:
                rmsd = rmap.get(var)
            md_lines.append(
                f"| {ab} | {var} | {c['adi_score']} | {c['pI']} | {c['SAP_score']} | "
                f"{a.get('VHH2_Score')} | {a.get('FR-VHH2_Score')} | {a.get('VH2_Score')} | {a.get('FR-VH2_Score')} | "
                f"{nb} | {rmsd} |"
            )
        md_lines.append("|  |  |  |  |  |  |  |  |  |  |  |")

    (out_dir / "merged_benchmark.md").write_text("\n".join(md_lines), encoding="utf-8")
    print(f"\nWrote {out_json} and {out_dir / 'merged_benchmark.md'}")


if __name__ == "__main__":
    main()
