"""
DecisionAdvisor — walks through the CAR decision layers and outputs
structured, per-layer recommendations that feed into CARDesigner.
"""
from __future__ import annotations


class DecisionAdvisor:
    """
    11-layer cascading decision engine for CAR-T design.

    Layers:
      D1  Disease biology
      D2  Antigen properties
      D3  Delivery modality
      D4  Cell chassis selection
      D5  Immune microenvironment
      D6  Vector & integration
      D7  Safety framework
      D8  Clinical evidence
      D9  Patient fitness & CMC
      D10 Boolean logic routing
      D11 Regulatory path
    """

    def __init__(self, framework: dict, indication_guide: dict):
        self._fw = framework
        self._ind = indication_guide

    def advise(
        self,
        target: str,
        indication: str,
        cell_type: str | None = None,
        delivery: str | None = None,
        patient_fitness: str = "moderate_prior_therapy",
        regulatory_goal: str = "clinical_fast_track",
        secondary_target: str | None = None,
        strict_evidence_only: bool = True,
        therapeutic_window_hours: float | None = None,
        knowledge_enrichment: dict | None = None,
    ) -> dict:
        self._strict_evidence_only = strict_evidence_only
        d1 = self._d1_disease_biology(indication)
        d2 = self._d2_antigen_properties(target)
        d4 = self._d4_cell_chassis(indication, d1, cell_type, d2)
        d3 = self._d3_delivery(indication, d1, delivery, d4, therapeutic_window_hours)
        d5 = self._d5_microenvironment(indication, d1)
        d6 = self._d6_vector(d3, d4, d5, regulatory_goal)
        d7 = self._d7_safety(target, d1, d2, d4)
        d8 = self._d8_clinical_evidence(target, indication)
        d9 = self._d9_patient_fitness(patient_fitness)
        d10 = self._d10_boolean_logic(target, secondary_target, indication)
        d11 = self._d11_regulatory_path(regulatory_goal)

        if knowledge_enrichment:
            from .knowledge_enricher import KnowledgeEnricher
            enricher = KnowledgeEnricher.__new__(KnowledgeEnricher)
            d2 = enricher.enrich_d2(d2, knowledge_enrichment)
            d8 = enricher.enrich_d8(d8, knowledge_enrichment)

        d_core = self._d_core_assembly(d1, d2, d4, d5)

        recommended_elements = self._synthesize_elements(d1, d2, d4, d5, d7, d9, d10, d11)
        audit = self._build_audit(
            target, indication, patient_fitness, regulatory_goal, secondary_target,
            d1, d2, d3, d4, d5, d6, d7, d8, d9, d10, d11, recommended_elements,
            therapeutic_window_hours=therapeutic_window_hours,
        )

        result = {
            "D1_disease_biology": d1,
            "D2_antigen_properties": d2,
            "D3_delivery_modality": d3,
            "D4_cell_chassis": d4,
            "D5_immune_microenvironment": d5,
            "D6_vector_integration": d6,
            "D7_safety_framework": d7,
            "D8_clinical_evidence": d8,
            "D9_patient_fitness_and_cmc": d9,
            "D10_boolean_logic_routing": d10,
            "D11_regulatory_path": d11,
            "D_core_assembly": d_core,
            "recommended_elements": recommended_elements,
            "strict_evidence_only_applied": strict_evidence_only,
            "audit": audit,
            "summary": self._build_summary(d1, d2, d3, d4, d5, d6, d7, d8, d9, d10, d11),
        }

        if knowledge_enrichment:
            result["knowledge_enrichment"] = knowledge_enrichment
            ada = knowledge_enrichment.get("ada_risk", {})
            if ada.get("entries"):
                result["ada_risk_assessment"] = ada

        return result

    # ── D1: Disease Biology ──────────────────────────────────────────

    def _d1_disease_biology(self, indication: str) -> dict:
        cats = self._fw.get("D1_disease_biology", {}).get("categories", {})
        matched = None
        for cat_key, cat_data in cats.items():
            if indication in cat_data.get("indications", []):
                matched = cat_key
                break

        if not matched:
            for cat_key, cat_data in cats.items():
                for ind in cat_data.get("indications", []):
                    if ind.lower() in indication.lower() or indication.lower() in ind.lower():
                        matched = cat_key
                        break
                if matched:
                    break

        if not matched:
            return {
                "category": "unknown",
                "design_impact": {},
                "rationale": f"Indication '{indication}' not found in disease biology framework; defaulting to solid_tumor rules.",
            }

        data = cats[matched]
        return {
            "category": matched,
            "evidence_confidence": data.get("evidence_confidence"),
            "sources": data.get("sources", []),
            "characteristics": data.get("characteristics", []),
            "design_impact": data.get("design_impact", {}),
            "key_challenges": data.get("key_challenges", []),
            "rationale": f"Indication '{indication}' classified as '{matched}'. {'; '.join(data.get('characteristics', [])[:3])}.",
        }

    # ── D2: Antigen Properties ───────────────────────────────────────

    def _d2_antigen_properties(self, target: str) -> dict:
        antigens = self._fw.get("D2_antigen_properties", {}).get("antigens", {})
        hinge_rules = self._fw.get("D2_antigen_properties", {}).get("hinge_rules", {})
        density_rules = self._fw.get("D2_antigen_properties", {}).get("density_safety_rules", {})

        ag = antigens.get(target)
        if not ag:
            for key, data in antigens.items():
                if target.lower() in key.lower() or key.lower() in target.lower():
                    ag = data
                    target = key
                    break

        if not ag:
            return {
                "target": target,
                "known": False,
                "hinge_recommendation": "short",
                "safety_risk": "unknown",
                "rationale": f"Antigen '{target}' not in properties database; using default short hinge.",
            }

        distance = ag.get("epitope_membrane_distance_nm", 5)
        if distance < 5:
            hinge_rec = hinge_rules.get("epitope_distance_lt_5nm", {})
        elif distance <= 10:
            hinge_rec = hinge_rules.get("epitope_distance_5_10nm", {})
        else:
            hinge_rec = hinge_rules.get("epitope_distance_gt_10nm", {})

        densities = ag.get("density_molecules_per_cell", {})
        tumor_vals = [v for k, v in densities.items() if "normal" not in k.lower()]
        normal_vals = [v for k, v in densities.items() if "normal" in k.lower() and v > 0]
        max_tumor = max(tumor_vals) if tumor_vals else 1
        max_normal = max(normal_vals) if normal_vals else 0
        ratio = max_tumor / max_normal if max_normal > 0 else float("inf")

        if ratio > 1000:
            density_risk = density_rules.get("ratio_gt_1000x", {})
        elif ratio > 100:
            density_risk = density_rules.get("ratio_100_1000x", {})
        elif ratio > 10:
            density_risk = density_rules.get("ratio_lt_100x", {})
        else:
            density_risk = density_rules.get("ratio_lt_10x", {})

        toxicity_profile = self._toxicity_profile(target)

        origin = ag.get("origin_type", "human")
        nucleated = ag.get("target_cell_nucleated", True)
        apoptosis_ok = ag.get("target_cell_apoptosis_competent", True)
        expr_pattern = ag.get("expression_temporal_pattern", "constitutive")
        ag_variation = ag.get("antigenic_variation")

        ratio_str = (
            f"{ratio:.0f}x" if ratio != float("inf")
            else "infinite (pathogen-only)" if origin == "pathogen"
            else "infinite (tumor-restricted)"
        )

        return {
            "target": target,
            "known": True,
            "type": ag.get("type", ""),
            "origin_type": origin,
            "target_cell_nucleated": nucleated,
            "target_cell_apoptosis_competent": apoptosis_ok,
            "expression_temporal_pattern": expr_pattern,
            "antigenic_variation": ag_variation,
            "evidence_confidence": ag.get("evidence_confidence"),
            "sources": ag.get("sources", []),
            "epitope_distance_nm": distance,
            "hinge_recommendation": hinge_rec.get("hinge", ag.get("hinge_recommendation", "short")),
            "hinge_elements": hinge_rec.get("elements", []),
            "tumor_normal_ratio": ratio_str,
            "density_safety": density_risk,
            "toxicity_tolerance": toxicity_profile,
            "heterogeneity": ag.get("heterogeneity", ""),
            "antigen_loss_frequency": ag.get("antigen_loss_frequency", ""),
            "on_target_off_tumor": ag.get("on_target_off_tumor", ""),
            "binder_formats": ag.get("binder_format_options", []),
            "multi_target_rationale": ag.get("multi_target_rationale", ""),
            "safety_requirements": ag.get("safety_requirements", []),
            "rationale": (
                f"{target}: {ag.get('type','')} ({origin}), epitope {distance}nm from membrane → "
                f"{hinge_rec.get('hinge','short')} hinge. Tumor/normal ratio {ratio_str} → "
                f"safety risk: {density_risk.get('risk','unknown')}; "
                f"tolerability class: {toxicity_profile.get('class', 'unknown')}."
                + (f" Target cell anucleate — T cell cytotoxic pathway incompatible." if not apoptosis_ok else "")
                + (f" Expression pattern: {expr_pattern}." if expr_pattern != "constitutive" else "")
                + (f" Antigenic variation: {ag_variation.get('mechanism', '')} ({ag_variation.get('variant_count', '?')} variants)." if ag_variation else "")
            ),
        }

    # ── D_core: Core CAR Assembly (SP, Hinge, TM, Costim, Activation) ─

    def _d_core_assembly(self, d1: dict, d2: dict, d4: dict, d5: dict) -> dict:
        """Explicit biological reasoning for each core CAR chain domain."""
        rules = self._fw.get("core_assembly_rules", {})
        cat = d1.get("category", "")
        chassis = d4.get("selected", "alpha_beta_T")
        epitope_dist = d2.get("epitope_distance_nm", 5)
        binder_formats = d2.get("binder_formats", [])
        is_vhh = any("VHH" in str(b) or "nanobody" in str(b).lower() for b in binder_formats)

        sp = self._select_sp(rules.get("signal_peptide", {}), chassis, is_vhh)
        hinge = self._select_hinge(rules.get("hinge_selection", {}), epitope_dist)
        tm = self._select_tm(rules.get("tm_selection", {}), hinge["selected"], chassis)
        pairing = self._check_hinge_tm_pairing(
            rules.get("hinge_tm_pairing", {}), hinge["selected"], tm["selected"],
        )
        costim = self._select_costim(rules.get("costim_selection", {}), cat, chassis)
        activation = self._select_activation(rules.get("activation_selection", {}), cat, chassis)

        return {
            "signal_peptide": sp,
            "hinge": hinge,
            "transmembrane": tm,
            "hinge_tm_pairing_check": pairing,
            "costimulation": costim,
            "activation": activation,
            "rationale": (
                f"Core assembly: {sp['selected']} → {hinge['selected']} → {tm['selected']} → "
                f"{costim['selected']} → {activation['selected']}. "
                f"Pairing: {pairing.get('quality', 'unknown')}."
            ),
        }

    def _select_sp(self, sp_rules: dict, chassis: str, is_vhh: bool) -> dict:
        rules = sp_rules.get("rules", [])
        dont_use_general = sp_rules.get("dont_use_general", [])
        for rule in rules:
            cond = rule["condition"]
            if cond == "macrophage_chassis" and chassis == "macrophage":
                return self._core_rule_to_output(rule, dont_use_general)
            if cond == "VHH_binder" and is_vhh:
                return self._core_rule_to_output(rule, dont_use_general)
        for rule in rules:
            if rule["condition"] == "default":
                return self._core_rule_to_output(rule, dont_use_general)
        return {"selected": "CD8a_SP", "use_rationale": "Default", "dont_use": dont_use_general}

    def _select_hinge(self, hinge_rules: dict, epitope_dist: float) -> dict:
        rules = hinge_rules.get("rules", [])
        for rule in rules:
            cond = rule["condition"]
            if cond == "epitope_distance_lt_5nm" and epitope_dist < 5:
                return self._core_rule_to_output(rule)
            if cond == "epitope_distance_5_10nm" and 5 <= epitope_dist <= 10:
                return self._core_rule_to_output(rule)
            if cond == "epitope_distance_gt_10nm" and epitope_dist > 10:
                return self._core_rule_to_output(rule)
        return {"selected": "CD8a_Short", "use_rationale": "Default short hinge", "dont_use": []}

    def _select_tm(self, tm_rules: dict, hinge_id: str, chassis: str) -> dict:
        rules = tm_rules.get("rules", [])
        chassis_map = {"NK": "chassis_NK", "macrophage": "chassis_macrophage"}
        hinge_map = {
            "CD8a_Short": "hinge_CD8a", "CD8a_Long": "hinge_CD8a",
            "CD28_Medium": "hinge_CD28",
            "IgG4_SPLE_Long": "hinge_IgG4", "IgG1_Hinge": "hinge_IgG4",
        }
        chassis_cond = chassis_map.get(chassis)
        if chassis_cond:
            for rule in rules:
                if rule["condition"] == chassis_cond:
                    return self._core_rule_to_output(rule)
        hinge_cond = hinge_map.get(hinge_id)
        if hinge_cond:
            for rule in rules:
                if rule["condition"] == hinge_cond:
                    return self._core_rule_to_output(rule)
        return {"selected": "CD8a_TM", "use_rationale": "Default TM", "dont_use": []}

    def _check_hinge_tm_pairing(self, pairing_rules: dict, hinge_id: str, tm_id: str) -> dict:
        pairings = pairing_rules.get("pairings", {})
        key = f"{hinge_id}+{tm_id}"
        if key in pairings:
            p = pairings[key]
            quality = "optimal" if p.get("tonic_signaling") == "low" else (
                "acceptable" if p.get("tonic_signaling") in ("low-moderate", "moderate") else "suboptimal"
            )
            return {
                "pair": key,
                "quality": quality,
                "tonic_signaling": p.get("tonic_signaling"),
                "preferred_costim": p.get("preferred_costim", []),
                "rationale": p.get("rationale", ""),
            }
        return {"pair": key, "quality": "unknown", "rationale": "No pairing data available."}

    def _select_costim(self, costim_rules: dict, disease_cat: str, chassis: str) -> dict:
        rules = costim_rules.get("rules", [])
        chassis_cond_map = {
            "Treg": "CAR_Treg", "NK": "CAR_NK", "macrophage": "CAR_macrophage",
        }
        chassis_cond = chassis_cond_map.get(chassis)
        if chassis_cond:
            for rule in rules:
                if rule["condition"] == chassis_cond:
                    return self._core_rule_to_output(rule)
        for rule in rules:
            if rule["condition"] == disease_cat:
                return self._core_rule_to_output(rule)
        for rule in rules:
            if rule["condition"] == "liquid_tumor" and disease_cat in ("liquid_tumor", "AML_special"):
                return self._core_rule_to_output(rule)
        return {"selected": "4-1BB_cyto", "use_rationale": "Default costimulation", "dont_use": []}

    def _select_activation(self, act_rules: dict, disease_cat: str, chassis: str) -> dict:
        rules = act_rules.get("rules", [])
        if chassis == "macrophage":
            for rule in rules:
                if rule["condition"] == "CAR_macrophage":
                    return self._core_rule_to_output(rule)
        for rule in rules:
            if rule["condition"] == "default_T_cell":
                return self._core_rule_to_output(rule)
        return {"selected": "CD3z_cyto", "use_rationale": "Default activation", "dont_use": []}

    @staticmethod
    def _core_rule_to_output(rule: dict, extra_dont_use: list | None = None) -> dict:
        reject = rule.get("reject", [])
        reject_rationale = rule.get("reject_rationale", {})
        dont_use = []
        for r in reject:
            reason = reject_rationale.get(r, f"Rejected in favor of {rule['select']}")
            dont_use.append({"element": r, "reason": reason})
        if extra_dont_use:
            dont_use.extend(extra_dont_use)
        result = {
            "selected": rule["select"],
            "use_rationale": rule.get("rationale", ""),
            "dont_use": dont_use,
            "evidence": rule.get("evidence"),
            "sources": rule.get("sources", []),
        }
        if "conditional_note" in rule:
            result["conditional_note"] = rule["conditional_note"]
        if "alternative" in rule:
            result["alternative"] = rule["alternative"]
            result["alternative_rationale"] = rule.get("alternative_rationale", "")
        return result

    # ── D3: Delivery Modality ────────────────────────────────────────

    def _d3_delivery(
        self, indication: str, d1: dict, override: str | None,
        d4: dict | None = None,
        therapeutic_window_hours: float | None = None,
    ) -> dict:
        modalities = self._fw.get("D3_delivery_modality", {}).get("modalities", {})
        cat = d1.get("category", "")

        if override:
            mod_data = modalities.get(override, {})
            return {
                "selected": override,
                "rationale": f"User specified delivery: {override}.",
                "details": mod_data,
                "evidence_confidence": mod_data.get("evidence_confidence"),
                "sources": mod_data.get("sources", []),
            }

        chassis = (d4 or {}).get("selected", "alpha_beta_T")

        if therapeutic_window_hours is not None and therapeutic_window_hours < 168:
            if chassis == "macrophage":
                selected = "in_vivo_LNP_mRNA_macrophage"
                rationale = (
                    f"Therapeutic window {therapeutic_window_hours}h < 168h precludes ex-vivo manufacturing. "
                    f"Macrophage chassis selected → ManC-LNP in-vivo macrophage programming."
                )
            else:
                selected = "in_vivo_LNP_mRNA"
                rationale = (
                    f"Therapeutic window {therapeutic_window_hours}h < 168h precludes ex-vivo manufacturing. "
                    f"In-vivo LNP-mRNA delivery selected."
                )
        elif cat == "infectious_disease":
            if chassis == "macrophage":
                selected = "in_vivo_LNP_mRNA_macrophage"
                rationale = "Infectious disease with macrophage chassis → in-vivo ManC-LNP macrophage programming preferred."
            else:
                selected = "ex_vivo_autologous"
                rationale = "Infectious disease (chronic): ex-vivo autologous default; in-vivo LNP is alternative."
        elif cat == "autoimmune":
            selected = "ex_vivo_autologous"
            rationale = "Autoimmune: autologous standard; in-vivo LNP is future candidate."
        elif cat in ("liquid_tumor", "solid_tumor", "AML_special"):
            selected = "ex_vivo_autologous"
            rationale = "Standard oncology: ex-vivo autologous is regulatory-proven default."
        elif cat == "transplant_GvHD":
            selected = "ex_vivo_autologous"
            rationale = "CAR-Treg: autologous Treg manufacturing."
        else:
            selected = "ex_vivo_autologous"
            rationale = "Default: ex-vivo autologous."

        dont_use = self._delivery_rejections(selected, cat, modalities)

        return {
            "selected": selected,
            "therapeutic_window_hours": therapeutic_window_hours,
            "rationale": rationale,
            "dont_use": dont_use,
            "details": modalities.get(selected, {}),
            "evidence_confidence": modalities.get(selected, {}).get("evidence_confidence"),
            "sources": modalities.get(selected, {}).get("sources", []),
            "alternative_candidates": self._delivery_alternatives(cat),
        }

    @staticmethod
    def _delivery_rejections(selected: str, disease_cat: str, modalities: dict) -> list[dict]:
        rejection_reasons = {
            "ex_vivo_autologous": {
                "in_vivo_LNP_mRNA": "In-vivo LNP-mRNA not selected: ex-vivo manufacturing is regulatory-proven and gives higher transduction control.",
                "ex_vivo_allogeneic": "Allogeneic not selected: autologous avoids GvHD and host rejection risks.",
            },
            "in_vivo_LNP_mRNA": {
                "ex_vivo_autologous": "Ex-vivo manufacturing rejected: therapeutic window too short for leukapheresis + 2-week manufacturing.",
                "ex_vivo_allogeneic": "Allogeneic rejected: in-vivo LNP delivery is simpler and avoids cell manufacturing entirely.",
            },
            "in_vivo_LNP_mRNA_macrophage": {
                "ex_vivo_autologous": "Ex-vivo T cell manufacturing rejected: macrophage chassis selected — ManC-LNP in-vivo delivery is the validated approach.",
            },
        }
        rejections = rejection_reasons.get(selected, {})
        return [
            {"modality": mod, "reason": reason}
            for mod, reason in rejections.items()
            if mod in modalities
        ]

    def _delivery_alternatives(self, disease_cat: str) -> list[str]:
        alts = []
        if disease_cat in ("liquid_tumor", "AML_special"):
            alts.append("ex_vivo_allogeneic")
        if disease_cat == "autoimmune":
            alts.extend(["in_vivo_LNP_mRNA", "ex_vivo_allogeneic"])
        if disease_cat == "solid_tumor":
            alts.append("ex_vivo_allogeneic")
        if disease_cat == "infectious_disease":
            alts.extend(["in_vivo_LNP_mRNA", "in_vivo_LNP_mRNA_macrophage", "ex_vivo_autologous"])
        return alts

    # ── D4: Cell Chassis ─────────────────────────────────────────────

    def _d4_cell_chassis(
        self, indication: str, d1: dict, override: str | None,
        d2: dict | None = None,
    ) -> dict:
        chassis = self._fw.get("D4_cell_chassis", {})
        cell_types = chassis.get("cell_types", {})
        rec_map = chassis.get("disease_to_chassis_recommendation", {})

        apoptosis_ok = (d2 or {}).get("target_cell_apoptosis_competent", True)
        nucleated = (d2 or {}).get("target_cell_nucleated", True)
        apoptosis_override = None

        if not apoptosis_ok or not nucleated:
            apoptosis_override = "macrophage"

        if override:
            if apoptosis_override and override == "alpha_beta_T":
                return {
                    "selected": apoptosis_override,
                    "rationale": (
                        f"User requested {override}, but target cell is "
                        f"{'anucleate' if not nucleated else 'apoptosis-incompetent'} — "
                        f"T cell caspase pathway is incompatible. Overriding to macrophage."
                    ),
                    "apoptosis_override_applied": True,
                    "details": cell_types.get(apoptosis_override, {}),
                    "evidence_confidence": cell_types.get(apoptosis_override, {}).get("evidence_confidence"),
                    "sources": cell_types.get(apoptosis_override, {}).get("sources", []),
                    "signaling": cell_types.get(apoptosis_override, {}).get("signaling_options", {}),
                }
            ct_data = cell_types.get(override, {})
            return {
                "selected": override,
                "rationale": f"User specified cell type: {override}.",
                "details": ct_data,
                "evidence_confidence": ct_data.get("evidence_confidence"),
                "sources": ct_data.get("sources", []),
                "signaling": ct_data.get("signaling_options", {}),
            }

        rec = rec_map.get(indication, {})
        primary = rec.get("primary", "alpha_beta_T")
        alternative = rec.get("alternative")
        note = rec.get("note", "")

        if not rec:
            cat = d1.get("category", "")
            if cat == "transplant_GvHD":
                primary = "Treg"
            elif cat == "AML_special":
                primary = "NK"
            elif cat == "autoimmune":
                primary = "alpha_beta_T"
            elif cat == "infectious_disease":
                primary = apoptosis_override or "alpha_beta_T"

        if apoptosis_override and primary in ("alpha_beta_T",):
            primary = apoptosis_override
            note = (note + " " if note else "") + (
                f"Target cell {'anucleate' if not nucleated else 'apoptosis-incompetent'} "
                f"→ T cell cytotoxic pathway incompatible → macrophage (phagocytosis) selected."
            )

        ct_data = cell_types.get(primary, {})

        required_elements = []
        required_payload = ct_data.get("required_payload", [])
        if isinstance(required_payload, list):
            required_elements.extend(required_payload)
        elif isinstance(required_payload, str):
            required_elements.append(required_payload)

        required_element = ct_data.get("required_element")
        if isinstance(required_element, list):
            required_elements.extend(required_element)
        elif isinstance(required_element, str):
            required_elements.append(required_element)

        dont_use = self._chassis_rejections(primary, d1.get("category", ""), cell_types)

        return {
            "selected": primary,
            "alternative": alternative,
            "evidence_confidence": ct_data.get("evidence_confidence"),
            "sources": ct_data.get("sources", []),
            "rationale": (
                f"For '{indication}': primary chassis = {primary}"
                + (f" (alternative: {alternative})" if alternative else "")
                + (f". {note}" if note else ".")
            ),
            "dont_use": dont_use,
            "details": ct_data,
            "signaling": ct_data.get("signaling_options", {}),
            "advantages": ct_data.get("advantages", []),
            "disadvantages": ct_data.get("disadvantages", []),
            "required_elements": required_elements,
            "forbidden_elements": ct_data.get("forbidden_elements", []),
        }

    @staticmethod
    def _chassis_rejections(selected: str, disease_cat: str, cell_types: dict) -> list[dict]:
        reasons = {
            "alpha_beta_T": {
                "NK": "NK rejected: lower persistence than T cells; limited in-vivo expansion for sustained anti-tumor response.",
                "macrophage": "Macrophage rejected: target cells are nucleated and apoptosis-competent — T cell cytotoxicity is appropriate.",
                "gamma_delta_T": "γδ T rejected: limited clinical validation; manufacturing yield lower than αβ T cells.",
            },
            "NK": {
                "alpha_beta_T": "αβ T rejected: NK selected for innate anti-tumor activity + lower GvHD risk in allogeneic setting.",
            },
            "macrophage": {
                "alpha_beta_T": "αβ T rejected: target cell is anucleate/apoptosis-incompetent — T cell caspase-dependent killing is ineffective. Macrophage phagocytosis required.",
            },
            "Treg": {
                "alpha_beta_T": "αβ Teff rejected: tolerance induction requires suppressive Treg phenotype, not cytotoxic T cell.",
                "NK": "NK rejected: NK cells are cytotoxic — incompatible with tolerance/suppression goals.",
            },
        }
        return [
            {"chassis": chassis, "reason": reason}
            for chassis, reason in reasons.get(selected, {}).items()
            if chassis in cell_types
        ]

    # ── D5: Immune Microenvironment ──────────────────────────────────

    def _d5_microenvironment(self, indication: str, d1: dict) -> dict:
        envs = self._fw.get("D5_immune_microenvironment", {}).get("environments", {})
        supp_map = self._fw.get("D5_immune_microenvironment", {}).get("suppression_to_element_map", {})
        cat = d1.get("category", "")

        matched_env = None
        for env_key, env_data in envs.items():
            if indication in env_data.get("applicable_to", []):
                matched_env = env_key
                break

        if not matched_env:
            if cat == "liquid_tumor" or cat == "AML_special":
                matched_env = "blood_bone_marrow"
            elif cat == "autoimmune":
                matched_env = "autoimmune_tissue"
            elif cat == "solid_tumor":
                matched_env = "solid_tumor_hot_suppressed"

        if not matched_env:
            return {
                "environment": "unknown",
                "suppression_level": "unknown",
                "countermeasure_elements": [],
                "rationale": "Could not determine microenvironment.",
            }

        env = envs[matched_env]
        suppression = env.get("suppression_level", "unknown")

        countermeasure_elements: list[str] = []
        countermeasure_reasons: list[str] = []

        if matched_env in ("solid_tumor_cold", "solid_tumor_hot_suppressed"):
            dominant = env.get("dominant_suppression_by_tumor", {}).get(indication, [])
            if not dominant:
                dominant = list(env.get("countermeasures_map", {}).keys())[:4]

            for factor in dominant:
                mapping = supp_map.get(factor, {})
                elements = mapping.get("elements", [])
                priority = mapping.get("priority", "medium")
                if elements and self._entry_is_default_recommendable(mapping):
                    countermeasure_elements.extend(elements[:1])
                    countermeasure_reasons.append(f"{factor} → {elements[0]} (priority: {priority})")

            if "exhaustion" not in dominant:
                exh = supp_map.get("exhaustion", {})
                if exh.get("elements") and self._entry_is_default_recommendable(exh):
                    countermeasure_elements.append(exh["elements"][0])
                    countermeasure_reasons.append(f"exhaustion → {exh['elements'][0]} (always recommended for solid tumor)")

            if "poor_homing" not in dominant:
                homing = supp_map.get("poor_homing", {})
                if homing.get("elements") and self._entry_is_default_recommendable(homing):
                    countermeasure_elements.append(homing["elements"][0])
                    countermeasure_reasons.append(f"poor_homing → {homing['elements'][0]} (always recommended for solid tumor)")

        return {
            "environment": matched_env,
            "suppression_level": suppression,
            "evidence_confidence": env.get("evidence_confidence"),
            "sources": env.get("sources", []),
            "dominant_factors": env.get("dominant_suppression_by_tumor", {}).get(indication, env.get("dominant_suppression", [])),
            "countermeasure_elements": list(dict.fromkeys(countermeasure_elements)),
            "countermeasure_reasons": countermeasure_reasons,
            "rationale": (
                f"Microenvironment: {matched_env} (suppression: {suppression}). "
                + (f"Countermeasures: {', '.join(countermeasure_elements[:5])}." if countermeasure_elements else "No specific countermeasures needed.")
            ),
        }

    # ── D6: Vector & Integration ─────────────────────────────────────

    def _d6_vector(self, d3: dict, d4: dict, d5: dict, regulatory_goal: str = "clinical_fast_track") -> dict:
        vectors = self._fw.get("D6_vector_integration", {}).get("vectors", {})
        delivery = d3.get("selected", "ex_vivo_autologous")
        chassis = d4.get("selected", "alpha_beta_T")
        n_countermeasures = len(d5.get("countermeasure_elements", []))

        if delivery in ("in_vivo_LNP_mRNA", "in_vivo_LNP_mRNA_macrophage"):
            selected = "mRNA_LNP"
            rationale = f"In-vivo delivery ({delivery}) → mRNA/LNP (no integration, transient expression = built-in safety)."
            dont_use = [
                {"vector": "lentiviral_LV", "reason": "Lentiviral requires ex-vivo transduction — incompatible with in-vivo delivery."},
                {"vector": "AAV_TRAC_knockin", "reason": "AAV requires ex-vivo electroporation — incompatible with in-vivo delivery."},
            ]
        elif chassis == "iPSC_derived":
            selected = "AAV_TRAC_knockin"
            rationale = "iPSC-derived chassis → AAV TRAC knock-in for site-specific integration. Eliminates random insertional mutagenesis, enables TRAC KO simultaneously."
            dont_use = [
                {"vector": "lentiviral_LV", "reason": "Random LV integration in iPSC risks insertional oncogenesis in pluripotent cells."},
                {"vector": "gamma_retroviral_RV", "reason": "Retroviral integration in iPSC has higher oncogenesis risk than site-specific AAV knock-in."},
            ]
        elif n_countermeasures >= 5:
            selected = "piggyBac_PB"
            rationale = f"Very large payload ({n_countermeasures} modules) exceeds SB capacity → PiggyBac (14kb capacity, precise excision, non-viral)."
            dont_use = [
                {"vector": "lentiviral_LV", "reason": f"LV 8kb capacity insufficient for {n_countermeasures} engineering modules."},
                {"vector": "gamma_retroviral_RV", "reason": f"RV 7kb capacity insufficient for {n_countermeasures} engineering modules."},
            ]
        elif n_countermeasures >= 4:
            selected = "sleeping_beauty_SB"
            rationale = f"Large payload ({n_countermeasures} modules) → Sleeping Beauty (12kb capacity, non-viral, cost-effective)."
            dont_use = [
                {"vector": "lentiviral_LV", "reason": f"LV 8kb capacity may be insufficient for {n_countermeasures} engineering modules."},
            ]
        elif regulatory_goal == "clinical_fast_track" and delivery == "ex_vivo_autologous":
            selected = "lentiviral_LV"
            rationale = "Clinical fast-track + standard payload → lentiviral (FDA-proven in 6 approved products, 8kb capacity sufficient)."
            dont_use = [
                {"vector": "sleeping_beauty_SB", "reason": "SB is non-viral and cheaper, but has less regulatory precedent than LV for fast-track approval."},
                {"vector": "gamma_retroviral_RV", "reason": "RV (used in Axi-cel) is valid but LV has broader regulatory acceptance and larger payload capacity (8 vs 7kb)."},
            ]
        else:
            selected = "lentiviral_LV"
            rationale = "Standard payload → lentiviral vector (FDA-proven, 8kb capacity sufficient)."
            dont_use = []

        vec = vectors.get(selected, {})
        return {
            "selected": selected,
            "payload_capacity_kb": vec.get("payload_capacity_kb", "?"),
            "integration_pattern": vec.get("integration_pattern", ""),
            "evidence_confidence": vec.get("evidence_confidence"),
            "sources": vec.get("sources", []),
            "advantages": vec.get("advantages", []),
            "rationale": rationale,
            "dont_use": dont_use,
            "alternatives": self._vector_alternatives(selected, n_countermeasures),
        }

    def _vector_alternatives(self, primary: str, n_modules: int) -> list[str]:
        alts = []
        if primary != "lentiviral_LV":
            alts.append("lentiviral_LV")
        if primary != "sleeping_beauty_SB" and n_modules >= 2:
            alts.append("sleeping_beauty_SB")
        if primary != "mRNA_LNP":
            alts.append("mRNA_LNP")
        if primary != "gamma_retroviral_RV" and n_modules <= 3:
            alts.append("gamma_retroviral_RV")
        if primary != "piggyBac_PB" and n_modules >= 4:
            alts.append("piggyBac_PB")
        if primary != "AAV_TRAC_knockin":
            alts.append("AAV_TRAC_knockin")
        return alts

    # ── D7: Safety Framework ─────────────────────────────────────────

    def _d7_safety(self, target: str, d1: dict, d2: dict, d4: dict) -> dict:
        fw = self._fw.get("D7_safety_framework", {})
        cat = d1.get("category", "")

        risk_level = d2.get("density_safety", {}).get("risk", "unknown")
        toxicity_class = d2.get("toxicity_tolerance", {}).get("class", "unknown")
        safety_reqs = d2.get("safety_requirements", [])

        crs_risk = "moderate"
        if cat in ("liquid_tumor", "AML_special"):
            crs_risk = "high"
        elif cat == "autoimmune":
            crs_risk = "low"
        elif cat == "solid_tumor":
            crs_risk = "moderate"

        switch_needed = "optional"
        if (
            "MANDATORY" in str(safety_reqs)
            or risk_level in ("high", "critical")
            or toxicity_class in ("high_risk_shared_antigen", "vital_organ_expression")
        ):
            switch_needed = "mandatory"
        elif cat == "AML_special":
            switch_needed = "mandatory"
        elif risk_level == "moderate" or toxicity_class == "manageable_toxicity":
            switch_needed = "recommended"

        logic_gate_needed = (
            risk_level == "critical"
            or toxicity_class == "vital_organ_expression"
            or "logic_gate" in str(d2.get("density_safety", {}))
        )
        affinity_tuning = (
            "recommended" in str(d2.get("density_safety", {}))
            or "REQUIRED" in str(safety_reqs)
            or toxicity_class in ("manageable_toxicity", "high_risk_shared_antigen", "vital_organ_expression")
        )

        recommended_switches = []
        if switch_needed in ("mandatory", "recommended"):
            recommended_switches.append("iCasp9")
            chassis = d4.get("selected", "alpha_beta_T")
            if chassis == "alpha_beta_T" and cat != "autoimmune":
                recommended_switches.append("tEGFR")

        failure_modes = fw.get("failure_modes_and_mitigation", {})
        relevant_failures = []
        if cat == "solid_tumor":
            relevant_failures = ["T_cell_exhaustion", "poor_tumor_infiltration", "immunosuppressive_TME"]
        elif cat in ("liquid_tumor", "AML_special"):
            relevant_failures = ["antigen_loss_escape"]
        elif cat == "autoimmune":
            relevant_failures = []

        return {
            "crs_risk": crs_risk,
            "on_target_off_tumor_risk": risk_level,
            "toxicity_tolerance_class": toxicity_class,
            "risk_class_sources": d2.get("sources", []),
            "risk_class_evidence_confidence": d2.get("evidence_confidence"),
            "general_risk_class_sources": fw.get("on_target_off_tumor", {}).get("risk_classification", {}).get(risk_level, {}).get("sources", []),
            "general_risk_class_evidence_confidence": fw.get("on_target_off_tumor", {}).get("risk_classification", {}).get(risk_level, {}).get("evidence_confidence"),
            "safety_switch_needed": switch_needed,
            "recommended_switches": recommended_switches,
            "logic_gate_needed": logic_gate_needed,
            "affinity_tuning_recommended": affinity_tuning,
            "relevant_failure_modes": [
                {
                    "mode": fm,
                    "mitigation": failure_modes.get(fm, {}).get("mitigation_elements", []),
                }
                for fm in relevant_failures
            ],
            "rationale": (
                f"CRS risk: {crs_risk}. On-target/off-tumor: {risk_level}. "
                f"Tolerability class: {toxicity_class}. "
                f"Safety switch: {switch_needed}"
                + (f" ({', '.join(recommended_switches)})" if recommended_switches else "")
                + (". Logic gate REQUIRED." if logic_gate_needed else ".")
                + (f" Affinity tuning recommended." if affinity_tuning else "")
            ),
        }

    # ── D8: Clinical Evidence ────────────────────────────────────────

    def _d8_clinical_evidence(self, target: str, indication: str) -> dict:
        ev = self._fw.get("D8_clinical_evidence", {})

        relevant_successes = []
        for s in ev.get("landmark_successes", []):
            if (target.lower() in s.get("target", "").lower()
                    or indication.lower() in s.get("indication", "").lower()):
                relevant_successes.append(s)

        relevant_failures = []
        for f in ev.get("instructive_failures", []):
            if (target.lower() in f.get("target", "").lower()
                    or indication.lower() in str(f).lower()):
                relevant_failures.append(f)

        consensus = ev.get("field_consensus_2025", {})
        relevant_consensus = []
        for key, opinion in consensus.items():
            if any(kw in indication.lower() for kw in key.lower().split("_")):
                relevant_consensus.append({"area": key, "opinion": opinion})

        emerging = ev.get("emerging_concepts_2024_2025", [])
        confidence_model = self._fw.get("evidence_confidence_model", {}).get("levels", {})
        confidence_values = []
        for item in relevant_successes + relevant_failures:
            level = item.get("evidence_confidence")
            if level in confidence_model:
                confidence_values.append(confidence_model[level]["score"])
        mean_conf = round(sum(confidence_values) / len(confidence_values), 2) if confidence_values else None

        return {
            "relevant_successes": relevant_successes,
            "relevant_failures": relevant_failures,
            "field_consensus": relevant_consensus if relevant_consensus else [{"area": "general", "opinion": consensus.get("solid_tumor", "")}],
            "emerging_concepts": [e["concept"] for e in emerging[:5]],
            "average_confidence_score": mean_conf,
            "rationale": (
                f"Found {len(relevant_successes)} relevant success(es) and "
                f"{len(relevant_failures)} cautionary failure(s) for {target}/{indication}."
                + (f" Mean evidence confidence={mean_conf}/5." if mean_conf is not None else "")
            ),
        }

    # ── Synthesis ────────────────────────────────────────────────────

    def _d9_patient_fitness(self, fitness: str) -> dict:
        fw = self._fw.get("D9_patient_fitness_and_cmc", {}).get("fitness_levels", {})
        data = fw.get(fitness, fw.get("moderate_prior_therapy", {}))

        elements = []
        if fitness == "heavily_pretreated":
            elements.extend(["DNMT3A_KO_guide", "TET2_CRISPR_Target", "c_Jun_OE"])
        if self._strict_evidence_only and not self._entry_is_default_recommendable(data):
            elements = []

        return {
            "fitness_level": fitness,
            "cmc_recommendation": data.get("cmc_recommendation", ""),
            "engineering_impact": data.get("engineering_impact", ""),
            "evidence_confidence": data.get("evidence_confidence"),
            "sources": data.get("sources", []),
            "recommended_elements": elements[:1],
            "rationale": f"Patient fitness '{fitness}': {data.get('cmc_recommendation', '')} {data.get('engineering_impact', '')}"
        }

    def _d10_boolean_logic(self, target: str, secondary_target: str | None, indication: str) -> dict:
        fw = self._fw.get("D10_boolean_logic_routing", {}).get("logic_types", {})
        
        if not secondary_target:
            # Check if there's a recommended pair
            for ltype, ldata in fw.items():
                for pair in ldata.get("validated_pairs", []):
                    if not self._pair_matches_disease(pair, indication):
                        continue
                    if not self._pair_matches_target(pair, target):
                        continue
                    if self._strict_evidence_only and not self._entry_is_default_recommendable(pair):
                        continue
                    return {
                        "logic_type": "recommended_" + ltype,
                        "evidence_confidence": pair.get("evidence_confidence", "unknown"),
                        "sources": pair.get("sources", []),
                        "rationale": f"Single target {target} provided, but {ltype} is recommended for {indication} (e.g., {pair}).",
                        "recommended_elements": []
                    }
            return {
                "logic_type": "none",
                "evidence_confidence": None,
                "sources": [],
                "rationale": "Single target design, no boolean logic applied.",
                "recommended_elements": []
            }
            
        # If secondary target is provided, determine logic
        for ltype, ldata in fw.items():
            for pair in ldata.get("validated_pairs", []):
                if not self._pair_matches_disease(pair, indication):
                    continue
                if self._strict_evidence_only and not self._entry_is_default_recommendable(pair):
                    continue
                targets = pair.get("targets", [])
                if not targets:
                    targets = [pair.get("primer"), pair.get("killer"), pair.get("protector")]
                if target in targets and secondary_target in targets:
                    return {
                        "logic_type": ltype,
                        "evidence_confidence": pair.get("evidence_confidence", "unknown"),
                        "sources": pair.get("sources", []),
                        "rationale": f"Targets {target} + {secondary_target} match validated {ltype} for {indication}.",
                        "recommended_elements": ["iCAR_PSMA"] if ltype == "NOT_gate" and indication == "prostate_cancer" else []
                    }
                    
        if self._strict_evidence_only:
            return {
                "logic_type": "none",
                "evidence_confidence": None,
                "sources": [],
                "rationale": (
                    f"Targets {target} + {secondary_target} have no default-recommendable "
                    "clinical/approved evidence-backed logic rule in strict mode."
                ),
                "recommended_elements": []
            }

        return {
            "logic_type": "OR_gate",
            "evidence_confidence": "concept_only",
            "sources": [],
            "rationale": f"Targets {target} + {secondary_target} default to OR_gate (tandem/bicistronic) to prevent escape.",
            "recommended_elements": []
        }

    def _d11_regulatory_path(self, goal: str) -> dict:
        fw = self._fw.get("D11_regulatory_path", {}).get("paths", {})
        data = fw.get(goal, fw.get("clinical_fast_track", {}))
        
        return {
            "regulatory_goal": goal,
            "constraints": data.get("constraints", {}),
            "heuristic_constraints": data.get("heuristic_constraints", False),
            "evidence_confidence": data.get("evidence_confidence"),
            "sources": data.get("sources", []),
            "rationale": f"Regulatory goal '{goal}': Max transgenes = {data.get('constraints', {}).get('max_transgenes', 2)}."
        }

    def _synthesize_elements(self, d1, d2, d4, d5, d7, d9, d10, d11) -> dict:
        """Collect all element recommendations from all layers."""
        elements: dict[str, list[str]] = {
            "hinge_from_D2": d2.get("hinge_elements", []),
            "countermeasures_from_D5": d5.get("countermeasure_elements", []),
            "safety_switches_from_D7": d7.get("recommended_switches", []),
            "required_by_chassis_D4": d4.get("required_elements", []),
            "rescue_from_D9": d9.get("recommended_elements", []),
            "logic_from_D10": d10.get("recommended_elements", []),
        }

        # Apply D11 constraints with bias toward safety and highest-value add-ons.
        max_t = d11.get("constraints", {}).get("max_transgenes", 5)
        if self._strict_evidence_only and d11.get("heuristic_constraints"):
            max_t = 999
        protected = set(elements["safety_switches_from_D7"] + elements["required_by_chassis_D4"])
        optional_sequence = (
            elements["countermeasures_from_D5"]
            + elements["rescue_from_D9"]
            + elements["logic_from_D10"]
        )
        allowed_optional = max(max_t - 1 - len(protected), 0)
        kept_optional = optional_sequence[:allowed_optional]
        elements["countermeasures_from_D5"] = [
            eid for eid in elements["countermeasures_from_D5"] if eid in kept_optional
        ]
        elements["rescue_from_D9"] = [
            eid for eid in elements["rescue_from_D9"] if eid in kept_optional
        ]
        elements["logic_from_D10"] = [
            eid for eid in elements["logic_from_D10"] if eid in kept_optional
        ]

        return elements

    def _toxicity_profile(self, target: str) -> dict:
        model = self._fw.get("toxicity_tolerance_model", {})
        target_map = model.get("target_map", {})
        classes = model.get("classes", {})
        tol_class = target_map.get(target, "manageable_toxicity")
        return {"class": tol_class, **classes.get(tol_class, {})}

    def _entry_is_default_recommendable(self, entry: dict) -> bool:
        if not self._strict_evidence_only:
            return True
        allowed = set(
            self._fw.get("_metadata", {}).get(
                "default_recommendable_evidence_levels",
                ["approved_human", "clinical_human"],
            )
        )
        return bool(entry.get("sources")) and entry.get("evidence_confidence") in allowed

    @staticmethod
    def _pair_matches_target(pair: dict, target: str) -> bool:
        if target in pair.get("targets", []):
            return True
        return target in {pair.get("primer"), pair.get("killer"), pair.get("protector")}

    @staticmethod
    def _pair_matches_disease(pair: dict, indication: str) -> bool:
        return pair.get("disease") == indication

    def _build_summary(self, d1, d2, d3, d4, d5, d6, d7, d8, d9, d10, d11) -> str:
        lines = [
            "=" * 60,
            "11-LAYER DECISION ADVISORY SUMMARY",
            "=" * 60,
            f"D1 Disease:       {d1.get('category', '?')} — {d1.get('rationale', '')[:80]}",
            f"D2 Antigen:       {d2.get('target', '?')} — hinge={d2.get('hinge_recommendation', '?')}, risk={d2.get('density_safety', {}).get('risk', '?')}, tolerance={d2.get('toxicity_tolerance', {}).get('class', '?')}",
            f"D3 Delivery:      {d3.get('selected', '?')}",
            f"D4 Cell chassis:  {d4.get('selected', '?')}" + (f" (alt: {d4.get('alternative', '')})" if d4.get('alternative') else ""),
            f"D5 Microenv:      {d5.get('environment', '?')} (suppression: {d5.get('suppression_level', '?')})",
            f"D6 Vector:        {d6.get('selected', '?')} ({d6.get('payload_capacity_kb', '?')}kb)",
            f"D7 Safety:        CRS={d7.get('crs_risk', '?')}, switch={d7.get('safety_switch_needed', '?')}, logic_gate={'YES' if d7.get('logic_gate_needed') else 'no'}",
            f"D8 Evidence:      {len(d8.get('relevant_successes', []))} successes, {len(d8.get('relevant_failures', []))} warnings, mean_conf={d8.get('average_confidence_score', '?')}",
            f"D9 Patient/CMC:   {d9.get('fitness_level', '?')} — {d9.get('cmc_recommendation', '?')}",
            f"D10 Logic Gate:   {d10.get('logic_type', '?')} (conf: {d10.get('evidence_confidence', '?')})",
            f"D11 Regulatory:   {d11.get('regulatory_goal', '?')} (max transgenes: {d11.get('constraints', {}).get('max_transgenes', '?')})",
            f"Strict Evidence:  {'ON' if self._strict_evidence_only else 'OFF'}",
            "=" * 60,
        ]
        return "\n".join(lines)

    def _build_audit(
        self,
        target: str,
        indication: str,
        patient_fitness: str,
        regulatory_goal: str,
        secondary_target: str | None,
        d1: dict,
        d2: dict,
        d3: dict,
        d4: dict,
        d5: dict,
        d6: dict,
        d7: dict,
        d8: dict,
        d9: dict,
        d10: dict,
        d11: dict,
        recommended_elements: dict,
        therapeutic_window_hours: float | None = None,
    ) -> dict:
        layer_map = {
            "D1_disease_biology": d1,
            "D2_antigen_properties": d2,
            "D3_delivery_modality": d3,
            "D4_cell_chassis": d4,
            "D5_immune_microenvironment": d5,
            "D6_vector_integration": d6,
            "D7_safety_framework": d7,
            "D8_clinical_evidence": d8,
            "D9_patient_fitness_and_cmc": d9,
            "D10_boolean_logic_routing": d10,
            "D11_regulatory_path": d11,
        }
        used_layers = {
            name: {
                "evidence_confidence": layer.get("evidence_confidence")
                or layer.get("risk_class_evidence_confidence")
                or layer.get("average_confidence_score"),
                "sources": layer.get("sources", [])
                or layer.get("risk_class_sources", []),
                "rationale": layer.get("rationale", ""),
            }
            for name, layer in layer_map.items()
        }

        used_source_index = []
        for layer_name, entry in used_layers.items():
            for src in entry.get("sources", []):
                used_source_index.append({"layer": layer_name, **src})

        filtered_candidates = self._collect_filtered_candidates(
            indication, target, patient_fitness, regulatory_goal, secondary_target, d5
        )

        return {
            "parameters": {
                "target": target,
                "indication": indication,
                "patient_fitness": patient_fitness,
                "regulatory_goal": regulatory_goal,
                "secondary_target": secondary_target,
                "strict_evidence_only": self._strict_evidence_only,
                "therapeutic_window_hours": therapeutic_window_hours,
            },
            "used_layers": used_layers,
            "used_source_index": used_source_index,
            "recommended_elements": recommended_elements,
            "filtered_candidates": filtered_candidates,
        }

    def _collect_filtered_candidates(
        self,
        indication: str,
        target: str,
        patient_fitness: str,
        regulatory_goal: str,
        secondary_target: str | None,
        d5: dict,
    ) -> list[dict]:
        filtered: list[dict] = []
        if not self._strict_evidence_only:
            return filtered

        d9_data = self._fw.get("D9_patient_fitness_and_cmc", {}).get("fitness_levels", {}).get(patient_fitness, {})
        if d9_data and not self._entry_is_default_recommendable(d9_data):
            filtered.append({
                "layer": "D9_patient_fitness_and_cmc",
                "candidate": patient_fitness,
                "reason": "below_default_evidence_threshold",
                "evidence_confidence": d9_data.get("evidence_confidence"),
                "sources": d9_data.get("sources", []),
            })

        logic_types = self._fw.get("D10_boolean_logic_routing", {}).get("logic_types", {})
        for ltype, ldata in logic_types.items():
            for pair in ldata.get("validated_pairs", []):
                if not self._pair_matches_disease(pair, indication):
                    continue
                if secondary_target is None:
                    if not self._pair_matches_target(pair, target):
                        continue
                else:
                    targets = pair.get("targets", []) or [pair.get("primer"), pair.get("killer"), pair.get("protector")]
                    if target not in targets or secondary_target not in targets:
                        continue
                if not self._entry_is_default_recommendable(pair):
                    filtered.append({
                        "layer": "D10_boolean_logic_routing",
                        "candidate": pair,
                        "reason": "below_default_evidence_threshold",
                        "evidence_confidence": pair.get("evidence_confidence"),
                        "sources": pair.get("sources", []),
                    })

        env_name = d5.get("environment")
        envs = self._fw.get("D5_immune_microenvironment", {}).get("environments", {})
        supp_map = self._fw.get("D5_immune_microenvironment", {}).get("suppression_to_element_map", {})
        env = envs.get(env_name, {})
        dominant = env.get("dominant_suppression_by_tumor", {}).get(indication, env.get("dominant_suppression", []))
        for factor in dominant:
            mapping = supp_map.get(factor, {})
            if mapping.get("elements") and not self._entry_is_default_recommendable(mapping):
                filtered.append({
                    "layer": "D5_immune_microenvironment",
                    "candidate": factor,
                    "reason": "below_default_evidence_threshold",
                    "evidence_confidence": mapping.get("evidence_confidence"),
                    "sources": mapping.get("sources", []),
                })

        d11_data = self._fw.get("D11_regulatory_path", {}).get("paths", {}).get(regulatory_goal, {})
        if d11_data.get("heuristic_constraints"):
            filtered.append({
                "layer": "D11_regulatory_path",
                "candidate": regulatory_goal,
                "reason": "heuristic_constraints_not_used_for_strict_filtering",
                "evidence_confidence": d11_data.get("evidence_confidence"),
                "sources": d11_data.get("sources", []),
            })

        return filtered
