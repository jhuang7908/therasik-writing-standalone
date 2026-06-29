#!/usr/bin/env python3
"""美东华人生活圈 — 小红书 + 公众号，每周两次（Mon/Thu）→ 各 1 封邮件 × 2 人。

Recipients: mail.jing.huang@gmail.com, 1725490135@qq.com

Usage:
  python scripts/uslifehub_wechat_weekly.py
  python scripts/uslifehub_wechat_weekly.py --emails-only
  python scripts/uslifehub_wechat_weekly.py --force-images
  python scripts/uslifehub_wechat_weekly.py --xhs-only
  python scripts/uslifehub_wechat_weekly.py --wechat-only
"""
from __future__ import annotations

import argparse
import json
import os
import shutil
import sys
from datetime import datetime, timezone
from pathlib import Path

import yaml

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "scripts"))

for _env in (ROOT / "content_generation_tools" / ".env", ROOT / ".env"):
    if _env.exists():
        for _line in _env.read_text(encoding="utf-8").splitlines():
            _line = _line.strip()
            if _line and not _line.startswith("#") and "=" in _line:
                k, v = _line.split("=", 1)
                os.environ.setdefault(k.strip(), v.strip())
        break


def _campaign_id() -> str:
    now = datetime.now()
    year, week, weekday = now.isocalendar()
    if weekday in (1, 2, 3):
        return f"{year}-W{week:02d}-Mon"
    return f"{year}-W{week:02d}-Thu"


def _load_cfg() -> dict:
    return yaml.safe_load((ROOT / "config" / "uslifehub_wechat.yaml").read_text(encoding="utf-8"))


def _recipients(cfg: dict) -> list[str]:
    for key in ("USLIFEHUB_SOCIAL_RECIPIENTS", "USLIFEHUB_WECHAT_RECIPIENTS"):
        env = os.getenv(key, "").strip()
        if env:
            return [x.strip() for x in env.replace(";", ",").split(",") if x.strip()]
    return list(cfg.get("recipients") or [])


def _out_dir(campaign_id: str) -> Path:
    safe = campaign_id.replace("/", "-")
    return ROOT / "outputs" / f"uslifehub_social_{safe}"


def _apply_visual_brand(cfg: dict) -> None:
    import social_images as si
    import wechat_ad_bar as wab

    style = (cfg.get("visual_style") or "").strip()
    if style:
        si.XHS_CARD_STYLE = style + "Square format 1:1 (1024x1024), Xiaohongshu card layout. "
        si.WECHAT_INLINE_STYLE = style + "Wide format 16:9 for WeChat article inline illustration. "
    si.FROZEN_WECHAT_DEFAULT = Path("__none__")
    ad = ROOT / cfg.get("ad_bar_config", "config/uslifehub_wechat_ad_bar.yaml")
    if ad.exists():
        wab.DEFAULT_CONFIG = ad
    logo = ROOT / "assets" / "uslifehub_logo.png"
    if not logo.exists():
        logo = ROOT / "assets" / "nextvivo_logo.png"
    if logo.exists():
        si.LOGO_PATH = logo


def stage_images(
    social_data: dict,
    img_root: Path,
    *,
    force: bool,
    ad_bar: Path,
    do_xhs: bool,
    do_wechat: bool,
) -> None:
    from social_images import (
        generate_wechat_ad_banner,
        generate_wechat_cover,
        generate_wechat_images,
        generate_xhs_images,
    )

    if force and img_root.exists():
        shutil.rmtree(img_root)
    img_root.mkdir(parents=True, exist_ok=True)

    if do_xhs:
        print("=== Stage: XHS 6 cards (gpt-image-2 → Nano Banana Pro) ===")
        generate_xhs_images(social_data, img_root / "xhs", force=force)

    if do_wechat:
        print("=== Stage: WeChat cover + inline + ad bar ===")
        wx_dir = img_root / "wechat"
        wx_dir.mkdir(parents=True, exist_ok=True)
        generate_wechat_cover(social_data, wx_dir, force=force)
        generate_wechat_images(social_data, wx_dir, force=force, inline_sections=[1, 2, 3])
        generate_wechat_ad_banner(wx_dir, force=force, ad_bar_config=ad_bar if ad_bar.exists() else None)


def stage_emails(
    social_data: dict,
    img_root: Path,
    recipients: list[str],
    campaign_id: str,
    *,
    do_xhs: bool,
    do_wechat: bool,
) -> None:
    from send_email import send_uslifehub_wechat_report, send_uslifehub_xhs_report

    meta = {"campaign_id": campaign_id, "title": "美东华人生活圈本周精选"}
    if do_xhs:
        print("=== Stage: Email — 小红书 ===")
        send_uslifehub_xhs_report(
            article=meta,
            social_data=social_data,
            img_dir=img_root / "xhs",
            recipients=recipients,
            week_tag=campaign_id,
        )
    if do_wechat:
        print("=== Stage: Email — 微信公众号 ===")
        send_uslifehub_wechat_report(
            article=meta,
            social_data=social_data,
            img_dir=img_root / "wechat",
            recipients=recipients,
            week_tag=campaign_id,
        )


def main() -> int:
    ap = argparse.ArgumentParser(description="US Life Hub XHS + WeChat Mon/Thu delivery")
    ap.add_argument("--force-images", action="store_true")
    ap.add_argument("--emails-only", action="store_true")
    ap.add_argument("--xhs-only", action="store_true")
    ap.add_argument("--wechat-only", action="store_true")
    ap.add_argument("--campaign-id", default=None)
    ap.add_argument("--hub-index", type=Path, default=None)
    args = ap.parse_args()

    do_xhs = not args.wechat_only
    do_wechat = not args.xhs_only

    cfg = _load_cfg()
    _apply_visual_brand(cfg)
    recipients = _recipients(cfg)
    campaign_id = args.campaign_id or _campaign_id()
    out_dir = _out_dir(campaign_id)
    out_dir.mkdir(parents=True, exist_ok=True)
    ad_bar = ROOT / cfg.get("ad_bar_config", "config/uslifehub_wechat_ad_bar.yaml")
    hub_index = args.hub_index or ROOT / cfg.get("hub_index", "insynbio-web-source/hub_search_index.json")

    print(f"\n{'='*60}")
    print(f"  美东华人生活圈 · 小红书 + 公众号 — {campaign_id}")
    print(f"  Recipients ({len(recipients)}): {recipients}")
    print(f"  Deliver: XHS={do_xhs} WeChat={do_wechat}")
    print(f"{'='*60}\n")

    social_path = out_dir / "social.json"
    img_root = out_dir / "social_images"

    if args.emails_only:
        if not social_path.exists():
            raise FileNotFoundError(f"Missing {social_path} — run full pipeline first")
        social_data = json.loads(social_path.read_text(encoding="utf-8"))
    else:
        from uslifehub_wechat_content import build_from_hub

        social_data = build_from_hub(hub_index, social_path, cfg, campaign_id)
        stage_images(
            social_data, img_root, force=args.force_images, ad_bar=ad_bar,
            do_xhs=do_xhs, do_wechat=do_wechat,
        )

    stage_emails(
        social_data, img_root, recipients, campaign_id,
        do_xhs=do_xhs, do_wechat=do_wechat,
    )
    n_mail = int(do_xhs) + int(do_wechat)
    print(f"\n✅ Done — {campaign_id}: {n_mail} email(s) × {len(recipients)} recipient(s)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
