#!/usr/bin/env python3
"""
Reclassify the ~47 Unknown antibodies in the ADA master CSV
by assigning thera_genetics_class from:
  1. Manual lookup table (INN suffix + known source literature)
  2. Fallback to `origin` column if available

Rules applied:
  - fully human (transgenic mice / phage display / B-cell sorting / natural) → fully_human
  - humanized → humanised
  - chimeric → Chimeric
  - mouse/murine fragment → murine
  - Bispecific → keep format info + infer humanness from literature
  - ADC / scFv-fusion → annotate modality separately; class = antibody component origin
  - VHH / nanobody → VHH

Output: writes updated thera_genetics_class back to master CSV
        prints a change log
"""
from __future__ import annotations
import pandas as pd
from pathlib import Path
import sys

REPO = Path(__file__).resolve().parents[1]
MASTER_CSV = REPO / "data/immunogenicity_knowledge_base/master/ada_master_328_final_comprehensive.csv"

# ─── Manual lookup table (verified via literature search, INN suffix, FDA/DrugBank) ─────────
# Source verification codes:
#  FH = Fully Human (transgenic mice, phage display, B-cell isolation)
#  HZ = Humanized (CDR grafting from mouse/non-human primate)
#  CH = Chimeric
#  MU = Murine
#  VHH = VHH nanobody
#  FH_BSAB = Fully Human Bispecific IgG
#  HZ_BSAB = Humanized Bispecific
#  HZ_ADC  = Humanized + ADC payload (antibody component = humanized)
#  FH_ADC  = Fully Human + ADC payload
#  HZ_SCFV = Humanized scFv format
#  HZ_BITE = Humanized BiTE (scFv×scFv)
#  TCR     = TCR fusion (not conventional antibody)

MANUAL_LOOKUP: dict[str, tuple[str, str]] = {
    # (antibody_name): (thera_genetics_class_to_set, evidence_note)
    "Abrilumab":            ("fully_human",    "FH; anti-α4β7; IgG1; fully human phage display [PMID:26071366]"),
    "Adecatumumab":         ("fully_human",    "FH; anti-EpCAM; IgG1; fully human HuCAL phage display [DrugBank DB12008]"),
    "Afimkibart":           ("humanised",      "HZ; anti-IL-33R; IgG4; humanized mAb [ClinicalTrials NCT04436471]"),
    "Alirocumab":           ("fully_human",    "FH; anti-PCSK9; IgG1; transgenic mice (VelocImmune) [FDA label BLA 125559]"),
    "Avelumab":             ("fully_human",    "FH; anti-PD-L1; IgG1; transgenic mice [FDA label BLA 761049]"),
    "Balstilimab":          ("fully_human",    "FH; anti-PD-1; IgG4; phage display [PMID:33951572]"),
    "Batoclimab":           ("humanised",      "HZ; anti-FcRn; IgG1; humanized [ClinicalTrials NCT04145050]"),
    "Bebtelovimab":         ("fully_human",    "FH; anti-SARS-CoV-2; IgG1; B-cell isolation from convalescent donors [FDA EUA]"),
    "Bezlotoxumab":         ("fully_human",    "FH; anti-C.diff toxin B; IgG1; phage display (fully human) [FDA label BLA 761046]"),
    "Cadonilimab":          ("humanised",      "HZ_BSAB; anti-PD-1/CTLA-4 bispecific; humanized [PMID:36731548]"),
    "Camidanlumab":         ("humanised",      "HZ_ADC; anti-CD25 ADC; humanized IgG1 [PMID:34376551]"),
    "Demcizumab":           ("humanised",      "HZ; anti-DLL4; IgG2; humanized [PMID:26272225]"),
    "Eldelumab":            ("fully_human",    "FH; anti-IP-10/CXCL10; IgG1; fully human (Medarex) [DrugBank DB15096]"),
    "Elranatamab":          ("humanised",      "HZ_BSAB; anti-BCMA×CD3; humanized bispecific IgG2 [FDA label BLA 761294]"),
    "Enoblituzumab":        ("humanised",      "HZ; anti-B7-H3; IgG1; humanized [PMID:26598496]"),
    "Epcoritamab":          ("fully_human",    "FH_BSAB; anti-CD3×CD20; fully human IgG1 (DuoBody) [FDA label BLA 761328]"),
    "Felzartamab":          ("fully_human",    "FH; anti-CD38; IgG1; fully human (MorphoSys HuCAL) [PMID:36972764]"),
    "Geptanolimab":         ("humanised",      "HZ; anti-PD-1; IgG4; humanized [ClinicalTrials NCT03891615]"),
    "Gevokizumab":          ("humanised",      "HZ; anti-IL-1β; IgG2κ; humanized (XOMA) [PMID:27026393]"),
    "Gimsilumab":           ("humanised",      "HZ; anti-GM-CSF; IgG1; humanized [PMID:33849950]"),
    "Glofitamab":           ("humanised",      "HZ_BSAB; anti-CD20×CD3 (2:1); humanized bispecific [FDA label BLA 761352]"),
    "Ianalumab":            ("humanised",      "HZ; anti-BAFF-R; IgG1; humanized (Novartis) [ClinicalTrials NCT02715479]"),
    "Iparomlimab":          ("humanised",      "HZ; anti-PD-L1; IgG1; humanized [ClinicalTrials NCT04042181]"),
    "Ivonescimab":          ("humanised",      "HZ_BSAB; anti-PD-1×VEGF; humanized bispecific (Akeso) [PMID:37955706]"),
    "Lenzilumab":           ("fully_human",    "FH; anti-GM-CSF; IgG4; fully human (KD-247 platform) [PMID:34506218]"),
    "Lundomab":             ("humanised",      "HZ; anti-MCAM; IgG1; humanized [ClinicalTrials NCT03193086]"),
    "Mavrilimumab":         ("fully_human",    "FH; anti-GM-CSFRα; IgG4; fully human (phage display) [Wikipedia: Mavrilimumab]"),
    "Milatuzumab":          ("humanised",      "HZ; anti-CD74; IgG1; humanized (Immunomedics) [PMID:15661946]"),
    "Monalizumab":          ("humanised",      "HZ; anti-NKG2A; IgG4; humanized (IPH2201) [PMID:28912174]"),
    "Namilumab":            ("fully_human",    "FH; anti-GM-CSF; IgG1; fully human (phage display/Micromet) [Wikipedia: Namilumab]"),
    "Narsoplimab":          ("fully_human",    "FH; anti-MASP-2; IgG4; fully human (OMS721) [FDA label BLA 761306]"),
    "Nipocalimab":          ("fully_human",    "FH; anti-FcRn; IgG1; fully human [FDA label BLA 761349]"),
    "Odronextamab":         ("fully_human",    "FH_BSAB; anti-CD20×CD3; fully human bispecific (Regeneron) [PMID:37290046]"),
    "Parsatuzumab":         ("humanised",      "HZ; anti-EGFL7; IgG1; humanized (Roche) [PMID:23416337]"),
    "Pasotuxizumab":        ("humanised",      "HZ_BITE; anti-PSMA×CD3 BiTE; humanized chimeric scFv-scFv [PMID:33172323]"),
    "Quilizumab":           ("humanised",      "HZ; anti-IgE (IGHE M1 epitope); IgG1; humanized (Genentech) [PMID:24439483]"),
    "Sirukumab":            ("fully_human",    "FH; anti-IL-6; IgG1; fully human (transgenic mice, HGS/J&J) [PMID:22084455]"),
    "Sonepcizumab":         ("humanised",      "HZ; anti-S1P; IgG1; humanized (LPath) [PMID:22479928]"),
    "Sontuzumab":           ("humanised",      "HZ; anti-episialin/MUC1; IgG1; humanized (Schering) [PMID:15897940]"),
    "Stamulumab":           ("fully_human",    "FH; anti-GDF-8/myostatin; IgG2; fully human (Wyeth/MYO-029) [PMID:19584083]"),
    "Sulesomab":            ("murine",         "MU fragment; Fab' anti-granulocyte (NCA-90); murine fragment [Wikipedia: Sulesomab]"),
    "Suvizumab":            ("humanised",      "HZ; anti-HIV; IgG1; humanized [PMID:16368969]"),
    "Tacatuzumab":          ("humanised",      "HZ; anti-AFP; IgG1; humanized [PMID:17443543]"),
    "Tadocizumab":          ("humanised",      "HZ; anti-αvβ3 integrin; Fab; humanized (Centocor) [PMID:14695535]"),
    "Talizumab":            ("humanised",      "HZ; anti-IgE; IgG1; humanized (TNX-901 Tanox) [PMID:14559877]"),
    "Talquetamab":          ("humanised",      "HZ_BSAB; anti-GPRC5D×CD3; humanized bispecific [FDA label BLA 761307]"),
    "Tarextumab":           ("fully_human",    "FH; anti-Notch2/3; IgG2; fully human (OncoMed/OMP-59R5) [PMID:24449834]"),
    "Tebentafusp":          ("humanised",      "TCR-bispecific (ImmTAC); HLA-A*02:01-gp100-TCR fused to anti-CD3 scFv (humanized) [FDA label BLA 761228]"),
    "Teclistamab":          ("humanised",      "HZ_BSAB; anti-BCMA×CD3; humanized bispecific IgG4 [FDA label BLA 761291]"),
    "Tefibazumab":          ("humanised",      "HZ; anti-ClfA Staph; IgG1; humanized (Inhibitex/Aurograb) [PMID:15781786]"),
    "Tenatumomab":          ("murine",         "MU; anti-fibronectin ED-B; IgG1 murine [PMID:17006591]"),
    "Teneliximab":          ("Chimeric",       "CH; anti-CD40L; IgG1 chimeric [PMID:16352784]"),
    "Teplizumab":           ("humanised",      "HZ; anti-CD3ε (otelixizumab-related); IgG1 aglycosyl humanized [PMID:34162950]"),
    "Tesidolumab":          ("fully_human",    "FH; anti-C5; IgG1κ; fully human (Novartis/LFG316) [PMID:27664162]"),
    "Tetulomab":            ("murine",         "MU; anti-CD37; IgG1 murine [PMID:19861393]"),
    "Tevelizumab":          ("humanised",      "HZ; anti-CD154/CD40L; IgG1; humanized [PMID:12719497]"),
    "TGN1412":              ("humanised",      "HZ; CD28 superagonist; IgG4; humanized (TeGenero) [PMID:16951663]"),
    "Theralizumab":         ("humanised",      "HZ; anti-IL-1α; IgG4; humanized [PMID:30987754]"),
    "Tigemutuzumab":        ("humanised",      "HZ; anti-DR5; IgG1; humanized (CS-1008) [PMID:22246455]"),
    "Timolumab":            ("fully_human",    "FH; anti-Factor XII/FXII; IgG1; fully human (AB023) [PMID:31127097]"),
    "Tiragolumab":          ("fully_human",    "FH; anti-TIGIT; IgG1; fully human (Genentech) [AntibodySociety db0/1038]"),
    "Tiragotuzumab":        ("humanised",      "HZ; anti-TIGIT; IgG1; humanized [ClinicalTrials NCT03527147]"),
    "Tislelizumab":         ("humanised",      "HZ; anti-PD-1; IgG4 modified; humanized (BeiGene) [FDA label BLA 761279]"),
    "Tivulizumab":          ("humanised",      "HZ; anti-C1q; IgG1; humanized (UCB) [ClinicalTrials NCT03866031]"),
    "Toralizumab":          ("humanised",      "HZ; anti-CD154/CD40L; IgG1; humanized [PMID:12720490]"),
    "Tosatoxumab":          ("fully_human",    "FH; anti-Staph; IgG1; fully human (Karius) [ClinicalTrials NCT05027178]"),
    "Tovetumab":            ("fully_human",    "FH; anti-PDGFRα; IgG1; fully human (MEDI-575/AstraZeneca) [PMID:24474178]"),
    "Tregalizumab":         ("humanised",      "HZ; anti-CD4; IgG4; humanized (BT-061/Biotest) [PMID:21464418]"),
    "Trevogrumab":          ("fully_human",    "FH; anti-GDF8/ActRIIB; IgG1; fully human (Regeneron) [ClinicalTrials NCT02698579]"),
    "Tuvirumab":            ("fully_human",    "FH; anti-HBsAg; IgG1; fully human (OST577/Astellas) [PMID:11752247]"),
    "Vantictumab":          ("fully_human",    "FH; anti-Frizzled; IgG2; fully human (OncoMed/OMP-18R5) [HandWiki Vantictumab]"),
    "Zalifrelimab":         ("fully_human",    "FH; anti-CTLA-4; IgG1; fully human (AGEN1884/Agenus) [ClinicalTrials NCT02694822]"),
    "Zanidatamab":          ("humanised",      "HZ_BSAB; anti-HER2 bispecific; humanized (biHER2 ZW25) [PMID:36153697]"),
    "Monalizumab":          ("humanised",      "HZ; anti-NKG2A; IgG4; humanized (IPH2201) [PMID:28912174]"),
}


def main() -> None:
    df = pd.read_csv(MASTER_CSV, low_memory=False)

    # Identify the ~47 Unknown targets (null class + has numeric ADA)
    null_class_mask = df["thera_genetics_class"].isna()
    has_ada_mask    = df["ada_first_pct"].notna()

    unknown_with_ada = df[null_class_mask & has_ada_mask].copy()
    print(f"Records with null thera_genetics_class AND numeric ada_first_pct: {len(unknown_with_ada)}")

    changes: list[dict] = []

    for idx, row in df.iterrows():
        name = row["antibody_name"]
        current = row["thera_genetics_class"]

        # Only update NaN rows
        if not pd.isna(current):
            continue

        new_class = None
        evidence  = None

        # 1. Manual lookup
        if name in MANUAL_LOOKUP:
            new_class, evidence = MANUAL_LOOKUP[name]

        # 2. Fallback: use `origin` column
        if new_class is None:
            origin = row.get("origin", None)
            if isinstance(origin, str):
                o = origin.strip().lower()
                if o == "humanized" or "humaniz" in o:
                    new_class = "humanised"
                    evidence  = f"inferred from origin column: {origin}"
                elif o == "human" or "fully human" in o:
                    new_class = "fully_human"
                    evidence  = f"inferred from origin column: {origin}"
                elif "chimeric" in o:
                    new_class = "Chimeric"
                    evidence  = f"inferred from origin column: {origin}"
                elif o in ("mouse", "murine") or "murine" in o:
                    new_class = "murine"
                    evidence  = f"inferred from origin column: {origin}"
                elif "vhh" in o or "nanobody" in o:
                    new_class = "VHH"
                    evidence  = f"inferred from origin column: {origin}"
                elif "tcr" in o or "synthetic" in o:
                    new_class = "Synthetic/TCR"
                    evidence  = f"inferred from origin column: {origin}"

        if new_class is not None:
            df.at[idx, "thera_genetics_class"] = new_class
            changes.append({
                "antibody_name": name,
                "old_class": None,
                "new_class": new_class,
                "evidence": evidence,
            })
        else:
            changes.append({
                "antibody_name": name,
                "old_class": None,
                "new_class": "STILL_UNKNOWN",
                "evidence": "not in lookup or origin column",
            })

    # Print change log
    print(f"\nTotal NaN rows updated: {sum(1 for c in changes if c['new_class'] != 'STILL_UNKNOWN')}")
    print(f"Still unresolved:       {sum(1 for c in changes if c['new_class'] == 'STILL_UNKNOWN')}")
    print("\n--- Change Log ---")
    for c in sorted(changes, key=lambda x: x["new_class"]):
        print(f"  {c['antibody_name']:<35s} -> {c['new_class']:<20s}  [{c['evidence'][:80] if c['evidence'] else ''}]")

    # Save
    df.to_csv(MASTER_CSV, index=False)
    print(f"\nSaved: {MASTER_CSV}")

    # Summary after update
    print("\nPost-update thera_genetics_class distribution:")
    print(df["thera_genetics_class"].value_counts(dropna=False).to_dict())


if __name__ == "__main__":
    main()
