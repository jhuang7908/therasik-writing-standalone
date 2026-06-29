"""
social_content.py — Generate XHS + WeChat content from article.

Pipeline: DeepSeek planner/writer → Kimi text fact reviewer → DeepSeek fixer → format validator
Note: Image audit = Gemini Vision only (see config/pipeline_rules.yaml)
Output:   social.json  conforming to 03_format_spec_v2.md
"""

import os, sys, json, re
from pathlib import Path

# ── Load .env ────────────────────────────────────────────────────────────────
ROOT = Path(__file__).parent.parent
for _env in [ROOT / "content_generation_tools" / ".env", ROOT / ".env"]:
    if _env.exists():
        for _l in _env.read_text(encoding="utf-8").splitlines():
            _l = _l.strip()
            if _l and not _l.startswith("#") and "=" in _l:
                _k, _v = _l.split("=", 1)
                os.environ.setdefault(_k.strip(), _v.strip())
        break

SPEC = (ROOT / "content_generation_tools" / "social_content_prompts" / "03_format_spec_v2.md"
        ).read_text(encoding="utf-8")

SYSTEM_PROMPT = """你是生物医药媒体内容策划（DeepSeek Writer）。面向小红书与微信公众号，不是论文投稿。

## 任务
阅读【主线文献全文】，每周只讲一个故事。产出事实约束的内容 SSOT，拆成两平台 JSON。
正文数据仅来自主线全文；文末可列 2–3 篇关联参考文献（延伸阅读，不作第二故事线）。

## 品牌
内容末尾统一加「未来模式生物科技 · NextVivo Biotech——专注人源化动物模型与药物评估」。

## 平台格式规范
""" + SPEC + """

## 规则
1. 禁止编造数字、样本量、疗效结论。
2. 原文未写明 → 删除或标注「原文未明确」。
3. JSON 字符串内禁止 ASCII 双引号，用「」。
4. 填写 format_annotation 并如实列出 violations（空则为 []）。
5. 只输出一个 JSON 对象，无 markdown 代码块。
6. 受众：**国内**科研、CRO、药企临床前团队；公众号需写 `cover_digest`（50–120 字，与本期内容相关，作外链摘要）。
"""

USER_TEMPLATE = """请根据以下【本周唯一主线文献】撰写社交媒体内容 SSOT（小红书 + 微信公众号）。

## 叙事要求
- 只讲一个故事：本篇主线文献。
- 所有数字、结论必须能在「全文」中找到依据。
- 关联文献仅放在延伸阅读/参考文献区，不要写成并列主故事。

主线文献：
标题：{title}
作者：{authors}
期刊：{journal} ({year})
PMID：{pmid}  PMCID：{pmcid}  DOI：{doi}
URL：{url}

摘要：
{abstract}

全文：
{full_text}

关联参考文献（延伸阅读，非主线）：
{related_references}

输出 format_version: v2.0，同时包含 xiaohongshu 和 wechat 两个顶层字段。
在 wechat 末尾和 xiaohongshu 最后一张卡片附上主线 PMID/DOI 及关联文献列表。"""


def _call_llm(prompt: str, system: str, max_tokens: int = 4000) -> str:
    """Writer: DeepSeek → Kimi → Gemini fallback on balance/API errors."""
    from openai import OpenAI

    writers = [
        ("deepseek", "deepseek-chat",
         os.environ.get("DEEPSEEK_API_KEY", ""), "https://api.deepseek.com"),
        ("kimi", "moonshot-v1-32k",
         os.environ.get("KIMI_API_KEY", ""), "https://api.moonshot.cn/v1"),
        ("gemini", "gemini-2.5-flash",
         os.environ.get("GEMINI_API_KEY", ""),
         os.environ.get("GEMINI_BASE_URL", "https://generativelanguage.googleapis.com/v1beta/openai")),
    ]
    last_err = None
    for name, model, key, base in writers:
        if not key:
            continue
        try:
            client = OpenAI(api_key=key, base_url=base)
            resp = client.chat.completions.create(
                model=model,
                messages=[{"role": "system", "content": system},
                          {"role": "user",   "content": prompt}],
                max_tokens=max_tokens,
                temperature=0.7,
            )
            print(f"  Writer: {name}")
            return resp.choices[0].message.content.strip()
        except Exception as e:
            print(f"  [WARN] {name} writer failed: {e}")
            last_err = e
    raise RuntimeError(f"All writers failed. Last error: {last_err}")


def _call_deepseek(prompt: str, system: str, max_tokens: int = 4000) -> str:
    return _call_llm(prompt, system, max_tokens)


def _call_kimi(draft_json: str, article_abstract: str) -> str:
    """Kimi fact-checks the draft against the article abstract."""
    from openai import OpenAI
    client = OpenAI(
        api_key=os.environ.get("KIMI_API_KEY", ""),
        base_url="https://api.moonshot.cn/v1",
    )
    prompt = f"""你是事实核查员。原文摘要如下：

{article_abstract}

请核查以下社交媒体 JSON 草稿中的所有数字、结论和声明，对照原文：
- 列出所有「不符事实」或「原文未支持」的条目
- 对每个问题写出修改建议
- 如果全部符合，回复「FACT_CHECK_PASS」

草稿 JSON（部分）：
{draft_json[:3000]}

用 JSON 格式回复：{{"pass": true/false, "issues": [{{"path": "...", "problem": "...", "fix": "..."}}]}}"""

    resp = client.chat.completions.create(
        model="moonshot-v1-8k",
        messages=[{"role": "user", "content": prompt}],
        max_tokens=1500,
        temperature=0.2,
    )
    return resp.choices[0].message.content.strip()


def _fix_with_deepseek(draft_json: str, kimi_report: str) -> str:
    """Apply Kimi's corrections via DeepSeek."""
    prompt = f"""根据以下事实核查报告修正 JSON。仅修正报告中指出的问题，其他内容保持不变。
只输出修正后的完整 JSON，无其他文字。

事实核查报告：
{kimi_report}

原始 JSON：
{draft_json}"""
    return _call_deepseek(prompt, "你是 JSON 编辑器，只输出修正后的 JSON，无其他内容。", max_tokens=5000)


def _validate(data: dict) -> list[str]:
    """Basic format validation. Returns list of violation strings."""
    violations = []
    xhs = data.get("xiaohongshu", {})
    wx  = data.get("wechat", {})

    # XHS checks
    cards = xhs.get("cards", [])
    if len(cards) != 6:
        violations.append(f"XHS: cards count={len(cards)}, expected 6")
    for i, c in enumerate(cards, 1):
        body = c.get("body", "")
        if not (40 <= len(body) <= 80):
            violations.append(f"XHS card {i} body length={len(body)}, expected 40-80")
    tags = xhs.get("tags", [])
    if len(tags) != 6:
        violations.append(f"XHS: tags count={len(tags)}, expected 6")
    body_len = len(xhs.get("body", ""))
    if not (400 <= body_len <= 600):
        violations.append(f"XHS body length={body_len}, expected 400-600")

    # WeChat checks
    sections = wx.get("sections", [])
    if len(sections) != 5:
        violations.append(f"WeChat: sections count={len(sections)}, expected 5")
    lead_len = len(wx.get("lead", ""))
    if not (100 <= lead_len <= 150):
        violations.append(f"WeChat lead length={lead_len}, expected 100-150")
    digest_len = len(wx.get("cover_digest", ""))
    if digest_len and not (50 <= digest_len <= 120):
        violations.append(f"WeChat cover_digest length={digest_len}, expected 50-120")

    return violations


def _clean_json(raw: str) -> str:
    """Strip markdown fences and extract JSON object."""
    raw = raw.strip()
    if raw.startswith("```"):
        lines = raw.split("\n")
        raw = "\n".join(lines[1:])
        if "```" in raw:
            raw = raw[:raw.rfind("```")]
    # Find first { to last }
    start = raw.find("{")
    end   = raw.rfind("}") + 1
    if start >= 0 and end > start:
        raw = raw[start:end]
    return raw.strip()


def _article_for_prompt(article: dict) -> dict:
    """Build prompt fields; truncate full text for token budget."""
    full = article.get("full_text") or article.get("abstract", "")
    related = article.get("related_references", [])
    return {
        **article,
        "pmcid": article.get("pmcid", "N/A"),
        "full_text": full[:20000],
        "related_references": json.dumps(related, ensure_ascii=False, indent=2),
    }


def generate_social_content(
    article: dict,
    out_path: Path,
    *,
    system_prompt: str | None = None,
    ad_bar_config: Path | None = None,
) -> dict:
    """Full pipeline: write → fact-check → fix → validate → save."""
    print("=== Social Content Pipeline ===")
    if not article.get("full_text"):
        print("  [WARN] No full_text on article; falling back to abstract only")

    prompt = system_prompt or SYSTEM_PROMPT

    # Stage 1: DeepSeek write
    print("  [1/3] DeepSeek writing...")
    user_msg = USER_TEMPLATE.format(**_article_for_prompt(article))
    raw = _call_deepseek(user_msg, prompt, max_tokens=5000)
    raw = _clean_json(raw)

    try:
        data = json.loads(raw)
    except Exception as e:
        print(f"  [WARN] Initial JSON parse failed: {e}")
        print(f"  Raw preview: {raw[:200]}")
        data = {}

    # Stage 2: Kimi fact-check
    print("  [2/3] Kimi fact-checking...")
    try:
        fact_source = (article.get("full_text") or article.get("abstract", ""))[:12000]
        kimi_report = _call_kimi(json.dumps(data, ensure_ascii=False)[:3000], fact_source)
        kimi_clean = _clean_json(kimi_report) if "{" in kimi_report else ""
        kimi_data  = json.loads(kimi_clean) if kimi_clean else {}
        issues     = kimi_data.get("issues", [])
        kimi_pass  = kimi_data.get("pass", True)

        if not kimi_pass and issues:
            print(f"  Kimi found {len(issues)} issue(s), applying fixes...")
            fixed_raw = _fix_with_deepseek(
                json.dumps(data, ensure_ascii=False),
                json.dumps(kimi_data, ensure_ascii=False)
            )
            fixed_raw = _clean_json(fixed_raw)
            try:
                data = json.loads(fixed_raw)
                print("  [3/3] DeepSeek fix applied.")
            except Exception:
                print("  [WARN] Fix parse failed, using pre-fix draft.")
        else:
            print("  Kimi: PASS — no fact issues found.")
    except Exception as e:
        print(f"  [WARN] Kimi review failed: {e}, skipping fix stage.")

    # Stage 4: Validate
    violations = _validate(data)
    if violations:
        print(f"  Validation warnings ({len(violations)}):")
        for v in violations:
            print(f"    - {v}")
    else:
        print("  Validation: PASS")

    # WeChat cover digest fallback + fixed ad bar
    try:
        from wechat_cover import ensure_cover_digest
        from wechat_ad_bar import inject_ad_bar, load_ad_bar_config

        ensure_cover_digest(data.setdefault("wechat", {}))
        if ad_bar_config and ad_bar_config.exists():
            inject_ad_bar(data, load_ad_bar_config(ad_bar_config))
        else:
            inject_ad_bar(data)
        print("  WeChat: cover_digest + ad_bar injected")
    except Exception as e:
        print(f"  [WARN] WeChat post-process failed: {e}")

    # Add metadata
    data["_meta"] = {
        "pmid":       article.get("pmid", ""),
        "doi":        article.get("doi", ""),
        "title":      article.get("title", ""),
        "generated":  __import__("datetime").datetime.now().isoformat(),
        "violations": violations,
    }

    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"  Saved: {out_path.name}")
    return data


if __name__ == "__main__":
    import sys
    # Test with a sample article
    sample = {
        "pmid": "37234567",
        "title": "Humanized mouse models for cancer immunotherapy assessment",
        "authors": "Zhang W, Li H, et al.",
        "journal": "Nature Communications",
        "year": "2024",
        "doi": "10.1038/s41467-024-00001-x",
        "url": "https://pubmed.ncbi.nlm.nih.gov/37234567/",
        "abstract": (
            "Humanized mouse models engrafted with human immune cells have become "
            "indispensable tools for preclinical evaluation of cancer immunotherapies. "
            "NSG-SGM3 mice show 50-70% human chimerism but 39% mortality due to "
            "myeloid hyperactivation between weeks 10-17. Hu-CD34+ models require "
            "12-16 weeks for full reconstitution while Hu-PBMC models achieve rapid "
            "T-cell engraftment within 1-2 weeks. Bispecific antibodies targeting "
            "EpCAM×CD3 achieved complete tumor regression in 3/9 mice."
        ),
    }
    out = ROOT / "outputs" / "social_test" / "social.json"
    generate_social_content(sample, out)
    print(f"\nDone: {out}")
