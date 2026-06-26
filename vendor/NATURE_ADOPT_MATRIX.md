# nature-skills → InSynBio/Therasik 采纳矩阵 (tracked SSOT)

维护日期：2026-06-21 (Step 1 完成) · Vendor pin: `vendor/nature_skills.lock.json`  
Cursor runtime copy: `.cursor/skills/insynbio-therasik-suite/static/core/nature-skills-adopt-matrix.md`

Legend: **◎ 已采纳** · **◐ 部分采纳** · **○ 待采纳** · **— 垂直替代 / 仅参考**

| nature 模块 | 状态 | 本地模块 | 采纳要点 | 差距 / 下一步 |
|-------------|------|----------|----------|---------------|
| `nature-academic-search` | Beta | `insynbio-literature-search` + `insynbio-citation` | T1→T2→T3 路由表、MeSH、dedup | **◎** static mirror (2)；frozen denovo corpus；**○** MCP Scopus/SD |
| `nature-writing` | Draft | ARS `academic-paper` + `writing_memory` | 论证架构、section job、adversarial self-review | **◐** article-architecture → polish profile |
| `nature-polishing` | **Stable** | `insynbio-polishing` | failure-modes、section/journal axes | **◎** static mirror (20)；**○** nat-comms diction refs |
| `nature-reviewer` | Draft | `academic-paper-reviewer` | 三份 reviewer report 格式 | **◎** 5 视角 pipeline 更深 |
| `nature-response` | Beta | `journal-submission-prep` M6 | 逐点回复、major revision 语气 | **◐** 模板对齐 audit |
| `nature-citation` | Beta | `insynbio-citation` | CNS 分段引用、Zotero RDF | **◎** static mirror + RDF CLI；**○** HTML browser |
| `nature-data` | Draft | bundle + §Data | FAIR statement | **—** PASS/FAIL 投稿包超集 |
| `nature-figure` | **Stable** | `insynbio-figure` | contract + stance + Python/R axes | **◎** static mirror (4)；**○** figures4papers atlas |
| `nature-reader` | Beta | `insynbio-paper-reader` | source_format axes、output-contract | **◎** static mirror (8)；**◐** Kimi translate QC |
| `nature-paper2ppt` | Beta | `insynbio-paper2ppt` | 6 paper_type arcs、spine | **◎** static mirror + editable pptx + QA JSON |
| `nature-paper-to-patent` | Beta | `insynbio-paper-to-patent` | CN 专利文体、证据约束 | **◎** static mirror (15 fragments) + JSON outline CLI |
| `openclaw-medical-skills` | vendor-only | — | OpenClaw 生物医学能力索引（867+ skills） | **—** 不纳入 insynbio 主线；clinical 场景查 `vendor/nature-skills/skills/openclaw-medical-skills/references/capability-index.md` |

## 2026-06-21 关闭项

- [x] `vendor/nature-skills/` clone + `scripts/diff_nature_adopt.py --mirror`
- [x] `nature-citation` static → `vendor/adopted/insynbio-citation/static/`
- [x] `nature-paper-to-patent` static → `vendor/adopted/insynbio-paper-to-patent/static/`
- [x] Zotero RDF: `insynbio_citation.py export-zotero-rdf` + `build_review_b_reference_library.py`
- [x] `openclaw-medical-skills` 入矩阵（reference-only）
- [x] `nature-reader` static (8) → `vendor/adopted/insynbio-paper-reader/`
- [x] `nature-paper2ppt` static (10) → `vendor/adopted/insynbio-paper2ppt/`
- [x] `nature-polishing` Stable static (20) → `vendor/adopted/insynbio-polishing/`
- [x] **Step 1** `nature-figure` static (4) → `vendor/adopted/insynbio-figure/` — 0 gap ✓
- [x] **Step 1** `nature-academic-search` static (2) → `vendor/adopted/insynbio-literature-search/` — 0 gap ✓
- [x] **Step 1** manifest v1.1.0：`insynbio-figure` (blocking gate axes) + `insynbio-literature-search` (5-workflow axes)

## Quarterly diff

```powershell
python scripts/diff_nature_adopt.py --update-vendor
python scripts/diff_nature_adopt.py --mirror citation paper-to-patent reader paper2ppt polishing figure academic-search
python scripts/diff_nature_adopt.py --report vendor/nature_skills_diff_report.json --markdown vendor/NATURE_ADOPT_DIFF.md
```
