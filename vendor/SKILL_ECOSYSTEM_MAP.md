# InSynBio Research Platform — Skill Ecosystem Map

生成日期：2026-06-22 · Step 5 完成（连贯性修复 + Submission Writer）

## 生态全景（公开 GitHub → 本地采纳）

```
公开生态（GitHub）                本地采纳层                         执行层（CLI）
─────────────────────────────────────────────────────────────────────────────────

【nature-skills 11模块 ◎ 11/11 · 0 gap】
Yuan1z0825/nature-skills       vendor/adopted/ mirror              diff_nature_adopt.py --mirror
  figure Stable 2.0   ◎   →   insynbio-figure (v1.2)          →   insynbio_figure.py
  polishing Stable 6.1 ◎  →   insynbio-polishing (v1.1)       →   insynbio_polishing.py
  citation Beta 2.0   ◎   →   insynbio-citation (v1.1)        →   insynbio_citation.py export-zotero-rdf
  paper2ppt Beta 2.0  ◎   →   insynbio-paper2ppt (v1.1)      →   insynbio_paper2ppt.py
  paper-to-patent Beta 1.0 ◎ → insynbio-paper-to-patent (v1.1) →  insynbio_paper_to_patent.py
  reader Beta 2.0     ◎   →   insynbio-paper-reader (v1.1)    →   insynbio_paper_reader.py
  academic-search Beta 2.0 ◎ → insynbio-literature-search (v1.2) → insynbio_openalex.py (new)
  writing Draft 1.0   ◐   →   insynbio-polishing (overlay)
  reviewer Draft 0.1  —   →   ARS academic-paper-reviewer (external)
  response Beta 1.0   ◐   →   ARS journal-submission-prep M6
  data Draft 2.0      —   →   journal-submission-bundle

【ARS v3.13 (5 skills · 已安装 ~/.cursor/skills/)】
Imbad0202/academic-research-skills  →   Layer 3 External
  deep-research v2.9    → 13-agent PRISMA + Semantic Scholar verify
  academic-paper v3.1   → 12-agent + Style Calibration + VLM figure verify
  academic-paper-reviewer v1.9 → 5-agent + 0-100 rubric
  academic-pipeline v3.13 → 10-stage + Material Passport + claim→experiment
  experiment-agent      → reproducibility validation

【GDM science-skills ◎ Step 2 完成 · commit 33557e0f (2026-06-08)】
google-deepmind/science-skills     vendor/science-skills/ (gitignored)
                                   vendor/science_skills.lock.json (tracked)
                                   vendor/adopted/science-skills/ (tracked mirrors)
  literature_search_openalex  ◎ →  scripts/insynbio_openalex.py         (free polite pool)
                                   insynbio-literature-search v1.2 openalex_search + doi_verify workflows
  alphafold_database_fetch    ◎ →  core/figure/afdb_plddt.py            (AFDB pLDDT figure recipe)
                                   insynbio-figure v1.2 recipe: afdb_plddt
  uniprot_database            —   (reference — use AbEngineCore UniProt calls for protein ID lookups)
  pubmed_database             —   (reference — PubMed covered by existing denovo corpus fetch pipeline)
  pdb_database                —   (reference — PDB covered by affinity_energy_toolkit.py + HADDOCK3)
  37 other skills             —   (available in vendor/science-skills/ for future adoption)

【K-Dense scientific-agent-skills (查阅用)】
K-Dense-AI/scientific-agent-skills (147 skills, MIT)
  protein-engineering     →   AbEngineCore VHH 设计参考
  scientific-communication →  投稿写作参考
  bioinformatics          →   序列分析参考

【openclaw-medical-skills (vendor-only 参考)】
vendor/adopted/openclaw-medical-skills/README.md

─────────────────────────────────────────────────────────────────────────────────
```

## 本地 Skill 矩阵（22 个可执行单元）

**平台定位（Step 3b 更新）：** 覆盖 PubMed 全域的生物医学学术写作平台。80+ 子领域 · 12 个 MeSH 大类：疾病学、治疗/药物开发、免疫学、遗传学/基因组学、结构生物学/生化、细胞生物学/生理学、计算生物学/生信、流行病学/公共卫生、临床医学/转化研究、生物医学工程、营养/运动医学、跨领域方法学。不局限于抗体工程。

### Layer 1 — Master Router
| Skill | 版本 | 作用 |
|-------|------|------|
| `insynbio-therasik-suite` | **1.1** | 通用生物医学写作 · 品牌分发 (InSynBio/Therasik/NextVivo) |

### Layer 2 — InSynBio 本地（14 个）
| Skill / 工具 | 版本 | nature / ARS 对标 | GDM 扩展 | 状态 |
|-------|------|------------|---------|------|
| `insynbio-research-suite` | **1.1** | 综合路由 | 通用生物医学域检测 | ◎ |
| `insynbio-literature-search` | **1.2** | nature-academic-search | OpenAlex T3 layer | ◎ 0 gap |
| `insynbio-citation` | **1.1** | nature-citation | — | ◎ 0 gap |
| `insynbio-polishing` | **1.1** | nature-polishing | — | ◎ 0 gap |
| `insynbio-figure` | **1.2** | nature-figure | AFDB pLDDT recipe | ◎ 0 gap |
| `insynbio-paper-reader` | **1.1** | nature-reader | — | ◎ 0 gap |
| `insynbio-paper2ppt` | **1.1** | nature-paper2ppt | — | ◎ 0 gap |
| `insynbio-paper-to-patent` | **1.1** | nature-paper-to-patent | — | ◎ 0 gap |
| `insynbio-rigor` | 1.0 | — (独有) | — | ◎ |
| `journal-submission-bundle` | — | nature-data 超集 | — | ◎ |
| `content-ssot-guard` | — | — (独有) | — | ◎ |
| **`style_calibration` workflow** | **new** | ARS academic-paper Step 10 | — | ◎ 新 |
| **`material_passport` workflow** | **new** | ARS academic-pipeline Schema 9 | — | ◎ 新 |
| **`biomedical-domains.md` SSOT** | **v1.2** | — (独有) | MeSH API live | ◎ 新 |
| **`journal_format` workflow** | **new** | — 外部API | CrossRef+Zotero+Sherpa | ◎ 新 |

### Layer 3 — 外部 ARS（5 个）
| Skill | 版本 | nature 对标 |
|-------|------|------------|
| `academic-paper` | v3.13 | nature-writing |
| `academic-paper-reviewer` | v1.9 | nature-reviewer |
| `journal-submission-prep` | — | nature-response |
| `deep-research` | v2.9 | nature-academic-search (通用) |
| `academic-pipeline` | v3.13 | — (端到端) |

## Step 进度

| Step | 状态 | 内容 |
|------|------|------|
| Step 1 | **✅ DONE** | nature-figure + academic-search mirror → 11/11 0 gap |
| Step 2 | **✅ DONE** | GDM science-skills vendored · OpenAlex CLI · AFDB pLDDT recipe |
| Step 3a | **✅ DONE** | 通用生物医学写作扩展 · Style Calibration · Material Passport |
| Step 3b | **✅ DONE** | 域分类扩展：80+ sub-domains · 12 MeSH categories · PubMed完整覆盖 |
| Step 4  | **✅ DONE** | 期刊格式 API：CrossRef + Zotero CSL (9,000+) + Sherpa RoMEO · 不自建 |
| Step 5  | **✅ DONE** | 连贯性修复：--init-project通用化 · insynbio_submission_writer.py · Material Passport checkpoint · figure chart-atlas v1.4.0 · AT figure comply |

## Step 2 交付物清单

| 文件 | 类型 | 说明 |
|------|------|------|
| `vendor/science-skills/` | gitignored clone | GDM 37 skills 原始库 |
| `vendor/science_skills.lock.json` | tracked | commit pin + 采纳 skills 列表 |
| `vendor/adopted/science-skills/openalex/SKILL_mirror.md` | tracked mirror | OpenAlex 采纳 diff |
| `vendor/adopted/science-skills/afdb/SKILL_mirror.md` | tracked mirror | AFDB pLDDT 采纳 diff |
| `scripts/insynbio_openalex.py` | new CLI | OpenAlex search / DOI verify / resolve-author |
| `core/figure/afdb_plddt.py` | new module | AFDB fetch + matplotlib pLDDT figure |
| `.cursor/skills/insynbio-literature-search/manifest.yaml` | v1.2.0 | openalex_search + doi_verify workflows |
| `.cursor/skills/insynbio-figure/manifest.yaml` | v1.2.0 | afdb_plddt recipe |
| `.cursor/skills/insynbio-literature-search/static/core/openalex-layer.md` | new | T3 layer rules |
| `.cursor/skills/insynbio-literature-search/static/workflows/openalex-search.md` | new | workflow |
| `.cursor/skills/insynbio-literature-search/static/workflows/doi-verify.md` | new | workflow |
| `.cursor/skills/insynbio-figure/static/recipes/afdb-plddt.md` | new | recipe spec |

## Step 3 交付物清单

| 文件 | 类型 | 说明 |
|------|------|------|
| `.cursor/skills/insynbio-research-suite/static/core/biomedical-domains.md` | 新 SSOT | 13 个生物医学领域分类 + 域检测信号 + 域特定gate规则 |
| `.cursor/skills/insynbio-research-suite/static/core/module-index.md` | 更新 | 移除抗体限制；新增 Style Calibration + Material Passport + AFDB 行 |
| `.cursor/skills/insynbio-research-suite/static/core/pipeline-order.md` | 更新 | 通用12步流程；移除 Review B 单一示例 |
| `.cursor/skills/insynbio-research-suite/static/workflows/style-calibration.md` | 新 workflow | 6维风格校准协议 (ARS Step 10 适配) |
| `.cursor/skills/insynbio-research-suite/static/workflows/material-passport.md` | 新 workflow | 跨会话稿件状态跟踪 (ARS Schema 9 适配) |
| `scripts/insynbio_style_calibration.py` | 新 CLI | 6维作者风格分析 → `style_profile.json` |
| `scripts/insynbio_material_passport.py` | 新 CLI | 稿件进度管理 + claim-evidence audit |
| `.cursor/skills/insynbio-research-suite/SKILL.md` | v1.1.0 | 描述更新：通用生物医学，不限抗体 |
| `.cursor/skills/insynbio-research-suite/manifest.yaml` | v1.1.0 | 新增 `biomedical-domains.md` + `style_calibration` + `material_passport` |
| `.cursor/skills/insynbio-therasik-suite/SKILL.md` | v1.1.0 | 描述更新：通用生物医学写作平台 |

## Step 5 交付物清单

| 文件 | 类型 | 说明 |
|------|------|------|
| `scripts/insynbio_submission_writer.py` | 新 CLI | 4 subcommands: abstract · highlights · cover-letter · response-to-reviewers |
| `scripts/insynbio_research.py` | 更新 | --init-project 通用化；submission-writer workflow；Material Passport checkpoint；容错缺失 key |
| `scripts/at_figure_comply.py` | 新 | 图表合规转换 AT/OUP (300dpi TIFF-LZW 170mm) |
| `scripts/insynbio_figure.py` | 更新 | comply subcommand；km + legend recipes |
| `core/figure/templates/km_plot.py` | 新 | KM survival curve (Greenwood CI + log-rank) |
| `core/figure/templates/figure_legend.py` | 新 | Figure legend generator (Nature/Cell/PLOS/generic) |

**已关闭的连贯性缺陷：**

| # | 缺陷 | 修复 |
|---|------|------|
| 🔴 1 | `--project` hardcoded `review_b` | `--init-project` 通用化；动态读取 JSON |
| 🟠 2 | 无投稿三件套（摘要/highlights/封信） | `insynbio_submission_writer.py` |
| 🟠 3 | Material Passport 未连通 | `_passport_checkpoint()` 写入 literature/bundle/rigor 节点 |
| 🟡 4 | `submission-writer` workflow 缺失 | 新增 `--workflow submission-writer` |

**仍待处理（已记录，未阻塞）：**
- LanguageTool grammar API 集成
- Semantic Scholar citation context
- FAIR data statement CLI
- Figure-text concordance checker

## Step 4 交付物清单

| 文件 | 类型 | 说明 |
|------|------|------|
| `scripts/insynbio_journal_format.py` | 新 CLI | CrossRef lookup + Zotero CSL download + Sherpa RoMEO OA policy |
| `.cursor/skills/insynbio-research-suite/static/workflows/journal-format.md` | 新 workflow | 期刊格式决策树 + 命令参考 |
| `.cursor/skills/insynbio-research-suite/manifest.yaml` | v1.3.0 | 新增 `journal_format` workflow + `journal_format` section |

**API 覆盖：**
- CrossRef → 30,000+ 期刊（发行商、ISSN、文章类型）
- Zotero CSL → 9,000+ 期刊引用格式，按需下载 `.csl`
- Sherpa RoMEO → 3,000+ 期刊开放获取政策（需免费注册 API key）

**Pandoc 集成：**
```powershell
python scripts/insynbio_journal_format.py get-csl "Nature Methods" --out styles/nature-methods.csl
pandoc manuscript.md --bibliography refs.bib --csl styles/nature-methods.csl --output manuscript.docx
```

**ARS change_style.ps1 集成：**
```powershell
.\change_style.ps1 -CslUrl https://www.zotero.org/styles/nature-methods
```

## 季度维护命令

```powershell
# nature-skills quarterly sync
python scripts/diff_nature_adopt.py --update-vendor
python scripts/diff_nature_adopt.py --mirror figure academic-search citation paper-to-patent reader paper2ppt polishing
python scripts/diff_nature_adopt.py --report vendor/nature_skills_diff_report.json --markdown vendor/NATURE_ADOPT_DIFF.md

# GDM science-skills update (manual — shallow re-clone)
cd vendor && git clone --depth 1 https://github.com/google-deepmind/science-skills science-skills-new
# compare, update lock, re-mirror if changed
cd ..

git add vendor/ scripts/ core/figure/afdb_plddt.py && git commit -m "chore(vendor): quarterly skill ecosystem sync"
```
