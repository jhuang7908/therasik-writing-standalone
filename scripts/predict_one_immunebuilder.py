#!/usr/bin/env python3
"""
One-shot Fv prediction for ImmuneBuilder (ABodyBuilder2).
Used by predict_igg_like_75_immunebuilder.py to run each arm in a subprocess
and avoid WinError 32 (file in use) on Windows.

Usage:
  python scripts/predict_one_immunebuilder.py --json <path_to_payload.json>

Payload JSON: { "out_path": "<.pdb path>", "H": "<VH sequence>", "L": "<VL sequence>" }
"""

import os
import sys
import site
import json
from pathlib import Path

# anarci_compat first so ImmuneBuilder uses ARANCII (no HMMER required)
_script_dir = Path(__file__).resolve().parent
_repo_root = _script_dir.parent
_anarci_compat = _repo_root / "reports" / "anarci_compat"
if _anarci_compat.exists():
    sys.path.insert(0, str(_anarci_compat))
# Ensure site-packages for ImmuneBuilder
_sp = [p for p in site.getsitepackages() if "site-packages" in p.lower()]
if _sp:
    _target = os.path.normpath(os.path.abspath(_sp[0]))
    if _target not in sys.path:
        sys.path.append(_target)
    sys.path.append(str(_repo_root))

def main():
    import argparse
    ap = argparse.ArgumentParser()
    ap.add_argument("--json", required=True, help="Path to payload JSON")
    args = ap.parse_args()
    with open(args.json, encoding="utf-8") as f:
        payload = json.load(f)
    out_path = Path(payload["out_path"])
    vh = payload.get("H", "")
    vl = payload.get("L", "")
    model_type = payload.get("model_type", "abody")
    # Use a temp dir unique to this output so no cross-process reuse
    _tmp_dir = out_path.parent / "_tmp" / (out_path.stem + "_run")
    _tmp_dir.mkdir(parents=True, exist_ok=True)
    os.environ["TEMP"] = os.environ["TMP"] = str(_tmp_dir)

    if model_type == "nanobody":
        from ImmuneBuilder import NanoBodyBuilder2
        predictor = NanoBodyBuilder2()
        antibody = predictor.predict({"H": vh})
    else:
        from ImmuneBuilder import ABodyBuilder2
        predictor = ABodyBuilder2()
        antibody = predictor.predict({"H": vh, "L": vl})
        
    antibody.save_single_unrefined(str(out_path))
    print(f"Saved {out_path}", flush=True)

if __name__ == "__main__":
    main()
