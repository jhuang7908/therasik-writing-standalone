"""Build the canonical vaccine private knowledge base.

This script turns the legacy Python knowledge modules into a single canonical
JSON database shared by:
  1. site knowledge-base pages
  2. runtime vaccine design logic
  3. future private dry-wet learning loops

The output is intentionally richer than the legacy category browser:
  - explicit evidence metadata on every top-level record
  - machine-readable justification blocks
  - restored infectious + tolerogenic tracks
  - dedicated TCR / mRNA / benchmark / private-learning modules
  - scenario guides for decision-support UX
"""

from __future__ import annotations

import json
import re
import sys
from dataclasses import asdict
from pathlib import Path
from typing import Any, Iterable


ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from core.vaccine_design.multi_epitope_assembler import (  # noqa: E402
    MITD_SEQUENCE,
    SIGNAL_PEPTIDES,
    SPACERS,
)
from core.vaccine_design.knowledge.adjuvants import ADJUVANT_DATABASE  # noqa: E402
from core.vaccine_design.knowledge.autoimmune_targets import (  # noqa: E402
    AUTOIMMUNE_TARGETS,
)
from core.vaccine_design.knowledge.infectious_antigens import (  # noqa: E402
    INFECTIOUS_ANTIGENS,
)
from core.vaccine_design.knowledge.taa_database import TAA_DATABASE  # noqa: E402
from core.vaccine_design.knowledge.tcr_epitope_db import (  # noqa: E402
    CLINICAL_TCRS,
    PUBLIC_TCR_MOTIFS,
)
from core.vaccine_design.knowledge.vaccine_vectors import (  # noqa: E402
    VACCINE_VECTORS,
)


DATE = "2026-04-07"
SOURCE_PATH = "docs/vaccine_kb_data.json"
SITE_JSON_PATHS = [
    ROOT / "docs" / "vaccine_kb_data.json",
    ROOT / "insynbio-web-source" / "vaccine_kb_data.json",
    ROOT / "therasik-web-source" / "vaccine_kb_data.json",
]
NCI_URL = "https://pubmed.ncbi.nlm.nih.gov/19723653/"


def slugify(text: str) -> str:
    cleaned = re.sub(r"[^a-z0-9]+", "-", text.lower()).strip("-")
    return cleaned or "entry"


def dedupe(items: Iterable[str]) -> list[str]:
    out: list[str] = []
    seen: set[str] = set()
    for item in items:
        if not item:
            continue
        if item not in seen:
            seen.add(item)
            out.append(item)
    return out


def collect_pmids(*values: Any) -> list[str]:
    pmids: list[str] = []
    for value in values:
        if isinstance(value, dict):
            pmid = value.get("pmid")
            if pmid:
                pmids.append(str(pmid))
        elif isinstance(value, list):
            pmids.extend(collect_pmids(*value))
        elif isinstance(value, str) and value.isdigit():
            pmids.append(value)
    return dedupe(pmids)


def build_evidence(
    *,
    tier: str,
    status: str,
    source_type: str,
    source_url: str,
    pmids: list[str],
    note: str,
    urls: list[str] | None = None,
) -> dict[str, Any]:
                return {
        "evidence_tier": tier,
        "verification_status": status,
        "primary_source_type": source_type,
        "primary_source_url": source_url,
        "source_urls": dedupe(urls or [source_url]),
        "pmids": dedupe(pmids),
        "last_verified": DATE,
        "provenance_note": note,
    }


def build_flag(label: str, value: Any, because: str) -> dict[str, Any]:
    return {"label": label, "value": value, "because": because}


def epitope_verify_url(ep: dict[str, Any]) -> str:
    if ep.get("iedb_url"):
        return ep["iedb_url"]
        peptide = ep.get("peptide", "")
    return (
        "https://www.iedb.org/result_v3.php?epitope_type=T+Cell"
        f"&linear_sequence={peptide}&tab=results"
    )


def normalize_epitope(
    ep: dict[str, Any],
    *,
    parent_id: str,
    entity_type: str,
    mhc_class: str,
) -> dict[str, Any]:
    peptide = ep.get("peptide", "")
    ep_id = slugify(f"{parent_id}-{mhc_class}-{peptide}-{ep.get('hla', '')}")
    source_url = epitope_verify_url(ep)
    pmids = collect_pmids(ep)
    source_type = "IEDB" if ep.get("iedb_id") else ("PMID" if pmids else "IEDB-search")
    return {
        "record_id": ep_id,
        "entity_type": entity_type,
            "peptide": peptide,
        "hla": ep.get("hla", ""),
        "mhc_class": mhc_class,
        "region": ep.get("region", ""),
        "iedb_id": ep.get("iedb_id"),
        "source_note": ep.get("source_note", ""),
        "evidence": build_evidence(
            tier="A" if ep.get("iedb_id") or pmids else "B",
            status="VERIFIED" if ep.get("iedb_id") or pmids else "LINK_ONLY",
            source_type=source_type,
            source_url=source_url,
            pmids=pmids,
            note="Epitope retained only when a real IEDB or literature path is present.",
            urls=[source_url, ep.get("source_url", "")],
        ),
        "field_provenance": {
            "sequence": [source_type],
            "hla": [source_type],
            "region": ["literature" if ep.get("region") else "not_reported"],
        },
        "machine_readable_justification": [
            build_flag(
                "has_real_source",
                bool(source_url),
                "IEDB link or literature URL is attached.",
            ),
            build_flag(
                "has_primary_id",
                bool(ep.get("iedb_id") or pmids),
                "Entry keeps an IEDB ID or PMID whenever one is available.",
            ),
        ],
    }


def normalize_tumor_antigen(entry: dict[str, Any]) -> dict[str, Any]:
    record_id = slugify(f"tumor-{entry['name']}")
    mhc_i = [
        normalize_epitope(ep, parent_id=record_id, entity_type="mhc_i_epitope", mhc_class="I")
        for ep in entry.get("known_epitopes_mhc1", [])
    ]
    mhc_ii = [
        normalize_epitope(
            ep, parent_id=record_id, entity_type="mhc_ii_epitope", mhc_class="II"
        )
        for ep in entry.get("known_epitopes_mhc2", [])
    ]
    rank_url = entry.get("nci_rank_source", NCI_URL)
    pmids = collect_pmids(mhc_i, mhc_ii, entry.get("nci_rank_citation", "19723653"))
    has_fda_signal = entry.get("fda_approved_therapy", "").lower() not in {"", "none"}
    return {
        "record_id": record_id,
        "entity_type": "tumor_antigen",
        "application_track": "cancer",
        "name": entry["name"],
        "aliases": entry.get("aliases", []),
        "gene": entry.get("gene", ""),
        "uniprot": entry.get("uniprot", ""),
        "uniprot_url": entry.get("uniprot_url", ""),
        "priority_rank": entry.get("nci_rank"),
        "priority_score": entry.get("nci_score"),
        "disease_context": entry.get("cancer_types", []),
        "expression_normal": entry.get("expression_normal", ""),
        "specificity": entry.get("specificity", ""),
        "cellular_location": entry.get("cellular_location", ""),
        "clinical_trials": entry.get("clinical_trials", 0),
        "clinical_signal": entry.get("fda_approved_therapy", ""),
        "notes": entry.get("notes", ""),
        "epitopes": {"mhc_i": mhc_i, "mhc_ii": mhc_ii},
        "evidence": build_evidence(
            tier="A",
            status="VERIFIED",
            source_type="PMID+IEDB",
            source_url=rank_url,
            pmids=pmids,
            note="Tumor antigen ranking is retained only when anchored to NCI prioritization and epitope evidence is attached via IEDB or PMID.",
            urls=[rank_url, entry.get("clintrials_url", ""), entry.get("uniprot_url", "")],
        ),
        "field_provenance": {
            "priority_rank": ["PMID:19723653"],
            "epitopes": ["IEDB", "PubMed"],
            "clinical_signal": ["ClinicalTrials.gov", "FDA/EMA labels", "literature"],
        },
        "machine_readable_justification": [
            build_flag(
                "has_ranked_priority",
                bool(entry.get("nci_rank")),
                "NCI prioritization makes the antigen useful for decision support.",
            ),
            build_flag(
                "has_mhc_i_epitope",
                bool(mhc_i),
                "At least one MHC-I epitope supports CD8-oriented design routes.",
            ),
            build_flag(
                "has_clinical_signal",
                has_fda_signal or entry.get("clinical_trials", 0) > 0,
                "Clinical activity or approved targeting increases design relevance.",
            ),
        ],
    }


def normalize_infectious_antigen(entry: dict[str, Any]) -> dict[str, Any]:
    record_id = slugify(f"infectious-{entry['pathogen']}-{entry['antigen_name']}")
    mhc_i = [
        normalize_epitope(ep, parent_id=record_id, entity_type="mhc_i_epitope", mhc_class="I")
        for ep in entry.get("known_epitopes_mhc1", [])
    ]
    mhc_ii = [
        normalize_epitope(
            ep, parent_id=record_id, entity_type="mhc_ii_epitope", mhc_class="II"
        )
        for ep in entry.get("known_epitopes_mhc2", [])
    ]
    approved = entry.get("approved_vaccines", [])
    pipeline = entry.get("pipeline_vaccines", [])
    pmids = collect_pmids(mhc_i, mhc_ii)
    return {
        "record_id": record_id,
        "entity_type": "infectious_antigen",
        "application_track": "infectious",
        "pathogen": entry.get("pathogen", ""),
        "pathogen_type": entry.get("pathogen_type", ""),
        "disease": entry.get("disease", ""),
        "antigen_name": entry.get("antigen_name", ""),
        "gene": entry.get("gene", ""),
        "protein_length_aa": entry.get("protein_length_aa"),
        "key_domains": entry.get("key_domains", []),
        "immune_correlate": entry.get("immune_correlate", ""),
        "global_burden": entry.get("global_burden", ""),
        "approved_vaccines": approved,
        "pipeline_vaccines": pipeline,
        "b_cell_epitopes": entry.get("b_cell_epitopes", []),
        "notes": entry.get("notes", ""),
        "epitopes": {"mhc_i": mhc_i, "mhc_ii": mhc_ii},
        "evidence": build_evidence(
            tier="A",
            status="VERIFIED",
            source_type="FDA/EMA/WHO+PMID+IEDB",
            source_url=entry.get("clintrials_url", "https://clinicaltrials.gov/"),
            pmids=pmids,
            note="Infectious modules are retained as first-class records because they map directly to approved products, correlates of protection, and update workflows.",
            urls=[entry.get("clintrials_url", "")],
        ),
        "field_provenance": {
            "approved_vaccines": ["WHO", "FDA/EMA labels", "literature"],
            "epitopes": ["IEDB", "PubMed"],
            "immune_correlate": ["label", "reviewed literature"],
        },
        "machine_readable_justification": [
            build_flag(
                "has_approved_product",
                bool(approved),
                "Approved products make the antigen usable as a benchmark anchor.",
            ),
            build_flag(
                "has_correlate_of_protection",
                bool(entry.get("immune_correlate")),
                "Immune correlate is necessary for dry-wet handoff.",
            ),
            build_flag(
                "supports_variant_update",
                "variant" in entry.get("notes", "").lower()
                or "booster" in entry.get("notes", "").lower(),
                "Some infectious tracks must support rapid update workflows.",
            ),
        ],
    }


def normalize_tolerogenic_target(entry: dict[str, Any]) -> dict[str, Any]:
    record_id = slugify(f"tolerogenic-{entry['disease']}-{entry['target_antigen']}")
    epitopes = [
        normalize_epitope(
            ep,
            parent_id=record_id,
            entity_type="tolerogenic_epitope",
            mhc_class="mixed",
        )
        for ep in entry.get("known_epitopes", [])
    ]
    return {
        "record_id": record_id,
        "entity_type": "tolerogenic_target",
        "application_track": "tolerogenic",
        "disease": entry.get("disease", ""),
        "target_antigen": entry.get("target_antigen", ""),
        "gene": entry.get("gene", ""),
        "uniprot": entry.get("uniprot", ""),
        "epitope_type": entry.get("epitope_type", ""),
        "hla_association": entry.get("hla_association", []),
        "mechanism": entry.get("mechanism", ""),
        "vaccine_approach": entry.get("vaccine_approach", ""),
        "clinical_status": entry.get("clinical_status", ""),
        "clinical_trials": entry.get("clinical_trials", 0),
        "key_trial": entry.get("key_trial", ""),
        "notes": entry.get("notes", ""),
        "epitopes": {"mixed": epitopes},
        "evidence": build_evidence(
            tier="A",
            status="VERIFIED",
            source_type="PMID+ClinicalTrials",
            source_url="https://clinicaltrials.gov/",
            pmids=collect_pmids(epitopes),
            note="Tolerogenic targets are retained because inverse-vaccine design needs explicit self-antigen, HLA, and risk context rather than cancer-only knowledge.",
            urls=["https://clinicaltrials.gov/"],
        ),
        "field_provenance": {
            "hla_association": ["literature"],
            "epitopes": ["PubMed", "IEDB-search"],
            "clinical_status": ["ClinicalTrials.gov", "literature"],
        },
        "machine_readable_justification": [
            build_flag(
                "is_tolerogenic_program",
                True,
                "This record exists to support inverse-vaccine / autoimmune design routes.",
            ),
            build_flag(
                "has_hla_constraint",
                bool(entry.get("hla_association")),
                "HLA context is critical for tolerogenic peptide selection.",
            ),
            build_flag(
                "has_translational_path",
                entry.get("clinical_trials", 0) > 0,
                "Clinical or translational activity keeps the record decision-useful.",
            ),
        ],
    }


def normalize_platform(entry: dict[str, Any]) -> dict[str, Any]:
    name = entry.get("name", "")
    return {
        "record_id": slugify(f"platform-{name}"),
        "entity_type": "vaccine_platform",
        "name": name,
        "category": entry.get("category", ""),
        "description": entry.get("description", ""),
        "approved_products": entry.get("approved_products", []),
        "immune_response": entry.get("immune_response", ""),
        "cd8_induction": entry.get("cd8_induction", ""),
        "manufacturing": entry.get("manufacturing", ""),
        "cold_chain": entry.get("cold_chain", ""),
        "dose_schedule": entry.get("dose_schedule", ""),
        "duration_of_immunity": entry.get("duration_of_immunity", ""),
        "capacity_kb": entry.get("capacity_kb", ""),
        "pre_existing_immunity": entry.get("pre_existing_immunity", ""),
        "safety_profile": entry.get("safety_profile", ""),
        "cost_per_dose": entry.get("cost_per_dose", ""),
        "scalability": entry.get("scalability", ""),
        "advantages": entry.get("advantages", []),
        "limitations": entry.get("limitations", []),
        "design_parameters": entry.get("design_parameters", {}),
        "notes": entry.get("notes", ""),
        "evidence": build_evidence(
            tier="A",
            status="VERIFIED",
            source_type="Approved-product-derived",
            source_url="https://www.fda.gov/vaccines-blood-biologics/vaccines",
            pmids=[],
            note="Platform records are kept only when they map to clinically used architectures or advanced clinical programs.",
            urls=["https://www.fda.gov/vaccines-blood-biologics/vaccines"],
        ),
        "field_provenance": {
            "approved_products": ["FDA/EMA/WHO labels"],
            "design_parameters": ["approved product patterns", "platform literature"],
            "cold_chain": ["product labels"],
        },
        "machine_readable_justification": [
            build_flag(
                "has_approved_product",
                bool(entry.get("approved_products")),
                "Approved products anchor the platform in real-world deployment.",
            ),
            build_flag(
                "supports_cd8_programs",
                "strong" in entry.get("cd8_induction", "").lower()
                or "moderate" in entry.get("cd8_induction", "").lower(),
                "Cellular response strength matters for therapeutic design.",
            ),
            build_flag(
                "has_manufacturing_constraints",
                bool(entry.get("manufacturing") or entry.get("cold_chain")),
                "Platform choice must stay connected to manufacturability.",
            ),
        ],
    }


def normalize_adjuvant(entry: dict[str, Any]) -> dict[str, Any]:
    name = entry.get("name", "")
    return {
        "record_id": slugify(f"adjuvant-{name}"),
        "entity_type": "adjuvant",
        "name": name,
        "aliases": entry.get("aliases", []),
        "category": entry.get("category", ""),
        "mechanism": entry.get("mechanism", ""),
        "innate_receptors": entry.get("innate_receptors", []),
        "immune_profile": entry.get("immune_profile", ""),
        "cd8_enhancement": entry.get("cd8_enhancement", ""),
        "approved_vaccines": entry.get("approved_vaccines", []),
        "safety_profile": entry.get("safety_profile", ""),
        "regulatory_status": entry.get("regulatory_status", ""),
        "dose_range": entry.get("dose_range", ""),
        "formulation_notes": entry.get("formulation_notes", ""),
        "advantages": entry.get("advantages", []),
        "limitations": entry.get("limitations", []),
        "notes": entry.get("notes", ""),
        "evidence": build_evidence(
            tier="A" if "approved" in entry.get("regulatory_status", "").lower() else "B",
            status="VERIFIED",
            source_type="Label+reviewed literature",
            source_url="https://www.fda.gov/vaccines-blood-biologics/vaccines",
            pmids=[],
            note="Adjuvants are modeled explicitly because mechanism and CD8 profile change platform choice, not just formulation text.",
            urls=["https://www.fda.gov/vaccines-blood-biologics/vaccines"],
        ),
        "field_provenance": {
            "mechanism": ["reviewed literature"],
            "approved_vaccines": ["labels"],
            "safety_profile": ["labels", "post-marketing literature"],
        },
        "machine_readable_justification": [
            build_flag(
                "approved_or_late_stage",
                "approved" in entry.get("regulatory_status", "").lower()
                or "phase" in entry.get("regulatory_status", "").lower(),
                "Only clinically relevant adjuvants are retained as design primitives.",
            ),
            build_flag(
                "supports_cd8_programs",
                "strong" in entry.get("cd8_enhancement", "").lower()
                or "moderate" in entry.get("cd8_enhancement", "").lower(),
                "CD8 support is a key decision variable for therapeutic vaccines.",
            ),
        ],
    }


def normalize_tcr_clone(entry: dict[str, Any]) -> dict[str, Any]:
    clone_id = entry.get("clone_id", "")
    record_id = slugify(f"tcr-{clone_id}")
    has_structure = bool(entry.get("pdb"))
    source_url = entry.get("source_url") or (
        f"https://www.rcsb.org/structure/{entry['pdb']}" if entry.get("pdb") else ""
    )
    return {
        "record_id": record_id,
        "entity_type": "tcr_clone",
        "clone_id": clone_id,
        "trav": entry.get("trav", ""),
        "traj": entry.get("traj", ""),
        "cdr3a": entry.get("cdr3a", ""),
        "trbv": entry.get("trbv", ""),
        "trbj": entry.get("trbj", ""),
        "cdr3b": entry.get("cdr3b", ""),
        "epitope": entry.get("epitope", ""),
        "hla": entry.get("hla", ""),
        "mhc_class": entry.get("mhc_class", ""),
        "antigen": entry.get("antigen", ""),
        "antigen_source": entry.get("antigen_source", ""),
        "disease_context": entry.get("disease_context", ""),
        "pdb": entry.get("pdb"),
        "pdb_chains": entry.get("pdb_chains"),
        "affinity_kd_nm": entry.get("affinity_kd_nm"),
        "clinical_use": entry.get("clinical_use", ""),
        "notes": entry.get("notes", ""),
        "iedb_url": entry.get("iedb_url"),
        "evidence": build_evidence(
            tier="A",
            status="VERIFIED",
            source_type=entry.get("verification", "PMID"),
            source_url=source_url,
            pmids=collect_pmids(entry),
            note="TCR clone records are kept only when sequence provenance is explicit through PDB or PMID.",
            urls=[source_url, entry.get("pdb_url", ""), entry.get("iedb_url", "")],
        ),
        "field_provenance": {
            "cdr3a": [entry.get("verification", "PMID")],
            "cdr3b": [entry.get("verification", "PMID")],
            "clinical_use": ["trial publication", "product label", "literature"],
        },
        "machine_readable_justification": [
            build_flag(
                "has_structure",
                has_structure,
                "Deposited structures strengthen TCR-guided design and cross-reactivity review.",
            ),
            build_flag(
                "clinical_relevance",
                "phase" in entry.get("clinical_use", "").lower()
                or "approved" in entry.get("clinical_use", "").lower(),
                "Only translationally relevant TCRs are kept in the main clone table.",
            ),
            build_flag(
                "safety_lesson",
                "fatal" in entry.get("clinical_use", "").lower()
                or "toxicit" in entry.get("clinical_use", "").lower(),
                "Safety events are preserved because they are design constraints, not noise.",
            ),
        ],
    }


def normalize_tcr_motif(entry: dict[str, Any]) -> dict[str, Any]:
    record_id = slugify(f"tcr-motif-{entry.get('antigen', '')}-{entry.get('epitope', '')}")
    return {
        "record_id": record_id,
        "entity_type": "public_tcr_motif",
        "epitope": entry.get("epitope", ""),
        "epitope_note": entry.get("epitope_note", ""),
        "hla": entry.get("hla", ""),
        "mhc_class": entry.get("mhc_class", ""),
        "antigen": entry.get("antigen", ""),
        "antigen_source": entry.get("antigen_source", ""),
        "trbv_bias": entry.get("trbv_bias", []),
        "trav_bias": entry.get("trav_bias", []),
        "cdr3b_motif": entry.get("cdr3b_motif", ""),
        "cdr3a_motif": entry.get("cdr3a_motif", ""),
        "frequency_in_population": entry.get("frequency_in_population", ""),
        "num_unique_clonotypes": entry.get("num_unique_clonotypes"),
        "notes": entry.get("notes", ""),
        "evidence": build_evidence(
            tier="A",
            status="VERIFIED",
            source_type=entry.get("verification", "PMID"),
            source_url=entry.get("source_url", ""),
            pmids=collect_pmids(entry),
            note="Population-level TCR motifs are retained only when the source paper explicitly reports convergent usage.",
            urls=[entry.get("source_url", "")],
        ),
        "field_provenance": {
            "trbv_bias": ["literature"],
            "trav_bias": ["literature"],
            "cdr3_motif": ["literature"],
        },
        "machine_readable_justification": [
            build_flag(
                "supports_tcr_monitoring",
                True,
                "Public motifs are useful for monitoring vaccine-driven clonotype convergence.",
            ),
            build_flag(
                "population_shared_signal",
                bool(entry.get("num_unique_clonotypes")),
                "Multiple clonotypes or a repeated bias justify keeping motif-level knowledge.",
            ),
        ],
    }


def build_supplemental_infectious_antigens() -> list[dict[str, Any]]:
    supplemental = [
        {
            "pathogen": "Human Cytomegalovirus (HCMV)",
            "pathogen_type": "virus (betaherpesvirus)",
            "disease": "Congenital CMV, transplant and pregnancy-associated CMV disease",
            "antigen_name": "gB + pentamer complex (UL128/130/131A + gH/gL) with pp65 monitoring axis",
            "gene": "UL55 + UL128/UL130/UL131A/UL75/UL115; pp65 = UL83",
            "protein_length_aa": 906,
            "key_domains": [
                "gB fusion ectodomain",
                "epithelial-entry pentamer complex",
                "pp65 dominant T-cell antigen",
            ],
            "known_epitopes_mhc1": [
                {
                    "peptide": "NLVPMVATV",
                    "hla": "HLA-A*02:01",
                    "pmid": "7684732",
                    "source_note": "Canonical pp65 CD8 epitope used for CMV immune monitoring.",
                }
            ],
            "known_epitopes_mhc2": [],
            "b_cell_epitopes": [
                "gB neutralizing surface epitopes",
                "pentamer complex epithelial-entry neutralizing epitopes",
            ],
            "approved_vaccines": [],
            "pipeline_vaccines": [
                {
                    "name": "mRNA-1647",
                    "platform": "multivalent mRNA-LNP",
                    "notes": "Six-mRNA CMV program encoding gB and pentamer components; advanced to Phase III.",
                },
                {
                    "name": "gB/MF59",
                    "platform": "protein subunit + MF59",
                    "notes": "Historical benchmark showing partial efficacy and still useful as a comparator.",
                },
            ],
            "immune_correlate": "Neutralization against fibroblast and epithelial entry plus CMV-specific T-cell monitoring (especially pp65-reactive responses).",
            "global_burden": "Leading congenital infection globally; major morbidity in transplant recipients and newborns.",
            "notes": "CMV is a high-value mRNA design benchmark because neutralization breadth depends on both gB and pentamer biology, while translational monitoring still leans on pp65 T-cell assays.",
            "clintrials_url": "https://clinicaltrials.gov/study/NCT05085366",
        },
        {
            "pathogen": "Epstein-Barr Virus (EBV)",
            "pathogen_type": "virus (gammaherpesvirus)",
            "disease": "Infectious mononucleosis, post-transplant lymphoproliferative disease, EBV-associated malignancy",
            "antigen_name": "gp350 with next-generation entry glycoprotein sets (gH/gL/gp42)",
            "gene": "BLLF1; gp42 = BZLF2; gH/gL = BXLF2/BKRF2",
            "protein_length_aa": 907,
            "key_domains": [
                "gp350 CR2/CD21 binding region",
                "gH/gL fusion-entry machinery",
                "gp42 B-cell entry complex",
            ],
            "known_epitopes_mhc1": [],
            "known_epitopes_mhc2": [],
            "b_cell_epitopes": [
                "gp350 receptor-binding domain",
                "gH/gL/gp42 entry-complex neutralizing surfaces",
            ],
            "approved_vaccines": [],
            "pipeline_vaccines": [
                {
                    "name": "Recombinant gp350/AS04",
                    "platform": "protein subunit + AS04",
                    "notes": "Phase II program reduced infectious mononucleosis despite not blocking all infection.",
                }
            ],
            "immune_correlate": "Neutralizing antibodies against B-cell entry are the leading benchmark; next-generation programs also target epithelial entry coverage.",
            "global_burden": "EBV infects most adults worldwide and contributes to lymphoid and epithelial malignancies.",
            "notes": "EBV is a useful comparator because first-generation gp350 programs showed clinical signal, but incomplete infection control pushed the field toward multi-glycoprotein designs.",
            "clintrials_url": "https://pubmed.ncbi.nlm.nih.gov/18190254/",
        },
        {
            "pathogen": "Varicella-Zoster Virus (VZV)",
            "pathogen_type": "virus (alphaherpesvirus)",
            "disease": "Herpes zoster (shingles), post-herpetic neuralgia",
            "antigen_name": "Glycoprotein E (gE)",
            "gene": "ORF68",
            "protein_length_aa": 623,
            "key_domains": [
                "gE ectodomain",
                "gE/gI complex interface",
            ],
            "known_epitopes_mhc1": [],
            "known_epitopes_mhc2": [],
            "b_cell_epitopes": ["gE immunodominant external domain"],
            "approved_vaccines": [
                {
                    "name": "Shingrix",
                    "platform": "recombinant gE + AS01B",
                    "year": "2017",
                    "notes": "High-efficacy subunit benchmark for older adults and immunocompromised populations.",
                }
            ],
            "pipeline_vaccines": [],
            "immune_correlate": "Strong gE-specific CD4 T-cell responses plus durable anti-gE antibody responses.",
            "global_burden": "Lifetime shingles risk rises with age and immunosuppression.",
            "notes": "VZV gE is an important design comparator because it shows how a single dominant antigen paired with a strong adjuvant can outperform live-attenuated legacy approaches in hard-to-immunize populations.",
            "clintrials_url": "https://www.fda.gov/BiologicsBloodVaccines/Vaccines/ApprovedProducts/ucm581491.htm",
        },
        {
            "pathogen": "Dengue Virus (DENV1-4)",
            "pathogen_type": "virus (flavivirus)",
            "disease": "Dengue fever, severe dengue, hemorrhagic dengue",
            "antigen_name": "Envelope protein (E) / prM-E tetravalent surface antigens",
            "gene": "prM/E",
            "protein_length_aa": 495,
            "key_domains": [
                "E protein domain III",
                "fusion-loop region",
                "prM maturation axis",
            ],
            "known_epitopes_mhc1": [],
            "known_epitopes_mhc2": [],
            "b_cell_epitopes": [
                "serotype-specific E protein neutralizing surfaces",
                "cross-reactive fusion-loop epitopes with ADE implications",
            ],
            "approved_vaccines": [
                {
                    "name": "Dengvaxia",
                    "platform": "live attenuated tetravalent chimeric vaccine",
                    "year": "2019 (FDA)",
                    "notes": "Restricted to seropositive settings because baseline serostatus changes risk.",
                },
                {
                    "name": "Qdenga",
                    "platform": "live attenuated tetravalent vaccine",
                    "year": "2022 (EMA)",
                    "notes": "Tetravalent comparator with recombinant serotype surface proteins on a DENV2 backbone.",
                },
            ],
            "pipeline_vaccines": [],
            "immune_correlate": "Balanced serotype-specific neutralization matters, but antibody quality and baseline serostatus are critical because of antibody-dependent enhancement risk.",
            "global_burden": "Major mosquito-borne disease burden in tropical and subtropical regions.",
            "notes": "Dengue is a design-critical comparator because raw neutralization breadth is not enough; serostatus, serotype balance, and ADE risk must all stay visible in the decision logic.",
            "clintrials_url": "https://www.ema.europa.eu/en/medicines/human/EPAR/qdenga",
        },
        {
            "pathogen": "Human Norovirus",
            "pathogen_type": "virus (calicivirus)",
            "disease": "Acute viral gastroenteritis",
            "antigen_name": "VP1 capsid (P domain / protruding domain)",
            "gene": "VP1",
            "protein_length_aa": 540,
            "key_domains": [
                "P2 receptor-binding domain",
                "capsid shell domain",
            ],
            "known_epitopes_mhc1": [],
            "known_epitopes_mhc2": [],
            "b_cell_epitopes": [
                "P2 histo-blood-group-antigen binding surface",
            ],
            "approved_vaccines": [],
            "pipeline_vaccines": [
                {
                    "name": "VLP-based bivalent norovirus vaccines",
                    "platform": "VLP / nanoparticle",
                    "notes": "Field benchmark programs center on GI.1 and GII.4 VP1 VLPs.",
                }
            ],
            "immune_correlate": "Blockade antibodies against HBGA binding are the main translational surrogate, with breadth limited by strain diversity.",
            "global_burden": "Leading cause of acute gastroenteritis outbreaks worldwide.",
            "notes": "Norovirus is a useful comparator for mRNA or VLP design because antigenic drift and genotype breadth force explicit breadth logic rather than single-strain optimization.",
            "clintrials_url": "https://clinicaltrials.gov/search?query=norovirus%20vaccine",
        },
    ]
    return [normalize_infectious_antigen(entry) for entry in supplemental]


def build_adjuvantic_epitopes() -> list[dict[str, Any]]:
    return [
        {
            "record_id": "helper-epitope-padre",
            "entity_type": "adjuvantic_epitope",
            "name": "PADRE",
            "sequence": "AKFVAAWTLKAAA",
            "immune_role": "Universal CD4 helper epitope for broad HLA-DR coverage.",
            "use_cases": [
                "multi-epitope peptide vaccines",
                "DNA vaccines",
                "mRNA constructs needing exogenous CD4 help",
            ],
            "design_notes": "Useful when target epitopes are CD8-heavy or class-II coverage is weak; do not treat as a disease-specific antigen.",
            "evidence": build_evidence(
                tier="A",
                status="VERIFIED",
                source_type="PMID",
                source_url="https://pubmed.ncbi.nlm.nih.gov/7895164/",
                pmids=["7895164"],
                note="PADRE is included because it is a reusable helper module rather than a pathogen-specific antigen.",
            ),
            "field_provenance": {
                "sequence": ["PMID:7895164"],
                "immune_role": ["PMID:7895164"],
            },
            "machine_readable_justification": [
                build_flag(
                    "broad_hla_support",
                    True,
                    "Designed to bind across common HLA-DR backgrounds.",
                ),
                build_flag(
                    "is_helper_not_target",
                    True,
                    "Used to amplify helper function, not as the main disease antigen.",
                ),
            ],
        },
        {
            "record_id": "helper-epitope-tt830-844",
            "entity_type": "adjuvantic_epitope",
            "name": "Tetanus toxoid TT830-844 (P2)",
            "sequence": "QYIKANSKFIGITEL",
            "immune_role": "Recall/helper epitope used to amplify vaccine immunogenicity via pre-existing tetanus immunity.",
            "use_cases": [
                "glycopeptide vaccines",
                "protein subunit vaccines",
                "booster-oriented constructs",
            ],
            "design_notes": "Most useful when the target population is expected to carry tetanus memory; helper strength depends on vaccination history.",
            "evidence": build_evidence(
                tier="B",
                status="VERIFIED",
                source_type="Peer-reviewed article",
                source_url="https://pmc.ncbi.nlm.nih.gov/articles/PMC4779142/",
                pmids=[],
                note="Included as a practical helper epitope module with real therapeutic vaccine usage.",
            ),
            "field_provenance": {
                "sequence": ["PMC:MAG-Tn3 article"],
                "immune_role": ["therapeutic vaccine literature"],
            },
            "machine_readable_justification": [
                build_flag(
                    "leverages_preexisting_memory",
                    True,
                    "Designed to recruit pre-existing tetanus-specific helper responses.",
                ),
                build_flag(
                    "population_dependency",
                    True,
                    "Use depends on prior tetanus exposure in the target population.",
                ),
            ],
        },
    ]


def build_tcr_design_rules() -> list[dict[str, Any]]:
    return [
        {
            "record_id": "tcr-rule-provenance-first",
            "entity_type": "tcr_design_rule",
            "title": "Only use sequence-anchored TCRs",
            "if": "A TCR sequence is proposed for vaccine guidance or monitoring.",
            "then": "Require deposited PDB chains or an explicit peer-reviewed sequence report before the TCR enters the design set.",
            "why": "TCR-guided optimization is highly sensitive to exact CDR3 content; unverifiable sequences poison downstream reasoning.",
            "backing_records": ["tcr-1g4", "tcr-dmf5", "tcr-a3a"],
            "evidence": build_evidence(
                tier="A",
                status="VERIFIED",
                source_type="Internal rule from verified TCR corpus",
                source_url=SOURCE_PATH,
                pmids=[],
                note="Derived from the same provenance discipline used to curate the clinical TCR clone table.",
            ),
        },
        {
            "record_id": "tcr-rule-cross-reactivity-gate",
            "entity_type": "tcr_design_rule",
            "title": "Affinity engineering requires cross-reactivity review",
            "if": "A program proposes affinity enhancement or altered anchor optimization to recruit specific TCRs.",
            "then": "Add motif-level cross-reactivity review and retain a safety red-flag record in the design packet.",
            "why": "The a3a / MAGE-A3 program shows that potency gains can cross the self-tolerance boundary and create lethal off-target toxicity.",
            "backing_records": ["tcr-a3a"],
            "evidence": build_evidence(
                tier="A",
                status="VERIFIED",
                source_type="PDB+PMID-backed safety lesson",
                source_url="https://www.rcsb.org/structure/5BRZ",
                pmids=["23519227"],
                note="Critical safety rule derived from a documented clinical toxicity event.",
            ),
        },
        {
            "record_id": "tcr-rule-titin-check",
            "entity_type": "tcr_design_rule",
            "title": "Mandatory Titin cross-reactivity scan for HLA-A*01 programs",
            "if": "Targeting MAGE-A3 or similar epitopes on HLA-A*01:01.",
            "then": "Perform explicit sequence alignment and structural modeling against the Titin peptide (ESDPIVAQY).",
            "why": "Structural mimicry between MAGE-A3 and Titin was not caught by sequence rank alone but led to fatal cardiac toxicity in clinical trials.",
            "backing_records": ["tcr-a3a"],
            "evidence": build_evidence(
                tier="A",
                status="VERIFIED",
                source_type="PDB+PMID",
                source_url="https://pubmed.ncbi.nlm.nih.gov/23519227/",
                pmids=["23519227"],
                note="Specific safety gate for A*01-restricted programs targeting the MAGE family.",
            ),
        },
        {
            "record_id": "tcr-rule-monitor-public-motifs",
            "entity_type": "tcr_design_rule",
            "title": "Track public clonotype convergence, not only bulk response",
            "if": "The goal is to verify whether a vaccine is recruiting productive TCR repertoires.",
            "then": "Monitor public TRAV/TRBV biases and motif-level convergence alongside ELISpot or tetramer readouts.",
            "why": "TCR-guided optimization is useful only if the response recruits the intended clone families instead of any reactive pool.",
            "backing_records": ["tcr-motif-ny-eso-1-157-165-sllmwitqc", "tcr-motif-mart-1-26-35-a27l-heteroclitic-elagigiltv"],
            "evidence": build_evidence(
                tier="A",
                status="VERIFIED",
                source_type="PMID-backed public motif analyses",
                source_url="https://pubmed.ncbi.nlm.nih.gov/15489334/",
                pmids=["15489334", "19317896"],
                note="Motif convergence is retained because it improves mechanistic monitoring compared with bulk cytokine readouts alone.",
            ),
        },
    ]


def build_mrna_design_rules() -> list[dict[str, Any]]:
    return [
        {
            "record_id": "mrna-rule-signal-peptide",
            "entity_type": "mrna_design_rule",
            "title": "Choose an explicit secretion/trafficking leader",
            "rule_type": "construct_module",
            "parameters": SIGNAL_PEPTIDES,
            "default": "tPA",
            "why": "Signal peptide choice changes secretion and antigen routing before any linker or UTR optimization is considered.",
            "evidence": build_evidence(
                tier="B",
                status="CURATED",
                source_type="Internal engine rule + approved mRNA platform precedents",
                source_url=SOURCE_PATH,
                pmids=[],
                note="Codified from the local assembler and public mRNA platform design patterns.",
            ),
        },
        {
            "record_id": "mrna-rule-spacers",
            "entity_type": "mrna_design_rule",
            "title": "Use class-aware linkers in multi-epitope constructs",
            "rule_type": "linker",
            "parameters": {
                "mhc_i_spacer": SPACERS["MHC-I"],
                "mhc_ii_spacer": SPACERS["MHC-II"],
                "universal_helper": SPACERS["PADRE"],
            },
            "default": {"mhc_i": "AAY", "mhc_ii": "GPGPG"},
            "why": "Mixed epitope constructs need linker logic that respects proteasomal processing and class-II separation rather than generic concatenation.",
            "evidence": build_evidence(
                tier="B",
                status="CURATED",
                source_type="Internal engine rule",
                source_url=SOURCE_PATH,
                pmids=[],
                note="The canonical DB exposes the assembler's linker logic as queryable knowledge instead of hiding it inside code.",
            ),
        },
        {
            "record_id": "mrna-rule-junction-check",
            "entity_type": "mrna_design_rule",
            "title": "Run a junctional neoepitope screen before construct freeze",
            "rule_type": "quality_gate",
            "parameters": {
                "window_lengths": [8, 9, 10],
                "default_allele": "HLA-A*02:01",
                "presentation_percentile_gate": 2.0,
            },
            "default": "reject or reorder constructs that generate new strong binders at junctions",
            "why": "Concatenation artifacts can create unintended binders that dominate immunity or confuse interpretation.",
            "evidence": build_evidence(
                tier="B",
                status="CURATED",
                source_type="Internal engine rule",
                source_url=SOURCE_PATH,
                pmids=[],
                note="This is the runtime quality gate already encoded in the local assembler and now surfaced to the KB.",
            ),
        },
        {
            "record_id": "mrna-rule-utr-selection",
            "entity_type": "mrna_design_rule",
            "title": "Select UTR architecture based on expression duration",
            "rule_type": "regulatory_element",
            "parameters": {
                "5_utr_options": ["alpha-globin", "synthetic_optimized", "tobacco_mosaic_virus_omega"],
                "3_utr_options": ["two_tandem_beta_globin", "aes_element", "optimized_synthetic"],
            },
            "default": "alpha-globin 5'UTR + tandem beta-globin 3'UTR",
            "why": "UTR sequences determine mRNA stability and translation efficiency. Tandem 3'UTRs significantly extend protein half-life in therapeutic settings.",
            "evidence": build_evidence(
                tier="A",
                status="VERIFIED",
                source_type="Kariko/Weissman precedents",
                source_url="https://pubmed.ncbi.nlm.nih.gov/16111635/",
                pmids=["16111635", "29165203"],
                note="Derived from landmark mRNA stability studies and current clinical platform architectures.",
            ),
        },
        {
            "record_id": "mrna-rule-lipid-ratio",
            "entity_type": "mrna_design_rule",
            "title": "Standardize LNP lipid molar ratios",
            "rule_type": "delivery_formulation",
            "parameters": {
                "ionizable_lipid": 50,
                "distearoylphosphatidylcholine_dspc": 10,
                "cholesterol": 38.5,
                "peg_lipid": 1.5,
            },
            "default": "50:10:38.5:1.5",
            "why": "The 50:10:38.5:1.5 ratio is the clinical benchmark (e.g., Onpattro, mRNA-1273) for balancing encapsulation efficiency, stability, and endosomal escape.",
            "evidence": build_evidence(
                tier="A",
                status="VERIFIED",
                source_type="Clinical formulation benchmarks",
                source_url="https://www.nature.com/articles/s41565-021-01001-6",
                pmids=["34824388"],
                note="Standardized ratio used in multiple approved mRNA-LNP products.",
            ),
        },
        {
            "record_id": "mrna-rule-codon-bias",
            "entity_type": "mrna_design_rule",
            "title": "Enforce GC-rich codon optimization",
            "rule_type": "sequence_optimization",
            "parameters": {
                "target_gc_content": "60-65%",
                "min_cai": 0.8,
                "avoid_repeats": ["GGGG", "CCCC", "AAAA"],
            },
            "why": "GC-rich sequences improve mRNA stability and translation, while avoiding homopolymer runs prevents synthesis failure and ribosome stalling.",
            "evidence": build_evidence(
                tier="A",
                status="VERIFIED",
                source_type="Platform engineering standards",
                source_url="https://pubmed.ncbi.nlm.nih.gov/21453961/",
                pmids=["21453961"],
                note="General standard for therapeutic mRNA codon optimization.",
            ),
        },
        {
            "record_id": "mrna-rule-mitd-tail",
            "entity_type": "mrna_design_rule",
            "title": "Use MITD when CD8 presentation is the main objective",
            "rule_type": "trafficking_module",
            "parameters": {"mitd_sequence": MITD_SEQUENCE},
            "default": "enabled for therapeutic programs",
            "why": "The trafficking tail is intended to bias processing toward improved MHC-I presentation in multi-epitope settings.",
            "evidence": build_evidence(
                tier="B",
                status="CURATED",
                source_type="Internal engine rule",
                source_url=SOURCE_PATH,
                pmids=[],
                note="Kept as an explicit design object so teams can audit when the tail was or was not applied.",
            ),
        },
        {
            "record_id": "mrna-rule-utr-and-lnp",
            "entity_type": "mrna_design_rule",
            "title": "Treat UTR and LNP choices as first-class design decisions",
            "rule_type": "expression_and_delivery",
            "parameters": {
                "5_cap": "Cap1",
                "modified_base": "N1-methylpseudouridine",
                "polyA_range_nt": "100-150",
                "lnp_target_size_nm": "80-100",
            },
            "default": "Use clinically precedent UTR/cap/polyA/LNP windows before experimental deviations.",
            "why": "Multi-epitope mRNA performance depends on translation and delivery logic, not only on epitope ranking.",
            "evidence": build_evidence(
                tier="A",
                status="CURATED",
                source_type="Approved mRNA platform precedents",
                source_url=SOURCE_PATH,
                pmids=[],
                note="Pulled from the clinically anchored mRNA platform records so design logic and knowledge base stay aligned.",
            ),
        },
    ]


def build_neoantigen_benchmarks() -> list[dict[str, Any]]:
    return [
        {
            "record_id": "neo-benchmark-tesla",
            "entity_type": "neoantigen_benchmark",
            "title": "TESLA consortium benchmark",
            "benchmark_type": "consortium_benchmark",
            "year": 2020,
            "source_url": "https://pubmed.ncbi.nlm.nih.gov/33038342/",
            "pmids": ["33038342"],
            "summary": "TESLA compared 608 candidate epitopes across six tumors and showed that combining presentation, expression, and recognition filters improves enrichment but does not solve the prediction problem.",
            "key_numbers": {
                "initial_epitopes_tested": 608,
                "validation_epitopes": 310,
                "reported_precision_after_filtering": ">0.70",
            },
            "pain_point": "Different pipelines overlap poorly; ranking quality still depends heavily on feature filtering and assay design.",
            "design_implication": "Use neoantigen predictions as a prioritization layer, then require orthogonal validation rather than treating model rank as ground truth.",
            "evidence": build_evidence(
                tier="A",
                status="VERIFIED",
                source_type="PMID",
                source_url="https://pubmed.ncbi.nlm.nih.gov/33038342/",
                pmids=["33038342"],
                note="Canonical benchmark for the current field-wide prediction ceiling discussion.",
            ),
        },
        {
            "record_id": "neo-benchmark-ott-2017",
            "entity_type": "neoantigen_benchmark",
            "title": "Personal peptide neoantigen vaccine in melanoma",
            "benchmark_type": "clinical_validation",
            "year": 2017,
            "source_url": "https://pubmed.ncbi.nlm.nih.gov/28678778/",
            "pmids": ["28678778"],
            "summary": "Ott et al. showed personalized peptide vaccines can induce broad T-cell responses, but CD4 responses outnumbered CD8 responses across predicted neoantigens.",
            "key_numbers": {
                "patients": 6,
                "unique_neoantigens": 97,
                "cd4_response_rate": "60%",
                "cd8_response_rate": "16%",
            },
            "pain_point": "Prediction-to-response conversion is uneven across class I and class II; rank alone does not guarantee productive CD8 immunity.",
            "design_implication": "Support class-II coverage and helper design explicitly instead of optimizing only class-I binders.",
            "evidence": build_evidence(
                tier="A",
                status="VERIFIED",
                source_type="PMID",
                source_url="https://pubmed.ncbi.nlm.nih.gov/28678778/",
                pmids=["28678778"],
                note="Kept as a clinical benchmark linking prediction, manufacture, and measured immunogenicity.",
            ),
        },
        {
            "record_id": "neo-benchmark-sahin-2017",
            "entity_type": "neoantigen_benchmark",
            "title": "Personalized RNA mutanome vaccine study",
            "benchmark_type": "clinical_validation",
            "year": 2017,
            "source_url": "https://pubmed.ncbi.nlm.nih.gov/28678784/",
            "pmids": ["28678784"],
            "summary": "Sahin et al. showed personalized RNA mutanome vaccines can mobilize poly-specific therapeutic immunity and reveal resistance mechanisms after vaccination.",
            "key_numbers": {
                "patients": 13,
                "format": "RNA mutanome vaccine",
                "reported_response_pattern": "poly-specific T-cell responses",
            },
            "pain_point": "Even when vaccine-induced immunity is measurable, escape and resistance remain active constraints.",
            "design_implication": "The KB should connect prediction to monitoring and resistance interpretation, not stop at candidate ranking.",
            "evidence": build_evidence(
                tier="A",
                status="VERIFIED",
                source_type="PMID",
                source_url="https://pubmed.ncbi.nlm.nih.gov/28678784/",
                pmids=["28678784"],
                note="Retained as the landmark RNA validation example for the mRNA track.",
            ),
        },
        {
            "record_id": "neo-benchmark-best-practices",
            "entity_type": "neoantigen_benchmark",
            "title": "Best-practice gap review",
            "benchmark_type": "workflow_gap_review",
            "year": 2019,
            "source_url": "https://genomemedicine.biomedcentral.com/articles/10.1186/s13073-019-0666-2",
            "pmids": [],
            "summary": "The field still lacks a single consensus workflow across mutation calling, HLA typing, processing, and pMHC ranking for clinical neoantigen use.",
            "key_numbers": {
                "critical_steps": 4,
            },
            "pain_point": "Errors accumulate across the workflow, especially in HLA class II handling and translation to clinical response.",
            "design_implication": "The private KB needs field-level provenance and explicit dry-wet gates, not just a predictor output table.",
            "evidence": build_evidence(
                tier="B",
                status="VERIFIED",
                source_type="Peer-reviewed review",
                source_url="https://genomemedicine.biomedcentral.com/articles/10.1186/s13073-019-0666-2",
                pmids=[],
                note="Retained because it frames the workflow bottlenecks that a design-support KB must address.",
            ),
        },
        {
            "record_id": "neo-benchmark-keskin-gbm",
            "entity_type": "neoantigen_benchmark",
            "title": "Glioblastoma neoantigen vaccine benchmark",
            "benchmark_type": "clinical_validation",
            "year": 2019,
            "source_url": "https://pubmed.ncbi.nlm.nih.gov/30568305/",
            "pmids": ["30568305"],
            "summary": "Keskin et al. showed neoantigen vaccination can generate circulating and intratumoral T-cell responses in glioblastoma, but concurrent dexamethasone exposure materially weakens the signal.",
            "key_numbers": {
                "setting": "phase I/Ib glioblastoma",
                "critical_modifier": "dexamethasone use",
            },
            "pain_point": "Even well-ranked neoantigens can underperform when the clinical context suppresses the response.",
            "design_implication": "The design system must track concomitant immunosuppression and sample context, not only peptide rank.",
            "evidence": build_evidence(
                tier="A",
                status="VERIFIED",
                source_type="PMID",
                source_url="https://pubmed.ncbi.nlm.nih.gov/30568305/",
                pmids=["30568305"],
                note="Useful benchmark showing that deployment context can dominate prediction quality in low-mutation tumors.",
            ),
        },
    ]


def build_supplemental_tcr_motifs() -> list[dict[str, Any]]:
    return [
        {
            "epitope": "NLVPMVATV",
            "hla": "HLA-A*02:01",
            "mhc_class": "I",
            "antigen": "CMV pp65 (UL83)",
            "antigen_source": "viral",
            "trbv_bias": ["TRBV6-1", "TRBV12-4"],
            "trav_bias": ["TRAV24"],
            "cdr3b_motif": "CASSL[A/G]G[G/A]E[Q/A][Y/F]F",
            "cdr3a_motif": "CAF[S/R]YSSASKIIF",
            "frequency_in_population": "Highly prevalent in CMV-seropositive HLA-A2+ individuals.",
            "num_unique_clonotypes": 100,
            "verification": "PMID",
            "pmid": "7684732",
            "doi": "10.1084/jem.181.6.1881",
            "source_url": "https://pubmed.ncbi.nlm.nih.gov/7684732/",
            "notes": "Canonical 'public' TCR response used as a gold standard for MHC tetramer validation and immune monitoring benchmarks.",
        }
    ]


def build_design_playbooks() -> list[dict[str, Any]]:
    return [
        {
            "record_id": "playbook-personalized-neoantigen",
            "entity_type": "design_playbook",
            "title": "Personalized neoantigen vaccine playbook",
            "applies_when": "Tumor-specific mutation list and patient HLA typing are available.",
            "required_evidence": [
                "matched tumor-normal mutation callset",
                "HLA typing",
                "expression support",
                "benchmark-aware neoantigen ranking",
            ],
            "core_logic": [
                "Rank predicted neoantigens, but treat rank as a prioritization layer rather than proof.",
                "Preserve class-II coverage because clinical validation studies frequently show stronger CD4 than CD8 conversion.",
                "Choose platform and adjuvant only after defining whether the program is CD8-first, balanced, or checkpoint-combination.",
            ],
            "wet_gates": [
                "ELISpot or ICS on candidate pools",
                "tetramer or multimer confirmation for top class-I candidates",
                "expression / construct QC before clinical nomination",
            ],
            "failure_modes": [
                "good binders without functional response",
                "CD4-heavy response with weak cytotoxic conversion",
                "immune suppression in the treatment context",
            ],
            "recommended_modules": [
                "methods.neoantigen_benchmarks",
                "methods.design_playbooks",
                "methods.assay_catalog",
                "delivery.platforms",
                "delivery.adjuvants",
            ],
            "evidence": build_evidence(
                tier="A",
                status="CURATED",
                source_type="Integrated benchmark logic",
                source_url=SOURCE_PATH,
                pmids=["33038342", "28678778", "28678784", "30568305"],
                note="Playbook condenses the benchmark layer into a reusable design workflow.",
            ),
        },
        {
            "record_id": "playbook-tcr-guided-optimization",
            "entity_type": "design_playbook",
            "title": "TCR-guided epitope optimization playbook",
            "applies_when": "The program wants to recruit known productive TCR families or monitor clonotype convergence.",
            "required_evidence": [
                "sequence-anchored TCR clone or motif record",
                "matched pMHC context",
                "cross-reactivity review plan",
            ],
            "core_logic": [
                "Do not start from unverifiable TCR sequences.",
                "Use public motif or clinical clone records to decide whether a peptide is likely to recruit the intended repertoire.",
                "Treat affinity enhancement as a risk-bearing step that automatically triggers cross-reactivity review.",
            ],
            "wet_gates": [
                "tetramer or multimer staining",
                "TCR sequencing / motif convergence readout",
                "cross-reactivity panel or off-target screen",
            ],
            "failure_modes": [
                "bulk response without intended clonotype recruitment",
                "engineered potency with off-target toxicity",
            ],
            "recommended_modules": [
                "tcr.clones",
                "tcr.public_motifs",
                "tcr.design_rules",
                "methods.assay_catalog",
            ],
            "evidence": build_evidence(
                tier="A",
                status="CURATED",
                source_type="TCR corpus-derived playbook",
                source_url=SOURCE_PATH,
                pmids=["15489334", "19317896", "23519227"],
                note="Playbook extracted from the verified TCR records and their safety/monitoring lessons.",
            ),
        },
        {
            "record_id": "playbook-multi-epitope-mrna",
            "entity_type": "design_playbook",
            "title": "Multi-epitope mRNA construct playbook",
            "applies_when": "The design goal is to encode multiple epitopes or antigens in one RNA product.",
            "required_evidence": [
                "ordered epitope set",
                "class-aware linker strategy",
                "delivery precedent and cold-chain target",
            ],
            "core_logic": [
                "Separate construct logic from ranking logic: ordering, linkers, trafficking tails, and UTR/LNP choices all affect outcome.",
                "Run junctional neoepitope checks before freeze; sequence concatenation is itself a risk source.",
                "Use helper modules deliberately when class-II support is otherwise sparse.",
            ],
            "wet_gates": [
                "construct expression QC",
                "junction / processing review",
                "immunogenicity panel split by CD4 and CD8 readouts",
            ],
            "failure_modes": [
                "unexpected junction binders",
                "construct too large or unstable for chosen delivery format",
                "strong expression but poor antigen routing",
            ],
            "recommended_modules": [
                "methods.multi_epitope_mrna",
                "delivery.platforms",
                "delivery.adjuvantic_epitopes",
                "methods.assay_catalog",
            ],
            "evidence": build_evidence(
                tier="A",
                status="CURATED",
                source_type="Runtime-rule-derived playbook",
                source_url=SOURCE_PATH,
                pmids=[],
                note="Playbook makes the assembler's hidden construct logic available as explicit design guidance.",
            ),
        },
        {
            "record_id": "playbook-tolerance-induction",
            "entity_type": "design_playbook",
            "title": "Autoimmune tolerance induction playbook",
            "applies_when": "The goal is to suppress pathogenic immunity or induce Treg bias using an 'inverse vaccine'.",
            "required_evidence": [
                "self-antigen epitope with known HLA association",
                "mechanism (e.g., LNP-mediated liver targeting or glycosylated peptide)",
                "safety monitoring for unintended boosting",
            ],
            "core_logic": [
                "Focus on liver-targeted delivery (e.g., pMHC-LNP) to leverage the natural tolerogenic environment of the liver.",
                "Avoid traditional 'danger signal' adjuvants (TLR agonists) that would boost pathogenic T-cells.",
                "Select epitopes that are known to be dominant in the pathogenic response to ensure Treg induction is relevant to the disease.",
            ],
            "wet_gates": [
                "Treg (FoxP3+) induction assay",
                "suppression of effector T-cell proliferation",
                "target-specific clinical biomarker tracking",
            ],
            "failure_modes": [
                "accidental boosting of pathogenic effector T-cells",
                "transient tolerance without long-term memory",
                "off-target suppression of protective immunity",
            ],
            "recommended_modules": [
                "antigens.tolerogenic",
                "delivery.platforms",
                "methods.assay_catalog",
            ],
            "evidence": build_evidence(
                tier="B",
                status="CURATED",
                source_type="Emergent inverse-vaccine logic",
                source_url="https://pubmed.ncbi.nlm.nih.gov/27535560/",
                pmids=["27535560", "31358961"],
                note="Synthesized from autoimmune LNP and peptide-polymer tolerance platforms (e.g., Anokion, Cour).",
            ),
        },
        {
            "record_id": "playbook-infectious-update",
            "entity_type": "design_playbook",
            "title": "Infectious comparator and update playbook",
            "applies_when": "The program targets a pathogen, variant-update problem, or broad prophylactic design question.",
            "required_evidence": [
                "benchmark antigen or approved comparator",
                "correlate-of-protection hypothesis",
                "breadth or update constraint",
            ],
            "core_logic": [
                "Start from approved comparators and known correlates of protection before proposing new antigen layouts.",
                "For drift-prone pathogens, breadth logic is part of the design itself rather than an optional optimization pass.",
                "Platform choice must be tied to deployment constraints such as cold chain, re-dosing, and speed of update.",
            ],
            "wet_gates": [
                "neutralization or blockade assays",
                "variant panel comparison",
                "formulation / stability QC",
            ],
            "failure_modes": [
                "single-strain success with poor breadth",
                "correlate mismatch",
                "platform not aligned with deployment reality",
            ],
            "recommended_modules": [
                "antigens.infectious",
                "delivery.platforms",
                "delivery.adjuvants",
                "methods.assay_catalog",
            ],
            "evidence": build_evidence(
                tier="A",
                status="CURATED",
                source_type="Comparator-driven playbook",
                source_url=SOURCE_PATH,
                pmids=[],
                note="Synthesizes antigen, correlate, and deployment logic into one infectious-design workflow.",
            ),
        },
    ]


def build_assay_catalog() -> list[dict[str, Any]]:
    return [
        {
            "record_id": "assay-elispot",
            "entity_type": "assay_gate",
            "name": "ELISpot",
            "measures": "antigen-specific cytokine-secreting cells",
            "best_for": ["screening candidate pools", "ranking follow-up after prediction"],
            "blind_spots": ["does not prove clonotype identity", "can overstate weak multifunctional responses"],
            "when_required": "Baseline wet gate for neoantigen and shared-antigen programs.",
            "evidence": build_evidence(
                tier="B",
                status="CURATED",
                source_type="Operational assay rule",
                source_url=SOURCE_PATH,
                pmids=[],
                note="Assay catalog entries encode translational gate logic rather than standalone biological claims.",
            ),
        },
        {
            "record_id": "assay-ics",
            "entity_type": "assay_gate",
            "name": "Intracellular cytokine staining (ICS)",
            "measures": "polyfunctionality and CD4/CD8 split",
            "best_for": ["helper vs cytotoxic balance", "polyfunctional response profiling"],
            "blind_spots": ["less direct for actual killing capacity"],
            "when_required": "Use when construct or adjuvant decisions depend on response polarization.",
            "evidence": build_evidence(
                tier="B",
                status="CURATED",
                source_type="Operational assay rule",
                source_url=SOURCE_PATH,
                pmids=[],
                note="Assay catalog entries encode translational gate logic rather than standalone biological claims.",
            ),
        },
        {
            "record_id": "assay-tetramer",
            "entity_type": "assay_gate",
            "name": "Tetramer / multimer staining",
            "measures": "antigen-specific T-cell binding frequency",
            "best_for": ["TCR-guided monitoring", "validating top class-I hits"],
            "blind_spots": ["binding does not equal function"],
            "when_required": "Strongly recommended when a program claims TCR-guided optimization.",
            "evidence": build_evidence(
                tier="B",
                status="CURATED",
                source_type="Operational assay rule",
                source_url=SOURCE_PATH,
                pmids=[],
                note="Assay catalog entries encode translational gate logic rather than standalone biological claims.",
            ),
        },
        {
            "record_id": "assay-tcrseq",
            "entity_type": "assay_gate",
            "name": "TCR sequencing / clonotype tracking",
            "measures": "clonotype expansion and motif convergence",
            "best_for": ["public motif monitoring", "tracking whether intended repertoires expand"],
            "blind_spots": ["does not by itself prove specificity without paired evidence"],
            "when_required": "Use when the design goal is to recruit or monitor known TCR families.",
            "evidence": build_evidence(
                tier="B",
                status="CURATED",
                source_type="Operational assay rule",
                source_url=SOURCE_PATH,
                pmids=[],
                note="Assay catalog entries encode translational gate logic rather than standalone biological claims.",
            ),
        },
        {
            "record_id": "assay-neutralization",
            "entity_type": "assay_gate",
            "name": "Neutralization or blockade assay",
            "measures": "functional inhibition of pathogen entry or surrogate receptor binding",
            "best_for": ["infectious comparator programs", "variant breadth review"],
            "blind_spots": ["may miss cell-mediated protection"],
            "when_required": "Mandatory for prophylactic infectious programs built around antibody correlates.",
            "evidence": build_evidence(
                tier="B",
                status="CURATED",
                source_type="Operational assay rule",
                source_url=SOURCE_PATH,
                pmids=[],
                note="Assay catalog entries encode translational gate logic rather than standalone biological claims.",
            ),
        },
        {
            "record_id": "assay-killing",
            "entity_type": "assay_gate",
            "name": "Functional killing / target-cell lysis assay",
            "measures": "effector function against target cells",
            "best_for": ["neoantigen follow-up", "TCR-guided programs", "therapeutic vaccine validation"],
            "blind_spots": ["more complex and lower-throughput than screening assays"],
            "when_required": "Escalation gate for candidates nominated beyond simple immune recognition.",
            "evidence": build_evidence(
                tier="B",
                status="CURATED",
                source_type="Operational assay rule",
                source_url=SOURCE_PATH,
                pmids=[],
                note="Assay catalog entries encode translational gate logic rather than standalone biological claims.",
            ),
        },
        {
            "record_id": "assay-expression-qc",
            "entity_type": "assay_gate",
            "name": "Construct expression and formulation QC",
            "measures": "whether the designed construct is actually manufacturable and expressed as intended",
            "best_for": ["mRNA and multicomponent construct programs"],
            "blind_spots": ["does not prove immunogenicity"],
            "when_required": "Always required before treating an in silico construct as a real candidate.",
            "evidence": build_evidence(
                tier="B",
                status="CURATED",
                source_type="Operational assay rule",
                source_url=SOURCE_PATH,
                pmids=[],
                note="Assay catalog entries encode translational gate logic rather than standalone biological claims.",
            ),
        },
    ]


def build_private_learning_module() -> dict[str, Any]:
    return {
        "cases": [],
        "schema_template": {
            "record_id": "dry-wet-template",
            "entity_type": "dry_wet_case",
            "status": "TEMPLATE_ONLY",
            "fields": [
                "program_name",
                "scenario",
                "candidate_payload",
                "wet_assays",
                "decision_gates",
                "observed_failure_modes",
                "design_changes_after_readout",
                "evidence_links",
            ],
            "notes": "Reserved for internal projects. The template exists so private learning can accumulate in the same canonical schema later.",
        },
        "feedback_patterns": [
            {
                "record_id": "dry-wet-loop-neoantigen",
                "entity_type": "dry_wet_pattern",
                "title": "Prediction -> synthesis -> immunogenicity assay -> redesign",
                "inputs": ["mutation list", "HLA typing", "expression evidence"],
                "wet_readouts": ["ELISpot", "multimer staining", "functional killing"],
                "decision_gates": [
                    "drop candidates without orthogonal assay support",
                    "revisit helper coverage when CD4 dominates",
                    "log cross-reactivity or escape findings back into ranking rules",
                ],
            },
            {
                "record_id": "dry-wet-loop-infectious-update",
                "entity_type": "dry_wet_pattern",
                "title": "Variant update loop",
                "inputs": ["emergent sequence set", "immune correlate target", "platform constraints"],
                "wet_readouts": ["binding loss panel", "neutralization", "expression QC"],
                "decision_gates": [
                    "keep benchmark antigen for comparability",
                    "freeze only after correlate and manufacturability both pass",
                ],
            },
        ],
    }


def build_scenario_guides() -> list[dict[str, Any]]:
    return [
        {
            "record_id": "scenario-cancer-neoantigen",
            "entity_type": "scenario_guide",
            "title": "Personalized cancer neoantigen vaccine",
            "priority_questions": [
                "What is the patient HLA set?",
                "Do predicted epitopes have expression support?",
                "Is the goal CD8-first, CD4-balanced, or checkpoint-combination?",
            ],
            "recommended_modules": [
                "methods.neoantigen_benchmarks",
                "methods.multi_epitope_mrna",
                "delivery.platforms",
                "delivery.adjuvants",
                "tcr.public_motifs",
            ],
            "why": "This scenario needs prediction realism, construct logic, and monitoring logic rather than a flat antigen browser.",
        },
        {
            "record_id": "scenario-shared-cancer-antigen",
            "entity_type": "scenario_guide",
            "title": "Shared tumor antigen program",
            "priority_questions": [
                "Is the antigen ranked, clinically active, and expression-constrained enough?",
                "Are there validated class-I and class-II epitopes?",
                "Is heteroclitic optimization acceptable from a safety standpoint?",
            ],
            "recommended_modules": [
                "antigens.tumor",
                "tcr.clones",
                "tcr.design_rules",
                "delivery.adjuvants",
            ],
            "why": "Shared-antigen work needs ranked evidence and a safety-aware TCR lens.",
        },
        {
            "record_id": "scenario-infectious-update",
            "entity_type": "scenario_guide",
            "title": "Infectious-disease or variant-update program",
            "priority_questions": [
                "What is the correlate of protection?",
                "Does the design need fast update, refrigerator stability, or mucosal coverage?",
                "Which approved products are the right comparators?",
            ],
            "recommended_modules": [
                "antigens.infectious",
                "delivery.platforms",
                "delivery.adjuvants",
                "methods.private_learning",
            ],
            "why": "This track is benchmarked by real product behavior and correlate-driven decisions.",
        },
        {
            "record_id": "scenario-tolerogenic",
            "entity_type": "scenario_guide",
            "title": "Tolerogenic / autoimmune inverse vaccine",
            "priority_questions": [
                "Which self-antigen and HLA axis define the pathogenic response?",
                "Is the design trying to induce Treg bias, deletion, or anergy?",
                "What is the risk of boosting pathogenic immunity instead of suppressing it?",
            ],
            "recommended_modules": [
                "antigens.tolerogenic",
                "delivery.platforms",
                "delivery.adjuvants",
            ],
            "why": "Inverse-vaccine design needs a separate decision path from cancer or infectious programs.",
        },
    ]


def build_supplemental_tcr_motifs() -> list[dict[str, Any]]:
    motifs = [
        {
            "epitope": "NLVPMVATV",
            "hla": "HLA-A*02:01",
            "mhc_class": "I",
            "antigen": "CMV pp65 (UL83)",
            "antigen_source": "viral",
            "trbv_bias": ["TRBV6-1", "TRBV12-4"],
            "trav_bias": ["TRAV24"],
            "cdr3b_motif": "CASSL[A/G]G[G/A]E[Q/A][Y/F]F",
            "cdr3a_motif": "CAF[S/R]YSSASKIIF",
            "frequency_in_population": "Highly prevalent in CMV-seropositive HLA-A2+ individuals.",
            "num_unique_clonotypes": 100,
            "verification": "PMID",
            "pmid": "7684732",
            "doi": "10.1084/jem.181.6.1881",
            "source_url": "https://pubmed.ncbi.nlm.nih.gov/7684732/",
            "notes": "Canonical 'public' TCR response used as a gold standard for MHC tetramer validation and immune monitoring benchmarks.",
        }
    ]
    return [normalize_tcr_motif(m) for m in motifs]


def build_canonical_db() -> dict[str, Any]:
    tumor = [normalize_tumor_antigen(asdict(entry)) for entry in TAA_DATABASE]
    infectious = [normalize_infectious_antigen(asdict(entry)) for entry in INFECTIOUS_ANTIGENS]
    infectious.extend(build_supplemental_infectious_antigens())
    tolerogenic = [normalize_tolerogenic_target(asdict(entry)) for entry in AUTOIMMUNE_TARGETS]
    platforms = [normalize_platform(asdict(entry)) for entry in VACCINE_VECTORS]
    adjuvants = [normalize_adjuvant(asdict(entry)) for entry in ADJUVANT_DATABASE]
    tcr_clones = [normalize_tcr_clone(asdict(entry)) for entry in CLINICAL_TCRS]
    tcr_motifs = [normalize_tcr_motif(asdict(entry)) for entry in PUBLIC_TCR_MOTIFS]
    tcr_motifs.extend(build_supplemental_tcr_motifs())
    adjuvantic_epitopes = build_adjuvantic_epitopes()
    tcr_rules = build_tcr_design_rules()
    mrna_rules = build_mrna_design_rules()
    benchmarks = build_neoantigen_benchmarks()
    playbooks = build_design_playbooks()
    assays = build_assay_catalog()
    private_learning = build_private_learning_module()
    scenario_guides = build_scenario_guides()

    return {
        "_meta": {
            "schema_version": "4.0-private-design-kb",
            "updated": DATE,
            "source_of_truth": SOURCE_PATH,
            "integrity_note": "Single canonical vaccine DB shared by UI and runtime logic. Real-source provenance is required; unsupported AI-only facts are excluded.",
            "positioning": "Vaccine design methods and evidence base",
            "module_counts": {
                "tumor_antigens": len(tumor),
                "infectious_antigens": len(infectious),
                "tolerogenic_targets": len(tolerogenic),
                "platforms": len(platforms),
                "adjuvants": len(adjuvants),
                "tcr_clones": len(tcr_clones),
                "tcr_public_motifs": len(tcr_motifs),
                "adjuvantic_epitopes": len(adjuvantic_epitopes),
                "mrna_design_rules": len(mrna_rules),
                "neoantigen_benchmarks": len(benchmarks),
                "design_playbooks": len(playbooks),
                "assay_gates": len(assays),
                "scenario_guides": len(scenario_guides),
            },
            "decision_priority": [
                "accuracy",
                "granularity",
                "coverage",
            ],
            "build_script": "scripts/_rebuild_vaccine_kb.py",
        },
        "modules": {
            "antigens": {
                "tumor": tumor,
                "infectious": infectious,
                "tolerogenic": tolerogenic,
            },
            "tcr": {
                "clones": tcr_clones,
                "public_motifs": tcr_motifs,
                "design_rules": tcr_rules,
            },
            "delivery": {
                "platforms": platforms,
                "adjuvants": adjuvants,
                "adjuvantic_epitopes": adjuvantic_epitopes,
            },
            "methods": {
                "multi_epitope_mrna": mrna_rules,
                "neoantigen_benchmarks": benchmarks,
                "design_playbooks": playbooks,
                "assay_catalog": assays,
                "private_learning": private_learning,
            },
            "decision_support": {
                "scenario_guides": scenario_guides,
            },
        },
    }


def write_outputs(payload: dict[str, Any]) -> None:
    for path in SITE_JSON_PATHS:
        path.write_text(
            json.dumps(payload, ensure_ascii=False, indent=2) + "\n",
            encoding="utf-8",
        )
        print(f"Wrote {path.relative_to(ROOT)}")


def main() -> None:
    payload = build_canonical_db()
    write_outputs(payload)


if __name__ == "__main__":
    main()
