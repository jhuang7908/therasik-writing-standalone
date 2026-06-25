// frontend/src/types/vhhQa.ts

export interface QaWarning {
  level: "minor" | "major";
  category: string;
  message: string;
}

export interface StructuralRiskComponents {
  fr2_hydrophilic_patch_risk: number;
  grafting_interface_risk: number;
  cdr3_anchor_risk: number;
  total_risk: number;
}

export interface RankingStabilityAnalysis {
  is_stable: boolean;
  stability_score: number;
  swap_risk: number;
  consistency_issues: string[];
}

export interface ScoreConsistency {
  calibrated: boolean;
  is_monotonic?: boolean;
  reason?: string;
}

export interface RankingSanity {
  stability_analysis: RankingStabilityAnalysis;
  score_consistency: ScoreConsistency;
}

export interface VhhGuidelineFlag {
  id: string;
  level: "low" | "medium" | "high";
  message: string;
  value: number;
}

export interface VhhGuideline {
  traffic_light: "green" | "yellow" | "red";
  flags: VhhGuidelineFlag[];
}

export interface VhhQaV35 {
  ok: boolean;
  errors: string[];
  warnings: QaWarning[];
  meta: {
    version: string;
    ruleset: string;
  };
  structural_risk_components: StructuralRiskComponents;
  checks: {
    ranking_sanity_v3_5: RankingSanity;
    [key: string]: any;
  };
  guideline: VhhGuideline;
}

export interface VhhQaEnvelope {
  active_version: string;
  ok: boolean;
  v3_5?: VhhQaV35;
  [key: string]: any;
}

















