# Creative Studio — MVP 技术方案书

> 面向中国商业客户的「AI 图文并茂文件生成平台」。
> AI 理解需求 → 多模型生图 → 模板排版 → 输出**可编辑**文件（PPT / 白皮书 / 小红书 / 公众号）。
>
> 文档版本：v0.1 · 状态：MVP 设计稿 · 与 InSynBio/Therasik 主业务**完全隔离**。

---

## 0. 一句话定位

> 不是「让 AI 画一张死图」，而是「AI 写内容 + 多模型生背景图 + 代码精准排版 + 导出可编辑文件」。

核心原则贯穿全系统：**图文分离（Text/Visual Separation）**。

- AI 生图引擎：只负责背景、插画、主视觉、纹理。
- LLM：负责文案、结构、版面建议，输出**结构化 JSON**。
- 渲染引擎：把真实中文文字精准排到版面，保证可编辑、不乱码。

---

## 1. MVP 产品范围

第一版只做 3 类高价值、可编辑、易交付场景：

| 优先级 | 场景 | 输出 | AI 生图 |
|---|---|---|---|
| P0 | 可编辑商业 PPT | `.pptx` | 仅封面/章节页 |
| P0 | 小红书 / 公众号封面 + 配图 | `.png` + 工程 JSON | 是 |
| P1 | 商业白皮书 / 产品说明书 | `.docx` / `.pdf` | 部分配图 |

二期：名片、菜单、海报。三期：Logo（矢量 + 商标 + 字体授权最复杂，最后做）。

**MVP 完成定义（Definition of Done）**

用户能完成闭环：
`选业务 → 选模板 → 输入需求/上传文档 → AI 生成 → 预览 → 充值扣积分 → 下载可编辑文件`。

---

## 2. 系统架构

### 2.1 分层图

```text
┌─────────────────────────────────────────────┐
│  前端操作台 (Next.js / React + Tailwind)       │
│  左:业务  中:模板+结果  右:AI对话+账户          │
└───────────────┬─────────────────────────────┘
                │ HTTPS / WebSocket
┌───────────────┴─────────────────────────────┐
│  API 网关 (FastAPI)                           │
│  鉴权 / 任务编排 / 支付 / 积分 / 模型路由        │
└──┬────────────┬──────────────┬───────────────┘
   │            │              │
┌──┴────┐  ┌────┴─────┐  ┌─────┴──────┐
│LLM路由 │  │图像路由   │  │任务队列     │
│Deepseek│  │GPT-Image2│  │Redis+Celery│
│Claude  │  │Flux/国内  │  └─────┬──────┘
└────────┘  │模板/图库  │        │
            └──────────┘  ┌──────┴───────────────┐
                          │ Worker 池             │
                          │ cpu / ocr / gpu(可选) │
                          └──────┬───────────────┘
                                 │
              ┌──────────────────┴─────────────────┐
              │ Postgres(用户/订单/任务)  对象存储(文件) │
              └─────────────────────────────────────┘
```

### 2.2 模块职责

| 模块 | 职责 | MVP 选型 |
|---|---|---|
| Frontend | 操作台、产品页、下载 | Next.js + Tailwind + shadcn/ui |
| API | 鉴权、编排、支付、路由 | FastAPI + Pydantic |
| LLM Router | 文案/大纲/结构 → JSON | `deepseek-chat` 主，`claude`/`gpt` 兜底 |
| Image Router | 是否生图 + 选模型 | template → stock → flux → 国内 → gpt-image-2 |
| Render Engine | JSON → 可编辑文件 | python-pptx / HTML→PDF / DOCX |
| Queue | 异步任务、并发控制 | Redis + Celery |
| Storage | 文件、模板、缓存 | Postgres + S3/R2/OSS |

---

## 3. 核心数据流

```text
用户需求(文本/文档)
   │
   ▼
[LLM Router] ── 生成 ContentDoc JSON (标题/要点/图片需求/版面类型)
   │
   ▼
[Image Router] ── 逐 visual_slot 判断:
   │   能套模板? → template_only (不烧钱)
   │   有合适图库? → stock_asset
   │   需新图?    → flux / 国内 / gpt-image-2
   ▼
[Render Engine] ── ContentDoc + 模板 + 图片 → 可编辑文件
   │
   ▼
[QA] ── 文本未乱码 / 占位符已填 / 无零字节图 / 页数一致
   │
   ▼
输出: pptx / pdf / docx / png + qa.json
```

**关键：** `ContentDoc` JSON 是全系统的「单一事实来源」（详见 `CONTENT_PROTOCOL.md`）。同一份 JSON 同时驱动 PPT、PDF、Web 预览，保证离线/在线一致。

---

## 4. 多模型路由（不绑死单一模型）

### 4.1 图像路由优先级

```text
ImageRouter.resolve(visual_slot) ->
  1. template_only   # 版面自带视觉，不生图（最省）
  2. stock_asset     # 开源图库命中关键词
  3. flux / sdxl     # 标准配图
  4. 国内模型         # 通义万相 / 即梦 (备用)
  5. gpt_image_2     # 高端兜底 / 付费套餐专属
```

由 LLM 在生成 ContentDoc 时给出 `visual.preferred_tier`，路由再结合用户套餐与预算决策。

### 4.2 文本路由

| 任务 | 默认 | 兜底 |
|---|---|---|
| 中文文案 / PPT 大纲 / 白皮书结构 | `deepseek-chat` | `claude` |
| 复杂逻辑 / 英文 | `claude` / `gpt` | `deepseek-reasoner` |

> 成本约束：文本默认走 DeepSeek（便宜），图像默认尽量套模板，GPT-Image-2 只在高端套餐触发。

---

## 5. 文件生成引擎

| 输出 | 主方案 | 说明 |
|---|---|---|
| PPT | `python-pptx` 填自建母版 | **首选**，稳定、可编辑（详见 `PPTX_TEMPLATE_SPEC.md`） |
| 海报/名片/菜单 | HTML/CSS → Puppeteer | 渲染 PDF/PNG，排版自由 |
| 白皮书 | Markdown → DOCX/PDF | 长文档、可改段落 |
| 图片转可编辑 PPT | DeckWeaver(已跑通) | **高级补充工具**，非主力 |

---

## 6. Docker 隔离方案

新平台依赖重（paddle/torch/easyocr/opencv/libreoffice/字体），**必须容器化**，与抗体工程主业务隔离。

```text
creative-frontend       # Next.js
creative-api            # FastAPI
creative-worker-cpu     # python-pptx / HTML→PDF / DOCX
creative-worker-ocr     # DeckWeaver / PaddleOCR (重依赖)
creative-worker-gpu     # 可选: 本地图像 / 放大 / 抠图
redis                   # 队列
postgres                # 用户/订单/任务
minio (或 OSS/R2/S3)     # 对象存储
```

队列分级：
- `queue:fast` → CPU worker（文案、PPTX、PDF）
- `queue:ocr` → OCR worker（DeckWeaver）
- `queue:gpu` → GPU worker（按需启用）

---

## 7. 部署与域名演进

| 阶段 | 入口 | 说明 |
|---|---|---|
| 1 内测 | `insynbio.com/creative`（介绍页）+ 独立操作台服务 | 复用品牌信任，快速测试 |
| 2 成长 | `studio.insynbio.com` | 服务独立，仍依托品牌 |
| 3 独立 | 独立商业域名 | ToB/ToC 中国商业定位，脱离生物医药品牌 |

InSynBio 官网仅放**入口介绍页 + CTA**，CTA 跳转到独立操作台容器，不污染现有 runtime。

---

## 8. 支付与积分

- **Stripe**：海外/跨境用户、信用卡。
- **微信支付**：国内客户（需商户资质）。
- **积分制 + 订阅制并行**：
  - 积分：充值得积分，按生成消耗扣（生图/PPT 页数/导出格式不同价）。
  - 订阅：月会员（更多积分、专属模板、批量、优先队列）。
  - 套餐分层：基础(标准模型) / 专业(GPT-Image-2) / 企业(品牌模板+批量)。

积分扣费在任务**成功产出后**结算，失败不扣或退还，写入 `usage_ledger`。

---

## 9. 素材与授权分级

| 级别 | 内容 | 可复用 |
|---|---|---|
| A Public Safe | 开源图标/CC0图片/开源字体/自生成背景 | 是 |
| B Licensed | Envato/Freepik/千库企业授权 | 按授权，留痕 |
| C Client Owned | 客户 Logo/产品图/品牌 VI | 否（仅该项目） |
| D Studio Original | 自建模板/筛选后AI素材/自有版式 | 是（核心壁垒） |

每个素材记录：来源、授权类型、下载日期、ID、是否可再分发、是否可客户商用。
字体优先：思源黑体/思源宋体/阿里巴巴普惠体/Noto。

---

## 10. 实施路线（8–10 周）

| 周 | 里程碑 |
|---|---|
| 1 | Docker 骨架、API、前端壳、DB |
| 2–3 | LLM 路由 + 图像路由 + ContentDoc JSON 协议 |
| 3–4 | python-pptx 自建母版，跑通可编辑 PPT |
| 4–5 | 模板库先做 20 套（PPT/小红书/公众号） |
| 5–6 | 操作台 UI（三栏布局） |
| 6–7 | Stripe + 微信 + 积分扣费 |
| 7–8 | Redis 队列、生成历史、下载记录 |
| 8–10 | 挂 InSynBio 入口页内测，小范围收费 |

---

## 11. 可行性与风险

**技术可行性：高** — 图像生成 + DeckWeaver 可编辑 PPT 链路已本地验证。

**商业可行性：中高** — 痛点真实、付费意愿存在、成本可控；难点在模板质量与运营。

| 风险 | 对策 |
|---|---|
| 排版乱码/不确定 | 图文分离 + 自建模板 |
| 模型供应/合规 | 多模型路由，不依赖单一模型 |
| 支付合规 | 微信商户资质 + 跨境合规通道 |
| 素材授权 | 开源优先 + 授权留痕 + 客户资产不复用 |
| GPU 成本 | MVP 不上 GPU，重任务排队 |

**成功关键不是模型，而是：模板质量 + 可编辑输出 + 中文场景 + 支付闭环 + 稳定队列。**

---

## 12. 关联文档

- `CONTENT_PROTOCOL.md` — ContentDoc JSON 协议（单一事实来源）
- `PPTX_TEMPLATE_SPEC.md` — python-pptx 模板规范
- `ui_prototype/console.html` — 操作台 UI 原型
- `schemas/content_doc.schema.json` — JSON Schema
- `schemas/content_doc.py` — Pydantic 模型
