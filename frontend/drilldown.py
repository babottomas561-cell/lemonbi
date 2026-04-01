from __future__ import annotations

import re

import pandas as pd
from dash import ALL, Input, Output, State, dcc, html, no_update
from dash.exceptions import PreventUpdate
from dash import ctx

from frontend.components.empty_state import empty_state
from frontend.components.tables import render_table
from frontend.utils import api_get, filter_params


def _filter_chips(filters: list[dict]) -> html.Div:
    if not filters:
        return html.Div("Sin filtros adicionales", className="drilldown-filter-empty")
    return html.Div(
        [
            html.Div(
                [
                    html.Span(item.get("label", ""), className="drilldown-filter-label"),
                    html.Span(item.get("value", ""), className="drilldown-filter-value"),
                ],
                className="drilldown-filter-pill",
            )
            for item in filters
        ],
        className="drilldown-filters",
    )


def _safe_filename(value: str) -> str:
    slug = re.sub(r"[^a-zA-Z0-9_-]+", "_", (value or "drilldown").strip())
    return slug.strip("_") or "drilldown"


def register_drilldown_callbacks(app):
    @app.callback(
        Output("drilldown-modal", "is_open"),
        Output("drilldown-request", "data"),
        Input({"type": "drill-kpi", "panel": ALL, "item": ALL}, "n_clicks"),
        Input({"type": "drill-chart", "panel": ALL, "item": ALL}, "n_clicks"),
        Input("drilldown-close", "n_clicks"),
        State({"type": "panel-filters", "panel": ALL}, "id"),
        State({"type": "panel-filters", "panel": ALL}, "data"),
        prevent_initial_call=True,
    )
    def toggle_drilldown_modal(_kpi_clicks, _chart_clicks, _close_clicks, filter_store_ids, filter_store_values):
        triggered = ctx.triggered_id
        if triggered == "drilldown-close":
            return False, no_update
        if not isinstance(triggered, dict):
            raise PreventUpdate

        kind = "kpi" if triggered.get("type") == "drill-kpi" else "chart"
        panel = triggered.get("panel", "")
        item = triggered.get("item", "")
        active_filters = {}
        for store_id, store_value in zip(filter_store_ids or [], filter_store_values or []):
            if store_id.get("panel") == panel:
                active_filters = store_value or {}
                break

        return True, {
            "kind": kind,
            "panel": panel,
            "item": item,
            "filters": active_filters,
            "nonce": ctx.triggered[0]["value"],
        }

    @app.callback(
        Output("drilldown-modal-title", "children"),
        Output("drilldown-modal-description", "children"),
        Output("drilldown-modal-body", "children"),
        Output("drilldown-data", "data"),
        Input("drilldown-request", "data"),
        prevent_initial_call=True,
    )
    def load_drilldown_payload(request_data):
        if not request_data:
            raise PreventUpdate

        kind = request_data.get("kind")
        panel = request_data.get("panel")
        item = request_data.get("item")
        params = filter_params(**(request_data.get("filters") or {}))
        payload = api_get(f"/api/drilldown/{kind}/{panel}/{item}", params=params, timeout=20)

        if not payload:
            message = empty_state(
                title="Detalle no disponible",
                message="No fue posible cargar los datos fuente para este indicador.",
                icon="!",
            )
            return "Detalle no disponible", "", message, {}

        rows = payload.get("rows", [])
        columns = payload.get("columns", [])
        record_count = payload.get("record_count", 0)
        body = html.Div(
            [
                html.Div(
                    [
                        html.Div(
                            [
                                html.Div("Filtros activos", className="drilldown-section-title"),
                                _filter_chips(payload.get("filters", [])),
                            ],
                            className="drilldown-meta-card",
                        ),
                        html.Div(
                            [
                                html.Div("Registros fuente", className="drilldown-section-title"),
                                html.Div(f"{record_count:,.0f}", className="drilldown-stat-value"),
                                html.Div("filas disponibles para análisis y descarga", className="drilldown-stat-caption"),
                            ],
                            className="drilldown-meta-card compact",
                        ),
                    ],
                    className="drilldown-meta-grid",
                ),
                html.Div(
                    [
                        html.Div("Datos base", className="table-header"),
                        render_table(rows, columns, "drilldown-table", page_size=14, max_rows=140)
                        if rows
                        else empty_state(
                            title="Sin datos para mostrar",
                            message="No se encontraron registros fuente para la combinación de filtros actual.",
                        ),
                    ],
                    className="table-card drilldown-table-card",
                ),
            ]
        )
        return payload.get("title", "Detalle"), payload.get("description", ""), body, payload

    @app.callback(
        Output("drilldown-download-csv-btn", "disabled"),
        Output("drilldown-download-excel-btn", "disabled"),
        Input("drilldown-data", "data"),
    )
    def sync_download_actions(payload):
        has_rows = bool(payload and payload.get("rows"))
        return (not has_rows, not has_rows)

    @app.callback(
        Output("drilldown-download-csv", "data"),
        Input("drilldown-download-csv-btn", "n_clicks"),
        State("drilldown-data", "data"),
        prevent_initial_call=True,
    )
    def download_csv(n_clicks, payload):
        if not n_clicks or not payload or not payload.get("rows"):
            raise PreventUpdate
        frame = pd.DataFrame(payload["rows"])
        return dcc.send_data_frame(
            frame.to_csv,
            f"{_safe_filename(payload.get('file_name'))}.csv",
            index=False,
            encoding="utf-8-sig",
        )

    @app.callback(
        Output("drilldown-download-excel", "data"),
        Input("drilldown-download-excel-btn", "n_clicks"),
        State("drilldown-data", "data"),
        prevent_initial_call=True,
    )
    def download_excel(n_clicks, payload):
        if not n_clicks or not payload or not payload.get("rows"):
            raise PreventUpdate
        frame = pd.DataFrame(payload["rows"])
        return dcc.send_data_frame(
            frame.to_excel,
            f"{_safe_filename(payload.get('file_name'))}.xlsx",
            sheet_name="Detalle",
            index=False,
        )
