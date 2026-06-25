import os
import glob

html_files = glob.glob("docs/Therasik_*.html") + ["docs/therasik_index.html"]

for file in html_files:
    with open(file, "r", encoding="utf-8") as f:
        content = f.read()

    # Ensure "Thera sik" spacing in brand
    if '<span style="color:#111827">Thera</span><span class="accent">sik</span>' in content:
        content = content.replace(
            '<span style="color:#111827">Thera</span><span class="accent">sik</span>',
            '<span style="color:#111827">Thera</span> <span class="accent">sik</span>'
        )
        with open(file, "w", encoding="utf-8") as f:
            f.write(content)
        print(f"Fixed brand spacing in {file}")
