"""
Update evidence chain excerpts for 3 AI-corrected records so they reflect
the verified source data rather than the original AI-generated text.
"""
import csv, subprocess, sys, shutil

MASTER = r'data\ada_master_136_curated.csv'
KB_MASTER = r'data\immunogenicity_knowledge_base\master\ada_master_136_curated.csv'

with open(MASTER, encoding='utf-8') as f:
    reader     = csv.DictReader(f)
    fieldnames = list(reader.fieldnames)
    all_rows   = list(reader)

row_map = {r['antibody_name']: r for r in all_rows}

EXCERPTS = {
    "Olokizumab": (
        "## Olokizumab ADA Data Evidence Chain (PMID-Verified; AI Contamination Corrected)\n\n"
        "### Data Summary\n"
        "ADA incidence: **3.2% (Q4W dosing)** and **7.0% (Q2W dosing)** per Phase III trial "
        "(PMID 36109142, Fleischmann et al. 2022, Arthritis Rheumatol).\n\n"
        "### Source\n"
        "Fleischmann R, et al. 'Olokizumab, a Monoclonal Antibody against Interleukin-6, "
        "in Combination with Methotrexate in Patients with Rheumatoid Arthritis Who Are "
        "Incompletely Controlled by Methotrexate: Efficacy and Safety Results of a Phase III "
        "Randomised Controlled Trial.' Arthritis & Rheumatology. 2022;74(11). PMID 36109142.\n\n"
        "### Correction Note\n"
        "Original evidence chain was identified as AI-generated ('Claude response') with no "
        "primary source, citing 10–15% ADA. This value was incorrect. The PMID-verified "
        "Phase III data confirms: Q4W dose = 3.2%, Q2W dose = 7.0% ADA incidence."
    ),
    "Relatlimab": (
        "## Relatlimab ADA Data Evidence Chain (FDA PI Verified; AI Contamination Corrected)\n\n"
        "### Data Summary\n"
        "ADA incidence: **5.6% (16/286 patients)** treatment-emergent; nAb: **0.3% (1/286)**. "
        "Source: FDA Prescribing Information (Opdualag® label §6.2).\n\n"
        "### Source\n"
        "FDA Prescribing Information for OPDUALAG (relatlimab-rmbw and nivolumab) Injection. "
        "Section 6.2 Immunogenicity. FDA approval 2022. "
        "https://www.accessdata.fda.gov/drugsatfda_docs/label/2022/761306s000lbl.pdf\n\n"
        "### Correction Note\n"
        "Original evidence chain was identified as AI-generated ('Claude response') with no "
        "primary source, citing <2% ADA. This was incorrect. The FDA PI §6.2 confirms: "
        "5.6% (16/286) treatment-emergent ADA, nAb 0.3% (1/286)."
    ),
    "Mogamulizumab": (
        "## Mogamulizumab ADA Data Evidence Chain (FDA PI Verified; Value Corrected)\n\n"
        "### Data Summary\n"
        "ADA incidence: **14.1% (overall, all clinical trials)**. "
        "Note: 3.9% (10/258) was reported in the MAVORIC monotherapy cohort specifically. "
        "Source: FDA Prescribing Information (Poteligeo® label §12.6 / DailyMed).\n\n"
        "### Source\n"
        "FDA Prescribing Information for POTELIGEO (mogamulizumab-kpkc) Injection. "
        "Section 12.6 Immunogenicity. FDA approval 2018. "
        "https://dailymed.nlm.nih.gov/dailymed/drugInfo.cfm?setid=e53960ab-42a1-40d1-9c7d-eb013fe7f18f\n\n"
        "### Notes\n"
        "The overall 14.1% ADA rate is the pooled figure across all POTELIGEO clinical studies "
        "as reported in the FDA PI. The MAVORIC monotherapy trial reported a lower rate "
        "of 3.9% (10/258 patients) which is trial-specific."
    ),
}

changed = 0
for drug, new_excerpt in EXCERPTS.items():
    row = row_map.get(drug)
    if row:
        row['ada_evidence_chain_excerpt'] = new_excerpt
        changed += 1
        print(f"  Updated excerpt: {drug}")
    else:
        print(f"  ⚠ Not found: {drug}")

with open(MASTER, 'w', newline='', encoding='utf-8') as f:
    writer = csv.DictWriter(f, fieldnames=fieldnames, extrasaction='ignore')
    writer.writeheader()
    writer.writerows(all_rows)

# Sync to KB master
shutil.copy(MASTER, KB_MASTER)
print(f"\nUpdated {changed} excerpts. Synced to KB master.")

# Rebuild JSON
print("Rebuilding JSON...")
subprocess.run([sys.executable, 'scripts/_regen_json_only.py'], check=False)

# Copy to web sources
shutil.copy('docs/ada_db_data.json', 'insynbio-web-source/ada_db_data.json')
shutil.copy('docs/ada_db_data.json', 'therasik-web-source/ada_db_data.json')
print("Copied to web sources.")
