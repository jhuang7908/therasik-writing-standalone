#!/usr/bin/env python3
"""
 50  4-arm  Fab  IgFold 。

：CrossMab  2  arm（Arm1, Arm2_cross）， CrossMab  4  arm（H1L1, H1L2, H2L1, H2L2）。
 arm  heavy_fab + light_fab ， PDB。
: data/design_rules/igg_like_50_four_arm_igfold/<antibody_id>_<arm_id>.pdb（ _vonly.pdb）

/： run_igfold_23_three_arm_fab.py （torch/transformers/abnumber/antiberty ）。

Usage:
  python scripts/run_igfold_50_four_arm_fab.py              #  50（ 7*2+43*4=186 ）
  python scripts/run_igfold_50_four_arm_fab.py --limit 2    #  2 
  python scripts/run_igfold_50_four_arm_fab.py --dry-run
  python scripts/run_igfold_50_four_arm_fab.py --v-only --no-refine
"""
#  23 （IgFold ）
import torch
_orig_torch_load = torch.load
def _torch_load_wrapper(*args, **kwargs):
    kwargs.setdefault("weights_only", False)
    return _orig_torch_load(*args, **kwargs)
torch.load = _torch_load_wrapper

def _patch_transformers_for_igfold():
    def _stub(name):
        class _C:
            pass
        _C.__name__ = name
        return _C
    try:
        import transformers.tokenization_utils_sentencepiece as _m1
        if not hasattr(_m1, "Trie"):
            _m1.Trie = _stub("Trie")
    except Exception:
        pass
    try:
        import transformers.models.bert.tokenization_bert as _m2
        if not hasattr(_m2, "BasicTokenizer"):
            _m2.BasicTokenizer = _stub("BasicTokenizer")
        if not hasattr(_m2, "WordpieceTokenizer"):
            _m2.WordpieceTokenizer = _stub("WordpieceTokenizer")
    except Exception:
        pass
_patch_transformers_for_igfold()

def _patch_transformers_tied_weights():
    try:
        import transformers.modeling_utils as _mu
        _orig_finalize = getattr(_mu.PreTrainedModel, "_finalize_model_loading", None)
        if _orig_finalize is None:
            return
        def _patched_finalize(self, load_config, loading_info=None):
            if not hasattr(self, "all_tied_weights_keys") and hasattr(self, "_tied_weights_keys"):
                self.all_tied_weights_keys = getattr(self, "_tied_weights_keys") or {}
            return _orig_finalize(self, load_config, loading_info)
        _mu.PreTrainedModel._finalize_model_loading = _patched_finalize
    except Exception:
        pass
_patch_transformers_tied_weights()

def _patch_abnumber_use_anarcii():
    try:
        from abnumber import chain as _ch
        _orig_init = _ch.Chain.__init__
        def _patched_init(self, sequence, scheme, cdr_definition=None, name=None,
                          assign_germline=False, allowed_species=None,
                          use_anarcii=True, anarcii_args=None, **kwargs):
            return _orig_init(self, sequence, scheme, cdr_definition=cdr_definition,
                              name=name, assign_germline=assign_germline,
                              allowed_species=allowed_species, use_anarcii=use_anarcii,
                              anarcii_args=anarcii_args, **kwargs)
        _ch.Chain.__init__ = _patched_init
    except Exception:
        pass
_patch_abnumber_use_anarcii()

def _patch_antiberty_eager_attention():
    try:
        from antiberty import AntiBERTy
        _orig_fp = AntiBERTy.from_pretrained.__func__
        def _from_pretrained_eager(cls, path_or_repo_id, *args, **kwargs):
            kwargs.setdefault("attn_implementation", "eager")
            return _orig_fp(cls, path_or_repo_id, *args, **kwargs)
        AntiBERTy.from_pretrained = classmethod(_from_pretrained_eager)
    except Exception:
        pass
_patch_antiberty_eager_attention()

import argparse
import json
import re
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent
DATA_DIR = PROJECT_ROOT / "data" / "design_rules"
FAB_JSON = DATA_DIR / "igg_like_50_four_arm_fab.json"
OUT_DIR = DATA_DIR / "igg_like_50_four_arm_igfold"
CH1_LEN, CL_LEN = 98, 107


def _sanitize_arm_id(arm_id: str) -> str:
    return re.sub(r"[\\/*?:\"<>|]", "_", arm_id)[:32]


def main():
    ap = argparse.ArgumentParser(description="IgFold modeling for 50 four-arm Fab sequences")
    ap.add_argument("--limit", type=int, default=0, help="Max number of antibodies (0 = all)")
    ap.add_argument("--dry-run", action="store_true", help="Only print planned runs")
    ap.add_argument("--no-refine", action="store_true", help="Disable OpenMM refinement")
    ap.add_argument("--v-only", action="store_true", help="Use V region only (strip CH1/CL)")
    args = ap.parse_args()

    if not FAB_JSON.exists():
        raise FileNotFoundError(f"Not found: {FAB_JSON}")

    with open(FAB_JSON, encoding="utf-8") as f:
        fab = json.load(f)

    records = [r for r in fab.get("per_antibody", []) if not r.get("error")]
    if args.limit:
        records = records[: args.limit]

    total_arms = sum(len(r.get("arms") or []) for r in records)
    print(f"Planned: {len(records)} antibodies, {total_arms} arms (IgFold runs)")

    if args.dry_run:
        for r in records:
            arms = r.get("arms") or []
            names = [a.get("arm_id", "?") for a in arms]
            print(f"  {r['antibody_id']}: {names}")
        return

    try:
        from igfold import IgFoldRunner
    except ImportError:
        raise ImportError("IgFold required: pip install igfold") from None

    OUT_DIR.mkdir(parents=True, exist_ok=True)
    runner = IgFoldRunner()
    do_refine = not args.no_refine
    use_openmm = do_refine
    v_only = getattr(args, "v_only", False)
    if v_only:
        print("Using V region only (stripping CH1/CL) for IgFold input.")

    run_idx = 0
    for i, rec in enumerate(records):
        aid = rec["antibody_id"]
        arms = rec.get("arms") or []
        for arm in arms:
            arm_id = arm.get("arm_id") or "arm"
            safe_arm = _sanitize_arm_id(arm_id)
            heavy = (arm.get("heavy_fab") or "").strip()
            light = (arm.get("light_fab") or "").strip()
            if not heavy or not light:
                print(f"[{run_idx+1}/{total_arms}] {aid} {arm_id}: skip (missing chain)")
                run_idx += 1
                continue
            if v_only:
                if len(heavy) > CH1_LEN and len(light) > CL_LEN:
                    heavy = heavy[:-CH1_LEN]
                    light = light[:-CL_LEN]
                else:
                    print(f"[{run_idx+1}/{total_arms}] {aid} {arm_id}: skip (Fab too short for v_only)")
                    run_idx += 1
                    continue
            suffix = "_vonly" if v_only else ""
            out_pdb = OUT_DIR / f"{aid}_{safe_arm}{suffix}.pdb"
            if out_pdb.exists():
                print(f"[{run_idx+1}/{total_arms}] {aid} {arm_id}: skip (exists)")
                run_idx += 1
                continue
            fasta_path = out_pdb.with_suffix(".fasta")
            with open(fasta_path, "w", encoding="utf-8") as f:
                f.write(f">H\n{heavy}\n>L\n{light}\n")
            print(f"[{run_idx+1}/{total_arms}] {aid} {arm_id}: predicting...")
            try:
                runner.fold(
                    str(out_pdb),
                    fasta_file=str(fasta_path),
                    do_refine=do_refine,
                    use_openmm=use_openmm,
                )
                print(f"  -> {out_pdb.name}")
                if fasta_path.exists():
                    fasta_path.unlink(missing_ok=True)
            except Exception as e:
                import traceback
                print(f"  ERROR: {e}")
                traceback.print_exc()
            run_idx += 1

    print(f"Done. Output dir: {OUT_DIR}")


if __name__ == "__main__":
    main()
