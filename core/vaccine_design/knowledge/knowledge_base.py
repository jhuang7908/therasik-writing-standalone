"""Unified query interface over the canonical vaccine knowledge database."""

from __future__ import annotations

import json
import logging
import re
from pathlib import Path
from typing import Any

import pandas as pd

logger = logging.getLogger(__name__)


ROOT = Path(__file__).resolve().parents[3]
DEFAULT_DB_PATH = ROOT / "docs" / "vaccine_kb_data.json"


def _read_json(path: Path) -> dict[str, Any]:
    with path.open(encoding="utf-8") as handle:
        return json.load(handle)


def _search_blob(value: Any) -> str:
    if isinstance(value, str):
        return value
    if isinstance(value, dict):
        return " ".join(_search_blob(v) for v in value.values())
    if isinstance(value, list):
        return " ".join(_search_blob(v) for v in value)
    return str(value)


class VaccineKnowledgeBase:
    """Single-source runtime loader for the canonical vaccine database."""

    def __init__(self, db_path: str | Path | None = None):
        self.db_path = Path(db_path) if db_path else DEFAULT_DB_PATH
        self.data = _read_json(self.db_path)
        modules = self.data["modules"]
        self.tumor = modules["antigens"]["tumor"]
        self.infectious = modules["antigens"]["infectious"]
        self.tolerogenic = modules["antigens"]["tolerogenic"]
        self.platforms = modules["delivery"]["platforms"]
        self.adjuvants = modules["delivery"]["adjuvants"]
        self.adjuvantic_epitopes = modules["delivery"]["adjuvantic_epitopes"]
        self.tcr_clones = modules["tcr"]["clones"]
        self.tcr_motifs = modules["tcr"]["public_motifs"]
        self.tcr_rules = modules["tcr"]["design_rules"]
        self.mrna_rules = modules["methods"]["multi_epitope_mrna"]
        self.neo_benchmarks = modules["methods"]["neoantigen_benchmarks"]
        self.design_playbooks = modules["methods"]["design_playbooks"]
        self.assay_catalog = modules["methods"]["assay_catalog"]
        self.private_learning = modules["methods"]["private_learning"]
        self.scenario_guides = modules["decision_support"]["scenario_guides"]

    def _iter_epitopes(self) -> list[dict[str, Any]]:
        rows: list[dict[str, Any]] = []
        for record in self.tumor:
            for ep in record["epitopes"]["mhc_i"] + record["epitopes"]["mhc_ii"]:
                rows.append(
                    {
                        "track": "tumor",
                        "antigen": record["name"],
                        "disease_context": "; ".join(record["disease_context"]),
                        **ep,
                    }
                )
        for record in self.infectious:
            for ep in record["epitopes"]["mhc_i"] + record["epitopes"]["mhc_ii"]:
                rows.append(
                    {
                        "track": "infectious",
                        "antigen": f"{record['pathogen']} / {record['antigen_name']}",
                        "disease_context": record["disease"],
                        **ep,
                    }
                )
        for record in self.tolerogenic:
            for ep in record["epitopes"]["mixed"]:
                rows.append(
                    {
                        "track": "tolerogenic",
                        "antigen": record["target_antigen"],
                        "disease_context": record["disease"],
                        **ep,
                    }
                )
        return rows

    def stats(self) -> dict[str, Any]:
        epitopes = self._iter_epitopes()
        return {
            "tumor_antigens": len(self.tumor),
            "infectious_antigens": len(self.infectious),
            "tolerogenic_targets": len(self.tolerogenic),
            "vaccine_platforms": len(self.platforms),
            "adjuvants": len(self.adjuvants),
            "adjuvantic_epitopes": len(self.adjuvantic_epitopes),
            "tcr_clones": len(self.tcr_clones),
            "tcr_with_structure": sum(1 for item in self.tcr_clones if item.get("pdb")),
            "public_tcr_motifs": len(self.tcr_motifs),
            "mrna_design_rules": len(self.mrna_rules),
            "neoantigen_benchmarks": len(self.neo_benchmarks),
            "design_playbooks": len(self.design_playbooks),
            "assay_gates": len(self.assay_catalog),
            "scenario_guides": len(self.scenario_guides),
            "total_epitopes": len(epitopes),
            "total_entries": (
                len(self.tumor)
                + len(self.infectious)
                + len(self.tolerogenic)
                + len(self.platforms)
                + len(self.adjuvants)
                + len(self.tcr_clones)
                + len(self.adjuvantic_epitopes)
                + len(self.mrna_rules)
                + len(self.neo_benchmarks)
                + len(self.design_playbooks)
                + len(self.assay_catalog)
            ),
        }

    def search(self, query: str) -> dict[str, list[dict[str, Any]]]:
        q = query.lower().strip()
        tokens = [token for token in re.split(r"\s+", q) if token]
        pools = {
            "tumor": self.tumor,
            "infectious": self.infectious,
            "tolerogenic": self.tolerogenic,
            "platforms": self.platforms,
            "adjuvants": self.adjuvants,
            "adjuvantic_epitopes": self.adjuvantic_epitopes,
            "tcr_clones": self.tcr_clones,
            "tcr_motifs": self.tcr_motifs,
            "neoantigen_benchmarks": self.neo_benchmarks,
            "design_playbooks": self.design_playbooks,
            "assay_catalog": self.assay_catalog,
            "scenario_guides": self.scenario_guides,
        }
        results: dict[str, list[dict[str, Any]]] = {key: [] for key in pools}
        for key, records in pools.items():
            for record in records:
                blob = _search_blob(record).lower()
                if q and (q in blob or all(token in blob for token in tokens)):
                    results[key].append(record)
        return results

    def get_all_epitopes(
        self,
        hla: str | None = None,
        mhc_class: str | None = None,
    ) -> pd.DataFrame:
        rows = self._iter_epitopes()
        frame = pd.DataFrame(rows)
        if frame.empty:
            return frame
        if hla:
            frame = frame[frame["hla"].fillna("").str.contains(hla, regex=False)]
        if mhc_class:
            frame = frame[frame["mhc_class"].fillna("").eq(mhc_class)]
        return frame.reset_index(drop=True)

    def get_tcr_for_epitope(self, epitope: str, hla: str | None = None) -> dict[str, Any]:
        clones = [
            item
            for item in self.tcr_clones
            if item["epitope"] == epitope and (hla is None or item["hla"] == hla)
        ]
        motifs = [
            item
            for item in self.tcr_motifs
            if item["epitope"] == epitope and (hla is None or item["hla"] == hla)
        ]
        related_rules = [
            rule
            for rule in self.tcr_rules
            if any(backing in _search_blob(clones + motifs) for backing in rule.get("backing_records", []))
        ]
        return {
            "clones": clones,
            "public_motifs": motifs,
            "design_rules": related_rules or self.tcr_rules,
        }

    def get_all_tcr_clones(
        self,
        antigen_source: str | None = None,
        has_structure: bool | None = None,
        clinical_only: bool = False,
    ) -> pd.DataFrame:
        rows = self.tcr_clones
        if antigen_source:
            rows = [row for row in rows if row["antigen_source"] == antigen_source]
        if has_structure is not None:
            rows = [row for row in rows if bool(row.get("pdb")) == has_structure]
        if clinical_only:
            rows = [
                row
                for row in rows
                if "phase" in row["clinical_use"].lower()
                or "approved" in row["clinical_use"].lower()
            ]
        return pd.DataFrame(rows)

    def recommend_platform(
        self,
        indication: str = "cancer",
        need_cd8: bool = True,
        need_humoral: bool = True,
        cold_chain_constraint: bool = False,
        low_cost: bool = False,
    ) -> list[dict[str, Any]]:
        recs: list[dict[str, Any]] = []
        for platform in self.platforms:
            score = 0
            reasons: list[str] = []
            cd8 = platform.get("cd8_induction", "").lower()
            immune = platform.get("immune_response", "").lower()
            cold_chain = platform.get("cold_chain", "").lower()
            scalability = platform.get("scalability", "").lower()
            cost = platform.get("cost_per_dose", "")

            if need_cd8 and "strong" in cd8:
                score += 3
                reasons.append("strong CD8 induction")
            elif need_cd8 and "moderate" in cd8:
                score += 1

            if need_humoral and "both" in immune:
                score += 2
                reasons.append("balanced humoral and cellular response")
            elif need_humoral and "humoral" in immune:
                score += 1

            if cold_chain_constraint and ("2-8" in cold_chain or "room" in cold_chain):
                score += 2
                reasons.append("easier cold-chain profile")
            elif cold_chain_constraint:
                score -= 1

            if low_cost and any(mark in cost for mark in ["$0", "$1", "$2", "$3", "$4", "$5"]):
                score += 1
                reasons.append("lower cost band")

            if indication.lower() in {"cancer", "neoantigen", "therapeutic"} and "strong" in cd8:
                score += 2
                reasons.append("suited to therapeutic cellular programs")
            if indication.lower() in {"pandemic", "infectious", "outbreak"} and "high" in scalability:
                score += 2
                reasons.append("high scalability")

            adj_matches: list[tuple[str, int]] = []
            for adjuvant in self.adjuvants:
                adj_score = 0
                profile = adjuvant.get("immune_profile", "").lower()
                cd8_profile = adjuvant.get("cd8_enhancement", "").lower()
                status = adjuvant.get("regulatory_status", "").lower()
                if need_cd8 and "strong" in cd8_profile:
                    adj_score += 2
                elif need_cd8 and "moderate" in cd8_profile:
                    adj_score += 1
                if indication.lower() in {"cancer", "neoantigen", "therapeutic"} and "th1" in profile:
                    adj_score += 1
                if "approved" in status:
                    adj_score += 1
                if adj_score:
                    adj_matches.append((adjuvant["name"], adj_score))

            adj_matches.sort(key=lambda item: item[1], reverse=True)
            top_adjuvant = adj_matches[0][0] if adj_matches else "None / self-adjuvanting"
            if "mrna" in platform.get("category", "").lower():
                top_adjuvant = "LNP (intrinsic delivery-adjuvant effect)"

            recs.append(
                {
                    "platform": platform["name"],
                    "category": platform["category"],
                    "recommended_adjuvant": top_adjuvant,
                    "score": score,
                    "rationale": "; ".join(reasons) if reasons else "general fit",
                    "cd8_induction": platform["cd8_induction"],
                    "cold_chain": platform["cold_chain"],
                    "cost": platform["cost_per_dose"],
                }
            )
        return sorted(recs, key=lambda row: row["score"], reverse=True)

    def _scenario_hits(self, description: str) -> list[dict[str, Any]]:
        q = description.lower()
        hits: list[dict[str, Any]] = []
        if any(token in q for token in ["neoantigen", "mutanome", "personalized"]):
            hits.append(self.scenario_guides[0])
        if any(token in q for token in ["tumor", "shared antigen", "taa", "heteroclitic"]):
            hits.append(self.scenario_guides[1])
        if any(token in q for token in ["infectious", "variant", "outbreak", "pathogen"]):
            hits.append(self.scenario_guides[2])
        if any(token in q for token in ["autoimmune", "tolerogenic", "inverse vaccine", "treg"]):
            hits.append(self.scenario_guides[3])
        return hits

    def design_brief(self, description: str) -> str:
        results = self.search(description)
        scenario_hits = self._scenario_hits(description)
        playbook_hits = results["design_playbooks"]
        assay_hits = results["assay_catalog"]
        need_cd8 = any(
            token in description.lower()
            for token in ["cancer", "tumor", "neoantigen", "therapeutic", "cd8", "ctl"]
        )
        platform_recs = self.recommend_platform(
            indication="cancer" if need_cd8 else "infectious",
            need_cd8=need_cd8,
        )

        lines = [
            "═══ InSynBio Vaccine Design Brief ═══",
            f"Query: {description}",
            "",
        ]
        if scenario_hits:
            lines.append("── Recommended Decision Paths ──")
            for guide in scenario_hits[:3]:
                lines.append(f"  • {guide['title']}")
                lines.append(f"    Why: {guide['why']}")

        if playbook_hits:
            lines.append("\n── Design Playbooks ──")
            for item in playbook_hits[:2]:
                lines.append(f"  • {item['title']}")
                lines.append(f"    Trigger: {item['applies_when']}")

        if results["tumor"]:
            lines.append("\n── Tumor Antigen Evidence ──")
            for item in results["tumor"][:4]:
                lines.append(
                    f"  • {item['name']} (rank #{item['priority_rank']}) — "
                    f"{', '.join(item['disease_context'][:3])}"
                )

        if results["infectious"]:
            lines.append("\n── Infectious Benchmarks ──")
            for item in results["infectious"][:3]:
                lines.append(f"  • {item['pathogen']}: {item['antigen_name']}")
                if item["approved_vaccines"]:
                    top = item["approved_vaccines"][0]
                    lines.append(f"    Approved comparator: {top['name']} ({top['platform']})")

        if results["tolerogenic"]:
            lines.append("\n── Tolerogenic Targets ──")
            for item in results["tolerogenic"][:3]:
                lines.append(f"  • {item['disease']}: {item['target_antigen']}")
                lines.append(f"    Strategy: {item['vaccine_approach']}")

        if results["tcr_clones"]:
            lines.append("\n── TCR Guidance ──")
            for item in results["tcr_clones"][:3]:
                lines.append(f"  • {item['clone_id']} vs {item['epitope']} ({item['hla']})")
                if item.get("pdb"):
                    lines.append(f"    Structure anchor: {item['pdb']}")

        if results["neoantigen_benchmarks"]:
            lines.append("\n── Prediction Reality Check ──")
            for item in results["neoantigen_benchmarks"][:2]:
                lines.append(f"  • {item['title']}: {item['pain_point']}")

        if assay_hits:
            lines.append("\n── Wet Assay Gates ──")
            for item in assay_hits[:2]:
                lines.append(f"  • {item['name']}: {item['when_required']}")

        lines.append("\n── Top Platform Options ──")
        for rec in platform_recs[:3]:
            lines.append(f"  • {rec['platform']} -> {rec['recommended_adjuvant']}")
            lines.append(f"    Rationale: {rec['rationale']}")
        return "\n".join(lines)
