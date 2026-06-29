#!/usr/bin/env python3
"""美东华人生活圈 — 双小红书（不同人设/画风）+ 公众号，Mon/Thu 09:30 ET。

XHS ×2 → christina600@gmail.com（干货清单局 + 种草生活局）
WeChat → mail.jing.huang@gmail.com, 1725490135@qq.com

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


def _parse_recipients(env_key: str, cfg_key: str, cfg: dict) -> list[str]:
    env = os.getenv(env_key, "").strip()
    if env:
        return [x.strip() for x in env.replace(";", ",").split(",") if x.strip()]
    return list(cfg.get(cfg_key) or [])


def _wechat_recipients(cfg: dict) -> list[str]:
    for key in ("USLIFEHUB_WECHAT_RECIPIENTS", "USLIFEHUB_SOCIAL_RECIPIENTS"):
        env = os.getenv(key, "").strip()
        if env:
            return [x.strip() for x in env.replace(";", ",").split(",") if x.strip()]
    return list(cfg.get("wechat_recipients") or cfg.get("recipients") or [])


def _xhs_recipients(cfg: dict) -> list[str]:
    return _parse_recipients("USLIFEHUB_XHS_RECIPIENTS", "xhs_recipients", cfg)


def _out_dir(campaign_id: str) -> Path:
    safe = campaign_id.replace("/", "-")
    return ROOT / "outputs" / f"uslifehub_social_{safe}"


def _apply_logo() -> None:
    import social_images as si

    si.FROZEN_WECHAT_DEFAULT = Path("__none__")
    logo = ROOT / "assets" / "uslifehub_logo.png"
    if not logo.exists():
        logo = ROOT / "assets" / "nextvivo_logo.png"
    if logo.exists():
        si.LOGO_PATH = logo


def _apply_visual_style(style: str, *, wechat: bool = False) -> None:
    import social_images as si

    style = (style or "").strip()
    if not style:
        return
    suffix = (
        "Wide format 16:9 for WeChat article inline illustration. "
        if wechat
        else "Square format 1:1 (1024x1024), Xiaohongshu card layout. "
    )
    if wechat:
        si.WECHAT_INLINE_STYLE = style + suffix
    else:
        si.XHS_CARD_STYLE = style + suffix


def _setup_ad_bar(cfg: dict) -> Path:
    import wechat_ad_bar as wab

    ad = ROOT / cfg.get("ad_bar_config", "config/uslifehub_wechat_ad_bar.yaml")
    if ad.exists():
        wab.DEFAULT_CONFIG = ad
    return ad


def stage_wechat_images(social_data: dict, img_root: Path, *, force: bool, ad_bar: Path) -> None:
    from social_images import (
        generate_wechat_ad_banner,
        generate_wechat_cover,
        generate_wechat_images,
    )

    wx_dir = img_root / "wechat"
    if force and wx_dir.exists():
        shutil.rmtree(wx_dir)
    wx_dir.mkdir(parents=True, exist_ok=True)
    print("=== Stage: WeChat cover + inline + ad bar ===")
    generate_wechat_cover(social_data, wx_dir, force=force)
    generate_wechat_images(social_data, wx_dir, force=force, inline_sections=[1, 2, 3])
    generate_wechat_ad_banner(wx_dir, force=force, ad_bar_config=ad_bar if ad_bar.exists() else None)


def stage_xhs_variant_images(
    social_data: dict,
    img_root: Path,
    variant_id: str,
    variant_style: str,
    *,
    force: bool,
) -> Path:
    from social_images import generate_xhs_images

    _apply_visual_style(variant_style, wechat=False)
    xhs_dir = img_root / f"xhs_{variant_id}"
    if force and xhs_dir.exists():
        shutil.rmtree(xhs_dir)
    label = social_data.get("_meta", {}).get("variant_label", variant_id)
    print(f"=== Stage: XHS [{label}] 6 cards (gpt-image-2 → Nano Banana Pro) ===")
    generate_xhs_images(social_data, xhs_dir, force=force)
    return xhs_dir


def main() -> int:
    ap = argparse.ArgumentParser(description="US Life Hub dual XHS + WeChat Mon/Thu delivery")
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
    _apply_logo()
    ad_bar = _setup_ad_bar(cfg)
    wechat_recipients = _wechat_recipients(cfg)
    xhs_recipients = _xhs_recipients(cfg)
    variants = list(cfg.get("xhs_variants") or [])
    campaign_id = args.campaign_id or _campaign_id()
    out_dir = _out_dir(campaign_id)
    out_dir.mkdir(parents=True, exist_ok=True)
    hub_index = args.hub_index or ROOT / cfg.get("hub_index", "insynbio-web-source/hub_search_index.json")

    print(f"\n{'='*60}")
    print(f"  美东华人生活圈 · 双小红书 + 公众号 — {campaign_id}")
    print(f"  XHS ({len(xhs_recipients)}): {xhs_recipients} × {len(variants)} variants")
    print(f"  WeChat ({len(wechat_recipients)}): {wechat_recipients}")
    print(f"  Deliver: XHS={do_xhs} WeChat={do_wechat}")
    print(f"{'='*60}\n")

    wechat_path = out_dir / "social_wechat.json"
    img_root = out_dir / "social_images"
    meta = {"campaign_id": campaign_id, "title": "美东华人生活圈本周精选"}

    from send_email import send_uslifehub_wechat_report, send_uslifehub_xhs_report

    if args.emails_only:
        if do_wechat and not wechat_path.exists():
            raise FileNotFoundError(f"Missing {wechat_path} — run full pipeline first")
        if do_xhs:
            for variant in variants:
                vid = variant.get("id", "xhs")
                vpath = out_dir / f"social_xhs_{vid}.json"
                if not vpath.exists():
                    raise FileNotFoundError(f"Missing {vpath}")
    else:
        from uslifehub_wechat_content import build_wechat_from_hub, build_xhs_variant_from_hub

        wechat_style = (cfg.get("wechat_visual_style") or cfg.get("visual_style") or "").strip()
        if do_wechat:
            _apply_visual_style(wechat_style, wechat=True)
            wechat_data = build_wechat_from_hub(hub_index, wechat_path, cfg, campaign_id)
            stage_wechat_images(wechat_data, img_root, force=args.force_images, ad_bar=ad_bar)
            (out_dir / "social.json").write_text(
                json.dumps(wechat_data, ensure_ascii=False, indent=2), encoding="utf-8"
            )

        if do_xhs:
            used_event_ids: set[str] = set()
            for variant in variants:
                vid = variant.get("id", "xhs")
                vpath = out_dir / f"social_xhs_{vid}.json"
                xhs_data = build_xhs_variant_from_hub(
                    hub_index,
                    vpath,
                    variant,
                    campaign_id,
                    exclude_event_ids=used_event_ids if used_event_ids else None,
                )
                xhs_data.setdefault("_meta", {})["variant_id"] = vid
                xhs_data["_meta"]["variant_label"] = variant.get("label", vid)
                vpath.write_text(json.dumps(xhs_data, ensure_ascii=False, indent=2), encoding="utf-8")
                for ev in xhs_data.get("_meta", {}).get("source_event_ids") or []:
                    used_event_ids.add(str(ev))
                stage_xhs_variant_images(
                    xhs_data,
                    img_root,
                    vid,
                    variant.get("visual_style", ""),
                    force=args.force_images,
                )

    if do_wechat and wechat_recipients:
        wechat_data = json.loads(wechat_path.read_text(encoding="utf-8"))
        print("=== Stage: Email — 微信公众号 ===")
        send_uslifehub_wechat_report(
            article=meta,
            social_data=wechat_data,
            img_dir=img_root / "wechat",
            recipients=wechat_recipients,
            week_tag=campaign_id,
        )

    if do_xhs and xhs_recipients:
        for variant in variants:
            vid = variant.get("id", "xhs")
            vpath = out_dir / f"social_xhs_{vid}.json"
            xhs_data = json.loads(vpath.read_text(encoding="utf-8"))
            tag = variant.get("mail_subject_tag") or variant.get("label") or vid
            print(f"=== Stage: Email — 小红书 [{tag}] ===")
            send_uslifehub_xhs_report(
                article=meta,
                social_data=xhs_data,
                img_dir=img_root / f"xhs_{vid}",
                recipients=xhs_recipients,
                week_tag=campaign_id,
                variant_label=tag,
            )

    n_xhs_mail = len(variants) if do_xhs else 0
    n_wx_mail = 1 if do_wechat else 0
    print(
        f"\n✅ Done — {campaign_id}: "
        f"{n_xhs_mail} XHS email(s) → {len(xhs_recipients)} recipient(s); "
        f"{n_wx_mail} WeChat email(s) → {len(wechat_recipients)} recipient(s)"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
