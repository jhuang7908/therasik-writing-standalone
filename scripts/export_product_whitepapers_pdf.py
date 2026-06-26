from __future__ import annotations

import html
import re
import shutil
import subprocess
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
CN_HTML = ROOT / "therasik-web-source" / "whitepaper_therasik_cn.html"
CN_PDF = ROOT / "therasik-web-source" / "whitepaper_therasik_cn.pdf"
EN_HTML = ROOT / "Web_Projects" / "insynbio_com" / "insynbio_product_whitepaper_en.html"
EN_PDF = ROOT / "Web_Projects" / "insynbio_com" / "insynbio_product_whitepaper_en.pdf"
# Legacy thin MD→HTML export (superseded by build_insynbio_whitepaper_en.py)
EN_MD = ROOT / "Web_Projects" / "insynbio_com" / "insynbio_product_whitepaper_en.md"
EN_HTML_LEGACY = ROOT / "Web_Projects" / "insynbio_com" / "insynbio_product_whitepaper_en.print.html"


def find_browser() -> str:
    candidates = [
        r"C:\Program Files (x86)\Microsoft\Edge\Application\msedge.exe",
        r"C:\Program Files\Microsoft\Edge\Application\msedge.exe",
        r"C:\Program Files\Google\Chrome\Application\chrome.exe",
        r"C:\Program Files (x86)\Google\Chrome\Application\chrome.exe",
    ]
    for candidate in candidates:
        if Path(candidate).exists():
            return candidate
    for exe in ("msedge", "chrome", "chromium"):
        found = shutil.which(exe)
        if found:
            return found
    raise RuntimeError("No Edge/Chrome executable found for PDF export.")


def inline_markdown(text: str) -> str:
    text = html.escape(text)
    text = re.sub(r"`([^`]+)`", r"<code>\1</code>", text)
    text = re.sub(r"\*\*([^*]+)\*\*", r"<strong>\1</strong>", text)
    return text


def markdown_to_html(md: str) -> str:
    blocks: list[str] = []
    list_items: list[str] = []

    def flush_list() -> None:
        nonlocal list_items
        if list_items:
            blocks.append("<ul>\n" + "\n".join(list_items) + "\n</ul>")
            list_items = []

    for raw in md.splitlines():
        line = raw.rstrip()
        if not line:
            flush_list()
            continue
        if line.startswith("---"):
            flush_list()
            blocks.append("<hr>")
        elif line.startswith("> "):
            flush_list()
            blocks.append(f"<blockquote>{inline_markdown(line[2:].strip())}</blockquote>")
        elif line.startswith("### "):
            flush_list()
            blocks.append(f"<h3>{inline_markdown(line[4:].strip())}</h3>")
        elif line.startswith("## "):
            flush_list()
            blocks.append(f"<h2>{inline_markdown(line[3:].strip())}</h2>")
        elif line.startswith("# "):
            flush_list()
            blocks.append(f"<h1>{inline_markdown(line[2:].strip())}</h1>")
        elif line.startswith("- "):
            list_items.append(f"<li>{inline_markdown(line[2:].strip())}</li>")
        elif re.match(r"^\d+\. ", line):
            flush_list()
            blocks.append(f"<p>{inline_markdown(re.sub(r'^\\d+\\. ', '', line).strip())}</p>")
        else:
            flush_list()
            blocks.append(f"<p>{inline_markdown(line)}</p>")
    flush_list()
    return "\n".join(blocks)


def build_english_html() -> None:
    doc = """<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1.0">
  <title>InSynBio Product Whitepaper 2026</title>
  <style>
    :root {
      --t8:#115e59; --t7:#0f766e; --t6:#0d9488; --t5:#14b8a6; --t3:#99f6e4; --t1:#ccfbf1; --t0:#f0fdfa;
      --r6:#dc2626; --r1:#fee2e2; --a6:#d97706; --a0:#fffbeb; --p6:#7c3aed; --p1:#ede9fe;
      --g9:#111827; --g8:#1f2937; --g7:#1f2937; --g5:#4b5563; --g3:#d1d5db; --g1:#f9fafb; --wh:#ffffff;
    }
    * { box-sizing: border-box; -webkit-print-color-adjust: exact; print-color-adjust: exact; }
    html, body { margin: 0; background: #eefdfa; color: var(--g9); font-family: Inter, Arial, "Microsoft YaHei", sans-serif; }
    body { font-size: 12.5px; line-height: 1.55; font-weight: 500; }
    .doc { max-width: 900px; margin: 0 auto; background: #fff; }
    .pg { min-height: 1120px; padding: 34px 38px; position: relative; overflow: hidden; page-break-after: always; }
    .pg:last-child { page-break-after: auto; }
    .pg-cover { background: linear-gradient(155deg,#f0fdfa 0%,#ffffff 52%,#ecfeff 100%); }
    .pg-lt { background: var(--t0); }
    .pg-wh { background: #fff; }
    .bg-orb { position:absolute; border-radius:999px; pointer-events:none; opacity:.72; }
    .orb-a { width:360px; height:360px; left:-160px; top:-120px; background:#d9fff5; }
    .orb-b { width:420px; height:420px; right:-210px; bottom:-150px; background:#e0f2fe; }
    .brand { font-size:22px; font-weight:900; color:var(--g9); letter-spacing:-.02em; }
    .brand b { color:var(--t6); font-style:italic; }
    .topbar { display:flex; justify-content:space-between; align-items:flex-start; gap:18px; margin-bottom:26px; position:relative; z-index:2; }
    .topmeta { font-size:11px; color:var(--g5); text-align:right; line-height:1.55; font-weight:650; }
    h1 { margin:0 0 10px; color:var(--g9); font-size:38px; line-height:1.14; letter-spacing:-.04em; font-weight:900; position:relative; z-index:2; }
    h1 em { display:block; color:var(--t7); font-style:normal; font-size:28px; margin-top:8px; }
    h2 { margin:0 0 12px; color:var(--g9); font-size:23px; line-height:1.25; letter-spacing:-.02em; font-weight:900; }
    h2 em { color:var(--t6); font-style:normal; }
    h3 { margin:0 0 7px; color:var(--g9); font-size:14px; font-weight:900; }
    p { margin:0 0 10px; color:var(--g7); }
    .sub { font-size:14px; max-width:720px; color:var(--g7); position:relative; z-index:2; }
    .lbl { display:inline-flex; padding:4px 13px; border-radius:20px; background:var(--t1); color:var(--t7); font-size:10px; font-weight:900; letter-spacing:.1em; text-transform:uppercase; margin-bottom:14px; }
    .badges { display:flex; flex-wrap:wrap; gap:8px; margin:16px 0; position:relative; z-index:2; }
    .badge { display:inline-flex; border:1.5px solid var(--t3); background:#fff; color:var(--t7); border-radius:18px; padding:5px 12px; font-size:11px; font-weight:850; }
    .cards3 { display:grid; grid-template-columns:repeat(3,1fr); gap:12px; margin:18px 0; position:relative; z-index:2; }
    .cards4 { display:grid; grid-template-columns:repeat(4,1fr); gap:10px; margin:16px 0; position:relative; z-index:2; }
    .cards2 { display:grid; grid-template-columns:repeat(2,1fr); gap:12px; margin:16px 0; position:relative; z-index:2; }
    .card { background:#fff; border:1.5px solid var(--t3); border-radius:13px; padding:14px 14px; box-shadow:0 2px 9px rgba(13,148,136,.07); }
    .card strong { color:var(--t7); }
    .card .k { color:var(--t7); font-size:15px; font-weight:900; margin-bottom:4px; }
    .card .d { color:var(--g7); font-size:11.5px; line-height:1.48; }
    .metric { text-align:center; padding:12px 8px; }
    .metric .n { display:block; color:var(--t6); font-size:20px; font-weight:950; line-height:1; }
    .metric .l { display:block; color:var(--g7); font-size:10.5px; line-height:1.35; margin-top:5px; font-weight:650; }
    .callout { position:relative; z-index:2; background:#fff; border:2px solid var(--t5); border-radius:12px; padding:13px 16px; color:var(--t8); font-weight:800; margin:16px 0; }
    .layer { display:flex; gap:12px; margin:0 0 9px; align-items:stretch; }
    .num { width:30px; height:30px; border-radius:50%; background:var(--t6); color:#fff; display:flex; align-items:center; justify-content:center; font-weight:900; flex-shrink:0; margin-top:10px; }
    .layerbox { flex:1; background:#fff; border:1.5px solid var(--t3); border-radius:11px; padding:12px 15px; }
    .layerbox .title { font-size:13px; font-weight:900; color:var(--t7); margin-bottom:4px; }
    .layerbox .desc { font-size:11.5px; color:var(--g7); line-height:1.5; }
    .tags { display:flex; flex-wrap:wrap; gap:5px; margin-top:8px; }
    .tag { font-size:9px; font-weight:850; color:#fff; background:var(--t6); border-radius:6px; padding:2px 7px; }
    .tag.r { background:var(--r6); }
    .tag.a { background:var(--a6); }
    .tag.p { background:var(--p6); }
    .svc { background:#fff; border:1.5px solid var(--t3); border-radius:12px; padding:14px; min-height:124px; }
    .svc h3 { color:var(--t7); }
    .svc ul { margin:6px 0 0 17px; padding:0; color:var(--g7); font-size:11.5px; line-height:1.45; }
    .diff { background:#fff; border:1.5px solid var(--g3); border-radius:12px; padding:13px; }
    .diff .idx { color:var(--t6); font-size:22px; font-weight:950; line-height:1; }
    .diff .title { color:var(--g9); font-weight:900; margin:3px 0 5px; }
    .diff .desc { color:var(--g7); font-size:11.5px; line-height:1.5; }
    .contact { display:grid; grid-template-columns:repeat(3,1fr); gap:10px; margin-top:20px; }
    .contact .card { text-align:center; }
    .contact .v { font-size:15px; color:var(--g9); font-weight:900; }
    .footnote { font-size:10.5px; color:var(--g5); margin-top:14px; }
    @media print {
      @page { size:A4 portrait; margin:12mm 10mm; }
      body { background:#fff; color:#111827 !important; }
      .doc { max-width:100%; }
      .pg { min-height:auto; padding:22px 26px; }
      p, li, .d, .desc, .diff .desc { color:#111827 !important; font-weight:500; }
      .pg, .pg * { text-shadow:none !important; }
    }
  </style>
</head>
<body>
<div class="doc">

<section class="pg pg-cover">
  <div class="bg-orb orb-a"></div><div class="bg-orb orb-b"></div>
  <div class="topbar">
    <div class="brand">In<b>Syn</b>Bio <span style="font-size:12px;color:var(--g5);font-weight:600;margin-left:8px;">Product Whitepaper 2026</span></div>
    <div class="topmeta">www.insynbio.com · console.insynbio.com<br>contact@insynbio.com</div>
  </div>
  <h1>Clinical Drug AI Design Engine<em>for Antibody and Cell-Therapy Programs</em></h1>
  <p class="sub">InSynBio does not position AI as a replacement for wet-lab work. The platform reduces experimental uncertainty before synthesis, expression, and validation begin.</p>
  <div class="badges">
    <span class="badge">Online Console</span><span class="badge">Expert Service</span><span class="badge">Customer-Safe AI Agent</span>
  </div>
  <div class="cards3">
    <div class="card"><div class="k">Reduce Blind Screening</div><div class="d">Prioritize high-rationale candidates before expensive wet-lab validation begins.</div></div>
    <div class="card"><div class="k">Improve R&D Efficiency</div><div class="d">Move from broad trial-and-error to clinically grounded, structure-aware design decisions.</div></div>
    <div class="card"><div class="k">Strengthen Preclinical Readiness</div><div class="d">Use clinical developability benchmarks and intelligent optimization to expose risk earlier.</div></div>
  </div>
  <div class="callout">Core position: AI should not make experiments disappear. It should help every experiment start with a clearer rationale.</div>
  <div class="cards4">
    <div class="card metric"><span class="n">Structure</span><span class="l">Humanization beyond sequence similarity</span></div>
    <div class="card metric"><span class="n">Benchmark</span><span class="l">Near-thousand clinical antibodies · 30+ indices</span></div>
    <div class="card metric"><span class="n">Optimize</span><span class="l">Risk-to-action intelligent optimization</span></div>
    <div class="card metric"><span class="n">Agent</span><span class="l">Safe expert guidance and report interpretation</span></div>
  </div>
</section>

<section class="pg pg-lt">
  <div class="lbl">01 · Platform Architecture</div>
  <h2>Five-Layer AI Design Workflow <em>Built Around Clinical Antibody Behavior</em></h2>
  <p>InSynBio is not a single-purpose prediction page. It is a layered design workflow that connects clinical pattern learning, structure-aware engineering, candidate design, developability interpretation, and customer-safe AI guidance.</p>
  <div class="layer"><div class="num">1</div><div class="layerbox"><div class="title">Clinical Pattern Learning Layer</div><div class="desc">Clinical-stage and approved biologics provide the practical reference space. Candidate sequences are interpreted in the context of clinical antibody behavior and format-specific constraints.</div><div class="tags"><span class="tag">Clinical behavior</span><span class="tag">Format context</span></div></div></div>
  <div class="layer"><div class="num">2</div><div class="layerbox"><div class="title">Structure-Aware Engineering Layer</div><div class="desc">Humanization, VHH design, and VH-to-VHH conversion are evaluated through binding-loop geometry, variable-domain architecture, pairing compatibility, and framework support.</div><div class="tags"><span class="tag">CDR preservation</span><span class="tag">Fv architecture</span></div></div></div>
  <div class="layer"><div class="num">3</div><div class="layerbox"><div class="title">Candidate Design Layer</div><div class="desc">The system converts broad search into focused design directions for antibody humanization, VHH engineering, multispecific formats, and Smart CAR-T / CAR-M concepts.</div><div class="tags"><span class="tag a">Focused candidates</span><span class="tag a">Format guidance</span></div></div></div>
  <div class="layer"><div class="num">4</div><div class="layerbox"><div class="title">Developability and Immunogenicity Layer</div><div class="desc">CMC and immunogenicity are interpreted as a balancing problem, not a single score. The report identifies risk categories and recommends practical next validation steps.</div><div class="tags"><span class="tag r">CMC balance</span><span class="tag r">Risk categories</span></div></div></div>
  <div class="layer"><div class="num">5</div><div class="layerbox"><div class="title">AI Agent and Report Interpretation Layer</div><div class="desc">The console AI Agent explains reports, structural concerns, CMC risk, multispecific design orientation, and validation routes without exposing backend implementation details.</div><div class="tags"><span class="tag p">Safe answers</span><span class="tag p">Next actions</span></div></div></div>
</section>

<section class="pg pg-wh">
  <div class="lbl">02 · Underestimated Core Technology</div>
  <h2>Clinical Antibody Developability Benchmark <em>Plus Intelligent Optimization</em></h2>
  <p>One of InSynBio's most important technologies is its clinical antibody developability benchmark system. InSynBio has evaluated a near-thousand-scale clinical antibody collection across more than 30 developability-related indices, using this as a practical reference ruler for humanized antibody candidates and engineered biologics.</p>
  <div class="cards2">
    <div class="card"><div class="k">Why It Matters</div><div class="d">Humanization is not complete when a sequence looks more human. A humanized candidate must also remain structurally plausible, manufacturable, stable enough for development, and compatible with downstream CMC expectations.</div></div>
    <div class="card"><div class="k">Benchmark Question</div><div class="d">Does this humanized candidate look developable when compared with clinical antibody behavior across multiple CMC-relevant dimensions?</div></div>
  </div>
  <div class="cards4">
    <div class="card metric"><span class="n">Charge</span><span class="l">pI and charge distribution</span></div>
    <div class="card metric"><span class="n">Surface</span><span class="l">Hydrophobic exposure and aggregation tendency</span></div>
    <div class="card metric"><span class="n">Liability</span><span class="l">Chemical motifs, glycosylation, free cysteine concerns</span></div>
    <div class="card metric"><span class="n">Format</span><span class="l">Format-dependent developability pressure</span></div>
  </div>
  <div class="callout">This benchmark is not used as a single black-box score. It supports multi-index interpretation and customer-facing engineering action.</div>
  <div class="cards2">
    <div class="card"><div class="k">Intelligent Optimization System</div><div class="d">Risk detection is translated into prioritized engineering directions. The platform favors conservative corrections that improve manufacturability signals while preserving binding-region integrity.</div></div>
    <div class="card"><div class="k">Conservative Design Principle</div><div class="d">Correct developability risks where possible without disturbing antigen-binding loops. Candidate ranking is based on engineering balance, not a single number.</div></div>
  </div>
</section>

<section class="pg pg-lt">
  <div class="lbl">03 · Product Modules</div>
  <h2>Online AI Workflows and Expert Services <em>Across Biotherapeutic Design</em></h2>
  <div class="cards3">
    <div class="svc"><h3>Antibody Humanization</h3><ul><li>Structure-aware VH/VL humanization</li><li>CDR preservation-oriented design</li><li>Developability review after humanization</li></ul></div>
    <div class="svc"><h3>VHH Humanization</h3><ul><li>Single-domain stability interpretation</li><li>Hydrophobic exposure and CDR length review</li><li>Humanization direction and CMC plausibility</li></ul></div>
    <div class="svc"><h3>VH-to-VHH Engineering</h3><ul><li>Miniaturization for multispecific and CAR formats</li><li>Autonomous-domain compatibility</li><li>Surface and framework adaptation</li></ul></div>
    <div class="svc"><h3>CMC Developability</h3><ul><li>30+ index clinical benchmark interpretation</li><li>Multi-risk balancing, not single scoring</li><li>Optimization and validation guidance</li></ul></div>
    <div class="svc"><h3>Multispecific Design</h3><ul><li>Target-pair and mechanism orientation</li><li>Format, valency, linker, and geometry guidance</li><li>Pairing and developability risk review</li></ul></div>
    <div class="svc"><h3>Smart CAR-T / CAR-M</h3><ul><li>Disease-context architecture planning</li><li>Binder suitability and cell-platform fit</li><li>Validation strategy orientation</li></ul></div>
  </div>
  <div class="callout">The online console supports fast evaluation and report interpretation. Expert services support deeper design projects, project-specific interpretation, and wet-lab planning.</div>
</section>

<section class="pg pg-wh">
  <div class="lbl">04 · Differentiation and Access</div>
  <h2>What Makes InSynBio Different</h2>
  <div class="cards4">
    <div class="diff"><div class="idx">01</div><div class="title">Clinical Reference Space</div><div class="desc">Clinical antibody behavior is used as the practical design reference, rather than treating each sequence in isolation.</div></div>
    <div class="diff"><div class="idx">02</div><div class="title">Structure-Aware Humanization</div><div class="desc">Humanized candidates are evaluated against structure and developability, not sequence similarity alone.</div></div>
    <div class="diff"><div class="idx">03</div><div class="title">Developability Yardstick</div><div class="desc">CMC risk is interpreted through a near-thousand-scale clinical antibody benchmark across 30+ indices.</div></div>
    <div class="diff"><div class="idx">04</div><div class="title">Intelligent Optimization</div><div class="desc">Risk detection is translated into practical engineering directions and next-step validation logic.</div></div>
    <div class="diff"><div class="idx">05</div><div class="title">Shared Design Philosophy</div><div class="desc">Antibody, VHH, multispecific, and CAR-related workflows share consistent structure and CMC principles.</div></div>
    <div class="diff"><div class="idx">06</div><div class="title">Safe AI Agent</div><div class="desc">Customers receive conclusions, risk explanations, recommended actions, and validation routes without proprietary backend disclosure.</div></div>
    <div class="diff"><div class="idx">07</div><div class="title">Online + Expert Track</div><div class="desc">Early-stage teams can begin with the console and escalate to expert-supported project work when needed.</div></div>
    <div class="diff"><div class="idx">08</div><div class="title">Wet-Lab Focus</div><div class="desc">The platform is designed to make experiments more focused, not to replace experimental validation.</div></div>
  </div>
  <div class="contact">
    <div class="card"><div class="k">Console</div><div class="v">console.insynbio.com</div></div>
    <div class="card"><div class="k">Website</div><div class="v">www.insynbio.com</div></div>
    <div class="card"><div class="k">Email</div><div class="v">contact@insynbio.com</div></div>
  </div>
  <p class="footnote">AI-assisted design outputs are intended for research planning and candidate prioritization. They do not replace wet-lab validation, clinical studies, regulatory review, or final development decisions.</p>
</section>

</div>
</body>
</html>"""
    EN_HTML.write_text(doc, encoding="utf-8")


def export_pdf(browser: str, src: Path, out: Path) -> None:
    out.parent.mkdir(parents=True, exist_ok=True)
    url = src.resolve().as_uri()
    cmd = [
        browser,
        "--headless",
        "--disable-gpu",
        "--no-pdf-header-footer",
        "--print-to-pdf-no-header",
        f"--print-to-pdf={out}",
        url,
    ]
    subprocess.run(cmd, check=True)


def main() -> None:
    browser = find_browser()
    # Full EN whitepaper (same section density as Therasik CN HTML)
    build_en = ROOT / "scripts" / "build_insynbio_whitepaper_en.py"
    subprocess.run([sys.executable, str(build_en)], check=True)
    export_pdf(browser, CN_HTML, CN_PDF)
    export_pdf(browser, EN_HTML, EN_PDF)
    print(f"Chinese PDF: {CN_PDF}")
    print(f"English PDF: {EN_PDF}")
    print("PDF export uses headless browser flags that suppress URL/path headers and footers.")


if __name__ == "__main__":
    main()
