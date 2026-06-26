"""Targeted retest of abiprubart (F1) + briakinumab (F3) after fixes.

Only re-runs the two failing demos from the full smoke test, skipping the slow
ones, to validate that:
  - abiprubart stability variant no longer raises agg_motifs.
  - briakinumab hydrophobic now reports CDR-driven advisory and emits 0 FR runs
    (so the variant pipeline can't destabilise FR3 by applying L/A/I→S/T).
"""
from __future__ import annotations
import json
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from core.cmc.igg_cmc_pipeline import run_igg_cmc_pipeline  # noqa: E402

DEMOS = {
    "abiprubart-engineered": {
        "vh": "QVQLVQSGAEVKKPGASVKVSCKASGYTFTNYWMHWVRQAPGQRLEWIGYINPSNDYTKYNQKFKDRATLTADKSANTAYMELSSLRSEDTAVYYCARQGFPYWGQGTLVTVSS",
        "vl": "EIVLTQSPATLSLSPGERATLSCSASSSVSYMHWYQQKPGQAPRRWIYDTSKLASGVPARFSGSGSGTDYTLTISSLEPEDFAVYYCHQLSSDPFTFGGGTKVEIK",
        "antibody_type": "humanized",
    },
    "briakinumab-phage": {
        "vh": "QVQLVESGGGVVQPGRSLRLSCAASGFTFSSYGMHWVRQAPGKGLEWVAFIRYDGSNKYYADSVKGRFTISRDNSKNTLYLQMNSLRAEDTAVYYCKTHGSHDNWGQGTMVTVSS",
        "vl": "QSVLTQPPSVSGAPGQRVTISCSGSRSNIGSNTVKWYQQLPGTAPKLLIYYNDQRPSGVPDRFSGSKSGTSASLAITGLQAEDEADYYCQSYDRYTHPALLFGTGTKVTVL",
        "antibody_type": "phage_display",
    },
}

OUT = Path("out/smoke") / f"cmc_targeted_retest_{time.strftime('%Y%m%d_%H%M%S')}"
OUT.mkdir(parents=True, exist_ok=True)

results = {}
for name, payload in DEMOS.items():
    print(f"\n[{name}] running baseline + Smart-CMC...")
    t0 = time.time()
    out = run_igg_cmc_pipeline(
        vh_sequence=payload["vh"], vl_sequence=payload["vl"],
        antibody_type=payload["antibody_type"],
        project_name=name,
        out_dir=OUT / name,
        run_structure=False,
        smart_cmc=True,
    )
    # Dump full FR suggestions for inspection
    (OUT / f"{name}_fr_suggestions.json").write_text(
        json.dumps((out or {}).get("regular_ab_developability", {}).get("fr_modification_suggestions", []), indent=2)
    )
    elapsed = time.time() - t0
    rb = (out or {}).get("regular_ab_developability", {})
    suggestions = rb.get("fr_modification_suggestions", []) or []
    print(f"  done in {elapsed:.1f}s · {len(suggestions)} FR suggestion target(s)")
    for s in suggestions:
        sc = s.get("sequence_candidates") or {}
        print(f"    target = {s.get('target')!r}")
        if sc.get("patch_is_cdr_driven"):
            print(f"      [F3] patch_is_cdr_driven = True · {sc.get('patch_location')}")
        if sc.get("safe_zone_stop"):
            print(f"      [F2] safe_zone_stop = {sc.get('safe_zone_stop')}")
        runs = sc.get("fr_hydrophobic_runs", [])
        inst = sc.get("fr_instability_sites", [])
        pos = sc.get("fr_positive_charge_sites", [])
        neg = sc.get("fr_negative_charge_sites", [])
        print(f"      runs={len(runs)} · inst={len(inst)} · pos_charge={len(pos)} · neg_charge={len(neg)}")
        # Print instability mutations
        for ent in inst:
            print(f"        instab: {ent.get('chain')} {ent.get('index_1')} {ent.get('from_aa')}→{ent.get('to_aa_hint')} ({ent.get('motif')})")
    results[name] = {
        "elapsed_s": elapsed,
        "fr_targets": [s.get("target") for s in suggestions],
        "fr_suggestion_count": len(suggestions),
        "rb_summary": {k: v for k, v in rb.items() if k in ("developability_index", "overall_status", "n_fail", "n_warn")},
    }

(OUT / "summary.json").write_text(json.dumps(results, indent=2))
print(f"\n✓ Summary: {OUT / 'summary.json'}")
