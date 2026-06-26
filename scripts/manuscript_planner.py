"""
manuscript_planner.py
=====================
TheraSIK Manuscript Planning & Outline Generation

Converts a research idea → structured writing plan:
  - Article type detection (Original / Review / Brief Comm. / Methods)
  - IMRaD or Review section scaffold
  - Section-level word budgets calibrated to journal limits
  - Writing order (science-first: Methods → Results → Discussion → Intro → Abstract)
  - Key message template for each section
  - Figure/table slot planning
  - Literature gap framing

No LLM API calls required — rule-based heuristics + templates.

Output:
  {project_dir}/00_planning/manuscript_plan.md
  {project_dir}/00_planning/section_outline.md

Usage (CLI):
  python scripts/manuscript_planner.py <project_dir>
  python scripts/manuscript_planner.py <project_dir> --topic "CAR-T therapy in AML" \\
      --journal "Nature Medicine" --type review

Programmatic:
  from manuscript_planner import plan_manuscript, generate_outline
"""

from __future__ import annotations

import argparse
import json
import os
import re
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional

SKILL_DIR = Path(os.environ.get("THERASIK_DIR", Path(__file__).resolve().parents[1]))
sys.path.insert(0, str(SKILL_DIR / "scripts"))

try:
    from submission_prep import load_journal
except ImportError:
    def load_journal(name): return None


# ── Article type profiles ──────────────────────────────────────────────────────

ARTICLE_PROFILES = {
    "original": {
        "label":         "Original Research Article",
        "sections":      ["Abstract", "Introduction", "Methods", "Results", "Discussion",
                          "Conclusions", "Acknowledgements", "References"],
        "word_budget":   {"Abstract": 250, "Introduction": 600, "Methods": 900,
                          "Results": 1200, "Discussion": 1000, "Conclusions": 150},
        "writing_order": ["Methods", "Results", "Discussion", "Introduction",
                          "Conclusions", "Abstract"],
        "figures":       5,
        "tables":        4,
        "refs":          50,
    },
    "review": {
        "label":         "Review Article",
        "sections":      ["Abstract", "Introduction", "Background", "Main Body",
                          "Discussion", "Conclusions", "References"],
        "word_budget":   {"Abstract": 300, "Introduction": 500, "Background": 800,
                          "Main Body": 3000, "Discussion": 800, "Conclusions": 300},
        "writing_order": ["Background", "Main Body", "Introduction", "Discussion",
                          "Conclusions", "Abstract"],
        "figures":       6,
        "tables":        3,
        "refs":          100,
    },
    "brief": {
        "label":         "Brief Communication / Letter",
        "sections":      ["Abstract", "Introduction", "Results", "Discussion",
                          "Methods", "References"],
        "word_budget":   {"Abstract": 150, "Introduction": 200, "Results": 600,
                          "Discussion": 400, "Methods": 300},
        "writing_order": ["Methods", "Results", "Discussion", "Introduction", "Abstract"],
        "figures":       2,
        "tables":        1,
        "refs":          20,
    },
    "methods": {
        "label":         "Methods / Protocol Article",
        "sections":      ["Abstract", "Introduction", "Protocol", "Technical Notes",
                          "Validation", "Discussion", "References"],
        "word_budget":   {"Abstract": 250, "Introduction": 400, "Protocol": 1500,
                          "Technical Notes": 600, "Validation": 600, "Discussion": 400},
        "writing_order": ["Protocol", "Technical Notes", "Validation", "Introduction",
                          "Discussion", "Abstract"],
        "figures":       4,
        "tables":        3,
        "refs":          40,
    },
    "meta": {
        "label":         "Systematic Review / Meta-Analysis",
        "sections":      ["Abstract (PRISMA)", "Introduction", "Methods",
                          "Results / PRISMA Flow", "Discussion", "Conclusions",
                          "References"],
        "word_budget":   {"Abstract (PRISMA)": 350, "Introduction": 500, "Methods": 1200,
                          "Results / PRISMA Flow": 1500, "Discussion": 1000, "Conclusions": 200},
        "writing_order": ["Methods", "Results / PRISMA Flow", "Discussion",
                          "Introduction", "Conclusions", "Abstract (PRISMA)"],
        "figures":       4,   # PRISMA diagram + forest plots
        "tables":        5,
        "refs":          80,
    },
    "case": {
        "label":         "Case Report",
        "sections":      ["Abstract", "Introduction", "Case Presentation",
                          "Discussion", "Conclusions", "References"],
        "word_budget":   {"Abstract": 200, "Introduction": 200, "Case Presentation": 800,
                          "Discussion": 500, "Conclusions": 100},
        "writing_order": ["Case Presentation", "Discussion", "Introduction",
                          "Conclusions", "Abstract"],
        "figures":       3,
        "tables":        2,
        "refs":          25,
    },
}

# ── Section key messages templates ────────────────────────────────────────────

KEY_MESSAGES = {
    "Abstract": (
        "Background (1 sentence): {gap}\n"
        "Objective (1 sentence): {aim}\n"
        "Methods (1-2 sentences): {design}\n"
        "Results (2-3 sentences): [PRIMARY OUTCOME + key numbers]\n"
        "Conclusion (1 sentence): [implication for the field]"
    ),
    "Introduction": (
        "Para 1 — Context: Why does this topic matter clinically/biologically?\n"
        "Para 2 — Knowledge gap: What is NOT known? (use: 'remains unknown', 'has not been shown')\n"
        "Para 3 — Hypothesis & Aim: 'We hypothesized that… / The aim of this study was to…'"
    ),
    "Methods": (
        "Study design & setting\n"
        "Participants / samples: inclusion & exclusion criteria, n=\n"
        "Intervention / exposure\n"
        "Outcomes: primary + secondary\n"
        "Statistical analysis: software, tests, α level, correction for multiple comparisons\n"
        "Ethics: IRB/IACUC approval number"
    ),
    "Results": (
        "Para 1 — Participant flow / sample characteristics (Table 1)\n"
        "Para 2+ — Primary outcome (one paragraph per figure)\n"
        "Each paragraph: finding statement first → figure reference → numbers with CI\n"
        "Final paragraph — secondary / exploratory outcomes"
    ),
    "Discussion": (
        "Para 1 — Summary: restate main findings without raw numbers\n"
        "Para 2 — Context vs literature: agree / disagree with prior work\n"
        "Para 3 — Mechanism / explanation\n"
        "Para 4 — Clinical / translational implications\n"
        "Para 5 — Limitations (required)\n"
        "Para 6 — Future directions\n"
        "Para 7 — Conclusion (1-2 sentences)"
    ),
    "Conclusions": (
        "1-3 sentences. Restate key finding + implication.\n"
        "Do NOT introduce new information."
    ),
    "Background": (
        "Para 1 — Epidemiology / clinical burden\n"
        "Para 2 — Current standard of care / existing knowledge\n"
        "Para 3 — Gaps and controversies\n"
        "Para 4 — Scope of this review + search strategy"
    ),
    "Main Body": (
        "Organise by theme, not chronology.\n"
        "Each sub-section: [Theme] → evidence → synthesis → outstanding questions.\n"
        "End each sub-section with a 'Key Points' box or summary sentence."
    ),
    "Protocol": (
        "Numbered step-by-step format.\n"
        "Include: timing, materials, expected outcome, critical steps, troubleshooting."
    ),
    "Case Presentation": (
        "Patient demographics (anonymised)\n"
        "Presenting complaint → history → examination → investigations\n"
        "Differential diagnosis considered\n"
        "Treatment & clinical course\n"
        "Outcome at follow-up"
    ),
    "Abstract (PRISMA)": (
        "Background, Objectives, Data sources, Eligibility criteria,\n"
        "Results (n included, summary effect, I² heterogeneity),\n"
        "Conclusions, Systematic review registration (PROSPERO ID)"
    ),
    "Methods (PRISMA)": (
        "Search strategy (databases, date range, MeSH terms)\n"
        "PRISMA flow diagram (Figure 1)\n"
        "Risk of bias assessment tool (Cochrane RoB / GRADE)\n"
        "Statistical pooling: model (fixed/random), heterogeneity test, subgroup analyses"
    ),
}


# ── Detect article type from keywords ─────────────────────────────────────────

def _detect_article_type(topic: str, hint: str = "") -> str:
    text = (topic + " " + hint).lower()
    if any(k in text for k in ["systematic review", "meta-analysis", "meta analysis", "prisma"]):
        return "meta"
    if any(k in text for k in ["review", "overview", "landscape", "progress", "advances in"]):
        return "review"
    if any(k in text for k in ["protocol", "method", "technique", "pipeline", "workflow", "assay"]):
        return "methods"
    if any(k in text for k in ["case report", "case series", "case of", "patient with"]):
        return "case"
    if any(k in text for k in ["brief", "letter", "communication", "short", "preliminary"]):
        return "brief"
    return "original"


# ── Budget calibration from journal data ──────────────────────────────────────

def _calibrate_to_journal(profile: dict, journal_data: dict | None, article_type: str) -> dict:
    """Adjust word budgets to match journal limits."""
    if not journal_data:
        return profile

    art_specs = journal_data.get("article_types", {})
    spec: dict = {}
    for k, v in art_specs.items():
        if k.lower() == article_type.lower():
            spec = v
            break
    if not spec and art_specs:
        spec = next(iter(art_specs.values()))

    total_limit = spec.get("max_words_main_text", 0)
    if not total_limit:
        return profile

    current_total = sum(profile["word_budget"].values())
    if current_total == 0:
        return profile

    scale = total_limit / current_total
    adjusted = {sec: max(50, int(w * scale)) for sec, w in profile["word_budget"].items()}
    profile = dict(profile)
    profile["word_budget"]    = adjusted
    profile["_total_budget"]  = total_limit
    profile["_abstract_limit"] = spec.get("max_words_abstract", profile["word_budget"].get("Abstract", 250))
    profile["refs"]            = spec.get("max_references", profile["refs"])
    profile["figures"]         = spec.get("max_figures", profile["figures"])
    return profile


# ── Figure slot planner ────────────────────────────────────────────────────────

FIGURE_SLOTS = {
    "original": [
        ("Figure 1", "Study design / overview / CONSORT/STROBE flow"),
        ("Figure 2", "Primary outcome — main result"),
        ("Figure 3", "Mechanistic / subgroup analysis"),
        ("Figure 4", "Secondary outcome or validation cohort"),
        ("Figure 5", "Model / summary schematic"),
    ],
    "review": [
        ("Figure 1", "Conceptual framework / overview diagram"),
        ("Figure 2", "Landscape of current evidence (timeline or heatmap)"),
        ("Figure 3", "Mechanism diagram"),
        ("Figure 4", "Comparative summary of key studies"),
        ("Figure 5", "Future directions / open questions diagram"),
        ("Figure 6", "Clinical translation roadmap"),
    ],
    "meta": [
        ("Figure 1", "PRISMA flow diagram (required)"),
        ("Figure 2", "Forest plot — primary outcome"),
        ("Figure 3", "Forest plot — subgroup analyses"),
        ("Figure 4", "Funnel plot (publication bias)"),
    ],
    "brief": [
        ("Figure 1", "Main finding"),
        ("Figure 2", "Validation / mechanism"),
    ],
    "methods": [
        ("Figure 1", "Protocol overview diagram"),
        ("Figure 2", "Key step illustration / micrograph"),
        ("Figure 3", "Validation data"),
        ("Figure 4", "Representative output / benchmark comparison"),
    ],
    "case": [
        ("Figure 1", "Clinical images / imaging"),
        ("Figure 2", "Lab values / timeline"),
        ("Figure 3", "Pathology (if applicable)"),
    ],
}

TABLE_SLOTS = {
    "original": [
        ("Table 1", "Baseline characteristics of study population"),
        ("Table 2", "Primary and secondary outcomes"),
        ("Table 3", "Subgroup / multivariate analysis"),
        ("Table 4", "Adverse events / safety data"),
    ],
    "review": [
        ("Table 1", "Summary of included studies / key papers"),
        ("Table 2", "Comparison of approaches / agents / trials"),
        ("Table 3", "Ongoing clinical trials"),
    ],
    "meta": [
        ("Table 1", "Characteristics of included studies"),
        ("Table 2", "Risk of bias assessment"),
        ("Table 3", "Sensitivity analyses"),
        ("Table 4", "GRADE evidence summary"),
        ("Table 5", "Subgroup analyses"),
    ],
    "brief": [("Table 1", "Data / comparison table")],
    "methods": [
        ("Table 1", "Materials list / reagents"),
        ("Table 2", "Troubleshooting guide"),
        ("Table 3", "Benchmark comparison with existing methods"),
    ],
    "case": [
        ("Table 1", "Laboratory results / investigations"),
        ("Table 2", "Similar reported cases in literature"),
    ],
}


# ── Literature gap framing ────────────────────────────────────────────────────

GAP_TEMPLATES = [
    "Despite [prior knowledge], the [specific aspect] remains poorly understood.",
    "While [A] has been demonstrated, it is unclear whether [B] also [C].",
    "Previous studies have focused on [narrow scope], leaving [broader question] unaddressed.",
    "No randomised controlled trial has evaluated [intervention] in [population].",
    "The mechanism by which [X] leads to [Y] has not been directly investigated.",
    "Existing [tools/models/datasets] do not account for [limiting factor].",
]


# ── Core planning function ────────────────────────────────────────────────────

def plan_manuscript(
    project_dir: str | Path,
    topic: str = "",
    aim: str = "",
    article_type: str = "",
    journal_name: str = "",
    design: str = "",
    keywords: list[str] | None = None,
) -> dict:
    """
    Generate a structured manuscript plan for a project.

    Args:
        project_dir:  Path to manuscript project directory.
        topic:        Research topic / title idea.
        aim:          Primary aim / hypothesis statement.
        article_type: Override type (original/review/brief/methods/meta/case).
        journal_name: Target journal (used to calibrate word budgets).
        design:       Study design (e.g. 'RCT', 'retrospective cohort', 'in vitro').
        keywords:     List of 5-8 keywords.

    Returns:
        Plan dict; also writes 00_planning/manuscript_plan.md and section_outline.md.
    """
    proj = Path(project_dir).resolve()

    # Load config if available
    config: dict = {}
    cfg_path = proj / "project_config.json"
    if cfg_path.exists():
        config = json.loads(cfg_path.read_text(encoding="utf-8"))

    topic        = topic        or config.get("title", "")
    aim          = aim          or config.get("aim", "")
    article_type = article_type or config.get("article_type", "")
    journal_name = journal_name or config.get("target_journal", "")
    design       = design       or config.get("study_design", "")
    keywords     = keywords     or config.get("keywords", [])

    # Detect article type
    if not article_type:
        article_type = _detect_article_type(topic, aim)
    article_type = article_type.lower().strip()
    if article_type not in ARTICLE_PROFILES:
        article_type = "original"

    profile = dict(ARTICLE_PROFILES[article_type])

    # Calibrate to journal
    journal_data = load_journal(journal_name) if journal_name else None
    profile = _calibrate_to_journal(profile, journal_data, article_type)

    # Build plan
    plan = {
        "topic":         topic,
        "aim":           aim,
        "article_type":  article_type,
        "article_label": profile["label"],
        "journal":       journal_name,
        "study_design":  design,
        "keywords":      keywords or [],
        "sections":      profile["sections"],
        "word_budget":   profile["word_budget"],
        "writing_order": profile["writing_order"],
        "figures":       FIGURE_SLOTS.get(article_type, FIGURE_SLOTS["original"])[:profile["figures"]],
        "tables":        TABLE_SLOTS.get(article_type, TABLE_SLOTS["original"])[:profile["tables"]],
        "max_refs":      profile["refs"],
        "key_messages":  {s: KEY_MESSAGES.get(s, f"[{s} content]") for s in profile["sections"]},
        "gap_templates": GAP_TEMPLATES,
        "planned_at":    datetime.now(timezone.utc).isoformat(),
    }

    # Write output
    plan_dir = proj / "00_planning"
    plan_dir.mkdir(exist_ok=True)
    _write_plan_md(plan, plan_dir / "manuscript_plan.md")
    _write_outline_md(plan, plan_dir / "section_outline.md", aim=aim, design=design)

    # Save JSON
    (plan_dir / "manuscript_plan.json").write_text(
        json.dumps(plan, indent=2, ensure_ascii=False), encoding="utf-8"
    )

    return plan


def _write_plan_md(plan: dict, path: Path):
    lines = [
        f"# Manuscript Plan",
        f"",
        f"**Topic:** {plan['topic'] or '(not specified)'}",
        f"**Type:** {plan['article_label']}",
        f"**Journal:** {plan['journal'] or '(not specified)'}",
        f"**Design:** {plan['study_design'] or '(not specified)'}",
        f"**Planned:** {plan['planned_at'][:10]}",
        f"",
        f"---",
        f"",
        f"## Aim / Hypothesis",
        f"",
        plan['aim'] or "> _State your primary aim here: 'We hypothesized that…'_",
        f"",
        f"---",
        f"",
        f"## Writing Order",
        f"",
        f"Follow this order to write efficiently (data-first, argument-second):",
        f"",
    ]
    for i, sec in enumerate(plan["writing_order"], 1):
        budget = plan["word_budget"].get(sec, "")
        bstr   = f" (~{budget} words)" if budget else ""
        lines.append(f"{i}. **{sec}**{bstr}")

    lines += [
        f"",
        f"---",
        f"",
        f"## Word Budget",
        f"",
        f"| Section | Target words |",
        f"|---------|-------------|",
    ]
    total = 0
    for sec, w in plan["word_budget"].items():
        lines.append(f"| {sec} | {w:,} |")
        total += w
    lines.append(f"| **Total (excl. refs)** | **{total:,}** |")

    lines += [
        f"",
        f"**Max references:** {plan['max_refs']}",
        f"",
        f"---",
        f"",
        f"## Planned Figures",
        f"",
    ]
    for label, desc in plan["figures"]:
        lines.append(f"- **{label}:** {desc}")

    lines += [
        f"",
        f"## Planned Tables",
        f"",
    ]
    for label, desc in plan["tables"]:
        lines.append(f"- **{label}:** {desc}")

    lines += [
        f"",
        f"---",
        f"",
        f"## Keywords",
        f"",
        ", ".join(plan["keywords"]) if plan["keywords"] else "_Add 5-8 MeSH-aligned keywords here_",
        f"",
        f"---",
        f"",
        f"## Knowledge Gap Templates",
        f"",
        f"_(Choose one and adapt to your topic)_",
        f"",
    ]
    for t in plan["gap_templates"]:
        lines.append(f"- {t}")

    lines += [
        f"",
        f"---",
        f"",
        f"*Generated by TheraSIK Manuscript Planner. Update as your research progresses.*",
    ]

    path.write_text("\n".join(lines), encoding="utf-8")


def _write_outline_md(plan: dict, path: Path, aim: str = "", design: str = ""):
    lines = [
        f"# Section Outline",
        f"",
        f"> **Type:** {plan['article_label']}  |  **Journal:** {plan['journal'] or 'TBD'}",
        f"",
    ]

    for sec in plan["sections"]:
        budget  = plan["word_budget"].get(sec, "")
        bstr    = f" *(~{budget} words)*" if budget else ""
        km      = plan["key_messages"].get(sec, "")
        in_order = plan["writing_order"].index(sec) + 1 if sec in plan["writing_order"] else "—"

        lines += [
            f"---",
            f"",
            f"## {sec}{bstr}",
            f"",
            f"**Write order:** #{in_order}",
            f"",
            f"**Key messages / structure:**",
            f"",
        ]
        for kline in km.split("\n"):
            lines.append(f"> {kline}")
        lines += [
            f"",
            f"**Draft:**",
            f"",
            f"_[Write here]_",
            f"",
        ]

    lines += [
        f"---",
        f"",
        f"*Generated by TheraSIK. Sections expand as you write.*",
    ]

    path.write_text("\n".join(lines), encoding="utf-8")


def generate_outline(
    project_dir: str | Path,
    article_type: str = "original",
) -> str:
    """
    Generate a blank section outline skeleton (no topic required).
    Returns the path to the generated file.
    """
    proj = Path(project_dir).resolve()
    plan = plan_manuscript(proj, article_type=article_type)
    return str(proj / "00_planning" / "section_outline.md")


# ── CLI ───────────────────────────────────────────────────────────────────────

def main():
    parser = argparse.ArgumentParser(description="TheraSIK Manuscript Planner")
    parser.add_argument("project_dir", help="Path to manuscript project directory")
    parser.add_argument("--topic",   default="", help="Research topic / title idea")
    parser.add_argument("--aim",     default="", help="Primary aim or hypothesis")
    parser.add_argument("--type",    default="", dest="article_type",
                        choices=list(ARTICLE_PROFILES.keys()) + [""],
                        help="Article type (auto-detected if omitted)")
    parser.add_argument("--journal", default="", help="Target journal name")
    parser.add_argument("--design",  default="", help="Study design")
    parser.add_argument("--json",    action="store_true", help="Output raw JSON")
    args = parser.parse_args()

    plan = plan_manuscript(
        args.project_dir,
        topic        = args.topic,
        aim          = args.aim,
        article_type = args.article_type,
        journal_name = args.journal,
        design       = args.design,
    )

    if args.json:
        print(json.dumps(plan, indent=2, ensure_ascii=False))
        return

    print(f"\nPlan generated: {plan['article_label']}")
    print(f"Journal: {plan['journal'] or '—'}")
    print(f"Sections ({len(plan['sections'])}): {', '.join(plan['sections'])}")
    print(f"Word budget: {sum(plan['word_budget'].values()):,} words")
    print(f"Figures: {len(plan['figures'])}  |  Tables: {len(plan['tables'])}  |  Refs: {plan['max_refs']}")
    proj = Path(args.project_dir).resolve()
    print(f"\nFiles written:")
    print(f"  {proj}/00_planning/manuscript_plan.md")
    print(f"  {proj}/00_planning/section_outline.md")


if __name__ == "__main__":
    main()
