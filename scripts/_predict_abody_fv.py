"""
ABodyBuilder2 VH+VL Fv predictor.
Writes ensemble-averaged structure PDB (uses .save() for B-factor RMSD).
"""
import os, sys, json, argparse, site
os.environ["KMP_DUPLICATE_LIB_OK"] = "TRUE"

from pathlib import Path
_repo_root = Path(__file__).resolve().parent.parent
_anarci_compat = _repo_root / "reports" / "anarci_compat"
if _anarci_compat.exists():
    sys.path.insert(0, str(_anarci_compat))
_sp = [p for p in site.getsitepackages() if "site-packages" in p.lower()]
if _sp:
    sys.path.append(os.path.normpath(os.path.abspath(_sp[0])))
    sys.path.append(str(_repo_root))


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--json", required=True)
    args = ap.parse_args()
    payload = json.loads(Path(args.json).read_text(encoding="utf-8"))
    out_path = Path(payload["out_path"])
    vh = payload["H"]
    vl = payload["L"]

    _tmp_dir = out_path.parent / "_tmp" / (out_path.stem + "_run")
    _tmp_dir.mkdir(parents=True, exist_ok=True)
    os.environ["TEMP"] = os.environ["TMP"] = str(_tmp_dir)

    from ImmuneBuilder import ABodyBuilder2
    predictor = ABodyBuilder2()
    antibody = predictor.predict({"H": vh, "L": vl})
    antibody.save(str(out_path))
    print(f"Saved {out_path}")


if __name__ == "__main__":
    main()
