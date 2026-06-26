# MVP 爬虫部署与同步清单

> 仓库：`jhuang7908/Antibody-Engineer-Suite-MVP`  
> 本地路径：`therasik-academic-writing-suite/`（即 MVP 根目录，`origin` 已指向该 repo）  
> 最后更新：2026-06-26

---

## 架构一览

```
┌─────────────────────────────────────────────────────────────┐
│  GitHub Actions（定时 / 手动）                               │
│  .github/workflows/scrape_guidelines_playwright.yml         │
│  → scripts/journal_db/scrape_journal_guidelines.py          │
│  → commit 到 MVP master                                     │
└──────────────────────────┬──────────────────────────────────┘
                           │
                           ▼
┌─────────────────────────────────────────────────────────────┐
│  本地按需拉回                                                │
│  python scripts/pull_cloud_journal_scrapes.py               │
│  → 合并 guidelines_url / scraped_at / submission_guidelines  │
│  → 报告：assets/journal_requirements/scraped/_cloud_pull_report.json │
└──────────────────────────┬──────────────────────────────────┘
                           │
                           ▼
┌─────────────────────────────────────────────────────────────┐
│  本地 L2 主刊精抓（可选）                                     │
│  python scripts/scrape_guidelines_local.py --limit 5        │
└─────────────────────────────────────────────────────────────┘
```

| 脚本 | 运行位置 | 作用 |
|------|----------|------|
| `journal_db/scrape_journal_guidelines.py` | **云端 GHA** | 大规模 URL 发现 + 字数/类型/声明项 |
| `pull_cloud_journal_scrapes.py` | **本地按需** | 把 MVP commit 同步回本地 |
| `scrape_guidelines_local.py` | 本地 | L2 种子表、robots 合规、慢积累 |
| `scrape_guidelines_playwright.py` | 本地 | 出版商专属深解析（Elsevier/Nature 等） |

---

## 一、本次升级包含的文件（push 前核对）

### 必推 — 云端爬虫 + 工作流

| 文件 | 变更 |
|------|------|
| `scripts/journal_db/scrape_journal_guidelines.py` | Frontiers requests 回退、声明项、provenance、非破坏性合并 |
| `.github/workflows/scrape_guidelines_playwright.yml` | 与 MVP 对齐：跑 `journal_db` 脚本；安装 bs4/requests |
| `scripts/pull_cloud_journal_scrapes.py` | **新增** — 云端结果拉回 |
| `scripts/scrape_guidelines_local.py` | **新增** — 本地 polite 爬虫（原 scrape_journal_guidelines 改名） |
| `assets/journal_requirements/_scrape_seeds.json` | **新增** — L2 种子表 |

### 必推 — MCP / CSL

| 文件 | 变更 |
|------|------|
| `scripts/csl_engine.py` | **新增** — CSL 10k+ 样式引擎 |
| `scripts/mcp_server.py` | `format_citations` 接 CSL |
| `requirements-mcp.txt` | + citeproc-py, beautifulsoup4, requests |
| `scripts/scrape_guidelines_playwright.py` | 声明项、provenance、issn list 修复 |

### 可选推 — 数据与文档

| 文件 | 说明 |
|------|------|
| `assets/journal_requirements/scraped/` | 本地抓取审计 + `_cloud_pull_report.json` |
| `assets/csl_styles/*.csl` | 已缓存 CSL 样式（可不上传，运行时会重新下载） |
| `assets/journal_requirements/*.json`（12 本 Frontiers） | 云端已 merge 的 guidelines_url |
| `MCP_FIX_BLOG_2026-06-26.md` | 变更日志 |
| `docs/operations/MVP_SCRAPER_DEPLOY.md` | 本文档 |

### 不要推

- `assets/literature_db/literature.db`（本地文献库）
- `DC_TCE_*.md`、`_cloud_files.txt`（临时/项目文件）
- `.env`、密钥

---

## 二、Push 步骤（PowerShell）

在 writing suite 根目录执行：

```powershell
cd "D:\InSynBio-AI-Research\Antibody_Engineer_Suite\data\ada245\writing_system_productization\therasik-academic-writing-suite"

# 1. 安全检查（mandatory）
git status
# 确认无大量 deleted；literature.db 不要 stage

# 2. 只 stage 爬虫/MCP 相关（示例）
git add `
  .github/workflows/scrape_guidelines_playwright.yml `
  scripts/journal_db/scrape_journal_guidelines.py `
  scripts/pull_cloud_journal_scrapes.py `
  scripts/scrape_guidelines_local.py `
  scripts/scrape_guidelines_playwright.py `
  scripts/csl_engine.py `
  scripts/mcp_server.py `
  scripts/stat_plots.py `
  requirements-mcp.txt `
  assets/journal_requirements/_scrape_seeds.json `
  docs/operations/MVP_SCRAPER_DEPLOY.md `
  MCP_FIX_BLOG_2026-06-26.md

# 3. 可选：stage 已 merge 的期刊 JSON（12 本 Frontiers + 6 本 local scrape）
git add assets/journal_requirements/scraped/
git add assets/journal_requirements/frontiers_*.json
git add assets/journal_requirements/nature.json assets/journal_requirements/plos_one.json
# … 按需

# 4. 再次确认 staged 列表
git diff --cached --name-status

# 5. 提交
git commit -m "$(cat <<'EOF'
feat(guidelines): upgrade cloud scraper, CSL engine, and cloud-pull bridge

- journal_db scraper: declarations, provenance, Frontiers requests fallback
- Align GHA workflow with journal_db script + bs4/requests deps
- Add pull_cloud_journal_scrapes.py for on-demand MVP sync
- Add scrape_guidelines_local.py and CSL format_citations engine
EOF
)"

# 6. 推送
git push origin HEAD
```

---

## 三、Push 后 — 触发云端跑一轮

### 方式 A：GitHub CLI

```powershell
gh workflow run scrape_guidelines_playwright.yml `
  --repo jhuang7908/Antibody-Engineer-Suite-MVP `
  --field publisher=Frontiers `
  --field limit=20 `
  --field full_rescrape=true
```

### 方式 B：GitHub 网页

`https://github.com/jhuang7908/Antibody-Engineer-Suite-MVP/actions/workflows/scrape_guidelines_playwright.yml`  
→ **Run workflow** → publisher=`Frontiers`, limit=`20`, full_rescrape=`true`

### 方式 C：本地 trigger 脚本

```powershell
$env:GITHUB_TOKEN = "<your PAT with repo+workflow scope>"
python scripts/trigger_playwright_batch.py --publisher Frontiers --limit 20
```

### 查看运行状态

```powershell
gh run list --repo jhuang7908/Antibody-Engineer-Suite-MVP --workflow scrape_guidelines_playwright.yml --limit 5
gh run view <run_id> --repo jhuang7908/Antibody-Engineer-Suite-MVP --log
```

---

## 四、云端跑完后 — 按需拉回本地

```powershell
cd ".../therasik-academic-writing-suite"

# 先看云端质量（不写文件）
python scripts/pull_cloud_journal_scrapes.py --audit-only

# 合并到本地
python scripts/pull_cloud_journal_scrapes.py

# 查看报告
Get-Content assets/journal_requirements/scraped/_cloud_pull_report.json
```

---

## 五、定时任务（已配置，push 后自动生效）

| 项 | 值 |
|----|-----|
| Cron | `0 3 * * 0`（每周日 03:00 UTC） |
| 模式 | 增量（跳过已有 `article_types` 的期刊） |
| 脚本 | `journal_db/scrape_journal_guidelines.py` |
| 产出 | 直接 commit 到 MVP `master` |

本地需在定时跑完后**手动或脚本**执行 `pull_cloud_journal_scrapes.py`（云端不会主动推到你电脑）。

可选：Windows 任务计划程序每周一执行 pull：

```powershell
# 示例：每周一 09:00 拉回
schtasks /Create /TN "TheraSIK-PullCloudGuidelines" /TR "python D:\...\scripts\pull_cloud_journal_scrapes.py" /SC WEEKLY /D MON /ST 09:00
```

---

## 六、验收标准（push + 一轮 GHA 后）

| 检查项 | 命令 / 位置 | 期望 |
|--------|-------------|------|
| GHA 成功 | `gh run list` | `completed` / `success` |
| 有 commit | MVP commit message | `data(guidelines): scrape article_types` |
| 字数或声明 | `--audit-only` | `has_word_limits` 或 `submission_guidelines` > 0 |
| 本地已同步 | `_cloud_pull_report.json` | `merged` > 0 |
| MCP 可读 | `get_journal_requirements("Frontiers in Immunology")` | 含 `submission_guidelines` 或 `guidelines_url` |

---

## 七、已知问题

1. **Submodule push 失败**：历史 GHA 曾因 `NJSLA_Grade3_Prep` submodule 报 128。若再出现，在 MVP repo 修 `.gitmodules` 或 workflow 里 `git config submodule.recurse false`。
2. **Frontiers SPA**：已加 requests 回退；若仍空，用 `scrape_guidelines_local.py --slug frontiers_in_immunology` 补抓。
3. **本地 workflow 曾与 MVP 分叉**：本次已对齐为 `journal_db` 脚本；push 后以本 repo 的 yml 为准。

---

## 八、快速命令备忘

```powershell
# 部署
git push origin HEAD

# 触发云端
gh workflow run scrape_guidelines_playwright.yml -f publisher=Frontiers -f limit=20 -f full_rescrape=true

# 拉回
python scripts/pull_cloud_journal_scrapes.py

# 本地 L2 补抓
python scripts/scrape_guidelines_local.py --limit 5
python scripts/scrape_guidelines_local.py --status
```
