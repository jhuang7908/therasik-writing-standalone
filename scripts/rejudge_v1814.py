"""
Re-judge V1.8.13 outputs using V1.8.14 thresholds.
"""
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
V1813_DIR = ROOT / "projects" / "CD3_VH2VHH_Batch_20260515" / "v1813_reports"


def label_pi_v1813(pI):
    if pI is None: return "UNKNOWN"
    if pI <= 9.0:  return "PASS"
    if pI <= 9.5:  return "WARN"
    return "FAIL"


def label_pi_v1814(pI):
    if pI is None: return "UNKNOWN"
    if pI <= 9.4:  return "PASS"
    if pI <= 9.6:  return "WARN"
    return "FAIL"


def label_an_v1813(d):
    if d is None:  return "UNKNOWN"
    if d >= 0:     return "EXCELLENT"
    if d >= -0.12: return "PASS"
    if d >= -0.20: return "WARN"
    return "FAIL"


def label_an_v1814(d, ighv):
    """IGHV-family-aware. IGHV3 uses calibrated thresholds; IGHV1/4/unknown low-confidence."""
    if d is None:  return "UNKNOWN"
    if ighv == "IGHV3":
        if d >= 0:     return "EXCELLENT"
        if d >= -0.13: return "PASS"
        if d >= -0.20: return "WARN"
        return "FAIL"
    else:
        # Low-confidence track: only flag FAIL at strong VH signal (<-0.30)
        if d >= 0:     return "EXCELLENT (low-conf)"
        if d >= -0.13: return "PASS (low-conf)"
        if d >= -0.20: return "WARN (low-conf)"
        if d >= -0.30: return "WARN (low-conf strict)"
        return "FAIL (low-conf strict)"


def composite_v1813(pi_l, an_l):
    if pi_l == "FAIL" or an_l == "FAIL": return "FAIL"
    if pi_l == "WARN" or an_l == "WARN": return "WARN"
    if "EXCELLENT" in an_l: return "EXCELLENT"
    if pi_l == "PASS" and an_l == "PASS": return "PASS"
    return "UNKNOWN"


def composite_v1814(pi_l, an_l, d, pI):
    # Composite override: AbΔ EXCELLENT + pI ≤ 9.4 (PASS bound) → PASS regardless of pI WARN
    if "EXCELLENT" in an_l and pI is not None and pI <= 9.4:
        return "PASS (override: high AbNatiV)"
    # FAIL gates
    if pi_l == "FAIL" or "FAIL" in an_l:
        return "FAIL"
    # WARN gates
    if pi_l == "WARN" or "WARN" in an_l:
        return "WARN"
    if "EXCELLENT" in an_l: return "EXCELLENT"
    if pi_l == "PASS" and "PASS" in an_l: return "PASS"
    return "UNKNOWN"


def main():
    samples = ["SP34", "Teplizumab", "OKT3", "Visilizumab", "Otelixizumab", "Foralumab"]
    print(f"{'Sample':<14} {'IGHV':<5} {'pI':>5} {'AbΔ':>8}  "
          f"{'V1.8.13':<22}  →  {'V1.8.14':<35}")
    print("=" * 130)
    summary = []
    for name in samples:
        d = json.loads((V1813_DIR / f"{name}_v1813.json").read_text(encoding="utf-8"))
        ighv = d["ighv_family"]
        pI = d["final_metrics"]["pI"]
        adelta = d["final_abnativ"]["delta"]
        # V1.8.13 verdict
        pi_l_13 = label_pi_v1813(pI)
        an_l_13 = label_an_v1813(adelta)
        v13 = composite_v1813(pi_l_13, an_l_13)
        v13_text = f"pI={pi_l_13},Ab={an_l_13[:9]}→{v13}"
        # V1.8.14 verdict
        pi_l_14 = label_pi_v1814(pI)
        an_l_14 = label_an_v1814(adelta, ighv)
        v14 = composite_v1814(pi_l_14, an_l_14, adelta, pI)
        v14_text = f"pI={pi_l_14},Ab={an_l_14[:18]}→{v14}"
        print(f"{name:<14} {ighv:<5} {pI:>5.2f} {adelta:>+8.4f}  {v13_text:<22}  →  {v14_text:<35}")
        summary.append({
            "name": name, "ighv": ighv, "pI": pI, "abnativ_delta": adelta,
            "v1813_verdict": v13, "v1814_verdict": v14,
            "v1814_pI_label": pi_l_14, "v1814_an_label": an_l_14,
        })
    # save
    (V1813_DIR / "v1814_reverdict_summary.json").write_text(
        json.dumps(summary, indent=2, ensure_ascii=False), encoding="utf-8")
    print(f"\nSaved → {V1813_DIR / 'v1814_reverdict_summary.json'}")


if __name__ == "__main__":
    main()
