import os
import re

files = [
    r"d:\InSynBio-AI-Research\Antibody_Engineer_Suite\insynbio-web-source\InSynBio_Pitch_Deck.html",
    r"d:\InSynBio-AI-Research\Antibody_Engineer_Suite\therasik-web-source\Therasik_Pitch_Deck.html"
]

white_css = """
/* ── Deep White Overrides ── */
.bg-white { background: #f8fafc; color: #111827; }
.bg-white h1.hero-title, .bg-white h2.slide-title, .bg-white .brand-name { color: #111827; }
.bg-white .slide-subtitle, .bg-white .brand-slogan { color: #4b5563; border-color: #cbd5e1; }
.bg-white .school-badge { color: #4b5563; border-color: #cbd5e1; background: #fff; }
.bg-white p, .bg-white li, .bg-white td { color: #4b5563 !important; }
.bg-white strong { color: #111827 !important; }
.bg-white .label-white { color: #0d9488; }
.bg-white .label-teal { color: #0d9488; }
.bg-white .data-label { color: #4b5563; }
.bg-white .data-num { color: #0d9488; }
.bg-white .compare-table th { color: #6b7280; border-bottom: 2px solid #e5e7eb; }
.bg-white .compare-table td { border-bottom: 1px solid #f1f5f9; }
.bg-white .pipe-step { background: #fff; border: 1px solid #e2e8f0; }
.bg-white .pipe-step::after { color: #9ca3af; }
.bg-white .pipe-step strong { color: #111827 !important; }
.bg-white .pipe-step span { color: #6b7280 !important; }
.bg-white .pipe-step .step-n { color: #2dd4bf; }
.bg-white .case-mini { background: #fff; border: 1px solid #e2e8f0; border-left-width: 4px; }
.bg-white .case-mini h4, .bg-white .case-mini a { color: #111827 !important; }
.bg-white .quote-box { background: #f0fdfa; border-left: 4px solid #0d9488; }
.bg-white .quote-box p { color: #0f766e !important; }
.bg-white .cta-primary { background: #0d9488; color: #fff; border: 1px solid #0d9488; }
.bg-white .cta-outline { border-color: #0d9488; color: #0d9488; }
.bg-white .cta-outline:hover { background: #f0fdfa; border-color: #0d9488; color:#0d9488;}
.bg-white .slide-num { color: #9ca3af; }
.nav-dot { background: #d1d5db; border: none; } 
.nav-dot.active { background: #0d9488; }
.bg-white .card div { color: #4b5563 !important; }
.bg-white .card div[style*="font-size:14px"] { color: #111827 !important; }
.bg-white .card div[style*="font-size:11px"] { color: #0d9488 !important; }
"""

for fpath in files:
    if os.path.exists(fpath):
        with open(fpath, "r", encoding="utf-8") as f:
            content = f.read()

        # Replace all slide backgrounds with bg-white
        content = re.sub(r'class="slide bg-[a-z-]+"', 'class="slide bg-white"', content)
        
        # Inject CSS if not there
        if "/* ── Deep White Overrides ── */" not in content:
            content = content.replace("</style>", white_css + "\n</style>")
            
        with open(fpath, "w", encoding="utf-8") as f:
            f.write(content)

print("White theme successfully applied!")
