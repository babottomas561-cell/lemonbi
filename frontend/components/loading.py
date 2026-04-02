from dash import dcc, html

from frontend.chart_theme import loading_figure
from frontend.components.empty_state import loading_state


def loading_graph(graph_id: str, message: str = "Aplicando filtros y preparando la visualización."):
    return dcc.Loading(
        type="default",
        color="#516C53",
        delay_show=180,
        className="loading-shell loading-shell-graph",
        children=dcc.Graph(
            id=graph_id,
            figure=loading_figure(message),
            config={
                "displayModeBar": False,
                "displaylogo": False,
                "responsive": True,
            },
            className="premium-graph",
        ),
    )


def loading_slot(slot_id: str, placeholder=None):
    return dcc.Loading(
        type="default",
        color="#516C53",
        delay_show=180,
        className="loading-shell loading-shell-slot",
        children=html.Div(
            placeholder
            if placeholder is not None
            else loading_state(
                title="Preparando bloque",
                message="Actualizando el contenido para el período y filtros seleccionados.",
            ),
            id=slot_id,
        ),
    )
