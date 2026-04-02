import dash_bootstrap_components as dbc
from dash import dcc, html

from frontend.components.loading import loading_graph


def chart_card(title: str, graph_id: str, subtitle: str = "", priority: str = "secondary"):
    return html.Div(
        [
            html.Div(
                [
                    html.Div(
                        [
                            html.Div(title, className="chart-title"),
                            html.Div(subtitle, className="chart-subtitle") if subtitle else None,
                        ],
                        className="chart-title-stack",
                    ),
                    html.Div("Vista ejecutiva", className="chart-static-pill"),
                ],
                className="chart-card-head",
            ),
            loading_graph(graph_id),
            html.Div("Valores agregados para el período seleccionado", className="chart-card-caption"),
        ],
        className=f"chart-card chart-card-{priority}",
    )


def drilldown_chart_card(
    title: str,
    graph_id: str,
    panel: str,
    item: str,
    subtitle: str = "",
    priority: str = "secondary",
):
    return html.Div(
        [
            html.Div(
                [
                    html.Div(
                        [
                            html.Div(title, className="chart-title"),
                            html.Div(subtitle, className="chart-subtitle") if subtitle else None,
                        ],
                        className="chart-title-stack",
                    ),
                    html.Div(
                        [
                            html.Div("Interactivo", className="chart-interactive-pill"),
                            html.Button(
                                "Ver datos",
                                id={"type": "drill-chart", "panel": panel, "item": item},
                                n_clicks=0,
                                className="chart-detail-button",
                            ),
                        ],
                        className="chart-action-group",
                    ),
                ],
                className="chart-card-head",
            ),
            loading_graph(graph_id),
            html.Div("Usá “Ver datos” para explorar el detalle con filtros activos", className="chart-card-caption"),
        ],
        className=f"chart-card chart-card-drill chart-card-{priority}",
    )


def render_drilldown_modal():
    return html.Div(
        [
            dcc.Store(id="drilldown-request"),
            dcc.Store(id="drilldown-data"),
            dcc.Download(id="drilldown-download-csv"),
            dcc.Download(id="drilldown-download-excel"),
            dbc.Modal(
                [
                    dbc.ModalHeader(
                        [
                            html.Div(
                                [
                                    html.Div("Detalle fuente", className="drilldown-kicker"),
                                    html.H3(id="drilldown-modal-title", className="drilldown-title"),
                                    html.Div(id="drilldown-modal-description", className="drilldown-description"),
                                ],
                                className="drilldown-header-copy",
                            )
                        ],
                        close_button=False,
                        class_name="drilldown-modal-header",
                    ),
                    dbc.ModalBody(
                        dcc.Loading(
                            type="default",
                            color="#516C53",
                            delay_show=120,
                            children=html.Div(id="drilldown-modal-body"),
                        ),
                        class_name="drilldown-modal-body",
                    ),
                    dbc.ModalFooter(
                        [
                            html.Div(
                                [
                                    dbc.Button("Descargar CSV", id="drilldown-download-csv-btn", class_name="drilldown-action-button", n_clicks=0),
                                    dbc.Button("Descargar Excel", id="drilldown-download-excel-btn", class_name="drilldown-action-button secondary", n_clicks=0),
                                ],
                                className="drilldown-action-group",
                            ),
                            dbc.Button("Cerrar", id="drilldown-close", class_name="drilldown-close-button", n_clicks=0),
                        ],
                        class_name="drilldown-modal-footer",
                    ),
                ],
                id="drilldown-modal",
                is_open=False,
                centered=True,
                size="xl",
                scrollable=True,
                fade=False,
                enforceFocus=False,
                keyboard=True,
                zindex=1060,
                class_name="drilldown-modal",
                modal_class_name="drilldown-modal-shell",
                backdrop_class_name="drilldown-backdrop",
                content_class_name="drilldown-modal-content",
                backdrop=True,
            ),
        ]
    )
