"""
CAR construct scoring engine.
Five dimensions, each 0–20 points → total 0–100:
  1. Clinical Precedent   — overlap with approved/trial products
  2. Safety               — safety switch, tier appropriateness
  3. Functional Completeness — required slots filled, no conflicts
  4. Innovation           — novel element combinations, 2024+ elements
  5. Domain Novelty       — component-level evidence when full-construct
                            precedent is unavailable (new disease domains)
"""
from __future__ import annotations
from typing import Any


class ConstructScorer:
    """Scores a CAR element list on 5 dimensions."""

    def __init__(
        self,
        library_idx: dict[str, dict],
        clinical_constructs: dict,
        rules: dict,
    ):
        self._lib = library_idx
        self._constructs = clinical_constructs.get("constructs", {})
        self._rules = rules

    def score(self, element_ids: list[str], validation_result: dict | None = None) -> dict:
        s1, d1 = self._score_precedent(element_ids)
        s2, d2 = self._score_safety(element_ids)
        s3, d3 = self._score_completeness(element_ids, validation_result)
        s4, d4 = self._score_innovation(element_ids)
        s5, d5 = self._score_domain_novelty(element_ids, s1)

        total = s1 + s2 + s3 + s4 + s5
        return {
            "total": total,
            "max": 100,
            "dimensions": {
                "clinical_precedent": {"score": s1, "max": 20, "detail": d1},
                "safety": {"score": s2, "max": 20, "detail": d2},
                "completeness": {"score": s3, "max": 20, "detail": d3},
                "innovation": {"score": s4, "max": 20, "detail": d4},
                "domain_novelty": {"score": s5, "max": 20, "detail": d5},
            },
        }

    def _score_precedent(self, ids: list[str]) -> tuple[int, str]:
        id_set = set(ids)
        best_match = ""
        best_overlap = 0

        for cid, construct in self._constructs.items():
            construct_ids = {e["id"] for e in construct.get("elements", [])}
            overlap = len(id_set & construct_ids)
            if overlap > best_overlap:
                best_overlap = overlap
                best_match = cid

        if not best_match:
            return 0, "No matching clinical precedent found"

        construct = self._constructs[best_match]
        construct_ids = {e["id"] for e in construct.get("elements", [])}
        overlap_pct = best_overlap / max(len(construct_ids), 1)

        approval = construct.get("approval", "")
        if "FDA" in approval or "EMA" in approval:
            tier_bonus = 5
        elif "Phase" in approval:
            tier_bonus = 2
        else:
            tier_bonus = 0

        raw = min(int(overlap_pct * 15) + tier_bonus, 20)
        detail = (
            f"Best match: {best_match} ({approval}), "
            f"{best_overlap}/{len(construct_ids)} elements overlap ({overlap_pct:.0%})"
        )
        return raw, detail

    def _score_safety(self, ids: list[str]) -> tuple[int, str]:
        score = 10  # baseline
        details = []
        id_set = set(ids)

        safety_cats = {"Safety Switch"}
        has_safety = any(
            self._lib.get(eid, {}).get("category") in safety_cats for eid in ids
        )
        if has_safety:
            score += 8
            details.append("Safety switch present (+8)")
        else:
            details.append("No safety switch (0)")

        tiers = [self._lib.get(eid, {}).get("regulatory_tier", "T3") for eid in ids]
        t1_count = sum(1 for t in tiers if t == "T1")
        t3_count = sum(1 for t in tiers if t == "T3")
        if t1_count >= 3:
            score += 5
            details.append(f"Multiple T1 elements ({t1_count}) (+5)")
        elif t3_count > len(ids) * 0.5:
            score += 0
            details.append(f"Majority T3 elements ({t3_count}) (+0)")
        else:
            score += 3
            details.append("Mixed tier (+3)")

        safety_rules = self._rules.get("constraints", {}).get(
            "indication_safety_rules", {}
        )
        on_target_risk = safety_rules.get("on_target_off_tumor_risk", {})
        risky_binders = set(on_target_risk.get("targets", []))
        if risky_binders & id_set and not has_safety:
            score = max(score - 10, 0)
            details.append("High on-target/off-tumor risk WITHOUT safety switch (-10)")

        return min(score, 20), "; ".join(details)

    def _score_completeness(
        self, ids: list[str], validation: dict | None
    ) -> tuple[int, str]:
        score = 15  # baseline
        details = []

        cats = {self._lib.get(eid, {}).get("category") for eid in ids}
        required_cats = {"Antigen Binder", "Primary Signaling Domain"}
        for rc in required_cats:
            if rc in cats:
                score += 2
                details.append(f"{rc} present (+2)")
            else:
                score -= 5
                details.append(f"{rc} MISSING (-5)")

        optional_cats = {"Signal Peptide", "Hinge & Spacer", "Transmembrane Domain"}
        for oc in optional_cats:
            if oc in cats:
                score += 1

        if validation:
            n_errors = len(validation.get("errors", []))
            if n_errors == 0:
                score += 3
                details.append("No validation errors (+3)")
            else:
                score -= n_errors * 2
                details.append(f"{n_errors} validation errors (-{n_errors*2})")

        return min(max(score, 0), 20), "; ".join(details)

    def _score_innovation(self, ids: list[str]) -> tuple[int, str]:
        score = 5  # baseline
        details = []

        novel_cats = {
            "Engineering Module", "Logic Gate & Switch",
        }
        novel_subs = {
            "Anti-Exhaustion", "Tumor Homing", "CRISPR KO",
            "In-Vivo", "iPSC", "CAR-Treg", "CAR-Macrophage",
        }

        novel_count = 0
        for eid in ids:
            e = self._lib.get(eid, {})
            cat = e.get("category", "")
            sub = e.get("subcategory", "")
            if cat in novel_cats or any(ns in sub for ns in novel_subs):
                novel_count += 1

        if novel_count >= 3:
            score += 15
            details.append(f"{novel_count} innovative elements (+15)")
        elif novel_count >= 1:
            score += novel_count * 5
            details.append(f"{novel_count} innovative element(s) (+{novel_count*5})")
        else:
            details.append("Standard elements only (+0)")

        all_construct_ids = set()
        for construct in self._constructs.values():
            all_construct_ids.update(e["id"] for e in construct.get("elements", []))
        novel_vs_clinical = set(ids) - all_construct_ids
        if len(novel_vs_clinical) >= 2:
            score += 5
            details.append(f"{len(novel_vs_clinical)} elements not in any clinical construct (+5)")

        return min(score, 20), "; ".join(details)

    def _score_domain_novelty(self, ids: list[str], precedent_score: int) -> tuple[int, str]:
        """Award points based on component-level evidence when no full-construct
        precedent exists. This prevents novel-domain designs (e.g. infectious
        disease CARs) from being unfairly penalized."""
        details = []

        if precedent_score >= 10:
            return 10, "Sufficient construct-level precedent exists; domain novelty baseline (10/20)"

        t1_count = 0
        t2_count = 0
        t3_count = 0
        for eid in ids:
            tier = self._lib.get(eid, {}).get("regulatory_tier", "T3")
            if tier == "T1":
                t1_count += 1
            elif tier == "T2":
                t2_count += 1
            else:
                t3_count += 1

        score = 0
        if t1_count >= 3:
            score += 12
            details.append(f"{t1_count} T1 (FDA-approved) elements — strong component-level evidence (+12)")
        elif t1_count >= 1:
            score += t1_count * 3
            details.append(f"{t1_count} T1 element(s) (+{t1_count * 3})")

        if t2_count >= 1:
            score += min(t2_count * 2, 6)
            details.append(f"{t2_count} T2 (clinical trial) element(s) (+{min(t2_count * 2, 6)})")

        novel_application_bonus = precedent_score == 0 and t1_count >= 2
        if novel_application_bonus:
            score += 4
            details.append("Novel application domain with proven components (+4)")

        if not details:
            details.append("No component-level evidence bonus")

        return min(score, 20), "; ".join(details)
