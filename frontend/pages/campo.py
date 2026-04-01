"""Campo page."""
import dash
from dash import html, dcc, callback, Output, Input, State
import dash_bootstrap_components as dbc
import plotly.graph_objects as go

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
    fmt_ars,
    fmt_num,
    insights_panel,
    panel_filter_options,
    sanitize_dropdown_value,
)

dash.register_page(__name__, path="/campo", name="Campo")

layout = html.Div(
    [
        render_header("Campo", "Producción y cosecha por lote y finca", "Campaña 2024"),
        dcc.Store(id={"type": "panel-filters", "panel": "campo"}, data={}),
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
                                    id="campo-campaña",
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
                                    id="campo-fecha-desde",
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
                                    id="campo-fecha-hasta",
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
                                    id="campo-finca",
                                    options=fetch_options("fincas", "fincas"),
                                    value="",
                                    clearable=True,
                                    placeholder="Todas",
                                    style={"minWidth": "160px", "fontSize": "13px"},
                                ),
                            ],
                            className="filter-group",
                        ),
                        html.Div(
                            [
                                html.Div("VARIEDAD", className="filter-label"),
                                dcc.Dropdown(
                                    id="campo-variedad",
                                    options=fetch_options("variedades", "variedades"),
                                    value="",
                                    clearable=True,
                                    placeholder="Todas",
                                    style={"minWidth": "130px", "fontSize": "13px"},
                                ),
                            ],
                            className="filter-group",
                        ),
                        html.Div(
                            [
                                html.Div("LOTE", className="filter-label"),
                                dcc.Dropdown(
                                    id="campo-lote",
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
                                html.Div("ESTADO", className="filter-label"),
                                dcc.Dropdown(
                                    id="campo-estado",
                                    options=fetch_options("estados", "estados"),
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
                                html.Div("ENCARGADO", className="filter-label"),
                                dcc.Dropdown(
                                    id="campo-encargado",
                                    options=fetch_options("encargados", "encargados"),
                                    value="",
                                    clearable=True,
                                    placeholder="Todos",
                                    style={"minWidth": "140px", "fontSize": "13px"},
                                ),
                            ],
                            className="filter-group",
                        ),
                    ],
                ),
                # KPI rows
                html.Div(id="campo-kpi-row-1", className="kpi-row"),
                html.Div(id="campo-kpi-row-2", className="kpi-row"),
                # Charts row 1
                dbc.Row(
                    [
                        dbc.Col(
                            html.Div(
                                [
                                    html.Div("Producción por Lote", className="chart-title"),
                                    loading_graph("campo-chart-lote"),
                                ],
                                className="chart-card",
                            ),
                            width=7,
                        ),
                        dbc.Col(
                            html.Div(
                                [
                                    html.Div("Rendimiento por Hectárea — Finca", className="chart-title"),
                                    loading_graph("campo-chart-rendimiento"),
                                ],
                                className="chart-card",
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
                            html.Div(
                                [
                                    html.Div("Avance de Cosecha por Finca", className="chart-title"),
                                    loading_graph("campo-chart-avance"),
                                ],
                                className="chart-card",
                            ),
                            width=6,
                        ),
                        dbc.Col(
                            html.Div(
                                [
                                    html.Div("Comparación entre Variedades", className="chart-title"),
                                    loading_graph("campo-chart-variedades"),
                                ],
                                className="chart-card",
                            ),
                            width=6,
                        ),
                    ],
                    className="g-3",
                ),
                # Charts row 3
                dbc.Row(
                    [
                        dbc.Col(
                            html.Div(
                                [
                                    html.Div("Costo por Lote", className="chart-title"),
                                    loading_graph("campo-chart-costo"),
                                ],
                                className="chart-card",
                            ),
                            width=12,
                        ),
                    ],
                    className="g-3",
                ),
                # Insights
                html.Div(id="campo-insights"),
                # Table
                html.Div(
                    [
                        html.Div("Detalle por Lote", className="table-header"),
                        loading_slot("campo-tabla"),
                    ],
                    className="table-card",
                ),
            ],
            id="page-content",
        ),
    ]
)


@callback(
    Output("campo-finca", "options"),
    Output("campo-variedad", "options"),
    Output("campo-lote", "options"),
    Output("campo-estado", "options"),
    Output("campo-encargado", "options"),
    Input("campo-campaña", "value"),
    Input("campo-fecha-desde", "date"),
    Input("campo-fecha-hasta", "date"),
    Input("campo-finca", "value"),
    Input("campo-lote", "value"),
    Input("campo-variedad", "value"),
    Input("campo-estado", "value"),
    Input("campo-encargado", "value"),
)
def update_campo_filter_options(campaña, fecha_desde, fecha_hasta, finca, lote, variedad, estado, encargado):
    options = panel_filter_options(
        "campo",
        campaña=campaña,
        fecha_desde=fecha_desde,
        fecha_hasta=fecha_hasta,
        finca=finca,
        lote=lote,
        variedad=variedad,
        estado=estado,
        encargado=encargado,
    )
    return (
        build_options(options.get("finca", []), all_label="Todas"),
        build_options(options.get("variedad", []), all_label="Todas"),
        build_options(options.get("lote", []), all_label="Todos"),
        build_options(options.get("estado", []), all_label="Todos"),
        build_options(options.get("encargado", []), all_label="Todos"),
    )


@callback(
    Output({"type": "panel-filters", "panel": "campo"}, "data"),
    Input("campo-campaña", "value"),
    Input("campo-fecha-desde", "date"),
    Input("campo-fecha-hasta", "date"),
    Input("campo-finca", "value"),
    Input("campo-lote", "value"),
    Input("campo-variedad", "value"),
    Input("campo-estado", "value"),
    Input("campo-encargado", "value"),
)
def sync_campo_filters_store(campaña, fecha_desde, fecha_hasta, finca, lote, variedad, estado, encargado):
    return filter_params(
        campaña=campaña,
        fecha_desde=fecha_desde,
        fecha_hasta=fecha_hasta,
        finca=finca,
        lote=lote,
        variedad=variedad,
        estado=estado,
        encargado=encargado,
    )


@callback(
    Output("campo-finca", "value"),
    Output("campo-variedad", "value"),
    Output("campo-lote", "value"),
    Output("campo-estado", "value"),
    Output("campo-encargado", "value"),
    Input("campo-finca", "options"),
    Input("campo-variedad", "options"),
    Input("campo-lote", "options"),
    Input("campo-estado", "options"),
    Input("campo-encargado", "options"),
    State("campo-finca", "value"),
    State("campo-variedad", "value"),
    State("campo-lote", "value"),
    State("campo-estado", "value"),
    State("campo-encargado", "value"),
)
def sync_campo_filter_values(
    finca_options,
    variedad_options,
    lote_options,
    estado_options,
    encargado_options,
    finca,
    variedad,
    lote,
    estado,
    encargado,
):
    return (
        sanitize_dropdown_value(finca, finca_options),
        sanitize_dropdown_value(variedad, variedad_options),
        sanitize_dropdown_value(lote, lote_options),
        sanitize_dropdown_value(estado, estado_options),
        sanitize_dropdown_value(encargado, encargado_options),
    )


@callback(
    Output("campo-kpi-row-1", "children"),
    Output("campo-kpi-row-2", "children"),
    Output("campo-chart-lote", "figure"),
    Output("campo-chart-rendimiento", "figure"),
    Output("campo-chart-avance", "figure"),
    Output("campo-chart-variedades", "figure"),
    Output("campo-chart-costo", "figure"),
    Output("campo-insights", "children"),
    Output("campo-tabla", "children"),
    Input("campo-campaña", "value"),
    Input("campo-fecha-desde", "date"),
    Input("campo-fecha-hasta", "date"),
    Input("campo-finca", "value"),
    Input("campo-lote", "value"),
    Input("campo-variedad", "value"),
    Input("campo-estado", "value"),
    Input("campo-encargado", "value"),
)
def update_campo(campaña, fecha_desde, fecha_hasta, finca, lote, variedad, estado, encargado):
    params = filter_params(
        campaña=campaña,
        fecha_desde=fecha_desde,
        fecha_hasta=fecha_hasta,
        finca=finca,
        lote=lote,
        variedad=variedad,
        estado=estado,
        encargado=encargado,
    )
    data = api_get("/api/campo", params=params)

    kpis = data.get("kpis", {})
    prod_por_lote = data.get("produccion_por_lote", [])
    rend_por_finca = data.get("rendimiento_por_finca", [])
    avance_finca = data.get("avance_por_finca", [])
    comp_variedades = data.get("comparacion_variedades", [])
    costo_lote = data.get("costo_por_lote", [])
    tabla = data.get("tabla", [])
    insights = data.get("insights", [])

    # KPI row 1
    ha_activas = kpis.get("ha_activas", 0) or 0
    ton_cos = kpis.get("ton_cosechadas", 0) or 0
    ton_pend = kpis.get("ton_pendientes", 0) or 0
    rinde = kpis.get("rinde_promedio_kg_ha", 0) or 0

    kpi_row_1 = dbc.Row(
        [
            dbc.Col(kpi_card("Hectáreas Activas", f"{ha_activas:,.0f}", "ha", accent="primary", drill_panel="campo", drill_item="ha_activas"), width=3),
            dbc.Col(kpi_card("Ton Cosechadas", f"{ton_cos:,.1f}", "ton", accent="green", drill_panel="campo", drill_item="ton_cosechadas"), width=3),
            dbc.Col(kpi_card("Ton Pendientes", f"{ton_pend:,.1f}", "ton", accent="amber", drill_panel="campo", drill_item="ton_pendientes"), width=3),
            dbc.Col(kpi_card("Rinde Promedio", f"{rinde:,.0f}", "kg/ha", accent="blue", drill_panel="campo", drill_item="rinde_promedio_kg_ha"), width=3),
        ],
        className="g-3 mb-3",
    )

    # KPI row 2
    costo_ha = kpis.get("costo_promedio_ha", 0) or 0
    costo_kg = kpis.get("costo_kg_cosechado", 0) or 0
    avance_pct = kpis.get("avance_cosecha_pct", 0) or 0

    kpi_row_2 = dbc.Row(
        [
            dbc.Col(kpi_card("Costo Promedio/Ha", fmt_ars(costo_ha), "", accent="amber", drill_panel="campo", drill_item="costo_promedio_ha"), width=3),
            dbc.Col(kpi_card("Costo/Kg Cosechado", fmt_num(costo_kg, 1), "ARS/kg", accent="red", drill_panel="campo", drill_item="costo_kg_cosechado"), width=3),
            dbc.Col(kpi_card("Avance Cosecha", f"{avance_pct:.1f}", "%", accent="green", drill_panel="campo", drill_item="avance_cosecha_pct"), width=3),
            dbc.Col(html.Div(), width=3),
        ],
        className="g-3",
    )

    # Chart 1: Producción por lote (horizontal bar)
    if prod_por_lote:
        sorted_lotes = sorted(prod_por_lote, key=lambda x: x.get("kg_cosechados", 0), reverse=True)[:15]
        lotes = [f"{d.get('lote','')} ({d.get('finca','')})" for d in sorted_lotes]
        kg_vals = [d.get("kg_cosechados", 0) for d in sorted_lotes]
        fig_lote = go.Figure(
            go.Bar(
                y=lotes,
                x=kg_vals,
                orientation="h",
                marker_color="#2E6B47",
                text=[f"{v:,.0f}" for v in kg_vals],
                textposition="outside",
            )
        )
    else:
        fig_lote = empty_figure()

    fig_lote.update_layout(**chart_layout(height=350))
    fig_lote.update_layout(
        xaxis_title="Kg Cosechados",
        margin=dict(l=160, r=40, t=40, b=40),
        yaxis=dict(showgrid=False, showline=False),
    )

    # Chart 2: Rendimiento por finca (bar)
    if rend_por_finca:
        fincas_r = [d.get("finca", "") for d in rend_por_finca]
        rend_vals = [d.get("rendimiento_promedio_kg_ha", 0) for d in rend_por_finca]
        fig_rend = go.Figure(
            go.Bar(
                x=fincas_r,
                y=rend_vals,
                marker_color=CHART_COLORS[:len(fincas_r)],
                text=[f"{v:,.0f}" for v in rend_vals],
                textposition="outside",
            )
        )
    else:
        fig_rend = empty_figure()

    fig_rend.update_layout(**chart_layout(height=300))
    fig_rend.update_layout(yaxis_title="kg/ha", showlegend=False)

    # Chart 3: Avance cosecha por finca (stacked bar)
    if avance_finca:
        fincas_a = [d.get("finca", "") for d in avance_finca]
        kg_cos = [d.get("kg_cosechados", 0) for d in avance_finca]
        kg_pend = [d.get("kg_pendientes", 0) for d in avance_finca]
        fig_avance = go.Figure()
        fig_avance.add_trace(
            go.Bar(name="Cosechado", x=fincas_a, y=kg_cos, marker_color="#2E6B47")
        )
        fig_avance.add_trace(
            go.Bar(name="Pendiente", x=fincas_a, y=kg_pend, marker_color="#F59E0B")
        )
        fig_avance.update_layout(barmode="stack")
    else:
        fig_avance = empty_figure()

    fig_avance.update_layout(**chart_layout(height=300))
    fig_avance.update_layout(yaxis_title="Kg")

    # Chart 4: Comparación entre variedades (grouped bar)
    if comp_variedades:
        variedades_c = [d.get("variedad", "") for d in comp_variedades]
        kg_total = [d.get("kg_total", 0) for d in comp_variedades]
        rend_prom = [d.get("rendimiento_promedio", 0) for d in comp_variedades]
        fig_var = go.Figure()
        fig_var.add_trace(
            go.Bar(name="Kg Total", x=variedades_c, y=kg_total, marker_color="#4A9B6A", yaxis="y")
        )
        fig_var.add_trace(
            go.Bar(name="Rend. Promedio kg/ha", x=variedades_c, y=rend_prom, marker_color="#C4A44A", yaxis="y2")
        )
        fig_var.update_layout(
            yaxis2=dict(overlaying="y", side="right", showgrid=False),
            barmode="group",
        )
    else:
        fig_var = empty_figure()

    fig_var.update_layout(**chart_layout(height=300))

    # Chart 5: Costo por lote (bar sorted)
    if costo_lote:
        sorted_costo = sorted(costo_lote, key=lambda x: x.get("costo_kg", 0), reverse=True)[:12]
        lotes_c = [f"{d.get('lote','')} ({d.get('finca','')})" for d in sorted_costo]
        costo_kg_vals = [d.get("costo_kg", 0) for d in sorted_costo]
        fig_costo = go.Figure(
            go.Bar(
                x=lotes_c,
                y=costo_kg_vals,
                marker_color="#8B6914",
                text=[f"${v:.3f}" for v in costo_kg_vals],
                textposition="outside",
            )
        )
    else:
        fig_costo = empty_figure()

    fig_costo.update_layout(**chart_layout(height=280))
    fig_costo.update_layout(yaxis_title="Costo/Kg ($)", showlegend=False)

    insights_comp = insights_panel("Insights de campo", insights)

    # Table
    if tabla:
        columns = [
            {"name": "Finca", "id": "finca"},
            {"name": "Lote", "id": "lote"},
            {"name": "Variedad", "id": "variedad"},
            {"name": "Hectáreas", "id": "hectareas", "type": "numeric"},
            {"name": "Prod. Est. (kg)", "id": "prod_estimada_kg", "type": "numeric"},
            {"name": "Prod. Real (kg)", "id": "prod_real_kg", "type": "numeric"},
            {"name": "Rend. (kg/ha)", "id": "rendimiento_kg_ha", "type": "numeric"},
            {"name": "Costo Total", "id": "costo_total", "type": "numeric"},
            {"name": "Estado", "id": "estado"},
        ]
        tabla_comp = render_table(tabla, columns, "campo-tabla-dt")
    else:
        tabla_comp = empty_state()

    return (
        kpi_row_1, kpi_row_2,
        fig_lote, fig_rend, fig_avance, fig_var, fig_costo,
        insights_comp, tabla_comp,
    )
