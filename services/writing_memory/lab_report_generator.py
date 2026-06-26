"""
Lab experiment report — HTML mini-paper generation.

Two-stage pipeline (when API key present): reasoning outline → prose HTML.
No vendor/model names in client-visible output.
"""

from __future__ import annotations

import html as html_lib
import os
import re
import time
from typing import Any

from openai import OpenAI

_REASONER = os.environ.get("DEEPSEEK_REASONER_MODEL", "deepseek-reasoner")
_CHAT = os.environ.get("DEEPSEEK_REPORT_MODEL", "deepseek-chat")
_BASE = os.environ.get("DEEPSEEK_BASE_URL", "https://api.deepseek.com/v1").rstrip("/")

_PLAN_SYSTEM = (
    "You are a principal investigator planning a short laboratory report (mini-paper). "
    "From raw notes, SOP text, reagent lists, and result blocks, produce a structured "
    "OUTLINE only in plain text. Sections required:\n"
    "1. Title\n2. Abstract (3–5 sentences)\n3. Background\n"
    "4. Materials & Reagents (bullets; include supplier/catalog/lot if present)\n"
    "5. Methods (stepwise; align with SOP)\n6. Experimental Conditions "
    "(groups, times, temperatures, deviations)\n7. Results (per experimental block; "
    "use ONLY numbers from PYTHON_STATISTICS)\n8. Discussion (follow DISCUSSION_ANALYSIS "
    "verbatim in substance; no new statistics)\n9. Conclusion\n"
    "10. References (from literature digest only)\n"
    "Do not output HTML. Do not name any AI product."
)

_HTML_SYSTEM = (
    "You are a scientific editor producing a brief communication–style lab report. "
    "Convert the outline and source data into ONE HTML fragment wrapped in <article>...</article>.\n"
    "Use: section, h2, h3, p, ul, ol, table (for numeric results).\n"
    "Do NOT add <figure> tags or 'Figure N' captions that reference image filenames "
    "(.png, .csv, .xlsx) — charts are appended automatically by the laboratory system.\n"
    "Required h2 sections (exact headings):\n"
    "Abstract; Materials and Reagents; Methods; Experimental Conditions; "
    "Results; Discussion; Conclusion; References\n"
    "In References: do NOT invent PMIDs, authors, or journals. If a literature digest is "
    "provided, mention only those PMIDs in plain text; the system will replace this section "
    "with verified citations.\n"
    "Professional English. Third person. Past tense for methods/results.\n"
    "Do not mention any AI vendor, model, or API. Output ONLY the <article> fragment."
)

_HTML_SYSTEM_ZH = (
    "你是实验室简报编辑。将大纲与源数据转为一个 <article>...</article> HTML 片段。\n"
    "使用 section、h2、h3、p、ul、ol、table（数值结果用表格）。\n"
    "禁止添加 <figure> 或「图1」等引用文件名（.png、.csv、.xlsx）的说明——统计图由系统自动追加。\n"
    "必须的 h2 标题（中文）：摘要；材料与试剂；方法；实验条件；结果；讨论；结论；参考文献\n"
    "参考文献：不得编造 PMID/作者/期刊；若有文献摘要，仅提及其中 PMID；系统将替换为核验条目。\n"
    "专业简体中文，第三人称，方法与结果用过去时。\n"
    "不得提及任何 AI 产品或 API。仅输出 <article> 片段。"
)

_PLAN_SYSTEM_ZH = (
    "你是课题组负责人，规划一篇短实验室报告大纲（纯文本，非 HTML）。"
    "章节：1. 标题 2. 摘要 3. 背景 4. 材料与试剂 5. 方法 6. 实验条件 "
    "7. 结果（仅用 PYTHON_STATISTICS 中的数字）8. 讨论 9. 结论 10. 参考文献\n"
    "不得输出 HTML，不得提及 AI 产品名。"
)


def normalize_report_language(lang: str | None) -> str:
    v = (lang or "en").strip().lower()
    if v in ("zh", "zh-cn", "zh_cn", "chinese", "cn", "中文"):
        return "zh"
    return "en"


def html_system_for_language(lang: str | None) -> str:
    return _HTML_SYSTEM_ZH if normalize_report_language(lang) == "zh" else _HTML_SYSTEM


def plan_system_for_language(lang: str | None) -> str:
    return _PLAN_SYSTEM_ZH if normalize_report_language(lang) == "zh" else _PLAN_SYSTEM


def _api_key() -> str:
    return (os.environ.get("DEEPSEEK_API_KEY") or "").strip()


def _client() -> OpenAI:
    key = _api_key()
    if not key:
        raise RuntimeError("Lab report engine not configured")
    return OpenAI(api_key=key, base_url=_BASE)


def _call(model: str, system: str, user: str, *, max_tokens: int = 4096, temperature: float = 0.35) -> str:
    client = _client()
    last_err: Exception | None = None
    for attempt in range(3):
        try:
            resp = client.chat.completions.create(
                model=model,
                max_tokens=max_tokens,
                temperature=temperature,
                messages=[
                    {"role": "system", "content": system},
                    {"role": "user", "content": user},
                ],
            )
            msg = resp.choices[0].message
            text = (getattr(msg, "content", None) or "").strip()
            if text:
                return text
            time.sleep(3.0 * (attempt + 1))
        except Exception as exc:
            last_err = exc
            if attempt < 2:
                time.sleep(5.0)
    raise RuntimeError(f"Lab report engine error: {last_err}")


def _extract_article(html_fragment: str) -> str:
    m = re.search(r"<article[\s\S]*?</article>", html_fragment, re.IGNORECASE)
    if m:
        return m.group(0)
    if html_fragment.strip().startswith("<"):
        return f"<article>{html_fragment}</article>"
    # Plain paragraphs → wrap
    paras = "".join(f"<p>{html_lib.escape(p)}</p>" for p in html_fragment.split("\n\n") if p.strip())
    return f"<article>{paras}</article>"


def _build_source_bundle(
    payload: dict[str, Any],
    *,
    sop_body: str = "",
    reagents_catalog: str = "",
) -> str:
    blocks = []
    for i, b in enumerate(payload.get("result_blocks") or [], 1):
        label = (b.get("label") or f"Result {i}").strip()
        notes = (b.get("notes") or "").strip()
        files = b.get("files") or []
        fn = ", ".join(
            f.get("name", "") for f in files if isinstance(f, dict) and f.get("name")
        )
        blocks.append(f"[{label}]\n{notes or '(no notes)'}\nAttachments: {fn or 'none'}")
    return "\n\n".join([
        f"Report title: {payload.get('title', '')}",
        f"Reference SOP: {payload.get('experiment_ref', '')}",
        f"Author: {payload.get('author', '')}",
        f"QC status: {payload.get('qc_status', '')}",
        f"Background / context:\n{payload.get('observations', '')}",
        f"SOP body (methods source):\n{sop_body or '(not loaded)'}",
        f"Reagent catalog (project inventory):\n{reagents_catalog or '(not listed)'}",
        f"Draft conclusion:\n{payload.get('conclusion', '')}",
        f"PYTHON_STATISTICS (authoritative, computed before report):\n"
        f"{payload.get('statistics_analysis', '')}",
        f"DISCUSSION_ANALYSIS (use for Discussion section):\n"
        f"{payload.get('discussion_analysis', '')}",
        f"Rationality / QC analysis:\n{payload.get('rationality_analysis', '')}",
        f"Literature digest:\n{payload.get('pubmed_digest', '')}",
        "Result blocks:\n" + ("\n\n".join(blocks) or "(none)"),
    ])


def generate_report_article_html(
    payload: dict[str, Any],
    *,
    sop_body: str = "",
    reagents_catalog: str = "",
    language: str = "en",
) -> str:
    """Run outline (reasoner) + HTML body (chat); return <article> fragment."""
    lang = normalize_report_language(language)
    bundle = _build_source_bundle(payload, sop_body=sop_body, reagents_catalog=reagents_catalog)
    if lang == "zh":
        bundle += "\n\n报告语言：简体中文"
    outline = _call(
        _REASONER,
        plan_system_for_language(lang),
        bundle,
        max_tokens=3500,
        temperature=0.25,
    )
    produce = (
        "Produce the complete <article> HTML fragment now."
        if lang == "en"
        else "现在生成完整的 <article> HTML 片段。"
    )
    html_user = f"## Approved outline\n{outline}\n\n## Source data\n{bundle}\n\n{produce}"
    raw_html = _call(
        _CHAT,
        html_system_for_language(lang),
        html_user,
        max_tokens=4500,
        temperature=0.4,
    )
    return _extract_article(raw_html)


def wrap_full_html_document(
    article_html: str,
    *,
    title: str,
    author: str,
    project_id: str,
    generated_at: str,
    qc_status: str,
    experiment_ref: str,
    language: str = "en",
) -> str:
    """Full printable HTML document (browser Print → Save as PDF)."""
    lang = normalize_report_language(language)
    safe_title = html_lib.escape(title or "Laboratory Report")
    html_lang = "zh-CN" if lang == "zh" else "en"
    meta_rows = [
        ("Author", author or "—"),
        ("Project ID", project_id or "—"),
        ("Generated", generated_at or "—"),
        ("Reference SOP", experiment_ref or "—"),
        ("QC Status", qc_status or "Pending"),
    ]
    meta_table = "".join(
        f"<tr><th>{html_lib.escape(k)}</th><td>{html_lib.escape(v)}</td></tr>"
        for k, v in meta_rows
    )
    return f"""<!DOCTYPE html>
<html lang="{html_lang}">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>{safe_title}</title>
<style>
  @page {{ margin: 18mm; }}
  body {{
    font-family: "Times New Roman", Georgia, serif;
    font-size: 11pt;
    line-height: 1.45;
    color: #1a1a1a;
    max-width: 210mm;
    margin: 0 auto;
    padding: 12mm 14mm;
  }}
  header.report-masthead {{
    border-bottom: 2px solid #2c5282;
    margin-bottom: 1.2em;
    padding-bottom: 0.6em;
  }}
  header.report-masthead h1 {{
    font-size: 18pt;
    margin: 0 0 0.35em;
    line-height: 1.2;
  }}
  .report-meta {{
    width: 100%;
    font-size: 9.5pt;
    border-collapse: collapse;
    margin-top: 0.5em;
  }}
  .report-meta th {{
    text-align: left;
    padding: 3px 10px 3px 0;
    color: #4a5568;
    font-weight: 600;
    vertical-align: top;
    width: 28%;
  }}
  .report-meta td {{ padding: 3px 0; }}
  article h2 {{
    font-size: 13pt;
    margin: 1.2em 0 0.4em;
    color: #2c5282;
    border-bottom: 1px solid #cbd5e0;
    padding-bottom: 0.15em;
  }}
  article h3 {{ font-size: 11.5pt; margin: 0.8em 0 0.3em; }}
  article p {{ margin: 0.4em 0 0.6em; text-align: justify; }}
  article ul, article ol {{ margin: 0.3em 0 0.8em 1.4em; }}
  article table {{
    width: 100%;
    border-collapse: collapse;
    font-size: 10pt;
    margin: 0.6em 0;
  }}
  article th, article td {{
    border: 1px solid #a0aec0;
    padding: 5px 8px;
    text-align: left;
  }}
  article th {{ background: #edf2f7; }}
  .ref-tag {{
    font-size: 8.5pt;
    font-weight: 700;
    padding: 1px 5px;
    border-radius: 3px;
    margin-right: 4px;
  }}
  .ref-verified {{ background: #c6f6d5; color: #22543d; }}
  .ref-partial {{ background: #fefcbf; color: #744210; }}
  .ref-unverified {{ background: #fed7d7; color: #742a2a; }}
  footer.report-footer {{
    margin-top: 2em;
    padding-top: 0.6em;
    border-top: 1px solid #cbd5e0;
    font-size: 9pt;
    color: #718096;
  }}
  @media print {{
    body {{ padding: 0; }}
    a {{ color: #1a1a1a; text-decoration: none; }}
  }}
</style>
</head>
<body>
<header class="report-masthead">
  <h1>{safe_title}</h1>
  <table class="report-meta">{meta_table}</table>
</header>
{article_html}
<footer class="report-footer">
  InSynBio Lab · Experimental progress report · Use browser Print (Ctrl+P) to save as PDF.
</footer>
</body>
</html>"""
