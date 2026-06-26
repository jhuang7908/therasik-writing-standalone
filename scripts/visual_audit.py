"""
visual_audit.py — GPT-4o Vision audit for scientific slide images.

Usage:
    python scripts/visual_audit.py --slide_dir outputs/humanized_mice_final/origin_image \
                                   --rules config/pipeline_rules.yaml \
                                   --out outputs/humanized_mice_final/audit_report.json

Each slide is inspected by GPT-4o Vision against the expected axes and visual
accuracy criteria defined in pipeline_rules.yaml.  Output is a JSON report with
pass/fail per check plus a human-readable summary.
"""

import os, sys, json, base64, argparse
from pathlib import Path

import yaml

# Load .env from content_generation_tools/.env
_env_file = Path(__file__).parent.parent / "content_generation_tools" / ".env"
if _env_file.exists():
    for _line in _env_file.read_text(encoding="utf-8").splitlines():
        _line = _line.strip()
        if _line and not _line.startswith("#") and "=" in _line:
            _k, _v = _line.split("=", 1)
            os.environ.setdefault(_k.strip(), _v.strip())

# Visual audit uses Gemini Vision (primary) with GPT-4o as fallback
# Gemini is preferred: lower cost, no quota issues, strong vision
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY", "")
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY", "")

ROOT = Path(__file__).parent.parent

# ── helpers ──────────────────────────────────────────────────────────────────

def load_rules(rules_path: str) -> dict:
    with open(rules_path, encoding="utf-8") as f:
        return yaml.safe_load(f)


def image_to_b64(img_path: Path) -> str:
    return base64.b64encode(img_path.read_bytes()).decode("utf-8")


def _build_audit_prompt(slide_num: int, spec: dict) -> str:
    slide_type = spec.get("type", "non_scientific_art")
    description = spec.get("description", "")
    expected_axes = spec.get("expected_axes", {})

    checks = []
    if slide_type == "scientific_charts" and expected_axes:
        checks.append(f"- X-axis range: {expected_axes.get('x', 'not specified')}")
        checks.append(f"- Y-axis range: {expected_axes.get('y', 'not specified')}")
        if "endpoint" in expected_axes:
            checks.append(f"- Curve endpoint: {expected_axes['endpoint']}")
        if "curves" in expected_axes:
            for c in expected_axes["curves"]:
                checks.append(f"- Curve shape: {c}")
        if "drop_zone" in expected_axes:
            checks.append(f"- Main mortality drop occurs at: {expected_axes['drop_zone']}")

    checks += [
        "- Are all Chinese and English text labels readable (no garbled characters)?",
        "- LOGO visible: NextVivo Biotech / 未来模式生物科技 logo in bottom-right corner?",
        "- LOGO overlap: logo must NOT cover any text, chart, legend, axis label, or diagram (FAIL if any pixel overlap)?",
        "- LOGO too close: logo must NOT touch or crowd content edges; need >=1% image-height gap to nearest content (FAIL if cramped)?",
        "- LOGO too far: gap between logo top edge and nearest content below it should be 1%-6% of image height (FAIL if >8% empty gap or logo floats in large empty band)?",
        "- LOGO margin: logo should sit ~1.5% from right and bottom canvas edges (not cut off, not hugging center)?",
        "- No duplicate branding (text watermark 未来模式 + logo together)?",
    ]

    return f"""You are a scientific figure auditor with vision capabilities.
Review Slide {slide_num} of a scientific PowerPoint presentation.

Slide description: {description}
Type: {slide_type}

Check ALL items below and report PASS or FAIL for each:
{chr(10).join(checks)}

For each FAIL, describe what you actually see vs. what was expected.
Overall verdict: PASS (all pass) or FAIL (any fail).

Respond ONLY in valid JSON:
{{
  "slide": {slide_num},
  "overall": "PASS",
  "checks": [
    {{"item": "...", "result": "PASS", "detail": "..."}}
  ],
  "summary": "one sentence"
}}"""


def audit_slide_gemini(slide_num: int, img_path: Path, spec: dict) -> dict:
    """Audit using Gemini 2.0 Flash Vision (primary auditor)."""
    from google import genai
    from google.genai import types as gtypes

    client = genai.Client(api_key=GEMINI_API_KEY)
    prompt = _build_audit_prompt(slide_num, spec)
    img_bytes = img_path.read_bytes()

    response = client.models.generate_content(
        model="gemini-2.5-flash",
        contents=[
            gtypes.Part.from_bytes(data=img_bytes, mime_type="image/png"),
            prompt,
        ],
    )
    raw = response.text.strip()
    # Strip markdown fences if present
    if raw.startswith("```"):
        raw = "\n".join(raw.split("\n")[1:])
        if raw.endswith("```"):
            raw = raw[: raw.rfind("```")]
    try:
        return json.loads(raw)
    except Exception:
        return {"slide": slide_num, "overall": "PARSE_ERROR", "raw": raw[:500]}


def audit_slide(slide_num: int, img_path: Path, spec: dict) -> dict:
    """Try Gemini Vision first, fall back to GPT-4o if needed."""
    if GEMINI_API_KEY:
        try:
            return audit_slide_gemini(slide_num, img_path, spec)
        except Exception as e:
            print(f"  [WARN] Gemini audit failed: {e}")

    # GPT-4o fallback
    from openai import OpenAI
    client = OpenAI(api_key=OPENAI_API_KEY)
    prompt = _build_audit_prompt(slide_num, spec)
    b64 = image_to_b64(img_path)
    response = client.chat.completions.create(
        model="gpt-4o",
        messages=[{
            "role": "user",
            "content": [
                {"type": "text", "text": prompt},
                {"type": "image_url", "image_url": {"url": f"data:image/png;base64,{b64}", "detail": "high"}},
            ],
        }],
        max_tokens=1000,
        response_format={"type": "json_object"},
    )
    raw = response.choices[0].message.content
    try:
        return json.loads(raw)
    except Exception:
        return {"slide": slide_num, "overall": "PARSE_ERROR", "raw": raw}


def run_audit(slide_dir: str, rules_path: str, out_path: str):
    rules = load_rules(rules_path)
    slide_specs = rules.get("slide_classification", {})

    img_dir = Path(slide_dir)
    results = []
    all_pass = True

    for i in range(1, 7):
        img_path = img_dir / f"slide_{i:02d}.png"
        if not img_path.exists():
            results.append({"slide": i, "overall": "SKIPPED", "reason": "file not found"})
            continue

        spec_key = f"slide_{i:02d}"
        spec = slide_specs.get(spec_key, {})

        print(f"  Auditing slide {i}: {spec.get('description', '')} ...")
        result = audit_slide(i, img_path, spec)
        results.append(result)

        verdict = result.get("overall", "UNKNOWN")
        icon = "✅" if verdict == "PASS" else "❌" if verdict == "FAIL" else "⚠️"
        print(f"  {icon} Slide {i}: {verdict} — {result.get('summary', '')}")
        if verdict == "FAIL":
            all_pass = False
            for chk in result.get("checks", []):
                if chk.get("result") == "FAIL":
                    print(f"       FAIL [{chk['item']}]: {chk['detail']}")

    report = {
        "overall_pass": all_pass,
        "total_slides": len(results),
        "failed_slides": [r["slide"] for r in results if r.get("overall") == "FAIL"],
        "results": results,
    }

    Path(out_path).parent.mkdir(parents=True, exist_ok=True)
    Path(out_path).write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"\n  Audit report saved: {out_path}")
    print(f"  Overall: {'ALL PASS ✅' if all_pass else 'FAILURES DETECTED ❌'}")
    return report


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="GPT-4o Vision slide auditor")
    parser.add_argument("--slide_dir", default="outputs/humanized_mice_final/origin_image")
    parser.add_argument("--rules",     default="config/pipeline_rules.yaml")
    parser.add_argument("--out",       default="outputs/humanized_mice_final/audit_report.json")
    args = parser.parse_args()

    print("=== Visual Audit (GPT-4o Vision) ===")
    run_audit(args.slide_dir, args.rules, args.out)
