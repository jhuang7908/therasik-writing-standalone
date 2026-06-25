# PDF

## 

MarkdownPDF：
1. **** - 
2. **Mermaid** - 
3. **** - LaTeX
4. **** - Pandoc

## 

### 1: Typora（，）

****：
- PDF
- 
- Mermaid
- 

****：
1. Typora: https://typora.io/
2.  `VHH7D12_InSynBio.md`
3. ： ->  -> PDF
4. ：
   - ：（SimSun/）
   - ：A4
   - ：
5. 

---

### 2: VS Code + Markdown PDF

****：
1. VS Code："Markdown PDF" (by yzane)
2. Markdown
3.  -> "Markdown PDF: Export (pdf)"
4. ：`Ctrl+Shift+P` -> "Markdown PDF: Export (pdf)"

****（VS Code）：
```json
{
  "markdown-pdf.outputDirectory": "paper",
  "markdown-pdf.styles": [],
  "markdown-pdf.includeDefaultStyles": true,
  "markdown-pdf.displayHeaderFooter": true,
  "markdown-pdf.headerTemplate": "",
  "markdown-pdf.footerTemplate": ""
}
```

---

### 3: Pandoc + XeLaTeX

****：
- Pandoc: https://pandoc.org/installing.html
- LaTeX（MiKTeXTeX Live）
- （Windows）

****：

#### Windows PowerShell:
```powershell
cd "d:\InSynBio-AI-Research\Antibody_Engineer_Suite\paper"

# A: XeLaTeX（，）
pandoc "VHH7D12_InSynBio.md" `
  -o "VHH7D12_InSynBio.pdf" `
  --pdf-engine=xelatex `
  --from=markdown+raw_html+tex_math_dollars `
  --toc `
  --number-sections `
  -V geometry:margin=2.5cm `
  -V fontsize=11pt `
  -V CJKmainfont=SimSun `
  -V mainfont=Times\ New\ Roman `
  --highlight-style=tango

# B: XeLaTeX，pdflatex
pandoc "VHH7D12_InSynBio.md" `
  -o "VHH7D12_InSynBio.pdf" `
  --pdf-engine=pdflatex `
  --from=markdown+raw_html+tex_math_dollars `
  --toc `
  --number-sections `
  -V geometry:margin=2.5cm `
  -V fontsize=11pt
```

#### Linux/Mac:
```bash
cd paper

pandoc "VHH7D12_InSynBio.md" \
  -o "VHH7D12_InSynBio.pdf" \
  --pdf-engine=xelatex \
  --from=markdown+raw_html+tex_math_dollars \
  --toc \
  --number-sections \
  -V geometry:margin=2.5cm \
  -V fontsize=11pt \
  -V CJKmainfont="Noto Sans CJK SC" \
  -V mainfont="Times New Roman" \
  --highlight-style=tango
```

****：
- Windows:  `SimSun` `Microsoft YaHei`
- Linux: ：`sudo apt-get install fonts-noto-cjk`
- Mac:  `STSong`  `PingFang SC`

---

### 4: Python

：
```bash
python scripts/generate_paper_pdf.py
```

：
- 
- Mermaid
- PDF
- 

---

### 5: Markdown -> HTML -> PDF（Chrome）

****：
1. HTML：
```bash
pandoc "VHH7D12_InSynBio.md" \
  -o "paper.html" \
  --standalone \
  --css=paper-style.css \
  --toc \
  --number-sections
```

2. Chrome `paper.html`
3.  `Ctrl+P` (Windows)  `Cmd+P` (Mac)
4. ：PDF
5. ：
   - ：
   - ：
   - ：
   - ：
6. 

****：
- LaTeX
- 
- 

---

### 6: 

1. **Dillinger**: https://dillinger.io/
   - Markdown
   -  -> PDF

2. **Markdown to PDF**: https://www.markdowntopdf.com/
   - 
   - PDF

3. **CloudConvert**: https://cloudconvert.com/md-to-pdf
   - Markdown
   - PDF

****：Mermaid，。

---

## Mermaid

PDFMermaid：

### 1: mermaid-cli
```bash
# 
npm install -g @mermaid-js/mermaid-cli

# 
mmdc -i paper/figures/Fig1_pipeline_mermaid.md -o paper/figures/Fig1_pipeline_mermaid.png
```

### 2: 
1.  https://mermaid.live/
2. Mermaid
3. PNG
4. MarkdownMermaid

### 3: Typora
TyporaMermaid，PDF。

---

## 

### Q1: 
****：
- XeLaTeX（`--pdf-engine=xelatex`）
- （`-V CJKmainfont=SimSun`）
- Typora/VS Code

### Q2: 
****：
-  `--from=markdown+tex_math_dollars`
- XeLaTeXLuaLaTeX
- （ `$$...$$`  `\[...\]`）

### Q3: 
****：
-  `--tables` 
- HTMLPDF
- Typora

### Q4: 
****：
- ：`figures/Fig2_fr23_delta_by_strategy.png`
- 
- 

### Q5: (TOC)
****：
-  `--toc` 
-  `--toc-depth=3` 

---

## （Pandoc）

 `paper-template.tex`：

```latex
\documentclass[11pt,a4paper]{article}
\usepackage[UTF8]{ctex}
\usepackage{geometry}
\geometry{margin=2.5cm}
\usepackage{graphicx}
\usepackage{booktabs}
\usepackage{longtable}
\usepackage{hyperref}
\hypersetup{colorlinks=true,linkcolor=blue}

\title{IMGTVHH7D12}
\author{InSynBio}
\date{2024}

\begin{document}
\maketitle
\tableofcontents
\newpage

$body$

\end{document}
```

：
```bash
pandoc input.md -o output.pdf --template=paper-template.tex --pdf-engine=xelatex
```

---

## 

### Windows PowerShell
```powershell
# （Typora）
# Typora

# Pandoc
pandoc "paper\VHH7D12_InSynBio.md" `
  -o "paper\VHH7D12_InSynBio.pdf" `
  --pdf-engine=xelatex `
  --from=markdown+raw_html+tex_math_dollars `
  --toc `
  --number-sections `
  -V CJKmainfont=SimSun `
  -V mainfont="Times New Roman"
```

### Linux/Mac
```bash
pandoc paper/VHH7D12_InSynBio.md \
  -o paper/VHH7D12_InSynBio.pdf \
  --pdf-engine=xelatex \
  --from=markdown+raw_html+tex_math_dollars \
  --toc \
  --number-sections \
  -V CJKmainfont="Noto Sans CJK SC"
```

---

## PDF

PDF：
- [ ] 
- [ ] 
- [ ] 
- [ ] 
- [ ] 
- [ ] 
- [ ] 

---

## 

PDF，：
1. 
2. 
3. Typora
4. HTML -> PDFChrome
