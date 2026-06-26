#!/usr/bin/env python3
"""Run In-Vivo CAR series (episodes 2+3) on VPS with SSOT guard + fact-check + 3 emails each.

Usage:
  python scripts/run_invivo_car_series.py
  python scripts/run_invivo_car_series.py --bundle in_vivo_car_tech_2026
  python scripts/run_invivo_car_series.py --skip-images   # emails only (reuse cached assets)
"""
from __future__ import annotations

import argparse
import json
import os
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "scripts"))

# ── Load .env ────────────────────────────────────────────────────────────────
for _env in [ROOT / "content_generation_tools" / ".env", ROOT / ".env"]:
    if _env.exists():
        for _line in _env.read_text(encoding="utf-8").splitlines():
            _line = _line.strip()
            if _line and not _line.startswith("#") and "=" in _line:
                _k, _v = _line.split("=", 1)
                os.environ[_k.strip()] = _v.strip()
        break

RECIP = ["mail.jing.huang@gmail.com"]

SERIES = [
    {"slug": "in_vivo_car_tech_2026",     "label": "In-Vivo CAR 系列 1/2", "week": "2026-W24"},
    {"slug": "in_vivo_car_humouse_2026",  "label": "In-Vivo CAR 系列 2/2", "week": "2026-W25"},
]


def _load_bundle(slug: str) -> Path:
    p = ROOT / "data" / "frozen" / slug
    if not p.is_dir():
        raise FileNotFoundError(f"Frozen bundle not found: {p}")
    return p


def run_ssot_guard(bundle: Path, out_dir: Path) -> dict:
    """Kimi/DeepSeek third-party review + PubMed citation audit."""
    from content_ssot_guard import audit_citations, guarded_pipeline

    article = json.loads((bundle / "article.json").read_text(encoding="utf-8"))
    source  = article.get("abstract", "")
    reports = {}

    for fname in ("deck_spec.json", "social.json"):
        fpath = bundle / fname
        text  = fpath.read_text(encoding="utf-8")
        print(f"\n  [Guard] Citation audit: {fname}")
        cite = audit_citations(text)
        print(f"    citation status: {cite.get('status')}")
        if cite.get("status") == "FAIL":
            err_path = out_dir / f"cite_audit_FAIL_{Path(fname).stem}.json"
            err_path.write_text(json.dumps(cite, ensure_ascii=False, indent=2), encoding="utf-8")
            raise RuntimeError(f"Citation audit FAIL — see {err_path}")

        print(f"  [Guard] Kimi/DeepSeek review: {fname}")
        guard = guarded_pipeline(source, text, content_type="ppt", max_rounds=2)
        rpt_path = out_dir / f"rigor_report_{fname}"
        rpt_path.write_text(json.dumps(guard, ensure_ascii=False, indent=2), encoding="utf-8")
        print(f"    guard passed: {guard.get('passed')} → {rpt_path.name}")
        reports[fname] = guard

        if not guard.get("passed"):
            print(f"  [WARN] Guard did not fully PASS for {fname} — proceeding with reviewed SSOT")
            reviewed = guard.get("content_ssot")
            if reviewed and fname == "deck_spec.json":
                (out_dir / "deck_spec.json").write_text(reviewed, encoding="utf-8")
            elif reviewed and fname == "social.json":
                (out_dir / "social.json").write_text(reviewed, encoding="utf-8")

    return reports


def run_pipeline(slug: str, week: str, label: str, *, force_images: bool) -> None:
    import weekly_pipeline as wp

    bundle   = _load_bundle(slug)
    out_dir  = ROOT / "outputs" / f"weekly_{slug}"
    out_dir.mkdir(parents=True, exist_ok=True)

    article     = json.loads((bundle / "article.json").read_text(encoding="utf-8"))
    spec        = json.loads((bundle / "deck_spec.json").read_text(encoding="utf-8"))
    social_data = json.loads((bundle / "social.json").read_text(encoding="utf-8"))

    # Patch pipeline globals — isolated output dir per episode
    wp.ROOT        = ROOT
    wp.WEEK_TAG    = week
    wp.OUT_DIR     = out_dir
    wp.IMG_DIR     = out_dir / "slides"
    wp.VOICE_DIR   = out_dir / "voice"
    wp.RECIPIENTS  = RECIP
    wp.LOGO_PATH   = ROOT / "assets" / "nextvivo_logo.png"
    topic_slug     = wp._resolve_topic_slug(bundle)
    wp.OUT_PPTX    = out_dir / f"{topic_slug}_{week}.pptx"
    wp.OUT_MP4     = out_dir / f"{topic_slug}_{week}.mp4"
    wp.OUT_MP4_VERTICAL = out_dir / f"{topic_slug}_{week}_douyin_9x16.mp4"

    frozen_wechat = bundle / "wechat" if (bundle / "wechat").is_dir() else None

    print(f"\n{'='*60}")
    print(f"  {label} · {slug}")
    print(f"  PMID {article['pmid']}: {article['title'][:60]}...")
    print(f"  Output: {out_dir.relative_to(ROOT)}")
    print(f"{'='*60}")

    # Stage 0: third-party guard
    run_ssot_guard(bundle, out_dir)

    # Stage 2b: Kimi fact-check deck_spec
    spec = wp.stage_fact_check(spec, article)
    (out_dir / "deck_spec.json").write_text(
        json.dumps(spec, ensure_ascii=False, indent=2), encoding="utf-8")
    (out_dir / "social.json").write_text(
        json.dumps(social_data, ensure_ascii=False, indent=2), encoding="utf-8")

    if force_images:
        import shutil
        for d in (wp.IMG_DIR, out_dir / "social_images"):
            if d.exists():
                shutil.rmtree(d)
        for f in (wp.OUT_PPTX, wp.OUT_MP4, wp.OUT_MP4_VERTICAL):
            if f.exists():
                f.unlink()

    wp.IMG_DIR.mkdir(parents=True, exist_ok=True)
    wp.VOICE_DIR.mkdir(parents=True, exist_ok=True)

    wp.stage_generate_images(spec)
    wp.stage_logo()
    audit_pass = wp.stage_audit()
    wp.stage_tts(spec)
    wp.stage_pptx()
    wp.stage_mp4()
    wp.stage_mp4_vertical()

    # Email 1: PPT + MP4
    from send_email import send_weekly_report, send_xhs_report, send_wechat_report
    send_weekly_report(
        article=article,
        pptx_path=wp.OUT_PPTX,
        mp4_path=wp.OUT_MP4,
        mp4_vertical_path=wp.OUT_MP4_VERTICAL,
        audit_pass=audit_pass,
        recipients=RECIP,
        week_tag=f"{week} {label}",
    )

    wp.stage_social_images(social_data, force=force_images,
                           frozen_wechat_dir=frozen_wechat,
                           slide_dir=wp.IMG_DIR)
    send_xhs_report(
        article=article,
        social_data=social_data,
        img_dir=out_dir / "social_images" / "xhs",
        recipients=RECIP,
        week_tag=f"{week} {label}",
    )
    send_wechat_report(
        article=article,
        social_data=social_data,
        img_dir=out_dir / "social_images" / "wechat",
        recipients=RECIP,
        week_tag=f"{week} {label}",
    )

    print(f"\n✅ {label} complete — 3 emails sent for {slug}")


def main() -> None:
    ap = argparse.ArgumentParser(description="Run In-Vivo CAR series episodes on VPS")
    ap.add_argument("--bundle", help="Run single bundle slug only")
    ap.add_argument("--skip-images", action="store_true",
                    help="Reuse cached slides/images (emails-only mode)")
    args = ap.parse_args()

    episodes = SERIES
    if args.bundle:
        episodes = [e for e in SERIES if e["slug"] == args.bundle]
        if not episodes:
            episodes = [{"slug": args.bundle, "label": args.bundle, "week": "2026-W25"}]

    for ep in episodes:
        run_pipeline(
            ep["slug"], ep["week"], ep["label"],
            force_images=not args.skip_images,
        )

    print("\n🎉 ALL SERIES EPISODES DELIVERED →", ", ".join(RECIP))


if __name__ == "__main__":
    main()
