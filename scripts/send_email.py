"""
send_email.py — Send weekly PPT report via SMTP.

Supports: QQ Mail, Gmail, and any SMTP server.
Attaches PPTX + MP4 (if under 20MB), otherwise provides download link.
"""

import os, smtplib, json, io
from pathlib import Path

# Load .env
for _env in [Path(__file__).parent.parent / "content_generation_tools" / ".env",
             Path(__file__).parent.parent / ".env"]:
    if _env.exists():
        for _l in _env.read_text(encoding="utf-8").splitlines():
            _l = _l.strip()
            if _l and not _l.startswith("#") and "=" in _l:
                _k, _v = _l.split("=", 1)
                os.environ.setdefault(_k.strip(), _v.strip())
        break
from email.mime.multipart import MIMEMultipart
from email.mime.text      import MIMEText
from email.mime.base      import MIMEBase
from email                import encoders
from datetime             import datetime

MAX_ATTACH_MB   = 20  # skip attachment if file > 20MB
MAX_EMAIL_MB    = 14  # QA gate: total email size limit before sending
IMG_MAX_PX      = 1080  # max width/height for compressed attachments
IMG_JPEG_Q      = 85    # JPEG quality for compressed images


def _compress_image(path: Path, max_px: int = IMG_MAX_PX) -> tuple[bytes, str]:
    """Resize to ≤max_px then encode as JPEG q85 for minimal email size.

    Returns (compressed_bytes, '.jpg').
    """
    from PIL import Image
    img = Image.open(path).convert("RGB")
    w, h = img.size
    if max(w, h) > max_px:
        scale = max_px / max(w, h)
        img   = img.resize((int(w * scale), int(h * scale)), Image.LANCZOS)
        print(f"    resized {w}×{h} → {img.width}×{img.height}")
    buf = io.BytesIO()
    img.save(buf, "JPEG", quality=IMG_JPEG_Q, optimize=True)
    kb_orig = path.stat().st_size // 1024
    kb_new  = len(buf.getvalue()) // 1024
    print(f"    compressed {kb_orig}KB → {kb_new}KB (JPEG q{IMG_JPEG_Q})")
    return buf.getvalue(), ".jpg"


def _smtp_configs() -> list[dict]:
    """
    Return an ordered list of SMTP configs to try.
    Priority: Gmail → Private Email (therasik/insynbio) → QQ Mail.
    """
    configs = []

    gmail_pass = os.getenv("GMAIL_APP_PASSWORD", "")
    if gmail_pass:
        configs.append({
            "label":    "Gmail",
            "host":     "smtp.gmail.com",
            "port":     587,
            "user":     os.getenv("GMAIL_USER", "mail.jing.huang@gmail.com"),
            "password": gmail_pass,
            "use_tls":  True,
            "use_ssl":  False,
        })

    host = os.getenv("SMTP_HOST") or os.getenv("INSYNBIO_SMTP_HOST")
    smtp_pass = os.getenv("SMTP_PASSWORD") or os.getenv("INSYNBIO_SMTP_PASS", "")
    if host and smtp_pass:
        use_ssl = os.getenv("SMTP_SSL", "false").lower() == "true"
        port = int(os.getenv("SMTP_PORT", "465" if use_ssl else "587"))
        use_tls = os.getenv("SMTP_TLS", "false" if use_ssl else "true").lower() == "true"

        primary_user = os.getenv("SMTP_USER") or os.getenv("INSYNBIO_SMTP_USER", "")
        if primary_user:
            configs.append({
                "label":    primary_user,
                "host":     host,
                "port":     port,
                "user":     primary_user,
                "password": smtp_pass,
                "use_tls":  use_tls,
                "use_ssl":  use_ssl,
            })

        fallback_user = os.getenv("SMTP_FALLBACK_USER", "")
        if fallback_user and fallback_user != primary_user:
            configs.append({
                "label":    fallback_user,
                "host":     host,
                "port":     port,
                "user":     fallback_user,
                "password": smtp_pass,
                "use_tls":  use_tls,
                "use_ssl":  use_ssl,
            })

    qq_pass = os.getenv("QQ_SMTP_PASSWORD", "")
    if qq_pass:
        configs.append({
            "label":    "QQMail",
            "host":     "smtp.qq.com",
            "port":     465,
            "user":     os.getenv("QQ_SMTP_USER", "1725490135@qq.com"),
            "password": qq_pass,
            "use_tls":  False,
            "use_ssl":  True,
        })

    if not configs:
        raise RuntimeError(
            "No SMTP config found. Set one of: GMAIL_APP_PASSWORD, SMTP_HOST+SMTP_PASSWORD, or QQ_SMTP_PASSWORD"
        )
    return configs


def _attach_file(msg: MIMEMultipart, path: Path, filename: str, compress: bool = False):
    size_mb = path.stat().st_size / 1024 / 1024
    if size_mb > MAX_ATTACH_MB:
        print(f"  [SKIP] {filename} too large ({size_mb:.1f}MB > {MAX_ATTACH_MB}MB), not attaching")
        return False
    if compress and path.suffix.lower() in (".png", ".jpg", ".jpeg"):
        data, ext = _compress_image(path)
        filename  = Path(filename).stem + ext  # keep .png
    else:
        data = path.read_bytes()
    part = MIMEBase("application", "octet-stream")
    part.set_payload(data)
    encoders.encode_base64(part)
    part.add_header("Content-Disposition", f'attachment; filename="{filename}"')
    msg.attach(part)
    kb = len(data) / 1024
    print(f"  Attached: {filename} ({kb:.0f}KB)")
    return True


def _qa_check_size(msg: MIMEMultipart, label: str):
    """Fail fast if email exceeds safe size before sending."""
    import email
    raw = msg.as_bytes()
    mb  = len(raw) / 1024 / 1024
    if mb > MAX_EMAIL_MB:
        raise RuntimeError(
            f"QA GATE FAIL — {label} email is {mb:.1f}MB > {MAX_EMAIL_MB}MB limit. "
            f"Reduce image attachments before sending."
        )
    print(f"  QA size check: {mb:.1f}MB ✅ (limit {MAX_EMAIL_MB}MB)")


def _build_html(article: dict, audit_pass: bool, week_tag: str,
                pptx_attached: bool, mp4_attached: bool) -> str:
    audit_badge = (
        '<span style="color:#27ae60;font-weight:bold">✅ 视觉审计通过</span>'
        if audit_pass else
        '<span style="color:#e74c3c;font-weight:bold">⚠️ 审计发现问题（见附件报告）</span>'
    )
    attachments = []
    if pptx_attached: attachments.append("📊 PPTX 演示文稿")
    if mp4_attached:  attachments.append("🎬 MP4 抖音视频")
    attach_html = "<br>".join(attachments) if attachments else "（文件过大，请在 GitHub Actions artifacts 下载）"

    return f"""
<html><body style="font-family:Arial,sans-serif;max-width:700px;margin:auto">
<h2 style="color:#1a5276">🧬 NextVivo 每周人源化小鼠科研简报 — {week_tag}</h2>
<hr>
<h3>本周精选文章</h3>
<table style="border-collapse:collapse;width:100%">
  <tr><td style="padding:6px;font-weight:bold;width:120px">标题</td>
      <td style="padding:6px">{article['title']}</td></tr>
  <tr style="background:#f2f2f2">
      <td style="padding:6px;font-weight:bold">作者</td>
      <td style="padding:6px">{article.get('authors','')}</td></tr>
  <tr><td style="padding:6px;font-weight:bold">期刊</td>
      <td style="padding:6px">{article.get('journal','')} ({article.get('year','')})</td></tr>
  <tr style="background:#f2f2f2">
      <td style="padding:6px;font-weight:bold">PMID</td>
      <td style="padding:6px"><a href="{article.get('url','#')}">{article['pmid']}</a></td></tr>
  <tr><td style="padding:6px;font-weight:bold">DOI</td>
      <td style="padding:6px">{article.get('doi','N/A')}</td></tr>
</table>

<h3>摘要</h3>
<p style="color:#444;line-height:1.6">{article.get('abstract','')[:600]}...</p>

<h3>本次输出</h3>
<p>{attach_html}</p>
<p>质量审计：{audit_badge}</p>

<hr>
<p style="font-size:12px;color:#888">
本邮件由 NextVivo Biotech 自动化内容流水线生成。<br>
数据来源：PubMed | 图像：gpt-image-2 / CogView-4 | 审计：Gemini Vision<br>
如有问题请联系 mail.jing.huang@gmail.com
</p>
</body></html>
"""


def send_weekly_report(
    article: dict,
    pptx_path: Path,
    mp4_path: Path,
    audit_pass: bool,
    recipients: list,
    week_tag: str,
    mp4_vertical_path: "Path | None" = None,
):
    sender = _smtp_configs()[0]["user"]

    msg = MIMEMultipart("mixed")
    msg["From"]    = f"NextVivo Pipeline <{sender}>"
    msg["To"]      = ", ".join(recipients)
    topic = article.get("series_title") or article["title"][:40]
    msg["Subject"] = f"【NextVivo】{article.get('series','每周简报')} {week_tag} — {topic}..."

    html = _build_html(article, audit_pass, week_tag,
                       pptx_path.exists(), mp4_path.exists())
    msg.attach(MIMEText(html, "html", "utf-8"))

    pptx_attached = False
    mp4_attached  = False
    mp4v_attached = False
    if pptx_path.exists():
        pptx_attached = _attach_file(msg, pptx_path, pptx_path.name)
    if mp4_path.exists():
        mp4_attached  = _attach_file(msg, mp4_path,  mp4_path.name)
    if mp4_vertical_path and mp4_vertical_path.exists():
        mp4v_attached = _attach_file(msg, mp4_vertical_path,
                                     mp4_vertical_path.name,
                                     compress=False)

    # Rebuild HTML with correct attachment status
    for part in msg.get_payload():
        if isinstance(part, MIMEText):
            msg.get_payload().remove(part)
            break
    html = _build_html(article, audit_pass, week_tag, pptx_attached, mp4_attached)
    msg.attach(MIMEText(html, "html", "utf-8"))
    _smtp_send(msg, recipients)

def _smtp_send(msg: MIMEMultipart, recipients: list):
    """Try every available SMTP config in priority order until one succeeds."""
    configs = _smtp_configs()
    # Override sender to the first config's user if the passed sender is empty
    for c in configs:
        label = c.get("label", c["host"])
        print(f"  Trying {label} ({c['user']}) → {recipients}")
        try:
            if c.get("use_ssl"):
                with smtplib.SMTP_SSL(c["host"], c["port"]) as s:
                    s.login(c["user"], c["password"])
                    msg.replace_header("From", f"NextVivo Pipeline <{c['user']}>")
                    s.sendmail(c["user"], recipients, msg.as_string())
            else:
                with smtplib.SMTP(c["host"], c["port"]) as s:
                    if c.get("use_tls"):
                        s.starttls()
                    s.login(c["user"], c["password"])
                    msg.replace_header("From", f"NextVivo Pipeline <{c['user']}>")
                    s.sendmail(c["user"], recipients, msg.as_string())
            print(f"  ✅ Email sent via {label}")
            return
        except Exception as e:
            print(f"  ❌ {label} failed: {e}")
    print("  ❌ All SMTP routes exhausted — email not delivered")


IMG_EMBED_PX = 800   # CID inline display size (compressed JPEG)


def _embed_image_cid(msg_root: MIMEMultipart, img_path: Path, cid: str,
                     compress: bool = False) -> bool:
    """Embed image inline via Content-ID (QQ/Gmail preview friendly).
    
    compress=True: resize to IMG_EMBED_PX and encode as JPEG q85.
    """
    if not img_path.exists():
        return False
    if compress:
        data, _ = _compress_image(img_path, max_px=IMG_EMBED_PX)
    else:
        data = img_path.read_bytes()
    img = MIMEBase("image", "jpeg" if compress else "png")
    img.set_payload(data)
    encoders.encode_base64(img)
    img.add_header("Content-ID", f"<{cid}>")
    img.add_header("Content-Disposition", "inline", filename=img_path.name)
    msg_root.attach(img)
    return True


def send_xhs_report(article: dict, social_data: dict, img_dir: Path,
                    recipients: list, week_tag: str):
    """Email 2: XHS — 6 card images inline + ASCII attachments."""
    from email.mime.multipart import MIMEMultipart as MMP

    sender = _smtp_configs()[0]["user"]
    xhs    = social_data.get("xiaohongshu", {})

    msg = MMP("related")
    msg["From"]    = f"NextVivo Pipeline <{sender}>"
    msg["To"]      = ", ".join(recipients)
    msg["Subject"] = f"【NextVivo 小红书】{week_tag} — {xhs.get('title','人源化小鼠')}"

    tags_str = "  ".join(xhs.get("tags", []))
    cards_html = ""
    for i, c in enumerate(xhs.get("cards", []), 1):
        cid = f"xhs_card_{i:02d}"
        img_tag = (
            f'<img src="cid:{cid}" style="max-width:100%;border:1px solid #eee;margin:8px 0"/>'
            if (img_dir / f"{cid}.png").exists() else
            f'<p style="color:red">[图片缺失: {cid}.png]</p>'
        )
        cards_html += (
            f"<h4>卡片 {i}：{c.get('title','')}</h4>"
            f"{img_tag}"
            f"<p>{c.get('body','')}</p>"
        )

    html = f"""<html><body style="font-family:Arial,sans-serif;max-width:700px;margin:auto">
<h2 style="color:#e74c3c">📱 小红书内容 — {week_tag}</h2>
<p><b>发布标题：</b>{xhs.get('title','')}</p>
<p><b>标签：</b>{tags_str}</p>
<hr>
<h3>正文（{len(xhs.get('body',''))} 字）</h3>
<p style="line-height:1.8;white-space:pre-wrap">{xhs.get('body','')}</p>
<hr>
<h3>6 张卡片（正文内嵌预览 + 附件可下载）</h3>{cards_html}
<hr>
<p style="font-size:11px;color:#888">来源文章：{article.get('title','')} | PMID {article.get('pmid','')} | DOI {article.get('doi','')}</p>
<p style="font-size:11px;color:#888">未来模式生物科技 · NextVivo</p>
</body></html>"""
    msg.attach(MIMEText(html, "html", "utf-8"))

    if img_dir.exists():
        for i in range(1, 7):
            img_path = img_dir / f"xhs_card_{i:02d}.png"
            cid = f"xhs_card_{i:02d}"
            if img_path.exists():
                _embed_image_cid(msg, img_path, cid, compress=True)
                _attach_file(msg, img_path, f"xhs_card_{i:02d}.jpg", compress=True)

    _smtp_send(msg, recipients)


def send_wechat_report(article: dict, social_data: dict, img_dir: Path,
                       recipients: list, week_tag: str):
    """Email 3: WeChat — full article + 3 images + ad bar."""
    from wechat_ad_bar import inject_ad_bar, render_ad_bar_html

    sender = _smtp_configs()[0]["user"]
    wx     = social_data.get("wechat", {})
    if not wx.get("ad_bar"):
        try:
            inject_ad_bar(social_data)
            wx = social_data["wechat"]
        except Exception:
            from wechat_ad_bar import ad_bar_dict
            wx["ad_bar"] = ad_bar_dict()

    from email.mime.multipart import MIMEMultipart as MMP

    # Top-level mixed container (file attachments go here)
    msg = MMP("mixed")
    msg["From"]    = f"NextVivo Pipeline <{sender}>"
    msg["To"]      = ", ".join(recipients)
    msg["Subject"] = f"【NextVivo 公众号】{week_tag} — {wx.get('title','人源化小鼠免疫评估')}"

    # Inner related: HTML + CID images (CID parts stay hidden from attachment panel)
    related = MMP("related")

    # Build sections HTML — one inline image after each corresponding section
    # wechat_inline_01 → 第一节, _02 → 第二节, _03 → 第三节 (1:1 mapping)
    _all_inline = sorted(img_dir.glob("wechat_inline_*.png")) if img_dir.exists() else []
    _sections   = wx.get("sections", [])
    _n          = len(_sections)
    _img_map: dict[int, Path] = {}
    for k, p in enumerate(_all_inline):
        if k < _n:
            _img_map[k] = p

    sections_html = ""
    for idx, sec in enumerate(_sections):
        sections_html += f"""
<h3 style="color:#1a5276">{sec.get('heading','')}</h3>
<p style="line-height:1.8">{sec.get('body','')}</p>"""
        if idx in _img_map:
            _cid = _img_map[idx].stem
            sections_html += f"""
<p style="text-align:center;margin:12px 0">
  <img src="cid:{_cid}" alt="配图" style="max-width:100%;border-radius:6px"/>
</p>"""

    total_chars = (len(wx.get("lead","")) +
                   sum(len(s.get("body","")) for s in wx.get("sections",[])) +
                   len(wx.get("closing","")))
    cover_digest = wx.get("cover_digest", "")
    cover_path = img_dir / "wechat_cover.png"
    cover_block = ""
    if cover_path.exists():
        cover_block = f"""
<div style="margin:0 0 20px;padding:16px;background:#fffbeb;border:1px solid #fbbf24;border-radius:8px">
  <p style="margin:0 0 8px;font-weight:bold;color:#92400e">📎 发布用「封面图」（群聊外链预览 · 正文内不显示）</p>
  <p style="margin:0 0 10px;font-size:13px;color:#78350f">
    后台上传 <code>wechat_cover.png</code> 为封面，并<strong>取消勾选「封面显示在正文中」</strong>。
  </p>
  <p style="text-align:center"><img src="cid:wechat_cover" alt="封面图"
     style="max-width:100%;border:1px solid #e5e7eb;border-radius:6px"/></p>
  <p style="margin:10px 0 0;font-size:13px;color:#374151"><b>建议摘要：</b>{cover_digest}</p>
</div>"""

    html = f"""<html><body style="font-family:Arial,sans-serif;max-width:700px;margin:auto">
<h2 style="color:#1a5276">📰 微信公众号内容 — {week_tag}</h2>
<p><b>标题：</b>{wx.get('title','')}</p>
<p><b>副标题：</b>{wx.get('subtitle','')}</p>
<p style="font-size:12px;color:#666">总字数：{total_chars} 字</p>
{cover_block}
<hr>
<h3 style="color:#64748b;font-size:14px">↓ 以下为点开文章后的正文（不含封面图）</h3>
<h3>导语</h3>
<p style="line-height:1.8">{wx.get('lead','')}</p>
{sections_html}
<h3>结语</h3>
<p style="line-height:1.8">{wx.get('closing','')}</p>
{render_ad_bar_html(wx.get('ad_bar') or {}, embed_cid='wechat_ad_bar' if (img_dir / 'wechat_ad_bar.png').exists() else None)}
<hr>
<p style="font-size:11px;color:#888">来源：{article.get('title','')} | PMID {article.get('pmid','')} | DOI {article.get('doi','')}</p>
<p style="font-size:11px;color:#888">未来模式生物科技 · NextVivo</p>
</body></html>"""
    related.attach(MIMEText(html, "html", "utf-8"))

    # CID inline images go inside related (hidden from attachments panel in Gmail/QQ)
    # Order matches article body flow: inline → ad_bar → cover (cover last, not in body)
    if img_dir.exists():
        for p in _all_inline:
            _embed_image_cid(related, p, p.stem, compress=True)
        ad_path = img_dir / "wechat_ad_bar.png"
        if ad_path.exists():
            _embed_image_cid(related, ad_path, "wechat_ad_bar", compress=True)
        if cover_path.exists():
            _embed_image_cid(related, cover_path, "wechat_cover", compress=True)

    msg.attach(related)

    # File attachments — ordered by article flow for easy WeChat upload:
    # inline_01 → 02 → 03 (body images in order) → ad_bar (end of body) → cover (uploaded separately)
    attach_count = 0
    if img_dir.exists():
        for p in _all_inline:
            if _attach_file(msg, p, p.name, compress=True):
                attach_count += 1
        ad_pp = img_dir / "wechat_ad_bar.png"
        if ad_pp.exists() and _attach_file(msg, ad_pp, "wechat_ad_bar.png", compress=True):
            attach_count += 1
        cover_pp = img_dir / "wechat_cover.png"
        if cover_pp.exists() and _attach_file(msg, cover_pp, "wechat_cover.png", compress=True):
            attach_count += 1
    print(f"  WeChat email: {attach_count} downloadable attachments (no duplicates)")

    _qa_check_size(msg, "WeChat")
    _smtp_send(msg, recipients)


if __name__ == "__main__":
    # Quick test with dummy data
    send_weekly_report(
        article={"pmid": "12345678", "title": "Test article", "authors": "Test Author et al.",
                 "journal": "Nature", "year": "2026", "doi": "10.1038/test",
                 "url": "https://pubmed.ncbi.nlm.nih.gov/12345678/",
                 "abstract": "This is a test abstract."},
        pptx_path=Path("outputs/humanized_mice_final/humanized_mice_final.pptx"),
        mp4_path=Path("outputs/humanized_mice_final/humanized_mice_final.mp4"),
        audit_pass=True,
        recipients=["1725490135@qq.com", "mail.jing.huang@gmail.com"],
        week_tag="2026-W24",
    )

