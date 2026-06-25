"""
Batch convert all 8 MD files in immunogenicity_knowledge_base to PDF.
Each PDF is written next to its MD source file.
"""
import subprocess
import sys
import os

BASE = "Antibody_Engineer_Suite/data/immunogenicity_knowledge_base"
SCRIPT = "Antibody_Engineer_Suite/scripts/md_to_pdf.py"

MD_FILES = [
    f"{BASE}/INDEX.md",
    f"{BASE}/ada_evidence/ada_evidence_consistency_final_report.md",
    f"{BASE}/ada_evidence/confirmed_ada.md",
    f"{BASE}/reports/ADA_Master_136_Evidence_Report.md",
    f"{BASE}/reports/ADA_Review_Discussion_Notes.md",
    f"{BASE}/reports/ADA_V2_Prediction_Results.md",
    f"{BASE}/reports/clinical_ada_full_evidence_report.md",
    f"{BASE}/reports/clinical_ada_engineered_evidence_report.md",
    f"{BASE}/reports/ADA_Clinical_Analysis_138_Report.md",
]

ok = 0
fail = 0
for md in MD_FILES:
    pdf = md.replace(".md", ".pdf")
    print(f"\n→ Converting: {os.path.basename(md)}")
    result = subprocess.run(
        [sys.executable, SCRIPT, md, pdf],
        capture_output=True, text=True
    )
    if result.returncode == 0:
        print(f"  ✅ OK → {pdf}")
        ok += 1
    else:
        print(f"  ❌ FAILED\n  STDERR: {result.stderr[:300]}")
        fail += 1

print(f"\n{'='*50}")
print(f"Done: {ok} OK, {fail} FAILED")
