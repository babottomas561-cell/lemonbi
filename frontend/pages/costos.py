import dash
import dash_bootstrap_components as dbc
import plotly.graph_objects as go
from dash import Input, Output, State, callback, dcc, html

from frontend.components.empty_state import empty_state
from frontend.components.drilldown import drilldown_chart_card
from frontend.components.filter_bar import date_filter, dropdown_filter, render_filter_bar
from frontend.components.header import render_header
from frontend.components.kpi_card import kpi_card
from frontend.components.loading import loading_graph, loading_slot
from frontend.components.tables import render_table
from frontend.utils import (
    CHART_COLORS,
    api_get,
    build_options,
    chart_layout,
    empty_figure,
    fetch_options,
    filter_params,
    fmt_num,
    fmt_usd,
    insights_panel,
    panel_filter_options,
    sanitize_dropdown_value,
)

dash.register_page(__name__, path="/costos", name="Costos y Rentabilidad")


layout = html.Div(
    [
        render_header("Costos y Rentabilidad", "Costo por kilo, lote, finca y canal", "Módulo de rentabilidad"),
        dcc.Store(id={"type": "panel-filters", "panel": "costos"}, data={}),
        html.Div(
            [
                render_filter_bar(
                    [
                        dropdown_filter("CAMPAÑA", "costos-campaña", fetch_options("campanas", "campanas"), width="110px"),
                        date_filter("DESDE", "costos-fecha-desde", "2024-03-01"),
                        date_filter("HASTA", "costos-fecha-hasta", "2024-11-30"),
                        dropdown_filter("FINCA", "costos-finca", fetch_options("fincas", "fincas"), width="170px"),
                        dropdown_filter("LOTE", "costos-lote", fetch_options("lotes", "lotes"), width="130px"),
                        dropdown_filter("CENTRO", "costos-centro", fetch_options("centros_costo", "centros_costo"), width="160px"),
                        dropdown_filter("TIPO", "costos-tipo", fetch_options("tipos_costo", "tipos_costo"), width="180px"),
                        dropdown_filter("CANAL", "costos-canal", fetch_options("canales", "canales"), width="190px"),
                    ]
                ),
                html.Div(id="costos-kpi-row-1", className="kpi-row"),
                html.Div(id="costos-kpi-row-2", className="kpi-row"),
                dbc.Row(
                    [
                        dbc.Col(
                            drilldown_chart_card("Composición del Costo", "costos-chart-composicion", "costos", "composicion_costo"),
                            width=4,
                        ),
                        dbc.Col(
                            drilldown_chart_card("Costo por Finca", "costos-chart-finca", "costos", "costo_por_finca"),
                            width=4,
                        ),
                        dbc.Col(
                            drilldown_chart_card("Costo por Canal", "costos-chart-canal", "costos", "costo_por_canal"),
                            width=4,
                        ),
                    ],
                    className="g-3",
                ),
                dbc.Row(
                    [
                        dbc.Col(
                            drilldown_chart_card("Costo por Lote", "costos-chart-lote", "costos", "costo_por_lote"),
                            width=6,
                        ),
                        dbc.Col(
                            drilldown_chart_card("Margen por Cliente", "costos-chart-cliente", "costos", "margen_por_cliente"),
                            width=6,
                        ),
                    ],
                    className="g-3",
                ),
                dbc.Row(
                    [
                        dbc.Col(
                            drilldown_chart_card("Margen por Destino", "costos-chart-destino", "costos", "margen_por_destino"),
                            width=12,
                        )
                    ],
                    className="g-3",
                ),
                html.Div(id="costos-insights"),
                html.Div(
                    [
                        html.Div("Detalle de Rentabilidad", className="table-header"),
                        loading_slot("costos-tabla"),
                    ],
                    className="table-card",
                ),
            ],
            id="page-content",
        ),
    ]
)


@callback(
    Output("costos-finca", "options"),
    Output("costos-lote", "options"),
    Output("costos-centro", "options"),
    Output("costos-tipo", "options"),
    Output("costos-canal", "options"),
    Input("costos-campaña", "value"),
    Input("costos-fecha-desde", "date"),
    Input("costos-fecha-hasta", "date"),
    Input("costos-finca", "value"),
    Input("costos-lote", "value"),
    Input("costos-centro", "value"),
    Input("costos-tipo", "value"),
    Input("costos-canal", "value"),
)
def update_costos_filter_options(campaña, fecha_desde, fecha_hasta, finca, lote, centro_costo, tipo_costo, canal):
    options = panel_filter_options(
        "costos",
        campaña=campaña,
        fecha_desde=fecha_desde,
        fecha_hasta=fecha_hasta,
        finca=finca,
        lote=lote,
        centro_costo=centro_costo,
        tipo_costo=tipo_costo,
        canal=canal,
    )
    return (
        build_options(options.get("finca", []), all_label="Todas"),
        build_options(options.get("lote", []), all_label="Todos"),
        build_options(options.get("centro_costo", []), all_label="Todos"),
        build_options(options.get("tipo_costo", []), all_label="Todos"),
        build_options(options.get("canal", []), all_label="Todos"),
    )


@callback(
    Output({"type": "panel-filters", "panel": "costos"}, "data"),
    Input("costos-campaña", "value"),
    Input("costos-fecha-desde", "date"),
    Input("costos-fecha-hasta", "date"),
    Input("costos-finca", "value"),
    Input("costos-lote", "value"),
    Input("costos-centro", "value"),
    Input("costos-tipo", "value"),
    Input("costos-canal", "value"),
)
def sync_costos_filters_store(campaña, fecha_desde, fecha_hasta, finca, lote, centro_costo, tipo_costo, canal):
    return filter_params(
        campaña=campaña,
        fecha_desde=fecha_desde,
        fecha_hasta=fecha_hasta,
        finca=finca,
        lote=lote,
        centro_costo=centro_costo,
        tipo_costo=tipo_costo,
        canal=canal,
    )


@callback(
    Output("costos-finca", "value"),
    Output("costos-lote", "value"),
    Output("costos-centro", "value"),
    Output("costos-tipo", "value"),
    Output("costos-canal", "value"),
    Input("costos-finca", "options"),
    Input("costos-lote", "options"),
    Input("costos-centro", "options"),
    Input("costos-tipo", "options"),
    Input("costos-canal", "options"),
    State("costos-finca", "value"),
    State("costos-lote", "value"),
    State("costos-centro", "value"),
    State("costos-tipo", "value"),
    State("costos-canal", "value"),
)
def sync_costos_filter_values(finca_options, lote_options, centro_options, tipo_options, canal_options, finca, lote, centro, tipo, canal):
    return (
        sanitize_dropdown_value(finca, finca_options),
        sanitize_dropdown_value(lote, lote_options),
        sanitize_dropdown_value(centro, centro_options),
        sanitize_dropdown_value(tipo, tipo_options),
        sanitize_dropdown_value(canal, canal_options),
    )


@callback(
    Output("costos-kpi-row-1", "children"),
    Output("costos-kpi-row-2", "children"),
    Output("costos-chart-composicion", "figure"),
    Output("costos-chart-finca", "figure"),
    Output("costos-chart-canal", "figure"),
    Output("costos-chart-lote", "figure"),
    Output("costos-chart-cliente", "figure"),
    Output("costos-chart-destino", "figure"),
    Output("costos-insights", "children"),
    Output("costos-tabla", "children"),
    Input("costos-campaña", "value"),
    Input("costos-fecha-desde", "date"),
    Input("costos-fecha-hasta", "date"),
    Input("costos-finca", "value"),
    Input("costos-lote", "value"),
    Input("costos-centro", "value"),
    Input("costos-tipo", "value"),
    Input("costos-canal", "value"),
)
def update_costos(campaña, fecha_desde, fecha_hasta, finca, lote, centro_costo, tipo_costo, canal):
    data = api_get(
        "/api/costos",
        params=filter_params(
            campaña=campaña,
            fecha_desde=fecha_desde,
            fecha_hasta=fecha_hasta,
            finca=finca,
            lote=lote,
            centro_costo=centro_costo,
            tipo_costo=tipo_costo,
            canal=canal,
        ),
    )

    kpis = data.get("kpis", {})
    composicion = data.get("composicion_costo", [])
    costo_por_finca = data.get("costo_por_finca", [])
    costo_por_lote = data.get("costo_por_lote", [])
    costo_por_canal = data.get("costo_por_canal", [])
    margen_por_cliente = data.get("margen_por_cliente", [])
    margen_por_destino = data.get("margen_por_destino", [])
    tabla = data.get("tabla", [])
    insights = data.get("insights", [])

    row_1 = dbc.Row(
        [
            dbc.Col(kpi_card("Costo Fruta", fmt_num(kpis.get("costo_fruta_kg", 0), 1), "ARS/kg", accent="green", drill_panel="costos", drill_item="costo_fruta_kg"), width=3),
            dbc.Col(kpi_card("Costo Empaque", fmt_num(kpis.get("costo_empaque_kg", 0), 1), "ARS/kg", accent="blue", drill_panel="costos", drill_item="costo_empaque_kg"), width=3),
            dbc.Col(kpi_card("Costo Logístico", fmt_num(kpis.get("costo_logistica_kg", 0), 1), "ARS/kg", accent="amber", drill_panel="costos", drill_item="costo_logistica_kg"), width=3),
            dbc.Col(kpi_card("Costo Total Exportado", fmt_num(kpis.get("costo_total_kg_exportado", 0), 1), "ARS/kg", accent="red", drill_panel="costos", drill_item="costo_total_kg_exportado"), width=3),
        ],
        className="g-3 mb-3",
    )

    row_2 = dbc.Row(
        [
            dbc.Col(kpi_card("Margen Bruto", fmt_usd(kpis.get("margen_bruto_usd", 0)), accent="primary", drill_panel="costos", drill_item="margen_bruto_usd"), width=3),
            dbc.Col(kpi_card("Margen Bruto %", fmt_num(kpis.get("margen_bruto_pct", 0), 1), "%", accent="green", drill_panel="costos", drill_item="margen_bruto_pct"), width=3),
            dbc.Col(kpi_card("Mejor Lote", kpis.get("mejor_lote", "-"), accent="amber", drill_panel="costos", drill_item="mejor_lote"), width=3),
            dbc.Col(kpi_card("Mejor Canal", kpis.get("mejor_canal", "-"), accent="blue", drill_panel="costos", drill_item="mejor_canal"), width=3),
        ],
        className="g-3",
    )

    if composicion:
        fig_composicion = go.Figure(
            go.Pie(
                labels=[item["tipo"] for item in composicion],
                values=[item["importe"] for item in composicion],
                hole=0.52,
                marker=dict(colors=CHART_COLORS[: len(composicion)]),
                textinfo="label+percent",
            )
        )
        fig_composicion.update_layout(height=310, margin=dict(l=10, r=10, t=15, b=10), paper_bgcolor="#FFFCF7")
    else:
        fig_composicion = empty_figure()

    if costo_por_finca:
        fig_finca = go.Figure(
            go.Bar(
                x=[item["finca"] for item in costo_por_finca],
                y=[item["costo_kg"] for item in costo_por_finca],
                marker_color="#6C8C5A",
                text=[fmt_num(item["costo_kg"], 1) for item in costo_por_finca],
                textposition="outside",
            )
        )
    else:
        fig_finca = empty_figure()
    fig_finca.update_layout(**chart_layout(height=310))
    fig_finca.update_layout(showlegend=False, yaxis_title="ARS/kg")

    if costo_por_canal:
        fig_canal = go.Figure(
            go.Bar(
                x=[item["canal"] for item in costo_por_canal],
                y=[item["margen_pct"] for item in costo_por_canal],
                marker_color=["#4D755A" if item["margen_pct"] >= 15 else "#C26A45" for item in costo_por_canal],
                text=[f"{item['margen_pct']:.1f}%" for item in costo_por_canal],
                textposition="outside",
            )
        )
    else:
        fig_canal = empty_figure()
    fig_canal.update_layout(**chart_layout(height=310))
    fig_canal.update_layout(showlegend=False, yaxis_title="%")

    if costo_por_lote:
        top = costo_por_lote[:12]
        fig_lote = go.Figure(
            go.Bar(
                y=[f"{item['lote']} ({item['finca']})" for item in top],
                x=[item["costo_kg"] for item in top],
                orientation="h",
                marker_color="#B69245",
                text=[fmt_num(item["costo_kg"], 1) for item in top],
                textposition="outside",
            )
        )
    else:
        fig_lote = empty_figure()
    fig_lote.update_layout(**chart_layout(height=330))
    fig_lote.update_layout(showlegend=False, margin=dict(l=170, r=25, t=25, b=30), xaxis_title="ARS/kg")

    if margen_por_cliente:
        top_clientes = margen_por_cliente[:10]
        fig_cliente = go.Figure(
            go.Bar(
                x=[item["cliente"] for item in top_clientes],
                y=[item["margen_pct"] for item in top_clientes],
                marker_color="#95B29E",
                text=[f"{item['margen_pct']:.1f}%" for item in top_clientes],
                textposition="outside",
            )
        )
    else:
        fig_cliente = empty_figure()
    fig_cliente.update_layout(**chart_layout(height=330))
    fig_cliente.update_layout(showlegend=False, yaxis_title="%")

    if margen_por_destino:
        fig_destino = go.Figure(
            go.Bar(
                x=[item["destino"] for item in margen_por_destino],
                y=[item["margen_pct"] for item in margen_por_destino],
                marker_color=CHART_COLORS[: len(margen_por_destino)],
                text=[f"{item['margen_pct']:.1f}%" for item in margen_por_destino],
                textposition="outside",
            )
        )
    else:
        fig_destino = empty_figure()
    fig_destino.update_layout(**chart_layout(height=300))
    fig_destino.update_layout(showlegend=False, yaxis_title="%")

    if tabla:
        tabla_comp = render_table(
            tabla,
            [
                {"name": "Finca", "id": "finca"},
                {"name": "Lote", "id": "lote"},
                {"name": "Costo Campo", "id": "costo_campo", "type": "numeric"},
                {"name": "Costo Empaque", "id": "costo_empaque", "type": "numeric"},
                {"name": "Costo Logística", "id": "costo_logistica", "type": "numeric"},
                {"name": "Costo Total", "id": "costo_total", "type": "numeric"},
                {"name": "Ingreso USD", "id": "ingreso_usd", "type": "numeric"},
                {"name": "Margen USD", "id": "margen", "type": "numeric"},
                {"name": "Margen %", "id": "margen_pct", "type": "numeric"},
            ],
            "costos-tabla-dt",
        )
    else:
        tabla_comp = empty_state(message="No hay datos de costos para los filtros activos.")

    return (
        row_1,
        row_2,
        fig_composicion,
        fig_finca,
        fig_canal,
        fig_lote,
        fig_cliente,
        fig_destino,
        insights_panel("Insights de costos y rentabilidad", insights),
        tabla_comp,
    )
