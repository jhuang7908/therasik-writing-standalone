"""Full regeneration after fact-check corrections:
slide 2 + 4 images → PPTX → TTS → MP4 → XHS cards 3+5 → WeChat → resend all 3 emails.
"""
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
for k, v in [('SMTP_HOST','mail.privateemail.com'),('SMTP_PORT','587'),
              ('SMTP_USER','contact@insynbio.com'),('SMTP_PASSWORD','Luna@7908')]:
    os.environ.setdefault(k, v)

WEEK   = '2026-W24'
SLUG   = 'in_vivo_car_tech_2026'
OUT    = ROOT / 'outputs' / f'weekly_{WEEK}'
FROZEN = ROOT / 'data' / 'frozen' / SLUG

# Reload corrected frozen files
SPEC   = json.loads((FROZEN / 'deck_spec.json').read_text(encoding='utf-8'))
social_data = json.loads((FROZEN / 'social.json').read_text(encoding='utf-8'))
article     = json.loads((FROZEN / 'article.json').read_text(encoding='utf-8'))

SLIDES_DIR = OUT / 'slides'
VOICE_DIR  = OUT / 'voice'
IMG_DIR    = OUT / 'social_images'

# ─── 1. Re-render slide 2 and slide 4 (corrected content) ────────────────────
print('=== Stage 3b: Re-render slides 2 and 4 (corrected) ===')
from weekly_pipeline import _render_gpt_image2, stage_logo, stage_tts, stage_pptx, stage_mp4_vertical
import weekly_pipeline as wp

# Override OUT_DIR so helpers write to correct location
wp.OUT_DIR   = OUT
wp.IMG_DIR   = SLIDES_DIR
wp.LOGO_PATH = ROOT / 'assets' / 'nextvivo_logo.png'
wp._TOPIC_SLUG = SLUG

SLIDES_DIR.mkdir(parents=True, exist_ok=True)
for slide in SPEC['slides']:
    n = slide['slide_num']
    if n not in (2, 4):
        continue
    out_path = SLIDES_DIR / f'slide_{n:02d}.png'
    out_path.unlink(missing_ok=True)  # force re-render
    print(f'  Rendering slide {n}: {slide["title"]}')
    openai_key = os.environ.get('OPENAI_API_KEY', '')
    prompt = wp._build_image_prompt(slide)
    _render_gpt_image2(prompt, out_path, openai_key)

# Re-stamp logo on regenerated slides
print('=== Stage 4b: Re-stamp logo on slides 2+4 ===')
stage_logo()

# ─── 2. Delete old TTS for slides 2+4, re-generate with Doubao ───────────────
print('=== Stage 6b: Re-generate TTS for slides 2+4 ===')
for n in (2, 4):
    p = VOICE_DIR / f'slide_{n:02d}.mp3'
    if p.exists():
        p.unlink()
from weekly_pipeline import stage_tts
stage_tts(SPEC)

# ─── 3. Re-assemble PPTX ─────────────────────────────────────────────────────
print('=== Stage 9b: Re-assemble PPTX ===')
from weekly_pipeline import stage_pptx
wp.OUT_PPTX = OUT / f'{SLUG}_{WEEK}.pptx'
stage_pptx()

# ─── 4. Re-assemble MP4 ──────────────────────────────────────────────────────
print('=== Stage 10b: Re-assemble MP4 (豆包 TTS) ===')
slide_imgs  = sorted(SLIDES_DIR.glob('slide_*.png'))
voice_files = sorted(VOICE_DIR.glob('slide_*.mp3'))
if slide_imgs and len(voice_files) >= 6:
    try:
        from moviepy import ImageClip, AudioFileClip, concatenate_videoclips
        clips = []
        for img_p, mp3_p in zip(slide_imgs, voice_files):
            audio = AudioFileClip(str(mp3_p))
            dur   = max(float(audio.duration) + 0.5, 4.0)
            clips.append(ImageClip(str(img_p)).with_duration(dur).with_audio(audio))
        video = concatenate_videoclips(clips, method='compose')
        mp4_out = OUT / f'{SLUG}_{WEEK}.mp4'
        video.write_videofile(str(mp4_out), fps=24, codec='libx264',
                              audio_codec='aac', preset='veryfast', logger=None)
        print(f'  MP4 (horizontal): {mp4_out.name} ({mp4_out.stat().st_size//1024}KB)')
        # 9:16 vertical version
        from weekly_pipeline import stage_mp4_vertical
        wp.OUT_MP4 = mp4_out
        wp.OUT_DIR = OUT
        wp.IMG_DIR = SLIDES_DIR
        wp.VOICE_DIR = VOICE_DIR
        stage_mp4_vertical()
    except Exception as e:
        print(f'  [WARN] MP4 failed: {e}')
else:
    print(f'  [SKIP] slides={len(slide_imgs)}, voice={len(voice_files)}')

# ─── 5. Regenerate XHS cards 3+5 + all WeChat images (corrected content) ─────
print('=== Stage 11b: Re-generate XHS cards 3+5 + WeChat ===')
from social_images import generate_xhs_images, generate_wechat_images, generate_wechat_cover

# Delete only cards 3 and 5 (affected by corrections)
for n in (3, 5):
    p = IMG_DIR / 'xhs' / f'xhs_card_{n:02d}.png'
    if p.exists():
        p.unlink()
generate_xhs_images(social_data, IMG_DIR / 'xhs', force=False,
                    slide_dir=SLIDES_DIR)

# Regenerate WeChat inline images (section 3 text corrected)
for p in (IMG_DIR / 'wechat').glob('wechat_inline_*.png'):
    p.unlink()
generate_wechat_images(social_data, IMG_DIR / 'wechat', force=True,
                       frozen_dir=FROZEN / 'wechat',
                       slide_dir=SLIDES_DIR,
                       inline_sections=[1, 2, 3])

# ─── 6. Resend all 3 emails ───────────────────────────────────────────────────
RECIP = ['mail.jing.huang@gmail.com']
from send_email import send_weekly_report, send_xhs_report, send_wechat_report

print('=== Email 1: PPT + MP4 (corrected) ===')
pptx_path = OUT / f'{SLUG}_{WEEK}.pptx'
mp4_path  = OUT / f'{SLUG}_{WEEK}.mp4'
mp4_v     = OUT / f'{SLUG}_{WEEK}_douyin_9x16.mp4'
send_weekly_report(
    article=article,
    pptx_path=pptx_path,
    mp4_path=mp4_path if mp4_path.exists() else None,
    mp4_vertical_path=mp4_v if mp4_v.exists() else None,
    recipients=RECIP, week_tag=WEEK, audit_pass=True,
)

print('=== Email 2: XHS (corrected cards 3+5) ===')
send_xhs_report(article=article, social_data=social_data,
                img_dir=IMG_DIR / 'xhs', recipients=RECIP, week_tag=WEEK)

print('=== Email 3: WeChat (corrected section 3) ===')
send_wechat_report(article=article, social_data=social_data,
                   img_dir=IMG_DIR / 'wechat', recipients=RECIP, week_tag=WEEK)

print('ALL DONE — corrected content delivered')
