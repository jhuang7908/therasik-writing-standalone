#!/usr/bin/env python3
"""Female-voice broadcast for finance XHS: Doubao TTS 2.0 + optional vertical video.

- Reuses the working Doubao TTS 2.0 HTTP streaming endpoint (seed-tts-2.0).
- Default voice: 爽快思思 (zh_female_shuangkuaisisi_uranus_bigtts) — lively female host.
- Display text is never changed; this only consumes the separate `voice_script`.
- All numbers in voice_script are already audited by number_guard before synthesis.
"""
from __future__ import annotations

import base64
import json
import os
import re
import uuid
from pathlib import Path
from typing import Any

_TTS_URL = "https://openspeech.bytedance.com/api/v3/tts/unidirectional"
DEFAULT_FEMALE_SPEAKER = "zh_female_shuangkuaisisi_uranus_bigtts"

# Reverse the XHS compliance spelling so TTS reads natural Mandarin (audio only).
_SPEECH_RESTORE: list[tuple[str, str]] = [
    ("商业房dai", "商业贷款"),
    ("抵押房dai", "抵押贷款"),
    ("住房dai", "住房贷款"),
    ("房屋dai", "房屋贷款"),
    ("房dai", "房贷"),
    ("dai款", "贷款"),
    ("dai", "贷"),
]


def normalize_for_speech(text: str) -> str:
    """Make voice_script natural for TTS: restore 贷款, drop hashtags/markdown/emoji."""
    t = text or ""
    t = re.sub(r"#\S+", "", t)
    t = re.sub(r"[*_`>#]+", "", t)
    for pat, repl in _SPEECH_RESTORE:
        t = t.replace(pat, repl)
    # strip most emoji / pictographs (keep CJK, latin, common punctuation)
    t = re.sub(
        r"[\U0001F000-\U0001FAFF\U00002600-\U000027BF\U0001F1E6-\U0001F1FF\u2190-\u21FF\u2B00-\u2BFF]",
        "",
        t,
    )
    t = re.sub(r"[ \t]+", " ", t)
    t = re.sub(r"\n{2,}", "\n", t)
    return t.strip()


def _api_key() -> str:
    return (
        os.environ.get("VOLC_SPEECH_API_KEY")
        or os.environ.get("ARK_API_KEY")
        or os.environ.get("VOLCENGINE_API_KEY")
        or ""
    )


def synthesize_voice(
    text: str,
    out_path: Path,
    *,
    speaker: str = DEFAULT_FEMALE_SPEAKER,
) -> dict[str, Any]:
    """Synthesize MP3 via Doubao TTS 2.0. Returns {ok, path|error, bytes, speaker}."""
    import requests

    key = _api_key()
    if not key:
        return {"ok": False, "error": "missing VOLC_SPEECH_API_KEY / ARK_API_KEY"}
    if not (text or "").strip():
        return {"ok": False, "error": "empty voice_script"}

    headers = {
        "X-Api-Key": key,
        "X-Api-Resource-Id": os.environ.get("VOLC_TTS_RESOURCE_ID", "seed-tts-2.0"),
        "X-Api-Request-Id": str(uuid.uuid4()),
        "Content-Type": "application/json",
    }
    payload = {
        "user": {"uid": "insynbio-finance-xhs"},
        "req_params": {
            "text": text,
            "speaker": speaker,
            "audio_params": {"format": "mp3", "sample_rate": 24000},
        },
    }
    try:
        session = requests.Session()
        resp = session.post(_TTS_URL, headers=headers, json=payload, stream=True, timeout=120)
        if resp.status_code != 200:
            return {"ok": False, "error": f"HTTP {resp.status_code}: {resp.text[:300]}"}
        audio = bytearray()
        for raw in resp.iter_lines(decode_unicode=True):
            if not raw:
                continue
            try:
                chunk = json.loads(raw)
            except json.JSONDecodeError:
                continue
            code = chunk.get("code")
            if code == 0 and chunk.get("data"):
                audio.extend(base64.b64decode(chunk["data"]))
            elif code == 20000000:
                break
            elif code not in (0, 20000000):
                return {"ok": False, "error": json.dumps(chunk, ensure_ascii=False)[:300]}
        if not audio:
            return {"ok": False, "error": "no audio data in stream"}
        out_path.parent.mkdir(parents=True, exist_ok=True)
        out_path.write_bytes(audio)
        return {"ok": True, "path": str(out_path), "bytes": len(audio), "speaker": speaker}
    except Exception as exc:  # network / SDK errors must not break the pipeline
        return {"ok": False, "error": str(exc)[:300]}


def build_voice_video(
    image_paths: list[Path],
    audio_path: Path,
    out_path: Path,
) -> dict[str, Any]:
    """Vertical video: cards shown in sequence over the single narration track."""
    imgs = [p for p in image_paths if p.exists()]
    if not imgs:
        return {"ok": False, "error": "no card images for video"}
    if not audio_path.exists():
        return {"ok": False, "error": "missing audio for video"}
    try:
        from moviepy import (  # type: ignore
            AudioFileClip,
            ImageClip,
            concatenate_videoclips,
        )
    except Exception as exc:
        return {"ok": False, "error": f"moviepy unavailable: {str(exc)[:160]}"}
    try:
        audio = AudioFileClip(str(audio_path))
        total = max(float(audio.duration), 2.0)
        per = total / len(imgs)
        clips = []
        for i, p in enumerate(imgs):
            # last clip absorbs rounding so audio fully covered
            dur = (total - per * (len(imgs) - 1)) if i == len(imgs) - 1 else per
            clips.append(ImageClip(str(p)).with_duration(max(dur, 1.0)))
        video = concatenate_videoclips(clips, method="compose").with_audio(audio)
        out_path.parent.mkdir(parents=True, exist_ok=True)
        video.write_videofile(
            str(out_path),
            fps=24,
            codec="libx264",
            audio_codec="aac",
            preset="veryfast",
            logger=None,
        )
        return {"ok": True, "path": str(out_path), "duration": round(total, 1)}
    except Exception as exc:
        return {"ok": False, "error": str(exc)[:300]}


def make_voice_assets(
    voice_script: str,
    image_paths: list[Path],
    out_dir: Path,
    *,
    speaker: str = DEFAULT_FEMALE_SPEAKER,
    make_video: bool = True,
) -> dict[str, Any]:
    """Synthesize MP3 (+ optional MP4). Returns asset paths + per-step status."""
    spoken = normalize_for_speech(voice_script)
    result: dict[str, Any] = {"spoken_text": spoken, "speaker": speaker}
    mp3_path = out_dir / "voice.mp3"
    tts = synthesize_voice(spoken, mp3_path, speaker=speaker)
    result["audio"] = tts
    if not tts.get("ok"):
        return result
    result["mp3"] = str(mp3_path)
    if make_video:
        mp4_path = out_dir / "voice_video.mp4"
        vid = build_voice_video(image_paths, mp3_path, mp4_path)
        result["video"] = vid
        if vid.get("ok"):
            result["mp4"] = str(mp4_path)
    return result
