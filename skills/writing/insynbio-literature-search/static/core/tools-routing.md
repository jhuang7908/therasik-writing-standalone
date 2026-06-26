# Tool routing T1 → T2 → T3

| Tier | Source | Use when |
|------|--------|----------|
| T1 | `config/denovo_literature_corpus.json` + build scripts | Review B / de novo landscape |
| T2 | PubMed E-utilities, Europe PMC (project fetch scripts) | Fill MISSING, verify DOI |
| T3 | MCP PubMed/CrossRef/arXiv (if configured) | Exploratory search, new reviews |
| T4 | Manual user-provided PDF/PMID | Last resort; tag `[user-provided]` |

Never invent PMIDs. Report FULL/MISSING counts after every build.
