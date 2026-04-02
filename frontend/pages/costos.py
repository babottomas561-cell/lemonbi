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
    add_donut_center_label,
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
    fmt_num,
    fmt_usd,
    insights_panel,
    page_empty_outputs,
    page_failure_outputs,
    panel_filter_options,
    safe_callback,
    sanitize_dropdown_value,
    smart_bar_colors,
)

dash.register_page(__name__, path="/costos", name="Costos y Rentabilidad")
bind_date_shortcuts("costos")


layout = html.Div(
    [
        render_header("Costos y Rentabilidad", "Costo por kilo, lote, finca y canal", "Módulo de rentabilidad"),
        dcc.Store(id={"type": "panel-filters", "panel": "costos"}, data={}),
        html.Div(
            [
                render_filter_bar(
                    [
                        campaign_filter("costos-campaña", width="110px"),
                        date_range_filter("costos", "2024-03-01", "2024-11-30"),
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
                            drilldown_chart_card(
                                "Margen comercial por canal",
                                "costos-chart-canal",
                                "costos",
                                "costo_por_canal",
                                subtitle="Rentabilidad comercial estimada por canal con criterio consistente frente a cliente y destino",
                                priority="primary",
                            ),
                            width=8,
                        ),
                        dbc.Col(
                            drilldown_chart_card(
                                "Composición del costo",
                                "costos-chart-composicion",
                                "costos",
                                "composicion_costo",
                                subtitle="Participación de campo, empaque, logística y estructura sobre el total",
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
                                "Costo unitario por lote",
                                "costos-chart-lote",
                                "costos",
                                "costo_por_lote",
                                subtitle="Lotes con mayor presión de costo por kilo exportable",
                                priority="primary",
                            ),
                            width=7,
                        ),
                        dbc.Col(
                            drilldown_chart_card(
                                "Costo por kg exportable por finca",
                                "costos-chart-finca",
                                "costos",
                                "costo_por_finca",
                                subtitle="Comparación entre fincas para detectar desvíos de eficiencia",
                            ),
                            width=5,
                        ),
                    ],
                    className="g-3",
                ),
                dbc.Row(
                    [
                        dbc.Col(
                            drilldown_chart_card(
                                "Margen comercial por cliente",
                                "costos-chart-cliente",
                                "costos",
                                "margen_por_cliente",
                                subtitle="Clientes que capturan o erosionan el margen comercial estimado",
                            ),
                            width=6,
                        ),
                        dbc.Col(
                            drilldown_chart_card(
                                "Margen comercial por destino final",
                                "costos-chart-destino",
                                "costos",
                                "margen_por_destino",
                                subtitle="Comparación ejecutiva entre exportación, mercado interno e industria con una base de margen homogénea",
                            ),
                            width=6,
                        ),
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
    Output("costos-campaña", "options"),
    Output("costos-finca", "options"),
    Output("costos-lote", "options"),
    Output("costos-centro", "options"),
    Output("costos-tipo", "options"),
    Output("costos-canal", "options"),
    Input("costos-campaña", "value"),
    Input("costos-fecha-desde", "date"),
    Input("costos-fecha-hasta", "date"),
)
def update_costos_filter_options(campaña, fecha_desde, fecha_hasta):
    options = panel_filter_options(
        "costos",
        campaña=campaña,
        fecha_desde=fecha_desde,
        fecha_hasta=fecha_hasta,
    )
    return (
        build_options(options.get("campaña", []), all_label="Todas"),
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
@safe_callback(
    lambda: page_failure_outputs(
        "Costos y Rentabilidad",
        kpi_blocks=2,
        chart_heights=[430, 360, 440, 420, 360, 340],
        insights_title="Insights de costos y rentabilidad",
    ),
    "costos",
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
    request_error = data.get("_request_error")
    if request_error:
        return page_failure_outputs(
            "Costos y Rentabilidad",
            kpi_blocks=2,
            chart_heights=[430, 360, 440, 420, 360, 340],
            insights_title="Insights de costos y rentabilidad",
            message=request_error,
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

    if not any([composicion, costo_por_finca, costo_por_lote, costo_por_canal, margen_por_cliente, margen_por_destino, tabla]):
        return page_empty_outputs(
            "Costos y Rentabilidad",
            path="/costos",
            kpi_blocks=2,
            chart_heights=[430, 360, 440, 420, 360, 340],
            insights_title="Insights de costos y rentabilidad",
            campaña=campaña,
        )

    mejor_lote_item = min(costo_por_lote, key=lambda item: item.get("costo_kg", float("inf"))) if costo_por_lote else None
    promedio_lote = sum(item.get("costo_kg", 0) for item in costo_por_lote) / len(costo_por_lote) if costo_por_lote else 0
    mejora_lote_pct = ((promedio_lote - mejor_lote_item.get("costo_kg", 0)) / promedio_lote * 100) if mejor_lote_item and promedio_lote else 0
    texto_mejora_lote = (
        f"{mejora_lote_pct:.1f}% debajo del promedio"
        if mejora_lote_pct >= 0
        else f"{abs(mejora_lote_pct):.1f}% por encima del promedio"
    ) if mejor_lote_item else ""

    mejor_canal_item = max(costo_por_canal, key=lambda item: item.get("margen_pct", float("-inf"))) if costo_por_canal else None
    promedio_canal = sum(item.get("margen_pct", 0) for item in costo_por_canal) / len(costo_por_canal) if costo_por_canal else 0
    mejora_canal_pp = (mejor_canal_item.get("margen_pct", 0) - promedio_canal) if mejor_canal_item else 0
    texto_mejora_canal = f"{mejora_canal_pp:+.1f} pp vs promedio" if mejor_canal_item else ""

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
            dbc.Col(
                kpi_card(
                    "Lote más eficiente",
                    mejor_lote_item.get("lote", "-") if mejor_lote_item else "-",
                    accent="amber",
                    subtitle=(
                        f"ARS {mejor_lote_item.get('costo_kg', 0):,.1f}/kg en {mejor_lote_item.get('finca', '-')}"
                        if mejor_lote_item
                        else ""
                    ),
                    delta=texto_mejora_lote,
                    delta_type="positive" if mejora_lote_pct >= 0 else "negative",
                    drill_panel="costos",
                    drill_item="mejor_lote",
                ),
                width=3,
            ),
            dbc.Col(
                kpi_card(
                    "Canal más rentable",
                    mejor_canal_item.get("canal", "-") if mejor_canal_item else "-",
                    accent="blue",
                    subtitle=(
                        f"Margen {mejor_canal_item.get('margen_pct', 0):,.1f}%"
                        if mejor_canal_item
                        else ""
                    ),
                    delta=texto_mejora_canal,
                    delta_type="positive" if mejora_canal_pp >= 0 else "negative",
                    drill_panel="costos",
                    drill_item="mejor_canal",
                ),
                width=3,
            ),
        ],
        className="g-3",
    )

    if composicion:
        labels = [item["tipo"] for item in composicion]
        values = [item["importe"] for item in composicion]
        top_cc_idx = best_index(values) or 0
        composition_colors = [
            CHART_COLORS[0] if label == "Empaque" else
            CHART_COLORS[1] if label == "Campo" else
            CHART_COLORS[2] if label == "Logística" else
            CHART_COLORS[5] if label == "Administración" else
            "rgba(120, 133, 106, 0.55)"
            for label in labels
        ]
        fig_composicion = go.Figure(
            go.Pie(
                labels=labels,
                values=values,
                hole=0.68,
                marker=dict(colors=composition_colors, line=dict(color="rgba(255,252,247,0.9)", width=2)),
                textinfo="none",
                sort=False,
                hovertemplate="<b>%{label}</b><br>Importe: ARS %{value:,.0f}<br>Participación: %{percent}<extra></extra>",
            )
        )
        add_donut_center_label(
            fig_composicion,
            f"ARS {fmt_num(kpis.get('costo_total_kg_exportado', 0), 1)}",
            "costo total / kg",
        )
        add_metric_badge(
            fig_composicion,
            f"{labels[top_cc_idx]} explica {composicion[top_cc_idx]['pct']:.1f}% del costo total",
            tone="warning",
        )
        composicion_layout = chart_layout(height=430, showlegend=True)
        composicion_layout["margin"] = dict(l=8, r=8, t=16, b=8)
        fig_composicion.update_layout(
            **composicion_layout,
            legend=dict(orientation="v", x=1.0, y=0.5, yanchor="middle", font=dict(size=11)),
        )
    else:
        fig_composicion = empty_figure(height=430)

    if costo_por_finca:
        finca_sorted = sorted(costo_por_finca, key=lambda item: item.get("costo_kg", 0), reverse=True)
        fincas = [item["finca"] for item in finca_sorted]
        costos_finca = [item["costo_kg"] for item in finca_sorted]
        highest_finca_idx = best_index(costos_finca) or 0
        fig_finca = go.Figure(
            go.Bar(
                y=fincas,
                x=costos_finca,
                orientation="h",
                marker_color=[CHART_COLORS[0] if idx == highest_finca_idx else CHART_COLORS[5] for idx, _ in enumerate(fincas)],
                text=[f"ARS {value:,.1f}" for value in costos_finca],
                textposition="outside",
                hovertemplate="<b>%{y}</b><br>Costo unitario: ARS %{x:,.1f}/kg<extra></extra>",
            )
        )
        fig_finca.add_vline(
            x=sum(costos_finca) / len(costos_finca),
            line_color=CHART_COLORS[5],
            line_dash="dot",
            annotation_text="promedio",
            annotation_position="top",
        )
        add_metric_badge(fig_finca, f"{fincas[highest_finca_idx]} tiene el mayor costo por kg", tone="warning")
    else:
        fig_finca = empty_figure(height=360)
    fig_finca.update_layout(**chart_layout(height=360, showlegend=False))
    fig_finca.update_layout(
        showlegend=False,
        xaxis_title="ARS/kg",
        margin=dict(l=170, r=22, t=24, b=32),
        yaxis=dict(showgrid=False, showline=False),
    )

    if costo_por_canal:
        canales_sorted = sorted(costo_por_canal, key=lambda item: item["margen_pct"], reverse=True)
        canales = [item["canal"] for item in canales_sorted]
        margenes = [item["margen_pct"] for item in canales_sorted]
        ingresos = [item["ingreso_usd"] for item in canales_sorted]
        best_canal_idx = best_index(margenes) or 0
        canales_negativos = sum(1 for value in margenes if value < 0)
        fig_canal = go.Figure(
            go.Bar(
                y=canales,
                x=margenes,
                orientation="h",
                customdata=ingresos,
                marker_color=[
                    CHART_COLORS[0] if value >= 0 and idx == best_canal_idx else
                    CHART_COLORS[1] if value >= 0 else
                    CHART_COLORS[4]
                    for idx, value in enumerate(margenes)
                ],
                text=[f"{value:.1f}%" for value in margenes],
                textposition="outside",
                hovertemplate="<b>%{y}</b><br>Margen: %{x:.1f}%<br>Ingreso: USD %{customdata:,.0f}<extra></extra>",
            )
        )
        fig_canal.add_vline(
            x=0,
            line_color=CHART_COLORS[5],
            line_dash="solid",
            annotation_text="punto de equilibrio",
            annotation_position="top",
        )
        add_metric_badge(
            fig_canal,
            (
                f"{canales[best_canal_idx]} lidera con {margenes[best_canal_idx]:.1f}%; {canales_negativos} canal(es) siguen en negativo"
                if canales_negativos
                else f"{canales[best_canal_idx]} es el canal más rentable"
            ),
            tone="primary" if not canales_negativos else "warning",
        )
    else:
        fig_canal = empty_figure(height=440)
    fig_canal.update_layout(**chart_layout(height=440, emphasis="hero", showlegend=False))
    fig_canal.update_layout(
        showlegend=False,
        xaxis_title="Margen %",
        margin=dict(l=210, r=32, t=26, b=34),
        yaxis=dict(showgrid=False, showline=False),
    )

    if costo_por_lote:
        top = sorted(costo_por_lote, key=lambda item: item.get("costo_kg", 0), reverse=True)[:12]
        lotes_top = [f"{item['lote']} ({item['finca']})" for item in top]
        costo_unit = [item["costo_kg"] for item in top]
        worst_lote_idx = best_index(costo_unit) or 0
        fig_lote = go.Figure(
            go.Bar(
                y=lotes_top,
                x=costo_unit,
                orientation="h",
                marker_color=[CHART_COLORS[0] if idx == worst_lote_idx else CHART_COLORS[5] for idx, _ in enumerate(lotes_top)],
                text=[f"ARS {value:,.1f}" for value in costo_unit],
                textposition="outside",
                hovertemplate="<b>%{y}</b><br>Costo unitario: ARS %{x:,.1f}/kg<extra></extra>",
            )
        )
        fig_lote.add_vline(
            x=sum(costo_unit) / len(costo_unit),
            line_color=CHART_COLORS[2],
            line_dash="dot",
            annotation_text="promedio",
            annotation_position="top",
        )
        sobre_promedio_lote = ((costo_unit[worst_lote_idx] - (sum(costo_unit) / len(costo_unit))) / (sum(costo_unit) / len(costo_unit)) * 100) if costo_unit else 0
        add_metric_badge(
            fig_lote,
            f"{top[worst_lote_idx]['lote']} está {sobre_promedio_lote:.1f}% por encima del promedio",
            tone="warning",
        )
    else:
        fig_lote = empty_figure(height=420)
    fig_lote.update_layout(**chart_layout(height=420, emphasis="hero", showlegend=False))
    fig_lote.update_layout(
        showlegend=False,
        margin=dict(l=182, r=25, t=26, b=34),
        xaxis_title="ARS/kg",
        yaxis=dict(showgrid=False, showline=False),
    )

    if margen_por_cliente:
        top_clientes = margen_por_cliente[:10]
        clientes = [item["cliente"] for item in top_clientes]
        margenes_cliente = [item["margen_pct"] for item in top_clientes]
        ingresos_cliente = [item["ingreso_usd"] for item in top_clientes]
        best_cliente_idx = best_index(margenes_cliente) or 0
        fig_cliente = go.Figure(
            go.Bar(
                x=clientes,
                y=margenes_cliente,
                customdata=ingresos_cliente,
                marker_color=smart_bar_colors(margenes_cliente, highlight=best_cliente_idx),
                text=[f"{value:.1f}%" for value in margenes_cliente],
                textposition="outside",
                hovertemplate="<b>%{x}</b><br>Margen: %{y:.1f}%<br>Ingreso: USD %{customdata:,.0f}<extra></extra>",
            )
        )
        add_reference_line(fig_cliente, sum(margenes_cliente) / len(margenes_cliente), "promedio")
        add_metric_badge(fig_cliente, f"{clientes[best_cliente_idx]} es el cliente más rentable", tone="primary")
    else:
        fig_cliente = empty_figure(height=360)
    fig_cliente.update_layout(**chart_layout(height=360, showlegend=False))
    fig_cliente.update_layout(showlegend=False, yaxis_title="%")

    if margen_por_destino:
        destinos = [item["destino"] for item in margen_por_destino]
        margenes_destino = [item["margen_pct"] for item in margen_por_destino]
        best_destino_idx = best_index(margenes_destino) or 0
        fig_destino = go.Figure(
            go.Bar(
                x=destinos,
                y=margenes_destino,
                marker_color=smart_bar_colors(margenes_destino, highlight=best_destino_idx),
                text=[f"{value:.1f}%" for value in margenes_destino],
                textposition="outside",
                hovertemplate="<b>%{x}</b><br>Margen: %{y:.1f}%<extra></extra>",
            )
        )
        add_metric_badge(fig_destino, f"{destinos[best_destino_idx]} captura el mejor margen del mix", tone="primary")
    else:
        fig_destino = empty_figure(height=340)
    fig_destino.update_layout(**chart_layout(height=340, showlegend=False))
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
