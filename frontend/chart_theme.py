from __future__ import annotations

import math

import plotly.graph_objects as go
import plotly.io as pio

BRAND_GREEN = "#3F6B4B"
FOREST = "#294536"
OLIVE = "#6C8C5A"
MOSS = "#95B29E"
GOLD = "#B69245"
SAND = "#D8C9A5"
CLAY = "#C26A45"
SLATE = "#78856A"
INK = "#243126"
TEXT_SOFT = "#667265"
GRID = "rgba(65, 86, 61, 0.08)"
BORDER = "rgba(65, 86, 61, 0.14)"
SURFACE = "rgba(0,0,0,0)"

CHART_COLORS = [BRAND_GREEN, OLIVE, GOLD, MOSS, CLAY, SLATE, SAND]


def register_plotly_theme() -> None:
    if "lemonbi" in pio.templates:
        pio.templates.default = "lemonbi"
        return

    template = go.layout.Template(
        layout=go.Layout(
            colorway=CHART_COLORS,
            paper_bgcolor=SURFACE,
            plot_bgcolor=SURFACE,
            font=dict(family="Manrope, Source Sans 3, Segoe UI, sans-serif", size=12, color=TEXT_SOFT),
            title=dict(font=dict(family="Manrope, sans-serif", size=16, color=INK), x=0.0, xanchor="left"),
            margin=dict(l=34, r=20, t=34, b=34),
            hoverlabel=dict(
                bgcolor="rgba(255, 252, 247, 0.96)",
                bordercolor="rgba(65, 86, 61, 0.18)",
                font=dict(family="Manrope, sans-serif", size=12, color=INK),
                align="left",
                namelength=-1,
            ),
            legend=dict(
                bgcolor="rgba(255,255,255,0)",
                borderwidth=0,
                font=dict(size=11, color=TEXT_SOFT),
                orientation="h",
                yanchor="bottom",
                y=1.01,
                xanchor="left",
                x=0.0,
            ),
            xaxis=dict(
                showgrid=False,
                showline=True,
                linecolor=BORDER,
                linewidth=1,
                tickcolor="rgba(0,0,0,0)",
                zeroline=False,
                automargin=True,
                separatethousands=True,
                tickfont=dict(size=11, color=TEXT_SOFT),
                title=dict(font=dict(size=11, color=TEXT_SOFT)),
            ),
            yaxis=dict(
                showgrid=True,
                gridcolor=GRID,
                gridwidth=1,
                showline=False,
                zeroline=False,
                automargin=True,
                separatethousands=True,
                tickfont=dict(size=11, color=TEXT_SOFT),
                title=dict(font=dict(size=11, color=TEXT_SOFT)),
            ),
            bargap=0.26,
            bargroupgap=0.12,
            dragmode=False,
            clickmode="event+select",
            transition=dict(duration=220),
            uniformtext=dict(minsize=10, mode="hide"),
        )
    )
    pio.templates["lemonbi"] = template
    pio.templates.default = "lemonbi"


def chart_layout(
    title: str = "",
    height: int = 340,
    emphasis: str = "secondary",
    showlegend: bool = True,
    unified_hover: bool = False,
) -> dict:
    top_margin = 28 if emphasis == "hero" else 22
    bottom_margin = 52 if showlegend else 34
    return dict(
        template="lemonbi",
        title=dict(text=title, font=dict(size=16 if emphasis == "hero" else 14, color=INK)),
        height=height,
        margin=dict(l=34, r=18, t=top_margin, b=bottom_margin),
        hovermode="x unified" if unified_hover else "closest",
        showlegend=showlegend,
        hoverlabel=dict(namelength=-1),
    )


def status_figure(
    title: str = "Sin datos",
    message: str = "No hay información disponible para los filtros seleccionados.",
    height: int = 320,
    tone: str = "empty",
    context: str = "",
) -> go.Figure:
    palette = {
        "empty": ("○", "#7A8376"),
        "loading": ("···", GOLD),
        "error": ("!", CLAY),
    }
    icon, accent = palette.get(tone, palette["empty"])
    fig = go.Figure()
    context_html = f"<br><span style='font-size:11px;color:{TEXT_SOFT}'>{context}</span>" if context else ""
    fig.add_annotation(
        text=f"<span style='font-size:20px;color:{accent}'>{icon}</span><br><b>{title}</b><br>"
        f"<span style='font-size:12px;color:{TEXT_SOFT}'>{message}</span>{context_html}",
        x=0.5,
        y=0.5,
        xref="paper",
        yref="paper",
        showarrow=False,
        align="center",
        font=dict(size=14, color=INK, family="Manrope"),
    )
    fig.update_layout(
        template="lemonbi",
        height=height,
        margin=dict(l=10, r=10, t=12, b=10),
        xaxis=dict(visible=False),
        yaxis=dict(visible=False),
        showlegend=False,
    )
    return fig


def empty_figure(
    message: str = "No hay información disponible para los filtros seleccionados.",
    height: int = 320,
    context: str = "",
) -> go.Figure:
    return status_figure(
        title="Sin datos",
        message=message,
        height=height,
        tone="empty",
        context=context,
    )


def loading_figure(message: str = "Aplicando filtros y actualizando la visualización.", height: int = 320) -> go.Figure:
    return status_figure(
        title="Preparando visual",
        message=message,
        height=height,
        tone="loading",
    )


def error_figure(message: str = "No se pudo cargar este visual.", height: int = 320) -> go.Figure:
    return status_figure(
        title="Visual no disponible",
        message=message,
        height=height,
        tone="error",
    )


def add_reference_line(fig: go.Figure, value: float, label: str, color: str = GOLD, dash: str = "dot") -> None:
    fig.add_hline(
        y=value,
        line_color=color,
        line_dash=dash,
        line_width=1.4,
        annotation_text=label,
        annotation_position="top right",
        annotation_font=dict(size=11, color=color, family="Manrope"),
    )


def add_metric_badge(fig: go.Figure, text: str, tone: str = "primary") -> None:
    palette = {
        "primary": ("rgba(63,107,75,0.1)", BRAND_GREEN),
        "warning": ("rgba(182,146,69,0.12)", GOLD),
        "danger": ("rgba(194,106,69,0.12)", CLAY),
    }
    bg, fg = palette.get(tone, palette["primary"])
    fig.add_annotation(
        x=0.0,
        y=1.13,
        xref="paper",
        yref="paper",
        xanchor="left",
        yanchor="bottom",
        align="left",
        text=text,
        showarrow=False,
        font=dict(size=11, color=fg, family="Manrope"),
        bgcolor=bg,
        bordercolor="rgba(0,0,0,0)",
        borderpad=6,
    )


def add_peak_annotation(fig: go.Figure, x, y, text: str, color: str = FOREST) -> None:
    fig.add_annotation(
        x=x,
        y=y,
        text=text,
        showarrow=True,
        arrowhead=2,
        arrowsize=1,
        arrowwidth=1.2,
        arrowcolor=color,
        ax=24,
        ay=-26,
        bgcolor="rgba(255,252,247,0.95)",
        bordercolor="rgba(65, 86, 61, 0.14)",
        borderwidth=1,
        borderpad=6,
        font=dict(size=11, color=INK, family="Manrope"),
    )


def donut_layout(height: int = 360) -> dict:
    return dict(
        template="lemonbi",
        height=height,
        margin=dict(l=10, r=10, t=10, b=10),
        showlegend=True,
        legend=dict(orientation="v", x=1.03, y=0.5, yanchor="middle"),
    )


def add_donut_center_label(fig: go.Figure, headline: str, caption: str = "") -> None:
    text = f"<b>{headline}</b>"
    if caption:
        text += f"<br><span style='font-size:11px;color:{TEXT_SOFT}'>{caption}</span>"
    fig.add_annotation(
        text=text,
        x=0.5,
        y=0.5,
        xref="paper",
        yref="paper",
        showarrow=False,
        align="center",
        font=dict(family="Manrope", size=16, color=INK),
    )


def smart_bar_colors(values: list[float], positive: str = BRAND_GREEN, neutral: str = MOSS, negative: str = CLAY, highlight: int | None = None) -> list[str]:
    if not values:
        return []
    if highlight is not None and 0 <= highlight < len(values):
        return [positive if idx == highlight else neutral for idx in range(len(values))]
    if min(values) < 0 < max(values):
        return [positive if value >= 0 else negative for value in values]
    return [positive] + [neutral] * max(0, len(values) - 1)


def best_index(values: list[float], reverse: bool = False) -> int | None:
    if not values:
        return None
    target = min(values) if reverse else max(values)
    return values.index(target)


def compact_number(value: float, suffix: str = "") -> str:
    absolute = abs(value)
    if absolute >= 1_000_000:
        return f"{value / 1_000_000:.1f}M{suffix}"
    if absolute >= 1_000:
        return f"{value / 1_000:.1f}k{suffix}"
    if isinstance(value, float) and not math.isclose(value, round(value)):
        return f"{value:.1f}{suffix}"
    return f"{value:,.0f}{suffix}"


register_plotly_theme()
