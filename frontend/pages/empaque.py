"""Empaque page."""
import dash
from dash import html, dcc, callback, Output, Input, State
import dash_bootstrap_components as dbc
import plotly.graph_objects as go

from frontend.components.drilldown import drilldown_chart_card
from frontend.components.filter_bar import bind_date_shortcuts, campaign_filter, date_range_filter, dropdown_filter, render_filter_bar
from frontend.components.kpi_card import kpi_card
from frontend.components.loading import loading_slot
from frontend.components.tables import render_table
from frontend.components.empty_state import empty_state
from frontend.components.header import render_header
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
    format_week_label,
    fmt_num,
    insights_panel,
    page_empty_outputs,
    page_failure_outputs,
    panel_filter_options,
    safe_callback,
    sanitize_dropdown_value,
    smart_bar_colors,
)

dash.register_page(__name__, path="/empaque", name="Empaque")
bind_date_shortcuts("empaque")

layout = html.Div(
    [
        render_header("Empaque", "Rendimiento y productividad del proceso de empaque", "Campaña 2024"),
        dcc.Store(id={"type": "panel-filters", "panel": "empaque"}, data={}),
        html.Div(
            [
                # Filter bar
                render_filter_bar(
                    [
                        campaign_filter("empaque-campaña", width="110px"),
                        date_range_filter("empaque", "2024-03-01", "2024-11-30"),
                        dropdown_filter("FINCA", "empaque-finca", fetch_options("fincas", "fincas"), width="150px"),
                        dropdown_filter("LOTE", "empaque-lote", fetch_options("lotes", "lotes"), width="130px"),
                        dropdown_filter("CALIBRE", "empaque-calibre", fetch_options("calibres", "calibres"), width="120px"),
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
                    ]
                ),
                # KPI rows
                html.Div(id="empaque-kpi-row-1", className="kpi-row"),
                html.Div(id="empaque-kpi-row-2", className="kpi-row"),
                html.Div(id="empaque-kpi-row-3", className="kpi-row"),
                # Charts row 1
                dbc.Row(
                    [
                        dbc.Col(
                            drilldown_chart_card(
                                "Conversión del proceso de empaque",
                                "empaque-chart-flujo",
                                "empaque",
                                "flujo_proceso",
                                subtitle="Del ingreso inicial al destino final para leer merma y aprovechamiento",
                            ),
                            width=5,
                        ),
                        dbc.Col(
                            drilldown_chart_card(
                                "Rendimiento exportable por lote",
                                "empaque-chart-lote",
                                "empaque",
                                "rendimiento_por_lote",
                                subtitle="Ranking operativo de los lotes que mejor convierten a exportación",
                                priority="primary",
                            ),
                            width=7,
                        ),
                    ],
                    className="g-3",
                ),
                # Charts row 2
                dbc.Row(
                    [
                        dbc.Col(
                            drilldown_chart_card(
                                "Rendimiento por calibre",
                                "empaque-chart-calibre",
                                "empaque",
                                "rendimiento_por_calibre",
                                subtitle="Relación entre volumen y calidad exportable por tamaño",
                            ),
                            width=4,
                        ),
                        dbc.Col(
                            drilldown_chart_card(
                                "Productividad por turno",
                                "empaque-chart-turno",
                                "empaque",
                                "productividad_turno",
                                subtitle="Cajas por hora según dotación y horas efectivas",
                            ),
                            width=4,
                        ),
                        dbc.Col(
                            drilldown_chart_card(
                                "Tasa exportable por finca",
                                "empaque-chart-finca",
                                "empaque",
                                "comparacion_fincas",
                                subtitle="Comparación de conversión por origen de fruta",
                            ),
                            width=4,
                        ),
                    ],
                    className="g-3",
                ),
                # Charts row 3
                dbc.Row(
                    [
                        dbc.Col(
                            drilldown_chart_card(
                                "Descarte semanal",
                                "empaque-chart-descarte",
                                "empaque",
                                "descarte_por_semana",
                                subtitle="Seguimiento de merma para detectar semanas con presión de calidad",
                            ),
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
    Output("empaque-campaña", "options"),
    Output("empaque-finca", "options"),
    Output("empaque-lote", "options"),
    Output("empaque-calibre", "options"),
    Output("empaque-turno", "options"),
    Output("empaque-linea", "options"),
    Output("empaque-calidad", "options"),
    Input("empaque-campaña", "value"),
    Input("empaque-fecha-desde", "date"),
    Input("empaque-fecha-hasta", "date"),
)
def update_empaque_filter_options(campaña, fecha_desde, fecha_hasta):
    options = panel_filter_options(
        "empaque",
        campaña=campaña,
        fecha_desde=fecha_desde,
        fecha_hasta=fecha_hasta,
    )
    return (
        build_options(options.get("campaña", []), all_label="Todas"),
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
@safe_callback(
    lambda: page_failure_outputs(
        "Empaque",
        kpi_blocks=3,
        chart_heights=[400, 430, 340, 340, 340, 360],
        insights_title="Insights de empaque",
    ),
    "empaque",
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
    request_error = data.get("_request_error")
    if request_error:
        return page_failure_outputs(
            "Empaque",
            kpi_blocks=3,
            chart_heights=[400, 430, 340, 340, 340, 360],
            insights_title="Insights de empaque",
            message=request_error,
        )

    kpis = data.get("kpis", {})
    flujo = data.get("flujo_proceso", [])
    rend_lote = data.get("rendimiento_por_lote", [])
    rend_calibre = data.get("rendimiento_por_calibre", [])
    prod_turno = data.get("productividad_turno", [])
    desc_semana = data.get("descarte_por_semana", [])
    comp_fincas = data.get("comparacion_fincas", [])
    tabla = data.get("tabla", [])
    insights = data.get("insights", [])

    if not any([flujo, rend_lote, rend_calibre, prod_turno, desc_semana, comp_fincas, tabla]):
        return page_empty_outputs(
            "Empaque",
            path="/empaque",
            kpi_blocks=3,
            chart_heights=[400, 430, 340, 340, 340, 360],
            insights_title="Insights de empaque",
            campaña=campaña,
        )

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

    # Chart 1: Flujo proceso
    if flujo:
        etapas = [d.get("etapa", "") for d in flujo]
        kg_vals = [d.get("kg", 0) for d in flujo]
        ingreso_base = kg_vals[0] if kg_vals else 0
        colors_flujo = [CHART_COLORS[0], CHART_COLORS[1], CHART_COLORS[2], CHART_COLORS[4]]
        fig_flujo = go.Figure(
            go.Bar(
                y=etapas,
                x=kg_vals,
                orientation="h",
                marker_color=colors_flujo[: len(etapas)],
                text=[f"{(v / ingreso_base * 100):.1f}%" if ingreso_base else "" for v in kg_vals],
                textposition="outside",
                customdata=[(v / ingreso_base * 100) if ingreso_base else 0 for v in kg_vals],
                hovertemplate="<b>%{y}</b><br>Kg: %{x:,.0f}<br>Participación: %{customdata:.1f}%<extra></extra>",
            )
        )
        if len(kg_vals) >= 2 and ingreso_base:
            merma_pct = max(0, 100 - (kg_vals[1] / ingreso_base * 100))
            add_metric_badge(fig_flujo, f"Merma total del proceso: {merma_pct:.1f}%", tone="warning")
    else:
        fig_flujo = empty_figure(height=400)

    fig_flujo.update_layout(**chart_layout(height=400, showlegend=False))
    fig_flujo.update_layout(
        showlegend=False,
        margin=dict(l=130, r=36, t=28, b=34),
        yaxis=dict(showgrid=False, showline=False),
        xaxis=dict(showgrid=True, gridcolor="rgba(65, 86, 61, 0.08)", title="Kg"),
    )

    # Chart 2: Rendimiento por lote
    if rend_lote:
        sorted_rl = sorted(rend_lote, key=lambda x: x.get("pct_exportable", 0), reverse=True)[:12]
        lotes_r = [f"{d.get('lote','')} ({d.get('finca','')})" for d in sorted_rl]
        pct_vals = [d.get("pct_exportable", 0) for d in sorted_rl]
        best_lote_idx = best_index(pct_vals) or 0
        fig_lote = go.Figure(
            go.Bar(
                y=lotes_r,
                x=pct_vals,
                orientation="h",
                customdata=[[d.get("pct_industria", 0), d.get("pct_descarte", 0)] for d in sorted_rl],
                marker_color=smart_bar_colors(pct_vals, highlight=best_lote_idx),
                text=[f"{v:.1f}%" for v in pct_vals],
                textposition="outside",
                hovertemplate="<b>%{y}</b><br>Exportable: %{x:.1f}%<br>Industria: %{customdata[0]:.1f}%<br>Descarte: %{customdata[1]:.1f}%<extra></extra>",
            )
        )
        fig_lote.add_vline(
            x=sum(pct_vals) / len(pct_vals),
            line_color=CHART_COLORS[2],
            line_dash="dot",
            annotation_text="promedio",
            annotation_position="top",
        )
        add_metric_badge(
            fig_lote,
            f"{sorted_rl[best_lote_idx]['lote']} convierte {pct_vals[best_lote_idx]:.1f}% a exportación",
            tone="primary",
        )
    else:
        fig_lote = empty_figure(height=430)

    fig_lote.update_layout(**chart_layout(height=430, emphasis="hero", showlegend=False))
    fig_lote.update_layout(
        xaxis_title="% exportable",
        margin=dict(l=182, r=28, t=28, b=34),
        yaxis=dict(showgrid=False, showline=False),
    )

    # Chart 3: Rendimiento por calibre
    if rend_calibre:
        calibres = [d.get("calibre", "") for d in rend_calibre]
        pct_c = [d.get("pct_exportable", 0) for d in rend_calibre]
        kg_total_calibre = [d.get("kg_total", 0) for d in rend_calibre]
        best_calibre_idx = best_index(pct_c) or 0
        fig_calibre = go.Figure(
            go.Bar(
                x=calibres,
                y=pct_c,
                customdata=kg_total_calibre,
                marker_color=smart_bar_colors(pct_c, highlight=best_calibre_idx),
                text=[f"{v:.1f}%" for v in pct_c],
                textposition="outside",
                hovertemplate="<b>Calibre %{x}</b><br>Exportable: %{y:.1f}%<br>Kg procesados: %{customdata:,.0f}<extra></extra>",
            )
        )
        add_reference_line(fig_calibre, sum(pct_c) / len(pct_c), "promedio")
        add_metric_badge(
            fig_calibre,
            f"Calibre {calibres[best_calibre_idx]} lidera con {pct_c[best_calibre_idx]:.1f}% exportable",
            tone="primary",
        )
    else:
        fig_calibre = empty_figure(height=340)

    fig_calibre.update_layout(**chart_layout(height=340, showlegend=False))
    fig_calibre.update_layout(yaxis_title="% Exportable", showlegend=False)

    # Chart 4: Productividad por turno
    if prod_turno:
        turnos = [d.get("turno", "") for d in prod_turno]
        cj_hora = [d.get("cajas_hora", 0) for d in prod_turno]
        horas_totales = [d.get("horas_totales", 0) for d in prod_turno]
        best_turno_idx = best_index(cj_hora) or 0
        fig_turno = go.Figure(
            go.Bar(
                x=turnos,
                y=cj_hora,
                customdata=horas_totales,
                marker_color=smart_bar_colors(cj_hora, positive=CHART_COLORS[2], neutral=CHART_COLORS[3], highlight=best_turno_idx),
                text=[f"{v:.1f}" for v in cj_hora],
                textposition="outside",
                hovertemplate="<b>%{x}</b><br>Cajas por hora: %{y:.1f}<br>Horas efectivas: %{customdata:,.0f}<extra></extra>",
            )
        )
        add_metric_badge(fig_turno, f"{turnos[best_turno_idx]} lidera la productividad", tone="primary")
    else:
        fig_turno = empty_figure(height=340)

    fig_turno.update_layout(**chart_layout(height=340, showlegend=False))
    fig_turno.update_layout(yaxis_title="Cajas/Hora", showlegend=False)

    # Chart 5: Exportable por finca
    if comp_fincas:
        sorted_fincas = sorted(comp_fincas, key=lambda item: item.get("pct_exportable", 0), reverse=True)
        fincas_c = [d.get("finca", "") for d in sorted_fincas]
        pct_f = [d.get("pct_exportable", 0) for d in sorted_fincas]
        kg_finca = [d.get("kg_ingresados", 0) for d in sorted_fincas]
        best_finca_idx = best_index(pct_f) or 0
        fig_finca = go.Figure(
            go.Bar(
                x=fincas_c,
                y=pct_f,
                customdata=kg_finca,
                marker_color=smart_bar_colors(pct_f, highlight=best_finca_idx),
                text=[f"{v:.1f}%" for v in pct_f],
                textposition="outside",
                hovertemplate="<b>%{x}</b><br>Exportable: %{y:.1f}%<br>Kg ingresados: %{customdata:,.0f}<extra></extra>",
            )
        )
        add_reference_line(fig_finca, sum(pct_f) / len(pct_f), "promedio")
        add_metric_badge(fig_finca, f"{fincas_c[best_finca_idx]} lidera la conversión", tone="primary")
    else:
        fig_finca = empty_figure(height=340)

    fig_finca.update_layout(**chart_layout(height=340, showlegend=False))
    fig_finca.update_layout(yaxis_title="% Exportable", showlegend=False)

    # Chart 6: Descarte por semana (line)
    if desc_semana:
        semanas = [format_week_label(d.get("semana", "")) for d in desc_semana]
        kg_desc_vals = [d.get("kg_descarte", 0) for d in desc_semana]
        peak_desc_idx = best_index(kg_desc_vals) or 0
        fig_desc = go.Figure(
            go.Scatter(
                x=semanas,
                y=kg_desc_vals,
                mode="lines+markers",
                name="Kg Descarte",
                line=dict(color=CHART_COLORS[4], width=2.7),
                marker=dict(size=7, color=CHART_COLORS[4]),
                fill="tozeroy",
                fillcolor="rgba(194,106,69,0.10)",
                hovertemplate="<b>%{x}</b><br>Kg descarte: %{y:,.0f}<extra></extra>",
            )
        )
        add_reference_line(fig_desc, sum(kg_desc_vals) / len(kg_desc_vals), "promedio")
        add_peak_annotation(
            fig_desc,
            semanas[peak_desc_idx],
            kg_desc_vals[peak_desc_idx],
            f"Pico {compact_number(kg_desc_vals[peak_desc_idx], ' kg')}",
        )
        add_metric_badge(fig_desc, f"Mayor presión de descarte en {semanas[peak_desc_idx]}", tone="danger")
    else:
        fig_desc = empty_figure(height=360)

    fig_desc.update_layout(**chart_layout(height=360, showlegend=False, unified_hover=True))
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
