"""Reusable DataTable component."""
from dash import dash_table, html

from frontend.components.empty_state import empty_state


def render_table(data, columns, table_id, page_size=12, max_rows=80):
    """
    data: list of dicts
    columns: list of {"name": display_name, "id": dict_key, "type": optional}
    """
    if not data:
        return html.Div(
            empty_state(
                title="Sin detalle para mostrar",
                message="No hay filas disponibles para los filtros seleccionados.",
            ),
            className="table-empty-wrapper",
        )

    visible_data = data[:max_rows]
    note = None
    if len(data) > max_rows:
        note = html.Div(
            f"Mostrando {max_rows} de {len(data)} filas para mantener fluidez.",
            className="table-note",
        )

    return html.Div(
        [
            note,
            dash_table.DataTable(
                id=table_id,
                data=visible_data,
                columns=columns,
                page_size=min(page_size, len(visible_data)),
                page_action="native",
                sort_action="native",
                filter_action="native",
                style_table={"overflowX": "auto", "maxHeight": "540px", "overflowY": "auto", "backgroundColor": "transparent"},
                fixed_rows={"headers": True},
                style_as_list_view=True,
                style_header={
                    "backgroundColor": "rgba(248, 244, 235, 0.88)",
                    "fontWeight": "700",
                    "fontSize": "11.5px",
                    "color": "#6B7280",
                    "textTransform": "uppercase",
                    "letterSpacing": "0.7px",
                    "border": "none",
                    "borderBottom": "1px solid rgba(78, 90, 67, 0.1)",
                    "padding": "12px 14px",
                },
                style_cell={
                    "fontSize": "13px",
                    "color": "#1A1A1A",
                    "backgroundColor": "transparent",
                    "border": "none",
                    "borderBottom": "1px solid rgba(78, 90, 67, 0.06)",
                    "padding": "12px 14px",
                    "fontFamily": "'Source Sans 3', 'Segoe UI', sans-serif",
                    "whiteSpace": "normal",
                    "maxWidth": "220px",
                    "overflow": "hidden",
                    "textOverflow": "ellipsis",
                },
                style_data_conditional=[
                    {"if": {"row_index": "odd"}, "backgroundColor": "rgba(255, 255, 255, 0.42)"},
                    {"if": {"state": "active"}, "backgroundColor": "rgba(77, 104, 77, 0.08)", "border": "none"},
                    {"if": {"state": "selected"}, "backgroundColor": "rgba(77, 104, 77, 0.1)", "border": "none"},
                ],
                style_filter={
                    "fontSize": "12px",
                    "backgroundColor": "rgba(248, 244, 235, 0.74)",
                    "border": "none",
                    "borderBottom": "1px solid rgba(78, 90, 67, 0.1)",
                },
            ),
        ]
    )
