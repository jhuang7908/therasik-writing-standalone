"""
VHH QA

VHH，QA
"""

import json
from pathlib import Path
from typing import Dict, Any, Optional, List
import numpy as np

PROJECT_ROOT = Path(__file__).resolve().parents[1]


class VHHDataCalibration:
    """
    VHH，QA
    """
    
    def __init__(self, calibration_db_path: Optional[str] = None):
        """
        
        
        Args:
            calibration_db_path: JSON（）
                                None，
        """
        self.calibration_db_path = calibration_db_path
        self.db = None
        self.success_risk_median = 0.2
        self.success_risk_p75 = 0.3
        self.failed_risk_median = 0.6
        self.failed_risk_p25 = 0.5
        self.structural_risk_weight = 0.20
        self.hallmark_penalty = 0.15
        
        if calibration_db_path:
            self.db = self._load_calibration_db(calibration_db_path)
            self._compute_distributions()
        else:
            # （）
            self._use_default_weights()
    
    def _load_calibration_db(self, db_path: str) -> Dict[str, Any]:
        """
        
        
        ：
        {
            "successful_cases": [
                {
                    "structural_risk": float,
                    "has_hallmark": bool,
                    "cdr3_anchor_match": bool,
                    "final_outcome": "success"
                },
                ...
            ],
            "failed_cases": [
                {
                    "structural_risk": float,
                    "has_hallmark": bool,
                    "cdr3_anchor_match": bool,
                    "final_outcome": "failed",
                    "failure_reason": str
                },
                ...
            ]
        }
        """
        db_file = Path(db_path)
        if not db_file.exists():
            # ，
            return {"successful_cases": [], "failed_cases": []}
        
        with open(db_file, 'r', encoding='utf-8') as f:
            return json.load(f)
    
    def _compute_distributions(self):
        """/"""
        if not self.db:
            self._use_default_weights()
            return
        
        # structural_risk
        success_cases = self.db.get("successful_cases", [])
        if success_cases:
            success_risks = [c.get("structural_risk", 0.2) for c in success_cases]
            self.success_risk_median = float(np.median(success_risks))
            self.success_risk_p75 = float(np.percentile(success_risks, 75))
        else:
            self.success_risk_median = 0.2
            self.success_risk_p75 = 0.3
        
        # structural_risk
        failed_cases = self.db.get("failed_cases", [])
        if failed_cases:
            failed_risks = [c.get("structural_risk", 0.6) for c in failed_cases]
            self.failed_risk_median = float(np.median(failed_risks))
            self.failed_risk_p25 = float(np.percentile(failed_risks, 25))
        else:
            self.failed_risk_median = 0.6
            self.failed_risk_p25 = 0.5
        
        # 
        self._calibrate_weights()
    
    def _calibrate_weights(self):
        """
        
        
        ：
        - median risk = 0.2，median risk = 0.6
        - risk = 0.4，""
        - final_score
        """
        risk_diff = self.failed_risk_median - self.success_risk_median
        
        if risk_diff > 0:
            # ：risk0.1final_score
            # ：weight * risk_diff >= 0.1
            self.structural_risk_weight = max(0.1, 0.1 / risk_diff)
        else:
            self.structural_risk_weight = 0.20  # 
        
        # Hallmark penalty
        success_cases = self.db.get("successful_cases", [])
        failed_cases = self.db.get("failed_cases", [])
        
        if success_cases and failed_cases:
            success_with_hallmark = sum(1 for c in success_cases 
                                       if c.get("has_hallmark", True))
            failed_without_hallmark = sum(1 for c in failed_cases 
                                         if not c.get("has_hallmark", True))
            
            total_success = len(success_cases)
            total_failed = len(failed_cases)
            
            hallmark_success_rate = success_with_hallmark / total_success if total_success > 0 else 0.9
            hallmark_failure_rate = failed_without_hallmark / total_failed if total_failed > 0 else 0.3
            
            # Hallmark
            hallmark_impact = hallmark_failure_rate - (1 - hallmark_success_rate)
            self.hallmark_penalty = max(0.05, min(0.25, hallmark_impact))
        else:
            self.hallmark_penalty = 0.15  # 
    
    def _use_default_weights(self):
        """（）"""
        self.structural_risk_weight = 0.20
        self.hallmark_penalty = 0.15
    
    def get_calibrated_weights(self) -> Dict[str, float]:
        """
        
        
        Returns:
            
        """
        return {
            "structural_risk_weight": self.structural_risk_weight,
            "hallmark_penalty": self.hallmark_penalty,
            "success_risk_median": self.success_risk_median,
            "failed_risk_median": self.failed_risk_median,
            "calibration_source": "VHH_historical_database" if self.db else "default"
        }

















