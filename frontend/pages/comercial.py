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

dash.register_page(__name__, path="/comercial", name="Comercial")


layout = html.Div(
    [
        render_header("Comercial", "Ventas, clientes, precios y canales", "Panel conectado al backend"),
        dcc.Store(id={"type": "panel-filters", "panel": "comercial"}, data={}),
        html.Div(
            [
                render_filter_bar(
                    [
                        dropdown_filter("CAMPAÑA", "comercial-campaña", fetch_options("campanas", "campanas"), width="110px"),
                        date_filter("DESDE", "comercial-fecha-desde", "2024-03-01"),
                        date_filter("HASTA", "comercial-fecha-hasta", "2024-11-30"),
                        dropdown_filter("CLIENTE", "comercial-cliente", fetch_options("clientes", "clientes"), width="190px"),
                        dropdown_filter("DESTINO", "comercial-destino", fetch_options("destinos", "destinos"), width="160px"),
                        dropdown_filter("CANAL", "comercial-canal", fetch_options("canales", "canales"), width="190px"),
                        dropdown_filter("MONEDA", "comercial-moneda", fetch_options("monedas_comercial", "monedas_comercial"), width="120px"),
                    ]
                ),
                html.Div(id="comercial-kpi-row-1", className="kpi-row"),
                html.Div(id="comercial-kpi-row-2", className="kpi-row"),
                dbc.Row(
                    [
                        dbc.Col(
                            drilldown_chart_card("Ventas por Cliente", "comercial-chart-clientes", "comercial", "ventas_por_cliente"),
                            width=7,
                        ),
                        dbc.Col(
                            drilldown_chart_card("Mix por Destino", "comercial-chart-destino", "comercial", "ventas_por_destino"),
                            width=5,
                        ),
                    ],
                    className="g-3",
                ),
                dbc.Row(
                    [
                        dbc.Col(
                            drilldown_chart_card("Precio Promedio por Calibre", "comercial-chart-calibre", "comercial", "precio_por_calibre"),
                            width=4,
                        ),
                        dbc.Col(
                            drilldown_chart_card("Margen por Canal", "comercial-chart-canal", "comercial", "margen_por_canal"),
                            width=4,
                        ),
                        dbc.Col(
                            drilldown_chart_card("Top Clientes", "comercial-chart-top", "comercial", "top_clientes"),
                            width=4,
                        ),
                    ],
                    className="g-3",
                ),
                dbc.Row(
                    [
                        dbc.Col(
                            drilldown_chart_card("Evolución de Ventas", "comercial-chart-evolucion", "comercial", "evolucion_ventas"),
                            width=12,
                        )
                    ],
                    className="g-3",
                ),
                html.Div(id="comercial-insights"),
                html.Div(
                    [
                        html.Div("Detalle Comercial", className="table-header"),
                        loading_slot("comercial-tabla"),
                    ],
                    className="table-card",
                ),
            ],
            id="page-content",
        ),
    ]
)


@callback(
    Output("comercial-cliente", "options"),
    Output("comercial-destino", "options"),
    Output("comercial-canal", "options"),
    Output("comercial-moneda", "options"),
    Input("comercial-campaña", "value"),
    Input("comercial-fecha-desde", "date"),
    Input("comercial-fecha-hasta", "date"),
    Input("comercial-cliente", "value"),
    Input("comercial-destino", "value"),
    Input("comercial-canal", "value"),
    Input("comercial-moneda", "value"),
)
def update_comercial_filter_options(campaña, fecha_desde, fecha_hasta, cliente, destino, canal, moneda):
    options = panel_filter_options(
        "comercial",
        campaña=campaña,
        fecha_desde=fecha_desde,
        fecha_hasta=fecha_hasta,
        cliente=cliente,
        destino=destino,
        canal=canal,
        moneda=moneda,
    )
    return (
        build_options(options.get("cliente", []), all_label="Todos"),
        build_options(options.get("destino", []), all_label="Todos"),
        build_options(options.get("canal", []), all_label="Todos"),
        build_options(options.get("moneda", []), all_label="Todas"),
    )


@callback(
    Output({"type": "panel-filters", "panel": "comercial"}, "data"),
    Input("comercial-campaña", "value"),
    Input("comercial-fecha-desde", "date"),
    Input("comercial-fecha-hasta", "date"),
    Input("comercial-cliente", "value"),
    Input("comercial-destino", "value"),
    Input("comercial-canal", "value"),
    Input("comercial-moneda", "value"),
)
def sync_comercial_filters_store(campaña, fecha_desde, fecha_hasta, cliente, destino, canal, moneda):
    return filter_params(
        campaña=campaña,
        fecha_desde=fecha_desde,
        fecha_hasta=fecha_hasta,
        cliente=cliente,
        destino=destino,
        canal=canal,
        moneda=moneda,
    )


@callback(
    Output("comercial-cliente", "value"),
    Output("comercial-destino", "value"),
    Output("comercial-canal", "value"),
    Output("comercial-moneda", "value"),
    Input("comercial-cliente", "options"),
    Input("comercial-destino", "options"),
    Input("comercial-canal", "options"),
    Input("comercial-moneda", "options"),
    State("comercial-cliente", "value"),
    State("comercial-destino", "value"),
    State("comercial-canal", "value"),
    State("comercial-moneda", "value"),
)
def sync_comercial_filter_values(cliente_options, destino_options, canal_options, moneda_options, cliente, destino, canal, moneda):
    return (
        sanitize_dropdown_value(cliente, cliente_options),
        sanitize_dropdown_value(destino, destino_options),
        sanitize_dropdown_value(canal, canal_options),
        sanitize_dropdown_value(moneda, moneda_options),
    )


@callback(
    Output("comercial-kpi-row-1", "children"),
    Output("comercial-kpi-row-2", "children"),
    Output("comercial-chart-clientes", "figure"),
    Output("comercial-chart-destino", "figure"),
    Output("comercial-chart-calibre", "figure"),
    Output("comercial-chart-canal", "figure"),
    Output("comercial-chart-top", "figure"),
    Output("comercial-chart-evolucion", "figure"),
    Output("comercial-insights", "children"),
    Output("comercial-tabla", "children"),
    Input("comercial-campaña", "value"),
    Input("comercial-fecha-desde", "date"),
    Input("comercial-fecha-hasta", "date"),
    Input("comercial-cliente", "value"),
    Input("comercial-destino", "value"),
    Input("comercial-canal", "value"),
    Input("comercial-moneda", "value"),
)
def update_comercial(campaña, fecha_desde, fecha_hasta, cliente, destino, canal, moneda):
    data = api_get(
        "/api/comercial",
        params=filter_params(
            campaña=campaña,
            fecha_desde=fecha_desde,
            fecha_hasta=fecha_hasta,
            cliente=cliente,
            destino=destino,
            canal=canal,
            moneda=moneda,
        ),
    )

    kpis = data.get("kpis", {})
    ventas_por_cliente = data.get("ventas_por_cliente", [])
    ventas_por_destino = data.get("ventas_por_destino", [])
    precio_por_calibre = data.get("precio_por_calibre", [])
    evolucion = data.get("evolucion_ventas", [])
    top_clientes = data.get("top_clientes", [])
    margen_por_canal = data.get("margen_por_canal", [])
    tabla = data.get("tabla", [])
    insights = data.get("insights", [])

    row_1 = dbc.Row(
        [
            dbc.Col(kpi_card("Ventas Netas", fmt_usd(kpis.get("ventas_netas_usd", 0)), accent="primary", drill_panel="comercial", drill_item="ventas_netas_usd"), width=3),
            dbc.Col(kpi_card("Kg Vendidos", f"{kpis.get('kg_vendidos', 0):,.0f}", "kg", accent="green", drill_panel="comercial", drill_item="kg_vendidos"), width=3),
            dbc.Col(kpi_card("Precio Promedio", fmt_num(kpis.get("precio_promedio_kg_usd", 0), 3), "USD/kg", accent="amber", drill_panel="comercial", drill_item="precio_promedio_kg_usd"), width=3),
            dbc.Col(kpi_card("Margen Comercial", fmt_num(kpis.get("margen_comercial_pct", 0), 1), "%", accent="green", drill_panel="comercial", drill_item="margen_comercial_pct"), width=3),
        ],
        className="g-3 mb-3",
    )

    row_2 = dbc.Row(
        [
            dbc.Col(kpi_card("Exportación", fmt_num(kpis.get("pct_exportacion", 0), 1), "%", accent="primary", drill_panel="comercial", drill_item="pct_exportacion"), width=3),
            dbc.Col(kpi_card("Mercado Interno", fmt_num(kpis.get("pct_mercado_interno", 0), 1), "%", accent="blue", drill_panel="comercial", drill_item="pct_mercado_interno"), width=3),
            dbc.Col(kpi_card("Industria", fmt_num(kpis.get("pct_industria", 0), 1), "%", accent="red", drill_panel="comercial", drill_item="pct_industria"), width=3),
            dbc.Col(kpi_card("Ticket Promedio", fmt_usd(kpis.get("ticket_promedio_usd", 0)), accent="amber", drill_panel="comercial", drill_item="ticket_promedio_usd"), width=3),
        ],
        className="g-3",
    )

    if ventas_por_cliente:
        top = ventas_por_cliente[:10]
        fig_clientes = go.Figure(
            go.Bar(
                y=[item["cliente"] for item in top],
                x=[item["importe_usd"] for item in top],
                orientation="h",
                marker_color="#4D755A",
                text=[fmt_usd(item["importe_usd"]) for item in top],
                textposition="outside",
            )
        )
    else:
        fig_clientes = empty_figure()
    fig_clientes.update_layout(**chart_layout(height=330))
    fig_clientes.update_layout(margin=dict(l=180, r=30, t=30, b=30), showlegend=False, xaxis_title="USD")

    if ventas_por_destino:
        fig_destino = go.Figure(
            go.Pie(
                labels=[item["destino"] for item in ventas_por_destino],
                values=[item["importe_usd"] for item in ventas_por_destino],
                hole=0.55,
                marker=dict(colors=CHART_COLORS[: len(ventas_por_destino)]),
                textinfo="label+percent",
            )
        )
        fig_destino.update_layout(height=330, margin=dict(l=10, r=10, t=20, b=10), paper_bgcolor="#FFFCF7")
    else:
        fig_destino = empty_figure()

    if precio_por_calibre:
        fig_calibre = go.Figure(
            go.Bar(
                x=[item["calibre"] for item in precio_por_calibre],
                y=[item["precio_promedio_usd"] for item in precio_por_calibre],
                marker_color="#B69245",
                text=[fmt_num(item["precio_promedio_usd"], 3) for item in precio_por_calibre],
                textposition="outside",
            )
        )
    else:
        fig_calibre = empty_figure()
    fig_calibre.update_layout(**chart_layout(height=290))
    fig_calibre.update_layout(showlegend=False, yaxis_title="USD/kg")

    if margen_por_canal:
        fig_canal = go.Figure(
            go.Bar(
                x=[item["canal"] for item in margen_por_canal],
                y=[item["margen_pct"] for item in margen_por_canal],
                marker_color=["#4D755A" if item["margen_pct"] >= 20 else "#B69245" for item in margen_por_canal],
                text=[f"{item['margen_pct']:.1f}%" for item in margen_por_canal],
                textposition="outside",
            )
        )
    else:
        fig_canal = empty_figure()
    fig_canal.update_layout(**chart_layout(height=290))
    fig_canal.update_layout(showlegend=False, yaxis_title="%")

    if top_clientes:
        fig_top = go.Figure(
            go.Scatter(
                x=[item["importe_usd"] for item in top_clientes],
                y=[item["margen_pct"] for item in top_clientes],
                mode="markers+text",
                text=[item["cliente"] for item in top_clientes],
                textposition="top center",
                marker=dict(
                    size=[max(10, min(28, item["importe_usd"] / 18_000)) for item in top_clientes],
                    color="#6C8C5A",
                    opacity=0.85,
                ),
            )
        )
    else:
        fig_top = empty_figure()
    fig_top.update_layout(**chart_layout(height=290))
    fig_top.update_layout(showlegend=False, xaxis_title="USD", yaxis_title="Margen %")

    if evolucion:
        fig_evolucion = go.Figure()
        fig_evolucion.add_trace(
            go.Bar(
                x=[item["mes"] for item in evolucion],
                y=[item["importe_usd"] for item in evolucion],
                name="Ventas USD",
                marker_color="#95B29E",
            )
        )
        fig_evolucion.add_trace(
            go.Scatter(
                x=[item["mes"] for item in evolucion],
                y=[item["kg"] for item in evolucion],
                name="Kg vendidos",
                mode="lines+markers",
                line=dict(color="#B05D3B", width=2.5),
                yaxis="y2",
            )
        )
        fig_evolucion.update_layout(yaxis2=dict(overlaying="y", side="right", title="Kg", showgrid=False))
    else:
        fig_evolucion = empty_figure()
    fig_evolucion.update_layout(**chart_layout(height=320))
    fig_evolucion.update_layout(yaxis_title="USD")

    if tabla:
        tabla_comp = render_table(
            tabla,
            [
                {"name": "Cliente", "id": "cliente"},
                {"name": "Destino", "id": "destino"},
                {"name": "Kg Vendidos", "id": "kg_vendidos", "type": "numeric"},
                {"name": "Precio Promedio", "id": "precio_promedio", "type": "numeric"},
                {"name": "Importe USD", "id": "importe_usd", "type": "numeric"},
                {"name": "Margen %", "id": "margen_pct", "type": "numeric"},
                {"name": "Estado Cobro", "id": "estado_cobro"},
            ],
            "comercial-tabla-dt",
        )
    else:
        tabla_comp = empty_state(message="No hay operaciones comerciales para los filtros seleccionados.")

    return (
        row_1,
        row_2,
        fig_clientes,
        fig_destino,
        fig_calibre,
        fig_canal,
        fig_top,
        fig_evolucion,
        insights_panel("Insights comerciales", insights),
        tabla_comp,
    )
