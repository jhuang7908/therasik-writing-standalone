# 社交媒体内容格式规范 v2.0（SSOT）

> Canonical copy for agents. Mirror: `docs/SOCIAL_CONTENT_FORMAT_V2.md`

## A. 小红书（`platform: xiaohongshu`）

| 字段 | 硬性约束 |
|------|----------|
| **配图/卡片数量** | **固定 6 张**（`cards` 长度必须 = 6，`page` 为 1–6） |
| `title` 发布标题 | ≤ 20 汉字 |
| `cover_hook` 封面主文案 | ≤ 30 汉字，可用 `\n` 换行 |
| `body` 发布正文 | **400–600 汉字**（不含标签行） |
| `tags` | **固定 6 个**，均以 `#` 开头 |
| 每张 `card.title` | ≤ 15 汉字 |
| 每张 `card.body` | 40–80 汉字 |
| 每张 `card.bullets` | 1–3 条，每条 ≤ 18 汉字 |
| 每张 `card.image_caption` | 配图说明 ≤ 12 汉字 |
| `card.image_role` | 第 1 张 `cover`，第 2–6 张 `content` |

文体：短句、有节奏、适度 emoji、强钩子；数据仅来自原文。

## B. 微信公众号（`platform: wechat`）

| 字段 | 硬性约束 |
|------|----------|
| `title` | ≤ 26 汉字 |
| `subtitle` | ≤ 40 汉字 |
| `lead` 导语 | **100–150 汉字** |
| `sections` | **固定 5 节**，`heading` 以「一、」…「五、」开头 |
| 每节 `body` | **250–350 汉字** |
| `closing` 结语 | **80–120 汉字** |
| **总字数** | 导语 + 五节正文 + 结语 = **1500–2000 汉字** |
| `cover_digest` 摘要 | **50–120 汉字**，与本期内容相关；用于后台「摘要」及群聊卡片说明 |
| `ad_bar` 广告栏 | **固定模板**（`config/wechat_ad_bar.yaml`），文末展示；国内微信，无海外邮箱 |

### 配图分工（勿混淆）

| 名称 | 文件 | 何时显示 | 后台操作 |
|------|------|----------|----------|
| **封面图** | `wechat_cover.png`（900×383，2.35:1） | 微信群/订阅号**未点开**时的外链卡片 | gpt-image-2 生成；上传为「封面图」，**取消**「封面显示在正文中」 |
| **正文配图** | `wechat_inline_01.png`、`wechat_inline_02.png` | **点开后**正文第 2、4 节内 | 编辑器内插入 |
| **广告栏图** | `wechat_ad_bar.png` | **点开后**文末广告块 | 编辑器末尾插入 |

正文**不要**再使用头图 `wechat_hero`（避免与封面重复）。

## C. JSON 顶层

`format_version`: `v2.0`；含 `xiaohongshu`、`wechat` 及各自 `format_annotation`。

字符串内禁止 ASCII 双引号 `"`，用「」。
