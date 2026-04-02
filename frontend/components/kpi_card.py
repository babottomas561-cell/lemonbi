"""KPI Card component."""
from dash import html

ACCENT_COLORS = {
    "green": "kpi-accent-green",
    "blue": "kpi-accent-blue",
    "amber": "kpi-accent-amber",
    "red": "kpi-accent-red",
    "primary": "kpi-accent-primary",
    "purple": "kpi-accent-purple",
}


def kpi_card(
    label: str,
    value,
    unit: str = "",
    delta: str = "",
    delta_type: str = "neutral",
    accent: str = "primary",
    subtitle: str = "",
    drill_panel: str | None = None,
    drill_item: str | None = None,
):
    """
    Render a KPI card.
    label: short descriptor in uppercase
    value: the main number/text
    unit: optional unit like "kg", "USD", "%"
    delta: optional delta text
    delta_type: "positive", "negative", "neutral"
    accent: color key for left border
    """
    accent_class = ACCENT_COLORS.get(accent, "kpi-accent-primary")

    delta_elem = None
    if delta:
        arrow = (
            "↑" if delta_type == "positive" else ("↓" if delta_type == "negative" else "→")
        )
        delta_elem = html.Div(
            [arrow, " ", delta],
            className=f"kpi-delta {delta_type}",
        )

    subtitle_elem = html.Div(subtitle, className="kpi-subtitle") if subtitle else None

    is_drilldown = bool(drill_panel and drill_item)
    detail_hint = (
        html.Div(
            [
                html.Span("Ver detalle"),
                html.Span("↗", className="kpi-detail-icon"),
            ],
            className="kpi-detail-hint",
        )
        if is_drilldown
        else None
    )

    component_props = {}
    if is_drilldown:
        component_props = {
            "id": {"type": "drill-kpi", "panel": drill_panel, "item": drill_item},
            "n_clicks": 0,
            "role": "button",
            "tabIndex": 0,
            "title": f"Ver datos fuente de {label}",
        }

    return html.Div(
        [
            html.Div(label, className="kpi-label"),
            html.Div(
                [
                    html.Span(value, className="kpi-value"),
                    html.Span(f" {unit}", className="kpi-unit") if unit else None,
                ],
                className="kpi-value-row",
            ),
            subtitle_elem,
            delta_elem,
            detail_hint,
        ],
        className=f"kpi-card {accent_class} {'is-drilldown' if is_drilldown else ''}",
        **component_props,
    )
