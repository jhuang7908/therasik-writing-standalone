"""
Publication-grade Kaplan-Meier / step-curve plot — InSynBio Figure Recipe.

Supports:
  - Kaplan-Meier survival curves (time-to-event data)
  - Dose-response step trends (sequential measurements)
  - Time-series panel overlays with CI bands
  - At-risk table below plot (standard for clinical KM figures)
  - Log-rank p-value annotation

No lifelines dependency required. Pure matplotlib + scipy implementation.

Usage (CLI):
    python scripts/insynbio_figure.py stats --recipe km \\
        --csv data.csv --out figures/km.svg -- --time-col time --event-col event --group-col group

    # Dose-response mode (no event column):
    python scripts/insynbio_figure.py stats --recipe km \\
        --csv data.csv --out figures/km.svg -- --mode trend

CSV schema (survival mode):
    time,event,group[,weight]
    12.5,1,Treatment
    8.2,0,Treatment      # 0 = censored
    15.1,1,Control
    ...

CSV schema (trend mode — sequential steps):
    timepoint,value,group[,ci_low,ci_high]
    0,1.0,Treatment
    3,0.82,Treatment
    6,0.71,Treatment
    ...
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path
from typing import Optional

try:
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    import matplotlib.patches as mpatches
    from matplotlib.lines import Line2D
except ImportError:
    sys.exit("ERROR: matplotlib not installed.")

try:
    import pandas as pd
    import numpy as np
except ImportError:
    sys.exit("ERROR: pandas / numpy not installed.")

try:
    from scipy.stats import chi2
    HAS_SCIPY = True
except ImportError:
    HAS_SCIPY = False


# ── rcParams SSOT ─────────────────────────────────────────────────────────────

def _apply_rcparams(font_size: int = 8) -> None:
    plt.rcParams.update({
        "font.family": "sans-serif",
        "font.sans-serif": ["Arial", "DejaVu Sans", "Liberation Sans"],
        "svg.fonttype": "none",
        "font.size": font_size,
        "axes.spines.right": False,
        "axes.spines.top": False,
        "axes.linewidth": 0.8,
        "legend.frameon": False,
        "xtick.major.width": 0.8,
        "ytick.major.width": 0.8,
    })


# ── Kaplan-Meier estimator ────────────────────────────────────────────────────

def _km_estimate(times: np.ndarray, events: np.ndarray) -> tuple[np.ndarray, np.ndarray, np.ndarray]:
    """
    Compute KM survival estimate.
    Returns (t, S, n_at_risk) at each event time.
    Greenwood's formula for CI is computed externally.
    """
    order = np.argsort(times)
    t = times[order]
    e = events[order]

    n = len(t)
    km_t = [0.0]
    km_s = [1.0]
    km_n = [n]

    unique_times = np.unique(t[e == 1])
    S = 1.0

    for ti in unique_times:
        mask_at_risk = t >= ti
        n_at_risk = mask_at_risk.sum()
        n_events = ((t == ti) & (e == 1)).sum()
        if n_at_risk > 0:
            S = S * (1.0 - n_events / n_at_risk)
        km_t.append(float(ti))
        km_s.append(float(S))
        km_n.append(int(n_at_risk))

    return np.array(km_t), np.array(km_s), np.array(km_n)


def _km_ci(times: np.ndarray, events: np.ndarray, z: float = 1.96
           ) -> tuple[np.ndarray, np.ndarray, np.ndarray]:
    """Greenwood's formula for 95% CI of KM estimator."""
    order = np.argsort(times)
    t = times[order]
    e = events[order]

    unique_times = np.unique(t[e == 1])
    S = 1.0
    var_log = 0.0
    km_t = [0.0]
    km_s = [1.0]
    km_lo = [1.0]
    km_hi = [1.0]

    for ti in unique_times:
        mask_at_risk = t >= ti
        n_at_risk = mask_at_risk.sum()
        n_events = ((t == ti) & (e == 1)).sum()
        if n_at_risk > 0 and (n_at_risk - n_events) > 0:
            S = S * (1.0 - n_events / n_at_risk)
            var_log += n_events / (n_at_risk * (n_at_risk - n_events))
        km_t.append(float(ti))
        km_s.append(float(S))
        # log-log CI
        if S > 0 and S < 1:
            se_log = np.sqrt(var_log)
            log_s = np.log(-np.log(S)) if S > 0 else 0
            lo = np.exp(-np.exp(log_s + z * se_log))
            hi = np.exp(-np.exp(log_s - z * se_log))
        else:
            lo, hi = float(S), float(S)
        km_lo.append(float(np.clip(lo, 0, 1)))
        km_hi.append(float(np.clip(hi, 0, 1)))

    return np.array(km_t), np.array(km_s), np.array(km_lo), np.array(km_hi)


def _logrank_p(t1: np.ndarray, e1: np.ndarray,
               t2: np.ndarray, e2: np.ndarray) -> float:
    """Simplified log-rank test for two groups. Returns p-value."""
    if not HAS_SCIPY:
        return float("nan")
    all_t = np.concatenate([t1[e1 == 1], t2[e2 == 1]])
    all_t = np.unique(all_t)
    O, E = 0.0, 0.0
    V = 0.0
    for ti in all_t:
        n1 = (t1 >= ti).sum()
        n2 = (t2 >= ti).sum()
        d1 = ((t1 == ti) & (e1 == 1)).sum()
        d2 = ((t2 == ti) & (e2 == 1)).sum()
        n = n1 + n2
        d = d1 + d2
        if n < 2:
            continue
        e1_exp = d * n1 / n
        E += e1_exp
        O += d1
        v = d * n1 * n2 * (n - d) / (n ** 2 * (n - 1)) if n > 1 else 0
        V += v
    if V == 0:
        return float("nan")
    chi2_stat = (O - E) ** 2 / V
    return float(1 - chi2.cdf(chi2_stat, df=1))


# ── Palette ───────────────────────────────────────────────────────────────────

DEFAULT_PALETTE = [
    "#2A6496",  # blue
    "#C0392B",  # red
    "#27AE60",  # green
    "#E67E22",  # orange
    "#8E44AD",  # purple
    "#16A085",  # teal
]


# ── Main renderer ─────────────────────────────────────────────────────────────

def km_plot(
    df: "pd.DataFrame",
    *,
    time_col: str = "time",
    event_col: str | None = "event",
    group_col: str | None = "group",
    ci_low_col: str | None = "ci_low",
    ci_high_col: str | None = "ci_high",
    value_col: str = "value",
    mode: str = "survival",       # "survival" | "trend"
    show_ci: bool = True,
    show_censors: bool = True,
    show_at_risk: bool = True,
    show_pvalue: bool = True,
    x_label: str = "Time",
    y_label: str = "Survival probability",
    y_lim: tuple[float, float] = (0.0, 1.05),
    title: str = "",
    palette: list[str] | None = None,
    double_column: bool = False,
    font_size: int = 8,
    dpi: int = 300,
) -> "plt.Figure":
    """
    Draw a Kaplan-Meier survival curve or step-trend plot.

    Parameters
    ----------
    mode       : "survival" uses KM estimator; "trend" uses raw value column
    show_at_risk : adds at-risk table below plot (survival mode only)
    """
    _apply_rcparams(font_size)
    pal = palette or DEFAULT_PALETTE

    groups = sorted(df[group_col].unique()) if group_col and group_col in df.columns else [None]
    n_groups = len(groups)

    # Figure layout — with or without at-risk table
    fig_w = 17.4 / 2.54 if double_column else 8.5 / 2.54
    if show_at_risk and mode == "survival" and n_groups > 0:
        fig_h_cm = 7.0 + n_groups * 0.8
        fig, axes = plt.subplots(
            2, 1, figsize=(fig_w, fig_h_cm / 2.54),
            gridspec_kw={"height_ratios": [4, n_groups * 0.8], "hspace": 0.04},
        )
        ax, ax_risk = axes
        ax_risk.axis("off")
    else:
        fig, ax = plt.subplots(figsize=(fig_w, 6.5 / 2.54))
        ax_risk = None

    logrank_p: Optional[float] = None
    legend_lines = []

    for gi, group in enumerate(groups):
        color = pal[gi % len(pal)]
        label = str(group) if group is not None else "Overall"

        if group is not None:
            gdf = df[df[group_col] == group]
        else:
            gdf = df

        if mode == "survival" and event_col and event_col in df.columns:
            times = gdf[time_col].values.astype(float)
            events = gdf[event_col].values.astype(float)
            km_t, km_s, km_lo, km_hi = _km_ci(times, events)

            # Step function
            t_step = np.repeat(km_t, 2)[1:]
            s_step = np.repeat(km_s, 2)[:-1]
            ax.plot(t_step, s_step, color=color, linewidth=1.5, label=label, zorder=3)

            if show_ci:
                lo_step = np.repeat(km_lo, 2)[:-1]
                hi_step = np.repeat(km_hi, 2)[:-1]
                ax.fill_between(t_step, lo_step, hi_step, color=color, alpha=0.12, step=None, zorder=1)

            if show_censors:
                censored = gdf[gdf[event_col] == 0]
                if len(censored):
                    cens_t = censored[time_col].values
                    cens_s = np.interp(cens_t, km_t, km_s)
                    ax.scatter(cens_t, cens_s, marker="+", s=30, color=color,
                               linewidths=1.0, zorder=4)

            # At-risk numbers
            if ax_risk is not None:
                at_risk_times = np.linspace(km_t[0], km_t[-1], 5)
                at_risk_n = [(times >= ti).sum() for ti in at_risk_times]
                for xi, (ti, ni) in enumerate(zip(at_risk_times, at_risk_n)):
                    ax_risk.text(ti / km_t[-1], 1 - (gi + 0.5) / n_groups,
                                 str(ni), ha="center", va="center",
                                 fontsize=font_size - 2, color=color,
                                 transform=ax_risk.transAxes)
                ax_risk.text(-0.01, 1 - (gi + 0.5) / n_groups, label,
                             ha="right", va="center", fontsize=font_size - 2,
                             color=color, transform=ax_risk.transAxes)

            # Log-rank p-value (two-group only)
            if show_pvalue and n_groups == 2 and gi == 0:
                t0, e0 = times, events
            elif show_pvalue and n_groups == 2 and gi == 1:
                logrank_p = _logrank_p(t0, e0, times, events)

        else:
            # Trend mode — raw step values
            tp = gdf[time_col].values if time_col in gdf.columns else gdf.iloc[:, 0].values
            vals = gdf[value_col].values if value_col in gdf.columns else gdf.iloc[:, 1].values
            ax.step(tp, vals, color=color, linewidth=1.5, where="post", label=label, zorder=3)
            if show_ci and ci_low_col and ci_low_col in gdf.columns and ci_high_col in gdf.columns:
                lo = gdf[ci_low_col].values
                hi = gdf[ci_high_col].values
                ax.fill_between(tp, lo, hi, color=color, alpha=0.15, step="post", zorder=1)

        legend_lines.append(Line2D([0], [0], color=color, linewidth=2, label=label))

    ax.set_ylim(*y_lim)
    ax.set_xlim(left=0)
    ax.set_xlabel(x_label, fontsize=font_size)
    ax.set_ylabel(y_label, fontsize=font_size)

    if title:
        ax.set_title(title, fontsize=font_size + 1, pad=6)

    if n_groups > 1:
        ax.legend(handles=legend_lines, fontsize=font_size - 1,
                  loc="lower left", handlelength=1.5)

    if logrank_p is not None:
        p_str = f"p<0.001" if logrank_p < 0.001 else f"p={logrank_p:.3f}"
        ax.text(0.97, 0.97, f"Log-rank\n{p_str}", ha="right", va="top",
                fontsize=font_size - 1, transform=ax.transAxes, color="#333333")

    # At-risk label
    if ax_risk is not None:
        ax_risk.set_xlim(0, 1)
        ax_risk.set_ylim(0, 1)
        ax_risk.text(-0.01, 1.0, "At risk:", ha="right", va="top",
                     fontsize=font_size - 2, transform=ax_risk.transAxes,
                     color="#666666", fontstyle="italic")

    plt.tight_layout(pad=0.3)
    return fig


# ── CLI ───────────────────────────────────────────────────────────────────────

def main() -> None:
    parser = argparse.ArgumentParser(prog="km_plot",
                                     description="KM survival / step-trend curve")
    parser.add_argument("--csv", required=True)
    parser.add_argument("--out", required=True)
    parser.add_argument("--time-col", default="time")
    parser.add_argument("--event-col", default="event",
                        help="Event indicator (1=event, 0=censored). Omit for trend mode.")
    parser.add_argument("--group-col", default="group")
    parser.add_argument("--value-col", default="value", help="For trend mode")
    parser.add_argument("--mode", default="survival", choices=["survival", "trend"])
    parser.add_argument("--no-ci", dest="show_ci", action="store_false", default=True)
    parser.add_argument("--no-at-risk", dest="show_at_risk", action="store_false", default=True)
    parser.add_argument("--no-censors", dest="show_censors", action="store_false", default=True)
    parser.add_argument("--x-label", default="Time")
    parser.add_argument("--y-label", default="Survival probability")
    parser.add_argument("--title", default="")
    parser.add_argument("--double-column", action="store_true")
    parser.add_argument("--dpi", type=int, default=300)
    args = parser.parse_args()

    df = pd.read_csv(args.csv)
    print(f"[km_plot] Loaded {len(df)} rows, mode={args.mode}")

    fig = km_plot(
        df,
        time_col=args.time_col,
        event_col=args.event_col if args.event_col in df.columns else None,
        group_col=args.group_col if args.group_col in df.columns else None,
        value_col=args.value_col,
        mode=args.mode,
        show_ci=args.show_ci,
        show_at_risk=args.show_at_risk,
        show_censors=args.show_censors,
        x_label=args.x_label,
        y_label=args.y_label,
        title=args.title,
        double_column=args.double_column,
        dpi=args.dpi,
    )

    out = Path(args.out)
    out.parent.mkdir(parents=True, exist_ok=True)
    fig.savefig(out, dpi=args.dpi, bbox_inches="tight")
    print(f"[km_plot] → {out}")
    svg = out.with_suffix(".svg")
    if svg != out:
        fig.savefig(svg, format="svg", bbox_inches="tight")
        print(f"[km_plot] → {svg}")
    plt.close(fig)


if __name__ == "__main__":
    main()
