#!/usr/bin/env python3
"""
 23  3-arm  Fab  IgFold 。

 Fab：Arm1 = heavy_fab_1 + light_fab，Arm2 = heavy_fab_2 + light_fab。
: data/design_rules/igg_like_23_three_arm_igfold/<antibody_id>_Arm1.pdb, <antibody_id>_Arm2.pdb

: pip install igfold。 PyTorch 2.6+  weights_only，； transformers.Trie ， transformers（ 4.30） IgFold 。
Usage:
  python scripts/run_igfold_23_three_arm_fab.py              #  23×2
  python scripts/run_igfold_23_three_arm_fab.py --limit 2   #  2 
  python scripts/run_igfold_23_three_arm_fab.py --dry-run   # 
"""
# PyTorch 2.6+  weights_only=True，IgFold  ckpt  weights_only=False 
import torch
_orig_torch_load = torch.load
def _torch_load_wrapper(*args, **kwargs):
    kwargs.setdefault("weights_only", False)
    return _orig_torch_load(*args, **kwargs)
torch.load = _torch_load_wrapper

#  transformers  tokenizer ，IgFold  ckpt ，
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

#  transformers  all_tied_weights_keys，AntiBERTy  _tied_weights_keys，
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

# abnumber.Chain  use_anarcii=False（ anarci ）， use_anarcii=True  anarcii。
#  anarcii，patch Chain.__init__  use_anarcii=True， anarci 。
def _patch_abnumber_use_anarcii():
    try:
        from abnumber import chain as _ch
        from abnumber.common import _anarci_align
        _orig_init = _ch.Chain.__init__
        def _patched_init(self, sequence, scheme, cdr_definition=None, name=None,
                          assign_germline=False, allowed_species=None,
                          use_anarcii=True,   # ← default changed to True
                          anarcii_args=None, **kwargs):
            return _orig_init(self, sequence, scheme, cdr_definition=cdr_definition,
                              name=name, assign_germline=assign_germline,
                              allowed_species=allowed_species, use_anarcii=use_anarcii,
                              anarcii_args=anarcii_args, **kwargs)
        _ch.Chain.__init__ = _patched_init
    except Exception:
        pass
_patch_abnumber_use_anarcii()

# IgFold  output_attentions=True； transformers  sdpa ， attentions 、stack 。 from_pretrained  attn_implementation="eager"。
def _patch_antiberty_eager_attention():
    try:
        from antiberty import AntiBERTy
        _orig_fp = AntiBERTy.from_pretrained.__func__  # unwrap classmethod
        def _from_pretrained_eager(cls, path_or_repo_id, *args, **kwargs):
            kwargs.setdefault("attn_implementation", "eager")
            return _orig_fp(cls, path_or_repo_id, *args, **kwargs)
        AntiBERTy.from_pretrained = classmethod(_from_pretrained_eager)
    except Exception:
        pass
_patch_antiberty_eager_attention()

import argparse
import json
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent
DATA_DIR = PROJECT_ROOT / "data" / "design_rules"
FAB_JSON = DATA_DIR / "igg_like_23_three_arm_fab.json"
OUT_DIR = DATA_DIR / "igg_like_23_three_arm_igfold"
CH1_LEN, CL_LEN = 98, 107


def main():
    ap = argparse.ArgumentParser(description="IgFold modeling for 23 3-arm Fab sequences")
    ap.add_argument("--limit", type=int, default=0, help="Max number of antibodies to run (0 = all)")
    ap.add_argument("--dry-run", action="store_true", help="Only print planned runs, do not call IgFold")
    ap.add_argument("--no-refine", action="store_true", help="Disable OpenMM refinement (faster, less accurate)")
    ap.add_argument("--v-only", action="store_true", help="Use V region only (strip CH1/CL); IgFold  Fab ， V ")
    args = ap.parse_args()

    if not FAB_JSON.exists():
        raise FileNotFoundError(f"Not found: {FAB_JSON}")

    with open(FAB_JSON, encoding="utf-8") as f:
        fab = json.load(f)

    records = [r for r in fab.get("per_antibody", []) if not r.get("error")]
    if args.limit:
        records = records[: args.limit]
    print(f"Planned: {len(records)} antibodies × 2 arms = {len(records) * 2} IgFold runs")

    if args.dry_run:
        for r in records:
            print(f"  {r['antibody_id']}: Arm1, Arm2")
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
    for i, rec in enumerate(records):
        aid = rec["antibody_id"]
        h1 = rec.get("heavy_fab_1") or ""
        h2 = rec.get("heavy_fab_2") or ""
        light = rec.get("light_fab") or ""
        if not h1 or not h2 or not light:
            print(f"[{i+1}/{len(records)}] {aid}: skip (missing chain)")
            continue
        if v_only:
            if len(h1) > CH1_LEN and len(h2) > CH1_LEN and len(light) > CL_LEN:
                h1, h2 = h1[:-CH1_LEN], h2[:-CH1_LEN]
                light = light[:-CL_LEN]
            else:
                print(f"[{i+1}/{len(records)}] {aid}: skip (Fab too short for v_only)")
                continue
        suffix = "_vonly" if v_only else ""
        for arm_name, heavy in [("Arm1", h1), ("Arm2", h2)]:
            out_pdb = OUT_DIR / f"{aid}_{arm_name}{suffix}.pdb"
            if out_pdb.exists():
                print(f"[{i+1}/{len(records)}] {aid} {arm_name}: skip (exists)")
                continue
            #  FASTA， fasta_file  tokenizer 
            fasta_path = out_pdb.with_suffix(".fasta")
            with open(fasta_path, "w", encoding="utf-8") as f:
                f.write(f">H\n{heavy}\n>L\n{light}\n")
            print(f"[{i+1}/{len(records)}] {aid} {arm_name}: predicting...")
            try:
                runner.fold(
                    str(out_pdb),
                    fasta_file=str(fasta_path),
                    do_refine=do_refine,
                    use_openmm=use_openmm,
                )
                print(f"  -> {out_pdb}")
                # Remove temporary FASTA to avoid clutter (optional: keep for debugging)
                if fasta_path.exists():
                    fasta_path.unlink(missing_ok=True)
            except Exception as e:
                import traceback
                print(f"  ERROR: {e}")
                traceback.print_exc()

    print(f"Done. Output dir: {OUT_DIR}")


if __name__ == "__main__":
    main()
