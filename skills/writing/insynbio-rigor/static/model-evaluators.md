# How each model evaluates rigor (independent roles)

These are **complementary**, not redundant. Production requires **layered JSON gates**, not one model's opinion.

## DeepSeek

| Evaluates well | Weakness |
|----------------|----------|
| Fast draft/fix loops | May smooth over missing citations |
| Code + CLI orchestration | Not primary PubMed authority |
| Cost-efficient iteration | |

**Typical task:** Writer in `content-ssot-guard`; fixer after Kimi FAIL  
**Does not alone:** Ship manuscript or social bundle

---

## Kimi (Moonshot)

| Evaluates well | Weakness |
|----------------|----------|
| Long-context source ↔ draft compare | English Nature prose nuance |
| Chinese fact-check; `[未验证]` tagging | Vision / slide layout |
| Zero-tolerance on fabricated numbers (when prompted) | |

**Typical task:** `stage_fact_check`, reader `--translate kimi`, verifier fallback  
**Prompt discipline:** Source excerpt must be in context window

---

## Claude

| Evaluates well | Weakness |
|----------------|----------|
| Journal prose + argument structure | Live corpus without tools |
| Rigor chain member (format/auth/science JSON) | Cost at full-manuscript scale |
| Platform polish (`writing_memory` Sonnet) | |

**Typical task:** `/rewrite`, rigor chain, academic-paper-reviewer  
**Best for:** "Does this **read** like defensible science?"

---

## Gemini

| Evaluates well | Weakness |
|----------------|----------|
| Rigor chain fallback | Citation database without MCP |
| Slide/deck visual coherence | Long manuscript single-shot |
| Structured JSON verdicts | |

**Typical task:** `openai_content_rigor` chain; `generate_ppt` backend  
**Best for:** Multimodal + format compliance at scale

---

## Local heuristics (non-LLM)

| Tool | Role |
|------|------|
| `insynbio_rigor.py` | Repeatable manuscript scan |
| `insynbio_polishing.py scan` | AI marker FAIL threshold |
| `build_submission_bundle` auditor | File/DPI existence |
| `validate_report_reliability.py` | Section contract |

**Principle:** LLMs propose; **gates dispose** (exit code 0/1).

---

## Consensus workflow (recommended)

```
Source SSOT (MD / article.json / corpus)
    → B local scan (insynbio_rigor)
    → C multi-model gate (if social/deck)
    → Platform polish (Claude) if EN journal
    → D reliability sections (if formal report)
    → E submission audit (before upload)
```

Review B golden path achieved: **B PASS (0 AI markers) + E PASS (figure DPI)**.
