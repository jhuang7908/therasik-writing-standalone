# python-pptx 模板规范 (v0.1)

> 把 `ContentDoc` JSON 渲染成**可编辑** `.pptx` 的规范。
> 核心理念：**确定性排版**——版式、字号、留白由模板规范决定，不交给 AI 临场发挥。

---

## 1. 为什么用 python-pptx 而不是「AI 直接画整页」

| 方案 | 文字可编辑 | 中文乱码风险 | 速度 | 成本 |
|---|---|---|---|---|
| AI 画整页图 | 否（死图） | 高 | 慢 | 高 |
| AI 画图 + DeckWeaver OCR 还原 | 是（近似） | 中 | 慢 | 中 |
| **python-pptx 填母版**（本规范） | **是（原生）** | **无** | **快** | **低** |

结论：MVP 主力用 python-pptx。AI 只负责 `visual`（背景/插画），真实文字由 python-pptx 写入文本框。

---

## 2. 模板包结构

每套模板是一个目录：

```text
templates/ppt_tech_blue_01/
├── template.json        # 模板清单 (尺寸/色/字/各 layout 的几何规范)
├── master.pptx          # 可选: 预置母版/主题 (空白起点亦可)
├── assets/              # 模板自带装饰 png/svg
└── preview.png          # 缩略图 (供 UI 模板选择)
```

`template_id` = 目录名，`ContentDoc.template_id` 引用它。

---

## 3. `template.json` 规范

坐标单位统一用 **EMU 的友好封装**：本规范用**英寸 (inch)**，渲染器内部转 EMU。
幻灯片默认 16:9 = `13.333in × 7.5in`。

```jsonc
{
  "template_id": "ppt_tech_blue_01",
  "slide_size": { "w_in": 13.333, "h_in": 7.5 },
  "palette": {
    "primary": "#1E3A8A",
    "secondary": "#0EA5E9",
    "text_dark": "#1F2937",
    "text_light": "#FFFFFF",
    "bg": "#F8FAFC"
  },
  "fonts": {
    "title": "思源黑体",
    "body": "思源黑体",
    "fallback": "Microsoft YaHei"
  },
  "layouts": {
    "cover": {
      "bg_fill": "primary",          // 或 "image" → 用 visual.resolved 图片铺满
      "boxes": {
        "title":    { "x":0.9,"y":2.6,"w":11.5,"h":1.6,"size":44,"bold":true,"color":"text_light","align":"left" },
        "subtitle": { "x":0.9,"y":4.3,"w":11.5,"h":0.9,"size":22,"color":"secondary","align":"left" },
        "tag":      { "x":0.9,"y":0.8,"w":3.0,"h":0.5,"size":14,"color":"text_light","align":"left" }
      }
    },
    "title_bullets": {
      "bg_fill": "bg",
      "boxes": {
        "title":   { "x":0.9,"y":0.7,"w":11.5,"h":1.0,"size":32,"bold":true,"color":"primary","align":"left" },
        "bullets": { "x":1.1,"y":2.0,"w":11.0,"h":4.8,"size":20,"color":"text_dark","line_spacing":1.4 }
      }
    }
    // ... 其余 layout 同构
  }
}
```

### 3.1 box 字段

| 字段 | 含义 |
|---|---|
| `x,y,w,h` | 位置/尺寸（英寸） |
| `size` | 字号（pt） |
| `bold` | 是否加粗 |
| `color` | 调色板键名或 `#hex` |
| `align` | `left/center/right` |
| `line_spacing` | 行距倍数（bullets 用） |

---

## 4. layout → box 映射

渲染器按 `block.layout` 取 `template.json.layouts[layout]`，把 `block.text` / `block.bullets` 写入对应 box：

| layout | 必填 box | 可选 box | visual 用法 |
|---|---|---|---|
| `cover` | title | subtitle, tag | 背景铺满 |
| `section` | title | subtitle | 背景/色块 |
| `title_bullets` | title, bullets | — | 无/角落小图 |
| `two_column` | title, body | bullets | 无 |
| `image_left` | title, body | caption | 左半区放图 |
| `image_right` | title, body | caption | 右半区放图 |
| `big_number` | title | subtitle, caption, bullets | 无 |
| `quote` | body | caption | 背景纹理 |

> 缺失的可选 box 自动跳过；多出的 text 字段忽略。**确定性**：同一 JSON + 同一模板 → 同一版面。

---

## 5. 中文与字体规则（强约束）

1. 标题/正文字体必须来自 `fonts`，且为**可商用字体**（思源黑体/思源宋体/阿里巴巴普惠体）。
2. 渲染器须设置 **East Asian font**（`rPr.eastAsia`），否则 Windows/Mac 打开可能回退乱字。
3. 不嵌入未授权商业字体。
4. 文本一律走文本框，**绝不**把中文写进生图 prompt。

---

## 6. 图片填充规则

- `visual.resolved.asset_url` 下载到本地缓存后插入。
- `cover` 背景图：铺满整页并叠加半透明色块保证文字可读（`primary` 加 ~35% 透明遮罩）。
- `image_left/right`：图片裁切适配半区，保持纵横比，居中裁剪。
- 无 `visual` 或 `resolved=null`：用 `palette` 纯色/色块兜底，不报错。

---

## 7. 渲染器接口

参考实现：`renderer/ppt_renderer.py`

```bash
# 用内置默认模板渲染示例（无需外部模板文件即可跑通）
python renderer/ppt_renderer.py \
  --doc ../schemas/example_ppt.json \
  --out ../outputs/example_ppt.pptx
```

函数签名：

```python
def render_ppt(doc: dict, template: dict | None, out_path: str) -> dict:
    """doc: ContentDoc dict; template: template.json dict 或 None(用内置默认);
    返回 qa 报告 dict。"""
```

---

## 8. QA 校验（渲染后）

渲染器输出 `qa` 报告，至少检查：

| 检查 | 通过条件 |
|---|---|
| slide_count | == len(blocks) |
| text_runs | 每页标题非空 |
| placeholder | 无残留 `{{...}}` |
| zero_byte_media | 无 0 字节图片 |
| font_set | 标题/正文均设置了 eastAsia 字体 |

任一失败 → doc `status=failed`，不扣积分。

---

## 9. 与 DeckWeaver 的关系

- **python-pptx（本规范）**：主力，结构化 → 原生可编辑 PPT。
- **DeckWeaver**：补充工具，用于「用户只有一张 PPT 图片」时逆向还原为可编辑 PPT。

二者并存，路由按输入类型选择。
