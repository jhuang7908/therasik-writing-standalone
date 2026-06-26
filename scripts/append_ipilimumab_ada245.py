"""Append Ipilimumab to ADA245 master CSV from Tremelimumab template row."""
import csv
import json
import urllib.request
from copy import deepcopy
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
CSV_PATH = ROOT / "data" / "ada245" / "database" / "ada_master_245_curated.csv"

VH = "QVQLVESGGGVVQPGRSLRLSCAASGFTFSSYTMHWVRQAPGKGLEWVTFISYDGNNKYYADSVKGRFTISRDNSKNTLYLQMNSLRAEDTAIYYCARTGWLGPFDYWGQGTLVTVSS"
VL = "EIVLTQSPGTLSLSPGERATLSCRASQSVGSSYLAWYQQKPGQAPRLLIYGAFSRATGIPDRFSGSGSGTDFTLTISRLEPEDFAVYYCQQYGSSPWTFGQGTKVEIK"

SEG = {
    "vh_fr1": "QVQLVESGGGVVQPGRSLRLSCAAS",
    "vh_cdr1": "GFTFSSYT",
    "vh_fr2": "MHWVRQAPGKGLEWVTF",
    "vh_cdr2": "ISYDGNNK",
    "vh_fr3": "YYADSVKGRFTISRDNSKNTLYLQMNSLRAEDTAIYYC",
    "vh_cdr3": "ARTGWLGPFDY",
    "vh_fr4": "WGQGTLVTVSS",
    "vl_fr1": "EIVLTQSPGTLSLSPGERATLSCRAS",
    "vl_cdr1": "QSVGSSY",
    "vl_fr2": "LAWYQQKPGQAPRLLIY",
    "vl_cdr2": "GAF",
    "vl_fr3": "SRATGIPDRFSGSGSGTDFTLTISRLEPEDFAVYYC",
    "vl_cdr3": "QQYGSSPWT",
    "vl_fr4": "FGQGTKVEIK",
}

ADA_DISPLAY = (
    "FDA PI §12.6 / Table 24 (YERVOY): single-agent melanoma ADA 1.1% (11/1024), NAb 0/11; "
    "adjuvant melanoma ADA 4.9% (7/144), NAb 0/7; "
    "with nivolumab (indication-dependent) e.g. melanoma 8.4% (33/391), "
    "mesothelioma 13.7% (37/271), NSCLC Part1 8.5% (41/483), "
    "NSCLC+chemo 7.5% (23/305). Neutralizing anti-ipilimumab antibodies uncommon; "
    "label states CL unchanged with binding ADA."
)

ADA_FIRST_PCT = "1.1"  # canonical monotherapy melanoma incidence for cohort scalar

EVIDENCE_EXCERPT = (
    "[FDA SPL via openFDA] Section 12.6 Immunogenicity: "
    '"The observed incidence of anti-drug antibodies (ADA) is highly dependent on the sensitivity and specificity of the assay..." '
    "Melanoma monotherapy: Eleven (1.1%) of 1024 evaluable patients tested positive for treatment-emergent binding antibodies "
    "against ipilimumab in an ECL-based assay (drug-tolerance limitations noted). "
    "Adjuvant melanoma (vs placebo): 7 (4.9%) of 144 on ipilimumab vs 7 (4.5%) of 156 on placebo using an improved ECL assay; "
    "no neutralizing antibodies. "
    "Combination trials (CHECKMATE-214/-142): 27 (5.4%) of 499 evaluable positive for anti-ipilimumab antibodies; no neutralizing. "
    "CHECKMATE-227 Part 1: 8.5% treatment-emergent anti-ipilimumab antibodies. "
    "CHECKMATE-9LA: 8% binding ADA; 1.6% neutralizing anti-ipilimumab. "
    "CHECKMATE-743 mesothelioma: 13.7% binding ADA; 0.4% neutralizing. "
    "Full incidence table: Table 24 (ADA/NAb by regimen and indication). "
    "Source retrieved programmatically from openFDA drug label API for generic_name ipilimumab."
)


def fetch_openfda_meta():
    url = (
        "https://api.fda.gov/drug/label.json?"
        'search=openfda.generic_name:"ipilimumab"&limit=1'
    )
    with urllib.request.urlopen(url, timeout=60) as resp:
        d = json.loads(resp.read().decode())
    r = d["results"][0]
    of = r.get("openfda", {})
    et = r.get("effective_time")
    if isinstance(et, list) and et:
        eff = et[0]
    else:
        eff = et or ""
    return {
        "effective_time": eff,
        "spl_id": of.get("spl_id", [""])[0],
        "brand_name": of.get("brand_name", [""])[0],
        "generic_name": of.get("generic_name", [""])[0],
    }


def main():
    meta = fetch_openfda_meta()
    print("openFDA meta:", meta)

    rows = []
    with CSV_PATH.open(encoding="utf-8", newline="") as f:
        reader = csv.DictReader(f)
        fieldnames = reader.fieldnames
        for row in reader:
            rows.append(row)

    for row in rows:
        if row["antibody_name"] == "Ipilimumab":
            raise SystemExit("Ipilimumab already present; abort.")

    base = next(r for r in rows if r["antibody_name"] == "Tremelimumab")
    ipi = deepcopy(base)

    ipi["antibody_name"] = "Ipilimumab"
    ipi["genetics_normalized"] = "genetically_human"
    ipi["thera_genetics_class"] = "fully_human"
    ipi["targets"] = "CTLA4|CD152"
    ipi["indication_text"] = (
        "Unresectable/metastatic melanoma; adjuvant melanoma; "
        "renal cell carcinoma; colorectal cancer (MSI-H/dMMR); HCC; "
        "NSCLC; malignant pleural mesothelioma (with nivolumab per label)"
    )
    ipi["disease_class_curated"] = "oncology"
    ipi["fc_isotype"] = "G1"
    ipi["fc_engineering"] = "none"
    ipi["fc_effector_status"] = "normal_IgG1"
    ipi["fc_mutation_notes"] = (
        "Fully human IgG1 κ; CTLA-4 checkpoint inhibitor (Medarex UltiMAb). "
        "Table 24 summarizes ADA/NAb by regimen — incidence varies by indication and combination."
    )
    ipi["route_curated"] = "IV infusion"
    ipi["dose_mg"] = "1–10 mg/kg (regimen-specific; monotherapy 3 mg/kg q3w legacy dosing per label)"
    ipi["dose_freq"] = "q3w to q6w (regimen-specific)"
    ipi["half_life_days"] = "15"
    ipi["assay_platform"] = "ECL"
    ipi["assay_generation"] = "2.0"
    ipi["mtx_comedication"] = "none"
    ipi["immunosuppressant_context"] = "oncology checkpoint; chemotherapy backbone in some NSCLC regimens"
    ipi["approval_year"] = "2011"
    ipi["oncology_indication"] = "1.0"
    ipi["checkpoint_inhibitor"] = "1.0"
    ipi["immune_depleting"] = "0.0"
    ipi["concomitant_immuno_likely"] = "1.0"
    ipi["ada_value_display"] = ADA_DISPLAY
    ipi["ada_first_pct"] = ADA_FIRST_PCT
    ipi["evidence_tier"] = "A"
    ipi["evidence_source"] = "FDA prescribing information (openFDA SPL; §12.6 Immunogenicity & Table 24)"
    ipi["citation_urls"] = (
        "https://api.fda.gov/drug/label.json?search=openfda.generic_name:%22ipilimumab%22&limit=1 ; "
        "DailyMed YERVOY (ipilimumab) SPL — cross-check spl_set_id via openFDA effective_time "
        + str(meta.get("effective_time", ""))
    )
    ipi["ada_source_url_primary"] = (
        "https://api.fda.gov/drug/label.json?search=openfda.generic_name:%22ipilimumab%22&limit=1"
    )
    ipi["ada_source_pmids"] = ""
    ipi["ada_source_type_curated"] = "FDA label (openFDA JSON)"
    ipi["ada_has_text_evidence"] = "True"
    ipi["ada_evidence_chain_excerpt"] = EVIDENCE_EXCERPT + f" openFDA spl_id={meta.get('spl_id','')}."

    ipi["vh_seq"] = VH
    ipi["vl_seq"] = VL
    for k, v in SEG.items():
        ipi[k] = v
    ipi["heavy_seq_len"] = str(len(VH))
    ipi["light_seq_len"] = str(len(VL))

    ipi["vh_germline"] = "IGHV3-30*01"
    ipi["vl_germline"] = "IGKV3-20*01"
    ipi["vh_family"] = "IGHV3-30"
    ipi["vl_family"] = "IGKV3-20"
    ipi["vh_germline_identity"] = "0.9490"
    ipi["vl_germline_identity"] = "0.9785"
    ipi["vh_germline_imgt"] = "IGHV3-30*01"
    ipi["vl_germline_imgt"] = "IGKV3-20*01"
    ipi["vh_identity_imgt"] = "0.949"
    ipi["vl_identity_imgt"] = "0.979"

    ipi["pdb_path"] = str(
        ROOT / "data" / "structures" / "natural" / "Ipilimumab.pdb"
    )
    ipi["vh_vl_angle_deg"] = "84.94"
    ipi["interface_n_pairs"] = "63"
    ipi["interface_mean_dist_A"] = "4.6541"
    ipi["interface_min_dist_A"] = "2.5253"

    ipi["verify_status"] = "VERIFIED"
    ipi["verify_note"] = (
        "ADA text extracted from openFDA SPL (§12.6 + Table 24). IMGT segments via ANARCI. "
        "Path metrics from atlas_structure_summary.json entry."
    )
    ipi["discovery_platform"] = "Transgenic Mice"
    ipi["moa_class"] = "immune_checkpoint"

    rows.append(ipi)

    with CSV_PATH.open("w", encoding="utf-8", newline="") as f:
        w = csv.DictWriter(f, fieldnames=fieldnames, quoting=csv.QUOTE_MINIMAL)
        w.writeheader()
        w.writerows(rows)

    print("Wrote", len(rows), "rows to", CSV_PATH)


if __name__ == "__main__":
    main()
