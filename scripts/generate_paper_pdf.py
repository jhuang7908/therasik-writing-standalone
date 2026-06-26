#!/usr/bin/env python3
"""
VHHPDF
、Mermaid、
"""

import os
import sys
import subprocess
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent
PAPER_MD = PROJECT_ROOT / "paper" / "VHH7D12_InSynBio.md"
OUTPUT_DIR = PROJECT_ROOT / "paper"
OUTPUT_PDF = OUTPUT_DIR / "VHH7D12_InSynBio.pdf"

def check_dependencies():
    """"""
    missing = []
    
    # pandoc
    try:
        result = subprocess.run(["pandoc", "--version"], 
                               capture_output=True, text=True, timeout=5)
        if result.returncode != 0:
            missing.append("pandoc")
    except (FileNotFoundError, subprocess.TimeoutExpired):
        missing.append("pandoc")
    
    # LaTeX (xelatex)
    latex_engines = ["xelatex", "pdflatex", "lualatex"]
    found_engine = None
    for engine in latex_engines:
        try:
            result = subprocess.run([engine, "--version"], 
                                   capture_output=True, text=True, timeout=5)
            if result.returncode == 0:
                found_engine = engine
                break
        except (FileNotFoundError, subprocess.TimeoutExpired):
            continue
    
    if not found_engine:
        missing.append("LaTeX (xelatex/pdflatex/lualatex)")
    
    return missing, found_engine

def convert_mermaid_to_image(mermaid_code, output_path):
    """Mermaid (mermaid-cli)"""
    try:
        # mermaid-cli (mmdc)
        subprocess.run(["mmdc", "-i", "-", "-o", str(output_path)], 
                      input=mermaid_code, text=True, check=True, timeout=30)
        return True
    except (FileNotFoundError, subprocess.CalledProcessError, subprocess.TimeoutExpired):
        print(f"[] mermaid-cliMermaid")
        print(f"       Mermaid，: https://mermaid.live/")
        return False

def preprocess_markdown(md_path, output_path):
    """Markdown，Mermaid"""
    with open(md_path, 'r', encoding='utf-8') as f:
        content = f.read()
    
    # Mermaid
    import re
    mermaid_pattern = r'```mermaid\n(.*?)```'
    matches = list(re.finditer(mermaid_pattern, content, re.DOTALL))
    
    # Mermaid（）
    # ，Mermaid
    fig1_path = OUTPUT_DIR / "figures" / "Fig1_pipeline_mermaid.png"
    if fig1_path.exists():
        content = re.sub(
            r'```mermaid\n(.*?)```',
            f'![1: ](figures/Fig1_pipeline_mermaid.png)',
            content,
            count=1,
            flags=re.DOTALL
        )
    
    # 
    with open(output_path, 'w', encoding='utf-8') as f:
        f.write(content)
    
    return len(matches)

def generate_pdf_with_pandoc(md_path, pdf_path, latex_engine="xelatex"):
    """pandocPDF"""
    
    # Markdown
    temp_md = OUTPUT_DIR / "temp_paper.md"
    mermaid_count = preprocess_markdown(md_path, temp_md)
    
    # Pandoc
    cmd = [
        "pandoc",
        str(temp_md),
        "-o", str(pdf_path),
        "--pdf-engine", latex_engine,
        "--from", "markdown+raw_html+tex_math_dollars",
        "--to", "pdf",
        "--toc",  # 
        "--toc-depth", "3",
        "--number-sections",  # 
        "--highlight-style", "tango",
        "-V", "geometry:margin=2.5cm",
        "-V", "fontsize=11pt",
        "-V", "linestretch=1.5",
        "-V", "documentclass=article",
    ]
    
    #  (XeLaTeX)
    if latex_engine == "xelatex":
        cmd.extend([
            "-V", "CJKmainfont=SimSun",  # Windows
            "-V", "CJKoptions=BoldFont=SimHei,ItalicFont=KaiTi",
            "--variable", "mainfont=Times New Roman",
        ])
    elif latex_engine == "lualatex":
        cmd.extend([
            "-V", "CJKmainfont=SimSun",
            "--variable", "mainfont=Times New Roman",
        ])
    
    print(f"[]  {latex_engine} PDF...")
    print(f"[] : {' '.join(cmd)}")
    
    try:
        result = subprocess.run(cmd, check=True, capture_output=True, text=True, timeout=300)
        print(f"[] PDF: {pdf_path}")
        
        # 
        if temp_md.exists():
            temp_md.unlink()
        
        return True
    except subprocess.CalledProcessError as e:
        print(f"[] PDF:")
        print(f"       : {e.returncode}")
        print(f"       : {e.stderr}")
        return False
    except subprocess.TimeoutExpired:
        print(f"[] PDF(>5)")
        return False

def generate_pdf_alternative_methods(md_path):
    """PDF"""
    print("\n" + "="*60)
    print("PDF:")
    print("="*60)
    
    print("\n1: Typora (，)")
    print("  1. Typora: https://typora.io/")
    print("  2. Markdown")
    print("  3.  ->  -> PDF")
    print("  4. ")
    
    print("\n2: VS Code + Markdown PDF")
    print("  1. : 'Markdown PDF' by yzane")
    print("  2. Markdown")
    print("  3.  -> Markdown PDF: Export (pdf)")
    
    print("\n3: ")
    print("  1. : https://www.markdowntopdf.com/")
    print("  2. : https://dillinger.io/ (PDF)")
    
    print("\n4: Chrome")
    print("  1. MarkdownHTML:")
    print(f"     pandoc {md_path} -o {OUTPUT_DIR / 'paper.html'}")
    print("  2. ChromeHTML")
    print("  3.  -> PDF")
    print("  4. : , : ")
    
    print("\n5: Python (weasyprint/markdown-pdf)")
    print("  : pip install weasyprint markdown")
    print("  Python")

def main():
    print("="*60)
    print("VHHPDF")
    print("="*60)
    
    if not PAPER_MD.exists():
        print(f"[] : {PAPER_MD}")
        return 1
    
    # 
    missing, latex_engine = check_dependencies()
    
    if missing:
        print(f"\n[] :")
        for dep in missing:
            print(f"  - {dep}")
        print("\n:")
        print("  - pandoc: https://pandoc.org/installing.html")
        print("  - LaTeX: MiKTeX (Windows)  TeX Live (Linux/Mac)")
        print("    XeLaTeX")
        
        generate_pdf_alternative_methods(PAPER_MD)
        return 1
    
    print(f"\n[] LaTeX: {latex_engine}")
    
    # PDF
    success = generate_pdf_with_pandoc(PAPER_MD, OUTPUT_PDF, latex_engine)
    
    if not success:
        print("\n[] Pandoc，...")
        generate_pdf_alternative_methods(PAPER_MD)
        return 1
    
    print(f"\n[] PDF: {OUTPUT_PDF}")
    print(f"       : {OUTPUT_PDF.stat().st_size / 1024:.1f} KB")
    
    return 0

if __name__ == "__main__":
    sys.exit(main())
