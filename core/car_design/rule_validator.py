"""
Rule-based CAR construct validator.
Checks element ordering, compatibility, cell-type constraints, and hard limits.
"""
from __future__ import annotations
from typing import Any


class RuleValidator:
    """Validates a CAR element list against design_rules.json."""

    def __init__(self, rules: dict, library_idx: dict[str, dict]):
        self._rules = rules
        self._lib = library_idx
        self._compat = rules.get("compatibility", {})
        self._constraints = rules.get("constraints", {})
        self._slot_cats = rules.get("slot_allowed_categories", {})

    def validate(
        self,
        element_ids: list[str],
        grammar_name: str | None = None,
        cell_type: str = "T",
    ) -> dict:
        errors: list[str] = []
        warnings: list[str] = []

        self._check_elements_exist(element_ids, errors)
        self._check_compatibility(element_ids, errors, warnings)
        self._check_cell_type(element_ids, cell_type, errors, warnings)
        self._check_hard_limits(element_ids, errors, warnings)

        if grammar_name:
            self._check_grammar(element_ids, grammar_name, errors, warnings)

        return {
            "valid": len(errors) == 0,
            "errors": errors,
            "warnings": warnings,
        }

    def _check_elements_exist(self, ids: list[str], errors: list[str]) -> None:
        for eid in ids:
            if eid not in self._lib:
                errors.append(f"Element '{eid}' not found in library")

    def _check_compatibility(
        self, ids: list[str], errors: list[str], warnings: list[str]
    ) -> None:
        id_set = set(ids)
        for eid in ids:
            rules = self._compat.get(eid, {})
            for incompat in rules.get("incompatible_with", []):
                if incompat in id_set:
                    reason = rules.get("reason", "")
                    errors.append(
                        f"Incompatible pair: {eid} + {incompat}. {reason}"
                    )
            for pref in rules.get("preferred_with", []):
                if pref not in id_set and pref in self._lib:
                    warnings.append(
                        f"{eid} works best with {pref} (not included)"
                    )

    def _check_cell_type(
        self, ids: list[str], cell_type: str, errors: list[str], warnings: list[str]
    ) -> None:
        ct_rules = self._constraints.get("cell_type_restrictions", {}).get(cell_type, {})
        id_set = set(ids)

        for field in ("forbidden_signaling", "forbidden_promoter", "forbidden_costim", "forbidden_payload"):
            for forbidden in ct_rules.get(field, []):
                if forbidden in id_set:
                    errors.append(
                        f"'{forbidden}' is forbidden in {cell_type} cell context"
                    )

        for required in ct_rules.get("required_payload", []):
            if required not in id_set:
                errors.append(
                    f"'{required}' is required for {cell_type} cell type"
                )

        for required in ct_rules.get("required_element", []):
            if required not in id_set:
                warnings.append(
                    f"'{required}' is expected for {cell_type} cell type"
                )

    def _check_hard_limits(
        self, ids: list[str], errors: list[str], warnings: list[str]
    ) -> None:
        total_len = 0
        binder_count = 0
        costim_count = 0
        safety_count = 0

        for eid in ids:
            e = self._lib.get(eid, {})
            total_len += e.get("length", 0)
            cat = e.get("category", "")
            if cat == "Antigen Binder":
                binder_count += 1
            elif cat == "Costimulatory Domain":
                costim_count += 1
            elif cat == "Safety Switch":
                safety_count += 1

        max_len = self._constraints.get("max_total_length_aa", 2000)
        min_len = self._constraints.get("min_total_length_aa", 300)
        if total_len > max_len:
            warnings.append(
                f"Total construct length {total_len}aa exceeds {max_len}aa limit"
            )
        if total_len < min_len and total_len > 0:
            warnings.append(
                f"Total construct length {total_len}aa is below {min_len}aa minimum"
            )

        if binder_count > self._constraints.get("max_binder_count", 2):
            errors.append(f"Too many binders ({binder_count})")
        if costim_count > self._constraints.get("max_costim_count", 2):
            errors.append(f"Too many costimulatory domains ({costim_count})")
        if safety_count > self._constraints.get("max_safety_switches", 2):
            warnings.append(f"Unusual: {safety_count} safety switches")

    def _check_grammar(
        self, ids: list[str], grammar_name: str, errors: list[str], warnings: list[str]
    ) -> None:
        grammars = self._rules.get("assembly_grammar", {})
        grammar = grammars.get(grammar_name)
        if not grammar:
            warnings.append(f"Unknown grammar '{grammar_name}'; skipping slot check")
            return

        id_set = set(ids)
        id_cats = {}
        for eid in ids:
            e = self._lib.get(eid, {})
            id_cats[eid] = e.get("category", "")

        required_slots = grammar.get("required", [])
        for slot in required_slots:
            allowed_cats = self._slot_cats.get(slot, [])
            if not allowed_cats:
                continue
            has_slot = any(id_cats.get(eid, "") in allowed_cats for eid in ids)
            if not has_slot:
                errors.append(
                    f"Grammar '{grammar_name}' requires slot '{slot}' "
                    f"(categories: {allowed_cats}) but none found"
                )
