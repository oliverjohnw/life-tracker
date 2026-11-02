"""Shared Plotly toolkit so every tracker's charts look like one system.

Rules baked in (see the dataviz skill): one accent per single-series chart,
hairline solid grids, thin rounded bars with a gap, donuts capped at six
slices, a legend whenever there is more than one series, selective labels.
"""

import math
from collections import Counter

import plotly.graph_objects as go

FONT = "Inter, system-ui, -apple-system, 'Segoe UI', sans-serif"
INK = "#eceef4"
MUTED = "#8b93a7"
GRID = "rgba(255,255,255,0.07)"
SURFACE = "#14171f"
OTHER = "#5b6377"
# Validated categorical order for dark surfaces (identity, never magnitude).
SERIES = ["#3987e5", "#d95926", "#199e70", "#c98500", "#d55181", "#9085e9"]


def _finish(fig, height, legend=False, left=8, bottom=8, legend_cfg=None, tick_prefix=""):
    fig.update_layout(
        height=height,
        autosize=True,
        paper_bgcolor="rgba(0,0,0,0)",
        plot_bgcolor="rgba(0,0,0,0)",
        font=dict(family=FONT, size=12, color=MUTED),
        margin=dict(l=left, r=12, t=12, b=bottom),
        hoverlabel=dict(
            bgcolor="#1d2230",
            bordercolor="#2c3346",
            font=dict(family=FONT, color=INK, size=13),
        ),
        showlegend=legend,
        legend=legend_cfg or dict(orientation="h", y=1.14, x=0, font=dict(color=INK, size=12)),
        dragmode=False,
    )
    fig.update_xaxes(showgrid=False, zeroline=False, ticks="", fixedrange=True, automargin=True,
                     linecolor=GRID, tickfont=dict(color=MUTED))
    fig.update_yaxes(gridcolor=GRID, zeroline=False, showline=False, ticks="", fixedrange=True,
                     automargin=True, tickfont=dict(color=MUTED), tickprefix=tick_prefix)
    return fig.to_html(
        full_html=False,
        include_plotlyjs=False,
        config={"displayModeBar": False, "responsive": True},
    )


def _short(label, limit=26):
    label = str(label)
    return label if len(label) <= limit else label[: limit - 1].rstrip() + "…"


def column_chart(labels, values, color, *, unit="", height=280, prefix=""):
    """Vertical bars, one series. Only the tallest bar carries a value label."""
    top = max(values) if values else 0
    labelled = [f"{prefix}{v:,.0f}" if v == top and v else "" for v in values]
    fig = go.Figure(
        go.Bar(
            x=[str(label) for label in labels],
            y=values,
            text=labelled,
            textposition="outside",
            textfont=dict(color=INK, size=12),
            cliponaxis=False,
            marker=dict(color=color, cornerradius=5),
            hovertemplate=f"<b>%{{x}}</b><br>{prefix}%{{y:,.0f}} {unit}<extra></extra>",
        )
    )
    fig.update_layout(bargap=0.38)
    if top <= 8:
        fig.update_yaxes(dtick=1)  # no half-a-show ticks on small counts
    return _finish(fig, height, bottom=4)


def row_chart(pairs, color, *, unit="", height=None, prefix=""):
    """Horizontal ranking bars from [(label, value), ...]; values labelled at the bar end."""
    pairs = list(pairs)
    labels = [_short(p[0]) for p in pairs]
    fig = go.Figure(
        go.Bar(
            x=[p[1] for p in pairs],
            y=labels,
            orientation="h",
            customdata=[str(p[0]) for p in pairs],
            text=[f"{prefix}{p[1]:,.0f}" for p in pairs],
            textposition="outside",
            textfont=dict(color=INK, size=12),
            cliponaxis=False,
            marker=dict(color=color, cornerradius=5),
            hovertemplate=f"<b>%{{customdata}}</b><br>{prefix}%{{x:,.0f}} {unit}<extra></extra>",
        )
    )
    fig.update_layout(bargap=0.4)
    fig.update_yaxes(autorange="reversed", showgrid=False, tickfont=dict(color=INK))
    fig.update_xaxes(showgrid=True, gridcolor=GRID, showticklabels=False)
    return _finish(fig, height or max(180, 40 * len(pairs) + 30), left=4)


def stacked_columns(labels, series, *, unit="", height=280, prefix=""):
    """series = [(name, values, color), ...] — stacked with a 2px surface gap between fills."""
    fig = go.Figure()
    for name, values, color in series:
        fig.add_bar(
            x=[str(label) for label in labels],
            y=values,
            name=name,
            marker=dict(color=color, line=dict(color=SURFACE, width=2), cornerradius=4),
            hovertemplate=f"{name}: {prefix}%{{y:,.0f}} {unit}<extra></extra>",
        )
    fig.update_layout(barmode="stack", bargap=0.38, hovermode="x unified")
    return _finish(fig, height, legend=True, bottom=4, tick_prefix=prefix)


def fold_tail(pairs, keep=6):
    """Keep the top `keep` slices and fold the rest into 'Other' (donuts are capped at six)."""
    pairs = list(pairs)
    if len(pairs) <= keep:
        return pairs
    head, tail = pairs[: keep - 1], pairs[keep - 1 :]
    return head + [("Other", sum(v for _, v in tail))]


def donut(pairs, *, height=280, center=None, center_label=""):
    pairs = fold_tail(pairs)
    colors = [OTHER if label == "Other" else SERIES[i % len(SERIES)] for i, (label, _) in enumerate(pairs)]
    fig = go.Figure(
        go.Pie(
            labels=[p[0] for p in pairs],
            values=[p[1] for p in pairs],
            hole=0.64,
            sort=False,
            direction="clockwise",
            textinfo="none",
            marker=dict(colors=colors, line=dict(color=SURFACE, width=2)),
            hovertemplate="<b>%{label}</b><br>%{value} (%{percent})<extra></extra>",
        )
    )
    if center is not None:
        fig.add_annotation(
            text=f"<b style='font-size:26px;color:{INK}'>{center}</b><br><span style='font-size:12px'>{center_label}</span>",
            showarrow=False, x=0.29, y=0.5, xref="paper", yref="paper", xanchor="center", yanchor="middle",
        )
    legend_cfg = dict(orientation="v", x=0.62, y=0.5, xanchor="left", yanchor="middle", font=dict(color=INK, size=12))
    fig.update_traces(domain=dict(x=[0, 0.58]))
    return _finish(fig, height, legend=True, legend_cfg=legend_cfg)


def line_chart(x, y, color, *, unit="", height=280, zero_line=False, y_title="", hover_text=None):
    fig = go.Figure(
        go.Scatter(
            x=x,
            y=y,
            mode="lines+markers",
            line=dict(color=color, width=2, shape="linear"),
            marker=dict(size=9, color=color, line=dict(color=SURFACE, width=2)),
            text=hover_text,
            hovertemplate=f"<b>%{{text}}</b><br>%{{y}} {unit}<extra></extra>" if hover_text else f"%{{x}}<br>%{{y}} {unit}<extra></extra>",
        )
    )
    if zero_line:
        fig.add_hline(y=0, line=dict(color=GRID, width=1))
    if y_title:
        fig.update_yaxes(title=dict(text=y_title, font=dict(color=MUTED, size=11)))
    return _finish(fig, height)


# ── data helpers ────────────────────────────────────────────────────────────

def tally(values, limit=None):
    """[('a', 3), ('b', 1)] — most common first, blanks dropped."""
    counts = Counter(v for v in values if v not in (None, ""))
    return counts.most_common(limit)


def per_year(dates):
    """Counts per calendar year, with empty years filled in so gaps are visible."""
    years = Counter(d.year for d in dates if d)
    if not years:
        return [], []
    labels = list(range(min(years), max(years) + 1))
    return labels, [years.get(y, 0) for y in labels]


def per_month(dates):
    """Continuous month-by-month counts from the first to the last month, gaps included."""
    dates = [d for d in dates if d]
    if not dates:
        return [], []
    counts = Counter((d.year, d.month) for d in dates)
    (y, m), (end_y, end_m) = min(counts), max(counts)
    labels, values = [], []
    names = ["Jan", "Feb", "Mar", "Apr", "May", "Jun", "Jul", "Aug", "Sep", "Oct", "Nov", "Dec"]
    while (y, m) <= (end_y, end_m):
        labels.append(f"{names[m - 1]} '{str(y)[2:]}")
        values.append(counts.get((y, m), 0))
        y, m = (y + 1, 1) if m == 12 else (y, m + 1)
    return labels, values


def per_month_of_year(dates):
    names = ["Jan", "Feb", "Mar", "Apr", "May", "Jun", "Jul", "Aug", "Sep", "Oct", "Nov", "Dec"]
    counts = Counter(d.month for d in dates if d)
    return names, [counts.get(m, 0) for m in range(1, 13)]


def rating_buckets(ratings):
    """Whole-point buckets (6–7, 7–8 …), lowest populated bucket through 9–10."""
    values = [float(r) for r in ratings if r is not None]
    if not values:
        return [], []
    lowest = max(0, min(int(math.floor(min(values))), 9))
    buckets = list(range(lowest, 10))
    counts = Counter(min(int(math.floor(v)), 9) for v in values)
    return [f"{b}–{b + 1}" for b in buckets], [counts.get(b, 0) for b in buckets]


def average(values):
    values = [float(v) for v in values if v is not None]
    return sum(values) / len(values) if values else None


def card(title, html, subtitle="", wide=False):
    return {"title": title, "subtitle": subtitle, "html": html, "wide": wide, "empty": None}


def empty_card(title, message, subtitle="", wide=False):
    return {"title": title, "subtitle": subtitle, "html": "", "wide": wide, "empty": message}
