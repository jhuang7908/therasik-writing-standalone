# PDF

## 🚀 

### 1: HTML

****：
1. ：`paper/VHH7D12_InSynBio.html`
2. （Chrome、Edge、Firefox）
3.  `Ctrl+P` (Windows)  `Cmd+P` (Mac)
4. ："PDF"
5. ：
   - ****：
   - ****：
   - ****：✅ 
   - ****：
6. ""

****：
- ✅ 
- ✅ 
- ✅ 
- ✅ Mermaid

---

### 2: Typora

1. Typora
2. ：`paper/VHH7D12_InSynBio.md`
3. ：**** -> **** -> **PDF**
4. ：
   - （SimSun/）
   - ：A4
   - ：
5. ""

---

### 3: VS Code

1. ："Markdown PDF" (by yzane)
2. ：`paper/VHH7D12_InSynBio.md`
3.  -> "Markdown PDF: Export (pdf)"
4. 

---

## 📝 HTML

：

```powershell
# Windows PowerShell
python scripts\generate_paper_html.py
```

```bash
# Linux/Mac
python scripts/generate_paper_html.py
```

---

## 🔧 

### Pandoc

****：
- Pandoc: https://pandoc.org/installing.html
- MiKTeX (Windows)  TeX Live (Linux/Mac)

****：
```powershell
# Windows
cd paper
pandoc "VHH7D12_InSynBio.md" `
  -o "VHH7D12_InSynBio.pdf" `
  --pdf-engine=xelatex `
  --from=markdown+raw_html+tex_math_dollars `
  --toc `
  --number-sections `
  -V CJKmainfont=SimSun `
  -V mainfont="Times New Roman"
```

：`PDF_GENERATION_GUIDE.md`

---

## ✅ PDF

PDF：
- [ ] 
- [ ] （ $H(X) = -\sum p_i \log_2(p_i)$）
- [ ] 
- [ ] 
- [ ] Mermaid

---

## 🆘 ？

1. ****
   - HTML -> PDF（1）
   - Typora

2. **Mermaid**
   - HTML，Mermaid
   - Typora

3. ****
   - HTMLMathJax，
   - JavaScript

4. ****
   - HTML -> PDF
   - Typora

---

## 📍 

- **Markdown**: `paper/VHH7D12_InSynBio.md`
- **HTML**: `paper/VHH7D12_InSynBio.html`
- **PDF**: `paper/VHH7D12_InSynBio.pdf`

---

****：HTML ->  -> PDF（、）
