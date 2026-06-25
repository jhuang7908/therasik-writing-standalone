import os
import re

files = [
    r"d:\InSynBio-AI-Research\Antibody_Engineer_Suite\insynbio-web-source\InSynBio_Pitch_Deck.html",
    r"d:\InSynBio-AI-Research\Antibody_Engineer_Suite\therasik-web-source\Therasik_Pitch_Deck.html"
]

for fpath in files:
    if os.path.exists(fpath):
        with open(fpath, "r", encoding="utf-8") as f:
            content = f.read

        # 1. Restore the original alternating deep backgrounds based on slide id
        def repl_bg(m):
            sid = int(m.group(1))
            val = (sid - 1) % 3
            bg_class = "bg-gradient"
            if val == 1: bg_class = "bg-deep"
            if val == 2: bg_class = "bg-dark"
            return f'<section class="slide {bg_class}" id="s{sid}">'
        
        content = re.sub(r'<section class="slide bg-white" id="s(\d+)">', repl_bg, content)

        # 2. Modify the Deep White Overrides to strictly apply ONLY when body has .mode-light class
        content = content.replace(".bg-white", "body.mode-light")
        content = content.replace("body.mode-light {", "body.mode-light .slide {")

        # 3. Inject Toggle Button HTML
        toggle_btn_en = """<button id="themeToggle" onclick="document.body.classList.toggle('mode-light')" style="position:fixed;top:20px;right:20px;z-index:9999;padding:8px 14px;border-radius:20px;background:rgba(255,255,255,0.1);border:1px solid rgba(255,255,255,0.2);color:#9ca3af;cursor:pointer;font-family:'Inter',sans-serif;font-weight:600;font-size:12px;backdrop-filter:blur(4px);transition:all 0.3s;">🌓 Theme Switch</button>"""
        
        toggle_btn_zh = """<button id="themeToggle" onclick="document.body.classList.toggle('mode-light')" style="position:fixed;top:20px;right:20px;z-index:9999;padding:8px 14px;border-radius:20px;background:rgba(255,255,255,0.1);border:1px solid rgba(255,255,255,0.2);color:#9ca3af;cursor:pointer;font-family:'Inter',sans-serif;font-weight:600;font-size:12px;backdrop-filter:blur(4px);transition:all 0.3s;">🌓 /</button>"""
        
        btn_html = toggle_btn_zh if "therasik" in fpath else toggle_btn_en
        
        if '<button id="themeToggle"' not in content:
            content = content.replace('<body>\n', f'<body>\n\n{btn_html}\n')

        # To ensure the button is visible in both modes, we add a quick css rule to the existing overrides
        if "body.mode-light #themeToggle" not in content:
            content = content.replace("</style>", "body.mode-light #themeToggle { background:#f1f5f9; border-color:#cbd5e1; color:#0d9488; }\n</style>")
            
        with open(fpath, "w", encoding="utf-8") as f:
            f.write(content)

print("Theme toggle successfully injected!")
