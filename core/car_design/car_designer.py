"""
CARDesigner — main entry point for the InSynBio CAR-T Design Engine.
Takes (target, indication, cell_type) → optimal construct with rationale.
"""
from __future__ import annotations
import json
from pathlib import Path
from typing import Any

from .rule_validator import RuleValidator
from .construct_scorer import ConstructScorer
from .fasta_assembler import FASTAAssembler
from .decision_advisor import DecisionAdvisor
from .plasmid_map import PlasmidMapGenerator
from .knowledge_enricher import KnowledgeEnricher

_DATA_DIR = Path(__file__).resolve().parents[2] / "data" / "CAR"


class CARDesigner:
    """
    Intelligent CAR construct designer.

    Usage:
        designer = CARDesigner()
        result = designer.design(target="CD19", indication="B_ALL")
        print(result["rationale"])
        print(result["fasta"])
    """

    def __init__(self, data_dir: Path | str | None = None):
        data = Path(data_dir) if data_dir else _DATA_DIR
        self._library = self._load(data / "CART_LIBRARY_V3.json")
        self._constructs = self._load(data / "clinical_constructs.json")
        self._rules = self._load(data / "design_rules.json")
        self._templates = self._load(data / "design_templates.json")
        self._indications = self._load(data / "indication_guide.json")

        self._framework = self._load(data / "decision_framework.json")

        self._lib_idx: dict[str, dict] = {
            e["id"]: e for e in self._library.get("elements", [])
        }
        self._clinical_human_elements = self._collect_clinical_human_elements()

        self._validator = RuleValidator(self._rules, self._lib_idx)
        self._scorer = ConstructScorer(self._lib_idx, self._constructs, self._rules)
        self._assembler = FASTAAssembler(self._lib_idx)
        self._advisor = DecisionAdvisor(self._framework, self._indications)
        self._plasmid_gen = PlasmidMapGenerator(self._lib_idx)
        self._enricher = KnowledgeEnricher(enable_api=True)

    @staticmethod
    def _load(path: Path) -> dict:
        if not path.exists():
            return {}
        return json.loads(path.read_text(encoding="utf-8"))

    def decision_advisor(
        self,
        target: str,
        indication: str,
        cell_type: str | None = None,
        delivery: str | None = None,
        patient_fitness: str = "moderate_prior_therapy",
        regulatory_goal: str = "clinical_fast_track",
        secondary_target: str | None = None,
        strict_evidence_only: bool = True,
        enable_knowledge: bool = True,
    ) -> dict:
        """Walk through the decision layers and return structured recommendations.

        When enable_knowledge=True (default), the Knowledge Bridge auto-queries
        UniProt, PubMed, PDB, and ADA tiered_db to enrich D2 and D8.

        Returns a dict with keys D1..D11, recommended_elements, and summary.
        """
        enrichment = None
        if enable_knowledge:
            enrichment = self._enricher.enrich(target, indication)

        return self._advisor.advise(
            target=target,
            indication=indication,
            cell_type=cell_type,
            delivery=delivery,
            patient_fitness=patient_fitness,
            regulatory_goal=regulatory_goal,
            secondary_target=secondary_target,
            strict_evidence_only=strict_evidence_only,
            knowledge_enrichment=enrichment,
        )

    def audit_decision(
        self,
        target: str,
        indication: str,
        cell_type: str | None = None,
        delivery: str | None = None,
        patient_fitness: str = "moderate_prior_therapy",
        regulatory_goal: str = "clinical_fast_track",
        secondary_target: str | None = None,
        strict_evidence_only: bool = True,
    ) -> dict:
        """Return evidence and filtering audit without assembling a construct."""
        advisory = self.decision_advisor(
            target=target,
            indication=indication,
            cell_type=cell_type,
            delivery=delivery,
            patient_fitness=patient_fitness,
            regulatory_goal=regulatory_goal,
            secondary_target=secondary_target,
            strict_evidence_only=strict_evidence_only,
        )
        template_name, template = self._select_template(indication, cell_type or "T", "standard")
        return {
            "advisor_audit": advisory.get("audit", {}),
            "template_filter_audit": self._build_template_filter_audit(
                indication, template_name, template, strict_evidence_only
            ),
        }

    def design(
        self,
        target: str,
        indication: str | None = None,
        cell_type: str = "T",
        mode: str = "standard",
        extra_elements: list[str] | None = None,
        use_advisor: bool = True,
        patient_fitness: str = "moderate_prior_therapy",
        regulatory_goal: str = "clinical_fast_track",
        secondary_target: str | None = None,
        strict_evidence_only: bool = True,
        enable_knowledge: bool = True,
    ) -> dict:
        """
        Design a CAR construct for a given target and indication.

        When *use_advisor* is True (default) and an indication is provided,
        the 11-layer DecisionAdvisor is invoked first.  Its element
        recommendations are merged into the template-based selection, and the
        full per-layer reasoning is included in the output.

        When *enable_knowledge* is True (default), the Knowledge Bridge
        auto-queries UniProt/PubMed/PDB/ADA to enrich D2 and D8.

        Args:
            target: Antigen name (e.g., "CD19", "BCMA", "Mesothelin")
            indication: Disease key from indication_guide (e.g., "B_ALL", "multiple_myeloma")
            cell_type: "T", "NK", "macrophage", "regulatory_T", "iNKT"
            mode: "standard", "armored", "tandem", "logic_AND", "logic_NOT", "allogeneic"
            extra_elements: Additional element IDs to include
            use_advisor: Whether to run the decision advisor
            patient_fitness: "healthy_donor", "moderate_prior_therapy", "heavily_pretreated", "rapid_progression"
            regulatory_goal: "clinical_fast_track", "advanced_research"
            secondary_target: Optional second antigen for logic gates
            strict_evidence_only: If True, default recommendations exclude concept/preclinical rules
            enable_knowledge: If True, run Knowledge Engine queries

        Returns:
            dict with keys: elements, template, rationale, validation, score, fasta, domain_map, decision_layers (if advisor used)
        """
        advisory: dict | None = None
        enrichment: dict | None = None
        if use_advisor and indication:
            if enable_knowledge:
                enrichment = self._enricher.enrich(target, indication)
            advisory = self._advisor.advise(
                target=target,
                indication=indication,
                cell_type=cell_type if cell_type != "T" else None,
                patient_fitness=patient_fitness,
                regulatory_goal=regulatory_goal,
                secondary_target=secondary_target,
                strict_evidence_only=strict_evidence_only,
                knowledge_enrichment=enrichment,
            )

        template_name, template = self._select_template(indication, cell_type, mode)
        binder = self._select_binder(target, indication)
        elements = self._fill_template(
            template,
            binder,
            indication,
            cell_type,
            mode,
            strict_evidence_only=strict_evidence_only,
        )

        if advisory:
            elements = self._apply_core_assembly_overrides(elements, advisory)
            for bucket in advisory.get("recommended_elements", {}).values():
                for eid in bucket:
                    if eid in self._lib_idx:
                        elements.append(eid)

        if extra_elements:
            elements.extend(extra_elements)

        elements = list(dict.fromkeys(elements))

        grammar = template.get("grammar")
        validation = self._validator.validate(elements, grammar, cell_type)
        score = self._scorer.score(elements, validation)
        assembly = self._assembler.assemble(elements, f"CAR_{target}_{mode}")
        rationale = self._build_rationale(
            target, indication, cell_type, mode, template_name,
            binder, elements, validation, score, advisory,
        )

        result: dict[str, Any] = {
            "target": target,
            "indication": indication,
            "cell_type": cell_type,
            "mode": mode,
            "template_used": template_name,
            "elements": elements,
            "element_details": [
                {
                    "id": eid,
                    "name": self._lib_idx.get(eid, {}).get("name", "?"),
                    "category": self._lib_idx.get(eid, {}).get("category", "?"),
                }
                for eid in elements
            ],
            "validation": validation,
            "score": score,
            "fasta": assembly["fasta"],
            "annotated_fasta": assembly["annotated_fasta"],
            "domain_map": assembly["domain_map"],
            "total_length_aa": assembly["total_length_aa"],
            "rationale": rationale,
        }

        if advisory:
            decision_layers = {
                k: v for k, v in advisory.items()
                if k.startswith("D") and (k[1:2].isdigit() or k.startswith("D_core"))
            }
            result["decision_layers"] = decision_layers
            result["decision_summary"] = advisory.get("summary", "")
            if advisory.get("knowledge_enrichment"):
                result["knowledge_enrichment"] = advisory["knowledge_enrichment"]
            if advisory.get("ada_risk_assessment"):
                result["ada_risk_assessment"] = advisory["ada_risk_assessment"]
            result["evidence_audit"] = {
                "advisor_audit": advisory.get("audit", {}),
                "template_filter_audit": self._build_template_filter_audit(
                    indication, template_name, template, strict_evidence_only
                ),
            }

        if enrichment:
            result["evidence_context"] = self._build_evidence_context(
                target, enrichment
            )

        return result

    @staticmethod
    def _build_evidence_context(target: str, enrichment: dict) -> dict:
        """Convert KnowledgeEnricher output into EvidenceContext-compatible dict.

        This allows the report layer (client_report.py) to render Tier labels,
        PMID evidence, and uncertainty disclaimers for CAR-T reports.
        """
        ada = enrichment.get("ada_risk", {})
        entries = ada.get("entries", [])

        tier_map = {
            "Tier1_Verified": "TIER1",
            "Tier2_Proprietary": "TIER2",
            "Tier3_Untraceable": "TIER3",
        }
        highest_tier = ada.get("highest_tier", "")
        ada_tier = tier_map.get(highest_tier, "NOT_FOUND")

        ada_value = None
        ada_evidence = None
        if entries:
            first = entries[0]
            ada_value = first.get("ada_value")
            ada_evidence = first.get("pmid")

        pubmed_hits = []
        for src_key in ("pubmed_clinical", "pubmed_cart"):
            for hit in enrichment.get(src_key, []):
                if isinstance(hit, dict) and "error" not in hit:
                    pubmed_hits.append(hit)

        return {
            "antibody_name": target,
            "target": target,
            "ada_tier": ada_tier,
            "ada_value": str(ada_value) if ada_value else None,
            "ada_evidence": str(ada_evidence) if ada_evidence else None,
            "pubmed_hit_count": len(pubmed_hits),
            "pubmed_hits": pubmed_hits[:5],
            "warnings": [ada.get("risk_summary", "")] if ada.get("risk_level") in ("HIGH", "MODERATE") else [],
            "is_trusted": ada_tier == "TIER1",
            "needs_disclaimer": ada_tier in ("TIER2", "NOT_FOUND", "OFFLINE"),
        }

    def validate(self, element_ids: list[str], cell_type: str = "T") -> dict:
        """Validate any list of element IDs against design rules."""
        return self._validator.validate(element_ids, cell_type=cell_type)

    def score(self, element_ids: list[str]) -> dict:
        """Score any list of element IDs."""
        validation = self._validator.validate(element_ids)
        return self._scorer.score(element_ids, validation)

    def explain(self, element_ids: list[str]) -> str:
        """Generate natural-language rationale for a set of elements."""
        lines = ["CAR Construct Rationale", "=" * 40]
        for eid in element_ids:
            e = self._lib_idx.get(eid, {})
            name = e.get("name", eid)
            cat = e.get("category", "?")
            tier = e.get("regulatory_tier", "?")
            notes = e.get("design_notes", "")
            first_sentence = notes.split(".")[0] + "." if notes else ""
            lines.append(f"\n[{cat}] {name} (Tier {tier})")
            if first_sentence:
                lines.append(f"  {first_sentence}")
        return "\n".join(lines)

    def export_fasta(self, element_ids: list[str], name: str = "CAR") -> str:
        """Export concatenated FASTA sequence."""
        return self._assembler.assemble(element_ids, name)["fasta"]

    def export_genbank(self, element_ids: list[str], name: str = "CAR") -> str:
        """Export amino-acid GenBank-style flat file with domain features."""
        return self._assembler.export_genbank_features(element_ids, name)

    def export_genbank_dna(self, element_ids: list[str], name: str = "CAR", deplete_cpg: bool = False) -> str:
        """Export codon-optimized DNA GenBank flat file."""
        return self._assembler.export_genbank_dna(element_ids, name, deplete_cpg=deplete_cpg)

    def export_dna_fasta(self, element_ids: list[str], name: str = "CAR", deplete_cpg: bool = False) -> dict:
        """Export codon-optimized DNA FASTA with QC metrics (CAI, GC content)."""
        return self._assembler.assemble_dna(element_ids, name, deplete_cpg=deplete_cpg)

    def export_plasmid_svg(
        self, element_ids: list[str], vector_type: str = "lentiviral_LV", name: str = "CAR Construct",
    ) -> str:
        """Generate a circular plasmid map SVG."""
        return self._plasmid_gen.generate_svg(element_ids, vector_type, name)

    def find_precedent(self, element_ids: list[str], top_n: int = 5) -> list[dict]:
        """Find clinical constructs most similar to the given elements."""
        id_set = set(element_ids)
        results = []
        for cid, construct in self._constructs.get("constructs", {}).items():
            c_ids = {e["id"] for e in construct.get("elements", [])}
            overlap = id_set & c_ids
            union = id_set | c_ids
            jaccard = len(overlap) / max(len(union), 1)
            results.append({
                "construct_id": cid,
                "product": construct.get("product", ""),
                "approval": construct.get("approval", ""),
                "indication": construct.get("indication", ""),
                "jaccard_similarity": round(jaccard, 3),
                "overlap_elements": sorted(overlap),
                "overlap_count": len(overlap),
            })
        results.sort(key=lambda x: -x["jaccard_similarity"])
        return results[:top_n]

    def list_templates(self) -> list[dict]:
        """List available design templates."""
        return [
            {"id": tid, "name": t.get("name", ""), "description": t.get("description", "")}
            for tid, t in self._templates.get("templates", {}).items()
        ]

    def list_indications(self) -> list[dict]:
        """List available indications."""
        return [
            {"id": iid, "name": ind.get("name", "")}
            for iid, ind in self._indications.get("by_indication", {}).items()
        ]

    def get_indication_guide(self, indication: str) -> dict | None:
        """Get full indication guide for a disease."""
        return self._indications.get("by_indication", {}).get(indication)

    def _select_template(
        self, indication: str | None, cell_type: str, mode: str
    ) -> tuple[str, dict]:
        templates = self._templates.get("templates", {})

        mode_map = {
            "standard": "standard_2G_hematologic",
            "armored": "armored_4G",
            "tandem": "tandem_bispecific",
            "logic_AND": "logic_AND_gate",
            "logic_NOT": "logic_NOT_gate",
            "allogeneic": "allo_universal",
            "in_vivo": "in_vivo_mRNA_car",
        }
        cell_map = {
            "NK": "car_nk",
            "macrophage": "car_macrophage",
            "regulatory_T": "car_treg",
            "iPSC_T": "ipsc_car_t",
            "iPSC_NK": "car_nk",
        }

        if cell_type in cell_map:
            tname = cell_map[cell_type]
        elif mode in mode_map:
            tname = mode_map[mode]
        else:
            tname = "standard_2G_hematologic"

        if indication:
            ind_data = self._indications.get("by_indication", {}).get(indication, {})
            pref_template = ind_data.get("preferred_template")
            if pref_template and pref_template in templates:
                tname = pref_template

        template = templates.get(tname, {})
        return tname, template

    def _select_binder(self, target: str, indication: str | None) -> str | None:
        by_target = self._indications.get("by_target_antigen", {})
        if target in by_target:
            binders = by_target[target].get("binders", [])
            if binders:
                return binders[0]

        if indication:
            ind = self._indications.get("by_indication", {}).get(indication, {})
            pref = ind.get("preferred_binders", [])
            if pref:
                return pref[0]

        for eid, e in self._lib_idx.items():
            if e.get("category") == "Antigen Binder":
                name_lower = (e.get("name", "") + " " + eid).lower()
                if target.lower() in name_lower:
                    return eid

        return None

    _CORE_CATEGORY_MAP = {
        "signal_peptide": "Signal Peptide",
        "hinge": "Hinge & Spacer",
        "transmembrane": "Transmembrane Domain",
        "costimulation": "Costimulatory Domain",
        "activation": "Primary Signaling Domain",
    }

    def _apply_core_assembly_overrides(self, elements: list[str], advisory: dict) -> list[str]:
        """Replace template-default core CAR elements with advisor-reasoned selections."""
        d_core = advisory.get("D_core_assembly")
        if not d_core:
            return elements

        overrides: dict[str, str] = {}
        for domain_key, cat_name in self._CORE_CATEGORY_MAP.items():
            domain = d_core.get(domain_key, {})
            selected_id = domain.get("selected")
            if selected_id and selected_id in self._lib_idx:
                overrides[cat_name] = selected_id

        if not overrides:
            return elements

        new_elements = []
        replaced_cats: set[str] = set()
        for eid in elements:
            cat = self._lib_idx.get(eid, {}).get("category", "")
            if cat in overrides:
                if cat not in replaced_cats:
                    new_elements.append(overrides[cat])
                    replaced_cats.add(cat)
            else:
                new_elements.append(eid)

        for cat, eid in overrides.items():
            if cat not in replaced_cats:
                new_elements.append(eid)

        return new_elements

    def _fill_template(
        self,
        template: dict,
        binder: str | None,
        indication: str | None,
        cell_type: str,
        mode: str,
        strict_evidence_only: bool = True,
    ) -> list[str]:
        elements: list[str] = []
        slots = template.get("slots", {})

        for slot_name, slot_def in slots.items():
            if "binder" in slot_name:
                if binder:
                    elements.append(binder)
                continue

            default = slot_def if isinstance(slot_def, str) else slot_def.get("default")
            if default and default in self._lib_idx:
                elements.append(default)

        promoter = template.get("promoter", {})
        if isinstance(promoter, dict):
            req = promoter.get("required")
            default = promoter.get("default")
            if req and req in self._lib_idx:
                elements.append(req)
            elif default and default in self._lib_idx:
                elements.append(default)

        if indication:
            ind = self._indications.get("by_indication", {}).get(indication, {})
            for eng_id in ind.get("recommended_engineering", []):
                if eng_id in self._lib_idx and self._allow_default_extra_element(eng_id, strict_evidence_only):
                    elements.append(eng_id)
            for arm_id in ind.get("recommended_armor", []):
                if arm_id in self._lib_idx and self._allow_default_extra_element(arm_id, strict_evidence_only):
                    elements.append(arm_id)

        opt_slots = template.get("optional_slots", {})
        for slot_name, slot_def in opt_slots.items():
            default = slot_def.get("default") if isinstance(slot_def, dict) else None
            if default and default in self._lib_idx and self._allow_default_extra_element(default, strict_evidence_only):
                elements.append(default)

        ko = template.get("ko_panel", {})
        for ko_id in ko.get("required", []):
            if ko_id in self._lib_idx:
                elements.append(ko_id)
        for ko_id in ko.get("recommended", []):
            if ko_id in self._lib_idx and self._allow_default_extra_element(ko_id, strict_evidence_only):
                elements.append(ko_id)

        evasion = template.get("evasion_transgenes", {})
        for ev_id in evasion.get("recommended", []):
            if ev_id in self._lib_idx and self._allow_default_extra_element(ev_id, strict_evidence_only):
                elements.append(ev_id)

        safety_rec = template.get("safety", {})
        for s_id in safety_rec.get("recommended", []) if isinstance(safety_rec, dict) else []:
            if s_id in self._lib_idx and self._allow_default_extra_element(s_id, strict_evidence_only):
                elements.append(s_id)

        programming = template.get("programming_factors", {})
        for pf_id in programming.get("required", []):
            if pf_id in self._lib_idx:
                elements.append(pf_id)
        for pf_id in programming.get("recommended", []):
            if pf_id in self._lib_idx and self._allow_default_extra_element(pf_id, strict_evidence_only):
                elements.append(pf_id)

        return elements

    def _collect_clinical_human_elements(self) -> set[str]:
        allowed: set[str] = set()
        for construct in self._constructs.get("constructs", {}).values():
            approval = str(construct.get("approval", "")).lower()
            if not approval or "preclinical" in approval or "research" in approval:
                continue
            for elem in construct.get("elements", []):
                eid = elem.get("id")
                if eid:
                    allowed.add(eid)
        return allowed

    def _allow_default_extra_element(self, eid: str, strict_evidence_only: bool) -> bool:
        if not strict_evidence_only:
            return True
        return eid in self._clinical_human_elements

    def _build_template_filter_audit(
        self,
        indication: str | None,
        template_name: str,
        template: dict,
        strict_evidence_only: bool,
    ) -> dict:
        filtered: list[dict] = []
        allowed: list[dict] = []
        if not indication:
            return {
                "template_name": template_name,
                "strict_evidence_only": strict_evidence_only,
                "allowed_default_extra_elements": allowed,
                "filtered_default_extra_elements": filtered,
            }

        ind = self._indications.get("by_indication", {}).get(indication, {})
        candidate_ids = list(ind.get("recommended_engineering", [])) + list(ind.get("recommended_armor", []))
        for slot_def in template.get("optional_slots", {}).values():
            default = slot_def.get("default") if isinstance(slot_def, dict) else None
            if default:
                candidate_ids.append(default)
        for eid in dict.fromkeys(candidate_ids):
            if eid not in self._lib_idx:
                continue
            record = {
                "id": eid,
                "allowed_by_strict_mode": self._allow_default_extra_element(eid, strict_evidence_only),
                "clinical_construct_support": eid in self._clinical_human_elements,
            }
            if record["allowed_by_strict_mode"]:
                allowed.append(record)
            else:
                record["reason"] = "no_clinical_human_element_support"
                filtered.append(record)
        return {
            "template_name": template_name,
            "strict_evidence_only": strict_evidence_only,
            "allowed_default_extra_elements": allowed,
            "filtered_default_extra_elements": filtered,
        }

    def _build_rationale(
        self,
        target: str,
        indication: str | None,
        cell_type: str,
        mode: str,
        template_name: str,
        binder: str | None,
        elements: list[str],
        validation: dict,
        score: dict,
        advisory: dict | None = None,
    ) -> str:
        lines = [
            "=" * 60,
            "CAR-T DESIGN RATIONALE",
            "=" * 60,
            f"Target antigen:  {target}",
            f"Indication:      {indication or 'unspecified'}",
            f"Cell type:       {cell_type}",
            f"Mode:            {mode}",
            f"Template:        {template_name}",
            f"Binder selected: {binder or 'none'}",
            f"Total elements:  {len(elements)}",
            "",
        ]

        if advisory:
            lines.append("-" * 60)
            lines.append("11-LAYER DECISION ADVISORY")
            lines.append("-" * 60)
            for layer_key in (
                "D1_disease_biology", "D2_antigen_properties",
                "D3_delivery_modality", "D4_cell_chassis",
                "D5_immune_microenvironment", "D6_vector_integration",
                "D7_safety_framework", "D8_clinical_evidence",
                "D9_patient_fitness_and_cmc", "D10_boolean_logic_routing",
                "D11_regulatory_path",
            ):
                layer = advisory.get(layer_key, {})
                rationale = layer.get("rationale", "")
                if rationale:
                    label = layer_key.split("_", 1)[0]
                    lines.append(f"  {label}: {rationale}")
            lines.append("")

        lines.append("ELEMENT CHAIN:")
        for eid in elements:
            e = self._lib_idx.get(eid, {})
            cat = e.get("category", "?")[:25]
            name = e.get("name", eid)[:50]
            tier = e.get("regulatory_tier", "?")
            lines.append(f"  [{tier}] {cat:<25} → {name}")

        lines.append("")
        lines.append(f"VALIDATION: {'PASS' if validation['valid'] else 'FAIL'}")
        for err in validation.get("errors", []):
            lines.append(f"  ERROR: {err}")
        for warn in validation.get("warnings", []):
            lines.append(f"  WARN:  {warn}")

        lines.append("")
        dims = score.get("dimensions", {})
        lines.append(f"SCORE: {score.get('total', 0)}/100")
        for dname, dinfo in dims.items():
            lines.append(f"  {dname}: {dinfo['score']}/{dinfo['max']} — {dinfo['detail']}")

        precedents = self.find_precedent(elements, top_n=3)
        if precedents:
            lines.append("")
            lines.append("CLOSEST CLINICAL PRECEDENTS:")
            for p in precedents:
                lines.append(
                    f"  {p['construct_id']} ({p['approval']}): "
                    f"similarity={p['jaccard_similarity']:.1%}, "
                    f"overlap={p['overlap_count']} elements"
                )

        if indication:
            ind = self._indications.get("by_indication", {}).get(indication, {})
            notes = ind.get("notes", "")
            if notes:
                lines.append("")
                lines.append(f"INDICATION NOTES: {notes}")

        lines.append("")
        lines.append("=" * 60)
        return "\n".join(lines)
