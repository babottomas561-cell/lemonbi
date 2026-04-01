"""Empty state component for when there's no data."""
from dash import html


def empty_state(
    title="Sin datos",
    message="No hay información disponible para los filtros seleccionados.",
    icon="○",
):
    return html.Div(
        className="empty-state",
        children=[
            html.Div(icon, className="empty-state-icon"),
            html.Div(title, className="empty-state-title"),
            html.Div(message, className="empty-state-text"),
        ],
    )
