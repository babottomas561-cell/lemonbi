import dash
import dash_bootstrap_components as dbc
import plotly.graph_objects as go
from dash import Input, Output, State, callback, dcc, html

from frontend.components.drilldown import chart_card
from frontend.components.empty_state import empty_state
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
    fmt_num,
    format_week_label,
    insights_panel,
    page_empty_outputs,
    page_failure_outputs,
    safe_callback,
    panel_filter_options,
)

dash.register_page(__name__, path="/contexto", name="Contexto Externo")
bind_date_shortcuts("contexto")


layout = html.Div(
    [
        render_header("Contexto Externo", "Tipo de cambio, clima y referencias de mercado", "Entorno de campaña"),
        dcc.Store(id={"type": "panel-filters", "panel": "contexto"}, data={}),
        html.Div(
            [
                render_filter_bar(
                    [
                        campaign_filter("contexto-campaña", width="110px"),
                        date_range_filter("contexto", "2024-03-01", "2024-11-30"),
                    ]
                ),
                html.Div(id="contexto-kpi-row-1", className="kpi-row"),
                html.Div(id="contexto-kpi-row-2", className="kpi-row"),
                dbc.Row(
                    [
                        dbc.Col(
                            chart_card(
                                "Evolución del dólar de referencia",
                                "contexto-chart-dolar",
                                subtitle="Trayectoria del tipo de cambio que condiciona competitividad y caja",
                                priority="primary",
                            ),
                            width=6,
                        ),
                        dbc.Col(
                            chart_card(
                                "Precio de referencia",
                                "contexto-chart-precio",
                                subtitle="Señal semanal del mercado para lectura de valor externo",
                            ),
                            width=6,
                        ),
                    ],
                    className="g-3",
                ),
                dbc.Row(
                    [
                        dbc.Col(
                            chart_card(
                                "Lluvia y temperatura",
                                "contexto-chart-clima",
                                subtitle="Cruce climático semanal para detectar semanas de mayor sensibilidad",
                            ),
                            width=8,
                        ),
                        dbc.Col(
                            chart_card(
                                "Índice de riesgo climático",
                                "contexto-chart-riesgo",
                                subtitle="Semanas que requieren mayor atención operativa",
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
    Output("contexto-campaña", "options"),
    Input("contexto-campaña", "value"),
    Input("contexto-fecha-desde", "date"),
    Input("contexto-fecha-hasta", "date"),
)
def update_contexto_filter_options(campaña, fecha_desde, fecha_hasta):
    options = panel_filter_options(
        "contexto",
        campaña=campaña,
        fecha_desde=fecha_desde,
        fecha_hasta=fecha_hasta,
    )
    return build_options(options.get("campaña", []), all_label="Todas")


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
@safe_callback(
    lambda: page_failure_outputs(
        "Contexto Externo",
        kpi_blocks=2,
        chart_heights=[410, 360, 400, 360],
        insights_title="Insights de contexto",
    ),
    "contexto",
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
    request_error = data.get("_request_error")
    if request_error:
        return page_failure_outputs(
            "Contexto Externo",
            kpi_blocks=2,
            chart_heights=[410, 360, 400, 360],
            insights_title="Insights de contexto",
            message=request_error,
        )

    kpis = data.get("kpis", {})
    evolucion_dolar = data.get("evolucion_dolar", [])
    lluvia_temperatura = data.get("lluvia_temperatura", [])
    precio_referencia = data.get("precio_referencia", [])
    tabla = data.get("tabla", [])
    insights = data.get("insights", [])

    if not any([evolucion_dolar, lluvia_temperatura, precio_referencia, tabla]):
        return page_empty_outputs(
            "Contexto Externo",
            path="/contexto",
            kpi_blocks=2,
            chart_heights=[410, 360, 400, 360],
            insights_title="Insights de contexto",
            campaña=campaña,
        )

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
        semanas_dolar = [format_week_label(item["fecha"]) for item in evolucion_dolar]
        dolar_vals = [item["dolar"] for item in evolucion_dolar]
        peak_dolar_idx = best_index(dolar_vals) or 0
        fig_dolar = go.Figure(
            go.Scatter(
                x=semanas_dolar,
                y=dolar_vals,
                mode="lines+markers",
                line=dict(color=CHART_COLORS[0], width=2.7),
                marker=dict(size=7, color=CHART_COLORS[0]),
                fill="tozeroy",
                fillcolor="rgba(63,107,75,0.12)",
                hovertemplate="<b>%{x}</b><br>Dólar de referencia: ARS %{y:,.2f}<extra></extra>",
            )
        )
        add_reference_line(fig_dolar, sum(dolar_vals) / len(dolar_vals), "promedio")
        add_peak_annotation(
            fig_dolar,
            semanas_dolar[peak_dolar_idx],
            dolar_vals[peak_dolar_idx],
            f"Máximo ARS {dolar_vals[peak_dolar_idx]:,.0f}",
        )
        add_metric_badge(fig_dolar, f"{semanas_dolar[peak_dolar_idx]} marcó el techo cambiario", tone="primary")
    else:
        fig_dolar = empty_figure(height=410)
    fig_dolar.update_layout(**chart_layout(height=410, emphasis="hero", showlegend=False, unified_hover=True))
    fig_dolar.update_layout(showlegend=False, yaxis_title="ARS/USD")

    if precio_referencia:
        semanas_precio = [format_week_label(item["fecha"]) for item in precio_referencia]
        precios = [item["precio_usd"] for item in precio_referencia]
        peak_precio_idx = best_index(precios) or 0
        fig_precio = go.Figure(
            go.Scatter(
                x=semanas_precio,
                y=precios,
                mode="lines+markers",
                line=dict(color=CHART_COLORS[2], width=2.6),
                marker=dict(size=7, color=CHART_COLORS[2]),
                hovertemplate="<b>%{x}</b><br>Precio de referencia: USD %{y:.3f}/kg<extra></extra>",
            )
        )
        add_peak_annotation(
            fig_precio,
            semanas_precio[peak_precio_idx],
            precios[peak_precio_idx],
            f"Pico USD {precios[peak_precio_idx]:.3f}/kg",
        )
    else:
        fig_precio = empty_figure(height=360)
    fig_precio.update_layout(**chart_layout(height=360, showlegend=False, unified_hover=True))
    fig_precio.update_layout(showlegend=False, yaxis_title="USD/kg")

    if lluvia_temperatura:
        semanas_clima = [format_week_label(item["fecha"]) for item in lluvia_temperatura]
        lluvia = [item["lluvia_mm"] for item in lluvia_temperatura]
        temp_min = [item["temp_min"] for item in lluvia_temperatura]
        temp_max = [item["temp_max"] for item in lluvia_temperatura]
        wettest_idx = best_index(lluvia) or 0
        fig_clima = go.Figure()
        fig_clima.add_trace(
            go.Bar(
                x=semanas_clima,
                y=lluvia,
                name="Lluvia",
                marker_color=CHART_COLORS[3],
                hovertemplate="<b>%{x}</b><br>Lluvia: %{y:.1f} mm<extra></extra>",
            )
        )
        fig_clima.add_trace(
            go.Scatter(
                x=semanas_clima,
                y=temp_min,
                name="Temp. mín.",
                mode="lines",
                line=dict(color=CHART_COLORS[0], width=2.2),
                hovertemplate="<b>%{x}</b><br>Temp. mín.: %{y:.1f} °C<extra></extra>",
                yaxis="y2",
            )
        )
        fig_clima.add_trace(
            go.Scatter(
                x=semanas_clima,
                y=temp_max,
                name="Temp. máx.",
                mode="lines",
                line=dict(color=CHART_COLORS[4], width=2.2),
                hovertemplate="<b>%{x}</b><br>Temp. máx.: %{y:.1f} °C<extra></extra>",
                yaxis="y2",
            )
        )
        fig_clima.update_layout(yaxis2=dict(overlaying="y", side="right", showgrid=False, title="°C"))
        add_metric_badge(fig_clima, f"{semanas_clima[wettest_idx]} fue la semana más lluviosa", tone="warning")
    else:
        fig_clima = empty_figure(height=400)
    fig_clima.update_layout(**chart_layout(height=400, unified_hover=True))
    fig_clima.update_layout(yaxis_title="mm")

    if tabla:
        semanas_riesgo = [format_week_label(item["fecha"]) for item in tabla]
        riesgo_vals = [item["indice_riesgo"] for item in tabla]
        risk_peak_idx = best_index(riesgo_vals) or 0
        fig_riesgo = go.Figure(
            go.Bar(
                x=semanas_riesgo,
                y=riesgo_vals,
                marker_color=[
                    CHART_COLORS[0] if value < 2 else CHART_COLORS[2] if value < 3.5 else CHART_COLORS[4]
                    for value in riesgo_vals
                ],
                text=[fmt_num(value, 2) for value in riesgo_vals],
                textposition="outside",
                hovertemplate="<b>%{x}</b><br>Índice de riesgo: %{y:.2f}<extra></extra>",
            )
        )
        add_reference_line(fig_riesgo, 3.0, "umbral alto", color=CHART_COLORS[4])
        add_peak_annotation(
            fig_riesgo,
            semanas_riesgo[risk_peak_idx],
            riesgo_vals[risk_peak_idx],
            f"Riesgo {riesgo_vals[risk_peak_idx]:.2f}",
        )
        add_metric_badge(fig_riesgo, f"{semanas_riesgo[risk_peak_idx]} mostró el mayor estrés climático", tone="danger")
    else:
        fig_riesgo = empty_figure(height=360)
    fig_riesgo.update_layout(**chart_layout(height=360, showlegend=False))
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
