#!/usr/bin/env python3
"""美东华人生活圈 — 微信公众号每周两次（Mon/Thu）→ 邮件交付包。

Recipients (default): mail.jing.huang@gmail.com, 1725490135@qq.com

Usage:
  python scripts/uslifehub_wechat_weekly.py
  python scripts/uslifehub_wechat_weekly.py --emails-only
  python scripts/uslifehub_wechat_weekly.py --force-images
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

WEEK_TAG = datetime.now(timezone.utc).strftime("%G-W%V")


def _campaign_id() -> str:
    """Align with subscriber newsletter Mon/Thu campaigns."""
    now = datetime.now()
    year, week, weekday = now.isocalendar()
    if weekday in (1, 2, 3):
        return f"{year}-W{week:02d}-Mon"
    return f"{year}-W{week:02d}-Thu"


def _load_cfg() -> dict:
    return yaml.safe_load((ROOT / "config" / "uslifehub_wechat.yaml").read_text(encoding="utf-8"))


def _recipients(cfg: dict) -> list[str]:
    env = os.getenv("USLIFEHUB_WECHAT_RECIPIENTS", "").strip()
    if env:
        return [x.strip() for x in env.replace(";", ",").split(",") if x.strip()]
    return list(cfg.get("recipients") or [])


def _out_dir(campaign_id: str) -> Path:
    safe = campaign_id.replace("/", "-")
    return ROOT / "outputs" / f"uslifehub_wechat_{safe}"


def _apply_visual_brand(cfg: dict) -> None:
    import social_images as si
    import wechat_ad_bar as wab

    style = (cfg.get("visual_style") or "").strip()
    if style:
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


def stage_images(social_data: dict, img_dir: Path, *, force: bool, ad_bar: Path) -> None:
    from social_images import (
        generate_wechat_ad_banner,
        generate_wechat_cover,
        generate_wechat_images,
    )

    wx_dir = img_dir / "wechat"
    if force and wx_dir.exists():
        shutil.rmtree(wx_dir)
    wx_dir.mkdir(parents=True, exist_ok=True)
    generate_wechat_cover(social_data, wx_dir, force=force)
    generate_wechat_images(social_data, wx_dir, force=force, inline_sections=[1, 2, 3])
    generate_wechat_ad_banner(wx_dir, force=force, ad_bar_config=ad_bar if ad_bar.exists() else None)


def stage_email(social_data: dict, img_dir: Path, recipients: list[str], campaign_id: str) -> None:
    from send_email import send_uslifehub_wechat_report

    meta = {"campaign_id": campaign_id, "title": "美东华人生活圈本周精选"}
    send_uslifehub_wechat_report(
        article=meta,
        social_data=social_data,
        img_dir=img_dir / "wechat",
        recipients=recipients,
        week_tag=campaign_id,
    )


def main() -> int:
    ap = argparse.ArgumentParser(description="US Life Hub WeChat weekly delivery")
    ap.add_argument("--force-images", action="store_true")
    ap.add_argument("--emails-only", action="store_true")
    ap.add_argument("--campaign-id", default=None)
    ap.add_argument("--hub-index", type=Path, default=None)
    args = ap.parse_args()

    cfg = _load_cfg()
    _apply_visual_brand(cfg)
    recipients = _recipients(cfg)
    campaign_id = args.campaign_id or _campaign_id()
    out_dir = _out_dir(campaign_id)
    out_dir.mkdir(parents=True, exist_ok=True)
    ad_bar = ROOT / cfg.get("ad_bar_config", "config/uslifehub_wechat_ad_bar.yaml")
    hub_index = args.hub_index or ROOT / cfg.get("hub_index", "insynbio-web-source/hub_search_index.json")

    print(f"\n{'='*60}")
    print(f"  美东华人生活圈 · 微信公众号 — {campaign_id}")
    print(f"  Recipients: {recipients}")
    print(f"  Hub index: {hub_index}")
    print(f"{'='*60}\n")

    social_path = out_dir / "social.json"

    if args.emails_only:
        if not social_path.exists():
            raise FileNotFoundError(f"Missing {social_path} — run full pipeline first")
        social_data = json.loads(social_path.read_text(encoding="utf-8"))
    else:
        from uslifehub_wechat_content import build_from_hub

        social_data = build_from_hub(hub_index, social_path, cfg, campaign_id)
        stage_images(social_data, out_dir / "social_images", force=args.force_images, ad_bar=ad_bar)

    stage_email(social_data, out_dir / "social_images", recipients, campaign_id)
    print(f"\n✅ WeChat delivery email sent — {campaign_id} → {recipients}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
