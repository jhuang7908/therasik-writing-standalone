#!/usr/bin/env python3
"""WeChat Moments & Daily Recap 1-Card Pipeline."""
from __future__ import annotations

import json
import os
import re
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from . import xhs_text_render as render
from .fetch_brief import fetch_yahoo_quotes, fetch_headlines, build_brief_markdown, pick_layout_variant
from .news_cache import load_cached_brief, record_recap_send
from .sanitize_copy import sanitize_xhs

import content_ssot_guard as guard

PKG = Path(__file__).resolve().parent
ROOT = PKG.parent.parent

RECAP_SYSTEM = (PKG / "recap_writer_system.md").read_text(encoding="utf-8")

def zh_chars(text: str) -> int:
    return len(re.findall(r"[\u4e00-\u9fff]", text or ""))

def validate_recap(x: dict) -> dict:
    v: list[str] = []
    
    # Root keys
    wm = x.get("wechat_moments") or x
    if not isinstance(wm, dict):
        v.append("wechat_moments format invalid")
        return {"pass": False, "violations": ["root-level structure error"]}
        
    # Defensive auto-correction: cards -> card
    if "card" not in wm and "cards" in wm:
        cards_val = wm["cards"]
        if isinstance(cards_val, list) and len(cards_val) > 0:
            wm["card"] = cards_val[0]
            if "cards" in wm:
                del wm["cards"]
        elif isinstance(cards_val, dict):
            wm["card"] = cards_val
            if "cards" in wm:
                del wm["cards"]
                
    title_n = zh_chars(wm.get("title", ""))
    if title_n > 15:
        v.append(f"微信标题汉字={title_n}，要求≤15")
        
    moments_n = zh_chars(wm.get("moments_text", ""))
    if not (80 <= moments_n <= 180):
        v.append(f"微信正文汉字={moments_n}，要求80-180")
        
    if "card" not in wm:
        v.append("卡片 card 对象缺失")
        return {"pass": False, "violations": v}
        
    card = wm["card"]
    if not isinstance(card, dict):
        v.append("card 字段必须为 dict")
        return {"pass": False, "violations": v}
        
    if zh_chars(card.get("title", "")) > 12:
        v.append(f"卡片标题={zh_chars(card.get('title'))}，要求≤12")
        
    cb = zh_chars(card.get("body", ""))
    if not (40 <= cb <= 95):
        v.append(f"卡片正文={cb}，要求40-95")
        
    bullets = card.get("bullets") or []
    if len(bullets) != 3:
        v.append(f"卡片 bullets={len(bullets)}，要求恰好3个")
        
    for i, b in enumerate(bullets, 1):
        if not str(b).strip().startswith(f"{i}."):
            v.append(f"bullet {i} 格式不符合 '{i}.' 开头")
            
    caption = card.get("image_caption") or ""
    if not re.search(r"截至 \d{2}/\d{2}/\d{4}", caption):
        v.append(f"配图页脚日期 '{caption}' 不符合 '截至 MM/DD/YYYY' 北美格式")
        
    return {
        "pass": len(v) == 0,
        "violations": v,
        "image_count": 1,
        "moments_char_count": moments_n
    }

def _strip_json(text: str) -> str:
    t = text.strip()
    if t.startswith("```"):
        t = re.sub(r"^```\w*\n?", "", t)
        t = re.sub(r"\n?```$", "", t)
    match = re.search(r"\{.*\}", t, re.DOTALL)
    return match.group(0) if match else t

def write_recap_json(brief: str) -> tuple[dict[str, Any], str]:
    spec = (PKG / "format_spec_recap.md").read_text(encoding="utf-8")
    user = f"## 格式规范\n{spec}\n\n## 每日收盘简报\n{brief}\n"
    guard.load_env()
    raw, provider = guard.writer_chat(RECAP_SYSTEM, user)
    data = json.loads(_strip_json(raw))
    # Standardize root
    if "wechat_moments" not in data:
        data = {"format_version": "recap_v1", "wechat_moments": data}
    return data, provider

def ensure_valid_recap(recap: dict[str, Any], brief: str, *, max_attempts: int = 2) -> dict[str, Any]:
    spec = (PKG / "format_spec_recap.md").read_text(encoding="utf-8")
    current = recap
    for _ in range(max_attempts + 1):
        validation = validate_recap(current)
        if validation.get("pass"):
            return current
        violations = validation.get("violations") or []
        if not violations:
            return current
        fix_user = (
            f"## 格式规范\n{spec}\n\n"
            f"## 待修正 violations\n{json.dumps(violations, ensure_ascii=False)}\n\n"
            f"硬性要求：朋友圈正文 moments_text 仅计汉字必须 80–180字；卡片 card.body 仅计汉字必须 40–95 汉字，bullets 恰好 3 条且以 1. 2. 3. 编号，页脚日期必须匹配 '截至 MM/DD/YYYY'（如 截至 06/08/2026）。\n\n"
            f"## 收盘简报\n{brief[:12000]}\n\n"
            f"## 当前 JSON（只输出修正后的完整 JSON，不要 markdown 外层包裹）\n"
            f"{json.dumps(current, ensure_ascii=False)}\n"
        )
        raw, _ = guard.writer_chat(RECAP_SYSTEM, fix_user)
        try:
            current = json.loads(_strip_json(raw))
            if "wechat_moments" not in current and "title" in current:
                current = {"format_version": "recap_v1", "wechat_moments": current}
        except json.JSONDecodeError:
            pass
    return current

def render_recap_image(
    recap: dict[str, Any],
    out_dir: Path,
    *,
    quotes: dict[str, Any] | None = None,
) -> tuple[list[Path], list[dict[str, Any]]]:
    out_dir.mkdir(parents=True, exist_ok=True)
    wm = recap.get("wechat_moments") or recap
    card = wm.get("card") or {}
    if isinstance(card, list):
        card = card[0] if card else {}
    
    # We enforce modern_office_minimal style for WeChat Recap
    style = json.loads((PKG / "image_styles.json").read_text(encoding="utf-8"))["styles"]["modern_office_minimal"]
    style["_name"] = "modern_office_minimal"
    
    q = quotes or {}
    tnx = (q.get("^TNX") or {}).get("value_pct")
    mort = (q.get("MORTGAGE30US") or {}).get("value_pct")
    
    # Build a dedicated professional minimal card prompt
    bullets = "\n".join(f"- {b}" for b in card.get("bullets") or [])
    body_snip = (card.get("body") or "")[:100]
    tnx = tnx if tnx is not None else 4.54
    mort = mort if mort is not None else 6.48
    as_of = card.get("image_caption") or datetime.now().strftime("%m/%d/%Y")
    
    prompt = (
        f"{style['prompt_prefix']}\n"
        f"【微信今日财经复盘】版式：极简办公白板。上半部分展示今日核心利率与利率未来走势风向标，下半部分展示财经讨论。\n"
        f"大标题字字照抄（文字直接浮于浅色背景之上，严禁使用任何黑色、深灰色、或实心深色背景框/黑框/深色横幅条作为大标题的背景底板，文字要直接书写于浅色马卡龙纸张纹理底色之上）：{card.get('title')}\n"
        f"副标题字字照抄（文字同样直接书写于浅色底板之上，禁止黑色背景条）：今日美债 TNX 约 {tnx:.2f}%，30年固定房dai预计约 {mort:.2f}%\n"
        f"核心讲解参考：{body_snip}\n"
        f"要点字字照抄不可改字：\n{bullets}\n"
        f"底部灰色细字逐字照抄：{as_of}。最下方标明：〔纯财经探讨，非投资及dai款建议〕\n"
        f"{style['prompt_suffix']}"
    )
    
    out_path = out_dir / "recap_card.png"
    render_log: list[dict[str, Any]] = []
    paths: list[Path] = []
    
    try:
        meta = render.render_xhs_card(prompt, out_path)
        meta["page"] = 1
        meta["image_style"] = "modern_office_minimal"
        meta["prompt_preview"] = prompt[:180]
        render_log.append(meta)
        if out_path.exists():
            paths.append(out_path)
    except Exception as exc:
        render_log.append({"page": 1, "error": str(exc)[:400]})
        
    return paths, render_log

def build_recap_preview(out_dir: Path) -> None:
    social_file = out_dir / "social.json"
    if not social_file.exists():
        return
    try:
        data = json.loads(social_file.read_text(encoding="utf-8"))
        wm = data.get("wechat_moments") or data
        card = wm.get("card") or {}
        if isinstance(card, list):
            card = card[0] if card else {}
        text = wm.get("moments_text") or ""
        title = wm.get("title") or "今日收盘复盘"
        
        # Build nice responsive HTML page
        html = f"""<!DOCTYPE html>
<html>
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>{title}</title>
<style>
  body {{ font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif; background: #f0f2f5; padding: 20px; color: #333; }}
  .container {{ max-width: 480px; margin: 0 auto; background: white; border-radius: 12px; box-shadow: 0 4px 12px rgba(0,0,0,0.1); overflow: hidden; }}
  .header {{ padding: 15px; border-bottom: 1px solid #eee; background: #fafafa; font-weight: bold; text-align: center; font-size: 16px; }}
  .moments-box {{ padding: 15px; font-size: 14px; line-height: 1.6; border-bottom: 8px solid #f0f2f5; }}
  .moments-user {{ font-weight: bold; color: #576b95; margin-bottom: 6px; }}
  .moments-text {{ margin-bottom: 12px; white-space: pre-wrap; }}
  .image-box {{ text-align: center; padding: 15px; background: #fafafa; }}
  .image-box img {{ max-width: 100%; border-radius: 8px; box-shadow: 0 2px 8px rgba(0,0,0,0.15); }}
</style>
</head>
<body>
<div class="container">
  <div class="header">朋友圈日常分享预览</div>
  <div class="moments-box">
    <div class="moments-user">投资人闺蜜 · 收盘快评</div>
    <div class="moments-text">{text}</div>
  </div>
  <div class="image-box">
    <h3>看板配图 ({card.get('image_caption', '日更')})</h3>
    <img src="images/recap_card.png" alt="Recap Board">
  </div>
</div>
</body>
</html>
"""
        (out_dir / "preview.html").write_text(html, encoding="utf-8")
    except Exception:
        pass

def run_recap_pipeline(
    *,
    out_root: str | None = None,
    notify_email: str | None = None,
    use_cache: bool = True,
    force_fetch: bool = False,
) -> dict[str, Any]:
    guard.load_env()
    out_root_path = Path(out_root or os.environ.get("FINANCE_XHS_OUT_ROOT") or "outputs/us_finance_recap")
    
    ts = datetime.now(timezone.utc).strftime("%Y%m%d_%H%M")
    out_dir = out_root_path / ts
    out_dir.mkdir(parents=True, exist_ok=True)
    
    # 1. Fetch / Load Brief
    if use_cache and not force_fetch:
        try:
            brief, quotes, headlines, _ = load_cached_brief(out_root_path)
        except Exception:
            # Fallback to fresh fetch
            quotes = fetch_yahoo_quotes()
            headlines = fetch_headlines()
            brief = build_brief_markdown(
                loan_topic={"id": "default", "title": "信用分与真实借款成本", "focus": "FICO高低利息差"},
                quotes=quotes,
                headlines=headlines,
                layout_variant={"id": "dashboard", "label": "极简看板", "card1_hint": "极简大盘看板"},
                edition_theme="recap"
            )
    else:
        quotes = fetch_yahoo_quotes()
        headlines = fetch_headlines()
        brief = build_brief_markdown(
            loan_topic={"id": "default", "title": "信用分与真实借款成本", "focus": "FICO高低利息差"},
            quotes=quotes,
            headlines=headlines,
            layout_variant={"id": "dashboard", "label": "极简看板", "card1_hint": "极简大盘看板"},
            edition_theme="recap"
        )
        
    brief_path = out_dir / "news_brief.md"
    brief_path.write_text(brief, encoding="utf-8")
    
    # 2. Write Recap Content
    raw_recap, writer_provider = write_recap_json(brief)
    recap = ensure_valid_recap(raw_recap, brief)
    
    (out_dir / "social_draft.json").write_text(json.dumps(recap, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    
    # 3. Third-party AISS Audit (review & fix loop)
    guard_result = {"passed": False, "trail": []}
    draft_str = json.dumps(recap, ensure_ascii=False, indent=2)
    try:
        guard_result = guard.guarded_pipeline(brief, draft_str, content_type="recap")
        (out_dir / "review_trail.json").write_text(
            json.dumps(guard_result["trail"], ensure_ascii=False, indent=2) + "\n",
            encoding="utf-8",
        )
        try:
            recap = json.loads(guard_result["content_ssot"])
        except json.JSONDecodeError:
            pass
    except Exception as exc:
        (out_dir / "review_trail.json").write_text(
            json.dumps({"error": str(exc)[:500]}, ensure_ascii=False, indent=2) + "\n",
            encoding="utf-8",
        )
        
    # 4. Sanitation
    recap = sanitize_xhs(recap)
    (out_dir / "social.json").write_text(json.dumps(recap, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    
    # 5. Rendering (1 card with minimal professional style)
    image_paths, render_log = render_recap_image(recap, out_dir / "images", quotes=quotes_lookup(quotes))
    (out_dir / "render_log.json").write_text(
        json.dumps(render_log, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )
    
    # 6. Mailing (SMTP Dual dispatch)
    recipients = parse_notify_emails(notify_email)
    email_result = {"sent": False, "reason": "no recipients"}
    if recipients:
        wm = recap.get("wechat_moments") or recap
        date_str = datetime.now(timezone.utc).strftime("%m/%d/%Y")
        email_result = send_recap_emails(
            recipients=recipients,
            subject=f"[朋友圈/收盘复盘] {wm.get('title', '美股收盘利息参考')} · {date_str}",
            recap=recap,
            image_paths=image_paths,
            brief_path=brief_path
        )
        if email_result.get("sent"):
            try:
                record_recap_send(out_root=out_root_path, out_dir=str(out_dir))
            except Exception:
                pass
                
    validation = validate_recap(recap)
    summary = {
        "ok": bool(recap.get("wechat_moments")),
        "out_dir": str(out_dir),
        "edition_theme": "recap",
        "writer_provider": writer_provider,
        "image_style": "modern_office_minimal",
        "guard_passed": guard_result.get("passed", False),
        "validation": validation,
        "images": [str(p) for p in image_paths],
        "render_backends": [r.get("backend") for r in render_log if r.get("backend")],
        "render_log": render_log,
        "email": email_result,
        "quotes_count": len(quotes) if quotes else 0,
        "headlines_count": len(headlines) if headlines else 0,
    }
    (out_dir / "run_summary.json").write_text(
        json.dumps(summary, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )
    
    build_recap_preview(out_dir)
    return summary

def quotes_lookup(quotes: list[dict[str, Any]] | None) -> dict[str, Any]:
    if not quotes:
        return {}
    return {q["symbol"]: q for q in quotes if q.get("symbol")}

def parse_notify_emails(emails_str: str | None) -> list[str]:
    raw = emails_str or os.environ.get("FINANCE_XHS_NOTIFY_EMAILS") or ""
    return [e.strip() for e in re.split(r"[,;]", raw) if "@" in e.strip()]

def send_recap_emails(
    recipients: list[str],
    subject: str,
    recap: dict[str, Any],
    image_paths: list[Path],
    brief_path: Path,
) -> dict[str, Any]:
    import smtplib
    from email.mime.multipart import MIMEMultipart
    from email.mime.text import MIMEText
    from email.mime.image import MIMEImage

    host = os.environ.get("INSYNBIO_SMTP_HOST", "mail.privateemail.com")
    port_str = os.environ.get("INSYNBIO_SMTP_PORT", "587")
    user = os.environ.get("INSYNBIO_SMTP_USER", "contact@insynbio.com")
    password = os.environ.get("INSYNBIO_SMTP_PASS")
    sender = os.environ.get("INSYNBIO_EMAIL_SENDER", "contact@insynbio.com")

    if not password:
        return {"sent": False, "reason": "SMTP password missing in environment"}

    try:
        port = int(port_str)
    except ValueError:
        port = 587

    wm = recap.get("wechat_moments") or recap
    text_content = wm.get("moments_text") or ""
    title_content = wm.get("title") or "收盘快评"
    
    # HTML Email body
    html_content = f"""<html>
<body style="font-family: Arial, sans-serif; background: #f9f9f9; padding: 20px;">
  <div style="max-width: 500px; margin: 0 auto; background: #ffffff; border-radius: 8px; border: 1px solid #ddd; overflow: hidden; box-shadow: 0 2px 4px rgba(0,0,0,0.05);">
    <div style="background: #fbf7ee; color: #b17e43; padding: 18px; font-weight: bold; font-size: 17px; text-align: center; border-bottom: 2px dashed #e9dfd1;">
      💌 微信朋友圈日更 · 今日收盘与利率风向标
    </div>
    <div style="padding: 20px;">
      <h3 style="color: #333; margin-top: 0;">{title_content}</h3>
      <p style="font-size: 14px; color: #666; line-height: 1.6; white-space: pre-wrap; background: #f5f5f5; padding: 15px; border-radius: 6px; border-left: 4px solid #576b95;">
{text_content}
      </p>
      <p style="font-size: 12px; color: #999;">
        💡 <b>发布建议</b>：长按或保存下方看板图片，复制上述灰色背景框内的文字，直接发布到您的个人朋友圈（WeChat Moments）或高净值社群中。
      </p>
      <div style="text-align: center; margin-top: 20px;">
        <img src="cid:recap_img" style="max-width: 100%; border-radius: 6px; box-shadow: 0 4px 10px rgba(0,0,0,0.1);" />
      </div>
    </div>
  </div>
</body>
</html>
"""

    results = []
    sent_all = True

    for to_email in recipients:
        try:
            msg = MIMEMultipart("related")
            msg["Subject"] = subject
            msg["From"] = f"InSynBio Recap <{sender}>"
            msg["To"] = to_email

            msg_alternative = MIMEMultipart("alternative")
            msg.attach(msg_alternative)

            # Plain text part
            text_part = MIMEText(
                f"【今日朋友圈日常推荐文案】\n\n{text_content}\n\n[图片已随附在邮件中]",
                "plain",
                "utf-8"
            )
            msg_alternative.attach(text_part)

            # HTML part
            html_part = MIMEText(html_content, "html", "utf-8")
            msg_alternative.attach(html_part)

            # Attach Image
            if image_paths and image_paths[0].exists():
                with open(image_paths[0], "rb") as f:
                    mime_img = MIMEImage(f.read())
                    mime_img.add_header("Content-ID", "<recap_img>")
                    mime_img.add_header("Content-Disposition", "inline", filename="recap_card.png")
                    msg.attach(mime_img)

            # SMTP Sending
            with smtplib.SMTP(host, port, timeout=30) as server:
                server.starttls()
                server.login(user, password)
                server.sendmail(sender, to_email, msg.as_string())
            results.append({"to": to_email, "sent": True})
        except Exception as exc:
            results.append({"to": to_email, "sent": False, "error": str(exc)})
            sent_all = False

    return {"sent": sent_all, "results": results, "from": sender}
