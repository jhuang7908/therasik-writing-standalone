import yaml
import os
from pathlib import Path
from typing import Dict, Any, List, Optional

class FrameworkRouter:
    """
    FrameworkRouter: Routes antibody sequences to appropriate humanization routes 
    and strategies based on framework quality, CDR load, and target context.
    """
    def __init__(self, rulebook_path: str = None):
        if rulebook_path is None:
            # Default to the v1 rulebook in the project
            rulebook_path = os.path.join(
                os.path.dirname(os.path.dirname(__file__)), 
                "data", "policy", "framework_cdr_target_rulebook_v1.yaml"
            )
        
        with open(rulebook_path, "r", encoding="utf-8") as f:
            self.rulebook = yaml.safe_load(f)
        
        self.thresholds = self.rulebook.get("thresholds", {})
        self.framework_bands = self.rulebook.get("framework_bands", [])
        self.cdr_load_bands = self.rulebook.get("cdr_load_bands", [])
        self.routes = self.rulebook.get("routes", [])
        self.hard_constraints = self.rulebook.get("hard_constraints", [])

    def _resolve_threshold(self, value: Any) -> float:
        """Resolves threshold aliases like 'p90' to their numeric values."""
        if isinstance(value, str):
            if value.startswith("p") and value in self.thresholds.get("delta_identity", {}):
                return self.thresholds["delta_identity"][value]
            if value in self.thresholds.get("cdr_load", {}):
                return self.thresholds["cdr_load"][value]
        return float(value)

    def determine_framework_band(self, vh_delta: Optional[float], vl_delta: Optional[float], 
                                vh_ool: bool, vl_ool: bool) -> Dict[str, Any]:
        """Categorizes the framework into a band (F0-F3)."""
        # max_delta_identity = max(vh_delta_identity, vl_delta_identity)（）
        deltas = [d for d in [vh_delta, vl_delta] if d is not None]
        max_delta = max(deltas) if deltas else 0.0
        
        any_ool = vh_ool or vl_ool
        
        for band in self.framework_bands:
            when = band.get("when", {})
            le_thresh = when.get("max_delta_identity_le")
            gt_thresh = when.get("max_delta_identity_gt")
            ool_cond = when.get("out_of_library")
            
            match = True
            if le_thresh is not None:
                if max_delta > self._resolve_threshold(le_thresh):
                    match = False
            if gt_thresh is not None:
                if max_delta <= self._resolve_threshold(gt_thresh):
                    match = False
            if ool_cond is not None and ool_cond != "either":
                if any_ool != ool_cond:
                    match = False
            
            if match:
                return band
        
        return {"id": "UNKNOWN", "label_cn": "", "label_en": "Unknown framework band"}

    def determine_cdr_load_band(self, cdrh3_len: Optional[int], atypical_count: Optional[int] = 0) -> Dict[str, Any]:
        """Categorizes the CDR load (C0-C3)."""
        if cdrh3_len is None:
            return {"id": "UNKNOWN", "label_cn": "CDR", "label_en": "Unknown CDR load"}
            
        atypical_count = atypical_count or 0
        
        for band in self.cdr_load_bands:
            when = band.get("when", {})
            
            # Helper to check a single condition set
            def check_conds(c):
                lt = c.get("cdrh3_length_lt")
                ge = c.get("cdrh3_length_ge")
                atypical_le = c.get("atypical_canonical_count_le")
                atypical_ge = c.get("atypical_canonical_count_ge")
                
                res = True
                if lt is not None and cdrh3_len >= self._resolve_threshold(lt): res = False
                if ge is not None and cdrh3_len < self._resolve_threshold(ge): res = False
                if atypical_le is not None and atypical_count > atypical_le: res = False
                if atypical_ge is not None and atypical_count < atypical_ge: res = False
                return res

            if "any_of" in when:
                if any(check_conds(c) for c in when["any_of"]):
                    return band
            elif check_conds(when):
                return band
        
        return {"id": "UNKNOWN", "label_cn": "CDR", "label_en": "Unknown CDR load"}

    def route(self, input_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Routes the record to a specific humanization route and strategy.
        
        Input should contain:
            - vh_delta_identity, vl_delta_identity (float|None)
            - vh_out_of_library_flag, vl_out_of_library_flag (bool)
            - vh_fr1, vh_fr2, vh_fr3, vl_fr1, vl_fr2, vl_fr3 (string|None)
            - cdrh3_length (int|None)
            - optional: atypical_canonical_count (int), antigen_type, mechanism, format (str)
        """
        vh_delta = input_data.get("vh_delta_identity")
        vl_delta = input_data.get("vl_delta_identity")
        vh_ool = input_data.get("vh_out_of_library_flag", False)
        vl_ool = input_data.get("vl_out_of_library_flag", False)
        cdrh3_len = input_data.get("cdrh3_length")
        atypical_count = input_data.get("atypical_canonical_count", 0)
        
        # has_full_fr123_pair：vh_fr1/2/3  vl_fr1/2/3 
        fr_fields = ["vh_fr1", "vh_fr2", "vh_fr3", "vl_fr1", "vl_fr2", "vl_fr3"]
        has_full_fr123_pair = all(input_data.get(f) is not None and str(input_data.get(f)).strip() != "" for f in fr_fields)
        
        antigen_type = input_data.get("antigen_type", "UNKNOWN")
        mechanism = input_data.get("mechanism", "UNKNOWN")
        fmt = input_data.get("format", "UNKNOWN")
        
        f_band = self.determine_framework_band(vh_delta, vl_delta, vh_ool, vl_ool)
        c_band = self.determine_cdr_load_band(cdrh3_len, atypical_count)
        
        matched_route = None
        for r in self.routes:
            applies = r.get("applies_to", {})
            f_match = f_band["id"] in applies.get("framework_band", [])
            c_match = c_band["id"] in applies.get("cdr_load_band", [])
            t_match = antigen_type in applies.get("antigen_type", ["UNKNOWN"]) or "UNKNOWN" in applies.get("antigen_type", [])
            
            if f_match and c_match and t_match:
                matched_route = r
                break
        
        # Mapping to strategy_id in mutation_strategy_templates_v1.yaml
        strategy_map = {
            "F0": "STRAT_F0_MINIMAL",
            "F1": "STRAT_F1_PARTITIONED",
            "F2": "STRAT_F2_FUNCTION_PRESERVE",
            "F3": "STRAT_F2_FUNCTION_PRESERVE"
        }
        
        result = {
            "framework_band": f_band["id"],
            "framework_band_label": f_band["label_cn"],
            "cdr_load_band": c_band["id"],
            "cdr_load_band_label": c_band["label_cn"],
            "route_id": matched_route["id"] if matched_route else "ROUTE_UNKNOWN",
            "route_name": matched_route["name_cn"] if matched_route else "",
            "policy_summary_cn": matched_route["report"]["summary_cn"] if matched_route else "",
            "policy_summary_en": matched_route["report"]["summary_en"] if matched_route else "No applicable policy",
            "strategy_id": strategy_map.get(f_band["id"], "STRAT_UNKNOWN"),
            "risk_overrides": [],
            "has_full_fr123_pair": has_full_fr123_pair
        }
        
        # Check hard constraints
        for hc in self.hard_constraints:
            triggered = False
            when = hc.get("when", {})
            
            def check_hc_unit(w):
                unit_match = True
                if "vh_out_of_library_flag" in w and vh_ool != w["vh_out_of_library_flag"]: unit_match = False
                if "vl_out_of_library_flag" in w and vl_ool != w["vl_out_of_library_flag"]: unit_match = False
                if "has_full_fr123_pair" in w and has_full_fr123_pair != w["has_full_fr123_pair"]: unit_match = False
                return unit_match

            if "any_of" in when:
                triggered = any(check_hc_unit(w) for w in when["any_of"])
            else:
                triggered = check_hc_unit(when)
                
            if triggered:
                action = hc.get("action", {})
                result["risk_overrides"].append({
                    "id": hc["id"],
                    "risk_level": action.get("raise_risk_level", "INFO"),
                    "note_cn": action.get("append_report_cn") or action.get("mark_data_quality_cn"),
                    "note_en": action.get("append_report_en") or action.get("mark_data_quality_en")
                })
        
        return result
