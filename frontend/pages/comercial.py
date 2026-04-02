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

dash.register_page(__name__, path="/comercial", name="Comercial")
bind_date_shortcuts("comercial")


layout = html.Div(
    [
        render_header("Comercial", "Ventas, clientes, precios y canales", "Panel conectado al backend"),
        dcc.Store(id={"type": "panel-filters", "panel": "comercial"}, data={}),
        html.Div(
            [
                render_filter_bar(
                    [
                        campaign_filter("comercial-campaña", width="110px"),
                        date_range_filter("comercial", "2024-03-01", "2024-11-30"),
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
                            drilldown_chart_card(
                                "Top clientes por facturación",
                                "comercial-chart-clientes",
                                "comercial",
                                "ventas_por_cliente",
                                subtitle="Clientes que concentran el valor vendido en el período filtrado",
                                priority="primary",
                            ),
                            width=7,
                        ),
                        dbc.Col(
                            drilldown_chart_card(
                                "Mix de ingresos por destino",
                                "comercial-chart-destino",
                                "comercial",
                                "ventas_por_destino",
                                subtitle="Participación relativa entre exportación, interno e industria",
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
                                "Precio promedio por calibre",
                                "comercial-chart-calibre",
                                "comercial",
                                "precio_por_calibre",
                                subtitle="Escalera de precios para entender prima comercial por tamaño",
                            ),
                            width=4,
                        ),
                        dbc.Col(
                            drilldown_chart_card(
                                "Margen por canal",
                                "comercial-chart-canal",
                                "comercial",
                                "margen_por_canal",
                                subtitle="Comparación de rentabilidad para decidir foco comercial",
                            ),
                            width=4,
                        ),
                        dbc.Col(
                            drilldown_chart_card(
                                "Top clientes: valor vs margen",
                                "comercial-chart-top",
                                "comercial",
                                "top_clientes",
                                subtitle="Cruce de facturación y margen para detectar cuentas premium",
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
                                "Evolución mensual de ventas",
                                "comercial-chart-evolucion",
                                "comercial",
                                "evolucion_ventas",
                                subtitle="Facturación y kilos vendidos para leer ritmo comercial de la campaña",
                                priority="primary",
                            ),
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
    Output("comercial-campaña", "options"),
    Output("comercial-cliente", "options"),
    Output("comercial-destino", "options"),
    Output("comercial-canal", "options"),
    Output("comercial-moneda", "options"),
    Input("comercial-campaña", "value"),
    Input("comercial-fecha-desde", "date"),
    Input("comercial-fecha-hasta", "date"),
)
def update_comercial_filter_options(campaña, fecha_desde, fecha_hasta):
    options = panel_filter_options(
        "comercial",
        campaña=campaña,
        fecha_desde=fecha_desde,
        fecha_hasta=fecha_hasta,
    )
    return (
        build_options(options.get("campaña", []), all_label="Todas"),
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
@safe_callback(
    lambda: page_failure_outputs(
        "Comercial",
        kpi_blocks=2,
        chart_heights=[430, 430, 340, 340, 340, 420],
        insights_title="Insights comerciales",
    ),
    "comercial",
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
    request_error = data.get("_request_error")
    if request_error:
        return page_failure_outputs(
            "Comercial",
            kpi_blocks=2,
            chart_heights=[430, 430, 340, 340, 340, 420],
            insights_title="Insights comerciales",
            message=request_error,
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

    if not any([ventas_por_cliente, ventas_por_destino, precio_por_calibre, evolucion, top_clientes, margen_por_canal, tabla]):
        return page_empty_outputs(
            "Comercial",
            path="/comercial",
            kpi_blocks=2,
            chart_heights=[430, 430, 340, 340, 340, 420],
            insights_title="Insights comerciales",
            campaña=campaña,
        )

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
        clientes = [item["cliente"] for item in top]
        importes = [item["importe_usd"] for item in top]
        kilos = [item["kg"] for item in top]
        leader_idx = best_index(importes) or 0
        fig_clientes = go.Figure(
            go.Bar(
                y=clientes,
                x=importes,
                orientation="h",
                customdata=kilos,
                marker_color=smart_bar_colors(importes, highlight=leader_idx),
                text=[fmt_usd(value) for value in importes],
                textposition="outside",
                hovertemplate="<b>%{y}</b><br>Ventas: USD %{x:,.0f}<br>Kg vendidos: %{customdata:,.0f}<extra></extra>",
            )
        )
        fig_clientes.add_vline(
            x=sum(importes) / len(importes),
            line_color=CHART_COLORS[2],
            line_dash="dot",
            annotation_text="promedio top clientes",
            annotation_position="top",
        )
        add_metric_badge(
            fig_clientes,
            f"{clientes[leader_idx]} lidera con {fmt_usd(importes[leader_idx])}",
            tone="primary",
        )
    else:
        fig_clientes = empty_figure(height=430)
    fig_clientes.update_layout(**chart_layout(height=430, emphasis="hero", showlegend=False))
    fig_clientes.update_layout(
        margin=dict(l=190, r=30, t=28, b=34),
        showlegend=False,
        xaxis_title="USD",
        yaxis=dict(showgrid=False, showline=False),
    )

    if ventas_por_destino:
        dest_labels = [item["destino"] for item in ventas_por_destino]
        dest_values = [item["importe_usd"] for item in ventas_por_destino]
        fig_destino = go.Figure(
            go.Pie(
                labels=dest_labels,
                values=dest_values,
                hole=0.55,
                marker=dict(colors=CHART_COLORS[: len(ventas_por_destino)]),
                textinfo="percent",
                hovertemplate="<b>%{label}</b><br>Ventas: USD %{value:,.0f}<br>Participación: %{percent}<extra></extra>",
            )
        )
        add_donut_center_label(fig_destino, dest_labels[0], "destino líder")
        destino_layout = chart_layout(height=430, showlegend=True)
        destino_layout["margin"] = dict(l=10, r=10, t=10, b=10)
        fig_destino.update_layout(
            **destino_layout,
            legend=dict(orientation="v", x=1.02, y=0.5, yanchor="middle"),
        )
    else:
        fig_destino = empty_figure(height=430)

    if precio_por_calibre:
        calibres = [item["calibre"] for item in precio_por_calibre]
        precios = [item["precio_promedio_usd"] for item in precio_por_calibre]
        best_calibre_idx = best_index(precios) or 0
        fig_calibre = go.Figure(
            go.Scatter(
                x=calibres,
                y=precios,
                mode="lines+markers",
                marker=dict(size=9, color=CHART_COLORS[2]),
                line=dict(color=CHART_COLORS[2], width=2.6),
                fill="tozeroy",
                fillcolor="rgba(182,146,69,0.10)",
                hovertemplate="<b>Calibre %{x}</b><br>Precio promedio: USD %{y:.3f}/kg<extra></extra>",
            )
        )
        add_peak_annotation(
            fig_calibre,
            calibres[best_calibre_idx],
            precios[best_calibre_idx],
            f"Prima máxima USD {precios[best_calibre_idx]:.3f}/kg",
        )
        add_metric_badge(fig_calibre, f"Calibre {calibres[best_calibre_idx]} concentra el mayor precio", tone="warning")
    else:
        fig_calibre = empty_figure(height=340)
    fig_calibre.update_layout(**chart_layout(height=340, showlegend=False, unified_hover=True))
    fig_calibre.update_layout(showlegend=False, yaxis_title="USD/kg")

    if margen_por_canal:
        canales_sorted = sorted(margen_por_canal, key=lambda item: item["margen_pct"], reverse=True)
        canales = [item["canal"] for item in canales_sorted]
        margenes = [item["margen_pct"] for item in canales_sorted]
        importes_canal = [item["importe_usd"] for item in canales_sorted]
        best_canal_idx = best_index(margenes) or 0
        worst_canal_idx = best_index(margenes, reverse=True) or 0
        fig_canal = go.Figure(
            go.Bar(
                y=canales,
                x=margenes,
                orientation="h",
                customdata=importes_canal,
                marker_color=smart_bar_colors(margenes, highlight=best_canal_idx),
                text=[f"{value:.1f}%" for value in margenes],
                textposition="outside",
                hovertemplate="<b>%{y}</b><br>Margen: %{x:.1f}%<br>Ventas: USD %{customdata:,.0f}<extra></extra>",
            )
        )
        fig_canal.add_vline(
            x=sum(margenes) / len(margenes),
            line_color=CHART_COLORS[2],
            line_dash="dot",
            annotation_text="promedio",
            annotation_position="top",
        )
        add_metric_badge(fig_canal, f"Menor margen en {canales[worst_canal_idx]}", tone="warning")
    else:
        fig_canal = empty_figure(height=340)
    fig_canal.update_layout(**chart_layout(height=340, showlegend=False))
    fig_canal.update_layout(
        showlegend=False,
        xaxis_title="Margen %",
        margin=dict(l=190, r=26, t=24, b=34),
        yaxis=dict(showgrid=False, showline=False),
    )

    if top_clientes:
        clientes_top = [item["cliente"] for item in top_clientes]
        ventas_top = [item["importe_usd"] for item in top_clientes]
        margen_top = [item["margen_pct"] for item in top_clientes]
        standout_idx = best_index(margen_top) or 0
        fig_top = go.Figure(
            go.Scatter(
                x=ventas_top,
                y=margen_top,
                mode="markers+text",
                text=[name if idx < 4 else "" for idx, name in enumerate(clientes_top)],
                textposition="top center",
                marker=dict(
                    size=[max(14, min(34, value / 22_000)) for value in ventas_top],
                    color=[CHART_COLORS[0] if idx == standout_idx else CHART_COLORS[3] for idx, _ in enumerate(clientes_top)],
                    opacity=0.88,
                    line=dict(width=1, color="rgba(36,49,38,0.12)"),
                ),
                customdata=clientes_top,
                hovertemplate="<b>%{customdata}</b><br>Ventas: USD %{x:,.0f}<br>Margen: %{y:.1f}%<extra></extra>",
            )
        )
        avg_x = sum(ventas_top) / len(ventas_top)
        avg_y = sum(margen_top) / len(margen_top)
        fig_top.add_vline(x=avg_x, line_color="rgba(108,140,90,0.35)", line_dash="dot")
        fig_top.add_hline(y=avg_y, line_color="rgba(108,140,90,0.35)", line_dash="dot")
        add_metric_badge(fig_top, f"{clientes_top[standout_idx]} es la cuenta más rentable", tone="primary")
    else:
        fig_top = empty_figure(height=340)
    fig_top.update_layout(**chart_layout(height=340, showlegend=False))
    fig_top.update_layout(showlegend=False, xaxis_title="USD", yaxis_title="Margen %")

    if evolucion:
        meses = [format_month_label(item["mes"]) for item in evolucion]
        ventas_mes = [item["importe_usd"] for item in evolucion]
        kilos_mes = [item["kg"] for item in evolucion]
        peak_month_idx = best_index(ventas_mes) or 0
        fig_evolucion = go.Figure()
        fig_evolucion.add_trace(
            go.Bar(
                x=meses,
                y=ventas_mes,
                name="Ventas USD",
                marker_color=CHART_COLORS[1],
                hovertemplate="<b>%{x}</b><br>Ventas: USD %{y:,.0f}<extra></extra>",
            )
        )
        fig_evolucion.add_trace(
            go.Scatter(
                x=meses,
                y=kilos_mes,
                name="Kg vendidos",
                mode="lines+markers",
                line=dict(color=CHART_COLORS[4], width=2.5),
                marker=dict(size=7, color=CHART_COLORS[4]),
                hovertemplate="<b>%{x}</b><br>Kg vendidos: %{y:,.0f}<extra></extra>",
                yaxis="y2",
            )
        )
        fig_evolucion.update_layout(yaxis2=dict(overlaying="y", side="right", title="Kg", showgrid=False))
        add_peak_annotation(
            fig_evolucion,
            meses[peak_month_idx],
            ventas_mes[peak_month_idx],
            f"Pico {fmt_usd(ventas_mes[peak_month_idx])}",
        )
        add_metric_badge(fig_evolucion, f"{meses[peak_month_idx]} concentró el mayor ingreso del período", tone="primary")
    else:
        fig_evolucion = empty_figure(height=420)
    fig_evolucion.update_layout(**chart_layout(height=420, emphasis="hero", unified_hover=True))
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
