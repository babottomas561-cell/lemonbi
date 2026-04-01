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
    api_get,
    build_options,
    chart_layout,
    empty_figure,
    fetch_options,
    filter_params,
    fmt_ars,
    insights_panel,
    panel_filter_options,
    sanitize_dropdown_value,
)

dash.register_page(__name__, path="/finanzas", name="Finanzas")


layout = html.Div(
    [
        render_header("Finanzas", "Caja, capital de trabajo y cobranza", "Valores en ARS"),
        dcc.Store(id={"type": "panel-filters", "panel": "finanzas"}, data={}),
        html.Div(
            [
                render_filter_bar(
                    [
                        dropdown_filter("CAMPAÑA", "finanzas-campaña", fetch_options("campanas", "campanas"), width="110px"),
                        date_filter("DESDE", "finanzas-fecha-desde", "2024-03-01"),
                        date_filter("HASTA", "finanzas-fecha-hasta", "2024-11-30"),
                        dropdown_filter("BANCO / CAJA", "finanzas-banco", fetch_options("bancos", "bancos"), width="170px"),
                        dropdown_filter("ESTADO", "finanzas-estado", fetch_options("estados_finanzas", "estados_finanzas"), width="150px"),
                        dropdown_filter("TIPO", "finanzas-tipo", build_options(["Ingreso", "Egreso"], all_label="Todos"), width="130px"),
                        dropdown_filter(
                            "FLUJO",
                            "finanzas-flujo",
                            build_options(["Operaciones", "Impuestos", "Financiamiento"], all_label="Todos"),
                            width="160px",
                        ),
                    ]
                ),
                html.Div(id="finanzas-kpi-row-1", className="kpi-row"),
                html.Div(id="finanzas-kpi-row-2", className="kpi-row"),
                dbc.Row(
                    [
                        dbc.Col(
                            drilldown_chart_card("Flujo de Caja Semanal", "finanzas-chart-flujo", "finanzas", "flujo_semanal"),
                            width=8,
                        ),
                        dbc.Col(
                            drilldown_chart_card("Evolución del Saldo", "finanzas-chart-saldo", "finanzas", "evolucion_saldo"),
                            width=4,
                        ),
                    ],
                    className="g-3",
                ),
                dbc.Row(
                    [
                        dbc.Col(
                            drilldown_chart_card("Cobros vs Pagos", "finanzas-chart-cobros", "finanzas", "cobros_vs_pagos"),
                            width=6,
                        ),
                        dbc.Col(
                            drilldown_chart_card("Aging de Cuentas", "finanzas-chart-aging", "finanzas", "aging"),
                            width=6,
                        ),
                    ],
                    className="g-3",
                ),
                html.Div(id="finanzas-insights"),
                html.Div(
                    [
                        html.Div("Detalle Financiero", className="table-header"),
                        loading_slot("finanzas-tabla"),
                    ],
                    className="table-card",
                ),
            ],
            id="page-content",
        ),
    ]
)


@callback(
    Output("finanzas-banco", "options"),
    Output("finanzas-estado", "options"),
    Output("finanzas-tipo", "options"),
    Output("finanzas-flujo", "options"),
    Input("finanzas-campaña", "value"),
    Input("finanzas-fecha-desde", "date"),
    Input("finanzas-fecha-hasta", "date"),
    Input("finanzas-banco", "value"),
    Input("finanzas-estado", "value"),
    Input("finanzas-tipo", "value"),
    Input("finanzas-flujo", "value"),
)
def update_finanzas_filter_options(campaña, fecha_desde, fecha_hasta, banco_caja, estado, tipo, categoria_flujo):
    options = panel_filter_options(
        "finanzas",
        campaña=campaña,
        fecha_desde=fecha_desde,
        fecha_hasta=fecha_hasta,
        banco_caja=banco_caja,
        estado=estado,
        tipo=tipo,
        categoria_flujo=categoria_flujo,
    )
    return (
        build_options(options.get("banco_caja", []), all_label="Todos"),
        build_options(options.get("estado", []), all_label="Todos"),
        build_options(options.get("tipo", []), all_label="Todos"),
        build_options(options.get("categoria_flujo", []), all_label="Todos"),
    )


@callback(
    Output({"type": "panel-filters", "panel": "finanzas"}, "data"),
    Input("finanzas-campaña", "value"),
    Input("finanzas-fecha-desde", "date"),
    Input("finanzas-fecha-hasta", "date"),
    Input("finanzas-banco", "value"),
    Input("finanzas-estado", "value"),
    Input("finanzas-tipo", "value"),
    Input("finanzas-flujo", "value"),
)
def sync_finanzas_filters_store(campaña, fecha_desde, fecha_hasta, banco_caja, estado, tipo, categoria_flujo):
    return filter_params(
        campaña=campaña,
        fecha_desde=fecha_desde,
        fecha_hasta=fecha_hasta,
        banco_caja=banco_caja,
        estado=estado,
        tipo=tipo,
        categoria_flujo=categoria_flujo,
    )


@callback(
    Output("finanzas-banco", "value"),
    Output("finanzas-estado", "value"),
    Output("finanzas-tipo", "value"),
    Output("finanzas-flujo", "value"),
    Input("finanzas-banco", "options"),
    Input("finanzas-estado", "options"),
    Input("finanzas-tipo", "options"),
    Input("finanzas-flujo", "options"),
    State("finanzas-banco", "value"),
    State("finanzas-estado", "value"),
    State("finanzas-tipo", "value"),
    State("finanzas-flujo", "value"),
)
def sync_finanzas_filter_values(banco_options, estado_options, tipo_options, flujo_options, banco, estado, tipo, flujo):
    return (
        sanitize_dropdown_value(banco, banco_options),
        sanitize_dropdown_value(estado, estado_options),
        sanitize_dropdown_value(tipo, tipo_options),
        sanitize_dropdown_value(flujo, flujo_options),
    )


@callback(
    Output("finanzas-kpi-row-1", "children"),
    Output("finanzas-kpi-row-2", "children"),
    Output("finanzas-chart-flujo", "figure"),
    Output("finanzas-chart-saldo", "figure"),
    Output("finanzas-chart-cobros", "figure"),
    Output("finanzas-chart-aging", "figure"),
    Output("finanzas-insights", "children"),
    Output("finanzas-tabla", "children"),
    Input("finanzas-campaña", "value"),
    Input("finanzas-fecha-desde", "date"),
    Input("finanzas-fecha-hasta", "date"),
    Input("finanzas-banco", "value"),
    Input("finanzas-estado", "value"),
    Input("finanzas-tipo", "value"),
    Input("finanzas-flujo", "value"),
)
def update_finanzas(campaña, fecha_desde, fecha_hasta, banco_caja, estado, tipo, categoria_flujo):
    data = api_get(
        "/api/finanzas",
        params=filter_params(
            campaña=campaña,
            fecha_desde=fecha_desde,
            fecha_hasta=fecha_hasta,
            banco_caja=banco_caja,
            estado=estado,
            tipo=tipo,
            categoria_flujo=categoria_flujo,
        ),
    )

    kpis = data.get("kpis", {})
    flujo_semanal = data.get("flujo_semanal", [])
    cobros_vs_pagos = data.get("cobros_vs_pagos", [])
    aging_cobrar = data.get("aging_cobrar", [])
    aging_pagar = data.get("aging_pagar", [])
    evolucion_saldo = data.get("evolucion_saldo", [])
    tabla = data.get("tabla", [])
    insights = data.get("insights", [])

    row_1 = dbc.Row(
        [
            dbc.Col(kpi_card("Saldo de Caja", fmt_ars(kpis.get("saldo_caja", 0)), accent="primary", drill_panel="finanzas", drill_item="saldo_caja"), width=3),
            dbc.Col(kpi_card("Ingresos Cobrados", fmt_ars(kpis.get("ingresos_cobrados", 0)), accent="green", drill_panel="finanzas", drill_item="ingresos_cobrados"), width=3),
            dbc.Col(kpi_card("Egresos Pagados", fmt_ars(kpis.get("egresos_pagados", 0)), accent="red", drill_panel="finanzas", drill_item="egresos_pagados"), width=3),
            dbc.Col(kpi_card("Flujo Neto", fmt_ars(kpis.get("flujo_neto", 0)), accent="amber", drill_panel="finanzas", drill_item="flujo_neto"), width=3),
        ],
        className="g-3 mb-3",
    )

    row_2 = dbc.Row(
        [
            dbc.Col(kpi_card("Cuentas a Cobrar", fmt_ars(kpis.get("cuentas_cobrar", 0)), accent="green", drill_panel="finanzas", drill_item="cuentas_cobrar"), width=3),
            dbc.Col(kpi_card("Cuentas a Pagar", fmt_ars(kpis.get("cuentas_pagar", 0)), accent="red", drill_panel="finanzas", drill_item="cuentas_pagar"), width=3),
            dbc.Col(kpi_card("Capital de Trabajo", fmt_ars(kpis.get("capital_trabajo", 0)), accent="blue", drill_panel="finanzas", drill_item="capital_trabajo"), width=3),
            dbc.Col(kpi_card("Necesidad de Financiamiento", fmt_ars(kpis.get("necesidad_financiamiento", 0)), accent="amber", drill_panel="finanzas", drill_item="necesidad_financiamiento"), width=3),
        ],
        className="g-3",
    )

    if flujo_semanal:
        fig_flujo = go.Figure()
        fig_flujo.add_trace(
            go.Bar(
                x=[item["semana"] for item in flujo_semanal],
                y=[item["ingresos"] for item in flujo_semanal],
                name="Ingresos",
                marker_color="#6C8C5A",
            )
        )
        fig_flujo.add_trace(
            go.Bar(
                x=[item["semana"] for item in flujo_semanal],
                y=[item["egresos"] for item in flujo_semanal],
                name="Egresos",
                marker_color="#C26A45",
            )
        )
        fig_flujo.add_trace(
            go.Scatter(
                x=[item["semana"] for item in flujo_semanal],
                y=[item["saldo_acumulado"] for item in flujo_semanal],
                name="Saldo acumulado",
                mode="lines+markers",
                line=dict(color="#243126", width=2.5),
                yaxis="y2",
            )
        )
        fig_flujo.update_layout(barmode="group", yaxis2=dict(overlaying="y", side="right", showgrid=False))
    else:
        fig_flujo = empty_figure()
    fig_flujo.update_layout(**chart_layout(height=330))
    fig_flujo.update_layout(yaxis_title="ARS")

    if evolucion_saldo:
        fig_saldo = go.Figure(
            go.Scatter(
                x=[item["fecha"] for item in evolucion_saldo],
                y=[item["saldo"] for item in evolucion_saldo],
                mode="lines",
                fill="tozeroy",
                line=dict(color="#4D755A", width=2.5),
                fillcolor="rgba(77,117,90,0.12)",
            )
        )
    else:
        fig_saldo = empty_figure()
    fig_saldo.update_layout(**chart_layout(height=330))
    fig_saldo.update_layout(showlegend=False, yaxis_title="ARS")

    if cobros_vs_pagos:
        fig_cobros = go.Figure()
        fig_cobros.add_trace(
            go.Bar(
                x=[item["mes"] for item in cobros_vs_pagos],
                y=[item["cobros"] for item in cobros_vs_pagos],
                name="Cobros",
                marker_color="#95B29E",
            )
        )
        fig_cobros.add_trace(
            go.Bar(
                x=[item["mes"] for item in cobros_vs_pagos],
                y=[item["pagos"] for item in cobros_vs_pagos],
                name="Pagos",
                marker_color="#B05D3B",
            )
        )
        fig_cobros.update_layout(barmode="group")
    else:
        fig_cobros = empty_figure()
    fig_cobros.update_layout(**chart_layout(height=300))
    fig_cobros.update_layout(yaxis_title="ARS")

    if aging_cobrar or aging_pagar:
        labels = [item["rango"] for item in aging_cobrar] or [item["rango"] for item in aging_pagar]
        fig_aging = go.Figure()
        fig_aging.add_trace(
            go.Bar(
                x=labels,
                y=[item["importe"] for item in aging_cobrar],
                name="A cobrar",
                marker_color="#6C8C5A",
            )
        )
        fig_aging.add_trace(
            go.Bar(
                x=labels,
                y=[item["importe"] for item in aging_pagar],
                name="A pagar",
                marker_color="#C26A45",
            )
        )
        fig_aging.update_layout(barmode="group")
    else:
        fig_aging = empty_figure()
    fig_aging.update_layout(**chart_layout(height=300))
    fig_aging.update_layout(yaxis_title="ARS")

    if tabla:
        tabla_comp = render_table(
            tabla,
            [
                {"name": "Fecha", "id": "fecha"},
                {"name": "Concepto", "id": "concepto"},
                {"name": "Tipo", "id": "tipo"},
                {"name": "Cliente / Proveedor", "id": "cliente_proveedor"},
                {"name": "Importe", "id": "importe", "type": "numeric"},
                {"name": "Vencimiento", "id": "vencimiento"},
                {"name": "Estado", "id": "estado"},
                {"name": "Moneda", "id": "moneda"},
            ],
            "finanzas-tabla-dt",
        )
    else:
        tabla_comp = empty_state(message="No hay movimientos financieros para la selección actual.")

    return (
        row_1,
        row_2,
        fig_flujo,
        fig_saldo,
        fig_cobros,
        fig_aging,
        insights_panel("Insights financieros", insights),
        tabla_comp,
    )
