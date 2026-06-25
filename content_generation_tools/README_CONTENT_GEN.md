# InSynBio AI Content Generation Studio

这个目录包含了用于生成**图文并茂的商业白皮书、可编辑 PPT、小红书图文和公众号文章**的开源核心工具链。

## 📁 目录结构

*   **`deckweaver/` (Image2PPT)**
    *   **用途：** 逆向还原工具。将 AI 生成的高清 PPT 图片，通过本地 PaddleOCR 识别，还原成**文字完全可编辑**的原生 `.pptx` 文件。
    *   **场景：** 英文文章转 PPT、学术汇报。
*   **`ppt-templates/` (gpt-image2-ppt-skills)**
    *   **用途：** 高级 PPT 模板库与克隆工具。
    *   **场景：** 内置 10 套极高审美的 PPT 风格（如科技蓝、极简、包豪斯等）。你可以直接参考里面的提示词和版式设计。
*   **`space-design/` (space-GPT-image2-design)**
    *   **用途：** 全能新媒体与长文配图工作室。包含四个子模块：
        1.  `space-article-batch-illustration`: **商业白皮书/公众号**（自动阅读长文，批量插入配图）。
        2.  `space-chart-image`: **公众号/报告**（生成 SWOT、流程图、架构图等逻辑图表）。
        3.  `space-image-studio`: **小红书**（生成高点击率封面、内页配图）。
        4.  `space-baoyu-slide-deck`: 内容到整套幻灯片的快速生成。

## 🛠️ 环境配置 (Windows / Cursor)

为了不污染您现有的 `affmat` 或 `anarcii` 等抗体工程环境，我们为您创建了一个专属的独立环境。

1.  在 Cursor 终端中，进入本目录：
    ```powershell
    cd content_generation_tools
    ```
2.  运行一键安装脚本（自动创建 `content_gen` conda 环境并安装 PaddleOCR 等依赖）：
    ```powershell
    .\setup_env.ps1
    ```
3.  激活环境：
    ```powershell
    conda activate content_gen
    ```

## 🚀 核心工作流实战指南

### 1. 英文文章 ➡️ 可编辑 PPT
1.  **大纲生成：** 用您服务器的 `DeepSeek-Chat` 将英文文章总结为 10 页的 PPT 大纲（每页包含标题和 3 个要点）。
2.  **图片生成：** 参考 `ppt-templates` 里的风格提示词，调用 `OpenAI (dall-e-3 / gpt-image-2)` 为这 10 页大纲生成 10 张图片。
3.  **转为可编辑：** 将这 10 张图片放入 `deckweaver` 的输入文件夹，运行：
    ```bash
    python deckweaver/scripts/convert.py --input ./my_images --output ./my_ppt.pptx
    ```
    *DeckWeaver 会自动把图片里的英文/中文抠出来，变成可双击修改的文本框。*

### 2. 商业白皮书 (Whitepaper) & 公众号
1.  **文本撰写：** 用 `DeepSeek-Chat` 写好 Markdown 格式的白皮书或公众号长文。
2.  **自动配图：** 使用 `space-design/space-article-batch-illustration` 脚本。
    ```bash
    # 伪代码示例，具体参考该目录下的 README
    python space-design/space-article-batch-illustration/main.py --file whitepaper.md --style "tech-blue"
    ```
    *脚本会自动阅读您的 Markdown，在需要解释的段落自动调用 OpenAI 画图并插入，最终输出图文并茂的文档。*

### 3. 小红书图文
1.  **封面生成：** 使用 `space-design/space-image-studio`。
    *   **Prompt 示例：** “画一张小红书封面，比例 3:4，主标题‘抗体工程效率翻倍’，使用 `xhs-vibrant` 风格。”
2.  **图表生成：** 如果需要科普硬核知识，使用 `space-design/space-chart-image` 生成一张漂亮的逻辑图（如抗体发现流程图），作为小红书的第二页。

## 🔑 API Key 配置
在使用这些 Python 脚本前，请确保在当前目录下创建一个 `.env` 文件，填入您的 API 密钥：
```env
OPENAI_API_KEY=sk-xxxxxx
OPENAI_BASE_URL=https://api.openai.com/v1  # 如果您有中转地址，填在这里
```