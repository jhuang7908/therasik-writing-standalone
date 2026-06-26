# huNSG-QUAD 实操流程（write.insynbio.com）

**目标**：从摘要 + 图 → 可投稿稿；**投稿就绪** = 0 个 `[FILL:]` + QC ≥ 80 PASS。

## 0. 登录与版本

- 打开 https://write.insynbio.com/
- 任意用户名 → Guest 档（10 Polish / 5 Draft 每天）
- 顶栏应显示 **v15.45+**（QC `[CITE:]` 锚定修复已部署于后端 v15.46，UI 版本号可仍为 15.45）

## 1. Draft 模式 — 录入研究内容

1. 切到 **📝 Draft**
2. 粘贴完整 **Abstract**（huNSG-QUAD 原文）
3. **§4 Discussion intent**：临床意义、MCC950 机制、与 pyroptosis 解耦、局限
4. **§8 Methods 模板**：勾选 Animal housing、HSPC、Flow、In vivo challenge、Cytokine、Statistics → **Generate Methods Template** → **Insert into Methods**
5. 上传 **Figure 1–4**（webp/png）→ 每张点 **📊 Data** 做定量提取
6. 可选：Excel 表 → Upload

## 2. 选刊与规划

1. 顶栏 **✦ Recommend** → 本次烟测首推 **PNAS**（机制 + 平台稿）
2. 期刊选择器切到 **PNAS**（或 Frontiers in Immunology）
3. **📐 Generate Plan** 或 **⚡ Plan + Draft All**

## 3. 逐节润色（Polish 模式）

1. 切 **🪶 Polish**，检查各节草稿
2. 填完所有黄色 **`[FILL:]`**（🔍 Placeholders 面板可列清单）
3. Results：把 figure **writing_manifest** 里的数字写进正文
4. 需要引用：**✍🔗 Draft + Cite** 或 Polish 里 **Find References / Insert Citations**

## 4. 质量闸门

1. **📊 QC Score** — 关注：
   - `fill_marker_residual` 必须 **0 占位**
   - `ai_tone` / `subjective_language`（v15.45 应已 PASS）
   - `logic_grounding`（v15.46+ 将 `[CITE:]` 与 Figure 计为锚定）
2. 若 FAIL 且为语言类 → **🛠 Auto-fix & rescore**
3. **🔗 Consistency** — Methods ↔ Results 数字/模型一致

## 5. 投稿包

1. **📦 Full Package** 或 **🗂 Finalize ZIP**
2. 检查 `submission_audit.txt` 中 `[FILL:]` 清单为空
3. 核对 DOCX 中黄色高亮占位是否已全部替换

## 烟测基线（2026-05-26）

| 运行 | 期刊 | 总分 | `[FILL:]` | logic_grounding | 主要 FAIL |
|------|------|------|-----------|-----------------|-----------|
| 有序烟测 Step2 | plos_med | 65 | 64 | 0/6 | FILL + logic + novelty |
| Step A（2026-05-27） | **pnas** | **77** | **43** | **6/12** | FILL + logic + novelty；**未插文献**（烟测曾关 `auto_insert_citations`） |
| Step A 回填文献 | pnas | 见 `*_cited_*.json` | 同左 | — | 用 `backfill_citations_rescore.py` |
| Step1 三刊 `/rewrite` | elife/pnas/nejm | — | 0 | — | 风格分化 OK，AI marker=0 |

报告文件：`smoke/huNSG_QUAD_pnas_20260527T001202Z.json`（VPS 已生成，本地已同步）。

填完 Methods/Results 的 43 处 `[FILL:]` 并插入真实文献后，预期总分 **80+**（需实测确认，非保证值）。
