#!/usr/bin/env python3
"""US finance → 2-card Xiaohongshu: story + dai款 knowledge → LLM → guard → images → email."""
from __future__ import annotations

import json
import os
import re
import smtplib
import sys
from datetime import datetime, timezone
from email.mime.application import MIMEApplication
from email.mime.image import MIMEImage
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from email.utils import formatdate, make_msgid
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[2]
CG = ROOT / "content_generation_tools"
PKG = Path(__file__).resolve().parent

sys.path.insert(0, str(ROOT / "scripts"))
import content_ssot_guard as guard  # noqa: E402
import render_tier  # noqa: E402

from us_finance_xhs.build_preview_post import build_post_preview  # noqa: E402
from us_finance_xhs.fetch_brief import (  # noqa: E402
    build_brief_markdown,
    fetch_headlines,
    fetch_mortgage_rates,
    fetch_yahoo_quotes,
    pick_edition_theme,
    pick_layout_variant,
    quotes_lookup,
)
from us_finance_xhs.number_guard import (  # noqa: E402
    audit_finance_numbers,
    build_facts_snapshot,
)
from us_finance_xhs.voice_tts import make_voice_assets  # noqa: E402
from us_finance_xhs.news_cache import load_cached_brief, record_send  # noqa: E402
from us_finance_xhs.sanitize_copy import sanitize_doc  # noqa: E402
from us_finance_xhs.validate_mini2 import validate_doc  # noqa: E402
from us_finance_xhs.xhs_text_render import build_card_prompt, render_xhs_card  # noqa: E402

WRITER_SYSTEM = (PKG / "writer_system.md").read_text(encoding="utf-8")
_XHS_IMAGE_SIZE = "1024x1536"
_IMAGE_STYLES = json.loads((PKG / "image_styles.json").read_text(encoding="utf-8"))


def _image_style() -> dict[str, Any]:
    name = (os.environ.get("FINANCE_XHS_IMAGE_STYLE") or _IMAGE_STYLES.get("default") or "editorial_soft").strip()
    styles = _IMAGE_STYLES.get("styles") or {}
    cfg = dict(styles.get(name) or styles.get("editorial_soft") or {})
    cfg["_name"] = name
    return cfg


def _card_visual_theme(page: int, card: dict[str, Any]) -> str:
    title = card.get("title") or ""
    if page == 1:
        return f"北美华人圈本周要闻解读与评论。卡片主题：{title}"
    return f"dai款知识科普（房dai/商业房dai），生活化手账。卡片主题：{title}"


def _card_image_prompt(page: int, card: dict[str, Any], style: dict[str, Any]) -> str:
    theme = _card_visual_theme(page, card)
    if style.get("renderer_preference") == "seedream":
        return f"{style.get('prompt_prefix', '')}{theme}。{style.get('prompt_suffix', '')}"
    title = card.get("title") or ""
    body = card.get("body") or ""
    bullets = "；".join(card.get("bullets") or [])
    caption = card.get("image_caption") or ""
    return (
        f"{style.get('prompt_prefix', '')}"
        f"标题：{title}。正文：{body}。要点：{bullets}。副标：{caption}。"
        f"{style.get('prompt_suffix', '')}"
    )


def _is_openai_quota_error(exc: BaseException) -> bool:
    msg = str(exc).lower()
    if any(k in msg for k in ("insufficient", "quota", "billing", "rate limit", "exceeded")):
        return True
    code = getattr(exc, "status_code", None)
    if code in (402, 429):
        return True
    body = getattr(exc, "body", None)
    if isinstance(body, dict):
        err = body.get("error") or {}
        if isinstance(err, dict) and "insufficient" in str(err.get("message", "")).lower():
            return True
    return False


def _seedream_model() -> str:
    try:
        cfg = render_tier.load_renderer_config()
        sd = cfg.get("backends", {}).get("seedream", {})
        return (
            sd.get("models", {}).get("standard_45", {}).get("endpoint_id")
            or "doubao-seedream-4-5-251128"
        )
    except Exception:
        return "doubao-seedream-4-5-251128"


def _render_one_card(prompt: str, out_path: Path, *, style: dict[str, Any]) -> dict[str, Any]:
    """Render card; style may prefer Seedream (illustration) or gpt-image-2 (infographic)."""
    guard.load_env()
    out_path.parent.mkdir(parents=True, exist_ok=True)
    env_renderer = (os.environ.get("FINANCE_XHS_RENDERER") or "auto").strip().lower()
    style_pref = (style.get("renderer_preference") or "seedream").strip().lower()
    preferred = env_renderer if env_renderer not in ("auto", "") else style_pref

    if preferred == "seedream":
        result = render_tier.render_seedream(
            prompt, _XHS_IMAGE_SIZE, out_path, model=_seedream_model()
        )
        result["fallback_from"] = None
        return result

    if preferred == "xhs_text_hero" or style.get("renderer_preference") == "xhs_text_hero":
        return render_xhs_card(prompt, out_path)

    if preferred == "gemini-pro":
        return render_xhs_card(prompt, out_path, force_backend="gemini-pro")

    if preferred not in ("auto", "", "gpt-image-2"):
        raise ValueError(f"Unknown FINANCE_XHS_RENDERER: {preferred}")

    gpt_model = "gpt-image-2"
    try:
        cfg = render_tier.load_renderer_config()
        gpt_model = (
            cfg.get("backends", {}).get("gpt-image-2", {}).get("models", {}).get("medium")
            or "gpt-image-2"
        )
    except Exception:
        pass

    try:
        result = render_tier.render_gpt_image(
            prompt,
            _XHS_IMAGE_SIZE,
            gpt_model,
            out_path,
            quality="medium",
        )
        result["fallback_from"] = None
        return result
    except Exception as gpt_exc:
        if preferred == "gpt-image-2" or not _is_openai_quota_error(gpt_exc):
            raise
        return render_xhs_card(prompt, out_path, force_backend="gemini-pro")


def render_card_images(
    social: dict[str, Any],
    out_dir: Path,
    *,
    quotes: dict[str, Any] | None = None,
    layout_variant: dict[str, str] | None = None,
    loan_category: str = "residential",
    edition_theme: str = "event",
) -> tuple[list[Path], list[dict[str, Any]]]:
    out_dir.mkdir(parents=True, exist_ok=True)
    xhs = social.get("xiaohongshu") or social
    cards = xhs.get("cards") or []
    style = _image_style()
    paths: list[Path] = []
    render_log: list[dict[str, Any]] = []
    for card in cards[:2]:
        page = card.get("page", len(paths) + 1)
        if style.get("renderer_preference") == "xhs_text_hero":
            q = quotes or {}
            tnx = (q.get("^TNX") or {}).get("value_pct")
            mort = (q.get("MORTGAGE30US") or {}).get("value_pct")
            prompt = build_card_prompt(
                page,
                card,
                tnx=tnx,
                mort=mort,
                layout_variant=layout_variant,
                loan_category=loan_category,
                edition_theme=edition_theme,
            )
        else:
            prompt = _card_image_prompt(page, card, style)
        out_path = out_dir / f"card_{page:02d}.png"
        try:
            meta = _render_one_card(prompt, out_path, style=style)
            meta["page"] = page
            meta["image_style"] = style.get("_name") or os.environ.get("FINANCE_XHS_IMAGE_STYLE")
            meta["prompt_preview"] = prompt[:180]
            render_log.append(meta)
            if out_path.exists():
                paths.append(out_path)
        except Exception as exc:
            render_log.append({"page": page, "error": str(exc)[:400]})
    return paths, render_log


def pick_loan_topic(*, run_index: int | None = None) -> dict[str, str]:
    topics = json.loads((PKG / "loan_topics.json").read_text(encoding="utf-8"))
    if not topics:
        return {"id": "default", "title": "贷款基础", "focus": "利率与 Fed 政策联动。"}
    idx = run_index if run_index is not None else datetime.now(timezone.utc).toordinal() // 2
    return topics[idx % len(topics)]


def _strip_json(text: str) -> str:
    t = text.strip()
    if t.startswith("```"):
        t = re.sub(r"^```\w*\n?", "", t)
        t = re.sub(r"\n?```$", "", t)
    match = re.search(r"\{.*\}", t, re.DOTALL)
    return match.group(0) if match else t


def write_social_json(brief: str) -> tuple[dict[str, Any], str]:
    spec = (PKG / "format_spec_mini2.md").read_text(encoding="utf-8")
    user = f"## 格式规范\n{spec}\n\n## 新闻简报\n{brief}\n"
    guard.load_env()
    raw, provider = guard.writer_chat(WRITER_SYSTEM, user)
    data = json.loads(_strip_json(raw))
    if "xiaohongshu" not in data:
        data = {"format_version": "finance_xhs_mini_v1", "xiaohongshu": data}
    return data, provider


def ensure_valid_social(social: dict[str, Any], brief: str, *, max_attempts: int = 3) -> dict[str, Any]:
    spec = (PKG / "format_spec_mini2.md").read_text(encoding="utf-8")
    current = social
    for _ in range(max_attempts + 1):
        validation = validate_doc(current)
        if validation.get("pass"):
            return current
        violations = (validation.get("xiaohongshu") or {}).get("violations") or []
        if not violations:
            return current
        fix_user = (
            f"## 格式规范\n{spec}\n\n"
            f"## 待修正 violations\n{json.dumps(violations, ensure_ascii=False)}\n\n"
            f"硬性要求：正文 body 仅计汉字，必须 180–320 个；cards 恰好 2 张，每张 card.body 50–120 汉字，bullets 2–4 条。"
            f"请扩写中文内容，数字可保留，不要删卡片。\n\n"
            f"## 新闻简报\n{brief[:12000]}\n\n"
            f"## 当前 JSON（只输出修正后的完整 JSON）\n"
            f"{json.dumps(current, ensure_ascii=False)}\n"
        )
        raw, _provider = guard.writer_chat(WRITER_SYSTEM, fix_user)
        try:
            current = json.loads(_strip_json(raw))
            if "xiaohongshu" not in current and "title" in current:
                current = {"format_version": "finance_xhs_mini_v1", "xiaohongshu": current}
        except json.JSONDecodeError:
            break
    return current


def _voice_enabled() -> bool:
    """Default off (cost); set FINANCE_XHS_VOICE=1 to enable Doubao TTS + MP4."""
    return (os.environ.get("FINANCE_XHS_VOICE") or "0").strip().lower() in (
        "1",
        "true",
        "yes",
        "on",
    )


def _number_gate_mode() -> str:
    """enforce (block send on FAIL, default) | warn (log only)."""
    mode = (os.environ.get("FINANCE_XHS_NUMBER_GATE") or "enforce").strip().lower()
    return "warn" if mode in ("warn", "off", "0", "false") else "enforce"


def enforce_number_gate(
    social: dict[str, Any],
    brief: str,
    facts: dict[str, Any],
) -> tuple[dict[str, Any], dict[str, Any]]:
    """Run deterministic number audit; on FAIL try one writer repair, then re-audit.

    Returns (possibly-repaired social, audit dict with final status + blocked flag).
    """
    xhs = social.get("xiaohongshu") or social
    audit = audit_finance_numbers(xhs, facts)
    if audit.get("status") == "PASS":
        audit["blocked"] = False
        return social, audit

    # One targeted repair attempt: ask the writer to drop/fix unsourced numbers.
    try:
        spec = (PKG / "format_spec_mini2.md").read_text(encoding="utf-8")
        viol = json.dumps(audit.get("violations") or [], ensure_ascii=False)
        fix_user = (
            f"## 格式规范\n{spec}\n\n"
            f"## 数字校验未通过（这些数值在数据快照里找不到来源，疑似编造）\n{viol}\n\n"
            f"硬性要求：删除或改写上述无来源的具体数值（利率/百分比/点位），"
            f"改为定性表达或替换为简报中真实存在的数字；其余内容、卡片数量、字数保持合规。"
            f"只输出修正后的完整 JSON。\n\n"
            f"## 数据快照可用数值标签\n{json.dumps(facts.get('labels') or [], ensure_ascii=False)}\n\n"
            f"## 新闻简报\n{brief[:12000]}\n\n"
            f"## 当前 JSON\n{json.dumps(social, ensure_ascii=False)}\n"
        )
        raw, _ = guard.writer_chat(WRITER_SYSTEM, fix_user)
        repaired = json.loads(_strip_json(raw))
        if "xiaohongshu" not in repaired and "title" in repaired:
            repaired = {"format_version": "finance_xhs_mini_v1", "xiaohongshu": repaired}
        repaired = sanitize_doc(repaired if "xiaohongshu" in repaired else {"xiaohongshu": repaired})
        repaired_xhs = repaired.get("xiaohongshu") or repaired
        reaudit = audit_finance_numbers(repaired_xhs, facts)
        if reaudit.get("status") == "PASS":
            reaudit["blocked"] = False
            reaudit["repaired"] = True
            return repaired, reaudit
        # repair failed too
        reaudit["repaired"] = True
        reaudit["blocked"] = _number_gate_mode() == "enforce"
        return repaired, reaudit
    except Exception as exc:
        audit["repair_error"] = str(exc)[:240]
        audit["blocked"] = _number_gate_mode() == "enforce"
        return social, audit


def parse_notify_emails(override: str = "") -> list[str]:
    raw = (
        override.strip()
        or os.environ.get("FINANCE_XHS_NOTIFY_EMAILS", "")
        or os.environ.get("FINANCE_XHS_NOTIFY_EMAIL", "")
    )
    return [e.strip() for e in raw.replace(";", ",").split(",") if e.strip()]


def _smtp_profile(prefix: str) -> dict[str, Any]:
    host = os.environ.get(f"{prefix}_HOST", "").strip()
    port = int((os.environ.get(f"{prefix}_PORT", "587").strip() or "587"))
    user = os.environ.get(f"{prefix}_USER", "").strip()
    password = (
        os.environ.get(f"{prefix}_PASS")
        or os.environ.get(f"{prefix}_PASSWORD")
        or ""
    ).strip()
    use_tls = os.environ.get(f"{prefix}_TLS", "1").strip().lower() not in ("0", "false", "no")
    from_addr = (os.environ.get(f"{prefix}_FROM") or user).strip()
    return {
        "host": host,
        "port": port,
        "user": user,
        "password": password,
        "use_tls": use_tls,
        "from_addr": from_addr,
        "profile": prefix,
    }


def _smtp_settings() -> dict[str, Any]:
    # Primary sender: contact@insynbio.com (INSYNBIO_* / SMTP_*)
    primary = _smtp_profile("INSYNBIO_SMTP")
    if not primary["host"]:
        primary["host"] = os.environ.get("SMTP_HOST", "").strip()
        primary["port"] = int((os.environ.get("SMTP_PORT", "587").strip() or "587"))
        primary["user"] = (primary["user"] or os.environ.get("SMTP_USER", "")).strip()
        primary["password"] = (primary["password"] or os.environ.get("SMTP_PASSWORD", "")).strip()
        primary["use_tls"] = (
            os.environ.get("SMTP_TLS", "1").strip().lower() not in ("0", "false", "no")
        )
        primary["from_addr"] = (
            primary["from_addr"]
            or os.environ.get("INSYNBIO_EMAIL_SENDER", "").strip()
            or os.environ.get("SMTP_FROM", "").strip()
            or primary["user"]
            or "contact@insynbio.com"
        )

    # Fallback sender: mail.jing.huang@gmail.com (LAB_SMTP_* or GMAIL_*)
    fallback = _smtp_profile("LAB_SMTP")
    if not fallback["host"]:
        gmail_user = os.environ.get("GMAIL_USER", "").strip()
        gmail_password = os.environ.get("GMAIL_APP_PASSWORD", "").strip()
        if gmail_user and gmail_password:
            fallback = {
                "host": "smtp.gmail.com",
                "port": 587,
                "user": gmail_user,
                "password": gmail_password,
                "use_tls": True,
                "from_addr": gmail_user,
                "profile": "GMAIL_FALLBACK",
            }

    return {
        "host": primary.get("host", ""),
        "port": primary.get("port", 587),
        "user": primary.get("user", ""),
        "password": primary.get("password", ""),
        "use_tls": bool(primary.get("use_tls", True)),
        "from_addr": primary.get("from_addr", "contact@insynbio.com"),
        "fallback": fallback,
    }


def smtp_configured() -> bool:
    return bool(_smtp_settings()["host"])


def send_delivery_email(
    *,
    to: str,
    subject: str,
    xhs: dict[str, Any],
    image_paths: list[Path],
    brief_path: Path | None = None,
    extra_attachments: list[Path] | None = None,
) -> dict[str, Any]:
    smtp = _smtp_settings()
    if not smtp["host"]:
        return {"sent": False, "reason": "SMTP host not configured (LAB_SMTP_* or INSYNBIO_SMTP_*)"}

    cards = xhs.get("cards") or []
    body_text = (
        f"标题：{xhs.get('title', '')}\n\n"
        f"{xhs.get('cover_hook', '')}\n\n"
        f"{xhs.get('body', '')}\n\n"
        f"标签：{' '.join(xhs.get('tags') or [])}\n\n"
        f"---\n卡1：{cards[0].get('title', '') if cards else ''}\n"
        f"卡2：{cards[1].get('title', '') if len(cards) > 1 else ''}\n"
    )
    html = (
        f"<h2>{xhs.get('title', '')}</h2>"
        f"<p><strong>{xhs.get('cover_hook', '')}</strong></p>"
        f"<pre style='white-space:pre-wrap'>{xhs.get('body', '')}</pre>"
        f"<p>{' '.join(xhs.get('tags') or [])}</p>"
    )

    msg = MIMEMultipart("related")
    msg["Subject"] = subject
    msg["To"] = to
    msg["Date"] = formatdate(localtime=True)
    alt = MIMEMultipart("alternative")
    alt.attach(MIMEText(body_text, "plain", "utf-8"))
    alt.attach(MIMEText(html, "html", "utf-8"))
    msg.attach(alt)

    for i, img_path in enumerate(image_paths):
        if not img_path.exists():
            continue
        img = MIMEImage(img_path.read_bytes(), name=img_path.name)
        img.add_header("Content-ID", f"<card{i}>")
        img.add_header("Content-Disposition", "attachment", filename=img_path.name)
        msg.attach(img)

    for att in extra_attachments or []:
        if not att or not att.exists():
            continue
        part = MIMEApplication(att.read_bytes(), Name=att.name)
        part.add_header("Content-Disposition", "attachment", filename=att.name)
        msg.attach(part)

    profiles = [
        {
            "host": smtp["host"],
            "port": smtp["port"],
            "user": smtp["user"],
            "password": smtp["password"],
            "use_tls": smtp["use_tls"],
            "from_addr": smtp["from_addr"],
            "profile": "PRIMARY",
        }
    ]
    fallback = smtp.get("fallback") or {}
    if fallback.get("host"):
        profiles.append(fallback)

    errors: list[dict[str, str]] = []
    for profile in profiles:
        try:
            from_addr = profile["from_addr"]
            del msg["From"]
            msg["From"] = from_addr
            domain = from_addr.split("@", 1)[1] if "@" in from_addr else None
            del msg["Message-ID"]
            msg["Message-ID"] = make_msgid(domain=domain)
            with smtplib.SMTP(profile["host"], profile["port"], timeout=45) as server:
                if profile["use_tls"]:
                    server.starttls()
                if profile["user"] and profile["password"]:
                    server.login(profile["user"], profile["password"])
                server.sendmail(profile["from_addr"], [to], msg.as_string())
            return {
                "sent": True,
                "to": to,
                "from": profile["from_addr"],
                "attachments": len(image_paths),
                "via": profile.get("profile", "PRIMARY"),
            }
        except Exception as exc:
            errors.append(
                {
                    "profile": profile.get("profile", "PRIMARY"),
                    "from": profile.get("from_addr", ""),
                    "reason": str(exc),
                }
            )

    return {"sent": False, "to": to, "reason": errors[-1]["reason"] if errors else "unknown", "attempts": errors}


def send_delivery_emails(
    *,
    recipients: list[str],
    subject: str,
    xhs: dict[str, Any],
    image_paths: list[Path],
    brief_path: Path | None = None,
    extra_attachments: list[Path] | None = None,
) -> dict[str, Any]:
    results = []
    for addr in recipients:
        results.append(
            send_delivery_email(
                to=addr,
                subject=subject,
                xhs=xhs,
                image_paths=image_paths,
                brief_path=brief_path,
                extra_attachments=extra_attachments,
            )
        )
    sent = [r for r in results if r.get("sent")]
    return {
        "sent": len(sent) == len(recipients) and bool(recipients),
        "recipients": recipients,
        "results": results,
        "from": (sent[0].get("from") if sent else _smtp_settings().get("from_addr")),
    }


def run_pipeline(
    *,
    out_dir: Path,
    notify_email: str = "",
    loan_topic_index: int | None = None,
    skip_render: bool = False,
    skip_guard: bool = False,
) -> dict[str, Any]:
    out_dir.mkdir(parents=True, exist_ok=True)
    out_root = out_dir.parent
    loan_topic = pick_loan_topic(run_index=loan_topic_index)
    layout_variant = pick_layout_variant(run_index=loan_topic_index)
    edition_theme = pick_edition_theme(run_index=loan_topic_index)
    quotes: list[dict[str, Any]] = []
    headlines: list[dict[str, str]] = []
    mortgage: dict[str, Any] = {}
    try:
        mortgage = fetch_mortgage_rates()
    except Exception:
        mortgage = {}
    use_cache = os.environ.get("FINANCE_XHS_USE_CACHE", "1").strip().lower() not in (
        "0",
        "false",
        "no",
    )
    if use_cache:
        try:
            brief, quotes, headlines, cache_meta = load_cached_brief(out_root)
            edition_theme = cache_meta.get("edition_theme") or edition_theme
            layout_variant = pick_layout_variant(run_index=loan_topic_index)
        except FileNotFoundError:
            quotes = fetch_yahoo_quotes()
            headlines = fetch_headlines()
            brief = build_brief_markdown(
                loan_topic=loan_topic,
                quotes=quotes,
                headlines=headlines,
                layout_variant=layout_variant,
                edition_theme=edition_theme,
                mortgage=mortgage,
            )
    else:
        quotes = fetch_yahoo_quotes()
        headlines = fetch_headlines()
        brief = build_brief_markdown(
            loan_topic=loan_topic,
            quotes=quotes,
            headlines=headlines,
            layout_variant=layout_variant,
            edition_theme=edition_theme,
            mortgage=mortgage,
        )
    brief_path = out_dir / "news_brief.md"
    brief_path.write_text(brief, encoding="utf-8")

    writer_provider = "unknown"
    llm_errors: list[str] = []
    try:
        social, writer_provider = write_social_json(brief)
    except Exception as exc:
        llm_errors.append(f"writer: {exc}")
        raise

    draft_str = json.dumps(social, ensure_ascii=False, indent=2)
    (out_dir / "social_draft.json").write_text(draft_str + "\n", encoding="utf-8")

    guard_result: dict[str, Any] = {"passed": False, "trail": [], "providers": []}
    if not skip_guard:
        try:
            guard_result = guard.guarded_pipeline(brief, draft_str, content_type="social")
            (out_dir / "review_trail.json").write_text(
                json.dumps(guard_result["trail"], ensure_ascii=False, indent=2) + "\n",
                encoding="utf-8",
            )
            try:
                social = json.loads(guard_result["content_ssot"])
            except json.JSONDecodeError:
                llm_errors.append("guard: content_ssot not JSON, keeping draft")
        except Exception as exc:
            llm_errors.append(f"guard: {exc}")
            (out_dir / "review_trail.json").write_text(
                json.dumps({"error": str(exc)[:500]}, ensure_ascii=False, indent=2) + "\n",
                encoding="utf-8",
            )

    try:
        social = ensure_valid_social(social, brief)
    except Exception as exc:
        llm_errors.append(f"validate_fix: {exc}")

    social = sanitize_doc(social if "xiaohongshu" in social else {"xiaohongshu": social})
    if "format_version" not in social and "xiaohongshu" in social:
        social = {"format_version": "finance_xhs_mini_v1", **social}
    elif "xiaohongshu" not in social:
        social = {"format_version": "finance_xhs_mini_v1", "xiaohongshu": social}

    facts = build_facts_snapshot(quotes, mortgage)
    social, number_audit = enforce_number_gate(social, brief, facts)
    (out_dir / "number_audit.json").write_text(
        json.dumps(number_audit, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )

    social_path = out_dir / "social.json"
    social_path.write_text(json.dumps(social, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    validation = validate_doc(social)
    social_path.write_text(json.dumps(social, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")

    image_paths: list[Path] = []
    render_log: list[dict[str, Any]] = []
    if not skip_render:
        image_paths, render_log = render_card_images(
            social,
            out_dir / "images",
            quotes=quotes_lookup(quotes),
            layout_variant=layout_variant,
            loan_category=loan_topic.get("category") or "residential",
            edition_theme=edition_theme,
        )
        (out_dir / "render_log.json").write_text(
            json.dumps(render_log, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
        )

    xhs = social.get("xiaohongshu") or social

    # Female-voice broadcast (display text unchanged). Numbers in voice_script were
    # already audited via number_guard.collect_copy_text. Skip when send is blocked.
    voice_result: dict[str, Any] = {"enabled": _voice_enabled()}
    voice_attachments: list[Path] = []
    voice_script = str(xhs.get("voice_script") or "").strip()
    if _voice_enabled() and voice_script and not number_audit.get("blocked"):
        try:
            voice_result.update(
                make_voice_assets(
                    voice_script,
                    image_paths,
                    out_dir,
                    speaker=(os.environ.get("FINANCE_XHS_VOICE_SPEAKER") or "").strip()
                    or "zh_female_shuangkuaisisi_uranus_bigtts",
                    make_video=os.environ.get("FINANCE_XHS_VOICE_VIDEO", "1").strip().lower()
                    not in ("0", "false", "no"),
                )
            )
            if voice_result.get("mp4"):
                voice_attachments.append(Path(voice_result["mp4"]))
            # MP3 is generated for video mux only; XHS delivery uses MP4 — do not email MP3.
        except Exception as exc:
            voice_result["error"] = str(exc)[:300]
        (out_dir / "voice_result.json").write_text(
            json.dumps(voice_result, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
        )

    recipients = parse_notify_emails(notify_email)
    email_result: dict[str, Any] = {"sent": False, "reason": "no recipients"}
    if number_audit.get("blocked"):
        email_result = {
            "sent": False,
            "reason": "number_gate_failed: 文案含无来源数字，已拦截发送（不能瞎报）",
            "violations": number_audit.get("violations"),
        }
        recipients = []
    if recipients:
        ts = datetime.now(timezone.utc).strftime("%Y-%m-%d")
        email_result = send_delivery_emails(
            recipients=recipients,
            subject=f"[小红书财经] {xhs.get('title', '美国财经')} · {ts}",
            xhs=xhs,
            image_paths=image_paths,
            brief_path=brief_path,
            extra_attachments=voice_attachments,
        )
        if email_result.get("sent"):
            try:
                record_send(out_root=out_root, out_dir=str(out_dir))
            except Exception:
                pass

    summary = {
        "ok": bool(social.get("xiaohongshu")),
        "out_dir": str(out_dir),
        "loan_topic": loan_topic.get("id"),
        "loan_category": loan_topic.get("category"),
        "layout_variant": layout_variant.get("id"),
        "edition_theme": edition_theme,
        "writer_provider": writer_provider,
        "image_style": (_image_style().get("_name") or os.environ.get("FINANCE_XHS_IMAGE_STYLE")),
        "guard_passed": guard_result.get("passed", False),
        "number_gate": {
            "status": number_audit.get("status"),
            "checked": number_audit.get("checked"),
            "blocked": number_audit.get("blocked", False),
            "repaired": number_audit.get("repaired", False),
            "violations": number_audit.get("violations"),
        },
        "mortgage_rates": mortgage,
        "voice": {
            "enabled": voice_result.get("enabled", False),
            "speaker": voice_result.get("speaker"),
            "mp3": voice_result.get("mp3"),
            "mp4": voice_result.get("mp4"),
            "audio_ok": (voice_result.get("audio") or {}).get("ok"),
            "video_ok": (voice_result.get("video") or {}).get("ok"),
            "error": voice_result.get("error")
            or (voice_result.get("audio") or {}).get("error"),
        },
        "llm_errors": llm_errors,
        "validation": validation,
        "images": [str(p) for p in image_paths],
        "render_backends": [r.get("backend") for r in render_log if r.get("backend")],
        "render_log": render_log,
        "email": email_result,
        "quotes_count": len(quotes),
        "headlines_count": len(headlines),
    }
    (out_dir / "run_summary.json").write_text(
        json.dumps(summary, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )

    if not skip_render and image_paths:
        try:
            build_post_preview(out_dir)
        except Exception:
            pass

    return summary
