"""Campo page."""
import dash
from dash import html, dcc, callback, Output, Input, State
import dash_bootstrap_components as dbc
import plotly.graph_objects as go

from frontend.components.drilldown import chart_card
from frontend.components.filter_bar import bind_date_shortcuts, campaign_filter, date_range_filter, dropdown_filter, render_filter_bar
from frontend.components.kpi_card import kpi_card
from frontend.components.loading import loading_slot
from frontend.components.tables import render_table
from frontend.components.empty_state import empty_state
from frontend.components.header import render_header
from frontend.utils import (
    CHART_COLORS,
    add_metric_badge,
    add_reference_line,
    api_get,
    best_index,
    build_options,
    chart_layout,
    compact_number,
    empty_figure,
    fetch_options,
    filter_params,
    fmt_ars,
    fmt_num,
    insights_panel,
    page_empty_outputs,
    page_failure_outputs,
    panel_filter_options,
    safe_callback,
    sanitize_dropdown_value,
    smart_bar_colors,
)

dash.register_page(__name__, path="/campo", name="Campo")
bind_date_shortcuts("campo")

layout = html.Div(
    [
        render_header("Campo", "Producción y cosecha por lote y finca", "Campaña 2024"),
        dcc.Store(id={"type": "panel-filters", "panel": "campo"}, data={}),
        html.Div(
            [
                # Filter bar
                render_filter_bar(
                    [
                        campaign_filter("campo-campaña", width="110px"),
                        date_range_filter("campo", "2024-03-01", "2024-11-30"),
                        dropdown_filter("FINCA", "campo-finca", fetch_options("fincas", "fincas"), width="160px"),
                        dropdown_filter("VARIEDAD", "campo-variedad", fetch_options("variedades", "variedades"), width="130px"),
                        dropdown_filter("LOTE", "campo-lote", fetch_options("lotes", "lotes"), width="130px"),
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
                    ]
                ),
                # KPI rows
                html.Div(id="campo-kpi-row-1", className="kpi-row"),
                html.Div(id="campo-kpi-row-2", className="kpi-row"),
                # Charts row 1
                dbc.Row(
                    [
                        dbc.Col(
                            chart_card(
                                "Top lotes por producción",
                                "campo-chart-lote",
                                subtitle="Ranking de volumen cosechado para detectar concentración operativa",
                                priority="primary",
                            ),
                            width=7,
                        ),
                        dbc.Col(
                            chart_card(
                                "Rendimiento por hectárea por finca",
                                "campo-chart-rendimiento",
                                subtitle="Comparación directa del rinde medio para lectura agronómica rápida",
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
                            chart_card(
                                "Cobertura de cosecha por finca",
                                "campo-chart-avance",
                                subtitle="Cosechado vs pendiente para ubicar el foco operativo del cierre",
                            ),
                            width=6,
                        ),
                        dbc.Col(
                            chart_card(
                                "Volumen y rinde por variedad",
                                "campo-chart-variedades",
                                subtitle="Peso de cada variedad y su productividad promedio en la campaña",
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
                            chart_card(
                                "Top lotes por costo unitario",
                                "campo-chart-costo",
                                subtitle="Costo por kilo cosechado para priorizar lotes bajo presión",
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
    Output("campo-campaña", "options"),
    Output("campo-finca", "options"),
    Output("campo-variedad", "options"),
    Output("campo-lote", "options"),
    Output("campo-estado", "options"),
    Output("campo-encargado", "options"),
    Input("campo-campaña", "value"),
    Input("campo-fecha-desde", "date"),
    Input("campo-fecha-hasta", "date"),
)
def update_campo_filter_options(campaña, fecha_desde, fecha_hasta):
    options = panel_filter_options(
        "campo",
        campaña=campaña,
        fecha_desde=fecha_desde,
        fecha_hasta=fecha_hasta,
    )
    return (
        build_options(options.get("campaña", []), all_label="Todas"),
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
@safe_callback(
    lambda: page_failure_outputs(
        "Campo",
        kpi_blocks=2,
        chart_heights=[430, 360, 360, 360, 380],
        insights_title="Insights de campo",
    ),
    "campo",
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
    request_error = data.get("_request_error")
    if request_error:
        return page_failure_outputs(
            "Campo",
            kpi_blocks=2,
            chart_heights=[430, 360, 360, 360, 380],
            insights_title="Insights de campo",
            message=request_error,
        )

    kpis = data.get("kpis", {})
    prod_por_lote = data.get("produccion_por_lote", [])
    rend_por_finca = data.get("rendimiento_por_finca", [])
    avance_finca = data.get("avance_por_finca", [])
    comp_variedades = data.get("comparacion_variedades", [])
    costo_lote = data.get("costo_por_lote", [])
    tabla = data.get("tabla", [])
    insights = data.get("insights", [])

    if not any([prod_por_lote, rend_por_finca, avance_finca, comp_variedades, costo_lote, tabla]):
        return page_empty_outputs(
            "Campo",
            path="/campo",
            kpi_blocks=2,
            chart_heights=[430, 360, 360, 360, 380],
            insights_title="Insights de campo",
            campaña=campaña,
        )

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

    # Chart 1: Producción por lote
    if prod_por_lote:
        sorted_lotes = sorted(prod_por_lote, key=lambda x: x.get("kg_cosechados", 0), reverse=True)[:15]
        lotes = [f"{d.get('lote','')} ({d.get('finca','')})" for d in sorted_lotes]
        kg_vals = [d.get("kg_cosechados", 0) for d in sorted_lotes]
        leader_idx = best_index(kg_vals) or 0
        fig_lote = go.Figure(
            go.Bar(
                y=lotes,
                x=kg_vals,
                orientation="h",
                marker_color=smart_bar_colors(kg_vals, highlight=leader_idx),
                text=[compact_number(v, " kg") for v in kg_vals],
                textposition="outside",
                hovertemplate="<b>%{y}</b><br>Kg cosechados: %{x:,.0f}<extra></extra>",
            )
        )
        promedio_top = sum(kg_vals) / len(kg_vals)
        fig_lote.add_vline(
            x=promedio_top,
            line_color=CHART_COLORS[2],
            line_dash="dot",
            annotation_text="promedio top lotes",
            annotation_position="top",
        )
        add_metric_badge(
            fig_lote,
            f"{sorted_lotes[leader_idx]['lote']} lidera con {compact_number(kg_vals[leader_idx], ' kg')}",
            tone="primary",
        )
    else:
        fig_lote = empty_figure(height=430)

    fig_lote.update_layout(**chart_layout(height=430, emphasis="hero", showlegend=False))
    fig_lote.update_layout(
        xaxis_title="Kg Cosechados",
        margin=dict(l=182, r=34, t=28, b=34),
        yaxis=dict(showgrid=False, showline=False),
    )

    # Chart 2: Rendimiento por finca
    if rend_por_finca:
        fincas_r = [d.get("finca", "") for d in rend_por_finca]
        rend_vals = [d.get("rendimiento_promedio_kg_ha", 0) for d in rend_por_finca]
        best_rinde_idx = best_index(rend_vals) or 0
        fig_rend = go.Figure(
            go.Bar(
                x=fincas_r,
                y=rend_vals,
                marker_color=smart_bar_colors(rend_vals, highlight=best_rinde_idx),
                text=[compact_number(v, " kg/ha") for v in rend_vals],
                textposition="outside",
                hovertemplate="<b>%{x}</b><br>Rendimiento promedio: %{y:,.0f} kg/ha<extra></extra>",
            )
        )
        add_reference_line(fig_rend, sum(rend_vals) / len(rend_vals), "promedio")
        add_metric_badge(
            fig_rend,
            f"{fincas_r[best_rinde_idx]} rinde {compact_number(rend_vals[best_rinde_idx], ' kg/ha')}",
            tone="primary",
        )
    else:
        fig_rend = empty_figure(height=360)

    fig_rend.update_layout(**chart_layout(height=360, showlegend=False))
    fig_rend.update_layout(yaxis_title="kg/ha", showlegend=False)

    # Chart 3: Avance cosecha por finca
    if avance_finca:
        fincas_a = [d.get("finca", "") for d in avance_finca]
        kg_cos = [d.get("kg_cosechados", 0) for d in avance_finca]
        kg_pend = [d.get("kg_pendientes", 0) for d in avance_finca]
        pct_avance = [d.get("pct_avance", 0) for d in avance_finca]
        laggard_idx = best_index(pct_avance, reverse=True) or 0
        fig_avance = go.Figure()
        fig_avance.add_trace(
            go.Bar(
                name="Cosechado",
                x=fincas_a,
                y=kg_cos,
                marker_color=CHART_COLORS[0],
                hovertemplate="<b>%{x}</b><br>Kg cosechados: %{y:,.0f}<extra></extra>",
            )
        )
        fig_avance.add_trace(
            go.Bar(
                name="Pendiente",
                x=fincas_a,
                y=kg_pend,
                marker_color=CHART_COLORS[2],
                hovertemplate="<b>%{x}</b><br>Kg pendientes: %{y:,.0f}<extra></extra>",
            )
        )
        fig_avance.update_layout(barmode="stack")
        add_metric_badge(
            fig_avance,
            f"{fincas_a[laggard_idx]} cierra con {pct_avance[laggard_idx]:.1f}% de avance",
            tone="warning",
        )
    else:
        fig_avance = empty_figure(height=360)

    fig_avance.update_layout(**chart_layout(height=360, showlegend=True, unified_hover=True))
    fig_avance.update_layout(yaxis_title="Kg")

    # Chart 4: Comparación entre variedades
    if comp_variedades:
        variedades_c = [d.get("variedad", "") for d in comp_variedades]
        kg_total = [d.get("kg_total", 0) for d in comp_variedades]
        rend_prom = [d.get("rendimiento_promedio", 0) for d in comp_variedades]
        top_var_idx = best_index(rend_prom) or 0
        fig_var = go.Figure()
        fig_var.add_trace(
            go.Bar(
                name="Kg total",
                x=variedades_c,
                y=kg_total,
                marker_color=CHART_COLORS[1],
                hovertemplate="<b>%{x}</b><br>Volumen: %{y:,.0f} kg<extra></extra>",
                yaxis="y",
            )
        )
        fig_var.add_trace(
            go.Scatter(
                name="Rinde promedio",
                x=variedades_c,
                y=rend_prom,
                mode="lines+markers",
                marker=dict(size=9, color=CHART_COLORS[2]),
                line=dict(color=CHART_COLORS[2], width=2.5),
                hovertemplate="<b>%{x}</b><br>Rinde promedio: %{y:,.0f} kg/ha<extra></extra>",
                yaxis="y2",
            )
        )
        fig_var.update_layout(
            yaxis2=dict(overlaying="y", side="right", showgrid=False, title="kg/ha"),
        )
        add_metric_badge(
            fig_var,
            f"{variedades_c[top_var_idx]} lidera el rinde con {compact_number(rend_prom[top_var_idx], ' kg/ha')}",
            tone="primary",
        )
    else:
        fig_var = empty_figure(height=360)

    fig_var.update_layout(**chart_layout(height=360, showlegend=True, unified_hover=True))
    fig_var.update_layout(yaxis_title="Kg")

    # Chart 5: Costo por lote
    if costo_lote:
        sorted_costo = sorted(costo_lote, key=lambda x: x.get("costo_kg", 0), reverse=True)[:12]
        lotes_c = [f"{d.get('lote','')} ({d.get('finca','')})" for d in sorted_costo]
        costo_kg_vals = [d.get("costo_kg", 0) for d in sorted_costo]
        worst_cost_idx = best_index(costo_kg_vals) or 0
        fig_costo = go.Figure(
            go.Bar(
                y=lotes_c,
                x=costo_kg_vals,
                orientation="h",
                marker_color=smart_bar_colors(costo_kg_vals, positive=CHART_COLORS[4], neutral=CHART_COLORS[2], highlight=worst_cost_idx),
                text=[f"ARS {v:,.1f}/kg" for v in costo_kg_vals],
                textposition="outside",
                hovertemplate="<b>%{y}</b><br>Costo unitario: ARS %{x:,.1f}/kg<extra></extra>",
            )
        )
        fig_costo.add_vline(
            x=sum(costo_kg_vals) / len(costo_kg_vals),
            line_color=CHART_COLORS[2],
            line_dash="dot",
            annotation_text="promedio lotes críticos",
            annotation_position="top",
        )
        add_metric_badge(
            fig_costo,
            f"{sorted_costo[worst_cost_idx]['lote']} concentra el mayor costo unitario",
            tone="danger",
        )
    else:
        fig_costo = empty_figure(height=380)

    fig_costo.update_layout(**chart_layout(height=380, showlegend=False))
    fig_costo.update_layout(
        xaxis_title="ARS/kg",
        margin=dict(l=182, r=28, t=26, b=34),
        yaxis=dict(showgrid=False, showline=False),
    )

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
