"""Offline regression tests. No email, image or language-model calls."""
from __future__ import annotations

import json
import sys
import tempfile
import types
import unittest
from pathlib import Path
from unittest.mock import MagicMock, patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))

import uslifehub_wechat_content as content
import uslifehub_wechat_weekly as weekly
from uslifehub_social_quality import SocialContentQualityError, validate_social_content


def payload(body="我们整理了本周办事信息，具体安排请查阅官方来源。", platform="xiaohongshu"):
    data = {"title": "生活信息整理", "body": body}
    if platform == "xiaohongshu":
        data["cards"] = [{"title": f"信息{i}", "body": body} for i in range(6)]
    else:
        data["sections"] = [{"heading": f"信息{i}", "body": body} for i in range(5)]
    return {platform: data}


def image_cache(img_dir, data, platform):
    """Local bytes only; never invoke an image generator."""
    img_dir.mkdir(parents=True, exist_ok=True)
    for name in weekly._expected_images(data, platform):
        (img_dir / name).write_bytes(b"mock image bytes " + name.encode())
    weekly._seal_image_cache(data, img_dir, platform)


class QualityRulesTests(unittest.TestCase):
    def test_rejects_wrong_library_attribution(self):
        for text in (
            "NYPL法拉盛图书馆推出免费课程", "纽约公共图书馆的法拉盛分馆",
            "New York Public Library Flushing Library", "NYPL 在法拉盛的图书馆",
            "法拉盛图书馆属于NYPL", "法拉盛图书馆（NYPL）",
            "Flushing Library is part of the New York Public Library",
            "NYPL's Flushing branch", "https://www.nypl.org/locations/flushing",
            "https://nypl.org/locations/flushing?ref=weekly",
        ):
            with self.subTest(text=text), self.assertRaises(SocialContentQualityError):
                validate_social_content(payload(text))

    def test_rejects_first_person_experience(self):
        for text in (
            "我在纽约生活了十年，帮你省心。", "我住在纽约。", "我上周去了法拉盛图书馆。",
            "我亲测这个活动很不错。", "我们带娃参加过这项活动。", "小编申请过这项福利。",
            "我老公上周去了现场。", "来纽约第十年了，这份指南收好。",
            "在纽约混十年，帮你看看。", "在纽约混了十年的闺蜜来分享。", "亲测有效，值得收藏！",
            "作为一个在纽约混了十年的闺蜜，这次帮你整理好啦",
            "🗽在纽约混了十年，帮你看看",
            "I have lived in New York for ten years.", "I've lived in New York for ten years.",
            "We visited the library last week.",
        ):
            with self.subTest(text=text), self.assertRaises(SocialContentQualityError):
                validate_social_content(payload(text))

    def test_preserves_editorial_voice_separate_institutions_and_history(self):
        for text in (
            "我们整理了法拉盛图书馆的信息，请以 Queens Public Library 官网为准。",
            "NYPL 提供线上资源；法拉盛图书馆属于皇后区公共图书馆。",
            "NYPL 活动和法拉盛图书馆活动均需查询各自官网。",
            "法拉盛图书馆不属于 NYPL，而属于 Queens Public Library。",
            "Flushing Library is not part of NYPL.",
            "法拉盛图书馆（NYPL 不经营该馆）属于皇后区公共图书馆。",
            "2017、2019、2024年的春节游行照片仅供历史回顾，不代表本周活动。",
            "如果你在纽约生活了十年，也可以看看这些信息。",
            "我来介绍官网公布的办事步骤。我们建议先查看预约要求。",
            "我们建议你亲自核对预约信息。", "我没有去过这个活动。",
        ):
            with self.subTest(text=text):
                validate_social_content(payload(text))

    def test_checks_nested_cards_image_prompts_and_urls(self):
        data = payload()
        data["xiaohongshu"]["cards"] = [{"image_prompt": "我带娃去过这个活动"}]
        with self.assertRaisesRegex(SocialContentQualityError, r"cards\[0\].image_prompt"):
            validate_social_content(data)

    def test_rejects_malformed_platform(self):
        for data in ([], {}, {"wechat": "invalid"}, {"wechat": {}}):
            with self.subTest(data=data), self.assertRaises(SocialContentQualityError):
                validate_social_content(data, required_fields=("wechat",))


class PipelineGuardTests(unittest.TestCase):
    def test_prompt_events_keep_canonical_and_legacy_end_dates(self):
        events = [{"id": "a", "event_end_date": "2026-10-12", "end_date": "2026-10-10"},
                  {"id": "b", "end_date": "2026-10-13"}]
        newsletter = types.ModuleType("send_community_newsletters")
        newsletter.filter_events_for_interests = MagicMock(return_value=events)
        with patch.dict(sys.modules, {"send_community_newsletters": newsletter}):
            result = content._top_events(events, 10)
        self.assertEqual([event["event_end_date"] for event in result], ["2026-10-12", "2026-10-13"])

    def test_writer_rejects_before_writing_or_enrichment(self):
        llm = types.ModuleType("social_content")
        llm.SPEC = "format rules"
        llm._call_deepseek = MagicMock(return_value=json.dumps(payload("NYPL法拉盛图书馆"), ensure_ascii=False))
        llm._clean_json = lambda value: value
        llm._validate = MagicMock(return_value=[])
        ad = types.ModuleType("wechat_ad_bar")
        ad.inject_ad_bar = MagicMock()
        ad.load_ad_bar_config = MagicMock()
        cover = types.ModuleType("wechat_cover")
        cover.ensure_cover_digest = MagicMock()
        with tempfile.TemporaryDirectory() as tmp, patch.dict(sys.modules, {
            "social_content": llm, "wechat_ad_bar": ad, "wechat_cover": cover,
        }):
            path = Path(tmp) / "social.json"
            path.write_text("existing approved content", encoding="utf-8")
            with self.assertRaises(SocialContentQualityError):
                content._write_llm_json([], path, writer_system="editor", campaign_id="test",
                                       user_hint="test", required_fields=("xiaohongshu",))
            self.assertEqual(path.read_text(encoding="utf-8"), "existing approved content")
            ad.inject_ad_bar.assert_not_called()
            cover.ensure_cover_digest.assert_not_called()
            self.assertIn("Queens Public Library", llm._call_deepseek.call_args.args[1])
            self.assertIn("不得", llm._call_deepseek.call_args.args[1])

    def test_writer_accepts_grounded_content(self):
        llm = types.ModuleType("social_content")
        llm.SPEC = "format rules"
        llm._call_deepseek = MagicMock(return_value=json.dumps(payload(), ensure_ascii=False))
        llm._clean_json = lambda value: value
        llm._validate = MagicMock(return_value=[])
        ad = types.ModuleType("wechat_ad_bar")
        ad.inject_ad_bar = MagicMock()
        ad.load_ad_bar_config = MagicMock()
        cover = types.ModuleType("wechat_cover")
        cover.ensure_cover_digest = MagicMock()
        with tempfile.TemporaryDirectory() as tmp, patch.dict(sys.modules, {
            "social_content": llm, "wechat_ad_bar": ad, "wechat_cover": cover,
        }):
            path = Path(tmp) / "social.json"
            content._write_llm_json([], path, writer_system="editor", campaign_id="test",
                                   user_hint="test", required_fields=("xiaohongshu",))
            self.assertEqual(json.loads(path.read_text())["xiaohongshu"], payload()["xiaohongshu"])

    def test_rendering_rejects_before_image_calls(self):
        images = types.ModuleType("social_images")
        for name in ("generate_wechat_ad_banner", "generate_wechat_cover", "generate_wechat_images", "generate_xhs_images"):
            setattr(images, name, MagicMock())
        with tempfile.TemporaryDirectory() as tmp, patch.dict(sys.modules, {"social_images": images}):
            root = Path(tmp) / "images"
            with self.assertRaises(SocialContentQualityError):
                weekly.stage_wechat_images(payload("我亲测这个活动", "wechat"), root,
                                           force=True, ad_bar=Path(tmp) / "ad.yaml")
            with self.assertRaises(SocialContentQualityError):
                weekly.stage_xhs_variant_images(payload("NYPL法拉盛图书馆"), root, "test", "style", force=True)
            self.assertFalse(root.exists())
            for value in vars(images).values():
                if isinstance(value, MagicMock):
                    value.assert_not_called()

    def _run_email_only(self, root, *, mode=None):
        variants = [{"id": "practical", "recipients": ["reader@example.com"]},
                    {"id": "lifestyle", "recipients": ["reader@example.com"]}]
        cfg = {"xhs_variants": variants, "wechat_recipients": ["reader@example.com"]}
        emails = types.ModuleType("send_email")
        emails.send_uslifehub_wechat_report = MagicMock()
        emails.send_uslifehub_xhs_report = MagicMock()
        argv = ["weekly", "--emails-only", "--campaign-id", "test"] + ([mode] if mode else [])
        with patch.dict(sys.modules, {"send_email": emails}), patch.object(sys, "argv", argv), \
                patch.object(weekly, "_load_cfg", return_value=cfg), \
                patch.object(weekly, "_out_dir", return_value=root), \
                patch.object(weekly, "_apply_logo"), patch.object(weekly, "_setup_ad_bar", return_value=root / "ad.yaml"):
            try:
                result = weekly.main()
            except Exception:
                emails.send_uslifehub_wechat_report.assert_not_called()
                emails.send_uslifehub_xhs_report.assert_not_called()
                raise
        return result, emails

    def test_bad_last_cached_variant_prevents_all_emails(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            (root / "social_wechat.json").write_text(json.dumps(payload(platform="wechat")))
            (root / "social_xhs_practical.json").write_text(json.dumps(payload()))
            (root / "social_xhs_lifestyle.json").write_text(json.dumps(payload("我在纽约住了十年")))
            with self.assertRaisesRegex(SocialContentQualityError, "social_xhs_lifestyle"):
                self._run_email_only(root)

    def test_malformed_last_cached_variant_prevents_all_emails(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            (root / "social_wechat.json").write_text(json.dumps(payload(platform="wechat")))
            (root / "social_xhs_practical.json").write_text(json.dumps(payload()))
            (root / "social_xhs_lifestyle.json").write_text("not json")
            with self.assertRaises(json.JSONDecodeError):
                self._run_email_only(root)

    def test_good_cached_batch_reaches_mock_senders(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            (root / "social_wechat.json").write_text(json.dumps(payload(platform="wechat")))
            image_cache(root / "social_images/wechat", payload(platform="wechat"), "wechat")
            for vid in ("practical", "lifestyle"):
                (root / f"social_xhs_{vid}.json").write_text(json.dumps(payload()))
                image_cache(root / f"social_images/xhs_{vid}", payload(), "xiaohongshu")
            result, emails = self._run_email_only(root)
            self.assertEqual(result, 0)
            emails.send_uslifehub_wechat_report.assert_called_once()
            self.assertEqual(emails.send_uslifehub_xhs_report.call_count, 2)

    def test_wechat_only_ignores_unselected_bad_xhs(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            (root / "social_wechat.json").write_text(json.dumps(payload(platform="wechat")))
            image_cache(root / "social_images/wechat", payload(platform="wechat"), "wechat")
            (root / "social_xhs_lifestyle.json").write_text("not json")
            result, emails = self._run_email_only(root, mode="--wechat-only")
            self.assertEqual(result, 0)
            emails.send_uslifehub_wechat_report.assert_called_once()
            emails.send_uslifehub_xhs_report.assert_not_called()

    def test_email_only_legacy_images_without_manifest_block_all_sends(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            (root / "social_wechat.json").write_text(json.dumps(payload(platform="wechat")))
            image_cache(root / "social_images/wechat", payload(platform="wechat"), "wechat")
            for vid in ("practical", "lifestyle"):
                (root / f"social_xhs_{vid}.json").write_text(json.dumps(payload()))
                image_cache(root / f"social_images/xhs_{vid}", payload(), "xiaohongshu")
            (root / "social_images/xhs_lifestyle" / weekly._IMAGE_MANIFEST).unlink()
            with self.assertRaisesRegex(SocialContentQualityError, "unverifiable image cache"):
                self._run_email_only(root)

    def test_email_only_corrected_json_with_old_cards_blocks_all_sends(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            (root / "social_wechat.json").write_text(json.dumps(payload(platform="wechat")))
            image_cache(root / "social_images/wechat", payload(platform="wechat"), "wechat")
            for vid in ("practical", "lifestyle"):
                (root / f"social_xhs_{vid}.json").write_text(json.dumps(payload()))
                old = payload("我在纽约混了十年") if vid == "lifestyle" else payload()
                image_cache(root / f"social_images/xhs_{vid}", old, "xiaohongshu")
            with self.assertRaisesRegex(SocialContentQualityError, "image cache does not match content"):
                self._run_email_only(root)


class ImageCacheTests(unittest.TestCase):
    def _images_module(self):
        images = types.ModuleType("social_images")

        def write_xhs(data, out, **kwargs):
            for name in weekly._expected_images(data, "xiaohongshu"):
                (out / name).write_bytes(b"new generated mock image")

        def write_cover(data, out, **kwargs):
            (out / "wechat_cover.png").write_bytes(b"new cover")

        def write_inline(data, out, **kwargs):
            for name in weekly._expected_images(data, "wechat"):
                if name.startswith("wechat_inline_"):
                    (out / name).write_bytes(b"new inline")

        def write_ad(out, **kwargs):
            (out / "wechat_ad_bar.png").write_bytes(b"new ad")

        images.generate_xhs_images = MagicMock(side_effect=write_xhs)
        images.generate_wechat_cover = MagicMock(side_effect=write_cover)
        images.generate_wechat_images = MagicMock(side_effect=write_inline)
        images.generate_wechat_ad_banner = MagicMock(side_effect=write_ad)
        return images

    def test_xhs_legacy_and_mismatched_caches_rebuild_only_the_variant(self):
        for legacy in (True, False):
            with self.subTest(legacy=legacy), tempfile.TemporaryDirectory() as tmp:
                root = Path(tmp)
                stale = root / "xhs_lifestyle"
                image_cache(stale, payload("previous content"), "xiaohongshu")
                if legacy:
                    (stale / weekly._IMAGE_MANIFEST).unlink()
                sibling = root / "xhs_practical"
                sibling.mkdir()
                (sibling / "keep.png").write_bytes(b"untouched")
                (stale / "xhs_card_99.png").write_bytes(b"stale extra")
                images = self._images_module()
                with patch.dict(sys.modules, {"social_images": images}):
                    weekly.stage_xhs_variant_images(payload(), root, "lifestyle", "style", force=False)
                images.generate_xhs_images.assert_called_once()
                self.assertTrue(images.generate_xhs_images.call_args.kwargs["force"])
                weekly._verify_image_cache(payload(), stale, "xiaohongshu")
                self.assertFalse((stale / "xhs_card_99.png").exists())
                self.assertEqual((sibling / "keep.png").read_bytes(), b"untouched")

    def test_wechat_stale_cache_rebuilds_all_expected_assets(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            image_cache(root / "wechat", payload("old content", "wechat"), "wechat")
            images = self._images_module()
            with patch.dict(sys.modules, {"social_images": images}):
                weekly.stage_wechat_images(payload(platform="wechat"), root, force=False, ad_bar=root / "ad.yaml")
            weekly._verify_image_cache(payload(platform="wechat"), root / "wechat", "wechat")
            for fn in (images.generate_wechat_cover, images.generate_wechat_images, images.generate_wechat_ad_banner):
                fn.assert_called_once()
                self.assertTrue(fn.call_args.kwargs["force"])

    def test_matching_cache_reused_without_generation(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            image_cache(root / "wechat", payload(platform="wechat"), "wechat")
            image_cache(root / "xhs_lifestyle", payload(), "xiaohongshu")
            images = self._images_module()
            with patch.dict(sys.modules, {"social_images": images}):
                weekly.stage_wechat_images(payload(platform="wechat"), root, force=False, ad_bar=root / "ad.yaml")
                weekly.stage_xhs_variant_images(payload(), root, "lifestyle", "style", force=False)
            for value in vars(images).values():
                if isinstance(value, MagicMock):
                    value.assert_not_called()

    def test_incomplete_generation_never_writes_manifest(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            images = self._images_module()
            images.generate_xhs_images.side_effect = lambda *args, **kwargs: None
            with patch.dict(sys.modules, {"social_images": images}), self.assertRaisesRegex(
                SocialContentQualityError, "missing or unexpected images"
            ):
                weekly.stage_xhs_variant_images(payload(), root, "lifestyle", "style", force=False)
            self.assertFalse((root / "xhs_lifestyle" / weekly._IMAGE_MANIFEST).exists())

    def test_failed_generation_clears_old_manifest(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            image_cache(root / "xhs_lifestyle", payload(), "xiaohongshu")
            images = self._images_module()
            images.generate_xhs_images.side_effect = RuntimeError("mock generation failed")
            with patch.dict(sys.modules, {"social_images": images}), self.assertRaises(RuntimeError):
                weekly.stage_xhs_variant_images(payload(), root, "lifestyle", "style", force=True)
            self.assertFalse((root / "xhs_lifestyle" / weekly._IMAGE_MANIFEST).exists())

    def test_changed_or_empty_image_bytes_fail_verification(self):
        for blob in (b"changed bytes", b""):
            with self.subTest(blob=blob), tempfile.TemporaryDirectory() as tmp:
                folder = Path(tmp)
                image_cache(folder, payload(), "xiaohongshu")
                (folder / "xhs_card_01.png").write_bytes(blob)
                with self.assertRaises(SocialContentQualityError):
                    weekly._verify_image_cache(payload(), folder, "xiaohongshu")


if __name__ == "__main__":
    unittest.main()
