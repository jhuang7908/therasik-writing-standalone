"""
Python-backed figures and statistics for lab HTML reports.

Called during POST /lab/generate_report — researchers upload raw CSV/XLSX;
this module computes descriptive stats + inferential tests and renders charts
before the LLM writes prose (Discussion must not invent numbers).
"""

from __future__ import annotations

import base64
import io
import re
from typing import Any, Callable


ReadTabularFn = Callable[[str, str], Any]
RenderChartFn = Callable[..., str]
LlmCompleteFn = Callable[..., tuple[str, Any]]


def read_tabular(filename: str, data_url: str):
    """Decode a base64 data URL into a pandas DataFrame."""
    import pandas as pd

    _, encoded = data_url.split(",", 1)
    raw = base64.b64decode(encoded)
    name = (filename or "").lower()
    if name.endswith(".csv") or name.endswith(".txt"):
        return pd.read_csv(io.BytesIO(raw))
    if name.endswith(".xlsx") or name.endswith(".xls"):
        return pd.read_excel(io.BytesIO(raw))
    raise ValueError("Unsupported file format. Use CSV or XLSX.")


def _suggest_axes(df) -> tuple[str | None, str | None]:
    numeric_cols = [str(c) for c in df.select_dtypes(include=["number"]).columns]
    cat_cols = [str(c) for c in df.columns if str(c) not in numeric_cols]
    x_col = cat_cols[0] if cat_cols else (str(df.columns[0]) if len(df.columns) else None)
    y_col = numeric_cols[0] if numeric_cols else None
    return x_col, y_col


def summarize_dataframe(df, label: str) -> str:
    """Descriptive + inferential statistics (Python only, no LLM)."""
    import pandas as pd

    lines = [
        f"## {label}",
        f"Rows: {len(df)} · Columns: {', '.join(str(c) for c in df.columns)}",
    ]
    numeric_cols = [str(c) for c in df.select_dtypes(include=["number"]).columns]
    cat_cols = [str(c) for c in df.columns if str(c) not in numeric_cols]

    for col in numeric_cols:
        s = pd.to_numeric(df[col], errors="coerce").dropna()
        if len(s) == 0:
            continue
        lines.append(
            f"  {col}: n={len(s)}, mean={s.mean():.4g}, SD={s.std(ddof=1):.4g}, "
            f"SEM={s.sem():.4g}, min={s.min():.4g}, max={s.max():.4g}"
        )

    x_col, y_col = _suggest_axes(df)
    if x_col and y_col and x_col in df.columns and y_col in df.columns:
        grp = df.groupby(x_col, dropna=False)[y_col]
        lines.append(f"  Grouped {y_col} by {x_col}:")
        for name, sub in grp:
            s = pd.to_numeric(sub, errors="coerce").dropna()
            if len(s) == 0:
                continue
            lines.append(
                f"    {name}: n={len(s)}, mean={s.mean():.4g}, SD={s.std(ddof=1):.4g}"
            )
        lines.extend(_inferential_tests(df, x_col, y_col))

    return "\n".join(lines)


def _inferential_tests(df, x_col: str, y_col: str) -> list[str]:
    out: list[str] = []
    try:
        from scipy import stats
    except Exception:
        return ["  (scipy not available — inferential tests skipped)"]

    groups = list(dict.fromkeys(df[x_col].dropna().astype(str).tolist()))
    series = {
        g: df.loc[df[x_col].astype(str) == g, y_col].dropna().astype(float).tolist()
        for g in groups
    }
    series = {g: v for g, v in series.items() if len(v) >= 2}
    if len(series) < 2:
        return ["  (Need ≥2 groups with n≥2 for hypothesis tests)"]

    if len(series) == 2:
        g0, g1 = list(series.keys())[:2]
        t, p = stats.ttest_ind(series[g0], series[g1], equal_var=False)
        out.append(f"  Welch t-test ({g0} vs {g1}): t={t:.4g}, p={p:.4g}")
    else:
        fval, p = stats.f_oneway(*[series[g] for g in series])
        out.append(f"  One-way ANOVA ({y_col} by {x_col}): F={fval:.4g}, p={p:.4g}")
        g0 = list(series.keys())[0]
        for g in list(series.keys())[1:]:
            t, p = stats.ttest_ind(series[g0], series[g], equal_var=False)
            out.append(f"    vs {g0}: Welch t={t:.4g}, p={p:.4g}")
    return out


def summarize_notes_table(notes: str, label: str) -> str:
    """Parse simple tab-separated or markdown table lines in free text."""
    lines_in = [ln.strip() for ln in (notes or "").splitlines() if ln.strip()]
    if len(lines_in) < 2:
        return ""
    header = None
    rows: list[list[str]] = []
    for ln in lines_in:
        if "\t" in ln:
            parts = [p.strip() for p in ln.split("\t")]
        elif "|" in ln and not re.match(r"^[\|\s\-:]+$", ln):
            parts = [p.strip() for p in ln.strip("|").split("|")]
        else:
            continue
        if not parts:
            continue
        if header is None:
            header = parts
        else:
            rows.append(parts)
    if not header or not rows:
        return ""
    try:
        import pandas as pd

        df = pd.DataFrame(rows, columns=header[: len(rows[0])])
        for c in df.columns:
            df[c] = pd.to_numeric(df[c], errors="ignore")
        return summarize_dataframe(df, f"{label} (from notes table)")
    except Exception:
        return ""


def prepare_blocks_for_report(
    blocks: list[dict[str, Any]] | None,
    *,
    render_chart: RenderChartFn | None = None,
) -> tuple[list[dict[str, Any]], str]:
    """
    Enrich result blocks: auto matplotlib charts + combined Python statistics text.
    """
    enriched: list[dict[str, Any]] = []
    stat_sections: list[str] = []

    for i, block in enumerate(blocks or [], 1):
        if not isinstance(block, dict):
            continue
        b = dict(block)
        label = (b.get("label") or f"Result {i}").strip()
        ds = b.get("dataset") or {}
        fn = str(ds.get("filename") or "").strip()
        data_url = str(ds.get("dataUrl") or ds.get("data_url") or "").strip()

        if fn and data_url:
            try:
                df = read_tabular(fn, data_url)
                stat_sections.append(summarize_dataframe(df, label))
                if render_chart and not str(b.get("chartUrl") or "").startswith("data:image"):
                    x_col, y_col = _suggest_axes(df)
                    if x_col and y_col:
                        b["chartUrl"] = render_chart(
                            df,
                            x_col=x_col,
                            y_col=y_col,
                            chart_type="bar",
                            error_bar="sd",
                            style="nature",
                        )
            except Exception as exc:
                stat_sections.append(f"## {label}\n  (Could not analyze {fn}: {exc})")

        notes_stat = summarize_notes_table(b.get("notes") or "", label)
        if notes_stat:
            stat_sections.append(notes_stat)

        enriched.append(b)

    combined = "\n\n".join(s for s in stat_sections if s.strip())
    if not combined:
        combined = "(No tabular datasets attached — add CSV/XLSX under a result block for Python statistics.)"
    return enriched, combined


_DISCUSSION_SYSTEM = (
    "You are a principal investigator writing the Discussion section of a lab report. "
    "You MUST use ONLY numbers and test results present in PYTHON_STATISTICS. "
    "Do not invent p-values, means, sample sizes, or literature claims. "
    "If statistics are missing, state limitations explicitly. "
    "Third person, past tense, 2–4 short paragraphs. No AI vendor names."
)


def generate_discussion(
    *,
    python_statistics: str,
    title: str = "",
    observations: str = "",
    conclusion: str = "",
    rationality_analysis: str = "",
    pubmed_digest: str = "",
    llm_complete: LlmCompleteFn | None = None,
    model: str = "claude-haiku-4-5",
) -> str:
    """Discussion prose grounded in Python-computed statistics."""
    stats = (python_statistics or "").strip()
    user = (
        f"Title: {title}\n"
        f"Background: {observations or 'n/a'}\n"
        f"Draft conclusion: {conclusion or 'n/a'}\n"
        f"QC / rationality notes: {rationality_analysis or 'n/a'}\n"
        f"Literature digest (cite only these PMIDs if mentioned): {pubmed_digest or 'none'}\n\n"
        f"PYTHON_STATISTICS (authoritative — do not contradict):\n{stats}\n\n"
        "Write the Discussion section text only (plain paragraphs, no HTML)."
    )
    if llm_complete:
        try:
            text, _ = llm_complete(
                system=_DISCUSSION_SYSTEM,
                user_content=user,
                max_tokens=1200,
                temperature=0.25,
                model=model,
            )
            if (text or "").strip():
                return text.strip()
        except Exception:
            pass

    # Deterministic fallback
    parts = [
        "Discussion (Python-statistics–guided):",
        stats[:3500],
    ]
    if conclusion:
        parts.append(f"Conclusion alignment: {conclusion}")
    if rationality_analysis:
        parts.append(f"QC notes: {rationality_analysis[:800]}")
    return "\n\n".join(parts)
