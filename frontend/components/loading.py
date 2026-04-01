from dash import dcc, html

from frontend.components.empty_state import empty_state
from frontend.utils import empty_figure


def loading_graph(graph_id: str, message: str = "Cargando visual..."):
    return dcc.Loading(
        type="default",
        color="#516C53",
        delay_show=120,
        children=dcc.Graph(
            id=graph_id,
            figure=empty_figure(message),
            config={"displayModeBar": False},
        ),
    )


def loading_slot(slot_id: str, placeholder=None):
    return dcc.Loading(
        type="default",
        color="#516C53",
        delay_show=120,
        children=html.Div(
            placeholder if placeholder is not None else empty_state("Cargando datos..."),
            id=slot_id,
        ),
    )
