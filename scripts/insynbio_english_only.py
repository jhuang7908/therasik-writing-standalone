# Convert InSynBio HTML to English-only: remove lang switch, drop Chinese, keep English.
import re
import os

DOCS = os.path.join(os.path.dirname(__file__), "..", "docs")
FILES = [
    "index.html",
    "InSynBio_Antibody_Developability_Assessment_Page.html",
    "InSynBio_CART_Design_Page.html",
    "InSynBio_Bispecific_Antibody_Design_Page.html",
]


def process(content):
    # 1) Remove language switcher CSS
    content = re.sub(
        r"\.lang-switch \{[^}]+\}\s*\.lang-switch button[^}]+\}[^}]*\}\s*body\[data-lang=\"zh\"\] \.lang-en \{ display: none !important; \}\s*body\[data-lang=\"en\"\] \.lang-zh \{ display: none !important; \}\s*",
        "",
        content,
        flags=re.DOTALL,
    )
    # Fallback: remove line by line if block not found
    content = re.sub(r"\.lang-switch \{[^}]+\}", "", content)
    content = re.sub(r"\.lang-switch button[^{]+\{[^}]+\}", "", content)
    content = re.sub(r"\.lang-switch button\.active[^{]+\{[^}]+\}", "", content)
    content = re.sub(r'body\[data-lang="zh"\] \.lang-en \{ display: none !important; \}', "", content)
    content = re.sub(r'body\[data-lang="en"\] \.lang-zh \{ display: none !important; \}', "", content)

    # 2) Remove the lang-switch div (EN/ZH buttons)
    content = re.sub(
        r'<div class="header-right">\s*<div class="lang-switch">.*?</div>\s*</div>',
        '<div class="header-right"></div>',
        content,
        flags=re.DOTALL,
    )
    # If header-right is now empty, remove it for cleaner HTML
    content = re.sub(r'<div class="header-right">\s*</div>', "", content)

    # 3) Remove any span with lang-zh (e.g. lang-zh or slogan lang-zh)
    content = re.sub(r'<span class="[^"]*lang-zh[^"]*">.*?</span>', "", content, flags=re.DOTALL)

    # 3b) Keep slogan styling: slogan lang-en -> slogan
    content = content.replace(' class="slogan lang-en"', ' class="slogan"')

    # 4) Unwrap any span with lang-en: <span class="...lang-en...">X</span> -> X
    content = re.sub(r'<span class="[^"]*lang-en[^"]*">(.*?)</span>', r"\1", content, flags=re.DOTALL)

    # 5) Remove Chinese paragraphs/blocks and blocks
    content = re.sub(r'<p class="[^"]*lang-zh[^"]*">.*?</p>', "", content, flags=re.DOTALL)
    content = re.sub(r'<h3 class="lang-zh">.*?</h3>', "", content, flags=re.DOTALL)
    content = re.sub(r'<ul class="lang-zh">.*?</ul>', "", content, flags=re.DOTALL)
    content = re.sub(r'<span class="section-label lang-zh">[^<]*</span>', "", content)
    content = re.sub(r'<span class="label lang-zh">[^<]*</span>', "", content)
    content = re.sub(r'<p class="hint lang-zh"[^>]*>.*?</p>', "", content, flags=re.DOTALL)

    # 5b) Strip lang-en from remaining tags (h3, ul, p, etc.)
    content = re.sub(r'<h3 class="lang-en">', "<h3>", content)
    content = re.sub(r'<ul class="lang-en">', "<ul>", content)
    content = re.sub(r'<p class="subtitle lang-en">', '<p class="subtitle">', content)
    content = re.sub(r'<p class="disclaimer lang-en">', '<p class="disclaimer">', content)
    content = re.sub(r'<p class="input-note lang-en">', '<p class="input-note">', content)
    content = re.sub(r'<p class="hint lang-en"', '<p class="hint"', content)
    content = re.sub(r'<p class="lang-en"', '<p ', content)

    # 6) Change English-only tags to plain (no class)
    content = re.sub(r'<p class="lang-en([^"]*)">', "<p>", content)
    content = re.sub(r'<span class="section-label lang-en">', '<span class="section-label">', content)
    content = re.sub(r'<span class="label lang-en">', '<span class="label">', content)
    content = re.sub(r'<p class="hint lang-en">', "<p class=\"hint\">", content)
    content = re.sub(r'<p class="([^"]*)\s+lang-en\s+([^"]*)">', r'<p class="\1 \2">', content)
    content = re.sub(r'<p class="lang-en\s+([^"]*)">', r'<p class="\1">', content)
    content = re.sub(r'<p class="workflow-subtitle lang-en"', '<p class="workflow-subtitle"', content)

    # 7) Remove the insynbio-lang JavaScript block
    content = re.sub(
        r"\(function\(\) \{\s*const KEY = 'insynbio-lang';[\s\S]*?\}\)\(\);",
        "",
        content,
    )

    # 8) Ensure body stays en (optional, already en)
    content = content.replace('data-lang="zh"', 'data-lang="en"')

    # Clean up empty lines
    content = re.sub(r"\n\s*\n\s*\n", "\n\n", content)
    return content


def main():
    for name in FILES:
        path = os.path.join(DOCS, name)
        if not os.path.isfile(path):
            print("Skip (not found):", name)
            continue
        with open(path, "r", encoding="utf-8") as f:
            text = f.read()
        out = process(text)
        with open(path, "w", encoding="utf-8") as f:
            f.write(out)
        print("OK:", name)


if __name__ == "__main__":
    main()
