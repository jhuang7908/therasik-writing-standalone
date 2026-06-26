"""Regenerate: XHS cards (new 2-panel design) + TTS (Doubao) + MP4. Then resend Emails 2+3."""
import os, sys, json, shutil
from pathlib import Path

ROOT = Path(__file__).parent.parent
sys.path.insert(0, str(ROOT / 'scripts'))

# Load all keys
for line in (ROOT / '.env').read_text(encoding='utf-8').splitlines():
    line = line.strip()
    if line and not line.startswith('#') and '=' in line:
        k, v = line.split('=', 1)
        os.environ[k.strip()] = v.strip()
# Fallback SMTP
for k, v in [('SMTP_HOST','mail.privateemail.com'),('SMTP_PORT','587'),
              ('SMTP_USER','contact@insynbio.com'),('SMTP_PASSWORD','Luna@7908')]:
    os.environ.setdefault(k, v)

WEEK   = '2026-W24'
SLUG   = 'in_vivo_car_tech_2026'
OUT    = ROOT / 'outputs' / f'weekly_{WEEK}'
FROZEN = ROOT / 'data' / 'frozen' / SLUG
SPEC   = json.loads((FROZEN / 'deck_spec.json').read_text(encoding='utf-8'))

article     = json.loads((FROZEN / 'article.json').read_text(encoding='utf-8'))
social_data = json.loads((OUT / 'social.json').read_text(encoding='utf-8'))

# ─── 1. Regenerate XHS cards (force=True) ─────────────────────────────────────
print('=== Re-generate XHS cards (2-panel design) ===')
from social_images import generate_xhs_images, generate_wechat_images, generate_wechat_ad_banner, generate_wechat_cover

img_dir = OUT / 'social_images'
# Delete old XHS cards so force triggers rebuild
for p in (img_dir / 'xhs').glob('xhs_card_*.png'):
    p.unlink()

generate_xhs_images(social_data, img_dir / 'xhs', force=True,
                    slide_dir=OUT / 'slides')

# ─── 2. Regenerate WeChat inline images ───────────────────────────────────────
print('=== Re-generate WeChat inline images (force) ===')
for p in (img_dir / 'wechat').glob('wechat_inline_*.png'):
    p.unlink()
generate_wechat_images(social_data, img_dir / 'wechat', force=True,
                       frozen_dir=FROZEN / 'wechat',
                       slide_dir=OUT / 'slides',
                       inline_sections=[1, 2, 3])

# ─── 3. TTS — Doubao seed-tts-2.0 ────────────────────────────────────────────
print('=== TTS with Doubao seed-tts-2.0 ===')
VOICE_DIR = OUT / 'voice'
# Delete old voice files
if VOICE_DIR.exists():
    shutil.rmtree(VOICE_DIR)
VOICE_DIR.mkdir(parents=True)

from weekly_pipeline import stage_tts
stage_tts(SPEC)

# ─── 4. Assemble new MP4 ──────────────────────────────────────────────────────
print('=== Assemble new MP4 ===')
slides_dir = OUT / 'slides'
slide_imgs = sorted(slides_dir.glob('slide_*.png'))
voice_files = sorted(VOICE_DIR.glob('slide_*.mp3'))

if slide_imgs and voice_files:
    try:
        from moviepy import ImageClip, AudioFileClip, concatenate_videoclips
        clips = []
        for img_p, mp3_p in zip(slide_imgs, voice_files):
            audio = AudioFileClip(str(mp3_p))
            dur   = max(float(audio.duration) + 0.5, 4.0)
            clips.append(ImageClip(str(img_p)).with_duration(dur).with_audio(audio))
        video = concatenate_videoclips(clips, method='compose')
        mp4_out = OUT / f'{SLUG}_{WEEK}_v2.mp4'
        video.write_videofile(str(mp4_out), fps=24, codec='libx264',
                              audio_codec='aac', preset='veryfast', logger=None)
        print(f'  MP4: {mp4_out} ({mp4_out.stat().st_size//1024}KB)')
    except Exception as e:
        print(f'  [WARN] MP4 failed: {e}')
else:
    print(f'  [WARN] slides={len(slide_imgs)}, voice={len(voice_files)} — skipping MP4')

# ─── 5. Resend Email 2 (XHS) + Email 3 (WeChat) ──────────────────────────────
from send_email import send_xhs_report, send_wechat_report
RECIP = ['mail.jing.huang@gmail.com']

print('=== Email 2: XHS (with new 2-panel cards) ===')
send_xhs_report(article=article, social_data=social_data,
                img_dir=img_dir / 'xhs', recipients=RECIP, week_tag=WEEK)

print('=== Email 3: WeChat (3 inline images) ===')
send_wechat_report(article=article, social_data=social_data,
                   img_dir=img_dir / 'wechat', recipients=RECIP, week_tag=WEEK)

print('ALL DONE')
