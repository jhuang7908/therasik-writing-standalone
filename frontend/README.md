# Frontend Components for VHH QA v3.5

This directory contains frontend components for displaying VHH QA v3.5 results in a React-based interface.

## Structure

```
frontend/
├── src/
│   ├── types/
│   │   └── vhhQa.ts          # TypeScript type definitions for QA data structures
│   └── components/
│       └── vhh/
│           └── VhhQaPanel.tsx # Main QA display component
└── README.md                  # This file
```

## Usage

### Installation

These components are designed for use with:
- React 18+
- TypeScript 5+
- Tailwind CSS 3+

### Basic Usage

```tsx
import { VhhQaPanel } from "@/components/vhh/VhhQaPanel";
import type { VhhQaV35 } from "@/types/vhhQa";

function MyComponent {
  // Assume you have QA data from your API
  const qaData: VhhQaV35 = {
    ok: true,
    errors: [],
    warnings: [],
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
          message: "FR2 hydrophilic patch ，。",
          value: 0.25
        }
        // ... more flags
      ]
    }
  };

  return <VhhQaPanel qaV35={qaData} />;
}
```

### Integration with Backend API

If your backend API returns QA results in the format:

```json
{
  "qa": {
    "active_version": "v3.5",
    "v3_5": {
      "ok": true,
      "errors": [],
      "warnings": [],
      // ... rest of QA structure
    }
  }
}
```

You can use it directly:

```tsx
import { VhhQaPanel } from "@/components/vhh/VhhQaPanel";
import type { VhhQaEnvelope } from "@/types/vhhQa";

function ResultDisplay({ result }: { result: { qa: VhhQaEnvelope } }) {
  const qaV35 = result.qa.v3_5;
  
  if (!qaV35) {
    return <div>QA data not available</div>;
  }

  return <VhhQaPanel qaV35={qaV35} />;
}
```

## Component Features

### VhhQaPanel

The main component displays:

1. **Status Bar** - Traffic light indicator, version info, and key metrics
2. **Risk Cards** - Four cards showing:
   - FR2 hydrophilic patch risk
   - Grafting interface risk
   - CDR3 anchor risk
   - Total structural risk
3. **Guideline Flags** - List of all guideline flags with risk levels
4. **Ranking Stability** - Analysis of template ranking stability and score consistency
5. **Errors & Warnings** - Separate sections for errors and warnings

### Styling

The component uses Tailwind CSS classes. Make sure your project has Tailwind configured with the following colors:
- Green: `green-100`, `green-500`, `green-700`
- Yellow: `yellow-100`, `yellow-400`, `yellow-700`
- Red: `red-100`, `red-500`, `red-800`
- Gray: `gray-50`, `gray-100`, `gray-400`, `gray-500`, `gray-600`

## Type Definitions

All TypeScript types are defined in `src/types/vhhQa.ts`:

- `QaWarning` - Warning structure with level and category
- `StructuralRiskComponents` - Risk component values
- `RankingStabilityAnalysis` - Ranking stability metrics
- `ScoreConsistency` - Score consistency calibration results
- `VhhGuidelineFlag` - Individual guideline flag
- `VhhGuideline` - Complete guideline with traffic light
- `VhhQaV35` - Complete QA v3.5 result structure
- `VhhQaEnvelope` - Wrapper for multiple QA versions

## Notes

- These components are designed to work with the VHH QA v3.5 backend API
- The component assumes data is already validated and in the correct format
- All numeric values are displayed with 2 decimal places
- The traffic light color is determined by the highest risk level in guideline flags

















