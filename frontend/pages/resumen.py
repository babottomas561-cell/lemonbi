"""Resumen Ejecutivo page."""
import dash
from dash import html, dcc, callback, Output, Input, State
import dash_bootstrap_components as dbc
import plotly.graph_objects as go

from frontend.components.filter_bar import bind_date_shortcuts, campaign_filter, date_range_filter, dropdown_filter, render_filter_bar
from frontend.components.drilldown import drilldown_chart_card
from frontend.components.kpi_card import kpi_card
from frontend.components.loading import loading_slot
from frontend.components.tables import render_table
from frontend.components.empty_state import empty_state
from frontend.components.header import render_header
from frontend.utils import (
    CHART_COLORS,
    add_donut_center_label,
    add_metric_badge,
    add_peak_annotation,
    add_reference_line,
    api_get,
    best_index,
    build_options,
    chart_layout,
    compact_number,
    donut_layout,
    empty_figure,
    fetch_options,
    filter_params,
    fmt_ars,
    fmt_num,
    fmt_usd,
    insights_panel,
    page_empty_outputs,
    page_failure_outputs,
    panel_filter_options,
    safe_callback,
    sanitize_dropdown_value,
)

dash.register_page(__name__, path="/", name="Resumen Ejecutivo")
bind_date_shortcuts("resumen")

layout = html.Div(
    [
        render_header(
            "Resumen Ejecutivo",
            "Vista consolidada de la operación",
            "Campaña 2024",
        ),
        dcc.Store(id={"type": "panel-filters", "panel": "resumen"}, data={}),
        html.Div(
            [
                render_filter_bar(
                    [
                        campaign_filter("resumen-campaña", width="110px"),
                        date_range_filter("resumen", "2024-03-01", "2024-11-30"),
                        dropdown_filter("FINCA", "resumen-finca", fetch_options("fincas", "fincas"), width="170px"),
                        dropdown_filter("VARIEDAD", "resumen-variedad", fetch_options("variedades", "variedades"), width="150px"),
                    ]
                ),
                # KPI rows
                html.Div(id="resumen-kpi-row-1", className="kpi-row"),
                html.Div(id="resumen-kpi-row-2", className="kpi-row"),
                # Charts row 1
                dbc.Row(
                    [
                        dbc.Col(
                            drilldown_chart_card(
                                "Ingreso semanal de fruta",
                                "resumen-chart-fruta",
                                "resumen",
                                "evolucion_fruta",
                                subtitle="Volumen recibido en empaque a lo largo de la campaña",
                                priority="primary",
                            ),
                            width=7,
                        ),
                        dbc.Col(
                            drilldown_chart_card(
                                "Mix comercial por destino",
                                "resumen-chart-destino",
                                "resumen",
                                "mix_destino",
                                subtitle="Participación del volumen vendido por canal de salida",
                                priority="secondary",
                            ),
                            width=5,
                        ),
                    ],
                    className="g-3",
                ),
                # Charts row 2
                dbc.Row(
                    [
                        dbc.Col(
                            drilldown_chart_card(
                                "Facturación semanal",
                                "resumen-chart-ventas",
                                "resumen",
                                "evolucion_ventas",
                                subtitle="Ventas netas en USD dentro de la ventana seleccionada",
                                priority="secondary",
                            ),
                            width=6,
                        ),
                        dbc.Col(
                            drilldown_chart_card(
                                "Ingresos y margen por mes",
                                "resumen-chart-margen",
                                "resumen",
                                "margen_por_mes",
                                subtitle="Resultado bruto mensual para lectura ejecutiva",
                                priority="secondary",
                            ),
                            width=6,
                        ),
                    ],
                    className="g-3",
                ),
                # Insights
                html.Div(id="resumen-insights"),
                # Table
                html.Div(
                    [
                        html.Div("Resumen por Finca", className="table-header"),
                        loading_slot("resumen-tabla"),
                    ],
                    className="table-card",
                ),
            ],
            id="page-content",
        ),
    ]
)


@callback(
    Output("resumen-campaña", "options"),
    Output("resumen-finca", "options"),
    Output("resumen-variedad", "options"),
    Input("resumen-campaña", "value"),
    Input("resumen-fecha-desde", "date"),
    Input("resumen-fecha-hasta", "date"),
)
def update_resumen_filter_options(campaña, fecha_desde, fecha_hasta):
    options = panel_filter_options(
        "resumen",
        campaña=campaña,
        fecha_desde=fecha_desde,
        fecha_hasta=fecha_hasta,
    )
    return (
        build_options(options.get("campaña", []), all_label="Todas"),
        build_options(options.get("finca", []), all_label="Todas"),
        build_options(options.get("variedad", []), all_label="Todas"),
    )


@callback(
    Output({"type": "panel-filters", "panel": "resumen"}, "data"),
    Input("resumen-campaña", "value"),
    Input("resumen-fecha-desde", "date"),
    Input("resumen-fecha-hasta", "date"),
    Input("resumen-finca", "value"),
    Input("resumen-variedad", "value"),
)
def sync_resumen_filters_store(campaña, fecha_desde, fecha_hasta, finca, variedad):
    return filter_params(
        campaña=campaña,
        fecha_desde=fecha_desde,
        fecha_hasta=fecha_hasta,
        finca=finca,
        variedad=variedad,
    )


@callback(
    Output("resumen-finca", "value"),
    Output("resumen-variedad", "value"),
    Input("resumen-finca", "options"),
    Input("resumen-variedad", "options"),
    State("resumen-finca", "value"),
    State("resumen-variedad", "value"),
)
def sync_resumen_filter_values(finca_options, variedad_options, finca, variedad):
    return (
        sanitize_dropdown_value(finca, finca_options),
        sanitize_dropdown_value(variedad, variedad_options),
    )


@callback(
    Output("resumen-kpi-row-1", "children"),
    Output("resumen-kpi-row-2", "children"),
    Output("resumen-chart-fruta", "figure"),
    Output("resumen-chart-ventas", "figure"),
    Output("resumen-chart-destino", "figure"),
    Output("resumen-chart-margen", "figure"),
    Output("resumen-insights", "children"),
    Output("resumen-tabla", "children"),
    Input("resumen-campaña", "value"),
    Input("resumen-fecha-desde", "date"),
    Input("resumen-fecha-hasta", "date"),
    Input("resumen-finca", "value"),
    Input("resumen-variedad", "value"),
)
@safe_callback(
    lambda: page_failure_outputs(
        "Resumen Ejecutivo",
        kpi_blocks=2,
        chart_heights=[430, 390, 430, 390],
        insights_title="Insights automáticos",
    ),
    "resumen",
)
def update_resumen(campaña, fecha_desde, fecha_hasta, finca, variedad):
    params = filter_params(
        campaña=campaña,
        fecha_desde=fecha_desde,
        fecha_hasta=fecha_hasta,
        finca=finca,
        variedad=variedad,
    )
    data = api_get("/api/resumen", params=params)
    request_error = data.get("_request_error")
    if request_error:
        return page_failure_outputs(
            "Resumen Ejecutivo",
            kpi_blocks=2,
            chart_heights=[430, 390, 430, 390],
            insights_title="Insights automáticos",
            message=request_error,
        )

    kpis = data.get("kpis", {})
    evolucion_fruta = data.get("evolucion_fruta", [])
    evolucion_ventas = data.get("evolucion_ventas", [])
    mix_destino = data.get("mix_destino", [])
    margen_por_mes = data.get("margen_por_mes", [])
    tabla_fincas = data.get("tabla_fincas", [])
    insights = data.get("insights", [])

    if not any([evolucion_fruta, evolucion_ventas, mix_destino, margen_por_mes, tabla_fincas]):
        return page_empty_outputs(
            "Resumen Ejecutivo",
            path="/",
            kpi_blocks=2,
            chart_heights=[430, 390, 430, 390],
            insights_title="Insights automáticos",
            campaña=campaña,
        )

    # --- KPI row 1 ---
    fruta_kg = kpis.get("fruta_ingresada_kg", 0) or 0
    kg_proc = kpis.get("kg_procesados", 0) or 0
    pct_exp = kpis.get("pct_exportable", 0) or 0
    ventas = kpis.get("ventas_netas_usd", 0) or 0

    kpi_row_1 = dbc.Row(
        [
            dbc.Col(
                kpi_card(
                    "Fruta Ingresada",
                    f"{fruta_kg / 1000:,.1f}",
                    "ton",
                    accent="green",
                    drill_panel="resumen",
                    drill_item="fruta_ingresada_kg",
                ),
                width=3,
            ),
            dbc.Col(
                kpi_card(
                    "Kg Procesados",
                    f"{kg_proc / 1000:,.1f}",
                    "ton",
                    accent="blue",
                    drill_panel="resumen",
                    drill_item="kg_procesados",
                ),
                width=3,
            ),
            dbc.Col(
                kpi_card(
                    "% Exportable",
                    f"{pct_exp:.1f}",
                    "%",
                    accent="amber",
                    drill_panel="resumen",
                    drill_item="pct_exportable",
                ),
                width=3,
            ),
            dbc.Col(
                kpi_card(
                    "Ventas Netas",
                    fmt_usd(ventas),
                    "",
                    accent="primary",
                    drill_panel="resumen",
                    drill_item="ventas_netas_usd",
                ),
                width=3,
            ),
        ],
        className="g-3 mb-3",
    )

    # --- KPI row 2 ---
    margen_pct = kpis.get("margen_bruto_pct", 0) or 0
    caja_30d = kpis.get("caja_proyectada_30d", 0) or 0
    costo_kg = kpis.get("costo_kg_exportado", 0) or 0
    cumplimiento = kpis.get("cumplimiento_pedidos_pct", 0) or 0

    kpi_row_2 = dbc.Row(
        [
            dbc.Col(
                kpi_card(
                    "Margen Bruto",
                    f"{margen_pct:.1f}",
                    "%",
                    accent="green",
                    drill_panel="resumen",
                    drill_item="margen_bruto_pct",
                ),
                width=3,
            ),
            dbc.Col(
                kpi_card(
                    "Caja Proyectada 30d",
                    fmt_ars(caja_30d),
                    "",
                    accent="blue",
                    drill_panel="resumen",
                    drill_item="caja_proyectada_30d",
                ),
                width=3,
            ),
            dbc.Col(
                kpi_card(
                    "Costo / Kg Exportado",
                    fmt_num(costo_kg, 1),
                    "ARS/kg",
                    accent="amber",
                    drill_panel="resumen",
                    drill_item="costo_kg_exportado",
                ),
                width=3,
            ),
            dbc.Col(
                kpi_card(
                    "Cumplimiento Pedidos",
                    f"{cumplimiento:.1f}",
                    "%",
                    accent="green",
                    drill_panel="resumen",
                    drill_item="cumplimiento_pedidos_pct",
                ),
                width=3,
            ),
        ],
        className="g-3",
    )

    # --- Chart 1: Evolución fruta (line) ---
    if evolucion_fruta:
        semanas = [d.get("semana", "") for d in evolucion_fruta]
        kg_vals = [d.get("kg_ingresados", 0) for d in evolucion_fruta]
        fig_fruta = go.Figure(
            go.Scatter(
                x=semanas,
                y=kg_vals,
                mode="lines+markers",
                name="Kg Ingresados",
                line=dict(color="#2E6B47", width=2.5),
                marker=dict(size=5, color="#2E6B47"),
                fill="tozeroy",
                fillcolor="rgba(63,107,75,0.12)",
                hovertemplate="Semana %{x}<br>Fruta ingresada: %{y:,.0f} kg<extra></extra>",
            )
        )
        add_reference_line(fig_fruta, sum(kg_vals) / len(kg_vals), "Promedio semanal")
        peak_idx = best_index(kg_vals)
        if peak_idx is not None:
            add_peak_annotation(fig_fruta, semanas[peak_idx], kg_vals[peak_idx], f"Pico: {compact_number(kg_vals[peak_idx], ' kg')}")
        add_metric_badge(fig_fruta, f"Semana pico: {compact_number(max(kg_vals), ' kg')}")
    else:
        fig_fruta = empty_figure()

    fig_fruta.update_layout(**chart_layout(height=430, emphasis="hero", showlegend=False, unified_hover=True))
    fig_fruta.update_layout(yaxis_title="Kg", xaxis=dict(tickangle=0, nticks=8))

    # --- Chart 2: Evolución ventas (bar) ---
    if evolucion_ventas:
        sem_v = [d.get("semana", "") for d in evolucion_ventas]
        imp_v = [d.get("importe_usd", 0) for d in evolucion_ventas]
        fig_ventas = go.Figure(
            go.Bar(
                x=sem_v,
                y=imp_v,
                name="Ventas USD",
                marker_color="#6C8C5A",
                hovertemplate="Semana %{x}<br>Ventas netas: USD %{y:,.0f}<extra></extra>",
            )
        )
        peak_idx = best_index(imp_v)
        if peak_idx is not None:
            add_peak_annotation(fig_ventas, sem_v[peak_idx], imp_v[peak_idx], f"Mejor semana: USD {compact_number(imp_v[peak_idx])}")
        add_metric_badge(fig_ventas, f"Facturación pico: USD {compact_number(max(imp_v))}")
    else:
        fig_ventas = empty_figure()

    fig_ventas.update_layout(**chart_layout(height=390, emphasis="secondary", showlegend=False, unified_hover=True))
    fig_ventas.update_layout(yaxis_title="USD", xaxis=dict(tickangle=0, nticks=8))

    # --- Chart 3: Mix destino (donut) ---
    if mix_destino:
        dest_labels = [d.get("destino", "") for d in mix_destino]
        dest_vals = [d.get("kg", 0) for d in mix_destino]
        fig_destino = go.Figure(
            go.Pie(
                labels=dest_labels,
                values=dest_vals,
                hole=0.55,
                marker=dict(colors=CHART_COLORS),
                textinfo="label+percent",
                textfont=dict(size=11),
                hovertemplate="%{label}<br>%{value:,.0f} kg<br>%{percent}<extra></extra>",
            )
        )
        add_donut_center_label(fig_destino, dest_labels[0], "destino líder")
    else:
        fig_destino = empty_figure()

    fig_destino.update_layout(**donut_layout(height=430))
    fig_destino.update_layout(showlegend=True)

    # --- Chart 4: Margen bruto por mes (bar + line combo) ---
    if margen_por_mes:
        meses = [d.get("mes", "") for d in margen_por_mes]
        ingresos = [d.get("ingresos_usd", 0) for d in margen_por_mes]
        margen_usd = [d.get("margen_bruto_usd", 0) for d in margen_por_mes]
        fig_margen = go.Figure()
        fig_margen.add_trace(
            go.Bar(
                x=meses,
                y=ingresos,
                name="Ingresos USD",
                marker_color="#95B29E",
                hovertemplate="Mes %{x}<br>Ingresos: USD %{y:,.0f}<extra></extra>",
            )
        )
        fig_margen.add_trace(
            go.Scatter(
                x=meses,
                y=margen_usd,
                name="Margen Bruto USD",
                mode="lines+markers",
                line=dict(color="#B69245", width=2.8),
                marker=dict(size=7, color="#B69245"),
                hovertemplate="Mes %{x}<br>Margen bruto: USD %{y:,.0f}<extra></extra>",
                yaxis="y2",
            )
        )
        fig_margen.update_layout(
            yaxis2=dict(overlaying="y", side="right", showgrid=False, title="Margen USD")
        )
        peak_idx = best_index(margen_usd)
        if peak_idx is not None:
            add_peak_annotation(fig_margen, meses[peak_idx], margen_usd[peak_idx], f"Mejor mes: USD {compact_number(margen_usd[peak_idx])}", color="#B69245")
    else:
        fig_margen = empty_figure()

    fig_margen.update_layout(**chart_layout(height=390, emphasis="secondary", showlegend=True, unified_hover=True))

    insights_comp = insights_panel("Insights automáticos", insights)

    # --- Table ---
    if tabla_fincas:
        columns = [
            {"name": "Finca", "id": "finca"},
            {"name": "Kg Cosechados", "id": "kg_cosechados", "type": "numeric"},
            {"name": "% Exportable", "id": "pct_exportable", "type": "numeric"},
            {"name": "Ventas USD", "id": "ventas_usd", "type": "numeric"},
            {"name": "Margen %", "id": "margen_pct", "type": "numeric"},
        ]
        tabla = render_table(tabla_fincas, columns, "resumen-tabla-dt")
    else:
        tabla = empty_state()

    return kpi_row_1, kpi_row_2, fig_fruta, fig_ventas, fig_destino, fig_margen, insights_comp, tabla
