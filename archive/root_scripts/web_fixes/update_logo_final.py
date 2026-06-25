import os, re

BASE = r"D:\InSynBio-AI-Research\Antibody_Engineer_Suite\insynbio-web-source"

NEW_LOGO = """<svg width="34" height="28" viewBox="0 0 32 30" fill="none" xmlns="http://www.w3.org/2000/svg" style="flex-shrink:0;">
          <path d="M16 2L2 10V22L16 28L30 22V10L16 2Z" fill="#0d9488" fill-opacity="0.05" stroke="#0d9488" stroke-width="1" stroke-opacity="0.3"/>
          <path d="M14.5 24 V 16" stroke="#0d9488" stroke-width="2.5" stroke-linecap="round"/>
          <path d="M17.5 24 V 16" stroke="#f59e0b" stroke-width="2.5" stroke-linecap="round"/>
          <line x1="13" y1="19" x2="19" y2="19" stroke="#9ca3af" stroke-width="1.5" stroke-linecap="round"/>
          <line x1="13" y1="21" x2="19" y2="21" stroke="#9ca3af" stroke-width="1.5" stroke-linecap="round"/>
          <path d="M14.5 16 L 8 7" stroke="#0d9488" stroke-width="2.5" stroke-linecap="round"/>
          <path d="M10 16 L 3.5 7" stroke="#2dd4bf" stroke-width="2.5" stroke-linecap="round"/>
          <path d="M17.5 16 L 24 7" stroke="#f59e0b" stroke-width="2.5" stroke-linecap="round"/>
          <rect x="21.5" y="3.5" width="5" height="5" rx="1" fill="#f59e0b" transform="rotate(45 24 6)"/>
        </svg>"""

PATTERN = re.compile(
    r'(<a href="index\.html"[^>]*>\s*)<svg[^>]*viewBox="0 0 32 30"[^>]*>.*?</svg>',
    re.DOTALL
)

count = 0
for fname in os.listdir(BASE):
    if fname.endswith(".html"):
        path = os.path.join(BASE, fname)
        with open(path, "r", encoding="utf-8") as f:
            content = f.read()
        
        new_content = PATTERN.sub(r'\1' + NEW_LOGO, content)
        if new_content != content:
            with open(path, "w", encoding="utf-8") as f:
                f.write(new_content)
            print(f"Updated logo in {fname}")
            count += 1

print(f"Total files updated: {count}")
