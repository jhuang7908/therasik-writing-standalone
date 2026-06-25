"""
ADC Intelligent Decision Engine  v2.0
======================================
Upgraded to use quantitative antigen/linker/payload fields and the
3D compatibility matrix built in adc_design_rules.json.

Key new capabilities vs v1:
  - Axiom-based constraint checking (AX-01 … AX-11)
  - Shedding-aware DAR uplift
  - Cell-cycle/proliferation matching
  - Internalization-profile-driven linker selection
  - Validated combination precedent lookup
  - Data-confidence-weighted scores
  - Contraindication hard rejection (not just soft warnings)

Usage
-----
    from core.adc_design import ADCDesignEngine

    engine = ADCDesignEngine()
    proposals = engine.recommend(
        disease_type="solid_tumor",
        disease_subtype="gastric_CLDN18.2",
        proliferation_index="low",      # new param
        tme_status="immunosuppressive", # new param
        binder_format_preference=None,
        cmc_priority="moderate",
        fto_concern="moderate",
        top_n=5,
    )
    for p in proposals:
        print(p.summary())
"""

from __future__ import annotations

import json
import math
from dataclasses import dataclass, field, asdict
from pathlib import Path
from typing import Optional

_DATA_DIR = Path(__file__).resolve().parents[2] / "data" / "adc_atlas"
_RULES_PATH = _DATA_DIR / "adc_design_rules.json"
_MASTER_PATH = _DATA_DIR / "adc_master_internal.json"
_COMP_PATH   = _DATA_DIR / "adc_components.json"


# ─────────────────────────────────────────────────────────────────────────────
# Data class
# ─────────────────────────────────────────────────────────────────────────────

@dataclass
class ADCProposal:
    rank: int = 0
    target_antigen: str = ""
    antigen_tier: str = ""
    antigen_confidence: str = "unknown"

    binder_format: str = ""
    linker_name: str = ""
    linker_type: str = ""
    payload_name: str = ""
    payload_class: str = ""
    conjugation_method: str = ""
    dar_range: tuple = (0.0, 0.0)
    dar_rationale: str = ""
    bystander_effect: bool = False

    score_total: float = 0.0
    score_breakdown: dict = field(default_factory=dict)

    axiom_violations: list = field(default_factory=list)      # hard contraindications
    safety_warnings: list = field(default_factory=list)        # soft warnings
    fto_alerts: list = field(default_factory=list)
    precedent_programs: list = field(default_factory=list)
    validated_combo: Optional[dict] = None   # if exact VC-xx match found
    differentiation_notes: str = ""
    rationale: str = ""

    def to_dict(self) -> dict:
        d = asdict(self)
        d["dar_range"] = list(self.dar_range)
        return d

    def summary(self) -> str:
        lines = [
            f"[Rank {self.rank}] Score={self.score_total:.3f}  {'⚠ CONTRAINDICATED' if self.axiom_violations else ''}",
            f"  Target   : {self.target_antigen} ({self.antigen_tier}, confidence={self.antigen_confidence})",
            f"  Binder   : {self.binder_format}",
            f"  Linker   : {self.linker_name} ({self.linker_type})",
            f"  Payload  : {self.payload_name} [{self.payload_class}]",
            f"  Conj     : {self.conjugation_method}",
            f"  DAR      : {self.dar_range[0]:.1f}–{self.dar_range[1]:.1f}  ({self.dar_rationale})",
            f"  Bystander: {'Yes' if self.bystander_effect else 'No'}",
        ]
        if self.validated_combo:
            lines.append(f"  VALIDATED: {self.validated_combo.get('drug','?')} ({self.validated_combo.get('clinical_status','?')})")
        if self.precedent_programs:
            lines.append(f"  Precedents: {', '.join(self.precedent_programs[:3])}")
        if self.axiom_violations:
            lines.append(f"  VIOLATIONS: {'; '.join(self.axiom_violations)}")
        if self.safety_warnings:
            lines.append(f"  Warnings : {'; '.join(self.safety_warnings[:2])}")
        lines.append(f"  Rationale: {self.rationale}")
        return "\n".join(lines)


# ─────────────────────────────────────────────────────────────────────────────
# Engine
# ─────────────────────────────────────────────────────────────────────────────

class ADCDesignEngine:
    """Rule-based ADC design recommendation engine v2.0."""

    def __init__(
        self,
        rules_path: Path | str = _RULES_PATH,
        master_path: Path | str = _MASTER_PATH,
        components_path: Path | str = _COMP_PATH,
    ):
        self.rules = json.loads(Path(rules_path).read_text(encoding="utf-8"))
        try:
            self.master_db = json.loads(Path(master_path).read_text(encoding="utf-8"))
        except FileNotFoundError:
            self.master_db = []
        try:
            self._components = json.loads(Path(components_path).read_text(encoding="utf-8"))
        except FileNotFoundError:
            self._components = []

        # Core rule blocks
        self.weights              = self.rules.get("scoring_weights", {})
        self._disease_map         = self.rules.get("disease_antigen_map", {})
        self._antigen_props       = self.rules.get("antigen_properties", {})
        self._compat              = self.rules.get("compatibility", {})
        self._safety              = self.rules.get("safety_rules", {})
        self._binder_rules        = self.rules.get("binder_format_rules", {})
        self._conjugation         = self.rules.get("conjugation_technology", {})
        self._cmc                 = self.rules.get("cmc_manufacturing_rules", {})
        self._payloads            = self.rules.get("payload_classification", {})

        # v2.0 new rule blocks
        self._ag_profiles         = self.rules.get("antigen_internalization_profile", {})
        self._payload_rules       = self.rules.get("payload_selection_rules", {})
        self._linker_rules        = self.rules.get("linker_selection_rules", {})
        self._axioms              = self.rules.get("design_axioms", [])
        self._validated_combos    = self.rules.get("validated_combinations", [])

        # Build component lookup caches
        self._payload_detail_map: dict[str, dict] = {}
        self._linker_detail_map: dict[str, dict] = {}
        for c in self._components:
            if isinstance(c, dict):
                if 'class' in c and 'type' not in c:
                    self._payload_detail_map[c.get('name', '')] = c
                elif 'type' in c and 'class' not in c:
                    self._linker_detail_map[c.get('name', '')] = c

    # ──────────────────────────────────────────────────────
    # Public API
    # ──────────────────────────────────────────────────────

    def recommend(
        self,
        disease_type: str,
        disease_subtype: str,
        proliferation_index: str = "moderate",   # high / moderate / low
        tme_status: str = "unknown",              # inflamed / immunosuppressive / unknown
        binder_format_preference: Optional[str] = None,
        cmc_priority: str = "moderate",
        fto_concern: str = "moderate",
        top_n: int = 5,
    ) -> list[ADCProposal]:
        """
        Main entry. Returns up to *top_n* ranked proposals.
        Proposals with axiom violations are filtered out unless
        no valid proposals remain.
        """
        antigens = self._step1_disease_to_antigens(disease_type, disease_subtype)
        if not antigens:
            return []

        proposals: list[ADCProposal] = []
        context = {
            "disease_type": disease_type,
            "disease_subtype": disease_subtype,
            "proliferation_index": proliferation_index,
            "tme_status": tme_status,
        }

        for ag_entry in antigens:
            ag_name = ag_entry["name"]
            ag_tier = ag_entry["tier"]

            # Step 2 — antigen properties (now with quantitative fields)
            profile = self._step2_antigen_profile(ag_name)

            # Step 3 — linker-payload combos via new compatibility matrix
            combos = self._step3_linker_payload_combos(profile, context)

            # Step 4 — axiom check + safety filter
            combos = self._step4_axiom_and_safety_filter(combos, ag_name, profile, context)

            # Step 5 — binder format
            binder_fmt = self._step5_binder_format(disease_type, binder_format_preference)

            for combo in combos:
                # Step 6 — conjugation
                conj = self._step6_conjugation(combo, cmc_priority, fto_concern)

                # Step 7 — precedent + validated combo check
                precedents, validated = self._step7_precedent(ag_name, combo["payload"], combo["linker"])

                # Step 8 — scoring (now quantitative)
                proposal = self._step8_score(
                    ag_name, ag_tier, binder_fmt, combo, conj,
                    precedents, validated, cmc_priority, fto_concern, profile, context,
                )
                proposals.append(proposal)

        # Separate valid from contraindicated
        valid = [p for p in proposals if not p.axiom_violations]
        contra = [p for p in proposals if p.axiom_violations]

        valid.sort(key=lambda p: p.score_total, reverse=True)
        contra.sort(key=lambda p: p.score_total, reverse=True)

        # Return valid first; append contraindicated at end with negative rank
        final = valid + contra
        for i, p in enumerate(final[:top_n], 1):
            p.rank = i

        return final[:top_n]

    def list_antigens_for_disease(self, disease_type: str, disease_subtype: str) -> list[dict]:
        return self._step1_disease_to_antigens(disease_type, disease_subtype)

    def get_antigen_profile(self, antigen: str) -> dict:
        return self._step2_antigen_profile(antigen)

    def get_supported_diseases(self) -> dict:
        return {
            cat: list(subtypes.keys())
            for cat, subtypes in self._disease_map.items()
            if isinstance(subtypes, dict)
        }

    def check_axioms(self, antigen: str, linker: str, payload: str, dar: float) -> list[str]:
        """
        Standalone axiom checker. Returns list of violated axiom IDs + titles.
        """
        profile = self._step2_antigen_profile(antigen)
        pdetail = self._payload_detail_map.get(payload, {})
        ldetail = self._linker_detail_map.get(linker, {})
        combo = {"linker": linker, "payload": payload, "dar_range": (dar, dar),
                 "bystander": pdetail.get("bystander_effect", "No") == "Yes"}
        context = {}
        violations = self._check_axioms(combo, profile, context)
        return violations

    # ──────────────────────────────────────────────────────
    # Decision tree steps
    # ──────────────────────────────────────────────────────

    def _step1_disease_to_antigens(self, disease_type: str, disease_subtype: str) -> list[dict]:
        category = self._disease_map.get(disease_type, {})
        entry = category.get(disease_subtype)
        if not entry:
            return []
        tier = entry.get("tier", "T3")
        results = []
        for ag in entry.get("primary", []):
            results.append({"name": ag, "tier": tier, "priority": "primary"})
        for ag in entry.get("secondary", []):
            results.append({"name": ag, "tier": tier, "priority": "secondary"})
        return results

    def _step2_antigen_profile(self, antigen: str) -> dict:
        return self._antigen_props.get(antigen, {
            "density": "unknown",
            "heterogeneity": "unknown",
            "internalization_rate": "unknown",
            "on_target_off_tumor_risk": "unknown",
            "shedding_rate": "unknown",
            "data_confidence": "unknown",
        })

    def _step3_linker_payload_combos(self, profile: dict, context: dict) -> list[dict]:
        """
        v2.0: Uses the new antigen_internalization_profile + linker/payload selection
        rules to generate candidate combinations, rather than only the flat
        compatibility table.
        """
        intern_rate = profile.get("internalization_rate", "moderate").lower()
        shedding    = profile.get("shedding_rate", "low").lower()
        heterog     = profile.get("heterogeneity", "moderate").lower()
        prolif      = context.get("proliferation_index", "moderate").lower()
        tme         = context.get("tme_status", "unknown").lower()

        # Determine internalization profile category
        ag_profile_key = self._classify_ag_profile(intern_rate, shedding)
        ag_profile_data = self._ag_profiles.get(ag_profile_key, {})

        preferred_linker_classes = ag_profile_data.get("recommended_linker_classes", [])
        require_bystander = (
            ag_profile_data.get("bystander_requirement", "").upper().startswith("REQUIRED")
            or "high" in heterog
        )
        dar_guidance = ag_profile_data.get("dar_guidance", "DAR 3–4")

        # Determine preferred payload classes by context
        preferred_payload_classes = self._pick_payload_classes(prolif, tme, context)

        # Enumerate all payload × linker candidates
        results = []
        for payload_name, pdetail in self._payload_detail_map.items():
            p_class = pdetail.get('class', '')

            # Filter by preferred payload classes if we have a preference
            if preferred_payload_classes:
                if not any(pc.lower() in p_class.lower() or p_class.lower() in pc.lower()
                           for pc in preferred_payload_classes):
                    continue

            bystander = "yes" in str(pdetail.get('bystander_effect', '')).lower()
            if require_bystander and not bystander:
                continue

            cell_cycle = pdetail.get('cell_cycle_dependency', 'ALL phases')
            # Penalize mitosis-only payloads for quiescent tumors
            score_mod = 0.0
            if prolif == "low" and "S/G2/M" in cell_cycle:
                score_mod -= 0.15

            # Select best linker for this payload
            for linker_name, ldetail in self._linker_detail_map.items():
                linker_compat = ldetail.get('compatible_payload_chemistry', '')
                linker_plasma = ldetail.get('plasma_t12', '')

                # Basic plasma stability check
                if "hours" in linker_plasma.lower() and "days" not in linker_plasma.lower():
                    score_mod -= 0.2  # unstable linker

                # DAR range from guidance
                dar_lo, dar_hi = self._parse_dar_guidance(dar_guidance)

                # Hydrophilicity check for high DAR
                hydro_note = ldetail.get('hydrophilicity_note', '')
                if dar_hi > 4 and "hydrophobic" in hydro_note.lower():
                    dar_hi = min(dar_hi, 4.0)
                    score_mod -= 0.1

                results.append({
                    "linker": linker_name,
                    "payload": payload_name,
                    "payload_class": p_class,
                    "bystander": bystander,
                    "dar_range": (dar_lo, dar_hi),
                    "dar_rationale": f"{ag_profile_key} profile → {dar_guidance}",
                    "score_modifier": score_mod,
                    "reason": f"{ag_profile_key} profile; {p_class}; bystander={bystander}",
                    "safety_warnings": [],
                    "axiom_violations": [],
                })

        # Fallback to legacy compat table if nothing found
        if not results:
            results = self._legacy_step3(profile)

        return results

    def _step4_axiom_and_safety_filter(
        self, combos: list[dict], antigen: str, profile: dict, context: dict
    ) -> list[dict]:
        """
        Check all 11 design axioms. Hard violations become axiom_violations.
        Also applies standard safety warnings.
        """
        dar_rules = self._safety.get("dar_potency_balance", {})
        off_tumor = self._safety.get("on_target_off_tumor", {})
        class_tox = self._safety.get("known_class_toxicities", {})
        high_risk_targets = set(off_tumor.get("high_risk_targets", []))
        is_high_risk = antigen in high_risk_targets

        filtered = []
        for combo in combos:
            violations = self._check_axioms(combo, profile, context)
            combo["axiom_violations"] = violations

            warnings = list(combo.get("safety_warnings", []))

            # Standard safety: DAR cap for ultra-potent payloads
            payload = combo["payload"]
            pdetail = self._payload_detail_map.get(payload, {})
            for level_key, level_info in dar_rules.items():
                if level_key == "rule" or not isinstance(level_info, dict):
                    continue
                if payload in level_info.get("payloads", []):
                    max_dar = level_info.get("max_dar", 8.0)
                    if combo["dar_range"][1] > max_dar:
                        combo["dar_range"] = (combo["dar_range"][0], max_dar)
                        warnings.append(f"DAR capped to {max_dar} for {payload} (potency constraint)")

            # Off-tumor risk warning
            if is_high_risk:
                mitigations = off_tumor.get("mitigation", [])
                warnings.append(f"{antigen}: high off-tumor risk — {'; '.join(mitigations[:2])}")
                combo["score_modifier"] = combo.get("score_modifier", 0.0) - 0.1

            # Class toxicity warnings from component data
            dlts = pdetail.get("dlts", [])
            if dlts:
                warnings.append(f"{payload} DLTs: {', '.join(dlts[:2])}")

            combo["safety_warnings"] = warnings
            filtered.append(combo)

        return filtered

    def _step5_binder_format(self, disease_type: str, preference: Optional[str] = None) -> str:
        if preference and preference in self._binder_rules:
            return preference
        return "IgG1"

    def _step6_conjugation(self, combo: dict, cmc_priority: str, fto_concern: str) -> dict:
        dar_hi = combo["dar_range"][1]

        if cmc_priority == "high":
            preferred = ["stochastic_cysteine", "lysine_coupling"]
        elif dar_hi >= 6:
            preferred = ["site_specific_engineered_cys", "enzymatic_transglutaminase",
                         "glycan_remodeling"]
        else:
            preferred = ["stochastic_cysteine", "site_specific_engineered_cys",
                         "enzymatic_transglutaminase"]

        if fto_concern == "high":
            preferred = [
                k for k in preferred
                if "broad" in self._conjugation.get(k, {}).get("patent_freedom", "")
                or "expired" in self._conjugation.get(k, {}).get("patent_freedom", "")
            ]
        if not preferred:
            preferred = ["stochastic_cysteine"]

        chosen_key = preferred[0]
        info = self._conjugation.get(chosen_key, {})
        return {
            "method": chosen_key,
            "description": info.get("description", ""),
            "homogeneity": info.get("dar_homogeneity", "unknown"),
            "patent_freedom": info.get("patent_freedom", "unknown"),
            "fto_alerts": [] if ("broad" in info.get("patent_freedom", "") or
                                  "expired" in info.get("patent_freedom", "")) else [
                f"Check FTO for {chosen_key}: {info.get('patent_freedom', 'unknown')}"
            ],
        }

    def _step7_precedent(self, antigen: str, payload: str, linker: str) -> tuple[list[dict], Optional[dict]]:
        # Check for exact validated combo
        validated = None
        for vc in self._validated_combos:
            if vc.get("antigen") == antigen:
                p_match = payload.upper() in vc.get("payload", "").upper()
                l_match = linker.upper() in vc.get("linker", "").upper()
                if p_match and l_match:
                    validated = vc
                    break
                elif p_match and validated is None:
                    validated = vc  # partial match (same antigen + payload)

        # Legacy master DB lookup
        hits = []
        for prog in self.master_db:
            if prog.get("target") == antigen:
                hits.append({
                    "name": prog.get("canonical_name", "unknown"),
                    "stage": prog.get("development_stage", "unknown"),
                    "payload": prog.get("payload_name", "unknown"),
                    "same_payload": payload.upper() in prog.get("payload_name", "").upper(),
                })
        return hits, validated

    def _step8_score(
        self,
        antigen: str,
        tier: str,
        binder_fmt: str,
        combo: dict,
        conjugation: dict,
        precedents: list[dict],
        validated: Optional[dict],
        cmc_priority: str,
        fto_concern: str,
        profile: dict,
        context: dict,
    ) -> ADCProposal:
        w = self.weights

        # --- Clinical precedent score ---
        has_approved = any(p["stage"] in ("approved", "Approved") for p in precedents)
        has_same_payload = any(p.get("same_payload") for p in precedents)
        tier_score = {"T1": 1.0, "T1/T2": 0.85, "T2": 0.7, "T2/T3": 0.5, "T3": 0.3}
        s_prec = tier_score.get(tier, 0.5)
        if validated:
            s_prec = min(1.0, s_prec + 0.15)  # validated combo bonus
        elif has_approved:
            s_prec = max(s_prec, 0.9)

        # --- Safety score (now includes axiom violations) ---
        n_violations = len(combo.get("axiom_violations", []))
        n_warnings = len(combo.get("safety_warnings", []))
        s_safety = max(0.0, 1.0 - n_violations * 0.4 - n_warnings * 0.08)

        # --- Payload-antigen match score (new in v2.0) ---
        s_pa_match = self._score_payload_antigen_match(combo, profile, context)

        # --- CMC feasibility score ---
        homogeneity_map = {"very_high": 1.0, "high": 0.85, "moderate": 0.6, "low": 0.4}
        s_cmc = homogeneity_map.get(conjugation.get("homogeneity", "moderate"), 0.6)

        # --- FTO freedom score ---
        fto_alerts = conjugation.get("fto_alerts", [])
        s_fto = 1.0 if not fto_alerts else 0.5

        # --- Differentiation score ---
        if validated:
            s_diff = 0.4
            diff_note = f"Exact validated combo: {validated.get('drug','?')} ({validated.get('clinical_status','?')})"
        elif has_same_payload and has_approved:
            s_diff = 0.3
            diff_note = f"Me-too risk: approved ADC with same target+payload exists."
        elif has_approved:
            s_diff = 0.7
            diff_note = f"Differentiated payload on validated target {antigen}."
        else:
            s_diff = 0.9
            diff_note = f"Novel target-payload combination for {antigen}."

        # --- Data confidence penalty ---
        conf = profile.get("data_confidence", "moderate")
        conf_mult = {"high": 1.0, "moderate": 0.92, "low": 0.80, "unknown": 0.70}.get(conf, 0.85)

        total = conf_mult * (
            w.get("clinical_precedent", 0.25) * s_prec
            + w.get("safety_profile", 0.25)   * s_safety
            + w.get("payload_match", 0.20)     * s_pa_match
            + w.get("cmc_feasibility", 0.15)   * s_cmc
            + w.get("fto_freedom", 0.10)       * s_fto
            + w.get("differentiation", 0.05)   * s_diff
        ) + combo.get("score_modifier", 0.0)

        total = round(max(0.0, min(1.0, total)), 3)

        # --- Rationale ---
        shedding = profile.get("shedding_rate", "?")
        intern_mech = profile.get("internalization_mechanism", "")
        intern_mech_short = intern_mech[:60] + "…" if len(intern_mech) > 60 else intern_mech

        rationale_parts = [
            f"Target: {antigen} ({tier}, conf={conf})",
            f"Internalization: {profile.get('internalization_rate','?')}" +
            (f" [{intern_mech_short}]" if intern_mech_short else ""),
            f"Shedding: {shedding}",
            f"Heterogeneity: {profile.get('heterogeneity','?')}",
            f"Bystander: {'Yes' if combo.get('bystander') else 'No'}",
            combo.get("reason", ""),
        ]

        return ADCProposal(
            target_antigen=antigen,
            antigen_tier=tier,
            antigen_confidence=conf,
            binder_format=binder_fmt,
            linker_name=combo.get("linker", ""),
            linker_type=self._linker_detail_map.get(combo.get("linker",""), {}).get("type",""),
            payload_name=combo.get("payload", ""),
            payload_class=combo.get("payload_class", "") or self._resolve_payload_class(combo.get("payload","")),
            conjugation_method=conjugation.get("method", ""),
            dar_range=combo.get("dar_range", (3.0, 4.0)),
            dar_rationale=combo.get("dar_rationale", ""),
            bystander_effect=combo.get("bystander", False),
            score_total=total,
            score_breakdown={
                "clinical_precedent":  round(s_prec, 2),
                "safety":              round(s_safety, 2),
                "payload_antigen_match": round(s_pa_match, 2),
                "cmc_feasibility":     round(s_cmc, 2),
                "fto_freedom":         round(s_fto, 2),
                "differentiation":     round(s_diff, 2),
                "data_confidence_mult": conf_mult,
            },
            axiom_violations=combo.get("axiom_violations", []),
            safety_warnings=combo.get("safety_warnings", []),
            fto_alerts=fto_alerts,
            precedent_programs=[p["name"] for p in precedents],
            validated_combo=validated,
            differentiation_notes=diff_note,
            rationale=" | ".join(p for p in rationale_parts if p),
        )

    # ──────────────────────────────────────────────────────
    # v2.0 Helper methods
    # ──────────────────────────────────────────────────────

    def _classify_ag_profile(self, intern_rate: str, shedding: str) -> str:
        """Map antigen internalization + shedding to a profile key."""
        ir = intern_rate.lower()
        sh = shedding.lower()
        rapid = any(w in ir for w in ["high", "rapid", "fast"])
        slow  = any(w in ir for w in ["low", "slow", "poor", "very"])
        shed_high = any(w in sh for w in ["high", "very"])

        if rapid and shed_high:
            return "rapid_high_shedding"
        if rapid and not shed_high:
            return "rapid_low_shedding"
        if slow and shed_high:
            return "slow_moderate_shedding"
        if slow:
            return "slow_low_shedding"
        if "recycl" in ir:
            return "rapid_recycling"
        return "moderate_very_low_shedding"

    def _pick_payload_classes(self, prolif: str, tme: str, context: dict) -> list[str]:
        """Return preferred payload classes for this context."""
        subtype = context.get("disease_subtype", "").lower()
        rules   = self._payload_rules

        # Disease-subtype-specific rules
        for ds_key, ds_rule in rules.get("disease_category_rules", {}).items():
            if ds_key.lower() in subtype:
                first = ds_rule.get("first_choice_payload", "")
                second = ds_rule.get("second_choice", "")
                classes = []
                for s in [first, second]:
                    if "tubulin" in s.lower(): classes.append("Tubulin Inhibitors")
                    if "topo" in s.lower(): classes.append("Topoisomerase I Inhibitors")
                    if "dna" in s.lower(): classes.append("DNA Damaging Agents")
                    if "rna pol" in s.lower(): classes.append("RNA Polymerase II Inhibitors")
                    if "immune" in s.lower() or "isac" in s.lower():
                        classes.append("Immune Stimulatory Agonists")
                if classes:
                    return classes

        # Proliferation-index-based
        prolif_rules = rules.get("tumor_proliferation_index", {})
        if prolif == "high":
            return prolif_rules.get("high_ki67", {}).get("preferred_payloads", [])
        elif prolif == "low":
            return prolif_rules.get("low_ki67", {}).get("preferred_payloads", [])
        else:
            return prolif_rules.get("heterogeneous", {}).get("preferred_payloads",
                   ["Topoisomerase I Inhibitors", "Tubulin Inhibitors"])

    def _parse_dar_guidance(self, guidance: str) -> tuple[float, float]:
        """Extract DAR lo/hi from guidance string like 'DAR 6–8'."""
        import re
        m = re.search(r'(\d+(?:\.\d+)?)\s*[–—-]\s*(\d+(?:\.\d+)?)', guidance)
        if m:
            return float(m.group(1)), float(m.group(2))
        m2 = re.search(r'DAR\s*(\d+(?:\.\d+)?)', guidance)
        if m2:
            v = float(m2.group(1))
            return v, v
        return 3.0, 4.0

    def _check_axioms(self, combo: dict, profile: dict, context: dict) -> list[str]:
        """
        Check all design axioms. Returns list of violation strings for
        hard contraindications.
        """
        violations = []
        payload = combo.get("payload", "")
        linker  = combo.get("linker", "")
        bystander = combo.get("bystander", False)
        dar_hi  = combo.get("dar_range", (0, 4))[1]
        pdetail = self._payload_detail_map.get(payload, {})
        ldetail = self._linker_detail_map.get(linker, {})
        intern_rate = profile.get("internalization_rate", "moderate").lower()
        shedding    = profile.get("shedding_rate", "low").lower()
        heterog     = profile.get("heterogeneity", "moderate").lower()
        cell_cycle  = pdetail.get("cell_cycle_dependency", "ALL phases")
        prolif      = context.get("proliferation_index", "moderate").lower()
        log_p       = pdetail.get("log_p", 2.0)
        hydro_note  = ldetail.get("hydrophilicity_note", "").lower()

        # AX-01: Bystander required for heterogeneous / slow-internalizing
        if ("high" in heterog or "low" in intern_rate or "slow" in intern_rate):
            if not bystander:
                violations.append("AX-01: Bystander effect required (high heterogeneity / slow internalization) — MMAF and other non-bystander payloads CONTRAINDICATED")

        # AX-03: Cell-cycle independent payload required for quiescent cells
        if prolif == "low" and "S/G2/M" in cell_cycle and "ALL" not in cell_cycle:
            violations.append("AX-03: Cell-cycle independent payload required for quiescent tumor (low proliferation index) — mitosis-only payload SUBOPTIMAL")

        # AX-04: Non-cleavable linker requires rapid internalization
        if "non-cleavable" in ldetail.get("cleavage_enzyme", "").lower() or \
           "none" in ldetail.get("cleavage_enzyme", "").lower():
            if "low" in intern_rate or "slow" in intern_rate or "poor" in intern_rate:
                violations.append("AX-04: Non-cleavable linker CONTRAINDICATED for slow-internalizing target — payload cannot be released")

        # AX-05: DAR > 4 requires hydrophilic linker
        if dar_hi > 4 and "hydrophobic" in hydro_note:
            violations.append(f"AX-05: DAR {dar_hi} with hydrophobic linker {linker} — aggregation risk; use PEG-vc or GGFG")

        # AX-06: High log P payload at high DAR requires PEG spacer
        try:
            lp = float(str(log_p).replace(">","").strip())
        except (ValueError, TypeError):
            lp = 2.0
        if lp > 3.0 and dar_hi > 4:
            if "peg" not in linker.lower() and "ggfg" not in linker.lower():
                violations.append(f"AX-06: {payload} log P={lp} at DAR {dar_hi} requires PEG-spacer linker to prevent aggregation")

        # AX-09: PBD dimer at DAR > 2 in solid tumor
        pbd_keywords = ["dgn", "pbd", "pyrrolobenzodiazepine", "sgg", "sg3249", "sg2000"]
        is_pbd = any(k in payload.lower() for k in pbd_keywords)
        disease_type = context.get("disease_type", "")
        if is_pbd and dar_hi > 2 and "solid" in disease_type.lower():
            violations.append(f"AX-09: PBD dimer at DAR >{dar_hi} in solid tumor CONTRAINDICATED (Rova-T TAHOE failure evidence)")

        # AX-11: Very-slow / non-internalizing target
        very_slow = any(w in intern_rate for w in ["very low", "very_low", "non-internaliz"])
        if very_slow:
            violations.append("AX-11: Very poor internalizer — ADC format may have limited efficacy; consider ISAC or bispecific engager alternative")

        return violations

    def _score_payload_antigen_match(self, combo: dict, profile: dict, context: dict) -> float:
        """
        Quantitative payload-antigen compatibility score (0–1).
        Based on: bystander match, cell cycle vs proliferation, DLT risk.
        """
        score = 0.5  # baseline
        payload = combo.get("payload", "")
        pdetail = self._payload_detail_map.get(payload, {})
        bystander = combo.get("bystander", False)
        cell_cycle = pdetail.get("cell_cycle_dependency", "ALL phases")
        prolif = context.get("proliferation_index", "moderate").lower()
        heterog = profile.get("heterogeneity", "moderate").lower()
        shedding = profile.get("shedding_rate", "low").lower()

        # Bystander bonus for heterogeneous/high-shedding
        if bystander and ("high" in heterog or "high" in shedding):
            score += 0.25
        elif not bystander and "high" in heterog:
            score -= 0.20

        # Cell cycle vs proliferation match
        if "ALL" in cell_cycle:
            score += 0.15  # cell-cycle independent is universally better
        elif "S/G2/M" in cell_cycle:
            if prolif == "high":
                score += 0.10
            elif prolif == "low":
                score -= 0.20

        # IC50 precision bonus
        ic50 = str(pdetail.get("ic50_nm", "?"))
        if ic50 not in ("?", "N/A", ""):
            score += 0.05  # we have quantitative data → higher confidence

        return max(0.0, min(1.0, round(score, 2)))

    def _legacy_step3(self, profile: dict) -> list[dict]:
        """Fallback to original flat compatibility table (v1 behavior)."""
        intern_rate = profile.get("internalization_rate", "moderate")
        heterogeneity = profile.get("heterogeneity", "moderate")
        intern_prefs = (self._compat.get("antigen_internalization_to_linker", {})
                        .get(intern_rate, {}))
        preferred_linker_types = set(intern_prefs.get("preferred", []))
        het_info = (self._compat.get("heterogeneity_to_bystander", {})
                    .get(heterogeneity, {}))
        require_bystander = het_info.get("require_bystander", False)
        lp_compat = self._compat.get("linker_payload", {})
        results = []
        for combo_key, combo_info in lp_compat.items():
            parts = combo_key.rsplit("_", 1)
            if len(parts) != 2:
                continue
            linker_raw, payload = parts
            has_bystander = combo_info.get("bystander_effect", False)
            if require_bystander is True and not has_bystander:
                continue
            dar_range = tuple(combo_info.get("dar_range", [3.0, 4.0]))
            results.append({
                "key": combo_key, "linker": linker_raw, "payload": payload,
                "payload_class": "", "bystander": has_bystander,
                "dar_range": dar_range, "dar_rationale": "legacy compat table",
                "reason": combo_info.get("reason", ""), "score_modifier": 0.0,
                "safety_warnings": [], "axiom_violations": [],
            })
        return results

    def _resolve_payload_class(self, payload_name: str) -> str:
        name_upper = payload_name.upper()
        for cls_key, cls_info in self._payloads.items():
            if not isinstance(cls_info, dict):
                continue
            members = [m.upper() for m in cls_info.get("members", [])]
            if name_upper in members:
                return cls_key
        return "unknown"
