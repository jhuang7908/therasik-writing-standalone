# 小红书财经迷你格式 v1.3（2 张图 · 北美华人圈）



每期：**卡1 财经故事/新闻**（近一月内均可）；**卡2 dai款知识**（轮换）。生活化手账风，版式每期微变。



| 字段 | 约束 |

|------|------|

| **cards** | **固定 2 张**（page 1–2） |

| `title` | ≤ 20 汉字 |

| `cover_hook` | ≤ 30 汉字 |

| `body` | **180–320 汉字** |

| `tags` | **固定 5 个**，以 `#` 开头 |

| 卡1 `image_role` | `cover` — 财经故事/新闻 + 评论 |

| 卡2 `image_role` | `content` — dai款知识科普 |

| 每张 `card.title` | ≤ 15 汉字 |

| 每张 `card.body` | 50–120 汉字 |

| 每张 `card.bullets` | 2–4 条，阿拉伯数字编号 |



合规：禁止「贷款」「房贷」「商业贷款」；用 dai款 / 房dai。



JSON 顶层：`format_version: "finance_xhs_mini_v1"`，含 `xiaohongshu` 对象。

