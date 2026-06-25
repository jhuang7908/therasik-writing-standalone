import os, re

BASE = r"D:\InSynBio-AI-Research\Antibody_Engineer_Suite\insynbio-web-source"

NEW_LOGO = """<svg width="34" height="28" viewBox="0 0 32 30" fill="none" xmlns="http://www.w3.org/2000/svg" style="flex-shrink:0;">
          <path d="M16 2L2 10V22L16 28L30 22V10L16 2Z" fill="#0d9488" fill-opacity="0.06" stroke="#0d9488" stroke-width="1.5" stroke-opacity="0.5"/>
          <path d="M16 18V25" stroke="#0d9488" stroke-width="2.5" stroke-linecap="round"/>
          <path d="M14.5 14.5L8 8" stroke="#0d9488" stroke-width="2.5" stroke-linecap="round"/>
          <path d="M11.5 13.5L5.5 7.5" stroke="#2dd4bf" stroke-width="2" stroke-linecap="round"/>
          <path d="M17.5 14.5L24 8" stroke="#0d9488" stroke-width="2.5" stroke-linecap="round"/>
          <circle cx="8" cy="8" r="2" fill="#0d9488"/>
          <circle cx="5.5" cy="7.5" r="1.5" fill="#2dd4bf"/>
          <rect x="22" y="5" width="5" height="5" rx="1" fill="#f59e0b" transform="rotate(45 24.5 7.5)"/>
          <circle cx="16" cy="16" r="2.5" fill="white" stroke="#0d9488" stroke-width="2"/>
        </svg>"""

# Match any SVG that is the old logo. The old logo has viewBox="0 0 32 30" and contains specific paths.
# Let's just replace the SVG block that follows the <a href="index.html" ...>
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
