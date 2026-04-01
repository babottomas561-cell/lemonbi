import dash
from dash import html

from frontend.components.empty_state import empty_state
from frontend.components.header import render_header


dash.register_page(__name__)


layout = html.Div(
    [
        render_header(
            "Página no encontrada",
            "La ruta solicitada no forma parte de la demo activa.",
            "Error 404",
        ),
        html.Div(
            [
                html.Div(
                    empty_state(
                        title="Ruta no disponible",
                        message="Volvé al resumen ejecutivo o navegá desde el menú lateral para continuar dentro de la demo.",
                        icon="404",
                    ),
                    className="chart-card",
                )
            ],
            id="page-content",
        ),
    ]
)
