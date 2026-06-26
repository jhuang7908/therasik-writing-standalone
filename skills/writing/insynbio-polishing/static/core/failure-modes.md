# Polishing failure modes (from nature-polishing Stable)

Before editing prose, diagnose the **main** failure mode:

| Mode | Signal | Fix order |
|------|--------|-----------|
| Wrong paper type logic | Review written like primary research | Switch to review playbook |
| Missing gap / positioning | Intro encyclopedia | Reframe funnel |
| Claim without evidence | "transformative" without citation | Add grade or cut |
| Evidence without claim | Figure dump | Add topic sentence |
| Missing boundary | No limitations | Add explicit limits paragraph |
| Results/Discussion mixed | Same section does both | Split jobs |
| Weak title/abstract | Vague title | Rewrite signal line |
| Terminology drift | VHH/VH mixed | Terminology ledger |
| Sentence clutter only | Structure OK | Sentence polish last |

## Mandatory fix priority

```
paper type → section job → paragraph logic → claim/evidence/boundary → sentence polish
```

**Do not** sentence-polish when section job is wrong.

## Cross-cutting

Build Terminology Ledger on first contact: `_shared/core/terminology-ledger.md`

## Platform

After structural pass: `insynbio_polishing.py scan` → write.insynbio.com `/reduce_ai_tone`
