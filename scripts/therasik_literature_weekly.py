#!/usr/bin/env python3
"""Therasik weekly: AI drug-design literature → XHS + WeChat → email.

Usage:
  python scripts/therasik_literature_weekly.py
  python scripts/therasik_literature_weekly.py --replay-bundle therasik_ai_drug_design_2026
  python scripts/therasik_literature_weekly.py --emails-only
  python scripts/therasik_literature_weekly.py --wechat-only
  python scripts/therasik_literature_weekly.py --force-images
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


def _load_config() -> dict:
    cfg_path = ROOT / "config" / "therasik_literature_weekly.yaml"
    return yaml.safe_load(cfg_path.read_text(encoding="utf-8"))


def _recipients(cfg: dict) -> list[str]:
    env = os.getenv("THERASIK_LITERATURE_RECIPIENTS", "").strip()
    if env:
        return [x.strip() for x in env.split(",") if x.strip()]
    return list(cfg.get("recipients") or ["mail.jing.huang@gmail.com"])


def _out_dir(cfg: dict) -> Path:
    return ROOT / "outputs" / f"therasik_literature_{WEEK_TAG}"


def _resolve_logo(cfg: dict) -> Path:
    brand = cfg.get("brand") or {}
    for key in ("logo_path", "logo_fallback"):
        rel = brand.get(key)
        if rel:
            p = ROOT / rel
            if p.exists():
                return p
    return ROOT / "assets" / "nextvivo_logo.png"


def _apply_brand_patches(cfg: dict) -> None:
    import social_images as si
    import wechat_ad_bar as wab

    style = (cfg.get("visual_style") or "").strip()
    if style:
        suffix_xhs = "Square format 1:1 (1024x1024), Xiaohongshu card layout. "
        suffix_wx = "Wide format 16:9 for WeChat article inline illustration. "
        si.XHS_CARD_STYLE = style + suffix_xhs
        si.WECHAT_INLINE_STYLE = style + suffix_wx

    si.LOGO_PATH = _resolve_logo(cfg)
    si.FROZEN_WECHAT_DEFAULT = Path("__none__")
    ad_cfg = ROOT / (cfg.get("paths") or {}).get("ad_bar_config", "config/therasik_wechat_ad_bar.yaml")
    if ad_cfg.exists():
        wab.DEFAULT_CONFIG = ad_cfg


def _social_system_prompt(cfg: dict) -> str:
    from social_content import SPEC

    writer = (cfg.get("social_writer") or "").strip()
    return writer + "\n\n## 平台格式规范\n" + SPEC


def stage_pubmed(cfg: dict, cache_path: Path) -> dict:
    import pubmed_fetch as pf

    pub = cfg.get("pubmed") or {}
    pf.SEARCH_QUERY = pub.get("search_query", pf.SEARCH_QUERY)
    pf.SCORER_SYSTEM = pub.get("scorer_system", pf.SCORER_SYSTEM)
    print("=== Stage 1: PubMed (AI drug design) ===")
    return pf.get_weekly_article(cache_path=str(cache_path))


def stage_social(article: dict, out_path: Path, cfg: dict) -> dict:
    from social_content import generate_social_content

    print("=== Stage 2: Social content (Therasik) ===")
    ad_cfg = ROOT / (cfg.get("paths") or {}).get("ad_bar_config", "config/therasik_wechat_ad_bar.yaml")
    return generate_social_content(
        article,
        out_path,
        system_prompt=_social_system_prompt(cfg),
        ad_bar_config=ad_cfg if ad_cfg.exists() else None,
    )


def stage_social_images(social_data: dict, out_dir: Path, *, force: bool, frozen_wechat: Path | None):
    from social_images import generate_all_images

    print("=== Stage 3: Social images (gpt-image-2 → Nano Banana Pro) ===")
    if force and out_dir.exists():
        shutil.rmtree(out_dir)
    generate_all_images(
        social_data,
        out_dir,
        force=force,
        frozen_wechat_dir=frozen_wechat,
        slide_dir=None,
        inline_sections=[1, 2, 3],
        ad_bar_config=ROOT / "config" / "therasik_wechat_ad_bar.yaml",
    )


def stage_emails(article: dict, social_data: dict, out_dir: Path, recipients: list[str]):
    from send_email import send_therasik_xhs_report, send_therasik_wechat_report

    print("=== Stage 4: Email XHS + WeChat ===")
    send_therasik_xhs_report(
        article=article,
        social_data=social_data,
        img_dir=out_dir / "social_images" / "xhs",
        recipients=recipients,
        week_tag=WEEK_TAG,
    )
    send_therasik_wechat_report(
        article=article,
        social_data=social_data,
        img_dir=out_dir / "social_images" / "wechat",
        recipients=recipients,
        week_tag=WEEK_TAG,
    )


def _load_bundle(slug_or_path: str | Path) -> Path:
    p = Path(slug_or_path)
    if p.is_absolute() or p.exists():
        bundle = p
    else:
        bundle = ROOT / "data" / "frozen" / p
    if not bundle.is_dir():
        raise FileNotFoundError(f"Frozen bundle not found: {bundle}")
    return bundle


def main() -> int:
    ap = argparse.ArgumentParser(description="Therasik AI drug-design literature weekly")
    ap.add_argument("--replay-bundle", type=str, default=None)
    ap.add_argument("--force-images", action="store_true")
    ap.add_argument("--emails-only", action="store_true")
    ap.add_argument("--wechat-only", action="store_true")
    args = ap.parse_args()

    cfg = _load_config()
    _apply_brand_patches(cfg)
    recipients = _recipients(cfg)
    out_dir = _out_dir(cfg)
    out_dir.mkdir(parents=True, exist_ok=True)
    cache_path = ROOT / (cfg.get("paths") or {}).get("cache", "outputs/therasik_literature_cache.json")

    print(f"\n{'='*60}")
    print(f"  Therasik AI Drug Design Literature — {WEEK_TAG}")
    print(f"  Output: {out_dir.relative_to(ROOT)}")
    print(f"  Recipients: {recipients}")
    print(f"{'='*60}\n")

    frozen_default = cfg.get("paths", {}).get("frozen_default", "")
    bundle_slug = args.replay_bundle or frozen_default

    if args.wechat_only:
        bundle = _load_bundle(args.replay_bundle or frozen_default)
        article = json.loads((bundle / "article.json").read_text(encoding="utf-8"))
        social_data = json.loads((bundle / "social.json").read_text(encoding="utf-8"))
        wx_dir = out_dir / "social_images" / "wechat"
        wx_dir.mkdir(parents=True, exist_ok=True)
        frozen_wx = bundle / "wechat" if (bundle / "wechat").is_dir() else None
        from social_images import generate_wechat_images, generate_wechat_cover, generate_wechat_ad_banner

        ad_cfg_path = ROOT / "config" / "therasik_wechat_ad_bar.yaml"
        generate_wechat_cover(social_data, wx_dir, force=True, frozen_dir=frozen_wx)
        generate_wechat_images(social_data, wx_dir, force=True, frozen_dir=frozen_wx, inline_sections=[1, 2, 3])
        generate_wechat_ad_banner(wx_dir, force=True, frozen_dir=frozen_wx, ad_bar_config=ad_cfg_path)
        from send_email import send_therasik_wechat_report

        send_therasik_wechat_report(article, social_data, wx_dir, recipients, WEEK_TAG)
        print(f"\n✅ WeChat email sent — {WEEK_TAG}")
        return 0

    if args.emails_only:
        bundle = _load_bundle(bundle_slug)
        article = json.loads((bundle / "article.json").read_text(encoding="utf-8"))
        social_data = json.loads((bundle / "social.json").read_text(encoding="utf-8"))
        stage_emails(article, social_data, out_dir, recipients)
        print(f"\n✅ Emails sent — {WEEK_TAG}")
        return 0

    frozen_wechat = None
    if args.replay_bundle:
        bundle = _load_bundle(args.replay_bundle)
        article = json.loads((bundle / "article.json").read_text(encoding="utf-8"))
        social_data = json.loads((bundle / "social.json").read_text(encoding="utf-8"))
        frozen_wechat = bundle / "wechat" if (bundle / "wechat").is_dir() else None
        (out_dir / "article.json").write_text(json.dumps(article, ensure_ascii=False, indent=2), encoding="utf-8")
        (out_dir / "social.json").write_text(json.dumps(social_data, ensure_ascii=False, indent=2), encoding="utf-8")
        print(f"  Loaded frozen bundle: {bundle.name}")
    else:
        article = stage_pubmed(cfg, cache_path)
        preview = {k: v for k, v in article.items() if k != "full_text"}
        preview["full_text_chars"] = article.get("full_text_chars", 0)
        (out_dir / "article.json").write_text(json.dumps(preview, ensure_ascii=False, indent=2), encoding="utf-8")
        social_data = stage_social(article, out_dir / "social.json", cfg)

    stage_social_images(social_data, out_dir / "social_images", force=args.force_images, frozen_wechat=frozen_wechat)
    stage_emails(article, social_data, out_dir, recipients)
    print(f"\n✅ Done — {WEEK_TAG}")
    print(f"   Social: {out_dir / 'social.json'}")
    print(f"   Emails: 2 sent to {recipients}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
