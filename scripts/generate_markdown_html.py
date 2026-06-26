#!/usr/bin/env python3
"""
Convert a Markdown report to a print-friendly HTML for browser PDF export.

Usage:
  python scripts/generate_markdown_html.py --input "output/7D12/7D12_CRO_Client_Report_CN_Rearranged.md" --output "output/7D12/7D12_CRO_Client_Report_CN_Rearranged.html" --title "7D12 VHH CRO Client Report"

Notes:
  - No pandoc/LaTeX required.
  - If the `markdown` package is installed, conversion quality improves:
      pip install markdown
"""

from __future__ import annotations

import argparse
import re
from pathlib import Path

try:
    import markdown  # type: ignore

    HAS_MARKDOWN = True
except Exception:
    HAS_MARKDOWN = False


HTML_TEMPLATE = """<!DOCTYPE html>
<html lang="zh-CN">
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width, initial-scale=1.0">
  <title>{title}</title>
  <style>
    @page {{ size: A4; margin: 2.2cm; }}
    body {{
      font-family: "Microsoft YaHei", "SimSun", "", "Times New Roman", serif;
      font-size: 11pt;
      line-height: 1.6;
      color: #222;
      max-width: 21cm;
      margin: 0 auto;
      padding: 16px;
      background: white;
    }}
    h1 {{ font-size: 22pt; text-align: center; margin: 24px 0 16px; page-break-after: avoid; }}
    h2 {{ font-size: 16pt; margin: 22px 0 10px; border-bottom: 2px solid #222; padding-bottom: 4px; page-break-after: avoid; }}
    h3 {{ font-size: 13pt; margin: 16px 0 8px; page-break-after: avoid; }}
    p {{ margin: 8px 0; text-align: justify; }}
    table {{ width: 100%; border-collapse: collapse; margin: 12px 0; page-break-inside: avoid; font-size: 9.5pt; }}
    th, td {{ border: 1px solid #ddd; padding: 6px 8px; vertical-align: top; }}
    th {{ background: #f2f2f2; }}
    code {{ background: #f4f4f4; padding: 1px 4px; border-radius: 3px; font-family: "Consolas", "Monaco", monospace; }}
    pre {{ background: #f4f4f4; padding: 10px; border-radius: 6px; overflow-x: auto; page-break-inside: avoid; }}
    img {{ max-width: 100%; height: auto; display: block; margin: 12px auto; page-break-inside: avoid; }}
    blockquote {{ border-left: 4px solid #ddd; margin: 12px 0; padding: 6px 12px; color: #555; }}
    hr {{ border: none; border-top: 1px solid #ddd; margin: 18px 0; }}
    @media print {{
      body {{ margin: 0; padding: 0; }}
      h1, h2, h3 {{ page-break-after: avoid; }}
      table, pre, img {{ page-break-inside: avoid; }}
    }}
  </style>
</head>
<body>
{content}
</body>
</html>
"""


def _md_to_html_simple(md_content: str) -> str:
    """Fallback converter (basic headings, bold, code, links, images, tables)."""
    html = md_content

    # Headings
    html = re.sub(r"^# (.+)$", r"<h1>\1</h1>", html, flags=re.MULTILINE)
    html = re.sub(r"^## (.+)$", r"<h2>\1</h2>", html, flags=re.MULTILINE)
    html = re.sub(r"^### (.+)$", r"<h3>\1</h3>", html, flags=re.MULTILINE)

    # Bold / inline code
    html = re.sub(r"\*\*(.+?)\*\*", r"<strong>\1</strong>", html)
    html = re.sub(r"`([^`]+)`", r"<code>\1</code>", html)

    # Images / links
    html = re.sub(r"!\[([^\]]*)\]\(([^)]+)\)", r'<img src="\2" alt="\1">', html)
    html = re.sub(r"\[([^\]]+)\]\(([^)]+)\)", r'<a href="\2">\1</a>', html)

    # Horizontal rule
    html = re.sub(r"^---$", r"<hr>", html, flags=re.MULTILINE)

    # Tables: simplest block conversion (pipe tables)
    def convert_table(match: re.Match) -> str:
        lines = match.group(0).strip().splitlines()
        if len(lines) < 2:
            return match.group(0)
        header = [c.strip() for c in lines[0].split("|")[1:-1]]
        # skip separator line
        body_lines = lines[2:] if len(lines) >= 3 else []
        out = ["<table>", "<thead><tr>"]
        out += [f"<th>{h}</th>" for h in header]
        out += ["</tr></thead>", "<tbody>"]
        for ln in body_lines:
            if not ln.strip().startswith("|"):
                continue
            cols = [c.strip() for c in ln.split("|")[1:-1]]
            out.append("<tr>" + "".join(f"<td>{c}</td>" for c in cols) + "</tr>")
        out += ["</tbody></table>"]
        return "\n".join(out)

    table_pattern = r"(^\|.*\|\n^\|[ \t:-]+\|.*\|\n(?:^\|.*\|\n)*)"
    html = re.sub(table_pattern, convert_table, html, flags=re.MULTILINE)

    # Paragraphs: wrap non-tag lines
    out_lines = []
    for line in html.splitlines():
        s = line.strip()
        if not s:
            out_lines.append("")
            continue
        if s.startswith("<h") or s.startswith("<table") or s.startswith("</table") or s.startswith("<tr") or s.startswith("</tr") or s.startswith("<td") or s.startswith("<th") or s.startswith("<img") or s.startswith("<hr") or s.startswith("<pre") or s.startswith("</pre") or s.startswith("<blockquote") or s.startswith("</blockquote") or s.startswith("<ul") or s.startswith("</ul") or s.startswith("<ol") or s.startswith("</ol") or s.startswith("<li") or s.startswith("</li") or s.startswith("<thead") or s.startswith("</thead") or s.startswith("<tbody") or s.startswith("</tbody"):
            out_lines.append(line)
        else:
            out_lines.append(f"<p>{line}</p>")
    return "\n".join(out_lines)


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--input", required=True, help="Input Markdown file")
    ap.add_argument("--output", required=True, help="Output HTML file")
    ap.add_argument("--title", default="Report", help="HTML title")
    args = ap.parse_args()

    in_path = Path(args.input)
    out_path = Path(args.output)

    md_text = in_path.read_text(encoding="utf-8")
    if HAS_MARKDOWN:
        html_body = markdown.markdown(
            md_text,
            extensions=["tables", "fenced_code"],
            output_format="html5",
        )
    else:
        html_body = _md_to_html_simple(md_text)

    out_path.write_text(HTML_TEMPLATE.format(title=args.title, content=html_body), encoding="utf-8")
    print("Wrote:", out_path)
    if not HAS_MARKDOWN:
        print("[]  markdown /：pip install markdown")


if __name__ == "__main__":
    main()

