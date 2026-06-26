"""
InSynBio Style Calibration CLI — 6-dimension author voice profiling.

Adopted from ARS shared/style_calibration_protocol.md (academic-paper Step 10).
Works for any biomedical domain: oncology, immunology, gene therapy, drug discovery,
structural biology, clinical, computational, etc.

Usage:
    python scripts/insynbio_style_calibration.py \\
        --samples paper1.pdf paper2.pdf paper3.pdf \\
        --domain oncology \\
        --out projects/my_project/style_profile.json

    python scripts/insynbio_style_calibration.py \\
        --samples paper1.txt paper2.md \\
        --domain gene_therapy \\
        --target-journal "Nature Medicine" \\
        --out projects/my_project/style_profile.json
"""

from __future__ import annotations

import argparse
import json
import re
import sys
from datetime import datetime, timezone
from pathlib import Path


def _require_package(name: str, install: str) -> None:
    try:
        __import__(name)
    except ImportError:
        sys.exit(f"ERROR: '{name}' not installed. Run: pip install {install}")


def extract_text_from_file(path: Path) -> str:
    """Extract plain text from PDF, DOCX, MD, or TXT."""
    suffix = path.suffix.lower()
    if suffix == ".pdf":
        _require_package("fitz", "pymupdf")
        import fitz  # type: ignore
        doc = fitz.open(str(path))
        return "\n".join(page.get_text() for page in doc)
    elif suffix == ".docx":
        _require_package("docx", "python-docx")
        from docx import Document  # type: ignore
        doc = Document(str(path))
        return "\n".join(p.text for p in doc.paragraphs if p.text.strip())
    elif suffix in {".md", ".txt", ".rst"}:
        return path.read_text(encoding="utf-8", errors="replace")
    else:
        # try plain text fallback
        try:
            return path.read_text(encoding="utf-8", errors="replace")
        except Exception as exc:
            print(f"[StyleCal] WARN: cannot read {path}: {exc}", file=sys.stderr)
            return ""


def _sentences(text: str) -> list[str]:
    """Split text into sentences (simple heuristic)."""
    parts = re.split(r"(?<=[.!?])\s+(?=[A-Z\(])", text)
    return [p.strip() for p in parts if len(p.split()) >= 3]


def _paragraphs(text: str) -> list[str]:
    parts = re.split(r"\n{2,}", text)
    return [p.strip() for p in parts if len(p.split()) >= 10]


HEDGING_WORDS = [
    "suggests", "suggest", "appears", "may", "might", "could", "likely",
    "possibly", "perhaps", "indicate", "imply", "seem", "tend to",
    "consistent with", "compatible with", "potentially",
]
TRANSITIONS = [
    "However", "Nevertheless", "Nonetheless", "In contrast", "Yet",
    "Furthermore", "Moreover", "Additionally", "Notably", "Interestingly",
    "Importantly", "Indeed", "In summary", "Taken together", "Therefore",
    "Thus", "Consequently", "Similarly", "In addition",
]
REPORTING_VERBS = [
    "found", "demonstrated", "showed", "reported", "observed",
    "identified", "revealed", "confirmed", "suggested", "described",
    "proposed", "argued", "noted", "indicated", "established",
]


def analyze_style(texts: list[str]) -> dict:
    """Run 6-dimension style analysis on a list of extracted text blocks."""
    combined = "\n\n".join(texts)

    # D1: Sentence length
    sents = _sentences(combined)
    lens = [len(s.split()) for s in sents] if sents else [20]
    mean_sl = sum(lens) / len(lens)
    stddev_sl = (sum((x - mean_sl) ** 2 for x in lens) / len(lens)) ** 0.5
    rhythm = "variable" if stddev_sl > 7 else "steady"

    # D2: Paragraph length
    paras = _paragraphs(combined)
    para_lens = [len(_sentences(p)) for p in paras] if paras else [4]
    mean_pl = sum(para_lens) / len(para_lens)

    # D3: Vocabulary preferences
    lower = combined.lower()
    hedging = sorted(
        set(w for w in HEDGING_WORDS if w in lower),
        key=lambda w: lower.count(w), reverse=True
    )[:5]
    trans_found = [t for t in TRANSITIONS if t in combined][:4]
    rv_found = sorted(
        set(v for v in REPORTING_VERBS if v in lower),
        key=lambda v: lower.count(v), reverse=True
    )[:4]
    # formality: if "we " or "I " appear a lot → conversational
    we_count = combined.count(" we ") + combined.count("We ")
    i_count = combined.count(" I ") + combined.count("I ")
    word_count = len(combined.split())
    formality = "formal" if (we_count + i_count) / max(word_count, 1) < 0.005 else "moderate-formal"

    # D4: Citation integration
    narrative = len(re.findall(r"[A-Z][a-z]+ (?:et al\.)? ?\(\d{4}\)", combined))
    parenthetical = len(re.findall(r"\(\w[\w\s,]+ ?\d{4}\)", combined))
    total_cit = max(narrative + parenthetical, 1)
    narrative_ratio = round(narrative / total_cit, 2)
    density = round(total_cit / max(len(paras), 1), 2)

    # D5: Modifier style
    adj_count = len(re.findall(r"\b(?:important|critical|significant|novel|unique|remarkable|substantial)\b", lower))
    modifier_density = "elaborate" if adj_count / max(word_count, 1) > 0.01 else "minimal"

    # D6: Register shifts (heuristic — look for Methods markers)
    has_methods = bool(re.search(r"\bmethod[s]?\b|\bprotocol\b|\bwe used\b", lower))
    has_discussion = bool(re.search(r"\bimplication[s]?\b|\bfuture\b|\bconclusion\b", lower))
    if has_methods and has_discussion:
        shifts = "noticeable — likely Methods (neutral) vs Discussion (interpretive)"
    else:
        shifts = "moderate — insufficient section markers to detect strong shifts"

    summary_parts = []
    if rhythm == "variable":
        summary_parts.append(f"variable sentence rhythm (mean {mean_sl:.0f} words, SD {stddev_sl:.0f})")
    else:
        summary_parts.append(f"steady sentence rhythm (~{mean_sl:.0f} words/sentence)")
    if hedging:
        summary_parts.append(f"prefers hedging with \"{hedging[0]}\"")
    summary = "; ".join(summary_parts[:2]) + "."

    return {
        "sentence_length": {
            "mean": round(mean_sl, 1),
            "stddev": round(stddev_sl, 1),
            "rhythm": rhythm,
        },
        "paragraph_length": {
            "mean_sentences": round(mean_pl, 1),
            "variation": "moderate",
        },
        "vocabulary": {
            "hedging": hedging,
            "transitions": trans_found,
            "reporting_verbs": rv_found,
            "formality": formality,
        },
        "citation_integration": {
            "narrative_ratio": narrative_ratio,
            "density_per_paragraph": density,
            "placement": "mixed" if 0.2 < narrative_ratio < 0.8 else ("narrative-dominant" if narrative_ratio >= 0.8 else "parenthetical-dominant"),
        },
        "modifier_style": modifier_density + " — lean prose" if modifier_density == "minimal" else modifier_density + " — rich descriptors",
        "register_shifts": shifts,
        "_summary": summary,
    }


def main() -> None:
    parser = argparse.ArgumentParser(
        prog="insynbio_style_calibration",
        description="6-dimension author voice profiling for biomedical manuscripts",
    )
    parser.add_argument(
        "--samples", nargs="+", required=True,
        help="Paths to past papers (PDF, DOCX, MD, TXT). Minimum 3 recommended.",
    )
    parser.add_argument("--domain", default="general_biomedical",
                        help="Biomedical domain (e.g. oncology, gene_therapy, structural_biology)")
    parser.add_argument("--target-journal", default=None, help="Target journal name (optional)")
    parser.add_argument("--project", default=None, help="Project name for the profile")
    parser.add_argument("--out", required=True, help="Output path for style_profile.json")
    args = parser.parse_args()

    samples = [Path(s) for s in args.samples]
    missing = [s for s in samples if not s.exists()]
    if missing:
        sys.exit(f"ERROR: files not found: {', '.join(str(s) for s in missing)}")
    if len(samples) < 3:
        print(f"[StyleCal] WARN: only {len(samples)} sample(s) provided. "
              "3+ recommended for reliable profiling.", file=sys.stderr)

    print(f"[StyleCal] Analyzing {len(samples)} sample(s) …")
    texts: list[str] = []
    for p in samples:
        text = extract_text_from_file(p)
        if not text.strip():
            print(f"[StyleCal] WARN: empty text from {p}", file=sys.stderr)
        else:
            texts.append(text)
            print(f"[StyleCal]   {p.name} → {len(text.split())} words extracted")

    if not texts:
        sys.exit("ERROR: no text could be extracted from any sample file.")

    profile = analyze_style(texts)

    output = {
        "project": args.project or Path(args.out).parent.name,
        "domain": args.domain,
        "target_journal": args.target_journal,
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "samples_analyzed": len(texts),
        "sample_files": [p.name for p in samples[:len(texts)]],
        "profile": profile,
        "summary": profile.pop("_summary", ""),
        "consumption_note": (
            "Soft guide only. Priority: (1) Discipline conventions > "
            "(2) Journal conventions > (3) Author personal style."
        ),
        "ars_protocol": "shared/style_calibration_protocol.md (ARS academic-paper Step 10)",
    }

    out_path = Path(args.out)
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(json.dumps(output, indent=2, ensure_ascii=False), encoding="utf-8")

    print(f"\n[StyleCal] Style Profile written → {out_path}")
    print(f"[StyleCal] Summary: {output['summary']}")
    print(f"[StyleCal] Key traits:")
    p = output["profile"]
    print(f"  Sentence rhythm : {p['sentence_length']['rhythm']} "
          f"(mean {p['sentence_length']['mean']} words, SD {p['sentence_length']['stddev']})")
    print(f"  Hedging words   : {', '.join(p['vocabulary']['hedging'][:3]) or 'none detected'}")
    print(f"  Citation style  : narrative ratio {p['citation_integration']['narrative_ratio']}")
    print(f"  Modifier density: {p['modifier_style']}")


if __name__ == "__main__":
    main()
