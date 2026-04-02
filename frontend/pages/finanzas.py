import dash
import dash_bootstrap_components as dbc
import plotly.graph_objects as go
from dash import Input, Output, State, callback, dcc, html

from frontend.components.empty_state import empty_state
from frontend.components.drilldown import drilldown_chart_card
from frontend.components.filter_bar import bind_date_shortcuts, campaign_filter, date_range_filter, dropdown_filter, render_filter_bar
from frontend.components.header import render_header
from frontend.components.kpi_card import kpi_card
from frontend.components.loading import loading_slot
from frontend.components.tables import render_table
from frontend.utils import (
    CHART_COLORS,
    add_metric_badge,
    add_peak_annotation,
    add_reference_line,
    api_get,
    best_index,
    build_options,
    chart_layout,
    compact_number,
    empty_figure,
    fetch_options,
    filter_params,
    format_month_label,
    format_week_label,
    fmt_ars,
    insights_panel,
    page_empty_outputs,
    page_failure_outputs,
    panel_filter_options,
    safe_callback,
    sanitize_dropdown_value,
    smart_bar_colors,
)

dash.register_page(__name__, path="/finanzas", name="Finanzas")
bind_date_shortcuts("finanzas")


layout = html.Div(
    [
        render_header("Finanzas", "Caja, capital de trabajo y cobranza", "Valores en ARS"),
        dcc.Store(id={"type": "panel-filters", "panel": "finanzas"}, data={}),
        html.Div(
            [
                render_filter_bar(
                    [
                        campaign_filter("finanzas-campaña", width="110px"),
                        date_range_filter("finanzas", "2024-03-01", "2024-11-30"),
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
                            drilldown_chart_card(
                                "Flujo neto semanal y saldo acumulado",
                                "finanzas-chart-flujo",
                                "finanzas",
                                "flujo_semanal",
                                subtitle="Ingresos y egresos del período con lectura inmediata de presión de caja",
                                priority="primary",
                            ),
                            width=8,
                        ),
                        dbc.Col(
                            drilldown_chart_card(
                                "Evolución del saldo de caja",
                                "finanzas-chart-saldo",
                                "finanzas",
                                "evolucion_saldo",
                                subtitle="Trayectoria del saldo disponible a lo largo de la campaña",
                            ),
                            width=4,
                        ),
                    ],
                    className="g-3",
                ),
                dbc.Row(
                    [
                        dbc.Col(
                            drilldown_chart_card(
                                "Cobros vs pagos mensuales",
                                "finanzas-chart-cobros",
                                "finanzas",
                                "cobros_vs_pagos",
                                subtitle="Comparación de caja operativa para anticipar brechas de liquidez",
                            ),
                            width=6,
                        ),
                        dbc.Col(
                            drilldown_chart_card(
                                "Aging de cuentas",
                                "finanzas-chart-aging",
                                "finanzas",
                                "aging",
                                subtitle="Distribución de deuda y cobranza según vencimiento",
                            ),
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
    Output("finanzas-campaña", "options"),
    Output("finanzas-banco", "options"),
    Output("finanzas-estado", "options"),
    Output("finanzas-tipo", "options"),
    Output("finanzas-flujo", "options"),
    Input("finanzas-campaña", "value"),
    Input("finanzas-fecha-desde", "date"),
    Input("finanzas-fecha-hasta", "date"),
)
def update_finanzas_filter_options(campaña, fecha_desde, fecha_hasta):
    options = panel_filter_options(
        "finanzas",
        campaña=campaña,
        fecha_desde=fecha_desde,
        fecha_hasta=fecha_hasta,
    )
    return (
        build_options(options.get("campaña", []), all_label="Todas"),
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
@safe_callback(
    lambda: page_failure_outputs(
        "Finanzas",
        kpi_blocks=2,
        chart_heights=[430, 430, 360, 360],
        insights_title="Insights financieros",
    ),
    "finanzas",
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
    request_error = data.get("_request_error")
    if request_error:
        return page_failure_outputs(
            "Finanzas",
            kpi_blocks=2,
            chart_heights=[430, 430, 360, 360],
            insights_title="Insights financieros",
            message=request_error,
        )

    kpis = data.get("kpis", {})
    flujo_semanal = data.get("flujo_semanal", [])
    cobros_vs_pagos = data.get("cobros_vs_pagos", [])
    aging_cobrar = data.get("aging_cobrar", [])
    aging_pagar = data.get("aging_pagar", [])
    evolucion_saldo = data.get("evolucion_saldo", [])
    tabla = data.get("tabla", [])
    insights = data.get("insights", [])

    aging_total = sum(item.get("importe", 0) for item in aging_cobrar + aging_pagar)
    if not any([flujo_semanal, cobros_vs_pagos, evolucion_saldo, tabla]) and aging_total == 0:
        return page_empty_outputs(
            "Finanzas",
            path="/finanzas",
            kpi_blocks=2,
            chart_heights=[430, 430, 360, 360],
            insights_title="Insights financieros",
            campaña=campaña,
        )

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
        semanas = [format_week_label(item["semana"]) for item in flujo_semanal]
        ingresos = [item["ingresos"] for item in flujo_semanal]
        egresos = [item["egresos"] for item in flujo_semanal]
        saldo_acumulado = [item["saldo_acumulado"] for item in flujo_semanal]
        pressure_idx = best_index(saldo_acumulado, reverse=True) or 0
        fig_flujo = go.Figure()
        fig_flujo.add_trace(
            go.Bar(
                x=semanas,
                y=ingresos,
                name="Ingresos",
                marker_color=CHART_COLORS[0],
                hovertemplate="<b>%{x}</b><br>Ingresos: ARS %{y:,.0f}<extra></extra>",
            )
        )
        fig_flujo.add_trace(
            go.Bar(
                x=semanas,
                y=egresos,
                name="Egresos",
                marker_color=CHART_COLORS[4],
                hovertemplate="<b>%{x}</b><br>Egresos: ARS %{y:,.0f}<extra></extra>",
            )
        )
        fig_flujo.add_trace(
            go.Scatter(
                x=semanas,
                y=saldo_acumulado,
                name="Saldo acumulado",
                mode="lines+markers",
                line=dict(color="#243126", width=2.7),
                marker=dict(size=7, color="#243126"),
                hovertemplate="<b>%{x}</b><br>Saldo acumulado: ARS %{y:,.0f}<extra></extra>",
                yaxis="y2",
            )
        )
        fig_flujo.update_layout(barmode="group", yaxis2=dict(overlaying="y", side="right", showgrid=False))
        add_peak_annotation(
            fig_flujo,
            semanas[pressure_idx],
            saldo_acumulado[pressure_idx],
            f"Piso {fmt_ars(saldo_acumulado[pressure_idx])}",
        )
        add_metric_badge(fig_flujo, f"Mayor presión de caja en {semanas[pressure_idx]}", tone="warning")
    else:
        fig_flujo = empty_figure(height=430)
    fig_flujo.update_layout(**chart_layout(height=430, emphasis="hero", unified_hover=True))
    fig_flujo.update_layout(yaxis_title="ARS")

    if evolucion_saldo:
        fechas_saldo = [format_week_label(item["fecha"]) for item in evolucion_saldo]
        valores_saldo = [item["saldo"] for item in evolucion_saldo]
        min_saldo_idx = best_index(valores_saldo, reverse=True) or 0
        fig_saldo = go.Figure(
            go.Scatter(
                x=fechas_saldo,
                y=valores_saldo,
                mode="lines",
                fill="tozeroy",
                line=dict(color=CHART_COLORS[0], width=2.6),
                fillcolor="rgba(63,107,75,0.12)",
                hovertemplate="<b>%{x}</b><br>Saldo: ARS %{y:,.0f}<extra></extra>",
            )
        )
        fig_saldo.add_hline(y=0, line_color="rgba(194,106,69,0.35)", line_dash="dot")
        add_peak_annotation(
            fig_saldo,
            fechas_saldo[min_saldo_idx],
            valores_saldo[min_saldo_idx],
            f"Punto más bajo {compact_number(valores_saldo[min_saldo_idx])}",
        )
    else:
        fig_saldo = empty_figure(height=430)
    fig_saldo.update_layout(**chart_layout(height=430, showlegend=False, unified_hover=True))
    fig_saldo.update_layout(showlegend=False, yaxis_title="ARS")

    if cobros_vs_pagos:
        meses = [format_month_label(item["mes"]) for item in cobros_vs_pagos]
        cobros = [item["cobros"] for item in cobros_vs_pagos]
        pagos = [item["pagos"] for item in cobros_vs_pagos]
        netos = [cobro - pago for cobro, pago in zip(cobros, pagos)]
        best_gap_idx = best_index(netos) or 0
        fig_cobros = go.Figure()
        fig_cobros.add_trace(
            go.Bar(
                x=meses,
                y=cobros,
                name="Cobros",
                marker_color=CHART_COLORS[1],
                hovertemplate="<b>%{x}</b><br>Cobros: ARS %{y:,.0f}<extra></extra>",
            )
        )
        fig_cobros.add_trace(
            go.Bar(
                x=meses,
                y=pagos,
                name="Pagos",
                marker_color=CHART_COLORS[4],
                hovertemplate="<b>%{x}</b><br>Pagos: ARS %{y:,.0f}<extra></extra>",
            )
        )
        fig_cobros.update_layout(barmode="group")
        add_metric_badge(fig_cobros, f"{meses[best_gap_idx]} mostró la mejor brecha neta", tone="primary")
    else:
        fig_cobros = empty_figure(height=360)
    fig_cobros.update_layout(**chart_layout(height=360, unified_hover=True))
    fig_cobros.update_layout(yaxis_title="ARS")

    if aging_cobrar or aging_pagar:
        labels = [item["rango"] for item in aging_cobrar] or [item["rango"] for item in aging_pagar]
        cobrar = [item["importe"] for item in aging_cobrar]
        pagar = [item["importe"] for item in aging_pagar]
        risk_idx = best_index([(pagar[idx] if idx < len(pagar) else 0) + (cobrar[idx] if idx < len(cobrar) else 0) for idx in range(len(labels))]) or 0
        fig_aging = go.Figure()
        fig_aging.add_trace(
            go.Bar(
                x=labels,
                y=cobrar,
                name="A cobrar",
                marker_color=CHART_COLORS[0],
                hovertemplate="<b>%{x}</b><br>A cobrar: ARS %{y:,.0f}<extra></extra>",
            )
        )
        fig_aging.add_trace(
            go.Bar(
                x=labels,
                y=pagar,
                name="A pagar",
                marker_color=CHART_COLORS[4],
                hovertemplate="<b>%{x}</b><br>A pagar: ARS %{y:,.0f}<extra></extra>",
            )
        )
        fig_aging.update_layout(barmode="group")
        add_metric_badge(fig_aging, f"Mayor exposición en {labels[risk_idx]}", tone="warning")
    else:
        fig_aging = empty_figure(height=360)
    fig_aging.update_layout(**chart_layout(height=360, unified_hover=True))
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
