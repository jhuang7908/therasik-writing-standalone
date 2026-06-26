"""
scripts/run_vaccine_design.py
─────────────────────────────
InSynBio Vaccine Design CLI — reproducible, auditable, AI-model-agnostic.

Every run writes a structured JSON audit log so any AI model or engineer
can reproduce results from the same inputs.

Subcommands
-----------
  scan          Scan a protein sequence for MHC-I epitopes
  neo-compare   Compare wild-type vs mutant peptide for neoantigen potential
  assemble      Assemble a multi-epitope mRNA vaccine construct
  codon-opt     Codon-optimize an amino acid sequence for human mRNA expression
  coverage      Calculate HLA population coverage for a set of alleles
  prioritize    Three-layer prioritisation: self-tolerance filter +
                expression weighting + greedy population coverage optimisation

Usage examples
--------------
  conda run -n vaccine python scripts/run_vaccine_design.py scan \\
      --seq MTEYKLVVVGADGVGKSALTIQLIQNHFV \\
      --alleles HLA-A*02:01 HLA-A*11:01 \\
      --out results/kras_scan.json

  conda run -n vaccine python scripts/run_vaccine_design.py neo-compare \\
      --wt KLVVVGAGGVGK --mut KLVVVGADGVGK \\
      --allele HLA-A*02:01 \\
      --out results/kras_g12d_neo.json

  conda run -n vaccine python scripts/run_vaccine_design.py assemble \\
      --mhc1 KLVVVGADGVGK VVVGADGVGKS \\
      --mhc2 KLVVVGADGVGKSALT \\
      --name KRAS_G12D_v1 \\
      --seed 42 \\
      --out results/kras_construct.json

  conda run -n vaccine python scripts/run_vaccine_design.py codon-opt \\
      --seq MDAMKRGLCCVLLLCGAVFVSPS \\
      --seed 42 \\
      --out results/signal_codon.json

Reproducibility guarantee
--------------------------
  - All runs fix random seed (default 42)
  - Audit JSON records: tool versions, MHCflurry version, inputs, outputs, timestamp
  - Given identical inputs + seed, output is deterministic
"""
from __future__ import annotations

import argparse
import hashlib
import json
import logging
import sys
from dataclasses import asdict
from datetime import datetime, timezone
from pathlib import Path

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    datefmt="%Y-%m-%dT%H:%M:%S",
)
logger = logging.getLogger("vaccine_design_cli")

# ── version bookkeeping ──────────────────────────────────────────────────────

CLI_VERSION = "1.0.0"

_SUITE = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(_SUITE))


def _get_module_versions() -> dict:
    try:
        from core.vaccine_design import MODULE_VERSIONS
        return MODULE_VERSIONS
    except Exception:
        return {}


def _get_mhcflurry_version() -> str:
    try:
        import mhcflurry
        return getattr(mhcflurry, "__version__", "unknown")
    except ImportError:
        return "not_installed"


# ── audit log helpers ────────────────────────────────────────────────────────

def _input_hash(data: dict) -> str:
    """SHA-256 of sorted JSON serialization of inputs."""
    blob = json.dumps(data, sort_keys=True, default=str).encode()
    return hashlib.sha256(blob).hexdigest()[:16]


def _write_audit(out_path: Path, subcommand: str, inputs: dict, outputs: dict) -> None:
    audit = {
        "run_id": f"{subcommand}_{datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%SZ')}_{_input_hash(inputs)}",
        "timestamp_utc": datetime.now(timezone.utc).isoformat(),
        "subcommand": subcommand,
        "cli_version": CLI_VERSION,
        "module_versions": _get_module_versions(),
        "mhcflurry_version": _get_mhcflurry_version(),
        "inputs": inputs,
        "inputs_hash_sha256_16": _input_hash(inputs),
        "outputs": outputs,
    }
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(json.dumps(audit, indent=2, default=str), encoding="utf-8")
    logger.info(f"Audit log written → {out_path}")


def _print_and_write(subcommand: str, inputs: dict, outputs: dict, out: Path | None) -> None:
    """Pretty-print outputs and optionally write audit JSON."""
    print(json.dumps(outputs, indent=2, default=str))
    if out:
        _write_audit(out, subcommand, inputs, outputs)


# ── subcommand: scan ─────────────────────────────────────────────────────────

def cmd_scan(args: argparse.Namespace) -> None:
    from core.vaccine_design.neoantigen_scanner import NeoantigenScanner

    alleles = args.alleles or ["HLA-A*02:01", "HLA-A*24:02", "HLA-A*11:01",
                                "HLA-B*07:02", "HLA-B*08:01"]
    scanner = NeoantigenScanner(alleles=alleles)
    df = scanner.scan_protein(args.seq, top_n=args.top_n, only_sb=args.only_sb)

    hits = df.to_dict(orient="records") if not df.empty else []
    inputs = {"seq": args.seq, "alleles": alleles, "top_n": args.top_n, "only_sb": args.only_sb}
    outputs = {
        "total_hits": len(hits),
        "strong_binders": int((df["rank_label"] == "SB").sum()) if not df.empty else 0,
        "weak_binders": int((df["rank_label"] == "WB").sum()) if not df.empty else 0,
        "hits": hits,
    }
    _print_and_write("scan", inputs, outputs, Path(args.out) if args.out else None)


# ── subcommand: neo-compare ───────────────────────────────────────────────────

def cmd_neo_compare(args: argparse.Namespace) -> None:
    from core.vaccine_design.neoantigen_scanner import NeoantigenScanner

    alleles = [args.allele] if args.allele else ["HLA-A*02:01"]
    scanner = NeoantigenScanner(alleles=alleles)

    results = []
    for allele in alleles:
        result = scanner.compare_neoantigen(args.wt, args.mut, allele=allele)
        results.append(asdict(result))

    inputs = {"wt": args.wt, "mut": args.mut, "alleles": alleles}
    outputs = {"comparisons": results}
    _print_and_write("neo-compare", inputs, outputs, Path(args.out) if args.out else None)


# ── subcommand: assemble ──────────────────────────────────────────────────────

def cmd_assemble(args: argparse.Namespace) -> None:
    from core.vaccine_design.multi_epitope_assembler import MultiEpitopeAssembler
    from core.vaccine_design.codon_optimizer import CodonOptimizer
    from core.vaccine_design.population_coverage import PopulationCoverage

    asm = MultiEpitopeAssembler(
        signal=args.signal,
        add_mitd=not args.no_mitd,
        add_padre=not args.no_padre,
        check_junctions=not args.no_junction_check,
    )
    construct = asm.assemble(
        mhc1_epitopes=args.mhc1 or [],
        mhc2_epitopes=args.mhc2 or [],
        construct_name=args.name,
    )

    codon_result = None
    if not args.no_codon_opt:
        opt = CodonOptimizer(seed=args.seed)
        codon_result = opt.optimize(construct.full_protein)

    cov_result = {}
    if construct.full_protein:
        all_alleles = (args.mhc1_alleles or []) + (args.mhc2_alleles or [])
        if all_alleles:
            cov = PopulationCoverage()
            cov_result = cov.calculate(all_alleles)

    inputs = {
        "mhc1_epitopes": args.mhc1 or [],
        "mhc2_epitopes": args.mhc2 or [],
        "signal": args.signal,
        "add_mitd": not args.no_mitd,
        "add_padre": not args.no_padre,
        "check_junctions": not args.no_junction_check,
        "codon_opt_seed": args.seed,
        "name": args.name,
    }
    outputs = {
        "construct_name": construct.name,
        "full_protein": construct.full_protein,
        "length_aa": construct.length_aa,
        "total_epitopes": construct.total_epitopes,
        "mhc1_count": construct.mhc1_count,
        "mhc2_count": construct.mhc2_count,
        "junctional_binders": construct.junctional_binders,
        "padre_included": construct.padre_included,
        "signal_peptide": construct.signal_peptide,
        "mitd_fused": construct.mitd_fused,
        "epitope_map": construct.epitope_map,
        "codon_optimization": {
            "mrna_sequence": codon_result.mrna_sequence if codon_result else None,
            "cai": codon_result.cai if codon_result else None,
            "gc_content": codon_result.gc_content if codon_result else None,
            "uridine_fraction": codon_result.uridine_fraction if codon_result else None,
            "cpg_count": codon_result.cpg_count if codon_result else None,
            "length_nt": codon_result.length_nt if codon_result else None,
            "mfe": codon_result.mfe if codon_result else None,
        } if codon_result else None,
        "population_coverage": cov_result or None,
    }
    _print_and_write("assemble", inputs, outputs, Path(args.out) if args.out else None)


# ── subcommand: codon-opt ────────────────────────────────────────────────────

def cmd_codon_opt(args: argparse.Namespace) -> None:
    from core.vaccine_design.codon_optimizer import CodonOptimizer

    opt = CodonOptimizer(
        seed=args.seed,
        n_candidates=args.n_candidates,
        use_linearfold=not args.no_linearfold,
    )
    result = opt.optimize(args.seq)

    inputs = {"seq": args.seq, "seed": args.seed, "n_candidates": args.n_candidates}
    outputs = asdict(result)
    _print_and_write("codon-opt", inputs, outputs, Path(args.out) if args.out else None)


# ── subcommand: coverage ──────────────────────────────────────────────────────

def cmd_coverage(args: argparse.Namespace) -> None:
    from core.vaccine_design.population_coverage import PopulationCoverage

    cov = PopulationCoverage()
    result = cov.calculate(args.alleles)

    inputs = {"alleles": args.alleles}
    outputs = result if isinstance(result, dict) else asdict(result)
    _print_and_write("coverage", inputs, outputs, Path(args.out) if args.out else None)


# ── subcommand: mhc2-predict ──────────────────────────────────────────────────

def cmd_mhc2_predict(args: argparse.Namespace) -> None:
    """MHC-II prediction via IEDB API (online, free, AUC ~0.80)."""
    from core.vaccine_design.mhc2_predictor import MHC2Predictor

    alleles = args.alleles or None  # None → use DEFAULT_DR_ALLELES inside module
    pred = MHC2Predictor(method=args.method)

    if args.peptides:
        results = []
        for allele in (alleles or ["HLA-DRB1*04:01"]):
            hits = pred.predict_peptides(args.peptides, allele=allele)
            results.extend([
                {"peptide": h.peptide, "allele": h.allele, "rank_percentile": h.rank_percentile,
                 "ic50_nm": h.ic50_nm, "rank_label": h.rank_label, "core": h.core}
                for h in hits
            ])
        inputs = {"peptides": args.peptides, "alleles": alleles, "method": args.method}
        outputs = {"total": len(results), "predictions": results}
    else:
        panel = pred.scan_panel(args.seq, alleles=alleles, top_n_per_allele=args.top_n)
        all_hits = []
        for r in panel:
            if r.error:
                logger.warning(f"IEDB error for {r.allele}: {r.error}")
            all_hits.extend([
                {"peptide": h.peptide, "allele": h.allele, "rank_percentile": h.rank_percentile,
                 "ic50_nm": h.ic50_nm, "rank_label": h.rank_label, "start": h.start}
                for h in r.hits
            ])
        inputs = {"seq": args.seq, "alleles": alleles, "method": args.method, "top_n": args.top_n}
        outputs = {
            "total_hits": len(all_hits),
            "strong_binders": sum(1 for h in all_hits if h["rank_label"] == "SB"),
            "weak_binders": sum(1 for h in all_hits if h["rank_label"] == "WB"),
            "accuracy_note": "MHC-II IEDB API (AUC ~0.80). Use for ranking only.",
            "hits": all_hits,
        }

    _print_and_write("mhc2-predict", inputs, outputs, Path(args.out) if args.out else None)


# ── subcommand: iedb-search ───────────────────────────────────────────────────

def cmd_iedb_search(args: argparse.Namespace) -> None:
    """Search IEDB online for T cell epitopes by antigen or pathogen."""
    from core.vaccine_design.iedb_search import IEDBSearcher

    searcher = IEDBSearcher()

    if args.pathogen:
        results = searcher.search_infectious_epitopes(
            pathogen=args.pathogen,
            hla=args.hla,
            mhc_class=args.mhc_class,
            max_results=args.max_results,
        )
    else:
        results = searcher.search_tcell(
            antigen=args.antigen,
            hla=args.hla,
            positive_only=True,
            max_results=args.max_results,
        )

    web_url = IEDBSearcher.web_url_epitope_search(
        antigen=args.antigen,
        hla=args.hla,
        pathogen=args.pathogen,
    )

    inputs = {
        "antigen": args.antigen,
        "pathogen": args.pathogen,
        "hla": args.hla,
        "mhc_class": args.mhc_class,
        "max_results": args.max_results,
    }
    outputs = {
        "count": len(results),
        "iedb_web_url": web_url,
        "note": "Data from IEDB (www.iedb.org). License: CC BY 3.0 US. Cite: Vita et al. 2019 NAR.",
        "results": results,
    }
    _print_and_write("iedb-search", inputs, outputs, Path(args.out) if args.out else None)


# ── subcommand: prioritize ────────────────────────────────────────────────────

def cmd_prioritize(args: argparse.Namespace) -> None:
    """
    Three-layer epitope prioritisation pipeline.

    Input: JSON file from a previous 'scan' run (outputs.hits array)
           OR any JSON array with keys: peptide, allele, presentation_score,
           affinity (nM), optional dai, wt_peptide.
    """
    from core.vaccine_design.epitope_prioritizer import (
        EpitopePrioritizer, EpitopeCandidate,
    )

    # Load scan results
    scan_path = Path(args.scan_out)
    raw = json.loads(scan_path.read_text(encoding="utf-8"))

    # Support both full audit JSON and bare arrays
    if isinstance(raw, dict):
        hits = raw.get("outputs", {}).get("hits", raw.get("hits", []))
    else:
        hits = raw  # bare list

    if not hits:
        logger.error("No epitope hits found in %s", scan_path)
        sys.exit(1)

    candidates = []
    for h in hits:
        candidates.append(EpitopeCandidate(
            peptide=str(h.get("peptide", "")),
            allele=str(h.get("allele", args.allele)),
            mhc_class="I",
            gene=args.gene,
            cancer_type=args.cancer_type,
            presentation_score=float(h.get("presentation_score", 0.0)),
            affinity_nM=float(h.get("affinity", h.get("affinity_nM", 9999.0))),
            processing_score=float(h.get("processing_score", 0.0)),
            dai=float(h.get("dai", 0.0)),
            wt_peptide=str(h.get("wt_peptide", "")),
            wt_affinity_nM=float(h.get("wt_affinity", h.get("wt_affinity_nM", 9999.0))),
        ))

    prioritizer = EpitopePrioritizer(cancer_type=args.cancer_type)
    ranked = prioritizer.prioritize(candidates, keep_failed=args.keep_failed)
    selected, trace = prioritizer.select_for_vaccine(
        ranked,
        n=args.n,
        target_population=args.target_pop,
        min_coverage=args.min_coverage,
    )

    # Print human-readable coverage trace to stderr
    print(prioritizer.coverage_report(trace), file=sys.stderr)

    inputs = {
        "scan_out": str(scan_path),
        "gene": args.gene,
        "cancer_type": args.cancer_type,
        "n": args.n,
        "target_pop": args.target_pop,
        "min_coverage": args.min_coverage,
        "n_input_candidates": len(candidates),
    }
    outputs = {
        "n_passed_tolerance": sum(1 for r in ranked if r.tolerance.pass_filter),
        "n_failed_tolerance": sum(1 for r in ranked if not r.tolerance.pass_filter),
        "n_selected": len(selected),
        "final_coverage": trace[-1].cumulative_coverage if trace else {},
        "ranked_epitopes": [
            {
                "rank": r.rank,
                "peptide": r.candidate.peptide,
                "allele": r.candidate.allele,
                "composite_score": r.composite_score,
                "presentation_score": r.candidate.presentation_score,
                "affinity_nM": r.candidate.affinity_nM,
                "dai": r.candidate.dai,
                "expression_weight": r.expression.weight,
                "tumor_tpm": r.expression.tumor_tpm,
                "normal_tpm": r.expression.normal_tpm,
                "diff_ratio": r.expression.diff_ratio,
                "tolerance_pass": r.tolerance.pass_filter,
                "tolerance_reason": r.tolerance.reason,
                "anchor_mutation": r.tolerance.anchor_mutation,
            }
            for r in ranked
        ],
        "selected_for_vaccine": [
            {
                "peptide": ep.candidate.peptide,
                "allele": ep.candidate.allele,
                "composite_score": ep.composite_score,
                "coverage_gain": ep.coverage_gain,
            }
            for ep in selected
        ],
        "coverage_trace": [
            {
                "step": s.step,
                "peptide": s.peptide,
                "allele": s.allele,
                "composite_score": s.composite_score,
                "cumulative_coverage": s.cumulative_coverage,
            }
            for s in trace
        ],
    }
    _print_and_write("prioritize", inputs, outputs, Path(args.out) if args.out else None)


# ── argument parser ───────────────────────────────────────────────────────────

def build_parser() -> argparse.ArgumentParser:
    ap = argparse.ArgumentParser(
        prog="run_vaccine_design",
        description=(
            f"InSynBio Vaccine Design CLI v{CLI_VERSION}\n"
            "Reproducible multi-epitope mRNA vaccine design. All runs produce audit JSON.\n"
            "Environment: conda activate vaccine"
        ),
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    ap.add_argument("--version", action="version", version=f"%(prog)s {CLI_VERSION}")

    sub = ap.add_subparsers(dest="subcommand", required=True)

    # ── scan ──
    p_scan = sub.add_parser("scan", help="Scan protein sequence for MHC-I epitopes")
    p_scan.add_argument("--seq", required=True, help="Protein sequence (single-letter AA)")
    p_scan.add_argument("--alleles", nargs="+", default=None,
                        help="HLA alleles to scan (default: 7-allele panel)")
    p_scan.add_argument("--top-n", type=int, default=50, dest="top_n",
                        help="Return top N hits (default: 50)")
    p_scan.add_argument("--only-sb", action="store_true", dest="only_sb",
                        help="Return only strong binders (presentation_percentile < 0.5%%)")
    p_scan.add_argument("--out", default=None, help="Write audit JSON to this path")

    # ── neo-compare ──
    p_neo = sub.add_parser("neo-compare",
                            help="Compare WT vs mutant peptide for neoantigen potential")
    p_neo.add_argument("--wt", required=True, help="Wild-type peptide sequence")
    p_neo.add_argument("--mut", required=True, help="Mutant peptide sequence")
    p_neo.add_argument("--allele", default=None,
                       help="Single HLA allele (default: HLA-A*02:01); "
                            "use multiple --allele flags or pass comma-separated")
    p_neo.add_argument("--out", default=None, help="Write audit JSON to this path")

    # ── assemble ──
    p_asm = sub.add_parser("assemble",
                            help="Assemble multi-epitope mRNA vaccine construct")
    p_asm.add_argument("--mhc1", nargs="+", default=None,
                       help="MHC-I epitope sequences (8-11 aa)")
    p_asm.add_argument("--mhc2", nargs="+", default=None,
                       help="MHC-II epitope sequences (13-25 aa)")
    p_asm.add_argument("--mhc1-alleles", nargs="+", default=None, dest="mhc1_alleles",
                       help="MHC-I alleles (for coverage calculation)")
    p_asm.add_argument("--mhc2-alleles", nargs="+", default=None, dest="mhc2_alleles",
                       help="MHC-II alleles (for coverage calculation)")
    p_asm.add_argument("--name", default="InSynBio_mRNA_Vaccine_v1",
                       help="Construct name")
    p_asm.add_argument("--signal", default="tPA",
                       choices=["tPA", "IgK", "CD8a"],
                       help="Signal peptide (default: tPA)")
    p_asm.add_argument("--seed", type=int, default=42,
                       help="Random seed for codon optimizer (default: 42)")
    p_asm.add_argument("--no-mitd", action="store_true", dest="no_mitd",
                       help="Disable MITD fusion")
    p_asm.add_argument("--no-padre", action="store_true", dest="no_padre",
                       help="Disable PADRE universal CD4 epitope")
    p_asm.add_argument("--no-junction-check", action="store_true", dest="no_junction_check",
                       help="Skip junctional neoepitope check (faster, less safe)")
    p_asm.add_argument("--no-codon-opt", action="store_true", dest="no_codon_opt",
                       help="Skip codon optimization step")
    p_asm.add_argument("--out", default=None, help="Write audit JSON to this path")

    # ── codon-opt ──
    p_cod = sub.add_parser("codon-opt",
                            help="Codon-optimize amino acid sequence for human mRNA")
    p_cod.add_argument("--seq", required=True, help="Amino acid sequence")
    p_cod.add_argument("--seed", type=int, default=42,
                       help="Random seed (default: 42)")
    p_cod.add_argument("--n-candidates", type=int, default=50, dest="n_candidates",
                       help="Number of candidate sequences to evaluate (default: 50)")
    p_cod.add_argument("--no-linearfold", action="store_true", dest="no_linearfold",
                       help="Skip LinearFold structure prediction")
    p_cod.add_argument("--out", default=None, help="Write audit JSON to this path")

    # ── coverage ──
    p_cov = sub.add_parser("coverage",
                            help="Calculate HLA population coverage for allele set")
    p_cov.add_argument("--alleles", nargs="+", required=True,
                       help="HLA alleles (e.g. HLA-A*02:01 HLA-B*07:02)")
    p_cov.add_argument("--out", default=None, help="Write audit JSON to this path")

    # ── mhc2-predict ──
    p_mhc2 = sub.add_parser(
        "mhc2-predict",
        help="Predict MHC-II epitopes via IEDB API (online, free, AUC ~0.80)",
    )
    mhc2_src = p_mhc2.add_mutually_exclusive_group(required=True)
    mhc2_src.add_argument("--seq", default=None,
                          help="Protein sequence to scan")
    mhc2_src.add_argument("--peptides", nargs="+", default=None,
                          help="Specific peptides to predict (15-mer recommended)")
    p_mhc2.add_argument("--alleles", nargs="+", default=None,
                        help="HLA-DR alleles (default: 8-allele global DR panel)")
    p_mhc2.add_argument("--method", default="IEDB_recommended",
                        choices=["IEDB_recommended", "nn_align", "sturniolo", "smm_align"],
                        help="Prediction method (default: IEDB_recommended consensus)")
    p_mhc2.add_argument("--top-n", type=int, default=10, dest="top_n",
                        help="Top N hits per allele (default: 10)")
    p_mhc2.add_argument("--out", default=None, help="Write audit JSON to this path")

    # ── iedb-search ──
    p_iedb = sub.add_parser(
        "iedb-search",
        help="Search IEDB online for T cell epitopes (requires internet)",
    )
    iedb_src = p_iedb.add_mutually_exclusive_group(required=True)
    iedb_src.add_argument("--antigen", default=None,
                          help="Antigen name keyword (e.g. 'KRAS', 'MART-1', 'NY-ESO-1')")
    iedb_src.add_argument("--pathogen", default=None,
                          help="Pathogen name (e.g. 'Influenza', 'SARS-CoV-2', 'EBV')")
    p_iedb.add_argument("--hla", default=None,
                        help="Filter by HLA allele (e.g. HLA-A*02:01)")
    p_iedb.add_argument("--mhc-class", default=None, choices=["I", "II"],
                        dest="mhc_class",
                        help="Filter by MHC class (I or II)")
    p_iedb.add_argument("--max-results", type=int, default=30, dest="max_results",
                        help="Maximum results to return (default: 30)")
    p_iedb.add_argument("--out", default=None, help="Write audit JSON to this path")

    # ── prioritize ──
    p_pri = sub.add_parser(
        "prioritize",
        help=(
            "Three-layer epitope prioritisation: "
            "self-tolerance filter + expression weighting + population coverage optimisation"
        ),
    )
    p_pri.add_argument(
        "--scan-out", dest="scan_out", required=True,
        help="JSON audit file from a previous 'scan' run (or a JSON array of epitope records)",
    )
    p_pri.add_argument(
        "--gene", default="",
        help="Gene symbol for expression weighting (e.g. KRAS, TP53, EGFR)",
    )
    p_pri.add_argument(
        "--cancer-type", dest="cancer_type", default="global",
        help="TCGA cancer type code for expression lookup (e.g. LUAD, SKCM, COAD; default: global)",
    )
    p_pri.add_argument(
        "--wt-seq", dest="wt_seq", default="",
        help="Wild-type protein sequence (for DAI + tolerance checking in neoantigen mode)",
    )
    p_pri.add_argument(
        "--allele", default="HLA-A*02:01",
        help="HLA allele used during scan (for coverage calculation, default: HLA-A*02:01)",
    )
    p_pri.add_argument(
        "--n", type=int, default=10,
        help="Number of epitopes to select for vaccine construct (default: 10)",
    )
    p_pri.add_argument(
        "--target-pop", dest="target_pop", default="global",
        choices=["global", "european", "east_asian", "african", "south_asian"],
        help="Target population for coverage optimisation (default: global)",
    )
    p_pri.add_argument(
        "--min-coverage", dest="min_coverage", type=float, default=0.0,
        help="Stop coverage optimisation once this population fraction is reached (0=disabled)",
    )
    p_pri.add_argument(
        "--keep-failed", dest="keep_failed", action="store_true",
        help="Include tolerance-failed epitopes in output (for diagnostics)",
    )
    p_pri.add_argument("--out", default=None, help="Write audit JSON to this path")

    return ap


SUBCOMMAND_MAP = {
    "scan": cmd_scan,
    "neo-compare": cmd_neo_compare,
    "assemble": cmd_assemble,
    "codon-opt": cmd_codon_opt,
    "coverage": cmd_coverage,
    "mhc2-predict": cmd_mhc2_predict,
    "iedb-search": cmd_iedb_search,
    "prioritize": cmd_prioritize,
}


def main() -> None:
    parser = build_parser()
    args = parser.parse_args()

    fn = SUBCOMMAND_MAP.get(args.subcommand)
    if fn is None:
        parser.print_help()
        sys.exit(1)

    logger.info(f"run_vaccine_design v{CLI_VERSION} | subcommand={args.subcommand}")
    fn(args)


if __name__ == "__main__":
    main()
