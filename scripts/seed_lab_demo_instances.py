#!/usr/bin/env python3
from __future__ import annotations

import json
from datetime import datetime, timedelta, timezone

import requests

base = "https://write.insynbio.com"


def post(path: str, payload: dict):
    r = requests.post(base + path, json=payload, timeout=60)
    try:
        d = r.json()
    except Exception:
        d = {"raw": r.text}
    return r.status_code, d


def main():
    out: dict[str, object] = {"created": {}}

    sop_ids: list[str] = []
    sops = [
        {
            "title": "VHH Purification by IMAC and SEC Polishing",
            "sections": {
                "Purpose & Scope": (
                    "Purify His-tagged VHH (single-domain antibody) from clarified E. coli "
                    "periplasmic extract or culture supernatant to >95% monomer purity for "
                    "downstream binding and developability assays. Applies to research-grade "
                    "lots up to 50 mL feed volume."
                ),
                "Materials & Equipment": (
                    "ÄKTA pure FPLC; 1 mL HisTrap HP column; HiLoad 16/600 Superdex 75 pg; "
                    "Binding buffer (20 mM phosphate, 500 mM NaCl, 20 mM imidazole, pH 7.4); "
                    "Elution buffer (same + 500 mM imidazole); SEC buffer (PBS, pH 7.4); "
                    "0.22 µm filters; Amicon Ultra 3 kDa concentrators; A280 detector."
                ),
                "Procedure": (
                    "1. Clarify feed by centrifugation (10,000 ×g, 20 min, 4°C) and 0.22 µm filtration.\n"
                    "2. Equilibrate HisTrap with 5 CV binding buffer.\n"
                    "3. Load sample at 1 mL/min; collect flow-through.\n"
                    "4. Wash with 10 CV binding buffer until A280 baseline.\n"
                    "5. Elute with 0–100% imidazole gradient over 20 CV; collect 1 mL fractions.\n"
                    "6. Pool A280 peak fractions; concentrate to <5 mL.\n"
                    "7. Inject onto Superdex 75; run isocratic in SEC buffer at 1 mL/min.\n"
                    "8. Pool monomer peak (~15–17 kDa apparent); concentrate to target.\n"
                    "9. Measure A280; calculate yield using ε; aliquot and store at −80°C."
                ),
                "QC & Acceptance Criteria": (
                    "SDS-PAGE: single band ~15 kDa, ≥95% by densitometry. SEC: monomer ≥95%, "
                    "no aggregate shoulder. Endotoxin <1 EU/mg if for cell assays. Yield logged."
                ),
                "Safety & Waste": (
                    "Imidazole irritant — wear gloves/goggles. Dispose of buffers per chemical "
                    "waste SOP. Decontaminate FPLC lines with 0.5 M NaOH after biological samples."
                ),
                "Revision Log": "v1.0 — initial release. Reviewed by purification lead.",
            },
        },
        {
            "title": "Indirect ELISA for Antibody Binding (EC50)",
            "sections": {
                "Purpose & Scope": (
                    "Quantify relative binding (EC50) of purified antibodies to a target antigen "
                    "by indirect ELISA. Used for clone ranking and lot-to-lot comparison."
                ),
                "Materials & Equipment": (
                    "96-well Maxisorp plates; target antigen (1 µg/mL coating); blocking buffer "
                    "(5% BSA in PBST); HRP-conjugated anti-human/anti-His secondary; TMB substrate; "
                    "2 N H2SO4 stop; multichannel pipette; plate washer; plate reader (450 nm)."
                ),
                "Procedure": (
                    "1. Coat plate with 100 µL/well antigen (1 µg/mL in PBS), overnight 4°C.\n"
                    "2. Wash 3× with PBST.\n"
                    "3. Block 200 µL/well blocking buffer, 1 h RT.\n"
                    "4. Apply 8-point 3-fold serial dilutions of test antibody (start 100 nM), 1 h RT.\n"
                    "   Include positive control mAb and isotype/buffer negative control.\n"
                    "5. Wash 3×. Add HRP secondary (1:5000), 1 h RT.\n"
                    "6. Wash 4×. Develop with 100 µL TMB, 12–15 min in dark.\n"
                    "7. Stop with 50 µL 2 N H2SO4; read A450 within 30 min.\n"
                    "8. Fit 4-parameter logistic curve; report EC50 and signal/background."
                ),
                "QC & Acceptance Criteria": (
                    "Positive control EC50 within 2-fold of historical mean. Blank A450 <0.10. "
                    "4PL fit R² >0.98. Signal/background at top dose >10."
                ),
                "Safety & Waste": (
                    "H2SO4 corrosive — handle in tray, wear PPE. TMB and stopped plates to "
                    "designated chemical waste. No mouth pipetting."
                ),
                "Revision Log": "v1.0 — initial release.",
            },
        },
        {
            "title": "RNA Sample Prep and RT-qPCR Setup",
            "sections": {
                "Purpose & Scope": (
                    "Extract total RNA and set up reverse-transcription qPCR for relative gene "
                    "expression quantification. Applies to adherent/suspension mammalian cells."
                ),
                "Materials & Equipment": (
                    "Column-based RNA kit; DNase I; NanoDrop/Qubit; RT master mix; qPCR master mix "
                    "(SYBR or probe); 384-well plates; qPCR instrument; nuclease-free water; "
                    "RNase-free filter tips."
                ),
                "Procedure": (
                    "1. Harvest 1×10^6 cells; lyse per kit; perform on-column DNase digestion.\n"
                    "2. Elute RNA in 30 µL; quantify (A260/280 1.9–2.1) and check integrity.\n"
                    "3. Normalize to 100 ng/µL; reverse-transcribe 500 ng in 20 µL, include −RT control.\n"
                    "4. Dilute cDNA 1:5; set up triplicate qPCR (10 µL): 5 µL mix, primers 0.3 µM, 2 µL cDNA.\n"
                    "5. Include NTC and reference gene (e.g., GAPDH/ACTB) per plate.\n"
                    "6. Run: 95°C 2 min; 40× (95°C 5 s, 60°C 30 s); melt curve for SYBR.\n"
                    "7. Analyze by ΔΔCt relative to reference gene and control sample."
                ),
                "QC & Acceptance Criteria": (
                    "NTC Ct >35 or undetermined. −RT control ≥5 Ct above +RT. Replicate Ct SD <0.3. "
                    "Single melt peak for SYBR assays. Reference gene Ct stable across samples (<1 Ct)."
                ),
                "Safety & Waste": (
                    "Maintain RNase-free technique. Guanidine lysis buffers hazardous — do not mix "
                    "with bleach. Dispose per biohazard/chemical SOP."
                ),
                "Revision Log": "v1.0 — initial release.",
            },
        },
    ]
    for sop in sops:
        c, d = post("/lab/save_sop", {"title": sop["title"], "sections": sop["sections"], "entity": "experiments"})
        if c == 200 and isinstance(d, dict) and d.get("id"):
            sop_ids.append(str(d["id"]))
    out["created"]["sop_ids"] = sop_ids

    def demo_eln_body(title: str, category: str, assay: str, readout: str) -> str:
        return (
            "<h3>Study Information</h3>"
            f"<p>Record ID: DEMO-{category}<br>"
            f"Category: {category}<br>"
            "Project / program: Demo Lab Validation<br>"
            "Study phase: Discovery<br>"
            "Run status: Planned<br>"
            "Lead scientist: Demo Operator<br>"
            f"Assay type: {assay}<br>"
            "Model system: In vitro (biochemical)</p>"
            "<h3>Protocol followed</h3><p>Ad-hoc demo method; replace with a saved SOP before production use.</p>"
            "<h3>Objective / Hypothesis</h3>"
            f"<p>Objective: Capture design parameters and raw inputs for {title}.<br>"
            f"Hypothesis: The selected condition will produce a measurable change in {readout} relative to control.</p>"
            "<h3>Experimental Design</h3>"
            "<p>Experimental groups / arms: Control; Test condition A; Test condition B<br>"
            "Independent variables: Condition/dose/time point as specified in the run sheet<br>"
            f"Dependent variables / readouts: {readout}<br>"
            "Controls: Negative control; positive/reference control where available<br>"
            "Sample size (n per group): n=3<br>"
            "Replicates: 3 technical replicates<br>"
            "Randomization / blinding: Plate positions randomized where applicable<br>"
            "Design notes: Demo record for validating structured ELN sections.</p>"
            "<h3>Design Data & Attachments</h3>"
            "<p><strong>Manual entry</strong></p>"
            "<pre style=\"white-space:pre-wrap;font-family:inherit;font-size:12px;background:#f7f7f7;padding:10px;border-radius:6px\">"
            "Sample\tReadout\nControl\tTBD\nTest A\tTBD\nTest B\tTBD</pre>"
            "<h3>Resources Used</h3>"
            "<p>Reagents:<br>Demo reagent lot TBD<br>Instrument/Booking:<br>Demo instrument slot TBD</p>"
            "<h3>Execution Notes</h3>"
            "<p>SOP deviations: None planned<br>Environmental conditions: Record at run time<br>"
            "Execution window: Record start/end time after run</p>"
            "<h3>Success Criteria / Readout</h3>"
            f"<p>{readout} measurable in test groups; controls pass predefined acceptance criteria.</p>"
            "<h3>Raw Data Reference</h3><p>Upload CSV/XLSX or link Experimental Data record after run.</p>"
        )

    exp_ids: list[str] = []
    demos = [
        ("DEMO EXP VHH Purification pH comparison", "Purification", "Purification / chromatography", "yield and purity"),
        ("DEMO EXP ELISA dose response", "AssayRun", "Binding assay (ELISA/SPR)", "OD450 response"),
        ("DEMO EXP Transfection timecourse", "Expression", "Expression / culture", "expression level over time"),
    ]
    for title, category, assay, readout in demos:
        body = demo_eln_body(title, category, assay, readout)
        c, d = post(
            "/lab/create_entry",
            {
                "entity": "experiments",
                "title": title,
                "body": body,
                "category": category,
                "tags": ["Demo", category, f"category:{category}", "StructuredELN"],
            },
        )
        if c == 200 and isinstance(d, dict) and d.get("id"):
            exp_ids.append(str(d["id"]))
    out["created"]["experiment_ids"] = exp_ids

    reagents = [
        (
            "DEMO REAG Anti-His Tag Antibody (HRP)",
            "Antibody",
            "Abcam ab18181",
            "L001 · 2027-12",
            "https://www.abcam.com/products/primary-antibodies/his-tag-antibody-ab18181.html",
        ),
        ("DEMO REAG Sodium Chloride", "Chemical", "Sigma S9888", "C221 · 2028-06", "https://www.sigmaaldrich.com/US/en/product/sial/s9888"),
        ("DEMO REAG qPCR Master Mix", "Kit", "Thermo K0171", "Q900 · 2027-09", "https://www.thermofisher.com/order/catalog/product/K0171"),
    ]
    item_ids: list[str] = []
    for title, cat, sup, lot, link in reagents:
        body = (
            f"<p><strong>Category:</strong> {cat}</p>"
            f"<p><strong>Supplier / Catalog:</strong> {sup}</p>"
            f"<p><strong>Lot / Expiry:</strong> {lot}</p>"
            f"<p><strong>Product link:</strong> <a href=\"{link}\" target=\"_blank\" rel=\"noopener\">{link}</a></p>"
        )
        c, d = post(
            "/lab/create_entry",
            {"entity": "items", "title": title, "body": body, "category": cat, "tags": ["Reagent", cat, "Demo"]},
        )
        if c == 200 and isinstance(d, dict) and d.get("id"):
            item_ids.append(str(d["id"]))
    out["created"]["reagent_ids"] = item_ids

    res_ids: list[str] = []
    for title in ["DEMO RES AKTA Pure 25", "DEMO RES Plate Reader Synergy"]:
        c, d = post(
            "/lab/create_entry",
            {"entity": "resources", "title": title, "body": "Location: Lab 402", "category": "Instrument", "tags": ["Resource", "Instrument", "Demo"]},
        )
        if c == 200 and isinstance(d, dict) and d.get("id"):
            res_ids.append(str(d["id"]))
    out["created"]["resource_ids"] = res_ids

    booking_ids: list[str] = []
    if res_ids:
        for rid in res_ids[:2]:
            post("/lab/set_bookable", {"item_id": rid, "is_bookable": True, "allow_overlap": False})
        starts = [datetime.now(timezone.utc) + timedelta(days=1, hours=1), datetime.now(timezone.utc) + timedelta(days=1, hours=3)]
        for rid, st in zip(res_ids[:2], starts):
            en = st + timedelta(hours=1)
            c, d = post(
                "/lab/create_booking",
                {
                    "item_id": rid,
                    "title": f"DEMO booking for #{rid}",
                    "start": st.replace(microsecond=0).isoformat().replace("+00:00", "Z"),
                    "end": en.replace(microsecond=0).isoformat().replace("+00:00", "Z"),
                },
            )
            if c == 200 and isinstance(d, dict) and d.get("booking_id"):
                booking_ids.append(str(d["booking_id"]))
    out["created"]["booking_ids"] = booking_ids

    report_ids: list[str] = []
    for title in ["DEMO REPORT VHH run", "DEMO REPORT ELISA run"]:
        blocks = [
            {
                "label": "Result A",
                "notes": "OD450 values: 0.11, 0.43, 0.89; control 0.10",
                "files": [{"name": "curve.png", "type": "image/png", "data_url": "data:image/png;base64,"}],
            },
            {
                "label": "Result B",
                "notes": "Yield mg/L: 3.2 vs 6.1",
                "files": [{"name": "yield.csv", "type": "text/csv", "data_url": "data:text/csv;base64,"}],
            },
        ]
        cs, ds = post("/lab/analyze_data", {"mode": "statistics", "title": title, "observations": "Demo observations", "result_blocks": blocks})
        cr, dr = post(
            "/lab/analyze_data",
            {"mode": "rationality", "title": title, "observations": "Demo observations", "conclusion": "improved performance", "result_blocks": blocks},
        )
        stats = ds.get("analysis", "") if cs == 200 and isinstance(ds, dict) else ""
        rat = dr.get("analysis", "") if cr == 200 and isinstance(dr, dict) else ""
        c, d = post(
            "/lab/generate_report",
            {
                "title": title,
                "experiment_ref": "",
                "sop_id": sop_ids[0] if sop_ids else None,
                "observations": "Demo observations",
                "result_blocks": blocks,
                "conclusion": "improved performance",
                "qc_status": "PASS",
                "statistics_analysis": stats[:3000],
                "rationality_analysis": rat[:3000],
                "include_pubmed": True,
                "save_to_eln": True,
                "author": "Demo Seed",
            },
        )
        if c == 200 and isinstance(d, dict) and d.get("report_id"):
            report_ids.append(str(d["report_id"]))
    out["created"]["report_ids"] = report_ids

    for ent, key in [("experiments", "experiments_demo"), ("items", "items_demo"), ("resources", "resources_demo")]:
        c, d = post("/lab/entries", {"entity": ent, "limit": 100, "search": "DEMO"})
        out[key] = len((d.get("entries") or [])) if c == 200 and isinstance(d, dict) else None

    print(json.dumps(out, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
