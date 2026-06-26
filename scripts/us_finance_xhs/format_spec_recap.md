# 每日收盘复盘 (WeChat Recap v1) 格式规范标准 (SSOT-Recap)

本规范用于 AISS 审计人对每日5点收盘复盘 JSON 输出进行格式层面的严格校验。所有不符合本规范的输出将被直接打回重修。

---

## 一、 属性表格约束

| **字段名** | **约束规则** | **严重等级** | **说明** |
| :--- | :--- | :--- | :--- |
| `format_version` | 固定为 `"recap_v1"` | High | 版本号校验 |
| `wechat_moments` | 必须为非空 Object | High | 朋友圈对象根节点 |
| `wechat_moments.title` | 字符串，15 汉字以内 | Medium | 吸引眼球的标题 |
| `wechat_moments.moments_text` | 字符串，80–150 汉字 | High | 微信朋友圈文案（不允许含有 # 标签） |
| `wechat_moments.card` | 必须为非空 Object，且仅能包含 1 个卡片 | High | 仅发 1 张图，不允许多图 |
| `card.image_role` | 固定为 `"cover"` | High | 首张/单张图角色 |
| `card.title` | 字符串，12 汉字以内 | High | 卡片内大标题 |
| `card.body` | 字符串，40–80 汉字 | High | 正文，必须提炼核心利率与大盘走势 |
| `card.bullets` | 必须为恰好 3 个元素的 String Array | High | 正好 3 个要点 |
| `card.bullets[i]` | 每个元素必须以 `1.` `2.` `3.` 阿拉伯数字编号开头 | High | 列表格式强约束 |
| `card.image_caption` | 必须匹配北美的月/天/年格式：`截至 MM/DD/YYYY` | High | 如 "截至 06/08/2026" |

---

## 二、 合规与免责约束

1. **绝对禁忌词（平台风控过滤）**：
   - 严禁出现「贷款」「房贷」「商业贷款」等字眼。
   - 必须使用 `dai款`、`房dai`、`商业房dai` 替代。
2. **零营销红线**：
   - 不得包含任何销售招揽字眼、微信二维码诱导、联系人方式。
3. **免责标签检验**：
   - 在 `wechat_moments.moments_text` 或 `card.body` 的底部，必须带有：`〔纯财经探讨，非投资及dai款建议〕` 免责文字。
