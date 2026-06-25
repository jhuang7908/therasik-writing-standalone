"""
Figure legend / caption generator — InSynBio Figure Recipe.

Generates structured, journal-compliant figure legends from a sidecar JSON spec.
Enforces: claim → methods → stats → data-source traceability chain.
NO stats or n-values are invented — they must be provided in the spec.

Journal templates built-in: Nature family | Cell Press | PLOS | generic

Usage (CLI):
    python scripts/insynbio_figure.py stats --recipe legend \\
        --legend-spec spec.json --out figures/Figure1_legend.md

    python scripts/insynbio_figure.py stats --recipe legend \\
        --legend-spec spec.json --journal nature --out figures/Figure1_legend.md

Spec JSON format:
{
  "figure_number": "1",
  "title": "Short descriptive title (≤12 words)",
  "panels": [
    {
      "label": "a",
      "claim": "One-sentence scientific claim this panel supports",
      "type": "bar_chart | box_plot | heatmap | forest | volcano | km | schematic | table | microscopy | other",
      "method": "What was measured / calculated / modeled",
      "stats": {
        "test": "one-way ANOVA + Tukey post-hoc",
        "n": "n=45 per group",
        "ci": "95% CI"
      },
      "source": "Table 2 / data/processed/panel_a.csv / [user-provided]",
      "data_availability": "Supplementary Table S1"
    }
  ],
  "overall_source": "All data from SSOT file paper/tables/table_main.xlsx",
  "journal": "nature",
  "word_limit": 350
}
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any


# ── Journal templates ─────────────────────────────────────────────────────────

JOURNAL_TEMPLATES: dict[str, dict] = {
    "nature": {
        "title_style": "bold",
        "panel_label_style": "bold_lowercase",   # **a**
        "stats_inline": True,                    # stats embedded in panel text
        "word_limit": 350,
        "max_panels_before_break": 6,
        "required_fields": ["claim", "stats", "source"],
        "preamble": "",
        "postamble": "All scale bars are indicated where applicable.",
    },
    "cell": {
        "title_style": "bold",
        "panel_label_style": "bold_uppercase",   # (A)
        "stats_inline": True,
        "word_limit": 400,
        "required_fields": ["claim", "stats", "source"],
        "preamble": "",
        "postamble": "Data are mean ± SEM unless otherwise stated.",
    },
    "plos": {
        "title_style": "plain",
        "panel_label_style": "uppercase_parens",  # (A)
        "stats_inline": False,
        "word_limit": 300,
        "required_fields": ["claim", "source"],
        "preamble": "",
        "postamble": "",
    },
    "generic": {
        "title_style": "plain",
        "panel_label_style": "lowercase_dot",    # a.
        "stats_inline": True,
        "word_limit": 300,
        "required_fields": ["claim"],
        "preamble": "",
        "postamble": "",
    },
}


# ── Formatters ────────────────────────────────────────────────────────────────

def _panel_label(label: str, style: str) -> str:
    l = label.strip().lower()
    u = l.upper()
    if style == "bold_lowercase":
        return f"**{l}**"
    if style == "bold_uppercase":
        return f"**({u})**"
    if style == "uppercase_parens":
        return f"({u})"
    if style == "lowercase_dot":
        return f"{l}."
    return l


def _format_stats(stats: dict | None, inline: bool) -> str:
    if not stats:
        return ""
    parts = []
    if "test" in stats:
        parts.append(stats["test"])
    if "n" in stats:
        parts.append(stats["n"])
    if "ci" in stats:
        parts.append(stats["ci"])
    if "p" in stats:
        parts.append(stats["p"])
    if not parts:
        return ""
    s = "; ".join(parts)
    return f"({s})" if inline else s


def _format_panel(panel: dict, template: dict, idx: int) -> str:
    style = template.get("panel_label_style", "lowercase_dot")
    label_str = _panel_label(panel.get("label", chr(97 + idx)), style)
    inline = template.get("stats_inline", True)

    parts = [label_str]

    claim = panel.get("claim", "").strip()
    if claim:
        parts.append(claim)

    method = panel.get("method", "").strip()
    if method:
        parts.append(method)

    stats_str = _format_stats(panel.get("stats"), inline)
    if stats_str:
        parts.append(stats_str)

    source = panel.get("source", "").strip()
    if source:
        parts.append(f"Source: {source}.")

    data_avail = panel.get("data_availability", "").strip()
    if data_avail:
        parts.append(f"See also {data_avail}.")

    return " ".join(parts)


def _count_words(text: str) -> int:
    return len(text.split())


# ── Main generator ────────────────────────────────────────────────────────────

def generate_legend(spec: dict, journal: str | None = None) -> dict:
    """
    Generate a figure legend from a spec dict.
    Returns dict with: legend_md, legend_text, word_count, warnings, qa.
    """
    journal_key = (journal or spec.get("journal", "generic")).lower()
    if journal_key not in JOURNAL_TEMPLATES:
        journal_key = "generic"
    tmpl = JOURNAL_TEMPLATES[journal_key]
    word_limit = spec.get("word_limit", tmpl.get("word_limit", 300))

    warnings: list[str] = []
    qa: list[dict] = []

    # Title
    fig_num = spec.get("figure_number", "")
    title = spec.get("title", "").strip()
    prefix = f"Figure {fig_num}. " if fig_num else "Figure. "
    if tmpl["title_style"] == "bold":
        title_line = f"**{prefix}{title}**"
    else:
        title_line = f"{prefix}{title}"

    if not title:
        warnings.append("WARN: 'title' is empty — required for all journals")
        qa.append({"field": "title", "status": "FAIL", "reason": "missing"})
    elif len(title.split()) > 15:
        warnings.append(f"WARN: title is long ({len(title.split())} words) — keep ≤12–15 words")
        qa.append({"field": "title", "status": "WARN", "reason": "too long"})
    else:
        qa.append({"field": "title", "status": "PASS"})

    # Panels
    panels = spec.get("panels", [])
    if not panels:
        warnings.append("WARN: no panels defined in spec")

    panel_texts = []
    required = tmpl.get("required_fields", ["claim"])

    for i, panel in enumerate(panels):
        panel_label = panel.get("label", chr(97 + i))
        for req in required:
            if not panel.get(req):
                warnings.append(f"WARN: panel '{panel_label}' missing required field '{req}'")
                qa.append({"panel": panel_label, "field": req, "status": "FAIL"})
        panel_texts.append(_format_panel(panel, tmpl, i))

    # Assemble
    preamble = tmpl.get("preamble", "")
    postamble = tmpl.get("postamble", "")
    overall_source = spec.get("overall_source", "")

    body_parts = []
    if preamble:
        body_parts.append(preamble)
    body_parts.extend(panel_texts)
    if overall_source:
        body_parts.append(f"All data: {overall_source}")
    if postamble:
        body_parts.append(postamble)

    legend_md = title_line + "\n\n" + " ".join(body_parts)
    legend_text = legend_md.replace("**", "").replace("*", "")
    wc = _count_words(legend_text)

    if wc > word_limit:
        warnings.append(f"WARN: legend is {wc} words, exceeds {word_limit}-word limit for {journal_key}")
        qa.append({"field": "word_count", "status": "WARN",
                   "value": wc, "limit": word_limit})
    else:
        qa.append({"field": "word_count", "status": "PASS",
                   "value": wc, "limit": word_limit})

    overall = "PASS" if not any(w.startswith("WARN: panel") or "missing" in w for w in warnings) else "WARN"

    return {
        "legend_md": legend_md,
        "legend_text": legend_text,
        "word_count": wc,
        "word_limit": word_limit,
        "journal_template": journal_key,
        "overall": overall,
        "warnings": warnings,
        "qa": qa,
    }


# ── Spec template generator ───────────────────────────────────────────────────

def generate_spec_template(figure_number: str = "1",
                            n_panels: int = 3,
                            journal: str = "nature") -> dict:
    """Generate a blank spec JSON template to fill in."""
    panels = []
    for i in range(n_panels):
        label = chr(97 + i)
        panels.append({
            "label": label,
            "claim": f"FILL_ME: one-sentence scientific claim for panel {label}",
            "type": "FILL_ME: bar_chart|box_plot|heatmap|forest|volcano|km|schematic|microscopy",
            "method": "FILL_ME: what was measured/calculated",
            "stats": {
                "test": "FILL_ME: statistical test used",
                "n": "FILL_ME: n= per group",
                "ci": "FILL_ME: 95% CI or SD",
                "p": "FILL_ME: p-value or 'NS'",
            },
            "source": "FILL_ME: table ID / CSV path / [user-provided]",
            "data_availability": "FILL_ME: Supplementary Table SX or 'N/A'",
        })
    return {
        "_warning": "FILL_ME all fields — do NOT submit without replacing every FILL_ME",
        "_never_invent_stats": "n, p-values, CI must come from actual analysis results",
        "figure_number": figure_number,
        "title": "FILL_ME: short descriptive title (≤12 words)",
        "journal": journal,
        "word_limit": JOURNAL_TEMPLATES.get(journal, JOURNAL_TEMPLATES["generic"])["word_limit"],
        "overall_source": "FILL_ME: where the data files live",
        "panels": panels,
    }


# ── CLI ───────────────────────────────────────────────────────────────────────

def main() -> None:
    parser = argparse.ArgumentParser(
        prog="figure_legend",
        description="Generate journal-compliant figure legend from spec JSON",
    )
    sub = parser.add_subparsers(dest="cmd", required=True)

    # generate from spec
    p_gen = sub.add_parser("generate", help="Generate legend from spec JSON")
    p_gen.add_argument("--legend-spec", required=True, help="Path to spec JSON")
    p_gen.add_argument("--journal", default=None,
                       choices=list(JOURNAL_TEMPLATES.keys()),
                       help="Override journal template")
    p_gen.add_argument("--out", default=None, help="Output .md file")

    # scaffold template
    p_tmpl = sub.add_parser("template", help="Scaffold a blank spec JSON template")
    p_tmpl.add_argument("--figure", default="1", help="Figure number")
    p_tmpl.add_argument("--panels", type=int, default=3, help="Number of panels")
    p_tmpl.add_argument("--journal", default="nature",
                        choices=list(JOURNAL_TEMPLATES.keys()))
    p_tmpl.add_argument("--out", required=True, help="Output spec JSON path")

    # list templates
    sub.add_parser("list-templates", help="List available journal templates")

    args = parser.parse_args()

    if args.cmd == "generate":
        spec_path = Path(args.legend_spec)
        if not spec_path.exists():
            sys.exit(f"ERROR: spec file not found: {spec_path}")
        spec = json.loads(spec_path.read_text(encoding="utf-8"))
        result = generate_legend(spec, args.journal)

        print(f"[figure_legend] {result['overall']} — {result['word_count']}/{result['word_limit']} words")
        for w in result["warnings"]:
            print(f"  {w}")

        if args.out:
            out = Path(args.out)
            out.parent.mkdir(parents=True, exist_ok=True)
            out.write_text(result["legend_md"], encoding="utf-8")
            # also write qa sidecar
            qa_path = out.with_suffix(".qa.json")
            qa_path.write_text(json.dumps({
                "overall": result["overall"],
                "word_count": result["word_count"],
                "word_limit": result["word_limit"],
                "warnings": result["warnings"],
                "qa": result["qa"],
            }, indent=2), encoding="utf-8")
            print(f"[figure_legend] Legend → {out}")
            print(f"[figure_legend] QA    → {qa_path}")
        else:
            print("\n" + result["legend_md"])

    elif args.cmd == "template":
        tmpl = generate_spec_template(args.figure, args.panels, args.journal)
        out = Path(args.out)
        out.parent.mkdir(parents=True, exist_ok=True)
        out.write_text(json.dumps(tmpl, indent=2, ensure_ascii=False), encoding="utf-8")
        print(f"[figure_legend] Spec template → {out}")
        print(f"  Fill every FILL_ME field before running 'generate'")

    elif args.cmd == "list-templates":
        print(f"\n{'Journal':<15} {'Word limit':<12} {'Panel style':<25} {'Stats inline'}")
        print("-" * 65)
        for k, v in JOURNAL_TEMPLATES.items():
            print(f"  {k:<13} {v['word_limit']:<12} {v['panel_label_style']:<25} {v['stats_inline']}")


if __name__ == "__main__":
    main()
