## VHH19 Fig5. Fold-informed humanization decision framework (Mermaid)

```mermaid
flowchart TD
  A[Input: VHH sequence] --> B[IMGT numbering + CDR definition]
  B --> C[Annotate H2 canonical fold (e.g., H2-9-1 / H2-10-1)]
  C --> D{H2 fold?}
  D -->|H2-9-1 (framework-dependent)| E[Prefer BM (grafting + back-mutations)]
  D -->|H2-10-1 (more robust)| F[Prefer SR or Native]
  D -->|unknown/ambiguous| G[Start with SR; escalate to BM if risks rise]
  E --> H[In silico checks: MHC-II scan + developability/CMC proxies]
  F --> H
  G --> H
  H --> I{Fusion module (HSA/Fc)?}
  I -->|Yes| J[Interpret humanness thresholds in context; evaluate ADA risk plan]
  I -->|No| K[Stricter immunogenicity control; consider SR/BM tuning]
  J --> L[Output: recommended strategy + verification checklist]
  K --> L
```
