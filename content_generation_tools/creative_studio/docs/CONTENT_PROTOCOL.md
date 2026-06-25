# ContentDoc — JSON 内容协议 (v0.1)

> 全系统的**单一事实来源 (Single Source of Truth)**。
> LLM 产出 `ContentDoc` → 图像路由填充 `visual` → 渲染引擎产出 PPT/PDF/DOCX/PNG。
> 同一份 JSON 同时驱动离线文件与在线预览，保证一致性。

---

## 1. 设计原则

1. **图文分离**：`text` 字段永远是真实可编辑文字；`visual` 只描述背景/插画需求，不承载正文文字。
2. **渲染无关**：协议不含字体磅值、像素坐标等渲染细节——那些属于模板（见 `PPTX_TEMPLATE_SPEC.md`）。协议只描述**内容与意图**。
3. **可路由**：每个 `visual` 带 `preferred_tier`，供图像路由按套餐/预算决策，不写死模型。
4. **可校验**：所有产出必须通过 `content_doc.schema.json` 校验后才进入渲染。
5. **可追溯**：`meta` 记录模型、时间、版本、积分预估，便于审计与计费。

---

## 2. 顶层结构

```jsonc
{
  "schema_version": "0.1",
  "doc_type": "ppt | xiaohongshu | wechat | whitepaper",
  "meta": { ... },          // 生成元数据
  "brand": { ... },         // 品牌约束 (色/字/logo)
  "template_id": "ppt_tech_blue_01",
  "locale": "zh-CN",
  "blocks": [ ... ]         // 内容块数组 (页/卡/章节)
}
```

### 2.1 `meta`

| 字段 | 类型 | 说明 |
|---|---|---|
| `generated_at` | string(ISO8601) | 生成时间 |
| `llm_model` | string | 产出此 doc 的文本模型 |
| `request_summary` | string | 用户原始需求摘要 |
| `credit_estimate` | int | 预估积分消耗 |
| `status` | enum | `draft / rendered / failed` |

### 2.2 `brand`

| 字段 | 类型 | 说明 |
|---|---|---|
| `primary_color` | string(#hex) | 主色 |
| `secondary_color` | string(#hex) | 辅色 |
| `font_family` | string | 优先可商用字体（思源黑体等） |
| `logo_asset_id` | string\|null | 客户上传 logo 资产 ID |

### 2.3 `blocks[]`

`block` 是通用内容单元，按 `doc_type` 解释为：
- ppt → 一页幻灯片
- xiaohongshu → 一张卡片（封面/内页）
- wechat → 一段图文
- whitepaper → 一个章节

| 字段 | 类型 | 说明 |
|---|---|---|
| `block_id` | string | 唯一 ID |
| `layout` | enum | 版面类型，见 §3 |
| `text` | object | 真实可编辑文字，见 §4 |
| `visual` | object\|null | 视觉需求（背景/插画），见 §5 |
| `bullets` | string[] | 要点列表（可空） |
| `notes` | string | 备注/讲者备注（可空） |

---

## 3. `layout` 枚举（与模板对应）

| layout | 适用 | 含义 |
|---|---|---|
| `cover` | 全部 | 封面/主视觉页 |
| `section` | ppt/whitepaper | 章节过渡页 |
| `title_bullets` | ppt | 标题 + 要点 |
| `two_column` | ppt/whitepaper | 左右分栏 |
| `image_left` / `image_right` | 全部 | 图文左右 |
| `big_number` | ppt/小红书 | 数据强调 |
| `quote` | 全部 | 引用/金句 |
| `card` | 小红书/公众号 | 单卡图文 |
| `chapter` | whitepaper | 正文章节 |

> 渲染引擎按 `template_id + layout` 找到具体母版版式（slide layout）。

---

## 4. `text` 对象

**只放真实文字，绝不交给生图模型。**

| 字段 | 类型 | 说明 |
|---|---|---|
| `title` | string | 主标题 |
| `subtitle` | string | 副标题（可空） |
| `body` | string | 正文段落（可空） |
| `caption` | string | 图注/角标（可空） |
| `tag` | string | 标签/栏目（可空，如「小红书」「干货」） |

---

## 5. `visual` 对象（图像路由消费）

| 字段 | 类型 | 说明 |
|---|---|---|
| `intent` | string | 中文意图描述（如「科技感蓝色抽象背景」） |
| `prompt_en` | string | LLM 扩写的英文 prompt（生图用，质量更高） |
| `role` | enum | `background / illustration / hero / texture / icon` |
| `aspect_ratio` | string | `16:9 / 3:4 / 1:1 / a4` |
| `preferred_tier` | enum | `template_only / stock / standard / premium` |
| `negative` | string | 负向提示（可空） |
| `resolved` | object\|null | 路由结果回填，见 §6 |

> `prompt_en` 由 LLM 把中文意图翻译扩写为高质量英文，再交给 GPT-Image-2/Flux，避免中文 prompt 出图质量下降。

---

## 6. `visual.resolved`（路由后回填）

| 字段 | 类型 | 说明 |
|---|---|---|
| `provider` | enum | `template_only / stock / flux / sdxl / qwen / jimeng / gpt_image_2` |
| `asset_id` | string | 产出图片资产 ID |
| `asset_url` | string | 存储 URL |
| `credit_cost` | int | 实际积分消耗 |
| `cached` | bool | 是否命中缓存 |

---

## 7. 完整示例

见 `schemas/example_ppt.json`（PPT）、`schemas/example_xhs.json`（小红书）。

---

## 8. 生命周期与状态机

```text
LLM 产出 (status=draft, visual.resolved=null)
   │ schema 校验通过
   ▼
图像路由填充 visual.resolved
   │
   ▼
渲染引擎产出文件 (status=rendered)
   │ 失败
   ▼
status=failed → 不扣积分 / 退还
```

---

## 9. 校验与计费

- 进入渲染前**必须** `jsonschema` 校验通过。
- `credit_estimate`（生成时）用于前端预估；`sum(visual.resolved.credit_cost)` + 渲染基价为**实际**扣费，成功后写入 `usage_ledger`。
- 任意 block 渲染失败 → 整 doc `failed`，按策略退还。

---

## 10. 关联文件

- `schemas/content_doc.schema.json` — JSON Schema (Draft 2020-12)
- `schemas/content_doc.py` — Pydantic v2 模型
- `schemas/example_ppt.json` — PPT 示例
- `schemas/example_xhs.json` — 小红书示例
