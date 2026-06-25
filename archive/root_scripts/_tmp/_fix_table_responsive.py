import os
import re
from pathlib import Path

ROOT = Path("D:/InSynBio-AI-Research/Antibody_Engineer_Suite/insynbio-web-source")

def fix_html(file_path):
    print(f"Processing {file_path.name}...")
    content = file_path.read_text(encoding='utf-8')

    # 1. Ensure body has overflow-x: hidden to prevent horizontal page scroll
    if 'body {' in content:
        if 'overflow-x: hidden' not in content:
            content = re.sub(r'(body\s*\{[^}]*)}', r'\1; overflow-x: hidden; }', content)
    elif 'body{' in content:
        if 'overflow-x: hidden' not in content:
            content = re.sub(r'(body\{[^}]*)}', r'\1; overflow-x: hidden; }', content)

    # 2. Force all tables to be responsive
    table_css = """
    /* Global responsive table fix */
    table { display: block; width: 100%; overflow-x: auto; -webkit-overflow-scrolling: touch; }
    thead, tbody, tr { width: 100%; }
    """
    if '</style>' in content and 'Global responsive table fix' not in content:
        content = content.replace('</style>', table_css + '\n  </style>')

    # 3. Ensure header is pinned to viewport edges
    header_fix = "left: 0 !important; right: 0 !important; width: auto !important; position: fixed !important;"
    content = re.sub(r'(\.top-header\s*\{[^}]*position:\s*fixed;[^}]*)', r'\1 ' + header_fix, content)

    file_path.write_text(content, encoding='utf-8')

def main():
    html_files = []
    for f in ROOT.glob("*.html"):
        html_files.append(f.name)

    for filename in html_files:
        fp = ROOT / filename
        fix_html(fp)

if __name__ == "__main__":
    main()
