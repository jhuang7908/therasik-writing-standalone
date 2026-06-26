"""
Inject V1.8.14 verdict overlay into existing V1.8.13 HTML reports.
"""
import json
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
V1813_DIR = ROOT / "projects" / "CD3_VH2VHH_Batch_20260515" / "v1813_reports"

# Load V1.8.14 reverdict
reverdict = {r["name"]: r for r in json.loads(
    (V1813_DIR / "v1814_reverdict_summary.json").read_text(encoding="utf-8"))}


def make_v1814_panel(name: str) -> str:
    r = reverdict.get(name)
    if not r:
        return ""
    v14_color = "#27ae60" if "PASS" in r["v1814_verdict"] or "EXCELLENT" in r["v1814_verdict"] else \
                "#e74c3c" if "FAIL" in r["v1814_verdict"] else "#f39c12"
    v13_color = "#27ae60" if r["v1813_verdict"] in ("PASS", "EXCELLENT") else \
                "#e74c3c" if r["v1813_verdict"] == "FAIL" else "#f39c12"
    lowconf_note = ""
    if "lowconf" in r["v1814_an_label"]:
        lowconf_note = '<div style="margin-top:8px;font-size:11px;color:#999"><b>Note:</b> non-IGHV3 input — AbNatiV verdict carries low_confidence label due to absent positive training data; experimental validation required.</div>'

    return f"""
<div class="section" style="background:#fffaf0;border-left:5px solid #d4a017">
  <h2 style="color:#a06800">V1.8.14 Verdict Update (cohort-recalibrated thresholds)</h2>
  <table style="margin-bottom:8px">
    <tr><th>Threshold version</th><th>pI label</th><th>AbNatiV label</th><th>Composite verdict</th></tr>
    <tr>
      <td><b>V1.8.13</b> (legacy)</td>
      <td>{r['v1814_pI_label']}</td>
      <td>—</td>
      <td><span style="color:{v13_color};font-weight:700">{r['v1813_verdict']}</span></td>
    </tr>
    <tr style="background:#fff5e0">
      <td><b>V1.8.14</b> (current)</td>
      <td>{r['v1814_pI_label']}</td>
      <td>{r['v1814_an_label']}</td>
      <td><span style="color:{v14_color};font-weight:700">{r['v1814_verdict']}</span></td>
    </tr>
  </table>
  <p style="font-size:12px;color:#666;margin:0">
    <b>V1.8.14 thresholds:</b> pI PASS ≤ 9.4 (was ≤9.0); WARN ≤9.6; FAIL >9.6 — recalibrated to cover marketed VHHs Caplacizumab(9.07), Envafolimab(9.03), Gefurulimab(9.17), Tarperprumig(9.36).
    AbNatiV Δ IGHV3 PASS ≥ -0.13 (was -0.12); non-IGHV3 uses low-confidence track (FAIL only when Δ &lt; -0.30).
    Recalibration verified on n=160 cohort: Clinical_VHH PASS rate 69.2% → 89.7%.
  </p>
  {lowconf_note}
</div>"""


def main():
    n_updated = 0
    for name in reverdict.keys():
        html_path = V1813_DIR / f"{name}_v1813.html"
        if not html_path.exists():
            print(f"  [SKIP] {name}: HTML not found")
            continue
        html = html_path.read_text(encoding="utf-8")
        if "V1.8.14 Verdict Update" in html:
            print(f"  [SKIP] {name}: V1.8.14 panel already injected")
            continue
        # Inject before <!-- METRICS COMPARISON --> section
        panel = make_v1814_panel(name)
        new_html = html.replace(
            "<!-- METRICS COMPARISON -->",
            f"<!-- V1.8.14 OVERLAY -->\n{panel}\n\n<!-- METRICS COMPARISON -->",
            1
        )
        html_path.write_text(new_html, encoding="utf-8")
        print(f"  [OK] Injected V1.8.14 panel → {html_path.name}")
        n_updated += 1
    print(f"\nUpdated {n_updated} reports.")


if __name__ == "__main__":
    main()
