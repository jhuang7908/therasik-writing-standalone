"""
rerun_cd3_v1810.py —  V1.8.10 （keep_framework_and_camelize ） 6  CD3 。
， API 。
"""
import sys, json, time
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

# Import the fixed pipeline functions
from api.routers.vh_to_vhh import (
    _generate_conversion_candidates,
    _apply_conversion_mutations,
    _apply_phase45_sdab_adapt,
    _compute_expressibility_verdict,
)

JOB_STORAGE = ROOT / ".job_storage"

SAMPLES = [
    {
        "job_id":       "cd3_v2v_sp34_murine_vh_blinatumomab",
        "name":         "SP34",
        "source_class": "murine_mab",
        "input_seq":    "DIKLQSGAELARPGASVKMSCKTSGYTFTRYTMHWVKQRPGQGLEWIGYINPSRGYTNYNQKFKDKATLTTDKSSSTAYMQLSSLTSEDSAVYYCARYYDDHYCLDYWGQGTTLTVSS",
    },
    {
        "job_id":       "cd3_v2v_teplizumab_vh_vl",
        "name":         "Teplizumab",
        "source_class": "humanized_mab",
        "input_seq":    "QVQLVQSGGGVVQPGRSLRLSCKASGYTFTRYTMHWVRQAPGKGLEWIGYINPSRGYTNYNQKVKDRFTISRDNSKNTAFLQMDSLRPEDTGVYFCARYYDDHYCLDYWGQGTPVTVSS",
    },
    {
        "job_id":       "cd3_v2v_okt3_humanized_scfv_actes",
        "name":         "OKT3",
        "source_class": "humanized_mab",
        "input_seq":    "QVQLVQSGAEVKKPGASVKVSCKASGYTFTRYTMHWVRQAPGQGLEWIGYINPSRGYTNYNQKFKDRVTMTRDTSTSTVYMELSSLRSEDTAVYYCARYYDDHYCLDYWGQGTLVTVSS",
    },
    {
        "job_id":       "cd3_v2v_otelixizumab_vh_vl",
        "name":         "Otelixizumab",
        "source_class": "humanized_mab",
        "input_seq":    "EVQLLESGGGLVQPGGSLRLSCAASGFTFSSFPMAWVRQAPGKGLEWVSTISTSGGRTYYRDSVKGRFTISRDNSKNTLYLQMNSLRAEDTAVYYCAKFRQYSGGFDYWGQGTLVTVSS",
    },
    {
        "job_id":       "cd3_v2v_foralumab_vh_vl",
        "name":         "Foralumab",
        "source_class": "human_mab",
        "input_seq":    "QVQLVESGGGVVQPGRSLRLSCAASGFKFSGYGMHWVRQAPGKGLEWVAVIWYDGSKKYYVDSVKGRFTISRDNSKNTLYLQMNSLRAEDTAVYYCARQMGYWHFDLWGRGTLVTVSS",
    },
    {
        "job_id":       "cd3_v2v_visilizumab_vh_vl",
        "name":         "Visilizumab",
        "source_class": "human_mab",
        "input_seq":    "QVQLVQSGAEVKKPGASVKVSCKASGYTFISYTMHWVRQAPGQGLEWMGYINPRSGYTHYNQKLKDKATLTADKSASTAYMELSSLRSEDTAVYYCARSAYYDYDGFAYWGQGTLVTVSS",
    },
]

from core.humanization.engine import _vhh_mini_cmc

for s in SAMPLES:
    t0 = time.time()
    name        = s["name"]
    source_cls  = s["source_class"]
    inp         = s["input_seq"]
    job_dir     = JOB_STORAGE / s["job_id"]

    print(f"\n=== {name} ({source_cls}) ===")

    # CDR length estimation (simple)
    # Use existing result.json for cdr lengths (don't re-run ANARCI here)
    old = json.loads((job_dir / "result.json").read_text())
    cdr3_len = old.get("cdr3_length") or 13
    cdr2_len = old.get("cdr2_length") or 10

    # [V1.8.10] Generate with enable_scaffold_graft=False (DEFAULT)
    candidates = _generate_conversion_candidates(
        vh_seq=inp,
        source_class=source_cls,
        cdr3_len=cdr3_len,
        cdr2_len=cdr2_len,
        top_n=3,
        enable_scaffold_graft=False,  # DEFAULT PATH C
    )

    if not candidates:
        print(f"  ERROR: no candidates generated")
        continue

    best = candidates[0]
    seq  = best.get("sequence") or inp
    strat = best.get("strategy")
    muts  = best.get("mutations_applied") or []
    canon = best.get("already_canonical") or []
    phase45_muts = best.get("phase45_mutations") or []

    print(f"  strategy        : {strat}")
    print(f"  mutations_applied: {muts}")
    print(f"  already_canonical: {canon}")
    print(f"  phase45_muts    : {phase45_muts}")
    print(f"  converted_seq   : {seq}")

    # Compute mini CMC
    cmc = _vhh_mini_cmc(seq)
    print(f"  pI={cmc.get('pI')}  GRAVY={cmc.get('GRAVY')}  Rg={cmc.get('cdr3_compactness')}")

    # AbNatiV
    an_delta = best.get("abnativ_delta")
    an_vh2   = best.get("abnativ_vh2")
    an_vhh2  = best.get("abnativ_vhh2")
    print(f"  AbNatiV: vh2={an_vh2} vhh2={an_vhh2} delta={an_delta}")

    # Update result.json with new fields
    old["converted_sequence"]    = seq
    old["selected_strategy"]     = strat
    old["selected_template_id"]  = best.get("template_id") or "parent_vh_framework"
    old["mutations_applied"]     = muts
    old["already_canonical"]     = canon
    old["phase45_mutations"]     = phase45_muts
    old["mini_cmc"]              = cmc
    old["candidates"]            = candidates
    old["algorithm_version"]     = "V1.8.10"

    out_path = job_dir / "result.json"
    out_path.write_text(json.dumps(old, indent=2, ensure_ascii=False), encoding="utf-8")
    print(f"  Saved -> {out_path.name}  ({time.time()-t0:.1f}s)")

print("\nAll done.")
