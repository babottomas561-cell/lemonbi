import dash
import dash_bootstrap_components as dbc
import plotly.graph_objects as go
from dash import Input, Output, callback, dcc, html

from frontend.components.empty_state import empty_state
from frontend.components.filter_bar import date_filter, dropdown_filter, render_filter_bar
from frontend.components.header import render_header
from frontend.components.kpi_card import kpi_card
from frontend.components.loading import loading_graph, loading_slot
from frontend.components.tables import render_table
from frontend.utils import api_get, chart_layout, empty_figure, fetch_options, filter_params, fmt_num, insights_panel

dash.register_page(__name__, path="/contexto", name="Contexto Externo")


layout = html.Div(
    [
        render_header("Contexto Externo", "Tipo de cambio, clima y referencias de mercado", "Entorno de campaña"),
        dcc.Store(id={"type": "panel-filters", "panel": "contexto"}, data={}),
        html.Div(
            [
                render_filter_bar(
                    [
                        dropdown_filter("CAMPAÑA", "contexto-campaña", fetch_options("campanas", "campanas"), width="110px"),
                        date_filter("DESDE", "contexto-fecha-desde", "2024-03-01"),
                        date_filter("HASTA", "contexto-fecha-hasta", "2024-11-30"),
                    ]
                ),
                html.Div(id="contexto-kpi-row-1", className="kpi-row"),
                html.Div(id="contexto-kpi-row-2", className="kpi-row"),
                dbc.Row(
                    [
                        dbc.Col(
                            html.Div(
                                [
                                    html.Div("Evolución del Dólar de Referencia", className="chart-title"),
                                    loading_graph("contexto-chart-dolar"),
                                ],
                                className="chart-card",
                            ),
                            width=6,
                        ),
                        dbc.Col(
                            html.Div(
                                [
                                    html.Div("Precio de Referencia", className="chart-title"),
                                    loading_graph("contexto-chart-precio"),
                                ],
                                className="chart-card",
                            ),
                            width=6,
                        ),
                    ],
                    className="g-3",
                ),
                dbc.Row(
                    [
                        dbc.Col(
                            html.Div(
                                [
                                    html.Div("Lluvia y Temperatura", className="chart-title"),
                                    loading_graph("contexto-chart-clima"),
                                ],
                                className="chart-card",
                            ),
                            width=8,
                        ),
                        dbc.Col(
                            html.Div(
                                [
                                    html.Div("Riesgo Climático", className="chart-title"),
                                    loading_graph("contexto-chart-riesgo"),
                                ],
                                className="chart-card",
                            ),
                            width=4,
                        ),
                    ],
                    className="g-3",
                ),
                html.Div(id="contexto-insights"),
                html.Div(
                    [
                        html.Div("Detalle de Contexto", className="table-header"),
                        loading_slot("contexto-tabla"),
                    ],
                    className="table-card",
                ),
            ],
            id="page-content",
        ),
    ]
)


@callback(
    Output({"type": "panel-filters", "panel": "contexto"}, "data"),
    Input("contexto-campaña", "value"),
    Input("contexto-fecha-desde", "date"),
    Input("contexto-fecha-hasta", "date"),
)
def sync_contexto_filters_store(campaña, fecha_desde, fecha_hasta):
    return filter_params(
        campaña=campaña,
        fecha_desde=fecha_desde,
        fecha_hasta=fecha_hasta,
    )


@callback(
    Output("contexto-kpi-row-1", "children"),
    Output("contexto-kpi-row-2", "children"),
    Output("contexto-chart-dolar", "figure"),
    Output("contexto-chart-precio", "figure"),
    Output("contexto-chart-clima", "figure"),
    Output("contexto-chart-riesgo", "figure"),
    Output("contexto-insights", "children"),
    Output("contexto-tabla", "children"),
    Input("contexto-campaña", "value"),
    Input("contexto-fecha-desde", "date"),
    Input("contexto-fecha-hasta", "date"),
)
def update_contexto(campaña, fecha_desde, fecha_hasta):
    data = api_get(
        "/api/contexto",
        params=filter_params(
            campaña=campaña,
            fecha_desde=fecha_desde,
            fecha_hasta=fecha_hasta,
        ),
    )

    kpis = data.get("kpis", {})
    evolucion_dolar = data.get("evolucion_dolar", [])
    lluvia_temperatura = data.get("lluvia_temperatura", [])
    precio_referencia = data.get("precio_referencia", [])
    tabla = data.get("tabla", [])
    insights = data.get("insights", [])

    row_1 = dbc.Row(
        [
            dbc.Col(kpi_card("Dólar de Referencia", fmt_num(kpis.get("dolar_actual", 0), 2), "ARS/USD", accent="primary", drill_panel="contexto", drill_item="dolar_actual"), width=4),
            dbc.Col(kpi_card("Lluvia Acumulada", fmt_num(kpis.get("lluvia_acumulada_mm", 0), 1), "mm", accent="blue", drill_panel="contexto", drill_item="lluvia_acumulada_mm"), width=4),
            dbc.Col(kpi_card("Precio Referencia", fmt_num(kpis.get("precio_referencia_actual", 0), 3), "USD/kg", accent="amber", drill_panel="contexto", drill_item="precio_referencia_actual"), width=4),
        ],
        className="g-3 mb-3",
    )

    row_2 = dbc.Row(
        [
            dbc.Col(kpi_card("Temperatura Mín.", fmt_num(kpis.get("temp_min_promedio", 0), 1), "°C", accent="green", drill_panel="contexto", drill_item="temp_min_promedio"), width=4),
            dbc.Col(kpi_card("Temperatura Máx.", fmt_num(kpis.get("temp_max_promedio", 0), 1), "°C", accent="red", drill_panel="contexto", drill_item="temp_max_promedio"), width=4),
            dbc.Col(kpi_card("Índice de Riesgo", fmt_num(kpis.get("indice_riesgo_promedio", 0), 2), "", accent="amber", drill_panel="contexto", drill_item="indice_riesgo_promedio"), width=4),
        ],
        className="g-3",
    )

    if evolucion_dolar:
        fig_dolar = go.Figure(
            go.Scatter(
                x=[item["fecha"] for item in evolucion_dolar],
                y=[item["dolar"] for item in evolucion_dolar],
                mode="lines+markers",
                line=dict(color="#4D755A", width=2.5),
                fill="tozeroy",
                fillcolor="rgba(77,117,90,0.12)",
            )
        )
    else:
        fig_dolar = empty_figure()
    fig_dolar.update_layout(**chart_layout(height=300))
    fig_dolar.update_layout(showlegend=False, yaxis_title="ARS/USD")

    if precio_referencia:
        fig_precio = go.Figure(
            go.Scatter(
                x=[item["fecha"] for item in precio_referencia],
                y=[item["precio_usd"] for item in precio_referencia],
                mode="lines+markers",
                line=dict(color="#B69245", width=2.5),
            )
        )
    else:
        fig_precio = empty_figure()
    fig_precio.update_layout(**chart_layout(height=300))
    fig_precio.update_layout(showlegend=False, yaxis_title="USD/kg")

    if lluvia_temperatura:
        fig_clima = go.Figure()
        fig_clima.add_trace(
            go.Bar(
                x=[item["fecha"] for item in lluvia_temperatura],
                y=[item["lluvia_mm"] for item in lluvia_temperatura],
                name="Lluvia",
                marker_color="#7AA6C2",
            )
        )
        fig_clima.add_trace(
            go.Scatter(
                x=[item["fecha"] for item in lluvia_temperatura],
                y=[item["temp_min"] for item in lluvia_temperatura],
                name="Temp. mín.",
                mode="lines",
                line=dict(color="#4D755A", width=2),
                yaxis="y2",
            )
        )
        fig_clima.add_trace(
            go.Scatter(
                x=[item["fecha"] for item in lluvia_temperatura],
                y=[item["temp_max"] for item in lluvia_temperatura],
                name="Temp. máx.",
                mode="lines",
                line=dict(color="#C26A45", width=2),
                yaxis="y2",
            )
        )
        fig_clima.update_layout(yaxis2=dict(overlaying="y", side="right", showgrid=False, title="°C"))
    else:
        fig_clima = empty_figure()
    fig_clima.update_layout(**chart_layout(height=320))
    fig_clima.update_layout(yaxis_title="mm")

    if tabla:
        fig_riesgo = go.Figure(
            go.Bar(
                x=[item["fecha"] for item in tabla],
                y=[item["indice_riesgo"] for item in tabla],
                marker_color=[
                    "#4D755A" if item["indice_riesgo"] < 2 else "#B69245" if item["indice_riesgo"] < 3.5 else "#C26A45"
                    for item in tabla
                ],
                text=[fmt_num(item["indice_riesgo"], 2) for item in tabla],
                textposition="outside",
            )
        )
    else:
        fig_riesgo = empty_figure()
    fig_riesgo.update_layout(**chart_layout(height=320))
    fig_riesgo.update_layout(showlegend=False, yaxis_title="Índice")

    if tabla:
        tabla_comp = render_table(
            tabla,
            [
                {"name": "Semana", "id": "fecha"},
                {"name": "Dólar", "id": "dolar", "type": "numeric"},
                {"name": "Lluvia mm", "id": "lluvia_mm", "type": "numeric"},
                {"name": "Temp. mín.", "id": "temp_min", "type": "numeric"},
                {"name": "Temp. máx.", "id": "temp_max", "type": "numeric"},
                {"name": "Precio Ref.", "id": "precio_ref_usd", "type": "numeric"},
                {"name": "Riesgo", "id": "indice_riesgo", "type": "numeric"},
            ],
            "contexto-tabla-dt",
        )
    else:
        tabla_comp = empty_state(message="No hay contexto externo para el período seleccionado.")

    return (
        row_1,
        row_2,
        fig_dolar,
        fig_precio,
        fig_clima,
        fig_riesgo,
        insights_panel("Insights de contexto", insights),
        tabla_comp,
    )
