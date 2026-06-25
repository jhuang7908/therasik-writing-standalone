// frontend/src/examples/VhhQaPanelExample.tsx
/**
 * Example usage of VhhQaPanel component
 * 
 * This file demonstrates how to integrate the VhhQaPanel component
 * into your React application.
 */

import React from "react";
import { VhhQaPanel } from "@/components/vhh/VhhQaPanel";
import type { VhhQaV35, VhhQaEnvelope } from "@/types/vhhQa";

/**
 * Example 1: Direct usage with QA v3.5 data
 */
export function ExampleDirectUsage() {
  const qaData: VhhQaV35 = {
    ok: true,
    errors: [],
    warnings: [
      {
        level: "minor",
        category: "delta_risk",
        message: "人源化后 developability 轻微下降 (Δ=-0.03)，整体可接受，但优选方案建议对比。"
      }
    ],
    meta: {
      version: "3.5.0",
      ruleset: "VHH_QA_V3.5_RANKING"
    },
    structural_risk_components: {
      fr2_hydrophilic_patch_risk: 0.25,
      grafting_interface_risk: 0.15,
      cdr3_anchor_risk: 0.10,
      total_risk: 0.17
    },
    checks: {
      ranking_sanity_v3_5: {
        stability_analysis: {
          is_stable: true,
          stability_score: 0.85,
          swap_risk: 0.15,
          consistency_issues: []
        },
        score_consistency: {
          calibrated: true,
          is_monotonic: true
        }
      }
    },
    guideline: {
      traffic_light: "yellow",
      flags: [
        {
          id: "FR2_RISK",
          level: "medium",
          message: "FR2 hydrophilic patch 风险中等，建议关注聚集倾向和可溶性。",
          value: 0.25
        },
        {
          id: "CDR3_ANCHOR_RISK",
          level: "low",
          message: "CDR3 anchor 风险较低，101/102 等关键位点匹配良好。",
          value: 0.10
        },
        {
          id: "GRAFTING_RISK",
          level: "low",
          message: "Grafting interface 风险较低，FR–CDR 界面理化性质变化有限。",
          value: 0.15
        },
        {
          id: "TOTAL_STRUCTURAL_RISK",
          level: "low",
          message: "总体结构风险较低，适合作为 VHH 人源化模板或候选骨架。",
          value: 0.17
        },
        {
          id: "VHH_HALLMARK",
          level: "low",
          message: "VHH hallmark 完整保留，符合典型单域抗体 FR2 特征。",
          value: 0.0
        }
      ]
    }
  };

  return (
    <div className="container mx-auto p-4">
      <h1 className="text-2xl font-bold mb-4">VHH QA v3.5 Results</h1>
      <VhhQaPanel qaV35={qaData} />
    </div>
  );
}

/**
 * Example 2: Integration with API response
 */
export function ExampleWithApiResponse() {
  // Simulate API response structure
  const apiResponse = {
    success: true,
    data: {
      sequence: "EVQLVESGGGLVQPGGSLRLSCAAS...",
      qa: {
        active_version: "v3.5",
        ok: true,
        v3_5: {
          ok: true,
          errors: [],
          warnings: [],
          // ... rest of QA structure
        } as VhhQaV35
      } as VhhQaEnvelope
    }
  };

  const qaV35 = apiResponse.data.qa.v3_5;

  if (!qaV35) {
    return <div>QA data not available</div>;
  }

  return (
    <div className="container mx-auto p-4">
      <VhhQaPanel qaV35={qaV35} />
    </div>
  );
}

/**
 * Example 3: Error state display
 */
export function ExampleWithErrors() {
  const qaDataWithErrors: VhhQaV35 = {
    ok: false,
    errors: [
      "CDR3 anchor residues风险过高 (0.75)，这是VHH折叠的生死线。模板101/102位置与humanized不匹配，可能导致结构不稳定或无法折叠。"
    ],
    warnings: [
      {
        level: "major",
        category: "structural",
        message: "FR2 hydrophilic patch 风险较高，VHH 可能存在聚集或折叠问题，建议谨慎使用该骨架。"
      }
    ],
    meta: {
      version: "3.5.0",
      ruleset: "VHH_QA_V3.5_RANKING"
    },
    structural_risk_components: {
      fr2_hydrophilic_patch_risk: 0.70,
      grafting_interface_risk: 0.50,
      cdr3_anchor_risk: 0.75,
      total_risk: 0.65
    },
    checks: {
      ranking_sanity_v3_5: {
        stability_analysis: {
          is_stable: false,
          stability_score: 0.45,
          swap_risk: 0.65,
          consistency_issues: [
            "候选模板 TEMPLATE_002 的 FR identity (0.92) 显著高于 TEMPLATE_001 (0.85)，但 final_score 更低 (0.78 vs 0.82)，存在排序不一致的风险。"
          ]
        },
        score_consistency: {
          calibrated: true,
          is_monotonic: false
        }
      }
    },
    guideline: {
      traffic_light: "red",
      flags: [
        {
          id: "FR2_RISK",
          level: "high",
          message: "FR2 hydrophilic patch 风险较高，VHH 可能存在聚集或折叠问题，建议谨慎使用该骨架。",
          value: 0.70
        },
        {
          id: "CDR3_ANCHOR_RISK",
          level: "high",
          message: "CDR3 anchor 风险较高，关键锚定位点与模板不匹配，可能严重影响 VHH 折叠与稳定性。",
          value: 0.75
        },
        {
          id: "GRAFTING_RISK",
          level: "medium",
          message: "Grafting interface 风险中等，建议关注局部结构扰动与亲和力变化。",
          value: 0.50
        },
        {
          id: "TOTAL_STRUCTURAL_RISK",
          level: "high",
          message: "总体结构风险较高，不建议作为首选候选骨架。",
          value: 0.65
        },
        {
          id: "VHH_HALLMARK",
          level: "low",
          message: "VHH hallmark 完整保留，符合典型单域抗体 FR2 特征。",
          value: 0.0
        }
      ]
    }
  };

  return (
    <div className="container mx-auto p-4">
      <h1 className="text-2xl font-bold mb-4 text-red-600">
        VHH QA v3.5 Results (Failed)
      </h1>
      <VhhQaPanel qaV35={qaDataWithErrors} />
    </div>
  );
}

/**
 * Example 4: Loading state wrapper
 */
export function ExampleWithLoading() {
  const [loading, setLoading] = React.useState(true);
  const [qaData, setQaData] = React.useState<VhhQaV35 | null>(null);

  React.useEffect(() => {
    // Simulate API call
    setTimeout(() => {
      // Replace with actual API call
      // const response = await fetch('/api/vhh/humanize', { ... });
      // const data = await response.json();
      // setQaData(data.qa.v3_5);
      setLoading(false);
    }, 1000);
  }, []);

  if (loading) {
    return (
      <div className="container mx-auto p-4">
        <div className="flex items-center justify-center h-64">
          <div className="text-gray-500">Loading QA results...</div>
        </div>
      </div>
    );
  }

  if (!qaData) {
    return (
      <div className="container mx-auto p-4">
        <div className="text-red-500">Failed to load QA data</div>
      </div>
    );
  }

  return (
    <div className="container mx-auto p-4">
      <VhhQaPanel qaV35={qaData} />
    </div>
  );
}

















