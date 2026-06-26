#!/usr/bin/env python3
"""
MarkdownHTML，PDF
pandocLaTeX
"""

import re
from pathlib import Path

# markdown（）
try:
    import markdown
    HAS_MARKDOWN = True
except ImportError:
    HAS_MARKDOWN = False
    print("[] markdown:")
    print("      pip install markdown")

PROJECT_ROOT = Path(__file__).resolve().parent.parent
PAPER_MD = PROJECT_ROOT / "paper" / "VHH7D12_InSynBio.md"
OUTPUT_HTML = PROJECT_ROOT / "paper" / "VHH7D12_InSynBio.html"

# HTML
HTML_TEMPLATE = """<!DOCTYPE html>
<html lang="zh-CN">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>IMGTVHH7D12</title>
    <style>
        @page {
            size: A4;
            margin: 2.5cm;
        }
        
        body {
            font-family: "Microsoft YaHei", "SimSun", "", "Times New Roman", serif;
            font-size: 11pt;
            line-height: 1.6;
            color: #333;
            max-width: 21cm;
            margin: 0 auto;
            padding: 20px;
            background: white;
        }
        
        h1 {
            font-size: 24pt;
            font-weight: bold;
            text-align: center;
            margin-top: 30px;
            margin-bottom: 20px;
            page-break-after: avoid;
        }
        
        h2 {
            font-size: 18pt;
            font-weight: bold;
            margin-top: 25px;
            margin-bottom: 15px;
            page-break-after: avoid;
            border-bottom: 2px solid #333;
            padding-bottom: 5px;
        }
        
        h3 {
            font-size: 14pt;
            font-weight: bold;
            margin-top: 20px;
            margin-bottom: 10px;
            page-break-after: avoid;
        }
        
        h4 {
            font-size: 12pt;
            font-weight: bold;
            margin-top: 15px;
            margin-bottom: 8px;
        }
        
        p {
            margin: 10px 0;
            text-align: justify;
        }
        
        table {
            width: 100%;
            border-collapse: collapse;
            margin: 15px 0;
            page-break-inside: avoid;
            font-size: 9pt;
        }
        
        table th, table td {
            border: 1px solid #ddd;
            padding: 8px;
            text-align: left;
        }
        
        table th {
            background-color: #f2f2f2;
            font-weight: bold;
        }
        
        table tr:nth-child(even) {
            background-color: #f9f9f9;
        }
        
        code {
            background-color: #f4f4f4;
            padding: 2px 4px;
            border-radius: 3px;
            font-family: "Consolas", "Monaco", monospace;
            font-size: 0.9em;
        }
        
        pre {
            background-color: #f4f4f4;
            padding: 15px;
            border-radius: 5px;
            overflow-x: auto;
            page-break-inside: avoid;
        }
        
        pre code {
            background: none;
            padding: 0;
        }
        
        blockquote {
            border-left: 4px solid #ddd;
            margin: 15px 0;
            padding-left: 15px;
            color: #666;
        }
        
        img {
            max-width: 100%;
            height: auto;
            display: block;
            margin: 15px auto;
            page-break-inside: avoid;
        }
        
        .mermaid {
            text-align: center;
            margin: 20px 0;
            page-break-inside: avoid;
        }
        
        ul, ol {
            margin: 10px 0;
            padding-left: 30px;
        }
        
        li {
            margin: 5px 0;
        }
        
        hr {
            border: none;
            border-top: 1px solid #ddd;
            margin: 20px 0;
        }
        
        .math {
            font-family: "Times New Roman", serif;
            font-style: italic;
        }
        
        @media print {
            body {
                margin: 0;
                padding: 0;
            }
            
            h1, h2, h3 {
                page-break-after: avoid;
            }
            
            table, pre, img {
                page-break-inside: avoid;
            }
        }
    </style>
    <!-- Mermaid -->
    <script src="https://cdn.jsdelivr.net/npm/mermaid@10/dist/mermaid.min.js"></script>
    <script>
        mermaid.initialize({ startOnLoad: true, theme: 'default' });
    </script>
    <!-- MathJax -->
    <script src="https://polyfill.io/v3/polyfill.min.js?features=es6"></script>
    <script id="MathJax-script" async src="https://cdn.jsdelivr.net/npm/mathjax@3/es5/tex-mml-chtml.js"></script>
    <script>
        window.MathJax = {
            tex: {
                inlineMath: [['$', '$'], ['\\(', '\\)']],
                displayMath: [['$$', '$$'], ['\\[', '\\]']]
            }
        };
    </script>
</head>
<body>
{content}
</body>
</html>
"""

def markdown_to_html_simple(md_content):
    """MarkdownHTML（）"""
    html = md_content
    
    # 
    html = re.sub(r'^# (.+)$', r'<h1>\1</h1>', html, flags=re.MULTILINE)
    html = re.sub(r'^## (.+)$', r'<h2>\1</h2>', html, flags=re.MULTILINE)
    html = re.sub(r'^### (.+)$', r'<h3>\1</h3>', html, flags=re.MULTILINE)
    html = re.sub(r'^#### (.+)$', r'<h4>\1</h4>', html, flags=re.MULTILINE)
    
    # 
    html = re.sub(r'\*\*(.+?)\*\*', r'<strong>\1</strong>', html)
    
    # 
    html = re.sub(r'\*(.+?)\*', r'<em>\1</em>', html)
    
    # Mermaid（）
    html = re.sub(r'```mermaid\n(.*?)```', 
                  lambda m: f'<div class="mermaid">\n{m.group(1)}\n</div>', 
                  html, flags=re.DOTALL)
    
    # 
    html = re.sub(r'```(\w+)?\n(.*?)```', 
                  lambda m: f'<pre><code class="{m.group(1) or ""}">{m.group(2)}</code></pre>', 
                  html, flags=re.DOTALL)
    
    # 
    html = re.sub(r'`([^`]+)`', r'<code>\1</code>', html)
    
    # 
    html = re.sub(r'\[([^\]]+)\]\(([^)]+)\)', r'<a href="\2">\1</a>', html)
    
    # 
    html = re.sub(r'!\[([^\]]*)\]\(([^)]+)\)', r'<img src="\2" alt="\1">', html)
    
    # 
    html = re.sub(r'^---$', r'<hr>', html, flags=re.MULTILINE)
    
    # MarkdownHTML
    def convert_table(match):
        lines = match.group(0).strip().split('\n')
        if len(lines) < 2:
            return match.group(0)
        
        # 
        header_line = lines[0]
        if not header_line.startswith('|'):
            return match.group(0)
        
        headers = [h.strip() for h in header_line.split('|')[1:-1]]
        
        # （ |---|---|）
        data_start = 2 if len(lines) > 1 and '---' in lines[1] else 1
        
        # HTML
        html_table = '<table>\n<thead>\n<tr>\n'
        for h in headers:
            html_table += f'<th>{h}</th>\n'
        html_table += '</tr>\n</thead>\n<tbody>\n'
        
        # 
        for line in lines[data_start:]:
            if not line.strip() or not line.startswith('|'):
                continue
            cells = [c.strip() for c in line.split('|')[1:-1]]
            if len(cells) == len(headers):
                html_table += '<tr>\n'
                for cell in cells:
                    html_table += f'<td>{cell}</td>\n'
                html_table += '</tr>\n'
        
        html_table += '</tbody>\n</table>'
        return html_table
    
    # Markdown（|）
    html = re.sub(
        r'(\|.+\|\n(?:\|[-: ]+\|\n)?(?:\|.+\|\n?)+)',
        convert_table,
        html,
        flags=re.MULTILINE
    )
    
    # （，）
    paragraphs = html.split('\n\n')
    processed = []
    for p in paragraphs:
        p = p.strip()
        if not p:
            continue
        # HTML
        if not p.startswith('<') and not p.startswith('|'):
            p = f'<p>{p}</p>'
        processed.append(p)
    html = '\n\n'.join(processed)
    
    # Mermaid
    html = re.sub(r'<pre><code class="mermaid">(.*?)</code></pre>', 
                  r'<div class="mermaid">\1</div>', html, flags=re.DOTALL)
    
    return html

def process_markdown_file(md_path):
    """Markdown，HTML"""
    with open(md_path, 'r', encoding='utf-8') as f:
        md_content = f.read()
    
    # markdown
    if HAS_MARKDOWN:
        # markdown
        md = markdown.Markdown(
            extensions=[
                'extra',  # 、
                'codehilite',  # 
                'tables',  # 
                'fenced_code',  # 
            ],
            extension_configs={
                'codehilite': {
                    'css_class': 'highlight'
                }
            }
        )
        html_content = md.convert(md_content)
        
        # Mermaid
        html_content = re.sub(
            r'<pre><code class="language-mermaid">(.*?)</code></pre>',
            r'<div class="mermaid">\1</div>',
            html_content,
            flags=re.DOTALL
        )
    else:
        # 
        html_content = markdown_to_html_simple(md_content)
    
    # （CSS）
    final_html = HTML_TEMPLATE.replace('{content}', html_content)
    
    return final_html

def main():
    print("="*60)
    print("MarkdownHTML（PDF）")
    print("="*60)
    print()
    
    if not PAPER_MD.exists():
        print(f"[] : {PAPER_MD}")
        return 1
    
    print(f"[] : {PAPER_MD}")
    html_content = process_markdown_file(PAPER_MD)
    
    print(f"[] HTML: {OUTPUT_HTML}")
    with open(OUTPUT_HTML, 'w', encoding='utf-8') as f:
        f.write(html_content)
    
    print(f"[] HTML: {OUTPUT_HTML}")
    print()
    print(":")
    print("1. HTML")
    print("2.  Ctrl+P (Windows)  Cmd+P (Mac)")
    print("3.  'PDF'")
    print("4. :")
    print("   - : ")
    print("   - : ")
    print("   - : ")
    print("5. ")
    print()
    print(f": {OUTPUT_HTML}")
    
    return 0

if __name__ == "__main__":
    import sys
    sys.exit(main())
