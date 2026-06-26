# nature-skills 学习协议（强制）

> **Upstream SSOT:** [Yuan1z0825/nature-skills](https://github.com/Yuan1z0825/nature-skills)  
> **Local index:** `insynbio-therasik-suite/static/core/nature-skills-adopt-matrix.md`

## 何时必须读 nature 原版

在以下情况 **先读 nature 对应模块**（GitHub `skills/nature-*` 或本地 clone），再改 InSynBio/Therasik 技能：

1. **新建** 与 nature 同名的 `insynbio-*` 模块
2. **升级** 已有模块 major version
3. **用户明确要求** 对齐 nature-skills / 取长补短
4. **头对头评估** 显示我们落后（如 reader 完成度、polishing Stable、figure stats）

## 五步法（mirror nature router）

1. **Load manifest** — nature 模块的 `manifest.yaml` + 我们的 `manifest.yaml`
2. **Detect axes** — paper_type / section / backend / journal（能映射则映射）
3. **Load fragments** — 只读当前任务需要的 `static/` + `references/`
4. **Diff** — 填 adopt matrix：「采纳 / 已有 / 垂直替代 / 暂不采纳」
5. **Execute** — 用 **CLI 产物** 验证，不只改 SKILL  prose

## 取长补短原则

| 规则 | 说明 |
|------|------|
| **采纳** | nature 的 router 结构、failure-mode 顺序、figure contract、lean PPT 模式 |
| **保留** | ScholarOne audit、corpus、AbEngineCore、content-ssot-guard、抗体 evidence grade |
| **垂直优先** | 与 Nature 泛模板冲突时，OUP/抗体规范优先（记录于 adopt matrix） |
| **不复制** | 21k star 社区运营、知识星球、Codex 安装文案 — 只复制 **工程与写作科学** |
| **署名** | adopt matrix 中注明 nature 模块版本与借鉴文件名 |

## 禁止

- 未读 nature 对应 `SKILL.md` 就声称「已超 nature」
- 把 nature 全文 copy 进 repo（只摘 **规则摘要** + 链接 upstream）
- 用 LLM 生成统计图 **替代** 明确的数据契约（figure contract 先行）

## 维护节奏

- 每季度：运行 `python scripts/diff_nature_adopt.py --update-vendor --report vendor/nature_skills_diff_report.json --markdown vendor/NATURE_ADOPT_DIFF.md`
- 每个 Review / 投稿项目：在 EVOLUTION_LOG 或项目 README 记一条 `[NATURE-ADOPT]` 借鉴点

## Vendor 目录

| Path | 用途 |
|------|------|
| `vendor/nature-skills/` | 只读 clone（`.gitignore`，本地更新） |
| `vendor/nature_skills.lock.json` | 提交 pin：commit / date |
| `scripts/diff_nature_adopt.py` | 模块版本 + static gap 报告 |
