"""Empaque page."""
import dash
from dash import html, dcc, callback, Output, Input, State
import dash_bootstrap_components as dbc
import plotly.graph_objects as go

from frontend.components.drilldown import drilldown_chart_card
from frontend.components.kpi_card import kpi_card
from frontend.components.loading import loading_graph, loading_slot
from frontend.components.tables import render_table
from frontend.components.empty_state import empty_state
from frontend.components.header import render_header
from frontend.utils import (
    CHART_COLORS,
    api_get,
    build_options,
    chart_layout,
    empty_figure,
    fetch_options,
    filter_params,
    fmt_num,
    insights_panel,
    panel_filter_options,
    sanitize_dropdown_value,
)

dash.register_page(__name__, path="/empaque", name="Empaque")

layout = html.Div(
    [
        render_header("Empaque", "Rendimiento y productividad del proceso de empaque", "Campaña 2024"),
        dcc.Store(id={"type": "panel-filters", "panel": "empaque"}, data={}),
        html.Div(
            [
                # Filter bar
                html.Div(
                    className="filter-bar",
                    children=[
                        html.Div(
                            [
                                html.Div("CAMPAÑA", className="filter-label"),
                                dcc.Dropdown(
                                    id="empaque-campaña",
                                    options=fetch_options("campanas", "campanas"),
                                    value="",
                                    clearable=True,
                                    placeholder="Todas",
                                    style={"minWidth": "110px", "fontSize": "13px"},
                                ),
                            ],
                            className="filter-group",
                        ),
                        html.Div(
                            [
                                html.Div("DESDE", className="filter-label"),
                                dcc.DatePickerSingle(
                                    id="empaque-fecha-desde",
                                    date="2024-03-01",
                                    display_format="DD/MM/YY",
                                ),
                            ],
                            className="filter-group",
                        ),
                        html.Div(
                            [
                                html.Div("HASTA", className="filter-label"),
                                dcc.DatePickerSingle(
                                    id="empaque-fecha-hasta",
                                    date="2024-11-30",
                                    display_format="DD/MM/YY",
                                ),
                            ],
                            className="filter-group",
                        ),
                        html.Div(
                            [
                                html.Div("FINCA", className="filter-label"),
                                dcc.Dropdown(
                                    id="empaque-finca",
                                    options=fetch_options("fincas", "fincas"),
                                    value="",
                                    clearable=True,
                                    placeholder="Todas",
                                    style={"minWidth": "150px", "fontSize": "13px"},
                                ),
                            ],
                            className="filter-group",
                        ),
                        html.Div(
                            [
                                html.Div("LOTE", className="filter-label"),
                                dcc.Dropdown(
                                    id="empaque-lote",
                                    options=fetch_options("lotes", "lotes"),
                                    value="",
                                    clearable=True,
                                    placeholder="Todos",
                                    style={"minWidth": "130px", "fontSize": "13px"},
                                ),
                            ],
                            className="filter-group",
                        ),
                        html.Div(
                            [
                                html.Div("CALIBRE", className="filter-label"),
                                dcc.Dropdown(
                                    id="empaque-calibre",
                                    options=fetch_options("calibres", "calibres"),
                                    value="",
                                    clearable=True,
                                    placeholder="Todos",
                                    style={"minWidth": "120px", "fontSize": "13px"},
                                ),
                            ],
                            className="filter-group",
                        ),
                        html.Div(
                            [
                                html.Div("TURNO", className="filter-label"),
                                dcc.Dropdown(
                                    id="empaque-turno",
                                    options=fetch_options("turnos", "turnos"),
                                    value="",
                                    clearable=True,
                                    placeholder="Todos",
                                    style={"minWidth": "110px", "fontSize": "13px"},
                                ),
                            ],
                            className="filter-group",
                        ),
                        html.Div(
                            [
                                html.Div("LÍNEA", className="filter-label"),
                                dcc.Dropdown(
                                    id="empaque-linea",
                                    options=fetch_options("lineas", "lineas"),
                                    value="",
                                    clearable=True,
                                    placeholder="Todas",
                                    style={"minWidth": "100px", "fontSize": "13px"},
                                ),
                            ],
                            className="filter-group",
                        ),
                        html.Div(
                            [
                                html.Div("CALIDAD", className="filter-label"),
                                dcc.Dropdown(
                                    id="empaque-calidad",
                                    options=fetch_options("calidades", "calidades"),
                                    value="",
                                    clearable=True,
                                    placeholder="Todas",
                                    style={"minWidth": "110px", "fontSize": "13px"},
                                ),
                            ],
                            className="filter-group",
                        ),
                    ],
                ),
                # KPI rows
                html.Div(id="empaque-kpi-row-1", className="kpi-row"),
                html.Div(id="empaque-kpi-row-2", className="kpi-row"),
                html.Div(id="empaque-kpi-row-3", className="kpi-row"),
                # Charts row 1
                dbc.Row(
                    [
                        dbc.Col(
                            drilldown_chart_card("Flujo del Proceso de Empaque", "empaque-chart-flujo", "empaque", "flujo_proceso"),
                            width=5,
                        ),
                        dbc.Col(
                            drilldown_chart_card("Rendimiento Exportable por Lote", "empaque-chart-lote", "empaque", "rendimiento_por_lote"),
                            width=7,
                        ),
                    ],
                    className="g-3",
                ),
                # Charts row 2
                dbc.Row(
                    [
                        dbc.Col(
                            drilldown_chart_card("Rendimiento por Calibre", "empaque-chart-calibre", "empaque", "rendimiento_por_calibre"),
                            width=4,
                        ),
                        dbc.Col(
                            drilldown_chart_card("Productividad por Turno (cajas/hora)", "empaque-chart-turno", "empaque", "productividad_turno"),
                            width=4,
                        ),
                        dbc.Col(
                            drilldown_chart_card("Exportable por Finca (%)", "empaque-chart-finca", "empaque", "comparacion_fincas"),
                            width=4,
                        ),
                    ],
                    className="g-3",
                ),
                # Charts row 3
                dbc.Row(
                    [
                        dbc.Col(
                            drilldown_chart_card("Descarte por Semana", "empaque-chart-descarte", "empaque", "descarte_por_semana"),
                            width=12,
                        ),
                    ],
                    className="g-3",
                ),
                # Insights
                html.Div(id="empaque-insights"),
                # Table
                html.Div(
                    [
                        html.Div("Detalle de Empaque por Lote", className="table-header"),
                        loading_slot("empaque-tabla"),
                    ],
                    className="table-card",
                ),
            ],
            id="page-content",
        ),
    ]
)


@callback(
    Output("empaque-finca", "options"),
    Output("empaque-lote", "options"),
    Output("empaque-calibre", "options"),
    Output("empaque-turno", "options"),
    Output("empaque-linea", "options"),
    Output("empaque-calidad", "options"),
    Input("empaque-campaña", "value"),
    Input("empaque-fecha-desde", "date"),
    Input("empaque-fecha-hasta", "date"),
    Input("empaque-finca", "value"),
    Input("empaque-lote", "value"),
    Input("empaque-calibre", "value"),
    Input("empaque-turno", "value"),
    Input("empaque-linea", "value"),
    Input("empaque-calidad", "value"),
)
def update_empaque_filter_options(campaña, fecha_desde, fecha_hasta, finca, lote, calibre, turno, linea, calidad):
    options = panel_filter_options(
        "empaque",
        campaña=campaña,
        fecha_desde=fecha_desde,
        fecha_hasta=fecha_hasta,
        finca=finca,
        lote=lote,
        calibre=calibre,
        turno=turno,
        linea=linea,
        calidad=calidad,
    )
    return (
        build_options(options.get("finca", []), all_label="Todas"),
        build_options(options.get("lote", []), all_label="Todos"),
        build_options(options.get("calibre", []), all_label="Todos"),
        build_options(options.get("turno", []), all_label="Todos"),
        build_options(options.get("linea", []), all_label="Todas"),
        build_options(options.get("calidad", []), all_label="Todas"),
    )


@callback(
    Output({"type": "panel-filters", "panel": "empaque"}, "data"),
    Input("empaque-campaña", "value"),
    Input("empaque-fecha-desde", "date"),
    Input("empaque-fecha-hasta", "date"),
    Input("empaque-finca", "value"),
    Input("empaque-lote", "value"),
    Input("empaque-calibre", "value"),
    Input("empaque-turno", "value"),
    Input("empaque-linea", "value"),
    Input("empaque-calidad", "value"),
)
def sync_empaque_filters_store(campaña, fecha_desde, fecha_hasta, finca, lote, calibre, turno, linea, calidad):
    return filter_params(
        campaña=campaña,
        fecha_desde=fecha_desde,
        fecha_hasta=fecha_hasta,
        finca=finca,
        lote=lote,
        calibre=calibre,
        turno=turno,
        linea=linea,
        calidad=calidad,
    )


@callback(
    Output("empaque-finca", "value"),
    Output("empaque-lote", "value"),
    Output("empaque-calibre", "value"),
    Output("empaque-turno", "value"),
    Output("empaque-linea", "value"),
    Output("empaque-calidad", "value"),
    Input("empaque-finca", "options"),
    Input("empaque-lote", "options"),
    Input("empaque-calibre", "options"),
    Input("empaque-turno", "options"),
    Input("empaque-linea", "options"),
    Input("empaque-calidad", "options"),
    State("empaque-finca", "value"),
    State("empaque-lote", "value"),
    State("empaque-calibre", "value"),
    State("empaque-turno", "value"),
    State("empaque-linea", "value"),
    State("empaque-calidad", "value"),
)
def sync_empaque_filter_values(
    finca_options,
    lote_options,
    calibre_options,
    turno_options,
    linea_options,
    calidad_options,
    finca,
    lote,
    calibre,
    turno,
    linea,
    calidad,
):
    return (
        sanitize_dropdown_value(finca, finca_options),
        sanitize_dropdown_value(lote, lote_options),
        sanitize_dropdown_value(calibre, calibre_options),
        sanitize_dropdown_value(turno, turno_options),
        sanitize_dropdown_value(linea, linea_options),
        sanitize_dropdown_value(calidad, calidad_options),
    )


@callback(
    Output("empaque-kpi-row-1", "children"),
    Output("empaque-kpi-row-2", "children"),
    Output("empaque-kpi-row-3", "children"),
    Output("empaque-chart-flujo", "figure"),
    Output("empaque-chart-lote", "figure"),
    Output("empaque-chart-calibre", "figure"),
    Output("empaque-chart-turno", "figure"),
    Output("empaque-chart-finca", "figure"),
    Output("empaque-chart-descarte", "figure"),
    Output("empaque-insights", "children"),
    Output("empaque-tabla", "children"),
    Input("empaque-campaña", "value"),
    Input("empaque-fecha-desde", "date"),
    Input("empaque-fecha-hasta", "date"),
    Input("empaque-finca", "value"),
    Input("empaque-lote", "value"),
    Input("empaque-calibre", "value"),
    Input("empaque-turno", "value"),
    Input("empaque-linea", "value"),
    Input("empaque-calidad", "value"),
)
def update_empaque(campaña, fecha_desde, fecha_hasta, finca, lote, calibre, turno, linea, calidad):
    params = filter_params(
        campaña=campaña,
        fecha_desde=fecha_desde,
        fecha_hasta=fecha_hasta,
        finca=finca,
        lote=lote,
        calibre=calibre,
        turno=turno,
        linea=linea,
        calidad=calidad,
    )
    data = api_get("/api/empaque", params=params)

    kpis = data.get("kpis", {})
    flujo = data.get("flujo_proceso", [])
    rend_lote = data.get("rendimiento_por_lote", [])
    rend_calibre = data.get("rendimiento_por_calibre", [])
    prod_turno = data.get("productividad_turno", [])
    desc_semana = data.get("descarte_por_semana", [])
    comp_fincas = data.get("comparacion_fincas", [])
    tabla = data.get("tabla", [])
    insights = data.get("insights", [])

    # KPI row 1
    kg_ing = kpis.get("kg_ingresados", 0) or 0
    kg_exp = kpis.get("kg_exportables", 0) or 0
    kg_ind = kpis.get("kg_industria", 0) or 0
    kg_desc = kpis.get("kg_descarte", 0) or 0

    kpi_row_1 = dbc.Row(
        [
            dbc.Col(kpi_card("Kg Ingresados", f"{kg_ing:,.0f}", "kg", accent="primary", drill_panel="empaque", drill_item="kg_ingresados"), width=3),
            dbc.Col(kpi_card("Kg Exportables", f"{kg_exp:,.0f}", "kg", accent="green", drill_panel="empaque", drill_item="kg_exportables"), width=3),
            dbc.Col(kpi_card("Kg Industria", f"{kg_ind:,.0f}", "kg", accent="blue", drill_panel="empaque", drill_item="kg_industria"), width=3),
            dbc.Col(kpi_card("Kg Descarte", f"{kg_desc:,.0f}", "kg", accent="red", drill_panel="empaque", drill_item="kg_descarte"), width=3),
        ],
        className="g-3 mb-3",
    )

    # KPI row 2
    pct_exp = kpis.get("pct_exportable", 0) or 0
    pct_ind = kpis.get("pct_industria", 0) or 0
    pct_desc = kpis.get("pct_descarte", 0) or 0

    kpi_row_2 = dbc.Row(
        [
            dbc.Col(kpi_card("% Exportable", f"{pct_exp:.1f}", "%", accent="green", drill_panel="empaque", drill_item="pct_exportable"), width=3),
            dbc.Col(kpi_card("% Industria", f"{pct_ind:.1f}", "%", accent="blue", drill_panel="empaque", drill_item="pct_industria"), width=3),
            dbc.Col(kpi_card("% Descarte", f"{pct_desc:.1f}", "%", accent="red", drill_panel="empaque", drill_item="pct_descarte"), width=3),
            dbc.Col(html.Div(), width=3),
        ],
        className="g-3 mb-3",
    )

    # KPI row 3
    cajas_prod = kpis.get("cajas_producidas", 0) or 0
    cajas_hora = kpis.get("cajas_hora", 0) or 0
    costo_caja = kpis.get("costo_caja", 0) or 0

    kpi_row_3 = dbc.Row(
        [
            dbc.Col(kpi_card("Cajas Producidas", f"{cajas_prod:,.0f}", "cajas", accent="primary", drill_panel="empaque", drill_item="cajas_producidas"), width=3),
            dbc.Col(kpi_card("Cajas / Hora", f"{cajas_hora:.1f}", "cj/h", accent="amber", drill_panel="empaque", drill_item="cajas_hora"), width=3),
            dbc.Col(kpi_card("Costo por Caja", fmt_num(costo_caja, 2), "USD/caja", accent="purple", drill_panel="empaque", drill_item="costo_caja"), width=3),
            dbc.Col(html.Div(), width=3),
        ],
        className="g-3",
    )

    # Chart 1: Flujo proceso (funnel with horizontal bars)
    if flujo:
        etapas = [d.get("etapa", "") for d in flujo]
        kg_vals = [d.get("kg", 0) for d in flujo]
        colors_flujo = ["#2E6B47", "#4A9B6A", "#7EC8A0", "#F59E0B", "#EF4444"]
        fig_flujo = go.Figure(
            go.Bar(
                y=etapas,
                x=kg_vals,
                orientation="h",
                marker_color=colors_flujo[:len(etapas)],
                text=[f"{v:,.0f} kg" for v in kg_vals],
                textposition="outside",
            )
        )
    else:
        fig_flujo = empty_figure()

    fig_flujo.update_layout(**chart_layout(height=280))
    fig_flujo.update_layout(
        showlegend=False,
        margin=dict(l=120, r=60, t=40, b=40),
        yaxis=dict(showgrid=False, showline=False),
        xaxis=dict(showgrid=True, gridcolor="#F3F4F6"),
    )

    # Chart 2: Rendimiento por lote (bar)
    if rend_lote:
        sorted_rl = sorted(rend_lote, key=lambda x: x.get("pct_exportable", 0), reverse=True)[:12]
        lotes_r = [f"{d.get('lote','')} ({d.get('finca','')})" for d in sorted_rl]
        pct_vals = [d.get("pct_exportable", 0) for d in sorted_rl]
        fig_lote = go.Figure(
            go.Bar(
                x=lotes_r,
                y=pct_vals,
                marker_color=[
                    "#22C55E" if v >= 70 else ("#F59E0B" if v >= 55 else "#EF4444")
                    for v in pct_vals
                ],
                text=[f"{v:.1f}%" for v in pct_vals],
                textposition="outside",
            )
        )
    else:
        fig_lote = empty_figure()

    fig_lote.update_layout(**chart_layout(height=300))
    fig_lote.update_layout(yaxis_title="% Exportable", showlegend=False)

    # Chart 3: Rendimiento por calibre
    if rend_calibre:
        calibres = [d.get("calibre", "") for d in rend_calibre]
        pct_c = [d.get("pct_exportable", 0) for d in rend_calibre]
        fig_calibre = go.Figure(
            go.Bar(
                x=calibres,
                y=pct_c,
                marker_color="#4A9B6A",
                text=[f"{v:.1f}%" for v in pct_c],
                textposition="outside",
            )
        )
    else:
        fig_calibre = empty_figure()

    fig_calibre.update_layout(**chart_layout(height=280))
    fig_calibre.update_layout(yaxis_title="% Exportable", showlegend=False)

    # Chart 4: Productividad por turno
    if prod_turno:
        turnos = [d.get("turno", "") for d in prod_turno]
        cj_hora = [d.get("cajas_hora", 0) for d in prod_turno]
        fig_turno = go.Figure(
            go.Bar(
                x=turnos,
                y=cj_hora,
                marker_color="#8B6914",
                text=[f"{v:.1f}" for v in cj_hora],
                textposition="outside",
            )
        )
    else:
        fig_turno = empty_figure()

    fig_turno.update_layout(**chart_layout(height=280))
    fig_turno.update_layout(yaxis_title="Cajas/Hora", showlegend=False)

    # Chart 5: Exportable por finca
    if comp_fincas:
        fincas_c = [d.get("finca", "") for d in comp_fincas]
        pct_f = [d.get("pct_exportable", 0) for d in comp_fincas]
        fig_finca = go.Figure(
            go.Bar(
                x=fincas_c,
                y=pct_f,
                marker_color=CHART_COLORS[:len(fincas_c)],
                text=[f"{v:.1f}%" for v in pct_f],
                textposition="outside",
            )
        )
    else:
        fig_finca = empty_figure()

    fig_finca.update_layout(**chart_layout(height=280))
    fig_finca.update_layout(yaxis_title="% Exportable", showlegend=False)

    # Chart 6: Descarte por semana (line)
    if desc_semana:
        semanas = [d.get("semana", "") for d in desc_semana]
        kg_desc_vals = [d.get("kg_descarte", 0) for d in desc_semana]
        fig_desc = go.Figure(
            go.Scatter(
                x=semanas,
                y=kg_desc_vals,
                mode="lines+markers",
                name="Kg Descarte",
                line=dict(color="#EF4444", width=2),
                fill="tozeroy",
                fillcolor="rgba(239,68,68,0.07)",
            )
        )
    else:
        fig_desc = empty_figure()

    fig_desc.update_layout(**chart_layout(height=260))
    fig_desc.update_layout(yaxis_title="Kg Descarte", showlegend=False)

    insights_comp = insights_panel("Insights de empaque", insights)

    # Table
    if tabla:
        columns = [
            {"name": "Lote", "id": "lote"},
            {"name": "Finca", "id": "finca"},
            {"name": "Kg Ingresados", "id": "kg_ingresados", "type": "numeric"},
            {"name": "Kg Exportables", "id": "kg_exportables", "type": "numeric"},
            {"name": "Kg Industria", "id": "kg_industria", "type": "numeric"},
            {"name": "Kg Descarte", "id": "kg_descarte", "type": "numeric"},
            {"name": "% Exportable", "id": "pct_exportable", "type": "numeric"},
            {"name": "Calibre Dom.", "id": "calibre_dominante"},
            {"name": "Calidad Dom.", "id": "calidad_dominante"},
        ]
        tabla_comp = render_table(tabla, columns, "empaque-tabla-dt")
    else:
        tabla_comp = empty_state()

    return (
        kpi_row_1, kpi_row_2, kpi_row_3,
        fig_flujo, fig_lote, fig_calibre, fig_turno, fig_finca, fig_desc,
        insights_comp, tabla_comp,
    )
